"""--verify-config subcommand.

API-call-free validation of the smolagents-based system. Confirms:

  * agents.yaml parses + has all six roles + each maps to a known model.
  * config.py imports cleanly (no syntax / yaml errors).
  * Each agent module imports cleanly (which transitively requires
    that get_api_key works for that role, so this also exercises the
    vault).
  * interface.py + style_guide.py importable.
  * tools/ exports the smolagents-compatible tool classes.

This is the FIRST thing to run after editing agents.yaml or .env.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


SIX_AGENTS = ("commander", "librarian", "idea", "experimenter", "reviewer", "writer")


def run(root: Path) -> int:
    """Return 0 if OK, 1 if any check fails."""
    failures: list[str] = []

    # ---- 1. agents.yaml ----
    yml = _check_agents_yaml(root, failures)
    if yml is not None:
        print(f"✅ agents.yaml parsed")
        print(f"   models:   {yml.get('models')}")
        print(f"   defaults: {yml.get('defaults')}")

    # ---- 2. config.py ----
    if _check_config_module(failures):
        print("✅ config.py imports cleanly")

    # ---- 3. interface + style_guide ----
    if _check_interface(failures):
        print("✅ interface.py + style_guide.py imports cleanly")

    # ---- 4. tools package ----
    if _check_tools(failures):
        print("✅ tools/ exports smolagents tools")

    # ---- 5. each agent module imports cleanly ----
    # We do this LAST because it's the heaviest check (each one calls
    # get_api_key + instantiates LiteLLMModel).
    if _check_agents(failures):
        print(f"✅ all {len(SIX_AGENTS)} agent modules importable")

    if failures:
        print("\n❌ verify-config found problems:")
        for f in failures:
            print(f"   • {f}")
        return 1

    print("\nAll checks passed. You can run:")
    print("   python cli.py --smoke-test       # cheap key/model ping")
    print("   python commander.py              # interactive Commander")
    print("   python commander.py Command.md   # one-shot run")
    return 0


# ============================================================================ checks


def _check_agents_yaml(root: Path, failures: list[str]) -> dict[str, Any] | None:
    import yaml
    p = root / "config" / "agents.yaml"
    if not p.is_file():
        failures.append(f"missing config/agents.yaml")
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        failures.append(f"agents.yaml malformed: {e}")
        return None

    models = data.get("models") or {}
    defaults = data.get("defaults") or {}

    for role in SIX_AGENTS:
        if role not in defaults:
            failures.append(f"agents.yaml::defaults missing role {role!r}")
            continue
        alias = defaults[role]
        if alias not in models:
            failures.append(
                f"agents.yaml::defaults.{role} = {alias!r} but "
                f"models.{alias} not defined"
            )
    return data


def _check_config_module(failures: list[str]) -> bool:
    try:
        import config  # noqa
    except Exception as e:
        failures.append(f"config.py import failed: {e}")
        return False
    return True


def _check_interface(failures: list[str]) -> bool:
    try:
        import interface  # noqa
        import style_guide  # noqa
    except Exception as e:
        failures.append(f"interface/style_guide import failed: {e}")
        return False
    if not getattr(interface, "COMMON_INTERFACE", None):
        failures.append("interface.py: COMMON_INTERFACE not defined")
        return False
    return True


def _check_tools(failures: list[str]) -> bool:
    try:
        from tools import (  # noqa
            ArxivSearchTool, SemanticScholarSearchTool,
            FileReadTool, FileWriteTool, DirectoryListTool,
        )
    except Exception as e:
        failures.append(f"tools package: {e}")
        return False
    return True


def _check_agents(failures: list[str]) -> bool:
    """Try importing each agent module. This forces get_api_key
    resolution and LiteLLMModel construction, which catches:
      - missing keys in .env
      - typos in model id
      - litellm not installed
    """
    ok = True
    for role in SIX_AGENTS:
        if role == "commander":
            module_name = "commander"
        else:
            module_name = f"agents.{role}"
        try:
            __import__(module_name)
        except Exception as e:
            failures.append(
                f"agent {role!r} ({module_name}) import failed: "
                f"{type(e).__name__}: {e}"
            )
            ok = False
    return ok
