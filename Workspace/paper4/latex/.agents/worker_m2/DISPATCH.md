## 2026-08-18T08:31:23Z
당신은 Milestone 2를 수행하는 Academic Worker (worker_m2)입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/latex/.agents/worker_m2
요구사항 원본: /home/imnyj/Workspace/paper4/latex/.agents/ORIGINAL_REQUEST.md
프로젝트 문서: /home/imnyj/Workspace/paper4/latex/PROJECT.md
참조 조사 보고서: /home/imnyj/Workspace/paper4/latex/.agents/explorer_1/analysis.md, /home/imnyj/Workspace/paper4/latex/.agents/explorer_1/handoff.md
관련 스킬: /home/imnyj/.agents/skills/academic-writing-style/SKILL.md, /home/imnyj/.agents/skills/academic-worker/SKILL.md, /home/imnyj/.agents/skills/anti-hallucination/SKILL.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행 지침 및 GEMINI.md 규칙 준수]
1. 원본 요구사항(ORIGINAL_REQUEST.md), 프로젝트 계획(PROJECT.md), Explorer 1의 조사 보고서(analysis.md, handoff.md)를 숙지하세요.
2. 작업 전 `/home/imnyj/Workspace/paper4/latex/backup/` 디렉토리에 `main.tex` 백업본 (`backup/main.tex.bak_m2`)을 생성하세요.
3. 파일 수정 전 반드시 파일 락을 획득하세요:
   `python3 /home/imnyj/Command/core/lock_manager.py acquire /home/imnyj/Workspace/paper4/latex/main.tex worker_m2`
4. `/home/imnyj/Workspace/paper4/latex/main.tex` 파일에 다음 R1 학술 문체 교정 작업을 완벽히 적용하세요:
   - **R1.1 과장/금지어 및 AI 상투어구 제거/대체**:
     - `comprehensive` 잔여 4건(L51, L68, L522, L933)을 `extensive`, `broad`, `detailed` 등으로 교체.
     - `utilize`(L166)를 `use`로 교체.
     - `elucidate`, `seamless`, `vital`, `fosters`, `significantly`, `substantially`, `leveraging`, `subsequently`, `effectively`, `encapsulates`가 본문에 없음을 최종 확인 (단, 표준 고유명사인 Connected and Autonomous Vehicles, autonomous sensing의 autonomous는 유지).
   - **R1.2 본문 내 파일명 전면 제거**:
     - 8건의 `.csv` 파일명 언급(L632 `cbr_trace.csv`, L636 `pdr_vs_density.csv`, L719 `aoi_vs_density.csv`, L793 `pdr_vs_distance.csv`, L822 `hardware_feasibility.csv`, L826 `ablation_study.csv`, L912 `moe_routing.csv`, L915 `tsne_clustering.csv`)을 완전 삭제하고 자연스러운 학술적 실험 맥락 문장으로 대체.
   - **R1.3 소괄호 감축 및 중복 약어 제거**:
     - 중복 약어 정의 제거(FSM L91, SAC L126, REMO-DQN L70 등은 이미 정의되었으므로 약어만 표기).
     - 괄호 내 데이터 나열(L66, L183, L453, L596, L636, L719, L721, L793, L826, L935 등)을 자연스러운 산문체(prose) 문장으로 전환.
   - **R1.4 문단 완결성(5문장 이상) 확보**:
     - 짧게 분절된 단락(L133, L173, L182-183, L632, L636/L638, L706-716, L822, L826, L915, L935 등)을 자연스럽게 병합하고 심층 논의 문장을 보강하여 모든 단락이 5문장 이상의 구조적 완결성을 갖추도록 교정.
5. 파일 수정 후 파일 락을 해제하세요:
   `python3 /home/imnyj/Command/core/lock_manager.py release /home/imnyj/Workspace/paper4/latex/main.tex worker_m2`
6. 감사 로그를 기록하세요:
   `python3 /home/imnyj/Command/core/audit_logger.py log --agent worker_m2 --file /home/imnyj/Workspace/paper4/latex/main.tex --action "Academic style revision, forbidden words removal, filename removal, parentheses reduction, and paragraph completeness enhancement (R1)"`
7. 검증 실행:
   - `python3 /home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py` 실행
   - 금지어 전수 검사 Python 스크립트 실행
   - 파일명 노출 검사 Python 스크립트 실행
8. 작업 결과 및 검증 결과를 `/home/imnyj/Workspace/paper4/latex/.agents/worker_m2/changes.md` 및 `handoff.md`에 작성하고 부모에게 send_message로 보고하세요.
