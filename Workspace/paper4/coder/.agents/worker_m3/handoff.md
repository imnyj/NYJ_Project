# Worker M3 Handoff Report: Environment Knobs & HPO Alignment

## 1. Observation (직접 관찰 결과)

1. **`src/NetSim.py`**:
   - `pre_define()` (443, 446행)에 과거 잔존값 `sumo_set.RSU_RANGE = 800.0`, `sumo_set.OUTAGE_ZONE = 800.0`이 하드코딩되어 있어 `InitSumoNetSim()` 호출 시 `make_sumo_set.py`의 300.0m 설정이 800.0m로 덮어써지는 문제가 관찰됨.
   - SUMO 실행 CLI 인수 (532행)에 `"--step-length", "1.0"`으로 하드코딩되어 있어 `generated.sumocfg`의 0.1초 설정이 1.0초로 무력화되는 결함 관찰.
   - `GetSignalState()` (752행) 기본 인수가 `comm_range: float = 800.0`으로 되어 있었음.

2. **`src/sumo/make_sumo_set.py`**:
   - 코드 상 `RSU_RANGE: float = 300.0`, `STEP_LENGTH: float = 0.1`로 정의되어 있으나, 서명 캐시 파일인 `src/sumo/.sumo_gen_signature.json`에 과거 실행 결과인 `"RSU_RANGE": 800.0`이 남아있었음.

3. **`src/evaluate.py`**:
   - `evaluate_single_run()` 기본 인수가 `rsu_range: float = 800.0`으로 지정되어 있었음.
   - `evaluate_single_run()`의 `HeuristicScheduler` 상태 딕셔너리 생성부(239행)에서 `"speed": 10.0`으로 고정 하드코딩되어 있어 정지/출발 예측 시 실제 SUMO 차량 속도가 반영되지 못함.
   - `instantiate_model()`의 `state_dim` 기본값이 16으로 되어 있어 M2에서 개편된 18차원 상태 벡터와 불일치 발생.

4. **`src/hpo.py`**:
   - `sample_reward_weights(trial)`가 $w_1 \in [0.10, 1.00]$, $w_2, w_3, w_4 \in [0.02, 0.60]$ 범위에서 샘플링 후 합이 1.0이 되도록 정규화하고 Optuna user attribute로 저장하는 로직이 있으나, `evaluate_trial_multiseed`에서 `state_dim=16` 및 `rsu_range` 기본값 연동이 미비했음.

---

## 2. Logic Chain (논리 추론 체인)

1. **[RSU_RANGE 300m 통일]**: 5.9GHz C-V2X 도심 환경 통신 반경 표준(200~300m)에 맞추어 `NetSim.py`의 `pre_define()` 및 `GetSignalState()`, `evaluate.py`의 기본값을 300.0m로 일치시키고, `make_sumo_set.py`의 `make_sumo_files(force_regenerate=True)`를 실행하여 SUMO 네트워크 파일 및 `.sumo_gen_signature.json`을 300.0m로 갱신함.
2. **[SUMO step-length 0.1s 적용]**: $\Delta \in [0.1, 45.0]$s의 초미세 갱신 인터벌을 물리적으로 모사하기 위해 SUMO CLI 인수를 `"--step-length", "0.1"`로 변경하여 `generated.sumocfg`의 0.1s 해상도와 일치시킴.
3. **[실시간 속도 연동]**: `HeuristicScheduler`가 감속/정지 및 출발 상황을 정확히 감지할 수 있도록 `evaluate.py`에서 `env.last_speeds.get(vid, 0.0)` 실측값을 추출하여 `st_dict["speed"]`에 주입함.
4. **[Optuna HPO 연동]**: $w_1 \sim w_4$ 보상 가중치가 Optuna 최적화 탐색 공간에 포함되어 환경(`AoiV2IEnv`)으로 전달되고, 최적화 결과 및 트라이얼 히스토리가 CSV 파일에 컬럼별로 정확히 기록되도록 보장함.

---

## 3. Caveats (주의사항 및 한계)

1. **기존 베이스라인 테스트 호환성**: `tests/test_evaluation.py` 등 일부 기존 테스트는 과거 하드코딩된 전력 범위(`[20, 30] dBm`) 및 16차원 상태 공간을 단언하고 있어 실패함. 이는 Milestone M4/M5에서 베이스라인 삭제 및 테스트 스위트 개편 시 업데이트될 예정임.
2. **SUMO step-length 변경에 따른 웜업 스텝 수**: SUMO step-length가 1.0s에서 0.1s로 변경됨에 따라, 동일 물리 시간(초) 동안 차량이 교차로에 도달하기 위해서는 필요한 스텝 수가 10배 증가함(예: 35s = 350 steps). `evaluate_single_run` 실행 시 스텝 수를 충분히 확보해야 통신 범위 내 차량 데이터가 수집됨.

---

## 4. Conclusion (결론 및 완료 상태)

Milestone M3의 4개 독점 파일(`src/NetSim.py`, `src/sumo/make_sumo_set.py`, `src/evaluate.py`, `src/hpo.py`)에 대한 수정이 완료되었으며, 동시성 락(`LockManager`)과 감사 로깅(`AuditLogger`) 하에 안전하게 반영되었습니다.

- `NetSim.py`: `RSU_RANGE = 300.0`, `OUTAGE_ZONE = 300.0`, `--step-length 0.1`, `comm_range = 300.0` 완벽 반영.
- `make_sumo_set.py`: `RSU_RANGE = 300.0`, `STEP_LENGTH = 0.1` 및 `.sumo_gen_signature.json` 최신화 완료.
- `evaluate.py`: `rsu_range = 300.0`, 실시간 `env.last_speeds` 연동, `state_dim = STATE_DIM (18)` 반영 완료.
- `hpo.py`: Optuna $w_1 \sim w_4$ 정규화 샘플링 및 CSV 저장, `STATE_DIM` 및 `rsu_range` 연동 완료.

---

## 5. Verification Method (독립 검증 방법)

독립 검증을 위해 아래 명령어를 실행하여 M3의 모든 요구사항이 충족되었는지 확인할 수 있습니다:

```bash
/home/imnyj/venv/bin/python -c '
import optuna
import tempfile
import pandas as pd
import src.NetSim as netsim
import src.sumo.make_sumo_set as ss
from src.evaluate import evaluate_single_run, instantiate_model
from src.heuristic_scheduler import HeuristicScheduler
from src.hpo import sample_reward_weights, save_study_results, REWARD_WEIGHT_KEYS, REWARD_WEIGHT_RANGES

# 1. Knob 검증
netsim.pre_define()
assert ss.RSU_RANGE == 300.0 and ss.OUTAGE_ZONE == 300.0 and ss.STEP_LENGTH == 0.1
sig = ss.current_generation_signature()
assert sig["RSU_RANGE"] == 300.0 and sig["STEP_LENGTH"] == 0.1
print("[PASS] 1. RSU_RANGE=300.0, STEP_LENGTH=0.1 verified")

# 2. 실시간 속도 및 HeuristicScheduler 검증 (400 steps)
speeds = []
class InstrumentScheduler(HeuristicScheduler):
    def decide_grant(self, vid, st_dict):
        speeds.append(st_dict["speed"])
        return super().decide_grant(vid, st_dict)

model = InstrumentScheduler()
res = evaluate_single_run(model, density=25.0, seed=42, n_steps=400, rsu_range=300.0)
assert len(speeds) > 0 and any(s != 10.0 for s in speeds)
print(f"[PASS] 2. Real vehicle speed verified ({len(speeds)} records, mean: {sum(speeds)/len(speeds):.2f} m/s)")

# 3. Optuna w1..w4 HPO 검증
study = optuna.create_study(direction="minimize")
trial = study.ask()
w = sample_reward_weights(trial)
assert abs(sum(w.values()) - 1.0) < 1e-4
for k in REWARD_WEIGHT_KEYS:
    assert k in trial.user_attrs
study.tell(trial, 1.0)
with tempfile.TemporaryDirectory() as tmpdir:
    csv_path, best = save_study_results(study, "HybridPPO", output_dir=tmpdir)
    df = pd.read_csv(csv_path)
    for k in REWARD_WEIGHT_KEYS:
        assert k in df.columns
print("[PASS] 3. Optuna w1..w4 sampling & CSV logging verified")
print("ALL M3 CHECKS PASSED!")
'
```
