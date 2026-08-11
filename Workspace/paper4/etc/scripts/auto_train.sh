#!/bin/bash
# Paper4 훈련 자동 재시작 래퍼 스크립트
# 프로세스가 중단되면 자동으로 재시작합니다 (checkpoint resume 로직 활용).
# 사용법: nohup bash /home/imnyj/Workspace/paper4/etc/scripts/auto_train.sh > /home/imnyj/Workspace/paper4/etc/logs/auto_train.log 2>&1 &

SCRIPT="/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py"
PYTHON="/home/imnyj/venv/bin/python"
LOG_DIR="/home/imnyj/Workspace/paper4/etc/logs"
MODELS_DIR="/home/imnyj/Workspace/paper4/data/models"
EVAL_DIR="/home/imnyj/Workspace/paper4/data/evaluation"

MAX_RETRIES=10
RETRY_DELAY=30  # seconds between retries

mkdir -p "$LOG_DIR"

is_training_complete() {
    local all_done=true
    for f in "$MODELS_DIR"/*_convergence.csv; do
        lines=$(($(wc -l < "$f") - 1))
        if [ "$lines" -lt 100 ]; then
            all_done=false
            break
        fi
    done
    echo "$all_done"
}

is_eval_complete() {
    local density_file="$EVAL_DIR/eval_density_results.csv"
    local speed_file="$EVAL_DIR/eval_speed_results.csv"
    if [ -f "$density_file" ] && [ -f "$speed_file" ]; then
        local d_lines=$(($(wc -l < "$density_file") - 1))
        local s_lines=$(($(wc -l < "$speed_file") - 1))
        # 21 methods x 6 densities x 3 seeds = 378; 21 methods x 5 speeds x 3 seeds = 315
        if [ "$d_lines" -ge 300 ] && [ "$s_lines" -ge 250 ]; then
            echo "true"
            return
        fi
    fi
    echo "false"
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Paper4 Auto-Train Wrapper Started ==="

for attempt in $(seq 1 $MAX_RETRIES); do
    # Check if everything is already done
    if [ "$(is_training_complete)" = "true" ] && [ "$(is_eval_complete)" = "true" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 모든 훈련 및 평가가 완료되었습니다! 종료합니다."
        exit 0
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시도 $attempt/$MAX_RETRIES: 훈련 스크립트 실행..."

    # Show current progress
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 현재 진행도:"
    for f in "$MODELS_DIR"/*_convergence.csv; do
        name=$(basename "$f" _convergence.csv)
        lines=$(($(wc -l < "$f") - 1))
        echo "  $name: $lines/100"
    done

    # Run the training script
    $PYTHON "$SCRIPT" >> "$LOG_DIR/training_nohup.log" 2>&1
    EXIT_CODE=$?

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 스크립트 종료 (exit code: $EXIT_CODE)"

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 스크립트 정상 완료!"
        break
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ 비정상 종료. ${RETRY_DELAY}초 후 재시작..."
        sleep $RETRY_DELAY
    fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Auto-Train Wrapper 종료 ==="
