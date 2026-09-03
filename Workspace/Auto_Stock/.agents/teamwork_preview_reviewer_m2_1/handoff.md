# Milestone 2 독립 코드 리뷰 및 적대적 평가 보고서 (Handoff Report)

- **Reviewer**: `teamwork_preview_reviewer_m2_1` (독립 코드 리뷰어 1)
- **Roles**: reviewer, critic
- **Verdict**: **`REQUEST_CHANGES`** (수정 요청)
- **Target Files**:
  - `modules/models/feature_extractor.py`
  - `modules/models/hybrid_policy.py`
  - `tests/test_models.py`

---

## 1. Observation (직접 관찰 결과)

### 1.1 무결성(Integrity) 검증 결과
- 하드코딩된 테스트 기대값이나 결과치 우회 코드 없음 (Pass).
- 실질적인 PyTorch 신경망 역전파, 오토그라드 연산 및 손실 최적화가 정상 구현됨 (Pass).
- 단위 테스트 및 통합 테스트 31개 항목 정상 수집 및 통과 (`tests/test_models.py` 18개, `tests/test_hybrid_trading_env.py` 13개).
- 코드 커버리지: `modules/models/` 90% 달성 (842 statements 중 88 missing).

### 1.2 관찰된 치명적 결함 및 에러 관찰 내역

#### [Observation 1.2.1] GAE 계산 시 `dones` 인덱스 오프셋 오차 (Critical Defect)
- **위치**: `modules/models/hybrid_policy.py`, Line 437
- **코드**:
  ```python
  def compute_returns_and_advantages(
      self,
      last_value: float,
      last_done: bool,
      gamma: float = 0.99,
      gae_lambda: float = 0.95,
  ) -> None:
      last_gae = 0.0
      for step in reversed(range(self.ptr)):
          if step == self.ptr - 1:
              next_non_terminal = 1.0 - float(last_done)
              next_value = float(last_value)
          else:
              next_non_terminal = 1.0 - self.dones[step + 1]  # <--- 결함 발생 지점
              next_value = self.values[step + 1]

          delta = self.rewards[step] + gamma * next_value * next_non_terminal - self.values[step]
          last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
          self.advantages[step] = last_gae
  ```
- **직접 실행 관찰**:
  - `RolloutBuffer.add()` 시점에 `self.dones[ptr] = float(done)`이 트랜지션 직후 저장되므로, `dones[step]`이 이미 해당 트랜지션의 에피소드 종료 여부를 담고 있습니다.
  - 하지만 역방향 루프에서 `1.0 - self.dones[step + 1]`을 참조함으로써, 트랜지션 `step`의 에피소드 종료 여부가 아닌 **다음 트랜지션(`step + 1`)의 종료 여부**로 마스킹됩니다.
  - 결과: 에피소드가 종료되는 스텝(`dones[1]=1`)에서 `next_non_terminal`이 0이 되지 않고 1이 되어 다음 에피소드의 시작 가치($V_2$)와 GAE가 이전 에피소드로 역방향 누수(Leakage)되며, 반대로 종료 직전 스텝(`dones[0]=0`)은 `dones[1]=1`에 의해 조기 절단(Premature truncation)되어 $V_1$이 0으로 날아갑니다.

#### [Observation 1.2.2] 배치 크기가 `seq_len`과 일치할 때 2D 텐서 형상 오인식 및 RuntimeError (Major Defect)
- **위치**: `modules/models/feature_extractor.py`, Line 262 및 Line 453
- **코드**:
  ```python
  # feature_extractor.py: Line 261-264
  elif x.dim() == 2:
      if x.shape[0] == self.seq_len and x.shape[1] == self.in_channels:
          x = x.unsqueeze(0).transpose(1, 2)  # (1, in_channels, seq_len)
          is_unbatched = True
  ```
- **직접 실행 에러 관찰**:
  - `batch_size == seq_len`인 2D 평탄화 텐서(예: `batch_size = 20`, `tot_dim = 14`, `temporal_in_channels = 10`)가 `DualStreamSLFeatureExtractor`로 들어오는 경우:
  - `Temporal1DCNNFeatureExtractor`가 `(20, 10)`을 20개 샘플의 배치가 아닌 단일 시계열 시퀀스 `(seq_len, in_channels)`로 오인식하여 1D 텐서 `(64,)`를 반환합니다.
  - 반면 `TabularMLPFeatureExtractor`는 정상적으로 `(20, 32)`를 반환합니다.
  - 결과적으로 Line 453 `torch.cat([feat_temp, feat_tab], dim=-1)`에서 다음 치명적 예외가 발생합니다:
    ```text
    RuntimeError: Sizes of tensors must match except in dimension 1. Expected size 1 but got size 20 for tensor number 1 in the list.
    ```

---

## 2. Logic Chain (논리 추론 체계)

```
[Observation 1.1: M2 구현물 및 단위 테스트 통과 (31 passed, 90% coverage)]
       │
       ▼ (Step 1: 심층 코드 감사 및 수학적 알고리즘 검증)
  - SL 특징 추출기(MLP, 1D-CNN, DualStream) 및 RL 정책(HybridActorCritic, HybridPPO, SB3 Adapter)의
    전반적인 아키텍처는 Gymnasium 및 PyTorch 표준을 준수함.
       │
       ▼ (Step 2: 적대적 엣지 케이스 및 GAE 수학적 정합성 스트레스 테스트)
  - [Observation 1.2.1] CleanRL의 사전 저장(Pre-step storage) 방식과 달리 RolloutBuffer.add()는
    사후 저장(Post-step storage) 방식을 사용함. 따라서 `dones[step + 1]`은 한 스텝 밀려 에피소드 경계
    마스킹이 완전히 왜곡됨.
  - [Observation 1.2.2] HPO 또는 배치 추론 시 배치 크기가 `seq_len` (기본 20)과 동일할 때
    `DualStreamSLFeatureExtractor`가 `RuntimeError`를 일으키며 크래시 발생.
       │
       ▼ (Step 3: 최종 판정 도출)
  - 강화학습의 정책 경사(Policy Gradient) 왜곡과 HPO 파이프라인 중단 위험이 존재하므로,
    코드 수정을 요청(`REQUEST_CHANGES`)함.
```

---

## 3. Findings (검토 세부 지적 사항)

### [Critical] Finding 1: RolloutBuffer GAE 계산 시 `dones` 인덱스 오프셋 버그

- **대상 파일**: `modules/models/hybrid_policy.py:437`
- **문제점**:
  `compute_returns_and_advantages` 루프 내에서 `next_non_terminal = 1.0 - self.dones[step + 1]`로 작성되어 있습니다. `self.dones[step]`이 해당 트랜지션의 `done` 상태를 담고 있으므로 `step + 1`을 조회하면 미래 트랜지션의 `done` 플래그로 현재 트랜지션의 벨만 오차($\delta_t$) 및 어드밴티지가 계산됩니다.
- **수정 제안**:
  `next_non_terminal`을 모든 `step`에 대해 `1.0 - self.dones[step]`으로 수정해야 합니다:
  ```python
  # 권장 수정안
  def compute_returns_and_advantages(
      self,
      last_value: float,
      last_done: bool,
      gamma: float = 0.99,
      gae_lambda: float = 0.95,
  ) -> None:
      last_gae = 0.0
      for step in reversed(range(self.ptr)):
          if step == self.ptr - 1:
              next_non_terminal = 1.0 - float(last_done)
              next_value = float(last_value)
          else:
              next_non_terminal = 1.0 - self.dones[step]
              next_value = self.values[step + 1]

          delta = self.rewards[step] + gamma * next_value * next_non_terminal - self.values[step]
          last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
          self.advantages[step] = last_gae

      self.returns[:self.ptr] = self.advantages[:self.ptr] + self.values[:self.ptr]
  ```

---

### [Major] Finding 2: `Temporal1DCNNFeatureExtractor` 2D 입력 형상 판별 모호성 및 `DualStream` 배치 크래시

- **대상 파일**: `modules/models/feature_extractor.py:261-274`
- **문제점**:
  `Temporal1DCNNFeatureExtractor.forward()`에서 2D 텐서가 들어올 때 `x.shape[0] == self.seq_len` 조건을 단일 시퀀스로 간주하여 unbatched 처리합니다. 이로 인해 배치 크기가 우연히 `seq_len`과 같은 2D 관측값 배치(`B, in_channels`)가 들어오면 배치 차원이 증발하여 `DualStreamSLFeatureExtractor`에서 `torch.cat` 차원 불일치 `RuntimeError`가 발생합니다.
- **수정 제안**:
  2D 텐서 처리 시 관측 벡터 `(B, in_channels)`와 단일 시계열 `(seq_len, in_channels)`의 모호성을 방지하도록 차원 변환 로직을 명확히 정돈하거나, 평탄화된 관측값 입력 시 `(B, in_channels, 1)` 형태로 일관되게 처리하도록 수정해야 합니다.

---

### [Minor] Finding 3: Stable-Baselines3 GPU 알림 경고 (UserWarning)

- **대상 파일**: `modules/models/hybrid_policy.py:791`
- **문제점**:
  SB3 PPO 정책을 GPU 환경에서 기본 실행 시 `UserWarning: You are trying to run PPO on the GPU, but it is primarily intended to run on the CPU when not using a CNN policy` 경고가 발생합니다.
- **수정 제안**:
  SB3 PPO 생성 시 필요에 따라 `device='cpu'` 옵션을 기본 파라미터로 두거나 전달할 수 있도록 유연성을 보장하는 것을 권장합니다.

---

## 4. Verified Claims (검증 완료 항목)

| 검증 항목 | 검증 방법 | 결과 |
|---|---|---|
| **SL 활성화 함수 팩토리** | `pytest tests/test_models.py -k test_activation_function_factory` | Pass |
| **TabularMLP 순전파/역전파/잔차연결** | `pytest tests/test_models.py -k test_tabular_mlp` | Pass |
| **Temporal1DCNN 3종 풀링 및 순전파** | `pytest tests/test_models.py -k test_temporal_1dcnn` | Pass |
| **SLPretrainer 멀티태스크 학습 및 저장/로드** | `pytest tests/test_models.py -k test_sl_pretrainer` | Pass |
| **HybridActorCritic Beta/Gaussian 샘플링** | `pytest tests/test_models.py -k test_hybrid_actor_critic` | Pass |
| **Actor-Critic 가중치 고정 및 SL 전이** | `pytest tests/test_models.py -k test_sl_to_rl_weight_transfer` | Pass |
| **SB3 커스텀 특징 추출기 및 어댑터 연동** | `pytest tests/test_models.py -k test_sb3` | Pass |
| **코드 커버리지** | `coverage run ... && coverage report -m` (90% Total) | Pass |
| **하이브리드 환경 전수 테스트 (31개)** | `pytest tests/test_models.py tests/test_hybrid_trading_env.py` | Pass (100%) |

---

## 5. Caveats (검토 한계 및 가정)

1. **단일 종목 베이스라인 환경 전제**:
   - 본 검토는 Milestone 2 범위인 단일 티커 하이브리드 SL-RL 환경 및 베이스라인 모델을 기준으로 검증하였으며, 다종목 포트폴리오 확장은 상위 마일스톤 요구사항에 따릅니다.
2. **PyTorch autograd 메모리 부하**:
   - `HybridPPO` 및 `SLPretrainer`는 CPU/GPU 환경에서 모두 정상 동작함을 확인하였으나, 대규모 롤아웃 시 버퍼 메모리 해제 패턴을 모니터링할 것을 권장합니다.

---

## 6. Conclusion (최종 결론)

- Milestone 2 산출물은 지도학습 백본과 하이브리드 RL 정책망의 전반적인 구조, 무결성, SB3 어댑터 브릿지 측면에서 높은 완성도를 보이고 있습니다.
- 그러나 **(1) RolloutBuffer GAE 인덱스 오프셋 버그(Critical)**와 **(2) Temporal1DCNN의 특정 배치 크기(B=seq_len) 텐서 차원 크래시(Major)**라는 명확하고 재현 가능한 결함이 발견되었습니다.
- 따라서 본 리뷰어는 **`REQUEST_CHANGES`** 판정을 내리며, Worker가 위의 2가지 결함을 수정한 후 회귀 테스트를 거쳐 재제출할 것을 요청합니다.

---

## 7. Verification Method (독립 재현 및 검증 방법)

### 재현 명령어 및 스크립트

```bash
# 1. GAE 인덱스 오프셋 결함 재현 검증 스크립트 실행
/home/imnyj/venv/bin/python3 -c "
import numpy as np
import torch
from modules.models.hybrid_policy import RolloutBuffer

buf = RolloutBuffer(buffer_size=4, obs_dim=2, device=torch.device('cpu'))
buf.add(np.array([1, 1]), (0, 0.5), reward=1.0, value=10.0, log_prob=-1.0, done=False)
buf.add(np.array([2, 2]), (1, 0.5), reward=2.0, value=20.0, log_prob=-1.0, done=True)
buf.add(np.array([3, 3]), (2, 0.5), reward=3.0, value=30.0, log_prob=-1.0, done=False)
buf.add(np.array([4, 4]), (0, 0.5), reward=4.0, value=40.0, log_prob=-1.0, done=False)
buf.compute_returns_and_advantages(last_value=50.0, last_done=False, gamma=0.99, gae_lambda=0.95)
print('Current Buggy Advantages:', buf.advantages)
# 기대값: step 1(done)의 advantage는 -18.0이어야 하나, 현재 코드는 35.49로 오계산됨
assert np.isclose(buf.advantages[1], -18.0), 'GAE Index Bug Confirmed!'
"

# 2. DualStream B=seq_len(20) 크래시 재현 검증 스크립트 실행
/home/imnyj/venv/bin/python3 -c "
import torch
from modules.models.feature_extractor import DualStreamSLFeatureExtractor
dual = DualStreamSLFeatureExtractor(temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=64)
x_batch = torch.randn(20, 14)
try:
    out = dual(x=x_batch)
    print('Pass:', out.shape)
except RuntimeError as e:
    print('DualStream Crash Confirmed:', e)
"

# 3. 전체 하이브리드 모델 및 환경 단위 테스트 실행
/home/imnyj/venv/bin/pytest tests/test_models.py tests/test_hybrid_trading_env.py -v
```
