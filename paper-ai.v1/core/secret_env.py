"""SecretEnv — process-singleton holder for decrypted API keys.

Goals
-----
* Keys live in this module's globals, NOT in os.environ. Other
  processes on the same UID can read /proc/<pid>/environ; we do not
  want the API keys to be visible there.
* Single source of truth: every callsite that previously did
  `os.environ["ANTHROPIC_API_KEY"]` should now do
  `secret_env.get("ANTHROPIC_API_KEY")`.
* Fall through to os.environ for plaintext values that were never
  encrypted (so non-sensitive vars in `.env` still work normally).

The module exposes a small functional API rather than a class because
there is exactly one of these per process and "import + call" reads
better than "build + pass everywhere".

Lifecycle
---------
    unlock(root, password)   →   parses .env, decrypts ENC: values,
                                 stashes them, leaves plaintext in
                                 os.environ as before
    is_unlocked()            →   has unlock() succeeded this process?
    get(name)                →   secret first, then os.environ, then None
    require(name)            →   like get() but raises if missing
    lock()                   →   wipe the in-memory secrets (best effort)
    encrypted_names()        →   which keys came from ENC: values

`unlock()` does NOT call os.environ.update() for the decrypted values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from core.logger import get_logger
from core.secrets_vault import (
    WrongPassword, decrypt, ensure_salt, load_env_file,
)

log = get_logger("secret_env")


_secrets: dict[str, str] = {}
_encrypted_names: set[str] = set()
_unlocked: bool = False


# ============================================================================ public API

def is_unlocked() -> bool:
    return _unlocked


def encrypted_names() -> list[str]:
    return sorted(_encrypted_names)


def get(name: str, default: str | None = None) -> str | None:
    """Look up a value: encrypted-secret first, then os.environ.

    Returning the secret-store value first means an attacker who manages
    to set `ANTHROPIC_API_KEY=junk` in os.environ before we run can't
    override the real key.
    """
    if name in _secrets:
        return _secrets[name]
    return os.environ.get(name, default)


def require(name: str) -> str:
    v = get(name)
    if v is None or v == "":
        raise KeyError(
            f"required secret {name!r} not available; "
            "set it in .env (encrypted with `python -m secrets_tool encrypt`) "
            "or as a plain environment variable"
        )
    return v


def unlock(root: Path, password: str) -> int:
    """Decrypt every ENC: value in `.env`. Returns the count of secrets
    loaded. Raises WrongPassword on any decryption failure (which means
    the password is wrong — Fernet is authenticated, so a bad password
    cannot silently produce garbage).

    Plaintext lines in .env are loaded into os.environ here too so the
    rest of the codebase that uses os.environ for non-sensitive
    settings keeps working without a separate dotenv loader.

    Idempotent: calling unlock() twice with the same password is fine
    (overwrites the cache); with a different password raises immediately
    on the first ENC: line that fails.
    """
    global _unlocked
    salt = ensure_salt(root)
    lines = load_env_file(root)

    new_secrets: dict[str, str] = {}
    new_encrypted: set[str] = set()
    for line in lines:
        if line.key is None:
            continue
        if line.encrypted:
            try:
                pt = decrypt(line.value or "", password, salt)
            except WrongPassword:
                raise          # propagate; let caller decide retry policy
            new_secrets[line.key] = pt
            new_encrypted.add(line.key)
        else:
            # Plaintext .env values: copy to os.environ so libraries
            # that consult os.environ directly (requests proxies, etc.)
            # still see them. No security loss — they were plaintext
            # on disk already.
            if line.key not in os.environ:
                os.environ[line.key] = line.value or ""

    _secrets.clear()
    _secrets.update(new_secrets)
    _encrypted_names.clear()
    _encrypted_names.update(new_encrypted)
    _unlocked = True
    log.info("secret_env_unlocked", encrypted_count=len(new_secrets),
             encrypted_keys=sorted(new_secrets.keys()))
    return len(new_secrets)


def lock() -> None:
    """Best-effort wipe. Python doesn't guarantee memory clearing
    (strings are interned, GC is non-deterministic), but we drop our
    references so a heap walk has to work harder."""
    global _unlocked
    for k in list(_secrets.keys()):
        # Overwrite then delete. Doesn't actually scrub the original
        # buffer because Python strings are immutable, but it does
        # drop our reference.
        _secrets[k] = "X" * len(_secrets[k])
        del _secrets[k]
    _encrypted_names.clear()
    _unlocked = False
    log.info("secret_env_locked")


# ============================================================================ adapter — let libraries that demand os.environ work

def install_passthrough(names: Iterable[str]) -> None:
    """For libraries that hard-require an env var (rare, but Anthropic
    SDK reads ANTHROPIC_API_KEY automatically if you don't pass api_key
    explicitly), call this with the names you want exposed. The values
    will be set in os.environ.

    USE SPARINGLY. Each name added here negates the security benefit
    for that key — it becomes visible via /proc/<pid>/environ.
    """
    for name in names:
        if name in _secrets:
            os.environ[name] = _secrets[name]
            log.warning("secret_env_passthrough", name=name)
