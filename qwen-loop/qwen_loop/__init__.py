"""qwen-loop: self-upgrading Qwen agent for paper-AI grunt work."""

from .agent import Agent
from .llm import QwenClient

__all__ = ["Agent", "QwenClient"]
__version__ = "0.1.0"
