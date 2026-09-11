# bot 프로젝트 작업 계획

- 목표: 친구의 Windows Claude Code CLI가 읽고 스스로 디스코드 연동 스킬(discord-link)을 구현하도록 하는 프롬프트를 만든다.
- 전달 형태: 프롬프트만 전달한다(2026-09-11 사용자 결정). 코드 패키지는 전달하지 않는다.
- 대상 운영체제: Windows(2026-09-11 사용자 결정).

## 요구사항 (사용자 원문 요약)
1. 백그라운드 리스너로 메인 세션에 영향 없이 디스코드 답장을 주고받는다.
2. 토큰과 채널 ID를 운용할 파일을 만들고 사용자에게 입력 위치를 알려 준다.
3. 스킬로 등록해 이후 세션에서 스킬만 부르면 바로 채널에 붙는다.
4. 세션명 기반으로 구분해 세션 사이 혼동을 막는다.
5. 기타 필요한 프롬프트(일상 사용, 점검, 해제, 문제 해결).

## 산출물
- prompts/01_install_prompt.md : 친구가 붙여 넣는 설치 프롬프트(구현 명세 포함)
- prompts/02_usage_prompts.md : 설치 뒤 쓰는 짧은 프롬프트 모음
- README.md : 전달 방법과 파일 설명

## 단계
1. [완료] 기존 dcbridge.py 구조 파악, 세션명 저장 위치 확인
2. [완료] Claude Code의 Windows 동작 문서 조사 (hooks.md, skills.md, tools-reference.md 직접 확인)
3. [완료] 설치 프롬프트 초안 작성
4. [완료] 검증 두 갈래: (a) 시험 구현(오프라인 18/18 통과, 메인 재실행 확인) (b) 사실 검증
5. [완료] 1차 개정(553줄) → 재검토 → 2차 개정(603줄). 내역은 etc/logs/verification.md
6. [완료] 사용 프롬프트 모음과 README 갱신, 최종 보고
7. [선택, 미실행] 2차 개정판으로 시험 구현 재실행 (사용자 판단 대기)

## 문서로 확인한 사실 (2026-09-11)
- 훅 command 핸들러는 `args` 배열(exec 형식)을 지원하며 이때 셸을 거치지 않는다. 셸 형식 기본값은 bash, Windows 에 Git Bash 가 없으면 powershell.
- 스킬 본문 치환: `$ARGUMENTS`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`. 스킬 폴더가 세션 시작 때 있었다면 새 스킬은 재시작 없이 인식된다.
- Monitor 는 Bedrock/Vertex/Foundry, `DISABLE_TELEMETRY`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` 에서 쓸 수 없다.
- Stop 훅은 `last_assistant_message` 를 받는다. 훅/Bash 의 세션 ID 환경 변수는 문서에 없다(스킬 치환만 문서화).
- 실제 settings.json 체크섬: etc/logs/settings_checksum_before.txt (시험 에이전트가 실제 설정을 건드리지 않았는지 대조용)

## 확인된 사실
- /rename 과 `claude -n/--name` 으로 세션 표시 이름을 지정할 수 있다(CLI 2.1.268 도움말).
- 표시 이름은 ~/.claude/sessions/<PID>.json 의 name 필드와 대화 기록 jsonl 의 custom-title 레코드에 남는다. 비공식 형식이다.
- Bash 도구 환경에 CLAUDE_CODE_SESSION_ID, CLAUDE_PID 환경 변수가 있다(Linux에서 확인).
