#!/usr/bin/env bash
# Snapshot the training run's irreplaceable state so an abnormal shutdown costs
# an episode rather than the whole run.
#
# WHAT IS AND IS NOT IRREPLACEABLE. Checkpoints and per-episode progress CSVs are
# the run. TensorBoard event files are large and regenerable from the CSVs, so
# they are excluded; copying them every fifteen minutes would dominate the I/O
# for no recovery benefit.
#
# WHY A COPY AT ALL, given `run_all.py` already checkpoints per episode. The
# per-episode checkpoint is written in place. A power loss during that write, or
# a disk error, takes the file that the resume path depends on. Keeping the last
# few generations elsewhere means the worst case is losing the episodes since the
# last snapshot, not losing the ability to resume at all.
#
# Snapshots are hard-linked against the previous one where files are unchanged,
# so N generations cost roughly one generation of disk plus the deltas.
#
# Usage: etc/backup_runs.sh          (intended to be run from cron)
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
RUNS_DIR="${CODER_DIR}/runs"
BACKUP_ROOT="/home/imnyj/Workspace/paper4/backup/runs_snapshots"
KEEP=8   # ~2 hours of history at a 15-minute cadence

[[ -d "$RUNS_DIR" ]] || exit 0

mkdir -p "$BACKUP_ROOT"
STAMP="$(date '+%Y%m%d_%H%M%S')"
DEST="${BACKUP_ROOT}/${STAMP}"

# Hard-link against the newest existing snapshot so unchanged checkpoints are not
# copied again.
PREV="$(ls -1d "${BACKUP_ROOT}"/*/ 2>/dev/null | sort | tail -1)"
LINK_ARG=()
[[ -n "$PREV" ]] && LINK_ARG=(--link-dest="${PREV%/}")

rsync -a --quiet \
    --include='*/' \
    --include='ck/***' \
    --include='lg/***' \
    --include='sup/***' \
    --include='run_config.json' \
    --include='run_result.json' \
    --exclude='*' \
    "${LINK_ARG[@]}" \
    "${RUNS_DIR}/" "${DEST}/"
rc=$?

if [[ $rc -ne 0 ]]; then
    echo "[$(date '+%F %T')] backup_runs: rsync failed rc=${rc}" >&2
    exit "$rc"
fi

# A snapshot that is still being written must never be mistaken for a complete
# one, so completeness is marked explicitly rather than inferred from existence.
date -Iseconds > "${DEST}/.snapshot_complete"

# Prune, keeping only complete snapshots.
mapfile -t ALL < <(ls -1d "${BACKUP_ROOT}"/*/ 2>/dev/null | sort)
COUNT=${#ALL[@]}
if (( COUNT > KEEP )); then
    for (( i = 0; i < COUNT - KEEP; i++ )); do
        rm -rf "${ALL[$i]}"
    done
fi

echo "[$(date '+%F %T')] backup_runs: snapshot ${STAMP} ok (${COUNT} kept)"
