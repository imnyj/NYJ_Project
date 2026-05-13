"""Artifact type definitions for the blackboard.

Every inter-agent message is a typed artifact, not free-form chat. This
enforces the MetaGPT-style structured-document communication pattern that
research shows cuts inter-agent tokens by 30-60% vs chat-based systems
(Hong et al., ICLR 2024, arXiv:2308.00352).

Each artifact has:
    - A canonical name (matches the prompts/*.txt "Published Artifacts" list)
    - A producer role (which of the 6 agents can publish it)
    - A consumer set (which agents subscribe)
    - A payload (the actual content — text, dict, or binary path)
    - Metadata (version, timestamp, producer agent, schema hash)

The blackboard enforces producer/consumer rules so no agent can publish
outside its contract.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --------------------------------------------------------------- artifact IDs

class ArtifactName(str, Enum):
    """Canonical artifact names. Must match the 'Published Artifacts' section
    of the corresponding prompt file."""

    # Idea agent
    MAIN_IDEA = "main_idea.md"
    STORYLINE = "storyline.md"
    NOVELTY_CHECK = "novelty_check.md"

    # Librarian
    REFS = "refs.json"

    # Experimenter (Designer + Engineer modes)
    EXPERIMENT_SPEC = "experiment_spec.yaml"
    CODE_MANIFEST = "code_manifest.json"      # list of code files produced
    SIM_RESULTS = "sim_results.npz"           # numpy path
    RUN_LOG = "run_log.json"

    # Reviewer (QA + Proofreader modes)
    QA_REPORT = "qa_report.md"
    POLISH_REPORT = "polish_report.md"

    # Writer
    DRAFT_OUTLINE = "outline.md"
    DRAFT_MAIN = "main.tex"
    FIGURES_MANIFEST = "figures_manifest.json"


# ------------------------------------------------- producer / consumer rules

# Who is ALLOWED to publish each artifact (enforced by blackboard)
PRODUCER: dict[ArtifactName, str] = {
    ArtifactName.MAIN_IDEA:        "idea",
    ArtifactName.STORYLINE:        "idea",
    ArtifactName.NOVELTY_CHECK:    "idea",
    ArtifactName.REFS:             "librarian",
    ArtifactName.EXPERIMENT_SPEC:  "experimenter",
    ArtifactName.CODE_MANIFEST:    "experimenter",
    ArtifactName.SIM_RESULTS:      "experimenter",
    ArtifactName.RUN_LOG:          "experimenter",
    ArtifactName.QA_REPORT:        "reviewer",
    ArtifactName.POLISH_REPORT:    "reviewer",
    ArtifactName.DRAFT_OUTLINE:    "writer",
    ArtifactName.DRAFT_MAIN:       "writer",
    ArtifactName.FIGURES_MANIFEST: "writer",
}

# Who subscribes (receives notifications when artifact is updated)
SUBSCRIBERS: dict[ArtifactName, set[str]] = {
    ArtifactName.MAIN_IDEA:        {"librarian", "experimenter", "reviewer", "writer", "commander"},
    ArtifactName.STORYLINE:        {"experimenter", "writer", "commander"},
    ArtifactName.NOVELTY_CHECK:    {"writer", "commander"},
    ArtifactName.REFS:             {"idea", "experimenter", "writer", "reviewer", "commander"},
    ArtifactName.EXPERIMENT_SPEC:  {"experimenter", "reviewer", "writer", "commander"},
    ArtifactName.CODE_MANIFEST:    {"reviewer", "commander"},
    ArtifactName.SIM_RESULTS:      {"writer", "reviewer", "commander"},
    ArtifactName.RUN_LOG:          {"reviewer", "commander"},
    ArtifactName.QA_REPORT:        {"experimenter", "writer", "commander"},
    ArtifactName.POLISH_REPORT:    {"writer", "commander"},
    ArtifactName.DRAFT_OUTLINE:    {"commander"},
    ArtifactName.DRAFT_MAIN:       {"reviewer", "commander"},
    ArtifactName.FIGURES_MANIFEST: {"commander"},
}


# --------------------------------------------------------------- payload kind

class PayloadKind(str, Enum):
    TEXT = "text"       # raw string (markdown, yaml, tex)
    JSON = "json"       # structured dict
    FILE = "file"       # path to a binary/large file on disk


# --------------------------------------------------------------- Artifact DTO

@dataclass
class Artifact:
    """An immutable snapshot of one published artifact."""
    name: ArtifactName
    producer: str                       # agent role
    kind: PayloadKind
    payload: Any                        # str | dict | path (depends on kind)
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    schema_hash: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.schema_hash:
            self.schema_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Stable hash for cache keying; based on kind + serialized payload."""
        if self.kind == PayloadKind.TEXT:
            s = self.payload if isinstance(self.payload, str) else str(self.payload)
        elif self.kind == PayloadKind.JSON:
            s = json.dumps(self.payload, sort_keys=True, default=str)
        else:
            s = str(self.payload)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def render_for_prompt(self, max_chars: int = 4000) -> str:
        """Render this artifact as a string for inclusion in an LLM prompt.
        Long payloads are truncated with a clear marker.

        Note on JSON truncation: slicing `json.dumps(...)` mid-structure
        yields invalid JSON. We keep the naive slice but wrap it in an
        explicit "--- partial dump ---" banner so the LLM doesn't try to
        parse it as complete. For large JSON the caller should raise
        `max_chars` or split across multiple artifact reads.
        """
        header = f"--- {self.name.value} (v{self.version}, by {self.producer}) ---"
        if self.kind == PayloadKind.TEXT:
            body = self.payload if isinstance(self.payload, str) else str(self.payload)
            trailer = "\n... [truncated {n} chars of text]"
        elif self.kind == PayloadKind.JSON:
            body = json.dumps(self.payload, indent=2, ensure_ascii=False, default=str)
            trailer = (
                "\n... [truncated {n} chars — WARNING: above is a partial JSON "
                "dump; request a narrower query to get parseable content]"
            )
        else:
            body = f"[FILE: {self.payload}] (binary, not inlined)"
            trailer = "\n... [truncated {n} chars]"
        if len(body) > max_chars:
            n = len(body) - max_chars
            body = body[:max_chars] + trailer.format(n=n)
        return f"{header}\n{body}\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "producer": self.producer,
            "kind": self.kind.value,
            "payload": self.payload if self.kind != PayloadKind.FILE else str(self.payload),
            "version": self.version,
            "timestamp": self.timestamp,
            "schema_hash": self.schema_hash,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Artifact":
        return cls(
            name=ArtifactName(d["name"]),
            producer=d["producer"],
            kind=PayloadKind(d["kind"]),
            payload=d["payload"],
            version=d["version"],
            timestamp=d["timestamp"],
            schema_hash=d["schema_hash"],
            notes=d.get("notes", ""),
        )


class ArtifactContractViolation(Exception):
    """Raised when an agent tries to publish something it's not allowed to."""


def check_producer(artifact_name: ArtifactName, agent_role: str) -> None:
    """Raise if `agent_role` is not the canonical producer of `artifact_name`.

    Unknown artifacts (not in PRODUCER) are also rejected so that adding a
    new `ArtifactName` without updating the map can't silently let any
    agent publish it.
    """
    expected = PRODUCER.get(artifact_name)
    if expected is None:
        raise ArtifactContractViolation(
            f"Artifact '{artifact_name.value}' has no registered producer in "
            f"PRODUCER; refusing publish by '{agent_role}'. "
            "Update core/artifacts.py:PRODUCER when adding a new artifact."
        )
    if expected != agent_role:
        raise ArtifactContractViolation(
            f"Agent '{agent_role}' attempted to publish '{artifact_name.value}' "
            f"but only '{expected}' may produce it."
        )
