# tools/upgrade_tool.py
"""smolagents Tools that Commander uses to upgrade its own code.

Workflow this module supports
-----------------------------
1. Commander decides to modify itself ("프롬프트가 너무 길어, 줄여야겠다").
2. Commander generates new commander.py source.
3. Commander calls `stage_upgrade(new_content=...)` — writes
   staging/commander.py.candidate. The live file stays untouched.
4. Commander calls `test_staged_upgrade()` — runs an isolated
   subprocess that imports the candidate and pings every agent's
   LiteLLMModel with one cheap call (per user requirement: real
   call verification, ~$0.001 total).
5. Test PASS → Commander calls `finalize_upgrade()` → marker written
   + sys.exit(EXIT_UPGRADE=10). Watchdog atomically swaps and
   restarts. Done.
6. Test FAIL → Commander reads stderr, fixes the code, repeats from
   step 3. After MAX_UPGRADE_ATTEMPTS failures, Commander gives up
   and calls `abort_upgrade(reason=...)` which removes the candidate
   and notifies the user.

Why these as smolagents Tools
-----------------------------
Commander's prompt could just describe the procedure as Python code
to run via PythonInterpreterTool, but exposing them as named Tools
makes the intent legible in the ReAct trace ("Commander invoked
test_staged_upgrade") and lets us count attempts properly via the
counter file.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from smolagents import Tool


# How many failed boot tests Commander gets before being told to give up.
MAX_UPGRADE_ATTEMPTS = 5

# Where we store the in-flight attempt counter. Reset to 0 when an
# upgrade is finalized OR aborted.
_ATTEMPT_COUNTER_NAME = "UPGRADE_ATTEMPTS"


def _staging_dir() -> Path:
    """Return staging/ under PAPER_AI_ROOT (resolved at call time so a
    test can override via env var)."""
    from config import PAPER_AI_ROOT
    p = PAPER_AI_ROOT / "staging"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _attempt_counter_path() -> Path:
    return _staging_dir() / _ATTEMPT_COUNTER_NAME


def _read_attempts() -> int:
    fp = _attempt_counter_path()
    try:
        return int(fp.read_text().strip()) if fp.is_file() else 0
    except (OSError, ValueError):
        return 0


def _bump_attempts() -> int:
    n = _read_attempts() + 1
    try:
        _attempt_counter_path().write_text(str(n))
    except OSError:
        pass
    return n


def _reset_attempts() -> None:
    try:
        _attempt_counter_path().unlink(missing_ok=True)
    except OSError:
        pass


# ============================================================================ Stage

class StageUpgradeTool(Tool):
    """Write a proposed new commander.py to staging — without touching live."""

    name = "stage_upgrade"
    description = (
        "Stage proposed new content for commander.py at "
        "staging/commander.py.candidate. The live commander.py is NOT "
        "modified. Call test_staged_upgrade next to verify it works "
        "before promoting."
    )
    inputs = {
        "new_content": {
            "type": "string",
            "description": (
                "Complete new commander.py source code. Must be valid "
                "Python. Will be syntax-checked before staging."
            ),
        },
    }
    output_type = "string"

    def forward(self, new_content: str) -> str:
        # Refuse the empty / trivial — almost always a bug in the caller.
        if len(new_content.strip()) < 200:
            return (
                "[stage_upgrade FAILED] new_content is suspiciously short "
                f"({len(new_content)} chars). commander.py is normally "
                "thousands of lines. Refusing to stage."
            )
        # Syntax check before writing — catches obvious typos that
        # would otherwise blow up at boot test.
        try:
            compile(new_content, "<staged_commander>", "exec")
        except SyntaxError as e:
            return (
                f"[stage_upgrade FAILED] syntax error in proposed code: "
                f"{e.msg} at line {e.lineno}. Fix and retry."
            )

        from monitoring.blue_green import candidate_path
        from config import PAPER_AI_ROOT
        cand = candidate_path(PAPER_AI_ROOT)
        try:
            cand.write_text(new_content, encoding="utf-8")
        except OSError as e:
            return f"[stage_upgrade FAILED] could not write candidate: {e}"

        attempts = _read_attempts()
        return (
            f"[stage_upgrade OK] wrote {len(new_content)} bytes to {cand.name}. "
            f"Attempt #{attempts + 1}/{MAX_UPGRADE_ATTEMPTS} ready for testing. "
            f"Call test_staged_upgrade next."
        )


# ============================================================================ Test

class TestStagedUpgradeTool(Tool):
    """Boot-test the staged candidate in an isolated subprocess.

    Per user spec: this does REAL API calls to verify each agent
    works. Cost ~$0.001. Time ~20-30s.
    """

    name = "test_staged_upgrade"
    description = (
        "Boot-test the staged candidate commander.py in an isolated "
        "subprocess. Imports the candidate, instantiates all 6 "
        "LiteLLMModel objects, and sends one short ping to each "
        "agent's API to confirm it actually responds. Returns "
        "PASS or FAIL with diagnostics. Costs ~$0.001 per call."
    )
    inputs = {}
    output_type = "string"

    BOOT_TIMEOUT_S = 60.0

    def forward(self) -> str:
        from config import PAPER_AI_ROOT
        from monitoring.blue_green import candidate_path

        cand = candidate_path(PAPER_AI_ROOT)
        if not cand.is_file():
            return (
                "[test_staged_upgrade FAILED] no candidate file at "
                f"{cand}. Call stage_upgrade first."
            )

        attempts = _bump_attempts()
        if attempts > MAX_UPGRADE_ATTEMPTS:
            return (
                f"[test_staged_upgrade FAILED — limit reached] "
                f"You have used {attempts} attempts (max "
                f"{MAX_UPGRADE_ATTEMPTS}). Call abort_upgrade to give "
                "up and notify the user."
            )

        # Driver script for the subprocess. We can't import the
        # candidate directly because `commander` is already loaded as
        # the LIVE module in this process; importlib loader bypasses
        # the path-based machinery to load a .candidate file as
        # "commander_candidate".
        driver = textwrap.dedent("""
            import os, sys, importlib.util, importlib.machinery, traceback
            cand_path = os.environ["PAPER_AI_CANDIDATE"]
            project_root = os.environ["PAPER_AI_ROOT"]
            sys.path.insert(0, project_root)

            # Step 1: Load the candidate file under a unique module
            # name so the live commander module isn't displaced.
            try:
                loader = importlib.machinery.SourceFileLoader(
                    "commander_candidate", cand_path,
                )
                spec = importlib.util.spec_from_loader(
                    "commander_candidate", loader,
                )
                mod = importlib.util.module_from_spec(spec)
                sys.modules["commander_candidate"] = mod
                loader.exec_module(mod)
            except Exception as e:
                traceback.print_exc()
                print(f"BOOT_FAIL_IMPORT: {type(e).__name__}: {e}",
                      file=sys.stderr)
                sys.exit(2)

            # Step 2: Confirm the candidate has the expected shape.
            commander_obj = getattr(mod, "commander", None)
            if commander_obj is None:
                print("BOOT_FAIL_SHAPE: no `commander` CodeAgent variable",
                      file=sys.stderr)
                sys.exit(3)
            managed = getattr(commander_obj, "managed_agents", None) or {}
            # smolagents stores managed_agents as a dict keyed by name
            # (or list — depends on version). Accept either.
            if isinstance(managed, dict):
                names = sorted(managed.keys())
            elif isinstance(managed, list):
                names = sorted(getattr(a, "name", "?") for a in managed)
            else:
                names = []
            print(f"managed_agents: {names}", file=sys.stderr)

            # Step 3: Real API ping for each agent (per user request).
            from config import get_api_key, get_model_id
            from smolagents import LiteLLMModel
            from smolagents.models import ChatMessage

            roles = ["commander", "librarian", "idea",
                     "experimenter", "reviewer", "writer"]
            failures = []
            for role in roles:
                try:
                    m = LiteLLMModel(
                        model_id=f"anthropic/{get_model_id(role)}",
                        api_key=get_api_key(role),
                    )
                    # Single trivial call. Reply length capped via
                    # max_tokens; we only care that it doesn't raise.
                    msg = [ChatMessage(role="user",
                                        content="Reply with the word OK.")]
                    resp = m(msg)
                    text = (getattr(resp, "content", None) or "")[:30]
                    print(f"  {role:14s} OK  ({text!r})", file=sys.stderr)
                except Exception as e:
                    print(f"  {role:14s} FAIL  {type(e).__name__}: {e}",
                          file=sys.stderr)
                    failures.append(f"{role}: {type(e).__name__}: {e}")

            if failures:
                print("BOOT_FAIL_API: " + "; ".join(failures),
                      file=sys.stderr)
                sys.exit(4)

            print("BOOT_OK")
        """)

        env = os.environ.copy()
        env["PAPER_AI_CANDIDATE"] = str(cand)
        env["PAPER_AI_ROOT"] = str(PAPER_AI_ROOT)

        try:
            proc = subprocess.run(
                [sys.executable, "-c", driver],
                cwd=str(PAPER_AI_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.BOOT_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return (
                f"[test_staged_upgrade FAILED — timeout] "
                f"boot test exceeded {self.BOOT_TIMEOUT_S}s. "
                "Likely an infinite loop or hung API call in the new code."
            )
        except Exception as e:
            return f"[test_staged_upgrade FAILED — launch] {e}"

        ok = (proc.returncode == 0
              and "BOOT_OK" in (proc.stdout or ""))
        # The driver uses stderr for everything diagnostic, so include
        # the tail of both for debugging.
        out_tail = (proc.stdout or "")[-300:]
        err_tail = (proc.stderr or "")[-1200:]

        if ok:
            return (
                f"[test_staged_upgrade PASS] attempt #{attempts}. "
                f"All 6 agents responded. Diagnostics:\n{err_tail}\n\n"
                "Call finalize_upgrade to promote and restart."
            )
        return (
            f"[test_staged_upgrade FAIL] attempt #{attempts}/"
            f"{MAX_UPGRADE_ATTEMPTS}. exit_code={proc.returncode}.\n"
            f"stdout: {out_tail}\n"
            f"stderr: {err_tail}\n\n"
            "Diagnose the error and try stage_upgrade again with a "
            "fix, OR call abort_upgrade if the problem is unfixable."
        )


# ============================================================================ Finalize

class FinalizeUpgradeTool(Tool):
    """Promote the candidate and exit with EXIT_UPGRADE so watchdog swaps."""

    name = "finalize_upgrade"
    description = (
        "Mark the staged commander.py as ready for promotion and exit "
        "the current Commander process. The watchdog will detect the "
        "marker, atomically swap the candidate into live, and restart "
        "Commander with the new code. Only call AFTER "
        "test_staged_upgrade returns PASS."
    )
    inputs = {}
    output_type = "string"

    # Exit code agreed with the watchdog. See monitoring/watchdog.py:
    # EXIT_UPGRADE = 10.
    EXIT_UPGRADE = 10

    def forward(self) -> str:
        from config import PAPER_AI_ROOT
        from monitoring.blue_green import candidate_path, marker_path

        cand = candidate_path(PAPER_AI_ROOT)
        if not cand.is_file():
            return (
                "[finalize_upgrade FAILED] no candidate. "
                "Call stage_upgrade + test_staged_upgrade first."
            )

        # Write the marker. The watchdog reads this on next boot to
        # decide whether to finalize before re-spawning.
        try:
            marker_path(PAPER_AI_ROOT).write_text("ready\n", encoding="utf-8")
        except OSError as e:
            return f"[finalize_upgrade FAILED] could not write marker: {e}"

        _reset_attempts()

        # Now exit with the agreed code. We DON'T let smolagents return
        # a normal value because that would let Commander think it can
        # keep running — we need the process to terminate so watchdog
        # can swap the file.
        print(
            "\n[finalize_upgrade] marker written. Exiting with code 10 "
            "for watchdog promotion.\n",
            flush=True,
        )
        # smolagents tools normally return a string. But since we're
        # going to sys.exit, the return value won't be used. We use
        # os._exit here instead of sys.exit because sys.exit raises
        # SystemExit which smolagents would catch and convert to a
        # tool error. os._exit terminates immediately.
        os._exit(self.EXIT_UPGRADE)


# ============================================================================ Abort

class AbortUpgradeTool(Tool):
    """Give up on the upgrade after exhausting attempts. Notify the user."""

    name = "abort_upgrade"
    description = (
        "Abort an in-progress upgrade. Removes the staged candidate "
        "and writes a user-visible note explaining why. Call this "
        "when test_staged_upgrade has failed repeatedly and the "
        "problem is unfixable. After this, Commander continues "
        "running normally on the OLD live commander.py."
    )
    inputs = {
        "reason": {
            "type": "string",
            "description": (
                "Explanation of why the upgrade was abandoned. Will "
                "be written to annotations/agent_notes.md and shown "
                "to the user. Be specific: include the failure mode "
                "and what was attempted."
            ),
        },
    }
    output_type = "string"

    def forward(self, reason: str) -> str:
        from config import PAPER_AI_ROOT, PATHS
        from monitoring.blue_green import candidate_path, marker_path
        from datetime import datetime

        # Clean up staging artefacts so the next run starts fresh.
        for fn in [
            candidate_path(PAPER_AI_ROOT),
            marker_path(PAPER_AI_ROOT),
        ]:
            try:
                fn.unlink(missing_ok=True)
            except OSError:
                pass
        attempts_used = _read_attempts()
        _reset_attempts()

        # Write a user-visible note.
        notes_path = PATHS["annotations"] / "agent_notes.md"
        try:
            with notes_path.open("a", encoding="utf-8") as f:
                f.write(
                    f"\n## [{datetime.now().strftime('%Y-%m-%d %H:%M')}] "
                    f"⚠️ Self-upgrade aborted\n"
                    f"- Attempts used: {attempts_used}/{MAX_UPGRADE_ATTEMPTS}\n"
                    f"- Reason: {reason}\n"
                    f"- Action: continuing on the existing commander.py. "
                    "Manual intervention may be needed.\n"
                )
        except OSError:
            pass

        # Also surface to stdout so the user sees it immediately when
        # running interactively.
        print(
            "\n" + "=" * 60 +
            f"\n⚠️  SELF-UPGRADE ABORTED ({attempts_used} attempts)" +
            f"\nReason: {reason}" +
            "\nContinuing on the current commander.py." +
            "\nDetails written to annotations/agent_notes.md." +
            "\n" + "=" * 60 + "\n",
            flush=True,
        )

        return (
            f"[abort_upgrade DONE] candidate removed, marker cleared, "
            f"counter reset. {attempts_used} attempts had been used. "
            "Continuing on existing commander.py."
        )
