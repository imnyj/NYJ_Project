"""CLI subcommand implementations + shared helpers.

Each `run_*` function here returns an int exit code that `cli.py` passes
straight to `sys.exit()`. Exit-code conventions match the Watchdog
protocol: 0 clean, 10 restart, 20 transient, 30 budget, 99 fatal.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.logger import get_logger
from core.paths import paths_for

log = get_logger("cli")


# ------------------------------------------------------------- input helpers

def sanitize(text: str) -> str:
    """Strip surrogate chars that break UTF-8 round-trip."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def resolve_input(
    raw: str, project_root: Path,
) -> tuple[str, Path | None]:
    """Detect whether `raw` is a path to a .md/.txt file or literal text.

    Returns (content, source_path_or_None). Tries UTF-8 first, then common
    Korean encodings, then a replacement-char fallback so we never crash
    on a stray byte.
    """
    raw = raw.strip().strip('"').strip("'")
    if len(raw) > 200 or " " in raw or not raw.endswith((".md", ".txt")):
        return sanitize(raw), None

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project_root / raw
    if not candidate.is_file():
        return sanitize(raw), None

    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "latin-1"):
        try:
            return sanitize(candidate.read_text(encoding=enc)), candidate
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    # last resort
    return sanitize(candidate.read_bytes().decode("utf-8", errors="replace")), candidate


def log_user_directive(
    root: Path, content: str, source: Path | None = None,
) -> None:
    """Append the directive to output/annotations/user_directives.md."""
    paths = paths_for(root)
    paths.annotations.mkdir(parents=True, exist_ok=True)
    path = paths.user_directives
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    src = f" (from file: {source.name})" if source else ""
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## [{stamp}]{src}\n{content}\n")
    log.info("user_directive_logged",
             chars=len(content),
             source=str(source) if source else None)
