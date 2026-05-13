# Commander Memory

## [2026-04-30] 워크스페이스 정리 세션
- 루트 정리: Main Idea.md + ST-CVAE 구조.md → paper/idea/research_overview.md 통합
- 사용자 요청 사항.md → .pipeline/annotations/user_directives.md 흡수
- paper/scheme.tex (직전 논문 ST-CVAE) → paper/draft/scheme_legacy.tex 이동
- history/launch_team.sh, run_writer_demo.sh 삭제 (옛 6에이전트 tmux 시스템, 현 architecture와 무관)
- paper/CLAUDE.md 갱신 (옛 Researcher/Writer/Editor 체계 → 새 6에이전트 체계)

## [2026-04-30] 현재 프로젝트 상태
- 토픽: CCVN V2I Precaching을 위한 RSU 체류 시간 예측 (ST-MBAN)
- 타깃: IEEE Internet of Things Journal (CIoV 강조)
- **블로커**: 시뮬레이션 데이터셋 미수집. RSU 1개가 ~20만 샘플 누적 후에 시작.
- 데이터 도착 전 가능 작업:
  1. Librarian → reference 보강 (사용자 요청 항목 5번 상세 키워드)
  2. Writer/Editor → Introduction 재구성, Abstract 60% 축약 (직전 scheme_legacy.tex 기반 — 단, 새 ST-MBAN 모델로)
  3. Experimenter[implement] → 신규 baselines (ST-MBAN 사용자 요청 5번에 언급된 비교 방안들) 사전 구현
  4. Reference table 갱신 (D1~D6 설명, Detail 항목 추가)

## [2026-04-30] 사용자 선호도
- AI 상투어 회피 (`---`, "novel", "significant" 남발 금지)
- ( )는 약어와 수식에서만 사용. 수식 인용은 Equation (n) 형식.
- 요약/서론은 트렌드 반영하여 압축적·구조적으로.

## [2026-04-30 14:12] 세션 스코프 확정
- 사용자 지시: 본 세션은 **paper1 폴더 전용**.
- 다른 세션에서 paper2(및 추가 paper)가 병행 작업 중 — 절대 paper1 외부 경로(상위 papers/, paper2/ 등)로 파일 생성/수정하지 않음.
- 모든 산출물 경로는 /home/imnyj/papers/paper1/ 하위로 한정.
- 다음 가능 액션 후보 (블로커 데이터셋 도착 전):
  1. Librarian — user_directives 5번 키워드 보강 (CIoV/V2I·V2V/Popularity/Mobility/Hybrid/ML·DL/snapshot/RSU-Local + baselines)
  2. Writer — Abstract 60% 축약, Introduction 재구조화 (scheme_legacy.tex 참고하되 ST-MBAN 모델로 갱신)
  3. Experimenter[implement] — baselines 사전 구현 (데이터셋 도착 전 선행)
  4. Reviewer[proofreader] — 기존 초안의 AI 상투어/괄호 사용 점검
- 우선순위는 사용자 다음 지시 대기.


## [2026-05-01] paper1 — 데이터셋 대기 중 가능 작업 일괄 진행 완료
사용자 지시: paper1에 필요한 작업을 모두 진행하도록 해 (데이터셋 완성 전까지).

### 완료된 작업
1. Librarian — references.json (37.3KB, 72편) + bibitem.tex (19.4KB) 작성.
   - 8개 카테고리 균형: CIoV(11), V2I(9), V2V(10), Popularity(6), Mobility(10),
     Hybrid(6), ML/DL(7), Snapshot/RSU-Local(13). 모두 Tier-1 출판처 + DOI 검증.
2. Experimenter[design] — experiment_spec.json (21.4KB) 작성.
   - 9 알고리즘 (proposed ST-MBAN + 8 baselines), 5 시나리오, 4 메트릭 그룹.
3. Experimenter[implement] (사전 구현) — baselines_extra.py (43.3KB) 신규.
   - 8개 baseline의 PyTorch 골격 + smoke test. 실제 학습/data CSV 생성은 데이터 도착 후.
4. Writer (4 step) — main.tex (66.1KB) 작성.
   - Step 1: 뼈대 + Abstract(legacy 60% 분량) + IEEEkeywords + Introduction
   - Step 2: Related Work — D1~D6 정의 + 5 카테고리 단락 + Comparison Table (\cite만 사용)
   - Step 3: System Model — Network/Snapshot/Task/Feature Table I/Targets
   - Step 4: ST-MBAN Architecture — Encoders + MHA Fusion + ResBlock Decoder + Huber Loss
   - Bibliography: bibitem.tex 72개 entry 삽입 (Commander 직접 처리)
5. Reviewer[proofreader] (1차) — final/main.tex (64.6KB) 생성.
   - 'novel' 1건 제거, 'e.g.,' 1건 정상화. em-dash/significantly 등 0건.

### 미완료 (데이터셋 도착 후 진행)
- Writer: Performance Evaluation, Conclusion.
- Experimenter[implement]: 실제 SUMO 데이터 학습/추론, data/*.csv 생성.
- Experimenter[visualize]: figure/, graph/ 생성.
- Reviewer[validator]: data/*.csv 검증.
- Reviewer[proofreader]: 최종본 재점검.

### 사용자 지시 충족 여부
- 1번 (Abstract 60%): OK
- 2번 (Intro 트렌드 재구조): OK
- 3번 (em-dash 지양): OK (0건)
- 4번 (괄호/Equation): OK
- 5번 (reference 보강 8 카테고리): OK (72편 검증)
- 6번 (reference table Paper/cite/D1-D6/Detail): OK
- 7번 (cite-reference 일치): proofreader 1차 점검 통과

### 호출 timeout 교훈
Writer/Reviewer 호출 시 final_answer 출력이 길어서 30초 timeout이 4건 발생.
산출물은 모두 정상 생성됨. 향후 에이전트 호출 시 응답 길이 제한 더 강하게 명시 필요.


## [2026-05-06 14:51] 주간 자체 업그레이드 검토 #1 — 변경 없음 결정
- 검토 결과 즉시 적용해야 할 코드 변경 없음.
- 발견 사항은 annotations/agent_notes.md에 상세 기록.
- 다음 검토 시 우선순위:
  (a) Writer/Reviewer 응답 timeout 추가 발생 여부 확인 → 발생 시 프롬프트 1줄 추가
  (b) smolagents/litellm/anthropic changelog 1회 점검 (Librarian 위임)
  (c) requirements.txt lock 파일 도입 검토
- record_outcome(outcome="completed")로 기록함.


## [2026-05-06 16:16] 시뮬 데이터 수집 병목 점검
사용자가 "snapshot 기록 주기, libsumo step 간격, I/O 빈도 점검"과 "RSU 로컬 데이터 5만으로 하향" 지시.

### 점검 결과 요약 (상세는 annotations/agent_notes.md)
- /home/imnyj/SumoNetSim1.1.5/dataset_scenario.py + src/NetSim.py 정독.
- 현재 누적: 23 RSU, 총 55,209 레코드 (RSU 평균 2,400, 최대 3,423, 최소 807).

### 발견된 병목 (우선순위 순)
1. NetSim.py L584/586/592/814/816 — `time.sleep(0.001)` × 5회 (이벤트 루프 + step_event)
   → episode당 ~18s wall-clock 손실. **제거 권고.**
2. dataset_scenario.py L11 — `BUFFER_SIZE = 1` (즉시 flush)
   → RSU 23개 × 매 레코드 open/close syscall. **BUFFER_SIZE=50 권고.**
3. dataset_scenario.py L13 — `PER_REQ = 300` (첫 REQUEST 평균 지연 150초)
   → **PER_REQ=30 권고**, RSU당 레코드 ~1.5x 기대.
4. run_collect.sh L17 — `timeout 120` (시뮬 3600s 대비 너무 짧음)
   → 일부 episode가 T_INIT(300s) 이전에 종료될 위험.

### 점검 결과: 변경 불필요
- libsumo step (1초) — 적정.
- send_request/check_range 1초 주기 — libsumo step과 동기화. 적정.
- 진행 파일(.sim_progress) 10초 주기 write — 무시 가능.

### 5만 목표 해석 모호성
- 합계 55K 이미 달성 vs RSU별 5만(현재 최대 3,423, 약 15x 더 필요) — 사용자 확인 필요.

### 세션 스코프 충돌
- 시뮬 코드는 /home/imnyj/SumoNetSim1.1.5 (paper1 외부). paper1-only 스코프 정책에 따라
  Commander가 자동 패치하지 않음. 사용자가 직접 수정하거나 명시적 허가 시 Experimenter[implement]에 위임.

### 다음 액션
- 사용자 응답 대기:
  (1) "RSU 1개당 5만" vs "전체 합계 5만" 의도 확인.
  (2) 위 4개 패치 적용 허가 여부.
