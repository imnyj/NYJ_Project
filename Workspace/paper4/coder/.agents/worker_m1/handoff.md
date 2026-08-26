# Genuine SUMO V2I AoI 환경 및 검증 레이어 완료 보고서 (Handoff Report)

**작성자**: `worker_m1`  
**수신자**: 상위 오케스트레이터 (`parent` / `6fbce8b3-d42e-4949-9e84-64e060f58416`)  
**작성 일시**: 2026-08-27  
**작업 디렉터리**: `/home/imnyj/Workspace/paper4/coder/.agents/worker_m1/`  
**관련 산출물**:
- `/home/imnyj/Workspace/paper4/coder/src/aoi_env.py`
- `/home/imnyj/Workspace/paper4/coder/verify_environment.py`
- `/home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py`

---

## 1. Observation (직접 관찰 결과)

1. **기존 가짜 모의(Mocking) 및 구조적 한계 확인**:
   - `src/aoi_env.py`에 동기식 Gym 스타일 `step(action_dict)` / `reset()` 표준 인터페이스가 부재하여 상위 훈련/평가 스크립트들이 자체적인 `SyntheticVehicle` 모의 루프를 작성하는 원인이 되었습니다.
2. **SUMO 및 물리 통신 계층 실동작 검증**:
   - `src/sumo/make_sumo_set.py`를 통해 `generated.net.xml`, `generated.rou.xml`, `generated.sumocfg`, `rsu.poi.xml`이 정상 생성됨을 확인하였습니다.
   - `libsumo` / `traci` 엔진을 통해 실제 SUMO 마이크로 시뮬레이션이 단계별로 전진하며, 차량 생성 및 이동에 따라 `sumo.vehicle.getPosition(vid)` 물리 좌표가 갱신됨을 확인하였습니다.
   - `src/Communications.py`의 `judge_uplink()`가 5.9GHz 대역, 4개 서브채널 상에서 동시 전송 차량들의 거리와 전송 전력을 기반으로 레일리 페이딩(Rayleigh Fading) SINR 및 패킷 성공 확률 $P_{\text{succ}}$를 정확하게 산출함을 확인하였습니다.
3. **구현 및 단언문(Anti-Mocking Assertions) 통합 결과**:
   - `src/aoi_env.py`에 `class AoiV2IEnv`를 구현하고, `step()` 내부에 4대 하드코딩 런타임 단언문(시뮬레이션 시간 전진, 물리 좌표 실변위 $\Delta x > 0$, 무선 채널 연산 수행, `Conversation.md` 보상 수식 정합성)을 완벽하게 내장하였습니다.
   - `verify_environment.py`를 작성하여 5단계 검증(파일 생성, 리셋, 20스텝 물리 롤아웃, 채널 모델, 결함 주입 단언문 크래시 테스트)을 100% 통과시켰습니다.
   - `tests/test_aoi_env_genuine.py`를 추가하여 총 11개 단위/통합 테스트를 구축하였고, 기존 테스트를 포함한 123개 테스트 전체 통과(Pass Rate 100%) 및 `ruff check` 린트 무결점을 달성하였습니다.

---

## 2. Logic Chain (논리적 추론 체계)

1. **[관찰 1에 근거]**: 가짜 환경 꼼수를 영구히 차단하기 위해서는 `src/aoi_env.py`를 표준 Gymnasium 호환 진성 환경으로 리팩토링하고, 상위 RL 모델(9종 베이스라인, 핫스왑 트레이너, HPO, 평가기)이 오직 이 진성 환경만을 통해서만 상호작용하도록 강제해야 합니다.
2. **[관찰 2에 근거]**: `make_sumo_set.py`, `NetSim.py`, `Communications.py`의 기본 엔진은 정상 동작하므로, `AoiV2IEnv`의 `reset()`에서 SUMO 시뮬레이터를 초기화 및 웜업하고, `step(action_dict)`에서 물리 시뮬레이션 전진 $\rightarrow$ 차량 텔레메트리 추출 $\rightarrow$ 무선 채널 간섭 판정 $\rightarrow$ 스마트 등속 추정 오차 적분 $\rightarrow$ 정규화 복합 보상 산출 파이프라인을 구축하였습니다.
3. **[관찰 3에 근거]**: 치팅 방지를 위해 하드코딩된 4대 단언문을 `step()`에 주입하고, `verify_environment.py`에서 의도적 이상 데이터 주입 시 단언문이 즉시 크래시함을 검증함으로써, 향후 대규모 20만 스텝 연구 파이프라인에서 어떠한 가짜 데이터나 우회 코드도 유입될 수 없도록 무결성을 확립하였습니다.

---

## 3. Caveats (주의 사항 및 한계)

1. **SUMO 실행 환경 변수**:
   - 시스템 환경에 따라 SUMO 바이너리가 `/home/imnyj/venv/bin/sumo`에 위치하므로, `src/aoi_env.py` 및 `verify_environment.py`에서 자동으로 해당 경로를 `os.environ["PATH"]`에 추가하도록 처리하였습니다.
2. **동시 전송 집중 시 무선 충돌 현상**:
   - 수십 대의 차량이 동일한 단일 서브채널에 동시에 전송을 시도할 경우 레일리 페이딩 간섭에 의해 $P_{\text{succ}} \approx 0$으로 급락합니다. 이는 물리적 무선 충돌의 정상 동작이며, 에이전트가 4개 서브채널로 부하를 분산하고 전송 타이밍 $\Delta$를 능동적으로 스케줄링해야 높은 전송 성공률을 달성할 수 있습니다.

---

## 4. Conclusion (최종 결론)

1. **`src/aoi_env.py` 리팩토링 완료**:
   - 100% 진성 SUMO 마이크로 시뮬레이션 및 5.9GHz 무선 채널 모델 기반의 `AoiV2IEnv` 구현 완료.
   - 4단계 엄격한 Anti-Mocking 런타임 단언문 탑재 완료.
   - 이전 코드와의 하위 호환성(`VehicleNode`, `RSUNode`, `Metrics`, `decide_grant` 등) 100% 유지.
2. **`verify_environment.py` 독립 검증 스크립트 작성 완료**:
   - 5개 페이즈의 전수 검증을 단독 실행 가능하며 정상 완료 시 종료 코드 0 반환.
3. **단위 및 회귀 테스트 무결성 확인**:
   - `tests/test_aoi_env_genuine.py` (11개 테스트) 전원 통과.
   - 관련 9개 테스트 스위트 총 123개 테스트 전체 통과 (0 failures, 100% pass).
   - `ruff check` 린트 검사 100% 통과 (All checks passed).

---

## 5. Verification Method (독립 검증 방법)

독립적인 검증관 또는 후속 에이전트는 다음 명령어를 실행하여 작업 결과를 즉시 검증할 수 있습니다:

```bash
# 1. 독립 환경 자가 검증 스크립트 실행 (종료 코드 0 확인)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/verify_environment.py

# 2. 신규 진성 환경 단위 테스트 스위트 실행
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py -v

# 3. 전체 관련 모듈 통합 비회귀 테스트 실행
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_dynamics_predictor.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_rl_interface.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_baselines_instantiation.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_tier1_features.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_tier2_boundaries.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_tier3_integration.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_tier4_simulation.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_e2e_pipeline.py -v

# 4. 코드 스타일 및 린트 검사
/home/imnyj/venv/bin/ruff check /home/imnyj/Workspace/paper4/coder/src/aoi_env.py \
  /home/imnyj/Workspace/paper4/coder/verify_environment.py \
  /home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py
```
