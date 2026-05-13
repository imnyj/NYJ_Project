"""Centralized custom exceptions for paper-ai.

Keeping them in one place makes it easy for orchestrator / watchdog / tests
to reference and catch consistently, and prevents circular imports between
modules that raise them.
"""

from __future__ import annotations


# ============================================================================
# Agent permissions
# ============================================================================

class ToolPermissionDenied(Exception):
    """Raised when an agent tries to use a tool not in its allowed set.

    Enforced at `BaseAgent.think()` against the list declared in
    `config/agents.yaml:tools[<agent>]`.
    """

    def __init__(self, agent_role: str, forbidden: set[str], allowed: set[str]):
        self.agent_role = agent_role
        self.forbidden = forbidden
        self.allowed = allowed
        super().__init__(
            f"Agent '{agent_role}' cannot use tools {sorted(forbidden)}. "
            f"Allowed: {sorted(allowed) or '(none)'}."
        )


class UnknownAgentRole(Exception):
    """Raised when asking the factory for a role that isn't in the registry."""


class AgentModeError(Exception):
    """Merged agents (experimenter, reviewer) have internal modes. Raised when
    a caller asks for a mode-specific operation while agent is in wrong mode."""

    def __init__(self, agent_role: str, current_mode: str, required_mode: str):
        self.agent_role = agent_role
        self.current_mode = current_mode
        self.required_mode = required_mode
        super().__init__(
            f"Agent '{agent_role}' is in mode '{current_mode}', "
            f"but operation requires mode '{required_mode}'."
        )
