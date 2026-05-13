"""
qwen-loop chat watchdog.

chat.py를 자식 프로세스로 띄우고 다음 조건에 자동 재시작:
1. chat이 정상 종료(exit 0)했고 .restart_requested 파일이 있을 때 → 재시작
2. chat이 비정상 종료(exit != 0)했을 때 → 5초 대기 후 재시작 (crash loop 방지)

사용:
    python scripts/watchdog.py
    python scripts/watchdog.py --max-restarts 100  # 무한 루프 방지

종료: Ctrl+C
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_PATH = PROJECT_ROOT / "scripts" / "chat.py"
RESTART_FLAG = PROJECT_ROOT / ".restart_requested"
LOG_PATH = PROJECT_ROOT / ".watchdog.log"

CRASH_BACKOFF_SEC = 5
MAX_CRASH_BURST = 5      # 30초 안에 5번 크래시 시 중단


def log(msg: str) -> None:
    line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-restarts", type=int, default=1000)
    p.add_argument("--policy", default=None)
    p.add_argument("--config", default=None)
    args = p.parse_args()

    if not CHAT_PATH.exists():
        log(f"FATAL: chat.py 없음 ({CHAT_PATH})")
        sys.exit(1)

    log(f"watchdog 시작. chat = {CHAT_PATH}")
    log(f"종료하려면 Ctrl+C")

    restart_count = 0
    recent_crashes: list[float] = []

    while restart_count < args.max_restarts:
        cmd = [sys.executable, str(CHAT_PATH)]
        if args.policy:
            cmd += ["--policy", args.policy]
        if args.config:
            cmd += ["--config", args.config]

        # restart 플래그 청소
        if RESTART_FLAG.exists():
            RESTART_FLAG.unlink()

        log(f"chat 기동 #{restart_count + 1}: {' '.join(cmd)}")
        start = time.time()

        try:
            proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
        except Exception as e:
            log(f"기동 실패: {e}")
            time.sleep(CRASH_BACKOFF_SEC)
            restart_count += 1
            continue

        try:
            exit_code = proc.wait()
        except KeyboardInterrupt:
            log("Ctrl+C — chat 종료 시도")
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log("watchdog 종료")
            return

        elapsed = time.time() - start
        log(f"chat 종료. exit={exit_code}, 실행 {elapsed:.1f}s")

        # crash burst 검사
        if exit_code != 0:
            now = time.time()
            recent_crashes = [t for t in recent_crashes if now - t < 30]
            recent_crashes.append(now)
            if len(recent_crashes) >= MAX_CRASH_BURST:
                log(f"FATAL: 30초 안에 {MAX_CRASH_BURST}회 크래시 — watchdog 중단")
                log("문제 진단: tail -f .watchdog.log 또는 chat.py 직접 실행해서 에러 확인")
                sys.exit(1)
            log(f"비정상 종료 → {CRASH_BACKOFF_SEC}초 후 재시작")
            time.sleep(CRASH_BACKOFF_SEC)
            restart_count += 1
            continue

        # 정상 종료
        if RESTART_FLAG.exists():
            log("재시작 요청 감지 — 즉시 재기동")
            restart_count += 1
            continue

        # 정상 종료 + 재시작 요청 없음 = 사용자가 끈 것
        log("정상 종료 (재시작 요청 없음). watchdog도 종료.")
        return

    log(f"max_restarts({args.max_restarts}) 도달 — watchdog 종료")


if __name__ == "__main__":
    main()
