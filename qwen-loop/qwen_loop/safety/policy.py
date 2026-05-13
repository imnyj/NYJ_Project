"""
정책 파일 로더.

정책 파일은 ~/.config/qwen-loop/policy.yaml 에 있어야 한다.
없으면 PolicyError로 거부 (safe-fail).

이 모듈은 chat 도구가 절대로 정책 파일을 수정할 수 없도록 보장하는 첫 관문이다.
정책 파일 경로는 환경변수 QWEN_LOOP_POLICY로도 오버라이드 가능 (테스트용).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_POLICY_PATH = Path.home() / ".config" / "qwen-loop" / "policy.yaml"


class PolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Policy:
    """불변 정책 객체. 한 번 로드되면 변경 불가."""

    version: int
    project_root: Path
    protected_paths: tuple[str, ...]
    daily_limit: int
    cooldown_minutes: int
    trial_timeout_seconds: int
    trial_max_retries: int
    history_keep_days: int
    web_enabled: bool
    web_max_calls: int
    web_blocked_domains: frozenset[str]
    shell_enabled: bool
    shell_allowed_commands: tuple[str, ...]
    shell_timeout_seconds: int
    notify_on_violation: bool
    log_violations: bool
    policy_file: Path                # 자기 자신이 어디서 왔는지 기록 (보호 대상)


def load_policy(path: Path | str | None = None) -> Policy:
    """
    정책 파일을 읽어 Policy 인스턴스 반환.
    파일 없거나 형식 오류면 PolicyError.
    """
    if path is None:
        env = os.environ.get("QWEN_LOOP_POLICY")
        path = Path(env) if env else DEFAULT_POLICY_PATH
    else:
        path = Path(path)

    if not path.exists():
        raise PolicyError(
            f"정책 파일이 없습니다: {path}\n\n"
            f"chat을 처음 사용하시는 거라면 다음 명령으로 생성하세요:\n"
            f"  mkdir -p {path.parent}\n"
            f"  cp policy_template/policy.yaml {path}\n"
            f"  $EDITOR {path}    # project_root 등을 본인 환경에 맞게 수정\n"
            f"  chmod 444 {path}  # (권장) 읽기 전용 잠금"
        )
    if not path.is_file():
        raise PolicyError(f"정책 파일이 일반 파일이 아님: {path}")

    try:
        raw = yaml.safe_load(path.read_text())
    except Exception as e:
        raise PolicyError(f"정책 파일 파싱 실패: {e}")

    if not isinstance(raw, dict):
        raise PolicyError("정책 파일은 매핑이어야 합니다.")

    try:
        version = int(raw.get("version", 1))
        project_root = Path(raw["project_root"]).resolve()
    except KeyError as e:
        raise PolicyError(f"정책 파일에 필수 키 없음: {e}")
    except Exception as e:
        raise PolicyError(f"정책 파일 형식 오류: {e}")

    if not project_root.exists():
        raise PolicyError(f"project_root가 존재하지 않음: {project_root}")
    if not project_root.is_dir():
        raise PolicyError(f"project_root가 디렉토리가 아님: {project_root}")

    su = raw.get("self_upgrade", {}) or {}
    web = raw.get("web", {}) or {}
    shell = raw.get("shell", {}) or {}
    viol = raw.get("on_violation", {}) or {}

    return Policy(
        version=version,
        project_root=project_root,
        protected_paths=tuple(raw.get("protected_paths") or []),
        daily_limit=int(su.get("daily_limit", 10)),
        cooldown_minutes=int(su.get("cooldown_minutes", 5)),
        trial_timeout_seconds=int(su.get("trial_timeout_seconds", 60)),
        trial_max_retries=int(su.get("trial_max_retries", 5)),
        history_keep_days=int(su.get("history_keep_days", 30)),
        web_enabled=bool(web.get("enabled", True)),
        web_max_calls=int(web.get("max_calls_per_session", 30)),
        web_blocked_domains=frozenset(web.get("blocked_domains") or []),
        shell_enabled=bool(shell.get("enabled", False)),
        shell_allowed_commands=tuple(shell.get("allowed_commands") or []),
        shell_timeout_seconds=int(shell.get("timeout_seconds", 30)),
        notify_on_violation=bool(viol.get("notify_user", True)),
        log_violations=bool(viol.get("log_to_file", True)),
        policy_file=path.resolve(),
    )
