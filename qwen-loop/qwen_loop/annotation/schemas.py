"""
페이퍼 잡일용 6개 + 행정/초안용 7개 = 총 13개 어노테이션 스키마.

mode 레지스트리는 task kind를 두 갈래로 나눈다:
- "structured"  : ReAct + Verifier + JSON 출력 (페이퍼 추출 작업)
- "markdown"    : 단일 호출 + 마크다운 본문 + 자동 저장 (행정/초안/요약)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------------
# 기존 — 페이퍼 처리용 구조화 스키마
# ----------------------------------------------------------------------------

class CitationRecord(BaseModel):
    in_text: str = Field(description="본문에 등장한 형태 (예: 'Smith et al. (2020)')")
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    title: str | None = None
    venue: str | None = None
    doi: str | None = None
    bibkey: str | None = None


class SectionLabel(BaseModel):
    label: Literal[
        "abstract", "introduction", "related_work", "method",
        "experiment", "result", "discussion", "limitation",
        "conclusion", "appendix", "other",
    ]
    confidence: float = Field(ge=0, le=1)
    rationale: str


class ClaimEvidence(BaseModel):
    claim: str
    evidence_quotes: list[str] = Field(default_factory=list)
    evidence_kind: Literal["empirical", "theoretical", "citation", "none"] = "none"
    strength: Literal["weak", "moderate", "strong"] = "moderate"


class MethodTag(BaseModel):
    primary_method: str
    paradigm: Literal["supervised", "self_supervised", "unsupervised", "rl", "mixed", "other"]
    keywords: list[str] = Field(default_factory=list, max_length=10)
    datasets: list[str] = Field(default_factory=list)


class LimitationNote(BaseModel):
    quote: str
    category: Literal["data", "method", "evaluation", "scope", "compute", "other"]
    severity_estimate: Literal["minor", "moderate", "major"] = "moderate"


class TodoTask(BaseModel):
    title: str
    kind: str
    inputs: dict = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    expected_output: str = ""


# ----------------------------------------------------------------------------
# 신규 — 행정/제안서/요약용 마크다운 초안 스키마
# ----------------------------------------------------------------------------

class MarkdownDraft(BaseModel):
    """범용 마크다운 초안 — 메타정보만 구조화, 본문은 자유."""

    title: str
    purpose: str
    body_md: str
    needs_followup: list[str] = Field(default_factory=list)


class MeetingMinutes(BaseModel):
    title: str
    date: str
    attendees: list[str] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    discussion_md: str
    decisions: list[str] = Field(default_factory=list)
    action_items: list[dict] = Field(default_factory=list)


class EmailDraft(BaseModel):
    to: str
    subject: str
    tone: Literal["formal", "neutral", "warm", "urgent"] = "formal"
    body_md: str
    notes_for_author: str = ""


class ProposalSection(BaseModel):
    section_kind: Literal[
        "background", "necessity", "objective", "method",
        "schedule", "outcome", "budget", "team", "other",
    ]
    body_md: str
    placeholders: list[str] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    source_kind: Literal["paper", "report", "article", "email_thread", "book_chapter", "other"]
    length_mode: Literal["one_line", "three_lines", "paragraph", "full"] = "paragraph"
    body_md: str
    key_points: list[str] = Field(default_factory=list)


class FormFill(BaseModel):
    form_name: str
    filled_fields: dict
    missing_fields: list[str] = Field(default_factory=list)
    notes_for_author: str = ""


class ActionItemList(BaseModel):
    source_summary: str
    items: list[dict] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# 레지스트리
# ----------------------------------------------------------------------------

SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "citation": CitationRecord,
    "section_label": SectionLabel,
    "claim_evidence": ClaimEvidence,
    "method_tag": MethodTag,
    "limitation": LimitationNote,
    "todo": TodoTask,
    "draft": MarkdownDraft,
    "meeting_minutes": MeetingMinutes,
    "email_draft": EmailDraft,
    "proposal_section": ProposalSection,
    "summary": DocumentSummary,
    "form_fill": FormFill,
    "action_items": ActionItemList,
}

KIND_MODE: dict[str, str] = {
    "citation": "structured",
    "section_label": "structured",
    "claim_evidence": "structured",
    "method_tag": "structured",
    "limitation": "structured",
    "todo": "structured",
    "draft": "markdown",
    "meeting_minutes": "markdown",
    "email_draft": "markdown",
    "proposal_section": "markdown",
    "summary": "markdown",
    "form_fill": "markdown",
    "action_items": "markdown",
}


def mode_for(kind: str) -> str:
    return KIND_MODE.get(kind, "markdown")
