# Phase 6 RL 및 트레이딩 환경 통합 조사 핸드오프 보고서 (handoff.md)

- **작성자**: teamwork_preview_explorer_p6_2 (Explorer / Investigator / Synthesist)
- **작성 일자**: 2026-09-03
- **보고 대상**: orchestrator (`f74e7742-8979-4d8a-92f2-3be7257266b1`)
- **작업 디렉토리**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/`
- **핵심 산출물**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/survey_rl_env.md`

---

## 1. Observation (관찰 사실)

1. **Gymnasium 1.2.0 트레이딩 환경 구조 (`modules/engine/hybrid_trading_env.py`)**:
   - `HybridTradingEnv` 클래스는 lines 51~631에 걸쳐 구현되어 있으며, Gymnasium 1.2.0 규격인 `reset(seed, options) -> (obs, info)` (lines 207~253), `step(action) -> (obs, reward, terminated, truncated, info)` (lines 365~459)를 반환합니다.
   - 액션 공간 (lines 98~110): `spaces.Tuple((spaces.Discrete(3), spaces.Box(0.0, 1.0, shape=(1,))))` 및 `spaces.Dict`를 지원하며, lines 632~661에 `ContinuousToHybridActionWrapper` (Box shape=(2,))가 정의되어 있습니다.
   - 관측 공간 (lines 112~122): `spaces.Box(low=-np.inf, high=np.inf, shape=(14,), dtype=np.float32)`.
   - 관측 벡터 생성 (`_get_observation`, lines 461~560): 10개 시장/기술적 피처(`returns_1d`, `volatility_20d`, `log_return`, `ma_5_dev`, `ma_20_dev`, `ma_60_dev`, `dynamic_per`, `dynamic_pbr`, `dynamic_market_cap`, `volume`) + 4개 계좌 상태 피처(`cash_ratio`, `position_ratio`, `unrealized_pnl_ratio`, `step_progress`) = 총 14차원.

2. **실시간 시뮬레이터 연동 (`modules/engine/live_learning_simulator.py`)**:
   - Phase 5 요구사항 R4에 따라 `inject_triggered_symbol` (lines 196~235), `build_rl_observation` (lines 237~289), `step_symbol` (lines 290~350)이 구현되어 있어 동적으로 14차원 관측 벡터를 추출하고 5-tuple 스텝을 수행할 수 있습니다.

3. **기존 SL 특징 추출기 및 멀티태스크 사전학습 구조 (`modules/models/feature_extractor.py`)**:
   - `TabularMLPFeatureExtractor` (lines 48~183), `Temporal1DCNNFeatureExtractor` (lines 185~335), `DualStreamSLFeatureExtractor` (lines 337~542), `SLPretrainer` (lines 544~700)가 구현되어 있습니다.
   - `SLPretrainer`는 `return_head` (1D 회귀) 및 `direction_head` (3-class 분류)를 멀티태스크로 학습합니다.

4. **하이브리드 정책 네트워크 및 PPO 구조 (`modules/models/hybrid_policy.py`)**:
   - `HybridActorCritic` (lines 45~417): Discrete 3클래스 Categorical 분포와 Continuous [0, 1] Beta(또는 Gaussian) 분포를 결합하여 액션을 산출하며, `load_from_sl_pretrainer` (lines 166~192) 및 `freeze_backbone` (lines 153~159)를 제공합니다.
   - `extract_features` (lines 193~255)는 단일 1D 텐서, 2-튜플, 딕셔너리, 다차원 텐서 입력을 유연하게 분할/결합할 수 있는 라우팅 방어 코드를 갖추고 있습니다.

5. **단위 테스트 실행 결과**:
   - 커맨드: `/home/imnyj/venv/bin/pytest tests/test_hybrid_trading_env.py tests/test_models.py`
   - 결과: `39 passed, 7 warnings in 5.48s` (Gymnasium `check_env`, 회계 불변식, PPO 학습 루프 등 100% Pass).

---

## 2. Logic Chain (추론 과정)

1. **문제 정의 및 요구사항 정합성**:
   - Phase 6 R1에서는 ResNet 1D, Time-Series Transformer, CVAE 등 3가지 SL 아키텍처를 구현해야 하며, 이들은 동일한 다중 타임프레임 시계열 텐서(`(B, seq_len, in_channels)`)를 처리해야 합니다.
   - Phase 6 R2에서는 이러한 SL 모델에서 추출된 특징 또는 예측 타겟 값(수익률, 추세 확률 등)을 상태(State)로 편입하여 매수/매도/관망 및 비중을 조절하는 Hybrid PPO 에이전트와 결합해야 합니다.
2. **관측 공간 확장 추론**:
   - 현재 `HybridTradingEnv`는 고정된 14차원 관측치를 기본으로 반환합니다.
   - SL 모델의 예측값(익일 기대수익률 1차원, 3클래스 추세 확률 3차원, CVAE 잠재 이상치 점수 1차원) 총 4~5차원을 상태로 편입하기 위해 가장 안전하고 무결한 방법은 환경 래퍼(`SLEnrichedTradingEnvWrapper`)를 도입하는 것입니다.
   - 원본 `HybridTradingEnv` 코드를 침습적으로 변경하지 않고 `gym.Wrapper`를 통해 observation을 `(14 + 4 = 18)`차원 또는 `(14 + 5 = 19)`차원으로 확장하면, 기존 14차원 기반 테스트 스위트 39개에 대한 회귀(Regression) 위험을 0으로 억제할 수 있습니다.
3. **Hybrid PPO 연동 추론**:
   - `HybridActorCritic`은 초기화 시 `obs_dim` 인자를 통해 임의의 관측 차원을 수용할 수 있으므로, `obs_dim=18` (또는 19)로 설정하면 추가적인 네트워크 변경 없이 정책-가치망이 SL 예측 타겟을 직접 입력받아 최적의 액션(이산 3개 + 비중 연속 1개)을 학습할 수 있습니다.
   - 또한 대규모 HPO 파이프라인(`modules/hpo/optuna_pipeline.py`)에서 `sl_architecture in ["resnet", "transformer", "cvae"]` 분기를 통해 각 모델별 하이퍼파라미터를 독립적으로 튜닝할 수 있습니다.

---

## 3. Caveats (주의 사항 및 가정)

1. **실제 모델 구현 미포함 (Read-Only 원칙 준수)**:
   - 본 조사는 Explorer로서 Read-Only 분석 및 인터페이스 설계만을 수행하였으며, `ResNet1DFeatureExtractor`, `TimeSeriesTransformerFeatureExtractor`, `CVAEFeatureExtractor`의 실제 PyTorch 레이어 코드는 작성하지 않았습니다 (다음 마일스톤 구현 담당자의 영역).
2. **연산 지연 시간 (Inference Latency) 가정**:
   - 스텝마다 시계열 윈도우 슬라이스를 잘라 PyTorch 모델로 실시간 추론을 돌릴 경우, 장기 백테스트 및 HPO 시 병목이 될 수 있습니다. 따라서 오프라인 HPO 및 대규모 시뮬레이션에서는 "사전 일괄 추론 후 DataFrame 캐시 주입(Batch Inference Caching)" 방식을 적용할 것을 권장합니다.

---

## 4. Conclusion (최종 평가 및 결론)

1. `modules/engine/`의 `HybridTradingEnv`와 `modules/models/`의 `HybridActorCritic`/`HybridPPO`는 Phase 6의 다중 SL 모델(ResNet, Transformer, CVAE)을 수용하기에 완벽한 구조적 유연성과 Gymnasium 1.2.0 호환성을 갖추고 있습니다.
2. 제안된 **`BaseSLFeatureExtractor` 표준 인터페이스**와 **`SLEnrichedTradingEnvWrapper` 상태 확장 래퍼**를 통해 예측 타겟(수익률, 추세 확률, 이상치 점수)을 상태로 편입하는 Phase 6 R2 요구사항을 100% 무결하게 충족할 수 있습니다.
3. 모든 세부 설계 사양, 텐서 규격, 수식, 클래스 다이어그램 및 데이터 흐름은 `survey_rl_env.md`에 집대성되어 있습니다.

---

## 5. Verification Method (독립적 검증 방법)

1. **보고서 및 설계 문서 무결성 검사**:
   ```bash
   test -f /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/survey_rl_env.md
   wc -l /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/survey_rl_env.md
   ```
2. **기존 트레이딩 환경 및 정책 테스트 스위트 회귀 검증**:
   ```bash
   /home/imnyj/venv/bin/pytest tests/test_hybrid_trading_env.py tests/test_models.py -v
   ```
   - 통과 조건: 39개 테스트 100% Pass.
3. **무효화 조건 (Invalidation Conditions)**:
   - Gymnasium 1.2.0 `check_env`가 실패하거나 `HybridTradingEnv`의 1원 회계 불변식이 깨질 경우.
   - SL 모델의 입력 형상이 다중 타임프레임 텐서 `(B, seq_len, in_channels)`와 불일치할 경우.
