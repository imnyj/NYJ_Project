# Handoff Report — Milestone M-9

## 1. Observation
- **작업 대상**: `sim_engine.py`, `oracle_generator.py`, `optuna_*.py`, `plot_*.py`, `run_*.py`, `code/` 내 하드코딩 절대경로 및 레거시 파일 격리
- **초기 상태 관측**:
  * `code/sim_engine.py`: L291 `source_script = "/home/imnyj/SumoNetSim1.1.5/src/sumo/make_sumo_set.py"`, L312 `rsu_source = "/home/imnyj/SumoNetSim1.1.5/src/sumo/rsu.poi.xml"`, L317 `env["PATH"] = "/home/imnyj/venv/bin:" + ...`, L433 `sumo_cmd = ["/home/imnyj/venv/bin/sumo", ...]` 잔존.
  * `code/oracle_generator.py`: L12/L23/L364/L638에 `/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv`, L59에 `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg` 잔존.
  * `code/optuna_optimize.py`: L17에 `/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv` 잔존.
  * `code/optuna_*.py` (9종) 및 `regenerate_optunas.py`: `output_dir = "/home/imnyj/Workspace/paper4/data/optuna"` 잔존.
  * `code/run_ablation_state.py`, `run_full_evaluation.py`, `run_parallel_evaluation.py`, `run_optuna_all_baselines.py`: `/home/imnyj/Workspace/paper4/...` 잔존.
  * `code/plot_*.py`: `DATA_DIR = "/home/imnyj/papers/paper4/paper/data"` 잔존.
  * `code/` 내 레거시 스크립트 및 백업 파일: `aggregator.py`, `train_final.py`, `tinymlp_train*.py`, `tinymlp_model.pkl*`, `_save_model.py`, `benchmark_edge.py`, `diagnostics_*`, `fix_*.py`, `rename_bl.py`, `update_plots.py`, `calc_flops_all.py`, `*.bak*`, `*.suspect*` 등 30여 개 파일 산재.
- **수정 및 격리 조치**:
  * `code/sim_engine.py`에 `find_executable(name)` (shutil.which 및 VIRTUAL_ENV/SUMO_HOME/sys.prefix/user home 순차 탐색), `get_sumo_env()`, `get_sumonetsim_paths()` 구현 및 SUMO 명령어/환경변수 동적화.
  * `code/` 내 모든 활성 `.py` 및 `.sh` 파일의 경로를 `os.path.dirname(os.path.abspath(__file__))`, `PROJECT_ROOT`, 환경변수(`DATA_DIR`, `OPTUNA_DIR`, `MODELS_DIR`, `EVAL_DIR`) 기반 상대/동적 경로로 전면 전환.
  * `code/aggregator.py`와 `code/train_final.py`, `fix_*.py`, `rename_bl.py`, `*.bak*`을 `backup/legacy_scripts/`로 이동.
  * `tinymlp_train*.py`, `tinymlp_model.pkl*`, `_save_model.py`, `benchmark_edge.py`, `diagnostics_*` 등을 `backup/legacy_tinymlp/`로 이동.

## 2. Logic Chain
1. **문제점**: 하드코딩된 `/home/imnyj/...` 및 `g:/...` 절대경로는 타 시스템, 가상환경, 컨테이너, CI/CD 환경에서 경로 미존재 오류(`FileNotFoundError`, `CalledProcessError`)를 유발하고 재현성을 심각하게 훼손함. 또한 `code/` 내에 방치된 구버전/폐기 스크립트 및 백업 파일은 유지보수 혼선과 모델 혼동을 초래함.
2. **해결 원리**:
   - 실행 바이너리(`sumo`, `netgenerate`, `python3`)는 `shutil.which`와 표준 가상환경 환경변수(`VIRTUAL_ENV`, `SUMO_HOME`, `sys.prefix`, `~/.local/bin`, `~/venv/bin`)를 순차 탐색하는 동적 헬퍼 `find_executable()`을 통해 해결.
   - 프로젝트 내 데이터 및 체크포인트 경로는 `__file__` 기반 상대경로와 환경변수 오버라이드로 해결하여 어떤 디렉토리에서 실행하더라도 자체적으로 기준 디렉토리를 도출하도록 구성.
   - 비활성/폐기 스크립트 및 백업 파일들을 `backup/legacy_scripts/` 및 `backup/legacy_tinymlp/`로 이동 격리하여 `code/`에는 순수 최신 파일만 보존.
3. **검증 결과**:
   - `code/test_m9_paths.py`를 통해 72개 파이썬 파일 전수 정규식/AST 검사 결과 하드코딩 절대경로 0건, 바이너리 동적 탐색 정상 작동, 레거시 파일 격리 완료 입증 (7 tests PASS).
   - 기존 마일스톤 전체 회귀 테스트(52개 테스트) 100% 통과로 무회귀(Zero Regression) 입증.

## 3. Caveats
- No caveats. SUMO 및 SumoNetSim 파일이 존재하지 않는 극단적 환경에서도 `None` 및 `False`를 안전하게 반환하도록 예외 처리가 완비되어 있습니다.

## 4. Conclusion
- Paper4 M-9 마일스톤(하드코딩 절대경로 제거, shutil.which/동적 경로 전환, 레거시 스크립트 backup/ 격리)이 완벽히 완료되었습니다.
- `code/` 내 잔여 72개 활성 파이썬 파일 모두 하드코딩 절대경로 위반 0건이며, 전체 테스트 스위트 52개 테스트가 100% PASS 하였습니다.

## 5. Verification Method
- **M-9 전용 검증 스위트 실행**:
  ```bash
  python3 /home/imnyj/Workspace/paper4/code/test_m9_paths.py
  ```
  - 결과: `Ran 7 tests in 0.213s, OK` (Exit Code 0)
- **전체 통합 회귀 테스트 스위트 실행**:
  ```bash
  python3 code/test_c3_reward.py && \
  python3 code/test_c1_c2_wiring.py && \
  python3 code/test_h4_grid.py && \
  python3 code/test_h5_ablation.py && \
  python3 code/test_h6_tabular.py && \
  python3 code/test_m7_nest.py && \
  python3 code/test_m8_local_cbr.py && \
  python3 code/test_m9_paths.py
  ```
  - 결과: 총 52개 테스트 100% PASS (Exit Code 0)
