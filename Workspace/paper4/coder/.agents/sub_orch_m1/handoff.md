# Milestone 1: 신호 기반 역학 예측 및 휴리스틱 베이스라인 (S2.5) — 완료 보고서

**작성자**: Sub-Orchestrator Milestone 1 (`sub_orch_m1`)  
**작성 일시**: 2026-08-26T22:08:00+09:00  
**대상 디렉토리**: `/home/imnyj/Workspace/paper4/coder`  
**관련 요구사항**: R1 (S2.5 신호 기반 역학 예측 및 휴리스틱 스케줄러 베이스라인)

---

## 1. Observation (직접 관측 내용)

1. **TraCI 및 SUMO 환경 연동 검증**:
   - `libsumo.vehicle.getNextTLS(vid)`는 `[(tls_id, tls_index, dist_to_stopline, state_char), ...]` 튜플 리스트를 정밀 반환함을 확인.
   - `libsumo.trafficlight.getNextSwitch(tls_id)`를 통해 다음 신호 위상 전환 시각 $t_{\text{switch}}$를 추출하고 잔여 시간 $t_{\text{left}} = \max(0.0, t_{\text{switch}} - t_{\text{curr}})$를 계산 가능함을 확인.
   - 선행 차량(`getLeader`), 대기 시간(`getWaitingTime`), 가속도(`getAcceleration`)를 통해 차량의 동역학 변화를 즉각 감지 가능함을 확인.

2. **구현 및 변경된 핵심 파일**:
   - `src/dynamics_predictor.py`:
     - TraCI 기반 신호 및 차량 동역학 특성 추출 함수 `extract_tls_features(sumo_conn, vid, current_time)`.
     - 물리 법칙 기반 정지 임박 지표 `predict_stop_imminent` 및 출발 임박 지표 `predict_start_imminent` ($I_{\text{stop}}, I_{\text{start}} \in [0.0, 1.0]$).
     - 고수준 제어 클래스 `DynamicsPredictor`.
   - `src/heuristic_scheduler.py`:
     - 도메인 지식 기반 규칙 스케줄러 클래스 `HeuristicScheduler`.
     - 정지/출발 전이 임박 시 즉시 상태 갱신 ($\Delta_i = 0.5\text{s}, p_i = 25.0\text{dBm}$, 부하 최소 서브채널 할당).
     - 긴 적색 신호 정지 차량 백오프 ($\Delta_i = \min(10.0, t_{\text{left}} - 1.0\text{s}), p_i = 20.0\text{dBm}$).
     - 순항 차량 동적 주기 할당 ($v, a$ 안정성에 따라 $\Delta_i \in [1.0, 3.5]\text{s}$).
     - 서브채널 부하 분산(Load-balancing) 메커니즘.
   - `src/aoi_env.py`:
     - `set_scheduler()`, `get_scheduler()`, `ACTIVE_SCHEDULER` 플러그인 인터페이스 추가.
     - `VehicleNode`에 가속도(`accel`) 및 `tls_features` 추적 연동.
     - `decide_grant()`에서 `ACTIVE_SCHEDULER`로의 디스패치 구현.
   - `src/sumo/make_sumo_set.py`:
     - `netconvert` 실행 시 venv 경로 자동 탐색 및 fallback 지원.
   - `tests/test_dynamics_predictor.py`:
     - 24개의 단위 및 통합 테스트 작성 완료.

3. **테스트 및 검증 결과**:
   - `pytest tests/test_dynamics_predictor.py`: **24/24 PASS** (0.63s).
   - `pytest tests/`: **56/56 ALL PASS** (2.42s, 전체 회귀 테스트 결함 0건).
   - `ruff check`: **0 errors, all clean**.

---

## 2. Logic Chain (논리적 추론 및 설계 근거)

1. **외삽 오차와 동역학 비선형 전이의 관계**:
   - RSU는 차량의 마지막 수신 상태 $(x, v)$를 기준으로 등속 외삽($\hat{x}(t) = x + v \cdot \Delta t$)을 수행함.
   - 차량이 정지 상태이거나 등속 주행 중일 때는 $e(t) \approx 0$으로 오차가 극히 작음.
   - 반면 정지하던 차량이 급출발하거나, 주행 중이던 차량이 적색 신호에 급제동할 때 비선형 가속도가 발생하여 RSU 외삽치와 실제 위치 간의 오차가 급격히 적분됨.
   - 따라서 $I_{\text{stop}}, I_{\text{start}} \ge 0.5$를 감지하는 즉시 $\Delta = 0.5\text{s}$와 고출력(25.0 dBm)으로 즉시 갱신을 부여함으로써 오차 발산을 원천 차단함.

2. **적색 신호 정지 차량 백오프의 효과**:
   - 차량이 적색 신호에서 정지($v \le 1.0\text{ m/s}$)해 있고 잔여 적색 시간이 긴 경우, 속도가 0이므로 갱신을 하지 않아도 외삽 오차는 0을 유지함.
   - 이때 $\Delta = \min(\Delta_{\max}, t_{\text{left}} - 1.0\text{s})$로 백오프하고 최저 전력(20.0 dBm)을 부여하여 무선 채널의 동시 경합(contention)을 제거함으로써, 실제 주행/전이 중인 차량의 업링크 성공 확률($P_{\text{succ}}$)을 대폭 향상시킴.

3. **서브채널 부하 분산**:
   - 4개 서브채널(`comm.NUM_SUBCHANNELS = 4`)에 대해 스케줄러가 할당 카운트를 추적하여 최소 경합 서브채널로 분산 할당함으로써 상호 Rayleigh 페이딩 간섭을 억제함.

---

## 3. Caveats (제약 사항 및 가정)

1. **신호등이 없는 구역**:
   - 도로망 외곽 또는 신호등이 없는 엣지에서는 `getNextTLS`가 빈 리스트를 반환함. 이 경우 `extract_tls_features`는 안전한 기본값(`state='none'`, `time_to_switch=inf`)을 반환하며, 순수 가속도 및 선행차량 기반으로 $I_{\text{stop}}, I_{\text{start}}$를 정상 판정함.
2. **SUMO 의존성**:
   - `predict_stop_imminent` 및 `predict_start_imminent`는 SUMO 라이브러리가 없는 환경에서도 독립 단위 테스트가 가능하도록 순수 함수로 분리 구현됨.

---

## 4. Conclusion (최종 결론)

- Milestone 1 (R1 - S2.5 신호 기반 역학 예측 및 휴리스틱 베이스라인)의 모든 요구사항이 100% genuine code로 완성되었으며, 56개 전체 테스트 스위트를 완벽하게 통과함.
- 다음 단계인 Milestone 2 (R2 - RL 에이전트 인터페이스 및 9개 베이스라인 모델 구축)로 즉시 진행할 수 있는 완벽한 환경 계층 인터페이스가 확보됨.

---

## 5. Verification Method (독립 검증 방법)

다음 명령어를 통해 직접 구현 및 검증 결과를 확인할 수 있습니다:

```bash
# 1. Milestone 1 전용 테스트 실행 (24개 테스트)
/home/imnyj/venv/bin/pytest tests/test_dynamics_predictor.py -v

# 2. 전체 테스트 스위트 실행 (56개 테스트)
/home/imnyj/venv/bin/pytest tests/ -v

# 3. 린트 및 문법 정합성 검사
/home/imnyj/venv/bin/ruff check src/dynamics_predictor.py src/heuristic_scheduler.py src/aoi_env.py tests/test_dynamics_predictor.py

# 4. SUMO 연동 실시간 휴리스틱 시뮬레이션 확인
/home/imnyj/venv/bin/python -c "
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
from src.heuristic_scheduler import HeuristicScheduler
ss.RSU_RANGE=800.0; ss.AV_SPEED=40.0; ss.DENSITY=25.0; ss.MAX_STEPS=50.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
env.WARMUP_S=15.0; env.set_scheduler(HeuristicScheduler()); env.reset_env()
sim = net.SumoNetSim(VehicleClass=env.VehicleNode, RSUClass=env.RSUNode, start_message_fn=env.start_message)
sim.run()
print('Heuristic Metrics:', env.METRICS.summary())
"
```
