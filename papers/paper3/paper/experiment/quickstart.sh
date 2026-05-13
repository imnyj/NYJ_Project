#!/usr/bin/env bash
# quickstart.sh — 시뮬레이션 빠른 실행 스크립트
# 사용법:
#   bash quickstart.sh check     # 환경 점검 (SUMO, libsumo, sumolib, 경로)
#   bash quickstart.sh tiny      # 30 step 초경량 (5~30초) — SUMO/import만 확인
#   bash quickstart.sh quick     # 180 step 가벼운 smoke (15초~2분) — 동작 검증
#   bash quickstart.sh smoke     # 1800 step 본 실험 1 run (5~30분) — 통계 의미 있음
#   bash quickstart.sh A         # 시나리오 A 실행 (백그라운드)
#   bash quickstart.sh B         # 시나리오 B 실행
#   bash quickstart.sh C         # 시나리오 C 실행
#   bash quickstart.sh D         # 시나리오 D 실행
#   bash quickstart.sh E         # 시나리오 E 실행
#   bash quickstart.sh all       # 빠른 순서로 모두 순차 실행 (C→D→E→B→A, foreground)
#   bash quickstart.sh status    # 진행 상황 확인
#   bash quickstart.sh tail X    # 시나리오 X 로그 실시간 보기 (X ∈ A,B,C,D,E)
#   bash quickstart.sh stop      # 실행 중인 모든 run_scenario.py 중지
#
# 이 스크립트는 RUN_COMMANDS.md (Round 5) 의 모든 명령을 한 곳에 모은 것입니다.
# 사용자가 어떤 줄도 복붙할 필요 없이 위 키워드 1개만 인자로 주면 동작합니다.

set -u

# ================== 환경 변수 (필요 시 사용자가 수정) ==================
PROJ=/home/imnyj/papers/paper3
EXP=$PROJ/paper/experiment
DATA=$PROJ/paper/data
CODE=$EXP/code
SUMO_NETSIM=/home/imnyj/paper-ai.v1/SumoNetSim1.1.6

# SUMO_HOME 자동 감지 (환경에 이미 있으면 그것 사용)
if [ -z "${SUMO_HOME:-}" ]; then
    if [ -d /usr/share/sumo ]; then
        export SUMO_HOME=/usr/share/sumo
    elif [ -d /usr/local/share/sumo ]; then
        export SUMO_HOME=/usr/local/share/sumo
    fi
fi
export PYTHONPATH="${SUMO_HOME:-}/tools:${PYTHONPATH:-}"
# ====================================================================

mkdir -p "$DATA"

cmd=${1:-help}

case "$cmd" in

  help|"-h"|"--help"|"")
    sed -n '2,22p' "$0"
    exit 0
    ;;

  check)
    echo "=== [1/5] sumo --version ==="
    sumo --version 2>&1 | head -n 2 || echo "(sumo 명령을 찾지 못함 — apt install sumo 필요)"
    echo
    echo "=== [2/5] SUMO_HOME = ${SUMO_HOME:-(미설정)} ==="
    echo
    echo "=== [3/5] python3 -c 'import libsumo' ==="
    python3 -c "import libsumo; print('libsumo OK')" || echo "FAIL — libsumo 설치 필요"
    echo
    echo "=== [4/5] python3 -c 'import sumolib' ==="
    python3 -c "import sumolib; print('sumolib OK')" || echo "FAIL — sumolib 설치 필요"
    echo
    echo "=== [5/5] SumoNetSim 설정파일 ==="
    ls "$SUMO_NETSIM/src/sumo/generated.sumocfg" 2>&1
    ls "$SUMO_NETSIM/src/sumo/rsu.poi.xml" 2>&1
    echo
    echo "=== 출력 폴더 ==="
    ls -la "$DATA" | head -n 20
    ;;

  tiny)
    # SUMO 부팅 + sim_core import + 30 step 만 — 5~30초 목표
    cd "$CODE" || exit 1
    echo "=== Tiny smoke (30 step, 5~30초 목표) ==="
    python3 -u - <<'PY'
import sys, time
sys.path.insert(0, '.')
from sim_core import CIoVSim
from algorithms import ALGORITHMS
t0 = time.time()
sim = CIoVSim(seed=42, density_per_cell=5,
              prediction_error_pct=10, gamma=2.0, tau_max=5,
              duration_steps=30, warmup_steps=5)
m = sim.run(ALGORITHMS['RILP-Greedy'])
print('Tiny smoke OK:', m, 'in', round(time.time()-t0,1), 's')
PY
    ;;

  quick)
    # 진짜 smoke — 180 step (warmup 30) — 약 15초~2분 목표
    cd "$CODE" || exit 1
    echo "=== Import self-test ==="
    python3 sim_core.py
    echo
    echo "=== Quick smoke (180 step, 15초~2분 목표) ==="
    python3 -u - <<'PY'
import sys, time
sys.path.insert(0, '.')
from sim_core import CIoVSim
from algorithms import ALGORITHMS
t0 = time.time()
sim = CIoVSim(seed=42, density_per_cell=5,
              prediction_error_pct=10, gamma=2.0, tau_max=5,
              duration_steps=180, warmup_steps=30)
m = sim.run(ALGORITHMS['RILP-Greedy'])
print('Quick smoke OK:', m, 'in', round(time.time()-t0,1), 's')
PY
    ;;

  smoke)
    cd "$CODE" || exit 1
    echo "=== Import self-test ==="
    python3 sim_core.py
    echo
    echo "=== Heavy smoke = 본 실험 1 run (1800 step, 5~30분 가능) ==="
    echo "    빠르게 동작 확인만 원하면: bash quickstart.sh tiny  또는  quick"
    python3 -u - <<'PY'
import sys, time
sys.path.insert(0, '.')
from sim_core import CIoVSim
from algorithms import ALGORITHMS
t0 = time.time()
sim = CIoVSim(seed=42, density_per_cell=5,
              prediction_error_pct=10, gamma=2.0, tau_max=5,
              duration_steps=1800, warmup_steps=300)
m = sim.run(ALGORITHMS['RILP-Greedy'])
print('Heavy smoke OK:', m, 'in', round(time.time()-t0,1), 's')
PY
    ;;

  A|B|C|D|E)
    S=$cmd
    cd "$EXP" || exit 1
    echo "=== Scenario $S 시작 (백그라운드) ==="
    nohup python3 -u "$CODE/run_scenario.py" \
        --scenario "$S" \
        --output_dir "$DATA" \
        > "$DATA/run_${S}.log" 2>&1 &
    pid=$!
    echo "Scenario $S 백그라운드 실행 중. pid=$pid"
    echo "  로그: tail -f $DATA/run_${S}.log"
    echo "  중지: bash $0 stop"
    disown $pid 2>/dev/null || true
    ;;

  all)
    cd "$EXP" || exit 1
    echo "=== 모든 시나리오 순차 실행 (C→D→E→B→A, foreground) ==="
    echo "=== 중간에 끊겨도 같은 명령으로 자동 resume ==="
    for S in C D E B A; do
        echo
        echo "########## Scenario $S 시작: $(date) ##########"
        python3 -u "$CODE/run_scenario.py" \
            --scenario "$S" \
            --output_dir "$DATA" \
            2>&1 | tee "$DATA/run_${S}.log"
        echo "########## Scenario $S 종료: $(date) ##########"
    done
    ;;

  status)
    echo "=== paper/data/ 내용 ==="
    ls -la "$DATA" 2>/dev/null
    echo
    echo "=== 시나리오별 진행도 (행 수 / 목표) ==="
    declare -A TOTAL=( [A]=6400 [B]=1680 [C]=560 [D]=480 [E]=560 )
    for S in A B C D E; do
        f="$DATA/${S}_full.csv"
        if [ -f "$f" ]; then
            n=$(($(wc -l < "$f") - 1))
            echo "  $S: $n / ${TOTAL[$S]}"
        else
            echo "  $S: (파일 없음)"
        fi
    done
    echo
    echo "=== 실행 중 프로세스 ==="
    ps -ef | grep run_scenario | grep -v grep || echo "  (실행 중인 run_scenario.py 없음)"
    ;;

  tail)
    S=${2:-A}
    f="$DATA/run_${S}.log"
    if [ -f "$f" ]; then
        echo "=== tail -f $f (Ctrl-C 로 종료) ==="
        tail -f "$f"
    else
        echo "FAIL: $f 없음. 먼저 'bash $0 $S' 로 시작하세요."
    fi
    ;;

  stop)
    echo "=== 실행 중인 run_scenario.py 모두 중지 ==="
    pids=$(pgrep -f run_scenario.py || true)
    if [ -z "$pids" ]; then
        echo "  (실행 중인 프로세스 없음)"
    else
        echo "  종료할 pid: $pids"
        kill $pids
        sleep 2
        echo "  남아있는 pid: $(pgrep -f run_scenario.py || echo '없음')"
    fi
    ;;

  *)
    echo "알 수 없는 명령: $cmd"
    echo "사용법: bash $0 {check|tiny|quick|smoke|A|B|C|D|E|all|status|tail X|stop}"
    exit 1
    ;;
esac
