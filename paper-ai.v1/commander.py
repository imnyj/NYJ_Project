# commander.py
"""Top-level orchestrator agent.

This is the user's original Commander prompt and managed_agents
structure (now 6 agents instead of 8 — Experimenter and Reviewer
absorb their sub-roles), enriched with our infrastructure:

  * Vault unlock — if .env contains ENC: entries, prompt for the
    password (or read it from stdin under watchdog).
  * LiteLLM cost tracking — install the bridge so PolicyRuntime
    sees every Anthropic call smolagents makes.
  * Blue-Green self-upgrade hooks — when Commander wants to rewrite
    its own code, it stages new files under
    `staging/`, writes UPGRADE_READY marker, and exits cleanly.
    The watchdog then atomically swaps and restarts.

CLI
---
  python commander.py                  # interactive REPL
  python commander.py Command.md       # run a command file once

The watchdog handles upgrade promotion (no `--upgrade-check` flag
needed on the Commander side anymore — see monitoring/watchdog.py
and monitoring/blue_green.py).

Watchdog stdin protocol
-----------------------
When PAPER_AI_UNLOCK_FROM_STDIN=1 is set (the watchdog sets this
when spawning), Commander reads one line from stdin as the vault
password instead of prompting interactively. After consuming the
line, /dev/tty is reopened so the REPL's input() still works.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────────────────────────── bootstrap
# Vault unlock MUST happen before any module that calls get_api_key
# is imported. We do it conditionally based on env presence.

def _bootstrap_vault() -> None:
    """Unlock the encrypted .env if ENC: entries are present.

    Three scenarios:
      1. No vault in use (no ENC: lines) → no-op.
      2. PAPER_AI_UNLOCK_FROM_STDIN=1 → read password from stdin
         (watchdog protocol). Re-attaches stdin to /dev/tty after
         consuming the password line.
      3. Interactive run → prompt with getpass.
    """
    try:
        from core.secrets_vault import has_any_encrypted, load_env_file
    except ImportError:
        return  # cryptography not installed — vault unavailable
    try:
        lines = load_env_file(Path(__file__).parent)
    except Exception:
        return
    if not has_any_encrypted(lines):
        return

    from core.unlock import unlock_from_stdin, unlock, is_unlocked
    if is_unlocked():
        return

    if os.getenv("PAPER_AI_UNLOCK_FROM_STDIN") == "1":
        # Watchdog wrote one password line into our pipe; consume it
        # and switch stdin to /dev/tty for the REPL.
        unlock_from_stdin(Path(__file__).parent)
    else:
        import getpass
        try:
            pw = getpass.getpass("Vault password: ")
        except (EOFError, KeyboardInterrupt):
            print("\naborted at password prompt.", file=sys.stderr)
            sys.exit(2)
        try:
            unlock(Path(__file__).parent, pw)
        except Exception as e:
            print(f"unlock failed: {e}", file=sys.stderr)
            sys.exit(2)
        finally:
            # Best-effort wipe — Python can't truly scrub a string but
            # we drop our reference.
            pw = "x" * len(pw) if pw else ""
            del pw


_bootstrap_vault()


# ──────────────────────────────────────────────────────────────────── autosave → PAPER_BASE_DIR
# This MUST run before `from config import ...` because config.py
# resolves BASE_DIR at module import time. If we wait until main(),
# every other module that read BASE_DIR (interface.py, agents/*) has
# already cached the wrong value.
#
# Resolution rules:
#   1. --autosave NAME     → papers/NAME/  (registers in paper_registry)
#   2. --resume NAME       → same (existing entry expected)
#   3. PAPER_BASE_DIR env  → use as-is, no registry interaction
#   4. neither             → fall through to config.py's default
#                            (PAPER_AI_ROOT/workspace)

def _bootstrap_paper_dir() -> str | None:
    """Inspect argv for --autosave/--resume, set PAPER_BASE_DIR, return name.

    Returns the session name if --autosave or --resume was given, else
    None. The caller (main()) reuses this name; we re-extract here so
    we can run BEFORE config import.
    """
    name = None
    raw = sys.argv[1:]
    i = 0
    while i < len(raw):
        if raw[i] in ("--autosave", "--resume") and i + 1 < len(raw):
            name = raw[i + 1]
            break
        i += 1

    if not name:
        return None

    # Resolve via the registry. This:
    #   * validates name (rejects "../", spaces, etc.)
    #   * creates papers/<name>/ if new
    #   * bumps last_accessed
    #   * regenerates list.md
    try:
        from core.paper_registry import resolve_or_create
        entry = resolve_or_create(name)
    except ValueError as e:
        print(f"[autosave] {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        # Non-fatal: registry unavailable (corrupted JSON, disk full).
        # Fall back to env var or default. We log to stderr because
        # logging isn't configured yet at this point in bootstrap.
        print(f"[autosave] registry unavailable, falling back: {e}",
              file=sys.stderr)
        return name

    # Override env so config.py picks it up. The env var also gets
    # inherited by any subprocess this commander spawns later
    # (e.g. test_staged_upgrade).
    os.environ["PAPER_BASE_DIR"] = str(entry.path)

    # Tag a flag so main() knows whether this was a fresh registration
    # (worth surfacing to the user) vs a re-open.
    if entry.is_new:
        os.environ["_PAPER_AI_BOOT_NEW_REG"] = "1"

    return name


_BOOT_AUTOSAVE_NAME = _bootstrap_paper_dir()


# ──────────────────────────────────────────────────────────────────── logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("commander.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("Commander")


# ──────────────────────────────────────────────────────────────────── imports
# These trigger get_api_key() at module load time, which is why the
# vault must be unlocked first.

from config import (
    get_api_key, get_model_id, MAX_STEPS, MAX_RETRIES,
    PATHS, BASE_DIR, PAPER_AI_ROOT, init_directories,
)
from interface import COMMON_INTERFACE
from tools import (
    FileReadTool, FileWriteTool, DirectoryListTool,
    StageUpgradeTool, TestStagedUpgradeTool,
    FinalizeUpgradeTool, AbortUpgradeTool,
)

from smolagents import CodeAgent, LiteLLMModel, PythonInterpreterTool

# Cost tracking: install the LiteLLM ↔ PolicyRuntime bridge BEFORE
# any agent's CodeAgent.run() fires. Otherwise the first turn's
# tokens go untracked.
try:
    from core.policy_runtime import PolicyRuntime
    from core.litellm_bridge import install as install_cost_bridge

    _policy = PolicyRuntime(config_dir=str(PAPER_AI_ROOT / "config"))
    install_cost_bridge(_policy, project_root=PAPER_AI_ROOT)
    logger.info("cost tracking enabled (LiteLLM ↔ PolicyRuntime, persistent)")
except Exception as e:
    logger.warning("cost tracking unavailable: %s", e)


init_directories()
logger.info("초기화 완료 (BASE_DIR=%s)", BASE_DIR)


# ──────────────────────────────────────────────────────────────────── upgrade hook
#
# The actual self-upgrade machinery lives in:
#   - tools/upgrade_tool.py     (Tools Commander calls during ReAct)
#   - monitoring/blue_green.py  (atomic swap + rollback, called by watchdog)
#
# This file just needs the marker path so the REPL can detect that
# Commander asked for promotion (rare path — finalize_upgrade normally
# exits via os._exit before we get back here).

from monitoring.blue_green import marker_path as _marker_path
UPGRADE_READY_MARKER = _marker_path(PAPER_AI_ROOT)


# ──────────────────────────────────────────────────────────────────── model + agents

model = LiteLLMModel(
    model_id=f"anthropic/{get_model_id('commander')}",
    api_key=get_api_key("commander"),
)

from agents.idea         import idea_agent
from agents.librarian    import librarian_agent
from agents.experimenter import experimenter_agent
from agents.reviewer     import reviewer_agent
from agents.writer       import writer_agent
from agents.qwen         import qwen_agent


COMMANDER_PROMPT = f"""
당신은 IEEE Transactions 논문 투고를 위한 '총괄 디렉터(Commander)'입니다.

[⚡ 매 세션 시작 시 필수 절차]
1. context_state/pipeline_state.json 읽기 → 현재 진행 상태 파악
2. context_state/session_history.md에 새 세션 시작 기록
3. annotations/user_directives.md 읽기 → 사용자 지시사항 누적분 확인
4. brain/ 폴더 스캔 → 어떤 에이전트가 memory를 가지고 있는지 확인
5. 마지막 완료 단계 다음부터 이어서 진행

[핵심 역할]
1. 작업 흐름 제어 및 에이전트 소집
2. 품질 게이트: 산출물 검수, 불합격 시 재작업 지시
3. 분쟁 조율
4. (선택) 자기 코드 업그레이드 — staging/에 새 코드 작성 후 종료,
   Watchdog이 atomic swap + 재시작

[6 에이전트 파이프라인]
Phase 1 — 기초 설계
  ① Librarian → references.json + bibitem.tex
  ② Idea → idea_spec.md
  ③ 품질 게이트

Phase 2 — 실험 설계 + 구현 + 검증
  ④ Experimenter[Stage 1: design]    → experiment_spec.json
  ⑤ Experimenter[Stage 2: implement] → data/*.csv (libsumo)
  ⑥ Reviewer[Mode A: validator]      → validation_report.json
     FAIL → Experimenter[Stage 2] 재호출 (최대 {MAX_RETRIES}회)

Phase 3 — 시각화 + 집필 + 교정
  ⑦ Experimenter[Stage 3: visualize] → figure/*.png, graph/*.png
  ⑧ Writer (분할 호출 7회): 뼈대→Intro→RW→NetModel→Proposed→PerfEval→Conclusion+Bib
  ⑨ Reviewer[Mode B: proofreader]    → final/main.tex

[Stage/Mode 명시 규칙]
Experimenter 호출 시 항상 Stage 명시:
  "Experimenter, Stage 1 (design)으로 idea_spec.md를 읽고 experiment_spec.json 작성"
  "Experimenter, Stage 2 (implement)로 시뮬레이션 실행"
  "Experimenter, Stage 3 (visualize)으로 그래프 생성"

Reviewer 호출 시 항상 Mode 명시:
  "Reviewer, Mode A (validator)로 data/*.csv 검증"
  "Reviewer, Mode B (proofreader)로 draft/main.tex 교정"

[Writer 분할 작성 관리]
Writer에게 전체 논문을 한 번에 쓰라고 지시하지 마십시오.
호출 1: "뼈대 생성 (패키지, 제목, 저자, 섹션 헤더만)"
호출 2~7: "draft/main.tex를 읽고 [섹션명]의 TODO를 채우시오"

[에이전트 호출 시 지시 사항]
- 해당 에이전트에게 "먼저 brain/<agent>_memory.md를 읽으시오"라고 명시
- 입력 파일 경로를 명시적으로 전달
- Stage / Mode 항상 명시

[상태 관리 (.pipeline/)]
- pipeline_state.json: 매 단계 시작 시 "running", 완료 시 "done"으로 갱신
  Experimenter는 stages_done에 ["design", "implement", "visualize"] 누적
  Reviewer는 modes_done에 ["validator", "proofreader"] 누적
  Writer는 sections_done에 완료 섹션 누적
- decision_log.md: 주요 결정·방향 변경 시 근거와 함께 기록
- session_history.md: 세션 시작/종료 시점 기록
- annotations/user_directives.md: 사용자의 새 지시사항 수신 시 즉시 기록
- annotations/agent_notes.md: 에이전트 간 전달 사항 기록

[implicit/ 관리]
- Reviewer가 반복 오류 발견 시 error_patterns.md 갱신 지시
- 사용자 선호도 파악 시 user_preferences.md에 기록

[부분 재실행]
사용자가 특정 단계부터 재실행 요청 시:
1. 해당 단계의 입력 파일 존재 확인
2. pipeline_state.json에서 해당 단계부터 "pending"으로 리셋
3. 해당 단계부터 파이프라인 재개

[제약 사항]
- 직접 작문/코드 작성 금지. 평가와 방향성 지시만.

================================================================================
[비용 절감 — Qwen 위임 정책]
================================================================================
당신의 managed_agents에는 'Qwen'이 포함되어 있습니다. Qwen은 사용자의
GPU에서 실행되는 로컬 LLM으로, 호출 비용이 0달러입니다. 단, 추론 능력은
Sonnet/Opus보다 약합니다.

[Qwen에게 위임할 것 — 적극 활용]
다음 작업이 들어오면 Anthropic 에이전트를 부르기 전에 Qwen에게 먼저 시도:
  - 짧은 텍스트 요약 (한 문단 → 한 줄)
  - 키워드 추출
  - 단순 분류 (긍정/부정, 카테고리 매핑)
  - 형식 변환 (JSON ↔ 표, 마크다운 정리)
  - 한 줄 답변 / 사용자 메모
  - 간단한 오타·문법 1차 점검 (최종 교정은 Reviewer)

호출 예시:
  call qwen("다음 abstract를 100자 이내로 한국어로 요약해줘:text")

[Qwen에게 위임하지 말 것]
  - 논문 본문 작성 → Writer
  - LaTeX/IEEE 스타일 검증 → Reviewer (Mode B)
  - 시뮬레이션 코드 → Experimenter
  - 학술 검색 → Librarian
  - 자기 코드 수정 → 본인이 직접
  - 다단계 추론 / 설계 결정 → Sonnet/Opus

[판단 기준]
"이 작업이 5초 안에 끝날 단순 변환인가?" → Yes면 Qwen.
"이 작업의 출력이 논문에 직접 들어가는가?" → Yes면 Sonnet 이상.

만약 Qwen 응답이 부족하거나 어색하면 Sonnet으로 재시도. Qwen 위임은
**최선의 시도**일 뿐 의무가 아닙니다 — 의심스러우면 Sonnet으로 직행.

================================================================================
[주간 자체 업그레이드 검토]
================================================================================
부팅 시 시스템이 마지막 자체 업그레이드 검토 시각을 확인합니다.
사용자가 부팅 프롬프트에서 'y'를 답하여 명시적으로 동의한 경우에만
검토를 시작하십시오. 그 외에는 평소처럼 사용자 명령을 기다립니다.

[검토 절차 — 사용자 동의가 있었을 때만]
1. 웹 검색으로 다음 항목 확인 (Librarian에게 위임):
   - smolagents 라이브러리 최신 릴리스 (현재 사용 버전과 비교)
   - LiteLLM 최신 릴리스 (Anthropic 새 모델 지원, 보안 패치)
   - Anthropic API 신규 기능·deprecation 공지
   - cryptography 보안 권고
2. 발견된 변경 사항을 annotations/agent_notes.md에 정리.
3. 자기 코드(commander.py + agents/*.py + tools/*.py)에 적용 가능한
   업그레이드가 있는지 평가:
   - 새 API 활용으로 비용 절감
   - deprecated API 사용 중인 부분
   - 프롬프트 개선 (이전 세션의 실패 패턴 분석)
4. 실제 코드 변경이 필요하면 [자체 업그레이드 절차] (아래) 진행.
5. 단순 메모만 필요하면 annotations/agent_notes.md에 기록 후 종료.

[중요한 가드]
- 사용자가 'y'를 답하지 않았는데 자체 업그레이드를 시작하지 마십시오.
- 검토 중 발견된 사항이 모호하면 사용자에게 질문하고, 임의 판단 금지.
- 검토는 한 세션에 1회만 — 반복 호출 금지.

================================================================================
[자체 업그레이드 절차 (Self-Upgrade Procedure)]
================================================================================
사용자가 명시적으로 "commander.py 자체를 수정하라"고 지시하거나
당신이 자기 코드를 개선해야 한다고 판단했을 때만 실행하십시오.
일반 작업 흐름에서는 절대 호출하지 않습니다.

[절차]
1. 현재 commander.py를 file_read로 읽어 전체 내용 확보.
2. 수정할 부분을 결정하고 새 commander.py 전체 내용 생성.
3. stage_upgrade(new_content=...) 호출 — staging/commander.py.candidate 작성.
   live commander.py는 건드리지 않음.
4. test_staged_upgrade() 호출 — 6 에이전트 실제 API ping (~$0.001).
5. PASS → finalize_upgrade() 호출. 이 시점에 프로세스가 종료되고
   watchdog이 atomic swap + 재시작 수행.
6. FAIL → 반환된 stderr를 분석하여 무엇이 잘못됐는지 파악.
   stage_upgrade를 다시 호출하여 수정된 코드 시도.
   최대 5회까지 시도 가능.
7. 5회 모두 실패 시 abort_upgrade(reason="...") 호출.
   사용자에게 알림이 출력되고 기존 commander.py가 그대로 유지됨.

[5회 시도 정책 — 본인이 본인을 코더로 활용]
부트 테스트가 실패하면 stderr를 정독하고 직접 코드를 수정해서 다시 시도하십시오:
  - SyntaxError → 문법 오류 위치 확인 후 수정
  - ImportError → 누락된 import 추가 또는 잘못된 모듈 경로 정정
  - LiteLLM 호출 실패 → API 키 alias 또는 모델 ID 확인
  - 타임아웃 → 무한 루프 또는 부적절한 max_steps 검토

각 시도 사이에 기존 시도와 동일한 코드를 다시 stage하지 마십시오.
명확한 변경 없이 재시도하는 것은 시도 횟수만 소모합니다.

[주의 사항]
- finalize_upgrade는 프로세스 종료를 발생시킵니다. 호출 후에는 후속 작업 불가능.
- abort_upgrade를 호출하면 staging/이 정리되고 다음 세션에서 신선한 시도 가능.
- 자체 업그레이드 중에는 다른 에이전트(Librarian/Idea/Experimenter/...)를 호출하지 마십시오.
  본인의 도구(file_read, python_interpreter, stage/test/finalize)만 사용.

{COMMON_INTERFACE}
"""


commander = CodeAgent(
    name="Commander",
    tools=[
        PythonInterpreterTool(),
        FileReadTool(),
        FileWriteTool(),
        DirectoryListTool(),
        # Self-upgrade tools (sequence: stage → test → finalize, or abort)
        StageUpgradeTool(),
        TestStagedUpgradeTool(),
        FinalizeUpgradeTool(),
        AbortUpgradeTool(),
    ],
    model=model,
    managed_agents=[
        librarian_agent,
        idea_agent,
        experimenter_agent,
        reviewer_agent,
        writer_agent,
        qwen_agent,
    ],
    description=COMMANDER_PROMPT,
    max_steps=MAX_STEPS * 6,
    additional_authorized_imports=["os", "json", "pathlib", "datetime"],
)


# ──────────────────────────────────────────────────────────────────── helpers

def log_session_start() -> None:
    hist = PATHS["context_state"] / "session_history.md"
    with open(hist, "a", encoding="utf-8") as f:
        f.write(f"\n## Session started: {datetime.now().isoformat()}\n")


def log_session_end() -> None:
    hist = PATHS["context_state"] / "session_history.md"
    with open(hist, "a", encoding="utf-8") as f:
        f.write(f"## Session ended: {datetime.now().isoformat()}\n\n")
    # Best-effort: print this session's token totals so the user sees
    # cost on every exit. The data lives in the in-process PolicyRuntime
    # we created in the bootstrap block; if the import failed (no
    # cost-bridge installed), we silently skip.
    try:
        if "_policy" in globals() and _policy is not None:
            sess = _policy.session_usage
            if sess.usd_spent > 0 or sess.input_tokens > 0:
                print("\n" + "─" * 60)
                print("  Session summary")
                print(f"    calls:    {sum(sess.calls_by_model.values())}")
                print(f"    input:    {sess.input_tokens:,} tokens")
                print(f"    output:   {sess.output_tokens:,} tokens")
                print(f"    cost:     ${sess.usd_spent:.4f}")
                if sess.tokens_by_agent:
                    print("    by agent:")
                    for role in sorted(sess.tokens_by_agent):
                        s = sess.tokens_by_agent[role]
                        print(f"      {role:<14} {s['calls']:>3} calls  "
                              f"${s['cost_usd']:.4f}")
                print("  (run `python cli.py --usage` for lifetime totals)")
                print("─" * 60)
    except Exception:
        pass


def _sanitize(text: str) -> str:
    """Drop surrogate halves to keep the string safely UTF-8."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def resolve_input(raw_input: str) -> str:
    """If the input looks like a path to a .md/.txt file, load it.

    Returns the loaded contents (or the original string if not a path).
    """
    raw = raw_input.strip().strip('"').strip("'")

    if len(raw) > 200 or " " in raw or not raw.endswith((".md", ".txt")):
        return _sanitize(raw_input)

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = BASE_DIR / raw

    try:
        if candidate.is_file():
            for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "latin-1"):
                try:
                    content = candidate.read_text(encoding=enc)
                    content = _sanitize(content)
                    print(f"[파일 로드] {candidate.name} ({len(content)}자, {enc})")
                    logger.info(
                        "파일 입력: %s (%d자, %s)",
                        candidate, len(content), enc,
                    )
                    return content
                except (UnicodeDecodeError, UnicodeEncodeError):
                    continue
            content = candidate.read_bytes().decode("utf-8", errors="replace")
            print(f"[파일 로드] {candidate.name} ({len(content)}자, fallback)")
            return content
    except OSError:
        pass

    return _sanitize(raw_input)


# ──────────────────────────────────────────────────────────────────── sessions
#
# Lightweight session tracking: each named session is a directory under
# `output/sessions/<NAME>/` containing a turn-by-turn log of user inputs
# and Commander outputs. The actual paper-state lives in `.pipeline/`
# under PAPER_BASE_DIR — that's shared across all sessions for the
# same paper. Sessions only differentiate "what did I tell Commander
# this time?" so you can flip back to find an earlier directive.

import re

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _setup_session(name: str | None, *, resume: bool = False) -> Path | None:
    """Create or open a session directory. Returns the dir, or None if
    autosave/resume was not requested.

    On resume, prints a recap so the user remembers what was in flight.
    """
    if not name:
        return None
    if not _NAME_RE.match(name):
        print(f"[warn] invalid session name {name!r}; ignoring autosave/resume")
        return None
    sdir = PAPER_AI_ROOT / "output" / "sessions" / name
    is_new = not sdir.is_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    if resume and not is_new:
        # Show last few inputs so the user knows where they left off.
        log_file = sdir / "turns.md"
        if log_file.is_file():
            text = log_file.read_text(encoding="utf-8")
            tail = text[-2000:] if len(text) > 2000 else text
            print(f"\n[resume {name!r}] last activity:\n{tail}\n")
    elif is_new:
        # Initialise an index file so the user can browse later.
        (sdir / "turns.md").write_text(
            f"# Session: {name}\n\n"
            f"Started: {datetime.now().isoformat()}\n\n"
            "All Commander inputs and outputs in this session are appended\n"
            "below in chronological order.\n\n",
            encoding="utf-8",
        )
    return sdir


def _session_record(session_dir: Path | None, kind: str, text: str) -> None:
    """Append one event to the session log. No-op if no session active.

    `kind` is "input" / "output" / "error". The log is plain Markdown
    so the user can read it in any editor.
    """
    if session_dir is None:
        return
    log_file = session_dir / "turns.md"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    icon = {"input": "🧑", "output": "🤖", "error": "❌"}.get(kind, "•")
    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n## [{timestamp}] {icon} {kind}\n{text}\n")
    except OSError as e:
        logger.warning("session_record_failed: %s", e)


# ──────────────────────────────────────────────────────────────────── main

def main() -> int:
    # ---- minimal argv parsing (we don't use argparse to keep the
    # original "Command.md as bare arg" behaviour) ----
    autosave_name: str | None = None
    resume_name: str | None = None
    force_interactive = False  # --interactive forces REPL even with positional file

    raw_argv = sys.argv[1:]
    positional: list[str] = []
    i = 0
    while i < len(raw_argv):
        a = raw_argv[i]
        if a == "--interactive" or a == "-i":
            force_interactive = True
            i += 1
        elif a == "--autosave" and i + 1 < len(raw_argv):
            autosave_name = raw_argv[i + 1]
            i += 2
        elif a == "--resume" and i + 1 < len(raw_argv):
            resume_name = raw_argv[i + 1]
            i += 2
        elif a.startswith("--"):
            # Unknown flag — ignore, keep going. The original system
            # silently dropped these.
            i += 1
        else:
            positional.append(a)
            i += 1

    print("=" * 60)
    print("  논문 제작 Commander 시작 (6 에이전트 통합)")
    print(f"  코드 베이스 (PAPER_AI_ROOT): {PAPER_AI_ROOT}")
    print(f"  논문 작업 (PAPER_BASE_DIR):  {BASE_DIR}")
    print(f"  최대 재시도: {MAX_RETRIES}회")
    print(f"  Commander max_steps: {MAX_STEPS * 6}")
    if autosave_name:
        print(f"  Autosave session: {autosave_name!r}")
        # Surface fresh registrations — the user typed a NEW name and
        # we just created papers/<name>/. Make this visible so they
        # can sanity-check before starting heavy work.
        if os.environ.pop("_PAPER_AI_BOOT_NEW_REG", "") == "1":
            print(f"  ✨ 신규 논문 등록: papers/{autosave_name}/ 생성됨")
            print(f"     (papers/list.md 에서 전체 목록 확인 가능)")
    elif resume_name:
        print(f"  Resume session:   {resume_name!r}")
    print("  종료: 'exit'")
    print("=" * 60)

    # Boot reached main() successfully. Reset the failure counter.
    try:
        from monitoring.blue_green import reset_boot_failures
        reset_boot_failures(PAPER_AI_ROOT)
    except Exception:
        pass

    # Set up the session directory if autosave or resume was requested.
    # Both store user inputs + commander outputs under
    # output/sessions/<NAME>/. Resuming means: print a recap, then
    # continue the REPL — the .pipeline/ memory is the actual context.
    session_dir = _setup_session(autosave_name or resume_name,
                                 resume=bool(resume_name))

    log_session_start()

    # ---- Weekly self-upgrade check ----
    # Consult upgrade_state.json. If it's been ≥7 days since the last
    # check AND we're running interactively, prompt the user. If the
    # user answers 'y', we prepend a directive to the first turn so
    # Commander knows to begin the review procedure.
    upgrade_directive: str | None = None
    try:
        import sys as _sys
        from core import upgrade_check as _upgrade_check
        is_tty = _sys.stdin.isatty() if hasattr(_sys.stdin, "isatty") else False
        result = _upgrade_check.boot_check(PAPER_AI_ROOT, interactive=is_tty)
        if result.get("due") and result.get("user_consent") is True:
            upgrade_directive = (
                "[시스템 알림 — 사용자가 부팅 시 'y'로 동의함]\n"
                "마지막 자체 업그레이드 검토로부터 "
                f"{result.get('days_since', '?')}일이 지났습니다. "
                "[주간 자체 업그레이드 검토] 섹션에 명시된 절차를 시작하십시오. "
                "사용자가 명시적으로 추가 명령을 줄 때까지는 검토 절차에만 집중하고, "
                "실제 코드 변경이 필요하면 [자체 업그레이드 절차]로 진행하십시오. "
                "변경이 불필요하면 annotations/agent_notes.md에 검토 결과를 기록 후 종료하십시오."
            )
    except Exception as e:
        logger.warning("upgrade_check_skipped: %s", e)
    # If boot_check is due but consent unresolved (non-tty, no answer),
    # we don't auto-trigger — the user can manually request a review.

    # Single-run mode: file or string passed on the command line.
    # Skipped if --interactive was given (force REPL even with file).
    if positional and not force_interactive:
        file_input = resolve_input(positional[0])
        if file_input != positional[0]:
            directives = PATHS["annotations"] / "user_directives.md"
            safe = _sanitize(file_input)
            with open(directives, "a", encoding="utf-8") as f:
                f.write(
                    f"\n## [{datetime.now().strftime('%Y-%m-%d %H:%M')}] "
                    f"(파일: {positional[0]})\n{safe}\n"
                )
            _session_record(session_dir, "input",
                            f"(파일: {positional[0]})\n{safe}")
        # If a weekly upgrade review was consented to, prepend it to
        # the first run so Commander tackles the review BEFORE the
        # user's directive (the review is short; it merges in front).
        if upgrade_directive:
            file_input = upgrade_directive + "\n\n---\n\n" + file_input
            _session_record(session_dir, "input",
                            "[auto] weekly upgrade review triggered")
        print("\n[Commander] 명령을 실행합니다...\n")
        try:
            result = commander.run(file_input)
            print("\n" + "=" * 60)
            print(f"[Commander 최종 결과]\n{result}")
            print("=" * 60)
            _session_record(session_dir, "output", str(result))
            log_session_end()
            return 0
        except Exception as e:
            logger.error("오류 발생: %s", e, exc_info=True)
            print(f"\n[오류 발생] {e}")
            _session_record(session_dir, "error", str(e))
            log_session_end()
            return 1

    # Interactive REPL.
    # Special case: if the user consented to a weekly upgrade review
    # at boot, run it as the auto-first-turn BEFORE accepting any
    # user input. This is the only place a turn is generated without
    # the user typing it. Once consumed, upgrade_directive is None
    # so subsequent loop iterations behave normally.
    while True:
        if upgrade_directive is not None:
            print("\n[Commander] 주간 업그레이드 검토를 시작합니다...\n")
            _session_record(session_dir, "input",
                            "[auto] weekly upgrade review triggered")
            try:
                result = commander.run(upgrade_directive)
                print("\n" + "=" * 60)
                print(f"[검토 결과]\n{result}")
                print("=" * 60)
                _session_record(session_dir, "output", str(result))
            except Exception as e:
                logger.error("upgrade review failed: %s", e, exc_info=True)
                print(f"\n[검토 중 오류] {e}")
                _session_record(session_dir, "error", str(e))
            upgrade_directive = None  # consumed; revert to normal REPL
            # Check for self-upgrade exit (Commander wrote UPGRADE_READY
            # marker as part of the review). Same handling as below.
            if UPGRADE_READY_MARKER.is_file():
                logger.info("self-upgrade requested; exiting for watchdog swap")
                print("\n[Commander] 자기 업그레이드 준비됨. Watchdog 교체 대기.")
                log_session_end()
                return 0
            continue

        try:
            user_input = _sanitize(
                input("\n[Commander] 명령을 입력하세요: ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            logger.info("사용자에 의해 종료됨")
            log_session_end()
            print("\n종료합니다.")
            return 0

        if user_input.lower() == "exit":
            logger.info("사용자가 exit 입력")
            log_session_end()
            print("종료합니다.")
            return 0
        if not user_input:
            continue

        user_input = resolve_input(user_input)

        directives = PATHS["annotations"] / "user_directives.md"
        safe = _sanitize(user_input)
        with open(directives, "a", encoding="utf-8") as f:
            f.write(
                f"\n## [{datetime.now().strftime('%Y-%m-%d %H:%M')}]\n{safe}\n"
            )
        _session_record(session_dir, "input", safe)

        logger.info("사용자 입력: %s", user_input[:100])
        print("\n[Commander] 작업을 시작합니다...\n")

        try:
            result = commander.run(user_input)
            logger.info("작업 완료")
            print("\n" + "=" * 60)
            print(f"[Commander 최종 결과]\n{result}")
            print("=" * 60)
            _session_record(session_dir, "output", str(result))
        except Exception as e:
            logger.error("오류 발생: %s", e, exc_info=True)
            print(f"\n[오류 발생] {e}")
            print(".pipeline/context_state/에 현재 상태가 기록되어 있습니다.")
            _session_record(session_dir, "error", str(e))

        # Check for self-upgrade signal: Commander wrote
        # staging/UPGRADE_READY → exit cleanly so the watchdog can
        # finalize and restart.
        if UPGRADE_READY_MARKER.is_file():
            logger.info("self-upgrade requested; exiting for watchdog swap")
            print("\n[Commander] 자기 업그레이드 준비됨. Watchdog 교체 대기.")
            log_session_end()
            return 0


if __name__ == "__main__":
    sys.exit(main())
