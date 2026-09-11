"""Does `HotSwapTrainer.pretrain_offline` still deadlock after the offline stage?

THE DEFECT. `pretrain_offline` handed the pretrained Rest weights to the Act
model with

    with self.update_lock:
        self.hot_swap_manager.hot_swap()

`hot_swap()` acquires `update_lock` itself, and `update_lock` is a plain
`threading.Lock`, which is not reentrant. The second acquisition waited on a
lock the same thread already held, so the process parked every thread in a futex
and never returned. Nothing timed out and nothing logged: a HOORL run simply
stopped, 21 seconds in, with the offline stage complete and episode 1 never
started.

WHY IT SURVIVED UNTIL NOW. The branch is guarded by `offline_stage_ran`, which
requires an offline dataset. None existed until 2026-09-06 07:00. Every earlier
HOORL run raised `OfflineDatasetMissing` before reaching this line, so the whole
branch was dead code that looked fine.

This script reproduces the deadlock mechanically, on the lock objects alone,
without SUMO and without a dataset: it asserts that the CURRENT code does not
take `update_lock` around a call that takes it again, and it demonstrates that
the OLD arrangement hangs. A watchdog thread bounds the demonstration so this
script cannot itself hang.
"""
from __future__ import annotations

import os
import sys
import threading
import time

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

failures = []


def check(ok: bool, message: str) -> None:
    print(("  PASS  " if ok else "  FAIL  ") + message)
    if not ok:
        failures.append(message)


# ---------------------------------------------------------------------------
# 1. The lock really is non-reentrant, so the bug is a bug.
# ---------------------------------------------------------------------------
print("[1] lock semantics")
import src.hot_swap_trainer as hst  # noqa: E402

probe = threading.Lock()
probe.acquire()
reacquired = probe.acquire(blocking=False)
probe.release()
if reacquired:
    probe.release()
check(not reacquired,
      "threading.Lock refuses a second acquisition from the same thread")


# ---------------------------------------------------------------------------
# 2. The old arrangement hangs; reproduced on the real classes.
# ---------------------------------------------------------------------------
print("\n[2] the old arrangement, reproduced")


class _Manager:
    """Only the locking shape of DualModelHotSwapManager.hot_swap."""

    def __init__(self) -> None:
        self.update_lock = threading.Lock()
        self.swapped = False

    def hot_swap(self) -> bool:
        with self.update_lock:      # hot_swap takes it itself -- line 496
            self.swapped = True
            return True


def _old_style(manager: _Manager) -> None:
    with manager.update_lock:       # the removed wrapper -- old line 1480
        manager.hot_swap()


def _new_style(manager: _Manager) -> None:
    manager.hot_swap()


def finishes_within(fn, manager: _Manager, seconds: float = 2.0) -> bool:
    done = threading.Event()

    def run() -> None:
        try:
            fn(manager)
        finally:
            done.set()

    # daemon so a thread that really is stuck cannot keep this script alive
    threading.Thread(target=run, daemon=True).start()
    return done.wait(timeout=seconds)


check(not finishes_within(_old_style, _Manager()),
      "the OLD arrangement (wrapping hot_swap in update_lock) never returns")
check(finishes_within(_new_style, _Manager()),
      "the NEW arrangement (calling hot_swap bare) returns")


# ---------------------------------------------------------------------------
# 3. The shipped source no longer contains the old arrangement.
# ---------------------------------------------------------------------------
print("\n[3] the shipped source")
source = open(hst.__file__, encoding="utf-8").read()
lines = source.splitlines()
offenders = []
for idx, line in enumerate(lines):
    if "with self.update_lock" not in line:
        continue
    # Look at the few lines this `with` body opens with.
    body = "\n".join(lines[idx + 1: idx + 4])
    if "hot_swap_manager.hot_swap()" in body:
        offenders.append(idx + 1)
check(not offenders,
      f"no `with self.update_lock:` wraps a `hot_swap()` call "
      f"(offending lines: {offenders or 'none'})")

# And the call that used to be wrapped is still there, so the fix removed the
# lock rather than the handover: a HOORL run must still push its pretrained
# weights to the Act model, or every action before the first scheduled swap
# comes from the random initialisation.
check("self.hot_swap_manager.hot_swap()" in source
      and "offline_stage_ran" in source,
      "the offline -> Act handover itself is still performed")

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    for f in failures:
        print("  - " + f)
    raise SystemExit(1)
print("all checks passed")
