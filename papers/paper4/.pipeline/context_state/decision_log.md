# Decision Log

## [2026-05-08] 프로젝트 방향 결정
- 타겟 저널: AIMS Mathematics
- 주제 영역: Layer-2 (MAC) for vehicular networks + lightweight AI
- 우선 검색 키워드 (Librarian에 전달):
  1. lightweight reinforcement learning MAC vehicular
  2. AI-based channel access C-V2X / DSRC / 802.11bd
  3. lightweight DRL beacon / broadcast scheduling VANET
  4. federated / split learning lightweight V2X MAC
  5. TinyML link-layer vehicular
  6. resource allocation NR-V2X sidelink (PC5) AI lightweight
  7. Q-learning CSMA/CA vehicular
  8. graph / GNN lightweight V2X resource allocation
  9. age-of-information AI MAC vehicular
  10. ALOHA / slotted access AI vehicular

## [2026-05-08] 작업 재개 — Librarian 재정비
이전 세션 미완료 산출물 발견 (bibitem 형식 오류 + references.json 빈 채로 중단).
사용자 의도(2024–2026, Layer-2 MAC + 경량 AI + 차량)에 부합하도록
기존 후보를 검증·재분류·IEEE 포맷 재작성 + 부족분 보강 검색 지시.

## [2026-05-08 11:53] 타겟 저널 변경 + 시뮬레이션 정책 + 아이디어 도출 프로세스
- **타겟 저널**: AIMS Mathematics → **IEEE Internet of Things Journal (IoT-J)** 로 변경
- **시뮬레이터 제약**:
  - libsumo (필수, traci 금지 — Experimenter 규약과 일치)
  - SumoNetSim (사용자 자작 시뮬레이터)
  - 필요 시 별도 정밀 시뮬레이터 제작 허용 (단, libsumo 기반 권장)
- **연구 방향**: 위 시뮬레이터로 구현 가능한 방안 + 비교(베이스라인) 방안
- **아이디어 도출 프로세스 (사용자 지시)**:
  1) Idea 1차 초안 작성
  2) Librarian이 동일·유사 선행 연구 유무 확인 (novelty check)
  3) Idea가 contribution·feasibility 재검토
  4) 합의된 안을 idea_spec.md로 확정
- IoT-J 톤 가점 요소: IoT 응용성, 확장성, 실측·시뮬레이션 양적 검증, 시스템 통합 관점
- 참고: AIMS Math 시절의 "수학적 정리(Theorem) 강조"는 부수적으로만 유지

## [2026-05-08] Sensitivity analysis 도입 + BL-B 단순화 결정

### 사용자 지시 (12:39)
1) 이전 회의에서 도출된 idea_spec.md 확인 — 그 이상 검토는 시뮬레이션 결과로 검증
2) BL-B (ETSI DCC Adaptive / LIMERIC) → **Simplified Adaptive**로 단순화
3) **Sensitivity analysis**를 통해 적절한 파라미터 값을 찾고, 분석 결과를 별도 저장하여 논문(특히 Performance Evaluation §Sensitivity and robustness analysis)에서 사용

### 적용 결정
- BL-B를 "Simplified Adaptive (CBR-tracking PID-style controller)"로 정의 — LIMERIC의 정확한 재현 부담 제거, 알고리즘 정확히 명세
- experiment_spec.json에 별도의 **sensitivity_analysis** 블록 추가:
  · 대상 파라미터: (a) Oracle cost weights α/β (=AoI/CBR 가중), (b) Discrete action grid (T_GenCam, p_tx), (c) CBR thresholds (Reactive/Adaptive 전환), (d) MLP hidden width
  · 수행 방식: 각 파라미터에 대해 grid sweep, 다른 파라미터는 default 고정 (one-at-a-time, OAT)
  · 출력: data/sensitivity/<param>_<metric>.csv → 추후 graph/sensitivity_*.png 생성
  · 절차: Sensitivity analysis 결과를 먼저 분석하여 default 파라미터를 확정한 후, 본 실험(S1/S2)을 수행
- Phase: Experimenter Stage 1 (design) — experiment_spec.json 작성으로 진행


## [2026-05-08 13:35] 워크플로우 분할 + SumoNetSim 시나리오 표준화 결정

### 배경
사용자 지시 (13:25): 작은 단위로 쪼개어 구현하고, SumoNetSim1.1.6 시나리오 (RSU 통신범위, RSU 간 거리, 차량 밀도) 참고.

### 결정
1. SumoNetSim1.1.6은 실제로 부재 → 1.1.5를 표준 참고로 채택 (사용자에게 사후 확인)
2. 채택할 SumoNetSim 1.1.5 파라미터:
   - RSU_RANGE = 800 m
   - V2V comm_range = 200 m
   - EDGE_LENGTH (RSU 간 거리) = 2400 m (= 2*800 + 800 outage zone)
   - 그리드 NUM_BLOCKS = 6 → 그러나 우리 실험에선 시뮬 시간 절약 위해 3 또는 5 blocks 사용
   - DENSITY = 5~20 veh/(km·lane) 가변
   - AV_SPEED = 20~60 km/h, MAX_STEPS = 3600 s
3. 워크플로우를 Phase X-1 ~ X-13으로 분할 (commander_memory.md 참조)
4. 각 Step마다 Reviewer[validator] 검증을 거쳐 다음 Step으로 진행

### 즉시 실행 순서
Phase X-2: Experimenter[design] 호출 — experiment_spec.json scenarios 섹션을 SumoNetSim 1.1.5 표준으로 패치 + sensitivity sweep 정렬

이후 사용자 컨펌 받고 X-3부터 진행.


## [2026-05-08 13:37] A안 채택 — Hierarchical Decomposition 구현 전략

### 결정
사용자 13:37 지시에 따라 A안(13:25 agent_notes의 Step 1~11 분할 워크플로우) 진행.
+ 추가: 모든 시뮬레이션 구현은 L1(큰 틀) → L2(작은 틀) → L3(세분화) 잎 단위로 분해 후 Experimenter[implement]에게 위임.

### 근거
- 13:02에 SA3 sweep 결과 의심 패턴 발견 (cbr_target 7개 값 모두 동일 AoI/CBR/PDR, runtime 1200x faster).
- libsumo silent fallback 의심 → 한 번에 큰 단위로 위임할 경우 환각·우회 가능성 높음.
- 사용자가 "Coder가 작은 부분부분을 구현"하라고 명시.

### 적용 결과
- agent_notes.md에 L1~L3 WBS 추가 (5개 메가 단계 → leaf 작업 5개씩)
- 위임 규칙 R1~R5 명문화: 1 호출=1 파일=1 책임, 검증 기준 1개, 스코프 크리프 차단.
- 첫 leaf 작업: L1-A-1 Reviewer[validator]에게 sim_engine.py의 libsumo 통합부 5개 질문(Q-A1~Q-A5)만 검증 의뢰.

### 다음 단계
L1-A-1 결과 → L1-A-2 → L1-A-3 → 결정 게이트 → L1-B 패치.


## [2026-05-08 13:55] L1-A-2 결과 + RUNBOOK.md 신설

### L1-A-2 (Reviewer[validator]) — FAIL
sim/etsi_cam_layer.py line 97: `self.params.get('CBR_target', 0.60)`
- runner는 `{'cbr_target': value}` (소문자) 전달 → 키 mismatch → 항상 default 0.60
- SA3 cbr_target sweep 무력화의 직접·유일 원인 확정
- BL-B 알고리즘 자체(line 339-344 비례 제어)는 정상

### 사용자 13:46 지시 적용 — RUNBOOK.md 신설
- 이전: 에이전트가 30s timeout으로 시뮬을 직접 못 돌림 → 실측 진단 어려움
- 신규: 사용자가 직접 실행할 명령을 RUNBOOK.md에 누적 정리, 사용자가 결과 알려주면 Commander가 다음 leaf 결정
- 효과: ① timeout 우회 ② 사용자가 결과 직접 확인 → 신뢰도 ↑ ③ 명령 이력이 한 파일에 모임

### L1-B-1 결정 — 1줄 패치를 사용자에게 위임 (Experimenter 호출 안 함)
- 변경 범위가 line 97 단일 키 1개로 매우 작음
- 사용자가 RUNBOOK 명령 A/B/C로 직접 적용·검증 가능 (sed + 3개 값 비교)
- 새 호출 비용·환각 위험 회피 → 가장 절약적인 경로

### 다음 leaf 후보 (사용자 RUNBOOK 결과 받은 후)
- 명령 A/B/C 결과 정상 → L1-A-3 (smoke test, 명령 1·2)
- 명령 2 정상 → L1-B 다른 항목(naming 일관성, method_params assert) 검토 또는 곧장 L1-D로
- 명령 2 비정상 → 추가 진단 leaf


## [2026-05-08 21:39] L1-A-2 패치 미적용 진단 + 사용자 옵션 제시
- 사용자 보고 "C에서 0.6 세 개" → 패치 무효
- Root cause: RUNBOOK 명령 B의 sed 패턴이 작은따옴표 매칭이나 실제 파일은 큰따옴표 사용
- 결정: 사용자 잘못 아님을 명시. 옵션 ①(수정된 sed 재실행) / 옵션 ②(Experimenter 위임) 제시
- 다음 leaf 진행은 사용자 응답 후 결정


## [2026-05-08 21:54] L1-B-1 패치 정상 / SA3 동일 결과의 새 root cause = generate_routes line 244

- L1-B-1 (line 97 키 mismatch) 패치 후 단위 테스트 PASS. blb_CBR_target = 0.30/0.60/0.70 정상.
- 그러나 SA3 풀 sweep 결과 21 row 모두 동일 → 더 근본적인 문제 잔존.
- Commander 직접 분석으로 sim_engine.py line 244의 depart 분포 [0, 30s] 가설 발견. warmup과 정확히 겹쳐 post-warmup에 차량 거의 없음.
- 결정: 다음 leaf L1-B-2를 Experimenter[implement]에게 위임 (1 파일 = sim_engine.py, 1 책임 = generate_routes 패치). 패치 범위는 사용자 컨펌 후 결정.
- 결정: L1-B-2 후속 smoke test (30~60초)는 RUNBOOK 명령 6으로 사용자 직접 실행 옵션을 열어둠. 사용자 컨펌에 따라 Experimenter에 묶어서 위임할 수도 있음.
- 결정: SA3 풀 sweep (10~20분)은 RUNBOOK 명령 7로 사용자 직접 실행.

## [2026-05-08T22:15:00] 위임 정책 강화 + L1-B-2 패치 위임
- 짧은 테스트는 Experimenter, 시뮬은 사용자 (R6/R7/R8 신설).
- L1-B-2 sim_engine.generate_routes() 패치를 Experimenter에게 위임. 정상 적용.
- 사용자에게 RUNBOOK 명령 6 → 명령 7 순으로 요청.


## [2026-05-08 22:50] L1-B-3 — SumoNetSim1.1.5 자산 통합 결정
- 사용자 22:41 지시: "해당 libsumo 관련 파일들을 활용하여 시뮬레이션을 구현 및 실행하도록 해."
- "해당" = 22:38에 고정한 /home/imnyj/SumoNetSim1.1.5/src/sumo/ 자산.
- sim/sim_engine.py 한 파일에 SUMOCFG_PATH 상수 + libsumo.start -c 인자 패턴으로 통합.
- 자체 net/route 생성 폐기 → L1-B-2-extended (trip→flow/route 변환) 워크 아이템 폐기.
- Experimenter Self-run smoke PASS (300 steps, 88 avg vehicles, n_cam>26k proxy, CBR=0.73).
- 다음 결정 게이트: 사용자 컨펌 필요 — Reviewer[validator] 호출(권장 A) vs RUNBOOK 명령 2-redo 직접 실행(권장 B).


## [2026-05-08 22:55] ABC-A 완료, B/C는 사용자 실행 대기

### 사용자 지시 (22:52)
"ABC 순서로 진행"

### 해석
22:50 commander_memory의 차기 leaf 후보 중 사용자가 A→B→C 순서 채택을 의미.
- A. Reviewer[validator] — sim_engine.py L1-B-3 패치 정합성 검증
- B. RUNBOOK 명령 2-redo — SimulationRunner full run (사용자 직접)
- C. RUNBOOK 명령 4-redo — SA3 cbr_target sweep (사용자 직접)

### ABC-A 수행 결과
- 1차 시도: Reviewer agent 호출 → 30초 timeout 직전에 sensitivity_runner.py 마지막 점검 단계에서 중단.
- Commander가 직접 인계해 Q-V1~Q-V5 5개 검증 완료. 모두 PASS.
- 핵심 발견: L1-A-2에서 발견된 cbr_target 키 케이스 버그(CBR_target vs cbr_target)는
  이미 L1-B-1 패치로 etsi_cam_layer.py L97이 'cbr_target' (소문자)으로 수정된 상태.
  sensitivity_runner.py L135도 'cbr_target' (소문자)이므로 cross-file 키 일치 ✅.
- 산출물: paper/validation/validation_report.json (PASS)

### B/C 단계 위임
- RUNBOOK.md에 ABC-B, ABC-C 섹션 추가, 정상/비정상 신호 + 보고 형식 명시.
- 사용자 직접 실행 후 결과 보고 받으면 Reviewer[validator] 재호출하여 데이터 무결성 검증.

### 학습 포인트
- Reviewer agent 30초 timeout이 발생할 때, 검증 작업 자체는 비교적 단순한 정적 분석이므로
  Commander가 직접 인계 수행하는 것이 효율적이었음. 사용자 시간을 절약하면서도 품질 유지.
- json.dumps에서 모듈 객체 직렬화 오류 → 'true' (소문자) 변수가 sandbox에서 import re로 잘못 resolve된 사례.
  앞으로 dict 리터럴 작성 시 Python boolean True/False 정확히 사용.


## [2026-05-12T18:30] 논문 작성 트랙 우선 결정
- 사용자 17:35 지시는 "E4 + 논문 작성" 두 트랙 동시 요청
- 17:52 "이어서 계속"의 해석 옵션:
  (a) E4 RUNBOOK 분해 후 사용자 직접 실행 (Proposed 결과 도착까지 대기)
  (b) 논문 작성 트랙 즉시 실행 (현재 가용 데이터로 partial draft)
- Commander 채택: (b) 우선 → Writer 3 stage 분할로 main.tex 1차 완성
- 근거:
  · "이어서 계속" 단발 지시는 즉시 산출물 선호 신호
  · 논문 작성은 환각 위험이 데이터 생성보다 낮음 (참고자료 풍부)
  · E4는 90분 × 3 seeds × 알고리즘 단계 → 사용자 직접 실행이 시간 효율
- 다음 사용자 응답 시 E4 진입 또는 추가 섹션 확장(figure/graph) 분기 예정
