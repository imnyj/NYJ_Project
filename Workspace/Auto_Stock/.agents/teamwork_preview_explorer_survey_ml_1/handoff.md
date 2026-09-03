# Handoff Report — Explorer Survey Agent 2 (ML/RL Pipeline & Architecture)

## 1. Observation (관측 사실)

### 1.1 `HybridTradingEnv` 관측값 스텝 인덱싱 지연 및 최초 관측값 중복
- **파일 및 라인**: `modules/engine/hybrid_trading_env.py:470`
- **실제 코드**:
  ```python
  idx = min(max(0, self._current_step - 1), len(self.df) - 1)
  row = self.df.iloc[idx]
  ```
- **관측 내용**:
  - `reset()` 시점(`self._current_step == 0`): `idx = max(0, 0 - 1) = 0` (0번째 행 반환).
  - `step(0)` 완료 시점(`self._current_step`이 1로 증가): `idx = max(0, 1 - 1) = 0` (또다시 0번째 행 반환).
  - 에이전트는 0번째 행 관측값을 2회 연속 수신하며, $t \ge 1$에서 $t-1$ 시점의 피처를 관측하여 $t$ 시점의 주가로 거래하는 1-스텝 지연 현상이 발생함.

### 1.2 PyTorch 특징 추출기 및 정책망의 CPU/CUDA 디바이스 불일치
- **파일 및 라인**: `modules/models/feature_extractor.py:154-156, 281-283`, `modules/models/hybrid_policy.py:196-198`
- **실제 코드**:
  ```python
  # feature_extractor.py (Line 154)
  if isinstance(x, np.ndarray):
      x = torch.as_tensor(x, dtype=torch.float32, device=device)
  is_unbatched = x.dim() == 1
  ```
- **관측 내용**:
  - `x`가 CPU 상의 `torch.Tensor`인 경우 `isinstance(x, np.ndarray)`가 `False`가 되어 디바이스 전환(`x.to(device)`)이 누락됨.
  - 모델이 CUDA에 있을 때 CPU 텐서가 입력되면 `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cpu and cuda:0!` 발생.

### 1.3 `LiveLearningSimulator`와 `HybridTradingEnv` 간 Step 인터페이스 및 보상 함수 불일치
- **파일 및 라인**: `modules/engine/live_learning_simulator.py:67, 120, 134` vs `modules/engine/hybrid_trading_env.py:365, 428, 459`
- **관측 내용**:
  - `LiveLearningSimulator.step()`은 `(state, reward, done, info)` 4-tuple 및 Simple Return `(E_t - E_{t-1})/E_{t-1}` 반환.
  - `HybridTradingEnv.step()`은 `(obs, reward, terminated, truncated, info)` 5-tuple 및 Log Return `ln(E_t / E_{t-1})` 반환.

### 1.4 `DataConsolidator` 연간 사업보고서 공시 기한 가정(45일)에 따른 Lookahead Bias 잠재 위험
- **파일 및 라인**: `modules/data/consolidator.py:112-113`
- **관측 내용**:
  - `announcement_date`가 없는 경우 일괄적으로 `period_end + 45 days`를 부여함.
  - 12월 결산 사업보고서의 법정 공시 기한은 90일이므로, 연간 재무제표에 대해 45일을 적용하면 실제 공시 전(2월 중순~3월 말 사이)에 미래 데이터가 누수될 수 있음.

### 1.5 Optuna HPO 목적 함수에서 무거래 정책 우대
- **파일 및 라인**: `modules/hpo/optuna_pipeline.py:254-256`
- **관측 내용**:
  - 무거래(100% 현금 유지) 정책은 수익률 분산이 0이므로 `sharpe_ratio = 0.0` 반환.
  - 소액 손실을 기록한 적극적 탐색 정책(음의 샤프 지수, 예: -0.5)보다 무거래 정책(0.0)이 더 높은 점수로 평가되는 인센티브 왜곡 발생.

### 1.6 테스트 스위트 내 GAE 오라클 인덱싱 오류
- **파일 및 라인**: `tests/test_adversarial_m2_rl_challenger.py:207, 309`
- **관측 내용**:
  - 테스트의 `_ground_truth_gae` 함수가 `dones[t + 1]`을 사용하여 $t+1$ 시점을 검사함으로써, 정상 동작하는 `RolloutBuffer`(`1.0 - dones[step]`)에 대해 5건의 `AssertionError`를 유발함.

---

## 2. Logic Chain (추론 단계)

1. **[인과 1: 인덱싱 지연]**: `HybridTradingEnv`가 `_current_step` 증가 직후 `_current_step - 1`을 조회하도록 설계되었으나, `reset()` 시점에서도 `max(0, 0 - 1) = 0`을 조회하므로 0번째 행이 2번 사용됨 → 시계열 1-스텝 지연 발생.
2. **[인과 2: 디바이스 에러]**: `isinstance(x, np.ndarray)` 조건문만 존재하여 `torch.Tensor`가 입력될 경우 `.to(device)`가 호출되지 않음 → 멀티 GPU / CUDA 환경에서 런타임 에러 불가피.
3. **[인과 3: 모드 전환 결함]**: `mode="live"` 시 `HybridTradingEnv`는 `LiveLearningSimulator`를 감싸지만, `LiveLearningSimulator`의 단독 `step()` 메서드는 레거시 4-tuple 규격이어서 외부 RL 프레임워크(SB3 등)와의 직접 호환이 불가능함.
4. **[인과 4: 미래 데이터 누수]**: 12월 결산 상장사의 사업보고서 제출 기한(90일)을 무시하고 45일로 일괄 추정할 경우, 미공시 상태의 4분기/연간 실적이 주가 시계열에 조기 반영되어 백테스트 성과가 과대평가됨.
5. **[인과 5: HPO 탐색 왜곡]**: 샤프 지수 0-분산 방어 로직이 0.0을 반환하도록 되어 있어, TPE Sampler가 손실 위험을 회피하는 '아무것도 하지 않는 정책'에 높은 가중치를 부여하게 됨.

---

## 3. Caveats (한계 및 가정)

- **조사 모드**: Read-Only Explorer 조사로 직접 소스 코드 수정은 수행하지 않았으며, 모든 제안은 Before/After 코드 스니펫 및 권고안 형태로 제시함.
- **네트워크 환경**: 키움 Open API 실서버 호출은 오프라인/모의 환경이므로 Mock 및 합성 데이터를 기반으로 검증함.
- **적대적 테스트**: `tests/test_adversarial_m2_rl_challenger.py`의 5개 실패는 소스 코드 결함이 아닌 테스트 오라클 인덱싱 오류(`dones[t + 1]`)로 확인됨.

---

## 4. Conclusion (최종 결론)

Auto_Stock 프로젝트의 ML/RL 파이프라인(Area 2)은 전반적으로 Gymnasium 1.2.0 규격 준수, 하이브리드 액션 공간(이산 + 연속) 처리, 1원 단위 정밀 가상 체결 및 fcntl 프로세스 락 기반 HPO 내보내기 등 높은 수준의 엔지니어링 완성도를 갖추고 있습니다.

그러나 다음 3대 주요 항목에 대한 리팩토링이 필수적입니다:
1. **`hybrid_trading_env.py`의 관측값 인덱싱 지연 수정** (`idx = min(self._current_step, len(self.df) - 1)`).
2. **`feature_extractor.py` 및 `hybrid_policy.py`의 PyTorch CPU/CUDA 디바이스 자동 전환 보강**.
3. **`consolidator.py`의 공시일자 추정(결산월별 45일/90일 차등화) 및 Optuna 목적 함수의 무거래 패널티 도입**.

상세 보고서는 `analysis.md`에 전수 정리되어 있습니다.

---

## 5. Verification Method (검증 방법)

### 5.1 전체 ML/RL 테스트 스위트 실행
```bash
/home/imnyj/venv/bin/pytest tests/test_models.py tests/test_hpo_pipeline.py tests/test_hybrid_trading_env.py tests/test_hybrid_env_gym_seeding_sb3.py tests/test_hybrid_env_stress.py tests/test_hpo.py tests/test_m2_models_adversarial.py -v
```

### 5.2 HPO CLI 서브프로세스 3-Trial E2E 검증
```bash
/home/imnyj/venv/bin/python3 scripts/run_hpo.py --n-trials 3 --symbol 005930 --output etc/hpo_results/baseline_hpo.csv --seed 42 --fast-mode
```

### 5.3 생성된 결과물 파일 확인
- 분석 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_ml_1/analysis.md`
- 핸드오프 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_ml_1/handoff.md`
