#!/usr/bin/env bash
# Restart every training run that is not finished. Safe to call at any time; it
# is what `@reboot` fires so an unattended run survives a workstation restart.
#
# WHY IT IS SAFE TO RUN REPEATEDLY. A run is considered finished only when its
# supervisor wrote `run_result.json` with exit_code 0. Anything else -- crashed,
# killed by a reboot, still going -- is a candidate. Before relaunching a
# candidate this checks whether a supervisor for that exact (arm, seed) is
# already alive, and skips it if so. Two supervisors on one run directory would
# have both writing the same checkpoints, which is the one way to actually lose
# the run.
#
# The relaunch never passes `--fresh`, so it always continues from the newest
# per-episode checkpoint. A reboot therefore costs the current episode, not the
# hours before it.
#
# Usage: etc/resume_all.sh            (from cron @reboot, or by hand)
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
RUNS_DIR="${CODER_DIR}/runs"
LAUNCHER="${CODER_DIR}/etc/run_main_training.sh"
LOG="/home/imnyj/Workspace/paper4/logs/resume_all.log"

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

[[ -d "$RUNS_DIR" ]] || { log "no runs directory; nothing to resume"; exit 0; }

# A reboot brings the machine up before the GPUs and the filesystem have
# necessarily settled. Waiting is cheaper than a spurious failed attempt.
sleep 60

for run_dir in "$RUNS_DIR"/*/; do
    [[ -d "$run_dir" ]] || continue
    name="$(basename "${run_dir%/}")"

    # Directory names are written by the launcher as <arm>_seed<N>.
    if [[ ! "$name" =~ ^(accumulate|mean)_seed([0-9]+)$ ]]; then
        log "skip ${name}: not a recognised run directory name"
        continue
    fi
    arm="${BASH_REMATCH[1]}"
    seed="${BASH_REMATCH[2]}"

    result="${run_dir}/run_result.json"
    if [[ -f "$result" ]] && grep -q '"exit_code":[[:space:]]*0' "$result"; then
        log "skip ${name}: already finished successfully"
        continue
    fi

    if pgrep -f "run_main_training.sh ${arm} ${seed}" > /dev/null 2>&1; then
        log "skip ${name}: a supervisor is already running for it"
        continue
    fi

    log "resuming ${name} (arm=${arm} seed=${seed})"
    setsid nohup "$LAUNCHER" "$arm" "$seed" > /dev/null 2>&1 < /dev/null &
    # Stagger so several runs do not all probe the GPUs in the same instant and
    # each conclude the same device is free.
    sleep 20
done

log "resume_all pass complete"
