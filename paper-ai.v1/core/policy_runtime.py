"""Policy runtime: model routing + budget enforcement + cache-friendly prompt assembly.

This is the "brain" that decides:
  1. Which Claude model handles a given task (Haiku vs Sonnet vs Opus).
  2. Whether the budget permits another call.
  3. How to assemble a request so it maximizes prompt-cache hits.

Research basis:
  - RouteLLM (arXiv:2406.18665) for routing heuristics.
  - Anthropic prompt-caching docs (2026) for breakpoint structure.
  - Finout.io cost benchmarks (Apr 2026) for target distribution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.logger import get_logger

log = get_logger("policy_runtime")

# Anthropic API pricing (USD per 1M tokens) as of 2026-04
# Source: https://www.anthropic.com/pricing + Finout.io Apr 2026
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":          {"in": 5.00, "out": 25.00,
                                 "cache_write_1h": 10.00, "cache_write_5m": 6.25,
                                 "cache_read": 0.50},
    "claude-sonnet-4-6":        {"in": 3.00, "out": 15.00,
                                 "cache_write_1h": 6.00,  "cache_write_5m": 3.75,
                                 "cache_read": 0.30},
    "claude-haiku-4-5-20251001":{"in": 1.00, "out": 5.00,
                                 "cache_write_1h": 2.00,  "cache_write_5m": 1.25,
                                 "cache_read": 0.10},
}


class BudgetExceeded(Exception):
    """Raised when a requested call would exceed paper/session/turn budget."""


@dataclass
class UsageSnapshot:
    """Cumulative usage counters.

    Two breakdowns are kept:
      * `calls_by_model` — used for distribution-drift checks
      * `tokens_by_agent` — used for the cost-savings report
        (how many tokens did Writer use? how many did Qwen save?)
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    usd_spent: float = 0.0
    calls_by_model: dict[str, int] = field(default_factory=dict)
    # Per-agent breakdown: agent -> {input, output, cache_read, cache_write,
    # cost_usd, calls}. Populated when record_call is given an agent kwarg.
    tokens_by_agent: dict[str, dict[str, float]] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def add_call(self, model: str, usage: dict[str, int],
                 agent: str | None = None) -> float:
        """Record a call; return its USD cost.

        When `agent` is given, also accumulate into tokens_by_agent so
        callers can answer "how much did Writer cost in this paper?".

        Pricing resolution:
          - Models with the `local:` prefix (Ollama-served local models)
            are free. Their tokens count toward distribution stats but
            cost zero.
          - Models in the PRICING table use their listed rates.
          - Anything else falls back to Opus pricing as a conservative
            estimate so budget tracking can't silently underestimate.
            PolicyRuntime.record_call emits a one-shot warning for
            this case (this dataclass stays logger-free).
        """
        if model.startswith("local:"):
            in_tok = usage.get("input_tokens", 0)
            out_tok = usage.get("output_tokens", 0)
            read_tok = usage.get("cache_read_input_tokens", 0)
            write_tok = usage.get("cache_creation_input_tokens", 0)
            cost = 0.0
            self.input_tokens += in_tok
            self.output_tokens += out_tok
            self.cache_read_tokens += read_tok
            self.cache_write_tokens += write_tok
            self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1
            self._add_to_agent(agent, in_tok, out_tok, read_tok, write_tok, cost)
            return cost

        if model not in PRICING:
            price = PRICING["claude-opus-4-7"]
        else:
            price = PRICING[model]
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        read_tok = usage.get("cache_read_input_tokens", 0)
        write_tok = usage.get("cache_creation_input_tokens", 0)

        cost = (
            in_tok   * price["in"]            / 1_000_000
            + out_tok  * price["out"]           / 1_000_000
            + read_tok * price["cache_read"]    / 1_000_000
            + write_tok * price["cache_write_1h"] / 1_000_000
        )
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.cache_read_tokens += read_tok
        self.cache_write_tokens += write_tok
        self.usd_spent += cost
        self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1
        self._add_to_agent(agent, in_tok, out_tok, read_tok, write_tok, cost)
        return cost

    def _add_to_agent(self, agent: str | None,
                      in_tok: int, out_tok: int,
                      read_tok: int, write_tok: int,
                      cost: float) -> None:
        """Update the per-agent bucket. No-op if agent is None."""
        if not agent:
            return
        slot = self.tokens_by_agent.setdefault(agent, {
            "input_tokens": 0, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "cost_usd": 0.0, "calls": 0,
        })
        slot["input_tokens"] += in_tok
        slot["output_tokens"] += out_tok
        slot["cache_read_tokens"] += read_tok
        slot["cache_write_tokens"] += write_tok
        slot["cost_usd"] += cost
        slot["calls"] += 1

    def distribution(self) -> dict[str, float]:
        total = sum(self.calls_by_model.values()) or 1
        return {m: c / total for m, c in self.calls_by_model.items()}


class PolicyRuntime:
    """Central router + budget guard."""

    def __init__(self, config_dir: Path | str = "config"):
        self.config_dir = Path(config_dir)
        self.routing = self._load_yaml("routing.yaml")
        self.agents = self._load_yaml("agents.yaml")
        self.budgets = self._load_yaml("budgets.yaml")
        self.caching = self._load_yaml("caching.yaml")
        # settings.yaml is optional — contains global project metadata +
        # per-subsystem knobs (e.g. response_cache.enabled).
        try:
            self.settings = self._load_yaml("settings.yaml")
        except FileNotFoundError:
            self.settings = {}

        self.paper_usage = UsageSnapshot()
        self.session_usage = UsageSnapshot()

        # Warning thresholds
        self._warned_paper_usd = False

    def _load_yaml(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ------------------------------------------------------------------ routing

    def resolve_model_alias(self, alias: str) -> str:
        """Translate 'sonnet' → 'claude-sonnet-4-6' etc."""
        models = self.agents["models"]
        return models.get(alias, alias)  # already-resolved IDs pass through

    def route(
        self,
        agent: str,
        task_type: str | None = None,
        *,
        force_model: str | None = None,
    ) -> dict[str, Any]:
        """Decide which model + params to use.

        Returns dict:
            { "model": "claude-sonnet-4-6",
              "max_tokens": 8192,
              "thinking": false,
              "reason": "task_type=draft_section → sonnet" }
        """
        if force_model:
            return {
                "model": self.resolve_model_alias(force_model),
                "max_tokens": self._cap_max_tokens(8192),
                "thinking": False,
                "reason": f"forced={force_model}",
            }

        # 1. Task-type explicit match
        if task_type and task_type in self.routing["task_types"]:
            spec = self.routing["task_types"][task_type]
            model = self.resolve_model_alias(spec["model"])
            thinking = bool(spec.get("thinking", False))
            # Anthropic's extended-thinking feature is Opus-only. If a config
            # typo pairs it with Haiku or Sonnet the API rejects the request;
            # silently disable here so a routing misconfig doesn't bring down
            # the pipeline.
            if thinking and "opus" not in model:
                log.warning("thinking_disabled_non_opus",
                            task_type=task_type, model=model)
                thinking = False
            return {
                "model": model,
                "max_tokens": self._cap_max_tokens(spec.get("max_tokens", 4096)),
                "thinking": thinking,
                "reason": f"task={task_type}",
            }

        # 2. Agent default
        alias = self.agents["defaults"].get(agent, "sonnet")
        model = self.resolve_model_alias(alias)
        return {
            "model": model,
            "max_tokens": self._cap_max_tokens(4096),
            "thinking": False,
            "reason": f"agent_default={agent}→{alias}",
        }

    def _cap_max_tokens(self, requested: int) -> int:
        """Clamp to per-agent-turn budget."""
        hard_cap = self.budgets["per_agent_turn"]["max_output_tokens"]
        return min(requested, hard_cap)

    # ----------------------------------------------------------------- budgets

    def check_budget_before(self, model: str, est_input: int, est_output: int) -> None:
        """Raise BudgetExceeded if this call would bust any ceiling.

        Local models (`local:` prefix) cost zero, so they only need the
        per-turn input-token guard checked — the USD-based caps are
        irrelevant.
        """
        if model.startswith("local:"):
            est_cost = 0.0
        else:
            if model not in PRICING:
                log.warning("unknown_model_using_opus_pricing", model=model)
                price = PRICING["claude-opus-4-7"]
            else:
                price = PRICING[model]
            est_cost = (est_input * price["in"] + est_output * price["out"]) / 1_000_000

        paper_cap_usd = self.budgets["per_paper"]["max_usd"]
        if self.paper_usage.usd_spent + est_cost > paper_cap_usd:
            raise BudgetExceeded(
                f"paper_usd {self.paper_usage.usd_spent:.2f}+{est_cost:.2f} "
                f"> cap {paper_cap_usd:.2f}"
            )

        session_cap_usd = self.budgets["per_session"]["max_usd"]
        if self.session_usage.usd_spent + est_cost > session_cap_usd:
            raise BudgetExceeded(
                f"session_usd {self.session_usage.usd_spent:.2f}+{est_cost:.2f} "
                f"> cap {session_cap_usd:.2f}"
            )

        turn_cap_in = self.budgets["per_agent_turn"]["max_input_tokens"]
        if est_input > turn_cap_in:
            raise BudgetExceeded(
                f"turn_input {est_input} > cap {turn_cap_in}"
            )

    def record_call(self, model: str, usage: dict[str, int],
                    agent: str | None = None) -> float:
        """Update both paper & session counters; emit warnings.

        `local:*` models are not in PRICING by design — they're free —
        and so suppress the unknown-model warning for those.

        `agent` (optional) tags this call so per-agent breakdowns can
        be reported later. Callers from LiteLLM bridge or
        AnthropicClient pass the agent name; legacy callers may omit it.
        """
        if model not in PRICING and not model.startswith("local:"):
            log.warning("unknown_model_using_opus_pricing", model=model)
        cost = self.paper_usage.add_call(model, usage, agent=agent)
        _ = self.session_usage.add_call(model, usage, agent=agent)

        warn_usd = self.budgets["warn_at"]["usd_per_paper"]
        if (not self._warned_paper_usd) and self.paper_usage.usd_spent > warn_usd:
            log.warning(
                "budget_warning",
                paper_usd=round(self.paper_usage.usd_spent, 2),
                warn_at=warn_usd,
            )
            self._warned_paper_usd = True

        log.info(
            "call_recorded",
            agent=agent or "?",
            model=model,
            cost_usd=round(cost, 5),
            paper_usd=round(self.paper_usage.usd_spent, 4),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read=usage.get("cache_read_input_tokens", 0),
            cache_write=usage.get("cache_creation_input_tokens", 0),
        )
        self._check_distribution_drift()
        return cost

    def _check_distribution_drift(self) -> None:
        """Log a warning if actual Haiku/Sonnet/Opus mix drifts from target."""
        if sum(self.paper_usage.calls_by_model.values()) < 10:
            return  # not enough data
        targets = self.routing.get("target_distribution", {})
        tol = self.routing.get("tolerance", 0.15)
        actual = self.paper_usage.distribution()

        alias_to_id = self.agents["models"]
        for alias, target_pct in targets.items():
            full_id = alias_to_id[alias]
            got = actual.get(full_id, 0.0)
            if abs(got - target_pct) > tol:
                log.warning(
                    "distribution_drift",
                    model=alias,
                    actual=round(got, 3),
                    target=target_pct,
                    tolerance=tol,
                )

    # ---------------------------------------------------------------- reset

    def start_new_session(self) -> None:
        """Reset per-session counters (keep paper counters)."""
        self.session_usage = UsageSnapshot()
        log.info("session_started")

    def start_new_paper(self) -> None:
        """Reset all counters."""
        self.paper_usage = UsageSnapshot()
        self.session_usage = UsageSnapshot()
        self._warned_paper_usd = False
        log.info("paper_started")

    # --------------------------------------------------------------- reporting

    def report(self) -> dict[str, Any]:
        return {
            "paper": {
                "input_tokens": self.paper_usage.input_tokens,
                "output_tokens": self.paper_usage.output_tokens,
                "cache_read_tokens": self.paper_usage.cache_read_tokens,
                "cache_write_tokens": self.paper_usage.cache_write_tokens,
                "usd_spent": round(self.paper_usage.usd_spent, 4),
                "distribution": self.paper_usage.distribution(),
            },
            "session": {
                "input_tokens": self.session_usage.input_tokens,
                "usd_spent": round(self.session_usage.usd_spent, 4),
            },
            "cache_hit_ratio": self._cache_hit_ratio(),
        }

    def _cache_hit_ratio(self) -> float:
        """Fraction of input tokens served from cache.

        Denominator includes fresh input tokens PLUS cache-write tokens
        (the first call that populated the cache — those bytes were billed
        as fresh) PLUS cache-read tokens. Only cache_read is a "hit".
        Excluding cache_write would overstate the hit rate in early calls.
        """
        fresh = self.paper_usage.input_tokens
        write = self.paper_usage.cache_write_tokens
        read = self.paper_usage.cache_read_tokens
        total = fresh + write + read
        if total == 0:
            return 0.0
        return read / total
