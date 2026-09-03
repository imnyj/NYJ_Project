# Handoff Report — Phase 6 ML & Models Exploration

- **작성자**: Phase 6 ML & Models Explorer (`teamwork_preview_explorer_p6_1`)
- **작성 일시**: 2026-09-03T11:03:20+09:00
- **수신자**: Orchestrator (`teamwork_preview_orchestrator_6`), Downstream Workers (`worker_m1`, etc.)
- **작업 디렉토리**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1`
- **산출물 문서**:
  - 상세 아키텍처 명세서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1/survey_models.md`

---

## 1. Observation (직접 관측 사실)

1. **기존 모델 구현 분석 (`modules/models/`)**:
   - `modules/models/feature_extractor.py:48-182`: `TabularMLPFeatureExtractor`는 입력 형상 `(Batch, input_dim)` 또는 `(input_dim,)`을 받아 `(Batch, output_dim)`을 반환하며, `nn.init.orthogonal_` 및 `torch.nan_to_num` 방어 로직이 적용되어 있음.
   - `modules/models/feature_extractor.py:185-335`: `Temporal1DCNNFeatureExtractor`는 `(Batch, seq_len, in_channels)` 입력을 받아 합성곱 및 풀링을 거쳐 `(Batch, output_dim)`을 반환함. 잔차 연결(Residual Block)이 없는 순차 구조이며, 단일 시계열만 수용 가능함.
   - `modules/models/feature_extractor.py:337-542`: `DualStreamSLFeatureExtractor`는 시계열 스트림(1D-CNN)과 정적 스트림(MLP)을 결합하여 `(Batch, output_dim)`으로 융합함. 단일 위치 인자(Dict, Tuple, 1D/2D Tensor) 자동 라우팅을 지원함.
   - `modules/models/feature_extractor.py:544-877`: `SLPretrainer`는 멀티태스크 헤드(`return_head`: 회귀, `direction_head`: 분류)를 장착하고 `SmoothL1Loss`와 `CrossEntropyLoss`의 가중 합으로 최적화하며, 사전학습 백본을 추출하는 `get_backbone()`을 제공함.
   - `modules/models/hybrid_policy.py:45-330`: `HybridActorCritic`은 주입된 `feature_extractor`로부터 `extract_features(obs)`를 호출하여 특징을 추출하고, `discrete_head` (3-class logits), `continuous_head` (Beta $\alpha, \beta$ / Gaussian $\mu, \sigma$), `value_head` ($V(s)$)를 산출함. `load_from_sl_pretrainer(pretrainer, freeze=...)`를 통해 가중치 전이 및 부분 동결을 지원함.

2. **기존 트레이딩 환경 관측치 구조 (`modules/engine/hybrid_trading_env.py`)**:
   - `hybrid_trading_env.py:112-123`: `self.observation_space = spaces.Box(shape=(14,), dtype=np.float32)`. 시장 피처 10개(`returns_1d`, `volatility_20d`, `log_return`, `ma_5/20/60_dev`, `dynamic_per/pbr/mcap`, `volume`)와 계좌 피처 4개(`cash_ratio`, `position_ratio`, `unrealized_pnl_ratio`, `step_progress`)로 구성된 14차원 1D 벡터를 반환함 (`hybrid_trading_env.py:461-560`).

3. **데이터 엔진의 분봉 데이터 수집 역량 (`modules/data/collector_price.py`)**:
   - `collector_price.py:587-640`: `get_minute_price(symbol, timeframe='1m', period='day')` 및 `resample_ohlcv(df, target_timeframe='5m')` 메서드가 이미 구축되어 있어 분봉 단위의 다중 타임프레임 데이터 추출이 가능함.

4. **기존 HPO 파이프라인 및 저장 규격 (`modules/hpo/`)**:
   - `modules/hpo/optuna_pipeline.py:94-260`: `objective()` 함수에서 `TabularMLPFeatureExtractor`와 `HybridActorCritic`을 인스턴스화하여 PPO 학습을 수행하고 Sharpe Ratio를 목적함수 값으로 산출함.
   - `modules/hpo/exporter.py:28-50`: 20개 표준 컬럼 스키마 및 `fcntl.flock` 프로세스 락 기반의 원자적 CSV 저장 메커니즘을 제공함.
   - Phase 6 요구사항: 결과 파일은 `etc/hpo_results/main_models_hpo.csv`에 기록되어야 함.

5. **현재 테스트 스위트 상태**:
   - `/home/imnyj/venv/bin/pytest tests/test_models.py` 실행 결과 24개 테스트 100% 통과 (5.43s).
   - `/home/imnyj/venv/bin/pytest tests/test_phase5_screener.py` 실행 결과 22개 테스트 100% 통과 (0.73s).
   - Phase 6 전용 테스트인 `tests/test_phase6_models.py` 및 `tests/test_phase6_hpo.py`는 현재 미존재.

---

## 2. Logic Chain (논리적 추론 체계)

1. **[관측 1, 2 기반] -> 다중 타임프레임 입력 인터페이스 표준화의 필요성**:
   - 기존 모델들은 단일 1D 시퀀스(길이 20) 또는 평탄화된 14차원 벡터만을 처리함.
   - 주식 시장의 거시 추세(일봉: 20거래일)와 미시 변동성(분봉: 60스텝)을 동시에 반영하기 위해서는 `daily_x: (B, T_day=20, C_day=10)`, `minute_x: (B, T_min=60, C_min=10)`, `tabular_x: (B, D_tab=4)`의 3개 텐서를 결합 수용하는 다중 타임프레임 표준 규격이 필수적임.
   - 기존 `HybridTradingEnv` 및 SB3 환경과의 호환성을 위해, 딕셔너리(`{"daily": ..., "minute": ..., "tabular": ...}`), 튜플(`(daily, minute, tabular)`), 기존 2-스트림 튜플(`(temporal, tabular)`), 단일 평탄화 텐서(`x: (B, 14)`)를 모두 자동 인식하여 전처리하는 유연한 입력 파서(Input Adapter)가 각 모델 내부에 구현되어야 함.

2. **[관측 1 기반] -> 1D-CNN 기반 ResNet 아키텍처 설계 도출**:
   - 기존 `Temporal1DCNNFeatureExtractor`는 순차 합성곱 계층으로 구성되어 층을 깊게 쌓을 수 없음.
   - `ResNet1DBlock` (Conv1d -> GroupNorm -> GELU -> Dropout -> Conv1d -> GroupNorm + Shortcut Identity/1x1 Conv) 구조를 도입하여 일봉 브랜치와 분봉 브랜치에 독립적으로 2~3개 블록을 적재하고, 적응형 풀링 후 Tabular MLP 표현과 Concat 융합하여 64차원 특징 벡터를 도출하는 설계가 적합함.

3. **[관측 1 기반] -> 시계열 Attention 기반 Transformer 아키텍처 설계 도출**:
   - CNN의 고정된 수용 영역 한계를 극복하고 시점 간의 비선형적 상호작용을 포착하기 위해 Multi-Head Attention 기반 인코더 도입 필요.
   - 금융 시계열의 노이즈 특성상 Post-LN보다 Pre-LN(`norm_first=True`)이 수렴 안정성에 월등함.
   - 일봉 토큰을 Query로, 분봉 토큰을 Key/Value로 참조하는 Cross-Timeframe Attention 또는 타임프레임별 인코딩 후 Temporal Attention Pooling(`AttentionPooling1D`)을 거쳐 특징 벡터를 융합하는 설계 도출.

4. **[관측 1 기반] -> 잠재 공간 이상치 탐지 기반 CVAE 아키텍처 설계 도출**:
   - 단순 지도학습 회귀/분류만으로는 시장의 블랙 스완, 플래시 크래시 등 체제 전환(Regime Shift)을 포착하기 어려움.
   - Tabular 및 거시 지표를 조건 변수 $C$로 삼고, 다중 타임프레임 시계열 $X$의 생성적 재건을 수행하는 CVAE($q(z|X, C)$, $p(X|z, C)$)를 구축.
   - Reparameterization Trick ($z = \mu + \sigma \odot \epsilon$)을 통해 잠재 공간을 탐색하며, 재건 오차와 KL 발산의 합을 $\text{AnomalyScore}$로 정량화하여 특징 벡터 및 상태에 편입.

5. **[관측 1, 4 기반] -> 하위 호환성 및 모듈화 전략 도출**:
   - 기존 `feature_extractor.py`가 이미 877라인이므로, 신규 3개 아키텍처를 단일 파일에 추가하면 가독성 및 유지보수성이 저하됨.
   - `modules/models/resnet.py`, `modules/models/transformer.py`, `modules/models/cvae.py`로 분할 생성하고, `modules/models/__init__.py`에서 일괄 re-export함으로써 기존 모듈들의 import 구문을 전혀 깨뜨리지 않고 확장 가능함.
   - 신규 3개 모델 모두 `output_dim` 속성과 `extract_features()` 메서드를 표준 준수하도록 설계함으로써 `SLPretrainer` 및 `HybridActorCritic`의 백본으로 즉각 호환 주입 가능함.

---

## 3. Caveats (한계 사항 및 가정)

1. **분봉 데이터의 실시간 가용성**:
   - 백테스트 또는 오프라인 환경에서 종목에 따라 분봉 데이터가 누락되거나 길이가 짧을 수 있습니다. 이에 대비하여 모델 내부에서 `minute_x`가 누락되거나 길이가 상이할 경우 자동 패딩(Zero-padding) 또는 복제(Duplication)하는 방어 메커니즘을 필수로 포함하도록 설계하였습니다.
2. **연산 복잡도 및 메모리 트레이드오프**:
   - Transformer 및 CVAE는 1D-CNN ResNet에 비해 파라미터 수 및 연산량이 큽니다. 대규모 HPO 실행 시 빠른 최적화를 위해 임베딩 차원(`d_model`)의 기본값을 64, 레이어 수를 2개 내외로 경량화하여 설정하였습니다.
3. **CVAE의 KL 소실(KL Vanishing) 방지**:
   - 초기 학습 시 디코더가 잠재 변수 $z$를 무시하고 재건 손실만 최적화하는 현상을 방지하기 위해, $\beta$-VAE 가중치 $\beta \approx 10^{-3}$ 스케일링을 기본 권장값으로 지정하였습니다.

---

## 4. Conclusion (최종 결론 및 Worker 지침)

Phase 6 R1 요구사항을 충족하기 위한 3가지 상이한 SL 특징 추출기 아키텍처 명세 수립을 완료하였습니다.

1. **신규 클래스 및 명세**:
   - **ResNet**: `TemporalResNetFeatureExtractor` (`modules/models/resnet.py`)
   - **Transformer**: `TemporalTransformerFeatureExtractor` (`modules/models/transformer.py`)
   - **CVAE**: `TemporalCVAEFeatureExtractor` (`modules/models/cvae.py`)
2. **다중 타임프레임 표준 Shape**:
   - 입력: `daily_x: (B, 20, 10)`, `minute_x: (B, 60, 10)`, `tabular_x: (B, 4)`
   - 출력: `features: (B, 64)`, `pred_return: (B, 1)`, `pred_direction: (B, 3)` (CVAE는 추가로 `anomaly_score: (B, 1)`)
3. **패키지 익스포트**:
   - `modules/models/__init__.py`에 3개 클래스를 노출하여 기존 코드베이스 및 외부 모듈과의 100% 하위 호환성 보장.
4. **차기 구현 담당자(Worker M1)를 위한 상세 가이드**:
   - 상세 수식, 레이어별 텐서 형상 변환 흐름, pseudo-code 및 Optuna HPO 탐색 공간 명세는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1/survey_models.md`에 완비되어 있으므로 이를 기준 설계도로 사용하여 코드를 구현할 것.

---

## 5. Verification Method (독립 검증 방법)

1. **보고서 및 명세서 물리적 경로 검증**:
   - `view_file /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1/survey_models.md`
   - `view_file /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1/handoff.md`

2. **기존 모델 테스트 스위트 회귀 검증**:
   - 명령: `/home/imnyj/venv/bin/pytest tests/test_models.py`
   - 통과 조건: 24 passed (100% Pass)

3. **신규 모델 구현 후 단위 검증 (Worker M1/M4 작업 시)**:
   - 신규 작성될 `tests/test_phase6_models.py`에 다음 검증 로직이 포함되어야 함:
     ```python
     # 3개 모델 각각에 대해 동일한 텐서 입력 테스트
     B, T_d, C_d = 4, 20, 10
     T_m, C_m = 60, 10
     D_tab = 4
     daily = torch.randn(B, T_d, C_d)
     minute = torch.randn(B, T_m, C_m)
     tab = torch.randn(B, D_tab)

     for model_cls in [TemporalResNetFeatureExtractor, TemporalTransformerFeatureExtractor, TemporalCVAEFeatureExtractor]:
         model = model_cls(output_dim=64)
         feats, ret, direction = model(daily_x=daily, minute_x=minute, tabular_x=tab)
         assert feats.shape == (B, 64)
         assert ret.shape == (B, 1)
         assert direction.shape == (B, 3)
     ```
   - 명령: `/home/imnyj/venv/bin/pytest tests/test_phase6_models.py`
