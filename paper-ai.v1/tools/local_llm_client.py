"""Local LLM client — Qwen2.5 72B via Ollama.

Mirrors the public surface of `tools.anthropic_client.AnthropicClient.call()`
just enough that `LLMClientRouter` can hand a request to either backend
without the agent caring which one runs it.

Why Ollama
----------
Two reasons:
1. We don't want to bake a heavy local-inference stack (transformers + vLLM
   + CUDA wheels) into the project. Ollama runs as a separate daemon the
   user manages, exposes an OpenAI-compatible HTTP endpoint, and keeps
   its own model cache. The Python side stays a thin HTTP client.
2. Hot-swappable: switching from `qwen2.5:72b` to a different local model
   is a config edit, not a code change.

Pricing
-------
Local inference is recorded with `cost_usd=0`. We DO track tokens (so
`PolicyRuntime.distribution()` and budget warnings still see the load)
and elapsed seconds — wall-clock is the real cost on a GPU box and a
useful signal for self-upgrade decisions ("Qwen takes 12s for a
classify, route to Haiku instead").

Cache compatibility
-------------------
Ollama doesn't have prompt-prefix caching like Anthropic. We surface
`cache_stats={"hit_ratio": 0.0, ...}` so downstream code (logging,
PolicyRuntime) doesn't need to special-case the local backend.
"""

from __future__ import annotations

import time
from typing import Any

from core.logger import get_logger

log = get_logger("local_llm")


class LocalLLMUnavailable(RuntimeError):
    """Raised when Ollama daemon is unreachable or the model isn't loaded.
    Caller (LLMClientRouter) should fall back to AnthropicClient."""


class LocalLLMClient:
    """Ollama-backed client for routing simple tasks off the paid API."""

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen2.5:72b"
    DEFAULT_TIMEOUT_S = 120.0

    def __init__(
        self,
        *,
        policy,                                  # PolicyRuntime
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
    ):
        self.policy = policy
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.timeout_s = timeout_s or self.DEFAULT_TIMEOUT_S
        self._available_cached: bool | None = None

    # ------------------------------------------------------------ availability

    def is_available(self) -> bool:
        """Quick health probe. Cached for the process lifetime — flip back to
        None via `invalidate_availability()` if the daemon may have started
        mid-run.
        """
        if self._available_cached is not None:
            return self._available_cached
        try:
            import requests
        except ImportError:
            log.warning("local_llm_unavailable", reason="requests not installed")
            self._available_cached = False
            return False
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            ok = r.status_code == 200
            if ok:
                # Optional: ensure our model is actually loadable. We don't
                # require it to be currently loaded — Ollama will load on
                # first request — just registered with `ollama pull`.
                tags = r.json().get("models", [])
                names = {m.get("name", "") for m in tags}
                if not any(self.model in n or n == self.model for n in names):
                    log.warning("local_llm_model_not_pulled",
                                model=self.model,
                                available=sorted(names))
                    self._available_cached = False
                    return False
            self._available_cached = ok
            return ok
        except Exception as e:
            log.info("local_llm_probe_failed", err=str(e))
            self._available_cached = False
            return False

    def invalidate_availability(self) -> None:
        self._available_cached = None

    # ------------------------------------------------------------ call

    def call(
        self,
        *,
        agent: str,
        user_turn: str,
        task_type: str | None = None,
        force_model: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        shared_artifacts: str | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
        extra_context: str | None = None,
    ) -> dict[str, Any]:
        """Same return shape as AnthropicClient.call().

        `tool_schemas` is silently ignored — the simple tasks we route
        to local don't need function calling. If a routed task suddenly
        starts requesting tools, the LLMClientRouter should refuse to
        send it here.
        """
        if not self.is_available():
            raise LocalLLMUnavailable(
                f"Ollama at {self.base_url} not reachable or model "
                f"{self.model!r} not pulled"
            )

        try:
            import requests
        except ImportError as e:
            raise LocalLLMUnavailable("requests package missing") from e

        # Build the prompt. Local model has no prefix cache so we just
        # concatenate everything in a fixed order. The system prompt
        # (`prompts/{agent}.txt`) is loaded by reusing the same loader the
        # Anthropic client uses, but to keep this client decoupled we let
        # the caller pass everything via `extra_context`.
        system_text = self._load_system_prompt(agent)
        sys_parts: list[str] = [system_text]
        if shared_artifacts:
            sys_parts.append("## Shared blackboard\n" + shared_artifacts)
        if extra_context:
            sys_parts.append(extra_context)
        system_block = "\n\n".join(p for p in sys_parts if p)

        messages: list[dict[str, str]] = [{"role": "system", "content": system_block}]
        if conversation_history:
            for m in conversation_history:
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_turn})

        # Routing decision (max_tokens etc.) goes through the same policy
        # so behaviour stays consistent. force_model is honoured only if it
        # explicitly names the local model.
        max_tokens = 1024
        if task_type:
            spec = self.policy.routing.get("task_types", {}).get(task_type, {})
            max_tokens = int(spec.get("max_tokens", max_tokens))
        if force_model and force_model not in (self.model, "local", "qwen", "qwen2.5"):
            log.warning("local_llm_force_model_ignored", requested=force_model)

        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                # Greedy-ish defaults for the categorical tasks this serves.
                # Self-upgrade can adjust per task_type later.
                "temperature": 0.2,
                "num_predict": max_tokens,
            },
        }
        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=body,
                timeout=self.timeout_s,
            )
        except requests.Timeout:
            raise LocalLLMUnavailable(
                f"local LLM timed out after {self.timeout_s}s"
            )
        except Exception as e:
            raise LocalLLMUnavailable(f"local LLM call failed: {e!r}") from e
        elapsed = time.perf_counter() - t0

        if r.status_code != 200:
            raise LocalLLMUnavailable(
                f"local LLM HTTP {r.status_code}: {r.text[:200]}"
            )
        data = r.json()
        text = (data.get("message") or {}).get("content", "")
        # Ollama returns prompt_eval_count / eval_count in newer versions.
        in_tok = int(data.get("prompt_eval_count", 0) or 0)
        out_tok = int(data.get("eval_count", 0) or 0)
        usage = {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        }

        # Local inference: cost in USD is 0. Pass the model name through
        # PolicyRuntime so distribution counters update; pricing fallback
        # would otherwise charge Opus rates by default. We register the
        # local model name with explicit zero pricing — see
        # PolicyRuntime.register_local_model().
        cost = self.policy.record_call(self._policy_model_id(), usage)

        log.info("local_llm_call",
                 agent=agent, task_type=task_type or "default",
                 in_tok=in_tok, out_tok=out_tok,
                 elapsed_s=round(elapsed, 2))

        return {
            "text": text,
            "stop_reason": data.get("done_reason") or "stop",
            "usage": usage,
            "model": self._policy_model_id(),
            "cost_usd": cost,         # always 0.0 for local
            "cache_stats": {
                "hit_ratio": 0.0,
                "read_tokens": 0,
                "write_tokens": 0,
                "fresh_tokens": in_tok,
            },
            "elapsed_s": elapsed,     # local-only field; ignored by callers
                                      # that don't know about it
            "raw": None,
        }

    # ------------------------------------------------------------ helpers

    def _policy_model_id(self) -> str:
        """Return the model identifier as PolicyRuntime knows it.
        Format: `local:qwen2.5:72b`. The `local:` prefix lets the
        pricing table give it $0 explicitly rather than by absence.
        """
        return f"local:{self.model}"

    def _load_system_prompt(self, agent: str) -> str:
        """Compose the system prompt from three sources:

            1. The Qwen profile's `prompt.txt` (main profile, self-tuned)
            2. The per-agent prompt file at `prompts/{agent}.txt`
               — treated as a specialisation on top of the profile's
               system voice
            3. The shared facts store (`memory/qwen_facts.md`) rendered
               into a compact block

        The profile prompt takes priority because self-tuning can improve
        it over time; the per-agent file is appended as a role hint. For
        the `qwen_companion` agent specifically we skip step 2 (the
        profile IS the agent prompt).

        If the profile directory is missing or empty (first run before
        any initialisation), we fall back to reading `prompts/{agent}.txt`
        alone, same as before.
        """
        from core.paths import get_paths
        paths = get_paths()

        profile_prompt = ""
        try:
            from memory.qwen_profile import QwenProfile
            prof = QwenProfile.from_files(paths.qwen_profile_main)
            profile_prompt = (prof.prompt or "").strip()
        except Exception as e:
            log.debug("qwen_profile_load_failed_in_prompt_assembly",
                      err=str(e))

        per_agent = ""
        if agent != "qwen_companion":
            agent_path = paths.prompts / f"{agent}.txt"
            if agent_path.exists():
                per_agent = agent_path.read_text(encoding="utf-8").strip()

        facts_block = ""
        try:
            from memory import qwen_facts
            entries = qwen_facts.load()
            facts_block = qwen_facts.render_for_prompt(entries)
        except Exception as e:
            log.debug("facts_load_failed", err=str(e))

        parts: list[str] = []
        if profile_prompt:
            parts.append(profile_prompt)
        elif not per_agent:
            # No profile and no per-agent file — last resort fallback
            # to the companion prompt file, if present.
            comp_path = paths.prompts / "qwen_companion.txt"
            if comp_path.exists():
                parts.append(comp_path.read_text(encoding="utf-8").strip())
        if per_agent:
            parts.append("## Role specialisation\n" + per_agent)
        if facts_block:
            parts.append(facts_block)

        return "\n\n".join(parts)

    # ------------------------------------------------------------ trivial wrappers

    def local_cache_stats(self) -> dict[str, Any]:
        """Stub so AnthropicClient-shaped callers don't crash."""
        return {"enabled": False, "backend": "ollama"}
