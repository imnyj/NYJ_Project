# config.py
"""Configuration for the smolagents-based paper-ai system.

Two distinct roots
------------------
This project separates two filesystem concerns:

  * PAPER_AI_ROOT  — the code base + infrastructure files.
                     vault (.env, .env.salt), logs, sessions, qwen
                     profiles, skills, tests live here.
                     Resolved by `core.paths.get_paths()`.

  * PAPER_BASE_DIR — the paper output / working directory.
                     `.pipeline/`, `paper/`, `figure/`, `graph/`,
                     `photo/` live here.
                     What `agents/*.py` write into.

Why two roots
-------------
The infrastructure (logs, vault, sessions) outlives any single paper
project. A user can start a new paper by pointing PAPER_BASE_DIR
elsewhere without touching the vault or losing past session
histories. Likewise, code upgrades (Blue-Green) only touch
PAPER_AI_ROOT, leaving the user's paper artefacts untouched.

API key resolution
------------------
`get_api_key(role)` reads from the encrypted vault first
(`core.secret_env`), falling back to plain `os.environ`. Six
canonical roles map to legacy names through `_KEY_ALIASES` so the
old smolagents agent files keep working without edits:

    coder, experiment, visualization → EXPERIMENTER key
    validator, proofreader            → REVIEWER key
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


# ============================================================================ roots

# PAPER_AI_ROOT: where the code lives. Default: this file's directory.
# Override via env var if your code lives elsewhere (uncommon).
_THIS_FILE = Path(__file__).resolve()
PAPER_AI_ROOT = Path(
    os.getenv("PAPER_AI_ROOT", str(_THIS_FILE.parent))
).resolve()

# PAPER_BASE_DIR: where paper artefacts go. Original system used
# /home/nyj/0_paper. We default to PAPER_AI_ROOT/workspace so a fresh
# install is self-contained, but the user can point this anywhere.
BASE_DIR = Path(
    os.getenv("PAPER_BASE_DIR", str(PAPER_AI_ROOT / "workspace"))
).resolve()


# ============================================================================ paths

# Paper-output paths. All under BASE_DIR. The keys here MUST match
# what `interface.py::COMMON_INTERFACE` references — agents read
# these via path strings.
PATHS: dict[str, Path] = {
    # .pipeline (영구 상태 관리)
    "brain":          BASE_DIR / ".pipeline" / "brain",
    "context_state":  BASE_DIR / ".pipeline" / "context_state",
    "code_tracker":   BASE_DIR / ".pipeline" / "code_tracker",
    "annotations":    BASE_DIR / ".pipeline" / "annotations",
    "implicit":       BASE_DIR / ".pipeline" / "implicit",
    # 논문 산출물
    "references":     BASE_DIR / "paper" / "references",
    "idea":           BASE_DIR / "paper" / "idea",
    "experiment":     BASE_DIR / "paper" / "experiment",
    "data":           BASE_DIR / "paper" / "data",
    "validation":     BASE_DIR / "paper" / "validation",
    "figure":         BASE_DIR / "figure",
    "graph":          BASE_DIR / "graph",
    "photo":          BASE_DIR / "photo",
    "draft":          BASE_DIR / "paper" / "draft",
    "final":          BASE_DIR / "paper" / "final",
}


# ============================================================================ runtime knobs

# How many ReAct steps a CodeAgent gets per `run()` call. The
# original system used 25; raising it lets agents do more autonomous
# work but also bounds runaway loops.
MAX_STEPS: int = int(os.getenv("MAX_STEPS", "25"))

# How many times Validator FAIL → Coder rework cycle can repeat
# before Commander gives up.
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "10"))

VERBOSITY: int = int(os.getenv("VERBOSITY", "1"))


# ============================================================================ canonical agents (6)

# After consolidating the original 8 agents into 6 (Experimenter
# absorbs Experiment+Coder+Visualization, Reviewer absorbs
# Validator+Proofreader). Commander stays as the orchestrator.
AGENTS: list[str] = [
    "commander",
    "librarian",
    "idea",
    "experimenter",
    "reviewer",
    "writer",
]


# ============================================================================ key resolution

# Six canonical keys + legacy aliases. Order matters: the first hit
# wins, so put the canonical name first. This mirrors the alias table
# in tools.anthropic_client._AGENT_KEY_ALIASES — duplicating here so
# this module loads without anthropic.
_KEY_ALIASES: dict[str, list[str]] = {
    "commander":    ["COMMANDER"],
    "idea":         ["IDEA"],
    "librarian":    ["LIBRARIAN"],
    "experimenter": ["EXPERIMENTER", "EXPERIMENT", "CODER", "VISUALIZATION"],
    "reviewer":     ["REVIEWER", "VALIDATOR", "PROOFREADER"],
    "writer":       ["WRITER"],
    # Legacy direct names for any code that still imports
    # `get_api_key("coder")` etc. They share the consolidated key.
    "coder":         ["EXPERIMENTER", "CODER", "EXPERIMENT", "VISUALIZATION"],
    "experiment":    ["EXPERIMENTER", "EXPERIMENT", "CODER"],
    "visualization": ["EXPERIMENTER", "VISUALIZATION", "CODER"],
    "validator":     ["REVIEWER", "VALIDATOR", "PROOFREADER"],
    "proofreader":   ["REVIEWER", "PROOFREADER", "VALIDATOR"],
}


def get_api_key(role: str) -> str:
    """Return the Anthropic API key for `role`.

    Resolution order:
      1. core.secret_env  (decrypted vault)
      2. os.environ       (plain text fallback)

    Aliases are honoured. Raises KeyError with a friendly message
    listing accepted env-var names — the SDK would otherwise emit an
    opaque 401.

    Side effect
    -----------
    Registers the resolved key with `core.litellm_bridge` so the
    LiteLLM callback can attribute calls back to this role. The
    registry stores only a 12-char prefix — the actual key is not
    retained beyond this function call.
    """
    role_l = role.lower().strip()
    aliases = _KEY_ALIASES.get(role_l, [role.upper()])

    resolved: str | None = None
    # 1. Vault
    try:
        from core import secret_env
        for suffix in aliases:
            v = secret_env.get(f"ANTHROPIC_API_KEY_{suffix}")
            if v:
                resolved = v
                break
    except Exception:
        pass

    # 2. Plain environment
    if resolved is None:
        for suffix in aliases:
            v = os.environ.get(f"ANTHROPIC_API_KEY_{suffix}")
            if v:
                resolved = v
                break

    if resolved is None:
        raise KeyError(
            f"No API key configured for role {role!r}. Set one of: "
            + ", ".join(f"ANTHROPIC_API_KEY_{a}" for a in aliases)
            + " in .env. Encrypt with `python encrypt_key.py --key-name "
            f"ANTHROPIC_API_KEY_{aliases[0]}`."
        )

    # Best-effort registration with the cost-tracking bridge. If
    # bridge isn't installed yet (e.g. during early bootstrap), we
    # silently skip — the bridge installer reads keys back via the
    # registry on demand.
    canonical = _ROLE_TO_CANONICAL.get(role_l, role_l)
    try:
        from core.litellm_bridge import register_agent_key
        register_agent_key(canonical, resolved)
    except Exception:
        pass

    return resolved


# ============================================================================ model resolution

# `agents.yaml` is the single source of truth for which model each
# role uses. Cached after first read; agents.yaml hot-edits don't
# take effect mid-run.
_agents_yaml_cache: dict[str, Any] | None = None


def _load_agents_yaml() -> dict[str, Any]:
    global _agents_yaml_cache
    if _agents_yaml_cache is not None:
        return _agents_yaml_cache
    path = PAPER_AI_ROOT / "config" / "agents.yaml"
    if not path.is_file():
        _agents_yaml_cache = {}
        return _agents_yaml_cache
    try:
        _agents_yaml_cache = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        _agents_yaml_cache = {}
    return _agents_yaml_cache


# Legacy role → canonical role for model lookup.
_ROLE_TO_CANONICAL: dict[str, str] = {
    "commander":     "commander",
    "idea":          "idea",
    "librarian":     "librarian",
    "experimenter":  "experimenter",
    "reviewer":      "reviewer",
    "writer":        "writer",
    # Legacy 8-agent role names
    "coder":         "experimenter",
    "experiment":    "experimenter",
    "visualization": "experimenter",
    "validator":     "reviewer",
    "proofreader":   "reviewer",
}


def get_model_id(
    agent_name: str,
    default: str = "claude-sonnet-4-6",
) -> str:
    """Return the concrete Anthropic model id for `agent_name`.

    Resolution:
      1. MODEL_<AGENT> env var (highest priority — emergency override)
      2. config/agents.yaml::defaults.<canonical_role> → alias
         → models.<alias> → concrete id
      3. `default` (sonnet 4.6 — safest middle ground)
    """
    # Emergency env override
    env_override = os.getenv(f"MODEL_{agent_name.upper()}")
    if env_override:
        return env_override

    cfg = _load_agents_yaml()
    canonical = _ROLE_TO_CANONICAL.get(
        agent_name.lower().strip(),
        agent_name.lower().strip(),
    )
    defaults = cfg.get("defaults") or {}
    alias = defaults.get(canonical)
    if alias:
        models = cfg.get("models") or {}
        model_id = models.get(alias)
        if model_id:
            return model_id
    return default


# ============================================================================ initialisation

def init_directories() -> None:
    """Create all output directories and seed the .pipeline/ state files.

    Idempotent — safe to call on every Commander startup.
    """
    for path in PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    _init_pipeline_state()
    _init_brain()
    _init_annotations()
    _init_implicit()
    _init_code_tracker()


def _init_pipeline_state() -> None:
    state_file = PATHS["context_state"] / "pipeline_state.json"
    if not state_file.exists():
        # Six-phase pipeline matching the consolidated agent list.
        state = {
            "topic": "",
            "phases": {
                "librarian":     {"status": "pending", "updated": "", "note": ""},
                "idea":          {"status": "pending", "updated": "", "note": ""},
                "experimenter": {
                    "status": "pending", "updated": "", "note": "",
                    "stages_done": [],     # ["design", "implement", "visualize"]
                    "retry_count": 0,
                },
                "reviewer": {
                    "status": "pending", "updated": "", "note": "",
                    "modes_done": [],      # ["validator", "proofreader"]
                },
                "writer": {
                    "status": "pending", "updated": "", "note": "",
                    "sections_done": [],
                },
            },
            "outputs": [],
        }
        state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    decision_log = PATHS["context_state"] / "decision_log.md"
    if not decision_log.exists():
        decision_log.write_text("# Decision Log\n\n", encoding="utf-8")

    session_hist = PATHS["context_state"] / "session_history.md"
    if not session_hist.exists():
        session_hist.write_text("# Session History\n\n", encoding="utf-8")


def _init_brain() -> None:
    for agent in AGENTS:
        brain_file = PATHS["brain"] / f"{agent}_memory.md"
        if not brain_file.exists():
            brain_file.write_text(
                f"# {agent.capitalize()} Memory\n\n"
                f"(첫 작업 수행 시 자동으로 채워집니다)\n",
                encoding="utf-8",
            )


def _init_annotations() -> None:
    for name in [
        "validation_history.md",
        "user_directives.md",
        "agent_notes.md",
    ]:
        f = PATHS["annotations"] / name
        if not f.exists():
            title = name.replace(".md", "").replace("_", " ").title()
            f.write_text(f"# {title}\n\n", encoding="utf-8")


def _init_implicit() -> None:
    for name in [
        "error_patterns.md",
        "user_preferences.md",
        "style_evolution.md",
    ]:
        f = PATHS["implicit"] / name
        if not f.exists():
            title = name.replace(".md", "").replace("_", " ").title()
            f.write_text(f"# {title}\n\n", encoding="utf-8")


def _init_code_tracker() -> None:
    changelog = PATHS["code_tracker"] / "changelog.md"
    if not changelog.exists():
        changelog.write_text("# Code Changelog\n\n", encoding="utf-8")
    version_map = PATHS["code_tracker"] / "version_map.json"
    if not version_map.exists():
        version_map.write_text("{}", encoding="utf-8")
