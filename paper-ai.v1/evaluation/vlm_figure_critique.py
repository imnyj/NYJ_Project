"""VLM (Vision-Language Model) critique of publication figures.

Source: AI Scientist v2 (arXiv:2504.08066) — every generated figure is
critiqued by a VLM before inclusion. For libsumo traffic plots, the most
common reviewer complaints are:

    - Missing axis labels or units
    - Wrong units (veh/h vs veh/s, m/s vs km/h)
    - Non-colorblind-safe palette
    - Overlapping legends or hidden series
    - Truncated y-axis that exaggerates differences
    - Missing error bars on aggregated metrics

One vision call per figure — token cost ≈ 1500 input + 500 output, so
<$0.02 per figure with Sonnet. This pays for itself the first time it
catches a unit-swap bug that would otherwise be a desk reject.

Output format: structured JSON with pass/fail per rubric item, so Writer
can decide whether to regenerate the figure or ship it.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from core.logger import get_logger

log = get_logger("vlm_figure_critique")

if TYPE_CHECKING:
    from tools.anthropic_client import AnthropicClient


CRITIQUE_PROMPT = """You are a senior reviewer for a SCIE-grade engineering
journal. Audit this figure against the rubric below. For each rubric item,
output pass/fail/not_applicable and a short reason.

RUBRIC:
1. axis_labels       — both axes labeled with a short name.
2. axis_units        — both axes state their units (e.g., "km/h", "veh/km").
3. units_consistent  — units match what the title/caption implies
                       (no km/h vs m/s confusion).
4. error_bars        — any aggregated metric shows error bars or CI.
5. legend            — legend present, no overlap with data, readable.
6. colorblind_safe   — distinct hues in a colorblind-safe palette OR
                       redundant encoding via linestyle/marker.
7. y_axis_honesty    — y-axis either starts at 0 or clearly marks a break.
8. font_legibility   — tick labels and axis labels are readable at figure size.
9. caption_self_contained — (if caption provided) a reader understands
                             the figure from caption alone.

Output ONLY a JSON object like:
{
  "overall_score": 0.0_to_1.0,
  "items": [
     {"name": "axis_labels", "status": "pass"|"fail"|"n/a", "reason": "..."},
     ...
  ],
  "critical_issues": ["..."],
  "suggestions": ["..."]
}

Context (optional caption or code comment): {context}
"""


@dataclass
class RubricItem:
    name: str
    status: str          # "pass" | "fail" | "n/a"
    reason: str = ""


@dataclass
class FigureCritique:
    figure_path: str
    overall_score: float = 0.0
    items: list[RubricItem] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def passed(self) -> bool:
        """Ship if overall_score >= 0.8 AND no critical_issues."""
        return self.overall_score >= 0.8 and not self.critical_issues

    def to_dict(self) -> dict:
        return {
            "figure_path": self.figure_path,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "items": [{"name": i.name, "status": i.status, "reason": i.reason}
                      for i in self.items],
            "critical_issues": self.critical_issues,
            "suggestions": self.suggestions,
            "parse_error": self.parse_error,
        }


# =================================================================== critic

class VLMFigureCritic:
    """Runs Claude vision over a figure and parses the structured verdict."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    def __init__(
        self,
        client: "AnthropicClient",
        *,
        agent: str = "reviewer",
        task_type: str = "figure_spec",
    ):
        self.client = client
        self.agent = agent
        self.task_type = task_type

    def critique(
        self,
        figure_path: Path | str,
        *,
        context: str = "",
    ) -> FigureCritique:
        figure_path = Path(figure_path)
        crit = FigureCritique(figure_path=str(figure_path))

        if not figure_path.is_file():
            crit.parse_error = f"file not found: {figure_path}"
            return crit
        if figure_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            crit.parse_error = (
                f"unsupported format {figure_path.suffix}; "
                "convert PDF to PNG first (e.g., pdftoppm)"
            )
            return crit

        try:
            img_b64, media_type = self._encode_image(figure_path)
        except Exception as e:
            crit.parse_error = f"encode failed: {e!r}"
            return crit

        # Vision call: we bypass AnthropicClient.call()'s text-only path
        # because we need to pass an image content block.
        try:
            text = self._call_vision(img_b64, media_type, context)
        except Exception as e:
            crit.parse_error = f"vision call failed: {e!r}"
            return crit

        try:
            self._parse_verdict(text, crit)
        except Exception as e:
            crit.parse_error = f"parse failed: {e!r}"
            crit.suggestions.append(f"raw reply head: {text[:300]!r}")
        return crit

    # ---------------------------------------------------- image encode

    @staticmethod
    def _encode_image(path: Path) -> tuple[str, str]:
        ext = path.suffix.lower()
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }[ext]
        data = path.read_bytes()
        return base64.standard_b64encode(data).decode("ascii"), media

    # ------------------------------------------------- vision call

    def _call_vision(
        self, img_b64: str, media_type: str, context: str,
    ) -> str:
        """Call Claude with an image+text content block."""
        route = self.client.policy.route(self.agent, self.task_type)
        model = route["model"]
        max_tokens = route["max_tokens"]

        # Build system blocks via AnthropicClient's helper so prompt caching
        # of the rubric system prompt is preserved across multiple figures.
        system_blocks = self.client._build_system_blocks(
            agent=self.agent,
            tool_schemas=None,
            shared_artifacts=None,
            extra_context=None,
            model=model,
        )

        prompt_text = CRITIQUE_PROMPT.format(context=context or "(none)")
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": prompt_text},
            ],
        }]

        self.client.policy.check_budget_before(
            model, est_input=2000, est_output=max_tokens,
        )
        response = self.client._call_with_retry(
            model=model, max_tokens=max_tokens,
            system=system_blocks, messages=messages,
            tools=None, thinking=False,
        )
        usage = self.client._extract_usage(response)
        self.client.policy.record_call(model, usage)
        return self.client._extract_text(response)

    # ---------------------------------------------------- parse

    @staticmethod
    def _parse_verdict(text: str, crit: FigureCritique) -> None:
        # Find the first balanced {...} while respecting string literals.
        # Naive brace counting breaks when a string value contains '}'.
        start = text.find("{")
        if start < 0:
            raise ValueError("no JSON object found")
        depth = 0
        end = -1
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end < 0:
            raise ValueError("unterminated JSON object")
        data = json.loads(text[start:end])
        crit.overall_score = float(data.get("overall_score", 0.0))
        crit.critical_issues = [str(x) for x in data.get("critical_issues", [])]
        crit.suggestions = [str(x) for x in data.get("suggestions", [])]
        for it in data.get("items", []):
            crit.items.append(RubricItem(
                name=str(it.get("name", "")),
                status=str(it.get("status", "n/a")),
                reason=str(it.get("reason", "")),
            ))

    # ---------------------------------------------- batch critique

    def critique_directory(
        self, dir_path: Path | str, *, context_map: dict[str, str] | None = None,
    ) -> list[FigureCritique]:
        """Critique every supported image in a directory."""
        dir_path = Path(dir_path)
        context_map = context_map or {}
        out: list[FigureCritique] = []
        for p in sorted(dir_path.iterdir()):
            if p.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue
            out.append(self.critique(p, context=context_map.get(p.name, "")))
        log.info("vlm_critique_batch",
                 dir=str(dir_path),
                 total=len(out),
                 passed=sum(1 for c in out if c.passed))
        return out
