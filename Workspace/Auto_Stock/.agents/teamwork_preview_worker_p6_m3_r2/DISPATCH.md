## 2026-09-03T05:56:51Z

당신은 Auto_Stock Phase 6의 Milestone 3(대규모 병렬 HPO 파이프라인 구축 - Large-scale HPO Pipeline) 전담 Worker (teamwork_preview_worker_p6_m3_r2)입니다. (이전 워커의 쿼터 고갈로 인한 공식 교체 투입)

### 작업 환경
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m3_r2`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필수 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (반드시 먼저 정독할 것)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_6/SCOPE.md`
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_3/survey_hpo_tests.md` (HPO 파이프라인 및 테스트 구조 정밀 분석서)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m1/handoff.md` (M1에서 완성된 SL 아키텍처 3종)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m2/handoff.md` (M2에서 완성된 Hybrid RL 통합 인터페이스)
  - `/home/imnyj/GEMINI.md` (파일 락, 감사 로깅, etc 정리, 한국어 준수)

### 독점 파일 소유권 (Exclusive File Ownership)
당신은 오직 다음 파일들만 생성/수정할 권한이 있습니다:
- `modules/hpo/optuna_pipeline.py`
- `modules/hpo/exporter.py`
- `modules/hpo/__init__.py`

### 핵심 작업 목표 (Milestone 3 - Requirement R3)
Explorer 3의 설계 및 M1/M2의 산출물을 바탕으로, ResNet, Transformer, CVAE 3대 본 모델 아키텍처에 대한 대규모 Optuna HPO 파이프라인을 완성하십시오:

1. **`modules/hpo/exporter.py` 회귀 방지 및 신규 내보내기 확장**:
   - **치명적 주의**: 기존 `CSV_COLUMNS`(20개 항목)는 기존 테스트(`test_hpo.py`, `test_adversarial_challenger2_hpo.py`)에서 `len(CSV_COLUMNS) == 20`을 엄격히 검증하므로 절대로 수정하거나 삭제하지 마십시오!
   - 신규 `MAIN_MODELS_CSV_COLUMNS` 정의: 모델 아키텍처 식별자(`model_type`: resnet/transformer/cvae) 및 각 모델 고유 파라미터 컬럼들을 포함한 확장 스키마를 정의하십시오.
   - `export_main_model_trial_to_csv(trial, metrics, model_type, filepath="etc/hpo_results/main_models_hpo.csv")` 함수 구현.
   - 기존 `_process_file_lock`(`fcntl.flock` + `threading.Lock`)을 철저히 활용하여 멀티프로세스 동시 쓰기 환경에서도 CSV 파일이 깨지지 않는 원자적 쓰기를 보장하십시오.
   - `etc/hpo_results/` 디렉토리가 없으면 자동 생성(`os.makedirs(..., exist_ok=True)`).

2. **`modules/hpo/optuna_pipeline.py` 다중 SL 아키텍처 HPO 파이프라인 구현**:
   - `suggest_model_params(trial, model_type)`:
     - `resnet`: `res_blocks` (1~3), `res_filters` (16, 32, 64), `res_kernel_size` (3, 5), `sl_lr` (1e-4 ~ 1e-2 log), `sl_dropout` (0.0 ~ 0.3).
     - `transformer`: `tf_d_model` (32, 64), `tf_nhead` (2, 4, 8 - 단 `tf_d_model % tf_nhead == 0` 반드시 보장), `tf_layers` (1~3), `sl_lr`, `sl_dropout`.
     - `cvae`: `cvae_latent_dim` (8, 16, 32), `cvae_hidden_dim` (32, 64), `cvae_kl_weight` (1e-4 ~ 1e-1 log), `sl_lr`.
     - 공통 RL PPO 파라미터: `rl_lr`, `rl_gamma`, `rl_clip_range`.
   - `objective_main_model(trial, model_type, ...)` 목적함수 구현:
     - 선택된 `model_type`의 SL 모델 및 `create_hybrid_agent`를 인스턴스화.
     - `SLEnrichedTradingEnvWrapper` 환경에서 롤아웃 및 간이 PPO 에피소드 실행.
     - 금융 지표(Sharpe Ratio + 0.01 * Return %) 계산.
     - 무거래 편향 방어(`total_trades == 0` 시 -1.0), 파산 방어(잔고 급감 시 -100.0).
     - `export_main_model_trial_to_csv`를 호출하여 매 trial 종료 시 `etc/hpo_results/main_models_hpo.csv`에 원자적 누적 기록.
   - 고수준 러너 함수 `run_model_hpo(model_type, n_trials=2, output_csv="etc/hpo_results/main_models_hpo.csv", seed=42, ...)` 구현:
     - 모델 타입별 Optuna Study 생성, 최적화 실행, 최적 파라미터 및 값 반환.

3. **안정성 및 회귀 방지**:
   - 기존 `create_hpo_study`, `objective`, `run_hpo_optimization` 함수 인터페이스를 100% 보존하여 기존 HPO 테스트 45개가 단 1개도 깨지지 않도록 하십시오.
   - `modules/hpo/__init__.py`에서 신규 함수 및 스키마(`run_model_hpo`, `export_main_model_trial_to_csv`, `MAIN_MODELS_CSV_COLUMNS` 등)를 re-export.
