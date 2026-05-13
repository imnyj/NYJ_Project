"""
Agent: 메모리/추론/어노테이션/자가 업그레이드를 묶는 메인 루프.

두 가지 출력 모드:
- structured : ReAct + Verifier + Pydantic 스키마 (페이퍼 추출 작업)
- markdown   : 단일 호출 + RAG 컨텍스트 주입 + 마크다운 본문 + 자동 저장
                 (행정·제안서·이메일·요약 등 사람이 검토·복붙할 초안)
"""

from __future__ import annotations

import datetime as dt
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .annotation import Annotator
from .annotation.schemas import KIND_MODE, mode_for
from .llm import QwenClient
from .memory import EpisodicMemory, SemanticMemory, WorkingMemory
from .reasoning import ReActLoop, Verifier
from .self_upgrade import PromptStore, Reflector, SkillProposer
from .tools import make_default_tools


@dataclass
class TaskRequest:
    kind: str
    input: dict
    output_mode: str | None = None       # 'structured' | 'markdown'. None이면 KIND_MODE 사용
    use_react: bool = True               # structured 모드 한정
    use_verifier: bool = True            # structured 모드 한정
    rag_k: int = 5                        # markdown 모드에서 끌어올 컨텍스트 청크 수


@dataclass
class TaskResult:
    task_id: int
    output: Any
    converged: bool
    saved_path: str | None = None
    score: float | None = None
    reflection_note: str = ""
    trace: list[dict] = field(default_factory=list)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"\s+", "-", text.strip())
    s = re.sub(r"[^\w가-힣\-]", "", s)
    return s[:max_len] or "untitled"


# ----------------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------------

class Agent:
    def __init__(self, config_path: str = "config.yaml"):
        cfg = yaml.safe_load(open(config_path))
        self.cfg = cfg

        self.llm = QwenClient(
            model=cfg["llm"]["model"],
            host=cfg["llm"]["base_url"],
            temperature=cfg["llm"]["temperature"],
            top_p=cfg["llm"]["top_p"],
            num_ctx=cfg["llm"]["num_ctx"],
            timeout=cfg["llm"]["request_timeout_sec"],
        )

        self.working = WorkingMemory(cfg["memory"]["working_size"])
        self.episodic = EpisodicMemory(cfg["memory"]["episodic_db"])
        self.semantic = SemanticMemory(
            persist_dir=cfg["memory"]["semantic_dir"],
            embed_model=cfg["memory"]["embed_model"],
        )

        self.verifier = Verifier(self.llm, strict=cfg["reasoning"]["verifier_strict"])
        self.tools = make_default_tools(self.semantic)
        self.react = ReActLoop(self.llm, self.tools, max_steps=cfg["reasoning"]["react_max_steps"])

        self.annotator = Annotator(
            self.llm,
            verifier=self.verifier if cfg["reasoning"]["verifier_enabled"] else None,
        )

        self.prompts = PromptStore(cfg["self_upgrade"]["prompt_dir"])
        self.reflector = Reflector(self.llm, self.episodic)
        self.skills = SkillProposer(
            self.llm, self.episodic, threshold=cfg["self_upgrade"]["skill_proposal_threshold"]
        )

        self.outputs_dir = Path(cfg.get("outputs_dir", "outputs"))
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    def run(self, req: TaskRequest) -> TaskResult:
        conc = self.cfg.get("concurrency", {})
        if conc.get("yield_to_others"):
            time.sleep(conc.get("yield_ms", 0) / 1000.0)

        mode = req.output_mode or mode_for(req.kind)
        if mode == "markdown":
            return self._run_markdown(req)
        return self._run_structured(req)

    # ------------------------------------------------------------------
    # Markdown mode — 행정/초안/요약
    # ------------------------------------------------------------------
    def _run_markdown(self, req: TaskRequest) -> TaskResult:
        version, sys_prompt = self.prompts.get(req.kind)
        instruction = req.input.get("instruction", "")

        task_id = self.episodic.log(
            kind=req.kind, prompt_version=version, input_payload=req.input
        )

        # RAG: instruction을 쿼리로 personal context 검색
        rag_chunks: list[dict] = []
        try:
            if self.semantic.count() > 0 and instruction:
                rag_chunks = self.semantic.search(instruction, k=req.rag_k)
        except Exception:
            rag_chunks = []

        rag_block = ""
        if rag_chunks:
            rag_block = "## 참고할 개인 자료 (이 사실들에 근거해서 작성하세요)\n\n"
            for i, ch in enumerate(rag_chunks, 1):
                src = ch.get("metadata", {}).get("source", "unknown")
                rag_block += f"### 자료 {i} (출처: {src})\n{ch['text']}\n\n"

        # 마크다운 모드 시스템 프롬프트
        md_system = (sys_prompt or "") + (
            "\n\n# 출력 규칙\n"
            "- 마크다운 본문만 출력하세요. 코드 블록(```)으로 감싸지 마세요.\n"
            "- 글의 첫 줄은 `# 제목`으로 시작하세요.\n"
            "- 사용자가 채워야 할 부분은 `[…]` 형식으로 명시하세요 (예: `[연구비 총액]`).\n"
            "- 참고 자료에 없는 사실(법령 조항·통계·실적 등)은 만들지 말고 `[…]` placeholder로 두세요.\n"
            "- 최종 출력 끝에 `\\n\\n---\\n\\n## 검토 노트\\n` 섹션을 두고, "
            "사용자가 발신/제출 전에 확인해야 할 항목을 짧게 bullet으로 적으세요.\n"
        )

        full_prompt = (rag_block + "\n## 작업 지시\n" + instruction).strip()

        t0 = time.time()
        body_md = ""
        error: str | None = None
        try:
            body_md = self.llm.chat(full_prompt, system=md_system)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

        # 저장
        saved_path = None
        if body_md and not error:
            saved_path = self._save_markdown(req.kind, task_id, instruction, body_md, rag_chunks)

        elapsed = time.time() - t0
        self.episodic.update(
            task_id,
            output={"saved_path": saved_path, "preview": body_md[:500]} if body_md else None,
            error=error,
        )

        ref_note = ""
        score = None
        if self.cfg["self_upgrade"].get("reflect_after_each_task"):
            ref_note, score = self._maybe_reflect(task_id, sys_prompt, req.kind)

        return TaskResult(
            task_id=task_id,
            output=body_md,
            converged=bool(body_md and not error),
            saved_path=saved_path,
            score=score,
            reflection_note=ref_note,
        )

    def _save_markdown(
        self,
        kind: str,
        task_id: int,
        instruction: str,
        body_md: str,
        rag_chunks: list[dict],
    ) -> str:
        today = dt.date.today().isoformat()
        out_dir = self.outputs_dir / today / kind
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = _slugify(instruction or kind)
        path = out_dir / f"{task_id:05d}__{slug}.md"

        # frontmatter — Obsidian/VS Code 호환
        sources = sorted({c.get("metadata", {}).get("source", "?") for c in rag_chunks})
        frontmatter = (
            "---\n"
            f"task_id: {task_id}\n"
            f"kind: {kind}\n"
            f"created: {dt.datetime.now().isoformat(timespec='seconds')}\n"
            f"instruction: {instruction!r}\n"
            f"sources: {sources}\n"
            "---\n\n"
        )
        path.write_text(frontmatter + body_md)

        # INDEX.md 갱신 — 최근 50개
        self._update_index()
        return str(path)

    def _update_index(self) -> None:
        idx_path = self.outputs_dir / "INDEX.md"
        files = sorted(self.outputs_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = [f for f in files if f.name != "INDEX.md"][:50]

        lines = ["# qwen-loop 출력 인덱스\n", "최근 50개. 최신순.\n\n"]
        for f in files:
            rel = f.relative_to(self.outputs_dir)
            mtime = dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(f"- `{mtime}` [{f.stem}]({rel})")
        idx_path.write_text("\n".join(lines))

    # ------------------------------------------------------------------
    # Structured mode — 페이퍼 추출 (기존 동작)
    # ------------------------------------------------------------------
    def _run_structured(self, req: TaskRequest) -> TaskResult:
        version, sys_prompt = self.prompts.get(req.kind)
        task_id = self.episodic.log(
            kind=req.kind, prompt_version=version, input_payload=req.input
        )

        output: Any = None
        converged = False
        trace: list[dict] = []
        error: str | None = None

        try:
            if req.use_react:
                context = yaml.safe_dump(req.input, allow_unicode=True)
                result = self.react.run(
                    task=req.input.get("instruction", req.kind),
                    context=context,
                )
                output = result.final
                converged = result.converged
                trace = result.steps
            else:
                output = self.llm.chat(
                    str(req.input.get("prompt", "")),
                    system=sys_prompt or None,
                )
                converged = True

            if req.use_verifier and output is not None:
                v = self.verifier.verify(str(output), context=str(req.input), task=req.kind)
                trace.append({"verifier": v.model_dump()})
                if not self.verifier.passes(v):
                    error = f"verifier_failed: {v.fabrications}"

        except Exception as e:
            error = f"{type(e).__name__}: {e}"

        self.episodic.update(
            task_id,
            plan=[s for s in trace if "thought" in s],
            actions=[s.get("action") for s in trace if "action" in s],
            output=output if isinstance(output, (dict, list, str, int, float, bool, type(None))) else str(output),
            error=error,
        )

        ref_note = ""
        score = None
        if self.cfg["self_upgrade"].get("reflect_after_each_task"):
            ref_note, score = self._maybe_reflect(task_id, sys_prompt, req.kind)

        return TaskResult(
            task_id=task_id,
            output=output,
            converged=converged,
            score=score,
            reflection_note=ref_note,
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Reflection helper
    # ------------------------------------------------------------------
    def _maybe_reflect(self, task_id: int, sys_prompt: str, kind: str) -> tuple[str, float | None]:
        from .memory.episodic import TaskRecord
        try:
            with self.episodic.Session() as s:
                rec = s.get(TaskRecord, task_id)
            if rec is None:
                return "", None
            r = self.reflector.reflect_and_log(rec, sys_prompt)
            note = r.note
            if r.improved_system_prompt:
                new_v = self.prompts.add_version(kind, r.improved_system_prompt)
                note += f" [proposed prompt {new_v}]"
            return note, r.score
        except Exception as e:
            return f"reflect_failed: {e}", None

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def run_ab_promotions(self) -> list[str]:
        from collections import defaultdict
        from sqlalchemy import select
        from .memory.episodic import TaskRecord

        promoted = []
        with self.episodic.Session() as s:
            rows = s.execute(select(TaskRecord.kind, TaskRecord.prompt_version).distinct()).all()
        per_kind: dict[str, set] = defaultdict(set)
        for kind, ver in rows:
            per_kind[kind].add(ver)
        for kind, versions in per_kind.items():
            for v in versions:
                if self.prompts.maybe_promote(
                    kind, v, self.episodic,
                    min_trials=self.cfg["self_upgrade"]["ab_min_trials"],
                    promote_winrate=self.cfg["self_upgrade"]["ab_promote_winrate"],
                ):
                    promoted.append(f"{kind}->{v}")
        return promoted

    def scan_skill_proposals(self) -> list[dict]:
        return [p.model_dump() for p in self.skills.scan()]

    def reflect_recent(self, n: int = 20) -> int:
        """배치 reflection — config의 reflect_batch_size에 맞춰 호출."""
        from .memory.episodic import TaskRecord
        with self.episodic.Session() as s:
            recs = (
                s.query(TaskRecord)
                .filter(TaskRecord.reflection.is_(None))
                .order_by(TaskRecord.id.desc())
                .limit(n)
                .all()
            )
        count = 0
        for r in recs:
            try:
                _, sys_prompt = self.prompts.get(r.kind)
                self.reflector.reflect_and_log(r, sys_prompt)
                count += 1
            except Exception:
                continue
        return count
