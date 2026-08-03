# RUN_COMMANDS.md — Scenario 실행 명령어 (사용자 직접 실행용)

> **2026-05-06 13:32 갱신**: 사용자 요청 — "복붙이 안되니 파일로 전달해줘" 반영.
> RUN_COMMANDS.md 의 모든 명령을 한 곳에 모은 **`quickstart.sh`** 추가.
> 사용자는 아래 §0 만 보고 그대로 실행하면 됩니다 (복붙 0줄, 키워드 1개만).

---

## 0. TL;DR — 복붙 없이 한 줄로 실행 (★ 여기만 봐도 됨)

새 셸 1개를 열고, 한 번에 한 줄씩 입력:

```bash
cd /home/imnyj/papers/paper3/paper/experiment

# (1) 환경 점검 (SUMO / libsumo / sumolib / 경로)
bash quickstart.sh check

# (2) 5분 안에 1 run 이 끝나는지 확인 (반드시 먼저 실행)
bash quickstart.sh smoke

# (3) 시나리오 실행 — 둘 중 택일
bash quickstart.sh all          # ① C→D→E→B→A 순차 (foreground, 화면에 진행 표시)
# 또는 시나리오별 백그라운드:
bash quickstart.sh C            # ② 백그라운드. 다른 시나리오는 추가로 D, E, B, A 차례로
bash quickstart.sh status       #    진행 상황 1번에 확인
bash quickstart.sh tail C       #    실시간 로그 보기 (Ctrl-C 로 종료)
bash quickstart.sh stop         #    멈추고 싶을 때
```

`quickstart.sh` 의 명령 목록:

| 명령 | 동작 |
|---|---|
| `bash quickstart.sh check`   | SUMO·libsumo·sumolib·경로 자가진단 (1~3초) |
| `bash quickstart.sh smoke`   | 1 run 만 돌려 60초~5분 안에 결과 출력되는지 확인 |
| `bash quickstart.sh A`       | 시나리오 A 백그라운드 실행, `data/run_A.log` 에 로그 |
| `bash quickstart.sh B` ~ `E` | 시나리오 B~E 백그라운드 실행 |
| `bash quickstart.sh all`     | 빠른 순서 (C→D→E→B→A) foreground 순차 실행 |
| `bash quickstart.sh status`  | 모든 시나리오 진행도 + 실행 중인 프로세스 확인 |
| `bash quickstart.sh tail X`  | 시나리오 X (A,B,C,D,E) 의 실시간 로그 |
| `bash quickstart.sh stop`    | 실행 중인 모든 `run_scenario.py` 종료 |

> 💡 어떤 시나리오든 중단되면 같은 명령으로 다시 실행 시 자동 resume (이미 끝난 (algo, density, ε, Γ, τ, seed) 조합은 건너뜀).
> 💡 `quickstart.sh` 가 곧 RUN_COMMANDS.md 의 모든 §1~§9 명령을 포함합니다. 아래 섹션은 참고/디버깅용입니다.

---

## 0a. 변경 요약 (Round 4 대비)

| 항목 | Round 4 | Round 5 (현재) |
|---|---|---|
| 실행 인터프리터 | `python` | **`python3 -u`** |
| CSV 저장 시점 | 시나리오 끝 1회 | **매 run 즉시 (line-buffered + fsync)** |
| 중단 후 재시작 | 처음부터 다시 | **자동 resume** (이미 저장된 (algo, density, eps, gamma, tau, seed) 조합 skip) |
| RILP solver | PuLP/CBC ILP per vehicle per window | **정렬 (knapsack 해석적 최적해, 결과 동일)** |
| 진행 표시 | 20 run마다 1줄 | **매 run 마다 1줄 + ETA** |
| 출력 경로 | 혼용 (cwd 의존) | **절대경로 일관** |
| Smoke test | 없음 | **`scenario S_smoke` 5분 검증 명령** |

---

## 1. 환경 준비 (사용자 머신, 1회만)

```bash
# (1) SUMO 설치 확인 — 1.18 이상 권장
sumo --version

# (2) SUMO_HOME 환경변수 (자신의 환경에 맞게 조정)
export SUMO_HOME=/usr/share/sumo
export PYTHONPATH=$SUMO_HOME/tools:$PYTHONPATH

# (3) libsumo / sumolib import 가능 여부 확인
python3 -c "import libsumo; print('libsumo OK:', libsumo.__version__ if hasattr(libsumo,'__version__') else 'ok')"
python3 -c "import sumolib; print('sumolib OK')"

# (4) SumoNetSim1.1.6 의 SUMO 설정 파일 존재 확인
ls /home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/generated.sumocfg
ls /home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/rsu.poi.xml

# (5) 출력 폴더 보장 (비어 있어야 정상)
mkdir -p /home/imnyj/papers/paper3/paper/data
ls /home/imnyj/papers/paper3/paper/data
```

> ⚠️  사용자 환경에는 `python` 명령이 없습니다 (Ubuntu 22.04+ 기본). 모든 명령은 **`python3`** 를 사용합니다. `tee` 로 로그를 남길 때 `python3 -u` 로 unbuffered 출력해야 실시간으로 보입니다.

---

## 2. Smoke-test (5분 이내 첫 CSV 줄 확인 — 반드시 먼저 실행)

본격 실행 전, sim_core.py + algorithms.py + libsumo + .rou.xml 이 정상 연결되는지 1개 run 으로 확인합니다.

```bash
cd /home/imnyj/papers/paper3/paper/experiment/code

# (a) import 자가 진단
python3 sim_core.py
# 기대: "Import OK. CIoVSim class loaded." + libsumo 버전 출력

# (b) 1개 시나리오 1개 seed 1개 알고리즘 (약 60초 ~ 5분)
python3 -u <<'PY'
import sys, time
sys.path.insert(0, '.')
from sim_core import CIoVSim
from algorithms import ALGORITHMS
t0 = time.time()
sim = CIoVSim(seed=42, density_per_cell=5,
              prediction_error_pct=10, gamma=2.0, tau_max=5,
              duration_steps=1800, warmup_steps=300)
m = sim.run(ALGORITHMS['RILP-Greedy'])
print('Smoke OK:', m, 'in', round(time.time()-t0,1), 's')
PY
```

**기대 출력**: `Smoke OK: {'CHR': 0.xx, 'CDSR': 0.xx, ...} in 60.0 s` 정도.

**실패 시** 가장 흔한 원인:
- `Command 'python' not found` → `python3` 로 바꿨는지 재확인.
- `ImportError: libsumo` → §1-(2),(3) 환경변수 재설정.
- `FileNotFoundError: generated.sumocfg` → §1-(4) 경로 확인. 필요 시 `CIoVSim(sumo_dir='절대경로')` 로 직접 전달.
- 60초 넘게 무반응 → SUMO 가 백그라운드에서 도는 중. 로그가 안 보이는 건 stdout 버퍼링 때문이 아닌, smoke-test 는 단일 run 끝에서만 출력하기 때문임. 정상.

---

## 3. 시나리오별 실행 명령 (run-by-run 즉시 CSV 저장)

각 명령은 시나리오 1개를 끝까지 실행하고 `data/` 에 다음을 생성합니다:
- `<S>_full.csv` ← **매 run 끝나는 즉시 한 줄씩 추가됨**. 중간에 끊겨도 이미 쓰인 행은 보존.
- `<S>_CHR.csv`, `<S>_CDSR.csv`, `<S>_AoI_violation_rate.csv`, `<S>_PCO.csv`, `<S>_RLBI.csv` ← 시나리오 끝에서 full 로부터 파생 생성.

> 📌 **재시작 보장**: 어떤 이유로든 중단되었다가 같은 명령을 다시 실행하면, `<S>_full.csv` 에 이미 있는 (algorithm, density, pred_error_pct, gamma, tau_max, seed) 조합은 건너뛰고 남은 조합만 실행합니다. 안전하게 Ctrl-C / 재부팅 후 재시도 가능.

### Scenario A — Vehicle Density Sweep (저~중밀도)
```bash
cd /home/imnyj/papers/paper3/paper/experiment
nohup python3 -u code/run_scenario.py \
    --scenario A \
    --output_dir /home/imnyj/papers/paper3/paper/data \
    > /home/imnyj/papers/paper3/paper/data/run_A.log 2>&1 &
echo "Scenario A pid=$!"
```
- grid: density ∈ {1,2,3,4,5} × ε ∈ {0,10,20,30}% × Γ ∈ {0,1,2,3} × τ=5 × 알고리즘 8 × seed 10
- 총 run 수: 5 × 4 × 1 × 4 × 8 × 10 = **6,400 runs**

### Scenario B — High Density Sweep (Greedy 중심)
```bash
cd /home/imnyj/papers/paper3/paper/experiment
nohup python3 -u code/run_scenario.py \
    --scenario B \
    --output_dir /home/imnyj/papers/paper3/paper/data \
    > /home/imnyj/papers/paper3/paper/data/run_B.log 2>&1 &
echo "Scenario B pid=$!"
```
- 총 run 수: 6 × 4 × 1 × 1 × 7 × 10 = **1,680 runs**

### Scenario C — Prediction Error Sweep
```bash
cd /home/imnyj/papers/paper3/paper/experiment
nohup python3 -u code/run_scenario.py \
    --scenario C \
    --output_dir /home/imnyj/papers/paper3/paper/data \
    > /home/imnyj/papers/paper3/paper/data/run_C.log 2>&1 &
echo "Scenario C pid=$!"
```
- 총 run 수: 1 × 7 × 1 × 1 × 8 × 10 = **560 runs**

### Scenario D — τ_max Sweep
```bash
cd /home/imnyj/papers/paper3/paper/experiment
nohup python3 -u code/run_scenario.py \
    --scenario D \
    --output_dir /home/imnyj/papers/paper3/paper/data \
    > /home/imnyj/papers/paper3/paper/data/run_D.log 2>&1 &
echo "Scenario D pid=$!"
```
- 총 run 수: 1 × 1 × 6 × 1 × 8 × 10 = **480 runs**

### Scenario E — Γ Sweep ★ 핵심 figure
```bash
cd /home/imnyj/papers/paper3/paper/experiment
nohup python3 -u code/run_scenario.py \
    --scenario E \
    --output_dir /home/imnyj/papers/paper3/paper/data \
    > /home/imnyj/papers/paper3/paper/data/run_E.log 2>&1 &
echo "Scenario E pid=$!"
```
- 총 run 수: 1 × 1 × 1 × 7 × 8 × 10 = **560 runs**

### 권장: 큰 시나리오부터 백그라운드, 빠른 시나리오 먼저 (선택)
```bash
# C → D → E (빠름) 먼저, 그 다음 B, 마지막에 A
cd /home/imnyj/papers/paper3/paper/experiment
DATA=/home/imnyj/papers/paper3/paper/data
for S in C D E B A; do
  echo "=== Starting Scenario $S ==="
  python3 -u code/run_scenario.py --scenario $S --output_dir $DATA \
      2>&1 | tee $DATA/run_${S}.log
done
```

> 동시에 5개 시나리오를 병렬로 돌리지 마십시오. 각각 SUMO 인스턴스를 띄우므로 충돌·메모리 부족 가능. 한 번에 1개 또는 (16GB+ RAM 환경에서) 최대 2개까지만.

---

## 4. 진행 모니터링 (실행 중 다른 터미널에서)

```bash
DATA=/home/imnyj/papers/paper3/paper/data

# (a) 실시간 stdout 보기 (가장 유용)
tail -f $DATA/run_A.log

# (b) 지금까지 저장된 run 수 (헤더 1줄 빼기)
echo "A: $(($(wc -l < $DATA/A_full.csv) - 1)) / 6400"
echo "B: $(($(wc -l < $DATA/B_full.csv) - 1)) / 1680"
echo "C: $(($(wc -l < $DATA/C_full.csv) - 1)) / 560"
echo "D: $(($(wc -l < $DATA/D_full.csv) - 1)) / 480"
echo "E: $(($(wc -l < $DATA/E_full.csv) - 1)) / 560"

# (c) 마지막 5줄로 어떤 grid 가 진행 중인지 확인
tail -n 5 $DATA/A_full.csv

# (d) python3 프로세스 살아 있는지 확인
ps -ef | grep run_scenario | grep -v grep
```

만약 `*_full.csv` 파일이 생성되었는데 1시간 넘게 행이 늘지 않으면 시뮬이 멈췄을 가능성. log 파일 마지막을 확인하고, 필요 시 `kill <pid>` 후 같은 명령 재실행 (자동 resume).

---

## 5. 산출물 검증 체크리스트

실행 종료 시 `paper/data/` 에 다음 파일이 있어야 합니다 (시나리오당 6개 × 5 = 30개):

| Scenario | 예상 row 수 (header 제외) |
|---|---|
| A | 6,400 |
| B | 1,680 |
| C |   560 |
| D |   480 |
| E |   560 |
| **합계** | **9,680** |

CSV 헤더: `scenario,algorithm,density,pred_error_pct,gamma,tau_max,seed,<metric>`

---

## 6. 사용자 실행 후 다음 액션

1. `paper/data/` 에 30개 CSV 가 다 차고 합 9,680 행 확인.
2. Commander 호출 → **Reviewer Validator 모드** 로 무결성 검증:
   - "Reviewer, Validator 모드로 paper/data/ 의 30개 CSV 를 검증하고 validation_report.json 을 생성하라."
3. Validator PASS → Experimenter Stage 3 (visualize).
4. Validator FAIL → Experimenter Stage 2 패치 후 사용자 재실행 (resume 모드 자동 동작).

---

## 7. 알고리즘 목록 (변경 없음)

`code/algorithms.py::ALGORITHMS` 에 등록된 8개:

| 코드명 | 역할 | 비고 |
|---|---|---|
| `RILP`         | Proposed exact      | **2026-05-06 패치**: PuLP/CBC 제거, knapsack 해석해 (정렬). 결과는 ILP 와 동일. |
| `RILP-Greedy`  | Proposed heuristic  | (1−1/e) bound greedy |
| `Nam2023b`     | Baseline            | Set Ranking deterministic |
| `Nam2025`      | Baseline            | Storage-aware (Γ=0) |
| `Youn2026`     | Baseline            | SAC-RL simulated policy |
| `V2I-Base`     | Baseline            | V2I 단순 베이스 |
| `V2V-Base`     | Baseline            | V2V 단순 베이스 |
| `Random-K`     | Baseline            | Random caching |

---

## 8. 트러블슈팅 (Round 5 추가)

| 증상 | 가능 원인 | 조치 |
|---|---|---|
| `Command 'python' not found` | `python` 심볼릭 링크 없음 (Ubuntu 22.04+) | **모든 명령에서 `python3` 사용** (이번 갱신으로 적용됨) |
| 로그가 한 줄도 안 보임 | stdout 버퍼링 (이전 Round 4 의 핵심 원인) | **`python3 -u`** 사용 + `tee` 또는 `>` 리디렉션. 이번 갱신으로 `flush=True` + line-buffered 적용됨. |
| `*_full.csv` 가 끝에서야 생기는 줄 알았다 | Round 4 의 batch-write 정책 (이번 라운드의 핵심 원인) | **이번 라운드부터 매 run 즉시 fsync**. 첫 run 종료 ~ 60s 후 첫 줄 보임. |
| 한 run 이 너무 오래 걸림 | 이전엔 RILP CBC 호출 ~수십 분 | **이번 라운드부터 RILP 정렬 기반**. 한 run 수 초~수십 초. |
| `libsumo` 충돌 / `Connection closed` | 동시 실행 SUMO 다중 인스턴스 | 한 번에 시나리오 1~2개만. |
| `nohup` 으로 띄웠는데 종료되어 있음 | 부모 셸 끊어짐 | `nohup ... &` 사용 + `disown` 권장. 또는 `screen`/`tmux` 안에서 실행. |
| 진행이 멈춘 듯함 (1시간+ 행 증가 0) | SUMO 단일 step hang | `kill <pid>` 후 동일 명령 재실행 → 자동 resume. |

---

## 9. 빠른 진단 한 줄 (지금 시뮬이 살아있는지)

```bash
DATA=/home/imnyj/papers/paper3/paper/data
ls -la $DATA && wc -l $DATA/*_full.csv 2>/dev/null && \
  ps -ef | grep run_scenario | grep -v grep
```

이 한 줄이 출력하는 것:
1. `paper/data/` 디렉터리 내 파일 목록 (CSV 들이 만들어졌는지)
2. 각 `_full.csv` 의 행 수 (run 진행도)
3. 살아있는 `run_scenario.py` 프로세스 (있다면 `pid`, 없다면 시뮬 멈춤)

— 끝 —
