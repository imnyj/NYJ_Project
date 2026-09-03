## 2026-09-02T02:31:18Z

당신은 Auto_Stock 프로젝트의 Milestone 3 구현 담당 Worker (`teamwork_preview_worker_m3`)입니다.

### 작업 환경
- Your Working Directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m3/
- Project Directory: /home/imnyj/Workspace/Auto_Stock
- Original Request File: /home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md
- Project Scope Document: /home/imnyj/Workspace/Auto_Stock/PROJECT.md
- Survey Reference: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_3/handoff.md
- Previous Milestones:
  - `modules/engine/hybrid_trading_env.py`
  - `modules/models/feature_extractor.py`
  - `modules/models/hybrid_policy.py`

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 파일 소유권 (Write Ownership)
- `modules/hpo/metrics.py`
- `modules/hpo/exporter.py`
- `modules/hpo/optuna_pipeline.py`
- `modules/hpo/__init__.py`
- `scripts/run_hpo.py`
- `tests/test_hpo.py`

### 미션 및 구현 요구사항 (Milestone 3)
1. **평가 지표 모듈 (`modules/hpo/metrics.py`) 구현**:
   - `calculate_total_equity()`: 잔고 + 보유주식 × 시장가
   - `calculate_total_return_pct()`: 총 수익률(%)
   - `calculate_annualized_sharpe_ratio()`: 연율화 샤프 지수 (일별 수익률 시계열, $\sigma_r \le 10^{-8}$ 시 $0.0$ 반환하는 zero-variance 방어 로직 필수)
   - `calculate_max_drawdown_pct()`: 최대 낙폭 (MDD, %)
   - `evaluate_trading_history()`: 종합 평가 지표 딕셔너리 산출 함수
2. **결과 내보내기 모듈 (`modules/hpo/exporter.py`) 구현**:
   - `etc/hpo_results/` 디렉토리 자동 생성 보장
   - `export_trial_to_csv()`: 20개 컬럼 스키마 (`trial_id`, `state`, `objective_value`, `total_equity`, `total_return_pct`, `sharpe_ratio`, `max_drawdown_pct`, `total_trades`, `win_rate`, `param_sl_lr`, `param_sl_hidden_dim`, `param_sl_batch_size`, `param_rl_lr`, `param_rl_gamma`, `param_rl_clip_range`, `param_rl_ent_coef`, `param_rl_hidden_dim`, `duration_seconds`, `datetime_start`, `datetime_complete`)를 갖는 CSV 원자적 저장기
3. **Optuna HPO 파이프라인 (`modules/hpo/optuna_pipeline.py`) 구현**:
   - `create_hpo_study()`: TPESampler(seed=42) 및 MedianPruner 설정
   - `objective()`: SL-RL 하이퍼파라미터(학습률, 배치 크기, 네트워크 차원, 감가율, 엔트로피 계수 등)를 제안받아 `HybridTradingEnv`에서 고속 훈련 및 평가를 수행하고, 평가 지표(`total_equity`, `sharpe_ratio`)를 산출하여 CSV에 기록 후 목적 함수 값 반환
   - `run_hpo_optimization()`: `n_trials` 동안 최적화 완주 및 best_trial, study 결과 반환
4. **CLI 스크립트 (`scripts/run_hpo.py`) 구현**:
   - `--n-trials` (기본 3), `--symbol` (기본 005930), `--output` (기본 `etc/hpo_results/baseline_hpo.csv`), `--seed` (기본 42) 등을 지원하는 커맨드라인 인터페이스
5. **단위 테스트 작성 및 실행 (`tests/test_hpo.py`)**:
   - 지표 계산(Equity, Sharpe Ratio, Zero Variance 방어, MDD) 유닛 테스트
   - CSV Exporter 파일 생성 및 스키마 검증
   - Optuna HPO 파이프라인 `n_trials=3` 완주 및 CSV 3행 기록 검증
   - CLI 실행 테스트
   - `/home/imnyj/venv/bin/pytest tests/test_hpo.py -v` 100% 통과 확인
6. **최종 보고서 작성**:
   - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m3/handoff.md`에 5-Component(Observation, Logic Chain, Caveats, Conclusion, Verification Method) 형식으로 작성하고 오케스트레이터에게 완료 메시지를 전송하세요.
