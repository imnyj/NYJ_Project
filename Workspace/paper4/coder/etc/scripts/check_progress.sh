#!/usr/bin/env bash
# 본훈련 진행 상황을 한 화면에 보여 준다. 세션 없이도 쓸 수 있다.
#
#   bash etc/scripts/check_progress.sh
#
# 에이전트가 계속 폴링하는 대신 사용자가 직접 확인하도록 두는 것이 목적이다.
# 읽기 전용이며 실행 중인 훈련에 어떤 영향도 주지 않는다.
set -uo pipefail

CODER_DIR="/home/imnyj/Workspace/paper4/coder"
cd "$CODER_DIR" || exit 1

echo "=============================================================="
echo " paper4 본훈련 진행 상황   $(date '+%F %T')"
echo "=============================================================="

# --- 프로세스 -------------------------------------------------------------
# 감독자와 훈련 프로세스를 따로 센다. 감독자만 살아 있으면 재시작 대기 중이고,
# 둘 다 없으면 끝났거나 포기한 것이다.
echo
echo "[프로세스]"
# 명령줄 앞머리에 고정해서 센다. `pgrep -f "run_main_training.sh"`만 쓰면 그
# 문자열을 인자로 담은 셸이나 이 스크립트를 부른 명령까지 함께 잡혀, 감독자가
# 하나인데 셋으로 보고된다. 첫 실행에서 실제로 그렇게 나왔다.
sup=$(pgrep -c -f "^bash etc/run_main_training\.sh" || true)
trn=$(pgrep -c -f "^/home/imnyj/venv/bin/python run_all\.py" || true)
printf "  감독자 %d개, 훈련 %d개\n" "$sup" "$trn"
if [[ $trn -gt 0 ]]; then
    ps -o etime=,time=,pcpu=,rss=,args= -C python 2>/dev/null \
        | grep "[r]un_all.py" \
        | awk '{printf "  경과 %-10s CPU %-10s %5s%%  %5.1fGB\n", $1, $2, $3, $4/1048576}'
fi

# --- GPU ------------------------------------------------------------------
echo
echo "[GPU]"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,temperature.gpu \
           --format=csv,noheader 2>/dev/null | sed 's/^/  /'

# --- 실행별 상태 ----------------------------------------------------------
echo
echo "[실행]"
shopt -s nullglob
found=0
for d in runs/*/; do
    found=1
    name=$(basename "$d")
    cfg="${d}run_config.json"
    res="${d}run_result.json"

    # 에피소드 진행은 체크포인트 파일 이름에서 읽는다. 훈련이 매 에피소드
    # 저장하므로 가장 큰 번호가 마지막으로 끝난 에피소드다.
    #
    # 배열로 받는다. `nullglob`이 켜진 상태에서 `ls <glob>`을 쓰면 매치가 없을 때
    # glob이 통째로 사라져 `ls`가 인자 없이 현재 디렉터리를 나열하고, 그 목록이
    # 모델 이름으로 보고된다. 첫 실행에서 실제로 그렇게 나왔다.
    cks=("${d}ck"/*_ep*.pt)
    if (( ${#cks[@]} > 0 )); then
        last_ep=$(printf '%s\n' "${cks[@]}" \
                  | sed -n 's/.*_ep0*\([0-9]\+\)\.pt/\1/p' | sort -n | tail -1)
        models=$(printf '%s\n' "${cks[@]}" \
                 | sed 's#.*/##; s/_ep[0-9]*\.pt//' | sort -u | tr '\n' ' ')
    else
        last_ep=""
        models=""
    fi

    printf "  %s\n" "$name"
    if [[ -f "$cfg" ]]; then
        total=$(grep -o '"total_steps"[^,}]*' "$cfg" | tr -d ' "' | cut -d: -f2)
        eps=$(grep -o '"episodes"[^,}]*' "$cfg" | tr -d ' "' | cut -d: -f2)
        printf "    설정   에피소드 %s, 총 %s스텝\n" "${eps:-?}" "${total:-?}"
    fi
    printf "    진행   마지막 에피소드 %s\n" "${last_ep:-없음}"
    [[ -n "$models" ]] && printf "    모델   %s\n" "$models"

    if [[ -f "$res" ]]; then
        printf "    결과   %s\n" "$(cat "$res")"
    fi

    sup_log="${d}sup/supervisor.log"
    [[ -f "$sup_log" ]] && printf "    감독   %s\n" "$(tail -1 "$sup_log")"

    # 훈련 로그의 마지막 의미 있는 줄. SUMO 경고는 쉼 없이 흐르므로 걸러낸다.
    trn_log="${d}sup/train.log"
    if [[ -f "$trn_log" ]]; then
        line=$(grep -iv "warning\|quitting\|^\s*$" "$trn_log" | tail -1 | cut -c1-100)
        [[ -n "$line" ]] && printf "    로그   %s\n" "$line"
        printf "    갱신   %s (%s bytes)\n" \
            "$(date -r "$trn_log" '+%F %T')" "$(stat -c%s "$trn_log")"
    fi
    echo
done
[[ $found -eq 0 ]] && echo "  (runs/ 아래에 실행 디렉터리가 없다)"

echo "=============================================================="
