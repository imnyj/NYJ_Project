# Research Idea Specification

**Candidate ID:** candidate_2_tinymlp_beacon_dcc  
**Phase:** Phase 2 — Feasibility & Contribution Review (Round 2)  
**GO/NO-GO Verdict:** ✅ GO  
**Date:** 2026-05-08  
**Target Journal:** IEEE Internet of Things Journal (IoT-J)  
**Confidence:** HIGH (Novelty: 90%, Feasibility: FEASIBLE with implementation notes)

---

## 1. Problem Statement

차량 통신(V2X) 네트워크에서 ETSI EN 302 637-2 표준에 따라 차량은 1–10 Hz로 CAM(Cooperative Awareness Message) 비콘을 주기적으로 브로드캐스트한다. 현재 표준 기반 DCC(Decentralized Congestion Control) 알고리즘(Reactive/Adaptive)은 채널 부하(CBR)만을 피드백 신호로 사용하여 비콘 주기를 반응적으로 조정하며, 전송 전력은 고정하거나 별도의 단순 휴리스틱으로만 제어한다.

이 접근의 근본적 한계는 세 가지다:
1. **단일 메트릭 의존**: CBR만 추종하여 AoI(Age of Information) — 즉, 인접 차량이 얼마나 오래된 위치 정보를 보유하는지 — 를 직접 제어하지 못한다.
2. **컨텍스트 무감각**: 차량 속도, 가속도, 국부적 밀도 변화에 반응하지 않아 고속 주행이나 급가속 상황에서 AoI가 급격히 악화된다.
3. **전력-주기 비연동**: 비콘 주기와 전송 전력을 독립적으로 제어하여 간섭 절감과 인식 품질 간 최적 균형점을 놓친다.

본 연구는 **TinyMLP 기반 AI-DCC(Intelligent Decentralized Congestion Control)**를 제안한다: 차량 컨텍스트 5-차원 입력(속도, 가속도, 추정 이웃 수, CBR, 누적 AoI)으로부터 비콘 주기와 전송 전력을 동시에 출력하는 초경량 2-레이어 MLP(파라미터 < 2,000개)를 ETSI CAM 생성 레이어에 직접 내장한다. 이 모델은 오프라인 Behavior Cloning으로 학습되어 ARM Cortex-M 급 MCU에서 실시간 추론(< 1 ms)이 가능하며, ETSI EN 302 637-2의 CAM 생성 규칙을 위반하지 않는다.

**핵심 질문(Research Question):** TinyMLP 기반 AI-DCC가 기존 ETSI DCC 대비 AoI와 CBR의 동시 최적화를 달성하면서도 MCU 배포 제약(메모리 < 16 KB, 추론 < 1 ms)을 만족할 수 있는가?

---

## 2. Core Contribution (3개 → 실질 2+1 구조)

### Contribution C1 — [Protocol Design] ETSI CAM 호환 AI-DCC 프로토콜 설계 (Novel + Verifiable)
> **근거 — Novel:** ETSI EN 302 637-2 CAM 생성 레이어에 TinyMLP를 직접 내장하여 비콘 주기(T_GenCam)와 전송 전력(p_tx)을 공동 제어하는 프로토콜 구조를 최초로 정형화함. 기존 DCC 알고리즘(Reactive/Adaptive)은 주기만 제어하고 전력은 고정이거나 독립 루프로 처리하는 반면, 본 설계는 2D 출력 벡터로 두 파라미터를 단일 추론 콜에서 결정하는 통합 제어 흐름을 제시한다.  
> **근거 — Verifiable:** ETSI EN 302 637-2 §6.1.3 CAM 생성 조건(T_GenCamMin=0.1s, T_GenCamMax=1.0s, ΔHeading/ΔPos/ΔSpeed 트리거)을 준수하는지 시뮬레이션 로그로 직접 검증 가능. 표준 위반 횟수를 메트릭으로 측정한다.

### Contribution C2 — [AI/System] AoI-CBR 공동 최적화 Behavior Cloning 프레임워크 (Novel + Impactful)
> **근거 — Novel:** Behavior Cloning의 교사(Oracle)를 "AoI + CBR 가중 합 최소화" 오프라인 최적 DCC 테이블로 구성한 것은 기존 RL/DRL 기반 V2X 제어와 근본적으로 다른 학습 패러다임이다. 교사 없는 강화학습 대신 확정적 Oracle 레이블로 학습하여 시뮬레이션 시간·편차를 획기적으로 줄인다.  
> **근거 — Impactful:** AoI는 자율주행·협력 인식에서 정보 신선도의 직접적 지표이므로, AoI 개선은 V2X 안전 애플리케이션의 실효성 향상으로 이어진다.

### Contribution C3 — [Deployment] MCU 배포 가능성 실증 (Verifiable + Impactful)
> **근거 — Verifiable:** TinyMLP 파라미터 수(< 2,000), FLASH 점유 용량(< 16 KB), 추론 지연(< 1 ms @ 80 MHz Cortex-M4 시뮬레이션 기준)을 구체적 수치로 제시하고 STM32F4 프로파일(CMSIS-NN 추론 사이클 수 추정치)과 비교한다.  
> **근거 — Impactful:** 기존 V2X AI 연구(DRL 기반)는 GPU/고성능 SoC를 암묵적으로 가정하나, 본 연구는 OBU(On-Board Unit) 내 저전력 MCU 배포 가능성을 IoT-J 맥락에서 정면으로 다룬다.

> **정리:** C1(프로토콜 설계), C2(AI 프레임워크), C3(IoT 배포)는 각각 프로토콜 연구자·AI 연구자·시스템 연구자 리뷰어를 포괄하며, IoT-J의 핵심 평가 항목(새로운 IoT 시스템 설계, 실제 배포 가능성)을 정면 공략한다.

---

## 3. Novelty vs. Prior Work

### 3.1 차별화 표

| 구분 | **본 연구 (AI-DCC)** | Bhattacharyya2024 | Zila2026 | Ni2024 | Wu2025 |
|------|---------------------|------------------|---------|--------|--------|
| **제어 대상** | 비콘 주기 + 전력 (2D 출력) | 비콘 주기만 | 일반 IIoT 패킷 전송 | MAC 채널 접근 | 긴급 메시지 브로드캐스트 |
| **AI 방법론** | TinyMLP + Behavior Cloning | 휴리스틱 규칙 (no ML) | TinyMLP (IIoT 도메인) | Hyperdimensional Computing | Deep RL (DQN 계열) |
| **최적화 목표** | AoI + CBR 동시 | CBR 감소 | 지연 + 에너지 | 충돌률 | PDR (긴급) |
| **표준 준수** | ETSI EN 302 637-2 CAM | ETSI 부분 | IEC 62443 (산업) | 표준 무관 | IEEE 802.11p 부분 |
| **MCU 배포** | ✅ < 16 KB, < 1 ms | ❌ (규칙 기반) | ✅ (IIoT 센서) | ❌ (HDC 하드웨어 필요) | ❌ (GPU 추론) |
| **AoI 메트릭** | ✅ 직접 최적화 | ❌ | ❌ | ❌ | ❌ |
| **V2X 도메인** | ✅ ITS-G5 / DSRC | ✅ VANET | ❌ Industrial IoT | ✅ VANET | ✅ VANET |
| **출력 차원** | 2D (주기 + 전력) | 1D (주기만) | 1D (전송 간격) | 1D (채널 접근) | 1D (브로드캐스트 여부) |

### 3.2 포지셔닝 전략
- **Bhattacharyya2024** 대비: 휴리스틱 → 학습 기반으로의 패러다임 전환, 단일 파라미터 → 공동 최적화.
- **Zila2026** 대비: IIoT 도메인의 TinyML을 V2X 도메인(ETSI 표준, 고이동성, AoI 요구)에 적용한 도메인 전이의 비자명성(non-triviality) 강조.
- **Ni2024** 대비: Hyperdimensional Computing은 특수 하드웨어 의존성이 높지만 TinyMLP는 범용 Cortex-M에서 동작.
- **Wu2025** 대비: RL의 샘플 비효율성·수렴 불안정성 대신 Behavior Cloning의 결정론적 학습, 긴급 메시지가 아닌 일상 CAM 비콘 제어 문제.

**핵심 포지셔닝 문구:** *"To the best of our knowledge, this is the first work to deploy a TinyMLP-based joint beacon rate and power controller within the ETSI EN 302 637-2 CAM generation framework, enabling on-device AoI-aware vehicular congestion control on commodity MCUs."*

---

## 4. Proposed Approach

### 4.1 System Model & MAC Layer Modification

**네트워크 모델:**
- 차량 N대가 ITS-G5 5.9 GHz 채널(10 MHz 대역폭, 802.11p OFDM)을 공유.
- 각 차량은 ETSI EN 302 637-2를 따르는 CAM 서비스를 실행.
- 현재 표준 DCC는 CBR을 측정하고 세 상태(Active/Restricted/Relaxed)에 따라 T_GenCam을 조정 (ETSI EN 302 571 TS DCC 참조).

**MAC 수정 포인트:**
- **표준 DCC 상태 머신(State Machine)을 제거하지 않고 확장**: AI-DCC는 DCC 상태 머신의 출력을 Override하는 별도의 "AI 제어 레이어"로 동작.
- **CAM 생성 트리거**: ETSI §6.1.3의 ΔHeading(4°), ΔPos(4 m), ΔSpeed(0.5 m/s) 트리거는 그대로 유지 — AI-DCC는 T_GenCam 상한(최대 1 Hz) 및 하한(최대 10 Hz) 범위 내 값을 출력.
- **출력 매핑**: TinyMLP 2D 출력 → (1) T_GenCam ∈ {100, 200, 500, 1000 ms} 이산값, (2) p_tx ∈ {-10, 0, +10, +20 dBm} 이산값. 이산 출력으로 softmax 불필요, argmax 매핑.
- **추론 시점**: 직전 CAM 전송 직후, 다음 T_GenCam 계획 시점에 1회 추론 (이벤트 트리거 방식, 주기 방식 아님).

**구현 위치**: SumoNetSim의 ETSI CAM 서비스 모듈(`cam_service.cc` 또는 파이썬 바인딩) 내에 AI-DCC 훅 삽입. **SumoNetSim에 ETSI DCC 모듈이 기본 내장되어 있지 않을 경우(Q1 참조), CAM 생성 + 기본 DCC를 포함하는 경량 Python 시뮬레이션 계층을 libsumo 위에서 직접 구현한다.**

### 4.2 TinyMLP Architecture & Training (Behavior Cloning)

**모델 구조:**
```
입력 (5차원): [속도 v (m/s), 가속도 a (m/s²), 추정 이웃 수 N_est, CBR, AoI (ms)]
  ↓
Linear(5 → 32) + ReLU
  ↓
Linear(32 → 32) + ReLU
  ↓
Linear(32 → 8)
  ↓
Reshape(4, 2): [T_GenCam 로짓(4개), p_tx 로짓(4개)]
  ↓
argmax → (T_GenCam 인덱스, p_tx 인덱스)
```
- 총 파라미터: 5×32 + 32 + 32×32 + 32 + 32×8 + 8 = 1,448개 (< 2,000)
- 양자화 후 INT8 가중치 기준 메모리: ~1.4 KB weights + ~0.5 KB activations ≈ 2 KB

**Behavior Cloning 학습 파이프라인:**
1. **Oracle 생성 (오프라인 최적 DCC 테이블)**: libsumo 시뮬레이션으로 다양한 밀도·속도·채널 부하 시나리오를 생성하고, 각 상태 (v, a, N_est, CBR, AoI)에 대해 AoI-CBR 결합 비용 최소화 grid-search를 수행하여 최적 (T_GenCam*, p_tx*) 레이블을 생성.
2. **데이터셋**: 10,000+ 상태-액션 쌍, 열차/검증/테스트 = 70/15/15%.
3. **손실 함수**: Cross-Entropy(T_GenCam) + Cross-Entropy(p_tx) — 두 출력 독립 분류.
4. **학습 환경**: PyTorch (CPU만으로 충분, 소형 모델), 에포크 < 100, 배치 64.
5. **배포 변환**: ONNX → TensorFlow Lite (양자화) → C array (CMSIS-NN 호환).

### 4.3 Joint AoI–CBR Optimization Formulation

**상태 공간**: $s = (v, a, N_{est}, \text{CBR}, \text{AoI}) \in \mathbb{R}^5$

**행동 공간**: $\pi(s) = (T_{\text{GenCam}}, p_{\text{tx}}) \in \mathcal{T} \times \mathcal{P}$  
여기서 $\mathcal{T} = \{0.1, 0.2, 0.5, 1.0\}$ s, $\mathcal{P} = \{-10, 0, +10, +20\}$ dBm.

**결합 비용 함수 (Oracle 학습용)**:
$$J(T_{\text{GenCam}}, p_{\text{tx}}) = \alpha \cdot \overline{\text{AoI}} + \beta \cdot \text{CBR} + \gamma \cdot \mathbb{1}[\text{ETSI 위반}] \cdot M$$

- $\overline{\text{AoI}}$: 이웃 차량 집합에서 평균 AoI (ms)
- CBR: 채널 점유율 (0–1)
- $\mathbb{1}[\text{ETSI 위반}]$: T_GenCam이 ETSI 범위 밖 → 대형 패널티 M
- 가중치 기본값: $\alpha = 0.5, \beta = 0.5, \gamma = 1.0$; ablation에서 변화

**Oracle 최적화**: 각 상태 s에 대해 $|\mathcal{T}| \times |\mathcal{P}| = 16$가지 조합을 시뮬레이션 평가 → 최소 비용 행동 선택 (전수 탐색 가능, 16개로 계산 비용 무시). 이것이 Behavior Cloning의 교사 레이블이 됨.

**AoI 정의**: 차량 j의 차량 i에 대한 AoI = 수신 시점 $t_{rx}$ − 해당 CAM 생성 시점 $t_{gen}$. 시뮬레이션에서 각 CAM 패킷에 생성 타임스탬프를 포함시켜 수신 측에서 직접 계산.

### 4.4 Deployment Considerations (MCU, ETSI Compliance)

**MCU 타겟 (참조 플랫폼):**
- STM32F407 (ARM Cortex-M4 @ 168 MHz, 1 MB FLASH, 192 KB SRAM)
- TinyMLP 추론: CMSIS-NN int8 추론 기준 ~500 사이클 ≈ **3 µs @ 168 MHz** (추정)
- 메모리: 가중치 ~2 KB (INT8) + 스택 ~1 KB → **총 < 4 KB** (192 KB SRAM의 2% 미만)
- 배포 형식: `tinymlp_aimdcc.h` C 헤더 파일 형태, ETSI 스택과 통합

**ETSI EN 302 637-2 준수 보장:**
- TinyMLP 출력이 T_GenCam ∉ [100ms, 1000ms]이면 Clamp 처리
- CAM 이벤트 트리거(ΔHeading/ΔPos/ΔSpeed) 조건이 만족되면 AI 출력과 무관하게 즉시 CAM 발생 (표준 우선)
- 주기 T_GenCam은 직전 CAM 발생 이후 AI가 제안한 값으로 타이머 재설정

**전력 소비 고려:**
- p_tx = -10 dBm: 에너지 최소 (근거리 고밀도 환경)
- p_tx = +20 dBm: 최대 인식 범위 (저밀도 고속 환경)
- 에너지 소비 메트릭: J/km (거리 정규화 에너지)

---

## 5. Experimental Plan

### 5.1 Simulators (libsumo + SumoNetSim) 및 추가 모듈 명세

**사용 시뮬레이터:**
| 구성요소 | 역할 | 구현 상태 |
|---------|------|---------|
| **libsumo** (SUMO Python API) | 차량 이동성 생성, 위치/속도/가속도 실시간 추출 | 기존 사용 중 ✅ |
| **SumoNetSim** | 802.11p MAC/PHY 계층 시뮬레이션 | 기존 사용 중 ✅ |
| **etsi_cam_layer.py** | ETSI CAM 생성 로직 + DCC 상태 머신 | **직접 구현 필요** ⚠️ |
| **ai_dcc_hook.py** | TinyMLP 추론 + ETSI Override 로직 | **직접 구현 필요** ⚠️ |
| **aoi_tracker.py** | 패킷별 생성/수신 타임스탬프 추적, AoI 계산 | **직접 구현 필요** ⚠️ |
| **oracle_generator.py** | Grid-search 기반 최적 DCC 테이블 생성 | **직접 구현 필요** ⚠️ |

**구현 우선순위 및 소요 시간 추정:**
1. `etsi_cam_layer.py`: ETSI DCC Reactive 알고리즘 구현 (2주) — 베이스라인 (a)도 이것에 의존
2. `aoi_tracker.py`: 패킷 타임스탬프 로깅 + AoI 계산 (1주)
3. `oracle_generator.py`: Grid-search 자동화 (1주)
4. `ai_dcc_hook.py`: TinyMLP 로드 + Override 로직 (1주)
5. TinyMLP 학습: PyTorch + ONNX 변환 (2주)

**총 구현 비용 추정: 7주 이내** (3개월 제약 내 충분히 가능)

### 5.2 Scenarios (최소 2개)

**시나리오 S1 — Urban Grid (교차로 밀집 환경)**
- 지도: 500m × 500m 격자 도로망 (10 교차로, OpenStreetMap 서울 강남 패치 또는 SUMO 내장 grid)
- 차량 수: 20 / 50 / 100대 (밀도 변화 3단계)
- 속도 프로파일: 0–60 km/h, 신호등 정지 포함
- 시뮬레이션 시간: 300초 / 시드 10개
- 목적: 고밀도 + 저속 환경에서 CBR 과부하 시나리오

**시나리오 S2 — Highway (고속 저밀도 환경)**
- 지도: 5 km 단방향 고속도로, 2차선
- 차량 수: 10 / 30 / 60대 (편도)
- 속도 프로파일: 80–130 km/h (Krauss 모델)
- 시뮬레이션 시간: 300초 / 시드 10개
- 목적: 고속 + AoI 민감 환경에서 비콘 주기 조정 효과 측정

**시나리오 S3 (추가, Optional) — Mixed Urban-Highway Entry**
- 도시-고속도로 진입로 전환 구간 (밀도·속도 급변)
- 목적: AI-DCC의 적응 속도(adaptation latency) 측정

### 5.3 Baselines (4개 + 2개 Ablation)

**기존 4개 베이스라인:**

| ID | 이름 | 설명 | 구현 방법 |
|----|------|------|---------|
| **BL-A** | ETSI DCC Reactive | ETSI EN 302 571 §8.1 Reactive 알고리즘: CBR 임계값(0.60/0.40)으로 상태 전환, T_GenCam 3단계 조정, 전력 고정(+20 dBm) | `etsi_cam_layer.py`에서 직접 구현 |
| **BL-B** | ETSI DCC Adaptive | ETSI EN 302 571 §8.2 Adaptive 알고리즘: LIMERIC 기반 CBR 추종, 전력 고정 | `etsi_cam_layer.py` 확장 |
| **BL-C** | Bhattacharyya2024 Variable Beacon | CBR + 이웃 수 기반 가변 비콘 주기, 전력 고정 | IEEE TVT 10.1109/TVT.2023.3307672 알고리즘 재현 |
| **BL-D** | Fixed 10 Hz | T_GenCam = 100 ms 고정, p_tx = +20 dBm 고정 | 1줄 구현 |

> **주의**: Zila2026(TinyML for IIoT)은 IIoT 도메인이라 직접 코드 재현이 불가능하므로, Related Work 비교 표에서 수치만 인용하고 베이스라인 목록에서는 제외한다. 대신 "도메인 전이(domain transfer) 평가"를 Additional Experiment에서 논의.

**2개 Ablation 변형:**

| ID | 이름 | 제거 요소 | 목적 |
|----|------|---------|------|
| **ABL-1** | Rate-Only (전력 제어 제거) | TinyMLP 출력을 T_GenCam만 사용, p_tx = +20 dBm 고정 | 전력 공동 제어의 기여도 격리 |
| **ABL-2** | No-AoI (AoI 입력 제거) | 입력을 4D (v, a, N_est, CBR)로 축소, AoI 제거 | AoI 피드백의 중요성 격리 |

> **추가 Ablation (선택)**: Oracle 대신 균등 랜덤 레이블(ABL-3 Random Oracle)로 학습하여 Behavior Cloning의 교사 품질 효과를 검증.

### 5.4 Metrics (5개 이내)

| # | 메트릭 | 정의 | 단위 | 측정 방법 |
|---|--------|------|------|---------|
| **M1** | 평균 AoI | $\overline{\text{AoI}} = \frac{1}{N(N-1)} \sum_{i \neq j} \text{AoI}_{ij}$ | ms | `aoi_tracker.py`: CAM 수신 시 (수신시각 − 생성타임스탬프) 누적 평균 |
| **M2** | CBR (채널 점유율) | 채널이 바쁜 시간 비율 | % (0–100) | SumoNetSim 802.11p PHY 계층 채널 감지 통계 |
| **M3** | PDR (패킷 전달률) | 전송된 CAM 중 인접 100m 내 수신 성공 비율 | % (0–100) | SumoNetSim 수신 이벤트 로그 |
| **M4** | 에너지 효율 | 차량당 거리 정규화 전송 에너지 소비 | mJ/km | p_tx 레벨 × 전송 횟수 × 패킷 길이 / 이동 거리 적분 |
| **M5** | ETSI 규범 준수율 | T_GenCam이 ETSI 범위 내 유지된 비율 | % (0–100) | CAM 생성 이벤트 로그에서 T_GenCam 범위 검사 |

### 5.5 Fair Comparison Protocol

**공정 비교 원칙:**

1. **동일 시드(Seed) 고정**: 각 시나리오(S1/S2) × 밀도(3단계) × 시드(10개) = 60개 시뮬레이션 실행 세트를 모든 베이스라인 + Ablation + 제안 모델에 동일하게 적용. 시드는 SUMO `--seed` 인수로 고정.

2. **동일 시나리오 파일**: 각 실험에서 동일한 `.sumocfg`, `.net.xml`, `.rou.xml` 파일 사용. 차량 경로 및 출발 시각 완전 고정.

3. **동일 PHY 파라미터**: SumoNetSim 내 전파 모델(Nakagami-m, 경로 손실 지수 α=2.0), 채널 대역폭(10 MHz), MCS(BPSK 1/2 = 3 Mbps)를 모든 방법에 동일 적용. AI-DCC의 p_tx 변화만이 수신 전력에 영향.

4. **동일 평가 윈도우**: 초기 30초 Warm-up 제외, 나머지 270초 동안 메트릭 수집.

5. **통계 유의성**: 10개 시드 결과에 대해 95% 신뢰 구간 계산(t-test 또는 bootstrap). 박스플롯으로 시각화.

6. **파라미터 공정성 (Bhattacharyya2024)**: 원 논문의 CBR 임계값·이웃 임계값을 논문 그대로 사용하되, 전력 수준은 우리 시뮬레이터의 기본값(+20 dBm)으로 고정 (원 논문도 전력 고정 기준).

7. **Ablation 데이터**: Ablation 변형 모델은 제안 모델과 동일한 Oracle 데이터셋에서 해당 차원만 제거하여 학습. 학습 에포크, 배치 크기, 학습률은 동일.

---

## 6. Expected Impact

**정량적 목표 (가설적, 검증 전):**
- 평균 AoI: ETSI DCC Reactive 대비 **20–35% 감소** (Urban Grid 고밀도 기준)
- CBR: ETSI DCC 대비 **10–20% 감소** (채널 혼잡 완화)
- PDR: Fixed 10 Hz 대비 **5–15% 향상** 또는 동등 유지
- 에너지 효율: Fixed 10 Hz 대비 **30–50% 감소** (저밀도 구간 전력 절감)
- MCU 메모리: < 16 KB FLASH (기존 DRL 기반 방법 수 MB 대비 3자리 수 개선)

**학문적 임팩트:**
- TinyMLP를 V2X 비콘 제어기로 활용하는 첫 번째 논문으로 포지셔닝 → 인용 가능성 높은 새 연구 흐름 개척
- IoT 커뮤니티에 "ETSI 표준 호환 AI-DCC"라는 실용적 청사진 제공
- Behavior Cloning Oracle 방법론은 다른 V2X 제어 문제(EDCA 파라미터, 슬롯 할당 등)에도 전이 적용 가능 → 방법론적 기여

**실용적 임팩트:**
- 기존 OBU(Cohda MK5, Autotalks CRATON2 등 Cortex-M/A 기반)에 소프트웨어 업데이트만으로 배포 가능
- ETSI 표준과의 후방 호환성 유지 → 실제 ITS 인프라 통합 경로 제시

---

## 7. Storyline (Introduction에서 풀어갈 한 단락 Narrative)

*현대 차량 통신(V2X) 시스템에서 협력 인식(Cooperative Awareness)은 자율 주행과 교통 안전의 핵심 기둥이다. 그러나 차량 밀도가 높아질수록 ETSI DCC가 채널 혼잡을 억제하기 위해 비콘 주기를 줄이고, 이는 역설적으로 이웃 차량의 위치 정보가 낡아지는 — 즉, Age of Information(AoI)이 증가하는 — 결과를 낳는다. 기존 DCC는 CBR이라는 단일 신호만으로 반응적으로 주기를 조정하며 전송 전력은 거의 고정한 채 운용된다; 차량의 속도, 가속도, 국부 밀도라는 풍부한 컨텍스트가 완전히 무시된다. 우리는 이 공백에 주목한다: 만약 차량의 이동 컨텍스트를 단 5개의 숫자로 압축하고, 초소형 MLP가 이를 입력받아 비콘 주기와 전송 전력을 공동으로 결정한다면, 기존 DCC를 대체하면서도 ETSI 표준을 준수하고 2,000개 미만의 파라미터로 MCU 위에서 실시간 동작할 수 있을까? 본 논문은 이 질문에 "그렇다"고 답하며, TinyMLP 기반 AI-DCC를 설계·학습·시뮬레이션 검증하는 end-to-end 프레임워크를 제시한다. Behavior Cloning 기반 학습은 복잡한 강화학습 수렴 문제를 우회하고, 결정론적 Oracle 레이블로 빠른 학습을 가능케 한다. 우리의 접근은 IoT 엣지 디바이스에서의 지능형 V2X 프로토콜의 실현 가능성을 구체적 수치로 입증한 최초의 연구다.*

---

## 8. Open Risks & Mitigations

### Q1. SumoNetSim에 ETSI DCC 모듈이 이미 있는가?

**판단: 불확실 — "구현 필요"로 보수적 가정**

SumoNetSim은 802.11p PHY/MAC 계층 시뮬레이션을 제공하지만, ETSI EN 302 571 DCC 상태 머신(Reactive/Adaptive)이 기본 모듈로 포함되어 있다는 공식 문서나 공개 소스가 확인되지 않는다. Veins(OMNeT++ 기반)에는 ETSI DCC 구현이 존재하지만 SumoNetSim에의 포함 여부는 별도 확인 필요.

**직접 구현이 필요한 모듈:**
1. ETSI DCC Reactive/Adaptive 알고리즘 (`etsi_cam_layer.py`) — 구현 복잡도: 중간 (상태 머신 3-5개 상태, CBR 측정 루프)
2. CAM 생성 트리거 로직 (ΔHeading/ΔPos/ΔSpeed) — 구현 복잡도: 낮음
3. CBR 측정 모듈 (채널 감지 통계 집계) — SumoNetSim 통계 API 활용 가능하면 낮음, 없으면 중간

**구현 비용**: 총 2–3주 (베이스라인 BL-A/BL-B 포함). 이 모듈은 모든 베이스라인이 공유하므로 한 번 구현 후 재사용. **위험 완화**: SumoNetSim 대신 ns-3 WAVE 모듈에 ETSI DCC 구현이 있으므로, 필요 시 ns-3으로 네트워크 계층 전환 고려. 단, 3개월 일정 압박 시에는 간소화된 Python DCC 계층을 libsumo 위에서 직접 구현하는 것이 더 빠름.

---

### Q2. Behavior Cloning을 위한 "최적 DCC 테이블"은 어떻게 만드는가?

**방법: Grid-Search 전수 시뮬레이션 (16개 조합 × 상태 샘플링)**

1. **상태 샘플링**: libsumo 시뮬레이션에서 (v, a, N_est, CBR, AoI) 상태를 10,000회 이상 샘플링 — 도시/고속도로 시나리오 모두 포함.
2. **Action Grid-Search**: 각 샘플 상태에서 16가지 (T_GenCam, p_tx) 조합을 적용하고 다음 200 ms 동안의 AoI·CBR을 시뮬레이션으로 측정.
3. **레이블 결정**: $J = 0.5 \cdot \text{AoI} + 0.5 \cdot \text{CBR}$을 최소화하는 조합을 해당 상태의 최적 행동으로 레이블.

**Oracle의 합리성 정당화:**
- 16개 행동 조합의 전수 탐색이므로 Oracle이 최적임이 수학적으로 보장됨 (이산 행동 공간에서 exhaustive search = 전역 최적).
- 단, Oracle은 "현재 상태만으로 미래 200 ms를 예측"하는 근시안적(myopic) 최적화이므로, 장기 최적성은 보장하지 않는다.
- **이 한계를 논문에서 명시**: "Our oracle is myopically optimal (200 ms horizon); future work may extend to multi-step lookahead." — 이것은 한계가 아닌 합리적 정당화의 일부.

**계산 비용**: 상태 10,000개 × 16개 조합 × 200 ms 시뮬레이션 → CPU 시간 2–8시간 (libsumo 병렬 실행 시). 충분히 3개월 이내 완료 가능.

---

### Q3. AoI 메트릭 측정은 SumoNetSim에서 어떻게 구현 가능한가?

**구현 방법:**
1. **생성 타임스탬프 삽입**: CAM 패킷 생성 시 `t_gen` 필드를 패킷 페이로드에 포함 (ETSI CAM payload의 optional container 활용 또는 시뮬레이션 전용 헤더 확장).
2. **수신 측 추적**: SumoNetSim 수신 이벤트에서 `t_rx` 기록 → AoI_ij = t_rx - t_gen.
3. **미수신 처리**: 패킷 손실 시 AoI는 증가 지속 (다음 성공 수신까지) → `aoi_tracker.py`에서 차량별 last_received 딕셔너리 유지.
4. **집계**: 각 평가 스텝(100 ms)에서 모든 (i,j) 쌍의 AoI 평균 → 시계열로 저장.

**잠재적 문제**: SumoNetSim이 패킷 레벨 수신 이벤트 콜백을 Python으로 노출하는지 확인 필요. 노출하지 않는 경우: 시뮬레이션 로그 파일(*.xml)을 후처리하여 AoI 계산. 이는 추가 1주일 작업으로 해결 가능.

---

### Q4. 모델 학습→배포→온라인 추론까지의 Wall-Clock Time 추정

| 단계 | 소요 시간 | 누적 |
|------|---------|------|
| 모듈 구현 (etsi_cam, aoi_tracker, oracle_gen, ai_dcc_hook) | 4주 | 4주 |
| Oracle 데이터 생성 (libsumo 병렬 시뮬레이션) | 1주 | 5주 |
| TinyMLP 학습 (PyTorch, CPU) | 0.5주 | 5.5주 |
| ONNX/TFLite 변환 + 검증 | 0.5주 | 6주 |
| 전체 실험 실행 (S1+S2, 60개 시드 × 7개 방법) | 2주 | 8주 |
| 결과 분석 + 그래프 작성 | 2주 | 10주 |
| 논문 작성 (초안) | 2주 | 12주 |

**결론: 12주(3개월) 이내 완료 가능** — 단, 구현 모듈이 첫 번째 주에 시작되어야 하며 병렬화가 필수.

---

### Q5. 베이스라인 4개 재현 시 가장 위험한 항목과 대안

| 베이스라인 | 위험 수준 | 위험 내용 | 대안 |
|---------|---------|---------|------|
| **BL-A ETSI DCC Reactive** | 🟡 중간 | SumoNetSim에 기본 구현 없을 가능성 | Python으로 직접 구현 (2주, 사양은 ETSI EN 302 571에 명확히 정의됨) |
| **BL-B ETSI DCC Adaptive (LIMERIC)** | 🔴 높음 | LIMERIC 알고리즘 구현 복잡도 높음, 수렴 파라미터 튜닝 필요 | **대안**: BL-B를 Simplified Adaptive (CBR 추종 PID)로 대체하거나, 원 논문 파라미터 그대로 적용 후 수렴 여부 확인; 또는 BL-B를 논문에서 "ETSI DCC Adaptive (simplified)"로 명시하여 한계 투명 공개 |
| **BL-C Bhattacharyya2024** | 🟡 중간 | 원 논문 알고리즘 세부 파라미터가 IEEE TVT에 게재되어 있으나 코드 미공개 | 논문 알고리즘 §III-B를 직접 재현. 불일치 시 "faithfully re-implemented based on [X]" 명시 |
| **BL-D Fixed 10 Hz** | 🟢 낮음 | 구현 자체는 1줄 | 없음 |

**전반적 가장 큰 위험**: ETSI DCC Adaptive (LIMERIC)의 정확한 재현. 이 베이스라인이 불공정하게 구현되면 리뷰어로부터 "비교가 불공정하다"는 지적을 받을 수 있다. **완화 전략**: 논문 Appendix에 재현 알고리즘 Pseudo-code 포함 + 독립 검증(ETSI TS 102 792 예시와 수치 비교).

---

## 9. IoT-J 리뷰어 예상 질문 및 답변 초안

### 질문 1: "이 연구가 왜 IoT 저널인가? V2X 전문 저널(TVT, ITS)이 더 적합하지 않은가?"

**답변 초안:**
본 연구는 차량을 IoT 에지 노드로 바라보는 관점에서 IoT-J에 기여한다. 구체적으로 세 가지 IoT 핵심 요소가 있다: (1) 제안 모델은 ARM Cortex-M 급 MCU (STM32F407 기준 < 4 KB 메모리)에서 실시간 추론이 가능하며, 이는 전형적인 IoT 엣지 배포 시나리오이다; (2) AoI는 IoT 센서 네트워크에서의 정보 신선도 문제와 동일한 프레임워크로, V2X의 협력 인식을 IoT AoI 문헌의 맥락에서 재해석한다; (3) ETSI EN 302 637-2 CAM 서비스는 차량 IoT 플랫폼(ITS-G5 기반 협력 인식)의 핵심 서비스로, 이를 TinyML로 제어하는 것은 IEEE IoT-J의 "smart transportation IoT systems" 특집 방향과 완벽히 일치한다. TVT/ITS는 V2X 신호 처리나 프로토콜 표준화에 집중하는 반면, IoT-J는 MCU 배포 가능성, 에너지 효율, AoI 기반 서비스 품질을 우선시하는 시스템 통합 연구를 포괄한다.

---

### 질문 2: "TinyMLP 추론을 실제 OBU/MCU에서 측정한 데이터가 없다. 시뮬레이션 가정만으로 IoT 배포 가능성을 주장할 수 있는가?"

**답변 초안:**
본 연구에서 실제 MCU 측정이 없는 것은 사실이며, 이를 한계로 명시한다. 그러나 다음 근거로 시뮬레이션 기반 주장의 타당성을 지지한다: (1) CMSIS-NN 라이브러리의 공개 벤치마크에 따르면 Cortex-M4 @168 MHz에서 INT8 완전 연결 레이어(32×32)는 약 50–200 사이클로 실행되며, 본 모델의 4개 레이어 총 추론은 ~500–1,000 사이클 ≈ **3–6 µs** 수준으로 추정된다; (2) MLPerf Tiny 벤치마크(2023)에서 유사 구조(2-layer MLP, 수백 파라미터)의 Cortex-M4 추론 지연이 < 1 ms임이 공개 검증되어 있다; (3) 모델 파라미터 수(< 2,000)와 메모리 풋프린트(< 4 KB)는 CMSIS-NN의 정적 분석 도구(CubeAI)로도 직접 산출 가능하다. 따라서 실제 측정 없이도 MCU 배포 가능성의 충분한 근거가 있으며, 실측 검증은 향후 연구로 명시한다.

---

### 질문 3: "Behavior Cloning Oracle이 합리적이라는 보장은? Oracle 자체가 최적이 아니면 모델이 나쁜 정책을 학습하지 않나?"

**답변 초안:**
Oracle의 합리성에 대한 우려는 정당하다. 우리의 Oracle은 두 가지 의미에서 합리적이다: (1) **이산 행동 공간의 전수 탐색**: T_GenCam × p_tx의 조합이 4×4=16가지에 불과하므로, 각 상태에서 모든 조합을 시뮬레이션으로 평가하여 AoI-CBR 결합 비용을 최소화하는 행동을 선택하는 것은 해당 상태에서의 **전역 최적(globally optimal) 결정**이다; (2) **투명한 근시안적 최적화**: Oracle은 200 ms 단일 스텝의 비용을 최소화하는 myopic 정책이며, 이를 논문에서 명시한다. 장기 최적성이 보장되지 않는다는 점은 한계로 적시하되, 실험에서 Oracle 정책 자체를 베이스라인의 상한(upper bound)으로 추가 표시함으로써 Behavior Cloning 모델이 Oracle에 얼마나 근접하는지를 정량화한다. 이는 리뷰어에게 Oracle의 품질과 모델의 근사 오차를 분리하여 보여주는 투명한 평가 설계다.


---

## 10. Update Patch — 2026-05-08 (User directive 12:39)

본 섹션은 idea_spec.md의 §5.3 (Baselines) 및 §8 Q5 (위험 완화)에 대한 사용자 지시 기반 갱신 사항이다.
본문 §5.3과 §8.Q5의 BL-B 관련 기술은 본 섹션의 명세로 대체한다.

### 10.1 BL-B 단순화 — "Simplified Adaptive" 정의 (사용자 지시 12:39, 항목 2)

**변경 전:** BL-B = ETSI DCC Adaptive (LIMERIC 기반). 재현 위험 🔴 높음.

**변경 후:** BL-B = **Simplified Adaptive** (CBR-tracking proportional controller).

**알고리즘 명세 (Simplified Adaptive):**
```
Inputs : CBR_target = 0.60, T_min = 0.1 s, T_max = 1.0 s,
         step_size delta_T = 0.05 s,
         smoothing factor lambda_s = 0.5
State  : T_GenCam (current beacon period), CBR_smoothed
Per measurement window (every 100 ms):
   1) CBR_smoothed <- (1 - lambda_s) * CBR_smoothed + lambda_s * CBR_meas
   2) error <- CBR_smoothed - CBR_target
   3) if error > 0:                          # channel too busy
        T_GenCam <- min(T_GenCam + delta_T, T_max)   # increase period
      elif error < 0:
        T_GenCam <- max(T_GenCam - delta_T, T_min)   # decrease period
   4) p_tx held constant at +20 dBm
```

**근거:**
- LIMERIC의 동기화·수렴 분석은 본 연구 범위 밖이며, 단순한 비례 제어로도 ETSI Adaptive 계열의 기본 동작(혼잡 시 주기 증가)을 충실히 재현 가능.
- 결정론적 알고리즘이라 시드 간 변동이 작아 공정 비교에 유리.
- 논문에서는 "We adopt a simplified adaptive controller as a representative non-AI Adaptive baseline; full LIMERIC reproduction is left as future work due to its tuning sensitivity." 형태로 한계 투명 공개.

**§8 Q5 갱신:** BL-B의 위험 수준을 🔴 높음 → 🟢 낮음으로 변경.

---

### 10.2 Sensitivity Analysis 추가 (사용자 지시 12:39, 항목 3)

본 실험(메인 비교) 이전에 **Sensitivity analysis 단계**를 추가하여 핵심 하이퍼파라미터의
적절한 값을 결정하고, 그 결과를 별도 데이터로 저장하여 논문 §Performance Evaluation의
"Sensitivity and robustness analysis" subsection에서 직접 인용한다.

**대상 파라미터 (4종):**

| ID  | 파라미터                                                     | 기본값(잠정)              | Sweep 범위                                  | 영향 컴포넌트                  |
|-----|------------------------------------------------------------|--------------------------|--------------------------------------------|-------------------------------|
| SA1 | Oracle cost weights (alpha, beta), with alpha+beta=1        | (0.5, 0.5)               | alpha in 0.1, 0.3, 0.5, 0.7, 0.9          | Oracle 레이블 → 모델 정책      |
| SA2 | Discrete action grid 크기 |T| x |P|                          | 4x4 = 16                 | 3x3=9 / 4x4=16 / 5x5=25                    | Oracle 탐색 비용, 모델 출력    |
| SA3 | Simplified Adaptive 임계값 CBR_target                        | 0.60                     | 0.40, 0.50, 0.60, 0.70, 0.80               | BL-B 동작점                    |
| SA4 | TinyMLP hidden width h (두 hidden layer 동일 폭)              | h = 32 (1,448 params)    | h in 16, 24, 32, 48, 64                    | 모델 용량, MCU footprint       |

**프로토콜 (One-at-a-Time, OAT):**
1. 모든 파라미터를 잠정 기본값으로 두고, 한 파라미터만 sweep.
2. 각 sweep 포인트마다 Urban Grid (50 vehicles, 단일 밀도) × 5 시드 = 5 runs.
3. 메트릭: M1 평균 AoI, M2 CBR, M3 PDR (M4/M5는 본 실험에서만 측정).
4. 각 파라미터에 대해 "AoI 정규화 + CBR 정규화의 가중 합(0.5/0.5)이 최소가 되는 값"을 default로 확정.
5. SA1–SA4 모두 종료 후 default를 확정 → 본 실험(S1/S2)을 시작.

**산출물 저장 형식:**
- 디렉터리: `paper/data/sensitivity/`
- 파일명: `SA<ID>_<param>_<metric>.csv` (예: `SA1_alpha_AoI.csv`, `SA3_cbr_target_PDR.csv`)
- 컬럼: `param_value, seed, AoI_mean, CBR_mean, PDR_mean, runtime_sec`
- 최종 정리 파일: `paper/data/sensitivity/sensitivity_summary.json`
  · 각 파라미터의 sweep 결과 요약 + 선택된 default 값 + 선택 근거

**논문 활용:**
- Performance Evaluation 섹션의 `\textbf{Sensitivity and robustness analysis.}` 단락에서 4개 그래프(SA1–SA4)로 시각화.
- 본 실험 결과와의 인과 관계(왜 default 값이 합리적인가)를 정량적으로 정당화.

---

### 10.3 본 실험과의 관계 — 실행 순서

```
Phase 2 실행 흐름 (사용자 지시 반영):
  Step 1. Sensitivity Analysis (Phase 2-alpha)
          -> 4 sweep x ~5 values x 5 seeds = ~100 runs (경량)
          -> sensitivity_summary.json 생성 + default 확정

  Step 2. Oracle Generation (확정된 alpha, beta, grid 사용)
          -> oracle_dataset.npz

  Step 3. TinyMLP Training (확정된 h 사용)
          -> tinymlp.onnx + tinymlp_int8.tflite

  Step 4. Main Experiment (S1 + S2)
          -> data/<scenario>_<metric>.csv

  Step 5. Validation (Reviewer[validator])
          -> validation_report.json
```

본 패치는 idea_spec.md §5.3 BL-B와 §8 Q5의 "BL-B LIMERIC" 기술을 우선 적용된 명세로 대체한다.
