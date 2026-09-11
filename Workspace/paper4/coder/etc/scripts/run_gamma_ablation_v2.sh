#!/usr/bin/env bash
# Widened discount sweep: three gammas x three seeds x two on-policy models,
# sharded across the four GPUs.
#
# WHY IT EXISTS. `etc/scripts/check_gamma_ablation.py` measured two gammas at one
# seed on 2026-09-04. Two points cannot separate a monotone trend from an
# interior optimum, and one seed cannot say whether the gap between the arms is
# larger than the gap between seeds. The HPO gamma upper bound is going to be set
# from this measurement, so both gaps have to be visible.
#
# WHY EACH SHARD GETS ITS OWN SUMO DIRECTORY. `src/sumo/make_sumo_set.py` reads
# PAPER4_SUMO_DIR into BASE_PATH at import time; unset, every process on the box
# shares one `generated.net.xml`. Generation is lock-serialised, so there is no
# torn write and no error -- process A simply starts libsumo on the network
# process B regenerated, and reports metrics for a scenario it never asked for.
# That happened on 2026-09-01. One directory per shard is what prevents it.
#
# WHY THE SHARDS ARE (model, seed). A shard owns one model and one seed and
# walks the three arms, so no two shards ever write the same row and a shard that
# dies costs three conditions rather than the sweep. Measured cost is about 360 s
# per PPO rollout and 280 s per I-HAMAPPO rollout, i.e. roughly 18 and 14 minutes
# per shard against 96 minutes for the whole sweep run serially.
#
# Usage:
#   etc/scripts/run_gamma_ablation_v2.sh              # launch and wait
#   etc/scripts/run_gamma_ablation_v2.sh --dry-run    # print the plan, touch nothing
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
PY="/home/imnyj/venv/bin/python"
cd "$CODER_DIR" || exit 1

DATE_TAG="20260905"
SHARD_ROOT="${CODER_DIR}/results/gamma_ablation_v2_shards"
LOG_ROOT="/home/imnyj/Workspace/paper4/logs/gamma_ablation_v2"
MERGED="${CODER_DIR}/results/hpo/gamma_ablation_v2_${DATE_TAG}.csv"
SUMMARY="${CODER_DIR}/results/hpo/gamma_ablation_v2_summary_${DATE_TAG}.csv"
ARMS="selected gamma097 gamma099"
N_STEPS=4000
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

# Shard i = one model at one seed, over all three arms.
SHARD_NAMES=(ppo_s1001 ppo_s1002 ppo_s1003 iham_s1001 iham_s1002 iham_s1003)
SHARD_MODELS=(PPO PPO PPO I-HAMAPPO I-HAMAPPO I-HAMAPPO)
SHARD_SEEDS=(1001 1002 1003 1001 1002 1003)
# PPO is stable-baselines3 with device="auto", so it lands on whatever CUDA
# device it can see; I-HAMAPPO builds its modules on the CPU and never moves
# them, so its GPU assignment only matters if that ever changes.
SHARD_GPUS=(0 1 2 3 0 1)

# Six processes on twenty cores. Left at the torch default each would claim all
# twenty and they would spend their time fighting over them; three apiece leaves
# two cores for SUMO's own work and the shell. Set identically for every shard so
# no arm is measured under a different reduction order from another.
export OMP_NUM_THREADS=3
export MKL_NUM_THREADS=3

if [[ $DRY_RUN -eq 1 ]]; then
    echo "arms:      ${ARMS}"
    echo "n_steps:   ${N_STEPS}"
    echo "merged:    ${MERGED}"
    echo "summary:   ${SUMMARY}"
    for i in "${!SHARD_NAMES[@]}"; do
        echo "GPU ${SHARD_GPUS[$i]}  ${SHARD_NAMES[$i]}: ${SHARD_MODELS[$i]} seed ${SHARD_SEEDS[$i]}"
        echo "        out  ${SHARD_ROOT}/${SHARD_NAMES[$i]}.csv"
        echo "        sumo ${SHARD_ROOT}/${SHARD_NAMES[$i]}/sumo"
        echo "        log  ${LOG_ROOT}/${SHARD_NAMES[$i]}.log"
    done
    exit 0
fi

# Overwrite guard. The 2026-09-04 single-seed file is the control this run is
# read against, and a half-finished shard set is worse than none, so anything
# already sitting in the destinations stops the launch here.
guard_hits=()
[[ -f "$MERGED" ]] && guard_hits+=("$MERGED")
[[ -f "$SUMMARY" ]] && guard_hits+=("$SUMMARY")
for name in "${SHARD_NAMES[@]}"; do
    [[ -f "${SHARD_ROOT}/${name}.csv" ]] && guard_hits+=("${SHARD_ROOT}/${name}.csv")
done
if [[ ${#guard_hits[@]} -gt 0 ]]; then
    echo "REFUSING TO LAUNCH: these outputs already exist." >&2
    printf '    %s\n' "${guard_hits[@]}" >&2
    echo "Move them aside (coder/backup/) before running again." >&2
    exit 3
fi

mkdir -p "$SHARD_ROOT" "$LOG_ROOT"

pids=()
for i in "${!SHARD_NAMES[@]}"; do
    name="${SHARD_NAMES[$i]}"
    sumo="${SHARD_ROOT}/${name}/sumo"
    out="${SHARD_ROOT}/${name}.csv"
    log="${LOG_ROOT}/${name}.log"
    mkdir -p "$sumo"

    env CUDA_VISIBLE_DEVICES="${SHARD_GPUS[$i]}" \
        PAPER4_SUMO_DIR="$sumo" \
        PYTHONPATH="$CODER_DIR" \
        "$PY" "${CODER_DIR}/etc/scripts/check_gamma_ablation.py" \
            --models "${SHARD_MODELS[$i]}" \
            --arms $ARMS \
            --seeds "${SHARD_SEEDS[$i]}" \
            --n-steps "$N_STEPS" \
            --out "$out" \
        > "$log" 2>&1 < /dev/null &
    pids+=($!)
    echo "[$(date '+%F %T')] ${name} pid $! on GPU ${SHARD_GPUS[$i]} -> ${log}"
    # Stagger so six processes do not hit the scenario generation lock together.
    sleep 5
done

rc=0
for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
        echo "SHARD FAILED: ${SHARD_NAMES[$i]} (see ${LOG_ROOT}/${SHARD_NAMES[$i]}.log)" >&2
        rc=1
    fi
done
echo "[$(date '+%F %T')] all shards finished (rc=${rc})"

PYTHONPATH="$CODER_DIR" "$PY" "${CODER_DIR}/etc/scripts/summarize_gamma_ablation.py" \
    --shard-root "$SHARD_ROOT" \
    --merged-out "$MERGED" \
    --summary-out "$SUMMARY"
exit $rc
