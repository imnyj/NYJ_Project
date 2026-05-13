"""Structured logging for paper-ai.

Emits JSON lines so later phases (monitoring.usage_tracker) can parse
token spend, cache hit rates, and per-agent performance without regex.

Usage:
    from core.logger import get_logger
    log = get_logger(__name__)
    log.info("agent_call", agent="writer", input_tokens=1234, cache_hit=True)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

_DEFAULT_LEVEL = os.environ.get("PAPER_AI_LOG_LEVEL", "INFO").upper()


def _log_file_path() -> Path:
    """Compute the log file path at configuration time, not import time.

    Reading `PAPER_AI_ROOT` lazily lets `cli.py` (which sets the env var
    after argparse) and pytest fixtures (which monkeypatch it per test)
    both land logs in the right place.
    """
    return (
        Path(os.environ.get("PAPER_AI_ROOT", ".")) / "output" / "paper-ai.log"
    )


class JsonFormatter(logging.Formatter):
    """Emit each record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Include any extra kwargs attached via log.info(..., extra={...})
        # or via our _KwargsAdapter below.
        for key, val in record.__dict__.items():
            if key in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                continue
            try:
                json.dumps(val)  # skip non-serializable
                payload[key] = val
            except (TypeError, ValueError):
                payload[key] = repr(val)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _KwargsAdapter(logging.LoggerAdapter):
    """Allow `log.info("msg", key=val, key2=val2)` shorthand.

    Python's LogRecord has reserved attribute names (name, msg, module, etc.)
    that cannot be overridden via `extra=`. We transparently prefix any
    colliding key with an underscore so user code can freely use natural
    names like `name=`, `module=`, etc.
    """

    # LogRecord attributes that CANNOT be overridden via `extra=`.
    _RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName", "asctime",
    })

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        passthrough_keys = {"exc_info", "stack_info", "stacklevel", "extra"}
        extras: dict[str, Any] = {}
        passthrough: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k in passthrough_keys:
                passthrough[k] = v
            elif k in self._RESERVED:
                extras[f"_{k}"] = v  # avoid LogRecord collision
            else:
                extras[k] = v
        if extras:
            passthrough.setdefault("extra", {}).update(extras)
        return msg, passthrough


def _configure_root() -> None:
    """Set up handlers once (idempotent)."""
    root = logging.getLogger("paper-ai")
    if root.handlers:
        return  # already configured
    root.setLevel(_DEFAULT_LEVEL)
    root.propagate = False

    # --- console (human-readable when TTY, json otherwise) ---
    console = logging.StreamHandler(sys.stderr)
    if sys.stderr.isatty():
        console.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    else:
        console.setFormatter(JsonFormatter())
    root.addHandler(console)

    # --- rotating JSON file log ---
    log_file = _log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)


def get_logger(name: str) -> _KwargsAdapter:
    """Get a namespaced logger with kwargs shorthand support."""
    _configure_root()
    base = logging.getLogger(f"paper-ai.{name}")
    return _KwargsAdapter(base, {})
