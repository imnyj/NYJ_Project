# interface.py
"""Inter-agent interface contract.

This is the single document every agent's prompt embeds at the
bottom (see `{COMMON_INTERFACE}` in agents/*.py). It tells each
agent:
  * where to read/write artefacts on disk
  * how to use the .pipeline/ persistent memory layer
  * what other agents will produce/consume

Updated for the 6-agent consolidation:
  - Experimenter handles Experiment+Coder+Visualization stages
  - Reviewer handles Validator+Proofreader modes
"""

from config import PATHS

PATH_STRINGS = {k: str(v) for k, v in PATHS.items()}


COMMON_INTERFACE = f"""
[에이전트 간 인터페이스 규약 — 6 에이전트 통합 버전]

1. 산출물 저장 경로
   참고문헌 JSON        : {PATH_STRINGS['references']}/references.json
   참고문헌 bibitem     : {PATH_STRINGS['references']}/bibitem.tex
   아이디어 명세         : {PATH_STRINGS['idea']}/idea_spec.md
   실험 명세서           : {PATH_STRINGS['experiment']}/experiment_spec.json
   시뮬레이션 데이터      : {PATH_STRINGS['data']}/<scenario>_<metric>.csv
   검증 리포트           : {PATH_STRINGS['validation']}/validation_report.json
   구조도/다이어그램      : {PATH_STRINGS['figure']}/xxx.png
   결과 그래프           : {PATH_STRINGS['graph']}/xxx.png
   논문 초안             : {PATH_STRINGS['draft']}/main.tex
   최종 교정본            : {PATH_STRINGS['final']}/main.tex

2. .pipeline/ 상태 관리 시스템

   [brain/] — 에이전트 영구 기억
   경로: {PATH_STRINGS['brain']}/<agent>_memory.md
   규칙:
     - 대용량 파일을 처음 읽을 때 핵심 내용을 자신의 memory 파일에 기록
     - 새 세션에서는 memory 파일을 먼저 읽고, 원본은 필요 시만 참조
     - 작업 완료 시 새로 알게 된 사실, 변경 사항을 memory에 추가
     - memory 파일은 누적식 (덮어쓰기 금지, 항상 append)
     - 각 항목에 날짜 기록: ## [YYYY-MM-DD] 제목

   에이전트별 memory 파일:
     - librarian_memory.md     : 검색 키워드, 발견 논문, 실패 케이스
     - idea_memory.md          : 연구 컨텍스트, 노벨티 분석
     - experimenter_memory.md  : 실험 설계 + 시뮬레이션 구조 + 시각화 설정
                                 (3 stage 통합 — design/implement/visualize)
     - reviewer_memory.md      : 검증 이력 + 교정 이력
                                 (2 mode 통합 — validator/proofreader)
     - writer_memory.md        : 작성 진행 상태, 섹션별 cite 키
     - commander_memory.md     : 결정 이력, 사용자 선호도 학습

   [context_state/] — 파이프라인 상태 추적
   경로: {PATH_STRINGS['context_state']}/
   파일:
     - pipeline_state.json: 각 단계의 상태 (pending/running/done/failed)
       Experimenter는 stages_done 배열에 ["design", "implement", "visualize"] 추가
       Reviewer는 modes_done 배열에 ["validator", "proofreader"] 추가
       Writer는 sections_done 배열에 완료 섹션 추가
       작업 시작 시 status를 "running"으로, 완료 시 "done"으로 갱신
     - decision_log.md: 주요 결정 사항 기록
       형식: ## [YYYY-MM-DD] 결정 제목 \\n 내용
     - session_history.md: 세션 시작/종료 기록

   [code_tracker/] — 코드 변경 추적 (Experimenter[implement] + Reviewer[validator])
   경로: {PATH_STRINGS['code_tracker']}/
   파일:
     - changelog.md: 코드 변경 이력
     - version_map.json: 파일별 최종 수정 시점
     - simulation_digest.md: 시뮬레이션 코드 구조 요약 (Experimenter가 최초 1회 생성)

   [annotations/] — 피드백 및 메모
   경로: {PATH_STRINGS['annotations']}/
   파일:
     - validation_history.md: Reviewer[validator] 검증 이력 누적
     - user_directives.md: 사용자 지시사항 누적 (Commander가 기록)
     - agent_notes.md: 에이전트 간 전달 메모

   [implicit/] — 학습된 패턴
   경로: {PATH_STRINGS['implicit']}/
   파일:
     - error_patterns.md: 반복 오류 패턴 (Reviewer[validator]가 학습)
     - user_preferences.md: 사용자 선호도 (Commander가 학습)
     - style_evolution.md: 논문 스타일 변화 추적 (Reviewer[proofreader])

3. 에이전트 간 데이터 흐름 (6 에이전트)

   Phase 1: 기초 설계
     Librarian          →  references.json + bibitem.tex   →  Idea, Writer
     Idea               →  idea_spec.md                     →  Experimenter, Commander

   Phase 2: 실험 설계 + 구현 + 검증
     Experimenter[design]    →  experiment_spec.json          →  Experimenter[implement]
     Experimenter[implement] →  data/*.csv                    →  Reviewer[validator]
     Reviewer[validator]     →  validation_report.json         →  Commander
        FAIL → Experimenter[implement] 재호출 (최대 retry_count)
        PASS → 다음 단계

   Phase 3: 시각화 + 집필 + 교정
     Experimenter[visualize] →  figure/*.png, graph/*.png    →  Writer
     Writer (분할 7회)       →  draft/main.tex               →  Reviewer[proofreader]
     Reviewer[proofreader]   →  final/main.tex               →  Commander

4. Commander의 단계별 호출 규약

   Experimenter는 한 에이전트가 3 stage를 수행하므로 호출 시 stage 명시:
     "Experimenter, Stage 1 (design): idea_spec.md를 읽고 experiment_spec.json 작성"
     "Experimenter, Stage 2 (implement): experiment_spec.json을 읽고 시뮬레이션 실행, data/*.csv 생성"
     "Experimenter, Stage 3 (visualize): data/*.csv를 읽고 figure/, graph/ 생성"

   Reviewer는 한 에이전트가 2 mode를 수행하므로 호출 시 mode 명시:
     "Reviewer, Validator 모드: data/*.csv 검증 → validation_report.json"
     "Reviewer, Proofreader 모드: draft/main.tex 교정 → final/main.tex"
"""


EXPERIMENT_SPEC_SCHEMA = """
[실험 명세서 JSON 스키마 — Experimenter[design] 단계 출력]
{{
  "title": "실험 제목",
  "objective": "실험 목적",
  "scenarios": [{{
    "name": "scenario_name",
    "description": "시나리오 설명",
    "parameters": {{"param_key": "value"}},
    "duration_steps": 3600
  }}],
  "algorithms": {{
    "proposed": {{"name": "알고리즘명", "description": "구현 상세"}},
    "baselines": [{{"name": "비교 알고리즘명", "description": "구현 상세"}}]
  }},
  "metrics": [{{"name": "metric_name", "formula": "수식", "unit": "단위"}}],
  "output_files": ["expected_filename.csv"]
}}
"""


VALIDATION_REPORT_SCHEMA = """
[검증 리포트 JSON 스키마 — Reviewer[validator] 모드 출력]
{{
  "result": "PASS 또는 FAIL",
  "timestamp": "ISO 8601",
  "retry_count": 0,
  "issues": [{{
    "bug_id": "BUG_001",
    "severity": "CRITICAL / MAJOR / MINOR",
    "location": "파일명:라인 또는 함수명",
    "description": "문제 설명",
    "suggestion": "수정 제안"
  }}],
  "summary": "종합 의견",
  "data_integrity": {{"nan_check": true, "range_check": true, "consistency_check": true}}
}}
"""
