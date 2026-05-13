"""Operator CLI for managing encrypted .env entries."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from core.paths import get_paths
from core.secrets_vault import (
    ENC_PREFIX, EnvLine, WrongPassword,
    decrypt, encrypt, ensure_salt,
    encrypted_keys, has_any_encrypted,
    load_env_file, plaintext_keys, salt_path, save_env_file,
    update_value,
)


# ============================================================================ helpers

def _root() -> Path:
    return get_paths().root


def _prompt_password(*, confirm: bool = False, label: str = "Password") -> str:
    while True:
        pw = getpass.getpass(f"{label}: ")
        if not pw:
            print("[empty password not accepted]", file=sys.stderr)
            continue
        if not confirm:
            return pw
        again = getpass.getpass(f"{label} (confirm): ")
        if pw == again:
            return pw
        print("[passwords did not match — try again]", file=sys.stderr)


def _prompt_secret_value(label: str) -> str:
    """Use getpass for the *value* too — it's a secret. Operators can
    paste; nothing echoes."""
    val = getpass.getpass(f"{label}: ")
    if not val:
        raise SystemExit("[empty value not accepted]")
    return val


# ============================================================================ subcommands

def cmd_init(args: argparse.Namespace) -> int:
    root = _root()
    p = salt_path(root)
    if p.is_file():
        print(f"[init] salt already exists at {p} — leaving as-is")
        return 0
    salt = ensure_salt(root)
    print(f"[init] created {p} ({len(salt)} bytes)")
    print("[init] add this file to your .gitignore — it must NOT be shared.")
    return 0


def cmd_encrypt(args: argparse.Namespace) -> int:
    root = _root()
    salt = ensure_salt(root)
    if args.key is None:
        print("usage: encrypt KEY", file=sys.stderr)
        return 2
    pw = _prompt_password(confirm=False, label="Vault password")
    plaintext = (args.value if args.value is not None
                 else _prompt_secret_value(f"Plaintext value for {args.key}"))

    # Sanity check: if there are existing ENC: values in .env, the password
    # must be able to decrypt one of them. Otherwise the operator just
    # quietly used a different password and split the vault.
    lines = load_env_file(root)
    if has_any_encrypted(lines):
        sample = next(l for l in lines if l.encrypted)
        try:
            decrypt(sample.value, pw, salt)
        except WrongPassword:
            print(f"[encrypt] password does not match existing ENC: keys "
                  f"(e.g. {sample.key}). Refusing to add a key encrypted with "
                  "a different password.", file=sys.stderr)
            print("[encrypt] either use the existing password, or run "
                  "`change-password` first.", file=sys.stderr)
            del pw
            return 3

    enc_value = encrypt(plaintext, pw, salt)
    update_value(lines, args.key, enc_value)
    save_env_file(root, lines)
    del pw, plaintext
    print(f"[encrypt] {args.key} stored encrypted in .env")
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    """Print decrypted value to stdout. Useful for debugging or for
    piping into another tool. Be aware shells log history — prefer
    `verify` for "is this still the right key?" checks."""
    root = _root()
    salt = ensure_salt(root)
    lines = load_env_file(root)
    target = next((l for l in lines if l.key == args.key), None)
    if target is None:
        print(f"[decrypt] {args.key!r} not found in .env", file=sys.stderr)
        return 4
    if not target.encrypted:
        print(f"[decrypt] {args.key!r} is plaintext, not encrypted",
              file=sys.stderr)
        print(target.value)
        return 0
    pw = _prompt_password(label="Vault password")
    try:
        pt = decrypt(target.value, pw, salt)
    except WrongPassword:
        print("[decrypt] wrong password", file=sys.stderr)
        del pw
        return 5
    finally:
        pass
    del pw
    print(pt)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Try to decrypt every ENC: value with the supplied password. Don't
    print plaintext — just report which ones succeed."""
    root = _root()
    salt = ensure_salt(root)
    lines = load_env_file(root)
    enc = [l for l in lines if l.encrypted]
    if not enc:
        print("[verify] no encrypted entries in .env")
        return 0
    pw = _prompt_password(label="Vault password")
    ok, fail = [], []
    for l in enc:
        try:
            decrypt(l.value, pw, salt)
            ok.append(l.key)
        except WrongPassword:
            fail.append(l.key)
    del pw
    print(f"[verify] {len(ok)} ok, {len(fail)} failed")
    if ok:
        print("  ok:    " + ", ".join(ok))
    if fail:
        print("  fail:  " + ", ".join(fail))
        return 1
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = _root()
    lines = load_env_file(root)
    enc = encrypted_keys(lines)
    plain = plaintext_keys(lines)
    print("encrypted keys:")
    for k in enc:
        print(f"  {k}")
    print("plaintext keys:")
    for k in plain:
        print(f"  {k}")
    if not enc:
        print("(no ENC: entries — vault is not in use)")
    return 0


def cmd_change_password(args: argparse.Namespace) -> int:
    """Re-encrypt every ENC: value with a new password. Atomic: if any
    decryption fails, nothing is written."""
    root = _root()
    salt = ensure_salt(root)
    lines = load_env_file(root)
    enc = [l for l in lines if l.encrypted]
    if not enc:
        print("[change-password] no encrypted entries — nothing to do")
        return 0
    old_pw = _prompt_password(label="Current vault password")
    # Decrypt everything first; abort if any fail.
    plaintexts: dict[str, str] = {}
    for l in enc:
        try:
            plaintexts[l.key] = decrypt(l.value, old_pw, salt)
        except WrongPassword:
            print(f"[change-password] decrypt of {l.key!r} failed — "
                  "old password is wrong, aborting", file=sys.stderr)
            del old_pw
            return 5
    del old_pw
    new_pw = _prompt_password(confirm=True, label="New vault password")
    for l in enc:
        l.raw = f"{l.key}={encrypt(plaintexts[l.key], new_pw, salt)}"
        l.value = l.raw.split("=", 1)[1]
    del plaintexts, new_pw
    save_env_file(root, lines)
    print(f"[change-password] re-encrypted {len(enc)} entries")
    return 0


# ============================================================================ entry

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="secrets_tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="create .env.salt if missing")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("encrypt", help="add or update an encrypted .env entry")
    sp.add_argument("key", help="environment variable name (e.g. ANTHROPIC_API_KEY)")
    sp.add_argument("--value",
                    help="provide plaintext on the command line "
                         "(NOT recommended — shows in shell history)")
    sp.set_defaults(func=cmd_encrypt)

    sp = sub.add_parser("decrypt", help="print plaintext of one entry")
    sp.add_argument("key")
    sp.set_defaults(func=cmd_decrypt)

    sp = sub.add_parser("verify",
                        help="try password against all ENC: entries (no plaintext shown)")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("list", help="show which keys are encrypted vs plaintext")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("change-password",
                        help="re-encrypt every ENC: entry with a new password")
    sp.set_defaults(func=cmd_change_password)

    # Aliases
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
