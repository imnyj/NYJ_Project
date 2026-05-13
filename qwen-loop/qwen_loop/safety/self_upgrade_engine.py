"""
자가 수정 엔진.

흐름:
1. Qwen이 (target_path, new_content)를 제안
2. Guard로 target_path 검증
3. cooldown / daily_limit 검사
4. 원본을 .history/에 백업
5. chat_temp/ (project_root 안)에 변경된 파일을 가진 사본 생성
6. 시범 실행: syntax check + import test
7. 통과하면 → 원본 교체 + 적용 로그
8. 실패하면 → 다른 변경안으로 trial_max_retries 회 재시도
9. 모두 실패면 → UpgradeResult.success=False, exhausted=True 반환
   (chat.py가 받아서 사용자에게 승인 요청 후 unlimited 모드로 재호출 가능)

핵심 안전:
- chat_temp/는 .gitignore 권장 (다음 chat 실행 때 자동 청소)
- 시범 운영 결과 검증은 syntax + import만 (런타임 동작은 검증 못 함 — 이건 watchdog의 crash burst가 잡음)
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .guard import Guard
from .policy import Policy


@dataclass
class UpgradeResult:
    success: bool
    target_path: Path
    attempts: int
    final_content: str | None = None
    backup_path: Path | None = None
    error: str = ""
    trial_log: list[str] = field(default_factory=list)
    exhausted: bool = False             # max_retries 모두 사용했는가
    last_proposal: str | None = None    # 마지막 시도의 코드 (사용자 승인 시 보여주기용)
    last_error: str | None = None       # 마지막 trial 에러 (재개용)


class SelfUpgradeEngine:
    """
    propose() 함수를 인자로 받는다.
    propose(target_path, prev_error) -> 새 파일 전체 내용(str).
    """

    def __init__(self, policy: Policy, guard: Guard):
        self.policy = policy
        self.guard = guard
        self.history_dir = policy.project_root / ".history"
        self.history_dir.mkdir(exist_ok=True)
        self.chat_temp_dir = policy.project_root / "chat_temp"
        self.chat_temp_dir.mkdir(exist_ok=True)
        self.log_path = self.history_dir / "upgrade-log.jsonl"
        self._cleanup_old_history()
        self._cleanup_chat_temp()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upgrade(
        self,
        target_path: str | Path,
        propose: Callable[[Path, str | None], str],
        validator: Callable[[Path], tuple[bool, str]] | None = None,
        notifier: Callable[[str], None] | None = None,
        max_retries: int | None = None,
        resume_from: dict | None = None,
    ) -> UpgradeResult:
        """
        target_path 파일을 자가 수정.

        max_retries: None이면 정책의 trial_max_retries 사용.
            정수면 그 값 (사용자 승인 후 무제한 재시도 모드용 — 큰 값 또는 -1).
        resume_from: 이전 시도 결과 dict {prev_error, attempts_used} — 이어서 시도할 때.
        """
        notify = notifier or (lambda _: None)
        if max_retries is None:
            max_retries = self.policy.trial_max_retries
        unlimited = (max_retries < 0 or max_retries > 1000)

        # 1. 검증
        try:
            target = self.guard.assert_writable(target_path, for_self_upgrade=True)
        except Exception as e:
            return UpgradeResult(success=False, target_path=Path(str(target_path)),
                                  attempts=0, error=str(e))

        # 2. 한도 검사 (resume이 아닐 때만 — 이미 시작한 작업은 한도 안 셈)
        if not resume_from:
            err = self._check_limits()
            if err:
                return UpgradeResult(success=False, target_path=target,
                                      attempts=0, error=err)

        # 3. 백업 (resume이면 스킵)
        backup = None
        if resume_from and "backup_path" in resume_from:
            backup = Path(resume_from["backup_path"])
        else:
            backup = self._backup(target)
            notify(f"📦 백업: {backup.relative_to(self.policy.project_root)}")

        # 4. 시범 운영 + 재시도
        prev_error: str | None = resume_from.get("last_error") if resume_from else None
        trial_log: list[str] = list(resume_from.get("trial_log", [])) if resume_from else []
        last_proposal: str | None = None

        attempt = 0
        max_attempts = 10**6 if unlimited else max_retries
        while attempt < max_attempts:
            attempt += 1
            label = f"{attempt}" + ("" if unlimited else f"/{max_retries}")
            notify(f"🔁 시도 {label}")
            try:
                new_content = propose(target, prev_error)
                last_proposal = new_content
            except Exception as e:
                prev_error = f"propose 실패: {e}"
                trial_log.append(f"#{attempt}: {prev_error}")
                continue

            ok, msg = self._trial_run(target, new_content, validator)
            trial_log.append(f"#{attempt}: {'PASS' if ok else 'FAIL'} — {msg[:200]}")
            notify(f"   → {'✅ 통과' if ok else '❌ 실패'}: {msg[:120]}")

            if ok:
                target.write_text(new_content)
                self._log(target, attempt, "success", msg, unlimited=unlimited)
                self._cleanup_chat_temp()
                return UpgradeResult(
                    success=True, target_path=target, attempts=attempt,
                    final_content=new_content, backup_path=backup,
                    trial_log=trial_log,
                )
            prev_error = msg

        # 정해진 횟수 모두 실패
        self._log(target, max_attempts, "exhausted", prev_error or "")
        return UpgradeResult(
            success=False, target_path=target,
            attempts=max_attempts,
            backup_path=backup,
            error=f"{max_attempts}회 시도 모두 실패. 마지막: {prev_error}",
            trial_log=trial_log,
            exhausted=True,
            last_proposal=last_proposal,
            last_error=prev_error,
        )

    # ------------------------------------------------------------------
    # Limit checks
    # ------------------------------------------------------------------
    def _check_limits(self) -> str | None:
        recent = self._recent_log_entries()
        today = dt.date.today().isoformat()

        today_count = sum(1 for r in recent if r["timestamp"].startswith(today))
        if today_count >= self.policy.daily_limit:
            return f"일일 자가 수정 한도 초과 ({self.policy.daily_limit})"

        if recent:
            last_ts = dt.datetime.fromisoformat(recent[-1]["timestamp"])
            elapsed = (dt.datetime.now() - last_ts).total_seconds() / 60
            if elapsed < self.policy.cooldown_minutes:
                wait = self.policy.cooldown_minutes - elapsed
                return f"cooldown 중. {wait:.1f}분 후 재시도 가능"
        return None

    # ------------------------------------------------------------------
    # Trial run — chat_temp/ 안에 시범 사본
    # ------------------------------------------------------------------
    def _trial_run(
        self,
        target: Path,
        new_content: str,
        validator: Callable[[Path], tuple[bool, str]] | None,
    ) -> tuple[bool, str]:
        """
        chat_temp/trial-TIMESTAMP/ 안에 변경된 파일을 가진 프로젝트 사본 생성하고 검증.
        """
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        trial_root = self.chat_temp_dir / f"trial-{ts}"
        try:
            shutil.copytree(
                self.policy.project_root, trial_root,
                ignore=shutil.ignore_patterns(
                    "data", "outputs", ".history", ".trash", ".backup",
                    "__pycache__", "*.pyc", ".venv", "venv",
                    "chat_temp",                # 자기 자신 재귀 방지
                ),
            )
        except Exception as e:
            return False, f"trial copy 실패: {e}"

        try:
            rel = target.relative_to(self.policy.project_root)
            trial_target = trial_root / rel
            trial_target.parent.mkdir(parents=True, exist_ok=True)
            trial_target.write_text(new_content)

            # 검증 1: syntax check (Python 파일만)
            if trial_target.suffix == ".py":
                proc = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(trial_target)],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode != 0:
                    return False, f"syntax error: {proc.stderr.strip()[:300]}"

            # 검증 2: 사용자 정의 validator
            if validator is not None:
                try:
                    return validator(trial_target)
                except Exception as e:
                    return False, f"validator exception: {e}"

            # 검증 3: import test (qwen_loop 패키지 모듈만)
            if trial_target.suffix == ".py":
                ok, msg = self._import_test(trial_root, trial_target)
                if not ok:
                    return False, msg

            return True, "passed"
        finally:
            # 시범 디렉토리는 항상 정리 (chat_temp이 부풀지 않도록)
            try:
                shutil.rmtree(trial_root)
            except Exception:
                pass

    def _import_test(self, trial_root: Path, trial_target: Path) -> tuple[bool, str]:
        rel = trial_target.relative_to(trial_root)
        if rel.parts[0] != "qwen_loop":
            return True, "non-package file, skip import test"
        module_path = ".".join(rel.with_suffix("").parts)
        proc = subprocess.run(
            [
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, {str(trial_root)!r}); import {module_path}",
            ],
            capture_output=True, text=True,
            timeout=self.policy.trial_timeout_seconds,
            env={
                "QWEN_LOOP_POLICY": str(self.policy.policy_file),
                "PATH": "",
            },
        )
        if proc.returncode != 0:
            return False, f"import 실패: {proc.stderr.strip()[:300]}"
        return True, "import OK"

    # ------------------------------------------------------------------
    # Backup, log, cleanup
    # ------------------------------------------------------------------
    def _backup(self, target: Path) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        rel = target.relative_to(self.policy.project_root)
        flat = str(rel).replace("/", "__")
        dst = self.history_dir / f"{ts}__{flat}"
        if target.exists():
            shutil.copy2(target, dst)
        else:
            dst.write_text("")
        return dst

    def _log(self, target: Path, attempts: int, status: str, msg: str,
             unlimited: bool = False) -> None:
        rec = {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "target": str(target.relative_to(self.policy.project_root)),
            "attempts": attempts,
            "status": status,
            "message": msg[:500],
        }
        if unlimited:
            rec["mode"] = "unlimited"
        with open(self.log_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _recent_log_entries(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        out = []
        for line in self.log_path.read_text().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("status") == "success":
                    out.append(rec)
            except Exception:
                continue
        return out

    def _cleanup_old_history(self) -> None:
        cutoff = dt.datetime.now() - dt.timedelta(days=self.policy.history_keep_days)
        for f in self.history_dir.glob("*"):
            if f.is_file() and f.name != "upgrade-log.jsonl":
                try:
                    if dt.datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                except Exception:
                    pass

    def _cleanup_chat_temp(self) -> None:
        """chat_temp 안 trial-* 디렉토리 모두 정리 (이전 실행에서 남은 것)."""
        for d in self.chat_temp_dir.glob("trial-*"):
            try:
                shutil.rmtree(d)
            except Exception:
                pass

    def restore(self, backup_name: str) -> str:
        src = self.history_dir / backup_name
        if not src.exists():
            return f"백업 없음: {backup_name}"
        rest = backup_name.split("__", 1)[1] if "__" in backup_name else backup_name
        rel = rest.replace("__", "/")
        dst = self.policy.project_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return f"복원: {backup_name} → {rel}"
