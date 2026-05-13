# Idea Agent Memory Log

## [2026-04-28] 사용자 연구 컨텍스트 분석

**분석 세션 유형**: Self-publication 연구 흐름 분석 전용 (idea_spec.md 미작성)
**분석 대상**: Youngju Nam 연구자의 발표 논문 21편 (2020–2026)
**데이터 출처**: workspace/paper/references/references.json (Librarian 정리본)

---

### 1. 연구자 한 줄 정의

> **"이동 차량 환경(VANET/CCN/CIoV)에서 콘텐츠 프리캐싱 최적화를 핵심 정체성으로 삼고, 이동성 예측·강화학습·RSU 협력으로 진화시켜온 네트워킹 연구자"**

---

### 2. 논문 통계 요약

| 항목 | 수치 |
|------|------|
| 총 논문 수 | 21편 |
| First Author | 8편 (38.1%) |
| Co-Author | 13편 (61.9%) |
| 연구 기간 | 2020–2026 (6년) |
| 피크 발표 연도 | 2022 (7편) |

**게재 저널 분포**
- MDPI (Electronics, Sensors): 13편 (tier3)
- IEEE (Access, IoT Journal): 4편 (tier1)
- Elsevier (Ad Hoc Networks): 3편 (tier2)
- AIMS MATH: 1편

---

### 3. 시간순 발전 과정 (2020–2026)

#### Phase 1 (2020–2021): VANET 탐색기 — 데이터·콘텐츠 전달 프로토콜 입문
- [2020, CA] Shin2020: 도로 궤적 정보 기반 VANET 데이터 전달 프로토콜
- [2021, **FA**] Nam2021: **속도 예측 기반 Adaptive Content Precaching in CCN vehicular** ← 첫 독립 주제 확립
- [2021, CA] Shin2021: VANET 비디오 패킷 분배 스킴

**특징**: Shin이 주도하는 VANET 연구팀에서 Co-Author로 시작 → 2021년 Content-Centric Vehicular Networks의 Precaching에서 독자 방향 발견

#### Phase 2 (2022): 연구 폭발적 확장기 — 7편 발표 (피크)
- [**FA**] Nam2022a: Cooperative Content Precaching (이동성 정보 활용, 단속 연결 환경)
- [**FA**] Nam2022b: WSN Mobile Sink 라우팅 (이색적 진출)
- [**FA**] Nam2022c: RSU-Aided Optimal Member Replacement for Vehicular Clouds
- [CA] Choi2022a: Partial Cloud Member Replacement (reactive/proactive)
- [CA] Choi2022b: Multiple Member Vehicle Replacement in Vehicular Clouds
- [CA] Mugerwa2022: SF-Partition LoRa 클러스터링 (첫 LoRa 논문)
- [CA] Shin2022: PSO 비디오 스트리밍 (IEEE Access)

**특징**: Precaching ↔ Vehicular Cloud ↔ LoRa 3개 주제 동시 탐색. Nam이 FA로 3편 발표하며 독립 연구자로 성장

#### Phase 3 (2023): 선택과 집중 — 3편, Precaching 심화
- [**FA**] Nam2023a: 지연 허용시간 기반 Traffic-Optimized Precaching (**IEEE Access** — 저널 격상)
- [**FA**] Nam2023b: Set Ranking 기반 다중 프리캐싱 차량 선택
- [CA] Mugerwa2023: Implicit Overhearing Node 기반 IoT LoRa 멀티홉

**특징**: Vehicular Cloud 주제에서 거리 두기 → Content Precaching에 집중. 첫 IEEE tier1 FA 논문 게재

#### Phase 4 (2024): 통합 준비기 & UAV 확장 — 4편
- [CA] Choi2024a: Resource Cluster-Based Resource Allocation for Vehicular Clouds
- [CA] Choi2024b: Mobility-Based Multi-Hop Content Precaching (CCN)
- [CA] Mugerwa2024: Adaptive Mobility-Based IoT LoRa Clustering
- [CA] Shin2024: PSO-Based Content Delivery for **UAV VANETs** (IEEE Access) ← 새 영역

**특징**: FA 논문 없음. 팀 전체로 연구 정리하며 UAV VANET 새 방향 탐색. 2025 대작을 위한 준비 단계로 해석 가능

#### Phase 5 (2025–2026): CIoV 통합 + 강화학습 도입
- [2025, **FA**] Nam2025: CCN 기반 IoV(CIoV) 통합 프레임워크, Content Storage Management & Precaching — **IEEE Internet of Things Journal** (최고 저널)
- [2026, **FA**] Nam2026: **SAC(Soft Actor-Critic) 강화학습** 기반 Precaching 차량 선택 in CIoV
- [2026, CA] Shin2026: PSO 기반 동적 RSU 역할 배분 프레임워크 (VANETs)
- [2026, CA] Youn2026: V2V 릴레이 동적 할당 for Content Precaching in CIoV

**특징**: VANET → CCN → CIoV(Content-Centric IoV)로 패러다임 전환 완성. 강화학습(SAC) 도입으로 최적화 도구 진화. RSU·V2V 협력 시스템화.

---

### 4. 주제 클러스터별 분류

#### Cluster A: Content Precaching in CCN/CIoV (8편, 핵심 줄기)
가장 큰 줄기. Nam FA 6편 포함. 이동성 예측 → 협력 프리캐싱 → 트래픽 최적화 → 스토리지 관리 → SAC 강화학습 순으로 진화.
- Nam2021 (속도 예측 기반 Adaptive Precaching, Sensors)
- Nam2022a (Cooperative Precaching, 이동성 정보, Electronics)
- Nam2023a (Traffic Optimized, 지연 허용시간, IEEE Access ★)
- Nam2023b (Multiple Vehicle Selection, Set Ranking, Sensors)
- Choi2024b (Multi-Hop Precaching, Electronics)
- Nam2025 (CIoV Storage Management + Precaching, IEEE IoT Journal ★★)
- Nam2026 (SAC 기반 Precaching Vehicle Selection, AIMS MATH)
- Youn2026 (V2V Relay Assignment for Precaching, Electronics)

#### Cluster B: Vehicular Cloud Member Replacement / Resource Allocation (4편)
차량 클라우드의 멤버 교체·자원 탐색 문제. Nam FA 1편.
- Choi2022a (Partial Cloud Member Replacement reactive/proactive, Ad Hoc Networks)
- Nam2022c (RSU-Aided Optimal Member Replacement + 이동성 예측 향상, Electronics ★FA)
- Choi2022b (Multiple Member Replacement 스킴 설계/평가, Electronics)
- Choi2024a (Resource Cluster-Based Resource Search & Allocation, Ad Hoc Networks)

#### Cluster C: VANET 데이터·비디오 전달 프로토콜 / RSU 역할 (4편, Shin 주도)
Shin이 FA. 데이터 전달 → 비디오 스트리밍 → PSO 최적화 → RSU 역할 배분으로 진화.
- Shin2020 (궤적 기반 데이터 전달, Ad Hoc Networks)
- Shin2021 (비디오 패킷 분배, Sensors)
- Shin2022 (PSO 비디오 스트리밍, IEEE Access)
- Shin2026 (PSO-Based Dynamic RSU Role Assignment, Sensors)

#### Cluster D: IoT LoRa Multihop / Clustering (3편, Mugerwa 주도)
Mugerwa가 FA. LoRa 근거리/원거리 불균형 해소 → 오버히어링 릴레이 → 이동성 기반 클러스터링.
- Mugerwa2022 (SF-Partition Clustering, Near-Far Unfairness, Sensors)
- Mugerwa2023 (Implicit Overhearing Multi-Hop, Sensors)
- Mugerwa2024 (Adaptive Mobility-Based LoRa Clustering, Electronics)

#### Cluster E: WSN Routing for Mobile Sinks (1편)
독립적인 이색 진출. Nam FA.
- Nam2022b (Expected Area-Based Real-Time Routing for Mobile Sinks, Electronics)

#### Cluster F: UAV VANET (1편, Shin 주도, 최근 확장)
기존 VANET 연구의 3D 공간 확장.
- Shin2024 (PSO-Based Content Delivery for UAV VANETs, IEEE Access)

---

### 5. First-Author 8편의 핵심 정체성

1. **Nam2021**: CCN 차량망에서 속도 예측 기반 Adaptive Precaching → **이동성 예측이 핵심 도구임을 확립**
2. **Nam2022a**: 단속 연결 환경(intermittently connected)에서 협력 Precaching → **현실적 네트워크 조건 고려**
3. **Nam2022b**: WSN 모바일 싱크 라우팅 → **이동성 지원 프로토콜 범용성 탐색**
4. **Nam2022c**: RSU 보조 최적 멤버 교체 + 이동성 예측 개선 → **인프라(RSU) 협력 패턴 확립**
5. **Nam2023a**: 지연 허용시간 기반 Traffic-Optimized Precaching (IEEE Access) → **QoS 최적화 접근**
6. **Nam2023b**: Set Ranking 기반 다중 프리캐싱 차량 선택 → **다중 에이전트 선택 알고리즘**
7. **Nam2025**: CIoV Storage Management + Precaching (IEEE IoT Journal) → **CCN→CIoV 통합, 스토리지 관리 포함**
8. **Nam2026**: SAC(Soft Actor-Critic) 기반 Precaching 차량 선택 in CIoV → **강화학습 도입으로 최적화 도약**

**공통 정체성**: "이동성(Mobility)을 예측하고 협력 구조(RSU/V2V/Cloud)를 설계하여, 차량 네트워크의 콘텐츠 프리캐싱 효율을 최대화하는 알고리즘 설계자"

---

### 6. 협업자 & 연구실 구성 (Euisin Lee 그룹)

| 연구자 | 협업 논문 수 | 역할 |
|--------|------------|------|
| Euisin Lee | 16편 | 지도교수/그룹장 (모든 논문의 마지막 저자) |
| Hyunseok Choi (= Hyun-Seok Choi) | ~18편 | 핵심 협업자 (CCN/Vehicular Cloud FA 다수) |
| Yongje Shin | 15편 | 핵심 협업자 (VANET/비디오/UAV FA) |
| Dick Mugerwa | 6편 | LoRa 전문 협력자 (LoRa 논문 FA) |
| Jaejeong Bang | 2편 | 중기 협력자 |
| Gayeong Kim | 2편 | 후기 참여 |
| Jongpil Youn | 1편 | 2026년 V2V 릴레이 논문 FA |

**그룹 구조**: Euisin Lee 교수 중심, Choi·Shin·Nam 3인이 각각 다른 주제 담당하면서 교차 협업

---

### 7. 핵심 키워드 맵

**L1 (도메인)**: vehicular networks, VANET, CCN, CIoV, IoT, LoRa, WSN, UAV

**L2 (메커니즘)**: content precaching, mobility prediction, RSU, V2V relay, vehicular cloud, member replacement, clustering, multihop

**L3 (최적화 기법)**: SAC (Soft Actor-Critic), PSO (Particle Swarm Optimization), set ranking, tolerable delay, adaptive scheme

**L4 (문제 설정)**: intermittently connected, near-far unfairness, mobile sink, traffic optimization, content delivery, storage management

---

### 8. 저널 격상 트렌드 (연구 성숙도 지표)

```
2021-2022: MDPI Sensors/Electronics (tier3) 위주
2023: IEEE Access 첫 FA 진출 (tier1)
2024: 팀 전체 IEEE Access + Elsevier Ad Hoc Networks (정리기)
2025: IEEE Internet of Things Journal FA ← 최고 저널 진출 ★★
2026: AIMS MATH + MDPI (SAC 강화학습 적용 확장)
```

---

### 9. 강점 & 차별화 포인트

1. **이동성 예측의 일관된 활용**: 속도/방향/궤적 정보를 활용한 사전적(Proactive) 자원 배치가 모든 주제를 관통
2. **CCN→CIoV 패러다임 전환의 선구자적 포지션**: 단순 데이터 전달이 아닌, Named Data 중심의 콘텐츠 네트워킹을 차량 환경에 적용
3. **RSU 인프라 협력 + V2V 분산 구조 통합**: 중앙화(RSU)와 분산화(V2V)를 조합한 하이브리드 설계
4. **강화학습 도입**: SAC 기반의 차량 선택 최적화 → 기존 휴리스틱 방식에서 학습 기반 방식으로 진화
5. **실용적 QoS 지표 설정**: 지연 허용시간(Tolerable Delay), 트래픽 최적화, 스토리지 관리 등 실제 시스템 제약 반영

---

### 10. 향후 연구 방향 추론

**후보 1**: **Multi-agent RL (MARL) 기반 협력 Precaching in CIoV**
- 배경: SAC(단일 에이전트 RL)에서 다중 차량의 협력 의사결정으로 확장
- 연결: Nam2026(SAC) + Youn2026(V2V Relay) + Nam2023b(Multiple Vehicle Selection)의 자연스러운 융합

**후보 2**: **UAV-Assisted CIoV Content Precaching**
- 배경: UAV VANET(Shin2024) + CIoV Precaching(Nam2025, Nam2026) 교차
- UAV를 이동형 RSU 또는 중계 노드로 활용한 3D 콘텐츠 프리캐싱 최적화

**후보 3**: **Digital Twin 또는 Semantic Communication 기반 Content Delivery in CIoV**
- 배경: 최신 6G/B5G 트렌드와 기존 CCN/CIoV 프레임워크의 융합
- 디지털 트윈으로 차량 이동성을 정밀 예측 → Precaching 정확도 향상

---

### 메모
- idea_spec.md 미작성 (분석 전용 세션, 2026-04-28)
- 새 아이디어 설계는 다음 세션에서 위 방향 후보를 기반으로 진행 가능


---

## [2026-04-28 21:04] ILP 기반 후속 연구 후보 도출 (방향 전환 세션)

**세션 유형**: ILP 기반 후속 논문 아이디어 설계 (사용자 명시 방향 전환)
**사용자 지시 요약**: AI/ML(강화학습·지도학습) 색채 배제 → 본인의 ILP 기반 최적화 정체성으로 복귀
**제약 조건**: libsumo 시뮬레이션 가능 규모, ILP 정식화 필수, 기존 FA 논문 라인 연속성
**상태**: 후보 3개 도출 완료, 사용자 선택 대기

---

### [후보 A] ILP 기반 RSU-차량 협력 콘텐츠 배치 및 프리캐싱 차량 선택 최적화

#### 제목 (가제)
**"Joint RSU Content Placement and Precaching Vehicle Selection via Integer Linear Programming in Content-Centric IoV"**

#### 한 줄 요약 + 기존 논문 연결
> RSU의 콘텐츠 저장 배치(placement)와 프리캐싱 담당 차량 선택을 동시에 ILP로 최적화.  
> **Nam2025** (CIoV Storage Management + Precaching) + **Nam2023a** (Traffic-Optimized Precaching) + **Nam2023b** (Multiple Vehicle Selection)의 직접 후속.

#### 문제 설정 (System Model 개략)
- **네트워크**: 도로 구간 위 RSU R개 설치, 콘텐츠 카탈로그 C개, 차량 V대 이동
- **시간 모델**: 슬롯 기반 (slot t = 1…T, T = 600~3600초)
- **콘텐츠 요청**: 차량이 특정 콘텐츠를 요청, RSU 캐시 히트 시 즉시 제공, 미스 시 프리캐싱 차량에서 V2V 전달
- **핵심 결정**: 슬롯 t에 RSU r이 콘텐츠 c를 저장할지(placement), 차량 v가 해당 콘텐츠를 이웃 차량에 프리캐싱할지(precaching vehicle selection)
- **목표**: 총 캐시 히트율 최대화 + 백홀 트래픽(RSU↔서버) 최소화

#### ILP 정식화 스케치

**결정변수**
```
x_{r,c,t} ∈ {0,1}  : 슬롯 t에 RSU r이 콘텐츠 c를 저장하면 1
y_{v,c,t} ∈ {0,1}  : 슬롯 t에 차량 v가 콘텐츠 c를 프리캐싱(담당 차량)이면 1
z_{v,r,t} ∈ {0,1}  : 슬롯 t에 차량 v가 RSU r의 통신 범위 내에 있으면 1 (libsumo 입력)
```

**목적함수**
```
Maximize  Σ_{v,c,t} [ x_{r(v,t),c,t} + Σ_{u∈N(v,t)} y_{u,c,t} ] · d_{v,c,t}
         - α · Σ_{r,c,t} x_{r,c,t} · (1 - x_{r,c,t-1})   (배치 변경 비용 페널티)
```
(d_{v,c,t}: 차량 v의 콘텐츠 c 요청 여부; N(v,t): t에서 v의 V2V 이웃; α: 트래픽 가중치)

**주요 제약식**
```
(C1) 저장 용량: Σ_c x_{r,c,t} ≤ S_r        ∀r, t     (RSU r의 캐시 용량 S_r)
(C2) 차량 캐시: Σ_c y_{v,c,t} ≤ B_v        ∀v, t     (차량 v의 캐시 용량 B_v)
(C3) 통신 범위: y_{v,c,t} ≤ z_{v,r,t}      ∀v,c,t,r  (RSU 범위 내 차량만 선택 가능)
(C4) 이동성 연속성: y_{v,c,t} ≤ y_{v,c,t+1} + (1-z_{v,r,t+1})  (범위 이탈 시 재선택)
(C5) 대역폭: Σ_v y_{v,c,t} · b_c ≤ BW_r   ∀r, t     (RSU 업링크 대역폭 BW_r)
```

**문제 규모**: |R|=5, |C|=50, |V|=100, T=60 슬롯 → 변수 수 ≈ 5×50×60 + 100×50×60 ≈ 315,000  
(NP-hard; 소규모 instance CPLEX/PuLP 최적해 가능, 대규모 → 다음 절 전략)

#### libsumo 시뮬레이션 시나리오
- **도로망**: SUMO 내장 grid/suburban 네트워크 또는 실제 도로 (e.g., Daejeon 시내 격자)
- **차량 수**: 100~200대, 랜덤 출발/목적지 (uniformly random trips)
- **RSU 배치**: 주요 교차로 5~7개소 (통신 범위 150~300m)
- **시뮬레이션 시간**: 1800~3600초, 슬롯 크기 30초
- **콘텐츠 카탈로그**: 50개 콘텐츠, Zipf(α=0.8) 분포로 요청 생성
- **libsumo 추출 데이터**: 차량 위치·속도·경로(traci.vehicle.getPosition/getSpeed/getRoute), RSU 범위 내 차량 목록

#### 비교 베이스라인
1. **ILP 최적해** (제안): CPLEX/PuLP, 소규모 instance 검증
2. **Greedy Heuristic**: 인기도(popularity) 내림차순 RSU 배치 + 체류시간 기반 차량 선택
3. **LP Relaxation**: x, y를 연속 변수로 완화 → 상한(upper bound) 분석
4. **Nam2025 기존 방식 (룰 기반)**: 기존 논문의 휴리스틱 알고리즘과 직접 비교 (★)

#### 예상 노벨티 (기존 논문 대비)
- **Nam2025** 대비: 스토리지 관리만 했던 것을 RSU 배치 + 차량 선택 **동시 최적화**로 격상
- **Nam2023b** 대비: Set Ranking 휴리스틱에서 **ILP 최적해**로 전환 → 최적성 갭 정량화
- **기술적 기여**: ILP 정식화로 최적성 보장 + LP relaxation 갭 분석이라는 이론적 기여 추가

#### NP-hardness 및 Scalability 전략
- **NP-hardness 증명**: Set Cover 또는 Generalized Assignment Problem으로 귀납 (간단히 증명 가능)
- **소규모 최적해**: |V|≤30, |C|≤20, T≤10 슬롯에서 CPLEX/PuLP 정확해
- **대규모 휴리스틱**: Column Generation 또는 Lagrangian Relaxation 기반 분해법
- **실용적 대안**: Sliding window (슬롯 단위 greedy) + 이동성 예측(Nam2021 방법 재활용)

---

### [후보 B] ILP 기반 이동성 인식 차량 클라우드 형성 및 콘텐츠 할당 최적화

#### 제목 (가제)
**"ILP-Based Joint Vehicular Cloud Formation and Content Task Assignment with RSU-Assisted Mobility Prediction in VANETs"**

#### 한 줄 요약 + 기존 논문 연결
> RSU 보조 이동성 예측 정보를 활용하여, 차량 클라우드 멤버 구성과 각 멤버의 콘텐츠 처리 태스크 배분을 ILP로 동시 최적화.  
> **Nam2022c** (RSU-Aided Optimal Member Replacement) + **Choi2024a** (Resource Cluster-Based Allocation) + **Nam2021** (Speed-based Mobility Prediction)의 직접 후속.

#### 문제 설정 (System Model 개략)
- **네트워크**: 도로 위 차량들이 자발적 클라우드(VC) 구성, RSU가 멤버십 관리 지원
- **클라우드 구조**: 클라우드 헤드(CH) 1대 + 멤버(CM) K대 (K=3~8)
- **태스크**: 콘텐츠 c를 처리·저장할 차량을 배정 (처리 능력·캐시·잔여 체류시간 고려)
- **핵심 결정**: 어떤 차량이 VC 멤버인지(formation), 각 멤버가 어떤 콘텐츠를 담당하는지(assignment)
- **목표**: VC 서비스 가용시간 최대화 + 콘텐츠 처리 총 지연 최소화

#### ILP 정식화 스케치

**결정변수**
```
m_{v,k,t} ∈ {0,1}   : 슬롯 t에 차량 v가 VC의 k번째 멤버 슬롯을 담당하면 1
a_{v,c,t} ∈ {0,1}   : 슬롯 t에 차량 v가 콘텐츠 c의 처리 담당이면 1
h_t ∈ {0,1}          : 슬롯 t에 VC가 서비스 가능 상태(정족수 충족)이면 1
r_{v,t} ∈ Z+         : 슬롯 t에서 차량 v의 예측 잔여 체류시간 (libsumo 입력)
```

**목적함수**
```
Maximize  Σ_t h_t · Δt   (VC 총 서비스 가용 시간)
Minimize  Σ_{v,c,t} a_{v,c,t} · delay_{v,c,t}   (콘텐츠 처리 지연)
→ 가중합: Maximize Σ_t h_t · Δt - β · Σ_{v,c,t} a_{v,c,t} · delay_{v,c,t}
```

**주요 제약식**
```
(C1) 멤버 수: Σ_v m_{v,k,t} = 1          ∀k, t          (각 슬롯에 정확히 1대)
(C2) 정족수: h_t ≤ (1/K) · Σ_{v,k} m_{v,k,t}  ∀t       (K명 충족 시만 가동)
(C3) 이동성: m_{v,k,t} ≤ [r_{v,t} ≥ Δt]   ∀v,k,t        (체류시간 부족 차량 제외)
(C4) 처리 능력: Σ_c a_{v,c,t} · w_c ≤ CPU_v  ∀v, t      (차량 v의 처리 능력)
(C5) 할당-멤버십: a_{v,c,t} ≤ Σ_k m_{v,k,t}  ∀v,c,t    (멤버인 차량만 할당 가능)
(C6) 커버리지: Σ_v a_{v,c,t} = 1           ∀c, t         (각 콘텐츠는 정확히 1대 담당)
```

**문제 규모**: |V|=50, K=5, |C|=30, T=30 슬롯 → 변수 수 ≈ 50×5×30 + 50×30×30 ≈ 52,500  
(NP-hard; Choi 논문들의 휴리스틱과 직접 비교 가능)

#### libsumo 시뮬레이션 시나리오
- **도로망**: 단방향 2차선 고속도로 또는 도시 격자 (SUMO highway/grid)
- **차량 수**: 50~150대, 다양한 속도 분포(30~120 km/h)
- **RSU 배치**: 3~5개소 (체류시간 예측 정확도 검증 포함)
- **시뮬레이션 시간**: 600~1800초, 슬롯 크기 60초
- **콘텐츠 태스크**: 30개 콘텐츠, 처리 부하 이질적(heterogeneous) 설정
- **libsumo 추출 데이터**: 차량 잔여 주행거리(getRoute + getDistance), 속도, RSU 진입/이탈 이벤트

#### 비교 베이스라인
1. **ILP 최적해** (제안): CPLEX/PuLP
2. **Proactive Replacement Heuristic (Choi2022a 방식)**: 기존 반응형/사전형 교체 스킴
3. **Nam2022c 이동성 예측 기반 휴리스틱**: 본인 기존 논문 방식
4. **LP Relaxation**: 연속 완화 상한 분석
5. **(선택적) SAC 기반 선택 (Nam2026)**: "ILP가 RL보다 최적에 가깝다"를 소규모에서 실증

#### 예상 노벨티 (기존 논문 대비)
- **Nam2022c** 대비: 멤버 교체만 다루던 것을 **초기 형성(formation) + 태스크 배분 동시 최적화**로 확장
- **Choi2024a** 대비: 자원 검색/할당 휴리스틱에서 **ILP 최적 정식화**로 격상
- **기술적 기여**: VC formation을 ILP로 처음 정식화 → 최적성 증명 + 이론적 하한 제시

#### NP-hardness 및 Scalability 전략
- **NP-hardness**: Bin Packing 또는 Vehicle Scheduling Problem으로 귀납
- **소규모 최적해**: |V|≤20, K≤4, |C|≤15에서 CPLEX 최적해
- **대규모 휴리스틱**: 이동성 예측 기반 Greedy (Nam2022c 재활용) + 지역 탐색(Local Search) 개선
- **롤링 호라이즌**: 슬롯 T를 짧은 구간(W개 슬롯)으로 분해 → 재귀적 ILP 풀이

---

### [후보 C] ILP 기반 다중홉 V2V 릴레이 경로 및 캐시 공간 배분 최적화 (트래픽 인식)

#### 제목 (가제)
**"Traffic-Aware ILP Optimization of Multi-Hop V2V Relay Path Selection and Cache Allocation for Content Precaching in CIoV"**

#### 한 줄 요약 + 기존 논문 연결
> 단속 연결 CIoV 환경에서 다중홉 V2V 릴레이 경로 선택과 각 릴레이 차량의 캐시 공간 배분을 ILP로 동시 최적화하여 트래픽 부하를 최소화.  
> **Youn2026** (Dynamic V2V Relay Assignment) + **Nam2023a** (Traffic-Optimized Precaching) + **Choi2024b** (Multi-Hop Precaching)의 직접 후속.

#### 문제 설정 (System Model 개략)
- **네트워크**: CIoV 환경, RSU → 차량 → 다중홉 V2V → 목적 차량으로 콘텐츠 전달
- **릴레이 구조**: 최대 H홉 (H=2~4), 각 홉에서 릴레이 차량 선택 + 캐시 공간 결정
- **트래픽 모델**: 각 V2V 링크의 트래픽 부하(전송량)가 네트워크 혼잡에 기여
- **핵심 결정**: 콘텐츠별 최적 릴레이 경로(path) + 각 릴레이 차량의 할당 캐시 크기(cache size)
- **목표**: 총 V2V 전송 트래픽 최소화 + 콘텐츠 전달 성공률 최대화

#### ILP 정식화 스케치

**결정변수**
```
p_{v,c,h,t} ∈ {0,1}  : 슬롯 t에 차량 v가 콘텐츠 c의 h번째 홉 릴레이이면 1
f_{v,c,t} ∈ Z+        : 슬롯 t에 차량 v가 콘텐츠 c에 할당한 캐시 블록 수 (정수)
e_{u,v,t} ∈ {0,1}     : 슬롯 t에 차량 u와 v 사이에 V2V 링크가 있으면 1 (libsumo 입력)
q_{c,t} ∈ {0,1}       : 슬롯 t에 콘텐츠 c가 목적 차량에 성공 전달되면 1
```

**목적함수**
```
Minimize   Σ_{v,c,t} p_{v,c,h,t} · traffic_{v,c}   (총 V2V 전송 트래픽)
Maximize   Σ_{c,t} q_{c,t}                          (전달 성공 콘텐츠 수)
→ 가중합: Minimize Σ traffic - γ · Σ q_{c,t}
```

**주요 제약식**
```
(C1) 경로 연속성: Σ_v p_{v,c,h,t} = 1        ∀c,h,t    (홉당 정확히 1개 릴레이)
(C2) 링크 존재: p_{u,c,h,t} + p_{v,c,h+1,t} ≤ 1 + e_{u,v,t}  ∀u≠v,c,h,t  (연결된 차량끼리만 이어짐)
(C3) 캐시 배분: Σ_c f_{v,c,t} ≤ CAP_v        ∀v, t     (차량 v 총 캐시 용량)
(C4) 최소 캐시: p_{v,c,h,t} · minblk_c ≤ f_{v,c,t}  ∀v,c,h,t  (릴레이라면 최소 캐시 확보)
(C5) 전달 성공: q_{c,t} ≤ Σ_{v,h} p_{v,c,h,t} / H   ∀c,t   (H홉 모두 충족 시 성공)
(C6) 홉 수 제한: Σ_h Σ_v p_{v,c,h,t} ≤ H            ∀c,t
```

**문제 규모**: |V|=100, |C|=50, H=3, T=60 슬롯 → 변수 수 ≈ 100×50×3×60 + 100×50×60 ≈ 1,200,000  
(대규모; 소규모 검증: |V|=20, |C|=10, H=2, T=10)

#### libsumo 시뮬레이션 시나리오
- **도로망**: SUMO 도시 격자 (5×5 또는 실제 도로망 osm 임포트)
- **차량 수**: 100~300대, 고밀도/저밀도 시나리오 각각 테스트
- **RSU 배치**: 7~10개소 (콘텐츠 주입 원점 역할)
- **시뮬레이션 시간**: 1800~3600초, 슬롯 크기 30초
- **콘텐츠 카탈로그**: 50개 콘텐츠 (크기 이질적: 10MB~500MB)
- **libsumo 추출 데이터**: V2V 링크 존재 여부(거리 기반 통신 범위 내 차량 쌍 계산), 속도, 위치, 경로

#### 비교 베이스라인
1. **ILP 최적해** (제안): CPLEX/PuLP (소규모)
2. **Shortest Path Relay (Hop-count Greedy)**: 홉 수 최소 경로 + 균등 캐시 배분
3. **Youn2026 동적 릴레이 할당 방식**: 기존 V2V 릴레이 논문 방식과 직접 비교
4. **LP Relaxation**: 연속 완화 상한
5. **(선택적) Nam2023a 지연 허용시간 기반 방식**: 트래픽 최적화 관점 비교

#### 예상 노벨티 (기존 논문 대비)
- **Youn2026** 대비: 단순 릴레이 배정에서 **경로 + 캐시 배분 동시 최적화 ILP**로 격상
- **Choi2024b** 대비: 멀티홉 휴리스틱에서 **ILP 정식화 + 최적성 분석**으로 이론적 기여 추가
- **Nam2023a** 대비: 트래픽 최적화를 RSU 수준에서 **V2V 다중홉 경로 수준으로 세분화**
- **기술적 기여**: V2V 다중홉 경로 선택과 캐시 배분의 coupled ILP 정식화 → 문제 구조 분석

#### NP-hardness 및 Scalability 전략
- **NP-hardness**: Multi-commodity Flow + Bin Packing 복합 문제 → NP-hard 증명
- **소규모 최적해**: |V|≤20에서 PuLP + CBC solver
- **대규모 휴리스틱**: 
  - 경로 선택: Dijkstra 기반 체류시간 가중 최단 경로
  - 캐시 배분: Knapsack-style Greedy (인기도 × 체류시간 / 크기 내림차순)
- **분해 방법**: Benders Decomposition (경로 선택 Master + 캐시 배분 Sub-problem)

---

### 3개 후보 비교표 및 추천 우선순위

| 항목 | 후보 A (RSU+차량 배치) | 후보 B (VC 형성+할당) | 후보 C (릴레이 경로+캐시) |
|------|----------------------|---------------------|------------------------|
| **기존 FA 연속성** | ★★★ (Nam2025, Nam2023a, Nam2023b 직결) | ★★☆ (Nam2022c, Choi 시리즈) | ★★☆ (Youn2026, Nam2023a, Choi2024b) |
| **ILP 실현 가능성** | ★★★ (변수 구조 단순, PuLP 구현 용이) | ★★★ (소규모 feasible, 변수 명확) | ★★☆ (대규모, 소규모 검증 필수) |
| **libsumo 시뮬레이션** | ★★★ (RSU 범위/차량 위치로 직접 구성) | ★★★ (잔여 체류시간 예측 활용) | ★★☆ (V2V 링크 계산 추가 필요) |
| **노벨티 수준** | ★★★ (동시 최적화 + 기존 대비 명확한 격상) | ★★☆ (VC formation ILP는 신선, Choi 선행 많음) | ★★★ (경로+캐시 coupled ILP, 이론 기여 높음) |
| **논문 게재 난이도** | 중 (IEEE Access/Sensors 적합) | 중 (Electronics/Ad Hoc Networks 적합) | 중상 (IEEE Access/Ad Hoc 상위권 가능) |
| **추천 우선순위** | **🥇 1순위** | **🥉 3순위** | **🥈 2순위** |

#### 추천 이유 요약
- **1순위 (후보 A)**: Nam2025(최고 저널)의 가장 자연스러운 ILP 후속. 변수 구조가 단순하여 PuLP 구현이 현실적. RSU 배치 + 차량 선택 동시 최적화라는 명확한 novelty. libsumo로 시나리오 구성 가장 용이.
- **2순위 (후보 C)**: 이론적 기여(coupled ILP)가 높고 Youn2026·Choi2024b의 직접 후속이지만, 변수 규모가 커서 구현 난이도가 A보다 높음. 시간 여유가 있으면 최고의 선택.
- **3순위 (후보 B)**: Vehicular Cloud 주제는 Nam이 거리를 두어온 방향(2022 이후 FA 없음). Choi 협업으로 공저 가능하지만 Nam의 독자 FA 논문으로는 핏이 약간 낮음.

**사용자 선택 후 다음 단계**: 선택된 후보에 대해 idea_spec.md 작성 (시스템 모델 세부화, ILP 코드 스켈레톤, 실험 설계 포함)

---

*Last updated: 2026-04-28 21:04 | Status: 후보 3개 도출 완료, 사용자 선택 대기*

---

## [2026-04-29] ML 배제 후속 scheme 회의

**세션 유형**: 후속 논문 Next Scheme 제안 회의 (사용자 2026-04-29 09:11 지시)
**핵심 제약**: ML/RL/DL 완전 배제, ILP+휴리스틱+증명 OR 형식 우선, IoT-J 타겟
**시뮬레이터**: SumoNetSim1.1.6 (5×5 RSU grid, RSU range=800m, Outage=800m)
**베이스 코드**: 7. V2I Precaching.py + 8. V2V Precaching.py

### 도출된 3개 후보 요약

| 안 | 제목 (가제) | 출발점 FA 논문 | IoT-J 점수 | 추천 순위 |
|----|-------------|---------------|-----------|----------|
| 1 ★ | Outage-Aware ILP-Based Precaching Vehicle Selection in CIoV | Nam2023b + Youn2026 | 9/10 | 🥇 1순위 |
| 2 | LET-Driven RSU Cache Replacement for Content Precaching in CIoV | Nam2025 + Nam2023a | 8/10 | 🥈 2순위 |
| 3 | Joint RSU-Vehicle Selection for Multi-Content Precaching via ILP in CIoV | Nam2022a + Nam2023b + Nam2025 | 8.5/10 | 🥉 3순위 |

### 추천 안 1 핵심 요약
- **문제**: 8번 코드 VehicleSelection()의 단순 룰(next RSU 동일 → 전부 선택)을 ILP로 격상
- **기법**: ILP (x_{v,c} 이진 선택 + f_{v,c} 캐시 블록 배분) + LET 제약 + Set Cover NP-hardness 증명 + Greedy 휴리스틱
- **시뮬 재사용**: 8번 코드 90% 재사용, VehicleSelection() 교체만 필요
- **베이스라인**: Proposed-ILP, Proposed-Greedy, Nam2023b, V2V-Base(8번), V2I-Base(7번), Random-K
- **실험**: 시나리오 A (density 1~5, ILP 최적성 분석) + 시나리오 B (density 6~20, Scalability)
- **지표 5개**: Cache Hit Ratio, Content Delivery Success Rate, Precaching Overhead, RSU Load Balance Index, V2V Offload Ratio
- **CSV 규약**: `<scenA/scenB>_<chr/cdsr/pco/rlbi/vor>.csv`

**상태**: 사용자 컨펌 대기. Commander가 컨펌 후 idea_spec.md 작성 의뢰 예정.
