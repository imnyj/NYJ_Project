#!/bin/bash
# Paper4 훈련 진행 상태 확인 스크립트
# 사용법: bash /home/imnyj/Workspace/paper4/etc/scripts/check_progress.sh

MODELS_DIR="/home/imnyj/Workspace/paper4/data/models"
EVAL_DIR="/home/imnyj/Workspace/paper4/data/evaluation"
LOG="/home/imnyj/Workspace/paper4/etc/logs/training_nohup.log"

echo "============================================"
echo "  Paper4 Training Progress Report"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# 1. Process check
echo ""
echo "[1] 프로세스 상태:"
PIDS=$(pgrep -f run_parallel_evaluation)
if [ -z "$PIDS" ]; then
    echo "  ❌ 훈련 프로세스가 실행 중이 아닙니다!"
    echo "  재시작 명령: cd /home/imnyj/Workspace/paper4 && nohup /home/imnyj/venv/bin/python code/run_parallel_evaluation.py >> $LOG 2>&1 &"
else
    echo "  ✅ PID: $PIDS (정상 가동 중)"
fi

# 2. Episode progress
echo ""
echo "[2] 모델별 훈련 진행도 (에피소드):"
for f in "$MODELS_DIR"/*_convergence.csv; do
    name=$(basename "$f" _convergence.csv)
    lines=$(($(wc -l < "$f") - 1))
    if [ "$lines" -ge 100 ]; then
        status="✅ 완료"
    elif [ "$lines" -gt 0 ]; then
        status="🟡 진행 중"
    else
        status="⏳ 대기"
    fi
    printf "  %-25s %3d / 100  %s\n" "$name" "$lines" "$status"
done

# 3. Weight files
echo ""
echo "[3] 저장된 가중치 파일:"
ls -lh "$MODELS_DIR"/*.pth "$MODELS_DIR"/*.pkl 2>/dev/null | awk '{printf "  %s (%s)\n", $NF, $5}'

# 4. Evaluation results
echo ""
echo "[4] 평가 결과 파일:"
for f in eval_density_results.csv eval_speed_results.csv; do
    fp="$EVAL_DIR/$f"
    if [ -f "$fp" ]; then
        lines=$(($(wc -l < "$fp") - 1))
        echo "  ✅ $f ($lines rows)"
    else
        echo "  ⏳ $f (아직 생성되지 않음)"
    fi
done

# 5. Last log lines
echo ""
echo "[5] 최근 로그 (마지막 5줄):"
tail -5 "$LOG" 2>/dev/null || echo "  로그 파일 없음"
echo ""
echo "============================================"
