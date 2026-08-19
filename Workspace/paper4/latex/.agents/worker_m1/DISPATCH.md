## 2026-08-18T08:29:05Z

<USER_REQUEST>
당신은 Milestone 1을 수행하는 Academic Worker (worker_m1)입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/latex/.agents/worker_m1
요구사항 원본: /home/imnyj/Workspace/paper4/latex/.agents/ORIGINAL_REQUEST.md
프로젝트 문서: /home/imnyj/Workspace/paper4/latex/PROJECT.md
참조 핸드오프: /home/imnyj/Workspace/paper4/latex/.agents/explorer_2/handoff.md
관련 스킬: /home/imnyj/.agents/skills/academic-worker/SKILL.md, /home/imnyj/.agents/skills/anti-hallucination/SKILL.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행 지침 및 GEMINI.md 규칙 준수]
1. 원본 요구사항(ORIGINAL_REQUEST.md), 프로젝트 계획(PROJECT.md), Explorer 2의 조사 보고서(/home/imnyj/Workspace/paper4/latex/.agents/explorer_2/handoff.md)를 숙지하세요.
2. 작업 전 `/home/imnyj/Workspace/paper4/latex/backup/` 디렉토리에 `main.tex` 백업본 (`backup/main.tex.bak_m1`)을 생성하세요.
3. 파일 수정 전 반드시 파일 락을 획득하세요:
   `python3 /home/imnyj/Command/core/lock_manager.py acquire /home/imnyj/Workspace/paper4/latex/main.tex worker_m1`
4. `/home/imnyj/Workspace/paper4/latex/main.tex` 파일에 다음 변경사항을 정확히 적용하세요:
   - R2 (Introduction Contributions): Line 72~78의 4개 기여 항목을 `\begin{itemize} ... \end{itemize}` 환경으로 선언하고, 금지어(Comprehensive, systematic) 배제 및 수치 산문체로 정제 (Explorer 2 Section 4.A 코드 스니펫 준용).
   - R3 (Related Works Table I): Line 138~163의 Table I에서 'Year' 열을 헤더 및 데이터 행(13개)에서 전면 삭제(6열->5열), 저자명 표기를 삭제하고 순수 `\cite{}` 키로만 표기, 캡션에서 금지어 수정, `tabularx` 열 너비 초과 방지를 위한 `>{\centering\arraybackslash}p{2.2cm} L L >{\centering\arraybackslash}p{2.0cm} >{\centering\arraybackslash}p{2.8cm}` 적용 (Explorer 2 Section 4.B 코드 스니펫 준용).
5. 파일 수정 후 파일 락을 해제하세요:
   `python3 /home/imnyj/Command/core/lock_manager.py release /home/imnyj/Workspace/paper4/latex/main.tex worker_m1`
6. 감사 로그를 기록하세요:
   `python3 /home/imnyj/Command/core/audit_logger.py log --agent worker_m1 --file /home/imnyj/Workspace/paper4/latex/main.tex --action "Restructure Introduction contributions itemize (R2) and Table I without authors/year and with fixed width (R3)"`
7. 정적 검증 스크립트를 실행하여 검증하세요:
   `python3 /home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py`
8. 작업 결과 및 검증 결과를 `/home/imnyj/Workspace/paper4/latex/.agents/worker_m1/changes.md` 및 `handoff.md`에 작성하고 부모에게 send_message로 보고하세요.

</USER_REQUEST>
