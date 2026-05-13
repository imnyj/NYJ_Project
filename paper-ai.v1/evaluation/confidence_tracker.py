"""Track confidence signals across the pipeline.

Every reviewer/verifier can report a claim (or artifact) with a confidence
score in [0.0, 1.0]. Selective CoVe and other gates consult this log to
decide whether to run expensive verification:

    confidence >= 0.9 → trusted, skip deep check
    0.7 <= c < 0.9    → normal, single check
    0.4 <= c < 0.7    → flagged, run Chain-of-Verification
    c < 0.4           → rejected, block until human review

This is what makes "selective" verification tractable: instead of running
CoVe on every paragraph (5× cost), we only run it on the ~15% of claims
that are actually low-confidence. Research basis: arXiv:2309.11495
(CoVe reduces hallucinations) + AI Scientist v2's confidence gating.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("confidence_tracker")


class ConfidenceTier(str, Enum):
    TRUSTED = "trusted"        # score >= 0.9
    NORMAL = "normal"          # 0.7 <= score < 0.9
    FLAGGED = "flagged"        # 0.4 <= score < 0.7
    REJECTED = "rejected"      # score < 0.4

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceTier":
        if score >= 0.9:
            return cls.TRUSTED
        if score >= 0.7:
            return cls.NORMAL
        if score >= 0.4:
            return cls.FLAGGED
        return cls.REJECTED


@dataclass
class ConfidenceRecord:
    """One confidence observation."""
    subject_id: str            # e.g., "cite:corpusID:12345" or "claim:L142"
    subject_type: str          # "citation" | "claim" | "figure" | "code"
    score: float               # 0..1
    source: str                # which component reported it (e.g., "verifier")
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def tier(self) -> ConfidenceTier:
        return ConfidenceTier.from_score(self.score)


class ConfidenceTracker:
    """Collects confidence records; exposes gating helpers."""

    def __init__(self):
        self._records: list[ConfidenceRecord] = []

    def record(
        self,
        *,
        subject_id: str,
        subject_type: str,
        score: float,
        source: str,
        reason: str = "",
    ) -> ConfidenceRecord:
        rec = ConfidenceRecord(
            subject_id=subject_id,
            subject_type=subject_type,
            score=max(0.0, min(1.0, score)),
            source=source,
            reason=reason,
        )
        self._records.append(rec)
        log.info(
            "confidence_recorded",
            subject_id=subject_id,
            subject_type=subject_type,
            score=round(score, 3),
            tier=rec.tier.value,
            source=source,
        )
        return rec

    # ---------------------------------------------------------- queries

    def needs_deep_verification(
        self,
        *,
        subject_type: str | None = None,
    ) -> list[ConfidenceRecord]:
        """Return records in FLAGGED tier (worth running CoVe on)."""
        out = [r for r in self._records if r.tier == ConfidenceTier.FLAGGED]
        if subject_type:
            out = [r for r in out if r.subject_type == subject_type]
        return out

    def should_block(self) -> list[ConfidenceRecord]:
        """REJECTED tier — pipeline should halt until user intervenes."""
        return [r for r in self._records if r.tier == ConfidenceTier.REJECTED]

    def all_records(
        self, *, subject_type: str | None = None,
    ) -> list[ConfidenceRecord]:
        if subject_type is None:
            return list(self._records)
        return [r for r in self._records if r.subject_type == subject_type]

    # ----------------------------------------------------------- summary

    def summary(self) -> dict[str, Any]:
        by_tier: dict[str, int] = {t.value: 0 for t in ConfidenceTier}
        by_type: dict[str, int] = {}
        for r in self._records:
            by_tier[r.tier.value] += 1
            by_type[r.subject_type] = by_type.get(r.subject_type, 0) + 1
        return {
            "total": len(self._records),
            "by_tier": by_tier,
            "by_type": by_type,
            "needs_cove": len(self.needs_deep_verification()),
            "blocked": len(self.should_block()),
        }

    # ----------------------------------------------------------- persist

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "subject_id": r.subject_id,
                "subject_type": r.subject_type,
                "score": r.score,
                "tier": r.tier.value,
                "source": r.source,
                "reason": r.reason,
                "timestamp": r.timestamp,
            }
            for r in self._records
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
