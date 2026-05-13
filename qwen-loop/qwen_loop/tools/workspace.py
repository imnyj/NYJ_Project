"""
파일 도구 — Guard를 통한 경계 검증.

기존 Workspace 클래스의 자체 검증을 Guard로 위임.
project_root 전체가 사실상 workspace이며, Guard가 protected_paths만 추가 보호한다.
"""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import Any

from ..safety.guard import Guard


MAX_READ_BYTES = 200_000
MAX_LIST_ENTRIES = 500


def _trash_dir(guard: Guard) -> Path:
    p = guard.policy.project_root / ".trash"
    p.mkdir(exist_ok=True)
    return p


def _backup_dir(guard: Guard) -> Path:
    p = guard.policy.project_root / ".backup"
    p.mkdir(exist_ok=True)
    return p


def _backup(guard: Guard, path: Path) -> Path | None:
    if not path.exists() or not path.is_file():
        return None
    rel = path.relative_to(guard.policy.project_root)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = _backup_dir(guard) / f"{ts}__{str(rel).replace('/', '__')}"
    shutil.copy2(path, dst)
    return dst


# ----------------------------------------------------------------------------
# READ TOOLS
# ----------------------------------------------------------------------------

def list_files(args: dict, guard: Guard) -> str:
    rel = args.get("path", ".")
    pattern = args.get("pattern", "*")
    base = guard.assert_readable(rel)
    if not base.exists():
        return f"NOT_FOUND: {rel}"
    if base.is_file():
        return f"FILE: {base.relative_to(guard.policy.project_root)}"

    entries = []
    for p in sorted(base.rglob(pattern)):
        if any(part.startswith(".") for part in p.relative_to(guard.policy.project_root).parts):
            continue
        if p.is_dir():
            entries.append(f"  [dir]  {p.relative_to(guard.policy.project_root)}/")
        else:
            size = p.stat().st_size
            entries.append(f"  [file] {p.relative_to(guard.policy.project_root)}  ({size:,} bytes)")
        if len(entries) >= MAX_LIST_ENTRIES:
            entries.append(f"  ... ({MAX_LIST_ENTRIES}+ 항목)")
            break
    if not entries:
        return f"EMPTY: {rel}"
    return f"project_root = {guard.policy.project_root}\n" + "\n".join(entries)


def read_file(args: dict, guard: Guard) -> str:
    p = guard.assert_readable(args["path"])
    if not p.exists():
        return f"NOT_FOUND: {args['path']}"
    if p.is_dir():
        return f"IS_DIR: {args['path']} (use list_files)"
    max_b = min(args.get("max_bytes", MAX_READ_BYTES), MAX_READ_BYTES)
    try:
        text = p.read_text(errors="replace")
    except Exception as e:
        return f"READ_ERROR: {e}"
    truncated = len(text) > max_b
    if truncated:
        text = text[:max_b]
    return f"# {p.relative_to(guard.policy.project_root)}\n{text}" + (
        f"\n\n[... 잘림. 전체 {len(text):,}+ chars]" if truncated else ""
    )


# ----------------------------------------------------------------------------
# WRITE TOOLS
# ----------------------------------------------------------------------------

def write_file(args: dict, guard: Guard) -> str:
    p = guard.assert_writable(args["path"])  # protected_paths 검사는 self_upgrade 전용 플래그
    p.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup(guard, p) if p.exists() else None
    p.write_text(args["content"])
    msg = f"WROTE: {p.relative_to(guard.policy.project_root)} ({len(args['content']):,} chars)"
    if backup:
        msg += f"\n  backup: {backup.relative_to(guard.policy.project_root)}"
    return msg


def edit_file(args: dict, guard: Guard) -> str:
    p = guard.assert_writable(args["path"])
    if not p.exists():
        return f"NOT_FOUND: {args['path']}"
    text = p.read_text()
    old = args["old_str"]
    new = args.get("new_str", "")
    count = text.count(old)
    if count == 0:
        return "NO_MATCH: old_str을 찾지 못함"
    if count > 1:
        return f"MULTIPLE_MATCH: {count}회 등장 — 더 길게/특정해서"
    backup = _backup(guard, p)
    p.write_text(text.replace(old, new, 1))
    return (
        f"EDITED: {p.relative_to(guard.policy.project_root)} "
        f"(-{len(old)} +{len(new)} chars)\n"
        f"  backup: {backup.relative_to(guard.policy.project_root) if backup else '(none)'}"
    )


def delete_file(args: dict, guard: Guard) -> str:
    p = guard.assert_writable(args["path"])
    if not p.exists():
        return f"NOT_FOUND: {args['path']}"
    if p.is_dir():
        return "REJECTED: 디렉토리 삭제 미지원"
    rel = p.relative_to(guard.policy.project_root)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = _trash_dir(guard) / f"{ts}__{str(rel).replace('/', '__')}"
    shutil.move(str(p), str(dst))
    return f"TRASHED: {rel}\n  복구: mv {dst} {p}"


def move_file(args: dict, guard: Guard) -> str:
    src = guard.assert_writable(args["src"])
    dst = guard.assert_writable(args["dst"])
    if not src.exists():
        return f"NOT_FOUND: {args['src']}"
    if dst.exists():
        backup = _backup(guard, dst)
        dst.unlink()
        dst_msg = f" (덮어쓰기, backup: {backup.relative_to(guard.policy.project_root) if backup else '?'})"
    else:
        dst_msg = ""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"MOVED: {args['src']} → {dst.relative_to(guard.policy.project_root)}{dst_msg}"


def create_dir(args: dict, guard: Guard) -> str:
    p = guard.assert_writable(args["path"])
    p.mkdir(parents=True, exist_ok=True)
    return f"DIR_CREATED: {p.relative_to(guard.policy.project_root)}"


# ----------------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------------

READ_TOOL_NAMES = {"list_files", "read_file"}
WRITE_TOOL_NAMES = {"write_file", "edit_file", "delete_file", "move_file", "create_dir"}


def make_workspace_tools(guard: Guard) -> dict[str, Any]:
    return {
        "list_files":  lambda a: list_files(a, guard),
        "read_file":   lambda a: read_file(a, guard),
        "write_file":  lambda a: write_file(a, guard),
        "edit_file":   lambda a: edit_file(a, guard),
        "delete_file": lambda a: delete_file(a, guard),
        "move_file":   lambda a: move_file(a, guard),
        "create_dir":  lambda a: create_dir(a, guard),
    }


TOOL_DOCS = {
    "list_files":  "파일 목록. args: {path: str, pattern?: str}",
    "read_file":   "파일 읽기. args: {path: str, max_bytes?: int}",
    "write_file":  "[쓰기] 파일 생성/덮어쓰기. args: {path: str, content: str}",
    "edit_file":   "[쓰기] 부분 수정. args: {path: str, old_str: str, new_str: str}",
    "delete_file": "[쓰기] 휴지통으로. args: {path: str}",
    "move_file":   "[쓰기] 이동/이름변경. args: {src: str, dst: str}",
    "create_dir":  "[쓰기] 디렉토리 생성. args: {path: str}",
}
