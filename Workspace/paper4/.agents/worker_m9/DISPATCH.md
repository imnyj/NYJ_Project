## 2026-08-20T10:05:36Z
[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_m9/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: M-9 하드코딩 절대경로 제거 및 레거시 스크립트 backup/ 격리]
순차 실행 원칙에 따라, M-8 완료에 이어 **M-9** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **하드코딩 절대경로 제거 및 shutil.which / 동적 경로 전환**:
   - `code/sim_engine.py`:
     * `/home/imnyj/venv/bin/netgenerate` 등 하드코딩된 바이너리 경로를 `shutil.which('netgenerate')` 또는 `os.environ.get('PATH')` 기반 동적 탐색으로 전환합니다.
   - `code/sensitivity_runner.py` 및 `code/` 내 모든 활성 `.py` 파일:
     * `/home/imnyj/papers/paper4/...`, Windows `g:/...`, 특정 사용자 홈 절대경로 등을 `CODE_DIR = os.path.dirname(os.path.abspath(__file__))`, `PROJECT_ROOT = os.path.dirname(CODE_DIR)` 등 상대/동적 경로 또는 환경변수로 안전하게 변경합니다.

2. **레거시 및 폐기 스크립트 backup/ 이동 격리**:
   - `code/aggregator.py`와 `code/train_final.py`를 `/home/imnyj/Workspace/paper4/backup/legacy_scripts/`로 안전하게 이동합니다.
   - `code/` 내에 잔존하는 TinyMLP 전용 레거시 스크립트 및 백업 파일들(예: `tinymlp_train.py`, `tinymlp_train_redo*.py`, `*.bak*`, `*.suspect*` 등)을 `/home/imnyj/Workspace/paper4/backup/legacy_tinymlp/` 또는 `backup/legacy_scripts/`로 격리하여 `code/`를 최신 파일만 유지하도록 정리합니다.

3. **독립 검증 스크립트 작성 및 실행 (`code/test_m9_paths.py`)**:
   - `code/test_m9_paths.py`를 작성하여:
     * `code/` 내 모든 `.py` 파일을 정규식/AST로 전수 검사하여 `/home/imnyj/papers/paper4/`, `/home/imnyj/venv/bin/netgenerate`, `g:/` 등의 하드코딩 절대경로가 **0건**임을 assert (동적 `os.path.abspath(__file__)` 등 표준 패턴은 허용).
     * `shutil.which('netgenerate')` 또는 동적 탐색이 실행 환경에서 정상 동작함을 확인.
     * `aggregator.py`, `train_final.py`가 `code/`에 존재하지 않고 `backup/`에 정상 이동되었음을 확인.
   - `python3 code/test_m9_paths.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

4. **마스터 작업 목록 갱신 (`idea/paper4_code_fix_tasklist.md`)**:
   - M-9 항목의 상태를 [x] 완료로 변경하고 수정 파일 목록, 경로 동적화 기법, backup 격리 내역 및 독립 검증 결과를 상세히 기록합니다.

5. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_m9/handoff.md`에 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
