# idea_revalidation_report.md
# AoI-Guaranteed Robust ILP Precaching in CIoV — Round 3 재검증 보고서
# Agent: Idea
# Date: 2026-04-29
# Based on: idea_spec.md (v1.0), references.json (21 items), idea_memory.md, experiment_spec.json

---

## 0. 검증 개요

| 항목 | 내용 |
|------|------|
| 검증 라운드 | Round 3 |
| 검증 대상 | idea_spec.md — AoI-Guaranteed Robust ILP Precaching in CIoV |
| 타겟 저널 | IEEE Internet of Things Journal |
| References | 21개 (전원 자가출판 그룹, 외부 참고문헌 0개) |
| 환각 여부 | 21/21 환각 아님 (Librarian Round 3 확인) |
| DOI 검증 | 0/21 미완 (Librarian Round 3 API 제한) |
| 2025-2026 최신 논문 보강 | 미완 (다음 라운드 예정) |
| ⚠️ 주의 | 노벨티 분석은 현재 21개 references 기반. **Librarian Round 4에서 2025-2026 신규 논문 추가 시 반드시 재평가 필요** |

---

## 1. 축 A: 중복성 검사 (Plagiarism / Concept Overlap)

### 1.1 가장 가까운 선행 연구 Top 5 식별

References 21개 중 본 연구와 가장 직접적으로 겹치는 상위 5편을 아래와 같이 선정.
선정 기준: CIoV/VANET 프리캐싱 도메인, LET 사용, ILP/최적화 사용, AoI 관련성.

| 순위 | 선행연구 키 | 핵심 기법 | AoI 다룸? | Robust 다룸? | ILP 사용? | Predictive cache? | 본 연구와의 결정적 차이점 |
|------|------------|----------|----------|------------|----------|------------------|--------------------------|
| 1 | **Nam2023b** | Set Ranking (deterministic LET 기반 다중 차량 선택) | ✗ | ✗ | ✗ (Set Ranking 조합 최적화) | ✓ (LET 예측 기반) | 본 연구는 Γ-uncertainty set으로 예측 오차를 공식 모델링하고, AoI 변수(a_{v,c})로 freshness를 명시적 추적함. Nam2023b는 결정론적 LET 가정, AoI 없음 → 본 연구의 Γ=0 특수 케이스 |
| 2 | **Nam2025** | Storage-aware ILP (deterministic, V2I precaching, CIoV) | ✗ | ✗ | ✓ (ILP) | ✓ (LET 기반) | 본 연구는 동일 ILP 프레임에 (a) Robust uncertainty 모델과 (b) AoI 결정변수를 추가. Nam2025는 스토리지 관리에 집중하며 예측 불확실성·AoI 보장 없음 → 직접 전임자(direct predecessor) |
| 3 | **Youn2026** | V2V Relay ILP (deterministic LET + outage zone 800m) | ✗ | ✗ | ✓ (ILP) | ✓ (LET 예측 기반) | 본 연구는 Youn2026의 시스템 모델(5×5 RSU, 800m 통신범위)을 상속하고 deterministic LET를 robust worst-case LET로 교체. Youn2026은 outage modeling에 집중, AoI/Robustness 없음 |
| 4 | **Choi2024b** | Mobility-based Multi-hop Content Precaching in CCN/CIoV | ✗ | ✗ | ✗ (휴리스틱) | ✓ (이동성 기반) | 멀티홉 구조 탐색 목적; ILP 정식화 없음, AoI 없음, Robust 없음. 본 연구와 도메인 공유하나 기법/목표 완전 상이 |
| 5 | **Nam2022a** | Cooperative Precaching (intermittently connected, mobility-based) | ✗ | ✗ | ✗ (휴리스틱) | ✓ (이동성 기반) | 단속 연결 환경에서 협력 캐싱. 이동성 예측 사용하지만 uncertainty 미모델링, AoI/ILP 없음. 방향성은 유사하나 기법 레이어가 완전히 다름 |

### 1.2 중복성 판정

**판정: 중복 없음 (No Plagiarism)**

- 가장 가까운 Nam2025(ILP 사용)와도 핵심 차별점이 명확: Robust optimization + AoI formalization 두 축 모두 부재.
- Youn2026(시스템 모델 공유)과도 기법적 독립성 확보: robust counterpart 도출, AoI 결정변수, SLA 정리 신규.
- 21개 references 전부 자가출판 그룹의 논문으로, **외부 관련 연구(Robust IoT caching, AoI vehicular, Bertsimas-Sim ILP 등)가 references.json에 포함되지 않음** — 이는 Librarian Round 4에서 보강 필요한 핵심 갭.
  - ⚠️ 외부 AoI + vehicular/IoT 논문(예: AoI minimization in V2X, 2022-2025 IEEE TCOM/TVT/IoT-J 논문)과의 비교가 현재 불완전함.
  - ⚠️ Bertsimas-Sim Robust ILP 원천 논문 reference 누락 (인용 필수).
  - ⚠️ 2024-2025 AoI-aware vehicular caching 논문 미확인 (중복 가능성 잔존).

---

## 2. 축 B: Contribution 충분성 평가 (C1~C4)

### C1: First Robust+AoI Joint Formulation in CIoV Precaching

**단독 기여 평가 (IoT-J 수준 여부):** ✅ **충분**
- Γ-budgeted uncertainty set을 CIoV precaching ILP에 적용한 첫 사례 — 독창성 확인.
- AoI 결정변수 a_{v,c} + worst-case violation 목적함수 — 기존 Nam2025/Youn2026과 명확한 차별화.
- Bertsimas-Sim robust counterpart로 semi-infinite 제약을 유한 LP로 변환 — 기법적 엄밀성.
- 단, **Big-M 방법(제약 R6)의 M 값 설정이 미명시** — 수치적 불안정성 위험. 보강 권장.
- Γ=0 recoverability 논증이 narratively 강하나 **수식 레벨에서 명시적으로 증명되지 않음** (서술에 의존).

**다른 contribution과의 시너지:** ✅ 명확
- C2(NP-hard → Greedy 필요성)의 동기부여 제공.
- C3(AoI-SLA Theorem)의 정식화 기반.
- C4(libsumo 검증)에서 RILP vs. 베이스라인 핵심 실험 대상.

**권고:** C1은 현재 상태 유지. Big-M 값의 적절한 상한 설정 방법 (예: M = T * Δt + τ_max) 명시 추가 권장.

---

### C2: NP-hardness Proof + Tractable Greedy with (1-1/e) Approximation Bound

**단독 기여 평가:** ⚠️ **조건부 충분 (보강 필요)**

**강점:**
- Robust Weighted Set Cover로의 reduction — 논리적으로 타당한 방향.
- (1-1/e) approximation claim — nominal case에서 submodularity 기반 well-known result 적용.
- 그리디 알고리즘의 시간복잡도 O(|V|·|C|·log(|V|·|C|)) — 실용적.

**약점 1 (수정 필요): NP-hardness Reduction 엄밀성 부족**
- 현재 reduction sketch는 "RILP with AoI=0 reduces to Robust Weighted Set Cover"라 서술.
- 그러나 AoI 제약(R5, R6)과 정수 시간슬롯 변수 f_{v,c}가 추가된 구조에서 reduction의 **방향성(one-way or equivalence)**이 명확히 서술되지 않음.
- "strict generalization, inheriting NP-hardness"라는 표현은 올바르지만, 실제 AoI=0이고 τ_max=∞인 특수 케이스에서 f_{v,c}가 어떻게 처리되는지 수식 수준의 서술 부재.
- **권고**: reduction의 대응 관계 (elements ↔ content chunks, sets ↔ vehicles) 수식으로 형식화, AoI 제약 제거 조건 명시.

**약점 2 (검토 필요): (1-1/e) bound 적용 조건**
- submodularity 주장을 위해 coverage function이 monotone submodular임을 증명해야 함.
- 현재 spec에는 "via submodularity analysis of weighted set cover"라고만 서술 — 구체적 증명 없음.
- Γ>0 robust case에서는 "additive factor O(Γ·ε_max)" 언급만 있고 엄밀한 분석 없음.
- **권고**: Appendix에 submodularity 증명 스케치 추가. Robust case bound를 별도 명제로 분리(e.g., "Greedy achieves ≥ (1-1/e) - O(Γ·ε_max) in the robust case").

**다른 contribution과의 시너지:** ✅ 명확
- C1(RILP NP-hard) → C2(Greedy 필요성 정당화) 연결이 자연스러움.
- C4에서 RILP vs. Greedy 솔브 타임 비교로 실용성 검증 (실험 설계 일관).

---

### C3: AoI-SLA Guarantee Theorem

**단독 기여 평가:** ✅ **충분 (IoT-J에서 가장 차별화되는 contribution)**
- Theorem 자체는 직관적이고 정확한 방향: Γ ≤ Γ* 조건 하에 worst-case AoI ≤ τ_max 보장.
- Proof outline의 4단계(Feasibility → Robust constraint → Delivery completion → AoI bound)가 논리적으로 연결됨.
- Closed-form Γ* (단일 RSU/단일 콘텐츠 케이스) 제공 — IoT-J 독자들이 이해하기 쉬운 분석적 베이스라인.
- Corollary 1(단조성) + Corollary 2(Γ=0 복원)가 Theorem을 보강.

**보완 사항:**
- **Γ* closed-form 증명의 completeness**: "Γ* = (τ_max − f_min) / Δ_max" 공식이 단일 RSU 케이스에서 어떻게 도출되는지 증명 단계가 spec에 미기재. Paper 작성 시 반드시 포함.
- **Multi-RSU 케이스 Γ***: "수치 분석으로 대체"라고 명시됨 — IoT-J reviewer는 이에 대해 analytical 접근 부재를 지적할 수 있음. 해결책: "Γ*의 lower/upper bound를 multi-RSU 케이스에서 유도" 또는 convex relaxation 기반 bound 추가 권장.
- **Theorem의 feasibility assumption**: Γ* 정의가 "RILP가 AoI ≤ τ_max 조건 하에 feasible한 최대 Γ"인데, 이 feasibility가 항상 존재한다는 보장 (즉, Γ*>0) 조건이 명시 필요.

**다른 contribution과의 시너지:** ✅ 매우 강함
- C1(RILP 정식화) 없이 C3 Theorem 불가 → 상호 의존성 명확.
- C4(libsumo Scenario C/D/E)에서 Theorem 수치 검증 → 이론-실험 연결.

---

### C4: Comprehensive libsumo Validation

**단독 기여 평가:** ⚠️ **단독으로는 contribution 아님 (검증 수단)**
- C4는 C1~C3를 empirically 뒷받침하는 검증 플랫폼 — 독립적 novelty claim 없음.
- 그러나 IoT-J에서는 시스템 논문의 필수 요소이므로 C4의 충분성이 전체 논문 수용 여부에 영향.
- 5×5 RSU, density {1,5,10,20}, prediction error {0%,10%,20%,30%}, 10회 반복 → 적절한 규모.
- 베이스라인 6개(RILP, Greedy, Nam2023b, Nam2025, Youn2026, Random-K) → 공정하고 충분.
- 5개 지표(AoI violation, CHR, CDSR, PCO, RLBI) → 다차원 평가 적절.

**보완 사항:**
- **베이스라인 개수**: idea_memory에서 "베이스라인 7개"라 기록되었으나 spec/experiment_spec에서는 6개. 일관성 확보 필요 (Minor inconsistency).
- **experiment_spec.json과의 일관성**: experiment_spec.json의 global_sumo_parameters와 idea_spec.md의 Appendix A가 대부분 일치(800m, 5×5, density, Zipf s=0.8, τ_max=5). ✅ 일관.
- **solver 선택**: Gurobi/CBC — 단, Gurobi는 상업 라이센스 필요. 논문에서 solver 선택 및 설정(time limit, gap tolerance) 명시 필요.
- **C4에서 C3 Theorem 수치 검증이 가장 중요한 figure**: Γ vs. AoI violation rate 곡선 (Scenario E) — 이것이 논문의 핵심 실험 figure가 되어야 함.

**다른 contribution과의 시너지:** ✅ 전체 C1~C3 지지
- C1 → Scenario A/B에서 RILP 정확해 우위 검증.
- C2 → Scenario B에서 Greedy ≥90% 확인.
- C3 → Scenario C/D/E에서 Theorem 단조성·복원 수치 검증.

---

## 3. 축 C: 가정·모델 타당성

### 3.1 시스템 모델 (CIoV, V2V/V2I, RSU coverage gap)

| 가정/모델 요소 | 내용 | 타당성 평가 |
|--------------|------|-----------|
| 5×5 RSU 격자, 800m 통신범위 | Youn2026에서 직접 상속 | ✅ WAVE/802.11p 표준에서 현실적 |
| Outage zone 800m | comm_range와 동일 | ⚠️ outage zone = comm_range로 설정하는 것은 worst-case 가정으로 이해 가능하나, 일반적으로 outage zone < comm_range. 정의 명확화 필요 |
| Vehicle density ρ ∈ {1,5,10,20} | 셀당 차량 수 | ✅ 실제 도시 도로 밀도 범위 적절 |
| libsumo 기반 차량 궤적 | 실제 도로 위상 사용 | ✅ SUMO는 vehicular network 시뮬레이션 de facto 표준 |
| Content catalog 100개, Zipf s=0.8 | | ✅ IoT/vehicular content caching 표준 파라미터 |
| Cache capacity 10 items | 동질 차량 가정 | ✅ 단순화 합리적; 이기종(heterogeneous) 차량은 future work로 명시 권장 |

### 3.2 수학적 모델링 일관성

| 모델 요소 | 평가 |
|----------|------|
| **AoI 정의** a_{v,c} = t_rx - t_gen | ✅ 표준 AoI 정의와 일치 (Costa et al. 2016 정의 준수). 단, "AoI at reception" 시점 — 실제 IoT-J 문헌에서는 AoI를 시간-평균으로 측정하는 경우도 있음. 본 연구의 "AoI at delivery time" 정의를 논문에서 명확히 구분할 것 |
| **Γ-budgeted uncertainty set** 𝒰(Γ) | ✅ Bertsimas-Sim (2004) 표준 정의와 일치. 유한 LP 변환(dual variables θ, φ) 타당 |
| **Bertsimas-Sim dual counterpart** | ✅ [R1]의 robust counterpart 변환이 정확 (θ_v, φ_v dual var, φ_v ≥ Δ_v·θ_v) |
| **Big-M constraint [R6]** | ⚠️ M 값 미명시. M이 너무 크면 LP relaxation이 느슨해져 ILP solve 시간 증가. 권장: M = T_max * Δt (scheduling horizon). 명시 필요 |
| **AoI-SLA constraint 방향** | ✅ R6: a_{v,c} ≤ τ_max + M(1-x_{v,c}) — x=1이면 a ≤ τ_max, x=0이면 비활성. 논리적으로 올바름 |
| **Violation slack z_{v,c}** [R7] | ✅ soft violation 추적 변수로 목적함수와 일관 |
| **정수 시간슬롯 f_{v,c}** | ⚠️ f_{v,c} ∈ {0,1,...,T}이지만 [R1]에서 f_{v,c} ≤ (LET_v - δ_v) * x_{v,c}에서 LET_v - δ_v가 실수일 수 있음 → floor 연산 또는 연속 근사 명시 필요 |
| **V2V outage constraint [R2]** | ⚠️ f_{v,c} ≥ outage_end(v) * x_{v,c}에서 outage_end(v) 결정 방식 미명시. 어떻게 계산되는지(통신 불가 구간 끝나는 시점) 시스템 모델에 추가 필요 |

### 3.3 가정 사항의 합리성

| 가정 | 합리성 |
|------|--------|
| 이동성 예측 오차 10~30% | ✅ GPS noise + lane change 통계적 측정값으로 인용 가능. 실제 SUMO 기반 실험에서 재현 가능 |
| Zipf 콘텐츠 인기도 (s=0.8) | ✅ IoT/vehicular caching 문헌에서 표준값 |
| τ_max = 5 time slots = 5초 | ✅ safety-critical ITS 콘텐츠(HD map 업데이트, 사고 알림 등)에 합리적 |
| 동질 차량 (CAP_v = 10 items) | ⚠️ 실제 차량은 스토리지 이기종. 제한사항으로 명시 필요. Nam2025의 이기종 스토리지 모델과 비교하여 단순화임을 인정할 것 |
| Γ default = 2.0 | ✅ Bertsimas-Sim에서 |V|^0.5 정도가 일반적 heuristic. density=5일 때 √5 ≈ 2.2이므로 합리적 |
| V2I bandwidth 20Mbps, V2V 10Mbps | ✅ WAVE/802.11p/5G-V2X 표준 범위 내 |

---

## 4. 축 D: 제안 알고리즘의 실현가능성

### 4.1 experiment_spec.json과의 일관성

| idea_spec.md 항목 | experiment_spec.json 항목 | 일치? |
|------------------|--------------------------|------|
| 5×5 RSU, 800m | rsu_grid=5x5, comm_range_m=800 | ✅ |
| density {1,5,10,20} | density_range [1,2,3,4,5] (Scenario A), [1,5,10,20] (Scenario B) | ✅ (A는 소규모) |
| prediction error {0%,10%,20%,30%} | prediction_error_pct [0,10,20,30] | ✅ |
| τ_max = 5 slots | aoi_threshold_tau_max_default_slots=5 | ✅ |
| Γ values [0,1,2,3] | gamma_values [0.0,1.0,2.0,3.0] | ✅ |
| Zipf s=0.8 | content_popularity_distribution: Zipf(s=0.8) | ✅ |
| 10 runs | simulation_runs_per_config=10 | ✅ |
| 베이스라인 6개 | RILP, Greedy, Nam2023b, Nam2025, Youn2026, Random-K | ✅ |
| 5개 지표 | AoI violation, CHR, CDSR, PCO, RLBI | ✅ |

**일관성 판정: 전반적으로 일치.** ⚠️ idea_memory에 "베이스라인 7개"로 기록된 내용은 spec에서 6개로 통일됨 → idea_memory 수정 또는 7번째 베이스라인 명시 필요 (minor).

### 4.2 NP-hard ILP의 실용성

**소규모(density 1~5):** RILP 정확해 (Scenario A)
- 차량 수 ≤ 25, 콘텐츠 100개 → 변수 수 |V|×|C| ≤ 2,500 binary + integer
- Gurobi/CBC로 수 분 내 해결 가능 ✅

**대규모(density 6~20):** RILP는 시간 초과 가능성
- density 20: 차량 수 ≤ 500 → binary 변수 50,000개 이상
- **Greedy Heuristic으로 대체 필수** — 이미 C2에서 동기부여됨 ✅
- Bertsimas-Sim counterpart 적용 후 LP relaxation 가능성도 언급하면 좋음

**알고리즘 복잡도:**
- RILP: NP-hard (C2 증명) → small instance exact, large instance greedy
- Greedy: O(|V|×|C|×log(|V|×|C|)) = 실용적 ✅
- Robust counterpart 변환: 원래 ILP 대비 2|V|개 dual variable 추가 → 선형 증가 ✅

### 4.3 베이스라인 공정성

| 베이스라인 | 공정성 체크 |
|-----------|-----------|
| Proposed-RILP | 제안 방법 (정확해) ✅ |
| Proposed-Greedy | 제안 방법 (휴리스틱) ✅ |
| Nam2023b | 동일 시뮬레이터, 동일 환경에서 deterministic LET 방식 ✅ |
| Nam2025 | ILP 기반 비교 가능 ✅ (스토리지 제약 부분 동치화 필요) |
| Youn2026 | 동일 통신범위/outage 모델 ✅ (시스템 모델 공유로 가장 공정) |
| Random-K | 하한 베이스라인 ✅ |
| ⚠️ 누락 베이스라인 | AoI-only (non-robust) 방법이 없음. AoI-aware deterministic 베이스라인 추가 권장 (예: "Greedy-AoI-noRobust" 변형 또는 기존 AoI-aware vehicular caching 논문 baseline) |

---

## 5. 판정

### ⚡ 최종 판정: **CONDITIONAL PASS**

**판정 근거:**

1. **핵심 신규성 확인**: Robust ILP (Γ-uncertainty) + AoI worst-case guarantee + CIoV precaching 3중 조합은 현재 21개 references 어디에도 존재하지 않음. 가장 가까운 Nam2025/Youn2026과의 차별성이 명확하고 체계적으로 논증됨.

2. **수정이 필요한 작은 결함들**: 치명적 결함은 없으나, 아래 5개 항목이 논문 작성 단계에서 문제가 될 수 있음 (지금 수정하는 것이 효율적):
   - (a) Big-M 값 명시화 (R6 제약)
   - (b) NP-hardness reduction의 수식 수준 형식화 (AoI=0, τ_max=∞ 특수 케이스 명시)
   - (c) outage_end(v) 계산 방식 시스템 모델에 추가
   - (d) f_{v,c} 정수 반올림 처리 명시
   - (e) Bertsimas-Sim 원천 논문 reference 필수 추가

3. **외부 references 미비**: 현재 references.json 21개 전부 자가출판 — Bertsimas & Sim (2004), AoI 원천 논문 (e.g., Kaul et al. 2012), 2024-2025 AoI vehicular caching 외부 논문들이 반드시 추가되어야 IEEE IoT-J 심사 통과 가능. **Librarian Round 4에서 보강 필수.**

**Experimenter Stage 2 진행 가능 여부:** ✅ **진행 가능** (소수정 병렬 수행 가능)
- experiment_spec.json과 idea_spec.md의 일관성이 확인됨.
- C4 검증 실험 설계는 충분히 구체적이며 실행 가능한 수준.
- 위 수정 사항들은 Writer 단계 이전까지 반영하면 충분.

---

## 6. 수정 제안 (CONDITIONAL PASS 사유별 대응)

| # | 수정 항목 | 위치 | 우선순위 | 구체적 수정 내용 |
|---|---------|------|---------|----------------|
| M1 | Big-M 값 명시 | Section 4.2 [R6] | 높음 | "M = (T_max + τ_max) * Δt로 설정하며, T_max는 스케줄링 윈도우 슬롯 수" 추가 |
| M2 | NP-hardness reduction 형식화 | Section 4.3 | 높음 | AoI=0 (τ_max→∞, f_{v,c}=0 허용) 특수 케이스에서 RILP ↔ RWSC 동치 관계를 수식으로 명시 |
| M3 | outage_end(v) 정의 | Section 4.1 System Model | 중간 | "outage_end(v) = 차량 v가 현재 outage zone을 벗어나는 예측 시간 슬롯" 정의 추가 |
| M4 | f_{v,c} 정수화 처리 | Section 4.2 [R1] | 중간 | "LET_v − δ_v는 실수이므로, [R1]에서 ⌊LET_v − δ_v⌋ (floor) 적용" 명시 |
| M5 | 외부 references 추가 요청 | Appendix B / 전체 | 높음 | Librarian Round 4에 다음 추가 요청: Bertsimas & Sim (2004), Kaul et al. AoI (2012), 2024-2025 AoI vehicular/IoT papers |
| M6 | AoI-only deterministic 베이스라인 | Section 5 / Appendix A.2 | 낮음 | "Greedy-AoI-noRobust" 7번째 베이스라인 추가 검토 (Γ=0으로 고정한 제안 Greedy 변형) |

---

## 7. Experimenter 핸드오프 권고

### 즉시 진행 가능 항목 (Experimenter Stage 2)
1. **libsumo Scenario A/B 실행**: density 1~5 (RILP exact) + density 1~20 (Greedy 비교)
2. **Scenario C**: prediction error sweep (0%,10%,20%,30%) — AoI violation rate vs. error
3. **Scenario D**: τ_max sweep — AoI violation rate 민감도
4. **Scenario E**: Γ sweep — C3 Theorem 단조성 검증 (가장 중요한 figure)

### Experimenter가 확인해야 할 사항
- Gurobi 라이센스 가용 여부 (없으면 CBC/PuLP 대체)
- libsumo Python API에서 outage_end(v) 계산 구현 방식 확인
- Big-M 값 M = (20 + 5) * 1 = 25로 default 설정 권장

### 병렬 처리 권고
- Experimenter Stage 2 실행과 동시에:
  - Librarian Round 4: 외부 references 보강 (Bertsimas-Sim, AoI origin, 2024-2025 vehicular AoI)
  - Idea agent: M1~M4 수정 사항 idea_spec.md에 반영

---

## ⚠️ 핵심 주의사항

> **Librarian Round 4에서 2025-2026 신규 논문이 추가되면 노벨티 재평가 필요**
>
> 현재 노벨티 분석은 21개 자가출판 references에만 기반. 외부 관련 연구
> (AoI vehicular caching, Robust IoT scheduling, Bertsimas-Sim ILP applications in V2X)를
> 검토하지 않은 상태로, 2024-2025 IEEE TCOM/TVT/IoT-J 논문 중 본 연구와 유사한
> 선행 연구가 존재할 가능성이 배제되지 않음.
> Librarian Round 4 완료 후 축 A(중복성 검사) 재실행 필수.

---

*Report Version: 1.0*
*Generated by: Idea Agent (Round 3 Revalidation)*
*Date: 2026-04-29*
*Status: CONDITIONAL PASS — Experimenter Stage 2 진행 가능 (소수정 병렬 수행)*
