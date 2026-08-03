# Antigravity 자체 업그레이드 계획서 (UPGRADE_PLAN)

> 이 문서는 Antigravity 에이전트가 순서대로 읽고 실행하는 작업 지시서다.
> 반드시 Phase 0부터 순서대로 진행하고, 각 Phase의 [검증] 항목을 통과한 뒤에만 다음 Phase로 넘어간다.
> 검증에 실패하면 해당 Phase의 변경 사항을 git으로 되돌리고, 실패 원인을 `logs/upgrade_failures.md`에 기록한 후 사용자에게 보고하고 중단한다.

## 공통 원칙 (모든 Phase에 적용)

1. 모든 변경 전에 `git add -A && git commit` 으로 현재 상태를 스냅샷한다. 커밋 메시지는 `[upgrade] phase-N 시작 전 스냅샷` 형식.
2. 기존 룰 프롬프트, 기존 skill, 기존 서브에이전트 정의를 **삭제하거나 약화시키지 않는다.** 개선이 필요하면 새 파일을 만들고 사용자 승인 후 교체한다.
3. 외부(GitHub 등)에서 가져온 skill/플러그인은 전문을 읽고, 도구 권한을 최소로 제한한 뒤에만 도입한다. 이해되지 않는 지시문이 포함된 외부 skill은 도입하지 않고 사용자에게 보고한다.
4. 한 Phase에서 수정하는 파일은 그 Phase의 범위 안에 있는 것만으로 한정한다.

---

## Phase 0. 현황 진단 및 백업

- [ ] `.antigravity/`, `.gemini/`, `.agents/`, `AGENTS.md`(있다면)의 전체 구조를 트리로 출력하고 `docs/harness_inventory.md`에 기록한다.
- [ ] 현재 등록된 룰, skill, 서브에이전트, hook, MCP 서버 목록과 각각의 역할 한 줄 요약을 같은 파일에 정리한다.
- [ ] 저장소가 git 관리 하에 있는지 확인하고, 아니라면 `git init` 후 초기 커밋을 만든다.

[검증] `docs/harness_inventory.md`가 존재하고, 룰/skill/서브에이전트 목록이 실제 파일 구조와 일치한다.

---

## Phase 1. 룰 계층 재구성 (AGENTS.md 정리)

목적: 룰 프롬프트가 매 요청에 통째로 들어가 컨텍스트를 낭비하지 않도록, 전역 룰과 작업별 룰을 분리한다.

- [ ] 현재 룰 프롬프트를 분석하여 다음 세 계층으로 분류한다.
  - (a) 항상 적용되어야 하는 절대 룰 → 프로젝트 루트 `AGENTS.md`에 유지 (최대한 짧게)
  - (b) 특정 작업 유형에만 필요한 룰 (논문 작성 규칙, SUMO 시뮬레이션 코딩 규칙, 제안서 양식 규칙) → 각 작업의 skill 파일 내부로 이동
  - (c) 중복되거나 사문화된 룰 → `docs/deprecated_rules.md`로 이동 후 사용자 확인 요청
- [ ] 재구성 결과를 `docs/rules_restructure_report.md`에 before/after로 정리한다.

[검증] `AGENTS.md`의 길이가 재구성 전보다 줄었고, 이동된 룰이 해당 skill 파일에서 확인된다. 룰이 소실된 항목은 0개여야 한다.

---

## Phase 2. Skill의 플러그인 번들화

목적: 작업 도메인별로 skill·rules·서브에이전트 정의를 하나의 배포 단위로 묶어 독립적으로 버전 관리·개선할 수 있게 한다.

- [ ] 다음 3개 플러그인 디렉토리를 생성하고, 기존 skill을 도메인별로 재배치한다.
  - `paper-writing/` : 논문 초안, 문헌 정리, LaTeX/참고문헌 관련 skill
  - `sumo-sim/` : SUMO 기반 Python 시뮬레이션 실행·분석·시각화 skill
  - `admin-proposal/` : 학과 업무 문서, 과제 제안서 작성 skill
- [ ] 각 플러그인에 `README.md`를 만들어 포함된 skill 목록, 의존 도구, 권한 범위를 명시한다.
- [ ] 재배치 후에도 기존 슬래시 명령이 동일하게 동작하는지 확인한다.

[검증] 각 플러그인의 skill이 TUI에서 정상 호출된다. 호출 불가한 skill이 있으면 원상 복구한다.

---

## Phase 3. Hooks 도입 (강제 검증 계층)

목적: "부탁하는 룰"을 "강제되는 검증"으로 전환한다. 최소 다음 3개 hook을 JSON으로 정의한다.

- [ ] **post-edit hook (Python)**: `sumo-sim/` 관련 `.py` 파일 수정 후 자동으로 문법 검사(`python -m py_compile`)와 린트를 실행하고, 실패 시 에이전트가 스스로 수정하도록 한다.
- [ ] **post-edit hook (문서)**: `paper-writing/` 산출물(.md, .tex) 저장 후 참고문헌 키 누락, 깨진 인용 형식을 검사하는 스크립트를 실행한다. 검사 스크립트는 `scripts/check_citations.py`로 직접 작성한다.
- [ ] **pre-tool-call hook (안전장치)**: `.antigravity/`, `.gemini/`, `AGENTS.md` 자체를 수정하는 도구 호출은 반드시 사용자 승인을 거치도록 한다. (자체 업그레이드 폭주 방지)

[검증] 의도적으로 문법 오류가 있는 .py 파일을 수정해 hook이 발동하는지 확인한다. 설정 파일 수정 시 승인 요청이 뜨는지 확인한다.

---

## Phase 4. Headless 자동화 파이프라인

목적: 사람이 없는 시간에 장기 작업을 돌리고 아침에 보고서를 받는 구조를 만든다.

- [ ] `scripts/nightly_sim.sh` 작성: 비대화형 모드(`agy -p "..."`)로 (1) 지정된 SUMO 시뮬레이션 실행 → (2) 결과 로그 파싱 → (3) 성능 지표 요약과 이상치 분석을 `reports/YYYY-MM-DD_sim_report.md`로 생성하는 스크립트.
- [ ] `scripts/weekly_digest.sh` 작성: 최근 1주일의 git 로그, 실험 결과, 미완료 TODO를 모아 주간 연구 요약 보고서를 생성하는 스크립트.
- [ ] 두 스크립트를 cron(또는 Windows 작업 스케줄러)에 등록하는 방법을 `docs/automation_setup.md`에 정리한다. 등록 자체는 사용자가 수행한다.

[검증] 두 스크립트를 수동 실행하여 보고서 md 파일이 실제로 생성되는지 확인한다.

---

## Phase 5. 실행 이력 기반 자가 개선 루프

목적: 반복 실패 패턴을 skill로 승격시키는 순환 구조를 만든다. 단, 무단 자기 수정은 금지한다.

- [ ] `logs/execution_notes.md` 를 생성하고, 이후 모든 세션 종료 시 (1) 수행한 작업 (2) 실패했거나 재시도한 지점 (3) 사용자가 수동으로 교정해 준 내용을 3줄 이내로 추가 기록하는 룰을 `AGENTS.md`에 1줄로 추가한다.
- [ ] `improve-skills`라는 메타 skill을 작성한다. 이 skill은 호출 시:
  1. `logs/execution_notes.md`에서 3회 이상 반복된 실패/교정 패턴을 추출하고
  2. 이를 해결하는 skill 초안 또는 기존 skill 수정안을 `proposals/` 디렉토리에 생성하며
  3. **직접 적용하지 않고** 사용자 승인을 요청한다.
- [ ] 각 수정안에는 개선 전/후를 비교할 수 있는 테스트 케이스(예시 입력과 기대 출력)를 반드시 포함시킨다.

[검증] `improve-skills` 호출 시 proposals/에 수정안이 생성되고, 승인 전에는 실제 skill 파일이 변경되지 않음을 확인한다.

---

## Phase 6. 최종 보고

- [ ] Phase 0의 인벤토리와 비교하여 무엇이 어떻게 바뀌었는지 `docs/upgrade_summary.md`에 정리한다.
- [ ] 사용자가 즉시 시험해 볼 수 있는 명령어 목록(새 skill 호출법, headless 스크립트 실행법)을 같은 문서 끝에 첨부한다.
- [ ] 전체 변경을 `[upgrade] 완료` 커밋으로 마무리한다.

[검증] `docs/upgrade_summary.md`가 존재하고, 모든 Phase의 검증 항목이 체크되어 있다.
