# Milestone 1 독립 검증 및 적대적 리뷰 보고서 (`review.md`)

- **검토자**: Milestone 1 검증 리뷰어 (`reviewer_m1_2`)
- **수행 일시**: 2026-08-24
- **대상 파일**:
  - `code/aoi_tracker.py`
  - `code/sim_engine.py`
  - `code/resnet_moe_agent.py`
  - `code/moe_agent.py`
  - `code/test_m1_audit.py`
- **최종 판정 (Verdict)**: **APPROVE (승인)**

---

## 1. 종합 평가 요약 (Review Summary)

Milestone 1에서 구현된 핵심 인터페이스 및 메트릭 추출 파이프라인(`distance_aoi`, `cbr_history`, `get_latent_and_gate`)에 대해 독립적인 소스 코드 정밀 검토, 단위/통합 테스트 스위트 실행, 그리고 극한 경계 조건에 대한 적대적 스트레스 테스트(Adversarial Stress Testing)를 수행하였습니다.

검토 결과:
1. **무결성(Integrity)**: 인위적인 하드코딩 결과값, 가짜 모의(Mock) 데이터 배열, 더미 구현이 일체 없음을 확인하였습니다.
2. **경계 조건 및 예외 처리(Boundary & Exception Handling)**: 
   - 0~300m 통신 반경 외 차량(300m 초과), 0m 거리, 정확한 경계 거리(50m, 100m, ..., 300m) 처리가 안전하게 벡터화 및 클리핑(`np.clip(..., 0, 5)`) 처리되어 있습니다.
   - 특정 거리 구간에 차량이 전혀 없는 빈 구간(Empty Bin)에 대해서도 Zero Division이나 NaN 발생 없이 안전하게 `0.0`으로 기본값이 반환됩니다.
3. **신경망 활성화 추출(Activation Extraction)**:
   - `ResNetMoEAgent` 및 `MoEAgent`의 `get_latent_and_gate`는 단일 벡터 `(5,)`, 배치 `(B, 5)`, 파이썬 리스트, PyTorch 텐서 입력을 모두 지원하며, `torch.no_grad()` 하에서 모델의 원래 훈련/평가 모드(`training`)를 보존하면서 정확히 128차원 잠재 벡터와 합이 1.0인 Softmax 게이팅 가중치를 추출합니다.
4. **시뮬레이션 및 테스트 검증(Simulation & Verification)**:
   - 신규 감사 테스트 스위트 `code/test_m1_audit.py` 6개 항목 100% 통과(5.12s 소요)를 독립적으로 재현 검증하였습니다.
   - 자체 제작한 적대적 스트레스 테스트(`stress_test.py`)를 통해 이상 입력, 차량 제거 시 메모리 누수 방지, 채널 감쇠 모델의 안정성을 완벽히 확인하였습니다.

---

## 2. 세부 검토 내역 (Detailed Findings)

### 2.1 `code/aoi_tracker.py`
- **구현 검토**:
  - `dist_aoi_sum`, `dist_aoi_count`, `dist_aoi_samples`를 6개 버킷(25, 75, 125, 175, 225, 275m)으로 관리.
  - `step()`에서 유효 차량 간 거리를 계산하고 `bin_indices = np.clip((dists / 50.0).astype(int), 0, 5)`로 버킷 인덱싱 수행.
  - `get_distance_aoi(as_dict=False)` 및 `get_distance_aoi_dict()`에서 `count == 0`일 때 `0.0`을 반환하여 NaN 방지.
  - `remove_vehicle(vid)` 호출 시 출발 차량의 모든 페어 상태(`last_received_gen_time`, `current_aoi`, `cam_rx_count`)를 안전하게 정리하여 장기 실행 시 메모리 누수 방지.
- **판정**: **양호 (Pass)**

### 2.2 `code/sim_engine.py`
- **구현 검토**:
  - `distance_aoi = aoi_tracker.get_distance_aoi()`를 반환 딕셔너리에 추가.
  - `cbr_history`는 웜업 이후 매 100ms 스텝마다 `cbr_mean`을 기록하여 시계열 추적 지원.
  - `simulate_receptions()` 내에서 송수신 거리별 Nakagami-m 감쇠 확률 `p_rx_arr` 및 로컬 CBR 충돌 팩터 `col_factors = np.maximum(0.1, 1.0 - rcv_cbrs * 0.8)`을 물리적으로 연동 계산.
  - `distance_pdr` 계산 시 `dist_tx_counts[b] > 0` 조건으로 Division by Zero 방어.
- **판정**: **양호 (Pass)**

### 2.3 `code/resnet_moe_agent.py` & `code/moe_agent.py`
- **구현 검토**:
  - `get_latent_and_gate(state)` 메서드 추가:
    - 5D 상태 -> 2-block ResNet Feature Extractor -> 128D 잠재 특징 벡터 추출.
    - 128D 특징 -> Softmax Gating Network -> 3D 전문가 가중치 (또는 2D) 추출.
  - 입력 차원 자동 분기: 1차원 `(5,)` 입력 시 `(128,)`, `(3,)` 반환, 2차원 `(B, 5)` 입력 시 `(B, 128)`, `(B, 3)` 반환.
  - `was_training = self.q_network.training`을 기록하여 호출 후 기존 모드로 복원.
- **판정**: **양호 (Pass)**

---

## 3. 검증된 항목 (Verified Claims)

| 검증 항목 | 검증 방법 | 결과 |
|---|---|---|
| AoI 거리별 6구간 집계 정확성 | `code/test_m1_audit.py::TestAoITrackerDistance` & `stress_test.py` | PASS |
| 빈 버킷 NaN 방지 및 reset 초기화 | `stress_test.py` 빈 구간 및 리셋 검증 | PASS |
| ResNetMoE 128D 잠재벡터 및 3D 게이트 추출 | `code/test_m1_audit.py::TestMoEActivationExtraction` | PASS |
| 배치 및 단일 입력 차원 정합성 | `stress_test.py` 배치(128) 및 단일 텐서 입력 테스트 | PASS |
| SUMO 시뮬레이션 메트릭(`distance_aoi`, `cbr_history`, `distance_pdr`) 통합 | `code/test_m1_audit.py::TestSimEngineMetrics` 실환경 구동 | PASS |
| 채널 모델 극한치(0m, 10km, CBR=1.0) 처리 | `stress_test.py` 채널 모델 극한값 검증 | PASS |

---

## 4. 적대적 도전 및 스트레스 테스트 결과 (Stress Test Results)

- **시나리오 1: 차량 0대 또는 1대만 존재하는 경우**
  - 결과: AoI step 계산 시 예외 없이 `0.0` 반환 확인 (PASS).
- **시나리오 2: 통신 반경(300m) 바깥 차량 간 통신 시도**
  - 결과: 통신 범위 마스크에 의해 정상 필터링되어 거리 버킷 누적 오염 없음 (PASS).
- **시나리오 3: 300.0m 정확한 경계값 및 300.1m 초과값**
  - 결과: `np.clip`에 의해 300.0m는 버킷 5에 정상 배정되고, 300.1m는 통신 범위 외로 제외됨 (PASS).
- **시나리오 4: 이종 데이터 타입 입력 (List, NumPy Array, PyTorch Tensor)**
  - 결과: `get_latent_and_gate`가 모든 형태를 수용하고 NumPy ndarray로 일관되게 반환 (PASS).
- **시나리오 5: 호출 중 신경망 모드 변경 부작용**
  - 결과: 추론 전후 `train()` / `eval()` 상태가 엄격하게 보존됨 (PASS).

---

## 5. 최종 결론

Worker가 수행한 Milestone 1 구현 사항은 요구사항 명세(PROJECT.md 및 ORIGINAL_REQUEST.md)를 100% 충족하며, 코드의 안정성, 예외 방어, 수학적 정합성, 무결성이 완벽함을 확인하여 **APPROVE**로 최종 판정합니다.
