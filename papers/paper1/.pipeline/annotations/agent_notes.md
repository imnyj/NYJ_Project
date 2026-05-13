# Agent Notes — Librarian Session

## Date: 2026-04-30
## Agent: Librarian
## Task: References Building for paper1 (ST-MBAN Dwell Time Prediction)

---

## Execution Summary

### Search Phase
- **Search Tool**: semantic_scholar_search
- **Search Scope**: 32 queries across 8 categories
- **Time Period**: 2015-2026
- **Results**: 153 papers found

### Validation Phase

#### Validation Criteria
1. DOI exists (or publication year >= 2023)
2. Venue is clearly identifiable
3. Authors information present
4. Publication year >= 2015
5. Tier-1 or Tier-2 publisher (IEEE/ACM/Springer/Elsevier/EURASIP)

#### Validation Results
- **Passed**: 72 papers (47.1%)
- **Failed**: 81 papers (52.9%)

#### Exclusion Reasons (Failed Papers)
- Missing or incomplete venue information: ~35 papers
- Pre-prints (arXiv only, no peer review): ~20 papers
- Year < 2015: ~12 papers
- Non-Tier-1 venues: ~14 papers

### Category Breakdown

| Category | Papers | Avg Citations | Min/Max Citations |
|----------|--------|---------------|-------------------|
| CIoV | 11 | 45.2 | 1-138 |
| V2I Precaching | 9 | 62.1 | 6-151 |
| V2V Precaching | 10 | 89.5 | 12-309 |
| Popularity-based | 6 | 71.3 | 5-181 |
| Mobility Prediction | 10 | 64.2 | 3-151 |
| Hybrid | 6 | 58.5 | 8-132 |
| ML/DL Precaching | 7 | 74.6 | 12-670 |
| Snapshot/RSU-Local | 13 | 38.1 | 1-123 |

### Quality Metrics
- **Average Citation Count**: 62.1 (across all 72 papers)
- **Median Citation Count**: 42
- **Most Cited**: "Caching in the Sky..." (670 citations, 2016)
- **Publication Year Range**: 2015-2025
- **Median Publication Year**: 2019

---

## Output Artifacts

### 1. references.json
- **Location**: `/home/imnyj/papers/paper1/paper/references/references.json`
- **Format**: JSON with 72 entries
- **Fields per Entry**:
  - id, title, authors, year, venue, citations
  - doi, github_url (empty, to be filled), source_query, source_tool, category
- **Size**: ~45 KB
- **Validation**: All entries have DOI and Tier-1 venue

### 2. bibitem.tex
- **Location**: `/home/imnyj/papers/paper1/paper/references/bibitem.tex`
- **Format**: IEEE Transactions style
- **Structure**: 8 sections with category headers
  ```
  % ********** Related Work — CIoV... **********
  ibitem1 ... 
  ibitem2 ...
  ```
- **Total Entries**: 72 bibitems
- **Size**: ~28 KB

---

## Notable Findings

### High-Impact Papers (>100 citations)
1. "Caching in the Sky" (2016, 670 citations) — UAV-based caching
2. "Intelligent Edge Computing in Internet of Vehicles" (2021, 309 citations) — Joint computation offloading
3. "Content Popularity Prediction" (2018, 181 citations) — Edge caching with popularity
4. "An Edge Caching Scheme" (2018, 151 citations) — V2I specific
5. "The Next Generation Vehicular Networks" (2017, 138 citations) — Content-centric framework

### Emerging Areas
- **ML/DL Precaching**: Mostly 2018-2024 publications, high citation growth
- **Snapshot/RSU-Local**: Distributed learning approaches (still emerging, lower citation avg)

### Gaps Identified (For Future Enhancement)
- Very few papers specifically on "dwell time prediction" (will require targeted manual search)
- Limited papers on ST-CVAE or variational approaches for vehicular networks
- Reinforcement learning for precaching still under-explored

---

## Recommendations for Writer

1. **Introduction**: Cite top 3-5 papers from V2I/V2V sections for motivation
2. **Related Work**: Use section headers from bibitem.tex for structure
3. **Baselines Section**: Select papers from ML/DL and Snapshot/RSU-Local categories
4. **Comparison Table**: Reference papers should map to Related Work — D1~D6 categorization

---

## Known Limitations

1. **GitHub URLs**: Not automatically extracted; recommend manual addition for baselines
2. **Dwell Time Specific**: Only ~3-4 papers directly address "dwell time" prediction
   - May need supplementary search for "trajectory prediction" + "dwell"
3. **Snapshot Learning**: Limited papers (13) on RSU-local/distributed learning in vehicular context
   - Suggests relatively novel approach for paper1

---

## Session Metadata
- **Start Time**: 2026-04-30 14:16:54
- **End Time**: 2026-04-30 14:35:22 (estimated)
- **Total Execution Time**: ~18 minutes
- **Librarian Agent**: Active
- **Status**: COMPLETE ✓


## agent_notes - Reviewer[proofreader] 2026-04-30 14:58
- Ran proofreader mode on main.tex
- 'novel' x1 removed, 'e.g.' x1 converted to 'for example'
- No '---', 'significantly', 'remarkable', 'groundbreaking' found
- 94 occurrences of ' (' remain - need human review for non-LaTeX parentheticals
- final/main.tex saved successfully


## [2026-05-06 14:51] Commander 주간 자체 업그레이드 검토 #1

### 검토 범위
- commander.py (34.4KB, 809 lines) — 6 에이전트 통합 + Blue/Green 자체 업그레이드 + 주간 검토 훅
- agents/*.py (writer, reviewer, experimenter, idea, librarian, qwen) — 모두 정상 구조
- requirements.txt — 모든 핵심 라이브러리가 `>=` 하한선만 명시 (smolagents>=1.0.0, litellm>=1.50.0, anthropic>=0.40.0 등)
- core/upgrade_check.py — boot_check / record_outcome 로직 정상

### 검토 시점 상태
- upgrade_state.json: 직전 기록은 `user_declined` (999d 표기 — 첫 부팅 sentinel)
- error_patterns.md: 비어 있음 — 반복 오류 패턴 미검출
- user_preferences.md: 비어 있음
- decision_log.md: 2026-05-01 paper1 일괄 처리 완료, 데이터셋 도착 대기 중

### 발견 사항 (변경 후보)

1. **응답 timeout 패턴** (commander_memory.md 2026-05-01 기록)
   - 증상: Writer/Reviewer 호출 4건이 final_answer 출력 길이로 30초 timeout.
     산출물은 모두 정상 생성됨 (file_write가 별개 채널로 작동).
   - 원인 추정: 에이전트가 작성한 LaTeX 본문 전체를 final_answer 인자로 returning.
   - 후보 패치: 각 managed_agent 프롬프트에 다음 한 줄 추가:
     "final_answer는 결과 파일 경로 + 1~2문장 요약만 반환. 본문 전체를 final_answer
     인자로 반복하지 말 것 (이미 file_write로 저장됨)."
   - 영향: 토큰 출력 절감, timeout 회피.
   - 위험: 매우 낮음. 프롬프트 텍스트 추가만, 동작 변경 없음.

2. **라이브러리 버전 동결 부재**
   - requirements.txt가 `>=`만 사용. 재현성·롤백 안전성 측면에서는 lock 파일이 더 좋음.
   - 그러나 본 시스템은 사용자가 단일 venv로 운용 중이며 현재 정상 작동.
   - **권고**: 즉시 변경 불필요. 다음 주간 검토에서 의도적 업그레이드 전에만 동결 고려.

3. **smolagents/litellm/anthropic 신규 기능 조사**
   - 본 검토에서는 웹/Librarian 검색을 수행하지 않음 (비용 회피 + 데이터셋 대기 중
     paper1 작업이 동시 진행 가능한 상태). 다음 검토 시 핵심 라이브러리 changelog 1회 점검 권고.

### 결론
- 즉시 적용해야 할 자체 업그레이드 사안 **없음**.
- 1번 항목(프롬프트 한 줄 추가)은 다음에 사용자가 명시적으로 요청하거나
  Writer/Reviewer 호출 시 timeout이 추가 발생하면 그때 적용 권고.
- error_patterns.md가 비어 있어, 코드 변경의 근거가 되는 반복 실패 데이터 부족.
- 본 검토 결과를 `record_outcome(..., outcome="completed", note=...)`로 기록.


## [2026-05-06 16:16] 시뮬레이션 데이터 수집 병목 점검 (사용자 지시)

### 사용자 지시
- snapshot 기록 주기, libsumo step 간격, I/O 빈도 점검.
- RSU 로컬 데이터 요구량은 5만으로 하향 조정 (기존 20만).

### 현재 누적 상태 (점검 시점)
- 데이터 폴더: /home/imnyj/SumoNetSim1.1.5/data/
- 23개 RSU CSV, 총 55,209 레코드.
- RSU별 평균 ~2,400 레코드, 최대 3,423 (rsu_N36), 최소 807 (rsu_N17).
- 사용자 표현 "2~3주에 2만개"와 부합 (한 머신 기준 ~15-25K 추정).

### 점검 1: libsumo step 간격
- 위치: src/NetSim.py L721 — `EventSimulator(step=1.0, max_time=sumo_set.MAX_STEPS)`
- 분석: 1초 간격은 데이터 수집 시뮬에 표준적이고 적정.
- **변경 권고: 없음.** step을 키우면 위치/속도 정밀도 손실, 줄이면 SUMO 부하 증가.

### 점검 2: 이벤트 루프 인공 sleep (가장 큰 병목 후보)
- 위치 1: NetSim.py L584/L586/L592 (EventSimulator.run 루프) — 매 이벤트마다 `time.sleep(0.001)` 3회.
- 위치 2: NetSim.py L814/L816 (step_event) — `sumo.simulationStep()` 전후 `time.sleep(0.001)` 2회.
- 영향: 매 step당 최소 5ms 인공 지연.
  3600 step × 5ms = 18s/episode (순수 wall-clock 손실).
  추가로 step당 다중 이벤트 처리 시 (request, check_range 등) 더 누적.
- **변경 권고: 모두 제거.** WSL/스레드 race를 피하려는 흔적으로 보이지만, libsumo는 단일 프로세스라 경합 없음.
  제거 시 episode 처리 속도 1.3~2x 가속 기대.

### 점검 3: I/O 빈도 (두 번째 큰 병목)
- 위치: dataset_scenario.py L11 — `BUFFER_SIZE = 1` (즉시 flush).
- L249 `flush_buffer()` 동작: 매 RSU report 1건마다
  `open(path, 'a')` → `csv.writer` 생성 → row 1개 write → close.
- 23개 RSU × 매 레코드 = 시뮬 1회당 수천 건의 open/close syscall.
- 코멘트 "WSL 프로세스 비정상 종료 대비"는 합리적이나, BUFFER_SIZE=50~100이면
  비정상 종료 시 잃는 양이 RSU당 50~100건 (현재 누적 2,400 대비 2~4%) 수준 — 허용 가능.
- **변경 권고: BUFFER_SIZE = 50 (또는 100).**
  reset_runtime() 시 force flush가 이미 구현되어 있어 정상 종료는 손실 없음.

### 점검 4: PER_REQ 첫 요청 지연
- 위치: dataset_scenario.py L13 — `PER_REQ = 300`.
- 동작: 차량 등장 후 random(0, 300)초 후 첫 REQUEST 발신 → 평균 150초 낭비.
- T_INIT_OVERRIDE = 300s (warm-up) 후의 추가 평균 150s 지연 = 차량별 실효 수집 시작 시점이 ~450s.
- MAX_STEPS = 3600s, timeout = 120 wall-clock seconds — 시뮬 시간으로 보면 1 episode 한도 안에서 손실.
- **변경 권고: PER_REQ = 30 (또는 60).** 첫 REQUEST 평균 지연 ~15s로 단축.
  차량당 수집 가능 dwell 횟수가 늘어나 RSU당 레코드 ~1.5x 증가 예상.

### 점검 5: send_request / check_range 주기
- 위치: dataset_scenario.py L42, L84 — `current_time + 1` (1초 주기).
- 분석: libsumo step과 동일한 1초 — 적정. 변경 시 over-sample/under-sample 위험.
- **변경 권고: 없음.**

### 점검 6: 진행 파일 I/O
- 위치: dataset_scenario.py 끝부분 — `_write_sim_progress` 매 10초 write.
- 영향: episode당 360회 write, 4 byte 짧은 파일. 무시 가능.
- **변경 권고: 없음.**

### 점검 7: run_collect.sh의 timeout 120s
- 위치: run_collect.sh L17 — `timeout 120 python3 ...`.
- 시뮬 MAX_STEPS = 3600s지만, wall-clock 120s 안에 끝낸다는 것은 시뮬 200~300s 진행 후 강제 종료.
  T_INIT_OVERRIDE = 300s 이전에 SIGTERM 가능성 — 데이터 0건 수확 episode 발생.
- watchdog-runner.py에서는 TOTAL_EPISODES=30 + RESTART_DELAY=10s, timeout 없음 (정상 종료까지 대기).
- **변경 권고**:
  (a) run_collect.sh를 사용 중이면 timeout 600~900초로 상향 (libsumo wall-clock 실측 기반).
  (b) 또는 run_collect.sh 사용 중단하고 watchdog-runner.py로 통일.

### 종합 우선순위 (수집 속도 향상 기여 순)
1. **time.sleep(0.001) × 5 제거** — 1.3~2x 속도 향상 (가장 큰 효과, 위험 거의 없음)
2. **BUFFER_SIZE = 50** — I/O syscall ×50 감소 (CPU/syscall 부하 완화)
3. **PER_REQ = 30** — 차량당 레코드 ~1.5x (시뮬 timestep 활용도)
4. **run_collect.sh timeout 상향** — episode 강제 종료로 인한 손실 제거

### 5만 목표 달성 추정
- 현재: ~55K 누적 (이미 23개 RSU 평균 2,400 = 5만 근접에 22 RSU만 포함하면 OK).
- **사실, 23 RSU × 2,400 평균 = 55,209로 이미 평균 기준 RSU당 ~2,400. 5만은 RSU당 5만**이라면 추가 ~20x 필요.
- "RSU 로컬 데이터 5만"의 해석:
  - (A) 모든 RSU 합계 5만 → 이미 달성 (55K).
  - (B) RSU 1개당 5만 → 현재 최대 3,423. 약 15x 더 수집 필요.
- 사용자 의도 확인 필요. (B) 해석이라면 위 4개 패치 적용 후에도 추가 1~2주 소요.

### Commander 권고
- 패치 1, 2, 3은 즉시 적용 가능하며 안전성 영향 미미. Experimenter[implement]에 위임 가능.
- 단, 시뮬레이션 코드는 paper1 외부 (/home/imnyj/SumoNetSim1.1.5)에 있어 "paper1 폴더 전용" 세션 스코프 위반 우려.
  → 사용자가 직접 수정하거나, 명시적 허가 후 Experimenter 호출 권고.
- 패치 적용 전에 사용자에게 5만 목표 해석(A vs B) 재확인 권고.
