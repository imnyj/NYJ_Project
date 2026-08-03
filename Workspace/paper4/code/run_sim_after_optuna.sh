#!/bin/bash
while pgrep -f "python3 optuna_optimize.py" > /dev/null; do
    sleep 5
done
python3 sensitivity_runner.py --sweep all
