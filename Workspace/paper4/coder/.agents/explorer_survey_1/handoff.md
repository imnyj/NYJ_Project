# [Survey Report] AoI 기반 V2I 상향링크 RL 파이프라인 아키텍처 분석 및 R1 결함 진단 보고서

**작성자**: Explorer 1  
**대상 범위**: R1 (`src/hot_swap_trainer.py`, `src/aoi_env.py` 및 관련 `tests/`)  
**작성 일시**: 2026-08-27  

---

## 1. Observation (직접 관찰 결과)

### 1.1 4항 보상 수식 ($I_{redundant}$ 패널티) 관찰
- **Ground Truth (`Conversation.md:21-27`)**:
  $$R_t = -( w_1 \cdot \text{Norm}(e_t^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant} )$$
  * $e_t^2$: 추정 오차 제곱 정규화 ($[0, 1]$)
  * $P_{tx}$: 송신 전력 정규화 ($[0, 1]$)
  * $C_{freq}$: 서브채널 경쟁/CBR 정규화 ($[0, 1]$)
  * $\mathbb{I}_{redundant}$: 물리적 상태 불변(정지) 시 갱신 시도에 대한 바이너리 패널티 ($\{0.0, 1.0\}$)
  * 기본 가중치: $w_1=0.5, w_2=0.2, w_3=0.2, w_4=0.1$
- **`src/aoi_env.py` 상태**:
  * 라인 410-413: 가중치 `w_error=0.5, w_power=0.2, w_congestion=0.2, w_redundant=0.1` 설정.
  * 라인 857-880:
    ```python
    norm_error_sq = float(min(1.0, (err ** 2) / max(1.0, self.norm_error_sq_max)))
    if vid in transmitting_dict:
        tx_info = transmitting_dict[vid]
        ptx = tx_info["p"]
        norm_ptx = float(np.clip((ptx - self.p_min) / max(1e-6, self.p_max - self.p_min), 0.0, 1.0))
        ch_contenders = len(transmissions_by_ch[tx_info["ch"] % self.num_channels])
        norm_cfreq = float(min(1.0, max(0.0, (ch_contenders - 1) / 10.0)))
        i_redundant = 1.0 if (spd < 0.1 and err < 0.05) else 0.0
    else:
        norm_ptx = 0.0
        norm_cfreq = 0.0
        i_redundant = 0.0

    r_val = -(
        self.w_error * norm_error_sq
        + self.w_power * norm_ptx
        + self.w_congestion * norm_cfreq
        + self.w_redundant * i_redundant
    )
    ```
- **`src/hot_swap_trainer.py` 상태**:
  * 과거 결함(`backup/hot_swap_trainer.py.bak.20260827_102551:929-935`):
    `reward_val = -(self.w1 * r_err + self.w2 * r_power + self.w3 * cbr)` (3항 수식, $I_{redundant}$ 누락, $w$ 불일치).
  * 현재 `src/hot_swap_trainer.py:1157-1184`:
    `_is_redundant_update` 판정 추가 및 4항 보상 수식 적용 완료.

### 1.2 전력 정규화 일반화 (`(p - p_min) / (p_max - p_min)`) 관찰
- **과거 결함**:
  `r_power = max(0.0, (p_val - 20.0) / 10.0)` 형태로 하드코딩되어, $p \in [10.0, 23.0]\text{ dBm}$ 설정 시 $p < 20.0$ 구간에서 음수가 되어 패널티가 가산 보상으로 왜곡됨.
- **현재 구현 상태**:
  * `src/hot_swap_trainer.py:1165-1168`:
    ```python
    p_lo = float(getattr(self.decoder, "p_min", 10.0))
    p_hi = float(getattr(self.decoder, "p_max", 23.0))
    if vid in step_tx_power:
        p_val = step_tx_power[vid]
        r_power = min(1.0, max(0.0, (p_val - p_lo) / max(1e-6, p_hi - p_lo)))
    else:
        r_power = 0.0
    ```
  * `src/aoi_env.py:416-417, 864`:
    `norm_ptx = float(np.clip((ptx - self.p_min) / max(1e-6, self.p_max - self.p_min), 0.0, 1.0))` 형태이나, `self.p_min`과 `self.p_max` 기본값이 `20.0, 30.0`으로 남아 있어 `P_MIN=10.0, P_MAX=23.0`과 기본값 동기화 필요.

### 1.3 `tx_powers[-1]` 전력 크레딧 할당 버그 관찰
- **과거 결함 (`hot_swap_trainer.py:1076` 백업본)**:
  `p_val = self.tx_powers[-1] if self.tx_powers else 25.0`
  루프 내 모든 차량의 보상 계산에 전역 리스트의 마지막 원소를 참조하여, 개별 차량의 고유 전력 제어 학습이 완전히 불가능했음.
- **현재 구현 상태**:
  * `src/hot_swap_trainer.py:1030-1043`:
    스텝별 딕셔너리 `step_tx_power: Dict[str, float]` 및 `step_redundant: Dict[str, float]`에 각 차량의 개별 전력과 갱신 여부를 저장.
  * 송신하지 않은 차량에 대해서는 `r_power = 0.0`, `i_redundant = 0.0`으로 정확히 귀속 처리됨.

### 1.4 Anti-Mocking Assertion A4 관찰
- **`src/aoi_env.py:894-913` 및 `src/hot_swap_trainer.py:1210-1227`**:
  ```python
  for vid, r_info in reward_details.items():
      re_ = r_info["r_err"]
      rp_ = r_info["r_power"]
      rc_ = r_info["cbr"]
      ir_ = r_info["i_redundant"]
      rv = r_info["reward"]

      assert 0.0 <= re_ <= 1.0, f"FATAL: Normalized error term {re_} out of bounds [0, 1]!"
      assert 0.0 <= rp_ <= 1.0, f"FATAL: Normalized power term {rp_} out of bounds [0, 1]!"
      assert 0.0 <= rc_ <= 1.0, f"FATAL: Normalized congestion term {rc_} out of bounds [0, 1]!"
      assert ir_ in (0.0, 1.0), f"FATAL: I_redundant must be binary (0.0 or 1.0), got {ir_}!"

      expected_r = -(self.w1 * re_ + self.w2 * rp_ + self.w3 * rc_ + self.w4 * ir_)
      assert math.isclose(rv, expected_r, abs_tol=1e-5), (
          f"FATAL: Reward calculation mismatch for {vid}: {rv} != {expected_r}"
      )
      assert rv <= 0.0, f"FATAL: Penalty-based reward must be <= 0, got {rv}"
  ```
  * 모든 4개 정규화 항의 $[0, 1]$ 바운드 검사, $I_{redundant}$의 바이너리 검사, 수식 재유도 대조(`isclose`), $R_t \le 0.0$ 비양수성 검증을 매 스텝 강제 수행함을 확인.

### 1.5 Resume 로직 및 체크포인트 `best_reward` 오버라이트 버그 관찰
- **`src/hot_swap_trainer.py:662-682` (체크포인트 저장/로드)**:
  ```python
  def save_checkpoint(self, filepath: str) -> None:
      checkpoint = {
          "model_name": self.model_name,
          "hparams": self.hparams,
          "rest_state_dict": self.rest_model.state_dict(),
          "act_state_dict": self.act_model.state_dict(),
          "training_steps": self.background_trainer.training_steps,
          "swap_count": self.hot_swap_manager.swap_count,
      }
      torch.save(checkpoint, filepath)
  ```
  * 관찰: `checkpoint` 딕셔너리에 `best_reward` 필드가 누락되어 있음.
- **`src/hot_swap_trainer.py:1450` (`run_hot_swap_training`)**:
  ```python
  global_step = min(int(start_ep) * steps_per_ep, total_steps)
  best_reward = -float("inf")
  ```
  * 관찰: `resume=True`로 기존 에피소드(예: ep50)부터 재개하더라도 `best_reward`가 항상 `-inf`로 초기화됨.
  * 라인 1530-1533:
    ```python
    if ep_mean_r > best_reward:
        best_reward = ep_mean_r
        best_ckpt_path = os.path.join(checkpoint_dir, f"{model_name}_best.pt")
        trainer.save_checkpoint(best_ckpt_path)
    ```
  * 결과: 재개 직후 에피소드(예: ep51)의 성능이 과거 기록보다 현저히 낮더라도(예: ep51 평균 보상 `-80.0`), `-80.0 > -inf`이 성립하여 과거의 우수한 `{model_name}_best.pt`를 즉시 덮어써버림.

### 1.6 테스트 스위트 실행 결과 (`/home/imnyj/venv/bin/pytest -v`)
- 전체 실행 결과: `38 failed, 166 passed in 54.13s`
- `tests/test_hot_swap.py` 실행 결과: `2 failed, 22 passed in 24.95s`
- 주요 실패 원인 및 구체적 에러 트레이스:
  1. **차원 불일치 (18-dim StateVectorizer vs 16-dim 모델 초기화)**:
     * `tests/test_hot_swap.py:339` 및 `tests/test_hot_swap.py:387`:
       `TestHotSwapRLScheduler`에서 `act_model = HybridPPO(state_dim=16, ...)`으로 모델을 16차원으로 생성하였으나, `HotSwapRLScheduler.decide_grant` 내부에서 `StateVectorizer`가 18차원 벡터를 생성하여 모델에 전달함.
       ```text
       RuntimeError: mat1 and mat2 shapes cannot be multiplied (1x18 and 16x32)
       ```
     * `tests/test_rl_interface.py:58, 112, 137`: `assert vec.shape == (16,)` (실제 18차원 반환으로 단언문 실패)
     * `tests/test_aoi_env_genuine.py:123`: `assert s_vec.shape == (16,)` (실제 18차원 반환으로 실패)
     * `tests/test_dummy_verification.py:60`: `assert len(s_vec) == 16`
  2. **액션 공간 변경 여파**:
     * $\Delta \in [0.1, 45.0]\text{s}$, $P \in [10.0, 23.0]\text{dBm}$으로 교정되었으나, 기존 테스트(`test_hot_swap.py:344`, `test_dummy_verification.py:98`, `test_evaluation.py:131`, `test_rl_interface.py:168`)가 구 액션 범위($[20, 30]\text{dBm}$, $[0.5, 10]\text{s}$)를 검사하여 실패.
  3. **폐기 대상 구 베이스라인 의존성**:
     * `test_baselines_instantiation.py` 등에서 R4에서 완전 삭제될 구 베이스라인 코드 테스트 수행 중 실패.

---

## 2. Logic Chain (추론 과정 및 분석)

1. **보상 함수 및 크레딧 할당 무결성**:
   - `Observation 1.1`, `1.2`, `1.3`에 따라, 과거 트레이너 구현체에 존재하던 3항 축소, 전력 정규화 왜곡, 전역 `tx_powers[-1]` 참조 결함은 `hot_swap_trainer.py` 및 `aoi_env.py`의 핵심 환경 루프에서 4항 Min-Max 정규화 및 per-vehicle 매핑으로 올바르게 구조화됨.
   - 단, `src/aoi_env.py`의 생성자 파라미터 기본값(`p_min=20.0, p_max=30.0`)이 `src/rl_interface.py`의 표준 상수(`P_MIN=10.0, P_MAX=23.0`)와 상이하므로 동기화가 필요함.

2. **단언문 A4의 일관성**:
   - `Observation 1.4`에 따라 `aoi_env.py`와 `hot_swap_trainer.py` 양쪽 모두에서 4대 단언문 중 A4가 수학적 보상 모델과 100% 일치하게 정렬되어 있음. 환경 스텝 시 실시간으로 계산 불일치 및 양수 보상 발생을 차단함.

3. **체크포인트 Resume 결함의 메커니즘**:
   - `Observation 1.5`에 따라, `save_checkpoint` 시 `best_reward`를 `.pt`에 기록하지 않고, `run_hot_swap_training`에서 `best_reward = -inf`로 재설정함.
   - 이로 인해 장기 훈련(20만 스텝)이 네트워크/장비 이슈 등으로 중단 후 재개될 때, 체크포인트 복원 시점 직후의 불안정한 에피소드가 과거 최고 모델(`_best.pt`)을 파괴하는 치명적 데이터 손실이 발생함.

---

## 3. Caveats (한계 및 가정 사항)

1. **R4 베이스라인 삭제 작업과의 경계**:
   - 본 보고서는 R1(트레이너, 환경, 보상, 체크포인트 로직)에 집중 조사하였으며, `src/baselines/` 디렉토리 내의 가짜/구 베이스라인 코드 삭제 및 R2/R3 영역의 변경 사항은 해당 전담 역할의 범위로 둠.
2. **SUMO 실구동 환경 의존성**:
   - SUMO 바이너리 및 libsumo가 정상 연동되는 Linux 환경(`/home/imnyj/venv/bin/sumo`)을 기준으로 검증하였음.

---

## 4. Conclusion (결론 및 권장 수정 전략)

### 4.1 R1 핵심 수정 권장안 (Actionable Fixes)

1. **`src/hot_swap_trainer.py` Checkpoint & Resume 로직 개선**:
   - `HotSwapTrainer.save_checkpoint(filepath, best_reward=None)`:
     * 체크포인트 딕셔너리에 `"best_reward": best_reward` 저장.
   - `HotSwapTrainer.load_checkpoint(filepath)`:
     * 로드된 `checkpoint` 딕셔너리를 반환하여 메타데이터 접근 허용.
   - `run_hot_swap_training(..., resume=False)`:
     * `resume=True` 시, `checkpoint_dir` 내 `{model_name}_best.pt` 또는 최신 `_ep*.pt` 파일에서 `best_reward`를 로드:
       ```python
       best_ckpt_path = os.path.join(checkpoint_dir, f"{model_name}_best.pt")
       if os.path.exists(best_ckpt_path):
           ckpt_data = torch.load(best_ckpt_path, map_location="cpu")
           best_reward = float(ckpt_data.get("best_reward", -float("inf")))
       ```
     * 매 에피소드 종료 후 `trainer.save_checkpoint(ckpt_path, best_reward=best_reward)` 호출로 항상 현재 `best_reward` 메타데이터 유지.

2. **`src/aoi_env.py` 파라미터 표준화**:
   - `rl_interface`에서 `P_MIN, P_MAX, DELTA_MIN, DELTA_MAX`를 임포트하여 기본값으로 설정:
     `self.p_min = float(self.config.get("p_min", P_MIN))`
     `self.p_max = float(self.config.get("p_max", P_MAX))`
   - `ActionDecoder` 생성자 호출 시에도 표준 상수를 사용하도록 통일.

3. **관련 단위 테스트(`tests/`) 갱신**:
   - 18차원 관측 벡터(`STATE_DIM=18`) 및 신규 액션 범위($P \in [10.0, 23.0]\text{dBm}$, $\Delta \in [0.1, 45.0]\text{s}$)를 테스트 단언문에 반영하여 회귀 테스트 패스 달성.

---

## 5. Verification Method (독립 검증 방법)

1. **단위 테스트 실행**:
   ```bash
   /home/imnyj/venv/bin/pytest tests/test_hot_swap.py tests/test_aoi_env_genuine.py -v
   ```
2. **Resume 로직 무결성 검증 시나리오**:
   - 2 에피소드 실행 후 의도적으로 약한 보상(-999.0)을 갖는 에피소드로 `resume=True` 실행 시 `_best.pt`가 덮어써지지 않고 유지되는지 단위 테스트로 검증.
3. **보상 단언문 A4 발화 검증**:
   - `env.step()` 실행 시 A4 단언문 통과 여부 및 $R_t \le 0$ 검증.
