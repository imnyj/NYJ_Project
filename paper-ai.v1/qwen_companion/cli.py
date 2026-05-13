"""qwen_companion REPL + subcommands.

Usage
-----
    python -m qwen_companion                # open chat REPL
    python -m qwen_companion self-tune       # trigger one tune cycle
    python -m qwen_companion self-tune --force
    python -m qwen_companion verify-config   # validate profile + Ollama
    python -m qwen_companion facts           # list stored facts

The REPL runs on top of LocalLLMClient. Anthropic is NEVER contacted
from a pure chat session — only the self-tune flow may reach for
Commander (Opus) and only when `failure_policy: iterative` is set.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from core.logger import get_logger
from core.paths import get_paths
from core.policy_runtime import PolicyRuntime

log = get_logger("companion")


DEFAULT_PROMPT_FALLBACK = (
    "You are the user's local Qwen assistant. Be concise and helpful."
)

DEFAULT_CONFIG = {
    "model": "qwen2.5:72b",
    "base_url": "http://127.0.0.1:11434",
    "timeout_s": 120,
    "temperature": 0.2,
    "num_predict_cap": 1024,
    "prompt_style": "default",
}


# ============================================================================ helpers

def _make_policy() -> PolicyRuntime:
    return PolicyRuntime(config_dir=str(get_paths().config))


def _make_local_client(policy: PolicyRuntime):
    from tools.local_llm_client import LocalLLMClient
    from memory.qwen_profile import QwenProfile
    paths = get_paths()
    prof = QwenProfile.from_files(paths.qwen_profile_main)
    cfg = {**DEFAULT_CONFIG, **(prof.config or {})}
    return LocalLLMClient(
        policy=policy,
        model=cfg["model"],
        base_url=cfg["base_url"],
        timeout_s=float(cfg["timeout_s"]),
    )


def _make_anthropic_client(policy: PolicyRuntime):
    """Only constructed when needed (iterative self-tune). Missing API key
    is not fatal — returns None and the caller adapts."""
    from core import secret_env
    key = secret_env.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from tools.anthropic_client import AnthropicClient
        return AnthropicClient(
            policy=policy, api_key=key, project_root=get_paths().root,
        )
    except Exception as e:
        log.warning("anthropic_client_init_failed", err=str(e))
        return None


def _initialize_profile_if_missing() -> None:
    """First-run bootstrap for the Qwen profile."""
    from memory.qwen_profile import QwenProfileManager
    mgr = QwenProfileManager()
    paths = get_paths()
    prompt_path = paths.prompts / "qwen_companion.txt"
    default_prompt = (prompt_path.read_text(encoding="utf-8")
                      if prompt_path.is_file() else DEFAULT_PROMPT_FALLBACK)
    mgr.initialize_default(
        default_prompt=default_prompt,
        default_config=DEFAULT_CONFIG,
    )


# ============================================================================ REPL

def _repl(args: argparse.Namespace) -> int:
    """Very small REPL. Meta-commands listed in prompts/qwen_companion.txt."""
    from memory import qwen_facts
    _initialize_profile_if_missing()

    policy = _make_policy()
    try:
        client = _make_local_client(policy)
    except Exception as e:
        print(f"❌ could not create local LLM client: {e}", file=sys.stderr)
        return 2
    if not client.is_available():
        print(f"❌ Ollama not reachable at {client.base_url} or model "
              f"{client.model!r} not pulled. "
              f"Run `ollama serve` and `ollama pull {client.model}`.",
              file=sys.stderr)
        return 3

    print(f"[qwen-companion] connected to {client.model} at {client.base_url}")
    print("[qwen-companion] meta: :remember TOPIC: TEXT | :forget TEXT | "
          ":facts | :self-tune | :reset | exit")

    history: list[dict[str, str]] = []

    while True:
        try:
            raw = input("\n[you] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if not raw:
            continue
        if raw in ("exit", ":exit", "quit", ":quit"):
            return 0

        # meta-commands
        if raw == ":reset":
            history.clear()
            print("[history cleared; facts preserved]")
            continue
        if raw == ":facts":
            facts = qwen_facts.load()
            if not facts:
                print("(no facts stored)")
            else:
                for f in facts:
                    print(f"  [{f.topic}] {f.text}")
            continue
        if raw.startswith(":remember "):
            body = raw[len(":remember "):]
            topic, _, txt = body.partition(":")
            topic = topic.strip() or "misc"
            txt = txt.strip()
            if not txt:
                print("usage: :remember TOPIC: TEXT")
                continue
            added = qwen_facts.add(topic, txt)
            print("[added]" if added else "[already present]")
            continue
        if raw.startswith(":forget "):
            txt = raw[len(":forget "):].strip()
            removed = qwen_facts.remove(txt)
            print("[removed]" if removed else "[not found]")
            continue
        if raw == ":self-tune":
            from qwen_companion import self_tune
            anthropic_client = _make_anthropic_client(policy)
            res = self_tune.run_self_tune(
                qwen_client=client,
                anthropic_client=anthropic_client,
                force=True,
            )
            print(f"[self-tune] promoted={res.promoted} rolled_back={res.rolled_back} "
                  f"iter={res.iterations} :: {res.reason}")
            # Profile may have changed; rebuild client so the new config
            # takes effect in this session.
            if res.promoted:
                client = _make_local_client(policy)
                print("[self-tune] client re-bound to new profile")
            continue

        # regular turn
        t0 = time.perf_counter()
        try:
            result = client.call(
                agent="qwen_companion",
                user_turn=raw,
                task_type="route_decision",
                conversation_history=history,
            )
        except Exception as e:
            print(f"❌ call failed: {e}")
            continue
        elapsed = time.perf_counter() - t0
        text = (result.get("text") or "").strip()
        print(f"\n[qwen] ({elapsed:.1f}s)\n{text}")
        history.append({"role": "user", "content": raw})
        history.append({"role": "assistant", "content": text})
        # Trim history to last ~20 turns to keep prompts small.
        if len(history) > 40:
            history = history[-40:]


# ============================================================================ subcommands

def _cmd_self_tune(args: argparse.Namespace) -> int:
    from qwen_companion import self_tune
    _initialize_profile_if_missing()
    policy = _make_policy()
    client = _make_local_client(policy)
    anthropic_client = _make_anthropic_client(policy)
    res = self_tune.run_self_tune(
        qwen_client=client,
        anthropic_client=anthropic_client,
        force=args.force,
    )
    print(f"promoted={res.promoted} rolled_back={res.rolled_back} "
          f"iter={res.iterations}\nreason: {res.reason}")
    if res.boot:
        print(f"boot: ok={res.boot.ok} elapsed={res.boot.elapsed_s:.1f}s")
        if not res.boot.ok and res.boot.stderr:
            print("stderr tail:\n" + res.boot.stderr[-400:])
    return 0 if res.promoted or "no change" in res.reason.lower() else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    _initialize_profile_if_missing()
    policy = _make_policy()
    try:
        client = _make_local_client(policy)
    except Exception as e:
        print(f"❌ client construction failed: {e}")
        return 2
    ok = client.is_available()
    print(f"ollama_reachable: {ok}")
    print(f"model: {client.model}")
    print(f"base_url: {client.base_url}")
    print(f"profile_main: {get_paths().qwen_profile_main}")
    print(f"profile_backup: {get_paths().qwen_profile_backup}")
    return 0 if ok else 1


def _cmd_facts(args: argparse.Namespace) -> int:
    from memory import qwen_facts
    for f in qwen_facts.load():
        print(f"[{f.topic}] {f.text}")
    return 0


# ============================================================================ entry

def main(argv: list[str] | None = None) -> int:
    # Vault: only relevant if there are encrypted entries. The companion
    # itself doesn't need Anthropic — it talks to Ollama — but the
    # iterative self-tune policy may invoke Commander, which needs the
    # ANTHROPIC_API_KEY. We unlock eagerly so the user only types the
    # password once per session.
    from core.secret_env import is_unlocked
    if not is_unlocked():
        try:
            from core.secrets_vault import has_any_encrypted, load_env_file
            if has_any_encrypted(load_env_file(get_paths().root)):
                from core.unlock import unlock_interactive
                unlock_interactive(get_paths().root)
        except Exception as e:
            log.debug("vault_unlock_skipped", err=str(e))

    p = argparse.ArgumentParser(prog="qwen_companion")
    sub = p.add_subparsers(dest="cmd")

    sp_tune = sub.add_parser("self-tune", help="run one self-tune cycle")
    sp_tune.add_argument("--force", action="store_true",
                         help="skip cooldown + calendar-day gates")
    sp_tune.set_defaults(func=_cmd_self_tune)

    sp_ver = sub.add_parser("verify-config", help="check profile + Ollama")
    sp_ver.set_defaults(func=_cmd_verify)

    sp_fac = sub.add_parser("facts", help="list stored facts")
    sp_fac.set_defaults(func=_cmd_facts)

    args = p.parse_args(argv)
    if args.cmd is None:
        return _repl(args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
