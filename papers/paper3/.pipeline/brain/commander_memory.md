# Commander Memory

(첫 작업 수행 시 자동으로 채워집니다)


## [2026-04-28] 주간 자체 업그레이드 검토 — NO-CHANGE 결정

**입력 트리거**: 부팅 시스템 알림 (사용자 'y' 동의, 마지막 검토로부터 N일 경과)

**수행 절차 요약**
1. pipeline_state, user_directives, agent_notes, validation_history, error_patterns 점검
2. commander.py 전체 (31KB) 코드 리뷰
3. requirements.txt 의존성 floor 검토
4. 변경 불필요 판정 → agent_notes.md에 결과 기록

**결정 근거**
- 운영 결함 데이터(validation_history, error_patterns) 모두 비어있음
- requirements.txt floor 버전이 합리적 (anthropic 0.40+, litellm 1.50+, smolagents 1.0+)
- 코드 흐름 일관성 OK, deprecation 사용 부재
- Librarian을 통한 외부 웹 검색은 ROI 낮음 (관찰된 결함이 0건이므로)

**학습된 패턴 (향후 사용자 선호도 추론)**
- 시스템이 막 부팅된 직후의 weekly review는 보통 NO-CHANGE가 합리적.
- 다음 사이클부터 운영 데이터(검증 실패율 등)가 누적되면 검토 가치가 상승.


## [2026-04-29] SumoNetSim1.1.6 코드베이스 분석 — Dataset 수집 & Precaching 디자인 파악

**트리거**: 사용자 지시 (2026-04-29 08:57) — "SumoNetSim1.1.6을 읽고 ML Dataset 추출 방식과 Precaching 디자인을 정리해서 보고하고 수정 사항 알려줘"

**조사 대상 파일**
- `dataset_scenario.py` (26KB): ML 학습용 dataset 수집 시뮬레이션 (현재 운용 중)
- `7. V2I Precaching.py` (8.8KB): RSU→다음 RSU로 LET 메시지 보내 단순 V2I precaching
- `8. V2V Precaching.py` (19.6KB): RSU 통신 영역 내 차량들에 PRECACHE 후 outage zone에서 V2V 전달
- `src/NetSim.py` (49KB): EventSimulator + Node 베이스 + RSU grid 자동 구성
- `src/sumo/make_sumo_set.py`: SUMO 네트워크/플로우 자동 생성 (RSU 배치 핵심 파일)
- `src/sumo/generated.nod.xml`: 현재 5×5 RSU(traffic_light) + 외곽 dead_end 노드 좌표

**현재 시뮬레이션 토폴로지 (코드에서 추출한 사실)**
- RSU = traffic_light 노드, 5×5 격자 (총 25개)
- RSU 좌표: x,y ∈ {1200, 3600, 6000, 8400, 10800} → 인접 RSU 간격 **2400m**
- `make_sumo_set.py`: `RSU_RANGE=800, OUTAGE_ZONE=800, EDGE_LENGTH = 2*RSU_RANGE + OUTAGE_ZONE = 2400`
- RSU `comm_range=800.0` (dataset/V2I/V2V RSUNode 모두), 차량 `comm_range=200.0`
- 외곽 dead_end가 차량 진입/퇴장 TAZ 역할 → flow probability `P_GEN`로 차량 생성
- `NUM_BLOCKS=6` → +1 후 코너 4개 빼서 5×5 traffic_light 구성

**Dataset 수집 메커니즘 (`dataset_scenario.py`)**
- 차량은 매 1s 마다 REQUEST 송신 → 가장 가까운 RSU 1개에서 ACK 수신 시 cur_rsu 설정
- RSU `handle_request`: 차량 route 상에 next RSU가 있고, 그 next RSU의 N/W/S 이웃이 모두 존재(외곽 RSU 배제)할 때만 record 등록
- check_range로 cur_rsu 범위 이탈 감지 → REPORT(prev_rsu, dwell_time, next_entry_time, exit_time) 송신 → 이전 RSU의 buffer에 (features+targets) 1행 append → CSV flush
- 기록되는 features (~22개): r_cov, dirct, d_rsu, d_e_n, n_t_0~3, d_l_c, d_l_n, v_c_a, v_n_a, tls_c/tls_n, tlt_c/tlt_n, n_cur, n_nxt, v_ahead_avg, dist_leader/v_leader, est_travel_time, route_lane_changes, q_len_cur/q_len_nxt, n_ahead_cur/n_ahead_nxt, n_merge_nxt, occ_cur/occ_nxt
- targets: dwell_cur (현 RSU 체류시간), dwell_nxt (다음 RSU 체류시간) → CSV `data/rsu_NXX.csv`

**Precaching 디자인 (7번/8번)**
- 7. V2I: 차량 REQUEST 받은 RSU가 즉시 ACK + (cache hit→DATA / miss→server REQUEST) + next RSU에 PRECACHE(LET) 메시지. next RSU는 캐시 없으면 server에 PRECACHE(REQUEST) → server가 PRECACHE(DATA) 응답하면 캐시 저장.
- 8. V2V: RSU가 요청 차량 처리 후 `VehicleSelection`으로 같은 RSU 범위 내 + 같은 next RSU를 갖는 다른 차량들에 PRECACHE 송신. 차량은 캐시 보유 후 outage zone(어느 RSU 범위에도 안 잡힘)에서 target 차량(req_veh_id)에게 V2V로 ACK+DATA 능동 전달. handle_request로 same-next-RSU 요청 차량 응답도 가능.

**사용자 새 요구 vs 현재 코드 차이**
| 항목 | 현재 코드 | 사용자 요구 | 수정 필요 |
|---|---|---|---|
| RSU 배치 | 5×5 | 5×5 | ✅ 그대로 |
| 통신범위 | 800m | 80m | ⚠️ `RSU_RANGE=80`, 모든 RSUNode comm_range=80, VehicleNode comm_range도 ≤80 권장 |
| 음영(outage) | 800m | 800m | ✅ `OUTAGE_ZONE=800` 유지 |
| 인접 RSU 간격 | 2400m | 960m (=2*80+800) | 자동 재계산됨 (위 2개만 바꾸면) |
| 차량 수 | P_GEN, DENSITY로 조절 | "엄청 많이" | DENSITY↑ 또는 P_GEN 직접 상향 |

**수정해야 할 파일 (주요)**
1. `src/sumo/make_sumo_set.py`: `RSU_RANGE = 80.0` (현재 800), DENSITY 상향 검토
2. `dataset_scenario.py` `RSUNode.__init__`: `comm_range=80.0` (현재 800)
3. `7. V2I Precaching.py`, `8. V2V Precaching.py`: 동일하게 RSU comm_range=80
4. VehicleNode.comm_range: 현재 200 → 80 이하로 (V2V 시 max(self,dst)로 동작하므로 의미 일치 위해 80 권장)
5. `make_sumo_set.py`의 외곽 dead_end가 step/2만큼 안쪽에 위치 — 통신반경 축소 시 차량이 외곽에서 첫 RSU 잡기 전 거리가 짧아져 워밍업 시간 영향 있음. `T_INIT_OVERRIDE=300` 그대로 둘지 재검토 필요.
6. NetSim 내부 일부 매크로/계산식이 RSU comm_range=800 가정하지 않는지 grep 추가 필요 (특히 GetAvgSpeed의 dwell→speed 환산 부분: `2*comm_range/dwell` 사용 — 이건 자동 스케일됨)

**다음 행동 제안**
- 사용자에게 위 정리를 한국어로 보고
- 사용자 승인 후 Experimenter[Stage 1 design]에게 명세 정리 위임 가능


## [2026-04-29 09:15] ML 배제 후속 논문 회의 — Idea 안 1 추천 받음

**사용자 신규 지시 (요약)**
- RSU 통신범위: 800m 유지 (이전 80m 분석 정정)
- Density: 1~20 sweep, default 5 또는 10
- ML 완전 배제 → dataset 수집 불필요, heuristic/ILP 노선
- 타겟: IEEE Internet of Things Journal

**Idea 회의 결과**
3안 도출 → 안 1 (Outage-Aware ILP Precaching Vehicle Selection) 추천.
출발점: Nam2023b(Set Ranking) + Youn2026(V2V relay), 8번 코드 90% 재사용.
Formulation: x_{v,c} 이진 + f_{v,c} 정수 변수 + LET 제약.
NP-hardness: Weighted Maximum Coverage 귀납 증명.
대규모: LET x popularity 그리디 휴리스틱.
실험: 시나리오 A(density 1~5 ILP) + B(6~20 Greedy).
지표 5개: CHR, CDSR, PCO, RLBI, VOR.
베이스라인 6개: Proposed-ILP, Proposed-Greedy, Nam2023b, V2V-Base(8), V2I-Base(7), Random-K.

**Commander 다음 행동**
1. 사용자에게 안 1/2/3 중 1개 컨펌 요청 (안 1 우선 추천)
2. 컨펌 후 → Idea에게 idea_spec.md 작성 의뢰
3. → Experimenter[Stage 1: design]에게 experiment_spec.json 작성 의뢰
4. → Experimenter[Stage 2: implement]에게 9. ILP_Precaching.py 작성 + libsumo 실행 의뢰

**학습된 사용자 선호 (implicit)**
- "빠른 후속 논문" = 시뮬레이터 70%+ 재사용, dataset 수집 미포함, 명확한 formulation
- ML/RL/DL/Digital Twin 키워드 회피
- ILP + heuristic + 증명의 OR 형식 선호

## [2026-04-29] Stage 2 진행 결정 + Qwen 활용 정책
- 사용자가 Stage 2 (implement) 진행을 컨펌.
- 동시에 가벼운 작업은 전적으로 Qwen에 위임하라는 지시 추가.
- Stage 2는 시뮬레이션 코드 작성·실행이므로 Experimenter[implement]에 위임 (Qwen 부적합).
- 향후 단순 요약/분류/포맷 변환 작업은 Qwen 우선 호출.


## [2026-04-29] Round 3 세션 — 사용자 지시 정리

### 사용자 지시 (Prompt.md)
1. analytical CSV 폐기 + paper/data/A_*.csv 6개 삭제 (B안 채택)
2. arXiv 검색 금지, 환각 의심 references 제거, 2025-2026 신규 논문 보강
3. librarian_memory.md 재정리
4. idea 재검증 → 부적합 시 수정, 통과 시 Experimenter Stage 2 진행
5. 시뮬레이션은 사용자가 직접 실행 → 실행 명령어만 제공할 것

### Commander 처리 결과
- ✅ paper/data/A_*.csv 6개 삭제 완료
- ✅ agent_notes.md, user_directives.md 에 지시사항 기록
- ✅ pipeline_state.json::experimenter.stages_done 에서 implement 제거
- ⚠ Librarian Round 3: 환각 검증 통과(0건). API 429 로 신규 검색 0건. Round 4 (24h 후) 필요.
- ✅ Idea Round 3: CONDITIONAL PASS. M1~M4 소수정 idea_spec.md v1.1 반영.
- ✅ Experimenter (Commander 직접 검수): RUN_COMMANDS.md + CODE_REVIEW.md 작성.

### 사용자에게 보고할 핵심
1. **시뮬레이션 실행 명령어**: `python code/run_scenario.py --scenario {A|B|C|D|E} --output_dir data`
2. **결정 필요 사항**: 현재 sim_core.py 가 libsumo 미사용 abstract simulator. 그대로 실행할지 (옵션 P), libsumo 기반으로 교체할지 (옵션 R) 결정 필요.
3. **Librarian Round 4**: API rate-limit 해소 후 (24+ 시간) 재시도 필요. 현재는 21개 self-cited references 만 있는 상태로, 외부 references (Bertsimas-Sim 2004, Kaul 2012 AoI 등) 보강 시급.
4. **다음 액션**: 사용자가 시나리오 A~E 실행 완료 후 Commander 호출 → Reviewer Validator 모드.

### 학습된 패턴
- Sub-agent 호출 시 30초 sandbox timeout 발생 → 단일 호출에 검수+생성 모두 시키지 말고 분할.
- Commander 가 직접 file_read 로 코드 본문을 부분적으로 확인하면 sub-agent 의존을 피할 수 있음.


## [2026-04-30] 세션 작업 범위 확정
- 사용자가 paper1, paper2는 다른 세션에서 병행 진행 중임을 알림
- 본 Commander 세션은 paper3 전담
- 향후 모든 작업은 `/home/imnyj/papers/paper3/` 내부에서만 수행
- 다른 paper 디렉토리는 읽기조차 자제 (동시 편집 충돌 방지)
- 사용자가 명시적으로 paper1/paper2 참조를 요청할 때만 예외 적용


## [2026-05-06] 사후 분석 — “3일 동안 결과 없음” 사건

**사용자 보고 (2026-05-06 10:31, 10:39)**:
- 시뮬레이션이 3일 지나도 `paper/data/` 에 결과 파일이 없음.
- 코드/명령어 재검토 후 RUN_COMMANDS.md 수정 요청.

**Commander 직접 진단 (sub-agent 호출 없이 file_read 로 본문 확인)**:

1. **`python` 명령어가 사용자 환경에 없음 (Ubuntu 22.04+ 기본)**
   - `paper/experiment/data/run_B.log..run_E.log` (각 125B) 가 모두
     `Command 'python' not found, did you mean: command 'python3'` 로 시작.
   - Round 4 RUN_COMMANDS.md 의 일괄 실행 루프 `for S in A B C D E; do python ...` 가
     첫 줄에서 즉시 실패 → B,C,D,E 는 단 한 번도 시뮬을 시작하지 못함.
   - 시나리오 A 가 `paper/experiment/data/A_*.csv` 로 남아 있던 것은 Round 3
     CIoVSimFast(abstract random walk) 잔재. seeds=[42,43,44] 3개로 1922 row 만 있어
     Round 4 의 10-seed 명세와 불일치. 사용자가 폐기 지시한 데이터 재발견.

2. **`run_scenario.py` 가 시나리오 끝에서야 CSV 를 1회 저장**
   - 한 시나리오 (A: 6,400 runs × 약 60s+) 가 다 끝나야 첫 파일 생성.
   - 사용자는 중간에 “파일이 없음 → 망가짐” 으로 오해.

3. **RILP 가 매 vehicle / 매 scheduling window 마다 PuLP/CBC ILP 호출**
   - catalog=100, cap=10, 단일 cardinality constraint → 정렬과 동일한 최적해.
   - solver overhead 때문에 한 run 이 수십 분 걸리는 경우 발생 가능.

4. **stdout 버퍼링** — `python -u` 미사용, `print(..., flush=True)` 미사용 →
   `tee`/`nohup` 환경에서 진행 로그가 거의 출력되지 않음.

**Commander 처리 (직접 수행)**:
- `paper/experiment/data/A_*.csv` + `run_*.log` 잔재 11개 → `_history/round3_stale_data/` 로 격리.
- `algorithms.py::rilp_decision` 패치 — PuLP 호출 제거, 정렬 기반 (수학적 동치).
- `run_scenario.py` 전면 재작성 — 매 run fsync, line-buffered, resume 가능, ETA 표시.
- `RUN_COMMANDS.md` Round 5 갱신 — `python3 -u` 강제, smoke-test 절차, 진행 모니터링 명령, 백그라운드 + nohup 안내.

**학습된 패턴**:
- 사용자 환경에 `python` 심볼릭 링크가 없을 수 있음 (Ubuntu 22.04+).
  앞으로 모든 실행 명령은 `python3` 로 표기. (user_preferences.md 에 추가)
- 장시간 실행 스크립트는 **반드시** incremental write + flush=True + resume 가능해야 함.
  사용자가 “결과가 안 나옴” 이라고 신고하기 전에 우리가 먼저 제공해야 할 기본 기능.
- Commander 가 sub-agent 호출이 부담스러울 때 `file_read` 로 코드 본문을 직접 확인하는 패턴이
  본 사건에서도 30초 timeout 회피에 효과적이었음 (이전에 학습한 패턴 재확인).


## [2026-05-06 13:32] 사용자 요청 — "복붙 안되니 파일로 전달해줘"

**사용자 지시**:
- "너가 준 정보에 대해서 복붙이 안되니깐 파일로 전달해줘. 예륻 들면, RUN_COMMANDS.md를 수정한다던지 말이야."

**해석**:
- 13:27 응답에서 채팅 본문에 명령어를 길게 적었지만 사용자가 복사·붙여넣기 어려움.
- 앞으로 모든 실행 명령은 채팅 본문이 아니라 **파일에 직접 작성**해서 전달해야 함.

**처리 (Commander 직접)**:
1. `paper/experiment/quickstart.sh` 새로 작성 — 한 키워드(check/smoke/A~E/all/status/tail/stop)만 인자로 주면 RUN_COMMANDS.md 의 모든 명령을 자동 실행하는 래퍼.
2. `paper/experiment/RUN_COMMANDS.md` 맨 위에 §0 "TL;DR" 섹션 추가 — 사용자가 §0 만 봐도 quickstart.sh 의 호출법을 즉시 파악 가능.
3. 기존 §0 (변경 요약) → §0a 로 리네임. 본문 §1~§9 는 그대로 보존.

**학습된 패턴 (user_preferences.md 갱신 필요)**:
- 사용자는 채팅 본문에 적힌 코드/명령을 복사하기 어려운 환경(터미널/GUI 미지원, 또는 텍스트 선택 불가) 사용 중.
- 앞으로 모든 명령·코드 산출물은 다음 우선순위로 전달:
  ① 가능하면 새 파일에 작성 (quickstart.sh 같은 1-키워드 래퍼)
  ② 기존 파일을 직접 수정 (RUN_COMMANDS.md 등)
  ③ 채팅 본문은 "이 파일에 적었으니 cat <파일> 해서 보세요" 정도의 안내문만.
- 명령은 한 번에 하나씩 줄 단위로 실행 가능하게, 다중행 heredoc 가능하면 스크립트로 감싸기.



## [2026-05-06 추가] 사용자: "smoke 조차 너무 오래 걸린다" — 코드 재분석

**진단 (Commander 직접, sub-agent 호출 없이 file_read 로 본문 확인)**

1. **smoke = 본 실험 1 run** (둘 다 duration=1800, warmup=300). smoke 의 정의 자체가 잘못됨.
2. **SUMO 부하 큼**: SumoNetSim1.1.6/generated.rou.xml 에 380 flow × prob 0.022
   → 매 초 ~8.4 vehicle 출발, 1800 step 동안 누적 ~15,000 출발, 동시 활성 N=수백~수천.
3. **sim_core.py O(N²)**: per-vehicle request 처리에서 매번 `_vehicles_near_rsu`
   가 self._veh_state 전체를 선형 검색 → step 당 O(N²). N=2000 이면 step 당 4M 거리계산,
   1500 metric step 으로 6×10⁹ → 수십 분~수 시간 가능.

**적용한 패치**

1. `paper/experiment/quickstart.sh`:
   - `tiny` 명령 신설 — duration=30, warmup=5 (SUMO 부팅 + import 만 검증, 5~30초 목표)
   - `quick` 명령 신설 — duration=180, warmup=30 (가벼운 동작 검증, 15초~2분 목표)
   - `smoke` 는 그대로 두되 "본 실험 1 run" 임을 안내 문구로 명시
2. `paper/experiment/code/sim_core.py`:
   - 매 step 시작 시 RSU 별 vehicle bucket 한 번 구축 (O(N))
   - per-vehicle request 처리에서 `_nearest_rsu` + `_vehicles_near_rsu` 호출 제거
   - 대신 사전 계산된 `rsu_buckets[v["_nearest_rsu"]]` 조회 (O(1) lookup, O(k) scan)
   - 결과: step 당 O(N²) → O(N · n_rsu + N) = O(N) (n_rsu=25 상수)
   - 알고리즘 결과는 동일 (의미 동일한 룩업, 단지 캐시 활용).
3. `paper/experiment/SMOKE_DIAGNOSIS.md` 작성 — 사용자에게 진단 보고서.

**사용자가 다음에 할 일 (권장 순서)**
1. `bash quickstart.sh tiny` — 5~30초 안에 끝나야 정상.
2. PASS 시 → `bash quickstart.sh quick` — 15초~2분 내 끝나야 정상.
3. PASS 시 → 본 실험 1 run 의 walltime 측정 (smoke 또는 quickstart.sh A 후 첫 row 시간).
4. 1 run 이 아직 5분 이상이면 처방 C (SUMO trajectory 사전생성·캐시) 검토 필요.

**학습된 패턴 (user_preferences.md 갱신 권장)**
- "X 가 너무 오래 걸린다" 보고가 들어오면, 먼저 X 와 본 실험의 부하가 동일한지 확인.
  smoke = 본 실험 인 경우가 많으며 사용자는 smoke 를 가벼운 검증으로 기대함.
- sub-agent 호출 없이 `file_read` 로 코드 본문 + .rou.xml 같은 보조 파일까지 직접 보면
  병목 원인을 정량적으로 짚을 수 있음. 본 사건에서도 30초 timeout 회피.
