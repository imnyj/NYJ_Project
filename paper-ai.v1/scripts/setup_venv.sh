#!/usr/bin/env bash
# ============================================================================
# paper-ai WSL2 venv setup
# ============================================================================
# Usage: bash scripts/setup_venv.sh
#
# Installs the COMPLETE (Phase 1-5) system. For a minimal install, edit
# the `pip install -r requirements.txt` line below.
# ============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Upgrading pip / wheel / setuptools..."
pip install --upgrade pip wheel setuptools

echo "Installing requirements.txt (all phases)..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Copying .env.example → .env (edit to set ANTHROPIC_API_KEY)..."
    cp .env.example .env
fi

echo ""
echo "✅ paper-ai setup done."
echo ""
echo "Next steps:"
echo "  1. edit .env and set ANTHROPIC_API_KEY (and optionally CROSSREF_MAILTO)"
echo "  2. python cli.py --verify-config       # lints configs/prompts; no API calls"
echo "  3. pytest tests/ -v                    # full offline test suite"
echo "  4. python cli.py --demo                # tiny live API smoke"
echo "  5. python cli.py --interactive         # Commander REPL"
echo "  6. python cli.py --pipeline '<topic>'  # full 6-agent pipeline"
echo ""
echo "Production run (watchdog-supervised Commander):"
echo "  python -m monitoring.watchdog"
