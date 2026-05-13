"""paper-ai CLI — auxiliary commands.

This module is for INFRASTRUCTURE checks. The actual paper pipeline
runs through `python commander.py` (with optional Command.md), which
is the smolagents Commander entry point.

Available commands:

    python cli.py --verify-config    # validate YAMLs + prompts; no API calls
    python cli.py --smoke-test       # ping every agent once via LiteLLM
    python cli.py --smoke-test --thorough   # uses real per-agent models
    python cli.py --smoke-test --no-qwen    # skip Qwen probe

Why split from commander.py?
----------------------------
commander.py imports every agent module at startup, which means it
calls get_api_key six times — needing the vault unlocked. The
verify-config and smoke-test commands need to work without that
overhead and provide actionable error messages BEFORE the user runs
the real pipeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper-ai-cli",
        description=(
            "Auxiliary commands for paper-ai. Run the actual pipeline "
            "with `python commander.py` instead."
        ),
    )
    p.add_argument(
        "--verify-config", action="store_true",
        help="Validate YAMLs + prompts + skills; no API calls.",
    )
    p.add_argument(
        "--smoke-test", action="store_true",
        help=(
            "Ping every agent once with a cheap LiteLLM call + ping "
            "Qwen via Ollama. Verifies all keys and the local model "
            "are working before running commander.py for real."
        ),
    )
    p.add_argument(
        "--usage", action="store_true",
        help=(
            "Print cumulative token usage and cost report (lifetime "
            "totals + per-agent breakdown + Qwen savings estimate)."
        ),
    )
    p.add_argument(
        "--no-qwen", action="store_true",
        help="Used with --smoke-test: skip the Qwen probe.",
    )
    p.add_argument(
        "--thorough", action="store_true",
        help=(
            "Used with --smoke-test: send each agent its real model "
            "instead of routing every ping to Haiku. Costs a few cents."
        ),
    )
    p.add_argument(
        "--root", type=Path, default=None,
        help="PAPER_AI_ROOT override (default: directory of cli.py).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Resolve project root early — every subcommand needs it.
    if args.root is not None:
        root = args.root.resolve()
    else:
        root = Path(__file__).parent.resolve()

    # Mode dispatch — exactly one of the modes must be set.
    if args.verify_config:
        from cli_commands import config_verify
        return config_verify.run(root)

    if args.smoke_test:
        from cli_commands import smoke_test
        return smoke_test.run(
            root,
            skip_qwen=args.no_qwen,
            thorough=args.thorough,
        )

    if args.usage:
        from cli_commands import usage_report
        return usage_report.run(root)

    _build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
