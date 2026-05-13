"""Phase-1 smoke tests (no API calls).

These tests verify:
    - All configs parse
    - All 6 prompts load
    - All 6 skills have valid SKILL.md with YAML frontmatter
    - PolicyRuntime routes correctly
    - AnthropicClient assembles cache blocks correctly

Run with:
    pytest tests/test_phase1.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.policy_runtime import PolicyRuntime, BudgetExceeded, PRICING

ROOT = Path(__file__).parent.parent


# --------------------------------------------------------------- fixtures

@pytest.fixture
def policy() -> PolicyRuntime:
    return PolicyRuntime(config_dir=ROOT / "config")


# --------------------------------------------------------------- config tests

def test_all_agents_have_prompts():
    expected = {"commander", "idea", "librarian", "experimenter", "reviewer", "writer"}
    found = {p.stem for p in (ROOT / "prompts").glob("*.txt")}
    assert expected.issubset(found), f"missing: {expected - found}"


def test_all_skills_have_frontmatter():
    skill_dir = ROOT / "skills"
    for d in skill_dir.iterdir():
        if not d.is_dir():
            continue
        md = d / "SKILL.md"
        assert md.exists(), f"missing SKILL.md in {d.name}"
        text = md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{d.name}: missing YAML frontmatter"
        assert "\nname:" in text[:200], f"{d.name}: missing 'name' field"
        assert "\ndescription:" in text[:500], f"{d.name}: missing 'description'"


def test_routing_resolves_all_agents(policy):
    for agent in policy.agents["defaults"]:
        decision = policy.route(agent)
        assert decision["model"] in PRICING, \
            f"{agent} routed to unknown model: {decision['model']}"


def test_routing_by_task_type(policy):
    # classify → haiku
    assert "haiku" in policy.route("librarian", task_type="classify")["model"]
    # draft_section → sonnet
    assert "sonnet" in policy.route("writer", task_type="draft_section")["model"]
    # orchestrate → opus
    assert "opus" in policy.route("commander", task_type="orchestrate")["model"]


def test_unknown_task_falls_back(policy):
    r = policy.route("writer", task_type="does_not_exist")
    assert r["model"] in PRICING
    assert "agent_default" in r["reason"]


def test_budget_pre_check_blocks_oversized_input(policy):
    with pytest.raises(BudgetExceeded):
        policy.check_budget_before(
            "claude-sonnet-4-6",
            est_input=10_000_000,  # way over turn cap
            est_output=1000,
        )


def test_budget_pre_check_blocks_on_usd(policy):
    # Fake-spend most of the paper budget, then try a huge call
    policy.paper_usage.usd_spent = 49.50
    with pytest.raises(BudgetExceeded):
        policy.check_budget_before(
            "claude-opus-4-7",
            est_input=1_000_000,
            est_output=100_000,
        )


def test_record_call_updates_counters(policy):
    before = policy.paper_usage.usd_spent
    cost = policy.record_call(
        "claude-haiku-4-5-20251001",
        {"input_tokens": 1000, "output_tokens": 500,
         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
    )
    assert cost > 0
    assert policy.paper_usage.usd_spent > before
    assert policy.paper_usage.calls_by_model["claude-haiku-4-5-20251001"] == 1


def test_cache_hit_ratio_computation(policy):
    policy.record_call(
        "claude-sonnet-4-6",
        {"input_tokens": 100, "output_tokens": 50,
         "cache_read_input_tokens": 900, "cache_creation_input_tokens": 0},
    )
    # 900 cached / (100 fresh + 900 cached) = 0.9
    assert policy._cache_hit_ratio() == pytest.approx(0.9, abs=0.01)


# --------------------------------------------------------------- client tests

def test_client_builds_system_blocks_without_api():
    """We don't call the API — just check block assembly is sane."""
    from tools.anthropic_client import AnthropicClient

    policy = PolicyRuntime(config_dir=ROOT / "config")
    # No API key needed since we don't call API
    client = AnthropicClient(policy=policy, api_key="fake", project_root=ROOT)

    blocks = client._build_system_blocks(
        agent="librarian",
        tool_schemas=None,
        shared_artifacts=None,
        extra_context=None,
        model="claude-haiku-4-5-20251001",
    )
    # Layer 0 (system prompt) must exist
    assert len(blocks) >= 1
    assert blocks[0]["type"] == "text"
    # Layer 0 should be cached (role prompt is force_cache=True)
    assert "cache_control" in blocks[0]


def test_client_caps_breakpoints_at_4():
    from tools.anthropic_client import AnthropicClient

    policy = PolicyRuntime(config_dir=ROOT / "config")
    client = AnthropicClient(policy=policy, api_key="fake", project_root=ROOT)

    # Feed it 6 cached blocks; expect at most 4 with cache_control
    fake_blocks = [
        {"type": "text", "text": "x" * 10000, "cache_control": {"type": "ephemeral"}}
        for _ in range(6)
    ]
    capped = client._cap_breakpoints(fake_blocks)
    n_cached = sum(1 for b in capped if "cache_control" in b)
    assert n_cached <= 4
