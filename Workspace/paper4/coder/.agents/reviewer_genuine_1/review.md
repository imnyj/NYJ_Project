# Genuine SUMO Environment & Verification Layer 코드 리뷰 및 적대적 평가 보고서

**작성자**: `reviewer_genuine_1` (Reviewer & Critic)  
**일자**: 2026-08-27  
**대상 모듈**:
- `src/aoi_env.py` (Genuine Gymnasium-style V2I AoI Scheduling Environment)
- `verify_environment.py` (Standalone E2E Verification Suite)
- `src/Communications.py` (5.9 GHz ITS Rayleigh fading SINR & Channel Contention)
- `src/NetSim.py` (Event simulator & Node baseline)
- `tests/test_aoi_env_genuine.py` (11 Unit/Integration Tests & Fault Injection)
- `tests/test_tier3_integration.py` (Cross-Feature Integration Tests)

---

## 1. Review Summary (검토 요약)

**최종 판정 (Verdict)**: **APPROVE (승인)**

본 리뷰는 가짜 시뮬레이션(Mock/Synthetic bypass)을 원천 차단하고, 실제 SUMO 마이크로 시뮬레이션과 5.9GHz 물리 Rayleigh 페이딩 무선 채널 모델을 완벽하게 결합한 진짜 환경(`AoiV2IEnv`) 및 검증 계층(`verify_environment.py`)의 구현 무결성을 정밀 검증하였습니다.

---

## 2. 세부 검증 항목별 결과

### 2.1 Genuine SUMO 마이크로 시뮬레이션 연동 및 라이프사이클
- `src/aoi_env.py`의 `AoiV2IEnv`는 `libsumo`/`traci`를 직접 기동하여 도로망, 경로, 신호등(RSU)을 실제 시뮬레이션합니다.
- `reset()` 시 60초의 워밍업 단계를 거쳐 셀 내 차량을 정상적으로 스폰시키며, 16차원 정규화 관측 벡터($[-1.0, 1.0]$)를 RSU 관점에서 정확히 벡터화합니다.
- `step()` 실행 시 `sumo.simulationStep()`을 통해 물리 시간을 실제로 1초씩 전진시키며, 차량의 $x, y$ 좌표를 SUMO로부터 실시간 추출합니다.

### 2.2 물리 무선 통신 계층 (5.9GHz Rayleigh Fading SINR)
- `src/Communications.py`의 `judge_uplink()`를 정직하게 호출하여 4개 서브채널 상의 동시 전송 차량들 간 상호 간섭(SINR) 및 레일리 페이딩 수신 성공 확률($P_{succ}$)을 계산합니다.
- 단독 전송 시 높은 성공률($> 0.99$), 8대 동시 충돌 시 성공률 급감($\approx 0.015$) 등 실제 통신 물리 법칙이 정확하게 반영되었습니다.

### 2.3 Conversation.md 보상 수식의 수학적 엄밀성
- 보상 수식: $R_t = -(w_1 \cdot \text{Norm}(e_t^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant})$
- 모든 4개 요소($\text{Norm}(e_t^2), \text{Norm}(P_{tx}), \text{Norm}(C_{freq}), \mathbb{I}_{redundant}$)가 $[0, 1]$ 범위로 정규화되며, 최종 보상은 상시 음수 패널티($R_t \le 0$)로 엄격하게 산출됩니다.

### 2.4 4대 안티 모킹(Anti-Mocking) 하드코딩 단언문 검증
`AoiV2IEnv.step()` 내부에 다음 4가지 핵심 무결성 단언문이 탑재되어 있습니다:
1. **Assertion 1 (SUMO Time Advance)**: `current_time > prev_sim_time` 및 `libsumo/traci` 실체 검증.
2. **Assertion 2 (Real Vehicle Coordinates & Displacement)**: 실수형 좌표 범위 검증 및 속도 $v > 1.0\text{ m/s}$ 주행 차량의 물리적 변위($\Delta x > 0$) 검증.
3. **Assertion 3 (Real Channel Invocation)**: `Communications.judge_uplink` 호출 여부 및 확률 유효성($0 \le P_{succ} \le 1$, NaN/Inf 부재) 검증.
4. **Assertion 4 (Mathematical Reward Invariant)**: Conversation.md 수학 공식과 실제 계산값 간 엄밀한 일치($\text{abs\_tol}=10^{-5}$) 및 $R_t \le 0$ 검증.

`verify_environment.py` (Phase 5) 및 `test_aoi_env_genuine.py` (Test 7~10)를 통해 인위적 오류 주입(Fault Injection) 시 4대 단언문이 100% 정상 차단(AssertionError 발생)함을 확인하였습니다.

---

## 3. 적대적 스트레스 테스트 및 무결성 분석 (Adversarial Analysis)

| 공격 / 장애 시나리오 | 환경 동작 및 방어 기제 | 검증 결과 |
| :--- | :--- | :--- |
| **시간 동결 / 역행 공격** | Assertion 1에 의해 즉각 `FATAL: Simulation time regression/freeze detected` 발생 및 중단 | **방어 성공** |
| **좌표 고정 (가짜 주행) 공격** | Assertion 2에 의해 $v > 1.0\text{ m/s}$ 차량의 $\Delta x = 0$ 발생 시 `FATAL: coordinate did not change` 발생 | **방어 성공** |
| **채널 계산 우회 / 가짜 확률** | Assertion 3에 의해 확률 범위 $[0, 1]$ 위반 또는 계산 누락 시 `FATAL: judge_uplink did not evaluate...` 발생 | **방어 성공** |
| **보상값 조작 / 부호 왜곡** | Assertion 4에 의해 수학적 공식과 불일치하거나 양수 보상 시 `FATAL: Reward calculation mismatch` 발생 | **방어 성공** |
| **차량 밀집 / 폭주 상황** | 서브채널별 전송 분할 및 Rayleigh SINR 상호 간섭 수식으로 안전하게 수렴 | **정상 작동** |

---

## 4. 테스트 수행 결과

1. **`python verify_environment.py`**:
   - Phase 1 (SUMO File Generation): **PASS** (45개 노드, 25개 RSU 신호등 교차로 검증)
   - Phase 2 (AoiV2IEnv Reset & State Vector): **PASS** (16차원 $[-1, 1]$ 벡터 검증)
   - Phase 3 (20-Step Physical Rollout): **PASS** (60/62대 실체 변위 $\Delta x \neq 0$, 44회 전송 성공)
   - Phase 4 (Rayleigh Fading SINR): **PASS** (단독 0.9988 vs 경합 0.0156)
   - Phase 5 (Anti-Mocking Fault Injection): **PASS** (4개 단언문 오류 주입 차단 검증)
   - **종합 결과: Exit Code 0 (100% Genuine Success)**

2. **`pytest tests/test_aoi_env_genuine.py tests/test_tier3_integration.py`**:
   - `test_aoi_env_genuine.py`: 11 / 11 PASSED
   - `test_tier3_integration.py`: 4 / 4 PASSED
   - **총 15개 테스트 통과 (5.41s 소요)**

---

## 5. 코드 품질 및 타이핑
- 모든 클래스 및 함수에 명확한 Type Hinting(`Tuple`, `Dict`, `Optional`, `np.ndarray`) 적용 완료.
- Gymnasium 인터페이스 규격(`reset() -> (obs, info)`, `step() -> (obs, reward, term, trunc, info)`) 준수.
- 상세한 Docstring 및 학술적 배경 설명 포함.

---

## 6. 결론
`src/aoi_env.py` 및 관련 검증 계층은 가짜 환경 꼼수(Mocking)가 완전히 제거되었으며, 실제 물리 시뮬레이터와 통신 계층이 완전하게 통합되어 학술 연구 및 강화학습 학습을 위한 완벽한 신뢰성을 확보하였습니다.
