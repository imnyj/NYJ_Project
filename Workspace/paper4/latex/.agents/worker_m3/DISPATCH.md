## 2026-08-18T08:36:17Z
당신은 Milestone 3을 수행하는 Verification & Packaging Worker (worker_m3)입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/latex/.agents/worker_m3
요구사항 원본: /home/imnyj/Workspace/paper4/latex/.agents/ORIGINAL_REQUEST.md
프로젝트 문서: /home/imnyj/Workspace/paper4/latex/PROJECT.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행 지침]
1. M1과 M2 수정을 거친 /home/imnyj/Workspace/paper4/latex/main.tex 파일에 대해 R4 수식 검증 및 빌드 패키징을 수행하세요:
   - 모든 32개 디스플레이 수식(equation, align)과 300+개 인라인 수식 구분자($)의 문법 오류, 첨자/위첨자, 표기법 일관성(로만체, 볼드 벡터) 최종 검증.
   - 프로젝트 정적 검증 스크립트 실행: `python3 /home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py` (Tier 1~4 전수 통과 확인).
   - 배포 패키지 생성 및 무결성 검증: `cd /home/imnyj/Workspace/paper4/latex && make zip && unzip -l paper4_latex_overleaf.zip`.
2. 전체 요구사항(R1~R4)에 대한 종합 무결성 테스트를 실행하고, 결과를 /home/imnyj/Workspace/paper4/latex/.agents/worker_m3/changes.md 및 handoff.md에 상세히 기록하세요.
3. 작업 완료 후 부모에게 send_message로 보고하세요.
