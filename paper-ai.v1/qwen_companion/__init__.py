"""qwen_companion — the paper-ai-external REPL and Qwen self-tune loop.

Entry points:
    python -m qwen_companion                  → open a REPL
    python -m qwen_companion self-tune        → run one self-tune cycle
    python -m qwen_companion verify-config    → sanity-check the profile

Philosophy:
    The companion is where Qwen's self-upgrade lives. The paper-ai
    pipeline only *reads* the Qwen profile; it never mutates it.
    Anything that changes prompts, routing overrides, or runtime
    config for Qwen has to go through the self-tune flow here,
    which goes through the Blue-Green profile manager.
"""

__all__: list[str] = []
