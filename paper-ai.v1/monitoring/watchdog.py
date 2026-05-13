"""Watchdog — Commander process supervisor.

Implements the exit-code protocol agreed in early design sessions:

    0   clean exit (task complete)        → stop, do not restart
    10  upgrade-requested, please restart  → restart immediately (new code)
    20  transient error, retry            → restart after cooldown
    30  budget exceeded                   → notify user, do not restart
    99  fatal / corrupted                 → restore from snapshot, restart
    *   unexpected (exception, signal)    → cooldown + restart with cap

Safety rails (user-approved defaults):
    - cooldown: 30 s between restarts
    - max 5 restarts within a 10 min rolling window → escalate and stop
    - absolute cap on total restarts to prevent log explosion

Usage:
    python -m monitoring.watchdog                       # default
    python -m monitoring.watchdog --commander-cmd "python cli.py --interactive"
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger

log = get_logger("watchdog")


# ------------------------------------------------------------------ codes

EXIT_CLEAN = 0
EXIT_UPGRADE = 10
EXIT_TRANSIENT = 20
EXIT_BUDGET = 30
EXIT_FATAL = 99


CODE_MEANINGS = {
    EXIT_CLEAN:     "clean exit (task complete)",
    EXIT_UPGRADE:   "upgrade-triggered restart",
    EXIT_TRANSIENT: "transient error, retry",
    EXIT_BUDGET:    "budget exceeded",
    EXIT_FATAL:     "fatal error (rollback expected)",
}


# ------------------------------------------------------------------ policy

@dataclass
class WatchdogPolicy:
    """Tunable safety rails."""
    cooldown_seconds: float = 30.0
    max_restarts_per_window: int = 5
    window_seconds: float = 600.0          # 10 minutes
    max_total_restarts: int = 100          # absolute ceiling
    upgrade_fast_restart: bool = True      # code 10 skips cooldown


@dataclass
class WatchdogState:
    total_restarts: int = 0
    recent_restarts: deque = field(default_factory=lambda: deque(maxlen=100))
    last_exit_code: int | None = None
    last_reason: str = ""

    def note_restart(self, reason: str, exit_code: int) -> None:
        now = time.time()
        self.total_restarts += 1
        self.recent_restarts.append(now)
        self.last_exit_code = exit_code
        self.last_reason = reason

    def restarts_in_window(self, window_seconds: float) -> int:
        cutoff = time.time() - window_seconds
        return sum(1 for t in self.recent_restarts if t >= cutoff)

    def to_dict(self) -> dict:
        return {
            "total_restarts": self.total_restarts,
            "last_exit_code": self.last_exit_code,
            "last_reason": self.last_reason,
            "recent_restarts": list(self.recent_restarts),
        }


# ---------------------------------------------------------------- watchdog

class Watchdog:
    """Single-commander supervisor."""

    def __init__(
        self,
        *,
        commander_cmd: list[str],
        project_root: Path | str = ".",
        policy: WatchdogPolicy | None = None,
        state_path: Path | str | None = None,
        vault_password: str | None = None,
    ):
        from core.paths import paths_for
        self.cmd = commander_cmd
        self.root = Path(project_root).resolve()
        self.paths = paths_for(self.root)
        self.policy = policy or WatchdogPolicy()
        self.state_path = Path(state_path) if state_path else self.paths.watchdog_state
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
        # Vault password (optional). If set, every child subprocess gets
        # it written to its stdin at spawn time, which that child's
        # bootstrap reads via core.unlock.unlock_from_stdin(). The
        # password lives in THIS process's memory for as long as the
        # watchdog runs — the caller is expected to have decided that's
        # an acceptable tradeoff against re-prompting per restart.
        self._vault_password: str | None = vault_password

    # ==================================================== state persist

    def _load_state(self) -> WatchdogState:
        if not self.state_path.exists():
            return WatchdogState()
        try:
            data = json.loads(self.state_path.read_text())
            s = WatchdogState(
                total_restarts=data.get("total_restarts", 0),
                last_exit_code=data.get("last_exit_code"),
                last_reason=data.get("last_reason", ""),
            )
            for t in data.get("recent_restarts", []):
                s.recent_restarts.append(t)
            return s
        except Exception as e:
            log.warning("state_load_failed", err=str(e))
            return WatchdogState()

    def _save_state(self) -> None:
        try:
            self.state_path.write_text(
                json.dumps(self.state.to_dict(), indent=2, default=str)
            )
        except OSError as e:
            log.warning("state_save_failed", err=str(e))

    # ========================================================= main loop

    def run(self) -> int:
        """Supervise commander until clean exit or policy stop."""
        log.info("watchdog_start",
                 cmd=self.cmd,
                 cooldown=self.policy.cooldown_seconds,
                 max_window=self.policy.max_restarts_per_window)

        while True:
            if self.state.total_restarts >= self.policy.max_total_restarts:
                log.error("watchdog_total_cap_hit",
                          total=self.state.total_restarts,
                          cap=self.policy.max_total_restarts)
                self._save_state()
                return 99

            recent = self.state.restarts_in_window(self.policy.window_seconds)
            if recent >= self.policy.max_restarts_per_window:
                log.error("watchdog_window_cap_hit",
                          recent=recent,
                          window_s=self.policy.window_seconds)
                print(
                    f"\n⚠️  Watchdog stopping: {recent} restarts in the last "
                    f"{self.policy.window_seconds:.0f}s "
                    f"(cap={self.policy.max_restarts_per_window}).",
                    file=sys.stderr,
                )
                print("   Manually inspect logs in output/paper-ai.log and "
                      "re-run `python -m monitoring.watchdog` when ready.",
                      file=sys.stderr)
                self._save_state()
                return 30

            # --- spawn child ---
            log.info("spawning_commander", attempt=self.state.total_restarts + 1)
            rc = self._spawn_and_wait()

            meaning = CODE_MEANINGS.get(rc, f"unexpected (rc={rc})")
            log.info("commander_exited", rc=rc, meaning=meaning)

            # --- branch on exit code ---
            if rc == EXIT_CLEAN:
                print(f"\n✅ Commander finished cleanly.")
                self._save_state()
                return 0

            if rc == EXIT_BUDGET:
                print(f"\n💰 Budget exceeded. Watchdog stopping; re-run "
                      f"after adjusting config/budgets.yaml.", file=sys.stderr)
                self._save_state()
                return EXIT_BUDGET

            if rc == EXIT_UPGRADE:
                # Commander's `finalize_upgrade` tool requested promotion.
                # The candidate file is staged; we must atomically swap
                # before re-spawning so the new commander.py is the one
                # that boots.
                self.state.note_restart("upgrade", rc)
                self._save_state()
                try:
                    from monitoring.blue_green import (
                        has_pending_upgrade, finalize_upgrade,
                    )
                    if has_pending_upgrade(Path(self.project_root)):
                        finalize_upgrade(Path(self.project_root))
                        print("\n🔄 Commander promoted; restarting on new code.",
                              file=sys.stderr)
                        log.info("promotion_finalized")
                    else:
                        # Commander returned 10 but no candidate exists.
                        # Treat as a transient restart so we don't loop.
                        log.warning("upgrade_exit_without_candidate")
                except Exception as e:
                    # Promotion itself failed (disk full, permissions).
                    # Don't restart endlessly — escalate.
                    print(f"\n⚠️  Promotion failed: {e}",
                          file=sys.stderr)
                    log.error("promotion_error", err=str(e))
                    return 99
                if not self.policy.upgrade_fast_restart:
                    self._cooldown()
                log.info("upgrade_triggered_restart")
                continue

            # ------------------ everything below is an UNCLEAN exit ------------------
            # If a recent promotion exists and Commander keeps crashing,
            # roll back automatically. This is the safety net for
            # promotions that pass `test_staged_upgrade` but still fail
            # in actual operation.
            try:
                from monitoring.blue_green import (
                    record_boot_failure, should_rollback, rollback,
                )
                fail_count = record_boot_failure(Path(self.project_root))
                if should_rollback(Path(self.project_root)):
                    print(
                        f"\n⚠️  Commander has crashed {fail_count} times in "
                        "a row. Rolling back to the previous version.",
                        file=sys.stderr,
                    )
                    log.warning("auto_rollback_triggered", fails=fail_count)
                    rollback(Path(self.project_root))
                    print("✅ Rollback complete. Restarting on previous version.",
                          file=sys.stderr)
            except Exception as e:
                # Don't let rollback bookkeeping prevent crash recovery.
                log.warning("rollback_check_failed", err=str(e))

            if rc == EXIT_FATAL:
                self.state.note_restart("fatal", rc)
                self._save_state()
                print("\n🔥 Fatal exit. Restoring from snapshot and "
                      "restarting after cooldown...", file=sys.stderr)
                self._try_rollback_hook()
                self._cooldown()
                continue

            # EXIT_TRANSIENT or anything else
            self.state.note_restart(f"rc={rc}", rc)
            self._save_state()
            self._cooldown()

    # --------------------------------------------------- subprocess exec

    def _spawn_and_wait(self) -> int:
        """Run commander and return its exit code. Propagates stdin/stdout.

        Vault-aware: when `vault_password` was set at construction time,
        the child is spawned with `stdin=PIPE`, the password is written
        as a single line, and stdin is closed. The child's bootstrap
        (see `core.unlock.unlock_from_stdin`) reads exactly that one
        line before doing anything else. We set an environment flag so
        the child knows to consult stdin instead of prompting via tty.

        We do NOT inherit our stdin to the child in vault mode — the
        child would otherwise see the watchdog's own tty and could
        interactively re-prompt, which defeats the point.
        """
        use_vault_pipe = self._vault_password is not None
        env = os.environ.copy()
        if use_vault_pipe:
            env["PAPER_AI_UNLOCK_FROM_STDIN"] = "1"
        try:
            if use_vault_pipe:
                proc = subprocess.Popen(
                    self.cmd,
                    cwd=str(self.root),
                    env=env,
                    stdin=subprocess.PIPE,
                )
                # Write + newline + close. A bare writelines() wouldn't
                # signal EOF, and the child's readline() would block
                # forever waiting for one.
                try:
                    assert proc.stdin is not None
                    proc.stdin.write((self._vault_password + "\n").encode("utf-8"))
                    proc.stdin.flush()
                except Exception as e:
                    log.error("vault_pipe_write_failed", err=str(e))
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    return EXIT_FATAL
                finally:
                    try:
                        if proc.stdin is not None:
                            proc.stdin.close()
                    except Exception:
                        pass
            else:
                proc = subprocess.Popen(
                    self.cmd,
                    cwd=str(self.root),
                    env=env,
                )
        except FileNotFoundError as e:
            log.error("commander_spawn_failed", err=str(e))
            return EXIT_FATAL

        try:
            return proc.wait()
        except KeyboardInterrupt:
            log.warning("watchdog_keyboard_interrupt")
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
            raise

    # ------------------------------------------------------ helpers

    def _cooldown(self) -> None:
        log.info("watchdog_cooldown", seconds=self.policy.cooldown_seconds)
        time.sleep(self.policy.cooldown_seconds)

    def _try_rollback_hook(self) -> None:
        """After a fatal exit, ask self_upgrader for a rollback.

        We avoid a hard dependency: if core.self_upgrader is unavailable
        we just log and continue.
        """
        try:
            from core.self_upgrader import SelfUpgrader  # noqa
            # The rollback is performed by Commander on next start;
            # we only signal via a sentinel file.
            flag = self.paths.rollback_flag
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text(str(time.time()))
            log.info("rollback_flag_written", path=str(flag))
        except Exception as e:
            log.warning("rollback_hook_failed", err=str(e))


# =============================================================== main

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "paper-ai watchdog: supervise commander.py with auto-restart "
            "policy. Prompts for the vault password ONCE and pipes it to "
            "every spawned commander child via stdin, so you don't re-type "
            "across crashes."
        ),
    )
    parser.add_argument(
        "--commander-cmd",
        default="python commander.py --interactive",
        help=(
            'Command line to launch commander. Default uses commander.py '
            'so the child accepts the watchdog stdin-pipe protocol via '
            'PAPER_AI_UNLOCK_FROM_STDIN. If you point this at cli.py '
            'directly the child will fail to unlock the vault when '
            'encrypted .env entries exist.'
        ),
    )
    # Convenience pass-throughs so users don't need to escape long
    # quoted commander-cmd strings for the common cases.
    parser.add_argument(
        "--autosave", default=None, metavar="NAME",
        help="Append --autosave NAME to the commander command line.",
    )
    parser.add_argument(
        "--resume", default=None, metavar="NAME",
        help="Append --resume NAME to the commander command line.",
    )
    parser.add_argument(
        "--as", dest="as_agent", default=None, metavar="ROLE",
        help="Append --as ROLE to the commander command line.",
    )
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--cooldown", type=float, default=30.0)
    parser.add_argument("--max-window", type=int, default=5)
    parser.add_argument("--window-seconds", type=float, default=600.0)
    parser.add_argument(
        "--no-vault", action="store_true",
        help=(
            "Skip the vault-password prompt. Use only when .env has no "
            "ENC: entries (i.e. all keys are plaintext)."
        ),
    )
    args = parser.parse_args()

    # Build the final commander command line, appending convenience flags.
    cmd = args.commander_cmd.split()
    if args.autosave:
        cmd += ["--autosave", args.autosave]
    if args.resume:
        cmd += ["--resume", args.resume]
    if args.as_agent:
        cmd += ["--as", args.as_agent]

    # Decide whether vault prompt is needed.
    #   - --no-vault forces skip.
    #   - Otherwise, peek at .env: any ENC: entry triggers the prompt.
    vault_password: str | None = None
    if not args.no_vault:
        vault_password = _maybe_prompt_for_vault_password(Path(args.root))

    policy = WatchdogPolicy(
        cooldown_seconds=args.cooldown,
        max_restarts_per_window=args.max_window,
        window_seconds=args.window_seconds,
    )
    dog = Watchdog(
        commander_cmd=cmd,
        project_root=args.root,
        policy=policy,
        vault_password=vault_password,
    )
    try:
        return dog.run()
    except KeyboardInterrupt:
        print("\nwatchdog: interrupted by user.")
        return 0
    finally:
        # Best-effort wipe of the local password reference. Python
        # doesn't guarantee the bytes are scrubbed (strings are
        # immutable), but we drop our handle so a heap walker has to
        # work harder.
        if vault_password:
            vault_password = "X" * len(vault_password)
            del vault_password


def _maybe_prompt_for_vault_password(root: Path) -> str | None:
    """Inspect `.env` and prompt for the vault password iff needed.

    Returns the password string or None.

    We do the prompt at the watchdog level — not the child — because
    the child gets respawned on crash and we don't want the user to
    re-type. The child reads stdin once, uses it, and never asks
    interactively (its commander.py honours PAPER_AI_UNLOCK_FROM_STDIN).
    """
    try:
        from core.secrets_vault import has_any_encrypted, load_env_file
    except ImportError:
        # cryptography not installed → no vault is in use
        return None
    try:
        lines = load_env_file(Path(root))
    except Exception:
        return None
    if not has_any_encrypted(lines):
        return None
    import getpass
    try:
        return getpass.getpass("Vault password: ")
    except (EOFError, KeyboardInterrupt):
        print("\nwatchdog: aborted at password prompt.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
