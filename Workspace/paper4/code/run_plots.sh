#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="$(which python3)"

"$PYTHON_BIN" plot_complexity.py
"$PYTHON_BIN" plot_convergence.py
"$PYTHON_BIN" plot_line_density.py
"$PYTHON_BIN" plot_pdr_distance.py
"$PYTHON_BIN" plot_cbr_cdf.py
"$PYTHON_BIN" plot_results.py
echo "Done generating plots."
