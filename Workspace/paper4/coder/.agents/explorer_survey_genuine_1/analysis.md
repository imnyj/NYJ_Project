# Genuine 환경 및 SUMO 연동 레이어 심층 분석 보고서

**작성자**: `explorer_survey_genuine_1`  
**작성 일시**: 2026-08-27  
**대상 디렉터리**: `/home/imnyj/Workspace/paper4/coder/`  
**관련 요구사항**: `ORIGINAL_REQUEST.md`, `scenario.md`, `Conversation.md`

---

## 1. 개요 및 분석 목적

본 조사는 SUMO 실환경 시뮬레이터(`make_sumo_set.py`, `NetSim.py`, `Communications.py`)와 강화학습 스케줄링 파이프라인(`aoi_env.py`, `rl_interface.py`, `dynamics_predictor.py`, `heuristic_scheduler.py`, `baselines/`, `hot_swap_trainer.py`, `hpo.py`, `evaluate.py`) 간의 연동 상태를 전수 조사하고, 이전에 잔존하던 가짜 환경(Mocking / Synthetic Bypass) 꼼수를 완전히 적발하여 제거하며, 100% 진성 SUMO 시뮬레이션 위에서 20만 스텝 이상 학습 및 평가가 가능하도록 엄격한 하드코딩 단언문(Anti-Mocking Hardcoded Assertions)과 `verify_environment.py` 사양을 설계하는 것을 목적으로 합니다.

---

## 2. 핵심 모듈별 동작 원리 및 연동 구조 분석

### 2.1 `src/sumo/make_sumo_set.py`: SUMO 네트워크 및 교통류 생성기
- **네트워크 파라미터**:
  - `RSU_RANGE = 800.0` m (RSU 통신 반경)
  - `OUTAGE_ZONE = 800.0` m (RSU 간 불감지대)
  - `EDGE_LENGTH = 2400.0` m (`RSU_RANGE * 2 + OUTAGE_ZONE`)
  - `GRID_SIZE = NUM_BLOCKS * EDGE_LENGTH` (격자망 크기)
  - `NUM_LANES = 2` (차선 수), `CORNER_SPEED_LIMIT = 50 / 3.6` m/s
- **파일 생성 프로세스**:
  1. `generated.nod.xml`: `(NUM_BLOCKS + 1) x (NUM_BLOCKS + 1)` 격자 형태로 노드 좌표를 생성. 내부 교차로는 `traffic_light` 타입, 외곽 경계 노드는 `dead_end` 타입으로 지정.
  2. `generated.edg.xml`: 양방향 2차선 에지 생성, 속도 한계 할당.
  3. `netconvert`: `subprocess.call`을 통해 `generated.net.xml`로 컴파일 (`--no-turnarounds`, `--junctions.limit-turn-speed` 적용).
  4. `generated.add.xml`: 외곽 경계 노드에 TAZ(Traffic Assignment Zone) sink/source shape를 생성하여 진출입로 구성.
  5. `generated.rou.xml`: 밀도(`DENSITY`)에 따라 `CalcP_GEN()`으로 차량 발생 확률($P_{gen}$)을 계산하여 `MAX_STEPS = 3600.0`초 동안의 `<flow>` 정의.
  6. `rsu.poi.xml`: `traffic_light` 타입의 노드 위치에 RSU POI 태그를 생성.
  7. `generated.sumocfg`: `generated.net.xml`, `generated.rou.xml`, `generated.add.xml, rsu.poi.xml`을 로드하도록 설정.

---

### 2.2 `src/NetSim.py` (`SumoNetSim`): TraCI 연동 및 물리 계층 이벤트 시뮬레이터
- **엔진 구성**:
  - `libsumo` (우선) 또는 `traci`를 통한 고속 SUMO 제어. `os.environ.setdefault("SUMO_USE_LIBSUMO", "1")`.
  - `EventSimulator`: `heapq` 기반 이벤트 큐로 통신 지연(전파 지연, 전송 지연) 및 주기적 스텝 이벤트를 관리.
- **`SumoNetSim` 라이프사이클**:
  - `__init__`: `generated.nod.xml`을 파싱하여 교차로 위치에 `RSUNode` 객체들을 생성하고 `rsu_dict`, `rsu_list`에 등록.
  - `run()`:
    - SUMO 실행 명령(`sumo -c generated.sumocfg --step-length 1.0 --no-step-log true ...`)을 `sumo.start()`로 호출.
    - 매 스텝 `sumo.simulationStep()`을 실행하여 `sumo.vehicle.getIDList()`로 활성 차량 목록을 획득.
    - 신규 차량 진입 시 `sumo.vehicle.getPosition(vid)`로 초기 좌표를 읽어 `VehicleNode`를 생성 및 등록.
    - 기존 차량에 대해 `node.pos = sumo.vehicle.getPosition(vid)`로 실제 SUMO 시뮬레이션 좌표를 실시간 동기화.
    - 이탈 차량은 `vehicles` 딕셔너리에서 제거.
    - 각 노드의 `update_dwell(current_time)`을 호출하여 상태 갱신, 속도 추정, 신호등 상태 확인 및 전송 큐 처리.
- **TraCI 래퍼 API**:
  - `GetPosition(vid)`: `sumo.vehicle.getPosition(vid)`
  - `GetSpeed(vid)`: `sumo.vehicle.getSpeed(vid)`
  - `GetAcceleration(vid)`: `sumo.vehicle.getAcceleration(vid)`
  - `GetSignalState(rsu_id, vid, dir_flag)`: `sumo.vehicle.getNextTLS(vid)` 및 `sumo.trafficlight.getRedYellowGreenState(rsu_id)`로 신호 상태(R=1, Y=2, G=3) 매핑.
  - `GetSignalChangeTime(rsu_id)`: `sumo.trafficlight.getNextSwitch(rsu_id) - sumo.simulation.getTime()`로 잔여 신호 시간 반환.

---

### 2.3 `src/Communications.py`: 물리 채널 및 동시 송신 간섭(SINR) 모델
- **물리 계층 상수**:
  - 중심 주파수: $f_c = 5.9\text{ GHz}$ (ITS 대역, `FREQ_HZ = 5.9e9`)
  - 경로 손실 지수: $\alpha = 2.3$ (`PL_EXP = 2.3`, semi-open road 환경)
  - 기준 거리(1m) 경로 손실: $PL_{0,\text{dB}} = 20 \log_{10}(4\pi f_c / c) \approx 47.85\text{ dB}$
  - 서브채널 수: `NUM_SUBCHANNELS = 4` (20 MHz 대역폭 중 서브채널당 5 MHz)
  - 잡음 지수: $NF = 9.0\text{ dB}$, 수신 잡음 전력 $N_0 = 10^{(-174 + 10\log_{10}(B) + NF)/10}\text{ mW}$
  - 복조 임계치: $\gamma_{th,\text{dB}} = 0.0\text{ dB}$ ($\gamma_{th} = 1.0$)
- **채널 수식 및 간섭 계산 (`judge_uplink`)**:
  - 거리 $d$에서의 수신 신호 전력:
    $$S_i = 10^{\frac{P_{tx,i} - (PL_0 + 10 \alpha \log_{10}(\max(d_i, 1)))}{10}}\text{ (mW)}$$
  - 동일 서브채널 내 타 차량 간섭 $I_{i} = \sum_{k \ne i} S_k$
  - 독립 레일리 페이딩(Rayleigh Fading) 하에서의 성공 확률:
    $$P_{\text{succ}, i} = \exp\left(-\gamma_{th}\frac{N_0}{S_i}\right) \prod_{k \ne i} \frac{1}{1 + \gamma_{th} \frac{S_k}{S_i}}$$
  - `judge_uplink(group)`: 동일 서브채널에 할당된 `[(vid, tx_dbm, dist), ...]` 그룹을 받아 각 차량의 실제 전송 성공 확률을 계산.

---

### 2.4 `src/aoi_env.py`: 추정 오차 및 V2I Uplink 환경
- **추정 모델 (Constant-Velocity Smart Extrapolation)**:
  - RSU는 차량의 마지막 수신 정보 $(p_{last}, v_{last}, t_{last})$를 기준으로 현재 시간 $t$에서의 차량 위치를 등속 추정:
    $$\hat{p}(t) = p_{last} + v_{last} \cdot (t - t_{last})$$
  - 실제 SUMO 차량 위치 $p_{true}(t)$와의 순간 유클리드 거리 오차:
    $$e(t) = \|p_{true}(t) - \hat{p}(t)\|_2$$
  - 정지 상태($v=0$)이거나 등속 주행 중인 차량은 $e(t) \approx 0$으로 유지되어 AoI가 증가해도 추정 오차는 0에 수렴.
- **이벤트 라이프사이클**:
  - `E1 Entry`: 통신 반경 진입 시 초기 등록 (`is_entry=True`, 직접 등록).
  - `E2 Update`: 스케줄링된 타이밍에 차량이 전송 큐(`pending_tx`)에 등록 $\rightarrow$ 1스텝 지연 후 `RSUNode._resolve_pending()`에서 `comm.judge_uplink()`를 통해 확률적 수신 결정 $\rightarrow$ 성공 시 RSU 테이블 갱신 및 오차 적분($\int e(t)dt$) 확정.
  - `E3 Exit`: 통신 반경 이탈 시 인터벌 종료 및 최종 오차 기록.

---

### 2.5 `src/dynamics_predictor.py` & `src/heuristic_scheduler.py`
- **신호 및 동역학 기반 예측**:
  - `predict_stop_imminent()`: 급감속($a \le -1.2\text{ m/s}^2$), 적색/황색 신호등 접근, 정지한 선행차량 접근 시 $I_{stop} = 1.0$ 산출.
  - `predict_start_imminent()`: 정지 상태에서 녹색 신호 점등, 적색 잔여 시간 $\le 2\text{s}$, 선행차량 출발, 발진 가속($a \ge 0.6\text{ m/s}^2$) 시 $I_{start} = 1.0$ 산출.
- **도메인 휴리스틱 스케줄러 (`HeuristicScheduler`)**:
  - 규칙 1 (전이 임박): $I_{stop} \ge 0.5$ 또는 $I_{start} \ge 0.5 \implies \Delta = 0.5\text{s}$, 고전력($25\text{ dBm}$), 최소 부하 서브채널 강제 갱신.
  - 규칙 2 (적색 신호 정지): 적색 잔여 시간 동안 백오프($\Delta = \min(10.0, t_{left}-1.0)$), 저전력($20\text{ dBm}$).
  - 규칙 3 (등속 순항): $\Delta = 3.5\text{s}$, 중간 전력.

---

## 3. 기존 코드베이스 내 가짜 모의(Mocking / Synthetic Bypass) 전수 조사

기존 코드베이스의 일부 스크립트에서 SUMO 시뮬레이터를 실제로 실행하지 않고, 순수 파이썬 난수로 가짜 차량 좌표와 오차를 시뮬레이션하던 치명적인 우회(Bypass) 꼼수를 확인하였습니다:

| 파일 경로 | 발견된 우회 코드 (Mocking Snippet) | 문제점 및 위험 요인 | 조치 사항 |
|---|---|---|---|
| `src/evaluate.py` (L190~464) | `class EvalSyntheticVehicle`<br>`px = rsu_pos[0] + dist * math.cos(angle)`<br>`v.pos[0] += v.vel[0] * dt` | SUMO 프로세스를 전혀 띄우지 않고 극좌표 삼각함수로 가짜 차량을 생성하여 벤치마크 수행 | **전면 폐기** 후 `SumoNetSim`을 물리적으로 구동하는 진성 평가 루프로 교체 |
| `src/hpo.py` (L213~441) | `class SyntheticVehicle`<br>`evaluate_model_in_env()` | Optuna HPO 시 SUMO를 배제하고 파이썬 루프 상에서 합성 차량으로 보상을 계산 | **전면 폐기** 후 진성 SUMO 환경 기반 Trial 평가 루프로 교체 |
| `src/hot_swap_trainer.py` (L613~664) | `vehicles = [f"veh_{i}" ...]`<br>`estimation_error = float(np.random.uniform(0.05, 0.4))` | 학습 루프에서 SUMO 없이 임의 난수 좌표와 `random.uniform()` 오차로 가짜 배치 생성 | **전면 폐기** 후 실시간 SUMO 스텝 기반 Transition 스트리밍으로 연동 |
| `src/aoi_env.py` | 표준 `gym.Env` 스타일의 `step()` 인터페이스 부재 | 외부 RL 모델이 동기식으로 SUMO 환경을 제어할 표준 API가 없어 상위 스크립트들이 Mock을 작성하게 됨 | 표준 `AoIEnv` 클래스 구현 및 `step()`, `reset()` 제공 |

---

## 4. `aoi_env.py` 내 엄격한 하드코딩 검증 단언문 (Anti-Mocking Assertions) 설계

학습 및 평가 과정에서 그 어떠한 하위 모듈도 가짜 데이터를 주입하거나 SUMO/통신 모듈을 우회할 수 없도록, `aoi_env.py`의 `step()` 및 상태 추출 함수 내부에 다음과 같은 강제 크래시 단언문을 하드코딩합니다.

### 4.1 Assertion 1: TraCI / libsumo 활성 및 시뮬레이션 시간 전진 검증
```python
# 1. SUMO 프로세스 및 시간 검증
assert sumo is not None, "FATAL: libsumo/traci is not imported or initialized!"
current_sumo_time = float(sumo.simulation.getTime())
assert current_sumo_time >= self._prev_sim_time, (
    f"FATAL: Simulation time regression detected: {current_sumo_time} < {self._prev_sim_time}"
)
assert hasattr(sumo.simulation, "getLoadedNumber"), "FATAL: Fake sumo module detected!"
```

### 4.2 Assertion 2: 실제 SUMO 차량 물리 좌표 및 이동량 검증
```python
# 2. SUMO 차량 ID 및 물리 좌표 유효성 검증
raw_vehicle_ids = sumo.vehicle.getIDList()
assert isinstance(raw_vehicle_ids, (list, tuple)), "FATAL: sumo.vehicle.getIDList() did not return a valid list!"

if len(raw_vehicle_ids) > 0:
    sample_vid = raw_vehicle_ids[0]
    pos = sumo.vehicle.getPosition(sample_vid)
    spd = sumo.vehicle.getSpeed(sample_vid)
    
    # 좌표 범위 검증 (make_sumo_set 기반 Grid 영역)
    assert 0.0 <= pos[0] <= self.grid_size and 0.0 <= pos[1] <= self.grid_size, (
        f"FATAL: Vehicle {sample_vid} position {pos} is out of SUMO grid bounds [0, {self.grid_size}]!"
    )
    
    # 이동 차량의 좌표 변화 검증 (속도가 존재할 때 좌표가 고정되어 있으면 치팅)
    if sample_vid in self._prev_vehicle_positions and spd > 1.0:
        prev_p = self._prev_vehicle_positions[sample_vid]
        dist_moved = math.hypot(pos[0] - prev_p[0], pos[1] - prev_p[1])
        assert dist_moved > 0.0, (
            f"FATAL: Vehicle {sample_vid} speed is {spd} m/s but coordinate did not change from {prev_p}!"
        )
    self._prev_vehicle_positions[sample_vid] = pos
```

### 4.3 Assertion 3: `Communications.py` (`judge_uplink`) 물리 계산 호출 검증
```python
# 3. Communications 모듈 진성 호출 검증
assert hasattr(comm, "judge_uplink"), "FATAL: Communications.judge_uplink is missing!"
assert hasattr(comm, "path_loss_db"), "FATAL: Communications.path_loss_db is missing!"
assert comm.FREQ_HZ == 5.9e9, f"FATAL: Communications.FREQ_HZ is corrupted: {comm.FREQ_HZ}"

# 패킷 전송 시 judge_uplink 호출 결과 검증
if len(pending_transmissions) > 0:
    succ_probs = comm.judge_uplink(pending_transmissions, num_subchannels=comm.NUM_SUBCHANNELS)
    assert isinstance(succ_probs, dict), "FATAL: judge_uplink must return a dict!"
    for vid, p in succ_probs.items():
        assert 0.0 <= p <= 1.0, f"FATAL: Uplink success probability {p} for {vid} is out of [0, 1]!"
```

### 4.4 Assertion 4: 보상 정규화 및 수식 엄격 검증 (`Conversation.md` 준수)
```python
# 4. Conversation.md 수식 준수: R_t = - (w1 * Norm(e^2) + w2 * Norm(P_tx) + w3 * Norm(C_freq) + w4 * I_redundant)
assert 0.0 <= norm_error_sq <= 1.0, f"FATAL: Normalized error {norm_error_sq} out of bounds!"
assert 0.0 <= norm_ptx <= 1.0, f"FATAL: Normalized power {norm_ptx} out of bounds!"
assert 0.0 <= norm_cfreq <= 1.0, f"FATAL: Normalized congestion {norm_cfreq} out of bounds!"
assert i_redundant in (0.0, 1.0), f"FATAL: I_redundant must be binary {i_redundant}!"
assert step_reward <= 0.0, f"FATAL: Penalty-based reward must be <= 0, got {step_reward}"
```

---

## 5. `verify_environment.py` 사양서 및 검증 시나리오

### 5.1 검증 스크립트 목적
`verify_environment.py`는 실제 SUMO 시뮬레이션 환경을 구동하여 다음 항목을 100% 자가 검증하고 테스트 성공 여부를 판정합니다:
1. `make_sumo_set.py`를 호출하여 네트워크 파일(`.net.xml`, `.rou.xml`, `.add.xml`, `.sumocfg`)이 정상 생성되는지 검증.
2. 진성 `AoIEnv` 환경을 초기화하고 `sumo.start()`가 에러 없이 물리 시뮬레이션을 시작하는지 검증.
3. 20 스텝 이상 `env.step(action)`을 수행하면서:
   - SUMO 내부 차량 좌표가 시간 경과에 따라 물리적으로 변경되는지 확인 ($\Delta x \ne 0$).
   - TraCI 신호등 정보(`getNextTLS`)가 실시간으로 수신되는지 확인.
   - `Communications.judge_uplink`가 호출되어 실제 SINR 및 패킷 성공률을 연산하는지 확인.
   - 16차원 정규화 State 벡터가 $[-1.0, 1.0]$ 범위 내에서 산출되는지 확인.
   - `Conversation.md`의 보상 수식이 정상 계산되는지 확인.

### 5.2 `verify_environment.py` 실행 흐름 사양
```python
def main():
    print("=== [1/5] Testing SUMO File Generation (make_sumo_set.py) ===")
    # make_sumo_files() 호출 및 XML 유효성 검사
    
    print("=== [2/5] Initializing Genuine AoIEnv with SUMO ===")
    # env = AoIEnv(config) 및 env.reset()
    
    print("=== [3/5] Executing 20 Step Rollout & Checking Coordinate Trajectory ===")
    # for step in range(20):
    #     obs, reward, done, info = env.step(action)
    #     좌표 변위 기록 및 TraCI 실시간 동기화 검증
    
    print("=== [4/5] Testing Communications Layer & Rayleigh Fading SINR ===")
    # 다중 차량 동시 송신 시 간섭 계산 및 성공 확률 검증
    
    print("=== [5/5] Testing Anti-Mocking Assertion Triggers ===")
    # 비정상 데이터 주입 시 하드코딩 assertion이 즉시 크래시를 유발하는지 검증
    
    print(">>> VERIFICATION SUCCESS: All Genuine SUMO & Communications integration tests PASSED!")
```

---

## 6. 결론 및 차기 단계 제안

1. **분석 요약**: SUMO 네트워크 생성기(`make_sumo_set.py`), TraCI 시뮬레이터(`NetSim.py`), 물리 계층 간섭 모델(`Communications.py`)은 완벽한 수학적·물리적 기반을 갖추고 있으나, 상위의 `evaluate.py`, `hpo.py`, `hot_swap_trainer.py`에 잔존하던 `SyntheticVehicle` 모의 루프를 전면 폐기해야 합니다.
2. **필수 구현 사항**:
   - `aoi_env.py`를 표준 진성 Gym 환경으로 리팩토링하고 4단계 하드코딩 단언문을 삽입.
   - `verify_environment.py`를 작성하여 100% 실제 시뮬레이션 기반 환경 검증 완료.
   - `evaluate.py`, `hpo.py`, `hot_swap_trainer.py`가 진성 `aoi_env.py`를 통해서만 20만 스텝 대규모 실험을 진행하도록 수정.
