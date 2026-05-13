#!/bin/bash
# ============================================================================
# cleanup_synthetic.sh
# ----------------------------------------------------------------------------
# 합성/가짜 데이터, 중복 코드, 잘못된 nested 경로, __pycache__ 정리 스크립트
# 진짜 시뮬레이션을 새로 돌리기 전에 한 번 실행하세요.
# ============================================================================

set -e

ROOT="/home/imnyj/papers/paper2"
cd "$ROOT"

echo "====================================================================="
echo "  MAFAC 프로젝트 정리"
echo "====================================================================="

# ── 1. 합성 CSV 데이터 삭제 (Phase 0,1 진짜 결과만 보존) ───────────────────
echo ""
echo "[1/5] 합성 CSV 데이터 삭제 (Phase 2/3/4/5는 실제 학습 안 됐는데 결과만 있음)"

SYNTHETIC_CSVS=(
    "paper/data/S1_density_average_aoi.csv"
    "paper/data/S1_density_cache_hit_ratio.csv"
    "paper/data/S1_density_constraint_violation.csv"
    "paper/data/S1_density_peak_aoi.csv"
    "paper/data/S1_density_throughput.csv"
    "paper/data/S1_density_tx_success_rate.csv"
    "paper/data/S2_cache_average_aoi.csv"
    "paper/data/S2_cache_cache_hit_ratio.csv"
    "paper/data/S2_cache_peak_aoi.csv"
    "paper/data/S2_cache_tx_success_rate.csv"
    "paper/data/S3_channel_average_aoi.csv"
    "paper/data/S3_channel_peak_aoi.csv"
    "paper/data/S3_channel_throughput.csv"
    "paper/data/S3_channel_tx_success_rate.csv"
    "paper/data/S4_zipf_average_aoi.csv"
    "paper/data/S4_zipf_cache_hit_ratio.csv"
    "paper/data/ablation_component_analysis.csv"
    "paper/data/communication_overhead.csv"
    "paper/data/convergence_constraint_satisfaction.csv"
    "paper/data/convergence_training_curves.csv"
)
for f in "${SYNTHETIC_CSVS[@]}"; do
    if [ -f "$f" ]; then
        rm "$f"
        echo "  rm $f"
    fi
done
echo "  → 보존된 진짜 데이터: paper/data/model_verification_theorem1.csv, theorem2.csv"

# ── 2. 잘못된 nested 경로 잔여물 삭제 ──────────────────────────────────────
echo ""
echo "[2/5] 잘못 생성된 중첩 디렉토리 삭제"
if [ -d "simulation/home" ]; then
    rm -rf simulation/home
    echo "  rm -rf simulation/home  (잘못된 경로로 출력된 잔여물)"
fi

# ── 3. 이전 학습 체크포인트 정리 (새 학습 위해) ────────────────────────────
echo ""
echo "[3/5] 이전 체크포인트 삭제 (50ep 시점에서 중단된 흔적)"
if [ -d "simulation/checkpoints/MAFAC/ep00050" ]; then
    rm -rf simulation/checkpoints/MAFAC/ep00050
    echo "  rm -rf simulation/checkpoints/MAFAC/ep00050"
fi

# ── 4. 중복 / 사용 안 하는 파일 ────────────────────────────────────────────
echo ""
echo "[4/5] 중복/구버전 코드 파일 삭제"

# run_all.py 는 run_full_simulation.py 의 구버전 — 둘이 거의 동일
if [ -f "simulation/run_all.py" ]; then
    rm simulation/run_all.py
    echo "  rm simulation/run_all.py  (run_full_simulation.py와 중복)"
fi

# backup/ 폴더는 이전 paper1 버전의 시뮬레이션 — 본 프로젝트 코드와 별개
if [ -d "simulation/backup" ]; then
    rm -rf simulation/backup
    echo "  rm -rf simulation/backup  (이전 paper1 잔여물, 21개 파일)"
fi

# ── 5. __pycache__ 캐시 정리 ──────────────────────────────────────────────
echo ""
echo "[5/5] Python 캐시 디렉토리 정리"
find . -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null || true
find . -type d -name ".vs" -prune -exec rm -rf {} \; 2>/dev/null || true
find . -type d -name ".vscode" -prune -exec rm -rf {} \; 2>/dev/null || true
echo "  모든 __pycache__ / .vs / .vscode 삭제"

echo ""
echo "====================================================================="
echo "  정리 완료"
echo "====================================================================="
echo ""
echo "정리 후 디렉토리 구조 확인:"
echo "  ls paper/data/"
ls paper/data/ 2>/dev/null || echo "  (없음)"
echo ""
echo "  ls simulation/"
ls simulation/ 2>/dev/null
