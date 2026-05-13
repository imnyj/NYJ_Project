# core/paper_registry.py
"""Paper directory registry.

Manages the mapping between a user-provided session name (e.g.
'paper3' or 'aoi_simple') and a working directory under
~/papers/<name>/. The session name IS the directory name —
there is no auto-numbering.

What this module does
---------------------
1. resolve_or_create(name) — return absolute path to ~/papers/<name>/,
   creating the directory if it doesn't exist. First creation also
   registers the paper in index.json and refreshes list.md.

2. update_last_accessed(name) — bump the last_accessed timestamp.
   Called every time a session is opened.

3. list_papers() — iterate registered papers, used by list.md
   regeneration.

What this module does NOT do
-----------------------------
* Migrate existing workspace/ — that's a one-time user task
  (mv workspace papers/<name>).
* Decide PAPER_BASE_DIR — that's commander.py's job. This module
  just provides the path on demand.
* Validate paper content — agents handle that via .pipeline/.

File layout
-----------
    PAPERS_ROOT/                                  ← default ~/papers/
    ├── index.json                                ← code-readable
    ├── list.md                                   ← human-readable
    ├── paper3/                                   ← <name>
    │   ├── .pipeline/
    │   ├── paper/
    │   └── ...
    └── aoi_simple/
        └── ...

PAPERS_ROOT is configurable via the PAPERS_ROOT env var. Defaults
to ~/papers/, deliberately outside PAPER_AI_ROOT so code upgrades
(Blue-Green) never touch paper artefacts.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("paper_registry")


# ============================================================================ paths

# Directory naming policy. Letters, digits, underscore, hyphen; must
# start with letter/digit; max 64 chars. Rejects shell-special chars
# and path separators that would let a session name break out.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def papers_root() -> Path:
    """Resolved at call time so tests can override PAPERS_ROOT."""
    raw = os.getenv("PAPERS_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    # Default: ~/papers/, sibling to (not under) the code base.
    return (Path.home() / "papers").resolve()


def index_path() -> Path:
    return papers_root() / "index.json"


def list_md_path() -> Path:
    return papers_root() / "list.md"


def paper_dir(name: str) -> Path:
    """Return the directory for a given paper name, no validation."""
    return papers_root() / name


# ============================================================================ name validation


def is_valid_name(name: str) -> bool:
    """Permissive enough for "paper3", "aoi_simple", "5g-handover-q2",
    strict enough to reject "../../etc/passwd" or names with spaces."""
    return bool(_NAME_RE.match(name))


def validate_name(name: str) -> None:
    """Raise ValueError if name fails validation."""
    if not is_valid_name(name):
        raise ValueError(
            f"Invalid paper name {name!r}. Allowed: letters, digits, "
            "dot, hyphen, underscore; must start with letter or digit; "
            "max 64 chars. Examples: 'paper3', 'aoi_simple', '5g-handover'."
        )


# ============================================================================ index.json


def _empty_index() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "papers": {},   # name -> {created_at, last_accessed, note}
    }


def _load_index() -> dict[str, Any]:
    """Load index.json, returning an empty blob if missing/malformed.

    We never raise on read errors — the registry should degrade
    gracefully so a corrupted index doesn't block paper-ai use.
    """
    p = index_path()
    if not p.is_file():
        return _empty_index()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "papers" not in data:
            log.warning("index_malformed_replacing", path=str(p))
            return _empty_index()
        return data
    except Exception as e:
        log.warning("index_unreadable", path=str(p), err=str(e))
        return _empty_index()


def _save_index(blob: dict[str, Any]) -> None:
    """Atomic write via tmp + rename."""
    papers_root().mkdir(parents=True, exist_ok=True)
    p = index_path()
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, p)


# ============================================================================ list.md


# Marker pair that delimits the auto-generated section. Anything
# OUTSIDE these markers is preserved across regenerations — the user
# can add notes, headings, etc. above or below and they survive.
_LIST_HEAD = "<!-- BEGIN auto-generated paper table — do not edit between markers -->"
_LIST_TAIL = "<!-- END auto-generated paper table -->"


def _format_list_md(blob: dict[str, Any]) -> str:
    """Render a markdown table of all papers from the index."""
    papers = blob.get("papers", {})
    if not papers:
        return (
            f"{_LIST_HEAD}\n"
            "_(아직 등록된 논문이 없습니다.)_\n"
            f"{_LIST_TAIL}\n"
        )

    rows = []
    rows.append("| 이름 | 생성일 | 최근 접근 | 메모 |")
    rows.append("|---|---|---|---|")
    # Sort by last_accessed descending so the active one floats to top.
    items = sorted(
        papers.items(),
        key=lambda kv: kv[1].get("last_accessed", 0),
        reverse=True,
    )
    for name, meta in items:
        created = _fmt_time(meta.get("created_at"))
        accessed = _fmt_time(meta.get("last_accessed"))
        note = (meta.get("note") or "").replace("|", "\\|").replace("\n", " ")
        rows.append(f"| `{name}` | {created} | {accessed} | {note} |")

    return f"{_LIST_HEAD}\n" + "\n".join(rows) + f"\n{_LIST_TAIL}\n"


def _refresh_list_md(blob: dict[str, Any]) -> None:
    """Regenerate list.md, preserving any user content outside the markers."""
    papers_root().mkdir(parents=True, exist_ok=True)
    p = list_md_path()

    new_section = _format_list_md(blob)

    if not p.is_file():
        # First time — write a header + the auto section.
        p.write_text(
            "# Paper Registry\n\n"
            "이 파일은 paper-ai에 등록된 논문 목록입니다.\n"
            "표 부분은 자동 생성·갱신되며, 표 밖의 메모는 유지됩니다.\n\n"
            f"{new_section}\n",
            encoding="utf-8",
        )
        return

    existing = p.read_text(encoding="utf-8")
    # If markers are present, replace the section. Otherwise append.
    if _LIST_HEAD in existing and _LIST_TAIL in existing:
        before = existing.split(_LIST_HEAD, 1)[0].rstrip()
        after = existing.split(_LIST_TAIL, 1)[1].lstrip()
        rebuilt = (
            (before + "\n\n" if before else "")
            + new_section
            + ("\n\n" + after if after else "\n")
        )
        p.write_text(rebuilt, encoding="utf-8")
    else:
        # User edited the file but lost the markers. Append rather than
        # blow away their content.
        p.write_text(
            existing.rstrip() + "\n\n" + new_section + "\n",
            encoding="utf-8",
        )


def _fmt_time(epoch: float | int | None) -> str:
    if not epoch:
        return "—"
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(epoch)))
    except (TypeError, ValueError):
        return "—"


# ============================================================================ public API


@dataclass
class PaperEntry:
    name: str
    path: Path
    created_at: float
    last_accessed: float
    note: str
    is_new: bool   # True if just created in this call


def resolve_or_create(name: str) -> PaperEntry:
    """Return the directory for `name`, creating it if needed.

    Raises ValueError if `name` fails validation. Otherwise always
    returns a valid PaperEntry — never raises on missing index or
    filesystem hiccups (degrades to defaults).

    Side effects on first creation:
      * mkdir papers/<name>/
      * Add entry to index.json
      * Regenerate list.md

    Side effects on existing entry:
      * Bump last_accessed
      * Save index.json + regenerate list.md
      * If directory was deleted out-of-band, recreate it (empty dir)
        so the caller still gets a usable path.
    """
    validate_name(name)

    blob = _load_index()
    papers = blob.setdefault("papers", {})

    target = paper_dir(name)
    now = time.time()

    is_new_entry = name not in papers
    is_new_dir = not target.is_dir()

    if is_new_entry:
        papers[name] = {
            "created_at": now,
            "last_accessed": now,
            "note": "",
        }
        log.info("paper_registered", name=name, path=str(target))
    else:
        papers[name]["last_accessed"] = now
        if is_new_dir:
            # Index has the entry but directory is gone — auto-recreate
            # silently. Per Q4 = (a).
            log.warning("paper_dir_recreated", name=name, path=str(target))

    target.mkdir(parents=True, exist_ok=True)
    _save_index(blob)
    _refresh_list_md(blob)

    meta = papers[name]
    return PaperEntry(
        name=name,
        path=target,
        created_at=float(meta.get("created_at", now)),
        last_accessed=now,
        note=str(meta.get("note", "")),
        is_new=is_new_entry,
    )


def list_papers() -> list[PaperEntry]:
    """Return all registered papers, most-recent-access first."""
    blob = _load_index()
    papers = blob.get("papers", {})
    items = sorted(
        papers.items(),
        key=lambda kv: kv[1].get("last_accessed", 0),
        reverse=True,
    )
    return [
        PaperEntry(
            name=name,
            path=paper_dir(name),
            created_at=float(meta.get("created_at", 0)),
            last_accessed=float(meta.get("last_accessed", 0)),
            note=str(meta.get("note", "")),
            is_new=False,
        )
        for name, meta in items
    ]


def update_note(name: str, note: str) -> None:
    """Programmatic note update. The user can also edit list.md notes
    column directly (within markers) but those are overwritten on the
    next regenerate; permanent notes belong here."""
    validate_name(name)
    blob = _load_index()
    papers = blob.setdefault("papers", {})
    if name not in papers:
        raise KeyError(f"Paper {name!r} not registered")
    papers[name]["note"] = note[:500]
    _save_index(blob)
    _refresh_list_md(blob)
