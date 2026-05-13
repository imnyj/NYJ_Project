"""Self-upgrade engine.

Safe file mutation with these guarantees (per user's design requirement):

    1. USER APPROVAL IS THE ONLY ENTRY POINT
       - Every upgrade runs through core/upgrade_approval.py.
       - Default policy denies; interactive CLI explicitly asks.

    2. SNAPSHOT BEFORE TOUCH
       - All target files copied to
         `output/snapshots/<timestamp>_<request_id>/`
         BEFORE any write.

    3. ATOMIC REPLACEMENT
       - New contents written to `<path>.tmp.<pid>`, then os.replace().
       - Partial writes cannot leave corrupted source files.

    4. DRY-RUN COMPILE CHECK
       - For .py files, `python -m py_compile` must pass on the new
         content BEFORE we swap the live file.

    5. POST-SWAP SMOKE TEST
       - `python cli.py --verify-config` must pass.
       - If it fails, ROLLBACK from snapshot.

    6. AUDIT LOG
       - Every request + decision + outcome in output/upgrade_log/.

    7. RESTART SIGNAL
       - On success, the engine's `apply()` method returns True; the
         calling watchdog pattern can exit(10) to trigger re-exec with
         the new commander.py.

No self-upgrade may bypass this module.
"""

from __future__ import annotations

import difflib
import os
import py_compile
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.logger import get_logger
from core.upgrade_approval import (
    AutoDenyApprover,
    InteractiveCLIApprover,
    UpgradeAuditLog,
    UpgradeDecision,
    UpgradeRequest,
)

log = get_logger("self_upgrader")


# -------------------------------------------------------------- file change

@dataclass
class FileChange:
    """One file's proposed new content."""
    path: Path                       # absolute or project-relative
    new_content: str
    purpose: str = ""                # short description

    def rel(self, project_root: Path) -> str:
        try:
            return str(self.path.relative_to(project_root))
        except ValueError:
            return str(self.path)


# ====================================================================== engine

@dataclass
class UpgradeOutcome:
    approved: bool
    applied: bool
    reason: str
    request_id: str
    snapshot_dir: str | None = None
    rolled_back: bool = False
    rollback_clean: bool = True         # False if rollback had file-level failures
    errors: list[str] = field(default_factory=list)
    smoke_test_stdout: str = ""


class SelfUpgrader:
    """End-to-end safe upgrade pipeline."""

    def __init__(
        self,
        project_root: Path | str = ".",
        *,
        approver=None,
        audit_log: UpgradeAuditLog | None = None,
        smoke_test_cmd: list[str] | None = None,
    ):
        from core.paths import paths_for
        self.root = Path(project_root).resolve()
        self.paths = paths_for(self.root)
        self.approver = approver or (
            InteractiveCLIApprover() if _stdin_is_tty() else AutoDenyApprover()
        )
        self.audit = audit_log or UpgradeAuditLog(self.paths.upgrade_log)
        self.snapshot_root = self.paths.snapshots
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.smoke_cmd = smoke_test_cmd or [
            "python", str(self.root / "cli.py"),
            "--verify-config", "--root", str(self.root),
        ]

    # ========================================================= propose & apply

    def apply(
        self,
        changes: list[FileChange],
        *,
        reason: str,
        impact_scope: list[str] | None = None,
        explain_hook: Callable[[UpgradeRequest], str] | None = None,
    ) -> UpgradeOutcome:
        """Main entry point. Validate → ask user → snapshot → atomic write →
        compile check → smoke test → maybe rollback.

        `explain_hook` is only used by the InteractiveCLIApprover when the
        user presses 'r' (request reasoning).
        """
        req_id = uuid.uuid4().hex
        for ch in changes:
            ch.path = self._resolve_path(ch.path)

        # ---- pre-flight: path safety ----
        safety_errors = self._check_paths(changes)
        if safety_errors:
            return self._fail(req_id, reason,
                              f"unsafe paths: {safety_errors}")

        # ---- pre-flight: python syntax ----
        syntax_errors = self._prevalidate_python(changes)
        if syntax_errors:
            return self._fail(req_id, reason,
                              f"python syntax errors: {syntax_errors}")

        # ---- build approval request with unified diff ----
        diff_text = self._build_diff(changes)
        estimated = self._estimate_tokens(diff_text)
        request = UpgradeRequest(
            reason=reason,
            target_files=[ch.rel(self.root) for ch in changes],
            diff_preview=diff_text,
            estimated_tokens=estimated,
            impact_scope=impact_scope or [],
            request_id=req_id,
        )

        # ---- USER APPROVAL (the only entry gate) ----
        if isinstance(self.approver, InteractiveCLIApprover) and explain_hook:
            self.approver._explain_hook = explain_hook  # type: ignore[attr-defined]
        decision = self.approver.decide(request)
        self.audit.record(request, decision)

        if not decision.approved:
            log.info("upgrade_denied", req=req_id, reason=decision.reason)
            return UpgradeOutcome(
                approved=False, applied=False, reason=decision.reason,
                request_id=req_id,
            )

        # ---- SNAPSHOT ----
        snap_dir = self._snapshot(changes, req_id)

        # ---- SPLIT: commander.py goes through Blue-Green promotion ----
        # commander.py is special because the usual smoke test
        # (`cli.py --verify-config`) doesn't actually instantiate
        # CommanderAgent, so a runtime bug in __init__ would only surface
        # AFTER watchdog re-execs — which is too late to roll back. We
        # stage it in `commander.py.candidate`, boot-test it in a fresh
        # subprocess, and only os.replace() on success. See
        # `core/commander_blue_green.py` for the full rationale.
        commander_change = None
        other_changes: list[FileChange] = []
        for ch in changes:
            try:
                rel = ch.path.resolve().relative_to(self.root)
                is_commander = str(rel) == "commander.py"
            except ValueError:
                is_commander = False
            if is_commander:
                commander_change = ch
            else:
                other_changes.append(ch)

        # ---- ATOMIC WRITE for non-commander files ----
        try:
            for ch in other_changes:
                self._atomic_write(ch)
        except Exception as e:
            log.error("atomic_write_failed", err=str(e))
            rb = self._rollback(snap_dir)
            return UpgradeOutcome(
                approved=True, applied=False, rolled_back=True,
                rollback_clean=rb["fully_clean"],
                request_id=req_id,
                reason=f"atomic write failed: {e!r}",
                snapshot_dir=str(snap_dir),
                errors=[str(e)] + rb["failures"],
            )

        # ---- POST-SWAP SMOKE TEST ----
        ok, smoke_out, smoke_err = self._smoke_test()
        if not ok:
            log.warning("smoke_test_failed_rolling_back",
                        stderr=smoke_err[:400])
            rb = self._rollback(snap_dir)
            return UpgradeOutcome(
                approved=True, applied=False, rolled_back=True,
                rollback_clean=rb["fully_clean"],
                request_id=req_id,
                reason="smoke test failed; rolled back",
                snapshot_dir=str(snap_dir),
                errors=[smoke_err[:1000]] + rb["failures"],
                smoke_test_stdout=smoke_out[:1000],
            )

        # ---- COMMANDER BLUE-GREEN PROMOTION (if commander.py changed) ----
        # At this point, all non-commander files are live and passed the
        # smoke test. Now stage the new commander.py into a candidate,
        # boot-test it in a subprocess, and only then atomically replace
        # the live commander. If the candidate fails to boot we roll back
        # every other file from the snapshot so the system returns to its
        # pre-upgrade state as a whole — we don't want a mixed universe
        # where core/* is on the new version but commander.py is still old.
        if commander_change is not None:
            from core.commander_blue_green import CommanderPromoter
            promoter = CommanderPromoter(self.root)
            promo = promoter.stage_test_and_promote(commander_change.new_content)
            if not promo.promoted:
                log.warning("commander_promotion_failed_rolling_back",
                            reason=promo.reason,
                            stderr_tail=promo.stderr[-300:])
                rb = self._rollback(snap_dir)
                return UpgradeOutcome(
                    approved=True, applied=False, rolled_back=True,
                    rollback_clean=rb["fully_clean"],
                    request_id=req_id,
                    reason=(
                        f"commander boot-test failed: {promo.reason}; "
                        "all other files rolled back"
                    ),
                    snapshot_dir=str(snap_dir),
                    errors=[promo.stderr[:1000]] + rb["failures"],
                    smoke_test_stdout=smoke_out[:1000],
                )
            log.info("commander_promoted_via_bluegreen", req=req_id)

        log.info("upgrade_applied", req=req_id, files=len(changes))
        return UpgradeOutcome(
            approved=True, applied=True, rolled_back=False,
            request_id=req_id,
            reason="success",
            snapshot_dir=str(snap_dir),
            smoke_test_stdout=smoke_out[:1000],
        )

    # ======================================================== helpers

    def _resolve_path(self, p: Path) -> Path:
        if not p.is_absolute():
            return (self.root / p).resolve()
        return p.resolve()

    def _check_paths(self, changes: list[FileChange]) -> list[str]:
        """Forbid targets outside project root or in output/ directory."""
        errors: list[str] = []
        protected = {self.root / "output"}   # output is runtime data, not code
        for ch in changes:
            try:
                ch.path.relative_to(self.root)
            except ValueError:
                errors.append(f"outside project root: {ch.path}")
                continue
            for p in protected:
                try:
                    ch.path.relative_to(p)
                    errors.append(f"protected dir: {ch.path}")
                    break
                except ValueError:
                    pass
        return errors

    def _prevalidate_python(self, changes: list[FileChange]) -> list[str]:
        """py_compile every .py change BEFORE touching disk.

        The validation writes the candidate source into a short-lived
        dot-prefixed file alongside the real path so relative imports in
        the code still resolve. To avoid leaving bytecode turds behind in
        ``__pycache__``, we point ``py_compile.compile(..., cfile=...)`` at
        an explicit path we control and delete both artifacts in ``finally``.
        """
        import tempfile
        errors: list[str] = []
        for ch in changes:
            if ch.path.suffix != ".py":
                continue
            tmp = ch.path.with_name(f".{ch.path.stem}.dryrun.py")
            # Route bytecode to a throwaway path so __pycache__ stays clean.
            cfile = Path(tempfile.gettempdir()) / f".{ch.path.stem}.{os.getpid()}.pyc"
            try:
                tmp.write_text(ch.new_content, encoding="utf-8")
                py_compile.compile(str(tmp), cfile=str(cfile), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{ch.rel(self.root)}: {e}")
            except Exception as e:
                errors.append(f"{ch.rel(self.root)}: {e!r}")
            finally:
                for p in (tmp, cfile):
                    try:
                        p.unlink()
                    except OSError:
                        pass
        return errors

    def _build_diff(self, changes: list[FileChange]) -> str:
        chunks: list[str] = []
        for ch in changes:
            old = ""
            if ch.path.is_file():
                try:
                    old = ch.path.read_text(encoding="utf-8")
                except Exception as e:
                    old = f"<read-failed: {e!r}>"
            d = difflib.unified_diff(
                old.splitlines(keepends=True),
                ch.new_content.splitlines(keepends=True),
                fromfile=f"a/{ch.rel(self.root)}",
                tofile=f"b/{ch.rel(self.root)}",
                n=3,
            )
            chunks.append("".join(d))
        return "\n".join(chunks)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return int(len(text) / 3.5)

    def _snapshot(self, changes: list[FileChange], req_id: str) -> Path:
        stamp = time.strftime("%Y-%m-%dT%H%M%S")
        dir_ = self.snapshot_root / f"{stamp}_{req_id[:8]}"
        dir_.mkdir(parents=True, exist_ok=True)
        # Track "net-new" files separately — they must be DELETED on rollback,
        # not restored, since there's no pre-existing version to restore to.
        new_files: list[str] = []
        for ch in changes:
            rel = ch.rel(self.root)
            if not ch.path.is_file():
                new_files.append(rel)
                continue
            dst = dir_ / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ch.path, dst)
        # Persist the list of net-new files alongside the snapshot so
        # rollback knows what to delete.
        if new_files:
            (dir_ / ".new_files.txt").write_text(
                "\n".join(new_files), encoding="utf-8"
            )
        log.info("snapshot_created", dir=str(dir_),
                 n_files=sum(1 for c in changes if c.path.is_file()),
                 n_new_files=len(new_files))
        return dir_

    def _atomic_write(self, ch: FileChange) -> None:
        """Write `ch.new_content` atomically via temp + rename.

        The tmp filename embeds pid but not thread id, so concurrent calls
        from multiple threads on the same target path would race. SelfUpgrader
        is called from the main thread only (interactive approval + single
        subprocess smoke test), so this is safe in current usage.
        """
        ch.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = ch.path.with_suffix(ch.path.suffix + f".tmp.{os.getpid()}")
        tmp.write_text(ch.new_content, encoding="utf-8")
        os.replace(tmp, ch.path)

    def _rollback(self, snapshot_dir: Path) -> dict[str, Any]:
        """Restore every file in snapshot_dir back to its project path.

        Additionally DELETE any files listed in .new_files.txt — those are
        files that did not exist pre-upgrade, so the correct rollback is
        to remove them rather than restore a non-existent original.

        Returns a status dict with counts and a list of any paths that
        failed to be restored/deleted; callers must check these so they
        don't mis-report a partial rollback as fully successful.
        """
        count = 0
        failures: list[str] = []
        new_files_manifest = snapshot_dir / ".new_files.txt"
        for src in snapshot_dir.rglob("*"):
            if not src.is_file():
                continue
            if src == new_files_manifest:
                continue
            rel = src.relative_to(snapshot_dir)
            dst = self.root / rel
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                count += 1
            except Exception as e:
                log.error("rollback_file_failed", path=str(dst), err=str(e))
                failures.append(f"restore {dst}: {e!r}")
        # Delete net-new files
        deleted = 0
        if new_files_manifest.is_file():
            for line in new_files_manifest.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                target = self.root / line
                try:
                    if target.is_file():
                        target.unlink()
                        deleted += 1
                except Exception as e:
                    log.error("rollback_delete_failed",
                              path=str(target), err=str(e))
                    failures.append(f"delete {target}: {e!r}")
        log.warning("rollback_complete", files_restored=count,
                    files_deleted=deleted,
                    failures=len(failures),
                    snapshot=str(snapshot_dir))
        return {
            "restored": count,
            "deleted": deleted,
            "failures": failures,
            "fully_clean": not failures,
        }

    def _smoke_test(self) -> tuple[bool, str, str]:
        """Run the configured smoke command; return (ok, stdout, stderr)."""
        try:
            proc = subprocess.run(
                self.smoke_cmd,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            ok = proc.returncode == 0
            log.info("smoke_test_result", ok=ok, rc=proc.returncode)
            return ok, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return False, "", "smoke test timeout"
        except Exception as e:
            return False, "", f"smoke test exception: {e!r}"

    def _fail(self, req_id: str, reason: str, message: str) -> UpgradeOutcome:
        log.error("upgrade_rejected_preflight",
                  req=req_id, reason=reason, message=message)
        return UpgradeOutcome(
            approved=False, applied=False,
            request_id=req_id, reason=message, errors=[message],
        )


# ------------------------------------------------------------- utility

def _stdin_is_tty() -> bool:
    import sys
    return sys.stdin.isatty()
