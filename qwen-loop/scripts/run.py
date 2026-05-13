"""
qwen-loop CLI.

예시:
    # 마크다운 초안 (행정·이메일·제안서·요약)
    python scripts/run.py email_draft "충북대 ○○교수님께 협업 제안 메일"
    python scripts/run.py proposal_section "○○사업 배경 섹션, 약 800자"
    python scripts/run.py summary "이 글을 3줄로 요약" --input-file note.md
    python scripts/run.py meeting_minutes "어제 학과 회의" --input-file memo.txt

    # 페이퍼 추출 (구조화)
    python scripts/run.py extract_citations "인용 모두 추출" --pdf paper.pdf

    # 유지보수
    python scripts/run.py --maintenance ab
    python scripts/run.py --maintenance reflect
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich import print as rprint

from qwen_loop.agent import Agent, TaskRequest
from qwen_loop.annotation.schemas import KIND_MODE


def main() -> None:
    p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", nargs="?", help="task kind (예: email_draft, summary, proposal_section)")
    p.add_argument("instruction", nargs="?", default="", help="작업 지시문")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--pdf", default=None, help="PDF 입력 (structured task용)")
    p.add_argument("--input-file", default=None, help="입력 텍스트 파일 (요약·회의록 등에 본문 제공)")
    p.add_argument("--mode", choices=["markdown", "structured"], default=None,
                   help="출력 모드 강제. 미지정 시 kind 기본값 사용.")
    p.add_argument("--rag-k", type=int, default=5)
    p.add_argument("--list-kinds", action="store_true")
    p.add_argument("--maintenance", choices=["ab", "skills", "reflect"])
    args = p.parse_args()

    if args.list_kinds:
        rprint("[bold]사용 가능한 task kind[/bold]")
        for k, mode in sorted(KIND_MODE.items()):
            tag = "[cyan]markdown[/cyan]" if mode == "markdown" else "[yellow]structured[/yellow]"
            rprint(f"  {tag}  {k}")
        return

    agent = Agent(args.config)

    if args.maintenance == "ab":
        rprint(json.dumps({"promoted": agent.run_ab_promotions()}, ensure_ascii=False, indent=2))
        return
    if args.maintenance == "skills":
        rprint(json.dumps({"proposals": agent.scan_skill_proposals()}, ensure_ascii=False, indent=2))
        return
    if args.maintenance == "reflect":
        n = agent.reflect_recent(n=20)
        rprint(f"[green]reflected {n} recent tasks[/green]")
        return

    if not args.kind:
        p.error("kind 인자가 필요합니다. --list-kinds 로 가능한 종류 확인.")

    payload = {"instruction": args.instruction}
    if args.pdf:
        payload["pdf_path"] = args.pdf
    if args.input_file:
        payload["body"] = Path(args.input_file).read_text()
        # input-file 내용은 instruction과 합쳐서 LLM에 전달
        payload["instruction"] = (
            f"{args.instruction}\n\n## 입력 본문\n\n{payload['body']}"
        )

    req = TaskRequest(
        kind=args.kind,
        input=payload,
        output_mode=args.mode,
        rag_k=args.rag_k,
    )
    result = agent.run(req)

    rprint(f"[bold green]task_id={result.task_id}[/bold green] converged={result.converged}")
    if result.saved_path:
        rprint(f"[bold]저장됨:[/bold] {result.saved_path}")
    if result.reflection_note:
        rprint(f"[dim]reflection: {result.reflection_note}[/dim]")
    rprint("\n[dim]--- 출력 미리보기 ---[/dim]")
    out = result.output if isinstance(result.output, str) else json.dumps(
        result.output, ensure_ascii=False, indent=2
    )
    rprint(out[:1500] + ("\n[...]" if out and len(out) > 1500 else ""))


if __name__ == "__main__":
    main()
