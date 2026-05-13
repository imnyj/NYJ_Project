"""
경계 가드. 모든 파일 작업과 자가 수정 시도가 통과해야 하는 검증.

핵심 보장:
1. project_root 밖의 파일은 읽기조차 거부
2. policy_file 자체는 read-only로도 접근 거부 (혼동 방지)
3. protected_paths 안의 파일은 자가 수정 불가
4. 모든 위반은 .violations.log에 기록되고 사용자에게 알림 (정책에 따라)
"""

from __future__ import annotations

import datetime as dt
import fnmatch
from pathlib import Path
from typing import Callable

from .policy import Policy


class BoundaryError(PermissionError):
    """project_root 밖 접근 시도."""


class ViolationError(PermissionError):
    """protected_paths 또는 policy_file 수정 시도."""


class Guard:
    def __init__(self, policy: Policy, notifier: Callable[[str], None] | None = None):
        self.policy = policy
        self._notifier = notifier or (lambda _: None)
        self._log_path = policy.project_root / ".violations.log"

    # ------------------------------------------------------------------
    # Path resolution & checks
    # ------------------------------------------------------------------
    def resolve_in_project(self, path: str | Path) -> Path:
        """
        주어진 경로를 project_root 기준으로 해석.
        project_root 밖이면 BoundaryError.
        반환된 Path는 항상 절대 경로이며 project_root 안에 있음을 보장한다.
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.policy.project_root / p
        p = p.resolve()
        # 정책 파일은 절대 접근 불가 (도구 통한 우회 방지)
        if p == self.policy.policy_file:
            self._violation(f"policy_file 접근 시도: {p}")
            raise ViolationError(f"정책 파일은 도구로 접근할 수 없습니다: {p}")
        try:
            p.relative_to(self.policy.project_root)
        except ValueError:
            self._violation(f"project_root 밖 접근 시도: {p}")
            raise BoundaryError(
                f"project_root({self.policy.project_root}) 밖의 경로는 거부됩니다: {p}"
            )
        return p

    def is_protected(self, path: str | Path) -> bool:
        """주어진 경로가 protected_paths 화이트리스트에 매칭되는가."""
        try:
            p = self.resolve_in_project(path)
        except (BoundaryError, ViolationError):
            return True  # 밖이면 당연히 보호됨
        rel = str(p.relative_to(self.policy.project_root))
        for pat in self.policy.protected_paths:
            # 디렉토리 패턴 (끝이 / 또는 /로 끝나는 형태) 처리
            pat_norm = pat.rstrip("/")
            if rel == pat_norm or rel.startswith(pat_norm + "/"):
                return True
            if fnmatch.fnmatch(rel, pat):
                return True
        return False

    def assert_writable(self, path: str | Path, *, for_self_upgrade: bool = False) -> Path:
        """
        쓰기 가능한지 확인하고 절대 경로 반환.
        - project_root 밖 → BoundaryError
        - protected → ViolationError
        - policy_file → ViolationError
        """
        p = self.resolve_in_project(path)
        if for_self_upgrade and self.is_protected(p):
            self._violation(f"보호된 경로 수정 시도: {p}")
            raise ViolationError(
                f"보호된 경로는 자가 수정 불가: {p.relative_to(self.policy.project_root)}\n"
                f"(정책 파일에서 protected_paths 변경 필요 — 사용자만 가능)"
            )
        return p

    def assert_readable(self, path: str | Path) -> Path:
        """읽기 가능한지 확인. 사실상 project_root 밖만 거부."""
        return self.resolve_in_project(path)

    # ------------------------------------------------------------------
    # Violation logging
    # ------------------------------------------------------------------
    def _violation(self, msg: str) -> None:
        timestamp = dt.datetime.now().isoformat(timespec="seconds")
        line = f"[{timestamp}] {msg}\n"
        if self.policy.log_violations:
            try:
                # 로그 파일 자체는 project_root 안에 있어 정상 쓰기 가능
                with open(self._log_path, "a") as f:
                    f.write(line)
            except Exception:
                pass
        if self.policy.notify_on_violation:
            try:
                self._notifier(f"⚠️  정책 위반 시도: {msg}")
            except Exception:
                pass
