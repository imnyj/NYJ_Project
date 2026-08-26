# 포렌식 무결성 감사 보고서 (Forensic Integrity Audit Report)

**대상 저장소 (Work Product)**: `/home/imnyj/Workspace/paper4/coder/`  
**감사관 (Auditor)**: `auditor_genuine_1`  
**감사 일시**: 2026-08-27T02:56:00+09:00  
**무결성 모드 (Integrity Mode)**: Demo / Benchmark Multi-Phase Mode  
**최종 판정 (Verdict)**: **CLEAN (무결성 통과)**

---

## 1. 감사 개요 및 목적 (Executive Summary)
본 감사는 `/home/imnyj/Workspace/paper4/coder/` 저장소 전체를 대상으로 인공 합성 모의 객체(`SyntheticVehicle`, `EvalSyntheticVehicle` 등) 및 가짜 좌표·채널 우회 코드가 100% 제거되었는지 검증하고, 실제 SUMO(`libsumo`/`TraCI`) 및 무선 물리 계층(`Communications.py`)이 전 단계에서 진성 구동되는지, 200,000 스텝 훈련 인프라의 완성도 및 사전 계산 중단(Pre-Compute Halt) 준수 여부를 독립적으로 교차 검증하기 위해 수행되었습니다.

---

## 2. 4대 핵심 검증 영역 결과 (Audit Results)

| 검증 영역 | 평가 항목 | 검증 결과 | 상세 내역 |
|:---|:---|:---:|:---|
| **1. 정적 코드 분석 (Static Analysis)** | Mock / Dummy / Synthetic 코드 전면 제거 여부 | **PASS** | `src/`, `tests/` 전역에 걸쳐 `SyntheticVehicle`, `EvalSyntheticVehicle`, 난수 기반 임의 좌표 생성 일체 부재. 과거 폐기 코드는 `backup/` 디렉토리에 정상 격리됨. |
| **2. 런타임 추적 및 단언문 (Runtime Tracing)** | SUMO & Communications 진성 연동 및 Anti-Mocking 단언문 | **PASS** | `python verify_environment.py` 실행 완료 (Exit Code 0). 51대 전 차량 실제 변위(`Delta x != 0`) 및 Rayleigh SINR 경합 확률 산출 확인. `AoiV2IEnv.step()` 내 4대 Anti-Mocking 단언문 검증 완료. |
| **3. 200,000 스텝 준비성 (200k Readiness)** | 장기 훈련 파이프라인, 로깅, 체크포인트, 메모리 관리 | **PASS** | `hot_swap_trainer.py` 내 `run_hot_swap_training()`이 200k 스텝(2,000 steps x 100 ep)을 완벽 지원하며 TensorBoard 9개 지표, 주기적/최고 성능 가중치 저장, `gc.collect()` 및 CUDA 캐시 비우기 완비. |
| **4. 사전 계산 중단 준수 (Pre-Compute Halt)** | 대규모 연산 착수 전 정지 및 승인 대기 준수 | **PASS** | 기본 스크립트 실행 및 테스트는 10~20스텝 더미 검증에 한정되며, 사용자의 명시적 승인 없이 200k 스텝 대량 훈련을 임의로 실행하지 않도록 안전하게 정지됨. |

---

## 3. 세부 기술 검증 증거 (Forensic Evidence Chain)

### [검증 1] 정적 코드 분석 및 잔존 Mock 스캔
- `src/` 및 `tests/` 전역 대상 grep 검색 (`SyntheticVehicle`, `EvalSyntheticVehicle`, `random.uniform` 기반 좌표 합성 등) 수행 결과:
  - `src/`: 0건 (완전 무결)
  - `backup/evaluate.py_old`, `backup/hpo.py_old`: 과거 코드가 `GEMINI.md` 규칙 5에 따라 `backup/`에 정상 격리 보관됨.
  - `tests/conftest.py`: 단위 테스트용 mock fixture(`synthetic_vehicle_node`)는 vectorizer 정규화 로직 단위 테스트에 국한되며 런타임 프로덕션 코드와 완전 분리됨.
- Facade / Stub 구현 검증: 9종 베이스라인(HybridPPO, HybridSAC, HybridTD3, MAPPO, HyARPPO, MPDQN, PureAoI, DuelingQAoI, SACAoI) 모두 실제 PyTorch 기반 신경망 연산, 경사 하강 업데이트, 버퍼 적재 로직이 정상 탑재됨.

### [검증 2] 런타임 환경 검증 (`verify_environment.py`)
`export PATH=/home/imnyj/venv/bin:$PATH; python verify_environment.py` 실행 결과:
```
======================================================================
GENUINE SUMO V2I AoI ENVIRONMENT INTEGRATION VERIFICATION
======================================================================
>>> [Phase 1/5] Testing SUMO File Generation (make_sumo_set.py)
  [OK] File exists: generated.nod.xml (2,601 bytes)
  [OK] File exists: generated.edg.xml (9,190 bytes)
  [OK] File exists: generated.net.xml (298,611 bytes)
  [OK] File exists: generated.rou.xml (49,039 bytes)
  [OK] File exists: generated.add.xml (5,433 bytes)
  [OK] File exists: generated.sumocfg (584 bytes)
  [OK] File exists: rsu.poi.xml (2,389 bytes)
  [OK] Validated nodes: total=45, RSUs(traffic_lights)=25, dead_ends=20

>>> [Phase 2/5] Initializing Genuine AoiV2IEnv with Real SUMO
  Instantiated AoiV2IEnv with genuine TraCI/libsumo interface.
  [OK] env.reset() completed at simulation time: 60.0s
  [OK] Target RSU selected: N39 at coordinates (10800.0, 10800.0)
  [OK] Active vehicles registered in target cell: 25
  [OK] All initial 16-dim state vectors are verified within [-1.0, 1.0].

>>> [Phase 3/5] Executing 20-Step Rollout & Checking Coordinate Trajectory
  Step 00 (t=61.0s): Active Vehicles=28 | Mean Reward=-0.3541 | Tx Attempts=25
  Step 04 (t=65.0s): Active Vehicles=34 | Mean Reward=-0.4159 | Tx Attempts=28
  Step 08 (t=69.0s): Active Vehicles=40 | Mean Reward=-0.3860 | Tx Attempts=39
  Step 12 (t=73.0s): Active Vehicles=46 | Mean Reward=-0.4239 | Tx Attempts=66
  Step 16 (t=77.0s): Active Vehicles=49 | Mean Reward=-0.4643 | Tx Attempts=83
  Step 19 (t=80.0s): Active Vehicles=51 | Mean Reward=-0.4333 | Tx Attempts=101
  [OK] Vehicles with verified physical displacement (Delta x != 0): 51/51
  [OK] Cumulative Metrics Summary: {'registrations_E1': 51, 'updates_E2': 43, 'exits_E3': 0, 'intervals': 43, 'mean_interval_err_integral': 597.6528, 'mean_interval_duration_s': 7.814, 'mean_err_lowspeed': 0.0, 'mean_err_highspeed': 120.1606, 'err_max': 549.2093, 'tx_attempts': 101, 'tx_success': 43, 'tx_fail': 58, 'tx_success_rate': 0.4257, 'mean_success_prob': 0.4075, 'mean_contenders_per_ch': 3.2772}

>>> [Phase 4/5] Testing Communications Layer & Rayleigh Fading SINR
  Solo transmitter (100m, 25dBm) success prob: 0.9988
  8-vehicle contention on same subchannel avg success prob: 0.0156
  [OK] Communications Rayleigh fading SINR and interference calculation verified.

>>> [Phase 5/5] Testing Anti-Mocking Assertion Triggers (Fault Injection)
  [Test 5.1] Testing Assertion 1 (Time regression detection)...
    [PASSED] Correctly caught simulated time regression: FATAL: Simulation time regression: 10.0 <= 12.0
  [Test 5.2] Testing Assertion 2 (Coordinate freeze / zero displacement detection)...
    [PASSED] Correctly caught simulated coordinate freeze: FATAL: Vehicle speed is 15.0 m/s but coordinate did not change from (100.0, 200.0)!
  [Test 5.3] Testing Assertion 3 (Invalid uplink probability detection)...
    [PASSED] Correctly caught invalid probability: FATAL: Uplink success probability 1.5 out of [0, 1]!
  [Test 5.4] Testing Assertion 4 (Reward formula violation detection)...
    [PASSED] Correctly caught reward formula violation: FATAL: Reward mismatch: 0.8 != -0.3400000000000001
  [OK] All 4 anti-mocking assertion triggers verified.

>>> ALL ENVIRONMENT VERIFICATION TESTS PASSED (100% GENUINE)
```

### [검증 3] 단기 더미 테스트 검증 (`pytest tests/test_dummy_verification.py -v`)
- `tests/test_dummy_verification.py` 14개 전 테스트 3.90초 만에 100% PASS:
  - `test_d1_sumo_real_environment_10_steps`: PASS
  - `test_d2_all_9_baseline_models_instantiation_and_inference` (9종 모델): PASS
  - `test_d3_hot_swap_gradient_step_and_parameter_sync`: PASS
  - `test_d4_optuna_hpo_single_trial_10_steps`: PASS
  - `test_d5_benchmark_evaluation_single_run_10_steps`: PASS
  - `test_d6_total_dummy_run_execution_under_15_seconds`: PASS

### [검증 4] AoiV2IEnv 4대 Anti-Mocking Assertion 검증
`src/aoi_env.py` 내 `step()` 함수에 하드코딩된 단언문 확인:
1. **Assertion 1 (시뮬레이션 시간 전진)**: `assert current_time > self._prev_sim_time` — 가짜 시간 루프 또는 정체 감지 시 즉시 크래시.
2. **Assertion 2 (실제 좌표 이동 및 변위)**: `assert dist_moved > 0.0` (속도 1.0 m/s 초과 시) — 고정 좌표 더미 반환 시 즉시 크래시.
3. **Assertion 3 (물리 채널 모델 실행)**: `comm.judge_uplink` 무선 Rayleigh SINR 연산 필수 호출 및 $p \in [0, 1]$ 검증 — 무선 채널 우회 시 즉시 크래시.
4. **Assertion 4 (보상 함수 정합성)**: $R_t = -(w_1 e^2 + w_2 P_{tx} + w_3 C_{freq} + w_4 I_{red}) \le 0$ 수식 정밀 일치 검증 — 가짜 보상 주입 시 즉시 크래시.

### [검증 5] 200,000 스텝 구조적 완비성 및 사전 정지 준수
- `src/hot_swap_trainer.py`:
  - `run_hot_swap_training(total_steps=200000, episodes=100, ...)` 함수 완비.
  - TensorBoard SummaryWriter 연동 완료 (`Reward/EpisodicMean`, `Loss/MeanRecent`, `AoI/Mean`, `AoI/Peak`, `Error/Mean`, `Outage/Rate`, `Power/Avg_dBm`, `HotSwap/Count` 등).
  - 매 10 에피소드 및 Best 모델 체크포인트 저장 지원.
  - `gc.collect()` 및 CUDA 메모리 캐시 정리 루틴 탑재.
- Pre-Compute Halt 준수: 기본 실행 시 200,000 스텝 연산이 자동 실행되지 않으며, 사용자 최종 승인 후 실행되도록 대기 상태 유지.

---

## 4. 부차적 발견 사항 및 권고사항 (Minor Technical Note)
- **SUMO 생성기 전역 변수 격리**: `src/sumo/make_sumo_set.py` 내 `NUM_BLOCKS` 전역 변수가 함수 호출 시마다 증가(`NUM_BLOCKS += 1`)하여, 독립 프로세스가 아닌 단일 프로세스 내에서 수십 번 반복 호출될 경우 XML 생성 크기가 비대해질 수 있습니다. `hot_swap_trainer.py`에서는 이를 사전에 `ss.NUM_BLOCKS = 5`로 고정 리셋하여 완벽히 방어하고 있으나, 추후 대규모 훈련 시 `make_sumo_set.py` 내부의 기본값 초기화를 함수 로컬화할 것을 권장합니다.

---

## 5. 최종 판정 (Final Forensic Verdict)
본 감사관은 `/home/imnyj/Workspace/paper4/coder/` 저장소가 **가짜 모의 객체 및 우회 구현체가 완전히 배제된 100% 진성(Genuine) SUMO 및 Rayleigh 무선 채널 기반 파이프라인**임을 확인하였으며, **CLEAN** 평결을 확정합니다.
