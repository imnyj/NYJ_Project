"""Qwen facts store.

A single markdown file at `memory/qwen_facts.md` that both the
paper-ai pipeline and the qwen_companion REPL read. The *companion*
writes to it when a conversation surfaces a durable fact; the
*pipeline* reads from it to bias agent prompts.

Chosen format — markdown, not JSON/YAML — because:

    1. Facts are shown verbatim to Qwen as part of its system prompt;
       markdown reads naturally in both directions.
    2. Hand-editable. The user can `cat` or `edit` the file without
       schema knowledge.
    3. Diff-friendly for audit (what changed after a self-tune run).

File layout
-----------
    <!-- paper-ai/qwen_facts v1 -->

    ## domain
    - user is a transportation engineering PhD student
    - preferred journals: IEEE T-ITS, Transportation Research Part C

    ## tooling
    - uses libsumo for simulations
    - 3090 Ti (24GB VRAM)

    ## interaction style
    - concise replies preferred
    - mixes Korean and English

Each "fact" is one bulleted line under a topic header. Duplicates are
detected by case-insensitive text match after whitespace collapse.

Concurrency
-----------
Companion and pipeline can both be running; the pipeline only reads.
Writes happen from a single process (companion self-tune or explicit
`:remember` command). We use atomic write-and-replace on save.

Privacy
-------
Per the current product decision, Qwen's own extraction output is
trusted and stored verbatim — no Opus PII filter. The file is created
with mode 0o600 (owner read/write only) and listed in .gitignore as
a minimal safety net. If you later want to add filtering, the
`normalize_fact()` function is the single hook to plug it in.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from core.logger import get_logger
from core.paths import get_paths

log = get_logger("qwen_facts")

HEADER_TAG = "<!-- paper-ai/qwen_facts v1 -->"
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")


@dataclass
class FactEntry:
    topic: str          # e.g. "domain", "tooling"
    text: str           # one fact as a single line


# ============================================================================ read

def _read_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("facts_read_failed", path=str(path), err=str(e))
        return ""


def parse(body: str) -> list[FactEntry]:
    """Parse the markdown body into a flat list of FactEntry."""
    out: list[FactEntry] = []
    topic = "misc"
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line or line.startswith(HEADER_TAG):
            continue
        m_sec = SECTION_RE.match(line)
        if m_sec:
            topic = m_sec.group(1).strip() or "misc"
            continue
        m_bul = BULLET_RE.match(line)
        if m_bul:
            out.append(FactEntry(topic=topic, text=m_bul.group(1).strip()))
    return out


def load() -> list[FactEntry]:
    """Read and parse the live qwen_facts.md file."""
    return parse(_read_file(get_paths().qwen_facts))


# ============================================================================ render

def render_for_prompt(entries: list[FactEntry], *, max_chars: int = 4000) -> str:
    """Render the fact list into a compact block suitable for inclusion in
    a system prompt. Groups by topic, truncates gracefully."""
    if not entries:
        return ""
    by_topic: dict[str, list[str]] = {}
    for e in entries:
        by_topic.setdefault(e.topic, []).append(e.text)
    lines = ["## User facts (from prior conversations)"]
    for topic, facts in by_topic.items():
        lines.append(f"### {topic}")
        for f in facts:
            lines.append(f"- {f}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n… [truncated]"
    return text


# ============================================================================ write

def normalize_fact(text: str) -> str:
    """One-liner, whitespace-collapsed, trailing period dropped.

    This is the hook where a future PII filter would plug in. Returning
    an empty string signals the caller to drop the fact.
    """
    t = re.sub(r"\s+", " ", text).strip()
    if t.endswith("."):
        t = t[:-1]
    return t


def _dedupe_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def add(topic: str, text: str) -> bool:
    """Append a fact if it's not already present (by dedupe key).

    Returns True if the fact was actually added.
    """
    text = normalize_fact(text)
    if not text:
        return False
    topic = (topic or "misc").strip() or "misc"
    entries = load()
    key = _dedupe_key(text)
    if any(_dedupe_key(e.text) == key and e.topic == topic for e in entries):
        return False
    entries.append(FactEntry(topic=topic, text=text))
    _write(entries)
    log.info("fact_added", topic=topic, preview=text[:80])
    return True


def remove(text: str) -> bool:
    """Remove a fact matching the dedupe key. Returns True if removed."""
    text = normalize_fact(text)
    if not text:
        return False
    key = _dedupe_key(text)
    entries = load()
    before = len(entries)
    entries = [e for e in entries if _dedupe_key(e.text) != key]
    if len(entries) == before:
        return False
    _write(entries)
    log.info("fact_removed", preview=text[:80])
    return True


def clear() -> None:
    _write([])
    log.warning("fact_store_cleared")


def _write(entries: list[FactEntry]) -> None:
    """Atomic write with 0o600 perms."""
    path = get_paths().qwen_facts
    path.parent.mkdir(parents=True, exist_ok=True)

    # Group by topic, preserving insertion order within each topic.
    by_topic: dict[str, list[str]] = {}
    for e in entries:
        by_topic.setdefault(e.topic, []).append(e.text)

    parts = [HEADER_TAG, ""]
    for topic, facts in by_topic.items():
        parts.append(f"## {topic}")
        for f in facts:
            parts.append(f"- {f}")
        parts.append("")
    body = "\n".join(parts).rstrip() + "\n"

    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{int(time.time()*1000)}")
    tmp.write_text(body, encoding="utf-8")
    # Set restrictive perms on the tmp file before rename so the rename
    # is the atomic visibility event.
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass        # Windows or similar; don't block write
    os.replace(tmp, path)
    # In case the file existed before with loose perms, re-apply.
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
