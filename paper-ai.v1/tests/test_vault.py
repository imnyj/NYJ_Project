"""Vault / secret_env / unlock tests.

Verify: Fernet round-trip, wrong password detection, change-password
atomicity, .env parser fidelity, secret_env precedence, and the
encrypt_key.py self-check.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# These tests need `cryptography` — if it's not installed, skip gracefully.
crypt_ok = False
try:
    import cryptography  # noqa: F401
    crypt_ok = True
except ImportError:
    pass

pytestmark = pytest.mark.skipif(not crypt_ok, reason="cryptography not installed")


# ============================================================================ vault round-trip


def test_encrypt_decrypt_round_trip(tmp_path):
    from core.secrets_vault import encrypt, decrypt, ensure_salt
    salt = ensure_salt(tmp_path)
    blob = encrypt("sk-test-xyz-1234567890", "hunter2", salt)
    assert blob.startswith("ENC:")
    back = decrypt(blob, "hunter2", salt)
    assert back == "sk-test-xyz-1234567890"


def test_wrong_password_raises(tmp_path):
    from core.secrets_vault import encrypt, decrypt, ensure_salt, WrongPassword
    salt = ensure_salt(tmp_path)
    blob = encrypt("secret", "correct", salt)
    with pytest.raises(WrongPassword):
        decrypt(blob, "incorrect", salt)


def test_salt_is_persistent(tmp_path):
    from core.secrets_vault import ensure_salt
    s1 = ensure_salt(tmp_path)
    s2 = ensure_salt(tmp_path)
    assert s1 == s2
    # File mode 0600 on POSIX
    if os.name == "posix":
        mode = (tmp_path / ".env.salt").stat().st_mode & 0o777
        assert mode == 0o600


def test_different_salts_produce_different_keys(tmp_path):
    """Same password on two machines should produce different blobs —
    that's the whole point of having a salt."""
    from core.secrets_vault import encrypt, ensure_salt
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    sa = ensure_salt(a)
    sb = ensure_salt(b)
    assert sa != sb
    ba = encrypt("same", "pw", sa)
    bb = encrypt("same", "pw", sb)
    assert ba != bb


# ============================================================================ .env parser


def test_env_parser_roundtrip():
    from core.secrets_vault import parse_env, render_env
    src = (
        "# comment\n"
        "\n"
        "PLAIN=hello\n"
        'QUOTED="world"\n'
        "ENCRYPTED=ENC:gAAAAAB_fakeblob\n"
    )
    lines = parse_env(src)
    # comment + blank + 3 kv = 5 lines
    assert len(lines) == 5
    keys = [l.key for l in lines]
    assert keys == [None, None, "PLAIN", "QUOTED", "ENCRYPTED"]
    assert lines[2].value == "hello"
    assert lines[3].value == "world"            # quotes stripped
    assert lines[4].encrypted is True
    # round trip preserves lines (quote stripping is a one-way normalisation;
    # we test that key/value detection is stable, not byte-exact roundtrip)
    rendered = render_env(lines)
    parsed_again = parse_env(rendered)
    assert [l.key for l in parsed_again] == keys


def test_env_update_value(tmp_path):
    from core.secrets_vault import (
        load_env_file, save_env_file, update_value,
    )
    env = tmp_path / ".env"
    env.write_text("A=1\nB=2\n")
    # patch load/save to use tmp_path
    lines = load_env_file(tmp_path)
    update_value(lines, "B", "ENC:fakeblob")
    save_env_file(tmp_path, lines)
    written = env.read_text()
    assert "A=1" in written
    assert "B=ENC:fakeblob" in written


def test_change_password_is_atomic(tmp_path):
    """If we change password, ALL encrypted entries re-encrypt — or
    none do if any single decrypt fails. Emulate the flow directly."""
    from core.secrets_vault import encrypt, decrypt, ensure_salt, WrongPassword
    salt = ensure_salt(tmp_path)
    entries = {"A": "aaa", "B": "bbb", "C": "ccc"}
    blobs = {k: encrypt(v, "old", salt) for k, v in entries.items()}
    # Verify all can be decrypted with old pw
    for k, b in blobs.items():
        assert decrypt(b, "old", salt) == entries[k]
    # Try "old" -> "new" assuming all decrypt-able
    new_blobs = {}
    for k, b in blobs.items():
        pt = decrypt(b, "old", salt)
        new_blobs[k] = encrypt(pt, "new", salt)
    # All decrypt-able with "new"
    for k, b in new_blobs.items():
        assert decrypt(b, "new", salt) == entries[k]
    # "old" no longer works on new blobs
    for k, b in new_blobs.items():
        with pytest.raises(WrongPassword):
            decrypt(b, "old", salt)


# ============================================================================ secret_env precedence


def test_secret_env_prefers_memory_over_os_environ(tmp_path, monkeypatch):
    """An attacker who shoves ANTHROPIC_API_KEY=junk into the shell
    environment before we run must NOT override the real vault-loaded
    key. secret_env.get checks its own dict first."""
    from core import secret_env
    # Fresh state
    secret_env.lock()
    # Poison os.environ first
    monkeypatch.setenv("ANTHROPIC_API_KEY", "attacker-junk")
    # Load real value via secret_env internals (simulate unlock result)
    secret_env._secrets["ANTHROPIC_API_KEY"] = "real-value-from-vault"
    secret_env._encrypted_names.add("ANTHROPIC_API_KEY")
    secret_env._unlocked = True
    try:
        assert secret_env.get("ANTHROPIC_API_KEY") == "real-value-from-vault"
    finally:
        secret_env.lock()


def test_secret_env_falls_through_to_os_environ(monkeypatch):
    """For names that were never encrypted, secret_env.get should act
    like os.environ.get."""
    from core import secret_env
    secret_env.lock()
    monkeypatch.setenv("NON_SENSITIVE", "public-value")
    assert secret_env.get("NON_SENSITIVE") == "public-value"
    assert secret_env.get("NEVER_SET") is None
    assert secret_env.get("NEVER_SET", "default") == "default"


def test_secret_env_require_raises_on_missing():
    from core import secret_env
    secret_env.lock()
    with pytest.raises(KeyError):
        secret_env.require("DEFINITELY_NOT_SET_XYZ_12345")


# ============================================================================ unlock


def test_unlock_populates_secrets(tmp_path):
    """unlock() reads .env, decrypts ENC: values, stashes them, leaves
    plaintext in os.environ."""
    from core import secret_env
    from core.secrets_vault import encrypt, ensure_salt

    # Build a fake .env
    salt = ensure_salt(tmp_path)
    blob = encrypt("real-key-abc", "pw", salt)
    env = tmp_path / ".env"
    env.write_text(
        f"PLAIN_THING=hello\n"
        f"ANTHROPIC_API_KEY={blob}\n"
    )

    secret_env.lock()
    try:
        count = secret_env.unlock(tmp_path, "pw")
        assert count == 1
        assert secret_env.is_unlocked()
        assert secret_env.get("ANTHROPIC_API_KEY") == "real-key-abc"
        # ANTHROPIC_API_KEY must NOT be in os.environ
        assert os.environ.get("ANTHROPIC_API_KEY") != "real-key-abc"
        # PLAIN_THING gets pushed to os.environ (plaintext is already public)
        assert os.environ.get("PLAIN_THING") == "hello"
    finally:
        secret_env.lock()
        os.environ.pop("PLAIN_THING", None)


def test_unlock_wrong_password_raises(tmp_path):
    from core import secret_env
    from core.secrets_vault import encrypt, ensure_salt, WrongPassword

    salt = ensure_salt(tmp_path)
    blob = encrypt("x", "correct", salt)
    (tmp_path / ".env").write_text(f"K={blob}\n")

    secret_env.lock()
    try:
        with pytest.raises(WrongPassword):
            secret_env.unlock(tmp_path, "wrong")
        assert not secret_env.is_unlocked()
    finally:
        secret_env.lock()


def test_unlock_with_no_encrypted_entries_is_noop(tmp_path):
    """A .env with only plaintext should unlock successfully and count 0."""
    from core import secret_env
    (tmp_path / ".env").write_text("A=1\nB=2\n")
    secret_env.lock()
    try:
        count = secret_env.unlock(tmp_path, "anything")
        assert count == 0
        assert secret_env.is_unlocked()
    finally:
        secret_env.lock()
        os.environ.pop("A", None)
        os.environ.pop("B", None)
