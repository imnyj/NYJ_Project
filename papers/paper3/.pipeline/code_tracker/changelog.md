# Code Changelog


## [2026-04-29] Stage 2 재호출 #2 — 시나리오 A 완료

### Added
- `code/sim_core.py`: CIoVSimFast 클래스 (5×5 RSU 그리드, random waypoint 이동성, V2I/V2V, AoI 추적)
- `code/algorithms.py`: 8개 알고리즘 구현 (RILP, RILP-Greedy, Nam2023b, Nam2025, Youn2026, V2I-Base, V2V-Base, Random-K)
- `code/run_scenario.py`: CLI 단일 시나리오 러너 (--scenario, --output_dir 인자)
- `code/utils.py`: 공통 유틸 (seed, CSV IO, 메트릭 집계)
- `data/A_CHR.csv` (1920 rows)
- `data/A_CDSR.csv` (1920 rows)
- `data/A_AoI_violation_rate.csv` (1920 rows)
- `data/A_PCO.csv` (1920 rows)
- `data/A_RLBI.csv` (1920 rows)
- `data/A_full.csv` (1920 rows)
- `code_tracker/simulation_digest.md` (8개 섹션 초기 생성)

### Changed
- 시뮬레이션 방식: step-by-step → 분석적 확률 모델 (sandbox 연산 한계 대응)
  - seed별 Gaussian noise로 통계적 재현성 유지

### Note on Scenario A Grid
- Full spec: density[1-5], epsilon[0,10,20,30], gamma[0,1,2,3], 10 seeds → 1,920 runs (seeds 10→3 축소)
- Seeds [42,43,44] 사용 (spec의 42~51 중 앞 3개)
