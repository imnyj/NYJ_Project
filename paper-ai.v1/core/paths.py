"""Centralized path resolution.

Replaces hardcoded `"output/.cache/..."` strings scattered across modules.
Every subsystem (memory, monitoring, self-upgrader) asks this module for
its canonical location, so the operator can relocate the project with a
single `PAPER_AI_ROOT` env var without touching code.

Resolution priority:
    1. Explicit argument (`Paths(root=...)`)
    2. `PAPER_AI_ROOT` environment variable
    3. Current working directory
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    """Project path registry — frozen so no caller can mutate it."""

    root: Path

    # -------- static subdirectories --------

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def prompts(self) -> Path:
        return self.root / "prompts"

    @property
    def skills(self) -> Path:
        return self.root / "skills"

    @property
    def tests(self) -> Path:
        return self.root / "tests"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    # -------- output tree (runtime artifacts) --------

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def cache_dir(self) -> Path:
        return self.output / ".cache"

    @property
    def sessions(self) -> Path:
        return self.output / "sessions"

    @property
    def drafts(self) -> Path:
        return self.output / "drafts"

    @property
    def figures(self) -> Path:
        return self.output / "figures"

    @property
    def code(self) -> Path:
        return self.output / "code"

    @property
    def final(self) -> Path:
        return self.output / "final"

    @property
    def snapshots(self) -> Path:
        return self.output / "snapshots"

    @property
    def upgrade_log(self) -> Path:
        return self.output / "upgrade_log"

    @property
    def annotations(self) -> Path:
        return self.output / "annotations"

    @property
    def pdfs(self) -> Path:
        return self.output / "pdfs"

    # -------- Qwen self-upgrade profile directories --------
    # The companion + pipeline both read from `qwen_profile_main`; the
    # companion writes candidates and keeps a rolling backup under the
    # same tree. See `memory/qwen_profile.py` for the read/write helpers.

    @property
    def qwen_profile_root(self) -> Path:
        return self.root / "memory" / "qwen_profile"

    @property
    def qwen_profile_main(self) -> Path:
        return self.qwen_profile_root / "main"

    @property
    def qwen_profile_backup(self) -> Path:
        return self.qwen_profile_root / "backup"

    @property
    def qwen_profile_candidate(self) -> Path:
        return self.qwen_profile_root / "candidate"

    @property
    def qwen_facts(self) -> Path:
        """Markdown file of durable facts extracted from companion
        conversations. Readable by the pipeline to bias prompts."""
        return self.root / "memory" / "qwen_facts.md"

    @property
    def qwen_self_tune_state(self) -> Path:
        """Last self-tune run: timestamp, cooldown-until, consecutive
        failure count. See core/qwen_self_tune_state.py."""
        return self.cache_dir / "qwen_self_tune_state.json"

    @property
    def companion_sessions(self) -> Path:
        return self.output / "companion_sessions"

    # -------- specific files --------

    @property
    def log_file(self) -> Path:
        return self.output / "paper-ai.log"

    @property
    def corpus_db(self) -> Path:
        return self.cache_dir / "corpus.sqlite3"

    @property
    def response_cache_db(self) -> Path:
        return self.cache_dir / "responses.sqlite3"

    @property
    def skill_library_db(self) -> Path:
        return self.cache_dir / "skills.sqlite3"

    @property
    def workflow_memory_db(self) -> Path:
        return self.cache_dir / "workflows.sqlite3"

    @property
    def watchdog_state(self) -> Path:
        return self.cache_dir / "watchdog_state.json"

    @property
    def rollback_flag(self) -> Path:
        return self.cache_dir / "rollback_requested"

    @property
    def langgraph_checkpoint(self) -> Path:
        return self.cache_dir / "lg_ckpt.sqlite"

    @property
    def user_directives(self) -> Path:
        return self.annotations / "user_directives.md"

    # -------- bootstrap --------

    def ensure_all(self) -> None:
        """Create every output directory if missing. Safe to call repeatedly."""
        for attr in (
            "output", "cache_dir", "sessions", "drafts", "figures",
            "code", "final", "snapshots", "upgrade_log", "annotations",
            "pdfs", "companion_sessions",
            "qwen_profile_root", "qwen_profile_main", "qwen_profile_backup",
        ):
            getattr(self, attr).mkdir(parents=True, exist_ok=True)


# ============================================================== resolver

@lru_cache(maxsize=1)
def get_paths() -> Paths:
    """Resolve project root from env or cwd; cached for the process.

    Call `reset_paths_for_tests()` in tests that need a fresh root.
    """
    env_root = os.environ.get("PAPER_AI_ROOT")
    root = Path(env_root).resolve() if env_root else Path.cwd().resolve()
    return Paths(root=root)


def paths_for(root: Path | str) -> Paths:
    """Explicit override — used by tests and CLI `--root` flag."""
    return Paths(root=Path(root).resolve())


def invalidate_paths_cache() -> None:
    """Clear the `get_paths()` LRU cache.

    Call after mutating `PAPER_AI_ROOT` at runtime (e.g. CLI startup or
    pytest fixtures) so subsequent `get_paths()` calls pick up the new env.
    """
    get_paths.cache_clear()


# Backward-compatible alias used by existing test fixtures.
reset_paths_for_tests = invalidate_paths_cache
