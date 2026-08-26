# Genuine 환경 및 SUMO 연동 레이어 인수인계 보고서 (Handoff Report)

**작성자**: `explorer_survey_genuine_1`  
**인계 대상**: 상위 Orchestrator / Worker 에이전트  
**작성 일시**: 2026-08-27  
**작업 디렉터리**: `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_1/`

---

## 1. Observation (직접 관찰 결과)

1. **SUMO 네트워크 및 트래픽 생성 (`src/sumo/make_sumo_set.py:38-148`)**:
   - `make_sumo_files()`는 `generated.nod.xml`에 격자 교차로 노드를 `traffic_light`로, 외곽 경계 노드를 `dead_end`로 기록합니다.
   - `netconvert`를 통해 `generated.net.xml`로 변환하고, TAZ 설정(`generated.add.xml`), RSU 위치(`rsu.poi.xml`), 차량 발생 흐름(`generated.rou.xml`), 메인 설정(`generated.sumocfg`)을 생성합니다.
2. **TraCI 및 물리 시뮬레이션 연동 (`src/NetSim.py:460-613`)**:
   - `SumoNetSim`은 `libsumo` 또는 `traci`를 구동하여 매 스텝 `sumo.simulationStep()`을 실행합니다.
   - `sumo.vehicle.getPosition(vid)`를 통해 실제 SUMO 시뮬레이션의 물리 좌표를 `VehicleNode.pos`에 반영하며, `sumo.vehicle.getNextTLS()` 및 `sumo.trafficlight.getRedYellowGreenState()`를 통해 실시간 신호 정보를 추출합니다.
3. **무선 채널 및 간섭 모델 (`src/Communications.py:155-214`)**:
   - 5.9 GHz 대역, semi-open road 경로 손실($PL_0 \approx 47.85\text{ dB}$, $\alpha = 2.3$), 4개 서브채널, 0 dB 복조 임계치($\gamma_{th} = 1.0$)를 적용합니다.
   - `judge_uplink(group)` 함수는 동일 서브채널 내 동시 전송 차량들의 거리에 따른 수신 전력($S_i$) 및 상호 간섭($I_k$)을 바탕으로 독립 레일리 페이딩(Rayleigh Fading) 폐쇄형 성공 확률 $P_{\text{succ}} = \exp(-\gamma_{th}N_0/S) \prod_k \frac{1}{1 + \gamma_{th}I_k/S}$를 정확히 계산합니다.
4. **가짜 환경(Mocking / Synthetic Bypass) 적발 지점**:
   - `src/evaluate.py:190-268`: `class EvalSyntheticVehicle`에서 `px = rsu_pos[0] + dist * math.cos(angle)`와 같은 극좌표 삼각함수로 가짜 차량을 생성하고 SUMO를 배제한 채 평가를 수행함.
   - `src/hpo.py:213-275`: `class SyntheticVehicle` 및 `evaluate_model_in_env()`에서 SUMO 없이 파이썬 루프 상에서 모의 차량을 전개함.
   - `src/hot_swap_trainer.py:613-664`: `run_hot_swap_training()` 내부에서 `vehicles = [f"veh_{i}" ...]`와 `estimation_error = float(np.random.uniform(0.05, 0.4))`로 가짜 데이터를 주입함.

---

## 2. Logic Chain (논리적 추론 체계)

1. **[관찰 1, 2, 3]에 근거**: `make_sumo_set.py`, `NetSim.py`, `Communications.py`의 핵심 물리 시뮬레이션 및 무선 통신 간섭 엔진은 실제 수학 모델과 SUMO TraCI API를 기반으로 정교하게 구현되어 있습니다.
2. **[관찰 4]에 근거**: 그러나 상위 실행 스크립트(`evaluate.py`, `hpo.py`, `hot_swap_trainer.py`)는 `aoi_env.py`에 동기식 Gym 스타일 `step()` 인터페이스가 없다는 이유로 `SyntheticVehicle`이라는 가짜 수학 모델을 우회 생성하여 SUMO를 건너뛰었습니다.
3. **[요구사항 R1, R4 및 Conversation.md]에 근거**: 이 모의(Mocking) 꼼수는 전면 폐기되어야 하며, `aoi_env.py`를 표준 진성 Gym 환경으로 통합하고 `step()` 내부에 실시간 TraCI 좌표 변화 및 `Communications.py` 호출 여부를 검사하는 하드코딩 단언문을 주입해야만 합니다.
4. **결론 도출**: 따라서, (1) 가짜 모의 클래스를 전면 삭제하고, (2) `aoi_env.py`에 강력한 Anti-Mocking 단언문 4종을 내장하며, (3) 물리 좌표 변위와 통신 연산을 100% 자가 검증하는 `verify_environment.py`를 도입해야 진정한 20만 스텝 연구 파이프라인의 무결성이 보장됩니다.

---

## 3. Caveats (주의 사항 및 한계)

- `libsumo`는 프로세스 내 C++ 바인딩으로 단일 프로세스에서 극도로 빠르지만, 다중 스레드 환경에서 동시 호출 시 주의가 필요합니다. 다중 에이전트/스레드 운용 시 `traci` 모드로 전환하거나 프로세스 격리를 사용해야 합니다.
- SUMO 네트워크 생성 시 `netconvert` 바이너리가 `/home/imnyj/venv/bin/netconvert` 또는 시스템 PATH에 존재해야 합니다 (환경 검증 시 확인 완료).

---

## 4. Conclusion (최종 진단 및 실행 결론)

1. **가짜 코드 전면 폐기**: `src/evaluate.py`, `src/hpo.py`, `src/hot_swap_trainer.py` 내의 `SyntheticVehicle`, `EvalSyntheticVehicle`, `random.uniform()` 오차 생성부를 완전히 삭제할 것.
2. **`aoi_env.py` 리팩토링 및 4단계 하드코딩 단언문 적용**:
   - 단언문 1: `sumo.simulation.getTime()` 정상 전진 및 `libsumo` 활성화 검증.
   - 단언문 2: `sumo.vehicle.getPosition()` 실제 물리 좌표 유효성 및 속도 발생 시 변위($\Delta x \ne 0$) 검증.
   - 단언문 3: 패킷 전송 시 `comm.judge_uplink()`의 레일리 페이딩 간섭 계산 및 반환값 검증.
   - 단언문 4: `Conversation.md`의 정규화 보상 수식 $R_t = - (w_1 \text{Norm}(e^2) + w_2 \text{Norm}(P_{tx}) + w_3 \text{Norm}(C_{freq}) + w_4 \mathbb{I}_{redundant})$ 준수 검증.
3. **`verify_environment.py` 스크립트 작성**: SUMO 파일 생성, 환경 리셋, 20스텝 물리 좌표 이동, 통신 계산, 단언문 크래시 방어 테스트를 자동 검증하도록 구현.

---

## 5. Verification Method (독립 검증 방법)

1. **보고서 파일 검증**:
   - `view_file`로 `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_1/analysis.md` 및 `handoff.md`의 내용을 확인.
2. **차기 구현 시 검증 커맨드**:
   - SUMO 파일 생성 검증: `python -c "import src.sumo.make_sumo_set as s; s.make_sumo_files()"`
   - 환경 검증 스크립트 실행: `python verify_environment.py`
   - 전체 파이프라인 무결성 테스트: `pytest tests/test_tier3_integration.py tests/test_tier4_simulation.py`
