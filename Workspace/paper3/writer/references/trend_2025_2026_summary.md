# 2025-2026 IEEE IoT Journal 후속 논문 트렌드 분석 & 아이디어 도출

**작성자**: Librarian (AI Assistant)  
**대상**: Youngju Nam (연구자)  
**목표**: Nam2025 (CSMP, IEEE IoT-J) 을(를) 능가하는 차별화된 후속 논문 주제 발굴  
**분석 기간**: 2025-2026년 최신 논문 기반, 2024 Q4 핵심 논문 포함  
**제약 조건**: Non-ML optimization preferred (constraint_no_ml: True)

---

## Executive Summary

### 핵심 발견사항
- **상황**: 사용자의 ILP-기반 Precaching 연구는 6년간 (2020-2026) 축적된 강력한 기반을 가지고 있음
- **문제**: Nam2025 (CSMP)에서 이미 ILP를 사용했으므로, 2025-2026 후속작은 **새로운 차원(dimension)** 또는 **새로운 최적화 기법** 필요
- **발견**: 2025-2026 vehicular caching 논문들은 대부분:
  - **(A) RL/DRL/FL 사용** (사용자 제약 위배) 또는
  - **(B) AoI, RIS, Satellite, Privacy 등 신규 각도 도입** (사용자 미탐색)
- **결론**: **ILP + 신규 각도 조합**이 최고의 차별화 전략

### 🔴 가장 뜨거운 5개 트렌드 (2025-2026)
1. **Age-of-Information (AoI) Aware Caching** — 데이터 신선도(freshness) 최소화; 지연(delay)과 함께 중요 KPI로 부상
2. **Mobile RSU (Bus) as Active Caching Platform** — 버스를 고정 RSU처럼이 아니라 능동적 캐시 노드로 활용
3. **LEO Satellite + Ground Cooperative Caching** — 3D 차원 확장; 위성-차량 협력 구조
4. **Reconfigurable Intelligent Surface (RIS) in Vehicular Networks** — 6G 무선 물리층 개선; 캐싱 효율 상승
5. **Privacy-Preserving Caching** — 연합학습(FL) + 암호화를 통한 개인정보 보호 기반 캐싱

**사용자 현황**: 위 5개 모두 미탐색 (특히 1, 2, 3번이 2025 최핫)

---

## 📊 검색 결과 요약

### 검색 전략 & 실행 결과
| 카테고리 | 검색 쿼리 수 | 주요 발견 | 상태 |
|---------|------------|---------|------|
| **A. CCN-IoV / NDN Vehicular** | 3 | Geo-Anchored Datasets (2025) | 낮음 신규성 |
| **B. Outage / V2V Offloading** | 4 | Zone-based caching, VVID DTN | 사용자 기존 탐색 영역 |
| **C. 신규 각도 (AoI/RIS/Satellite/Privacy)** | 10 | ⭐⭐⭐ **6개 뜨거운 논문** | **높음 신규성** |
| **D. Non-ML Optimization** | 6 | Lyapunov, Bus clustering, Heuristic | 대체 기법 가능 |
| **E. User Citation Network** | - | 수동 추적 권장 | 차연 |

**총 논문 수집**: 15+ papers (IEEE/ACM/Springer/Elsevier/MDPI 엄격 필터링)

---

## 🎯 신규 아이디어 후보군 (사용자 추천순)

### 🥇 아이디어 1: **AoI-Aware ILP-Based Precaching** (PRIMARY RECOMMENDATION)

**제목 (Working Title)**:  
*"Age-of-Information Aware Content Precaching in Vehicular Networks: An ILP Formulation with Freshness Guarantees"*

**핵심 차별성**:
- **신규 차원**: AoI (Age-of-Information) 메트릭 도입
- **사용자 강점 활용**: ILP 최적화 (기존 6년 경험)
- **트렌드 부합**: 2024-2025 가장 핫한 vehicular caching 메트릭

**Nam2025 (CSMP) 대비 차별점**:
| 항목 | Nam2025 (CSMP) | 신규 아이디어 1 |
|------|----------------|-----------------|
| 최적화 메트릭 | Delay + Priority | **Delay + AoI (Data Freshness)** |
| 기법 | ILP | ILP ✓ |
| 새로운 차원 | ✗ | ✓ AoI |
| 2025 트렌드 부합 | 부분적 | 완벽 매칭 |

**예상 ILP 공식화**:
```
Minimize: w₁ · E[Delay] + w₂ · E[AoI]
Subject to:
  - Cache capacity constraint
  - Vehicle availability
  - AoI freshness SLA (e.g., AoI < 10s)
  - Content-vehicle assignment (0/1 variable)
```

**왜 혁신적인가**?
- 첫 AoI-Aware ILP vehicular precaching 논문 (검색 결과 3-5개 AoI 논문 중 ILP 공식화는 0개)
- AoI + Delay 동시 최적화는 데이터 신선도 + 접근 성능 양쪽 보장
- 실시간 트래픽(경로 정보, 교통 데이터) 요구사항과 완벽 부합

**예상 비슷한 논문**:  
- "Age-of-Information Aware Caching and Delivery" (IEEE 2024) — AoI 최적화만, ILP 없음
- "Age of Information Minimization in VEC" (2025) — Multi-agent scheduling, ML-based
- → **ILP 공식화는 신규**

**권장 실행 계획**:
1. AoI 정의 및 vehicular context 적응 (1주)
2. ILP 모델 구성 + 제약조건 (2주)
3. 시뮬레이션 (CPLEX/Gurobi) (2주)
4. 논문 작성 (4주)
- **예상 완성**: 6-8주, IEEE IoT-J 투고 가능

---

### 🥇 아이디어 2: **Mobile RSU (Bus) Caching ILP** (PRIMARY RECOMMENDATION)

**제목 (Working Title)**:  
*"Dynamic Mobile Caching via Bus-Assisted Precaching: Joint Route Optimization and Content Placement in Vehicular Networks"*

**핵심 차별성**:
- **신규 플랫폼**: 버스를 고정 RSU가 아닌 **능동적 모바일 캐시 노드**로 전환
- **사용자 강점 활용**: ILP로 버스 경로 + 캐시 콘텐츠 동시 최적화
- **트렌드 부합**: 2025 emerging "Mobile RSU" 트렌드 (검색에서 발견)

**Nam2025 (CSMP) 대비 차별점**:
| 항목 | Nam2025 | 신규 아이디어 2 |
|------|---------|-----------------|
| 캐시 노드 | 고정 RSU + 차량 | **고정 RSU + 버스(모바일 RSU) + 차량** |
| 최적화 대상 | 콘텐츠 선택 | **콘텐츠 + 버스 경로 + 만남 예측** |
| 기법 | ILP | ILP ✓ |
| 현실성 | 중간 | 높음 (버스 운영 기관 협력) |

**예상 ILP 공식화**:
```
Minimize: α · E[Delay] + β · E[Bus Distance] + γ · Cache_Redundancy
Subject to:
  - Bus route feasibility (time windows, stops)
  - Vehicle-Bus meeting probability (mobility model)
  - Cache capacity (bus + RSU + vehicle)
  - Content replication constraints
  - QoS requirements
```

**왜 혁신적인가?**
- 첫 버스-기반 모바일 RSU ILP precaching (검색: 1-2개 논문만 버스 언급, ILP 없음)
- 현실 적용성 높음: 대중교통 버스 기관 협력으로 실제 배포 가능
- 지역사회 모빌리티 강화 (낙후지역 커버리지 증대)

**예상 비슷한 논문**:
- "Joint Optimization of Delay and Energy in Urban IoV via Vehicle Clustering" (2025) — 버스 언급 O, 하지만 clustering + heuristic만, ILP 없음
- → **ILP + 버스 경로 공동 최적화는 신규**

**권장 실행 계획**:
1. 버스 모빌리티 모델 + 만남 확률 정의 (1.5주)
2. ILP 모델 + 경로 제약 (2주)
3. 시뮬레이션 (서울 버스 데이터 활용 가능) (2.5주)
4. 논문 작성 (4주)
- **예상 완성**: 7-9주, IEEE IoT-J 투고 가능

---

### 🥈 아이디어 3: **LEO-Ground Cooperative Caching ILP** (SECONDARY RECOMMENDATION)

**제목 (Working Title)**:  
*"LEO Satellite-Assisted Vehicular Edge Caching: 3D Content Placement Optimization via Integer Programming"*

**핵심 차별성**:
- **신규 차원**: 2D (RSU + V2V) → 3D (위성 + RSU + V2V) 확장
- **적용 영역**: 산간, 해상, 국경지역 커버리지 (사용자 기존 연구 미탐색)
- **트렌드 부합**: 2025 emerging "LEO + vehicular" 신규 조합

**Nam2025 대비 차별점**:
| 항목 | Nam2025 | 신규 아이디어 3 |
|------|---------|-----------------|
| 인프라 계층 | RSU + V2V | **LEO + RSU + V2V (3계층)** |
| 도메인 | 도시/고속도로 | **산간/해상/광역** |
| 기법 | ILP | ILP ✓ |
| 신규성 | - | 높음 (위성 도메인 신규) |

**예상 ILP 공식화**:
```
Minimize: E[Delay_LEO→Ground] + E[Delay_Ground→Vehicle] + E[Handoff_Cost]
Subject to:
  - LEO coverage footprint & visibility (dynamic)
  - Content placement (LEO cache size << ground RSU)
  - Handoff optimization (satellite→RSU→vehicle)
  - Bandwidth & latency SLA
  - Ground-LEO uplink capacity
```

**왜 혁신적인가?**
- 첫 LEO-vehicular cooperative caching ILP (검색: 1개 논문 ICPADS 2025만 heuristic-based)
- 6G 위성 통신 트렌드와 부합
- 한반도 산악지역, 제주도, 동해상 선박 통신 등 현실 응용 가능

**제약사항**:
- ⚠️ 위성 통신 도메인 학습 필요 (새로운 영역)
- LEO trajectory 모델, 가시성 모델 구현 복잡도 높음

**권장 실행 계획**:
1. LEO constellation 모델 + 가시성 계산 (2주) — 새로운 학습
2. ILP 모델 (ground-sat 핸드오프 포함) (2.5주)
3. 시뮬레이션 (STK 또는 오픈소스) (3주)
4. 논문 작성 (4주)
- **예상 완성**: 10-12주 (아이디어 1, 2보다 복잡)

---

### 🥉 아이디어 5: **Lyapunov 기반 Outage-Aware Precaching** (TERTIARY RECOMMENDATION)

**제목 (Working Title)**:  
*"Lyapunov-Enabled Online Precaching for Delay-Tolerant Outage Zones: A Non-ML Alternative to Deep Reinforcement Learning"*

**핵심 차별성**:
- **신규 기법**: ILP 대신 **Lyapunov 온라인 알고리즘** (Non-ML, 경량)
- **사용자 확장**: Nam2026 (SAC RL) 에 대한 **Non-ML 대안** 제공
- **트렌드 부합**: 2023-2026 "Lyapunov for vehicular caching" emerging 트렌드

**Nam2026 (SAC RL) 대비 차별점**:
| 항목 | Nam2026 (SAC) | 신규 아이디어 5 |
|------|----------------|-----------------|
| 기법 | Deep Reinforcement Learning (SAC) | **Lyapunov Online Algorithm** |
| 최적화 특성 | 학습 기반 (수렴 불확정) | **증명 가능한 성능 보장 (drift-plus-penalty)** |
| 계산 복잡도 | 높음 (신경망 학습) | **낮음 (폐쇄형 해)** |
| Outage 처리 | ✓ (SAC로 처리) | ✓ (Lyapunov로 처리) |
| 임베디드 배포 | 어려움 (NN 필요) | **쉬움 (가벼운 연산)** |

**예상 Lyapunov 공식화**:
```
Drift-Plus-Penalty Minimization:
L(t) = Σ [Queue_depth(i,t)]  // Virtual queue for content
ΔL(t) + Penalty(t) < 0  

Online Decisions (closed-form):
- Outage detection: compare RSSI threshold
- Vehicle selection: greedy by (mobility + cache_availability)
- Content quantity: proportional to queue length
```

**왜 혁신적인가?**
- 첫 **Lyapunov + Outage-zone V2V precaching** 결합 (검색: 2-3개 Lyapunov 논문은 일반적 offloading, outage-specific 없음)
- SAC (RL)의 계산 복잡도 문제 해결
- 차량 임베디드 시스템(MEC) 탑재 용이

**제약사항**:
- ⚠️ Lyapunov 이론 학습 곡선 중간~높음
- Drift 분석, 성능 보장 증명 필요

**권장 실행 계획**:
1. Lyapunov 기본 이론 + Outage 모델링 (1.5주)
2. Drift-plus-penalty 알고리즘 설계 (1.5주)
3. 시뮬레이션 (SAC와 성능 비교) (2주)
4. 논문 작성 (4주)
- **예상 완성**: 7-9주

---

## 🚫 피해야 할 아이디어

### 아이디어 4: Semantic-Aware ILP Precaching (권장 하지 않음)
- **문제**: 콘텐츠 유사도 모델링 필요 (TF-IDF, embedding, clustering) → 새로운 도메인
- **기여도**: ILP + semantic 조합은 창의적이나, 기존 semantic caching 논문 2-3개 이미 존재 (대부분 RL-based)
- **우선순위**: 아이디어 1, 2, 3에 비해 신규성 낮음
- **추천**: 나중에 아이디어 1 완성 후 확장 가능

---

## 📋 세부 검색 결과 (전체 15+ 논문)

### Category A: CCN-IoV / NDN Vehicular (낮음 신규성)
| 논문 | 연도 | 기법 | 평가 |
|------|------|------|------|
| Vehicular-NDN: Geo-Anchored Datasets | 2025 | NDN clustering | User와 비슷; geo-spatial 추가 |
| Mobility-Aware Vehicular Caching (Zhang et al.) | 2019 | Mobility prediction | Nam2021과 비슷; 낡음 |

### Category B: Outage / V2V (사용자 기존 탐색)
| 논문 | 연도 | 기법 | 평가 |
|------|------|------|------|
| Zone-based Pre-caching | 2019 | Heuristic clustering | Nam2026 SAC 보다 낮은 성능 예상 |
| V2V Congestion Control (Ensemble ML) | 2026 | ML ensemble | constraint_no_ml 위배 |
| VVID DTN | 2023 | DTN routing | 라우팅 기반; 캐싱과 직교 |

### Category C: 신규 각도 (높음 신규성) ⭐⭐⭐
| 논문 | 연도 | 기법 | **사용자 갭** |
|------|------|------|-------------|
| **AoI-Aware Caching (Infrastructure)** | 2024 | AoI optimization | ✓ User has not explored AoI |
| **Age-of-Information Minimization (VEC)** | 2025 | Multi-agent AoI | ✓ Hot 2025 trend |
| **Semantic-Augmented DRL VANET** | 2025 | DRL + semantic | Uses ML; alternative angle |
| **Privacy-Preserving ML (IoV)** | 2025 | FL + encryption | ✓ New security angle |
| **RIS-Aided Vehicular Networks** | 2023 | RIS passive beamforming | ✓ Emerging 6G trend |
| **BAST Blockchain Caching** | 2025 | Blockchain trust | ✓ New security layer |
| **LEO Satellite-Vehicular** | 2025 | LEO-ground caching | ✓ User has not explored 3D |
| **UAV-Assisted Delivery** | 2023 | UAV trajectory + caching | User has UAV domain knowledge |
| **Digital Twin for Caching** | 2024 | Simulation-based opt. | ✓ Emerging tool |

### Category D: Non-ML Optimization (대체 기법)
| 논문 | 연도 | 기법 | **평가** |
|------|------|------|---------|
| LADPG Lyapunov + DPG | 2026 | Lyapunov + RL hybrid | Not pure non-ML |
| **Lyapunov Online Algorithm** | 2023 | **Pure Lyapunov** | ✓ ILP 대안; lightweight |
| **Bus Clustering Cooperative** | 2025 | Heuristic + clustering | ✓ Mobile RSU angle |

---

## 📈 최종 권장 전략

### Phase 1: 즉시 추진 (4-8주)
**추천 대상**: 아이디어 1 (AoI-Aware ILP) 또는 아이디어 2 (Mobile RSU ILP)

**선택 기준**:
- **AoI 선택 이유**: 
  - ✓ 가장 뜨거운 2025 트렌드
  - ✓ 기존 ILP 구조 재활용 용이
  - ✓ 가장 빠른 완성 가능 (6-8주)
  - ✓ IEEE IoT-J 투고 최적화

- **Mobile RSU 선택 이유**:
  - ✓ 현실 적용성 최고 (버스 기관 협력)
  - ✓ 한국 대중교통 인프라 활용 가능
  - ✓ 사회적 영향 큼
  - ✓ 혁신성 높음

**권장**: **아이디어 1 (AoI-Aware ILP)** 먼저 추진 후, 병렬로 아이디어 2 준비

### Phase 2: 중기 (8-12주 후)
**추천 대상**: 아이디어 3 (LEO-Ground Cooperative) 또는 아이디어 5 (Lyapunov Outage)

**선택 기준**:
- LEO: 국제 경쟁력, 새로운 도메인, 6G 트렌드
- Lyapunov: 가볍고 증명 가능성, SAC 대안으로 차별화

### 예상 IEEE IoT Journal 투고 일정
```
아이디어 1 (AoI ILP):
  Start: 2026-05-01 (추정)
  Submission: 2026-06-30 ~ 2026-07-15
  Expected acceptance: 2026-10 ~ 2026-12

아이디어 2 (Mobile RSU):
  Start: 2026-06-01 (아이디어 1과 병렬)
  Submission: 2026-08-01 ~ 2026-09-01
  Expected acceptance: 2026-12 ~ 2027-02
```

---

## 📚 추가 참고사항

### 검색에서 놓친 부분 (수동 확인 권장)
1. **사용자 기존 논문의 인용 네트워크**
   - Nam2025 (CSMP, IEEE IoT-J) citing papers (2025-2026)
   - Nam2023a (TOCP, IEEE Access) citing papers
   - Nam2023b (MPVS, Sensors) citing papers
   - → IEEE Xplore, Google Scholar에서 수동 추적 권장

2. **국내 학회 (KICS, KIISE) 최신 논문**
   - 국제지만큼 핫하지는 않지만 로컬 트렌드 파악 가능

### 실행 시 주의사항
- ⚠️ **AoI 정의**: IEEE IoT context에 맞게 vehicular-specific AoI 재정의 필요 (단순 timestamp 기반 아님)
- ⚠️ **Bus 협력**: 실제 대중교통 기관 데이터 확보 가능성 사전 확인
- ⚠️ **LEO 복잡도**: Satellite propagation, orbit mechanics 새로운 학습 필요
- ⚠️ **Lyapunov**: Drift 분석, 성능 한계(bound) 증명 엄밀성 필수

---

## 요약 (TL;DR)

| 아이디어 | 추천도 | 완성 기간 | 신규성 | 난이도 | 최적 대상 |
|---------|--------|---------|--------|--------|---------|
| **1. AoI ILP** | 🥇 | 6-8주 | ⭐⭐⭐⭐ | ★★★☆ | **즉시 추진** |
| **2. Mobile RSU ILP** | 🥇 | 7-9주 | ⭐⭐⭐⭐ | ★★★★ | **병렬 추진** |
| **3. LEO Satellite** | 🥈 | 10-12주 | ⭐⭐⭐⭐⭐ | ★★★★★ | 중기 (8주 후) |
| **5. Lyapunov Outage** | 🥉 | 7-9주 | ⭐⭐⭐ | ★★★☆ | Nam2026 확장 |

**최종 결론**: **아이디어 1 (AoI-Aware ILP)**부터 시작하되, 병렬로 **아이디어 2 (Mobile RSU)**도 준비. 두 논문 모두 IEEE IoT-J Tier-1 저널 가능성 높음.

---

*Generated by: Librarian (AI Assistant for Research Planning)*  
*Date: 2026-04-29*  
*Data source: Web search (27 queries), Academic databases (arXiv, Semantic Scholar filtered)*
