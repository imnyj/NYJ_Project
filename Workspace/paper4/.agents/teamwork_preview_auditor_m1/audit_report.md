# Forensic Audit Report — Milestone 1

**Work Product**: `code/aoi_tracker.py`, `code/sim_engine.py`, `code/resnet_moe_agent.py`, `code/moe_agent.py`, `code/test_m1_audit.py`  
**Profile**: General Project (Forensic Integrity)  
**Integrity Mode**: Benchmark (Strict from-scratch computation, zero mock/fake/hardcoding)  
**Auditor**: `auditor_m1` (Conversation ID: `d2ca5069-37fe-4d8d-836a-d6fb5e7a3957`)  
**Date**: 2026-08-24  
**Verdict**: **CLEAN**

---

## 1. Executive Summary
Milestone 1의 주요 산출물인 시뮬레이션 엔진, AoI 추적기, REMO-DQN 및 MoE 에이전트에 대해 무결성 전수 포렌식 감사(Forensic Integrity Audit)를 수행하였습니다.
감사 결과, 코드베이스 전반에 걸쳐 하드코딩된 상수값 반환, 모킹(Mocking) 배열, 인위적 결과 조작, 더미 텐서 반환 등의 위반 사항이 전혀 발견되지 않았으며(Zero Tolerance 충족), 모든 계산 및 활성화 추출 로직이 실제 물리 수식, 실시간 패킷 타임스탬프, PyTorch 순전파 연산에 기반하여 엄격하게 동작함을 확인하였습니다.

---

## 2. Forensic Phase Results

| # | Check Item | Status | Key Evidence / Observations |
|---|------------|:------:|-----------------------------|
| 1 | **Hardcoded Output & Facade Detection** | **PASS** | 소스코드 전수 검사 결과, 고정된 상수 리턴, 더미 배열, 사전 채워진 결과 아티팩트 부재 확인. 모든 메트릭이 런타임 이벤트 기반으로 동적 생성됨. |
| 2 | **SUMO Mobility & Mathematical Decay** | **PASS** | `sim_engine.py` 내 IEEE 802.11p Log-distance Path Loss ($\alpha=2.0, PL_0=47.85\text{dB}$) 및 Nakagami-$m$ ($m=3$) fading CCDF가 정상 적용되어 거리에 따른 단조 PDR 감소 확인. 로컬 CBR 충돌 계수 $\max(0.1, 1.0 - 0.8 \times CBR)$ 실제 반영. |
| 3 | **PyTorch Forward Pass in `get_latent_and_gate`** | **PASS** | `resnet_moe_agent.py` 및 `moe_agent.py`의 `get_latent_and_gate`가 실제 ResNet 피처 추출기 및 Softmax 게이팅 네트워크를 통과하여 128D 잠재 벡터 및 유효한 확률 가중치(합 1.0)를 반환. 가중치 섭동 시 출력 변화 실증. |
| 4 | **Timestamp-based `distance_aoi` Calculation** | **PASS** | `aoi_tracker.py`에서 패킷 전송 타임스탬프(`t_gen`), 수신 타임스탬프(`t_rx`), 차량 간 유클리드 거리 및 6개 거리 구간(0~300m, 50m 간격)별로 실제 지연 및 staleness가 정확히 누적 계산됨. |
| 5 | **End-to-End Simulation Metric Export** | **PASS** | `SimulationRunner.run()` 실행 시 `AoI_mean`, `CBR_mean`, `PDR_mean`, `distance_aoi`, `distance_pdr`, `cbr_history`가 정상 추출됨. |

---

## 3. Empirical Verification Evidence

### 3.1. 무선 채널 모델 거리 감쇄 검증
- 거리별 패킷 도달 확률(PDR):
  - 10m: 100.0%
  - 50m: 100.0%
  - 100m: 100.0%
  - 150m: 100.0%
  - 200m: 99.99%
  - 250m: 99.96%
  - 300m: 99.87%
  - 350m: 99.70%
  - 400m: 99.36%
  - 500m: 97.91%
- CBR 혼잡도에 따른 충돌 패널티 팩터:
  - CBR 0.0: 1.000
  - CBR 0.2: 0.840
  - CBR 0.5: 0.600
  - CBR 0.8: 0.360
  - CBR 1.0: 0.200

### 3.2. PyTorch 순전파 잠재 벡터 및 게이팅 가중치 검증
- 서로 다른 입력 상태 $s_1, s_2$에 대해 고유한 128차원 벡터 및 3차원(Softmax $\sum=1.0$) 게이팅 가중치 산출 확인.
- 입력 계층 가중치($W=0$) 변조 시 잠재 벡터 출력이 변조됨을 확인하여, 정적 더미 텐서가 아닌 실제 연산 그래프를 통과함을 검증 완료.

### 3.3. AoITracker 타임스탬프 기반 지연 누적 및 6구간 집계 검증
- 패킷 수신 성공 노드(Rx0)와 패킷 손실 노드(Rx1~Rx5)의 AoI staleness가 각각 200ms 및 1200ms로 정상 누적 분기됨을 확인.
- 거리 구간별(25m, 75m, 125m, 175m, 225m, 275m) 평균 AoI 및 표준편차가 정확하게 집계됨.

### 3.4. 단위 및 회귀 테스트 실행 결과
- `code/test_m1_audit.py`: 6개 테스트 항목 **전부 통과 (6/6 PASSED)**
- `etc/scripts/verify_m1_forensics.py`: 4개 독립 검증 항목 **전부 통과 (4/4 PASSED)**
- `code/test_c1_c2_wiring.py` & `code/test_m8_local_cbr.py`: 11개 심층 회귀 테스트 항목 **전부 통과 (11/11 PASSED, 420.68s)**

---

## 4. Final Verdict
**VERDICT: CLEAN**  
Milestone 1 대상 코드(`aoi_tracker.py`, `sim_engine.py`, `resnet_moe_agent.py`, `moe_agent.py`)는 Benchmark 모드의 무결성 기준을 100% 충족하며, 어떠한 조작이나 모킹 없이 순수 실제 연산으로 동작함을 최종 확정합니다.
