"""Qwen profile triad — main / backup / candidate.

Why a "profile" instead of individual files?
---------------------------------------------
Qwen's behaviour is the joint product of several files: its system
prompt, its routing overrides, its runtime config (temperature,
max_tokens, base_url), and its accumulated facts. Self-upgrading any
one of them in isolation can break the others (e.g. a new prompt
that assumes a higher max_tokens). Treating the bundle as an atomic
"profile" means a single os.replace of a directory gets us all-or-
nothing semantics — the same guarantee the commander Blue-Green flow
provides for `commander.py`.

Directory layout
----------------
    memory/qwen_profile/
        main/           ← currently-serving profile (always present)
        backup/         ← last known-good profile (always present)
        candidate/      ← proposed next profile (transient)

Files inside each:
    prompt.txt                  — system prompt Qwen sees
    config.yaml                 — {temperature, max_tokens, base_url,
                                   model, timeout_s, prompt_style, ...}
    routing_overrides.yaml      — task-type → options map (merged on top
                                   of the global routing.yaml)
    facts.snapshot.md           — frozen copy of qwen_facts.md at the
                                   time this profile was promoted
                                   (the live memory/qwen_facts.md is
                                   outside the profile so both paper-ai
                                   and companion share it)

Transitions
-----------
    stage(new_profile_dict)  →  candidate/ written
    boot_test()              →  subprocess loads candidate, runs smoke
    promote()                →  atomic: main→backup, candidate→main
    abort(reason)            →  rm -rf candidate
    restore_from_backup()    →  atomic: backup→main (backup stays as copy)

The restore path exists because self-upgrade can — in theory — go
wrong even after promotion: the boot test is a smoke test, not a
full integration test. If the companion or pipeline detects a
regression on main *after* it's live, it can restore without
needing the user to intervene.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.logger import get_logger
from core.paths import get_paths

log = get_logger("qwen_profile")


# Files that define a profile. Any file outside this set in a profile
# directory is ignored on read and wiped on promote.
PROFILE_FILES = (
    "prompt.txt",
    "config.yaml",
    "routing_overrides.yaml",
    "facts.snapshot.md",
)


@dataclass
class QwenProfile:
    """In-memory representation of a profile directory."""
    prompt: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    routing_overrides: dict[str, Any] = field(default_factory=dict)
    facts_snapshot: str = ""

    def is_empty(self) -> bool:
        return not (self.prompt or self.config or self.routing_overrides)

    def to_files(self, dir_: Path) -> None:
        """Write this profile to `dir_`, creating missing files."""
        dir_.mkdir(parents=True, exist_ok=True)
        (dir_ / "prompt.txt").write_text(self.prompt or "", encoding="utf-8")
        (dir_ / "config.yaml").write_text(
            yaml.safe_dump(self.config or {}, sort_keys=True, allow_unicode=True),
            encoding="utf-8",
        )
        (dir_ / "routing_overrides.yaml").write_text(
            yaml.safe_dump(self.routing_overrides or {}, sort_keys=True,
                           allow_unicode=True),
            encoding="utf-8",
        )
        (dir_ / "facts.snapshot.md").write_text(
            self.facts_snapshot or "", encoding="utf-8",
        )

    @classmethod
    def from_files(cls, dir_: Path) -> "QwenProfile":
        if not dir_.is_dir():
            return cls()
        prompt = ""
        cfg: dict[str, Any] = {}
        routing: dict[str, Any] = {}
        facts = ""
        p_prompt = dir_ / "prompt.txt"
        p_cfg = dir_ / "config.yaml"
        p_routing = dir_ / "routing_overrides.yaml"
        p_facts = dir_ / "facts.snapshot.md"
        if p_prompt.is_file():
            prompt = p_prompt.read_text(encoding="utf-8")
        if p_cfg.is_file():
            cfg = yaml.safe_load(p_cfg.read_text(encoding="utf-8")) or {}
        if p_routing.is_file():
            routing = yaml.safe_load(p_routing.read_text(encoding="utf-8")) or {}
        if p_facts.is_file():
            facts = p_facts.read_text(encoding="utf-8")
        return cls(prompt=prompt, config=cfg, routing_overrides=routing,
                   facts_snapshot=facts)


@dataclass
class ProfileBootResult:
    ok: bool
    reason: str
    stdout: str = ""
    stderr: str = ""
    elapsed_s: float = 0.0


# ============================================================================ manager


class QwenProfileManager:
    """Manage the main/backup/candidate triad with atomic transitions.

    This is pure filesystem orchestration. It does NOT call Qwen itself;
    the boot-test subprocess invokes a small driver that, given a
    candidate directory, instantiates `LocalLLMClient` configured to
    read from that directory and sends a handful of smoke prompts.
    """

    BOOT_TEST_TIMEOUT_S = 90.0

    # Minimal canned smoke prompts. Each tuple is (prompt, must_contain_any).
    # Kept intentionally short — the goal is to confirm the candidate
    # *responds* in the expected shape, not to evaluate quality.
    SMOKE_PROMPTS: list[tuple[str, list[str]]] = [
        ("Classify the following sentence as 'question' or 'statement'. "
         "Sentence: 'Is this a test?' Reply with only the single word.",
         ["question"]),
        ("Extract the year from: 'Published in 2021 at IEEE T-ITS.' "
         "Reply with only the four-digit number.",
         ["2021"]),
        ("Three keywords for: 'Reinforcement learning for urban traffic "
         "signal control'. Reply as a comma-separated list, no extras.",
         ["reinforcement", "traffic", "signal"]),
    ]

    def __init__(self, *, paths=None):
        self.paths = paths or get_paths()

    # ---------------------------------------------------------------- load

    def load_main(self) -> QwenProfile:
        """Current serving profile. Callers (LocalLLMClient, pipeline,
        companion) should go through this."""
        return QwenProfile.from_files(self.paths.qwen_profile_main)

    def load_backup(self) -> QwenProfile:
        return QwenProfile.from_files(self.paths.qwen_profile_backup)

    def load_candidate(self) -> QwenProfile:
        return QwenProfile.from_files(self.paths.qwen_profile_candidate)

    def has_candidate(self) -> bool:
        d = self.paths.qwen_profile_candidate
        return d.is_dir() and (d / "config.yaml").exists()

    def has_backup(self) -> bool:
        d = self.paths.qwen_profile_backup
        return d.is_dir() and (d / "config.yaml").exists()

    # ---------------------------------------------------------------- stage

    def stage(self, profile: QwenProfile) -> Path:
        """Write `profile` to candidate/, replacing any prior candidate.

        Does NOT touch main/ or backup/. Returns the candidate path.
        """
        if profile.is_empty():
            raise ValueError("refusing to stage an empty Qwen profile")
        cand = self.paths.qwen_profile_candidate
        if cand.exists():
            shutil.rmtree(cand)
        cand.mkdir(parents=True, exist_ok=True)
        profile.to_files(cand)
        log.info("qwen_candidate_staged",
                 path=str(cand),
                 prompt_bytes=len(profile.prompt),
                 routing_rules=len(profile.routing_overrides))
        return cand

    # ---------------------------------------------------------------- boot test

    def boot_test(self) -> ProfileBootResult:
        """Spawn a subprocess that loads the candidate profile and runs the
        canned smoke prompts against it. Returns a ProfileBootResult.

        The subprocess uses the CANDIDATE's config.yaml to decide which
        Ollama model to hit. If Ollama isn't running or the model isn't
        pulled, the probe returns ok=False with a clear reason (not a
        generic failure), so the caller can distinguish "candidate is bad"
        from "runtime is bad".
        """
        if not self.has_candidate():
            return ProfileBootResult(ok=False, reason="no candidate on disk")

        driver = textwrap.dedent(r"""
            import os, sys, json, time
            sys.path.insert(0, os.environ["PAPER_AI_ROOT"])
            cand_dir = os.environ["QWEN_CANDIDATE_DIR"]

            from tools.local_llm_client import LocalLLMClient, LocalLLMUnavailable
            from core.policy_runtime import PolicyRuntime
            from memory.qwen_profile import QwenProfile

            prof = QwenProfile.from_files(__import__("pathlib").Path(cand_dir))
            cfg = prof.config or {}
            model = cfg.get("model", "qwen2.5:72b")
            base_url = cfg.get("base_url", "http://127.0.0.1:11434")
            timeout_s = float(cfg.get("timeout_s", 30))

            policy = PolicyRuntime(config_dir=os.path.join(
                os.environ["PAPER_AI_ROOT"], "config"))
            client = LocalLLMClient(policy=policy, model=model,
                                    base_url=base_url, timeout_s=timeout_s)

            if not client.is_available():
                print("BOOT_FAIL: local LLM unavailable "
                      "(daemon down or model not pulled?)", file=sys.stderr)
                sys.exit(5)

            # Override the system prompt loader to use the candidate's prompt.
            client._load_system_prompt = lambda agent: prof.prompt

            # Smoke prompts come from env as JSON.
            probes = json.loads(os.environ["QWEN_SMOKE_PROBES"])
            failed = []
            for i, (prompt, needles) in enumerate(probes):
                try:
                    r = client.call(agent="qwen_probe",
                                    user_turn=prompt,
                                    task_type="classify",
                                    remember=False if False else None)
                except TypeError:
                    # older local_llm_client signatures may not accept remember
                    r = client.call(agent="qwen_probe",
                                    user_turn=prompt,
                                    task_type="classify")
                except LocalLLMUnavailable as e:
                    print(f"BOOT_FAIL: probe {i}: runtime: {e}", file=sys.stderr)
                    sys.exit(6)
                text = (r.get("text") or "").lower()
                if not any(n.lower() in text for n in needles):
                    failed.append((i, text[:120]))
            if failed:
                print(f"BOOT_FAIL: {len(failed)}/{len(probes)} probes missed: "
                      f"{failed}", file=sys.stderr)
                sys.exit(7)
            print("BOOT_OK")
        """)

        import json as _json
        env = os.environ.copy()
        env["PAPER_AI_ROOT"] = str(self.paths.root)
        env["QWEN_CANDIDATE_DIR"] = str(self.paths.qwen_profile_candidate)
        env["QWEN_SMOKE_PROBES"] = _json.dumps(self.SMOKE_PROMPTS)
        # Qwen probe doesn't need an API key — Anthropic never touched.
        env.pop("ANTHROPIC_API_KEY", None)

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-c", driver],
                cwd=str(self.paths.root),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.BOOT_TEST_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ProfileBootResult(
                ok=False,
                reason=f"boot test timeout after {self.BOOT_TEST_TIMEOUT_S}s",
                elapsed_s=time.perf_counter() - t0,
            )
        except Exception as e:
            return ProfileBootResult(
                ok=False, reason=f"boot test launch failure: {e!r}",
                elapsed_s=time.perf_counter() - t0,
            )

        elapsed = time.perf_counter() - t0
        ok = proc.returncode == 0 and "BOOT_OK" in (proc.stdout or "")
        log.info("qwen_candidate_boot_test",
                 ok=ok, rc=proc.returncode, elapsed_s=round(elapsed, 2),
                 stderr_tail=(proc.stderr or "")[-400:])
        return ProfileBootResult(
            ok=ok,
            reason=("boot test passed" if ok
                    else f"subprocess rc={proc.returncode}"),
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            elapsed_s=elapsed,
        )

    # ---------------------------------------------------------------- promote

    def promote(self) -> None:
        """Atomic-ish promotion: main→backup, candidate→main.

        Two os.replace calls on the same filesystem. Between them the
        old main is gone and the new main isn't placed yet; any concurrent
        reader in that ~microsecond gap would see a missing directory.
        The LocalLLMClient's profile loader treats a missing directory as
        "use last-loaded in-process profile", so the worst case is a
        single call with stale config, not a crash.

        To minimise the window we stage the swap via a tempdir rename.
        """
        cand = self.paths.qwen_profile_candidate
        if not cand.is_dir():
            raise FileNotFoundError(f"no candidate to promote at {cand}")

        main = self.paths.qwen_profile_main
        backup = self.paths.qwen_profile_backup

        # Step 1: current backup → scratch (to free the backup slot)
        scratch = None
        if backup.exists():
            scratch = backup.with_name(f"backup.retire.{os.getpid()}.{time.time_ns()}")
            os.replace(backup, scratch)

        # Step 2: current main → backup
        if main.exists():
            os.replace(main, backup)

        # Step 3: candidate → main
        os.replace(cand, main)

        # Step 4: delete the retired backup
        if scratch and scratch.exists():
            try:
                shutil.rmtree(scratch)
            except OSError as e:
                log.warning("scratch_cleanup_failed", path=str(scratch), err=str(e))

        log.warning("qwen_profile_promoted",
                    main=str(main), backup=str(backup))

    def abort(self, reason: str) -> None:
        """Remove the candidate. Leave main and backup alone."""
        cand = self.paths.qwen_profile_candidate
        if cand.exists():
            try:
                shutil.rmtree(cand)
            except OSError as e:
                log.error("qwen_candidate_unlink_failed",
                          path=str(cand), err=str(e))
        log.warning("qwen_candidate_aborted", reason=reason)

    def restore_from_backup(self, *, reason: str) -> bool:
        """Copy backup → main, overwriting. Returns True on success.

        Does NOT delete the backup — restoring multiple times should be
        safe. The caller is responsible for deciding when it's OK to
        restore (usually: main is demonstrably broken).
        """
        if not self.has_backup():
            log.error("qwen_restore_no_backup", reason=reason)
            return False
        main = self.paths.qwen_profile_main
        backup = self.paths.qwen_profile_backup
        tmp = main.with_name(f"main.restoring.{os.getpid()}")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(backup, tmp)
        if main.exists():
            # Swap in the new copy and remove the old one.
            retired = main.with_name(f"main.retired.{time.time_ns()}")
            os.replace(main, retired)
            os.replace(tmp, main)
            try:
                shutil.rmtree(retired)
            except OSError:
                pass
        else:
            os.replace(tmp, main)
        log.warning("qwen_main_restored_from_backup", reason=reason)
        return True

    # ---------------------------------------------------------------- bootstrap

    def initialize_default(self, *, default_prompt: str,
                           default_config: dict[str, Any]) -> None:
        """First-run only: if main/ is empty, populate it from defaults.
        Also seeds backup/ with a copy so restore_from_backup() has something.
        """
        if self.has_backup() and self.paths.qwen_profile_main.is_dir() \
                and (self.paths.qwen_profile_main / "config.yaml").exists():
            return  # already initialized
        prof = QwenProfile(
            prompt=default_prompt,
            config=default_config,
            routing_overrides={},
            facts_snapshot="",
        )
        prof.to_files(self.paths.qwen_profile_main)
        prof.to_files(self.paths.qwen_profile_backup)
        log.info("qwen_profile_initialized")

    # ---------------------------------------------------------------- end-to-end

    def stage_test_and_promote(
        self, profile: QwenProfile,
    ) -> ProfileBootResult:
        """Convenience wrapper. Returns the boot result; on success the
        promotion has already happened."""
        self.stage(profile)
        boot = self.boot_test()
        if not boot.ok:
            self.abort(reason=f"boot_failed: {boot.reason}")
            return boot
        try:
            self.promote()
        except Exception as e:
            self.abort(reason=f"promote_failed: {e!r}")
            return ProfileBootResult(
                ok=False, reason=f"promote step raised: {e!r}",
                stdout=boot.stdout, stderr=boot.stderr,
                elapsed_s=boot.elapsed_s,
            )
        return boot
