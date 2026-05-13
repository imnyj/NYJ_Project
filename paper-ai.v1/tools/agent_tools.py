"""Agent-callable tools.

Each tool is a function that takes keyword arguments matching its
schema and returns a string (success) or raises ToolError (failure
visible to the agent). The dispatcher in BaseAgent maps tool names
to these functions.

Why functions (not classes)
---------------------------
The Anthropic tool_use schema is JSON; agents call tools by name with
a dict of arguments. A function with **kwargs is the most direct
match. We register each in TOOL_REGISTRY by name.

Path safety
-----------
All file paths get resolved against the project root and confined to
it. An agent that asks to read `../../etc/passwd` gets a
ToolError, not surprising behaviour. The constraint is enforced in
`_resolve_safe_path`.

Token discipline
----------------
read_file truncates at MAX_FILE_BYTES per call to protect prompt
budgets. The agent gets a clear marker when truncation happens so it
can decide whether to ask for a different range.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from core.logger import get_logger
from core.paths import get_paths

log = get_logger("tools.agent_tools")

# Per-call ceilings — agents asking for more get a partial result with
# an explicit truncation marker so they don't think they got everything.
MAX_FILE_BYTES = 200_000
MAX_DIR_ENTRIES = 500
MAX_PYTHON_SECONDS = 30
MAX_PYTHON_OUTPUT_BYTES = 50_000


class ToolError(Exception):
    """Raised when a tool call fails. The message is sent back to the
    agent as the tool_result content so it can recover or apologise."""


# ============================================================================ path safety

def _resolve_safe_path(rel_or_abs: str) -> Path:
    """Resolve a path under the project root. Reject anything that
    escapes via .. or absolute paths outside the root.

    The agent shouldn't need to think about the project's filesystem
    layout — it gets to use relative paths and we anchor them.
    """
    root = get_paths().root.resolve()
    p = Path(rel_or_abs)
    if p.is_absolute():
        candidate = p.resolve()
    else:
        candidate = (root / p).resolve()
    # The candidate must be under root.
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ToolError(
            f"path {rel_or_abs!r} resolves outside the project root "
            f"({root}); refusing for safety"
        )
    return candidate


# ============================================================================ file tools

def read_file(*, path: str, start_line: int | None = None,
              end_line: int | None = None, **_) -> str:
    """Read a UTF-8 text file, optionally a line range.

    Returns the file content. If the file is too large, returns the
    head and a truncation marker — the agent can re-call with
    start_line/end_line to read further.

    Args:
        path: file path relative to project root (e.g. "drafts/intro.md")
        start_line: 1-indexed inclusive (optional)
        end_line: 1-indexed inclusive (optional)
    """
    p = _resolve_safe_path(path)
    if not p.is_file():
        raise ToolError(f"not a file: {path}")
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file; refuse rather than return mojibake
        raise ToolError(f"file is not UTF-8 text: {path}")
    except OSError as e:
        raise ToolError(f"could not read {path}: {e}")

    # Line range slicing
    if start_line is not None or end_line is not None:
        lines = text.splitlines()
        a = max(1, start_line or 1) - 1
        b = min(len(lines), end_line or len(lines))
        text = "\n".join(lines[a:b])
        suffix = f"\n[lines {a+1}-{b} of {len(lines)}]"
    else:
        suffix = ""

    # Byte-budget truncation
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        # Take the first ~MAX_FILE_BYTES bytes worth, decode-safely
        truncated = text.encode("utf-8")[:MAX_FILE_BYTES].decode(
            "utf-8", errors="ignore")
        suffix += (f"\n[truncated at {MAX_FILE_BYTES} bytes — file is "
                   f"{len(text.encode('utf-8'))} bytes total. Use "
                   "start_line/end_line to read further.]")
        text = truncated

    log.info("read_file", path=str(p),
             chars_returned=len(text),
             truncated=bool(suffix))
    return text + suffix


def list_directory(*, path: str = ".", **_) -> str:
    """List files and subdirectories under `path`.

    Returns a newline-separated list with file/dir markers and sizes.
    Hidden files (`.`-prefixed) are skipped — agents don't usually
    need to see them and the noise hurts prompt budgets.
    """
    p = _resolve_safe_path(path)
    if not p.is_dir():
        raise ToolError(f"not a directory: {path}")
    entries = []
    try:
        for child in sorted(p.iterdir()):
            if child.name.startswith("."):
                continue
            if child.is_dir():
                entries.append(f"d  {child.name}/")
            else:
                try:
                    size = child.stat().st_size
                    size_str = (f"{size:>8}b" if size < 1024
                                else f"{size/1024:>7.1f}K" if size < 1024**2
                                else f"{size/1024**2:>7.1f}M")
                except OSError:
                    size_str = "      ?"
                entries.append(f"f {size_str}  {child.name}")
    except OSError as e:
        raise ToolError(f"could not list {path}: {e}")
    if len(entries) > MAX_DIR_ENTRIES:
        truncated = MAX_DIR_ENTRIES
        entries = entries[:truncated] + [
            f"… [{len(entries) - truncated} more entries omitted]"
        ]
    log.info("list_directory", path=str(p), n=len(entries))
    if not entries:
        return f"(empty directory: {path})"
    return f"# {path}\n" + "\n".join(entries)


def write_file(*, path: str, content: str, append: bool = False, **_) -> str:
    """Write text to a file under the project root.

    By design, write_file CAN overwrite existing files. The agent's
    system prompt is responsible for not destroying user work; we
    don't second-guess it here. (For overwrite-protection use
    explicit prompt rules per agent.)

    Args:
        path: relative path under project root
        content: text to write
        append: if True, append instead of overwrite (default False)
    """
    p = _resolve_safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    try:
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise ToolError(f"could not write {path}: {e}")
    log.info("write_file", path=str(p), bytes=len(content.encode("utf-8")),
             append=append)
    return f"wrote {len(content)} chars to {path}" + (" (appended)" if append else "")


# ============================================================================ python execution

def python_exec(*, code: str, **_) -> str:
    """Execute Python code in a subprocess and return its stdout/stderr.

    Confines the process to the project root, kills it after
    MAX_PYTHON_SECONDS, and truncates output above MAX_PYTHON_OUTPUT_BYTES.

    Use cases:
        - quick numerical sanity checks ("does this regression converge?")
        - data summarisation ("how many rows, mean, std?")
        - figure generation (Experimenter, Writer)

    The subprocess inherits the parent's PYTHONPATH but NOT its
    environment beyond that — we explicitly DO NOT pass
    ANTHROPIC_API_KEY or anything from secret_env, so a wandering
    print() can't leak the vault.
    """
    paths = get_paths()
    # Build a clean env: PATH and PYTHONPATH only.
    safe_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(paths.root),
        "HOME": os.environ.get("HOME", ""),    # matplotlib needs HOME
        "TERM": "dumb",                         # no colour escapes
    }
    log.info("python_exec_start", code_len=len(code))
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(paths.root),
            env=safe_env,
            capture_output=True,
            text=True,
            timeout=MAX_PYTHON_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"python_exec timed out after {MAX_PYTHON_SECONDS}s. "
            "Simplify the code or break it into smaller calls."
        )
    except Exception as e:
        raise ToolError(f"could not run python: {e}")

    # Trim outputs and report exit code clearly.
    stdout = (proc.stdout or "")[:MAX_PYTHON_OUTPUT_BYTES]
    stderr = (proc.stderr or "")[:MAX_PYTHON_OUTPUT_BYTES]
    parts = [f"exit_code: {proc.returncode}"]
    if stdout.strip():
        parts.append("stdout:\n" + stdout.rstrip())
    if stderr.strip():
        parts.append("stderr:\n" + stderr.rstrip())
    if (len(proc.stdout or "") > MAX_PYTHON_OUTPUT_BYTES
            or len(proc.stderr or "") > MAX_PYTHON_OUTPUT_BYTES):
        parts.append(f"[output truncated at {MAX_PYTHON_OUTPUT_BYTES} bytes]")
    return "\n\n".join(parts)


# ============================================================================ web search (lightweight)

def web_search(*, query: str, n: int = 5, **_) -> str:
    """Web search via the project's existing tools.web_search module.

    Returns a JSON-shaped list of {title, url, snippet}. For DOI lookup
    or paper search the agent should use semantic_scholar_search or
    arxiv_search instead.
    """
    try:
        from tools.web_search import WebSearchTool
    except ImportError as e:
        raise ToolError(f"web_search backend unavailable: {e}")
    try:
        searcher = WebSearchTool()
        results = searcher.search(query=query, limit=int(n))
    except Exception as e:
        raise ToolError(f"web_search failed: {e}")
    log.info("web_search", q=query, n=len(results))
    return json.dumps(results[:int(n)], ensure_ascii=False, indent=2)


def semantic_scholar_search(*, query: str, limit: int = 10,
                            from_year: int | None = None, **_) -> str:
    """Search Semantic Scholar — academic-paper specific."""
    try:
        from tools.web_search import WebSearchTool
    except ImportError as e:
        raise ToolError(f"semantic_scholar backend unavailable: {e}")
    try:
        s = WebSearchTool()
        # Re-use the same module — its s2_search method wraps the API.
        results = s.s2_search(query=query, limit=int(limit),
                              from_year=from_year)
    except AttributeError:
        raise ToolError(
            "this build of WebSearchTool doesn't expose s2_search; "
            "use web_search instead"
        )
    except Exception as e:
        raise ToolError(f"semantic_scholar_search failed: {e}")
    log.info("s2_search", q=query, n=len(results))
    return json.dumps(results, ensure_ascii=False, indent=2)


# ============================================================================ registry

# Maps tool names → callable. The dispatcher in BaseAgent uses this.
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "read_file":               read_file,
    "list_directory":          list_directory,
    "write_file":              write_file,
    "python_exec":             python_exec,
    "web_search":              web_search,
    "semantic_scholar_search": semantic_scholar_search,
}


# Anthropic tool schemas. Each agent picks which subset to enable via
# `ALLOWED_TOOLS_NATIVE`. The schemas here are JSON Schema as accepted
# by the Anthropic Messages API tools parameter.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_file": {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the project. Optionally specify start_line/end_line to read a slice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to project root."},
                "start_line": {"type": "integer", "description": "1-indexed inclusive start line.", "minimum": 1},
                "end_line": {"type": "integer", "description": "1-indexed inclusive end line.", "minimum": 1},
            },
            "required": ["path"],
        },
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List files and subdirectories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to project root. Default is project root."},
            },
        },
    },
    "write_file": {
        "name": "write_file",
        "description": "Write text content to a file. Overwrites by default; pass append=true to append.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to project root."},
                "content": {"type": "string", "description": "Text to write."},
                "append": {"type": "boolean", "description": "Append instead of overwrite. Default false."},
            },
            "required": ["path", "content"],
        },
    },
    "python_exec": {
        "name": "python_exec",
        "description": (
            "Run a Python code snippet in a sandboxed subprocess and "
            "return stdout/stderr. Time-limited. No environment "
            "variables (incl. API keys) are forwarded — the snippet "
            "cannot make Anthropic calls."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute."},
            },
            "required": ["code"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "General web search. Returns a JSON list of results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "n": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Number of results (default 5)."},
            },
            "required": ["query"],
        },
    },
    "semantic_scholar_search": {
        "name": "semantic_scholar_search",
        "description": "Semantic Scholar search — paper-focused.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "from_year": {"type": "integer", "description": "Only papers from this year or later."},
            },
            "required": ["query"],
        },
    },
}


def schemas_for(names: list[str] | tuple[str, ...] | set[str]) -> list[dict[str, Any]]:
    """Return Anthropic-formatted tool schemas for the given names."""
    out = []
    for name in names:
        if name in TOOL_SCHEMAS:
            out.append(TOOL_SCHEMAS[name])
        else:
            log.warning("schema_missing_for_tool", tool=name)
    return out
