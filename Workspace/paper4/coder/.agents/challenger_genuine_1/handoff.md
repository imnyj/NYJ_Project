# Adversarial Challenge & Empirical Verification Handoff Report

- **작성 에이전트**: challenger_genuine_1 (Empirical Challenger)
- **대상 모듈**: `AoiV2IEnv` (`src/aoi_env.py`), `verify_environment.py`, `Communications.py`, `SUMOManager.py`
- **최종 판정**: **APPROVE** (진성 SUMO 연동 및 물리 무선 채널 모델 무결성 100% 실증 승인)

---

## 1. Observation (관측 사실)

### 1.1 `python verify_environment.py` 실행 결과
- **실행 명령**: `python verify_environment.py`
- **실행 결과**: Exit Code 0, 전체 5단계(Phase 1~Phase 5) 검증 100% 정상 통과
```text
======================================================================
GENUINE SUMO V2I AoI ENVIRONMENT INTEGRATION VERIFICATION
======================================================================

======================================================================
>>> [Phase 1/5] Testing SUMO File Generation (make_sumo_set.py)
======================================================================
  [OK] File exists: generated.nod.xml (2,601 bytes)
  [OK] File exists: generated.edg.xml (9,206 bytes)
  [OK] File exists: generated.net.xml (298,611 bytes)
  [OK] File exists: generated.rou.xml (49,039 bytes)
  [OK] File exists: generated.add.xml (5,433 bytes)
  [OK] File exists: generated.sumocfg (584 bytes)
  [OK] File exists: rsu.poi.xml (1,659 bytes)
  [OK] Validated nodes: total=45, RSUs(traffic_lights)=25, dead_ends=20

======================================================================
>>> [Phase 2/5] Initializing Genuine AoiV2IEnv with Real SUMO
======================================================================
  Instantiated AoiV2IEnv with genuine TraCI/libsumo interface.
  [OK] env.reset() completed at simulation time: 60.0s
  [OK] Target RSU selected: N39 at coordinates (10800.0, 10800.0)
  [OK] Active vehicles registered in target cell: 40
  [OK] All initial 16-dim state vectors are verified within [-1.0, 1.0].

======================================================================
>>> [Phase 3/5] Executing 20-Step Rollout & Checking Coordinate Trajectory
======================================================================
  Step 00 (t=61.0s): Active Vehicles=42 | Mean Reward=-0.4346 | Tx Attempts=40
  Step 04 (t=65.0s): Active Vehicles=47 | Mean Reward=-0.4607 | Tx Attempts=42
  Step 08 (t=69.0s): Active Vehicles=54 | Mean Reward=-0.4208 | Tx Attempts=55
  Step 12 (t=73.0s): Active Vehicles=62 | Mean Reward=-0.4406 | Tx Attempts=95
  Step 16 (t=77.0s): Active Vehicles=69 | Mean Reward=-0.4477 | Tx Attempts=117
  Step 19 (t=80.0s): Active Vehicles=74 | Mean Reward=-0.4431 | Tx Attempts=140
  [OK] Vehicles with verified physical displacement (Delta x != 0): 73/74
  [OK] Cumulative Metrics Summary: {'registrations_E1': 74, 'updates_E2': 38, 'exits_E3': 0, 'intervals': 38, 'mean_interval_err_integral': 594.2687, 'mean_interval_duration_s': 7.4211, 'mean_err_lowspeed': 0.0, 'mean_err_highspeed': 137.5709, 'err_max': 452.0238, 'tx_attempts': 140, 'tx_success': 38, 'tx_fail': 102, 'tx_success_rate': 0.2714, 'mean_success_prob': 0.248, 'mean_contenders_per_ch': 5.3571}

======================================================================
>>> [Phase 4/5] Testing Communications Layer & Rayleigh Fading SINR
======================================================================
  Solo transmitter (100m, 25dBm) success prob: 0.9988
  8-vehicle contention on same subchannel avg success prob: 0.0156
  [OK] Communications Rayleigh fading SINR and interference calculation verified.

======================================================================
>>> [Phase 5/5] Testing Anti-Mocking Assertion Triggers (Fault Injection)
======================================================================
  [Test 5.1] Testing Assertion 1 (Time regression detection)...
    [PASSED] Correctly caught simulated time regression: FATAL: Simulation time regression: 10.0 <= 12.0
  [Test 5.2] Testing Assertion 2 (Coordinate freeze / zero displacement detection)...
    [PASSED] Correctly caught simulated coordinate freeze: FATAL: Vehicle speed is 15.0 m/s but coordinate did not change from (100.0, 200.0)!
  [Test 5.3] Testing Assertion 3 (Invalid uplink probability detection)...
    [PASSED] Correctly caught invalid probability: FATAL: Uplink success probability 1.5 out of [0, 1]!
  [Test 5.4] Testing Assertion 4 (Reward formula violation detection)...
    [PASSED] Correctly caught reward formula violation: FATAL: Reward mismatch: 0.8 != -0.3400000000000001
  [OK] All 4 anti-mocking assertion triggers verified.

======================================================================
>>> ALL ENVIRONMENT VERIFICATION TESTS PASSED (100% GENUINE)
======================================================================
```

---

### 1.2 적대적 스트레스 테스트 (`stress_test_env.py`) 실행 결과
- **테스트 스크립트 경로**: `/home/imnyj/Workspace/paper4/coder/.agents/challenger_genuine_1/stress_test_env.py`
- **실행 명령**: `python /home/imnyj/Workspace/paper4/coder/.agents/challenger_genuine_1/stress_test_env.py`
- **실행 결과**: Exit Code 0, 5개 적대적 스위트 전면 통과
```text
==============================================================================
STARTING EMPIRICAL ADVERSARIAL STRESS TESTING SUITE
Target: AoiV2IEnv & Communications.py & SUMO Simulation
==============================================================================

==============================================================================
  >>> SUITE 1: Boundary & Extreme Action Space Stress Testing
==============================================================================
    - Negative Infinity -> delta=0.50s, ch=0, p=20.00dBm (OK)
    - Positive Infinity -> delta=10.00s, ch=3, p=30.00dBm (OK)
    - Negative Out-of-Bounds Channel -> delta=5.25s, ch=2, p=25.00dBm (OK)
    - Large Out-of-Bounds Channel -> delta=5.25s, ch=3, p=25.00dBm (OK)
    - All Zeros -> delta=5.25s, ch=0, p=25.00dBm (OK)
    - Float Channel Rounding -> delta=5.25s, ch=3, p=25.00dBm (OK)
    - ... (17 sub-verifications completed)
  [PASS] Suite 1 (Action Space & Boundaries): 17 tests verified

==============================================================================
  >>> SUITE 2: Rayleigh Fading Channel & Massive Contention Stress Testing
==============================================================================
    - Power 20.0dBm distance sweep monotonically attenuated: 1m -> 1.0000 down to 5000m -> 3.177524e-14
    - Power 25.0dBm distance sweep monotonically attenuated: 1m -> 1.0000 down to 5000m -> 5.389962e-05
    - Power 30.0dBm distance sweep monotonically attenuated: 1m -> 1.0000 down to 5000m -> 4.468985e-02
    - Contention N=  1: Mean Success Probability = 0.994031
    - Contention N=  2: Mean Success Probability = 0.496849
    - Contention N=  4: Mean Success Probability = 0.125906
    - Contention N=  8: Mean Success Probability = 0.010178
    - Contention N= 16: Mean Success Probability = 0.000098
    - Contention N= 32: Mean Success Probability = 0.000000
    - Contention N= 64: Mean Success Probability = 0.000000
    - Contention N=128: Mean Success Probability = 0.000000
    - Contention N=256: Mean Success Probability = 0.000000
    - Near-Far Capture Effect: Strong/Close P_succ=0.9996 vs Weak/Far P_succ=0.00000006
    - Edge distances: 0m -> 1.0000, 100,000m -> 0.00000000e+00
    - Empty transmitter group handled cleanly -> {}
  [PASS] Suite 2 (Communications & Rayleigh SINR): 9 contention levels & physical laws verified

==============================================================================
  >>> SUITE 3: Live Fault Injection & Anti-Mocking Assertion Bypass Tests
==============================================================================
  [Attack 3.1] Testing Time Regression / Freeze Assertion in live step()...
  [Attack 3.2] Testing Vehicle Coordinate Freeze Assertion in live step()...
  [Attack 3.3] Testing Out-of-Bounds Coordinate Assertion in live step()...
  [Attack 3.4] Testing Corrupted Uplink Probability Assertion in live step()...
  [Attack 3.5] Testing Carrier Frequency Constant Assertion...
    - Attack 3.1 caught as expected: FATAL: Simulation time regression/freeze detected: 62.0 <= 99999.0
    - Attack 3.2 caught as expected: FATAL: Vehicle F18_0.0 speed is 20.0 m/s but coordinate did not change from (10795.2, 11213.430195344126)!
    - Attack 3.3 caught as expected: FATAL: Vehicle F18_0.0 position (9999999.0, 9999999.0) is out of SUMO grid bounds [0, 12000.0]!
    - Attack 3.4 caught as expected: FATAL: Uplink success probability 1.88 for F18_0.0 out of [0, 1]!
    - Attack 3.5 caught as expected: FATAL: Communications.FREQ_HZ is corrupted: 2400000000.0
  [PASS] Suite 3 (Anti-Mocking Assertion Triggers): 5 live attack vectors verified and blocked

==============================================================================
  >>> SUITE 4: Multi-Cycle Reset & TraCI Zombie Process Audit
==============================================================================
    - Initial SUMO processes before test: []
    - Cycle 1/5 (seed=1000) completed: t=60.0s, active=31
    - Cycle 2/5 (seed=1001) completed: t=60.0s, active=37
    - Cycle 3/5 (seed=1002) completed: t=60.0s, active=32
    - Cycle 4/5 (seed=1003) completed: t=60.0s, active=32
    - Cycle 5/5 (seed=1004) completed: t=60.0s, active=33
    - Independent instance 1/3 cleanly executed and closed
    - Independent instance 2/3 cleanly executed and closed
    - Independent instance 3/3 cleanly executed and closed
    - Final SUMO processes after test: []
    - ZERO zombie / orphaned TraCI processes detected (Clean Lifecycle)
  [PASS] Suite 4 (Reset Lifecycle & Zombie Process Audit): Clean termination across 8 reset cycles without zombie processes

==============================================================================
  >>> SUITE 5: High-Contention 50-Step Full Rollout & Invariant Audit
==============================================================================
    - Rollout started: Target RSU=N39 at (10800.0, 10800.0), Initial Active=32
    - Step 00 (t=61.0s): Active=34 | Reward=-0.4527 | TxAttempts=32 | TxSuccess=0 | TxFail=32 | SuccessRate=0.0% | Contenders/Ch=32.0
    - Step 10 (t=71.0s): Active=50 | Reward=-0.8227 | TxAttempts=404 | TxSuccess=0 | TxFail=404 | SuccessRate=0.0% | Contenders/Ch=37.3
    - Step 20 (t=81.0s): Active=62 | Reward=-0.8387 | TxAttempts=911 | TxSuccess=2 | TxFail=909 | SuccessRate=0.2% | Contenders/Ch=44.9
    - Step 30 (t=91.0s): Active=74 | Reward=-0.8361 | TxAttempts=1555 | TxSuccess=14 | TxFail=1541 | SuccessRate=0.9% | Contenders/Ch=53.1
    - Step 40 (t=101.0s): Active=87 | Reward=-0.8599 | TxAttempts=2327 | TxSuccess=23 | TxFail=2304 | SuccessRate=1.0% | Contenders/Ch=61.2
    - Step 49 (t=110.0s): Active=101 | Reward=-0.8404 | TxAttempts=3126 | TxSuccess=25 | TxFail=3101 | SuccessRate=0.8% | Contenders/Ch=68.3
    - Final 50-step metrics: {'registrations_E1': 101, 'updates_E2': 25, 'exits_E3': 0, 'intervals': 25, 'mean_interval_err_integral': 3899.4065, 'mean_interval_duration_s': 12.16, 'mean_err_lowspeed': 391.3231, 'mean_err_highspeed': 381.4324, 'err_max': 1340.5482, 'tx_attempts': 3126, 'tx_success': 25, 'tx_fail': 3101, 'tx_success_rate': 0.008, 'mean_success_prob': 0.0072, 'mean_contenders_per_ch': 68.2617}
  [PASS] Suite 5 (High-Contention 50-Step Rollout): 50 steps completed under maximum contention; All invariants verified

==============================================================================
FINAL ADVERSARIAL STRESS TEST SUMMARY
==============================================================================
  [PASS]  | Suite 1 (Action Space & Boundaries): 17 tests verified
  [PASS]  | Suite 2 (Communications & Rayleigh SINR): 9 contention levels & physical laws verified
  [PASS]  | Suite 3 (Anti-Mocking Assertion Triggers): 5 live attack vectors verified and blocked
  [PASS]  | Suite 4 (Reset Lifecycle & Zombie Process Audit): Clean termination across 8 reset cycles without zombie processes
  [PASS]  | Suite 5 (High-Contention 50-Step Rollout): 50 steps completed under maximum contention; All invariants verified
==============================================================================

>>> OVERALL VERDICT: ALL ADVERSARIAL CHALLENGES PASSED (100% GENUINE & ROBUST)
```

---

## 2. Logic Chain (논리 전개)

1. **하이브리드 액션 공간 극단값 디코딩 무결성**:
   - `ActionDecoder`의 $\Delta \in [0.5, 10.0]\text{s}$, $\text{ch} \in \{0, 1, 2, 3\}$, $P_{\text{tx}} \in [20.0, 30.0]\text{dBm}$ 매핑 로직은 입력값이 $\pm \infty$, 음수 채널 인덱스($-10$), 초과 채널 인덱스($999$) 등 극단적인 입력에 대해서도 예외 없이 물리적 안전 한계 내로 클램핑/모듈로 연산됨을 실증함 (Suite 1 관측).
   - PyTorch Tensor, NumPy array, Dict, Tuple, List 등 다형성 입력에 대해 정확한 디코딩을 수행함을 확인.

2. **Rayleigh 페이딩 및 물리적 무선 채널 간섭/충돌 역학**:
   - `Communications.judge_uplink()`는 단일 전송 시 $99.4\%$ 이상의 높은 성공 확률을 보이나, 동일 서브채널 내 동시 전송 차량 수가 $N=1 \to 256$으로 증가함에 따라 $P_{\text{succ}}$이 $0.994 \to 0.496 \to 0.010 \to 0.000$으로 단조 감소하여 실제 무선 충돌 및 간섭 현상을 충실히 모사함 (Suite 2 관측).
   - Near-Far Capture Effect 테스트에서 근거리/고출력 차량($30\text{ dBm}, 20\text{m}$)이 $P_{\text{succ}} = 0.9996$으로 원거리/저출력 다수 차량($20\text{ dBm}, 600\text{m}, P_{\text{succ}} \approx 6 \times 10^{-8}$)을 지배함을 확인.
   - 거리 $0\text{m}$부터 $100,000\text{m}$까지의 극단적 경계값 및 빈 그룹(`[]`) 입력 시에도 NaN/Inf 및 분모 0 오류 없이 안정적으로 동작함을 확인.

3. **안티 모킹 단언문(Anti-Mocking Assertion) 방어력 실증**:
   - `AoiV2IEnv.step()` 내부에 내장된 4대 핵심 단언문은 라이브 시뮬레이션 중 다음 결함 주입 공격을 모두 100% 감지하여 즉시 `AssertionError`를 발생시키고 실행을 차단함 (Suite 3 관측):
     - **공격 3.1 (시간 역행/정체)**: `FATAL: Simulation time regression/freeze detected` 발생 확인.
     - **공격 3.2 (차량 좌표 정체/스피드 불일치)**: `FATAL: Vehicle ... speed is 20.0 m/s but coordinate did not change` 발생 확인.
     - **공격 3.3 (격자 범위 이탈 좌표 조작)**: `FATAL: Vehicle ... position ... is out of SUMO grid bounds` 발생 확인.
     - **공격 3.4 (무선 전송 확률 1.0 초과 위조)**: `FATAL: Uplink success probability 1.88 ... out of [0, 1]` 발생 확인.
     - **공격 3.5 (반송파 주파수 상수 위조)**: `FATAL: Communications.FREQ_HZ is corrupted` 발생 확인.

4. **환경 리셋 수명주기 및 TraCI 좀비 프로세스 부재**:
   - 동일 인스턴스에 대한 5회 연속 리셋 및 3개 독립 인스턴스 순차 실행(총 8회 시뮬레이션 라이프사이클) 후 시스템 프로세스 감사 결과, 고아(Orphaned) 또는 좀비 SUMO 프로세스가 0개(`[]`)로 완전하게 자원이 해제됨을 확인 (Suite 4 관측).

5. **초고경합 50스텝 롤아웃 및 상태/보상 불변성 검증**:
   - 모든 차량이 매 스텝 최소 주기($0.5\text{s}$), 서브채널 0, 최대 출력($30\text{ dBm}$)으로 동시 전송하는 극단적 부하 환경에서 50스텝 동안 3,126건의 전송 시도 중 3,101건의 충돌 실패($99.2\%$ 패킷 드롭)가 발생하여 심각한 AoI 열화($\text{err\_max} = 1340.5\text{m}$)와 보상 페널티($-0.8404$)가 정상 누적됨을 확인 (Suite 5 관측).
   - 50스텝 전 과정에서 16차원 관측 벡터의 $[-1.0, 1.0]$ 경계 조건 및 보상의 음수 페널티 조건이 단 한 번의 위반 없이 유지됨을 확인.

---

## 3. Caveats (주의사항 및 권고사항)

1. **SUMO 네트워크 생성기의 `NUM_BLOCKS` 글로벌 상태**:
   - `src/sumo/make_sumo_set.py`의 `make_sumo_files()` 함수 내부에서 `global NUM_BLOCKS; NUM_BLOCKS += 1`이 수행되므로, 동일 파이썬 프로세스 내에서 이 함수를 반복 호출하면 격자 크기가 불필요하게 팽창할 수 있습니다.
   - `AoiV2IEnv._ensure_sumo_files()`는 파일이 이미 존재하는 경우 `make_sumo_files()`를 중복 호출하지 않도록 안전하게 방어되어 있으나, 타 모듈이나 테스트 코드에서 `make_sumo_files()`를 직접 호출할 때는 `NUM_BLOCKS = 5`로 사전 초기화 후 호출하는 패턴을 준수해야 합니다.
2. **SUMO Warmup Steps 권장값**:
   - 대규모 12km x 12km 격자망 특성상, 차량이 외곽 TAZ에서 출발하여 내부 RSU 통신 반경(800m)에 정주 도달하기 위해서는 최소 45초 이상의 워밍업 시간이 필요합니다. 기본 설정인 `warmup_steps = 60`을 유지할 것을 권장합니다.

---

## 4. Conclusion (최종 판정)

- **최종 판정**: **APPROVE** (승인)
- **근거**:
  - `verify_environment.py` 5단계 검증 100% 정상 통과.
  - 전용 적대적 스트레스 테스트 스위트(`stress_test_env.py`) 5개 전 항목 완전 통과.
  - Rayleigh 페이딩 SINR 물리 채널 연동, 하이브리드 액션 공간 디코딩, 16차원 관측 벡터 및 복합 페널티 보상 공식, 4대 안티 모킹 런타임 단언문의 완벽한 무결성과 강건성 실증 완료.

---

## 5. Verification Method (독립 재현 검증 방법)

다음 명령어를 통해 본 보고서의 모든 실증 결과를 독립적으로 재현 검증할 수 있습니다:

```bash
# 1. 진성 환경 5단계 기본 검증
python /home/imnyj/Workspace/paper4/coder/verify_environment.py

# 2. 5대 적대적 스트레스 테스트 스위트 실행
python /home/imnyj/Workspace/paper4/coder/.agents/challenger_genuine_1/stress_test_env.py

# 3. pytest 진성 환경 테스트 단위 검증
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py
```
