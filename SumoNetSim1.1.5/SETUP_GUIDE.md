# SumoNetSim 데이터 수집 환경 설치 가이드

> 다른 컴퓨터에서 병렬 데이터 수집을 위한 환경 구성 절차  
> 기준 버전: Python 3.10–3.12, eclipse-sumo 1.26.0

---

## 0. 사전 요구사항

- **OS**: Windows 10/11 또는 Ubuntu 22.04 (WSL2 포함)
- **Python**: 3.10 이상 (3.12 권장)
  - Windows: [https://www.python.org/downloads/](https://www.python.org/downloads/) 에서 다운로드
  - Linux/WSL: `sudo apt install python3 python3-venv python3-pip`
- **Git**: 프로젝트 파일 복사용 (또는 압축파일 직접 복사)

---

## 1. 프로젝트 파일 복사

다른 컴퓨터로 `SumoNetSim1.1.5` 폴더 전체를 복사한다.  
(USB, 네트워크 공유, 또는 압축 후 전송)

```
SumoNetSim1.1.5/
├── dataset_scenario.py     ← 시뮬레이션 메인 스크립트
├── watchdog-runner.py      ← 자동 반복 실행 GUI
├── src/
│   ├── NetSim.py
│   ├── Communications.py
│   ├── model.py
│   └── sumo/               ← SUMO 네트워크 파일 (.xml, .sumocfg)
└── data/                   ← 수집된 CSV 저장 위치 (없으면 자동 생성)
```

---

## 2. Python 가상환경 생성

### Windows (CMD 또는 PowerShell)

```cmd
cd SumoNetSim1.1.5
python -m venv venv
venv\Scripts\activate
python -m pip install -U pip
```

### Linux / WSL

```bash
cd SumoNetSim1.1.5
python3 -m venv venv
source venv/bin/activate
pip install -U pip
```

---

## 3. 패키지 설치

### 3-1. SUMO + libsumo (핵심)

```bash
pip install eclipse-sumo==1.26.0
```

> `eclipse-sumo`를 pip으로 설치하면 `sumo`, `libsumo`, `sumolib`, `traci`가 함께 설치된다.  
> 별도로 SUMO GUI 프로그램을 설치할 필요 없음.

설치 확인:
```bash
python -c "import libsumo; print('libsumo OK')"
sumo --version
```

### 3-2. 시뮬레이션 의존 패키지

```bash
pip install numpy pandas
```

### 3-3. (선택) watchdog-runner GUI 실행 시

tkinter는 Python 표준 라이브러리에 포함되어 있으나, Linux에서 누락된 경우:

```bash
# Ubuntu / WSL
sudo apt install python3-tk
```

Windows는 Python 설치 시 자동 포함.

---

## 4. watchdog-runner.py 경로 수정

`watchdog-runner.py` 상단의 두 상수를 현재 컴퓨터 환경에 맞게 수정한다.

```python
# watchdog-runner.py 7~8번째 줄
TARGET_FILE = "SumoNetSim1.1.5\\dataset_scenario.py"   # Windows 경로
PYTHON_EXE  = "C:/Users/user/python/venv/Scripts/python.exe"  # 가상환경 python 경로
```

#### Windows 수정 예시

```python
TARGET_FILE = "SumoNetSim1.1.5\\dataset_scenario.py"
PYTHON_EXE  = r"C:\Users\<사용자명>\SumoNetSim1.1.5\venv\Scripts\python.exe"
```

#### Linux / WSL 수정 예시

```python
TARGET_FILE = "dataset_scenario.py"
PYTHON_EXE  = "/home/<사용자명>/SumoNetSim1.1.5/venv/bin/python3"
```

> `TARGET_FILE` 경로는 watchdog-runner.py를 실행하는 **작업 디렉토리 기준** 상대경로다.  
> watchdog-runner.py를 `SumoNetSim1.1.5/` 안에서 실행하면 `"dataset_scenario.py"`만 써도 된다.

---

## 5. 시뮬레이션 실행

`watchdog-runner.py`는 OS를 자동 감지하여 동작 방식을 결정한다.

### Linux / WSL (CLI 모드 — 자동 선택)

```bash
# myenv 활성화 후, SumoNetSim1.1.5/ 내에서
source ~/myenv/bin/activate
python watchdog-runner.py
```

터미널에서 로그와 함께 아래 형식의 상태 라인이 1초마다 갱신된다:

```
[2026-04-10 14:00:00][INFO] ▶ Episode 3/30 시작
  Ep  3/30 (10.0%)  Step  840/3600 (23.3%)  |  소요 00:03:12  남은 01:44:21  완료예정 04/10 15:47:33  [1187s/ep]
```

- **Ctrl+C**: 즉시 종료 (완료된 에피소드까지만 데이터 보존)
- **`touch exit.flag`**: 현재 에피소드 완료 후 정상 종료

### Windows (GUI 모드 — 자동 선택)

```cmd
venv\Scripts\activate
python watchdog-runner.py
```

Run 버튼 클릭 → 30 에피소드 자동 반복 수행.

### 직접 단일 실행 (수동)

```bash
# 가상환경 활성화 후, SumoNetSim1.1.5/ 내에서
python dataset_scenario.py
```

---

## 6. 수집된 데이터 병합 방법

각 컴퓨터에서 수집된 `data/rsu_NXX.csv` 파일들을 하나의 컴퓨터로 모은 뒤 합산한다.

### 방법 A: bash (Linux / WSL)

```bash
# 컴퓨터 B의 data/ 폴더를 컴퓨터 A의 data_B/ 로 복사한 후
cd /path/to/SumoNetSim1.1.5

for f in data_B/rsu_*.csv; do
    rsu=$(basename "$f")
    if [ -f "data/$rsu" ]; then
        # 헤더 제거 후 append
        tail -n +2 "$f" >> "data/$rsu"
    else
        cp "$f" "data/$rsu"
    fi
done
echo "병합 완료"
```

### 방법 B: Python

```python
import pandas as pd
from pathlib import Path

data_a = Path("data")          # 컴퓨터 A 원본
data_b = Path("data_B")        # 컴퓨터 B에서 복사한 폴더

for f_b in data_b.glob("rsu_*.csv"):
    f_a = data_a / f_b.name
    df_b = pd.read_csv(f_b)
    if f_a.exists():
        df_a = pd.read_csv(f_a)
        pd.concat([df_a, df_b], ignore_index=True).to_csv(f_a, index=False)
    else:
        df_b.to_csv(f_a, index=False)

print("병합 완료")
```

---

## 7. 에피소드 seed 다양성 확인

`NetSim.py`의 수정으로 각 에피소드마다 다른 SUMO seed가 사용된다.  
실행 로그에서 아래와 같이 확인 가능:

```
Episode 1/1
  [seed=1739284021]
```

두 컴퓨터가 독립적으로 랜덤 seed를 생성하므로 별도 설정 없이 다양한 교통 패턴이 수집된다.

---

## 8. 패키지 버전 요약

| 패키지 | 버전 | 용도 |
|--------|------|------|
| eclipse-sumo | 1.26.0 | SUMO 시뮬레이터 (libsumo/sumolib/traci 포함) |
| numpy | 2.4.x 이상 | 수치 연산 |
| pandas | 3.0.x 이상 | CSV 입출력 |
| python-tk | (시스템) | watchdog-runner GUI |

> 데이터 수집 전용 환경이므로 학습용 패키지 (torch, scikit-learn 등)는 **설치 불필요**.

---

## 빠른 설치 요약 (복사용)

```bash
# 1. 가상환경
python -m venv venv && source venv/bin/activate   # Linux
# python -m venv venv && venv\Scripts\activate    # Windows

# 2. 패키지
pip install -U pip
pip install eclipse-sumo==1.26.0 numpy pandas

# 3. 실행
python watchdog-runner.py
```
