"""Shared pytest fixtures.

These support the Phase 2+ offline test suite. Every fixture that touches
the filesystem uses tmp_path so we never pollute the real project tree.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

# Tests are structural — silence paper-ai's noisy INFO logs by default
logging.getLogger("paper-ai").setLevel(logging.WARNING)


# ================================================================= MockClient

class MockClient:
    """Stand-in for `tools.anthropic_client.AnthropicClient`.

    Records calls, returns a canned response, never hits the network.
    Responses include the minimum fields downstream code reads.
    """

    def __init__(self, policy=None, reply_text: str = "[mock reply]"):
        self.policy = policy
        self.reply_text = reply_text
        self.calls: list[dict[str, Any]] = []

    def call(self, **kwargs) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "text": self.reply_text,
            "stop_reason": "end_turn",
            "usage": {},
            "model": "mock-model",
            "cost_usd": 0.0,
            "cache_stats": {"hit_ratio": 0.0, "read_tokens": 0,
                            "write_tokens": 0, "fresh_tokens": 0},
            "raw": None,
        }

    def local_cache_stats(self) -> dict[str, Any]:
        return {"enabled": False, "hits": 0, "misses": 0}


@pytest.fixture
def mock_client():
    """Plain MockClient with no policy wiring — use for pure-logic tests."""
    return MockClient()


# ================================================================= policy

@pytest.fixture
def policy_runtime():
    """Load the real PolicyRuntime from the project's config/ directory.

    We reach up from tests/ to the project root. If a test moves configs
    into tmp_path, parametrize this fixture instead.
    """
    from core.policy_runtime import PolicyRuntime
    root = Path(__file__).resolve().parents[1]
    return PolicyRuntime(config_dir=root / "config")


@pytest.fixture
def mock_client_with_policy(policy_runtime):
    """MockClient with a real PolicyRuntime attached so permission checks
    (which read policy.agents['tools']) work correctly."""
    return MockClient(policy=policy_runtime)


# ================================================================= isolation

@pytest.fixture(autouse=True)
def isolate_paper_ai_root(tmp_path, monkeypatch):
    """Re-point `PAPER_AI_ROOT` at a tmp dir for the duration of each test.

    Ensures no test writes to the real `output/` tree.
    """
    monkeypatch.setenv("PAPER_AI_ROOT", str(tmp_path))
    # Reset cached paths so the new root takes effect
    try:
        from core.paths import reset_paths_for_tests
        reset_paths_for_tests()
    except ImportError:
        pass
    yield
    try:
        from core.paths import reset_paths_for_tests
        reset_paths_for_tests()
    except ImportError:
        pass
