"""
qwen-loop 대화형 셸 — v0.3.1
자가 수정 + watchdog + 5회 실패 시 사용자 승인 → 무제한 재시도.

자가 수정 흐름:
  /upgrade <대상파일> <설명>
    1차: trial_max_retries(기본 5)회까지 시범 운영
       성공 → 적용 + 재시작
       실패 → 사용자에게 다음을 보여주고 승인 요청:
              - 무엇을 수정하려 했는지 (설명)
              - 마지막 실패 에러
              - 마지막 시도 코드 미리보기
       사용자 승인 → 무제한 재시도 모드로 재시작
       사용자 거부 → 종료, 원본 그대로

watchdog 약속:
  - chat이 정상 종료(exit 0) + .restart_requested 있으면 → watchdog이 재시동
  - chat이 정상 종료 + .restart_requested 없으면 → 사용자가 끈 것 → watchdog도 종료
  - chat이 SIGINT(Ctrl+C)로 죽으면 → 사용자 의도 → watchdog도 종료
  - chat이 비정상 크래시 → backoff 후 재시동 (5회/30초 burst 시 중단)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

try:
    import readline  # noqa
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from qwen_loop.agent import Agent, _slugify
from qwen_loop.annotation.schemas import KIND_MODE
from qwen_loop.safety import (
    Guard,
    PolicyError,
    SelfUpgradeEngine,
    load_policy,
)
from qwen_loop.tools import is_write_tool, make_chat_tools


HELP = """
[bold cyan]대화 / 모드[/bold cyan]
  /kind <name>   /list   /rag on|off   /tools on|off   /yolo on|off
  /workspace

[bold cyan]도구 명시 호출[/bold cyan]
  /ls [path]   /read <path>   /edit <path>   /web <q>   /fetch <url>

[bold cyan]자가 수정[/bold cyan]
  /upgrade <파일경로> <개선 설명>   chat이 파일을 자가 수정
  /history                          자가 수정 이력
  /restore <백업명>                 백업에서 복원
  /policy                           현재 정책 표시

[bold cyan]유틸[/bold cyan]
  /multi   /show   /save [제목]   /clear   /quit
"""

TOOL_CALL_RE = re.compile(r"TOOL_CALL:\s*(\{.*?\})\s*(?:\n|$)", re.S)
RESTART_FLAG_FILE = ".restart_requested"


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--kind", default="draft")
    p.add_argument("--no-rag", action="store_true")
    p.add_argument("--no-tools", action="store_true")
    p.add_argument("--policy", default=None)
    args = p.parse_args()

    console = Console()

    # Ctrl+C는 KeyboardInterrupt로 잡되, watchdog에 "사용자 종료"임을 알리기 위해
    # 정상 종료 + restart 플래그 없음 으로 처리.
    def _on_sigint(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, _on_sigint)

    try:
        policy = load_policy(args.policy)
    except PolicyError as e:
        console.print(f"[bold red]정책 로드 실패[/bold red]\n{e}")
        sys.exit(2)

    chat_path = Path(__file__).resolve()
    try:
        chat_path.relative_to(policy.project_root)
    except ValueError:
        console.print(
            f"[bold red]보안 오류[/bold red]\n"
            f"chat.py({chat_path})가 policy.project_root({policy.project_root}) 밖."
        )
        sys.exit(2)

    try:
        mode = oct(policy.policy_file.stat().st_mode)[-3:]
        if mode != "444":
            console.print(
                f"[yellow]주의: 정책 파일 mode={mode}. 권장: chmod 444 {policy.policy_file}[/yellow]"
            )
    except Exception:
        pass

    agent = Agent(args.config)
    notifier = lambda msg: console.print(f"[yellow]{msg}[/yellow]")
    guard = Guard(policy, notifier=notifier)
    upgrade_engine = SelfUpgradeEngine(policy, guard)

    tools, web_state, tool_docs = make_chat_tools(agent.semantic, guard)
    max_tool_iters = agent.cfg.get("tools", {}).get("max_iters_per_turn", 5)

    state = {
        "kind": args.kind,
        "rag_on": not args.no_rag,
        "tools_on": not args.no_tools,
        "yolo": False,
        "guard": guard,
        "tools": tools,
        "tool_docs": tool_docs,
        "web_state": web_state,
        "max_tool_iters": max_tool_iters,
        "upgrade_engine": upgrade_engine,
        "policy": policy,
        "self_path": chat_path,
    }

    n_chunks = 0
    try:
        n_chunks = agent.semantic.count()
    except Exception:
        pass

    console.print(Panel.fit(
        f"[bold cyan]qwen-loop chat (v0.3.1)[/bold cyan]\n"
        f"모델: [yellow]{agent.cfg['llm']['model']}[/yellow]   "
        f"kind: [green]{state['kind']}[/green]\n"
        f"project_root: [magenta]{policy.project_root}[/magenta]\n"
        f"policy: [dim]{policy.policy_file}[/dim] "
        f"(보호 {len(policy.protected_paths)}개)\n"
        f"RAG: [{'green' if state['rag_on'] else 'dim'}]"
        f"{'ON' if state['rag_on'] else 'OFF'}[/] ({n_chunks} chunks)   "
        f"도구: [{'green' if state['tools_on'] else 'dim'}]"
        f"{'ON' if state['tools_on'] else 'OFF'}[/]\n"
        f"자가 수정: 일 {policy.daily_limit}회 / cooldown {policy.cooldown_minutes}분 / "
        f"기본 시도 {policy.trial_max_retries}회\n"
        "[dim]/help · Ctrl+C 사용자 종료 (watchdog도 같이 종료)[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]사용자 종료. watchdog도 종료됩니다.[/dim]")
            _maybe_save_on_exit(agent, state, console)
            # 정상 종료 + restart 플래그 없음 = watchdog이 종료
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if not handle_command(user_input, state, agent, console):
                break
            continue

        try:
            chat_loop(user_input, state, agent, console)
        except KeyboardInterrupt:
            console.print("\n[yellow]중단됨 (대화 계속)[/yellow]")
        except Exception as e:
            console.print(f"[red]에러: {type(e).__name__}: {e}[/red]")


# ----------------------------------------------------------------------------
# Chat loop with tool use
# ----------------------------------------------------------------------------

def chat_loop(user_msg: str, state: dict, agent: Agent, console: Console) -> None:
    agent.working.add("user", user_msg)
    pending_input = user_msg
    iters = 0

    while True:
        with console.status("[dim]Qwen 생각 중...[/dim]", spinner="dots"):
            response = agent.llm.chat(
                pending_input,
                system=build_system_prompt(state, agent, pending_input),
                history=agent.working.history()[:-1],
            )

        tool_calls = TOOL_CALL_RE.findall(response)
        visible = TOOL_CALL_RE.sub("", response).strip()
        if visible:
            console.print()
            console.print(Markdown(visible))

        if not tool_calls or not state["tools_on"] or iters >= state["max_tool_iters"]:
            agent.working.add("assistant", response)
            return

        tool_results = []
        for raw in tool_calls:
            try:
                call = json.loads(raw)
                name = call.get("tool")
                args = call.get("args", {})
            except Exception as e:
                tool_results.append(f"PARSE_ERROR: {e}")
                continue

            if name not in state["tools"]:
                tool_results.append(f"UNKNOWN_TOOL: {name}")
                continue

            if is_write_tool(name) and not state["yolo"]:
                console.print(Panel(
                    f"[bold yellow]쓰기 도구 호출 요청[/bold yellow]\n\n"
                    f"도구: [cyan]{name}[/cyan]\n"
                    f"인자: {json.dumps(args, ensure_ascii=False, indent=2)}",
                    border_style="yellow",
                ))
                approval = console.input(
                    "[yellow]실행? [y/N/skip-all]:[/yellow] "
                ).strip().lower()
                if approval == "skip-all":
                    tool_results.append("USER_SKIPPED_ALL")
                    break
                if approval not in ("y", "yes"):
                    tool_results.append(f"USER_DECLINED: {name}")
                    continue

            try:
                with console.status(f"[dim]도구 실행: {name}[/dim]", spinner="dots"):
                    result = state["tools"][name](args)
                if not isinstance(result, str):
                    result = json.dumps(result, ensure_ascii=False, default=str)
                console.print(f"[dim cyan]✓ {name}[/dim cyan]")
                tool_results.append(f"# 도구 결과: {name}\n{result[:5000]}")
            except Exception as e:
                tool_results.append(f"TOOL_ERROR ({name}): {type(e).__name__}: {e}")
                console.print(f"[red]✗ {name}: {e}[/red]")

        agent.working.add("assistant", response)
        pending_input = (
            "도구 실행 결과:\n\n"
            + "\n\n---\n\n".join(tool_results)
            + "\n\n위 결과를 바탕으로 답변을 이어가세요."
        )
        agent.working.add("user", pending_input)
        iters += 1


def build_system_prompt(state: dict, agent: Agent, current_query: str) -> str:
    try:
        _, seed = agent.prompts.get(state["kind"])
    except Exception:
        seed = ""

    rag_block = ""
    if state["rag_on"]:
        try:
            if agent.semantic.count() > 0:
                chunks = agent.semantic.search(current_query, k=5)
                if chunks:
                    rag_block = "\n\n## 참고 자료\n"
                    for i, ch in enumerate(chunks, 1):
                        src = ch.get("metadata", {}).get("source", "?")
                        rag_block += f"\n### 자료 {i} ({src})\n{ch['text'][:1500]}\n"
        except Exception:
            pass

    tools_block = ""
    if state["tools_on"] and state["tools"]:
        tool_lines = "\n".join(
            f"- {n}: {state['tool_docs'].get(n, '')}" for n in sorted(state["tools"])
        )
        tools_block = (
            "\n\n## 사용 가능 도구\n"
            f"{tool_lines}\n\n"
            '도구 호출: TOOL_CALL: {"tool": "이름", "args": {...}}\n'
            "쓰기 도구는 사용자 승인 후 실행됩니다.\n"
        )

    rules = (
        "\n\n## 대화 규칙\n"
        "- 자연스러운 한국어. 마크다운 사용 가능.\n"
        "- 참고 자료에 없는 사실은 만들지 말 것.\n"
    )
    return (seed or "") + rag_block + tools_block + rules


# ----------------------------------------------------------------------------
# Slash commands
# ----------------------------------------------------------------------------

def handle_command(cmd: str, state: dict, agent: Agent, console: Console) -> bool:
    parts = cmd.split(maxsplit=1)
    head = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if head in ("/quit", "/exit"):
        _maybe_save_on_exit(agent, state, console)
        return False

    if head == "/help":
        console.print(HELP)
        return True

    if head == "/upgrade":
        return cmd_upgrade(arg, state, agent, console)
    if head == "/history":
        return cmd_history(state, console)
    if head == "/restore":
        return cmd_restore(arg, state, console)
    if head == "/policy":
        return cmd_policy(state, console)

    if head == "/kind":
        if not arg:
            console.print(f"현재 kind: {state['kind']}")
        elif arg in KIND_MODE:
            state["kind"] = arg
            console.print(f"[green]kind → {arg}[/green]")
        else:
            console.print("[red]알 수 없는 kind[/red]")
        return True
    if head == "/list":
        for k, mode in sorted(KIND_MODE.items()):
            tag = "[cyan]md[/cyan]" if mode == "markdown" else "[yellow]json[/yellow]"
            mark = " ←현재" if k == state["kind"] else ""
            console.print(f"  {tag} {k}{mark}")
        return True
    if head == "/rag":
        return _toggle(state, "rag_on", arg, console, "RAG")
    if head == "/tools":
        return _toggle(state, "tools_on", arg, console, "도구")
    if head == "/yolo":
        if arg.lower() == "on":
            state["yolo"] = True
            console.print("[bold red]YOLO ON[/bold red]")
        elif arg.lower() == "off":
            state["yolo"] = False
            console.print("[green]YOLO OFF[/green]")
        else:
            console.print(f"YOLO: {'ON' if state['yolo'] else 'off'}")
        return True
    if head == "/workspace":
        console.print(f"project_root: [magenta]{state['policy'].project_root}[/magenta]")
        return True

    if head == "/ls":
        console.print(state["tools"]["list_files"]({"path": arg or "."}))
        return True
    if head == "/read":
        if not arg:
            console.print("[red]사용법: /read <path>[/red]")
            return True
        result = state["tools"]["read_file"]({"path": arg})
        console.print(Markdown(result[:3000]))
        return True
    if head == "/edit":
        if not arg:
            console.print("[red]사용법: /edit <path>[/red]")
            return True
        editor = os.environ.get("EDITOR", "nano")
        full = state["guard"].assert_writable(arg)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.touch(exist_ok=True)
        subprocess.call([editor, str(full)])
        console.print(f"[green]저장: {full.relative_to(state['policy'].project_root)}[/green]")
        return True
    if head == "/web":
        if "web_search" not in state["tools"]:
            console.print("[red]웹 검색 비활성[/red]")
            return True
        console.print(Markdown(state["tools"]["web_search"]({"query": arg, "k": 5})))
        return True
    if head == "/fetch":
        if "web_fetch" not in state["tools"]:
            console.print("[red]web_fetch 비활성[/red]")
            return True
        console.print(Markdown(state["tools"]["web_fetch"]({"url": arg})[:5000]))
        return True

    if head == "/multi":
        console.print("[dim]여러 줄. 빈 줄로 종료.[/dim]")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                break
            lines.append(line)
        if lines:
            try:
                chat_loop("\n".join(lines), state, agent, console)
            except Exception as e:
                console.print(f"[red]에러: {e}[/red]")
        return True
    if head == "/show":
        for i, msg in enumerate(agent.working.history(), 1):
            color = "cyan" if msg["role"] == "user" else "green"
            preview = msg["content"][:300].replace("\n", " ")
            ellip = "..." if len(msg["content"]) > 300 else ""
            console.print(f"[{color}]{i}. {msg['role']}[/]: {preview}{ellip}")
        return True
    if head == "/save":
        save_conversation(agent, state, console, title=arg or None)
        return True
    if head == "/clear":
        agent.working.clear()
        console.print("[green]초기화[/green]")
        return True

    console.print(f"[red]알 수 없는 명령: {head}[/red]")
    return True


def _toggle(state, key, arg, console, label):
    if arg.lower() == "on":
        state[key] = True
        console.print(f"[green]{label} ON[/green]")
    elif arg.lower() == "off":
        state[key] = False
        console.print(f"[yellow]{label} OFF[/yellow]")
    else:
        console.print(f"{label}: {'on' if state[key] else 'off'}")
    return True


# ----------------------------------------------------------------------------
# Self-upgrade — 2단계 흐름
# ----------------------------------------------------------------------------

def cmd_upgrade(arg: str, state: dict, agent: Agent, console: Console) -> bool:
    if not arg:
        console.print(
            "[red]사용법: /upgrade <파일경로> <개선 설명>[/red]\n"
            "예: /upgrade qwen_loop/tools/workspace.py 디렉토리 삭제 도구 추가"
        )
        return True

    parts = arg.split(maxsplit=1)
    target = parts[0]
    description = parts[1] if len(parts) > 1 else "개선"

    engine: SelfUpgradeEngine = state["upgrade_engine"]
    guard: Guard = state["guard"]

    try:
        target_path = guard.assert_writable(target, for_self_upgrade=True)
    except Exception as e:
        console.print(f"[red]대상 거부: {e}[/red]")
        return True

    rel = target_path.relative_to(state["policy"].project_root)
    is_self = (target_path == state["self_path"])

    console.print(Panel(
        f"[bold yellow]자가 수정 요청[/bold yellow]\n\n"
        f"대상: [cyan]{rel}[/cyan]" +
        (" [bold red](chat.py 자기 자신!)[/bold red]" if is_self else "") +
        f"\n설명: {description}\n\n"
        f"흐름:\n"
        f"  1) 원본 백업 → chat_temp/에 시범 사본 → syntax + import 검증\n"
        f"  2) {state['policy'].trial_max_retries}회 시도 후 실패 시 사용자에게 승인 요청\n"
        f"  3) 사용자 승인 시 무제한 재시도로 반드시 성공시키기",
        border_style="yellow",
    ))
    if console.input("[yellow]진행? [y/N]:[/yellow] ").strip().lower() not in ("y", "yes"):
        console.print("[dim]취소됨[/dim]")
        return True

    current = target_path.read_text() if target_path.exists() else ""

    def make_propose():
        def propose(target_p: Path, prev_error: str | None) -> str:
            prompt = build_upgrade_prompt(rel, description, current, prev_error)
            with console.status(
                f"[dim]Qwen 코드 생성{' (재시도)' if prev_error else ''}...[/dim]",
                spinner="dots",
            ):
                response = agent.llm.chat(prompt, system=UPGRADE_SYSTEM)
            return extract_code(response)
        return propose

    notify = lambda m: console.print(f"   [dim]{m}[/dim]")

    # 1단계 — 기본 횟수
    result = engine.upgrade(
        target_path, make_propose(), validator=None, notifier=notify,
    )

    # 2단계 — 1단계가 exhausted면 사용자 승인 받아 무제한 재시도
    if not result.success and result.exhausted:
        result = _request_user_approval_and_retry(
            engine, target_path, rel, description,
            result, make_propose(), notify, console,
        )

    # 결과 처리
    if result.success:
        console.print(Panel(
            f"[bold green]✅ 자가 수정 성공[/bold green]\n\n"
            f"대상: {rel}\n"
            f"시도: {result.attempts}회\n"
            f"백업: {result.backup_path.name if result.backup_path else '?'}",
            border_style="green",
        ))
        if is_self:
            console.print(
                "\n[bold yellow]chat.py가 변경되었습니다. "
                "재시작 신호를 기록하고 종료합니다.[/bold yellow]\n"
                "[dim](watchdog이 새 chat을 자동으로 띄웁니다)[/dim]\n"
            )
            request_restart(state["policy"].project_root, console)
            _maybe_save_on_exit(agent, state, console)
            sys.exit(0)
    else:
        console.print(Panel(
            f"[bold red]❌ 자가 수정 실패[/bold red]\n\n"
            f"대상: {rel}\n"
            f"시도: {result.attempts}회\n"
            f"에러: {result.error}\n\n"
            f"trial 로그:\n" + "\n".join(f"  {l}" for l in result.trial_log[-10:]) +
            f"\n\n원본은 변경되지 않았습니다.",
            border_style="red",
        ))
    return True


def _request_user_approval_and_retry(
    engine, target_path, rel, description, first_result,
    propose, notify, console,
):
    """1단계 5회 실패 시 사용자에게 상황을 설명하고 무제한 모드 승인 요청."""
    console.print(Panel(
        f"[bold yellow]⚠️  자가 수정 1단계 실패 ({first_result.attempts}회 시도)[/bold yellow]\n\n"
        f"[bold]대상[/bold]: {rel}\n"
        f"[bold]요청한 변경[/bold]: {description}\n\n"
        f"[bold]마지막 에러[/bold]:\n{first_result.last_error or '(없음)'}\n\n"
        f"[bold]시도 로그[/bold]:\n" +
        "\n".join(f"  {l}" for l in first_result.trial_log[-5:]),
        border_style="yellow",
    ))

    # 마지막 시도 코드 미리보기 (있으면)
    if first_result.last_proposal:
        console.print("\n[bold]마지막 시도 코드 (앞부분 30줄):[/bold]")
        preview = "\n".join(first_result.last_proposal.splitlines()[:30])
        try:
            console.print(Syntax(preview, "python", theme="ansi_dark", line_numbers=True))
        except Exception:
            console.print(preview)
        if first_result.last_proposal.count("\n") > 30:
            console.print(f"[dim]... ({first_result.last_proposal.count(chr(10))} 줄 중 30줄)[/dim]")

    console.print(
        "\n[bold yellow]선택지:[/bold yellow]\n"
        "  [y] 무제한 재시도로 끝까지 성공시키기 (시간 오래 걸릴 수 있음)\n"
        "  [n] 포기 (원본 유지)\n"
        "  [s] 마지막 시도 코드를 강제 적용 (위험: 시범 검증 미통과 코드)\n"
    )
    ans = console.input("[yellow]선택 [y/n/s]:[/yellow] ").strip().lower()

    if ans == "n":
        console.print("[dim]자가 수정 포기[/dim]")
        return first_result

    if ans == "s":
        # 마지막 코드 강제 적용 — 위험하지만 사용자 명시 동의
        if first_result.last_proposal:
            target_path.write_text(first_result.last_proposal)
            console.print("[bold red]⚠️ 검증 미통과 코드 강제 적용됨.[/bold red]")
            return type(first_result)(
                success=True, target_path=target_path,
                attempts=first_result.attempts,
                final_content=first_result.last_proposal,
                backup_path=first_result.backup_path,
                trial_log=first_result.trial_log + ["FORCED_APPLY"],
            )
        else:
            console.print("[red]마지막 코드가 없어 강제 적용 불가[/red]")
            return first_result

    if ans not in ("y", "yes"):
        return first_result

    # 무제한 재시도 모드
    console.print(
        Panel(
            "[bold cyan]무제한 재시도 모드 진입[/bold cyan]\n"
            "성공할 때까지 시도합니다. Ctrl+C로 중단 가능 (원본은 안전).",
            border_style="cyan",
        )
    )
    try:
        result = engine.upgrade(
            target_path, propose, validator=None, notifier=notify,
            max_retries=-1,
            resume_from={
                "backup_path": str(first_result.backup_path) if first_result.backup_path else None,
                "last_error": first_result.last_error,
                "trial_log": first_result.trial_log,
            },
        )
        return result
    except KeyboardInterrupt:
        console.print("\n[yellow]사용자 중단. 원본 유지.[/yellow]")
        first_result.error = "user interrupted unlimited retry"
        return first_result


def cmd_history(state, console):
    log_path = state["upgrade_engine"].log_path
    if not log_path.exists():
        console.print("[dim]이력 없음[/dim]")
        return True
    console.print("[bold]자가 수정 이력 (최근 20)[/bold]")
    for line in log_path.read_text().strip().splitlines()[-20:]:
        try:
            r = json.loads(line)
            color = "green" if r["status"] == "success" else "red"
            mode = f" [{r.get('mode', '')}]" if r.get('mode') else ""
            console.print(
                f"  [{color}]{r['timestamp']}[/] {r['target']} "
                f"({r['attempts']}회){mode} — {r['status']}"
            )
        except Exception:
            continue
    return True


def cmd_restore(arg, state, console):
    if not arg:
        history_dir = state["policy"].project_root / ".history"
        files = sorted(history_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = [f for f in files if f.is_file() and f.name != "upgrade-log.jsonl"][:20]
        if not files:
            console.print("[dim]백업 없음[/dim]")
        else:
            console.print("[bold]최근 백업[/bold]")
            for f in files:
                ts = dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                console.print(f"  {ts}  {f.name}")
        console.print("\n[dim]사용: /restore <백업파일명>[/dim]")
        return True
    msg = state["upgrade_engine"].restore(arg)
    console.print(f"[green]{msg}[/green]")
    return True


def cmd_policy(state, console):
    p = state["policy"]
    console.print(Panel(
        f"[bold]정책[/bold] (read-only)\n\n"
        f"파일: {p.policy_file}\n"
        f"version: {p.version}\n"
        f"project_root: {p.project_root}\n"
        f"protected_paths: {list(p.protected_paths) or '(없음)'}\n"
        f"daily_limit: {p.daily_limit}\n"
        f"cooldown: {p.cooldown_minutes}분\n"
        f"trial: {p.trial_timeout_seconds}s × {p.trial_max_retries}회 (1단계)\n"
        f"web: {'on' if p.web_enabled else 'off'} (max {p.web_max_calls}/세션)\n"
        f"shell: {'on' if p.shell_enabled else 'off'}",
        border_style="blue",
    ))
    return True


# ----------------------------------------------------------------------------
# Self-upgrade prompts
# ----------------------------------------------------------------------------

UPGRADE_SYSTEM = """당신은 자기 자신을 포함한 qwen-loop 프로젝트의 코드를 수정합니다.

규칙:
1. 출력은 **수정된 파일의 전체 내용**입니다. 일부만 출력하지 마세요.
2. 코드는 ```python ... ``` 블록으로 감싸세요. 다른 텍스트는 블록 밖에.
3. import 문, 함수, 클래스가 모두 동작해야 합니다 (syntax error / import error 금지).
4. 기존 인터페이스(함수 시그니처, 클래스 메서드 이름)를 가능한 유지하세요.
5. 변경 의도를 코드 위 주석으로 짧게 적으세요.
6. 보안·검증·로깅 코드를 제거하지 마세요. 추가는 OK.
"""


def build_upgrade_prompt(rel_path, description, current, prev_error):
    parts = [f"# 대상 파일: {rel_path}", "", "## 개선 요청", description, ""]
    if prev_error:
        parts += [
            "## 이전 시도가 실패했습니다",
            f"```\n{prev_error[:1500]}\n```",
            "",
            "이 에러를 피하면서 다시 시도하세요.",
            "",
        ]
    parts += [
        "## 현재 파일 내용",
        f"```python\n{current[:30000]}\n```",
        "",
        "위 파일의 전체 내용을 개선 요청에 맞게 수정해서 출력하세요.",
    ]
    return "\n".join(parts)


_CODE_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)\n```", re.S)


def extract_code(response):
    m = _CODE_BLOCK_RE.search(response)
    if m:
        return m.group(1)
    return response.strip()


# ----------------------------------------------------------------------------
# Restart signaling
# ----------------------------------------------------------------------------

def request_restart(project_root, console):
    flag = project_root / RESTART_FLAG_FILE
    flag.write_text(dt.datetime.now().isoformat())
    console.print(f"[yellow]재시작 신호: {flag.name}[/yellow]")


# ----------------------------------------------------------------------------
# Save / exit
# ----------------------------------------------------------------------------

def save_conversation(agent, state, console, title=None):
    history = agent.working.history()
    if not history:
        console.print("[yellow]대화 없음[/yellow]")
        return
    today = dt.date.today().isoformat()
    out_dir = agent.outputs_dir / today / "chat"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not title:
        first = next((m["content"] for m in history if m["role"] == "user"), "chat")
        title = first[:50]
    slug = _slugify(title)
    ts = dt.datetime.now().strftime("%H%M%S")
    path = out_dir / f"{ts}__{slug}.md"
    lines = ["---", f"created: {dt.datetime.now().isoformat(timespec='seconds')}",
             "kind: chat", f"context_kind: {state['kind']}", f"turns: {len(history)}",
             "---", "", f"# {title}", ""]
    for msg in history:
        role = "사용자" if msg["role"] == "user" else "Qwen"
        lines.append(f"## {role}\n\n{msg['content']}\n")
    path.write_text("\n".join(lines))
    console.print(f"[green]저장: {path}[/green]")


def _maybe_save_on_exit(agent, state, console):
    if len(agent.working) == 0:
        return
    try:
        ans = console.input("[yellow]대화 저장? [Y/n]:[/yellow] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if ans in ("", "y", "yes"):
        save_conversation(agent, state, console)


if __name__ == "__main__":
    main()
