# qwen-loop v0.3

자가 수정 가능한 Qwen 비서. flat layout + 외부 정책 파일 + watchdog 자동 재시작.

## v0.3의 새로운 점

- **디렉토리 재구성**: `src/qwen_loop/` → `qwen_loop/`. flat layout.
- **외부 정책 파일**: `~/.config/qwen-loop/policy.yaml`. chat이 절대 수정 불가.
- **자가 수정 엔진**: `/upgrade <파일> <설명>`. 시범 운영 → 5회 재시도 → 성공 시 적용, 실패 시 원본 유지.
- **watchdog**: chat.py 자기 수정 후 자동 재시작.
- **백업**: 매 자가 수정마다 `.history/` 사본. git 없이도 복구 가능.

## 처음 한 번 — 정책 파일 만들기

이게 첫 단계입니다. 정책 없으면 chat이 시작조차 안 합니다.

```bash
cd ~/qwen-loop                            # 또는 압축 푼 위치
mkdir -p ~/.config/qwen-loop
cp policy_template/policy.yaml ~/.config/qwen-loop/policy.yaml

# project_root를 본인 환경에 맞게 수정
$EDITOR ~/.config/qwen-loop/policy.yaml
# project_root: "/home/imnyj/qwen-loop"  ← 본인 경로로

# 권장: 읽기 전용 잠금
chmod 444 ~/.config/qwen-loop/policy.yaml
```

## 실행 두 가지 방법

### A. 단순 실행 (자가 수정 시 수동 재실행)

```bash
cd ~/qwen-loop
source .venv/bin/activate
python scripts/chat.py
```

chat.py가 자가 수정되면 종료 후 다시 실행해야 합니다.

### B. watchdog (자가 수정 시 자동 재시작) — 권장

```bash
cd ~/qwen-loop
source .venv/bin/activate
tmux new -s qwen-loop
python scripts/watchdog.py
# Ctrl+B, D 로 detach
```

watchdog이 chat.py를 띄우고, 자가 수정으로 종료되면 자동으로 다시 띄웁니다.

## 자가 수정 사용법

```
> /upgrade scripts/chat.py /clear 명령에 확인 프롬프트를 추가해줘

╭─ 자가 수정 요청 ─╮
│ 대상: scripts/chat.py (chat.py 자기 자신!) │
│ 설명: /clear 명령에 확인 프롬프트을 추가해줘 │
│ 흐름: 원본 백업 → 시범 운영 → 시범 통과 시 적용 → 실패 시 최대 5회 재시도 │
╰────────────────╯
진행? [y/N]: y

   📦 백업: 20260430-150301__scripts__chat.py
   🔁 시도 1/5
   → ✅ 통과: passed
✅ 자가 수정 성공
chat.py가 변경되었습니다.
지금 재시작? [Y/n]: y
[watchdog이 새 chat.py로 다시 띄움]
```

## 안전 모델

| 항목 | 보호 |
|---|---|
| `~/imnyj/paper-ai/`, `~/.ssh/`, `/etc/` | 절대 접근 불가 (project_root 밖) |
| `~/.config/qwen-loop/policy.yaml` | chat 안에서 수정 불가 |
| `protected_paths` 안 파일들 | 자가 수정 불가 (정책에 정의) |
| 자가 수정 횟수 | 일 10회 + 5분 cooldown (정책에서 변경) |
| 시범 운영 실패 시 | 원본 손대지 않음 |
| 모든 변경 | `.history/` 백업 + `.history/upgrade-log.jsonl` |
| 위반 시도 | `.violations.log` 기록 + 사용자에게 알림 |

`protected_paths`를 빈 리스트로 두면 chat이 자기 자신 포함 모든 파일 수정 가능. 정책 파일이 외부에 있어 보호되므로 이게 안전한 기본값.

## 디렉토리 구조

```
qwen-loop/
├── pyproject.toml
├── config.yaml
├── policy_template/
│   └── policy.yaml          ← 사용자가 ~/.config/qwen-loop/ 로 복사
├── prompts/                 ← 프롬프트 버전들 (자가 수정 가능)
├── qwen_loop/               ← 메인 패키지
│   ├── __init__.py
│   ├── llm.py
│   ├── agent.py
│   ├── memory/
│   ├── reasoning/
│   ├── annotation/
│   ├── self_upgrade/        ← prompt A/B + reflector (기존)
│   ├── safety/              ← NEW: policy + guard + self_upgrade_engine
│   └── tools/
│       ├── workspace.py     ← Guard 통합
│       └── web.py
├── scripts/
│   ├── chat.py              ← 자가 수정 통합
│   ├── watchdog.py          ← NEW: 자동 재시작 감시자
│   ├── run.py
│   ├── serve.py
│   └── ingest.py
└── (런타임 생성)
    ├── data/                ← chroma + sqlite
    ├── outputs/             ← 마크다운 결과물
    ├── ingest/              ← 개인 자료 (read-only로 두는 게 안전)
    ├── .history/            ← 자가 수정 백업 + 로그
    ├── .backup/             ← 일반 파일 작업 백업
    ├── .trash/              ← 삭제된 파일
    ├── .violations.log      ← 정책 위반 시도 기록
    ├── .watchdog.log        ← watchdog 로그
    └── .restart_requested   ← 재시작 신호 (watchdog용)
```

## 슬래시 명령 전체

```
대화/모드:    /kind /list /rag /tools /yolo /workspace
도구 명시:    /ls /read /edit /web /fetch
자가 수정:    /upgrade /history /restore /policy
유틸:         /multi /show /save /clear /quit /help
```

## 복구

자가 수정으로 뭔가 망가졌을 때:

```bash
# chat 안에서
> /history                          # 최근 자가 수정 이력 보기
> /restore 20260430-150301__scripts__chat.py   # 백업에서 복원

# chat 자체가 안 켜지면 셸에서
ls .history/                        # 백업 파일들
cp .history/20260430-150301__scripts__chat.py scripts/chat.py
```

## 마이그레이션 (v0.2 → v0.3)

기존 v0.2 워크스테이션에서 v0.3으로 옮기실 때:

```bash
# 1. 데이터 백업
cp -r ~/qwen-loop/data ~/qwen-loop-data-backup
cp -r ~/qwen-loop/outputs ~/qwen-loop-outputs-backup
cp -r ~/qwen-loop/ingest ~/qwen-loop-ingest-backup

# 2. v0.3 압축 풀기 (다른 위치에)
tar -xzf qwen-loop-v3.tar.gz
mv qwen-loop-v3 ~/qwen-loop-new

# 3. 데이터 옮기기
mv ~/qwen-loop-data-backup ~/qwen-loop-new/data
mv ~/qwen-loop-outputs-backup ~/qwen-loop-new/outputs
mv ~/qwen-loop-ingest-backup ~/qwen-loop-new/ingest

# 4. 옛 폴더 보관, 새 폴더로 교체
mv ~/qwen-loop ~/qwen-loop-old-v0.2
mv ~/qwen-loop-new ~/qwen-loop

# 5. 의존성 다시 설치
cd ~/qwen-loop
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 6. 정책 파일 만들기 (위 "처음 한 번" 섹션)

# 7. 동작 확인 후 옛 폴더 삭제
rm -rf ~/qwen-loop-old-v0.2
```
