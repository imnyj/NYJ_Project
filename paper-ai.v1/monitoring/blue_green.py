"""Blue-Green commander.py promotion infrastructure (watchdog side).

This module is called by the watchdog (and by `commander.py
--upgrade-check`) when a self-upgrade is pending. It does NOT
generate the new code — Commander does that itself, using its
upgrade tools (`tools/upgrade_tool.py`). This module's job is
mechanical:

  1. Swap candidate → live atomically.
  2. Keep one backup of the previous live for rollback.
  3. On consecutive boot failures, restore the backup automatically.

File layout
-----------
    PAPER_AI_ROOT/
        commander.py                    (live)
        staging/
            commander.py.candidate      (proposed new version)
            commander.py.backup         (previous live, kept after promotion)
            UPGRADE_READY               (marker — Commander wrote it, then exited)
            BOOT_FAILURES               (counter — incremented on each crash;
                                         reset to 0 on first successful boot)

Why not put backup in a totally separate dir?
---------------------------------------------
`os.replace` is atomic only within a single filesystem. Keeping
candidate, live, and backup in the same project tree guarantees
they're on the same FS. No half-promoted state, no race.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from core.logger import get_logger

log = get_logger("blue_green")


COMMANDER_FILENAME = "commander.py"
STAGING_DIRNAME = "staging"
CANDIDATE_NAME = "commander.py.candidate"
BACKUP_NAME = "commander.py.backup"
UPGRADE_READY_MARKER = "UPGRADE_READY"
BOOT_FAILURE_COUNTER = "BOOT_FAILURES"

# How many consecutive boot failures before we auto-rollback to the
# backup. Three is conservative — gives the user a chance to interrupt
# and inspect manually if the new code is intermittently broken.
MAX_BOOT_FAILURES = 3


# ============================================================================ paths

def _staging_dir(root: Path) -> Path:
    p = Path(root).resolve() / STAGING_DIRNAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def candidate_path(root: Path) -> Path:
    return _staging_dir(root) / CANDIDATE_NAME


def backup_path(root: Path) -> Path:
    return _staging_dir(root) / BACKUP_NAME


def marker_path(root: Path) -> Path:
    return _staging_dir(root) / UPGRADE_READY_MARKER


def failure_counter_path(root: Path) -> Path:
    return _staging_dir(root) / BOOT_FAILURE_COUNTER


def live_path(root: Path) -> Path:
    return Path(root).resolve() / COMMANDER_FILENAME


# ============================================================================ public API

def has_pending_upgrade(root: Path) -> bool:
    """True iff Commander wrote the marker AND a candidate exists."""
    return marker_path(root).is_file() and candidate_path(root).is_file()


def finalize_upgrade(root: Path) -> None:
    """Atomically swap candidate → live, keeping previous live as backup.

    Sequence:
        1. Read candidate; refuse if empty (Commander must have crashed
           between writing the marker and writing the file).
        2. Copy current live → backup (so rollback is one rename away).
        3. os.replace(candidate, live) — single atomic step.
        4. Remove the UPGRADE_READY marker.

    Steps 1+2 happen BEFORE the atomic step, so a crash anywhere in
    those leaves live untouched and the user can re-run finalize
    safely.
    """
    cand = candidate_path(root)
    live = live_path(root)
    backup = backup_path(root)

    if not cand.is_file():
        raise RuntimeError(f"no candidate file at {cand}")
    if cand.stat().st_size == 0:
        raise RuntimeError(
            f"candidate file is empty: {cand}. "
            "Commander likely crashed mid-write — refusing to promote."
        )

    # Step 1: backup current live (only if it exists; first install has no live)
    if live.is_file():
        try:
            shutil.copy2(live, backup)
            log.info("commander_backup_saved", backup=str(backup))
        except OSError as e:
            raise RuntimeError(
                f"could not back up live commander.py before swap: {e}"
            )

    # Step 2: atomic replace. After this returns, live IS the new code.
    try:
        os.replace(cand, live)
    except OSError as e:
        raise RuntimeError(f"atomic swap failed: {e}")

    # Step 3: clean up the marker.
    try:
        marker_path(root).unlink(missing_ok=True)
    except OSError:
        pass

    # Step 4: reset the boot-failure counter for the new version.
    try:
        failure_counter_path(root).unlink(missing_ok=True)
    except OSError:
        pass

    log.info("commander_promoted", live=str(live), backup=str(backup))


def record_boot_failure(root: Path) -> int:
    """Increment the boot-failure counter. Return new count."""
    fp = failure_counter_path(root)
    try:
        n = int(fp.read_text().strip()) if fp.is_file() else 0
    except (OSError, ValueError):
        n = 0
    n += 1
    try:
        fp.write_text(str(n))
    except OSError as e:
        log.warning("counter_write_failed", err=str(e))
    log.warning("commander_boot_failure", count=n, max=MAX_BOOT_FAILURES)
    return n


def reset_boot_failures(root: Path) -> None:
    """Called by Watchdog on first successful Commander boot."""
    fp = failure_counter_path(root)
    if fp.is_file():
        try:
            fp.unlink()
        except OSError:
            pass


def should_rollback(root: Path) -> bool:
    """True iff boot failure count has reached the rollback threshold
    AND a backup exists."""
    if not backup_path(root).is_file():
        return False
    fp = failure_counter_path(root)
    try:
        n = int(fp.read_text().strip()) if fp.is_file() else 0
    except (OSError, ValueError):
        return False
    return n >= MAX_BOOT_FAILURES


def rollback(root: Path) -> None:
    """Restore commander.py from the backup. Call this when
    `should_rollback()` returns True.

    The backup is moved to live (not copied), so subsequent boot
    failures don't trigger another rollback against the same backup.
    The user must produce a new working version manually before
    further upgrades.
    """
    bk = backup_path(root)
    live = live_path(root)
    if not bk.is_file():
        raise RuntimeError("no backup to roll back to")
    try:
        os.replace(bk, live)
    except OSError as e:
        raise RuntimeError(f"rollback failed: {e}")
    reset_boot_failures(root)
    log.warning("commander_rolled_back", live=str(live))
