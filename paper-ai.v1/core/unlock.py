"""Password handling & unlock entry points.

Two main entry points:

    unlock_interactive(root)  → prompt user via getpass, retry once on
                                wrong password, then SystemExit(2).
    unlock_from_stdin(root)   → read a single line from stdin (used
                                when watchdog spawns this process and
                                pipes the password in). No retry —
                                bad password = exit immediately, the
                                user already typed it once at the
                                watchdog level.

Both call into core.secret_env.unlock(). The password string lives in
local scope only and is `del`'d on the way out. Python's GC may keep
the underlying bytes around, but we don't write or pass them anywhere
else.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

from core.logger import get_logger
from core.secret_env import is_unlocked, unlock
from core.secrets_vault import SaltMissing, VaultError, WrongPassword

log = get_logger("unlock")

MAX_INTERACTIVE_ATTEMPTS = 2     # per the design decision: two strikes


def unlock_interactive(root: Path, *, prompt: str = "Password: ") -> None:
    """Prompt user for a password and try to unlock.

    On success: returns silently, secret_env is now populated.
    On failure: prints to stderr and SystemExit(2).
    Already unlocked: returns silently without re-prompting (idempotent).
    """
    if is_unlocked():
        return

    last_err: str = ""
    for attempt in range(1, MAX_INTERACTIVE_ATTEMPTS + 1):
        try:
            pw = getpass.getpass(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n[unlock] aborted by user", file=sys.stderr)
            raise SystemExit(2)
        if not pw:
            print("[unlock] empty password not accepted", file=sys.stderr)
            last_err = "empty"
            continue
        try:
            count = unlock(root, pw)
        except WrongPassword:
            last_err = "wrong password"
            print(f"[unlock] {last_err} (attempt {attempt}/"
                  f"{MAX_INTERACTIVE_ATTEMPTS})", file=sys.stderr)
            del pw
            continue
        except SaltMissing as e:
            print(f"[unlock] salt file unavailable: {e}", file=sys.stderr)
            del pw
            raise SystemExit(2)
        except VaultError as e:
            print(f"[unlock] vault error: {e}", file=sys.stderr)
            del pw
            raise SystemExit(2)
        except Exception as e:
            # Be paranoid: any unexpected error exits cleanly so we
            # don't accidentally proceed in an unlocked state.
            print(f"[unlock] unexpected error: {e!r}", file=sys.stderr)
            del pw
            raise SystemExit(2)
        # Success.
        del pw
        if count == 0:
            log.warning("no_encrypted_keys_found")
        return

    print(f"[unlock] giving up after {MAX_INTERACTIVE_ATTEMPTS} attempts "
          f"(last: {last_err})", file=sys.stderr)
    raise SystemExit(2)


def unlock_from_stdin(root: Path) -> None:
    """Read one line from stdin and try to unlock, then re-attach stdin
    to the controlling terminal so any subsequent REPL works.

    Used by watchdog-spawned children. The flow is:

        1. Watchdog opens a Popen(stdin=PIPE) for the child.
        2. Watchdog writes the password + "\\n" + closes the pipe.
        3. Child reads exactly one line — that's the password.
        4. Child re-opens `/dev/tty` and replaces sys.stdin with it,
           so input() in the REPL still gets the user's typing.

    Step 4 is the subtle part. Without it, sys.stdin is at EOF after
    the password line, and input() returns immediately, ending the
    REPL on its first iteration.

    On systems without `/dev/tty` (Windows, SSH session without a
    controlling terminal), this falls back gracefully: stdin stays
    bound to the closed pipe and we warn the user. Interactive mode
    won't work in that environment without tty access; use the
    interactive prompt directly instead of via watchdog.
    """
    if is_unlocked():
        return
    try:
        pw = sys.stdin.readline().rstrip("\r\n")
    except Exception as e:
        print(f"[unlock] could not read password from stdin: {e}",
              file=sys.stderr)
        raise SystemExit(2)
    if not pw:
        print("[unlock] empty password from stdin", file=sys.stderr)
        raise SystemExit(2)
    try:
        unlock(root, pw)
    except WrongPassword:
        print("[unlock] wrong password from watchdog (this should not happen)",
              file=sys.stderr)
        del pw
        raise SystemExit(2)
    except (SaltMissing, VaultError) as e:
        print(f"[unlock] {e}", file=sys.stderr)
        del pw
        raise SystemExit(2)
    del pw

    # Re-attach stdin to /dev/tty so the REPL's input() works after
    # watchdog closed the pipe. This is safe because we've already
    # consumed the one and only thing watchdog wrote to the pipe.
    _reattach_stdin_to_tty()


def _reattach_stdin_to_tty() -> None:
    """Replace sys.stdin with /dev/tty so input() reads from the
    controlling terminal, not the closed watchdog pipe.

    No-op on platforms without /dev/tty. Errors are warnings, not
    fatal — a non-interactive child (e.g. --pipeline mode) doesn't
    need tty access at all.
    """
    try:
        # On POSIX, /dev/tty is the controlling terminal of the process,
        # regardless of how stdin was redirected. opening it for
        # reading and assigning to sys.stdin restores REPL input.
        tty_in = open("/dev/tty", "r")
    except OSError as e:
        # Windows, SSH-without-tty, or other environments where the
        # process has no controlling terminal. The child will see EOF
        # on its first input() and exit cleanly. Print a hint for the
        # user so they know what happened.
        print(f"[unlock] note: could not reattach stdin to tty ({e}). "
              "Interactive REPL won't work under this watchdog setup; "
              "run `python commander.py --interactive` directly instead.",
              file=sys.stderr)
        return
    sys.stdin = tty_in
