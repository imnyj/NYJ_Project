# Milestone 1 Code & Architecture Review Report (`review.md`)

- **검토자**: Milestone 1 검증 리뷰어 및 적대적 감사관 (`reviewer_m1_1`)
- **검토 일시**: 2026-08-24
- **대상 작업**: Milestone 1 (`code/aoi_tracker.py`, `code/sim_engine.py`, `code/resnet_moe_agent.py`, `code/moe_agent.py`, `code/test_m1_audit.py`)
- **작업자**: `worker_m1`

---

## 1. Review Summary

**Verdict**: **APPROVE (승인)**

Milestone 1의 모든 핵심 요구사항(6개 통신 거리 구간별 실측 AoI 추적, `sim_engine.py`의 `distance_aoi` 및 `cbr_history` 시계열 메트릭 추출 연동, `ResNetMoEAgent` 및 `MoEAgent`의 128차원 잠재 특징 벡터 및 Softmax 게이팅 가중치 추출 API `get_latent_and_gate` 구현)이 결함 없이 완벽하게 구현되었음을 확인하였습니다.

모의 데이터(Mock Data)나 하드코딩된 결과값, 파사드(Facade) 구현 등의 무결성 위반(Integrity Violation) 사례는 일절 발견되지 않았으며, 엄격한 적대적 스트레스 테스트(경계값, 웜업 격리, 메모리 누수 방지, 극단값 입력, 훈련 모드 보존 등)를 전수 통과하였습니다.

---

## 2. Findings & Detailed Assessments

### [Good Practice] 거리 구간별 벡터화 계산 및 수학적 정밀성
- `code/aoi_tracker.py:140-180`: 거리 계산 $d = \sqrt{\Delta x^2 + \Delta y^2}$을 NumPy 벡터 브로드캐스팅으로 수행하여 대규모 차량 환경에서도 오버헤드를 최소화함.
- `np.clip((dists / 50.0).astype(int), 0, 5)`를 통해 6개 거리 구간([0~50), [50~100), [100~150), [150~200), [200~250), [250~300]m)을 정확히 인덱싱하고 중심거리(25, 75, 125, 175, 225, 275m)와 일치시킴.
- `get_distance_aoi(as_dict=True)` 및 `get_distance_aoi_dict()`를 제공하여 하위 모듈이 리스트 형태와 표준 딕셔너리 스키마 형태를 자유롭게 활용할 수 있도록 인터페이스 확장성을 확보함.

### [Good Practice] `get_latent_and_gate` API의 견고한 타입 유연성 및 부작용 방지
- `code/resnet_moe_agent.py:178-226` & `code/moe_agent.py:170-215`:
  - Python List, 1D NumPy `(5,)`, 2D Batch NumPy `(B, 5)`, 1D/2D PyTorch Tensor 등 다양한 입력 타입을 자동으로 변환 지원.
  - 추론 전 `was_training = self.q_network.training`을 기록하고 `eval()` 모드로 전환 후 `torch.no_grad()` 환경에서 안전하게 추론한 뒤 원래 상태로 복원함으로써 모델 평가 및 훈련 중 의도치 않은 상태 오염(State Mutation) 방지.
  - 게이팅 가중치의 Softmax 확률 속성($\sum_k g_k = 1.0, 0 \le g_k \le 1$)을 완벽히 만족.

### [Good Practice] 연속 시계열 및 하위 호환성 유지
- `code/sim_engine.py:633, 664-676`: 웜업 이후 스텝별 글로벌 CBR 평균이 `cbr_history` 리스트에 누적되어 결과 딕셔너리에 온전히 반환됨을 확인.
- 기존 사용되던 키인 `"M1_mean_AoI"`와 신규 표준 키 `"AoI_mean"`, `"distance_aoi"`, `"distance_pdr"`가 모두 안전하게 포함됨.

---

## 3. Verified Claims

| 검증 항목 | 검증 방법 | 결과 |
|---|---|---|
| **6개 거리 구간 AoI 누적 로직** | `code/test_m1_audit.py` 및 `etc/scripts/test_m1_adversarial.py` 실행 | **PASS** (6개 버킷 정확성 확인) |
| **거리 경계값 처리 ($d=0, 49.999, 50.0, 299.999, 300.0, 300.001$)** | 경계값 지정 차량 배치 스트레스 테스트 | **PASS** (경계 분기 및 300m 초과 필터링 확인) |
| **웜업 구간 메트릭 격리** | 웜업 내 이벤트 주입 후 기록 여부 검증 | **PASS** (웜업 기간 데이터 완벽 배제) |
| **패킷 유실 시 AoI 선형 증가 및 수신 시 리셋** | 스텝별 패킷 송수신 시뮬레이션 | **PASS** (지연 시간 비례 증가 및 리셋 일치) |
| **차량 퇴장 시 메모리 정리 (`remove_vehicle`)** | 퇴장 차량 ID 삭제 후 내부 딕셔너리 잔여 검사 | **PASS** (모든 페어 딕셔너리 정리 확인) |
| **`ResNetMoEAgent` Latent/Gate 추출** | 단일/배치/텐서/리스트 입력 및 차원 (`128`, `3`), Softmax 합 검증 | **PASS** (모양 및 확률 정합성 100%) |
| **`MoEAgent` Latent/Gate 추출** | 단일/배치 입력 및 차원 (`128`, `2`), Softmax 합 검증 | **PASS** (베이스라인 인터페이스 통일 확인) |
| **`sim_engine.py` 통합 메트릭 반환** | SUMO 시뮬레이션 구동 후 반환 딕셔너리 필드 검사 | **PASS** (`distance_aoi`, `cbr_history`, `distance_pdr` 정상 반환) |
| **기존 연계 회귀 테스트** | `test_comm_module.py`, `test_c3_reward.py`, `test_m7_nest.py`, `test_m8_local_cbr.py` | **PASS** (전수 통과, 회귀 없음) |

---

## 4. Adversarial Stress Test Results (`etc/scripts/test_m1_adversarial.py`)

```
============================= test session starts ==============================
collected 7 items

etc/scripts/test_m1_adversarial.py::TestAoITrackerAdversarial::test_exact_distance_boundaries PASSED [ 14%]
etc/scripts/test_m1_adversarial.py::TestAoITrackerAdversarial::test_warmup_isolation PASSED [ 28%]
etc/scripts/test_m1_adversarial.py::TestAoITrackerAdversarial::test_aoi_growth_and_reset_on_reception PASSED [ 42%]
etc/scripts/test_m1_adversarial.py::TestAoITrackerAdversarial::test_vehicle_removal_cleanup PASSED [ 57%]
etc/scripts/test_m1_adversarial.py::TestMoEAgentsAdversarial::test_mode_preservation_and_no_grad PASSED [ 71%]
etc/scripts/test_m1_adversarial.py::TestMoEAgentsAdversarial::test_extreme_input_values PASSED [ 85%]
etc/scripts/test_m1_adversarial.py::TestMoEAgentsAdversarial::test_various_input_types PASSED [100%]

============================== 7 passed in 4.26s ===============================
```

---

## 5. Coverage Gaps & Unverified Items

- **Coverage Gaps**: 없음 (Milestone 1 요구사항 및 인터페이스 전체 커버).
- **Unverified Items**: 없음 (단위 테스트, 적대적 스트레스 테스트, SUMO 시뮬레이션 연계 테스트 전수 검증 완료).

---

## 6. Next Steps for Downstream Milestones
1. Milestone 1 승인에 따라 오케스트레이터는 Milestone 2(가상 데이터/구 모델 파일 정리 및 Optuna 하이퍼파라미터 재최적화)로의 전환을 승인할 수 있습니다.
2. `ResNetMoEAgent.get_latent_and_gate()` 및 `aoi_tracker.get_distance_aoi()`는 향후 M4 평가 스윕(`run_density_sweep_parallel.py`) 및 M5 시각화 파이프라인(`prepare_data.py`)에서 직접 호출되어 100% 실측 데이터를 제공하게 됩니다.
