"""encrypt_key.py — standalone helper for putting an API key into .env.

What this is for
----------------
You have a plaintext API key (e.g. `sk-ant-api03-xxxx...`) and a password.
You want the encrypted blob to paste into your `.env` file. This script
prints exactly that blob — nothing else — so you can copy it once and
move on.

What this is NOT for
--------------------
Editing `.env` for you. Look at `python -m secrets_tool encrypt KEY` for
the all-in-one workflow that updates `.env` in place.

Usage
-----
    python encrypt_key.py
        → prompts (hidden input) for password and plaintext key
        → prints `ENC:gAAAAA...`

    python encrypt_key.py --key-name ANTHROPIC_API_KEY
        → same, but also prints a copy-paste-ready `KEY=ENC:...` line

    python encrypt_key.py --decrypt
        → reverse: prompts for password and an `ENC:...` blob, prints
          the plaintext. Useful for verifying you stored the right
          thing without round-tripping through .env.

Verification
------------
After printing the encrypted blob, the script does an immediate
self-check: it decrypts what it just produced with the same password
and confirms it matches the input. If that ever fails, the script
exits with a non-zero status and does NOT print the (possibly
corrupt) blob. This catches Fernet/cryptography misinstallation
before you commit a useless string to `.env`.

Salt
----
The script reads `.env.salt` from the project root. If absent, it
creates one (16 bytes urandom). The same salt is used by every other
unlock/encrypt operation in the project — that's the whole point of
the file. NEVER copy a `.env.salt` from one machine to another unless
you also intend to share its vault.

Why a separate script (vs `secrets_tool encrypt`)?
--------------------------------------------------
Two reasons:
  1. Discoverability. `encrypt_key.py` at the project root is one
     `ls` away.
  2. Output discipline. `secrets_tool encrypt` writes to `.env` for
     you, which is convenient but makes the resulting blob harder
     to inspect or reuse. This script prints to stdout and stops.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


# ---------------------------------------------------------------------- imports
# We do the heavy import inside main() so a missing `cryptography` package
# yields a friendly message instead of an opaque ModuleNotFoundError at
# import time.

def _import_vault():
    try:
        from core.secrets_vault import (
            ENC_PREFIX, WrongPassword, decrypt, encrypt, ensure_salt,
        )
    except ModuleNotFoundError as e:
        if e.name == "cryptography":
            print(
                "[encrypt_key] the 'cryptography' package is required.\n"
                "  Install it with:  pip install cryptography",
                file=sys.stderr,
            )
        else:
            print(f"[encrypt_key] import error: {e}", file=sys.stderr)
        raise SystemExit(2)
    return ENC_PREFIX, WrongPassword, decrypt, encrypt, ensure_salt


# ---------------------------------------------------------------------- prompts

def _prompt_hidden(label: str, *, confirm: bool = False) -> str:
    """getpass with optional confirmation. Empty input is rejected."""
    while True:
        try:
            v = getpass.getpass(f"{label}: ")
        except (EOFError, KeyboardInterrupt):
            print("\n[encrypt_key] aborted", file=sys.stderr)
            raise SystemExit(130)
        if not v:
            print("[encrypt_key] empty input not accepted", file=sys.stderr)
            continue
        if not confirm:
            return v
        again = getpass.getpass(f"{label} (confirm): ")
        if v == again:
            return v
        print("[encrypt_key] inputs did not match — try again", file=sys.stderr)


# ---------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="encrypt_key.py",
        description=(
            "Encrypt one API key with a password and print the ENC: blob. "
            "Paste the result into .env."
        ),
    )
    p.add_argument(
        "--root", default=".",
        help="project root holding .env.salt (default: current directory)",
    )
    p.add_argument(
        "--key-name", default=None,
        help=("if given, also print a `NAME=ENC:...` line ready to paste "
              "(e.g. --key-name ANTHROPIC_API_KEY)"),
    )
    p.add_argument(
        "--decrypt", action="store_true",
        help="reverse mode: prompt for an ENC: blob and print the plaintext",
    )
    p.add_argument(
        "--no-confirm", action="store_true",
        help=("don't ask the password twice (default is to confirm in "
              "encrypt mode to catch typos)"),
    )
    args = p.parse_args(argv)

    ENC_PREFIX, WrongPassword, decrypt_fn, encrypt_fn, ensure_salt = _import_vault()

    root = Path(args.root).resolve()
    try:
        salt = ensure_salt(root)
    except OSError as e:
        print(f"[encrypt_key] cannot create .env.salt at {root}: {e}",
              file=sys.stderr)
        return 2

    if args.decrypt:
        return _do_decrypt(salt, ENC_PREFIX, WrongPassword, decrypt_fn)

    return _do_encrypt(salt, ENC_PREFIX, WrongPassword,
                       encrypt_fn, decrypt_fn,
                       key_name=args.key_name,
                       confirm=not args.no_confirm)


# ---------------------------------------------------------------------- modes

def _do_encrypt(
    salt, ENC_PREFIX, WrongPassword, encrypt_fn, decrypt_fn,
    *, key_name: str | None, confirm: bool,
) -> int:
    # Order matters here: prompt for the key first, password second. If
    # we asked for the password first and the user mistyped the key,
    # they'd have re-typed both. Asking for the key first means a
    # mistake in either input only forces re-entry of that one.
    plaintext = _prompt_hidden("API key (plaintext)")
    password = _prompt_hidden("Vault password", confirm=confirm)

    try:
        encrypted = encrypt_fn(plaintext, password, salt)
    except Exception as e:
        print(f"[encrypt_key] encryption failed: {e!r}", file=sys.stderr)
        del plaintext, password
        return 3

    # Self-check: round-trip immediately. If the result doesn't decrypt
    # back to the input, something is badly wrong (library mismatch,
    # corrupted salt, etc.) and we refuse to print a blob the user
    # might paste into .env.
    try:
        roundtrip = decrypt_fn(encrypted, password, salt)
    except WrongPassword:
        print("[encrypt_key] internal error: round-trip decryption failed "
              "with the same password. Refusing to print an unverified blob.",
              file=sys.stderr)
        del plaintext, password
        return 4
    if roundtrip != plaintext:
        print("[encrypt_key] internal error: round-trip plaintext mismatch. "
              "Refusing to print.", file=sys.stderr)
        del plaintext, password
        return 4
    del plaintext, password

    # Print to stdout. Two lines: the bare blob, and (optionally) the
    # full `KEY=ENC:...` form. Comments / banners go to stderr so a
    # caller piping stdout gets clean output.
    print("[encrypt_key] done. paste the line(s) below into .env",
          file=sys.stderr)
    if key_name:
        print(f"{key_name}={encrypted}")
    else:
        print(encrypted)
    return 0


def _do_decrypt(
    salt, ENC_PREFIX, WrongPassword, decrypt_fn,
) -> int:
    blob = _prompt_hidden("ENC: blob")
    if not blob.startswith(ENC_PREFIX):
        print(f"[encrypt_key] input does not start with {ENC_PREFIX!r}",
              file=sys.stderr)
        return 2
    password = _prompt_hidden("Vault password")
    try:
        pt = decrypt_fn(blob, password, salt)
    except WrongPassword:
        print("[encrypt_key] wrong password (or blob is corrupt)",
              file=sys.stderr)
        del password
        return 5
    del password
    # Plaintext to stdout, banner to stderr, same convention as encrypt.
    print("[encrypt_key] decrypted plaintext follows on next line",
          file=sys.stderr)
    print(pt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
