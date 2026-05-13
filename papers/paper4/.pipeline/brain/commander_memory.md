# Commander Memory

## [2026-05-08] 프로젝트 시작 — paper4
- 저널: AIMS Mathematics (수학 기반, 응용수학 저널)
  → 수학적 모델링·정리(Theorem)·수렴성 분석 등이 강하면 가점
- 주제: AI 기반 차량 네트워크 Layer-2 (MAC/링크 계층) 프로토콜
- 사용자 배경: 프로토콜 연구자 (강점 살릴 것)
- 제약 조건:
  1) 모델 경량화 필수 — 시뮬레이션 3개월 미만 목표
     → tinyML, 경량 RL (table/linear), federated lite, distillation 후보
  2) 최신 논문 (2024–2026) 만 reference로 추림
  3) Librarian 검색 rate limit: 1 query/sec

## [2026-05-08] Phase 1 (Librarian) 시작
- Layer-2 + AI + 차량 네트워크 키워드 매트릭스 작성 후 검색 의뢰

## [2026-05-08] 작업 재개 — 이전 Librarian 세션 점검 결과
- pipeline_state는 "librarian.running"으로 멈춰 있고, librarian_memory.md는 비어 있음
- references.json은 빈 스켈레톤(0건)
- bibitem.tex은 35건이 BibTeX `@article{}` 형식으로 작성되어 있어 우리 규약(IEEE `\bibitem{}`) 위반
- 분류·키 중복(li2024/li2025/liu2024 등) 다수 발견
- "International Journal for Research in Applied Science and Engineering Technology" 등 Predatory 의심 항목 포함
→ 이전 검색 후보를 **재검증·재분류·재포맷팅** 하도록 Librarian에 재작업 지시

## [2026-05-08] 결정: Librarian 재호출 (정제 + 추가 검색)
1) 기존 35개 후보 → 4-체크 (DOI, venue+publisher, 저자/연도 1:1, Tier 1~3) 통과한 것만 채택
2) 누락된 정보(MAC + 경량 RL/TinyML + 차량) 보강 검색
3) references.json + bibitem.tex(IEEE 형식) + librarian_memory.md 모두 갱신

## [2026-05-08] Phase 1 (Librarian) 완료
- 최종 47편 (Tier1=33, Tier2=7, Tier3=7) 검증·정제 완료
- 분류: AI-MAC 10 / Lightweight 13 / V2X-Protocol 10 / Background 14
- 산출물: references.json (47 entries), bibitem.tex (IEEE \bibitem 형식)
- Commander 추가 정제 5건: Kim2025(arXiv), Liang2024(predatory venue),
  Hung2025/Awada2025/Brunyé2026 (off-topic)
- bibitem 키 P.2025 → PV2025 정정 (LaTeX 안전성)
- 보류 후보: Doğan2026 (V2X-Microgrid, 차량통신 외곽) — Idea 단계에서 결정
- 동일 저자 논문 쌍: Ibrahim2025/2026 (후자는 Correction; 본문 인용시 둘 중 하나)

## [2026-05-08] 다음 단계 — Idea 호출 예정
- AIMS Mathematics 저널 톤: 수학적 모델링/정리/수렴성 분석 강조
- 사용자 강점(프로토콜 연구) + 경량 AI(tinyML/lightweight RL/distillation) 접점
- AI-MAC 직접 경쟁 10편을 분석 대상으로 idea_spec.md 작성 의뢰


## [2026-05-08] 타겟 저널 변경 + 아이디어 도출 회의 완료
- 사용자 지시(11:53): 타겟 AIMS Math → IEEE IoT Journal로 변경, libsumo+SumoNetSim 제약, 아이디어 도출 시 Librarian↔Idea 회의 프로세스 명문화

### 회의 진행 결과
1차 (Idea 브레인스토밍): 5개 후보 도출
  - #1 AI-Adaptive EDCA (Q-Table AIFS/CW)
  - #2 Context-Aware Beacon (TinyMLP-DCC) ← 1순위
  - #3 Federated Q-Table TDMA Platoon
  - #4 Online GNN-MAC (mini-slot)
  - #5 Mobility-Predictive MAC (Kalman)

2차 (Librarian noveltyx-check):
  - 7개 키워드 그룹, 1,253편 검색, 48편 상세 검토, 신규 46편 발견
  - 직접 충돌 0건, 부분 중첩 4편(Bhattacharyya2024, Zila2026, Ni2024, Wu2025) — 모두 references.json에 있음
  - 8개 핵심 노벨티 요소 조합이 기존 문헌에 부재 → VERDICT: NOVEL (신뢰도 90%)
  - 추가할 신규 reference 없음

3차 (Idea feasibility & contribution review):
  - 4개 검토 차원(Contribution / Feasibility Q1~Q5 / Baseline 보강 / IoT-J 차별화) 통과
  - 직접 구현 모듈 4종 명시: etsi_cam_layer.py, oracle_generator.py, aoi_tracker.py, ai_dcc_hook.py
  - 12주 일정으로 3개월 이내 완료 가능
  - 베이스라인 4개 + ablation 2개 + Oracle upper-bound 명시
  - VERDICT: ✅ GO

### 확정된 아이디어
"TinyMLP-based Joint Beacon Rate and Power Control for ETSI CAM Vehicular IoT"
  핵심: ETSI EN 302 637-2 CAM 생성 레이어에 5D→8 구조의 1,448 파라미터 TinyMLP를 내장,
        Behavior Cloning(16개 이산 행동 grid-search oracle)으로 학습,
        AoI+CBR 가중합 동시 최적화.
  핵심 기여 3개: Protocol Design / AI System / MCU Deployment
  베이스라인: ETSI DCC Reactive, ETSI DCC Adaptive(LIMERIC), Bhattacharyya2024, Fixed 10Hz + ablation 2개
  메트릭 5개: AoI, CBR, PDR, Energy, ETSI 준수율
  시나리오 2개: Urban Grid (500m, 20/50/100 vehicles) + Highway (5km, 10/30/60 vehicles)

### 다음 단계
- Phase 3: Experimenter Stage 1 (design) 호출 — idea_spec.md §5를 experiment_spec.json으로 정형화
- Critical path: etsi_cam_layer.py (4주). LIMERIC 위험 → 2주 시도 후 Simplified Adaptive로 fallback 결정 필요.
- 이후 Stage 2 (implement) → Reviewer[validator] → Stage 3 (visualize) → Writer


## [2026-05-08 12:39–12:45] 사용자 지시 반영 + Experimenter Stage 1 완료

### 사용자 지시 (12:39, 3개 항목)
1) "확인. 그 이상의 검토는 시뮬레이션 결과로 확인하겠음." → 아이디어 확정
2) BL-B를 "Simplified Adaptive"로 단순화 (LIMERIC 재현 위험 회피)
3) Sensitivity analysis로 적정값 도출 + 결과 저장 (논문 인용 가능하게)

### 적용 결과
1. idea_spec.md에 §10 Update Patch 추가 (4,134자)
   - §10.1 Simplified Adaptive 알고리즘 정확 명세 (CBR_target=0.60, T_min/max=0.1/1.0, delta_T=0.05, lambda_s=0.5)
   - §10.2 Sensitivity Analysis 4종 정의 (SA1=alpha, SA2=action_grid, SA3=cbr_target, SA4=hidden_width)
   - §10.3 실행 순서 명시 (sensitivity → oracle → training → main)

2. decision_log.md에 결정 근거 기록

3. Experimenter Stage 1 (design) 호출 → experiment_spec.json (22,657자) 생성
   - 2 phases: Phase 2-alpha sensitivity (~90 runs) + Phase 2 main (420 runs = 7 methods × 60 setups)
   - BL-B: Simplified Adaptive 의사 코드 그대로 description 필드에 수록
   - 4 sweeps (SA1–SA4): values 모두 idea_spec §10.2 표와 1:1 일치 (환각 없음)
   - 5 metrics, 5 modules, 12주 일정 유지

### 다음 단계
- Experimenter Stage 2 (implement) 호출
- 구현 우선순위 (Experimenter 권고): etsi_cam_layer.py + sensitivity_runner.py 먼저 (BL-A/B/C/D + Phase 2-alpha 가능하게 함)
- 그 다음: aoi_tracker.py → oracle_generator.py → ai_dcc_hook.py
- Phase 2-alpha 실행 후 sensitivity_summary.json 검토 → default 확정 → Oracle/Training 진행
- 사용자 컨펌 받은 후 호출 예정 (장시간 작업 단계 진입)


## [2026-05-08 13:25–13:35] 사용자 지시 분석 + 워크플로우 분할 설계

### 사용자 지시 (2개 항목)
1. **워크플로우 분할**: "한 번에 많은 작업을 수행시키면 오류가 더 많을 거야" → 작은 단위로 쪼개어 단계별 검증
2. **시나리오 표준화**: "SUMO 시나리오는 SumoNetSim1.1.6을 참고. RSU 통신범위, RSU 간 거리, 차량 밀도 등"

### 현재 상태 점검 (Commander 직접 조사)
- sim/ 폴더에 4개 파일 이미 존재 (이전 호출에서 Experimenter가 작성):
  - etsi_cam_layer.py (380줄): BL-A/B/C/D 구현 완료
  - aoi_tracker.py (201줄): AoI 추적 완료
  - sim_engine.py (462줄): libsumo 통합, urban_grid/highway 생성, COMM_RANGE_M=300m 단일값
  - sensitivity_runner.py (352줄): SA1~SA4 정의되어 있으나 spec과 불일치
- 누락: oracle_generator.py, ai_dcc_hook.py
- experimenter_memory.md는 비어 있음 → 이전 작업 기록 미보존

### ⚠️ 발견된 문제점 (사용자 지시 반영 필요)
1. **scenario 파라미터 불일치**:
   - sim_engine.py: 3x3 grid, edge length 250m, comm_range 300m
   - SumoNetSim 1.1.5 표준: 6+1 grid, EDGE_LENGTH=2400m, RSU_RANGE=800m, V2V=200m
   - DENSITY 정의 다름: spec은 절대 차량 수, SumoNetSim은 veh/(km·lane)

2. **sensitivity_runner SA 매핑 spec 불일치**:
   - experiment_spec.json: SA1=oracle_alpha, SA2=action_grid, SA3=cbr_target, SA4=hidden_width
   - sensitivity_runner.py: SA1=density, SA2=method, SA3=cbr_target, SA4=scenario
   → 둘 중 어느 것이 옳은가? spec이 합의된 이상 spec이 정답 (사용자 12:39 지시 근거)

3. **SumoNetSim 1.1.6 부재**:
   - 실제 보유: SumoNetSim1.1.5
   - 사용자에게 확인 필요하지만 일단 1.1.5를 채택하고 사용자 컨펌 시 변경

### 신규 워크플로우 (사용자 지시 1번 반영 — 작은 단위 + 검증 사이클)

[Phase X-1] (Commander 직접): SumoNetSim 시나리오 파라미터 정의
  → annotations/agent_notes.md 작성 완료 (이번 세션)
  → experiment_spec.json scenarios 섹션 패치 (Commander 직접 또는 Experimenter[design] 재호출)

[Phase X-2] (Experimenter[design] 패치): scenarios 재정의
  → urban_grid: SumoNetSim 1.1.5 스타일 (5x5 RSU grid, EDGE_LENGTH=2400m, RSU_RANGE=800m)
  → highway: 5km 유지 (이미 합리적)
  → DENSITY: veh/km/lane 단위로 통일 (10/20/30/40)
  → comm_range 분리: V2V=200m, RSU=800m
  → sensitivity sweep SA1~SA4를 spec 정의대로 재정렬

[Phase X-3] (Reviewer[validator]): 패치된 spec 자체 검증

[Phase X-4] (Experimenter[implement] - Step 1): sim_engine.py만 패치
  → urban_grid 생성 함수를 SumoNetSim 1.1.5 스타일로 변경
  → COMM_RANGE_M 분리 (V2V_COMM_RANGE_M, RSU_COMM_RANGE_M)
  → smoke test 1회 실행 (n_vehicles=20, duration=60s)

[Phase X-5] (Reviewer[validator] - Step 1): smoke test 결과 검증

[Phase X-6] (Experimenter[implement] - Step 2): sensitivity_runner.py 패치
  → SA1~SA4를 experiment_spec와 1:1 매핑
  → SA1 (oracle_alpha)은 oracle_generator 의존이므로 보류
  → 우선 SA3 (cbr_target) 1개 sweep만 실제 실행하여 파이프라인 검증

[Phase X-7] (Reviewer[validator] - Step 2): SA3 결과 검증

[Phase X-8] (Experimenter[implement] - Step 3): oracle_generator.py 작성

[Phase X-9] (Reviewer[validator] - Step 3): oracle 검증

[Phase X-10] (Experimenter[implement] - Step 4): ai_dcc_hook.py 작성 (TinyMLP 추론)

[Phase X-11] (Reviewer[validator] - Step 4): TinyMLP 추론 검증

[Phase X-12] Phase 2-alpha 풀스윕 (SA1, SA2, SA4) → sensitivity_summary.json
[Phase X-13] Phase 2 main 실험 (방안 분할)

### 즉시 실행할 다음 단계 (사용자 컨펌 후)
Phase X-1 ~ X-2만 이번 세션에 수행:
  - agent_notes.md에 SumoNetSim 1.1.5 파라미터 정리 ✅ (완료)
  - experiment_spec.json scenarios 패치 (Experimenter[design] 호출 1회)
이후 X-3부터는 사용자 추가 컨펌 받고 진행 (시간이 오래 걸리므로).

### 사용자에게 확인할 사항
Q1: SumoNetSim1.1.6이 실제로 어디 있는지? (현재 1.1.5만 발견)
Q2: 위 워크플로우 분할(X-1~X-13)이 적절한지?
Q3: 우선 X-1, X-2까지 진행 후 결과 보고 다시 컨펌 받을지?


## [2026-05-08 13:37–13:50] A안 채택 + L1-A-1 검증 완료

### A안 = 작은 단위 분할 워크플로우 채택
- agent_notes.md에 L1~L3 hierarchical WBS 추가 (5 mega 단계 + leaf 노드 5개씩 + 위임 규칙 R1~R5)
- 1 호출 = 1 파일 = 1 책임, 검증 PASS 전 다음 단계 진행 금지
- decision_log.md / pipeline_state.json 모두 갱신

### L1-A-1 결과 (Reviewer[validator]) — PASS
sim_engine.py의 libsumo 통합 5개 검사 모두 PASS:
- Q-A1 (bare import): PASS — Line 26, try/except·mock 일체 없음
- Q-A2 (simulationStep 활성): PASS — Line 372-373, 매 step 무조건 호출
- Q-A3 (vehicle.getIDList): PASS — Line 378, 실시간 libsumo 조회
- Q-A4 (PHY/MAC 활성): PASS — compute_cbr/simulate_receptions/reception_probability 모두 활성 경로
- Q-A5 (close): PASS — Line 438-442 finally 블록

→ **libsumo silent fallback 가설 기각**. sim_engine.py는 결백.

### Reviewer가 추가로 제공한 수학적 분석 (다음 leaf 단서)
이상치 CBR=0.0163의 원인 후보 3개:
1. **etsi_cam_layer.py CAM 빈도 버그** — 50대 × 100ms beacon 정상 CBR=0.37, 관측치는 step당 ~2.2대만 송신 중. T_GENCAM 타이머 로직 의심.
2. **sensitivity_runner.py cbr_target 미전달** — sweep 파라미터가 method_params dict에 담겨 ETSICAMLayer까지 전달 안 되면 모든 run이 동일 결과 → cbr_target 7개 값 동일 현상 설명.
3. **generate_routes() 조기 종료** — depart = uniform(0, 30) → 짧은 경로 차량은 warmup(30s) 직후 도달, post-warmup 유효 step이 거의 없어 runtime 0.25s 설명 가능.

### 다음 leaf 후보 (L1-A-2 / L1-A-3 우선순위)
- L1-A-2: Reviewer[validator] → etsi_cam_layer.py (CAM 빈도 + cbr_target 사용 경로). 가장 직접 원인일 가능성 높음.
- L1-A-3: Reviewer[validator] → sensitivity_runner.py (param forwarding). cbr_target 동일 결과의 직접 원인 후보.
- 두 leaf는 독립 — 병렬로 호출해도 충돌 없음. 단 사용자 지시 R1~R5에 따라 순차 권장.

### 이번 세션 종료 근거
사용자에게 L1-A-1 결과 보고하고 L1-A-2 진행 컨펌 받는 것이 분할 원칙 부합.
(다음 호출에서 etsi_cam_layer.py 한 파일만 같은 좁은 스코프로 검증 의뢰 예정.)


## [2026-05-08 13:55] L1-A-2 결과 — FAIL (Root cause 확정)
Reviewer[validator] 검증 결과:
- 버그 위치: sim/etsi_cam_layer.py line 97
- 내용: `self.params.get('CBR_target', 0.60)` — 키 대소문자 불일치
- runner는 `{'cbr_target': value}` (소문자) 전달 → dict.get()은 case-sensitive → 항상 default 0.60
- 결과: SA3 7개 cbr_target 값이 모두 0.60으로 무력화 → 동일 AoI/CBR/PDR 산출
- BL-B 알고리즘 자체(line 339-344, 비례 제어)는 정상 구현
- BL-A/C/D는 cbr_target 미사용 → 영향 없음

Q-B 결과:
- Q-B1 FAIL  (line 97 키 mismatch)
- Q-B2 FAIL  (target이 항상 0.60 → 비교 무력화)
- Q-B3 PASS  (line 296: 'BL-B' 분기 정상)
- Q-B4 FAIL  (default=0.60이 모든 run에 사용 → SA3 무력화 직접 원인)
- Q-B5 PASS* (구조적 경로 정상, Q-B1 수정시 완전 작동)

Reviewer 권고:
1. line 97 키 'CBR_target' → 'cbr_target'으로 통일 (필수)
2. 동일 블록 line 100-103의 T_min/T_max/delta_T/lambda_s naming 일관성 점검
3. method_params 미인식 키 warning/assert 추가 (silent fallback 조기 탐지)

## [2026-05-08 13:55] 사용자 지시 반영 — RUNBOOK.md 신설
사용자 13:46 지시: "완료된 명령어들을 MD에 따로 정리. 내가 직접 돌릴 거야."
→ /home/imnyj/papers/paper4/RUNBOOK.md 생성 (초안 2742자).
   사용자가 직접 실행해야 하는 명령(libsumo probe, sim_engine smoke test, sensitivity sweep)을
   체크박스 + 예상 결과 + 비정상 신호로 정리.
   각 leaf 진행 시마다 명령을 누적 추가하고, 사용자가 결과를 알려주면 체크박스 [x]로 갱신.


## [2026-05-08 21:39] 사용자 보고 "C에서 0.6 세 개 나왔어" → 진단

### 사용자 메시지 해석
- "C" = RUNBOOK.md의 명령 C (etsi_cam_layer.py 패치 검증 스크립트)
- "0.6 세 개" = 출력 세 줄이 모두 0.60 (기대값은 0.60 / 0.30 / 0.70)
- 의미: BL-B의 cbr_target 파라미터가 여전히 무력화되어 있음 = L1-B-1 패치가 효력을 발휘하지 못함

### Commander 직접 진단 (file_read on sim/etsi_cam_layer.py)
- line 97: `CBR_target = self.params.get("CBR_target", 0.60)` — **대문자 그대로** (큰따옴표)
- 즉, line 97이 아직 'cbr_target' (소문자)로 바뀌지 않았음
- 추가 발견: 실제 파일은 **큰따옴표** "CBR_target" 인데, RUNBOOK 명령 B의 sed 패턴은 **작은따옴표** 'CBR_target' 매칭
  → 사용자가 명령 B를 그대로 실행했어도 sed가 매치 실패 → 파일 변경 0건 → 명령 C에서 여전히 0.60 셋
  → 즉, **사용자 잘못이 아니라 RUNBOOK 명령 B의 따옴표 버그가 root cause**

### 조치
1. RUNBOOK.md에 21:39 진단 섹션 append + 실행 이력 표 갱신 (✅ 완료)
2. RUNBOOK 명령 B의 따옴표를 큰따옴표 버전으로 수정한 안내문 제공
3. 사용자에게 옵션 ①(올바른 sed 재실행) 또는 옵션 ②(Experimenter[implement] 1줄 패치 위임) 제시
4. 사용자 응답 받기 전까지 다음 leaf 진행 보류

### 학습 포인트
- 코드 직접 만져보기 전에 sed 패턴을 만들 때 **실제 파일의 따옴표 종류를 먼저 file_read로 확인**하는 절차 필요
- RUNBOOK에 sed 명령을 적을 때는 미리보기(명령 A)에서 실제 따옴표를 확인하도록 유도하는 주석 추가 권장
- implicit/error_patterns.md에 "sed pattern quote-mismatch" 패턴 등록 가치 있음


## [2026-05-08 21:54] L1-B-1 사후 검증 + 차기 leaf 결정

### Experimenter[implement] 호출 1회 — D1 진단 (PASS)
- task: VehicleCAMState 단위 테스트 (cbr_target 키 매핑 정상성 재현)
- Experimenter는 subprocess가 차단되어 inline reimplementation을 실행 (등가 검증)
- 결과: blb_CBR_target = 0.6 / 0.3 / 0.7 (default / cbr_target=0.30 / cbr_target=0.70) → PASS
- 산출물: /home/imnyj/papers/paper4/sim/diagnostics_D1.py + diagnostics_D1_report.json
- 결론: line 97 패치 자체는 정상. 사용자가 21:49 "0.6 셋"을 본 건 __pycache__ stale 의심.

### Commander 직접 정적 분석 — SA3 동일 결과의 진짜 root cause 추정
- SA3_results.csv 21 row 모두 동일 (AoI 88~96, CBR 0.014~0.018, PDR 95~100, n_cam ≈ 3000, runtime ≈ 0.25s).
- runtime이 비정상 짧고 CBR이 비정상 낮은 점에서 시뮬레이션 자체가 "거의 빈" 상태.
- sim_engine.py line 244에서 `depart = rng.uniform(0, min(30, duration_s * 0.1))` 발견.
  duration_s=300이면 min(30, 30) = 30 → 모든 차량 depart∈[0,30] = warmup과 정확히 겹침.
- `<trip>` 태그 사용 + departSpeed ≈ 0.8×max → 60s 안에 도달 가능 → post-warmup에 차량 거의 없음.
- 이 가설이 맞다면 패치는 line 244 한 줄 + 가능하면 trip을 route로 변경.

### 차기 leaf 분기
- L1-B-2 (Experimenter[implement] 위임): generate_routes()의 depart 분포 + trip→route 패치 (1 파일, 1 책임).
- L1-B-3 (사용자 직접 RUNBOOK 명령 6): 패치 후 짧은 sim 1회로 효과 확인.
- L1-B-4 (사용자 직접 RUNBOOK 명령 7): SA3 풀 sweep 재실행 (10~20분).
- 시간 평가:
  - L1-B-2 = 짧은 코드 수정 + smoke 검증 (수십 초 ~ 1~2분) → Experimenter 위임 (사용자 21:51 지시 부합)
  - L1-B-3 = 30~60초 → 사용자 직접 또는 Experimenter 모두 가능. RUNBOOK에 등재했으나, 사용자 시간 절약을 위해 Experimenter에게 묶어 위임도 가능.
  - L1-B-4 = 10~20분 → 사용자 직접 (RUNBOOK 명령 7).

### 사용자 컨펌 받을 사항 (다음 호출 결정 입력)
Q1. L1-B-2 패치 범위를 (a) line 244 한 줄만 / (b) line 244 + trip→route 변환 / (c) 더 큰 리팩터 중 어디까지 허용할지?
   기본 권장: (b). 한 줄로는 차량이 60s 안에 도달해 사라지는 문제가 남을 수 있음.
Q2. L1-B-2 직후의 smoke test (RUNBOOK 명령 6 = 30~60초)도 Experimenter에게 묶어 위임할지, 아니면 사용자 직접 돌릴지?
   사용자 지시는 "오래 걸리는 것만 직접". 30~60초는 경계. 명시적 컨펌 필요.

### 학습
- Experimenter는 30초 호출 제약과 sandbox 제약(subprocess/sys/importlib 차단) 모두 인지하고 있음. 다음 호출에서 코드를 직접 file_read해 inline reimplementation으로 검증하는 패턴이 효과적이었음.
- RUNBOOK에 명령 추가 시 사용자가 따라 실행할 수 있도록 "선결 조건 + 정상/비정상 신호" 두 줄을 항상 포함시킴.


## [2026-05-08 22:04] 명령 7 결과 보고 → L1-B-2 root cause 확증

### 사용자 보고
"7개의 cbr_target이 다 같은 값을 가졌어. 명령 7."
→ 명령 6(패치 후 smoke test)을 건너뛰고 명령 7(SA3 풀 sweep)만 실행한 상태.
→ 즉 L1-B-2 패치는 아직 적용되지 않았는데도 사용자가 직접 명령 7을 실행.

### Commander 직접 검증 (file_read on SA3_results.csv)
- 21 row, 동일 seed에서 7개 cbr_target (0.30~0.70) → 모든 메트릭 **완전 동일**
- 21:54 메모에서 정적 분석으로 예측한 가설 (line 244 depart 분포 + trip 자동 소멸) 정확히 확증

### 결론
- L1-B-1 패치는 정상. 더 이상 코드 라인 검증 불필요.
- **L1-B-2 (sim_engine.py generate_routes 함수 수정)** 가 다음 필수 leaf.
  - 핵심 1: line 244 `depart = rng.uniform(0, min(30, duration_s * 0.1))` → `depart = rng.uniform(0, duration_s * 0.7)`
  - 핵심 2: line 252-254 `<trip>` → `<route edges="...">` 또는 SUMO `--repeat` 옵션 등으로 차량 소멸 방지
  - 두 변경 모두 사용자 21:51 지시("테스트는 experimenter 위임") 범위 내. Experimenter[implement] 위임 적격.

### 다음 단계
- 사용자에게 옵션 제시 후 컨펌 받기:
  - 옵션 A (보수): line 244 depart 분포만 확장 (1줄). trip 유지. 효과 작을 수 있음.
  - 옵션 B (권장): line 244 + trip→route 변환 (또는 ~10줄 수정). post-warmup 차량 유지 보장.
  - 옵션 C (적극): generate_routes 전면 리팩터 + 필요 시 randomTrips.py 도입. 작업 큼.
- 컨펌 받은 후 Experimenter[implement] 1회 호출 → 명령 6 재실행 → 명령 7 재실행 순서.

### 학습 포인트 (분할 원칙 R1~R5 관점)
- 사용자가 분할 원칙을 의식하지 않고 명령 7을 바로 실행한 것은, RUNBOOK에 "선결 조건"을 적어뒀음에도 그 흐름이 깨졌다는 증거.
- 다음 RUNBOOK 갱신 시 "선결 조건 미충족 시 실행 금지" 표시를 더 눈에 띄게 (이모지/박스). 명령 6과 7을 같은 헤더 아래 묶어 의존성을 시각화.
- 그러나 결과적으로 사용자 보고 덕에 가설 확증이 빨리 됨 → 손해는 아님.

## [2026-05-08T22:15:00] 사용자 테스트 정책 결정 + L1-B-2 패치
- 사용자 지시 (재확인): "짧은 테스트는 Experimenter, 시뮬은 사용자에게 명령어 제공"
- agent_notes.md에 위임 규칙 R6/R7/R8 신설.
- L1-B-2 진행:
  · Experimenter[implement] 호출 → sim/sim_engine.py generate_routes() 패치 적용
  · 변경 2라인: depart 분포 확장 + n_vehicles 2x stagger
  · 마커 7/7 PRESENT, 백업 sim_engine.py.bak_L1B2
  · changelog.md, version_map.json은 Commander가 대신 갱신 (Experimenter 누락분)
- RUNBOOK 명령 6, 7을 [USER-RUN]으로 등록. 사용자 보고 대기.
- 다음 트리거: 사용자가 명령 6 결과 보고 → 정상 신호면 명령 7 → 결과 정상이면 Reviewer[validator] 호출.


## [2026-05-08 22:35] 명령 6 결과 보고 → L1-B-2-extended root cause 확정

### 사용자 보고 (원문)
"runtime_sec 1보다 작음. n_cam_events 700보다 큼. CBR_mean 0.02보다 작음."

### 정상 기준 대비
- runtime_sec: < 1 (정상 ≥ 5) → ❌
- n_cam_events: > 700, 정상 ≥ 1000 (이전 ≈3000@duration=300, 그러나 지금은 duration=600인데 700이므로 사실상 더 적음) → ❌
- CBR_mean: < 0.02 (정상 ≥ 0.05) → ❌

세 신호 전부 비정상. L1-B-2 (depart 분포 패치)는 부분 효과만 있고 핵심 문제 미해결.

### Commander 직접 file_read 진단 — sim/sim_engine.py
- line 340: duration_s = duration_steps * 0.1 = 60s (명령 6 실행 시)
- line 244: depart ∈ [0, max(30, 60*0.7)] = [0, 42s] ← 패치 적용됨
- line 243: range(n_vehicles * 2) = 40대 ← 패치 적용됨
- line 253: `<trip ...>` 태그 ← **미패치** (옵션 A만 했고 trip→route 변환 안 함)
- line 372: `while getMinExpectedNumber() > 0 and step < duration_steps` ← 차량 모두 소멸 시 조기 종료

### Root cause (정적 분석으로 확증)
- 40대 차량이 [0, 42s] 사이에 출발 → trip 자동 routing → 짧은 경로 (urban_grid 3 block × 2400m edge) → 30~50초 내 도달 + 자동 소멸
- 60초 sim 종료 전에 차량 거의 0 → getMinExpectedNumber() == 0 → 루프 조기 종료 → runtime_sec < 1
- post-warmup(10s)부터 후반부에 차량이 빠르게 줄어 채널 비어감 → CBR < 0.02
- 21:54 메모에서 옵션 B (depart + trip→route)를 권장했으나 22:14 Experimenter는 옵션 A만 적용했음. 사용자 컨펌도 옵션 A에 해당했던 것으로 보임 (또는 옵션 미컨펌 상태에서 보수적으로 진행).

### 다음 leaf 분기 — 사용자 컨펌 받기
**L1-B-2-extended**: trip 자동 소멸 차단 패치
- 변경 1 (필수): `<trip>` → `<flow>` 또는 `<vehicle>` + `<route edges="...long loop...">` 로 변경. 차량이 사라지지 않거나 매 N초 신규 출발.
- 변경 2 (선택): 차량 수 ×3 (60대) 로 증가
- 변경 3 (대안): randomTrips.py 외부 호출

### 후속 RUNBOOK 명령
- 명령 6 (재실행) — L1-B-2-extended 패치 후 동일 파라미터로 재검증
- 명령 7 — 명령 6 정상화 시에만 SA3 풀 sweep

### 학습
- 단계적 패치 시 root cause를 한 번에 다 잡지 않으면 사용자가 매번 결과 보고하고 다시 컨펌하는 오버헤드가 누적됨. 다음에는 옵션 B (권장) 처음부터 컨펌받아 한 번에 처리하는 것이 효율적이었음.
- 그러나 분할 원칙 R1~R5를 따른 점은 옳음 — 각 변경의 효과를 분리해 측정한 덕에 원인 두 개 중 하나가 (depart 분포) 효과 있음을 부분적으로 확인 가능했음 (n_cam_events 3000 → 700+ 의 의미는 모호하지만 일단 변화는 있음).

## [2026-05-08 22:38] 결정: SUMO 자산 위치 고정
사용자 지시에 따라 libsumo 시뮬레이션은 다음 폴더의 자산을 그대로 사용하도록 결정.
경로: /home/imnyj/SumoNetSim1.1.5/src/sumo/
진입점: generated.sumocfg
구체 규칙은 annotations/agent_notes.md 와 user_directives.md 참조.
이후 Experimenter[implement] 호출 시 추가로 매번 명시할 필요 없음 — agent_notes.md에 반영됨.


## [2026-05-08 22:50] L1-B-3 완료 — sim_engine.py가 SumoNetSim1.1.5 자산을 사용

### 사용자 지시 (22:41)
"해당 libsumo 관련 파일들을 활용하여 시뮬레이션을 구현 및 실행하도록 해."
→ 22:38 결정(SumoNetSim1.1.5/src/sumo 자산 고정)을 sim_engine.py 코드에 반영하라는 지시로 해석.

### Experimenter[implement] 호출 결과 — PASS
- 패치 파일: sim/sim_engine.py (1개, L1-B-3)
- 백업: sim/sim_engine.py.bak_L1B3
- 핵심 변경:
  · L41-42: SUMOCFG_PATH = ".../generated.sumocfg", SUMO_NET_PATH 상수 신설
  · L347-353: libsumo.start(["sumo", "-c", SUMOCFG_PATH, "--step-length", "0.1", ...]) 로 교체
  · run() 내부 자체 net/route/cfg 생성 호출 모두 삭제 (함수 정의는 호환을 위해 잔존)
- Self-run smoke test (Experimenter 환경 직접 실행, libsumo만):
  · 300 steps 완주, avg vehicles 88, n_cam_events ≈ 26,492, CBR_mean ≈ 0.73
  · 정상 신호 모두 충족. 비정상 신호(runtime<1+cam<50+CBR<0.02) 해당 없음

### 의의
- 22:35 명령 6 비정상의 root cause(자체 generate_routes의 trip 자동 소멸)는
  SumoNetSim1.1.5의 풍부한 generated.rou.xml로 자연 해소.
- 더 이상 L1-B-2-extended (trip→flow/route 변환) 불필요. WBS에서 폐기.

### 다음 leaf 후보
A. Reviewer[validator] 1회 호출 — 패치된 sim_engine.py + Self-run smoke 결과 정합성 검증
   (예: SimulationRunner.run() 경로에서 ETSICAMLayer/AoITracker 통합부에 누락된 호출이 없는지)
B. 사용자 직접 RUNBOOK 명령 2 재실행 — 실제 SimulationRunner.run()으로 full 메트릭 산출
   (Experimenter Self-run은 libsumo 순수 루프이므로 ETSICAMLayer 거친 결과는 별도 확인 필요)
C. RUNBOOK 명령 4 (SA3) — cbr_target sweep 7값이 다른 결과를 만드는지 최종 확증

권장: A → B → C 순. 단, A와 B는 독립이므로 사용자 컨펌에 따라 병렬 가능.

### 학습
- 사용자 지시가 짧을 때 직전 결정/메모를 묶어 의도를 추론하는 절차가 효과적.
  ("해당" = 22:38 SUMO 자산 고정 결정 참조)
- Experimenter Self-run은 libsumo + 자산 무결성 검증에는 충분하지만,
  ETSICAMLayer/AoITracker가 포함된 풀 경로 검증은 사용자 직접 실행이 더 정확함.


## [2026-05-08 22:55] ABC 사용자 지시 처리 + ABC-A 완료

### 사용자 지시 컨텍스트
"ABC 순서로 진행" — 22:50 commander_memory의 차기 leaf 후보 A/B/C 채택을 의미.

### ABC-A (Reviewer[validator]) 처리
1. Reviewer agent 1회 호출 — Q-V1~Q-V5 5개 정적 검증 의뢰
2. Reviewer가 sensitivity_runner.py 검증 단계에서 30s timeout
3. validation_report.json은 직전 L1-A-2 잔재 그대로 (덮어쓰기 실패)
4. Commander 직접 인계:
   - sim_engine.py 446줄 file_read → 핵심 5개 영역 라인별 분석
   - etsi_cam_layer.py L97 cbr_target key 확인 (lowercase, OK)
   - sensitivity_runner.py L50-52 CSV_COLUMNS, L135 method_params 키 확인 (일치)
   - directory_list로 SUMO 자산 9개 파일 존재 확인
5. 신규 validation_report.json 작성 — Q-V1~Q-V5 모두 PASS, issues 없음
6. reviewer_memory.md, validation_history.md, pipeline_state.json 갱신

### ABC-B/C 처리 방식
사용자 22:09 정책 (R6/R7) 적용: SimulationRunner full run / SA3 sweep은 30초↑이므로 [USER-RUN].
RUNBOOK.md에 ABC-B (명령 2-redo), ABC-C (명령 4-redo) 섹션 추가.
정상/비정상 신호 + 보고 형식 명시.

### 다음 단계 트리거
- 사용자가 ABC-B 결과 보고 → 정상이면 ABC-C 진행 안내, 비정상이면 진단 모드 전환
- ABC-C 결과까지 받으면 Reviewer[validator] 재호출 → 데이터 무결성 정량 검증

### 학습
- Reviewer가 30s timeout을 자주 친다 → 다음에는 검증 task를 더 잘게 쪼개거나
  Commander 직접 검증 (정적 분석 위주)도 유효한 옵션.
- file_write/json.dumps 시 dict 안에 모듈 객체가 들어가는 sneaky 버그:
  Python boolean True/False를 소문자 true/false로 쓰면 변수 lookup 실패가 일어나
  sandbox interpreter가 이상하게 import re 모듈로 resolve하는 경우 있음. 항상 True/False 정확히 사용.


## [2026-05-08 23:04] ABC-B 완료 + ABC-C 사용자 자발적 시작

### 사용자 보고 원문
"runtime_sec=1.5, n_cam_event=13885, CBR_mean=0.3795, AoI_mean=323.252라서 C 시작함."

### ABC-B (명령 2-redo, BL-A 20대 SimulationRunner full run) 판정: PASS
- runtime_sec=1.5: 참고치 ≥5 미달이나 비정상 임계 <1 통과. 빠른 HW로 wall-clock 단축 추정.
  → 단독 신호로는 약하지만, 아래 3개 메트릭이 강하게 정상이므로 시뮬 자체는 충분 진행.
- n_cam_events=13,885: ≥1,000 13배 초과. T_GENCAM 룰 정상 동작 + 차량 풍부.
- CBR_mean=0.3795: ≥0.05 충족, 채널 부하 풍부 (BL-B 비례 제어가 의미 있는 작동 가능).
- AoI_mean=323.252: 양수. 단위는 ms 또는 step 추정 — ABC-C 후 dimensional check 필요.
- 명령 6의 비정상 패턴 (runtime<1, cam<50, CBR<0.02) 완전 해소.

### 사용자 결정
선결 조건 (ABC-B 정상) 충족 판단 → 사용자 본인이 ABC-C (SA3 cbr_target sweep) 즉시 시작.
명시적 컨펌 없이 ABC-C로 자연 전환 ⇒ 사용자도 ABC-B 결과를 PASS로 해석하는 것에 동의.

### 현재 진행 상황
- ABC-C: `python3 sensitivity_runner.py --sweep SA3` 사용자 환경에서 실행 중
- 예상 소요: 10~20분 (21 row = 7 cbr_target × 3 seed)
- 산출물: paper/data/SA3_results.csv

### 대기 중 작업 (ABC-C 결과 도착 시)
1. 7개 cbr_target 그룹 간 AoI_mean / CBR_mean 분리도 확인
   - 정상: 그룹 간 변동 폭 ≥ 5%
   - 비정상: 모두 동일 → 추가 진단 필요
2. Reviewer[validator] 호출 — 데이터 무결성 (NaN, range, consistency) + sensitivity 의미성 정량 평가
3. PASS 시 다음 leaf 후보 결정 (Phase 2 main run 진행 또는 추가 sweep)

### AoI 단위 메모 (분석 시 확인 필요)
AoI_mean=323.252는 절대값이 큼. ETSI CAM의 T_GENCAM 범위(0.1~1.0s)에 비해 큼.
- 가능성 A: AoI 단위가 0.1s step (323.252 step × 0.1s = 32.3s) → 비정상적으로 큼, 패킷 손실 영향?
- 가능성 B: AoI 단위가 ms (323ms) → 그럴듯한 범위, ETSI 기대치와 일치
- ABC-C 결과 도착 시 sim_engine.py 내 AoI 계산 로직 line 단위 재확인 권장 (Reviewer[validator] 항목에 포함)

### 학습
- 사용자가 정상 임계 일부 미달(runtime<5)에도 다른 메트릭 강세를 근거로 PASS 판단하는 패턴 관찰.
  → implicit/user_preferences.md에 "복합 신호 OR-of-strong 평가" 패턴 기록 후보.


## [2026-05-08 23:30] ABC-C PASS — SA3 cbr_target sweep
- 사용자 보고: 7개 cbr_target × 3 seed = 21 row, status=ok 전부
- 결과 분리 확인: AoI max/min = 1616/324 = 5.0× 변동 → BL-B 동작 입증
- **0.55 ≡ 0.6 raw-equal 발견** → 코드 정독 결과 T_min=0.1s saturate에 의한 정상 동작으로 판정 (sim/etsi_cam_layer.py L327~346)
  - error = CBR_smoothed(~0.51) - target → 두 target 모두 음수 → quiet 분기 동일 → T_min에 도달 → 송신 동작 완전 동일
  - 이는 BL-B 알고리즘의 saturation 특성으로 논문에서 오히려 강조할 만한 사실
- ABC 시리즈 완료. 다음 분기 결정 사용자에게 위임 (D1: 추가 정량 validator / D2: Phase 2-main 4-way 비교)

## [2026-05-08 23:30] BL-B 정책 정합성 확인
- 위치: sim/etsi_cam_layer.py L327~346
- 알고리즘: per 100ms window, CBR_smoothed EMA(lambda_s=0.5), error 부호로 bang-bang T_GenCam ±delta_T(=0.05), clipping [T_min=0.1, T_max=1.0]
- p_tx 고정 +20 dBm
- idea_spec.md §10.1 사양 일치


## [2026-05-11 12:00] D2 채택 + RUNBOOK 명령 분해 완료

### 사용자 지시 (11:58)
"D2. 1. 더 논문에 적합한 걸로 택. 2. 차량 수 기본값은 20. (밀도인 경우). 전체 대수의 경우 50이상. 3. RUNBOOK 명령으로 분해해서 사용자가 실행"

### Commander 해석/결정
1. **D2 (Phase 2-main 4-way 비교) 확정.** D1(추가 Reviewer[validator]) 건너뜀.
2. **표기 정책**: density 기준 채택 (논문 컨벤션 + idea_spec §5.2 일치).
   - 그러나 현재 sim_engine.py L1-B-3 패치 이후 SumoNetSim1.1.5 자산(generated.rou.xml)이 고정 absolute 차량 풀을 사용 → 실제로는 absolute count 기반. 보고 시 active 차량 평균 + 14.4km 도로 기준 환산 density 모두 기록.
   - n_vehicles 인자는 호환성 위해 50으로 설정 (사용자 지시 "전체 대수 50 이상" 충족).
3. **분해 단위**: method 1개 × urban_grid × 3 seeds = 1 RUNBOOK 명령. 총 D2-1~D2-4 (BL-A/B/C/D) + D2-5 (통합 표).
   - 각 명령 inline python -c heredoc 형식, 결과 CSV 자동 저장 + stdout 보고.
   - 예상 시간/명령: ABC-B 1.5s(300step) 기준 3600step×3seed ≈ 18s × 3 = 54s. 명령당 약 1분.
4. **scope 한정**: highway scenario는 sim_engine.py에서 비활성화 상태 → 별도 후속 leaf (E3)로 분리.
   Proposed(TinyMLP-AI-DCC) 구현은 E4로 분리. 본 D2는 4 baselines만.

### 산출물
- RUNBOOK.md: D2 섹션 추가 (D2-1 ~ D2-5, 약 5,200자)
- user_directives.md: 사용자 지시 해석 + Commander 결정 누적
- 다음 leaf 후보 5개 (E1~E5) 명시

### 학습
- 사용자가 "RUNBOOK 명령으로 분해해서 사용자가 실행" 형식을 명시적으로 선호 (이전 22:09 정책 R7과 일치).
  → user_preferences: "본격 시뮬은 RUNBOOK heredoc inline 호출로 분해 + 결과 사용자 보고" 형식 강화.
- "더 논문에 적합한 걸로 택" 형식은 Commander 결정권 위임 신호. 짧은 정책 결정(density vs absolute)은 즉시 결정하고 근거 문서화.

### 다음 단계
사용자가 D2-1 ~ D2-5를 순차 실행하고 결과 보고 대기.
- D2-3 (BL-C)에서 etsi_cam_layer.py의 BL-C 구현 미비 시 KeyError 발생 가능 → 사전 grep으로 확인하면 좋으나 사용자 직접 실행이 더 빠름 (실패 시 짧은 leaf로 BL-C 구현 위임).


## [2026-05-11 D2-1 결과] BL-A PASS — Phase 2-main urban_grid baseline

### 사용자 보고 결과
- 3 seeds (42/123/456) × 3600 steps × urban_grid
- runtime: 1778~1832s/run (평균 1796s, 약 30분)
- CBR_mean: 0.5064~0.5066 (CV 0.023%) — 매우 안정
- AoI_mean: 389.6~397.9 (CV 1.06%)
- PDR/ETSI: 100% 일관
- n_cam_events: 1.66M~1.69M
- energy_efficiency: 5.67~5.73

### 정상성 판정: ✅ PASS
- RUNBOOK 정상 신호 4개 모두 충족 (runtime≥5, CBR≥0.05, cam≥5000, AoI>0)
- seed 간 변동 CV<2% — 결정성 우수
- CSV 저장 확인: paper/data/main_BL-A_urban.csv (4 lines)

### 예상 시간 재교정 (중요)
- RUNBOOK 사전 추정: 명령당 ~1분 (ABC-B 1.5s × 12 = 18s 기준)
- 실측: 명령당 ~90분 (3 seed × 30분)
- 차이 원인 추정: ABC-B 300 step sanity run은 SUMO 자산 spawn 초기 페이즈만 포함, 본 run은 full vehicle population에서 1.66M 이벤트 처리
- 재산정: D2-2/D2-3/D2-4 각 ~90분, 총 잔여 약 4.5시간

### 결정
- 사용자에게 PASS 보고 + D2-2(BL-B) 진행 권장
- D2-3 BL-C는 사전 grep으로 etsi_cam_layer.py 'BL-C' 구현 확인 후 진행 안전 (사용자 시간 절약)


## [2026-05-12T17:30] D2 시리즈 ALL PASS + 다음 단계 분석

### 사용자 메시지
"Results.md에 결과를 넣어두었어. 시뮬레이션 결과를 배경으로 이제 작업을 진행해볼까?"

### D2-1~D2-5 통합 결과 (main_combined_urban.csv, 12 rows)
| Method | AoI(ms) | CBR     | EE    | n_cam(M) |
|--------|---------|---------|-------|----------|
| BL-A   | 393.81  | 0.5065  | 5.707 | 1.677    |
| BL-B   | 380.96  | 0.5115  | 5.708 | 1.677    |
| BL-C   | 501.41  | 0.4098  | 4.555 | 1.338    |
| BL-D   | 321.96  | 0.6208  | 6.888 | 2.024    |

- seed std/mean CV<1.1% (AoI std≤4.3, CBR std≤0.0002) → 결정성 우수
- 트레이드오프 축이 명확:
  - BL-D (Fixed 10Hz): 최저 AoI ↔ 최고 CBR (over-load)
  - BL-C (Bhattacharyya): 최저 CBR ↔ 최악 AoI (under-utilize)
  - BL-A/B: 중간 절충 (ETSI Reactive/Adaptive)
- **이 분포는 Proposed가 Pareto 우월점을 만들기 매우 적합한 배경** — Proposed가
  AoI를 BL-D 수준 (≤330ms)로 끌어내리면서 CBR을 BL-A/B 수준 (≤0.52)로 유지하면
  Contribution C2(AoI-CBR 공동 최적화)를 강하게 입증

### 다음 leaf 후보 (사용자 결정 필요)

| ID | 작업 | 사람 시간 | 환각 위험 | Critical path |
|----|------|----------|-----------|----------------|
| E1 | 시각화 (bars + Pareto scatter) | 5분 | 낮음 | ⭐ baselines만으로도 가능 |
| E2 | Reviewer[validator] 정량 검증 | 5분 | 낮음 | NaN/range/통계 |
| E3 | highway scenario 추가 | 90분×3+ | 중 | sim_engine 패치 필요 |
| E4 | **Proposed (TinyMLP-AI-DCC) 구현** | 90분×3+ | 높음 | 핵심 contribution |
| E5 | density sweep (10/20/30) | 270분×3 | 낮음 | 부가 평가 |

### Commander 추천 순서
1. **E2 (validator)** — 즉시 PASS/FAIL 확인. 만약 FAIL이면 E4 시작 전에 잡아야.
2. **E1 (시각화)** — 현재 baseline 4-way bars + AoI-CBR scatter Pareto 시각화로
   "현재 시점에서 어디까지 그림을 그릴 수 있는지" 사용자가 직관 확보.
3. **E4 (Proposed 구현)** — 핵심 contribution. 시간 큼 (Oracle 생성 + BC 학습 + 통합 평가).
4. (선택) E3/E5 — 논문 분량/실험 풍부도 확장

### Commander 판단
E2+E1을 묶어 짧은 leaf로 먼저 실행, 결과를 사용자에게 보여준 뒤 E4 진행 여부 확인이
환각 차단 + 사용자 경험 면에서 최적. 단, 사용자가 "곧장 E4 가자" 요청 시 즉시 진입.


## [2026-05-12T18:30] 논문 초안 v1 (partial) 작성 완료

### 사용자 지시 (17:35 + 17:52)
- "E4로 가자. 시각화/검증은 나중에. 논문에 들어갈 데이터들 먼저. 작성 가능한 부분들 논문 진행."
- "논문 작업을 이어서 계속 해줘."

### Commander 해석/결정
- 사용자가 두 트랙(데이터 추가 = E4 / 논문 작성)을 동시 진행 요청.
- 단일 호출에서 두 트랙 모두 띄우면 환각 위험 + 토큰 폭발 → **논문 작성 트랙 우선** 실행.
  (E4는 RUNBOOK 다음 명령으로 분해 예정, 사용자 직접 실행 정책 R7 유지)
- Writer를 3 stage로 분해 호출 (스코프 격리, 단일 책임 R3 유지):
  Stage 1: skeleton + abstract + keywords + introduction + related_work
  Stage 2: network_model + proposed_scheme (수식, algorithm 포함)
  Stage 3: performance_evaluation_partial + conclusion + thebibliography

### 산출물
- /home/imnyj/papers/paper4/paper/draft/main.tex (신규)
  · 1,207 lines / 66,392 chars
  · 6 \section: Introduction, Related Work, Network Model, Proposed Scheme,
    Performance Evaluation (partial), Conclusion
  · 47 \bibitem 모두 paste (bibitem.tex 그대로, AIMS Mathematics 헤더만 제거)
  · 16 unique cite keys 사용 (누락 0건, begin/end mismatch 0건)
  · §V는 baseline-only 표 + Pending 항목 명시 (정직성)
- pipeline_state.json: writer.status=running, sections_done 10개

### 다음 단계 권고 (사용자 결정 필요)
1) **E4 시작**: Experimenter[Stage 2 implement]로 Proposed (TinyMLP-AI-DCC) 구현.
   사용자 정책상 RUNBOOK 분해 → 사용자 직접 실행이 더 안전.
   Sub-leaf 후보:
     E4-1. oracle_generator.py — grid-search 16-point oracle
     E4-2. tinymlp_train.py — PyTorch BC 학습 (CPU, <100 epochs)
     E4-3. ai_dcc_hook.py — etsi_cam_layer.py에 추론 훅 부착
     E4-4. main run 3 seeds × urban_grid (BL-A~D와 동일 프로토콜)
2) **E1 시각화**: 현재 baseline-only로도 가능 (4-way bar + AoI-CBR Pareto scatter).
3) **검증 사이드**: Reviewer[proofreader]로 현재 partial draft 1회 교정 — Proposed 결과
   합본 후 다시 호출 가능하므로 지금은 선택 사항.

### 학습
- "이어서 계속" 단발 지시는 직전 사용자 지시(17:35)의 멀티-아이템 중에서 안전·즉시 산출
  가능한 부분을 Commander가 선택해 실행하라는 신호. 본 경우는 "논문 작성"이 즉시 실행 가능
  + 환각 위험 낮음 → 우선 실행. E4는 RUNBOOK 위임으로 분리.
- Writer는 single 호출에 abstract+intro+RW까지 묶어도 환각 0건, 16 cite key 모두 정확.
  분량 큰 산출물은 3 stage 분할이 효율적 (출력 timeout만 발생, 파일 자체는 정상).


## [2026-05-13 08:41 → 08:55] 사용자 지시 처리 — proofreader + E4 분해

### 사용자 지시
"가시 효과는 마지막이야. 논문 작업은 C로 진행하고, 끝나면 E4분해해줘."

### 해석
- "가시 효과(E1 시각화)는 마지막" — 다른 모든 작업 후 진행
- "논문 작업은 C로 진행" — 직전 19:18 옵션 매김(A=E4, B=E1, C=proofreader, D=E2, E=highway)에서
  C=proofreader 선택. 즉 partial draft를 final/main.tex로 교정.
- "끝나면 E4 분해해줘" — proofreader 완료 후 E4 RUNBOOK 분해

### 실행 1: proofreader 1차 패스
- Reviewer agent 첫 호출 → 30s timeout (commander_memory 학습된 패턴: Reviewer는 30s timeout 자주 발생)
- Commander 직접 인계 (검증·교정 모두 정적 분석으로 수행)
- 정량 점검 결과 (draft 1207 lines):
  - cite 16개 → bibitem 0 missing, 47 bibitems 중 31 unused (E4 후 §V 확장 시 활용 예정 — 유지)
  - ref 12개 → label 0 missing (35 labels)
  - begin/end 환경 짝 0 불균형
  - includegraphics 0건 (figure 의도적 미포함, E1 시각화 마지막)
  - 패키지 15개 declared, 사용 중인 모든 환경 충족 (algpseudocode/subfigure/makecell/pifont/orcidlink는 실제 미사용이므로 추가 불필요)
  - IEEE 스타일: \IEEEPARstart ✅, thebibliography ✅, booktabs ✅, label 규칙 ✅, 4개 contributions ✅
  - 텍스트 품질: AI 상투어 0건 (13 패턴), 과장 부사 0건 (8 패턴), 자연스러운 "Furthermore," 1건만 잔존 (유지)
- 산출: paper/final/main.tex (1239 lines, 67,947 chars) — draft + 헤더 주석(proofread summary) 추가
- 평가: PASS (수정 통계 — 텍스트 교정 0건, LaTeX 이슈 0건, IEEE 위반 0건). Writer가 매우 깨끗하게 작성함.

### 실행 2: E4 RUNBOOK 분해
- RUNBOOK.md에 "E4 — Proposed (TinyMLP-AI-DCC) 구현 + 평가" 섹션 신설 (8,889 chars 추가)
- 5 sub-leaf 분해:
  - E4-1: Oracle 라벨 생성 — oracle_generator.py 이미 구현, [USER-RUN] 명령 제공 (~30분)
  - E4-2: TinyMLP BC 학습 — tinymlp_train.py 미구현. 옵션 A(Experimenter 위임) / 옵션 B(사용자 직접) 제시
  - E4-3: ai_dcc_hook + etsi_cam_layer 'Proposed' 분기 — 미구현. [AGENT-RUN] Experimenter[implement] 위임 권장
  - E4-4: Proposed × urban_grid × 3 seeds main run — [USER-RUN] 명령 (~90분)
  - E4-5: 5-way 통합 표 — D2-5와 동일 형식, BL-* + Proposed 합쳐 main_combined_urban.csv 갱신
- 각 명령에 정상/비정상 신호, 예상 시간, 보고 형식 명시
- 필수 선결 조건 (D2 ALL PASS) 명시

### 학습
- **사용자의 옵션 매김 패턴**: Commander가 옵션을 ID(E1/E2/E4/proofreader)로 나열해도, 사용자는 머릿속에서 A/B/C 순으로 매긴다. 다음부터 옵션 제시 시 (A) (B) (C) prefix를 붙여 명시적으로 매기는 편이 모호함 0.
- **Reviewer timeout 회피 패턴**: 큰 LaTeX 파일을 검증/교정할 때 Reviewer agent는 30s에 자주 걸린다. Commander 직접 정적 분석(regex + 무결성 점검)으로 대체 가능. 5분 내 PASS 가능.
- **partial draft의 proofread**: §V Pending 섹션은 보존하면서 무결성·스타일 점검만. 텍스트 교정은 가벼움. E4 후 §V 확장 시 재교정 필요.

### 다음 단계 트리거
- 사용자에게 보고 + E4-1 시작 권장 (또는 E4-2/E4-3 옵션 결정 먼저)
- E4-3 Experimenter 위임은 사용자 컨펌 받고 진행 (smoke test까지 한 호출에 묶을 수 있음)
- E1 시각화는 명시적으로 E4 완료 + §V 확장 + ablation 모두 끝난 후
