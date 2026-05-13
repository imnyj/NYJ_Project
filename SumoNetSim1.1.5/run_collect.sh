#!/bin/bash
# 데이터 수집 반복 실행 스크립트
# 600s짜리 시뮬레이션을 N회 반복하여 데이터 누적
# 각 실행 사이 5초 대기 (libsumo 소켓 정리)

RUNS=${1:-20}       # 기본 20회 (약 8000+ 레코드 목표)
LOG_DIR="/tmp/sumo_collect_logs"
mkdir -p "$LOG_DIR"

echo "=== 데이터 수집 시작: ${RUNS}회 반복 ==="
echo "출력: /home/nyj/ST-MBAN/SumoNetSim1.1.5/data/"

for i in $(seq 1 $RUNS); do
    echo "[$(date '+%H:%M:%S')] Run $i / $RUNS 시작..."
    cd /home/nyj/ST-MBAN/SumoNetSim1.1.5
    PYTHONPATH="" timeout 120 python3 -u dataset_scenario.py > "$LOG_DIR/run_${i}.log" 2>&1
    STATUS=$?
    RECORDS=$(awk 'NR>1' /home/nyj/ST-MBAN/SumoNetSim1.1.5/data/rsu_*.csv 2>/dev/null | wc -l)
    echo "[$(date '+%H:%M:%S')] Run $i 완료 (exit=$STATUS) | 누적 레코드: $RECORDS"
    sleep 3
done

echo ""
echo "=== 수집 완료 ==="
TOTAL=$(awk 'NR>1' /home/nyj/ST-MBAN/SumoNetSim1.1.5/data/rsu_*.csv 2>/dev/null | wc -l)
echo "최종 누적 레코드: $TOTAL"
echo "CSV 파일 수: $(ls /home/nyj/ST-MBAN/SumoNetSim1.1.5/data/rsu_*.csv 2>/dev/null | wc -l)"
