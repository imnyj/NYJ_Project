#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="$(which python3)"

# Run training scripts
"$PYTHON_BIN" train_dqn.py
"$PYTHON_BIN" train_ddqn.py
"$PYTHON_BIN" train_dueling_dqn.py
"$PYTHON_BIN" train_moe.py
"$PYTHON_BIN" train_resnet.py
"$PYTHON_BIN" train_actor_critic.py
"$PYTHON_BIN" train_qlearning.py
"$PYTHON_BIN" train_sarsa.py

# Run simulations
"$PYTHON_BIN" sweep_density.py
