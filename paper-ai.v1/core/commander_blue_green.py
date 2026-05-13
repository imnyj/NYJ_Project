"""Blue-Green self-upgrade for commander.py.

Problem this module solves
--------------------------
`SelfUpgrader` normally writes new file content, runs `cli.py --verify-config`
as a smoke test, and on success returns to the watchdog which re-execs. For
most files this is safe: the smoke test imports them. For `commander.py`
specifically the smoke test is **not enough**:

    * `cli.py --verify-config` does not instantiate `CommanderAgent`.
    * An import-level error surfaces in `--verify-config`, but a runtime
      error in `CommanderAgent.__init__` or in the first `think()` call
      only shows up after watchdog re-execs the *real* process — which is
      already too late because the old commander.py has been overwritten.

The promotion strategy
----------------------
Treat `commander.py` like a deployable service. The live file is BLUE.
The proposed new content is written to `commander.py.candidate` (GREEN).
We boot-test GREEN in a throw-away subprocess that imports it and
instantiates `CommanderAgent` with a fake client. Only if that succeeds do
we atomically `os.replace(candidate, commander.py)`.

Guarantees
----------
* The live `commander.py` is NEVER modified before the candidate passes.
* On candidate failure, the candidate file is removed; BLUE keeps running.
* On candidate success, promotion is a single `os.replace` — atomic on
  POSIX and on NTFS/ReFS (Windows 10+). No half-promoted state.
* The watchdog still sees the usual EXIT_UPGRADE(10) signal only when the
  promotion succeeded end-to-end.

This module is intentionally narrow: it handles exactly one file
(`commander.py` at project root). All other files flow through the
normal `SelfUpgrader._atomic_write` path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from core.logger import get_logger

log = get_logger("commander_bluegreen")

COMMANDER_FILENAME = "commander.py"
CANDIDATE_SUFFIX = ".candidate"


@dataclass
class PromotionResult:
    """Outcome of a commander.py promotion attempt."""
    promoted: bool
    reason: str
    stdout: str = ""
    stderr: str = ""
    candidate_path: str | None = None


class CommanderPromoter:
    """Stage, boot-test, and atomically promote a new commander.py."""

    BOOT_TEST_TIMEOUT_S = 30.0

    def __init__(self, project_root: Path):
        self.root = Path(project_root).resolve()
        self.live = self.root / COMMANDER_FILENAME
        self.candidate = self.root / (COMMANDER_FILENAME + CANDIDATE_SUFFIX)

    # ------------------------------------------------------------ stage

    def stage(self, new_content: str) -> Path:
        """Write proposed new content to `commander.py.candidate`.

        Does NOT touch the live commander.py. Returns the candidate path.
        """
        # Safety: refuse to stage an empty file — that almost certainly is a
        # bug in the caller and would silently disable commander.
        if not new_content.strip():
            raise ValueError("refusing to stage empty commander.py content")
        self.candidate.write_text(new_content, encoding="utf-8")
        log.info("candidate_staged",
                 path=str(self.candidate), bytes=len(new_content))
        return self.candidate

    # ------------------------------------------------------------ boot test

    def boot_test(self) -> tuple[bool, str, str]:
        """Import the CANDIDATE commander and instantiate it with a fake
        client in a subprocess.

        Returns (ok, stdout, stderr). The subprocess runs with
        PAPER_AI_COMMANDER_SOURCE pointing at the candidate file so the
        test loads the NEW code, not the live one. Actual network / API
        calls are avoided by using a minimal stub AnthropicClient.
        """
        if not self.candidate.is_file():
            return False, "", f"no candidate at {self.candidate}"

        # The subprocess executes this small driver. It must:
        #   (1) load the candidate's bytes and exec it in an isolated
        #       module namespace (so we don't touch the live commander).
        #   (2) construct a no-op client that satisfies whatever BaseAgent
        #       needs at __init__ time.
        #   (3) instantiate CommanderAgent and call a trivial method.
        driver = textwrap.dedent("""
            import os, sys, types, importlib.util, importlib.machinery
            candidate = os.environ["PAPER_AI_COMMANDER_SOURCE"]
            root = os.environ["PAPER_AI_ROOT"]
            sys.path.insert(0, root)

            # Load candidate as module "commander" without importing the
            # live file. Because the candidate filename ends in .candidate,
            # we must give importlib an explicit SourceFileLoader — the
            # default loader only picks files matching *.py.
            loader = importlib.machinery.SourceFileLoader("commander", candidate)
            spec = importlib.util.spec_from_loader("commander", loader)
            if spec is None:
                print("BOOT_FAIL: cannot build spec", file=sys.stderr); sys.exit(2)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["commander"] = mod
            try:
                loader.exec_module(mod)
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"BOOT_FAIL: exec_module: {e!r}", file=sys.stderr); sys.exit(3)

            CommanderAgent = getattr(mod, "CommanderAgent", None)
            if CommanderAgent is None:
                print("BOOT_FAIL: no CommanderAgent class", file=sys.stderr); sys.exit(4)

            # Build the minimum fake client that BaseAgent + anything
            # touched in __init__ might access. Intentionally no network.
            class _FakePolicy:
                agents = {"tools": {"commander": []},
                          "skills": {"commander": []},
                          "models": {"opus": "claude-opus-4-7",
                                     "sonnet": "claude-sonnet-4-6",
                                     "haiku": "claude-haiku-4-5-20251001"},
                          "defaults": {"commander": "opus"}}
                settings = {}
                routing = {"task_types": {},
                           "target_distribution": {}, "tolerance": 0.15}
                budgets = {"per_agent_turn": {"max_output_tokens": 8192,
                                              "max_input_tokens": 180000},
                           "per_paper": {"max_usd": 10},
                           "per_session": {"max_usd": 5},
                           "warn_at": {"usd_per_paper": 5}}
                caching = {"enabled": False,
                           "tools": {"cache_definitions": False}}
            class _FakeClient:
                policy = _FakePolicy()
            try:
                ca = CommanderAgent(_FakeClient())
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"BOOT_FAIL: __init__: {e!r}", file=sys.stderr); sys.exit(5)

            # Touch a couple of attributes the pipeline relies on.
            if not hasattr(ca, "role"):
                print("BOOT_FAIL: no .role", file=sys.stderr); sys.exit(6)
            if ca.role != "commander":
                print(f"BOOT_FAIL: role={ca.role!r}", file=sys.stderr); sys.exit(7)

            print("BOOT_OK")
        """)

        env = os.environ.copy()
        env["PAPER_AI_COMMANDER_SOURCE"] = str(self.candidate)
        env["PAPER_AI_ROOT"] = str(self.root)
        # Disable any API keys so no real calls happen by accident.
        env.pop("ANTHROPIC_API_KEY", None)

        try:
            proc = subprocess.run(
                [sys.executable, "-c", driver],
                cwd=str(self.root),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.BOOT_TEST_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "", (
                f"boot test timeout after {self.BOOT_TEST_TIMEOUT_S}s"
            )
        except Exception as e:
            return False, "", f"boot test launch failure: {e!r}"

        ok = proc.returncode == 0 and "BOOT_OK" in (proc.stdout or "")
        log.info("candidate_boot_test",
                 ok=ok, rc=proc.returncode,
                 stdout_tail=(proc.stdout or "")[-200:],
                 stderr_tail=(proc.stderr or "")[-400:])
        return ok, proc.stdout or "", proc.stderr or ""

    # ------------------------------------------------------------ promote

    def promote(self) -> None:
        """Atomically replace live commander.py with the candidate.

        os.replace is atomic within a single filesystem. The candidate
        file is staged in the same directory as the live file, so this
        is safe on every supported OS. After a successful replace the
        candidate path no longer exists.
        """
        if not self.candidate.is_file():
            raise FileNotFoundError(f"no candidate to promote at {self.candidate}")
        os.replace(self.candidate, self.live)
        log.warning("commander_promoted",
                    live=str(self.live),
                    candidate_removed=True)

    # ------------------------------------------------------------ abort

    def abort(self, reason: str) -> None:
        """Remove the candidate file, leaving the live commander untouched."""
        if self.candidate.is_file():
            try:
                self.candidate.unlink()
            except OSError as e:
                log.error("abort_unlink_failed",
                          path=str(self.candidate), err=str(e))
        log.warning("commander_promotion_aborted", reason=reason)

    # ------------------------------------------------------------ end-to-end

    def stage_test_and_promote(
        self, new_content: str
    ) -> PromotionResult:
        """Convenience: stage, run boot-test, promote on success.

        Returns a PromotionResult. Caller is responsible for signalling
        the watchdog (EXIT_UPGRADE) only when `promoted=True`.
        """
        self.stage(new_content)
        ok, out, err = self.boot_test()
        if not ok:
            self.abort(reason="boot_test_failed")
            return PromotionResult(
                promoted=False,
                reason="candidate failed boot test",
                stdout=out, stderr=err,
                candidate_path=None,
            )
        try:
            self.promote()
        except Exception as e:
            # Promote itself failed (filesystem race, permissions).
            # The candidate may still be on disk; try to clean up so a
            # stray file doesn't poison later promotions.
            self.abort(reason=f"promote_failed:{e!r}")
            return PromotionResult(
                promoted=False,
                reason=f"promote step raised: {e!r}",
                stdout=out, stderr=err,
                candidate_path=None,
            )
        return PromotionResult(
            promoted=True,
            reason="boot test ok, live commander.py replaced",
            stdout=out, stderr=err,
            candidate_path=None,
        )
