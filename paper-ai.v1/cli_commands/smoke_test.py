"""--smoke-test subcommand: check every agent + Qwen are reachable.

Pings each of the six agent's LiteLLMModel directly with a tiny prompt.
This bypasses smolagents.CodeAgent's full ReAct loop — we just want
to confirm:

  * The vault unlocks.
  * Each per-agent API key is valid (Anthropic accepts it).
  * The configured model id is recognised.
  * Qwen / Ollama is reachable.

Failures are classified per-agent so the user can fix exactly the
broken key without repeating the diagnostic.

Two modes
---------
  default     : all six agents + Qwen → ~$0.0002 total cost
                (every agent receives the same trivial prompt; the
                 model-id is unchanged so Sonnet vs Haiku are still
                 distinct calls — we just don't ask for hard work)

  --thorough  : same six agents but with longer prompts that exercise
                the real model id properly. ~$0.005-0.01.

  --no-qwen   : skip the Ollama probe (e.g. on a machine without it).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("smoke_test")


# Keep this prompt minimal — we want to confirm the LLM responds, not
# stress-test it. "OK" or one short word is fine.
SMOKE_PROMPT = (
    "Reply with one short word that means 'acknowledged'. "
    "No explanation. No punctuation."
)

THOROUGH_PROMPT = (
    "Briefly (one to two sentences) acknowledge this test message. "
    "No code. No analysis. Just acknowledge."
)


AGENTS = ("commander", "librarian", "idea", "experimenter", "reviewer", "writer")


def run(root: Path, *, skip_qwen: bool = False, thorough: bool = False) -> int:
    """Entry point called from cli.py."""
    # We need to bootstrap the vault so get_api_key works.
    _bootstrap_vault(root)

    mode = "thorough" if thorough else "cheap"
    print(f"\n🔬 paper-ai smoke test — pinging {len(AGENTS)} agents + Qwen")
    print(f"   mode: {mode}\n")
    print(f"{'AGENT':<14} {'STATUS':<10} {'MODEL':<32} {'ms':>6}  NOTES")
    print("-" * 90)

    results: list[dict[str, Any]] = []

    for role in AGENTS:
        prompt = THOROUGH_PROMPT if thorough else SMOKE_PROMPT
        row = _ping_agent(role, prompt=prompt)
        results.append(row)
        _print_row(row)

    if skip_qwen:
        results.append({
            "agent": "qwen (local)", "ok": None,
            "model": "—", "ms": 0, "note": "skipped (--no-qwen)",
        })
        _print_row(results[-1])
    else:
        row = _ping_qwen(root)
        results.append(row)
        _print_row(row)

    print("-" * 90)

    n_ok = sum(1 for r in results if r["ok"] is True)
    n_fail = sum(1 for r in results if r["ok"] is False)
    n_skip = sum(1 for r in results if r["ok"] is None)
    print(f"\nSummary: {n_ok} ok, {n_fail} fail, {n_skip} skipped")

    if n_fail:
        print("\n❌ Failures:")
        for r in results:
            if r["ok"] is False:
                print(f"   • {r['agent']:14s}  {r['note']}")
        return 1
    if n_ok < len(AGENTS):
        print("\n✅ Anthropic agents pass. Qwen not tested.")
        return 0
    print("\n✅ All agents and Qwen reachable. Run `python commander.py` "
          "for the real pipeline.")
    return 0


# ============================================================================ helpers


def _bootstrap_vault(root: Path) -> None:
    """Unlock the encrypted vault before agent imports trigger get_api_key."""
    try:
        from core.secrets_vault import has_any_encrypted, load_env_file
        from core.unlock import unlock, is_unlocked
    except ImportError:
        return
    try:
        lines = load_env_file(root)
    except Exception:
        return
    if not has_any_encrypted(lines) or is_unlocked():
        return
    import getpass
    import sys
    try:
        pw = getpass.getpass("Vault password: ")
    except (EOFError, KeyboardInterrupt):
        print("\naborted at password prompt.", file=sys.stderr)
        sys.exit(2)
    try:
        unlock(root, pw)
    except Exception as e:
        print(f"unlock failed: {e}", file=sys.stderr)
        sys.exit(2)


def _ping_agent(role: str, *, prompt: str) -> dict[str, Any]:
    """Send one LiteLLM call as `role`. Capture timing + outcome."""
    t0 = time.perf_counter()
    try:
        from config import get_api_key, get_model_id
        from smolagents import LiteLLMModel
        from smolagents.models import ChatMessage

        model_id = get_model_id(role)
        api_key = get_api_key(role)
        model = LiteLLMModel(
            model_id=f"anthropic/{model_id}",
            api_key=api_key,
        )
        # smolagents LiteLLMModel.__call__ wants a list of ChatMessage.
        # We use a minimal user message and ignore the result text — we
        # just want to confirm the call returns without raising.
        messages = [ChatMessage(role="user", content=prompt)]
        result = model(messages)
        text = getattr(result, "content", None) or str(result)
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "agent": role,
            "ok": True,
            "model": model_id,
            "ms": dt_ms,
            "note": (text or "").strip()[:40] or "(empty reply)",
        }
    except Exception as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        log.error(
            "smoke_agent_failed",
            agent=role,
            err_type=type(e).__name__,
            err=str(e),
        )
        return {
            "agent": role, "ok": False,
            "model": "—", "ms": dt_ms,
            "note": f"{type(e).__name__}: {str(e)[:80]}",
        }


def _ping_qwen(root: Path) -> dict[str, Any]:
    """Reuse the existing LocalLLMClient — nothing changes here."""
    t0 = time.perf_counter()
    try:
        from core.policy_runtime import PolicyRuntime
        from memory.qwen_profile import QwenProfileManager
        from tools.local_llm_client import LocalLLMClient, LocalLLMUnavailable

        policy = PolicyRuntime(config_dir=str(root / "config"))
        mgr = QwenProfileManager()
        prompt_path = root / "prompts" / "qwen_companion.txt"
        default_prompt = (
            prompt_path.read_text(encoding="utf-8") if prompt_path.is_file()
            else "You are the user's local Qwen assistant. Be concise."
        )
        mgr.initialize_default(
            default_prompt=default_prompt,
            default_config={
                "model": "qwen2.5:72b",
                "base_url": "http://127.0.0.1:11434",
                "timeout_s": 120,
                "temperature": 0.2,
                "num_predict_cap": 1024,
                "prompt_style": "default",
            },
        )
        prof = mgr.load_main()
        cfg = prof.config or {}
        client = LocalLLMClient(
            policy=policy,
            model=cfg.get("model", "qwen2.5:72b"),
            base_url=cfg.get("base_url", "http://127.0.0.1:11434"),
            timeout_s=float(cfg.get("timeout_s", 120)),
        )
        if not client.is_available():
            raise LocalLLMUnavailable(
                f"Ollama at {client.base_url} not reachable, or model "
                f"{client.model!r} not pulled. Try `ollama serve` and "
                f"`ollama pull {client.model}`."
            )
        result = client.call(
            agent="qwen_companion",
            user_turn="Reply with the single word OK.",
            task_type="classify",
        )
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "agent": "qwen (local)", "ok": True,
            "model": client.model, "ms": dt_ms,
            "note": (result.get("text", "") or "").strip()[:40] or "(empty)",
        }
    except Exception as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        log.error("smoke_qwen_failed",
                  err_type=type(e).__name__, err=str(e))
        return {
            "agent": "qwen (local)", "ok": False,
            "model": "—", "ms": dt_ms,
            "note": f"{type(e).__name__}: {str(e)[:80]}",
        }


def _print_row(row: dict[str, Any]) -> None:
    if row["ok"] is True:
        status = "✓ ok"
    elif row["ok"] is False:
        status = "✗ FAIL"
    else:
        status = "—"
    model = row.get("model", "—")
    if len(model) > 32:
        model = model[:29] + "..."
    print(f"{row['agent']:<14} {status:<10} {model:<32} "
          f"{row['ms']:>6}  {row['note']}")
