#!/usr/bin/env bash
# Supervised, unattended launcher for the HPO re-search, split across GPUs.
#
# WHY SPLIT. Each model's Optuna study is independent of the others, so the nine
# of them are embarrassingly parallel. Measured from the `duration` column of the
# nine committed studies, a trial (3 seeds, one rollout each) runs 911 to 1646 s
# depending on the model, so 9 models x 15 trials is 43.5 hours end to end on a
# single device. The box has four GPUs; splitting the models across them brings
# that to 12.7 hours without changing a single number that comes out. See the
# group table below for where the 12.7 comes from.
#
# WHY EACH GROUP GETS ITS OWN OUTPUT DIRECTORY. `run_all_baselines_hpo` writes
# `optuna_best_params.csv` once, at the end, containing the models IT ran. Four
# processes pointed at one directory would each overwrite that file with their
# own partial view, and the last writer would win. Groups therefore write to
# `<output-root>/<group>/` and are merged afterwards by
# `etc/merge_hpo_results.py`.
#
# WHY THE ROOTS ARE ARGUMENTS. They used to be constants pointing at
# `results/hpo_parallel/`. That directory now holds the results measured under
# the old observation normaliser (N_ACTIVE_MAX_OBS = 100.0), which are the
# control group for the re-search; a second run writing into it would erase the
# comparison and nobody would notice until the merge nine hours later. The
# defaults are unchanged so nothing that called this script silently moves, but
# the overwrite guard below now refuses that default rather than obeying it.
#
# WHAT EACH GROUP DIRECTORY GETS BESIDES ITS RESULTS. A `run_metadata.json`
# written before the group starts, holding the commit, the launch time, and the
# full list of paths that differed from that commit. The previous main training
# finished at 11:38 on 2026-09-03 and the divergence guard it was credited with
# was first committed at 15:37 the same day; nothing in the outputs recorded the
# gap, and it was only found by noticing a column missing from a progress CSV.
#
# Usage:
#   etc/run_hpo_parallel.sh --output-root DIR --log-root DIR   # launch, detached
#   etc/run_hpo_parallel.sh --dry-run [--output-root DIR ...]  # print the plan
#   etc/run_hpo_parallel.sh --preflight-only [...]             # run the gate only
#
# Options:
#   --output-root DIR   group result directories go under here
#   --log-root DIR      per-group launcher logs go under here
#   --sumo-root DIR     per-group SUMO scenarios go under here; must be
#                       outside the git work tree (default /var/tmp/paper4_sumo)
#   --n-trials N        Optuna trials per model (default 15)
#   --seeds "A B C"     tuning seeds (default "1001 1002 1003")
#   --dry-run           print the plan and exit; touches nothing
#   --preflight-only    run etc/preflight_hpo.py and exit with its status
#   --allow-overwrite   proceed even if the destinations already hold results
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
PY="/home/imnyj/venv/bin/python"
cd "$CODER_DIR" || exit 1

# Defaults reproduce the historical behaviour. They are not safe to reuse now --
# the guard below is what makes that explicit instead of destructive.
OUT_ROOT="${CODER_DIR}/results/hpo_parallel"
LOG_ROOT="/home/imnyj/Workspace/paper4/logs/hpo_parallel"
# Outside the work tree on purpose; see the SUMO_DIRS block below.
SUMO_ROOT="/var/tmp/paper4_sumo"

# HOORL's offline stage reads its collection from this variable and there is NO
# fallback path: `hoorl_wiring.load_offline_dataset` raises OfflineDatasetMissing
# when it is unset, `evaluate_trial_multiseed` turns that into FAILED_RUN_PENALTY,
# and in the trial CSV a penalised trial is indistinguishable from a genuinely
# poor one. So an unset variable does not stop the run, it silently costs all
# fifteen HOORL trials and reports the loss as bad hyper-parameters.
#
# It was never set here. The group processes are started with `env` naming three
# variables, and this was not among them, so HOORL depended on whoever ran the
# script having exported it by hand. Found on 2026-09-07 by the pre-flight probe
# that runs each model for sixty steps.
HOORL_DATASET="/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"
N_TRIALS=15
SEEDS="1001 1002 1003"
DRY_RUN=0
PREFLIGHT_ONLY=0
ALLOW_OVERWRITE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-root)     OUT_ROOT="$2"; shift 2 ;;
        --output-root=*)   OUT_ROOT="${1#*=}"; shift ;;
        --log-root)        LOG_ROOT="$2"; shift 2 ;;
        --log-root=*)      LOG_ROOT="${1#*=}"; shift ;;
        --sumo-root)       SUMO_ROOT="$2"; shift 2 ;;
        --hoorl-dataset)   HOORL_DATASET="$2"; shift 2 ;;
        --hoorl-dataset=*) HOORL_DATASET="${1#*=}"; shift ;;
        --sumo-root=*)     SUMO_ROOT="${1#*=}"; shift ;;
        --n-trials)        N_TRIALS="$2"; shift 2 ;;
        --n-trials=*)      N_TRIALS="${1#*=}"; shift ;;
        --seeds)           SEEDS="$2"; shift 2 ;;
        --seeds=*)         SEEDS="${1#*=}"; shift ;;
        --dry-run)         DRY_RUN=1; shift ;;
        --preflight-only)  PREFLIGHT_ONLY=1; shift ;;
        --allow-overwrite) ALLOW_OVERWRITE=1; shift ;;
        # Print the whole leading comment block, however long it grows. A fixed
        # line range would silently truncate the help the next time this header
        # gains a paragraph.
        -h|--help)         awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"; exit 0 ;;
        *)
            echo "unknown argument: $1" >&2
            echo "run '$0 --help' for the accepted options" >&2
            exit 2
            ;;
    esac
done

# Relative roots are resolved against the coder directory, not the caller's cwd,
# so `--output-root results/hpo_parallel_v2` means the same thing from anywhere.
[[ "$OUT_ROOT" = /* ]] || OUT_ROOT="${CODER_DIR}/${OUT_ROOT}"
[[ "$LOG_ROOT" = /* ]] || LOG_ROOT="${CODER_DIR}/${LOG_ROOT}"
OUT_ROOT="${OUT_ROOT%/}"
LOG_ROOT="${LOG_ROOT%/}"
SUMO_ROOT="${SUMO_ROOT%/}"

# Groups are balanced by MEASURED trial cost. The earlier split assumed the two
# on-policy models were the expensive pair and separated them on that basis, but
# the algorithm family turned out not to predict the cost: read out of the
# `duration` column of the nine committed studies (excluding the trials that lost
# their rollouts), the median trial takes
#
#   PPO 1646 s | RES-MAPDDPG 1313 s | MADDPG-MT 1206 s | TD3 1120 s
#   MA2HDQN 1071 s | I-HAMAPPO 1005 s | SPAM-D3QN 911 s | HOORL 882 s
#
# WHEN EACH FIGURE WAS MEASURED, because a stale cost table is what put a
# discarded baseline in this list for a day. The seven above other than HOORL are
# medians of the `duration` column of the nine studies committed on 2026-09-04,
# excluding the trials that lost their rollouts. HOORL's is a single measurement
# taken on 2026-09-06 and is described below.
#
# I-HAMAPPO, on-policy, is the second CHEAPEST of the nine and sits among the
# off-policy models; only PPO is genuinely expensive. Group by the measurement,
# not by the family. SAC has no valid trial to measure -- all 45 of its rollouts
# were lost on 2026-09-04 -- and is budgeted at the median of the six off-policy
# baselines, which is 1096 s both before and after CARLTON was replaced. The
# figures and the arithmetic are in `results/diagnostics/hpo_group_balance.csv`.
#
# HOORL REPLACED CARLTON HERE ON 2026-09-06 and does NOT inherit its 1071 s.
# HOORL has an offline stage the other eight do not, so its trial cost had to be
# measured rather than assumed. Measured on 2026-09-06 with the collected
# 133,405-transition dataset, at the search's own 4000-step rollout:
#
#   one seed        293.8 s   (of which offline pre-training 15.4 s)
#   trial, 3 seeds  881.5 s   (pre-training runs ONCE PER SEED, not once per
#                              trial: `pretrain_hoorl` sits inside the seed loop
#                              of `evaluate_trial_multiseed`)
#
# so the offline stage is 5.2 % of the trial and HOORL is the CHEAPEST of the
# nine, not the mid-priced model CARLTON was. Sources:
# `results/hoorl_offline/hoorl_trial_cost.csv` and
# `results/hoorl_offline/pretrain_cost_per_trial.csv`. It is one measurement at
# median hyper-parameters rather than a median over a whole study, so treat it as
# accurate to within the spread the search itself will produce.
#
# At 15 trials per model that projects to g0 11.88 h, g1 8.75 h, g2 10.14 h and
# g3 11.93 h, so the critical path is g3 at 11.93 h -- 0.78 h shorter than the
# 12.71 h it was with CARLTON, purely because the replacement is cheaper. MA2HDQN
# stays in g3 rather than beside TD3 and RES-MAPDDPG for the original reason:
# leaving it in g2 makes that group 14.60 h.
#
# Moving MA2HDQN to g0 and I-HAMAPPO to g3 would reach 11.66 h. That is 16
# minutes for disturbing two further groups, and the same standard was applied
# when this table was last balanced, so it is not taken.
GROUP_NAMES=(g0 g1 g2 g3)
GROUP_GPUS=(0 1 2 3)
GROUP_MODELS=(
    "PPO MADDPG-MT"
    "I-HAMAPPO SAC"
    "TD3 RES-MAPDDPG"
    "SPAM-D3QN HOORL MA2HDQN"
)

# Scenario directories live OUTSIDE the git work tree. They used to sit at
# `<output-root>/<group>/sumo`, which is under /home/imnyj -- and this repository's
# top level IS /home/imnyj, so everything beneath Workspace/ is tracked territory.
# `.gitignore` does not protect them: `git clean -fdx` removes ignored files by
# design, and even without -x a plain `git clean -nd Workspace/paper4` lists 175
# entries because untracked is enough. That is exactly how the g1 group lost its
# scenario directory on 2026-09-04, two and a half hours in, taking 62 rollouts
# and the whole SAC study with it.
#
# /var/tmp rather than /tmp: it is on the ext4 root filesystem here, not a tmpfs,
# so it survives a reboot, and the `q /var/tmp ... 30d` age rule in
# /usr/lib/tmpfiles.d/tmp.conf is commented out on this box, so nothing sweeps it.
# A scenario set is 488 KB; four groups need about 2 MB against 159 GB free.
SUMO_DIRS=()
for name in "${GROUP_NAMES[@]}"; do
    SUMO_DIRS+=("${SUMO_ROOT}/${name}")
done

if [[ $DRY_RUN -eq 1 ]]; then
    echo "output root: ${OUT_ROOT}"
    echo "log root:    ${LOG_ROOT}"
    echo "sumo root:   ${SUMO_ROOT}"
    echo "trials:      ${N_TRIALS}   seeds: ${SEEDS}"
    for i in "${!GROUP_NAMES[@]}"; do
        echo "GPU ${GROUP_GPUS[$i]}  ${GROUP_NAMES[$i]}: ${GROUP_MODELS[$i]}"
        echo "        out  ${OUT_ROOT}/${GROUP_NAMES[$i]}"
        echo "        sumo ${SUMO_DIRS[$i]}"
        echo "        log  ${LOG_ROOT}/${GROUP_NAMES[$i]}.log"
    done
    exit 0
fi

# ---------------------------------------------------------------------------
# Overwrite guard. Nine hours is too long to find out afterwards that the run
# landed on top of the control group. Anything that looks like a result file
# under either root stops the launch here.
# ---------------------------------------------------------------------------
guard_hits=()
for i in "${!GROUP_NAMES[@]}"; do
    d="${OUT_ROOT}/${GROUP_NAMES[$i]}"
    if [[ -d "$d" ]]; then
        while IFS= read -r f; do
            [[ -n "$f" ]] && guard_hits+=("$f")
        done < <(find "$d" -maxdepth 1 -type f \
                     \( -name 'optuna_*' -o -name 'hpo_failed_models.csv' \) 2>/dev/null)
    fi
    l="${LOG_ROOT}/${GROUP_NAMES[$i]}.log"
    [[ -f "$l" ]] && guard_hits+=("$l")
done

if [[ ${#guard_hits[@]} -gt 0 && $ALLOW_OVERWRITE -eq 0 ]]; then
    echo "REFUSING TO LAUNCH: the destinations already hold results." >&2
    echo "  output root: ${OUT_ROOT}" >&2
    echo "  log root:    ${LOG_ROOT}" >&2
    echo "  ${#guard_hits[@]} file(s) would be overwritten or appended to:" >&2
    for f in "${guard_hits[@]:0:12}"; do echo "    $f" >&2; done
    if [[ ${#guard_hits[@]} -gt 12 ]]; then
        echo "    ... and $(( ${#guard_hits[@]} - 12 )) more" >&2
    fi
    echo "" >&2
    echo "results/hpo_parallel/ is the control group measured under the old" >&2
    echo "observation normaliser. Point --output-root and --log-root at a new" >&2
    echo "location, e.g.:" >&2
    echo "  $0 --output-root ${CODER_DIR}/results/hpo_parallel_v2 \\" >&2
    echo "     --log-root /home/imnyj/Workspace/paper4/logs/hpo_parallel_v2" >&2
    echo "" >&2
    echo "Pass --allow-overwrite only if you have already moved them aside." >&2
    exit 3
fi

# ---------------------------------------------------------------------------
# Pre-flight. Every check in it corresponds to something this run has already
# lost once. A non-zero exit stops the launch.
# ---------------------------------------------------------------------------
PYTHONPATH="$CODER_DIR" PAPER4_HOORL_OFFLINE_DATASET="$HOORL_DATASET" \
    "$PY" "${CODER_DIR}/etc/preflight_hpo.py" \
    --output-root "$OUT_ROOT" \
    --log-root "$LOG_ROOT" \
    --sumo-dirs "${SUMO_DIRS[@]}" \
    --gpus "${GROUP_GPUS[@]}" \
    --group-models "${GROUP_MODELS[@]}"
preflight_rc=$?

if [[ $PREFLIGHT_ONLY -eq 1 ]]; then
    exit $preflight_rc
fi

if [[ $preflight_rc -ne 0 ]]; then
    echo "" >&2
    echo "pre-flight failed (exit ${preflight_rc}); nothing was launched." >&2
    echo "fix the items listed above, then run this script again." >&2
    exit 4
fi

mkdir -p "$LOG_ROOT"

for i in "${!GROUP_NAMES[@]}"; do
    name="${GROUP_NAMES[$i]}"
    gpu="${GROUP_GPUS[$i]}"
    models="${GROUP_MODELS[$i]}"
    out="${OUT_ROOT}/${name}"
    log="${LOG_ROOT}/${name}.log"
    sumo="${SUMO_DIRS[$i]}"
    mkdir -p "$out" "$sumo"

    # Record which code this group starts from, BEFORE it starts, in the same
    # directory as its results. The previous main training finished four hours
    # before the divergence guard it was credited with was first committed, and
    # no artefact said so; it was reconstructed from a missing CSV column. The
    # commit alone is not enough while several sessions edit this tree, so the
    # `git status --porcelain` list goes in too.
    PYTHONPATH="$CODER_DIR" "$PY" "${CODER_DIR}/etc/write_run_metadata.py" \
        --output-dir "$out" \
        --group "$name" \
        --gpu "$gpu" \
        --models $models \
        --n-trials "$N_TRIALS" \
        --seeds $SEEDS \
        --sumo-dir "$sumo" \
        --log-path "$log"

    # Each group needs its own SUMO scenario directory. Without it every process
    # regenerates one shared generated.net.xml and the others silently read a
    # network they did not ask for -- no error, wrong numbers.
    setsid nohup env \
        CUDA_VISIBLE_DEVICES="$gpu" \
        PAPER4_SUMO_DIR="$sumo" \
        PAPER4_HOORL_OFFLINE_DATASET="$HOORL_DATASET" \
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

echo "launched ${#GROUP_NAMES[@]} groups into ${OUT_ROOT}"
echo "merge with etc/merge_hpo_results.py --input-root ${OUT_ROOT} when all are done"
