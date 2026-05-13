# core/litellm_bridge.py
"""LiteLLM ↔ PolicyRuntime cost-tracking bridge.

smolagents drives Anthropic via LiteLLM. LiteLLM doesn't know about
PolicyRuntime, so by default our distribution / budget tracking sees
nothing when CodeAgent does its ReAct loop. This module installs a
LiteLLM `success_callback` that records every completed call.

Identifying which agent made the call
--------------------------------------
LiteLLM doesn't propagate arbitrary metadata reliably across all its
internal hooks, so we use a simpler trick: each agent gets a UNIQUE
api_key (the user's per-agent vault keys), and we maintain a
`api_key → agent_role` registry. The callback looks up the role from
the kwargs's api_key.

This works because in our deployment every role really does have a
distinct key (vault enforcement). If two agents accidentally share a
key, the registry only remembers the first registered — that's a
defect we want to surface anyway.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from core.policy_runtime import PolicyRuntime

log = get_logger("litellm_bridge")


_installed = False
_policy: PolicyRuntime | None = None
_project_root = None  # for usage_persist
# Map of api_key prefix → agent role. We keep just a prefix (first 12
# chars) so the actual key never lives in our state for longer than
# the registry call itself.
_KEY_PREFIX_LEN = 12
_key_to_agent: dict[str, str] = {}


def install(policy: PolicyRuntime, project_root=None) -> None:
    """Wire LiteLLM success/failure callbacks to PolicyRuntime.

    Idempotent — repeat calls update the policy reference but don't
    double-register.
    """
    global _installed, _policy, _project_root
    _policy = policy
    _project_root = project_root
    if _installed:
        return

    try:
        import litellm
    except ImportError:
        log.warning("litellm_not_installed_no_cost_tracking")
        return

    if not isinstance(litellm.success_callback, list):
        litellm.success_callback = []
    litellm.success_callback.append(_litellm_success_handler)

    if not isinstance(litellm.failure_callback, list):
        litellm.failure_callback = []
    litellm.failure_callback.append(_litellm_failure_handler)

    _installed = True
    log.info("litellm_bridge_installed")


def register_agent_key(agent_role: str, api_key: str) -> None:
    """Register that calls with this api_key prefix come from `agent_role`.

    Called by config.get_api_key_with_register() — we tag every key
    handed out so the callback can identify the caller.

    Silently skipped if the key is empty or already registered to
    a different role (which would indicate two agents sharing a key —
    we keep the first registration to avoid surprises).
    """
    if not api_key:
        return
    prefix = api_key[:_KEY_PREFIX_LEN]
    existing = _key_to_agent.get(prefix)
    if existing and existing != agent_role:
        log.warning("agent_key_collision",
                    prefix=prefix[:8] + "...",
                    keeping=existing,
                    rejected=agent_role)
        return
    _key_to_agent[prefix] = agent_role


def _agent_from_kwargs(kwargs: dict[str, Any]) -> str | None:
    """Best-effort: identify which agent issued this LiteLLM call.

    Resolution order:
      1. explicit metadata.paper_ai_agent (if some path passes it)
      2. api_key prefix lookup against _key_to_agent
      3. None (call goes into the unattributed bucket)
    """
    md = kwargs.get("metadata") or {}
    if isinstance(md, dict) and md.get("paper_ai_agent"):
        return str(md["paper_ai_agent"])

    api_key = kwargs.get("api_key") or ""
    if api_key:
        prefix = api_key[:_KEY_PREFIX_LEN]
        return _key_to_agent.get(prefix)
    return None


def _litellm_success_handler(
    kwargs: dict[str, Any],
    completion_response: Any,
    start_time: Any,
    end_time: Any,
) -> None:
    """Called by LiteLLM after every successful completion.

    Defensive — callback exceptions must never propagate to the agent
    loop.
    """
    if _policy is None:
        return
    try:
        model = kwargs.get("model", "") or ""
        if "/" in model:
            provider, model = model.split("/", 1)
        else:
            provider = ""

        # Normalise so PolicyRuntime sees a consistent prefix:
        #   anthropic/...  → strip provider, keep bare id (priced via PRICING)
        #   ollama/qwen... → "local:qwen..." (free, separate bucket)
        # Other providers (openai, etc.) get their bare id; PolicyRuntime
        # falls back to Opus pricing as a conservative estimate.
        if provider == "ollama":
            model = f"local:{model}"

        usage = _extract_usage(completion_response)
        if not usage:
            return

        agent = _agent_from_kwargs(kwargs)
        cost = _policy.record_call(model, usage, agent=agent)

        # Persistent lifetime totals
        if _project_root is not None:
            try:
                from core import usage_persist
                usage_persist.record(
                    _project_root,
                    model=model,
                    usage=usage,
                    cost_usd=cost,
                    agent=agent,
                )
            except Exception as e:
                log.warning("persist_record_failed", err=str(e))

        log.info("litellm_call_recorded",
                 agent=agent or "?",
                 model=model,
                 in_tok=usage.get("input_tokens", 0),
                 out_tok=usage.get("output_tokens", 0),
                 cost_usd=round(cost, 5))
    except Exception as e:
        log.warning("litellm_success_handler_error", err=str(e))


def _litellm_failure_handler(
    kwargs: dict[str, Any],
    completion_response: Any,
    start_time: Any,
    end_time: Any,
) -> None:
    if _policy is None:
        return
    try:
        model = kwargs.get("model", "") or ""
        agent = _agent_from_kwargs(kwargs) or "?"
        log.warning("litellm_call_failed",
                    agent=agent, model=model,
                    err=str(completion_response)[:160] if completion_response else "?")
    except Exception:
        pass


def _extract_usage(response: Any) -> dict[str, int]:
    """Pull usage tokens off a LiteLLM completion response."""
    if response is None:
        return {}
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return {}

    def _g(obj, name, default=0):
        if hasattr(obj, name):
            return getattr(obj, name) or default
        if isinstance(obj, dict):
            return obj.get(name, default) or default
        return default

    in_tok = _g(usage, "prompt_tokens") or _g(usage, "input_tokens")
    out_tok = _g(usage, "completion_tokens") or _g(usage, "output_tokens")
    cache_read = _g(usage, "cache_read_input_tokens")
    cache_write = _g(usage, "cache_creation_input_tokens")

    return {
        "input_tokens": int(in_tok or 0),
        "output_tokens": int(out_tok or 0),
        "cache_read_input_tokens": int(cache_read or 0),
        "cache_creation_input_tokens": int(cache_write or 0),
    }
