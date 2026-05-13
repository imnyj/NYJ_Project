"""
PromptStore: 프롬프트를 버전별로 보관하고, A/B 결과에 따라 default를 promote.

구조:
prompts/
  extract_citations/
    v1.md          (default 표시는 default.txt가 가리킴)
    v2.md
    default.txt    (예: "v2")
"""

from __future__ import annotations

from pathlib import Path

from ..memory.episodic import EpisodicMemory


class PromptStore:
    def __init__(self, base_dir: str = "prompts"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _kind_dir(self, kind: str) -> Path:
        d = self.base / kind
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get(self, kind: str, version: str | None = None) -> tuple[str, str]:
        """(version_id, content) 반환. version=None이면 default."""
        d = self._kind_dir(kind)
        if version is None:
            default_file = d / "default.txt"
            if not default_file.exists():
                # 첫 사용 — 기본 프롬프트 시드
                return self._seed(kind)
            version = default_file.read_text().strip()
        path = d / f"{version}.md"
        if not path.exists():
            raise FileNotFoundError(f"prompt {kind}@{version} not found")
        return version, path.read_text()

    def _seed(self, kind: str) -> tuple[str, str]:
        d = self._kind_dir(kind)
        seed = f"# {kind} 기본 시스템 프롬프트\n\n임시 placeholder. self-upgrade 가 채울 예정.\n"
        (d / "v1.md").write_text(seed)
        (d / "default.txt").write_text("v1")
        return "v1", seed

    def add_version(self, kind: str, content: str) -> str:
        d = self._kind_dir(kind)
        existing = sorted(p.stem for p in d.glob("v*.md"))
        next_n = len(existing) + 1
        version = f"v{next_n}"
        (d / f"{version}.md").write_text(content)
        return version

    def set_default(self, kind: str, version: str) -> None:
        d = self._kind_dir(kind)
        (d / "default.txt").write_text(version)

    def maybe_promote(
        self,
        kind: str,
        challenger: str,
        memory: EpisodicMemory,
        min_trials: int = 20,
        promote_winrate: float = 0.6,
    ) -> bool:
        """
        challenger 버전이 충분한 시도 수에서 default보다 winrate가 높으면 promote.
        반환값: 승격 여부.
        """
        default_v, _ = self.get(kind)
        if challenger == default_v:
            return False

        n_c, wr_c = memory.winrate(kind, challenger)
        n_d, wr_d = memory.winrate(kind, default_v)
        if n_c < min_trials or n_d < min_trials:
            return False
        if wr_c >= promote_winrate and wr_c > wr_d + 0.05:
            self.set_default(kind, challenger)
            return True
        return False
