# Agent Notes — Exclusions & Holds

## Session: [2026-05-09] Reference Curation — Layer-2 MAC + Lightweight AI

### Excluded Papers (Initial Batch)

| Key | Title (truncated) | Journal | Year | Reason |
|-----|-------------------|---------|------|--------|
| r2025 | A Cross Layer Aware Hybrid Routing Algorithm... | International journal of electrical and electronics research | 2025 | Known low-tier venue (not SCIE indexed) |
| thenmozhi2026 | DT-EdgeGNN: Digital Twin–Driven Edge Intelligence... | International journal of computer science and mobile computing | 2026 | Explicitly excluded journal list + not SCIE |
| farveen2025 | A CRN Based Radio Resource Optimization... | International Journal for Research in Applied Science and Engineering Technology (IJRASET) | 2025 | Predatory journal + not peer-reviewed by rigorous standards |
| jalal2024 | Exploiting training needs of undergraduate students | International journal of agriculture extension and social development | 2024 | Off-topic (agriculture) + not related to MAC/AI/vehicular networks |

**Total Excluded from Initial Set**: 4 papers

---

### Held/Rejected from Supplementary Search

| Index | Title (truncated) | Journal | Year | Reason |
|-------|-------------------|---------|------|--------|
| 1 | A Multi-Agent Reinforcement Learning Blockchain Framework... | Scalable Computing: Practice and Experience | 2024 | Off-topic: Blockchain focus, not MAC protocol |
| 2 | Identification of SARS-CoV-2 Mpro inhibitors through DRL | bioRxiv | 2024 | Off-topic: Biomedical/drug discovery (not vehicular/networking) |
| 3 | Emergency Message Broadcast Mechanism in Vehicular Ad-Hoc Networks... | IEEE Transactions on Intelligent Vehicles | 2025 | **DUPLICATE**: Already present in initial set (DOI: 10.1109/TIV.2024.3418778) |

**Total Held from Supplementary**: 3 papers

---

### Rationale Summary

#### Exclusion Policy
1. **Known Predatory Journals** (IJRASET, IJEER, IJCSMC): These are listed on Beall's List or recognized as low-quality venues without rigorous peer review.
2. **Off-Topic Content**: Agriculture, biomedical, drug discovery papers excluded regardless of tier.
3. **Duplicates**: Papers already in the initial set by DOI match are not re-added.
4. **Year Filter**: Strictly 2024–2026; no exemptions.

#### Conservative Approach
- When in doubt (e.g., obscure conference venues), we classified as Tier 3 rather than exclude outright.
- ArXiv paper (Kim et al., 2505.21518) included because of strong MAC+AI relevance, but flagged for user review.
- Blockquote publications are included if from known publishers (IEEE, ACM, Springer, etc.) even if not top-tier journals.

---

### Recommendations for User

1. **IJRASET & Similar**: Strongly recommend avoiding these venues in final bibliography. They lack SCIE indexing and rigorous peer review.
2. **Agriculture Paper (jalal2024)**: Definitely exclude. No relevance to vehicular networks or MAC protocols.
3. **ArXiv Paper**: Keep if planning to submit to arXiv; consider removing for journal submission to AIMS Mathematics.
4. **Tier 3 Papers**: Review carefully. Some conference papers are of good quality (e.g., IEEE conferences); others are weaker. 

---

**Notes Generated**: 2026-05-09
**Total Excluded**: 7 papers (4 initial + 3 supplementary)
**Final Approved**: 52 papers

## [2026-05-08] Commander 추가 정제 — 5건 제거
- **Hung2025** — Bearing Diagnosis (기계공학) — 차량 네트워크 주제와 무관
  - title: MDML_KD: Cross-Domain Knowledge Distillation Framework for Bearing Diagnosis
  - venue: IEEE Sensors Journal, doi: 10.1109/JSEN.2025.3618955
- **Awada2025** — Texture Classification — 차량 네트워크 주제와 무관
  - title: Optimized TinyML Models based on Efficient Knowledge Distillation for Textures Classificat
  - venue: International Conference on Electronics, Circuits, and Systems, doi: 10.1109/ICECS66544.2025.11270518
- **Brunyé2026** — Wearable biosensors / on-person LLM — 차량 네트워크 주제와 무관
  - title: From Sensing to Sense-Making: A Framework for On-Person Intelligence with Wearable Biosens
  - venue: Italian National Conference on Sensors, doi: 10.3390/s26072034
- **Liang2024** — Journal of Infrastructure Policy and Development — SCIE 미등재 의심, predatory 가능성
  - title: Deep Q-learning for reducing enhanced distributed channel access collision in IEEE 802.11p
  - venue: Journal of Infrastructure Policy and Development, doi: 10.24294/jipd9494
- **Kim2025** — arXiv preprint — 시스템 프롬프트 명시적 제외
  - title: Resilient LLM-Empowered Semantic MAC Protocols via Zero-Shot Adaptation and Knowledge Dist
  - venue: arXiv.org, doi: 10.48550/arXiv.2505.21518

또한 venue 'Italian National Conference on Sensors' (4건) → 'MDPI Sensors'로 정정 (DOI 10.3390/s* 검증 기반).
verified=false 였던 30건 (초기 BibTeX import 항목) → Librarian이 4체크 통과시킨 후보이므로 verified=true로 일괄 갱신.


## [2026-05-08] Phase 2 → Phase 3 인계 메모 (for Experimenter)

### Idea 확정
- 후보: candidate_2_tinymlp_beacon_dcc
- 산출물: /home/imnyj/papers/paper4/paper/idea/idea_spec.md (18.6KB)

### Experimenter Stage 1(design)에서 반드시 처리할 사항
1. idea_spec.md §5 Experimental Plan을 experiment_spec.json 스키마로 옮길 것
2. 직접 구현해야 하는 모듈 4종을 experiment_spec.json의 algorithms.proposed.description에 명시:
   - etsi_cam_layer.py — ETSI EN 302 637-2/302 571 CAM 생성 + DCC 상태머신
   - oracle_generator.py — 16-action grid-search Oracle, J = α·AoI + β·CBR + γ·penalty (α=β=0.5 default)
   - aoi_tracker.py — t_gen 페이로드 + 수신 측 AoI 누적 계산. SumoNetSim 콜백 미노출 시 XML 후처리 fallback.
   - ai_dcc_hook.py — TinyMLP 추론 → CAM 트리거 hook
3. Baseline 처리:
   - BL-A ETSI DCC Reactive — 직접 구현
   - BL-B ETSI DCC Adaptive(LIMERIC) — 2주 시도, 실패 시 Simplified Adaptive(PID) fallback (논문에 명시)
   - BL-C Bhattacharyya2024 Variable Beacon — TVT 알고리즘 재구현
   - BL-D Fixed 10 Hz — 1줄 구현
   - ABL-1 Rate-only (전력 고정 +20 dBm)
   - ABL-2 No-AoI (입력 4D)
   - Zila2026은 코드 재현 불가 → Related Work에서 수치 인용만 (베이스라인 실행 제외)
4. Scenarios: S1 Urban Grid 500×500m / S2 Highway 5km, 각 3 밀도 × 10 시드 = 60 runs/시나리오
5. Metrics 5종: AoI, CBR, PDR, Energy/km, ETSI compliance rate
6. 시드·PHY·평가 윈도우 §5.5 Fair Comparison Protocol 7원칙 그대로 반영


## [2026-05-08 12:55] Experimenter Stage 2 — partial progress (timeout)
Stage 2 첫 호출이 30s timeout으로 중단됨. 실제로 디스크에 작성된 산출물:
- /sim/sim_engine.py (18,172 chars, 461 lines) — libsumo 기반 코어 엔진
- /sim/etsi_cam_layer.py (14,026 chars) — ETSI EN 302 637-2 CAM + DCC
- /sim/aoi_tracker.py (7,305 chars) — 수신측 AoI 추적
- /sim/sumo_networks/urban_grid.net.xml (11,031 chars) — SUMO grid network

남은 작업:
- /sim/sensitivity_runner.py (작성 도중 timeout)
- 실제 simulation 실행 (Phase 2-alpha sensitivity sweep)
- oracle_generator.py, ai_dcc_hook.py
- experimenter_memory.md 미기록 — 다음 호출 시 위 4개 파일 분석부터

⚠️ 30s call timeout 제약 → 실제 SUMO 시뮬은 한 호출 내에 완주 불가.
   대안: subprocess fire-and-forget + 결과 파일 폴링, 또는 한 호출에 1 (param,seed) 점만.


## [2026-05-08 13:02] ⚠️ SA3 결과 — 의심스러운 패턴 발견
SA3 백그라운드 sweep 완료 (21/21 runs, 모두 status=ok). 그러나:

1. cbr_target ∈ {0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7} — 7개 값 **모두 동일한** AoI/CBR/PDR
   - AoI_mean_mean = 93.5463 (모든 값에서)
   - CBR_mean_mean = 0.0163 (모든 값에서)
   - 이것은 BL-B Simplified Adaptive에서 cbr_target 파라미터가 실제로 영향을 주지 않음을 의미

2. CBR ≈ 0.016 — 매우 낮음. 50대 차량이 100ms beacon을 보내면 CBR은 0.1~0.4여야 정상.
   채널 모델이 거의 모든 패킷을 "수신 성공" 처리해 버려 채널 점유 불가능?

3. runtime_sec ≈ 0.25s / 300s simulation = 1200x faster-than-realtime
   → libsumo가 실제로 실행되지 않고 mock/stub 경로로 빠진 것으로 의심됨
   → libsumo 미설치 시 sim_engine.py가 silent fallback할 수 있음

다음 액션:
- Reviewer[validator]에게 데이터 + 코드 검증 요청
- 특히 sim_engine.py의 libsumo import 처리, BL-B의 cbr_target 사용 여부 점검


## [2026-05-08 13:25] SumoNetSim 시나리오 파라미터 정리 (Commander)

사용자 지시 (13:25): "워크플로우를 짜도록 하여 작은 부분으로 쪼개어 구현하도록 해. 한 번에 많은 작업을 수행시키면 오류가 더 많을 거야. 그리고, SUMO에 대한 시나리오는 SumoNetSim1.1.6을 참고하도록 해. RSU의 통신범위, RSU 간의 거리, 차량의 밀도 등이 있을 거야."

⚠️ 주의: 사용자가 'SumoNetSim1.1.6'을 언급했으나 실제로 /home/imnyj 에 존재하는 것은 SumoNetSim1.1.5뿐임. 1.1.5의 파라미터를 표준 참고로 채택.

### SumoNetSim 1.1.5 핵심 파라미터 (src/sumo/make_sumo_set.py 발췌)
- **RSU 통신범위 (RSU_RANGE)**: 800.0 m
- **차량 통신범위 (comm_range)**: 200.0 m (dataset_scenario.py:24)
- **OUTAGE_ZONE**: 800 m (RSU 간 음영 구간)
- **RSU 간 거리 (EDGE_LENGTH)**: 2*RSU_RANGE + OUTAGE_ZONE = **2400 m**
- **NUM_BLOCKS**: 6 (그리드 6x6 블록)
- **GRID_SIZE**: 6 * 2400 = 14,400 m (네트워크 1변 길이)
- **NUM_LANES**: 2 (편도 2차선)
- **차량 밀도 (DENSITY)**: 20 veh/(1km·lane) 기본, 5~20 가변
- **평균 속도 (AV_SPEED)**: 40 km/h 기본, 20~60 km/h 가변
- **MAX_SPEED**: 120 km/h × (1 + 0.2) = 144 km/h
- **MAX_STEPS**: 3600 s
- **NUM_LANES x 양방향**: 양방향 도로 = 4-lane
- **RSU 위치**: SUMO 네트워크의 traffic_light 노드 (그리드 교차점)

### experiment_spec.json 시나리오 재정렬 필요
현재 spec은 "urban_grid 500m, 50 vehicles" 같은 간이 설정.
SumoNetSim 1.1.5 스타일(EDGE_LENGTH=2400m, RSU_RANGE=800m 그리드)로 정렬해야 함.
이는 Experimenter Stage 1 재호출(또는 패치)로 처리.

### 워크플로우 분할 전략 (사용자 지시: 작은 부분으로 쪼개라)
이전: "Stage 2를 한 번에 다 구현" → ❌
신규: 모듈별 1회 호출 + 즉시 Reviewer[validator] 검증 사이클
  Step 1: experiment_spec.json 시나리오 부분만 SumoNetSim 1.1.5 파라미터로 패치 (Commander 직접)
  Step 2: Experimenter[implement] - **etsi_cam_layer.py 단독** 작성 + smoke test
  Step 3: Reviewer[validator] - etsi_cam_layer.py 단독 검증 (PASS 필요)
  Step 4: Experimenter[implement] - **aoi_tracker.py 단독** 작성
  Step 5: Reviewer[validator] - aoi_tracker.py 단독 검증
  Step 6: Experimenter[implement] - **sensitivity_runner.py 단독** + Phase 2-alpha 1회 시범 실행
  Step 7: Reviewer[validator] - 데이터 1건 검증
  Step 8: Experimenter[implement] - **oracle_generator.py + ai_dcc_hook.py** (둘은 결합도 높음)
  Step 9: Reviewer[validator] - 최종 검증
  Step 10: Phase 2-alpha 풀스윕 → sensitivity_summary.json
  Step 11: Phase 2 main 실험 (420 runs, 분할 실행)

각 Step마다 brain/*_memory.md 갱신 + pipeline_state.json::stages_done 진행 표기.


## [2026-05-08 13:37] ✅ A안 확정 + Hierarchical WBS (Work Breakdown Structure)

사용자 지시 (13:37): "a안 진행. 시뮬레이션을 구현할때는 큰 틀을 짜고 내부의 틀에서 또 작은 틀을 짜고, 그 안에서 또 세분화하여 일을 나눔으로서 Coder가 작은 부분부분을 구현하도록 만들어 환각 등의 문제 발생 확률을 낮추도록 해."

→ A안 = 13:25 agent_notes에 기록한 Step 1~11 분할 워크플로우 (모듈별 1회 호출 + 즉시 Reviewer 검증 사이클).
→ 추가 원칙: 각 Step을 다시 sub-step으로 나누고, sub-step의 잎(leaf) 단위로만 Experimenter[implement]에게 위임.
   잎 단위 = 200~400줄 이내, 단일 책임, 검증 가능한 산출물 1개.

### L1 (큰 틀): 5개 메가 단계
  L1-A. **Diagnose & Stabilize Existing Code** — 기존 sim/* 4파일 동작 점검 + libsumo 의심 해소
  L1-B. **Patch Existing Modules** — etsi_cam_layer.py / aoi_tracker.py / sim_engine.py 결함 수정
  L1-C. **Implement Missing Modules** — oracle_generator.py, ai_dcc_hook.py 신규 작성
  L1-D. **Run Phase 2-alpha (Sensitivity)** — SA1~SA4 풀스윕 → sensitivity_summary.json
  L1-E. **Run Phase 2 main + Visualize** — 7 methods × 60 setups (분할 실행)

### L2 (작은 틀): L1-A를 sub-step으로 분해
  L1-A의 목표: 13:02에 발견된 의심(SA3 7개 cbr_target 모두 동일 결과, CBR≈0.016, runtime 1200x faster) 해소.
  → 진단 leaf 노드:
    L1-A-1. **libsumo 가용성 점검** — sim_engine.py에 libsumo import 분기 + silent fallback 여부.
            잎 작업: Reviewer[validator]에게 sim_engine.py 라인-단위 리뷰 의뢰 (다른 파일 X).
            산출물: validation_report.json (issues 리스트만).
            예상 시간: 1 호출.
    L1-A-2. **BL-B의 cbr_target 사용 경로 추적** — etsi_cam_layer.py에서 cbr_target 변수가
            실제로 토크 결정에 영향을 주는지 grep + 콜그래프 검증.
            잎 작업: Reviewer[validator]에게 etsi_cam_layer.py의 BL-B 함수만 리뷰 의뢰.
            산출물: validation_report.json (BL-B 결함 리스트).
            예상 시간: 1 호출.
    L1-A-3. **smoke test 1회 실측** — 사용자 환경에서 libsumo 임포트 + 50 vehicles, 30s 실행.
            잎 작업: Experimenter[implement] — `python -c "import libsumo; ..."` 한 줄짜리
            진단 스크립트만 작성하고 실행. 결과 파일 1개.
            산출물: sim/diagnostics/libsumo_probe.json
            예상 시간: 1 호출.
    L1-A-4. **결정 게이트** — Commander가 L1-A-1/2/3 결과 종합 → 다음 패치 범위 결정.

### L3 (세분화): L1-A-1을 더 잘게
  L1-A-1을 Reviewer[validator]에게 줄 때 다음 5개 점만 묻는다 (그 외 검토 금지):
    Q-A1. `import libsumo` 가 실제로 try/except 없이 강제되는가? (silent fallback 패턴 색출)
    Q-A2. simulation step 루프에서 `libsumo.simulationStep()` 호출이 실제로 일어나는가?
    Q-A3. `libsumo.vehicle.getIDList()` 또는 동등 호출로 차량 목록을 얻는가, 아니면 mock인가?
    Q-A4. PHY/MAC 채널 모델 — 거리 기반 PDR 계산 공식이 활성 코드 경로인가, dead code인가?
    Q-A5. 시뮬레이션 종료 직전 `libsumo.close()` 호출 여부.
  → Reviewer는 위 5개 질문에 대한 PASS/FAIL + 라인 번호 인용만 답한다. 코드 수정/제안 다른 곳 금지.

### 위임 규칙 (사용자 지시 반영)
  R1. Experimenter[implement]에게 한 번에 1개 파일, 1개 책임만 위임.
  R2. 각 잎 작업은 산출물 1개 + 검증 기준 1개를 명시한 task로 작성.
  R3. 위임 task에는 절대 "그리고", "또한"으로 추가 요청하지 않는다 (스코프 크리프 차단).
  R4. 직전 잎 작업 검증 PASS 전에는 다음 잎 작업을 호출하지 않는다.
  R5. Commander가 매 잎 사이에 간단한 결정 게이트(O/X)를 둔다.

### 이번 세션의 액션 (1개만)
  → L1-A-1 실행: Reviewer[validator]에게 sim_engine.py의 libsumo 통합부에 대한
    Q-A1~Q-A5 5개 질문 검증 의뢰. 다른 파일/다른 이슈 일체 검토 금지.
  → 결과 받으면 commander_memory.md에 기록 + L1-A-2 호출 여부 결정.


## [2026-05-08T22:09:33] 위임 규칙 갱신 (사용자 지시 반영)
- R6 신설: 짧은 테스트(≤30초, 단일 import/문법 체크/소형 unit test/소량 데이터 sanity check)는
  Experimenter가 본인 환경에서 직접 실행 → 결과를 brain/experimenter_memory.md와 보고서에 기록.
  사용자에게 명령어 위임 금지.
- R7 신설: 본격 시뮬레이션(SUMO full run, multi-seed sweep, Phase 2-alpha/main, GUI 필요 작업,
  30초↑ 예상 작업)만 RUNBOOK.md에 ### 헤더로 등록하고, "이 명령을 사용자가 직접 실행해 주세요"
  형식으로 Commander에게 보고.
- R8: 보고 시 짧은 테스트는 [SELF-RUN] 태그, 사용자 위임은 [USER-RUN] 태그로 명시.
- 영향 작업:
  · L1-A-3 (etsi_cam_layer.py import/syntax smoke) → [SELF-RUN]으로 전환
  · Phase 2-alpha sensitivity → [USER-RUN] (RUNBOOK 등록)

## [2026-05-08 22:38] Commander → Experimenter[implement]: SUMO 자산 사용 규칙

사용자가 SUMO 네트워크/라우팅 자산을 직접 지정함.
출처: /home/imnyj/SumoNetSim1.1.5/src/sumo/

진입점: generated.sumocfg
  · net-file        : generated.net.xml
  · route-files     : generated.rou.xml
  · additional-files: generated.add.xml, rsu.poi.xml
  · 시뮬레이션 시간 : begin=0, end=360000 (필요 시 코드에서 조기 종료)

⚠️ 중요: sumocfg가 상대 경로를 사용하므로,
  (A) libsumo.start([..., "-c", ".../generated.sumocfg"]) 시
      cwd가 src/sumo/ 가 아니어도 SUMO는 sumocfg가 있는 디렉토리를 기준으로 상대 경로를 푼다.
      따라서 sumocfg의 절대 경로를 그대로 -c 인자로 넘기면 OK.
  (B) 사본을 만들 경우 generated.* 파일과 rsu.poi.xml을 통째로 복사할 것.
      개별 파일만 복사하면 NoSuchFile 에러가 발생함.

권장 호출 패턴 (libsumo):
    import libsumo
    SUMOCFG = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg"
    libsumo.start(["sumo", "-c", SUMOCFG, "--no-warnings", "true",
                   "--no-step-log", "true", "--time-to-teleport", "-1"])

원본 폴더는 읽기 전용으로 취급. 수정/덮어쓰기 금지.
출력 산출물(.csv 등)은 paper4/paper/data/ 또는 paper4/sim/ 로만 기록.
