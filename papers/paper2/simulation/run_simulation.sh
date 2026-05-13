#!/bin/bash
# ============================================================================
# MAFAC Full Simulation Runner
# ============================================================================
# 
# 사용법:
#   chmod +x run_simulation.sh
#   ./run_simulation.sh              # 전체 시뮬레이션 (모든 Phase)
#   ./run_simulation.sh --phase 2    # Phase 2만 (MAFAC 학습)
#   ./run_simulation.sh --phase 3    # Phase 3만 (성능 평가)
#   ./run_simulation.sh --quick      # 빠른 테스트 (에피소드 축소)
#
# Phase 구성:
#   Phase 0: SUMO 네트워크 검증
#   Phase 1: 모델 검증 (Theorem 1 & 2)          ~5분
#   Phase 2: MAFAC 학습 + 수렴 곡선              ~2-6시간
#   Phase 3: 4시나리오 × 6알고리즘 성능 평가      ~4-12시간
#   Phase 4: Ablation Study                       ~2-4시간
#   Phase 5: Communication Overhead               ~1-2시간
#
# 예상 총 소요 시간:
#   - 기본(500 episodes):  ~12-24시간
#   - 축소(200 episodes):  ~4-8시간
#   - 빠른 테스트(20 ep):  ~30분-1시간
# ============================================================================

set -e

# 스크립트 위치로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 색상 출력 ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  MAFAC Simulation Pipeline${NC}"
echo -e "${BLUE}============================================${NC}"

# ── 환경 확인 ────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[환경 확인]${NC}"

# Python 확인
if command -v python3 &> /dev/null; then
    PYTHON=python3
    echo -e "  ${GREEN}[OK]${NC} Python: $(python3 --version)"
else
    echo -e "  ${RED}[ERROR]${NC} Python3 not found!"
    exit 1
fi

# PyTorch 확인
$PYTHON -c "import torch; print(f'  \033[0;32m[OK]\033[0m PyTorch {torch.__version__}')" 2>/dev/null || \
    echo -e "  ${YELLOW}[WARN]${NC} PyTorch not found. Using numpy fallback."

# libsumo 확인
$PYTHON -c "import libsumo; print('  \033[0;32m[OK]\033[0m libsumo available')" 2>/dev/null || \
    echo -e "  ${YELLOW}[WARN]${NC} libsumo not found. Using Mock SUMO mode."

# CUDA 확인
$PYTHON -c "
import torch
if torch.cuda.is_available():
    print(f'  \033[0;32m[OK]\033[0m CUDA: {torch.cuda.get_device_name(0)}')
else:
    print('  \033[1;33m[INFO]\033[0m CUDA not available. Using CPU.')
" 2>/dev/null || true

# NumPy 확인
$PYTHON -c "import numpy; print(f'  \033[0;32m[OK]\033[0m NumPy {numpy.__version__}')" 2>/dev/null || \
    { echo -e "  ${RED}[ERROR]${NC} NumPy not found! Run: pip install numpy"; exit 1; }

echo ""

# ── 인자 파싱 ────────────────────────────────────────────────────────────────
PHASES="0,1,2,3,4,5"
P2_EPISODES=500
P3_EPISODES=100
EVAL_EPISODES=5
SEED=42
DEVICE="auto"
NOHUP_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase|--phases)
            PHASES="$2"
            shift 2
            ;;
        --p2-episodes)
            P2_EPISODES="$2"
            shift 2
            ;;
        --p3-episodes)
            P3_EPISODES="$2"
            shift 2
            ;;
        --eval-episodes)
            EVAL_EPISODES="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --device)
            DEVICE="$2"
            shift 2
            ;;
        --quick)
            P2_EPISODES=20
            P3_EPISODES=10
            EVAL_EPISODES=1
            echo -e "${YELLOW}[Quick Mode]${NC} Reduced episodes: P2=${P2_EPISODES}, P3=${P3_EPISODES}"
            shift
            ;;
        --medium)
            P2_EPISODES=200
            P3_EPISODES=50
            EVAL_EPISODES=3
            echo -e "${YELLOW}[Medium Mode]${NC} P2=${P2_EPISODES}, P3=${P3_EPISODES}"
            shift
            ;;
        --background|--nohup)
            NOHUP_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_simulation.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --phases N,N,...    Phases to run (default: 0,1,2,3,4,5)"
            echo "  --phase N          Single phase to run"
            echo "  --p2-episodes N    Phase 2 training episodes (default: 500)"
            echo "  --p3-episodes N    Phase 3-5 training episodes (default: 100)"
            echo "  --eval-episodes N  Evaluation episodes (default: 5)"
            echo "  --seed N           Random seed (default: 42)"
            echo "  --device DEV       Device: auto/cpu/cuda (default: auto)"
            echo "  --quick            Quick mode (20/10 episodes)"
            echo "  --medium           Medium mode (200/50 episodes)"
            echo "  --background       Run in background with nohup"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# ── 실행 정보 출력 ────────────────────────────────────────────────────────────
echo -e "${BLUE}[실행 설정]${NC}"
echo "  Phases:            ${PHASES}"
echo "  Phase 2 episodes:  ${P2_EPISODES}"
echo "  Phase 3-5 episodes:${P3_EPISODES}"
echo "  Eval episodes:     ${EVAL_EPISODES}"
echo "  Seed:              ${SEED}"
echo "  Device:            ${DEVICE}"
echo "  Output dir:        $(dirname "$SCRIPT_DIR")/paper/data/"
echo ""

# ── 실행 ────────────────────────────────────────────────────────────────────
CMD="$PYTHON run_full_simulation.py \
    --phases $PHASES \
    --p2-episodes $P2_EPISODES \
    --p3-episodes $P3_EPISODES \
    --eval-episodes $EVAL_EPISODES \
    --seed $SEED \
    --device $DEVICE"

if [ "$NOHUP_MODE" = true ]; then
    echo -e "${YELLOW}[Background Mode]${NC} Running with nohup..."
    echo "  Log: simulation_log.txt"
    echo "  PID file: simulation.pid"
    nohup $CMD > simulation_nohup.log 2>&1 &
    echo $! > simulation.pid
    PID=$(cat simulation.pid)
    echo -e "${GREEN}Started!${NC} PID: $PID"
    echo "  Monitor: tail -f simulation_log.txt"
    echo "  Stop:    kill $(cat simulation.pid)"
else
    echo -e "${GREEN}[Starting Simulation]${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    $CMD
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}[완료]${NC} 결과 확인: ls -la $(dirname "$SCRIPT_DIR")/paper/data/"
fi
