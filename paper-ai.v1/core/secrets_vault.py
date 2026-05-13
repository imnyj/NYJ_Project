"""Symmetric secrets vault.

Used to encrypt/decrypt API keys stored in `.env`. Lines beginning with
`ENC:` are interpreted as base64-encoded Fernet tokens; everything else
is treated as plaintext (so `OLLAMA_BASE_URL=...` can sit next to
`ANTHROPIC_API_KEY=ENC:gAAAAAB...`).

Threat model
------------
Workstation is shared with other accounts. Adversary can read `.env`
and `.env.salt` from disk. They CANNOT read your terminal input or
the running process's heap. Goal: an adversary who reads `.env`
without your password gets nothing usable.

Crypto choices
--------------
* Fernet (AES-128-CBC + HMAC-SHA256, authenticated encryption — wrong
  password produces InvalidToken instead of garbage).
* PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2023 floor).
* Per-installation salt in `.env.salt` (16 bytes urandom). Salt is
  PUBLIC by design — it just defeats precomputed rainbow tables.
* Password is never written to disk and never put into os.environ.

Why not Argon2
--------------
Argon2 would be marginally stronger but adds a heavy native dependency.
PBKDF2 at 600k iterations is acceptable for a password used a few
times per day on a workstation.
"""

from __future__ import annotations

import base64
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

# Hard-fail import: this module is meaningless without `cryptography`.
# If you want a degraded mode, do that explicitly at the call site.
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ENC_PREFIX = "ENC:"
SALT_FILENAME = ".env.salt"
ENV_FILENAME = ".env"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16


# ============================================================================ exceptions

class VaultError(Exception):
    """Base class."""


class WrongPassword(VaultError):
    """Decryption failed — almost certainly the wrong password."""


class CorruptCiphertext(VaultError):
    """The ENC: payload isn't a valid Fernet token even with the
    right key — file probably edited by hand."""


class SaltMissing(VaultError):
    """`.env.salt` not present and no permission to create it."""


# ============================================================================ salt management

def salt_path(root: Path) -> Path:
    return root / SALT_FILENAME


def ensure_salt(root: Path) -> bytes:
    """Read `.env.salt`, creating it (16 bytes of urandom) if absent.

    File mode 0o600 — readable only by owner — applied immediately on
    creation. We don't fix permissions on an existing file because that
    might paper over a deliberate operator choice (e.g. a shared salt
    on a multi-user trusted machine).
    """
    p = salt_path(root)
    if p.is_file():
        data = p.read_bytes()
        if len(data) < 8:
            raise SaltMissing(f"{p} exists but is too short — delete to regenerate")
        return data
    data = secrets.token_bytes(SALT_BYTES)
    p.write_bytes(data)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass    # Windows or noperm; not fatal
    return data


# ============================================================================ key derivation

def derive_key(password: str, salt: bytes) -> bytes:
    """Return a Fernet key (urlsafe-base64 of 32 bytes) derived from
    password + salt via PBKDF2-HMAC-SHA256."""
    if not password:
        raise VaultError("empty password")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    raw = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


# ============================================================================ encrypt / decrypt

def encrypt(plaintext: str, password: str, salt: bytes) -> str:
    """Encrypt → ENC:<token> string suitable for direct insertion into
    .env. The ENC: prefix is OUR convention; Fernet tokens themselves
    start with `gAAAAA…`."""
    key = derive_key(password, salt)
    token = Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return ENC_PREFIX + token


def decrypt(env_value: str, password: str, salt: bytes) -> str:
    """Decrypt one ENC:-prefixed value. Strips the prefix automatically."""
    if not env_value.startswith(ENC_PREFIX):
        raise VaultError("value missing ENC: prefix")
    token = env_value[len(ENC_PREFIX):]
    key = derive_key(password, salt)
    try:
        return Fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        # Could be wrong password OR corrupted ciphertext. We can't tell
        # which from Fernet alone — treat as wrong password by default.
        # Caller can re-prompt and on second failure should give up.
        raise WrongPassword("decryption failed (wrong password or corrupt token)")


# ============================================================================ .env file ops

@dataclass
class EnvLine:
    """One parsed line of .env. Round-trippable: `to_text()` reproduces
    the original including blank lines, comments, and unusual quoting."""
    raw: str
    key: str | None = None     # None for blanks/comments
    value: str | None = None
    encrypted: bool = False

    def to_text(self) -> str:
        return self.raw


def parse_env(text: str) -> list[EnvLine]:
    """Light .env parser. Recognises:
        KEY=value         → plain
        KEY="value"       → strips outer quotes
        KEY=ENC:...       → encrypted
        # comment / blank → preserved as-is
    Does NOT handle multi-line values, command substitution, or any of
    the dotenv exotica. Sufficient for API keys.
    """
    out: list[EnvLine] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out.append(EnvLine(raw=line))
            continue
        if "=" not in line:
            out.append(EnvLine(raw=line))    # malformed; preserve verbatim
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip a single layer of matching quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        encrypted = value.startswith(ENC_PREFIX)
        out.append(EnvLine(raw=line, key=key, value=value, encrypted=encrypted))
    return out


def render_env(lines: list[EnvLine]) -> str:
    """Reverse of parse_env. Newline-terminated."""
    return "\n".join(l.to_text() for l in lines) + "\n"


def load_env_file(root: Path) -> list[EnvLine]:
    p = root / ENV_FILENAME
    if not p.is_file():
        return []
    return parse_env(p.read_text(encoding="utf-8"))


def save_env_file(root: Path, lines: list[EnvLine]) -> None:
    """Atomic write + 0o600 perms."""
    p = root / ENV_FILENAME
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(render_env(lines), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def update_value(
    lines: list[EnvLine], key: str, new_raw_value: str,
) -> list[EnvLine]:
    """Replace (or append) `KEY=new_raw_value` — caller controls whether
    it's plaintext or already an ENC: token. Mutates in place AND returns
    the list for chaining."""
    for line in lines:
        if line.key == key:
            line.raw = f"{key}={new_raw_value}"
            line.value = new_raw_value
            line.encrypted = new_raw_value.startswith(ENC_PREFIX)
            return lines
    lines.append(EnvLine(
        raw=f"{key}={new_raw_value}",
        key=key, value=new_raw_value,
        encrypted=new_raw_value.startswith(ENC_PREFIX),
    ))
    return lines


# ============================================================================ smoke check

def has_any_encrypted(lines: list[EnvLine]) -> bool:
    return any(l.encrypted for l in lines)


def encrypted_keys(lines: list[EnvLine]) -> list[str]:
    return [l.key for l in lines if l.encrypted and l.key]


def plaintext_keys(lines: list[EnvLine]) -> list[str]:
    return [l.key for l in lines if l.key and not l.encrypted]
