# Milestone 1 적대적 스트레스 테스트 보고서 (Stress Test Report)

- **검증 일시**: 2026-08-24T01:36:20Z
- **검증 에이전트**: `challenger_m1_1` (Critic / Specialist)
- **테스트 스크립트**: `/home/imnyj/Workspace/paper4/etc/scripts/test_m1_stress.py`, `/home/imnyj/Workspace/paper4/code/test_m1_audit.py`
- **검증 대상 모듈**: `code/aoi_tracker.py`, `code/sim_engine.py`, `code/resnet_moe_agent.py`
- **최종 판정**: **APPROVE** (모든 적대적 스트레스 테스트 및 불변식 통과)

---

## 1. Challenge Summary (적대적 검증 요약)

**Overall risk assessment**: **LOW**

Milestone 1에서 구현된 3개 핵심 모듈(`aoi_tracker.py`, `sim_engine.py`, `resnet_moe_agent.py`)에 대해 극한의 경계 조건(차량 0대/1대/500대 초고밀도), 비정상 상태값(극단값 $\pm 10^4$, 코시 난수 노이즈), 텐서 차원(1D/2D 배치 크기 1~512), 무선 채널 모델 감쇄 및 CBR 충돌 인자의 수학적 단조성 검증을 수행하였습니다. 총 24개 테스트 케이스(스트레스 테스트 18개 + 감사 테스트 6개)를 직접 실행하여 전건 통과(100% PASS)를 확인하였습니다.

---

## 2. Challenges & Detailed Stress-Testing Analysis (상세 검증 항목)

### [Low Risk] Challenge 1: 차량 수 경계값 및 대규모 고밀도 환경에서의 안정성 (AoITracker & sim_engine)
- **가정 검증**: 차량 수가 0대, 1대이거나 통신 반경(300m) 바깥에 고립되어 있을 때, 또는 500대 이상의 초고밀도 환경에서 ZeroDivisionError, IndexError, NaN이 발생하지 않아야 함.
- **공격 시나리오 (Attack Scenarios)**:
  1. 차량 수 $N=0$ 상태에서 warmup 이전/이후 step 호출 및 `get_distance_aoi()`, `get_pdr()`, `get_mean_aoi()` 조회.
  2. 단일 차량 $N=1$ 상태에서 CAM 브로드캐스트 후 step 및 메트릭 조회.
  3. 두 차량 간 거리 $1000\text{m} > 300\text{m}$로 완전히 분리된 상태에서 step 실행.
  4. 500대 차량을 $200\text{m} \times 200\text{m}$ 영역에 배치하여 $500 \times 500 = 250,000$ 페어 연산 및 빈 누적 부하 가중.
  5. 시뮬레이션 도중 50%의 차량이 동적으로 이탈(`remove_vehicle`)할 때 메모리 누수 및 dangling key 발생 여부.
- **검증 결과 (Actual Behavior)**:
  - $N=0, 1$일 때 `get_distance_aoi()`는 `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`을 안정적으로 반환하며 NaN/ZeroDivision이 전혀 발생하지 않음.
  - 500대 고밀도 환경에서 5스텝 연속 실행 시 평균 AoI는 $[0, 2000]\text{ms}$ 범위 내에서 정상 산출됨.
  - `remove_vehicle()` 호출 시 `last_cam_sent`, `first_tx_time`, `last_received_gen_time`, `current_aoi`에서 완벽히 정리되어 고아 상태(Orphaned state)가 남지 않음.

### [Low Risk] Challenge 2: `get_latent_and_gate` 입력 형태 및 수치적 안정성 (ResNetMoEAgent)
- **가정 검증**: 단일 1D 벡터(리스트, ndarray, torch.Tensor) 및 임의의 배치 크기(B=1, 7, 32, 128, 512) 2D 텐서, 극단적인 비정상 상태값 입력 시에도 출력 형상 (128,) / (3,)을 유지하고 Softmax 가중치 합이 $1.0 \pm 10^{-5}$를 만족해야 함.
- **공격 시나리오 (Attack Scenarios)**:
  1. 1D Python list `[0.1, 10.0, 5.0, 0.05, 0.2]`, 1D numpy array, 1D torch tensor 입력.
  2. 임의의 2D 배치 크기 $B \in \{1, 7, 32, 128, 512\}$ 텐서 입력.
  3. All zeros ($\mathbf{0}_5$), Extreme positive ($10^4$), Extreme negative ($-10^4$), Cauchy 분포 난수 입력.
  4. `get_latent_and_gate` 호출 전후 신경망의 `training` 모드 보존 여부.
- **검증 결과 (Actual Behavior)**:
  - 1D 입력 시 Latent `(128,)`, Gate `(3,)` 정확히 반환.
  - 2D 입력 시 Latent `(B, 128)`, Gate `(B, 3)` 정확히 반환.
  - 극단값($\pm 10^4$) 및 코시 난수 입력 시에도 NaN/Inf 발생 없이 게이트 확률의 합이 정확히 $1.0$ (오차 $< 10^{-5}$)을 유지.
  - `eval()` 전환 후 원래 `training` 상태로 완벽 복원됨을 확인.

### [Low Risk] Challenge 3: 무선 채널 모델 및 CBR 패킷 전달률(PDR)의 수학적 단조 감소성 (SimEngine)
- **가정 검증**: 거리 $d \in [0, 3000\text{m}]$ 및 CBR $\in [0.0, 1.0]$ 증가에 따라 수신 확률 및 PDR이 수학적으로 단조 감소(Monotonically non-increasing)해야 함.
- **공격 시나리오 (Attack Scenarios)**:
  1. $d \in [0.5, 3000\text{m}]$ 구간 1,000개 지점에서 $\Delta P_{rx}(d) \le 0$ 검증.
  2. 스칼라 함수 `reception_probability(d)`와 벡터화 함수 `reception_probability_vec(d)`의 수치 일치성 ($< 10^{-6}$).
  3. 충돌 인자 $\max(0.1, 1.0 - 0.8 \times CBR)$의 CBR에 따른 단조 감소 검증.
  4. CBR 레벨 $[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]$에 따른 3,000회 시뮬레이션 기반 경험적 PDR 측정.
- **검증 결과 (Actual Behavior)**:
  - $\Delta P_{rx}(d) \le 0$ 전 구간 성립: $d \le 125\text{m} \to 1.000$, $d=300\text{m} \to 0.9987$, $d=1000\text{m} \to 0.5942$, $d=2000\text{m} \to 0.0052$, $d=3000\text{m} \to 2.28 \times 10^{-7}$.
  - 스칼라와 벡터 연산 결과 오차 $< 10^{-6}$으로 완벽 일치.
  - CBR 증가에 따른 경험적 PDR:
    - $\text{CBR}=0.0 \to 100.0\%$
    - $\text{CBR}=0.2 \to 83.81\%$
    - $\text{CBR}=0.4 \to 67.09\%$
    - $\text{CBR}=0.6 \to 51.94\%$
    - $\text{CBR}=0.8 \to 36.57\%$
    - $\text{CBR}=1.0 \to 19.78\%$
    - 엄밀한 단조 감소(Monotonic decrease) 확인 완료.

---

## 3. Stress Test Results Matrix (스트레스 테스트 결과 매트릭스)

| Test ID | 대상 모듈 | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| TC-01 | `aoi_tracker.py` | 차량 수 $N=0$ 상태 step 및 메트릭 조회 | AoI=0, PDR=100, Bins=[0]*6, NaN 없음 | AoI=0.0, PDR=100.0, Bins=[0]*6, No NaN | **PASS** |
| TC-02 | `aoi_tracker.py` | 단일 차량 $N=1$ 상태 step 및 메트릭 조회 | AoI=0, PDR=100, Bins=[0]*6, ZeroDivision 없음 | AoI=0.0, PDR=100.0, Bins=[0]*6, No ZeroDiv | **PASS** |
| TC-03 | `aoi_tracker.py` | 통신 범위 초과 ($d=1000\text{m}$) 차량 쌍 | AoI=0, 수신 이벤트 없음 | AoI=0.0, 빈 누적 없음 | **PASS** |
| TC-04 | `aoi_tracker.py` | 500대 차량 초고밀도 ($250,000$ 페어) | AoI $\in [0, 2000]\text{ms}$, 연산 성공 | Mean AoI 유효, 6개 빈 정상 누적 | **PASS** |
| TC-05 | `aoi_tracker.py` | 동적 차량 이탈 (50% remove_vehicle) | 메모리 누수 및 dangling key 없음 | 딕셔너리 완벽 정리, step 정상 동작 | **PASS** |
| TC-06 | `aoi_tracker.py` | $t_{rx} < t_{gen}$ 타임스탬프 역전 및 미래 step | 음수 AoI 0 클램핑, 최대 2000ms 클램핑 | $AoI \in [0, 2000]\text{ms}$ 클램핑 확인 | **PASS** |
| TC-07 | `resnet_moe_agent.py` | 1D 입력 (list, ndarray, torch.Tensor) | Latent (128,), Gate (3,), sum=1.0 | Shape (128,), (3,), sum=1.000000 | **PASS** |
| TC-08 | `resnet_moe_agent.py` | 2D 배치 입력 ($B=1, 7, 32, 128, 512$) | Latent (B, 128), Gate (B, 3), sum=1.0 | All Batch shapes match, Softmax sum=1.0 | **PASS** |
| TC-09 | `resnet_moe_agent.py` | 비정상 극단값 ($\pm 10^4$, Zeros, Cauchy noise) | NaN/Inf 없음, Softmax sum=1.0 | No NaN/Inf, Softmax sum=1.000000 | **PASS** |
| TC-10 | `resnet_moe_agent.py` | 신경망 Train/Eval 모드 보존 | get_latent_and_gate 후 모드 유지 | Mode conserved (train=True/False) | **PASS** |
| TC-11 | `sim_engine.py` | 스칼라 vs 벡터화 무선 채널 모델 수치 일치 | Max absolute error $< 10^{-6}$ | Max error $< 10^{-6}$ | **PASS** |
| TC-12 | `sim_engine.py` | 무선 채널 수신 확률 거리 단조성 ($0 \sim 3000\text{m}$) | $\Delta P_{rx}(d) \le 0$ 단조 비증가 | $d \uparrow \implies P_{rx}(d) \downarrow$, $3000\text{m} < 10^{-5}$ | **PASS** |
| TC-13 | `sim_engine.py` | CBR 충돌 인자 단조성 ($\text{CBR} \in [0, 1]$) | $\Delta \text{ColFactor} \le 0$ 단조 감소 | $1.0 \to 0.2$ 단조 감소 확인 | **PASS** |
| TC-14 | `sim_engine.py` | 송신 전력 감쇄 시 ($0\text{ dBm}$) 거리별 수신 확률 | 거리 25m~275m에서 수신 확률 엄밀 감소 | $P(25\text{m}) > P(75\text{m}) > \dots > P(275\text{m})$ | **PASS** |
| TC-15 | `sim_engine.py` | CBR 레벨별 경험적 PDR ($0.0 \sim 1.0$) | CBR 증가에 따른 PDR 단조 감소 | $100\% \to 83.8\% \to 67.1\% \to 51.9\% \to 36.6\% \to 19.8\%$ | **PASS** |
| TC-16 | `sim_engine.py` | `compute_local_n_est` (0, 1, 2, 500대) | 올바른 이웃 수 딕셔너리 반환 | $N=0 \to \{\}$, $N=1 \to 0$, $N=500 \to 499$ | **PASS** |
| TC-17 | `sim_engine.py` | `compute_local_cbr` 경계 조건 | Zero division 없음, 올바른 CBR 계산 | No ZeroDivision, list/dict 입력 호환 | **PASS** |
| TC-18 | `sim_engine.py` | `simulate_receptions` 빈 입력 | 빈 리스트 반환, 에러 없음 | Returns `[]` gracefully | **PASS** |
| TC-19 | `sim_engine.py` | `SimulationRunner` End-to-End 실행 (80 steps) | 6개 거리 빈 AoI/PDR, CBR trace 산출 | distance_aoi, distance_pdr, cbr_history 완료 | **PASS** |

---

## 4. Unchallenged Areas (미검증 영역)
- **대규모 17,000 에피소드 파라미터 스윕 및 멀티 GPU 병렬성**: Milestone 4 범위로 계획되어 있어 Milestone 1의 단위 시뮬레이션 및 메트릭 추출 스트레스 테스트에 집중함.
- **Optuna 하이퍼파라미터 최적화 수렴성**: Milestone 2 범위에 해당함.

---

## 5. 결론 (Conclusion)
- Milestone 1 구현 사항은 경계값 및 극단 조건에서도 무결성을 유지하며, 모든 요구사항을 완벽히 만족합니다.
- 최종 판정: **APPROVE** (다음 마일스톤 진행 승인)
