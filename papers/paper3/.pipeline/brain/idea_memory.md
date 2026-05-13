# Idea Memory

(첫 작업 수행 시 자동으로 채워집니다)


## [2026-04-28] 사용자(Youngju Nam) 연구 컨텍스트 분석

### 한 줄 정의
"이동 차량 환경(VANET → CCN → CIoV)에서 콘텐츠 프리캐싱 최적화를 핵심 정체성으로 삼고,
이동성 예측·RSU 협력·강화학습(SAC)으로 6년간 진화시켜온 차량 네트워킹 알고리즘 연구자"

### 6년간(2020-2026) 연구 진화 — 5 Phase
- Phase 1 (2020-2021): VANET 입문, 데이터·콘텐츠 전달 프로토콜 (3편). Nam2021에서 "이동성(속도) 예측 → 사전 캐싱" 프레임 정립.
- Phase 2 (2022): 폭발적 확장 (7편 — 연구 피크). Precaching·Vehicular Cloud·LoRa 3개 주제 동시 탐색. FA 3편으로 독립 연구자 성장.
- Phase 3 (2023): 선택과 집중 — Precaching 심화 (3편). Nam2023a로 첫 IEEE Access tier1 FA 진출.
- Phase 4 (2024): 통합 준비기 & UAV 확장 (4편, FA 없음). 2025 IEEE IoT Journal 준비기.
- Phase 5 (2025-2026): CIoV 통합 + 강화학습 도입 (4편). Nam2025 (IEEE IoT Journal), Nam2026 (SAC 기반 Precaching).

### 주제 클러스터 (6개)
- Cluster A: Content Precaching in CCN/CIoV — 8편 (Nam FA 6편, 핵심 줄기)
  Nam2021 → Nam2022a → Nam2023a → Nam2023b → Choi2024b → Nam2025 → Nam2026 → Youn2026
- Cluster B: Vehicular Cloud Member Replacement / Resource Allocation — 4편 (Nam FA 1: Nam2022c)
  Choi2022a, Nam2022c, Choi2022b, Choi2024a
- Cluster C: VANET 데이터·비디오 전달 / RSU 역할 — 4편 (Shin 주도)
  Shin2020 → Shin2021 → Shin2022(PSO) → Shin2026(RSU 역할 배분)
- Cluster D: IoT LoRa Multihop / Clustering — 3편 (Mugerwa 주도)
  Mugerwa2022 → Mugerwa2023 → Mugerwa2024
- Cluster E: WSN Mobile Sink 라우팅 — 1편 (Nam FA: Nam2022b)
- Cluster F: UAV VANET — 1편 (Shin 주도, 3D 확장: Shin2024)

### First-Author 8편 정체성
공통 정체성: 이동성 예측 + 협력 구조(RSU·V2V·Cloud) + Precaching 알고리즘 최적화
진화 궤적: 이동성 예측(규칙 기반) → 협력 구조 설계 → QoS 최적화 → 시스템 통합 → 강화학습(RL)
1. Nam2021: 속도 기반 이동성 예측 → Adaptive Precaching (도구 확립)
2. Nam2022a: 단속 연결 환경의 협력 Precaching
3. Nam2022b: WSN 모바일 싱크 라우팅 (이색 진출, 이동성 지원 범용 역량)
4. Nam2022c: RSU 협력 + 이동성 예측 향상 (인프라 활용 하이브리드)
5. Nam2023a: 지연 허용시간 기반 트래픽 최적화 (IEEE Access, QoS 지향)
6. Nam2023b: Set Ranking 기반 다중 차량 선택 (조합 최적화)
7. Nam2025: CIoV 통합 스토리지+Precaching (IEEE IoT Journal, 시스템 통합)
8. Nam2026: SAC 강화학습 기반 차량 선택 (학습 기반 최적화)

### 키워드 맵
- 도메인: VANET → CCN → CIoV / IoT LoRa / WSN / UAV
- 메커니즘: content precaching ← (mobility prediction, RSU 협력, V2V relay, vehicular cloud)
- 최적화 도구: SAC(RL, 2026) / PSO / Set Ranking / Adaptive·Proactive·Reactive
- QoS 지표: tolerable delay time, traffic optimization, storage management,
  near-far unfairness, intermittent connectivity

### 강점 & 차별화 포인트
1. 이동성 예측 활용의 일관성 (모든 FA 논문에서 핵심 도구)
2. CCN/CIoV 적용의 선구자적 포지션 (IEEE IoT Journal 게재로 검증)
3. RSU + V2V 하이브리드 아키텍처 (Nam2022c, Youn2026)
4. 실용적 QoS 제약 반영 (지연·트래픽·스토리지)
5. 규칙 기반 → 최적화 → RL의 단계적 진화 (depth 입증)
6. VANET·CCN·CIoV·LoRa·WSN·UAV 폭넓은 도메인 경험

### 협업자 구성 (Euisin Lee 그룹)
- Euisin Lee: 21/21 (마지막 저자, 지도교수)
- 핵심 3인 팀:
  * Youngju Nam: Precaching / CIoV FA 라인
  * Hyunseok Choi: Vehicular Cloud FA 라인
  * Yongje Shin: VANET / Video / UAV FA 라인
- Dick Mugerwa: LoRa FA 라인 (4편 협업)

### 저널 격상 트렌드
- MDPI tier3 (2021-2022) → IEEE Access tier1 (2023) → IEEE IoT Journal tier1 (2025)
  → 연구 성숙도 명확

### 다음 연구 후보 방향 (3개)
1. **MARL 기반 협력 Precaching in CIoV**
   - 흐름: Nam2026(단일 SAC) + Nam2023b(다중 차량 선택) + Youn2026(V2V 릴레이)
   - 차별점: 분산형 학습 기반 협력 (중앙화 PSO·단일 RL을 넘어)
   - 타겟: IEEE TVT, IEEE IoT Journal

2. **UAV-Assisted CIoV Precaching (UAV를 이동형 RSU로)**
   - 흐름: Shin2024(UAV) + Nam2025(CIoV) + Shin2026(RSU 역할 배분)
   - 차별점: 고정 RSU 커버리지 한계를 3D 이동형 UAV-RSU로 극복
   - 타겟: IEEE Access, IEEE IoT Journal

3. **Digital Twin 기반 이동성 예측 강화 Precaching in CIoV**
   - 흐름: Nam2021~Nam2026 이동성 예측 라인 + 최신 DT 트렌드
   - 차별점: 통계/규칙 기반 예측을 DT 시뮬레이션으로 대체
   - 타겟: IEEE IoT Journal, IEEE TITS

### 참고 메모
- references.json의 'Hyun-Seok Choi'와 'Hyunseok Choi'는 동일인 (표기 불일치)
- Choi2024a 제목이 일부 절단된 것으로 보임 — 추후 보정 권장
- 2024년은 유일하게 FA 0편 (대형 저널 준비기)


## [2026-04-29 Round 2] 전략적 후속 논문 아이디어 재구상 — Round 2

### Round 1 후보 4개 평가 점수표

| 후보 | 신규성(Novelty)/10 | 정체성부합(Identity Fit)/10 | 시뮬레이션실현성/10 | IoT-J Scope/10 | 차별성·창의성 종합/10 |
|------|-------------------|----------------------------|---------------------|----------------|----------------------|
| A) AoI-aware ILP Precaching | 7 | 9 | 8 | 8 | 7.5 |
| B) Mobile RSU (Bus) Caching ILP | 8 | 8 | 7 | 7 | 7.5 |
| C) LEO-Ground Cooperative ILP | 9 | 6 | 4 | 8 | 7.0 |
| D) Lyapunov Outage-aware Precaching | 6 | 7 | 8 | 7 | 6.5 |

평가 코멘트:
- A: ILP+AoI 조합 자체는 신규이나, AoI 단독 논문 2024-2025년 다수 존재. 단독으로는 창의성 한계.
- B: 버스-모바일 RSU는 2025 emerging이나, libsumo 버스 노선 모델링 추가 복잡성 존재.
- C: 신규성 최고이나, 위성 궤도/가시성 모델이 libsumo 스코프 밖 → 시뮬레이션 실현성 낮음.
- D: Lyapunov는 비-ML 대안이나, ILP 정체성 부합 낮고 Nam2026 SAC 대비 단순 기법 교체에 그침.

### Step 2: 신규 Angle 도출 결과

- Angle α: AoI + Near-Far Fairness 이중-차원 확장 (Nam2023b Set Ranking의 진화)
- Angle β: Robust ILP (Γ-불확실성 집합) — 모든 기존 논문이 deterministic → 완전 신규
- Angle γ: Bilevel Programming — 상위(RSU 배치)+하위(차량 경로) 계층적 최적화 — 완전 신규 기법
- Angle δ: AoI + Robust ILP (α+β 결합) ← 최강 조합: 신선도 worst-case 보장

### Step 3: 최종 3개 안 요약

[안 1] AoI-Guaranteed Robust ILP Precaching (차별성 8.5/10)
- 핵심: 이동성 예측 불확실성 하에서도 AoI SLA를 worst-case 보장하는 최초의 Robust ILP 프리캐싱
- 도구: Robust ILP (Γ-불확실성 집합), Branch-and-Bound
- 시뮬레이션: libsumo 5x5 RSU, AoI 위반률 vs Γ, density 1~20

[안 2] Fairness-Aware Multi-Hop ILP Precaching with AoI Constraints (차별성 7.8/10)
- 핵심: V2V 멀티홉 환경에서 근거리/원거리 차량 간 AoI 공정성을 ILP로 보장
- 도구: MILP + Jain's Fairness Index 제약, max-min fairness 목적함수
- 시뮬레이션: near/far group 분리, Jain's Index vs density

[안 3] Bilevel ILP for Joint Content-Placement and Vehicle-Route Precaching (차별성 8.2/10)
- 핵심: RSU 콘텐츠 배치(상위) + 차량 경로 선택(하위) Bilevel ILP로 계층적 최적화
- 도구: Bilevel ILP → KKT 변환 → 단일 레벨 MILP
- 시뮬레이션: 25개 RSU 오프라인 배치 + libsumo 동적 차량 시뮬레이션

### Step 4: 최종 추천

Tier 1 (즉시 진행): [안 1] AoI-Guaranteed Robust ILP Precaching (8.5/10)
- 이유: Robust+AoI+Vehicular Precaching 3중 조합 문헌 없음, ILP 정체성 유지, 1주 내 libsumo 검증 가능

Tier 2 (백업/후속): [안 3] Bilevel ILP (8.2/10)
- 이유: 학계 처음 보는 계층적 의사결정 구조, 창의성 최고이나 KKT 이론 2~3주 추가 학습 필요


## [2026-04-29 Round 2 컨펌] idea_spec.md 작성 완료

### 핵심 결정 사항

**확정 논문 제목 (안):** AoI-Guaranteed Robust ILP Precaching in CIoV  
**타겟 저널:** IEEE Internet of Things Journal  
**사용자 컨펌:** Round 2 - Plan 1 (AoI-Guaranteed Robust ILP Precaching) 최종 확정

### 확정된 4-Contribution Frame (Commander 위임 결정)

- **C1** — First Robust+AoI Joint Formulation in CIoV Precaching
  - 결정변수: x_{v,c} ∈ {0,1}, f_{v,c} ∈ ℤ₊, a_{v,c} (AoI 추적)
  - Γ-budgeted uncertainty set 𝒰(Γ)으로 이동성 예측 오차 모델링
  - 목적함수: worst-case max AoI 위반률 최소화
  - 제약: LET(Nam2023b), V2V outage(Youn2026), 캐시 용량, Γ-uncertainty

- **C2** — NP-hardness Proof + Tractable Greedy with (1-1/e) Approximation Bound
  - Robust Weighted Set Cover reduction으로 NP-hard 증명
  - LET × popularity × (1+AoI 가중) 그리디 휴리스틱
  - Nominal case 하 (1-1/e) approximation ratio

- **C3** — AoI-SLA Guarantee Theorem
  - Γ ≤ Γ* 조건 하에 worst-case AoI ≤ τ_max 보장 증명
  - Γ* closed-form (단일 RSU 케이스) + 수치 분석 곡선

- **C4** — Comprehensive libsumo Validation (Validation Plan으로 분리)
  - 5×5 RSU 격자, 800m comm_range, density ∈ {1,5,10,20}
  - 이동성 오차 ∈ {0%,10%,20%,30%}
  - 베이스라인 6개: Proposed-RILP, Proposed-Greedy, Nam2023b, Nam2025, Youn2026, Random-K
  - 지표 5개: AoI 위반률(주력), CHR, CDSR, PCO, RLBI
  - 시뮬레이터: 8.V2V Precaching.py 90% 재사용, VehicleSelection() → RILP/Greedy 교체

### idea_spec.md 저장 경로
`/home/imnyj/papers/paper3/paper/idea/idea_spec.md` (24,934자, 6개 섹션 완성)

### 6개 섹션 완성 확인
1. ✅ Problem Statement — deterministic LET 한계 + IoT-J gap 명시
2. ✅ Core Contribution — C1(RILP 정식화), C2(NP-hard+Greedy), C3(SLA Theorem)
3. ✅ Novelty vs. Prior Work — Nam2023b/Nam2025/Youn2026 대비 + 2025-2026 트렌드
4. ✅ Proposed Approach — 시스템 모델, RILP 정식화, 증명 스케치, Greedy 알고리즘, Theorem
5. ✅ Expected Impact — IoT-J 기여도, ITS/자율주행/6G 응용, 베이스라인 우위 가설
6. ✅ Storyline — 7-beat narrative arc (deterministic 위험 → AoI 보장 동시 달성)

### 다음 단계
- pipeline_state.json::idea.status → "done" 갱신 완료
- 다음 에이전트: **Experimenter** — libsumo C4 검증 실험 설계 및 구현


## [2026-04-29] Round 3 재검증

### 판정 결과 및 핵심 근거
- **판정: CONDITIONAL PASS**
- 핵심 근거 1: Robust ILP(Γ-uncertainty) + AoI worst-case guarantee + CIoV precaching 3중 조합은 현재 21개 references 어디에도 존재하지 않음 → 핵심 신규성 확인
- 핵심 근거 2: 치명적 결함 없으나 4개 소수정(M1~M4) 필요 → 즉시 idea_spec.md v1.1 반영 완료
- 핵심 근거 3: 외부 references 0개 (21개 전부 자가출판) → Librarian Round 4 외부논문 보강 필수 (Bertsimas-Sim 2004, Kaul AoI 2012, 2024-2025 vehicular AoI papers)

### 가장 가까운 선행 연구 Top 3
1. **Nam2025** (IEEE IoT-J, 직접 전임자): Storage-aware ILP in CIoV. Robust/AoI 없음 → 본 연구는 Robust+AoI를 추가한 직접 확장
2. **Youn2026** (Electronics, 시스템 모델 공유): V2V Relay ILP + deterministic LET + 800m outage. AoI/Robustness 없음 → 시스템 모델 상속 후 RILP로 대체
3. **Nam2023b** (Sensors, 개념적 전임자): Set Ranking 기반 deterministic LET 프리캐싱. 본 연구의 Γ=0 특수 케이스 → 완전 포함 관계

### C1~C4 평가 요약
- **C1 (Robust+AoI Joint Formulation):** ✅ 충분. 단, Big-M 값 명시(M1) 수정 완료
- **C2 (NP-hard + Greedy + Approximation):** ⚠️ 조건부 충분. NP-hard reduction 형식화(M2) 수정 완료. submodularity 증명 스케치는 논문 Appendix에서 보완 예정
- **C3 (AoI-SLA Guarantee Theorem):** ✅ 충분 (가장 차별화된 contribution). Multi-RSU Γ* 수치 분석 한계 명시 권장
- **C4 (libsumo Validation):** ✅ experiment_spec.json과 전면 일관. 베이스라인 6개 공정. Scenario E(Γ sweep)가 핵심 figure

### 수정 완료 사항 (idea_spec.md v1.1)
- M1: [R6] Big-M 값 M=(T_max+τ_max)·Δt 명시
- M2: NP-hardness reduction formal correspondence 표 + AoI=0 케이스 수식화
- M3: outage_end(v) = ⌈outage_zone_length / v_speed⌉ 정의 추가
- M4: [R1] f_{v,c} ≤ ⌊LET_v − δ_v⌋ floor 연산 명시

### 미해결 사항 (다음 단계)
- M5: Bertsimas-Sim (2004), Kaul AoI (2012) 등 외부 references 추가 → Librarian Round 4
- M6: "Greedy-AoI-noRobust" 7번째 베이스라인 검토 → Experimenter 협의
- 2025-2026 외부 논문 노벨티 재평가 → Librarian Round 4 완료 후 필수

### 다음 단계
- **Experimenter Stage 2**: libsumo Scenario A~E 실행 (idea_spec.md v1.1 기준, 즉시 가능)
- **Librarian Round 4**: 외부 references 보강 (Robust ILP, AoI, vehicular caching 2024-2025)
- **병렬 진행**: Experimenter 실험 실행 ↔ Librarian 외부 논문 보강
- pipeline_state.json::idea.status = "done"


## [2026-04-30] Round 5 Contribution 재검증
- Librarian Round 5 후 신규 41개 (2025-2026) 논문에 대해 contribution 침해 여부 평가
- 후보 11건 면밀 검토 (Shi2026, Wang2025x2, Li2025, Khan2025, Em2025, Tang2025, Lu2025, Liu2025, Wu2025a, Xu2026a)
- 핵심 발견: Robust + AoI worst-case + CIoV precaching ILP 3중 조합은 신규 논문 0건
- 판정: C1, C2, C3 모두 INTACT → PASS
- idea_spec.md 본문 변경 불필요, Revision Log v1.2 entry만 추가
- Writer Related Work 작성 시 비교 표에 위 5개 신규 논문 포함 권고
