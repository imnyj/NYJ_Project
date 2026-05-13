# User Directives


## [2026-05-08 11:30]
AIMS MATH에 제출할 AI 기술이 들어간 차량 네트워크 분야 논문을 작성하려고 하는데, 이왕이면 2Layer 분야면 좋겠어. 나는 주로 프로토콜 관련한 연구를 하던 사람이야. 최신 논문 2024, 2025, 2026년 논문을 찾아서 정리하면서 아이디어를 추려보자. 참고로 검색은 1초에 1편씩 하는 것이 안전하니깐 librarian 에이전트를 부릴 때는 그 점을 유의해줘. 그리고 참고로 현재 진행 중인 다른 AI 논문들의 시뮬레이션이 기본적으로 3달 이상이 걸릴 느낌이라 이번에는 좀 짧게 걸릴 경량화 모델 중심으로 연구하는 것이 좋아보여.

## [2026-05-08 11:36]
작업을 이어서 해주겠어?

## [2026-05-08 11:53]
내가 사용할 수 있는 것은 libsumo이며 가지고 있는 시뮬레이터는 직접 만든 SumoNetSim 밖에 없어. 이 시뮬레이터 혹은 별도로 너가 정밀한 시뮬레이터를 만들 수 있다면 그것으로 구현할 수 있는 방안에 대해서 또한 비교 방안에 대해서 연구를 진행하고 싶어. 일단 목표를 IEEE IoT J.이라고 생각하고, 글을 작해 나가보자. 아이디어부터 잡아봐. 하위 에이전트들과의 회의를 통해서 말이야. 또한, 매번 아이디어를 잡을 때 librarian에게 해당 아이디어가 아직 없는 아이디어인지 확인하고, idea에게 타당성이나 contribution등을 검토하도록 하자.

## [2026-05-08 12:39]
1) 확인. 그 이상의 검토는 시뮬레이션 결과로 확인하겠음. 2) Simplified Adaptive로 단순화 할 것. 3) sensitivity analysis를 통해 적절한 값을 찾고, analysis 결과를 저장하여 나중에 논문에서 사용할 수있도록 할 것.

## [2026-05-08 12:51]
실행

## [2026-05-08 13:25]
워크플로우를 짜도록 하여 작은 부분으로 쪼개어 구현하도록 해. 한 번에 많은 작업을 수행시키면 오류가 더 많을 거야. 그리고, SUMO에 대한 시나리오는 SumoNetSim1.1.6을 참고하도록 해. RSU의 통신범위, RSU 간의 거리, 차량의 밀도 등이 있을 거야.

## [2026-05-08 13:37]
a안 진행. 시뮬레이션을 구현할때는 큰 틀을 짜고 내부의 틀에서 또 작은 틀을 짜고, 그 안에서 또 세분화하여 일을 나눔으로서 Coder가 작은 부분부분을 구현하도록 만들어 환각 등의 문제 발생 확률을 낮추도록 해.

## [2026-05-08 13:46]
그대로 진행하는데, 완료된 명령어들은 어디에 따로 정리해둬. 내가 직접 돌릴 거야. 이왕이면 md 파일로 저장해주면 좋겠어. 내가 돌리기 좋게 말이야.

## [2026-05-08 21:39]
C에서 0.6 세 개 나왔어.

## [2026-05-08 21:49]
아직 모두 0.6이야.

## [2026-05-08 21:51]
시뮬레이션을 구현해주는데, 오래 걸릴 거만 내가 직접 돌리도록 명령어를 제공해줘. 테스트 등의 작업은 experimenter에게 위임할게.

## [2026-05-08 22:04]
7개의 cbr_target이 다 같은 값을 가졌어. 명령 7.

## [2026-05-08 22:04]
7개의 cbr_target이 다 같은 값을 가졌어. 명령 7.
→ Commander 진단: 명령 6(L1-B-2 패치)을 건너뛴 채 명령 7만 실행됨.
   SA3_results.csv 21 row 직접 검사 결과 21:54 가설 (sim_engine.generate_routes line 244 depart 분포 + <trip> 자동 소멸) 확증.
   L1-B-2 패치 (Experimenter 위임) 후 명령 6 → 7 재실행 필요. 사용자 컨펌 대기.

## [2026-05-08 22:09]
C로 진행. 짧은 테스트들은 Experimenter가 검증하고, 시뮬레이션으로 결과를 뽑아야 할 때만 사용자에게 돌릴 명령어를 알려주길 바


## [2026-05-08T22:09:33] 사용자 지시 — 테스트 구분 정책
- 원문: "C로 진행. 짧은 테스트들은 Experimenter가 검증하고, 시뮬레이션으로 결과를 뽑아야 할 때만 사용자에게 돌릴 명령어를 알려주길 바"
- 해석:
  1) 진행(Continue) — 현재 L1-A 진단 후속 작업 그대로 진행.
  2) 짧은 테스트(unit test, smoke test, syntax check, import check, 작은 함수 sanity check 등)는
     Experimenter가 직접 실행하여 검증.
  3) 본격 시뮬레이션(긴 시간 소요 / GUI / SUMO full run / sweep 등)만 RUNBOOK.md에 명령어를 기록하고
     사용자에게 직접 실행을 요청.
- 적용 규칙:
  · L1-A-3 같은 단순 import/구문 smoke test → Experimenter가 직접 수행 (사용자 위임 X)
  · Phase 2-alpha sensitivity sweep, Phase 2 main run 등 → RUNBOOK.md 등록 후 사용자 실행
  · 경계가 모호하면 Experimenter가 30초 이내 끝날지로 판단. 30초↑면 사용자에게.

## [2026-05-08 22:33]
명령 6 결과: runtime_sec 1보다 작음. n_cam_events 700보다 큼. CBR_mean 0.02보다 작음.

## [2026-05-08 22:37]
libsumo는 SumoNetSim/src/sumo 안의 내용을 참고하도록 해. 그 파일들을 그대로 불러와도 좋아.

## [2026-05-08 22:38] 지시 구체화: SUMO 자산 위치
사용자 지시: "libsumo는 SumoNetSim/src/sumo 안의 내용을 참고하도록 해. 그 파일들을 그대로 불러와도 좋아."

확인된 절대 경로:
  /home/imnyj/SumoNetSim1.1.5/src/sumo/

해당 폴더의 파일 목록 (그대로 사용 허가):
  - generated.sumocfg     (SUMO 시뮬레이션 설정 — 진입점)
  - generated.net.xml     (291.7KB, 도로 네트워크)
  - generated.rou.xml     (49.4KB, 차량 라우팅)
  - generated.edg.xml     (엣지 정의)
  - generated.nod.xml     (노드 정의)
  - generated.add.xml     (추가 인프라)
  - rsu.poi.xml           (RSU POI 정의)
  - make_sumo_set.py      (생성 스크립트, 참고용)

운영 규칙:
  · Experimenter[implement] 단계에서 libsumo로 SUMO를 띄울 때 위 폴더의
    generated.sumocfg를 그대로 진입점으로 사용. 새로 .net/.rou를 생성하지 말 것.
  · 별도 사본 생성 없이 위 절대 경로를 직접 참조하는 것을 허용.
  · 사본이 필요하면 paper4/sim/sumo_networks/ 아래로 복사 가능 (원본 수정 금지).

## [2026-05-08 22:40]
해당 libsumo 관련 파일들을 활용하여 시뮬레이을 구현 및 실행하도록 해.


## [2026-05-08 22:41] 사용자 지시 — libsumo 시뮬레이션 구현 및 실행
"해당 libsumo 관련 파일들을 활용하여 시뮬레이션을 구현 및 실행하도록 해."

해석:
- "해당 libsumo 관련 파일들" = 22:38에 고정된 SumoNetSim1.1.5 자산
  (/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg + generated.{net,rou,add}.xml + rsu.poi.xml)
- "구현" = sim/sim_engine.py를 위 자산을 직접 사용하도록 리팩터
  (자체 generate_routes/generate_urban_grid_net 로직 비활성화, libsumo.start([..., "-c", SUMOCFG, ...]) 사용)
- "실행" = 패치 후 smoke test 1회 (소량/짧은 duration)로 정상 동작 확인

워크플로우 분할 (R1~R8):
- L1-B-2-extended를 폐기 (자체 routes 생성 자체를 폐기하므로 무관해짐)
- 신규 leaf L1-B-3: Experimenter[implement] — sim_engine.py 패치 (1 파일 1 책임)
- 패치 직후 [SELF-RUN] smoke test (≤30s): 정상 신호 확인
- 정상 시 사용자에게 보고 후 다음 leaf (Reviewer[validator] 또는 Phase 2-alpha 일부 sweep) 진행

## [2026-05-08 22:52]
ABC 순서로 진행

## [2026-05-08 23:04]
runtime_sec=1.5, n_cam_event=13885, CBR_mean=0.3795, AoI_mean=323.252라서 C 시작함.


## [2026-05-08T23:04] 사용자 보고 — ABC-B 결과 + ABC-C 자발적 시작
- 원문: "runtime_sec=1.5, n_cam_event=13885, CBR_mean=0.3795, AoI_mean=323.252라서 C 시작함."
- 해석:
  1) ABC-B (RUNBOOK 명령 2-redo, BL-A 20대 SimulationRunner full run) 결과 보고
  2) "C 시작함" → 사용자가 결과를 PASS로 판단하고 ABC-C (SA3 cbr_target sweep) 본인 환경에서 즉시 실행 시작
- Commander 처리:
  · ABC-B PASS 판정 기록 (commander_memory.md, RUNBOOK.md)
  · RUNBOOK ABC-B 체크박스 [x], 결과 표 기재
  · ABC-C 섹션에 "🔄 실행 중 [2026-05-08 23:04~]" 표시
  · pipeline_state.json: experimenter.note 갱신 (ABC-C in-flight)
  · 사용자가 ABC-C 결과 보고할 때까지 추가 호출 금지 (R7 정책 — 본격 시뮬 사용자 직접 실행)
- 비고: 사용자가 ABC-B의 "정상 임계 ≥5" 미달(runtime=1.5)에도 PASS 판단한 점은 user_preferences로 학습.

## [2026-05-11 11:13]
결과가 나왔어. 0.3: AoI=1616.0237 CBR=0.5403 PDR=100.0, 0.4: AoI=550.48 CBR=0.4982 PDR=100.0, 0.5: AoI=389.1563 CBR=0.5096 PDR=100.0, 0.55: AoI=380.0307 CBR=0.5104 PDR=100.0, 0.6: AoI=380.0307 CBR=0.5104 PDR=100.0, 0.65: AoI=377.167 CBR=0.512 PDR=100.0, 0.7: AoI=324.325 CBR=0.6019 PDR=100.0. 이제 뭐해?

## [2026-05-11 11:58]
D2. 1. 더 논문에 적합한 걸로 택. 2. 차량 수 기본값은 20. (밀도인 경우). 전체 대수의 경우 50이상. 3. RUNBOOK 명령으로 분해해서 사용자가 실행


## [2026-05-11T11:58] 사용자 지시 — D2 (Phase 2-main 4-way 비교) 확정 + 세부 정책

원문: "D2. 1. 더 논문에 적합한 걸로 택. 2. 차량 수 기본값은 20. (밀도인 경우). 전체 대수의 경우 50이상. 3. RUNBOOK 명령으로 분해해서 사용자가 실행"

해석:
1. D2 (Phase 2-main 4-way 비교) 확정. D1(추가 validator 검증) 건너뛰고 본 실험 진입.
2. 차량 수 표기 정책: 논문에 적합한 표기 방식을 Commander가 택할 것.
   - density(밀도) 표기 시 default = 20 veh/(km·lane) — idea_spec §5.2 / experiment_spec phase_2alpha와 일치, ETSI 문헌 표준 컨벤션
   - absolute(전체 대수) 표기 시 최소 50대 이상
3. Phase 2-main 실행을 RUNBOOK 명령으로 작은 단위로 분해. 사용자가 직접 순차 실행하고 결과 보고.

Commander 결정:
- 표기는 **density 기준** 채택 (논문 컨벤션 + idea_spec §5.2 일치). 다만 현재 SumoNetSim1.1.5 자산은 generated.rou.xml에 차량 풀이 고정 absolute count로 정의되어 있으므로, 실측 시 SimulationRunner의 평균 active vehicle 수를 함께 기록하고 14.4km 총 도로 길이 기준 환산 density를 부기.
- ABC-B 실측치 = 평균 88 vehicles / 14.4 km / 2 lanes ≈ 3.06 veh/(km·lane) — 매우 sparse. 그러나 CBR=0.38로 부하 충분 → 비교 실험은 의미 있음.
- highway scenario는 현재 sim_engine.py L1-B-3 패치에서 비활성화 상태 (SumoNetSim 자산은 urban_grid 그리드 1개). highway 추가는 별도 후속 leaf로 분리. 본 D2 1차 분해에는 urban_grid만 포함.
- Phase 2-main 1차 분해: 4 methods (BL-A/B/C/D) × urban_grid × 3 seeds = 12 runs를 method별 4개 명령으로 분해. 각 명령 ≈ 3 seeds × 1.5s wall-clock (ABC-B 실측 기준) → 매우 짧음. 단, duration_steps를 main 실험 기준(3600 step = 360s)으로 늘리면 명령당 약 5~15분.
- 후속 leaf 후보: (a) highway scenario 추가 (sim_engine 패치), (b) Proposed(TinyMLP-AI-DCC)와 ABL-1/ABL-2 추가, (c) density 가변 sweep.

## [2026-05-11 16:48]
D2-1 결과가 나왔어. 정상인지 하고 계속 실행해야 할 지 알려줘. [BL-A seed=42] 1778.8s :: {'runtime_sec': 1778.49, 'n_cam_events': 1676581, 'CBR_mean': 0.5064, 'AoI_mean': 389.571, 'PDR_mean': 100.0, 'energy_efficiency': 5.7343, 'ETSI_compliance': 100.0}

## [2026-05-11 16:48]
D2-1 결과 나왔어. 정상인지 확인하고 계속 나머지도 돌리면 되는지 알려줘. [BL-A seed=42] 1778.8s :: {'runtime_sec': 1778.49, 'n_cam_events': 1676581, 'CBR_mean': 0.5064, 'AoI_mean': 389.571, 'PDR_mean': 100.0, 'energy_efficiency': 5.7343, 'ETSI_compliance': 100.0}, [BL-A seed=123] 1831.9s :: {'runtime_sec': 1831.55, 'n_cam_events': 1690125, 'CBR_mean': 0.5066, 'AoI_mean': 393.959, 'PDR_mean': 100.0, 'energy_efficiency': 5.6752, 'ETSI_compliance': 100.0}, [BL-A seed=456] 1779.1s :: {'runtime_sec': 1778.76, 'n_cam_events': 1663373, 'CBR_mean': 0.5064, 'AoI_mean': 397.894, 'PDR mean': 100.0, 'energy_efficiency': 5.7102, 'ETSI_compliance': 100.0}

## [2026-05-12 09:40]
BL-C가 etsi_cam_layer.py에 구현되어 있는지 사전 확인 필요. 만약 KeyError 또는 NotImplementedError 발생 시 보고 → 별도 leaf로 BL-C 구현/패치. BL-C와 BL-D를 확인하고 해결한 뒤 문제가 없으면 그대로실행하도록 알려줄 것! 현재 BL-B까지 실행 완료!

## [2026-05-12 17:29]
Results.md에 결과를 넣어두었어. 시뮬레이션 결과를 배경으로 이제 작업을 진행해볼까?

## [2026-05-12T17:30]
Results.md에 결과를 넣어두었어. 시뮬레이션 결과를 배경으로 이제 작업을 진행해볼까?

**Commander 해석**: D2-1~D2-5 (BL-A/B/C/D × urban_grid × 3 seeds) 모두 완료.
main_combined_urban.csv 12 rows 정상 저장. seed CV<2%, 트레이드오프 명확.
사용자가 "이제 작업 진행" 신호를 보낸 것은 → 다음 leaf 결정 요청.
Proposed(TinyMLP-AI-DCC)가 핵심 기여인데 아직 미구현 상태 → E4가 가장 critical path.
다만 baselines만으로도 시각화/검증은 가능하므로 사용자에게 옵션 제시.

## [2026-05-12 17:35]
E4로 가자. 시각화나 검증은 나중에 해도 되고, 그 외의 논문에 들어갈 데이터들을 먼저 뽑자. 그러면서 논문도 진행해줬으면 좋겠어. 성능 평가라던가 그 부분은 완성되지 않았으니깐 작성할 수 있는 부분들만 말이야.

## [2026-05-12 17:52]
논문 작업을 이어서 계속 해줘.


## [2026-05-12T18:30]
"논문 작업을 이어서 계속 해줘." (17:52 지시 + 17:35 멀티-트랙 지시의 연속)

**Commander 해석:** 17:35의 두 트랙(E4 + 논문 작성) 중 환각 위험 낮고 즉시 산출 가능한
"논문 작성" 트랙을 우선 실행. E4는 다음 사용자 응답 후 RUNBOOK으로 분해.

**Applied in:**
- paper/draft/main.tex 신규 생성 — Writer 3 stage 분할 호출
  · Stage 1: skeleton+abstract+keywords+introduction+related_work
  · Stage 2: network_model+proposed_scheme
  · Stage 3: performance_evaluation(partial)+conclusion+bibliography
- pipeline_state.json writer.sections_done 10개, status=running
- 무결성 검증 자체 점검: 인용 키 누락 0, begin/end mismatch 0, 47 bibitems 그대로 paste
- 정직성: §V Performance Evaluation은 baseline-only로 작성, Proposed 행은 "Pending",
  §V-D Pending Evaluation Items에서 향후 보강 항목(Proposed/ABL/Sensitivity/highway) 명시

## [2026-05-12 19:18]
진행할수있도록 알려줘.


## [2026-05-12 19:18]
"진행할수있도록 알려줘."

**Commander 해석:** 현재 파이프라인은 두 갈래가 모두 열려있는 상태. 사용자는 다음
leaf 결정을 위한 옵션 제시를 요청. Commander가 일방적으로 E4를 분해 실행하면
사용자 정책 R7(RUNBOOK 직접 실행)을 위반할 수 있으므로, 옵션을 정리하여 사용자
결정 후 진입.

**현황 스냅샷:**
- Phase 1 (Librarian, Idea): done
- Phase 2 baselines (BL-A/B/C/D × urban_grid × 3 seeds): done (data/main_combined_urban.csv)
- Phase 3 partial: paper/draft/main.tex v1 (§I~VI + bibliography, baseline-only) done
- 미진행: Proposed(TinyMLP-AI-DCC) 구현, 시각화, validator, proofreader

**제시한 옵션:** E4 / E1 / E2 / proofreader / highway+density 중 택일.

## [2026-05-13 08:41]
가시 효과는 마지막이야. 논문 작업은 C로 진행하고, 끝나면 E4분해해줘.


## [2026-05-13T08:41]
"가시 효과는 마지막이야. 논문 작업은 C로 진행하고, 끝나면 E4분해해줘."

**Commander 해석:**
- "가시 효과(=시각화 E1)는 마지막" → E1은 보류, 다른 모든 작업 완료 후 진행.
- "논문 작업은 C로 진행" → 직전 19:18 옵션 제시(E4/E1/E2/proofreader/highway)를
  A/B/C/D/E로 매기면 C=E2(validator)이지만, 사용자가 명시적으로 "논문 작업"이라 표현했으므로
  Commander는 "C=Claude/Sonnet 메인 모델로 정식 Reviewer[proofreader] 호출하여 현재
  partial draft를 1차 교정하여 final/main.tex 생성"으로 해석. (Qwen 미사용)
- "끝나면 E4 분해" → proofreader 완료 후 E4(Proposed TinyMLP-AI-DCC 구현)를
  RUNBOOK 명령으로 분해(E4-1 oracle / E4-2 train / E4-3 hook / E4-4 main run),
  사용자 직접 실행 정책 R7 유지.

**실행 계획:**
1. Reviewer[proofreader] 호출 — paper/draft/main.tex → paper/final/main.tex 1차 교정
2. RUNBOOK.md에 E4-1 ~ E4-4 분해 명령 append (사용자 직접 실행용 inline heredoc)
3. E1 시각화는 명시적 보류 (E4 main run 결과 합본 후 진행 예정)

**Applied in:**
- annotations/user_directives.md (이 파일, 본 항목)
- brain/commander_memory.md (해석 + 실행 계획 누적)
- paper/final/main.tex (Reviewer[proofreader] 산출물 예정)
- RUNBOOK.md (E4 분해 섹션 신설 예정)
- pipeline_state.json (reviewer.modes_done append "proofreader" 예정)
