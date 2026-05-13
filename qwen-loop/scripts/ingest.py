"""
개인 자료를 semantic memory(ChromaDB)에 적재한다.

지원 형식: PDF, MD, TXT, DOCX
한 번 적재해두면 모든 markdown-mode task가 RAG로 자동 활용한다.

사용:
    python scripts/ingest.py /path/to/folder
    python scripts/ingest.py /path/to/folder --tag cv
    python scripts/ingest.py /path/to/folder --rebuild   # 같은 source 재적재

idempotent: 같은 (source_path, mtime) 조합은 중복 추가하지 않음.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml
from rich import print as rprint

from qwen_loop.memory.semantic import SemanticMemory


CHUNK_SIZE = 1500       # 문자 기준 — 한국어/영문 혼용에서 ~600 토큰
CHUNK_OVERLAP = 200


def read_file(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in {".md", ".txt"}:
        return path.read_text(errors="ignore")
    if suf == ".pdf":
        from pypdf import PdfReader
        try:
            r = PdfReader(str(path))
            return "\n\n".join((p.extract_text() or "") for p in r.pages)
        except Exception as e:
            rprint(f"[yellow]PDF read failed[/yellow] {path}: {e}")
            return ""
    if suf == ".docx":
        try:
            from docx import Document
            d = Document(str(path))
            return "\n\n".join(p.text for p in d.paragraphs)
        except ImportError:
            rprint("[yellow]python-docx not installed; skipping .docx[/yellow]")
            return ""
        except Exception as e:
            rprint(f"[yellow]DOCX read failed[/yellow] {path}: {e}")
            return ""
    return ""


def chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return [c for c in chunks if c.strip()]


def file_fingerprint(path: Path) -> str:
    stat = path.stat()
    h = hashlib.sha1(f"{path}:{stat.st_size}:{int(stat.st_mtime)}".encode()).hexdigest()
    return h[:16]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--tag", default="", help="이 적재 묶음에 붙일 태그 (cv, proposals, ...)")
    p.add_argument("--rebuild", action="store_true", help="같은 source 재적재 허용")
    args = p.parse_args()

    if not args.folder.exists():
        rprint(f"[red]폴더 없음: {args.folder}[/red]")
        sys.exit(1)

    cfg = yaml.safe_load(open(args.config))
    mem = SemanticMemory(
        persist_dir=cfg["memory"]["semantic_dir"],
        embed_model=cfg["memory"]["embed_model"],
    )

    files = []
    for ext in ("*.md", "*.txt", "*.pdf", "*.docx"):
        files.extend(args.folder.rglob(ext))

    if not files:
        rprint(f"[yellow]지원 파일 없음 in {args.folder}[/yellow]")
        return

    rprint(f"[cyan]{len(files)}개 파일 발견. 적재 시작...[/cyan]")

    # 이미 적재된 fingerprint 수집
    seen: set[str] = set()
    if not args.rebuild:
        try:
            existing = mem.coll.get(include=["metadatas"])
            for m in existing.get("metadatas", []) or []:
                if m and "fingerprint" in m:
                    seen.add(m["fingerprint"])
        except Exception:
            pass

    n_added = 0
    n_skipped = 0
    for f in files:
        fp = file_fingerprint(f)
        if fp in seen:
            n_skipped += 1
            continue

        text = read_file(f)
        if not text.strip():
            continue

        chunks = chunk(text)
        metas = [
            {
                "source": str(f.relative_to(args.folder.parent) if args.folder.parent in f.parents else f),
                "fingerprint": fp,
                "chunk_idx": i,
                "total_chunks": len(chunks),
                "tag": args.tag,
                "filename": f.name,
                "ext": f.suffix.lstrip("."),
            }
            for i in range(len(chunks))
        ]
        try:
            mem.add(chunks, metadatas=metas)
            n_added += len(chunks)
            rprint(f"  [green]✓[/green] {f.name} ({len(chunks)} chunks)")
        except Exception as e:
            rprint(f"  [red]✗[/red] {f.name}: {e}")

    rprint(
        f"\n[bold]완료[/bold] — 신규 {n_added} 청크 추가, "
        f"{n_skipped} 파일 스킵 (이미 적재됨)."
    )
    rprint(f"전체 chunk 수: {mem.count()}")


if __name__ == "__main__":
    main()
