# Auto_Stock ML/RL 파이프라인 및 모델 아키텍처 전수 조사 보고서 (Area 2)

- **조사 일시**: 2026-09-02
- **담당 에이전트**: Explorer Survey Agent 2 (teamwork_preview_explorer_survey_ml_1)
- **대상 모듈**:
  - 데이터 전처리 및 피처 엔지니어링: `modules/data/consolidator.py`, `modules/data/collector_price.py`, `modules/data/pipeline.py`
  - 강화학습 환경: `modules/engine/hybrid_trading_env.py`, `modules/engine/live_learning_simulator.py`, `modules/engine/mock_environment.py`
  - 지도학습 특징 추출기: `modules/models/feature_extractor.py`
  - 하이브리드 강화학습 정책망: `modules/models/hybrid_policy.py`
  - HPO 및 성과 평가 지표: `modules/hpo/metrics.py`, `modules/hpo/optuna_pipeline.py`, `modules/hpo/exporter.py`, `scripts/run_hpo.py`

---

## 1. 전수 조사 요약 (Executive Summary)

Auto_Stock 프로젝트의 머신러닝/강화학습(ML/RL) 시스템은 Gymnasium 1.2.0 호환 하이브리드 트레이딩 환경(`HybridTradingEnv`), 1D-CNN + MLP 기반의 이중 스트림 지도학습 특징 추출기(`DualStreamSLFeatureExtractor`), Categorical(3) + Beta/Gaussian([0, 1]) 하이브리드 액션 공간을 지원하는 `HybridActorCritic` / `HybridPPO`, 그리고 Optuna 기반의 HPO 파이프라인으로 구성되어 있습니다.

본 전수 조사에서는 다음의 5대 핵심 영역에 대해 심층 코드 분석 및 정적/동적 검증을 수행하였습니다:
1. **데이터 전처리 & 피처 파이프라인**: Lookahead bias 차단 여부, 정규화/스케일링 수치 안정성, 결측치 방어 메커니즘
2. **강화학습 환경(Gym Env) 설계**: Observation Space, Action Space 디코더, Step 시계열 인덱싱, Done/Truncated 조건
3. **보상 함수(Reward Function) 설계**: Log Equity Return vs Simple Return 일관성, 희소 보상 및 보상 해킹 취약점
4. **모델 아키텍처 및 학습 알고리즘**: GAE(Generalized Advantage Estimation) 수치 무결성, 텐서 차원 불일치 방어, CPU/CUDA 디바이스 일관성
5. **모델 서빙 및 실시간 추론 연동**: `LiveLearningSimulator` 인터페이스 정합성, SB3 연속형 액션 어댑터 디코딩 다형성

---

## 2. 발견된 주요 결함 및 상세 분석 (Defect Catalog)

### [결함 1] `HybridTradingEnv` 관측값 스텝 인덱싱 지연 및 최초 관측값 중복 (Observation Time-Lag & Duplication Bug)
- **심각도**: **High (구조적 결함)**
- **위치**: `modules/engine/hybrid_trading_env.py` (Line 470-471)
- **코드 스니펫**:
  ```python
  # modules/engine/hybrid_trading_env.py (Line 470)
  def _get_observation(self) -> np.ndarray:
      ...
      if self.mode == "offline" and self.df is not None and len(self.df) > 0:
          idx = min(max(0, self._current_step - 1), len(self.df) - 1)
          row = self.df.iloc[idx]
  ```
- **원인 분석**:
  1. `reset()` 호출 시 `self._current_step = 0` 상태에서 `_get_observation()`이 호출되어 `idx = max(0, 0 - 1) = 0` (0번째 행)의 피처가 관측값으로 반환됩니다.
  2. 첫 번째 `step(action)` 실행 시, 가격 `df.iloc[0]`에서 주문이 체결되고 난 후 `self._current_step += 1`로 증가합니다 (`_current_step = 1`).
  3. 직후 `step()` 내부에서 반환할 `next_obs`를 생성하기 위해 `_get_observation()`을 호출하면 `idx = max(0, 1 - 1) = 0` (또다시 0번째 행)의 피처가 반환됩니다!
  4. 따라서 에이전트는 `reset` 시점과 `step(0)` 완료 시점에 **동일한 0번째 행 관측값을 2회 연속 수신**하게 되며, 이후 모든 스텝 $t \ge 1$에서 에이전트는 $t-1$ 시점의 과거 피처를 보고 $t$ 시점의 가격으로 거래하게 되는 **1-스텝 관측 지연(Lag)**이 발생합니다.
  5. 또한 마지막 행 `len(df) - 1`의 피처는 `_current_step >= len(df)`로 인해 환경이 `truncated`되면서 에이전트의 의사결정에 단 한 번도 사용되지 못하고 버려집니다.
- **권장 수정안**:
  ```python
  # 수정 후:
  idx = min(self._current_step, len(self.df) - 1)
  row = self.df.iloc[idx]
  ```

---

### [결함 2] CPU/CUDA 디바이스 불일치 런타임 에러 (Cross-Device Runtime Mismatch)
- **심각도**: **High (실행 에러)**
- **위치**: `modules/models/feature_extractor.py` (Line 154-156, 281-283), `modules/models/hybrid_policy.py` (Line 196-198)
- **코드 스니펫**:
  ```python
  # modules/models/feature_extractor.py (Line 154)
  if isinstance(x, np.ndarray):
      x = torch.as_tensor(x, dtype=torch.float32, device=device)
  is_unbatched = x.dim() == 1
  ```
  ```python
  # modules/models/hybrid_policy.py (Line 196)
  device = next(self.parameters()).device if list(self.parameters()) else torch.device("cpu")
  if isinstance(obs, np.ndarray):
      obs = torch.as_tensor(obs, dtype=torch.float32, device=device)
  ```
- **원인 분석**:
  1. 모델(`TabularMLPFeatureExtractor`, `Temporal1DCNNFeatureExtractor`, `HybridActorCritic`)이 CUDA 디바이스(`model.to("cuda")`)로 이동된 상태에서, 외부 DataLoader나 호출자가 CPU 상의 `torch.Tensor`를 전달할 경우 `isinstance(..., np.ndarray)`가 `False`가 되어 디바이스 변환(`x.to(device)`)이 누락됩니다.
  2. 이후 내부 PyTorch 레이어(예: `nn.Linear`, `nn.Conv1d`)와 연산 시 `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cpu and cuda:0!`이 발생합니다.
- **권장 수정안**:
  ```python
  # 수정 후 (feature_extractor.py & hybrid_policy.py):
  if isinstance(x, np.ndarray):
      x = torch.as_tensor(x, dtype=torch.float32, device=device)
  elif isinstance(x, torch.Tensor):
      x = x.to(device=device, dtype=torch.float32)
  ```

---

### [결함 3] `LiveLearningSimulator`와 `HybridTradingEnv` 간 Step 인터페이스 및 보상 함수 불일치
- **심각도**: **Medium (아키텍처 불일치)**
- **위치**: `modules/engine/live_learning_simulator.py` (Line 67, 120, 134) vs `modules/engine/hybrid_trading_env.py` (Line 365, 428, 459)
- **코드 스니펫**:
  ```python
  # modules/engine/live_learning_simulator.py
  def step(self, symbol: str, action: Union[int, ActionType], quantity: int = 1) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
      ...
      reward = float((curr_equity - self._prev_equity) / self._prev_equity) if self._prev_equity > 0 else 0.0
      ...
      return state, reward, done, info  # Legacy Gym 4-tuple
  ```
  ```python
  # modules/engine/hybrid_trading_env.py
  def step(self, action: Any) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
      ...
      reward = float(np.log(float(curr_equity) / float(self._prev_equity)))
      ...
      return obs, reward, terminated, truncated, info  # Gymnasium 1.2.0 5-tuple
  ```
- **원인 분석**:
  1. `HybridTradingEnv`는 최신 Gymnasium 1.2.0 규격의 5-tuple `(obs, reward, terminated, truncated, info)`과 Log Return $\ln(E_t / E_{t-1})$을 사용하는 반면, `LiveLearningSimulator`는 과거 Gym 규격의 4-tuple `(state, reward, done, info)`과 단순 수익률 $(E_t - E_{t-1})/E_{t-1}$을 사용합니다.
  2. 오프라인에서 `HybridTradingEnv`로 학습된 RL 정책망(`HybridPPO`, SB3)을 `LiveLearningSimulator`에 직접 연결할 경우 반환값 튜플 길이(4 vs 5) 및 보상 스케일 불일치로 인해 추론/학습 파이프라인이 중단될 수 있습니다.
- **권장 수정안**:
  `LiveLearningSimulator`에 Gymnasium 1.2.0 호환 어댑터 또는 5-tuple 반환 모드를 도입하고, 보상 계산식을 Log Return으로 표준화.

---

### [결함 4] `DataConsolidator` 분기/사업보고서 공시 기한 가정 차이로 인한 Lookahead Bias 잠재 위험
- **심각도**: **Medium (데이터 무결성)**
- **위치**: `modules/data/consolidator.py` (Line 112-113)
- **코드 스니펫**:
  ```python
  if 'announcement_date' not in f_df.columns:
      if 'period_end' in f_df.columns:
          # 공시일자가 없는 경우 분기말 + 45일 추정
          f_df['announcement_date'] = pd.to_datetime(f_df['period_end']) + pd.Timedelta(days=45)
  ```
- **원인 분석**:
  1. 자본시장법상 분기/반기 보고서의 제출 기한은 분기말 경과 후 45일 이내이나, 결산 사업보고서(12월 결산법인의 4분기/연간 보고서)는 결산 후 **90일 이내**에 공시됩니다.
  2. 연간 재무제표에 대해 일괄적으로 +45일로 공시일을 추정할 경우, 12월 31일 결산 데이터가 익년 2월 14일에 공시된 것으로 처리되어 실제 공시 전(3월 말 전)에 미래 재무 정보가 주가에 매핑되는 **Lookahead bias**가 발생할 수 있습니다.
- **권장 수정안**:
  ```python
  # 수정 후:
  def estimate_announcement_date(row):
      dt = pd.to_datetime(row['period_end'])
      # 12월 결산(연간)인 경우 90일, 기타 분기(3/6/9월)는 45일 추정
      days = 90 if dt.month == 12 else 45
      return dt + pd.Timedelta(days=days)
  f_df['announcement_date'] = f_df.apply(estimate_announcement_date, axis=1)
  ```

---

### [결함 5] Optuna HPO 목적 함수에서 무거래(Zero-Action) 정책 우대 현상 (Zero Return Preference)
- **심각도**: **Low ~ Medium (하이퍼파라미터 튜닝 편향)**
- **위치**: `modules/hpo/optuna_pipeline.py` (Line 254-256)
- **코드 스니펫**:
  ```python
  sr = float(metrics["sharpe_ratio"])
  objective_value = sr if not (math.isnan(sr) or math.isinf(sr)) else 0.0
  ```
- **원인 분석**:
  1. 100% 현금만 보유하고 단 한 번도 매수하지 않은 정책(No-op)은 수익률의 표준편차가 0이므로 `metrics["sharpe_ratio"] = 0.0`을 반환합니다.
  2. 반면, 적극적으로 시장에 참여하여 약간의 손실(예: -0.2%)을 기록한 정책은 음의 샤프 지수(예: -0.5)를 반환합니다.
  3. 결과적으로 Optuna의 TPE Sampler는 적극적으로 탐색하는 정책보다 아무것도 하지 않는(거래수 0) 정책을 더 우수한 Trial로 평가하여 무거래 정책으로 수렴할 수 있는 인센티브 왜곡(Reward/Objective Hacking)이 발생합니다.
- **권장 수정안**:
  목적 함수에 최소 거래 횟수 패널티 또는 총 수익률 복합 가중치를 부여:
  ```python
  if metrics["total_trades"] == 0:
      objective_value = -1.0  # 무거래 정책에 대한 탐색 패널티
  else:
      objective_value = sr + 0.01 * float(metrics["total_return_pct"])
  ```

---

### [결함 6] `SB3HybridPolicyAdapter.predict_hybrid` 반환 타입 다형성(Type Ambiguity)
- **심각도**: **Low (타입 안정성)**
- **위치**: `modules/models/hybrid_policy.py` (Line 854-874)
- **코드 스니펫**:
  ```python
  if raw_action.ndim == 2:
      ...
      return hybrid_actions, raw_action  # List[Tuple[int, float]]
  ...
  return (act_type, weight), raw_action  # Tuple[int, float]
  ```
- **원인 분석**:
  입력 `obs`가 단일 관측값(`ndim == 1`)인지 배치(`ndim == 2`)인지에 따라 첫 번째 반환값의 타입이 `Tuple[int, float]` 또는 `List[Tuple[int, float]]`로 달라집니다. 특히 배치 크기가 1인 2D 텐서 `(1, 14)`를 전달할 경우 `[(act_type, weight)]`가 반환되어, `(act, weight) = predict_hybrid(...)` 형태의 단일 언패킹을 수행하는 호출자에서 런타임 오류가 발생할 수 있습니다.
- **권장 수정안**:
  `raw_action.shape[0] == 1`일 때는 항상 단일 튜플 `(act_type, weight)`를 반환하도록 정규화.

---

### [결함 7] 적대적 테스트 스위트의 GAE 오라클 인덱싱 오류 (Test Oracle Indexing Flaw)
- **심각도**: **Low (테스트 코드 결함)**
- **위치**: `tests/test_adversarial_m2_rl_challenger.py` (Line 207, 309)
- **코드 스니펫**:
  ```python
  next_non_terminal = 1.0 - float(dones[t + 1])
  ```
- **원인 분석**:
  1. `RolloutBuffer`에서 스텝 $t$에 저장된 `dones[t]`는 전이 $(s_t, a_t, r_t, s_{t+1}, d_t)$에서 스텝 $t$가 에피소드를 종료시켰는지 여부입니다.
  2. 따라서 $s_t$에서 다음 상태 가치 $V(s_{t+1})$을 부트스트랩할 때 비종료 계수는 $(1 - d_t)$이어야 하며, `RolloutBuffer` 구현은 `1.0 - self.dones[step]`으로 수학적으로 정확합니다.
  3. 그러나 `test_adversarial_m2_rl_challenger.py`의 테스트 검증용 독립 오라클 함수가 `dones[t + 1]`을 참조하여 계산하도록 작성되어 있어, 정상 구현에 대해 불일치(AssertionError)를 발생시켰습니다.
- **권장 수정안**:
  `tests/test_adversarial_m2_rl_challenger.py`의 `_ground_truth_gae` 및 `test_gae_lambda_zero_is_exact_td_error`에서 `dones[t + 1]`을 `dones[t]`로 수정.

---

## 3. 영역별 상세 검증 및 아키텍처 평가

| 평가 영역 | 상태 | 주요 검증 내용 |
|---|:---:|---|
| **1. Feature Engineering** | 양호 (개선 권장) | Point-in-Time 병합(`merge_asof backward`)으로 Lookahead bias 원천 차단 확인. 단, `HybridTradingEnv._get_observation()`의 스텝 인덱싱 지연 수정 필요. |
| **2. Gym Environment** | 우수 | Gymnasium 1.2.0 `check_env` 100% 통과, 1원 단위 정밀 회계 및 회계 불변식(0원 오차) 유지 확인. |
| **3. Reward Function** | 우수 | Log Equity Return $\ln(E_t / E_{t-1})$의 시간 가산성 및 스케일 불변성 확인. 마이너 거래 비용 반영으로 Churning/Reward Hacking 억제. |
| **4. RL Algorithm & Buffer** | 우수 (디바이스 보강 필요) | PPO Clipped Surrogate, Beta 분포 포지션 사이징([0, 1]), GAE 계산 수학적 건전성 검증 완료. CPU/CUDA 디바이스 자동 전환 로직 보강 필요. |
| **5. HPO Pipeline & Storage** | 우수 | Optuna TPESampler/MedianPruner 연동, `fcntl.flock` 기반 프로세스 락 및 20개 컬럼 원자적 CSV 저장 완비. |

---

## 4. 결론 및 리팩토링 권고사항

1. **`HybridTradingEnv._get_observation()` 인덱싱 수정**:
   `idx = min(self._current_step, len(self.df) - 1)`로 수정하여 1-스텝 지연 및 초기 상태 중복 문제를 즉시 해소할 것.
2. **PyTorch 디바이스 자동 캐스팅 추가**:
   `feature_extractor.py` 및 `hybrid_policy.py`의 모든 입력 진입점에 `elif isinstance(x, torch.Tensor): x = x.to(device)`를 추가하여 CUDA 실행 시 디바이스 불일치 충돌을 원천 방지할 것.
3. **`LiveLearningSimulator` 규격 동기화**:
   Gymnasium 1.2.0 5-tuple 및 Log Return 기반으로 인터페이스를 일원화하여 실시간 학습 모드 전환 시의 호환성을 보장할 것.
4. **HPO 목적 함수에 무거래 패널티 도입**:
   아무것도 하지 않는 정책(0-분산 0.0 샤프)이 음수 샤프 정책보다 항상 우선시되는 현상을 방지하기 위해 최소 거래 수 보너스 또는 총수익률 정규화 항을 결합할 것.
