"""Anthropic Claude client with multi-breakpoint prompt caching.

This is the Phase-1 centerpiece. Everything downstream (agents, orchestrator)
goes through AnthropicClient.call() so caching + routing + budget are
enforced in one place.

Prompt structure (per config/caching.yaml):
    [Layer 0] system_prompt         @ 1h cache
    [Layer 1] tool_schemas          @ 1h cache (if tools)
    [Layer 2] skill_metadata        @ 1h cache (if skills)
    [Layer 3] shared_artifacts      @ 1h cache (blackboard snapshot)
    [Layer 4] conversation_history  @ 5m cache
    (current user turn — never cached)

References:
    - Anthropic prompt caching docs (2026)
    - Finout.io $4500→$666/mo case study (Apr 2026)
    - Agent Skills overview (Oct 2025, progressive disclosure)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.logger import get_logger
from core.policy_runtime import BudgetExceeded, PolicyRuntime

if TYPE_CHECKING:
    from memory.cache import ResponseCache

log = get_logger("anthropic_client")


class AnthropicClient:
    """Token-efficient wrapper around anthropic.Anthropic().messages.create."""

    # -------- Cache breakpoint thresholds -------------------------------------
    # Anthropic requires ≥1024 tokens per breakpoint (2048 on Haiku).
    # We use rough char/token ratio ≈ 3.5 for English + code to decide whether
    # a layer is "big enough" to be worth a breakpoint slot.
    MIN_TOKENS_DEFAULT = 1024
    MIN_TOKENS_HAIKU = 2048
    CHARS_PER_TOKEN_APPROX = 3.5
    MAX_BREAKPOINTS = 4  # Anthropic hard limit per request

    # The six worker roles paper-ai actually instantiates.
    _KNOWN_AGENTS: frozenset[str] = frozenset({
        "commander", "idea", "librarian", "experimenter", "reviewer", "writer",
    })

    # Legacy / sub-role aliases that map to the consolidated agents.
    # paper-ai used to have nine agents; some users still keep nine
    # separate Anthropic keys (one per sub-task) for billing/tracking
    # purposes. We honour those names by mapping them onto the agent
    # that actually does the work today. The mapping picks the FIRST
    # alias whose env var is set, so the user can keep any subset of
    # the sub-keys without a conflict.
    #
    # Format:  {agent_role: [primary_env_suffix, *legacy_aliases]}
    # The primary suffix is the canonical name (matches the agent
    # role); aliases are the historical names from the 9-agent layout.
    _AGENT_KEY_ALIASES: dict[str, list[str]] = {
        "commander":    ["COMMANDER"],
        "idea":         ["IDEA"],
        "librarian":    ["LIBRARIAN"],
        # experimenter absorbed Experiment + Coder + Visualization
        "experimenter": ["EXPERIMENTER", "EXPERIMENT", "CODER", "VISUALIZATION"],
        # reviewer absorbed Validator + Proofreader
        "reviewer":     ["REVIEWER", "VALIDATOR", "PROOFREADER"],
        "writer":       ["WRITER"],
    }

    def __init__(
        self,
        policy: PolicyRuntime,
        *,
        api_key: str | None = None,
        project_root: Path | str = ".",
        response_cache: "ResponseCache | None" = None,
    ):
        self.policy = policy
        self.root = Path(project_root)

        # ---- API key policy: STRICT per-agent ---------------------------
        # Every agent must have its own ANTHROPIC_API_KEY_<NAME> entry.
        # The legacy 9-key layout is supported via the alias table above:
        # for example, ANTHROPIC_API_KEY_CODER satisfies the experimenter
        # agent's requirement. The shared `ANTHROPIC_API_KEY` fallback is
        # NOT used — separate keys make billing + audit per role
        # straightforward, which is the reason the user asked for them.
        #
        # `api_key=` is still accepted for tests and for callers that
        # want to drive a single client with a specific key, but it does
        # NOT participate in the per-agent resolution: it's used only as
        # an emergency last-resort when no per-agent key is configured,
        # so test harnesses keep working.
        self._explicit_api_key = api_key

        # Lazily-built per-agent SDK client cache. Populated on first
        # call from each agent so we don't pay SDK construction cost
        # for agents that never run.
        self._agent_clients: dict[str, "anthropic.Anthropic"] = {}

        # Surface the topology once so users can confirm their .env was
        # parsed correctly. We log alias hits so a user who sets
        # ANTHROPIC_API_KEY_CODER can see it being honoured for
        # 'experimenter'.
        self._log_key_topology()

        # ---- Lazy-loaded caches (unchanged) -----------------------------
        self._prompt_cache: dict[str, Any] = {}
        self._skill_meta_cache: dict[str, Any] = {}

        caching_cfg = self.policy.caching
        self.caching_enabled = caching_cfg.get("enabled", True)
        self.tool_cache_enabled = caching_cfg["tools"]["cache_definitions"]

        if response_cache is not None:
            self._local_cache = response_cache
        elif self.policy.settings.get("response_cache", {}).get("enabled", True):
            from core.paths import get_paths
            from memory.cache import ResponseCache
            self._local_cache = ResponseCache(
                get_paths().cache_dir / "response_cache.db"
            )
        else:
            self._local_cache = None

    # ------------------------------------------------------------------ keys

    def _resolve_key_for_agent(self, agent: str) -> tuple[str | None, str | None]:
        """Find the API key for `agent`. Returns (key, source_name).

        Walks the alias list for the agent in order, checking secret_env
        first then os.environ for each name. The first hit wins; later
        aliases are ignored. Returns (None, None) if nothing is set —
        the caller decides whether that's fatal.
        """
        try:
            from core import secret_env
            secret_lookup = secret_env.get
        except Exception:
            secret_lookup = lambda _name: None  # noqa: E731

        for suffix in self._AGENT_KEY_ALIASES.get(agent, [agent.upper()]):
            env_name = f"ANTHROPIC_API_KEY_{suffix}"
            v = secret_lookup(env_name) or os.environ.get(env_name)
            if v:
                return v, env_name
        return None, None

    def _log_key_topology(self) -> None:
        """Log per-agent key sources at startup. Helps users catch typos
        in env var names before any API call is made."""
        sources: dict[str, str | None] = {}
        for agent in sorted(self._KNOWN_AGENTS):
            _, src = self._resolve_key_for_agent(agent)
            sources[agent] = src
        log.info(
            "anthropic_key_topology",
            agents_with_key={a: s for a, s in sources.items() if s},
            agents_unconfigured=[a for a, s in sources.items() if s is None],
            explicit_arg_present=bool(self._explicit_api_key),
        )

    def _client_for_agent(self, agent: str) -> "anthropic.Anthropic":
        """Return the SDK client for `agent`, building one on first use.

        Resolution: per-agent key (with alias support) → explicit
        constructor arg → error. There is no shared-default fallback;
        the user explicitly opted into separate keys per role.
        """
        if agent in self._agent_clients:
            return self._agent_clients[agent]

        key, source = self._resolve_key_for_agent(agent)
        if key:
            log.info("agent_specific_api_key_in_use",
                     agent=agent, source=source)
            sdk = anthropic.Anthropic(api_key=key)
        elif self._explicit_api_key:
            # Test/embedded path: the caller passed a key explicitly.
            # We don't normally want this in production, but it lets
            # unit tests construct a client without populating .env.
            sdk = anthropic.Anthropic(api_key=self._explicit_api_key)
        else:
            primary = f"ANTHROPIC_API_KEY_{self._AGENT_KEY_ALIASES.get(agent, [agent.upper()])[0]}"
            aliases = self._AGENT_KEY_ALIASES.get(agent, [])[1:]
            alias_msg = ""
            if aliases:
                alias_msg = (" (legacy aliases also accepted: "
                             + ", ".join(f"ANTHROPIC_API_KEY_{a}" for a in aliases)
                             + ")")
            raise RuntimeError(
                f"No API key configured for agent {agent!r}. Set "
                f"{primary} in .env{alias_msg}. Encrypt with "
                f"`python encrypt_key.py --key-name {primary}`."
            )
        self._agent_clients[agent] = sdk
        return sdk

    def local_cache_stats(self) -> dict[str, Any]:
        """Expose local ResponseCache stats for CLI/reporter."""
        return self._local_cache.stats() if self._local_cache else {
            "enabled": False,
        }

    # ========================================================================
    # Public API
    # ========================================================================

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
        """Call Claude with cache-friendly layered prompts.

        Args:
            agent: One of "commander" | "idea" | "librarian" | "experimenter" |
                   "reviewer" | "writer".
            user_turn: The current-turn user message (never cached).
            task_type: Hint for router (e.g. "draft_section", "lookup_citation").
            force_model: Override routing (rare).
            conversation_history: List of {role, content} dicts, older first.
            shared_artifacts: Concatenated blackboard snapshot (layer 3).
            tool_schemas: Anthropic tool definitions list (layer 1).
            extra_context: Any additional system-level context.

        Returns:
            {
                "text": "<assistant text>",
                "stop_reason": ...,
                "usage": {...},
                "model": "claude-sonnet-4-6",
                "cost_usd": 0.00234,
                "cache_stats": {...},
                "raw": <full anthropic response>,
            }
        """
        # --- 1. Route ---------------------------------------------------------
        route = self.policy.route(agent, task_type, force_model=force_model)
        model = route["model"]
        max_tokens = route["max_tokens"]
        thinking = route["thinking"]

        log.debug(
            "routing_decision",
            agent=agent,
            task_type=task_type,
            chosen_model=model,
            reason=route["reason"],
        )

        # --- 2. Assemble cacheable system blocks ------------------------------
        system_blocks = self._build_system_blocks(
            agent=agent,
            tool_schemas=tool_schemas,
            shared_artifacts=shared_artifacts,
            extra_context=extra_context,
            model=model,
        )

        # --- 3. Build messages (history + current turn) -----------------------
        messages = self._build_messages(
            conversation_history=conversation_history,
            user_turn=user_turn,
            model=model,
        )

        # --- 4. Budget pre-check ---------------------------------------------
        est_input = self._estimate_tokens(system_blocks, messages)
        self.policy.check_budget_before(model, est_input, max_tokens)

        # --- 4b. Local response-cache lookup ---------------------------------
        # Key on the exact request payload; bypass for interactive/creative
        # routing categories where determinism isn't desired.
        cache_key = None
        cache_skip_types = {"draft_section", "orchestrate", "novelty_analysis",
                            "proofread_text"}
        cache_eligible = (
            self._local_cache is not None and task_type not in cache_skip_types
        )
        if cache_eligible:
            cache_key = self._local_cache.make_key(
                model, system_blocks, messages,
                tool_schemas or [], max_tokens,
            )
            hit = self._local_cache.get(cache_key)
            if hit is not None:
                log.info("local_cache_hit",
                         agent=agent, task_type=task_type or "default",
                         key_prefix=cache_key[:12])
                # Serve from cache; still return a compatible dict shape
                return hit

        # --- 5. API call (with retry) ----------------------------------------
        response = self._call_with_retry(
            agent=agent,
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            thinking=thinking,
        )

        # --- 6. Record + return ----------------------------------------------
        usage_dict = self._extract_usage(response)
        cost = self.policy.record_call(model, usage_dict)
        text = self._extract_text(response)
        cache_stats = self._cache_stats(usage_dict)

        log.info(
            "agent_call_complete",
            agent=agent,
            model=model,
            task_type=task_type or "default",
            cache_hit_ratio=cache_stats["hit_ratio"],
            cost_usd=round(cost, 5),
        )

        result = {
            "text": text,
            "stop_reason": getattr(response, "stop_reason", None),
            "usage": usage_dict,
            "model": model,
            "cost_usd": cost,
            "cache_stats": cache_stats,
            "raw": None,   # intentionally drop raw SDK object for cache safety
        }

        # --- 7. Local-cache write (after we know it succeeded) ---------------
        if cache_eligible and cache_key is not None:
            try:
                # We can only cache JSON-serializable payloads; strip `raw`
                self._local_cache.put(cache_key, result)
            except Exception as e:
                log.warning("local_cache_put_failed", err=str(e))

        # Restore `raw` for callers in the immediate turn (it's stripped on
        # cache roundtrip but usable for the current caller).
        result["raw"] = response
        return result

    # ========================================================================
    # Internal: prompt assembly
    # ========================================================================

    def _build_system_blocks(
        self,
        *,
        agent: str,
        tool_schemas: list[dict[str, Any]] | None,
        shared_artifacts: str | None,
        extra_context: str | None,
        model: str,
    ) -> list[dict[str, Any]]:
        """Produce Anthropic-style `system` as a list of typed blocks with
        cache_control markers on layers 0–3.
        """
        blocks: list[dict[str, Any]] = []
        min_tokens = (
            self.MIN_TOKENS_HAIKU if "haiku" in model else self.MIN_TOKENS_DEFAULT
        )

        # --- Layer 0: system prompt (role + rules) — ALWAYS cached -----------
        system_text = self._load_prompt(agent)
        blocks.append(
            self._maybe_cached_block(
                text=system_text,
                ttl="1h",
                min_tokens=min_tokens,
                force_cache=True,   # always cache role prompt
            )
        )

        # --- Layer 1: tool schemas -------------------------------------------
        # (Anthropic's `tools=` parameter is separate; but we also expose
        #  a stable text summary of it inside `system` so the model sees it
        #  behind the cache breakpoint.)
        if tool_schemas and self.tool_cache_enabled:
            tool_text = "## Tools available\n" + _render_tools_as_text(tool_schemas)
            blocks.append(
                self._maybe_cached_block(
                    text=tool_text,
                    ttl="1h",
                    min_tokens=min_tokens,
                )
            )

        # --- Layer 2: skill metadata (progressive disclosure) ----------------
        skill_meta = self._skill_metadata_for(agent)
        if skill_meta:
            blocks.append(
                self._maybe_cached_block(
                    text=skill_meta,
                    ttl="1h",
                    min_tokens=min_tokens,
                )
            )

        # --- Layer 3: shared blackboard artifacts ----------------------------
        if shared_artifacts:
            blocks.append(
                self._maybe_cached_block(
                    text=shared_artifacts,
                    ttl="1h",
                    min_tokens=min_tokens,
                )
            )

        # --- Extra context (never cached) ------------------------------------
        if extra_context:
            blocks.append({"type": "text", "text": extra_context})

        # Enforce MAX_BREAKPOINTS. Anthropic's hard limit is 4 cache_control
        # markers TOTAL across system blocks AND messages. We reserve 1 slot
        # for the conversation-history block (see _build_messages) and only
        # allow up to (MAX_BREAKPOINTS - 1) markers on system blocks.
        blocks = self._cap_breakpoints(blocks, cap=self.MAX_BREAKPOINTS - 1)
        return blocks

    def _maybe_cached_block(
        self,
        *,
        text: str,
        ttl: str,
        min_tokens: int,
        force_cache: bool = False,
    ) -> dict[str, Any]:
        """Build a `{"type": "text", "text": ..., "cache_control": {...}}` block
        only if caching is enabled AND text is big enough to meet the minimum.
        """
        block: dict[str, Any] = {"type": "text", "text": text}
        if not self.caching_enabled:
            return block
        approx_tokens = len(text) / self.CHARS_PER_TOKEN_APPROX
        if not force_cache and approx_tokens < min_tokens:
            log.debug(
                "skip_cache_too_small",
                approx_tokens=int(approx_tokens),
                min_tokens=min_tokens,
            )
            return block
        cache_ctl: dict[str, Any] = {"type": "ephemeral"}
        if ttl == "1h":
            cache_ctl["ttl"] = "1h"   # extended TTL
        # (5m is Anthropic's default — no need to specify)
        block["cache_control"] = cache_ctl
        return block

    def _cap_breakpoints(
        self,
        blocks: list[dict[str, Any]],
        *,
        cap: int | None = None,
    ) -> list[dict[str, Any]]:
        """Anthropic allows ≤4 cache_control breakpoints per request.
        If we have more, drop the smallest ones (keep layer 0 always).
        """
        effective_cap = cap if cap is not None else self.MAX_BREAKPOINTS
        cached_indices = [
            i for i, b in enumerate(blocks) if "cache_control" in b
        ]
        if len(cached_indices) <= effective_cap:
            return blocks
        # Keep layer 0 + top-N by size
        keep = set(cached_indices[:1])  # layer 0
        sizes = sorted(
            cached_indices[1:],
            key=lambda i: len(blocks[i]["text"]),
            reverse=True,
        )
        keep.update(sizes[: effective_cap - 1])
        for i in cached_indices:
            if i not in keep:
                blocks[i].pop("cache_control", None)
        log.warning(
            "breakpoint_cap_applied",
            total_cached_blocks=len(cached_indices),
            kept=len(keep),
            cap=effective_cap,
        )
        return blocks

    def _build_messages(
        self,
        *,
        conversation_history: list[dict[str, str]] | None,
        user_turn: str,
        model: str,
    ) -> list[dict[str, Any]]:
        """Build messages list. History gets a 5m cache_control on its
        LAST message; current turn is not cached.
        """
        messages: list[dict[str, Any]] = []

        if conversation_history:
            # Anthropic expects list of {role, content}; content can be str or blocks
            for i, msg in enumerate(conversation_history):
                role = msg["role"]
                content = msg["content"]
                is_last = i == len(conversation_history) - 1
                if is_last and self.caching_enabled:
                    # Wrap the last history message as a block with 5m cache
                    approx_tokens = len(content) / self.CHARS_PER_TOKEN_APPROX
                    min_tokens = (
                        self.MIN_TOKENS_HAIKU
                        if "haiku" in model
                        else self.MIN_TOKENS_DEFAULT
                    )
                    if approx_tokens >= min_tokens:
                        messages.append({
                            "role": role,
                            "content": [{
                                "type": "text",
                                "text": content,
                                "cache_control": {"type": "ephemeral"},
                            }],
                        })
                        continue
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_turn})
        return messages

    # ========================================================================
    # Internal: API call w/ retry
    # ========================================================================

    @retry(
        retry=retry_if_exception_type((
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
            anthropic.InternalServerError,
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _call_with_retry(
        self,
        *,
        agent: str,
        model: str,
        max_tokens: int,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        thinking: bool,
    ) -> Any:
        t0 = time.perf_counter()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if thinking:
            # Extended thinking is supported on Claude Opus 4.x and
            # Sonnet 4.x; on older or non-matching models it yields a
            # 400. Skip with a warning rather than blindly enabling.
            if "opus-4" in model or "sonnet-4" in model:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2048}
            else:
                log.warning("thinking_skipped_unsupported_model", model=model)
        try:
            sdk_client = self._client_for_agent(agent)
            resp = sdk_client.messages.create(**kwargs)
        except anthropic.BadRequestError as e:
            log.error("bad_request", error=str(e), model=model)
            raise
        dt = time.perf_counter() - t0
        log.debug("api_latency_seconds", seconds=round(dt, 2), model=model)
        return resp

    # ========================================================================
    # Internal: helpers
    # ========================================================================

    def _load_prompt(self, agent: str) -> str:
        """Read and cache prompts/{agent}.txt.

        Cache is keyed on the file's mtime so edits made during the process
        lifetime (e.g. by a self-upgrade that rewrites a prompt without
        triggering a watchdog restart) are picked up on the next call.
        """
        path = self.root / "prompts" / f"{agent}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt not found: {path}. Known agents: commander/idea/"
                f"librarian/experimenter/reviewer/writer."
            )
        try:
            mt = path.stat().st_mtime
        except OSError:
            mt = 0.0
        cached = self._prompt_cache.get(agent)
        if isinstance(cached, dict) and cached.get("mt") == mt:
            return cached["text"]
        text = path.read_text(encoding="utf-8")
        self._prompt_cache[agent] = {"mt": mt, "text": text}
        return text

    def _skill_metadata_for(self, agent: str) -> str:
        """Progressive-disclosure: include only name+description of each skill
        the agent may load. The full SKILL.md body is not sent until Claude
        explicitly decides to use it.

        The cache is keyed on (agent, tuple of SKILL.md mtimes) so editing a
        skill or adding a new one invalidates the cached metadata string
        on the next call. This matters when self-upgrade writes skills —
        without mtime keying, the process would serve stale descriptions
        until restart.
        """
        skill_names = self.policy.agents.get("skills", {}).get(agent, [])
        if not skill_names:
            self._skill_meta_cache[agent] = ""
            return ""

        # Compute a signature over every SKILL.md the agent is allowed to
        # use. Missing files contribute 0 so adding a file later (mtime
        # non-zero) still invalidates the cache.
        sig_parts: list[tuple[str, float]] = []
        for name in skill_names:
            meta_path = self.root / "skills" / name / "SKILL.md"
            try:
                mt = meta_path.stat().st_mtime if meta_path.exists() else 0.0
            except OSError:
                mt = 0.0
            sig_parts.append((name, mt))
        sig = tuple(sig_parts)
        cache_key = (agent, sig)

        # `_skill_meta_cache` now stores dicts: {"sig": ..., "text": ...}
        cached = self._skill_meta_cache.get(agent)
        if isinstance(cached, dict) and cached.get("sig") == sig:
            return cached["text"]

        chunks: list[str] = ["## Available Skills (load on demand)"]
        for name in skill_names:
            meta_path = self.root / "skills" / name / "SKILL.md"
            if not meta_path.exists():
                log.warning("skill_missing", skill=name, agent=agent)
                continue
            frontmatter = _extract_frontmatter(meta_path.read_text(encoding="utf-8"))
            if frontmatter:
                chunks.append(f"### {name}\n{frontmatter}")
        result = "\n\n".join(chunks)
        self._skill_meta_cache[agent] = {"sig": sig, "text": result}
        return result

    def _estimate_tokens(
        self,
        system_blocks: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> int:
        """Rough estimator for pre-call budget check (no tokenizer dep)."""
        total_chars = 0
        for b in system_blocks:
            total_chars += len(b.get("text", ""))
        for m in messages:
            c = m.get("content", "")
            if isinstance(c, str):
                total_chars += len(c)
            elif isinstance(c, list):
                for block in c:
                    total_chars += len(block.get("text", ""))
        return int(total_chars / self.CHARS_PER_TOKEN_APPROX)

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int]:
        u = getattr(response, "usage", None)
        if u is None:
            return {"input_tokens": 0, "output_tokens": 0,
                    "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        return {
            "input_tokens":                getattr(u, "input_tokens", 0) or 0,
            "output_tokens":               getattr(u, "output_tokens", 0) or 0,
            "cache_read_input_tokens":     getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Concatenate all text blocks from assistant response."""
        parts: list[str] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)

    @staticmethod
    def _cache_stats(usage: dict[str, int]) -> dict[str, Any]:
        read = usage.get("cache_read_input_tokens", 0)
        fresh = usage.get("input_tokens", 0)
        total = read + fresh
        hit_ratio = (read / total) if total else 0.0
        return {
            "read_tokens": read,
            "write_tokens": usage.get("cache_creation_input_tokens", 0),
            "fresh_tokens": fresh,
            "hit_ratio": round(hit_ratio, 3),
        }


# -------------------------------- module helpers -----------------------------

def _extract_frontmatter(skill_md: str) -> str:
    """Return only the YAML frontmatter lines of a SKILL.md file."""
    if not skill_md.startswith("---"):
        return ""
    end = skill_md.find("---", 3)
    if end == -1:
        return ""
    return skill_md[3:end].strip()


def _render_tools_as_text(schemas: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for t in schemas:
        name = t.get("name", "<unknown>")
        desc = t.get("description", "")
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)
