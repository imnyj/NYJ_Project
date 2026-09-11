#!/usr/bin/env bash
# Supervised, unattended launcher for the HPO re-search, split across GPUs.
#
# WHY SPLIT. Each model's Optuna study is independent of the others, so the nine
# of them are embarrassingly parallel. Measured after the on-policy fix, one
# 4,000-step rollout costs about 315 s, and 9 models x 15 trials x 3 seeds is 405
# rollouts -- 35.5 hours if run one after another on a single device. The box has
# four GPUs, so splitting the models across them turns that into roughly a
# quarter of the wall clock without changing a single number that comes out.
#
# WHY EACH GROUP GETS ITS OWN OUTPUT DIRECTORY. `run_all_baselines_hpo` writes
# `optuna_best_params.csv` once, at the end, containing the models IT ran. Four
# processes pointed at one directory would each overwrite that file with their
# own partial view, and the last writer would win. Groups therefore write to
# `results/hpo_parallel/<group>/` and are merged afterwards by
# `etc/merge_hpo_results.py`.
#
# Usage:
#   etc/run_hpo_parallel.sh              # launch all four groups, detached
#   etc/run_hpo_parallel.sh --dry-run    # print what would run
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
PY="/home/imnyj/venv/bin/python"
cd "$CODER_DIR" || exit 1

OUT_ROOT="${CODER_DIR}/results/hpo_parallel"
LOG_ROOT="/home/imnyj/Workspace/paper4/logs/hpo_parallel"
N_TRIALS=15
SEEDS="1001 1002 1003"

# Groups are balanced by measured rollout cost, not by model count. The two
# on-policy models are the expensive ones (350 s and 280 s per rollout against
# roughly 200 s for the rest), so they are placed on separate devices rather
# than stacked together where they would set the critical path.
GROUP_NAMES=(g0 g1 g2 g3)
GROUP_GPUS=(0 1 2 3)
GROUP_MODELS=(
    "PPO MADDPG-MT"
    "I-HAMAPPO SAC"
    "TD3 RES-MAPDDPG MA2HDQN"
    "SPAM-D3QN CARLTON"
)

if [[ "${1:-}" == "--dry-run" ]]; then
    for i in "${!GROUP_NAMES[@]}"; do
        echo "GPU ${GROUP_GPUS[$i]}  ${GROUP_NAMES[$i]}: ${GROUP_MODELS[$i]}"
    done
    exit 0
fi

mkdir -p "$LOG_ROOT"

for i in "${!GROUP_NAMES[@]}"; do
    name="${GROUP_NAMES[$i]}"
    gpu="${GROUP_GPUS[$i]}"
    models="${GROUP_MODELS[$i]}"
    out="${OUT_ROOT}/${name}"
    log="${LOG_ROOT}/${name}.log"
    mkdir -p "$out"

    # Each group needs its own SUMO scenario directory. Without it every process
    # regenerates one shared generated.net.xml and the others silently read a
    # network they did not ask for -- no error, wrong numbers.
    setsid nohup env \
        CUDA_VISIBLE_DEVICES="$gpu" \
        PAPER4_SUMO_DIR="${out}/sumo" \
        PYTHONPATH="$CODER_DIR" \
        "$PY" -m src.hpo \
            --n-trials "$N_TRIALS" \
            --seeds $SEEDS \
            --models $models \
            --output-dir "$out" \
        > "$log" 2>&1 < /dev/null &

    echo "[$(date '+%F %T')] ${name} on GPU ${gpu}: ${models} -> ${log}"
    # Stagger so four processes do not generate their scenarios in the same
    # instant and contend on the generation lock.
    sleep 5
done

echo "launched ${#GROUP_NAMES[@]} groups; merge with etc/merge_hpo_results.py when all are done"
