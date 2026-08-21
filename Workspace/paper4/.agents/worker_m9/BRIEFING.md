# BRIEFING — 2026-08-20T19:17:30+09:00

## Mission
Paper4 (REMO-DQN) M-9 작업: 하드코딩 절대경로 제거 및 레거시 스크립트 backup/ 격리, 독립 검증 스크립트 작성 및 마스터 작업 목록 갱신

## 🔒 My Identity
- Archetype: Coder Worker
- Roles: implementer, qa, specialist
- Working directory: /home/imnyj/Workspace/paper4/.agents/worker_m9/
- Original parent: e3b2977e-a98e-4f8c-8acd-2ad32aed2815
- Milestone: M-9

## 🔒 Key Constraints
- M-9 항목만 수정하고 독립 검증한 뒤 기록
- Integrity Mandate: No hardcoding test results, no dummy implementations
- 하드코딩 절대경로(/home/imnyj/papers/paper4, /home/imnyj/venv/bin/netgenerate, g:/ 등) 완전 제거 및 동적 경로/shutil.which 전환
- aggregator.py, train_final.py, tinymlp 레거시 스크립트/백업 파일 backup/ 격리
- code/test_m9_paths.py 작성 및 100% 통과 입증
- tasklist.md, handoff.md, execution_notes.md 갱신 및 parent에 send_message 보고
- 언어: 한국어 (GEMINI.md Rule 14)

## Current Parent
- Conversation ID: e3b2977e-a98e-4f8c-8acd-2ad32aed2815
- Updated: 2026-08-20T19:05:36+09:00

## Task Summary
- **What to build**: 절대경로 동적화, 레거시 스크립트 backup 격리, M-9 경로 검증 테스트
- **Success criteria**: code/ 내 하드코딩 절대경로 0건, legacy 파일 backup 이동, test_m9_paths.py 통과, 기존 테스트 회귀 없음
- **Interface contracts**: /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- **Code layout**: /home/imnyj/Workspace/paper4/code/

## Change Tracker
- **Files modified**:
  * `code/sim_engine.py`: find_executable, get_sumo_env, get_sumonetsim_paths 동적 탐색 추가 및 하드코딩 제거
  * `code/oracle_generator.py`: SUMOCFG_PATH, DEFAULT_ORACLE_CSV 동적화 및 docstring 구문 오류 수정
  * `code/optuna_optimize.py`: DATASET_PATH 동적화
  * `code/optuna_*.py` (9종) + `regenerate_optunas.py`: output_dir 동적화
  * `code/run_ablation_state.py`: STATE_ABLATION_DIR 동적화
  * `code/run_full_evaluation.py`, `code/run_parallel_evaluation.py`, `code/run_optuna_all_baselines.py`: sys.path 및 디렉토리 경로 동적화
  * `code/plot_*.py` (7종): DATA_DIR, OUT_DIR 동적화
  * `code/run_all_sims.sh`, `code/run_plots.sh`: SCRIPT_DIR, which python3 적용
  * `code/test_m9_paths.py`: 신규 독립 검증 테스트 스위트 작성 (7 tests)
  * `backup/legacy_scripts/`: aggregator.py, train_final.py 및 백업/유틸리티 파일 격리
  * `backup/legacy_tinymlp/`: TinyMLP 전용 레거시 스크립트/모델/진단 파일 격리
- **Build status**: PASS (Exit Code 0)
- **Pending issues**: 없음

## Quality Status
- **Build/test result**: PASS (누적 52개 테스트 전원 통과: test_c3 7, test_c1_c2 4, test_h4 5, test_h5 7, test_h6 8, test_m7 7, test_m8 7, test_m9 7)
- **Lint status**: 0 violations, AST parse 100% clean
- **Tests added/modified**: `code/test_m9_paths.py` (7 tests)

## Loaded Skills
- None required

## Key Decisions Made
- `sim_engine.py`에 `shutil.which` 기반 우선 탐색 및 가상환경(`VIRTUAL_ENV`), `SUMO_HOME`, `sys.prefix`, `~/.local/bin`, `~/venv/bin` 순차 폴백을 지원하는 `find_executable`과 `get_sumo_env`, `get_sumonetsim_paths` 구현
- 모든 스크립트의 경로를 `os.path.dirname(os.path.abspath(__file__))` 기준 프로젝트 상대경로 및 환경변수 오버라이드로 전환하여 이식성 확보
- TinyMLP 및 구버전 마이그레이션 잔존 파일 30여 개를 `backup/`으로 안전 격리

## Artifact Index
- /home/imnyj/Workspace/paper4/.agents/worker_m9/DISPATCH.md
- /home/imnyj/Workspace/paper4/.agents/worker_m9/BRIEFING.md
- /home/imnyj/Workspace/paper4/.agents/worker_m9/progress.md
- /home/imnyj/Workspace/paper4/.agents/worker_m9/handoff.md
