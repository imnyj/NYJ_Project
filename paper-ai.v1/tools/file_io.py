# tools/file_io.py
"""파일 읽기/쓰기 도구 — 샌드박스에서 open() 사용 불가 문제 해결."""
from smolagents import Tool
from pathlib import Path


class FileReadTool(Tool):
    name = "file_read"
    description = (
        "Read the contents of a file. "
        "Returns the file content as a string. "
        "Use this instead of open() which is blocked in the sandbox."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Absolute or relative path to the file to read",
        },
    }
    output_type = "string"

    def forward(self, file_path: str) -> str:
        p = Path(file_path)
        if not p.exists():
            return f"[오류] 파일이 존재하지 않습니다: {file_path}"
        if not p.is_file():
            return f"[오류] 파일이 아닙니다: {file_path}"
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return p.read_text(encoding="cp949")
            except Exception as e:
                return f"[오류] 파일 읽기 실패: {e}"
        except Exception as e:
            return f"[오류] 파일 읽기 실패: {e}"


class FileWriteTool(Tool):
    name = "file_write"
    description = (
        "Write content to a file. Creates parent directories automatically. "
        "Use this instead of open() which is blocked in the sandbox."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Absolute or relative path to the file to write",
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file",
        },
        "mode": {
            "type": "string",
            "description": "'write' to overwrite, 'append' to add to end (default: 'write')",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, file_path: str, content: str, mode: str = "write") -> str:
        p = Path(file_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == "append":
                with open(p, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                p.write_text(content, encoding="utf-8")
            return f"[성공] 파일 저장 완료: {file_path} ({len(content)}자)"
        except Exception as e:
            return f"[오류] 파일 쓰기 실패: {e}"


class DirectoryListTool(Tool):
    name = "directory_list"
    description = (
        "List files and folders in a directory. "
        "Returns a formatted list of contents with file sizes."
    )
    inputs = {
        "dir_path": {
            "type": "string",
            "description": "Path to the directory to list",
        },
    }
    output_type = "string"

    def forward(self, dir_path: str) -> str:
        p = Path(dir_path)
        if not p.exists():
            return f"[오류] 디렉토리가 존재하지 않습니다: {dir_path}"
        if not p.is_dir():
            return f"[오류] 디렉토리가 아닙니다: {dir_path}"
        try:
            items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
            lines = []
            for item in items:
                if item.is_dir():
                    lines.append(f"  [DIR]  {item.name}/")
                else:
                    size = item.stat().st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/1024/1024:.1f}MB"
                    lines.append(f"  [FILE] {item.name} ({size_str})")
            return f"=== {dir_path} ({len(items)}개) ===\n" + "\n".join(lines)
        except Exception as e:
            return f"[오류] 디렉토리 읽기 실패: {e}"
