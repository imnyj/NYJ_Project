## 2026-09-03T18:20:19Z

당신은 Auto_Stock Phase 6의 Milestone 4(자동화 검증 테스트 스위트 작성 - Automated Test Suites) 전담 Test Writer (teamwork_preview_test_writer_p6_m4_r2)입니다. (공식 교체 투입)

### 작업 환경
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_test_writer_p6_m4_r2`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필수 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (최신 Phase 6 요구사항 및 Acceptance Criteria 반드시 정독)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_6/SCOPE.md`
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m1/handoff.md` (M1 SL 3종 모델 명세)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m2/handoff.md` (M2 Hybrid RL 결합 명세)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m3_r2/handoff.md` (M3 HPO 파이프라인 명세)
  - `/home/imnyj/GEMINI.md` (파일 락, 감사 로깅, clean workspace, 한국어)

### 독점 파일 소유권 (Exclusive File Ownership)
당신은 오직 다음 2개 테스트 파일만 생성/수정할 권한이 있습니다:
- `tests/test_phase6_models.py` (신규 생성)
- `tests/test_phase6_hpo.py` (신규 생성)

### 핵심 작업 목표 (Milestone 4 - Acceptance Criteria 달성)
사용자 승인 기준(Acceptance Criteria)을 완벽하고 엄격하게 입증하는 고품질 pytest 테스트 스위트를 작성하십시오:

1. **`tests/test_phase6_models.py`**:
   - **핵심 목표**: 3가지 SL 아키텍처 모델들(`TemporalResNetFeatureExtractor`, `TemporalTransformerFeatureExtractor`, `TemporalCVAEFeatureExtractor`)이 각각 정의된 형태의 동일한 텐서(Tensor) 입력을 받아 정상적인 형태(Shape)의 출력을 반환하는지 검증.
   - **세부 검증 항목**:
     a. **동일 텐서 입력 대비 정상 출력 Shape 검증**:
        - 3종 모델 각각에 동일한 표준 입력 텐서 `(B=4, seq_len=20, in_channels=10)` 주입 시:
          - `features`의 shape가 `(4, 64)`인지 검증.
          - `returns`의 shape가 `(4, 1)`인지 검증.
          - `trend_probs`의 shape가 `(4, 3)`이며 softmax 확률 합이 1.0(오차 1e-5 이내)인지 검증.
          - `anomaly_score`의 shape가 `(4, 1)`이며 비음수(non-negative)인지 검증.
     b. **다양한 입력 형태 호환성 검증**:
        - 2D 관측치 `(B=4, 14)`, Unbatched 단일 샘플 `(20, 10)` 및 `(14,)`, NumPy ndarray 입력 시에도 crash 없이 정상 텐서가 출력되는지 검증.
        - 다중 타임프레임(일봉 `(B, 20, 10)` + 분봉 `(B, 60, 10)` + 계좌 `(B, 4)`) 딕셔너리/키워드 인자 입력 시 정상 동작 검증.
     c. **RL 연동 검증 (`HybridActorCritic` & `SLEnrichedTradingEnvWrapper`)**:
        - 3종 모델을 백본으로 하는 `HybridActorCritic` 에이전트가 `create_hybrid_agent`로 정상 생성되고 `get_action_and_value` 수행 시 이산 액션(3), 연속 비중(1), 가치(1)가 유효한 범위로 출력되는지 검증.
        - `freeze_feature_extractor()` 호출 시 백본 파라미터의 `requires_grad == False` 전환 검증.
        - `SLEnrichedTradingEnvWrapper`가 SL 모델과 결합되어 reset/step 시 18차원 또는 19차원 관측치를 정확히 반환하는지 검증.

2. **`tests/test_phase6_hpo.py`**:
   - **핵심 목표**: 각 아키텍처(ResNet, Transformer, CVAE)별 Optuna 최적화가 최소 2회(`n_trials=2`) 이상 크래시 없이 정상적으로 실행되며, 결과가 `etc/hpo_results/main_models_hpo.csv` 형태로 저장됨을 입증.
   - **세부 검증 항목**:
     a. **3대 모델 Optuna HPO 완주 및 CSV 저장 입증**:
        - `resnet`, `transformer`, `cvae` 각각에 대해 `run_model_hpo(model_type, n_trials=2, output_csv="etc/hpo_results/main_models_hpo.csv", ...)`를 실행하여, 3개 최적화가 모두 크래시 없이 완료되고 반환된 best_trial 및 best_value가 유효함을 검증.
        - `etc/hpo_results/main_models_hpo.csv` 파일이 실제로 디스크에 존재함을 `os.path.exists`로 검증.
        - CSV 파일을 로드하여 총 6개 이상(각 모델별 2개 이상)의 행이 존재하고, `model_type` 컬럼에 `resnet`, `transformer`, `cvae`가 각각 2개씩 포함되어 있음을 검증.
        - `MAIN_MODELS_CSV_COLUMNS`의 필수 금융 지표(total_equity, sharpe_ratio 등) 및 하이퍼파라미터 컬럼들이 유효한 값으로 채워져 있음을 검증.
     b. **예외 처리 및 안전성 검증**:
        - 잘못된 모델명 주입 시 적절한 ValueError 발생 검증.
        - 동시성/멀티프로세스 환경에서 CSV 파일 쓰기 충돌 방지 검증 (`export_main_model_trial_to_csv` lock 검증).

3. **전체 테스트 스위트 회귀 검증**:
   - 새로 작성한 2개 테스트 파일뿐만 아니라, 기존 테스트 스위트 전체를 실행하여 **100% Pass**를 직접 확인하십시오.
