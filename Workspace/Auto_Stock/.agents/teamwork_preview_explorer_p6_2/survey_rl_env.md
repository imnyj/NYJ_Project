# Auto_Stock Phase 6: RL 및 트레이딩 환경 통합 조사 보고서 (survey_rl_env.md)

- **작성 일자**: 2026-09-03
- **작성 에이전트**: teamwork_preview_explorer_p6_2 (Explorer / Investigator / Synthesist)
- **프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`
- **대상 모듈**: `modules/engine/` (`hybrid_trading_env.py`, `live_learning_simulator.py`), `modules/models/` (`feature_extractor.py`, `hybrid_policy.py`), `modules/hpo/` (`optuna_pipeline.py`)

---

## 1. 개요 및 요약 (Executive Summary)

본 조사는 주식 자동 매매 프로그램 Auto_Stock의 **Phase 6: 본 모델(Main Model) 아키텍처 개발 및 병렬 탐색** 중 **R2 (하이브리드 강화학습 통합)** 요구사항을 성공적으로 달성하기 위해, 기존의 강화학습 트레이딩 환경(`modules/engine/`) 및 하이브리드 정책 네트워크(`modules/models/hybrid_policy.py`)의 구조를 면밀히 분석하고, 신규 구현될 3가지 지도학습(SL) 아키텍처(**ResNet, Transformer, CVAE**)와의 완벽한 결합(End-to-End 연결) 인터페이스를 도출하는 것을 목적으로 합니다.

### 핵심 조사 결과 요약:
1. **Gymnasium 1.2.0 트레이딩 환경 구조 확인**:
   - `HybridTradingEnv`는 표준 5-tuple `(obs, reward, terminated, truncated, info)` 반환 규격을 완벽 준수하며, `spaces.Tuple(Discrete(3), Box(1,))` 및 `ContinuousToHybridActionWrapper(Box(2,))`를 통해 이산(매수/매도/관망)과 연속(포지션 비중 0.0~1.0) 결정을 동시에 처리합니다.
   - 현재 기본 관측치(Observation)는 **14차원** 벡터(10개 시장/기술적/밸류에이션 피처 + 4개 계좌 상태 피처)로 구성되어 있습니다.
   - `LiveLearningSimulator`는 Phase 5에서 추가된 `inject_triggered_symbol`, `build_rl_observation`, `step_symbol` 인터페이스를 통해 실시간 종목 트리거 및 14차원 관측 생성을 지원합니다.

2. **Phase 6 R2 결합 인터페이스 설계 도출**:
   - **다중 SL 모델 공통 입력 규격**: 다중 타임프레임 시계열 텐서 `(B, seq_len, in_channels)` (기본 $20 \times 10$)를 동일하게 수용하는 `BaseSLFeatureExtractor` 추상 베이스 클래스 정의.
   - **State 편입 (Prediction-Level State Augmentation)**:
     - SL 모델이 산출한 예측 타겟 값(익일 기대 수익률 1차원 + 3클래스 추세 확률 3차원 + CVAE 잠재 이상치 점수 1차원 등 총 4~5차원)을 환경의 관측 공간에 동적으로 결합하여 **18~19차원**의 확장 상태 벡터 $S_t^{aug}$를 생성하는 `SLEnrichedTradingEnvWrapper` 아키텍처 수립.
   - **End-to-End 특징 백본 결합 (Feature-Level Integration)**:
     - `HybridActorCritic`의 `feature_extractor` 백본 자리에 ResNet/Transformer/CVAE 인코더를 직접 탑재하고, SL 사전학습 가중치를 전이(Transfer) 및 부분 고정(Freeze)할 수 있는 통합 팩토리 인터페이스 설계.

3. **환경 호환성 및 데이터 무결성 검증**:
   - 기존 39개 단위/통합 테스트 스위트(Gymnasium `check_env`, SB3 연동, PPO 학습 루프 등)가 100% 통과(Pass)함을 실증하였으며, 제안된 연동 설계는 기존 회계 불변식(1원 오차 방어) 및 Gymnasium 1.2.0 표준을 완전하게 보존합니다.

---

## 2. `modules/engine/` 트레이딩 환경 및 관측치 구조 정밀 분석

### 2.1 `HybridTradingEnv` (`modules/engine/hybrid_trading_env.py`)

`HybridTradingEnv`는 고성능 백테스트(오프라인 모드) 및 키움 실시간 Paper Trading(라이브 모드)을 모두 지원하는 Gymnasium 1.2.0 규격 강화학습 환경입니다.

#### A. 액션 공간 (Action Space)
환경은 매매 방향(방향성)과 자금 집행 비중(포지션 크기)을 독립적으로 결정하는 하이브리드 액션 공간을 제공합니다.
- **Tuple 모드 (기본값)**:
  ```python
  spaces.Tuple((
      spaces.Discrete(3),                             # 0: HOLD, 1: BUY, 2: SELL
      spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)  # 포지션 비중 (0.0 ~ 1.0)
  ))
  ```
- **Dict 모드 (`action_space_type="dict"`)**:
  ```python
  spaces.Dict({
      "action_type": spaces.Discrete(3),
      "position_size": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
  })
  ```
- **Continuous 2D Wrapper (`ContinuousToHybridActionWrapper`)**:
  - `Box(low=[-1.0, 0.0], high=[1.0, 1.0], shape=(2,))`
  - Stable-Baselines3 등 연속 액션 전용 알고리즘을 위해 `action[0] > 0.333` (BUY), `action[0] < -0.333` (SELL), 기타 (HOLD)로 매핑.
- **액션 파서 (`_parse_action`)**:
  - Tuple, Dict, 1D ndarray, int, float, 2D Box tensor 등 어떠한 포맷의 액션이 들어와도 내부적으로 `(act_type: int, weight: float)`의 튜플로 안전하게 정규화(clipping 및 NaN 방어 포함).

#### B. 관측 공간 (Observation Space) 및 피처 구성
현재 관측 벡터는 총 **14차원**의 1D `np.float32` 배열로 구성됩니다 (`spaces.Box(low=-np.inf, high=np.inf, shape=(14,), dtype=np.float32)`).

| 인덱스 | 피처 명칭 | 데이터 소스 / 산출 수식 | 정규화 및 클리핑 범위 | 설명 |
|---|---|---|---|---|
| `0` | `returns_1d` | $(P_t - P_{t-1}) / P_{t-1}$ | $[-0.3, 0.3]$ | 직전 거래일 대비 단순 수익률 |
| `1` | `volatility_20d` | $\sigma_{20d} \times \sqrt{252}$ | $[0.0, 1.0]$ | 20일 롤링 연율화 변동성 |
| `2` | `log_return` | $\ln(P_t / P_{t-1})$ | $[-0.5, 0.5]$ | 연속 복리 로그 수익률 |
| `3` | `ma_5_dev` | $(P_t - MA_5) / MA_5$ | $[-1.0, 1.0]$ | 5일 단순 이동평균 이격도 |
| `4` | `ma_20_dev` | $(P_t - MA_{20}) / MA_{20}$ | $[-1.0, 1.0]$ | 20일 단순 이동평균 이격도 |
| `5` | `ma_60_dev` | $(P_t - MA_{60}) / MA_{60}$ | $[-1.0, 1.0]$ | 60일 중기 이동평균 이격도 |
| `6` | `dynamic_per` | 주가 / PIT EPS (DART 공시 기준) | $\text{clip}(PER / 50.0, -5.0, 5.0)$ | 일별 동적 주가수익비율 |
| `7` | `dynamic_pbr` | 주가 / PIT BPS (DART 공시 기준) | $\text{clip}(PBR / 5.0, -5.0, 5.0)$ | 일별 동적 주가순자산비율 |
| `8` | `dynamic_market_cap` | 주가 $\times$ 상장주식수 | $\text{clip}(\ln(1 + Cap) / 35.0, 0.0, 2.0)$ | 일별 동적 시가총액 (로그 스케일) |
| `9` | `volume` | 거래량 (체결량) | $\text{clip}(Vol / 1,000,000, 0.0, 50.0)$ | 정규화된 거래량 |
| `10` | `cash_ratio` | 잔여 현금 / 총 평가 에쿼티 | $[0.0, 1.0]$ | 계좌 내 현금 비중 |
| `11` | `position_ratio` | 보유 주식 평가금 / 총 평가 에쿼티 | $[0.0, 1.0]$ | 계좌 내 주식 포지션 비중 |
| `12` | `unrealized_pnl_ratio` | $(P_t - P_{avg}) / P_{avg}$ | $[-2.0, 5.0]$ | 보유 주식의 미실현 손익률 |
| `13` | `step_progress` | $\text{current\_step} / \text{max\_steps}$ | $[0.0, 1.0]$ | 에피소드 진행률 |

- **동적 피처 확장성**: `feature_cols: Optional[List[str]] = None` 매개변수를 지원하여, 사용자 정의 피처 컬럼을 제공하면 `obs_dim = len(feature_cols) + 4` 형태로 자동 확장 가능.
- **결측 방어**: `np.nan_to_num(..., nan=0.0, posinf=1.0, neginf=-1.0)`을 거쳐 모델 입력의 수치 안정성을 보장.

#### C. 보상 함수 및 에피소드 종료 조건
- **보상 (Reward)**:
  $$r_t = \ln\left(\frac{E_t}{E_{t-1}}\right)$$
  - 총 에쿼티(순자산 가치)의 로그 변화율을 사용하여, 포트폴리오 복리 성장률(Geometric Growth)을 최대화하도록 유도.
  - 마찰 비용(위탁수수료 0.015%, 증권거래세 0.18%, 슬리피지 0.1%)이 $E_t$ 계산에 자동 차감 반영되어 오버트레이딩 방지.
- **파산 종료 (Terminated)**:
  $$\text{terminated} = \text{True} \quad \text{if } E_t < E_0 \times 0.05$$
  - 초기 자본금의 5% 미만으로 자산이 축소되면 파산 판정 및 즉시 종료.
- **타임아웃/소진 (Truncated)**:
  - 지정된 `max_steps` 도달 또는 시계열 데이터셋 끝에 도달했을 때 발생.

---

### 2.2 `LiveLearningSimulator` (`modules/engine/live_learning_simulator.py`)

실거래 REST API 및 실시간 모의 트레이딩을 전담하는 시뮬레이터입니다. Phase 5 스크리너와의 연동을 거쳐 다음과 같은 인터페이스를 제공하고 있습니다:

1. `inject_triggered_symbol(symbol, trigger_info)`:
   - 스크리너에서 포착된 모멘텀 돌파 종목을 실시간 활성 풀(`active_pool`) 및 큐(`triggered_queue`)에 등록.
2. `build_rl_observation(symbol, market_features)`:
   - 실시간 시세 및 가상 계좌 정보를 결합하여 `HybridTradingEnv` 규격과 100% 동일한 **14차원 관측 벡터** 생성.
3. `step_symbol(symbol, action, quantity, position_weight)`:
   - 포지션 비중($w$) 또는 수량을 기반으로 지정 종목에 대해 가상 주문을 체결하고 5-tuple `(obs, reward, terminated, truncated, info)` 반환.

---

## 3. Phase 6 R2: 다중 SL 아키텍처 및 Hybrid PPO 연동 설계

### 3.1 다중 지도학습(SL) 아키텍처 명세 및 입력/출력 텐서 규격

Phase 6 R1에서 요구하는 3가지 아키텍처는 **동일한 다중 타임프레임 시계열 텐서**를 입력받아야 합니다.

#### [입력 텐서 규격 (Standardized Input Specification)]
- **다중 타임프레임 시계열 입력 ($X_{temporal}$)**:
  - 텐서 형상: `(Batch, seq_len, in_channels)`
  - 표준 차원: `seq_len = 20` (또는 HPO에 따라 30, 60), `in_channels = 10`
  - 채널 구성: `[returns_1d, volatility_20d, log_return, ma5_dev, ma20_dev, ma60_dev, dynamic_per, dynamic_pbr, dynamic_mcap, volume]`
- **보조 정적/계좌 입력 ($X_{tabular}$, 선택적)**:
  - 텐서 형상: `(Batch, tabular_dim)`
  - 표준 차원: `tabular_dim = 4` (`[cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress]`)

#### [3가지 SL 아키텍처 요약]
```
+-----------------------------------------------------------------------------------+
|                           다중 타임프레임 시계열 텐서 X                           |
|                       (Batch, seq_len=20, in_channels=10)                         |
+-------------------------+-------------------------+-------------------------------+
                          |                         |
                          v                         v
       +------------------------------------+  +------------------------------------+
       |  1. ResNet1DFeatureExtractor       |  |  2. TransformerFeatureExtractor    |
       |  - 1D-CNN 잔차 블록 (Skip Conns)   |  |  - Positional Encoding             |
       |  - GroupNorm + SiLU/ReLU           |  |  - Multi-Head Self Attention       |
       |  - Adaptive Average Pooling        |  |  - Feed-Forward Trans Layer        |
       +-----------------+------------------+  +-----------------+------------------+
                         |                                       |
                         +-------------------+-------------------+
                                             |
                                             v
                       +------------------------------------+
                       |  3. CVAEFeatureExtractor           |
                       |  - Encoder: X -> (mu, log_var)     |
                       |  - Reparameterization z ~ N(mu, s) |
                       |  - Latent Representation z         |
                       |  - Decoder & Reconstruction Loss   |
                       +-----------------+------------------+
                                         |
                                         v
               +---------------------------------------------------+
               |             공통 멀티태스크 출력 헤드             |
               |  - Features: (Batch, feature_dim=64)              |
               |  - Pred Return: (Batch, 1)                        |
               |  - Trend Class Logits / Probs: (Batch, 3)         |
               |  - (CVAE) Anomaly / Recon Loss: (Batch, 1)        |
               +---------------------------------------------------+
```

1. **ResNet1D (`ResNet1DFeatureExtractor`)**:
   - 1D 합성곱 기반 잔차 블록(Residual Block: Conv1d -> GroupNorm -> SiLU -> Conv1d -> GroupNorm + Identity Shortcut).
   - 국소 시계열 특징 보존 및 깊은 신경망에서의 기울기 소실 방지.
2. **Transformer (`TimeSeriesTransformerFeatureExtractor`)**:
   - Sinusoidal 또는 Learnable Positional Encoding 적용 후 Multi-Head Self-Attention(MHA) 블록 2~4개 적층.
   - 시간 축 전반에 걸친 장기 의존성(Long-range Dependencies) 및 시점 간 상관성 추출.
3. **CVAE (`CVAEFeatureExtractor`)**:
   - 시계열 인코더 $q_\phi(z|X, C)$를 통해 잠재 변수 $z$의 평균($\mu$)과 분산($\sigma^2$) 추정.
   - 재매개변수화(Reparameterization Trick)로 잠재 공간 특징 샘플링.
   - 디코더 $p_\theta(X|z, C)$를 통해 원본 시계열 복원 및 복원 오차(Reconstruction Error)를 **이상치 점수(Anomaly Score)**로 산출.

---

### 3.2 하이브리드 RL 결합 설계안 (3대 통합 패턴)

Phase 6 요구사항 R2는 SL 모델의 예측 타겟 값(수익률, 추세 확률 등)을 상태(State)로 편입하여 하이브리드 PPO 에이전트와 완벽히 결합(End-to-End 연결)할 것을 명시합니다.

이를 완벽히 지원하기 위해 **두 가지 상호 보완적인 통합 구조**와 이를 아우르는 **통합 인터페이스**를 설계합니다.

```
=============================================================================================
[결합 구조 1: Prediction-Level State Augmentation (R2 요구사항 직결 - 환경 래퍼 확장)]
=============================================================================================
 시계열 윈도우 X_t (20, 10) ---> [ SL 모델 (ResNet/Transformer/CVAE) ]
                                            |
                                            v
                                 예측 타겟 값 산출 (K=4~5 dims)
                                 - pred_return (1)
                                 - trend_prob_up (1)
                                 - trend_prob_neutral (1)
                                 - trend_prob_down (1)
                                 - [CVAE] anomaly_score (1)
                                            |
                                            v
 [ 원본 환경 관측치 (14 dims) ] + [ SL 예측 타겟 (4~5 dims) ]
                  |
                  v
 [ 확장된 상태 벡터 S_t^{aug} (18 또는 19 dims) ]
                  |
                  v
 [ HybridActorCritic Policy ] ---> Action: (Discrete 3 [HOLD/BUY/SELL], Continuous [Weight])
                  |
                  v
 [ HybridTradingEnv Execution & Accounting ]

=============================================================================================
[결합 구조 2: Feature-Level End-to-End Backbone Integration (특징 수준 직접 전이)]
=============================================================================================
 [ 시계열 텐서 X_temporal ] ---> [ SL Backbone (ResNet / Trans / CVAE) ] ---> Latent Feat (64)
                                                                                     |
 [ 계좌 텐서 X_tabular ]   ---> [ Tabular MLP Extractor ]               ---> Tab Feat (32)
                                                                                     |
                                                                                     v
                                                                        [ Fusion MLP (128->64) ]
                                                                                     |
                                                                                     v
                                                            [ HybridActorCritic Action Heads ]
```

---

### 3.3 상세 인터페이스 명세 (Code-Level Interface Specification)

#### 인터페이스 1: SL 공통 추상 베이스 클래스 (`BaseSLFeatureExtractor`)
`modules/models/feature_extractor.py`에 추가될 표준 클래스 인터페이스:

```python
class BaseSLFeatureExtractor(nn.Module):
    """
    Phase 6 다중 지도학습(SL) 모델의 공통 표준 추상 클래스.
    ResNet, Transformer, CVAE 모델은 모두 본 규격을 준수하여 구현됩니다.
    """
    def __init__(self, in_channels: int = 10, seq_len: int = 20, output_dim: int = 64):
        super().__init__()
        self.in_channels = in_channels
        self.seq_len = seq_len
        self.output_dim = output_dim

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """시계열 텐서 (B, seq_len, in_channels)로부터 고차원 특징 표현 (B, output_dim) 추출"""
        raise NotImplementedError

    def predict_targets(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        RL State 편입용 예측 타겟 값 딕셔너리 반환:
        - "pred_return": Tensor of shape (B, 1)
        - "trend_probs": Tensor of shape (B, 3) (Softmax 확률)
        - "anomaly_score": Tensor of shape (B, 1) (선택적, CVAE 등)
        """
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> Union[torch.Tensor, Tuple[torch.Tensor, ...]]:
        """순전파"""
        raise NotImplementedError
```

#### 인터페이스 2: 상태 확장 트레이딩 환경 래퍼 (`SLEnrichedTradingEnvWrapper`)
`modules/engine/hybrid_trading_env.py`에 추가될 Gymnasium 1.2.0 호환 래퍼:

```python
class SLEnrichedTradingEnvWrapper(gym.Wrapper):
    """
    Gymnasium 1.2.0 호환 SL 예측 기반 관측치 확장 래퍼.
    
    기존 14차원 관측 벡터에 SL 모델(ResNet, Transformer, CVAE)의 예측 타겟
    (익일 예상 수익률 1차원 + 3클래스 추세 확률 3차원 + 이상치 점수 1차원)을
    동적으로 편입하여 (14 + K)차원의 상태 벡터를 생성합니다.
    """
    def __init__(
        self,
        env: HybridTradingEnv,
        sl_model: Optional[BaseSLFeatureExtractor] = None,
        sl_predictions_df: Optional[pd.DataFrame] = None,
        include_anomaly_score: bool = False,
        seq_len: int = 20,
    ):
        super().__init__(env)
        self.sl_model = sl_model
        self.sl_predictions_df = sl_predictions_df
        self.include_anomaly_score = include_anomaly_score
        self.seq_len = seq_len

        # K: 추가되는 SL 피처 차원 수 (기본: 수익률 1 + 추세 확률 3 = 4차원, CVAE 포함 시 5차원)
        self.sl_feature_dim = 5 if include_anomaly_score else 4
        self.base_obs_dim = env.observation_space.shape[0]
        self.augmented_obs_dim = self.base_obs_dim + self.sl_feature_dim

        # Gymnasium 1.2.0 표준 observation_space 확장
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.augmented_obs_dim,),
            dtype=np.float32,
        )

    def _get_sl_targets(self) -> np.ndarray:
        """현재 시점의 시계열 슬라이스로부터 SL 예측 타겟 추출 (추론 또는 사전 계산 캐시)"""
        # 1. 사전 계산된 DataFrame 캐시가 존재하는 경우 (고속 백테스트 모드)
        if self.sl_predictions_df is not None:
            step = min(self.env.unwrapped._current_step, len(self.sl_predictions_df) - 1)
            row = self.sl_predictions_df.iloc[step]
            pred_ret = float(row.get("pred_return", 0.0))
            p_up = float(row.get("prob_up", 0.333))
            p_neutral = float(row.get("prob_neutral", 0.334))
            p_down = float(row.get("prob_down", 0.333))
            targets = [pred_ret, p_up, p_neutral, p_down]
            if self.include_anomaly_score:
                targets.append(float(row.get("anomaly_score", 0.0)))
            return np.array(targets, dtype=np.float32)

        # 2. PyTorch SL 모델 실시간 추론 (온라인 / 라이브 모드)
        if self.sl_model is not None:
            # 환경의 내부 df로부터 최근 seq_len 구간 슬라이스
            window_tensor = self._extract_recent_window()
            with torch.no_grad():
                preds = self.sl_model.predict_targets(window_tensor)
                pred_ret = preds["pred_return"].squeeze().cpu().item()
                trend_probs = preds["trend_probs"].squeeze().cpu().numpy()
                targets = [pred_ret] + trend_probs.tolist()
                if self.include_anomaly_score:
                    anom = preds.get("anomaly_score", torch.zeros(1)).squeeze().cpu().item()
                    targets.append(anom)
            return np.array(targets, dtype=np.float32)

        # 3. 모델 부재 시 기본 제로 패딩
        return np.zeros(self.sl_feature_dim, dtype=np.float32)

    def reset(self, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        base_obs, info = self.env.reset(**kwargs)
        sl_targets = self._get_sl_targets()
        aug_obs = np.concatenate([base_obs, sl_targets]).astype(np.float32)
        info["sl_targets"] = sl_targets
        return aug_obs, info

    def step(self, action: Any) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        base_obs, reward, terminated, truncated, info = self.env.step(action)
        sl_targets = self._get_sl_targets()
        aug_obs = np.concatenate([base_obs, sl_targets]).astype(np.float32)
        info["sl_targets"] = sl_targets
        return aug_obs, reward, terminated, truncated, info
```

---

## 4. `hybrid_policy.py`의 Actor-Critic 및 행동 공간(Action Space) 연계 분석

### 4.1 Actor-Critic 네트워크와의 정합성 검토

`modules/models/hybrid_policy.py`의 `HybridActorCritic`은 이미 매우 유연한 입력 파이프라인을 갖추고 있습니다:
1. **관측 차원 적응성 (`obs_dim`)**:
   - `HybridActorCritic(obs_dim=18)` 또는 `obs_dim=19`로 초기화 시, 첫 번째 MLP 레이어(`Linear(18, hidden_dim)`)가 자동으로 맞춰져 별도의 아키텍처 변경 없이 즉시 작동합니다.
2. **다형적 입력 추출기 (`extract_features`)**:
   - 단일 1D 벡터 `(B, obs_dim)`
   - 2-튜플 `(temporal_x, tabular_x)`
   - 딕셔너리 `{"temporal": ..., "tabular": ...}`
   - 위 3가지 입력 형식을 모두 감지하여 자동 라우팅 및 결합(concatenate)을 수행할 수 있도록 방어 코드가 기 구축되어 있습니다.
3. **가중치 전이 및 고정 (`load_from_sl_pretrainer`, `freeze_backbone`)**:
   - Phase 6에서 사전학습된 SL 가중치를 `HybridActorCritic`의 백본으로 로드하고, `freeze=True`를 통해 RL 정책망 학습 시 SL 특징 추출기를 고정하여 표현 붕괴(Representation Collapse)를 방지할 수 있습니다.

### 4.2 행동 공간(Action Space)과의 연계 방안

PPO 에이전트는 SL 모델의 예측 정보(수익률, 상승 확률, 이상치 점수)와 계좌 상태(현금, 미실현 손익)를 결합 관측한 상태 $S_t$를 기반으로 다음 두 가지 결정을 내립니다:

1. **이산 결정 (Categorical Action)**:
   - 로짓 출력 $\mathbf{z}_{disc} \in \mathbb{R}^3 \to \text{Categorical}(\text{Softmax}(\mathbf{z}_{disc}))$
   - $a_{type} \in \{0: \text{HOLD}, 1: \text{BUY}, 2: \text{SELL}\}$
   - **연계 원리**: SL 모델이 강력한 상승 추세($P_{up} > 0.7$)와 양의 기대수익률을 예측할 경우, PPO 에이전트는 $a_{type}=1$ (BUY)을 적극적으로 선택하도록 정책이 수렴합니다.
2. **연속 비중 결정 (Beta Distribution Continuous Action)**:
   - 형상 모수 $\alpha, \beta = \text{Softplus}(\mathbf{z}_{cont}) + 1.0 \to \text{Beta}(\alpha, \beta) \in (0, 1)$
   - $w \in [0.0, 1.0]$ (가용 현금 대비 매수 비중 또는 보유 주식 대비 매도 비중)
   - **연계 원리**: CVAE의 이상치 점수가 높거나(시장 불확실성 급증), 예측 수익률 대비 변동성이 큰 경우, 에이전트는 비중 $w$를 낮추어 리스크를 능동적으로 축소(Downsizing)합니다.

---

## 5. End-to-End 데이터 흐름 (Data Flow) 맵

전체 시스템을 관통하는 데이터 흐름은 다음과 같은 6단계 파이프라인으로 구조화됩니다:

```
[1. 원천/통합 데이터 레이어]
   - Parquet 스토리지 (OHLCV + DART PIT 펀더멘털 + 기술적 피처)
   - 또는 LiveLearningSimulator 실시간 틱/호가 스트림
             |
             v
[2. 시계열 윈도우 슬라이서]
   - 최근 seq_len=20일의 10개 시장 피처 슬라이싱: X_t in R^{20 x 10}
             |
             v
[3. SL 메인 모델 추론 레이어 (Phase 6 R1)]
   - ResNet1D / Transformer / CVAE 모델 통과
   - 출력: pred_return (1), trend_probs (3), [anomaly_score (1)]
             |
             v
[4. 강화학습 환경 레이어 (Gymnasium 1.2.0)]
   - SLEnrichedTradingEnvWrapper: 원본 14차원 obs + SL 4~5차원 targets
   - 최종 관측 벡터 S_t in R^{18} (또는 R^{19}) 생성
             |
             v
[5. 하이브리드 PPO 정책 레이어 (Phase 6 R2)]
   - HybridActorCritic(obs_dim=18) 순전파
   - Action 샘플링: a_type in {HOLD, BUY, SELL}, weight in [0.0, 1.0]
             |
             v
[6. 가상 체결 및 회계 검증 레이어]
   - MockExecutionEngine 가상 체결 (수수료 0.015%, 세금 0.18%, 슬리피지 0.1%)
   - VirtualAccount 자산 및 포지션 갱신
   - 회계 불변식 검증: Cash + Holdings_Value == Total_Equity (1원 오차 방어)
   - 보상 산출: r_t = ln(E_t / E_{t-1})
   - RolloutBuffer 기록 -> PPO 에포크 최적화 (GAE + Clipped Surrogate Loss)
```

---

## 6. 대규모 HPO 파이프라인 (R3)과의 연계 전략

`modules/hpo/optuna_pipeline.py`와의 정합성 검토 결과, HPO 파이프라인에서 3가지 SL 아키텍처를 원활하게 탐색하기 위해 다음의 인터페이스 확장이 권장됩니다:

1. **아키텍처 스위치 파라미터 제안**:
   ```python
   sl_architecture = trial.suggest_categorical("sl_architecture", ["resnet", "transformer", "cvae"])
   ```
2. **아키텍처별 전용 하이퍼파라미터 분기**:
   - **ResNet**: `res_num_blocks` (1~3), `res_filters` (32, 64), `kernel_size` (3, 5)
   - **Transformer**: `n_heads` (2, 4), `n_layers` (1~3), `dim_feedforward` (64, 128), `dropout` (0.0~0.2)
   - **CVAE**: `latent_dim` (8, 16, 32), `beta_kl` (0.01~1.0, log=True)
3. **원자적 CSV 저장 규격 (`etc/hpo_results/main_models_hpo.csv`)**:
   - Trial 식별자, `sl_architecture`, SL 파라미터, RL 파라미터, Total Return, Sharpe Ratio, MDD, Win Rate 기록.

---

## 7. 결론 및 구현 엔지니어를 위한 권장 사항

1. **Gymnasium 1.2.0 규격 100% 보존**:
   - 관측치 확장은 원본 `HybridTradingEnv` 코드를 무리하게 뜯어고치기보다는, `SLEnrichedTradingEnvWrapper`를 통해 모듈화된 방식으로 래핑하는 것이 기존 39개 테스트 스위트의 회귀(Regression)를 0건으로 유지하는 최선의 접근법입니다.
2. **성능 및 연산 속도 최적화 (Dual-Mode Caching)**:
   - 오프라인 대규모 백테스트 및 HPO 시에는 SL 모델을 스텝마다 PyTorch로 반복 추론하면 속도 병목이 발생할 수 있으므로, 데이터셋 전체에 대해 SL 모델의 추론 결과를 일괄 사전 연산(Batch Inference)한 후 DataFrame 캐시 형태로 환경에 주입하는 패턴을 적극 권장합니다.
3. **SL 가중치 고정(Freeze) 옵션 제공**:
   - PPO 초기 탐색 단계에서 SL 백본이 급격한 정책 변화로 인해 파괴되지 않도록, `freeze_feature_extractor=True` 옵션을 기본값 또는 탐색 변수로 구성할 것을 권장합니다.
