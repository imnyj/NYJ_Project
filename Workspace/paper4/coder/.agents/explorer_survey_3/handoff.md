# Explorer 3 조사 보고서: R3(Environment Knobs & HPO) 및 R4(Baseline Scraping & References)

## 1. Observation (직접 관찰 결과)

### [R3.1] RSU 통신 반경 설정 (`RSU_RANGE = 300.0`)
1. **`src/sumo/make_sumo_set.py`**:
   - 38행: `RSU_RANGE: float = 300.0`
   - 39행: `EDGE_LENGTH: float = RSU_RANGE * 2.0 + OUTAGE_ZONE` (300*2 + 300 = 900.0m)
   - 142행: `_SIGNATURE_EXACT_KEYS`에 `"RSU_RANGE"` 포함.
   - `src/sumo/.sumo_gen_signature.json` 9행: 과거 잔존값 `"RSU_RANGE": 800.0`으로 남아있음.
2. **`src/NetSim.py`**:
   - 443행 (`pre_define()` 함수 내부):
     ```python
     def pre_define() -> None:
         global MODE, MAX_EPISODE, b_reroute, b_step_log
         sumo_set.RSU_RANGE = 800.0  # <--- 하드코딩 결함!
         MAX_EPISODE = 1
         sumo_set.MAX_STEPS = 3600.0
         sumo_set.OUTAGE_ZONE = 800.0  # <--- 하드코딩 결함!
     ```
     `InitSumoNetSim()` 호출 시 `make_sumo_set.py`의 `RSU_RANGE`가 800.0으로 덮어써지는 치명적 결함 발견.
3. **`src/aoi_env.py`**:
   - 304행: `comm_range=float(getattr(ss, "RSU_RANGE", 800.0))` -> 기본 fallback이 800.0
   - 402행: `self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 800.0)))` -> 기본 fallback이 800.0
4. **`src/hot_swap_trainer.py`**:
   - 441행: `HotSwapRLTrainer.__init__(..., rsu_range: float = 800.0, ...)` -> 기본값 800.0
   - 719행: `AoiV2IEnv.__init__(..., rsu_range: float = 800.0, ...)` -> 기본값 800.0
5. **`src/rl_interface.py`**:
   - 87행: `StateVectorizer.__init__(..., rsu_range: float = 800.0, ...)` -> 기본값 800.0
6. **`src/evaluate.py`**:
   - 215행: `evaluate_single_run(..., rsu_range: float = 800.0)` -> 기본값 800.0
7. **`tests/` 파일들**:
   - `tests/conftest.py` 16, 39행 (`comm_range=800.0`), `tests/contract_adapters.py` 35, 76, 130, 182행, `tests/test_rl_interface.py` 36, 45, 47, 118행, `tests/test_tier1_features.py` 82행, `tests/test_tier2_boundaries.py` 30, 45, 52행, `tests/test_tier3_integration.py` 61행, `tests/test_dynamics_predictor.py` 373행, `tests/test_e2e_pipeline.py` 34, 39행에서 800.0 전달 및 기본값 사용.

---

### [R3.2] SUMO Step-Length 설정 (`step-length = 0.1`)
1. **`src/sumo/make_sumo_set.py`**:
   - 31행: `STEP_LENGTH: float = 0.1`
   - 445행: `<step-length value="{STEP_LENGTH}"/>` (sumocfg 템플릿에 정상 반영)
   - 149행: `_SIGNATURE_EXACT_KEYS`에 `"STEP_LENGTH"` 등록.
2. **`src/sumo/generated.sumocfg`**:
   - 17행: `<step-length value="0.1"/>` (정상 반영됨)
3. **`src/hot_swap_trainer.py`**:
   - 824-825행:
     ```python
     cmd = [
         "sumo",
         "-c",
         "src/sumo/generated.sumocfg",
         "--step-length",
         "1.0",  # <--- 하드코딩 결함! generated.sumocfg의 0.1 설정을 무력화
     ```
4. **`src/NetSim.py`**:
   - 532행: `"--step-length", "1.0"` (하드코딩 결함)
5. **`src/aoi_env.py`**:
   - 399행: `self.step_length = float(self.config.get("step_length", 1.0))` (기본값이 1.0으로 설정됨)
   - 517행: `"--step-length", str(self.step_length)` 전달.

---

### [R3.3] `evaluate.py`: 하드코딩된 `"speed": 10.0` 결함
- **위치**: `src/evaluate.py:236-246`
```python
236:             if isinstance(model, HeuristicScheduler):
237:                 st_dict = {
238:                     "vid": vid,
239:                     "pos": env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0)),
240:                     "speed": 10.0,  # <--- 하드코딩 결함 발견!
241:                     "dist_to_rsu": math.hypot(
242:                         env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[0] - env.target_rsu_pos[0],
243:                         env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[1] - env.target_rsu_pos[1],
244:                     ),
245:                     "current_time": env.sim_time,
246:                 }
247:                 grant = model.decide_grant(vid, st_dict)
```
- **실시간 차량 속도 소스 확인**:
  - `src/hot_swap_trainer.py:950`: `self.last_speeds[vid] = spd` (`libsumo.vehicle.getSpeed(vid)` 실측값 매 스텝 기록).
  - `src/hot_swap_trainer.py:1481`: `veh_speed = float(env.last_speeds.get(vid, 0.0))` 형태로 정상 추출 패턴 존재.
  - `src/evaluate.py`에서는 이 `env.last_speeds`를 활용하지 않고 10.0으로 고정하여 휴리스틱 스케줄러의 정지/출발 예측 규칙을 왜곡하고 있었음.

---

### [R3.4] `hpo.py`: Optuna Search Space 및 보상 가중치 `w1, w2, w3, w4`
- **위치**: `src/hpo.py:112-142`
  - `sample_reward_weights(trial)` 함수가 구현되어 `w1_raw ~ w4_raw`를 샘플링하고 합계 1.0으로 Min-Max 정규화된 비중을 계산:
    ```python
    REWARD_WEIGHT_KEYS: Tuple[str, ...] = ("w1", "w2", "w3", "w4")
    REWARD_WEIGHT_RANGES: Dict[str, Tuple[float, float]] = {
        "w1": (0.10, 1.00),   # estimation-error penalty Norm(e_t^2)
        "w2": (0.02, 0.60),   # transmit-power penalty Norm(P_tx)
        "w3": (0.02, 0.60),   # channel-congestion penalty Norm(C_freq)
        "w4": (0.02, 0.60),   # redundant-update penalty I_redundant
    }
    ```
  - `objective(trial)`에서 `reward_weights`를 `evaluate_trial_multiseed` -> `evaluate_model_in_env` -> `AoiV2IEnv(..., **env_kwargs)`로 전달.
  - `save_study_results`에서 `optuna_trials_<model>.csv` 및 `optuna_best_params.csv`에 `w1, w2, w3, w4`를 컬럼으로 저장.
  - **불일치 확인**: `hot_swap_trainer.py`의 `AoiV2IEnv`는 `w1, w2, w3, w4`를 직접 인자로 받으나, `src/aoi_env.py`는 `config["weights"]` 딕셔너리로 받고 레거시 키(`w_error`, `w_power`, `w_congestion`, `w_redundant`)와의 호환 처리가 복잡함.

---

### [R4] Baseline Scraping & References 현황 조사
1. **`src/baselines/` 디렉토리 내부 파일 목록 (전부 삭제 대상, 총 11개 파일)**:
   - `src/baselines/__init__.py`
   - `src/baselines/base_agent.py`
   - `src/baselines/hybrid_ppo.py`
   - `src/baselines/hybrid_sac.py`
   - `src/baselines/hybrid_td3.py`
   - `src/baselines/mappo.py`
   - `src/baselines/hyar_ppo.py`
   - `src/baselines/pdqn.py`
   - `src/baselines/pure_aoi.py`
   - `src/baselines/dueling_q_aoi.py`
   - `src/baselines/sac_aoi.py`

2. **코드베이스 전역 Baseline Import/참조 위치 목록**:
   - `src/hot_swap_trainer.py:51`: `from src.baselines import BASELINE_REGISTRY, BaseRLModel`
   - `src/hot_swap_trainer.py:324, 437`: `BaseRLModel` 타입 힌트
   - `src/hot_swap_trainer.py:602-605`: `BASELINE_REGISTRY` 딕셔너리 조회
   - `src/evaluate.py:41-44`: `from src.baselines import (BASELINE_REGISTRY, BaseRLModel)`
   - `src/evaluate.py:55-66`: `CANONICAL_EVAL_MODELS` (9종 베이스라인 목록)
   - `src/evaluate.py:183-190`: `instantiate_model`에서 `BASELINE_REGISTRY` 모델 생성
   - `src/hpo.py:32-33`: `from src.baselines import BASELINE_REGISTRY, BaseRLModel`
   - `src/hpo.py:48-58`: `CANONICAL_MODEL_NAMES` (9종 베이스라인 목록)
   - `src/hpo.py:144-234`: `sample_hparams` 내 9종 개별 모델 탐색 공간
   - `src/hpo.py:399-402`: `BASELINE_REGISTRY` 모델 클래스 참조
   - `run_all.py:10-14`: `MODELS = ["HybridPPO", ...]` 9종 훈련 루프
   - `etc/scripts/test_adversarial_suite.py:39-50`: 9종 모델 import 및 Suite 3 실행
   - `etc/scripts/verify_dueling_q_action_idx.py`: `DuelingQAoI` 테스트 스크립트
   - `tests/test_baselines_instantiation.py`: 9종 모델 인스턴스화 전용 테스트
   - `tests/test_dummy_verification.py:28-30, 82-100`: `test_d2_all_9_baseline_models_instantiation_and_inference`
   - `tests/test_hot_swap.py:33-40`: 9종 베이스라인 모델 import
   - `tests/test_hpo.py:13, 30-70`: 9종 베이스라인 대상 HPO 테스트
   - `tests/test_evaluation.py:30`: `BaseRLModel` import
   - `tests/test_tier1_features.py:18, 140-165`: `BASELINE_REGISTRY` fixture 테스트
   - `tests/test_tier3_integration.py:20, 63, 95, 142`: `BASELINE_REGISTRY` 모델 인스턴스화
   - `tests/contract_adapters.py:250-570`: 내부 가짜 베이스라인 구현체 및 `BASELINE_REGISTRY`

---

## 2. Logic Chain (논리 추론 체인)

1. **[R3.1 RSU 통신 반경 불일치]**:
   - `scenario.md` 및 `Conversation.md`에서 5.9 GHz C-V2X 환경의 실제 RSU 통신 반경은 200~300m로 규정되어 있음.
   - `make_sumo_set.py`는 `RSU_RANGE = 300.0`으로 수정되었으나, `NetSim.py`의 `pre_define()`이 800.0으로 덮어쓰고, `hot_swap_trainer.py`, `aoi_env.py`, `evaluate.py`, `rl_interface.py` 기본 인자가 800.0으로 남아 있어 런타임에 불일치가 발생함.
   - 따라서 모든 모듈의 기본값 및 fallback을 `300.0` 또는 `getattr(ss, "RSU_RANGE", 300.0)`으로 통일해야 함.

2. **[R3.2 SUMO Step-Length 불일치]**:
   - $\Delta \in [0.1, 5.0]$s의 초미세 갱신 인터벌을 시뮬레이터에서 정확히 묘사하려면 SUMO의 `step-length`가 0.1초여야 함.
   - `make_sumo_set.py`와 `generated.sumocfg`는 0.1초로 설정되었으나, `hot_swap_trainer.py`와 `NetSim.py`가 SUMO CLI 실행 인자로 `"--step-length", "1.0"`을 넘겨 1.0초로 강제 덮어쓰기하고 있음.
   - CLI 인자를 `0.1`로 수정해야만 $\Delta=0.1$s가 물리적으로 유효해짐.

3. **[R3.3 `evaluate.py` 실시간 차량 속도 연동]**:
   - `HeuristicScheduler`는 차량 속도와 정지선 거리, 신호등 상태를 기반으로 정지/출발을 예측(`predict_stop_imminent`, `predict_start_imminent`)함.
   - 현재 `evaluate.py:239`가 `"speed": 10.0`으로 하드코딩되어 있어 교차로에서 차량이 감속/정지하거나 정지 상태에서 출발할 때도 항상 10m/s로 간주되어 휴리스틱 규칙이 오작동함.
   - `env.last_speeds.get(vid, 0.0)`을 통해 실시간 SUMO 속도를 전달하도록 수정해야 함.

4. **[R3.4 Optuna 보상 가중치 HPO 연동]**:
   - `Conversation.md` line 31에 따라 보상 수식의 4개 가중치 $w_1, w_2, w_3, w_4$는 최적화 공간에 포함되어야 함.
   - `hpo.py`에 `sample_reward_weights`가 이미 정규화($\sum w_i = 1$) 방식으로 구현되어 있으므로, 이를 환경(`AoiV2IEnv`)과 완전하게 연동시키고 최적화 파라미터로 저장되도록 정렬해야 함.

5. **[R4 Baseline 완전 삭제 및 클린업]**:
   - 기존 9개 베이스라인(`src/baselines/`)은 임의로 작성된 가짜/결함 모델이며, 향후 IEEE 공인 베이스라인 6종 재구현 전까지는 일체의 베이스라인 코드를 남기지 말아야 함 (`ORIGINAL_REQUEST.md` R4 명시).
   - 따라서 `src/baselines/` 디렉토리를 통째로 삭제하고, `hot_swap_trainer.py`, `evaluate.py`, `hpo.py`, `run_all.py`, `tests/`에서 베이스라인 import 및 종속성을 제거해야 함.

---

## 3. Caveats (주의사항 및 한계)

1. **베이스라인 삭제 시 기존 테스트 깨짐 현상**:
   - `tests/test_baselines_instantiation.py` 및 베이스라인 모델을 import하는 테스트들은 `src/baselines/` 삭제 시 즉시 `ModuleNotFoundError`를 유발함.
   - 베이스라인 전용 테스트 파일은 삭제/격리하고, `test_hot_swap.py`나 `test_hpo.py` 등은 더미 `nn.Module` 또는 환경 기반 테스트로 전환해야 함.
2. **`AoiV2IEnv` 클래스 이중 정의**:
   - 현재 `src/aoi_env.py`와 `src/hot_swap_trainer.py` 내부에 `AoiV2IEnv`가 중복 정의되어 있음. 두 클래스 모두에 `RSU_RANGE=300.0`, `step_length=0.1`, `w1..w4` 4항 보상이 일관되게 적용되어야 함.

---

## 4. Conclusion (결론 및 제안 작업)

### 4.1 R3 수정 제안 사항

#### 1) `src/NetSim.py` RSU_RANGE 및 step-length 수정
```python
# src/NetSim.py:441-447
def pre_define() -> None:
    global MODE, MAX_EPISODE, b_reroute, b_step_log
-   sumo_set.RSU_RANGE = 800.0
+   sumo_set.RSU_RANGE = 300.0
    MAX_EPISODE = 1
    sumo_set.MAX_STEPS = 3600.0
-   sumo_set.OUTAGE_ZONE = 800.0
+   sumo_set.OUTAGE_ZONE = 300.0

# src/NetSim.py:532
-   "--step-length", "1.0",
+   "--step-length", "0.1",
```

#### 2) `src/hot_swap_trainer.py` RSU_RANGE 및 step-length 수정
```python
# src/hot_swap_trainer.py:441
-   rsu_range: float = 800.0,
+   rsu_range: float = 300.0,

# src/hot_swap_trainer.py:719
-   rsu_range: float = 800.0,
+   rsu_range: float = 300.0,

# src/hot_swap_trainer.py:824-825
    cmd = [
        "sumo",
        "-c",
        "src/sumo/generated.sumocfg",
        "--step-length",
-       "1.0",
+       "0.1",
```

#### 3) `src/aoi_env.py` RSU_RANGE 및 step-length fallback 수정
```python
# src/aoi_env.py:304
-   super().__init__(node_id, pos=pos, comm_range=float(getattr(ss, "RSU_RANGE", 800.0)))
+   super().__init__(node_id, pos=pos, comm_range=float(getattr(ss, "RSU_RANGE", 300.0)))

# src/aoi_env.py:399-402
-   self.step_length = float(self.config.get("step_length", 1.0))
-   self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 800.0)))
+   self.step_length = float(self.config.get("step_length", getattr(ss, "STEP_LENGTH", 0.1)))
+   self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 300.0)))
```

#### 4) `src/rl_interface.py` StateVectorizer RSU_RANGE 기본값 수정
```python
# src/rl_interface.py:87
-   rsu_range: float = 800.0,
+   rsu_range: float = 300.0,
```

#### 5) `src/evaluate.py` 실시간 속도 및 RSU_RANGE 수정
```python
# src/evaluate.py:215
-   rsu_range: float = 800.0,
+   rsu_range: float = 300.0,

# src/evaluate.py:236-246
            if isinstance(model, HeuristicScheduler):
+               veh_pos = env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))
+               veh_speed = float(getattr(env, "last_speeds", {}).get(vid, 0.0))
                st_dict = {
                    "vid": vid,
-                   "pos": env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0)),
-                   "speed": 10.0,
-                   "dist_to_rsu": math.hypot(
-                       env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[0] - env.target_rsu_pos[0],
-                       env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[1] - env.target_rsu_pos[1],
-                   ),
+                   "pos": veh_pos,
+                   "speed": veh_speed,
+                   "dist_to_rsu": math.hypot(
+                       veh_pos[0] - env.target_rsu_pos[0],
+                       veh_pos[1] - env.target_rsu_pos[1],
+                   ),
                    "current_time": env.sim_time,
                }
                grant = model.decide_grant(vid, st_dict)
```

---

### 4.2 R4 베이스라인 삭제 및 클린업 작업 목록

1. **`src/baselines/` 디렉토리 완전 삭제**:
   - `rm -rf /home/imnyj/Workspace/paper4/coder/src/baselines/`
2. **`src/hot_swap_trainer.py` 클린업**:
   - `from src.baselines import BASELINE_REGISTRY, BaseRLModel` 제거.
   - `HotSwapRLTrainer`가 `act_model`, `rest_model` 인스턴스 또는 사용자 정의 모델 팩토리를 직접 받도록 변경.
3. **`src/evaluate.py` 클린업**:
   - `from src.baselines import BASELINE_REGISTRY, BaseRLModel` 제거.
   - `CANONICAL_EVAL_MODELS = ["HeuristicScheduler"]`로 간소화.
   - `instantiate_model`에서 `HeuristicScheduler`만 인스턴스화하고 미구현 베이스라인 요청 시 `NotImplementedError` 발생.
4. **`src/hpo.py` 클린업**:
   - `from src.baselines import BASELINE_REGISTRY, BaseRLModel` 제거.
   - 4개 보상 가중치(`w1, w2, w3, w4`) 탐색 메커니즘을 보존하되, 특정 가짜 베이스라인 의존성 제거.
5. **`run_all.py` 클린업**:
   - 9개 베이스라인 훈련 루프 제거 (`MODELS = []` 또는 사용자 승인 대기 메시지 출력).
6. **`tests/` 및 `etc/` 테스트 클린업**:
   - `tests/test_baselines_instantiation.py`, `etc/scripts/verify_dueling_q_action_idx.py` 삭제.
   - `tests/contract_adapters.py` 내 가짜 베이스라인 구현체 제거.
   - `test_dummy_verification.py`, `test_hot_swap.py`, `test_hpo.py`, `test_evaluation.py`를 베이스라인 없이 환경 및 휴리스틱 스케줄러, 더미 `nn.Module`로 동작하도록 리팩토링.

---

## 5. Verification Method (독립 검증 방법)

1. **RSU_RANGE 및 step-length 검증**:
   ```bash
   # 1. codebase 내 800.0 및 step-length 1.0 잔존 여부 확인
   grep -rn "RSU_RANGE" src/ tests/
   grep -rn "step-length" src/ tests/
   
   # 2. SUMO config 서명 재생성 확인
   python -c "import src.sumo.make_sumo_set as ss; ss.make_sumo_files(force_regenerate=True); print(ss.current_generation_signature())"
   ```
2. **`evaluate.py` 실시간 속도 전달 검증**:
   ```bash
   # evaluate_single_run 실행 시 실제 속도가 전달되는지 테스트
   python -c "from src.evaluate import evaluate_single_run, instantiate_model; model = instantiate_model('HeuristicScheduler'); res = evaluate_single_run(model, density=25.0, seed=42, n_steps=10); print(res)"
   ```
3. **`hpo.py` w1~w4 탐색 검증**:
   ```bash
   # 1 trial Optuna HPO 실행 및 w1~w4 파라미터 생성 검증
   python -c "import optuna; from src.hpo import sample_reward_weights; study = optuna.create_study(); trial = study.ask(); print(sample_reward_weights(trial))"
   ```
4. **베이스라인 삭제 및 테스트 스위트 실행**:
   ```bash
   # src/baselines/ 삭제 후 pytest 실행
   /home/imnyj/venv/bin/pytest tests/test_dynamics_predictor.py tests/test_aoi_env_genuine.py -v
   ```
