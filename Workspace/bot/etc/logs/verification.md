# 검증 기록

## 1. 기술 사실 검증 (2026-09-11, 사실 검증 서브에이전트)

설치 프롬프트 초안(438줄 판)의 기술 주장을 공식 문서와 신뢰할 수 있는 자료로 대조했다. 주요 판정은 아래와 같다.
메인 세션이 공식 문서 원문(curl)으로 다시 확인한 항목은 [메인 재확인] 으로 표시했다.

### 고쳐야 할 항목
| 절 | 판정 | 내용 | 반영 방향 |
|---|---|---|---|
| 8.3 | 틀림 | `CLAUDE_PID` 는 공식 환경 변수다(v2.1.214+, Bash/PowerShell 도구와 훅 하위 프로세스). [메인 재확인: env-vars.md 401행] | 공식 변수로 고쳐 쓰고, 없으면 확인을 건너뛴다 |
| 5.1 | 부분 | SessionStart 훅 입력에 공식 필드 `session_title` 이 있다(`--name`, `/rename` 값). [메인 재확인: hooks.md 1142~1149행] | SessionStart 에서는 `session_title` 을 먼저 쓰고 비공식 파일은 대체 수단으로 둔다 |
| 5.1 | 보강 | `CLAUDE_CODE_SESSION_ID` 는 Bash/PowerShell 도구와 훅에 공식 제공되며 `/clear` 때 갱신된다. `--continue` 나 ID 없는 `--resume` 에서는 처음 시작한 ID 가 들어올 수 있다. [메인 재확인: env-vars.md 351행] | 스킬에서는 `${CLAUDE_SESSION_ID}` 를 우선하고 환경 변수는 대체로 쓴다 |
| 보강 | 신규 | SessionStart 와 UserPromptSubmit 훅 출력의 `sessionTitle` 로 세션 제목을 바꿀 수 있다(`/rename` 과 같은 효과). [메인 재확인: hooks.md 1185, 1374행] | 스킬 인자로 정한 이름을 터미널 세션 제목과 맞추는 선택 기능으로 넣는다 |
| 9.1 | 부분 | 콘솔 직접 출력은 UTF-8 이지만, 파이프(Monitor, 훅)에 연결되면 ANSI 코드 페이지(cp949)를 쓴다 | 설명을 파이프 기준으로 고친다. 대처(`reconfigure`)는 그대로 둔다 |
| 6.2 | 부분 | 보관된 스레드는 메시지를 보내면 자동 해제된다. 잠긴 스레드는 160005, 50083 은 메시지 수정 같은 작업에서 난다 | 전송 실패가 160005/50083 일 때만 PATCH 를 시도한다 |
| 5.3 | 부분 | 스레드 이름 변경 제한(10분 2회)은 공식 문서에 없고 커뮤니티 관측이다. 관측된 `retry_after` 는 약 582초다 | `retry_after` 가 30초보다 길면 재시도하지 않는다 |
| 부록 A | 부분 | 특권 인텐트 기준 설명이 부정확하다. 개인 봇은 포털에서 켜면 된다는 결론은 맞다 | 문구를 "개인용 봇은 심사 없이 켤 수 있다" 로 줄인다 |
| 7장 | 부분 | `os.startfile` 은 메모장이 아니라 확장자 연결 프로그램으로 연다 | `notepad.exe` 를 직접 실행한다 |
| 6.1 | 확인 못함 | 스레드 ID 로 메시지 조회가 되는지는 문서 문구가 없다(추론으로는 동작). 조회 결과는 최신순으로 온다 | ID 오름차순 재정렬, 100건이면 이어서 조회 |

### 목록 밖에서 발견된 문제
1. 5.1 과 3장의 `.claude` 경로도 `CLAUDE_CONFIG_DIR` 을 따라야 한다.
2. `msvcrt.locking` 전에 파일 위치를 0으로 옮겨야 하고, 잠긴 바이트에 PID 를 쓰면 다른 프로세스가 읽지 못한다(강제 잠금).
3. ctypes `OpenProcess` 는 반환형 지정, `CloseHandle`, 실패 시 없는 프로세스로 판정이 필요하다.
4. Windows 에서 `os.replace` 재시도는 1초 정도까지 늘리는 편이 안전하다.
5. 스킬 인자에 따옴표가 들어가면 명령 문자열이 깨진다.
6. `argument-hint` 는 로컬 스킬에서는 문제없지만 claude.ai 업로드 때 거부된다.

### 사실로 확인된 항목(요약)
`os.kill(pid, 0)` 위험, `msvcrt.locking` 배타 잠금, `GetExitCodeProcess` 259, `os.getppid()` 한계, `reconfigure`(3.7+), `os.replace` 의
PermissionError, 디스코드 User-Agent 형식, 권한 값 309237713920(비트 10, 11, 16, 35, 38 합), 429 `retry_after`, 2000자 제한, 스레드 생성
엔드포인트와 `auto_archive_duration` 값, `allowed_mentions`, 훅 exec 형식과 `shell` 필드, SessionStart source 와 SessionEnd reason 의 `clear`,
`/clear` 뒤 새 세션 ID, Stop 훅의 `last_assistant_message`, `agent_id`, additionalContext 형식, 스킬 치환 변수, `CLAUDE_CONFIG_DIR`, Monitor 사용 조건.

## 2. 시험 구현 (2026-09-11, 시험 구현 서브에이전트, 438줄 판 프롬프트 기준)

- 가짜 홈: /tmp/claude-1001/-home-imnyj/c2a2766b-5c17-4297-b125-cc6f4187a91a/scratchpad/friend_home
- 결과: 프롬프트만으로 dclink.py(2017줄)와 테스트(18개)를 구현했다. 메인 세션이 CLAUDE* 환경 변수를 지우고 다시 실행해 18개 통과를 확인했다(18.99초). [EVIDENCE: TEST]
- 실제 설정 보호: 시험 뒤 실제 settings.json 체크섬이 시험 전과 같고(sha256 OK), ~/.discord-link 가 없고, settings.json 에 dclink 문자열이 0건이다. [EVIDENCE: RUNTIME]
- 메인 재확인: ~/.claude/sessions/*.json 에 nameSource "derived" 인 자동 이름이 실제로 있다. SessionEnd 훅 예산은 기본 1.5초이고 설정된 timeout 최댓값까지(최대 60초) 늘어난다(hooks.md 3315행, env-vars.md 350행). [EVIDENCE: DATA]

### 시험 구현이 찾은 프롬프트 결함과 반영 (개정판 01_install_prompt.md)
| 결함 | 반영 위치 |
|---|---|
| 자동 이름(nameSource derived)이 표시 이름으로 섞임 | 5.2 |
| 재개한 세션의 리스너가 ended_at 때문에 곧바로 끝남 | 5.4, 8.3 |
| 기록 없는 새 세션 ID 에서 /clear 인계가 8.2 와 충돌 | 8.2 예외 |
| 채널 본문 메시지에 스레드에서 답장 불가 | 6.5 답장 위치 |
| 조회 결과 최신순, 100건 페이징 | 6.1 |
| SessionEnd 1.5초 예산 | 8.3 (파일 기록 먼저) |
| -2 접미사 세션의 무한 rename | 5.4 base_name |
| 테스트 격리(CLAUDE* 변수), 느린 대기, unittest discover | 12.1, 3장, 8.4 |
| argparse 종료 코드 2 겹침 | 7장 |
| 셸 판별 수단 부재 | 7장 MONITOR_COMMAND 두 줄, 8.1 --shell-form bash/powershell, 8.2 receive_mode |
| SKILL.md 생성 시점, 인자 따옴표·$ 확장, 치환 실패 감지 | 10장, 5.1 |
| link 시점 대화 기록 경로 | 5.2 (설정 폴더 projects 탐색) |
| Stop 훅 30초 초과 가능 | 8.2 시간 예산 |
| 세션 기록 동시 쓰기 | 7장 기록 잠금 |
| 6.3 미정 동작(@없는이름, 문장 부호, 제어어 판정, 시스템·웹후크, 첨부, 표시 이름) | 6.3, 6.4 |
| 턴 번호·소요 시간 정의, 턴 경계 경합 | 6.5 (대화 기록에 message ID 가 있을 때만 답장) |
| 정규화 순서, 32자와 접미사, 기본 이름 길이, 채널 변경 | 5.3, 5.4 |
| 메모장 BOM, cp949 저장 | 4장, 9장 |
| msvcrt 위치·강제 잠금, 잠금 확인 경합, ctypes 세부 | 8.4 |
| 스토어판 파이썬 | 8.1 (py.exe 대체) |

## 3. 개정판 재검토 (2026-09-11, 재검토 서브에이전트, 553줄 판 기준)

주의: 1장 표의 절 번호는 438줄 판 기준이다. 553줄 판에서는 CLAUDE_PID 가 8.4, session_title 이 5.2, 이름 변경 제한이 5.5 에 있다.

### 메인 재확인
- 스레드를 만든 쪽은 MANAGE_THREADS 없이 스레드 이름을 바꿀 수 있다(docs.discord.com topics/threads: "Editing a thread to change the name, archived, auto_archive_duration fields requires MANAGE_THREADS or that the current user is the thread creator"). 재검토가 제기한 권한 우려는 해당하지 않는다. [EVIDENCE: DATA]
- hooks.md 1033행: additionalContext 는 명령문이 아니라 사실 서술로 써야 프롬프트 인젝션 방어에 걸리지 않는다. hooks.md 756행: transcript 는 비동기로 기록되어 현재 턴의 최신 메시지가 없을 수 있다. [EVIDENCE: DATA]

### 지적과 반영 (2차 개정판)
| 구분 | 지적 | 반영 |
|---|---|---|
| 모순 | 8.2 의 켜진 기록 조건 때문에 재개 세션 훅이 스스로 막힘, updated_at 갱신 주체 없음 | 8.2: 훅은 enabled 만 본다. 5.4: 기록을 고칠 때마다 updated_at 갱신 |
| 모순 | 5.6 뒤 -2 세션의 잘못된 이름 변경 알림, rename 을 display 가 되돌림 | 5.5, 5.6, 7장 rename |
| 모순 | link.log 에 정상 기록이 없어 설치 확인 불가 | 8.2: 훅마다 한 줄 기록 |
| 모순 | 훅 미발동 때 대처 순서 | 8.1, 11장 7단계 정리 |
| 모순 | 12.1-19 의 160005 설명, 12.1-11 의 시간, 6.1 과 5.5 의 재시도, 11장 2단계 | 각 절 수정 |
| 누락 | PowerShell 에서 빈 인자 '' 가 사라짐 | 10장: 인자가 없으면 --name 을 빼고 실행 |
| 누락 | Monitor 리스너에 CLAUDE_PID 가 들어온다는 보장 없음 | 7장·8.4: 리스너 명령에 --claude-pid 를 넣음 |
| 누락 | receive_mode 를 바꾸는 수단 없음, 셸 판별 | 7장 link --receive-mode, 10장 절차 3 |
| 누락 | 테스트 프로세스 자신의 CLAUDE* 변수 | 12.1 |
| 누락 | 대화 기록 비동기, 대기 목록 만료, 소요 시간 누적 | 6.5, 11장 1단계 |
| 누락 | @이름 토큰 끝과 대소문자 | 6.3 |
| 공백 | /clear 인계 항목(커서 등), 리스너가 죽은 세션, @all 과 제어어, 발신자 제한, handover 파일 하나 | 8.5, 6.3, 6.4, 4장 allowed_user_ids, 3장 |
| 사실 | additionalContext 명령문 문구 | 8.2 안내문을 사실 서술로 |
| 사실 | 스토어판 파이썬 판정과 py.exe 위치 | 8.1, 11장 1단계 |
| 데이터 | 자동 제목은 ai-title 레코드로 따로 남음 | 5.2 |

- 2차 개정 적용: 수정 33건, 모두 적용 성공. 옛 표기(`handover.json`, `--name ''`) 잔존 여부를 grep 으로 점검했다.
- 스레드 이름 PATCH 권한 우려는 스레드 생성자 예외로 해소되어 부록 A 권한 값은 바꾸지 않았다.

## 4. 남은 한계
- 2차 개정판(603줄)으로 처음부터 다시 구현하는 시험은 하지 않았다. 필요하면 1차와 같은 방식(가짜 홈, 새 서브에이전트)으로 재시험한다.
- Windows 실기 동작(msvcrt, ctypes, PowerShell 인자 처리, exec 형식 훅, Monitor 셸)은 확인하지 못했다. [UNKNOWN]
- Monitor 알림이 대화 기록에 남는 형식은 친구 PC 에서 11장 1단계로 확인하도록 했다. [UNKNOWN]

## 5. 워크스테이션 브리지 실사용 결함과 반영 (2026-09-11 오후)

이 워크스테이션의 discord-bridge 를 실제로 쓰다가 드러난 결함을 고치고, 같은 교훈을 설치 프롬프트에 넣었다.

| 결함 | 증거 | 워크스테이션 수정 | 설치 프롬프트 반영 |
|---|---|---|---|
| 채널 본문 호출 무반응: 스레드 세션 리스너가 스레드만 조회, `<@봇ID>` 멘션을 모름 | 채널 메시지 `<@1547779667564695653> 테스트...` | 채널 본문 조회, 봇 멘션 인식, 온 채널에 답장 | 6.3 표와 설명, 12.1-26 |
| `@Bot` 자동완성이 역할 멘션 `<@&역할ID>` 로 들어와 무반응 | 역할 1547780268381704352 의 tags.bot_id 가 봇 ID | 관리 역할 멘션 인식 | 6.3 설명, 12.1-26 |
| 팀 메일 미전달: 리스너가 팀 소속을 시작할 때 한 번만 확인 | 리스너 12:37 시작, teams.conf 12:43 수정 | 매 주기 팀 정의 재확인, 공유 채널 전환 | 6.6, 12.1-28 |
| 봇 메시지 전면 무시로 bot2 의 디스코드 호출 무반응 | bot2 의 역할 멘션 메시지 | 등록된 브리지 봇의 명시적 호출만 수신, 연속 10회 상한 | 6.7(선택 확장), 6.6 상한, 12.1-29 |
| 코드 갱신이 돌고 있는 리스너에 반영되지 않음 | paper4, paper2, bot2 리스너가 옛 코드 | 스크립트 변경 감지 뒤 os.execv 자동 재시작 | 8.4(Windows 는 종료와 재실행 안내), 12.1-31 |

- 회귀 테스트: ~/.claude/skills/discord-bridge/tests/test_listen.py 45/45 통과. 각 수정 전 판에서는 해당 테스트가 실패했다. [EVIDENCE: TEST]
- 실사용 확인: 역할 멘션과 봇 멘션 호출에 채널 본문 답장, bot2 와 팀 메일 대화 2회, 스크립트 수정 시각 변경 때 bot·bot2·paper2·paper4 리스너가 같은 PID 로 자동 재시작(13:03). [EVIDENCE: RUNTIME]
