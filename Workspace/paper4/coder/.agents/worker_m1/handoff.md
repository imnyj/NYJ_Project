# [Handoff Report] 마일스톤 M1 (Trainer & Env Core Fixes) 완료 보고서

**작성자**: Worker 1 (Milestone M1 Lead)  
**수행 일시**: 2026-08-27  
**대상 파일**: `src/aoi_env.py`, `src/hot_swap_trainer.py`  

---

## 1. Observation (직접 관찰 결과)

### 1.1 `src/aoi_env.py` 수정 전후 관찰
- **수정 전 (기본값 및 임포트 결함)**:
  * 라인 50: `from src.rl_interface import ActionDecoder, StateVectorizer` (상수 미임포트)
  * 라인 399: `self.step_length = float(self.config.get("step_length", 1.0))` (0.1s 미지원)
  * 라인 402: `self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 800.0)))` (구 800m 잔존)
  * 라인 416-417: `self.p_min = float(self.config.get("p_min", 20.0))`, `self.p_max = float(self.config.get("p_max", 30.0))` (구 전력 범위 잔존)
  * 라인 425-426: `ActionDecoder(..., delta_min=0.5, delta_max=10.0, ...)` (구 델타 범위 하드코딩)
- **수정 후 (`src/aoi_env.py`)**:
  * 라인 50-57: `from src.rl_interface import (ActionDecoder, StateVectorizer, P_MIN, P_MAX, DELTA_MIN, DELTA_MAX)`
  * 라인 406: `self.step_length = float(self.config.get("step_length", 0.1))`
  * 라인 409: `self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 300.0)))`
  * 라인 422-425: `self.p_min = float(self.config.get("p_min", P_MIN))`, `self.p_max = float(self.config.get("p_max", P_MAX))`, `self.delta_min = float(self.config.get("delta_min", DELTA_MIN))`, `self.delta_max = float(self.config.get("delta_max", DELTA_MAX))`
  * 라인 430-436: `ActionDecoder(num_channels=self.num_channels, delta_min=self.delta_min, delta_max=self.delta_max, p_min=self.p_min, p_max=self.p_max)`
  * 라인 857-891: 4항 보상 수식 및 전력 정규화 일반화 `norm_ptx = float(np.clip((ptx - self.p_min) / max(1e-6, self.p_max - self.p_min), 0.0, 1.0))` 적용.
  * 라인 896-913: Anti-Mocking Assertion A4를 통해 각 항의 $[0, 1]$ 범위, $I_{redundant}$ 바이너리성, $R_t == -(w_1 \cdot \text{Norm}(e^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant})$ 일치(`math.isclose`), $R_t \le 0.0$ 검증 강제.

### 1.2 `src/hot_swap_trainer.py` 수정 전후 관찰
- **수정 전 (체크포인트 및 Resume 결함)**:
  * 라인 661: `def save_checkpoint(self, filepath: str) -> None:` (체크포인트 딕셔너리에 `best_reward` 누락)
  * 라인 674: `def load_checkpoint(self, filepath: str) -> None:` (로드된 체크포인트 미반환)
  * 라인 1450: `best_reward = -float("inf")` (`resume=True` 시에도 `-inf`로 강제 리셋되어 이전 우수 가중치를 덮어쓰는 문제)
  * 라인 441, 719: `rsu_range: float = 800.0`
  * 라인 825: `"--step-length", "1.0"`
- **수정 후 (`src/hot_swap_trainer.py`)**:
  * 라인 441: `HotSwapRLScheduler` 기본 `rsu_range = 300.0` 설정.
  * 라인 661-673: `def save_checkpoint(self, filepath: str, best_reward: Optional[float] = None) -> None:`에서 `"best_reward": best_reward` 영속화.
  * 라인 674-681: `def load_checkpoint(self, filepath: str) -> Dict[str, Any]:`에서 로드된 `checkpoint` 딕셔너리 반환.
  * 라인 721: `AoiV2IEnv` 기본 `rsu_range = 300.0` 설정.
  * 라인 826: `_init_sumo` 내 `"--step-length", "0.1"` 설정.
  * 라인 1432-1454: `run_hot_swap_training`에서 `resume=True` 시 `resumed_from` 체크포인트 및 `{model_name}_best.pt`로부터 `best_reward`를 로드하여 복원.
  * 라인 1540-1546: 주기적 체크포인트 및 최고 성능 체크포인트 저장 시 `trainer.save_checkpoint(ckpt_path, best_reward=best_reward)` 호출로 메타데이터 지속 유지 및 `if ep_rewards and ep_mean_r > best_reward:`로 유효 에피소드만 갱신.

---

## 2. Logic Chain (추론 과정 및 분석)

1. **상수 단일 소스 원칙 (Single Source of Truth)**:
   - `Observation 1.1`에 따라, `src/aoi_env.py` 내의 `p_min, p_max, delta_min, delta_max, rsu_range, step_length` 기본값을 `src.rl_interface` 및 `Conversation.md`의 표준 상수(`P_MIN=10.0, P_MAX=23.0, DELTA_MIN=0.1, DELTA_MAX=45.0, RSU_RANGE=300.0, step_length=0.1`)와 100% 동기화함.
   - 이를 통해 모듈 간 인터페이스 불일치 및 전력/갱신 간격 왜곡 문제를 원천 제거함.

2. **4항 보상 수식 및 A4 단언문 무결성**:
   - `Observation 1.1`에 따라 `aoi_env.py`와 `hot_swap_trainer.py` 양쪽 모두에서 $R_t = -(0.5 \cdot \text{Norm}(e^2) + 0.2 \cdot \text{Norm}(P_{tx}) + 0.2 \cdot \text{Norm}(C_{freq}) + 0.1 \cdot \mathbb{I}_{redundant})$ 4개 정규화 항이 엄격하게 계산되고, 매 스텝 Anti-Mocking Assertion A4를 통해 비양수성($R_t \le 0.0$)과 수학적 일치성이 강제됨.

3. **체크포인트 복원 및 최적 모델 보존 메커니즘**:
   - `Observation 1.2`에 따라, 훈련 재개 시 과거의 최고 보상치(`best_reward`)가 손실되지 않고 복원되도록 `save_checkpoint`와 `load_checkpoint`, `run_hot_swap_training`을 개선함.
   - 재개 직후의 불안정한 에피소드로 인해 최고 모델 파일(`_best.pt`)이 파괴되는 현상을 완벽히 방지함.

---

## 3. Caveats (한계 및 가정 사항)

- 본 마일스톤 M1은 `src/aoi_env.py` 및 `src/hot_swap_trainer.py`에 국한되며, 베이스라인 파일 삭제(M4) 및 `verify_environment.py`/테스트 파일의 18차원 단언문 교정(M5)은 후속 마일스톤에서 전담합니다.
- `lock_manager.py`와 `audit_logger.py`를 엄격히 준수하여 변경 전후 파일 락 및 감사 로그를 모두 기록 완료하였습니다.

---

## 4. Conclusion (최종 결론)

- `src/aoi_env.py`와 `src/hot_swap_trainer.py`의 핵심 환경/트레이너 로직이 `Conversation.md` 및 마일스톤 M1 요구사항에 완벽하게 정렬되었습니다.
- 전력 정규화 일반화, 차량별 개별 전력 크레딧 할당, 4항 보상 모델 및 A4 단언문 검증, 체크포인트 `best_reward` 영속화 및 `resume` 복원이 모두 검증되었습니다.

---

## 5. Verification Method (독립 검증 방법)

1. **파라미터 및 체크포인트 영속화 검증 스크립트 실행**:
   ```bash
   /home/imnyj/venv/bin/python -c '
   import os, tempfile, torch
   from src.aoi_env import AoiV2IEnv
   from src.hot_swap_trainer import HotSwapTrainer, AoiV2IEnv as HotSwapAoiV2IEnv

   env1 = AoiV2IEnv()
   assert env1.p_min == 10.0 and env1.p_max == 23.0
   assert env1.delta_min == 0.1 and env1.delta_max == 45.0
   assert env1.step_length == 0.1 and env1.rsu_range == 300.0

   with tempfile.TemporaryDirectory() as tmpdir:
       trainer = HotSwapTrainer(model_name="HybridPPO")
       ckpt_path = os.path.join(tmpdir, "test.pt")
       trainer.save_checkpoint(ckpt_path, best_reward=-25.0)
       loaded = trainer.load_checkpoint(ckpt_path)
       assert loaded["best_reward"] == -25.0
   print("ALL M1 CORE VERIFICATIONS PASSED")
   '
   ```

2. **Resume 동작 시 `best_reward` 보존 검증**:
   ```bash
   /home/imnyj/venv/bin/python -c '
   import os, tempfile, torch
   from src.hot_swap_trainer import HotSwapTrainer, run_hot_swap_training

   with tempfile.TemporaryDirectory() as tmpdir:
       ckpt_dir = os.path.join(tmpdir, "checkpoints")
       os.makedirs(ckpt_dir, exist_ok=True)
       best_path = os.path.join(ckpt_dir, "HybridPPO_best.pt")
       ep1_path = os.path.join(ckpt_dir, "HybridPPO_ep001.pt")
       t = HotSwapTrainer(model_name="HybridPPO")
       t.save_checkpoint(best_path, best_reward=-10.0)
       t.save_checkpoint(ep1_path, best_reward=-10.0)

       res = run_hot_swap_training(
           model_name="HybridPPO", total_steps=40, episodes=2,
           checkpoint_dir=ckpt_dir, resume=True, warmup_steps=35
       )
       best_data = torch.load(best_path, map_location="cpu")
       assert best_data["best_reward"] == -10.0
   print("RESUME BEST_REWARD PRESERVATION VERIFIED")
   '
   ```

3. **관련 테스트 실행**:
   ```bash
   /home/imnyj/venv/bin/pytest tests/test_hot_swap.py::TestHotSwapTrainerAndLoop -v
   ```
