# core/usage_persist.py
"""Persistent token-usage accumulator.

PolicyRuntime tracks usage per-process (paper + session). When the
Commander process exits, those counters are lost. This module bridges
the gap: every call recorded by PolicyRuntime is also flushed to a
JSON file under PAPER_AI_ROOT/output/usage.json, so cumulative
totals survive across runs.

Schema
------
    {
      "schema_version": 1,
      "started_at":     <epoch>,
      "updated_at":     <epoch>,
      "lifetime": {
        "input_tokens":       <int>,
        "output_tokens":      <int>,
        "cache_read_tokens":  <int>,
        "cache_write_tokens": <int>,
        "usd_spent":          <float>,
        "calls":              <int>,
        "by_model":           {"claude-opus-4-7": <calls>, ...},
        "by_agent": {
          "writer":    {"input_tokens": ..., "output_tokens": ...,
                        "cache_read_tokens": ..., "cache_write_tokens": ...,
                        "cost_usd": ..., "calls": ...},
          ...
        }
      }
    }

Concurrency
-----------
We use atomic write (tmp + rename) and a per-process lock around
read-modify-write. Two Commander processes writing simultaneously
remains undefined behaviour — but a single Commander + watchdog +
the ad-hoc `cli.py --usage` reader is safe.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("usage_persist")


SCHEMA_VERSION = 1
_LOCK = threading.Lock()


def _usage_file(root: Path) -> Path:
    """Return `<root>/output/usage.json`, creating the parent dir."""
    output = Path(root) / "output"
    output.mkdir(parents=True, exist_ok=True)
    return output / "usage.json"


def _empty_blob() -> dict[str, Any]:
    now = time.time()
    return {
        "schema_version": SCHEMA_VERSION,
        "started_at": now,
        "updated_at": now,
        "lifetime": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "usd_spent": 0.0,
            "calls": 0,
            "by_model": {},
            "by_agent": {},
        },
    }


def load(root: Path) -> dict[str, Any]:
    """Load the lifetime totals (or empty blob if absent / unreadable)."""
    p = _usage_file(root)
    if not p.is_file():
        return _empty_blob()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "lifetime" not in data:
            log.warning("usage_file_malformed", path=str(p))
            return _empty_blob()
        return data
    except Exception as e:
        log.warning("usage_file_unreadable", path=str(p), err=str(e))
        return _empty_blob()


def record(root: Path, *, model: str, usage: dict[str, int],
           cost_usd: float, agent: str | None) -> None:
    """Add one call to the persistent totals.

    Errors are caught and logged — a usage-write failure must not
    crash the agent loop.
    """
    try:
        with _LOCK:
            blob = load(root)
            life = blob["lifetime"]
            in_tok = int(usage.get("input_tokens", 0) or 0)
            out_tok = int(usage.get("output_tokens", 0) or 0)
            read_tok = int(usage.get("cache_read_input_tokens", 0) or 0)
            write_tok = int(usage.get("cache_creation_input_tokens", 0) or 0)

            life["input_tokens"]       += in_tok
            life["output_tokens"]      += out_tok
            life["cache_read_tokens"]  += read_tok
            life["cache_write_tokens"] += write_tok
            life["usd_spent"]          += float(cost_usd or 0.0)
            life["calls"]              += 1

            life["by_model"][model] = life["by_model"].get(model, 0) + 1

            if agent:
                slot = life["by_agent"].setdefault(agent, {
                    "input_tokens": 0, "output_tokens": 0,
                    "cache_read_tokens": 0, "cache_write_tokens": 0,
                    "cost_usd": 0.0, "calls": 0,
                })
                slot["input_tokens"]       += in_tok
                slot["output_tokens"]      += out_tok
                slot["cache_read_tokens"]  += read_tok
                slot["cache_write_tokens"] += write_tok
                slot["cost_usd"]           += float(cost_usd or 0.0)
                slot["calls"]              += 1

            blob["updated_at"] = time.time()
            _save(root, blob)
    except Exception as e:
        log.warning("usage_record_failed", err=str(e))


def _save(root: Path, blob: dict[str, Any]) -> None:
    """Atomic write via tmp + rename."""
    p = _usage_file(root)
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, p)
