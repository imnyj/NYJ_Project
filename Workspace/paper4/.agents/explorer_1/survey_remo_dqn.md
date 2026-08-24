# REMO-DQN 훈련 및 시스템 현황 종합 조사 보고서 (Explorer 1)

- **작성일시**: 2026-08-21T14:03:00+09:00
- **조사자**: Explorer 1 (탐색 에이전트)
- **대상 프로젝트**: paper4 (V2X 혼잡 제어 REMO-DQN 프로젝트)

---

## 1. 프로세스 및 시스템 자원 현황 점검

### 1.1 PID 97001 및 훈련 프로세스 상태
- **PID 97001 상태**: **종료됨 (Terminated / Dead)**
  - `ps aux | grep 97001` 및 `ps -ef | grep python` 확인 결과, PID 97001을 포함한 일체의 강화학습/SUMO 시뮬레이션 프로세스가 현재 실행 중이지 않음.
  - 로그 파일 최종 수정 시각(`2026-08-21 12:42`) 기준으로 에피소드 9 완료 후 종료된 것으로 파악됨.
- **백그라운드 프로세스**: OS 기본 프로세스 외 활성 시뮬레이션 태스크 없음.

### 1.2 GPU / CPU / 메모리 자원 현황
- **GPU (NVIDIA GeForce RTX 3090 x 4)**:
  - GPU 0: VRAM 15MiB / 24576MiB, GPU-Util 0%, 온도 42°C
  - GPU 1: VRAM 15MiB / 24576MiB, GPU-Util 0%, 온도 45°C
  - GPU 2: VRAM 15MiB / 24576MiB, GPU-Util 0%, 온도 47°C
  - GPU 3: VRAM 38MiB / 24576MiB, GPU-Util 0%, 온도 46°C
  - **상태**: 4장의 GPU 모두 완전한 유휴(Idle) 상태로 즉시 대규모 병렬/훈련 작업 투입 가능.
- **CPU**:
  - 모델: Intel(R) Core(TM) i9-10900X CPU @ 3.70GHz (20 logical threads)
  - 부하: Load average 2.50, 0.89, 0.77 (안정적 유휴 상태 진입 중)
- **시스템 메모리 (RAM)**:
  - 전체: 125 GiB, 사용 중: 5.8 GiB, 여유 공간(Available): 119 GiB

---

## 2. REMO-DQN 훈련 및 파일 상태 파악

### 2.1 훈련 로그 파일 분석
- **대상 파일**:
  - `code/resnet_train_log.csv` (885 bytes, 최종 수정: 2026-08-21 12:42)
  - `data/models/REMO-DQN_convergence.csv` (885 bytes, 최종 수정: 2026-08-21 12:42)
- **기록 상태**: **총 9개 에피소드 (18,000 steps)** 기록됨 (100개 에피소드 중 9% 완료)
- **에피소드별 진행 데이터 요약**:
  | Episode | Global Step | Reward | AoI Mean (ms) | CBR Mean | PDR Mean (%) | Loss | Epsilon | Density |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
  | 1 | 2,000 | -332,271.25 | 553.022 | 0.0822 | 63.82 | 0.0951 | 0.9500 | 100 |
  | 2 | 4,000 | -339,056.51 | 566.339 | 0.0823 | 63.69 | 0.0011 | 0.9025 | 100 |
  | 3 | 6,000 | -310,278.86 | 548.671 | 0.0811 | 64.49 | 0.0010 | 0.8574 | 100 |
  | 4 | 8,000 | -191,520.03 | 551.551 | 0.0662 | 63.12 | 0.0012 | 0.8145 | 30 |
  | 5 | 10,000 | -309,827.23 | 528.302 | 0.0803 | 67.11 | 0.0033 | 0.7738 | 100 |
  | 6 | 12,000 | -309,456.33 | 542.869 | 0.0797 | 65.03 | 0.0046 | 0.7351 | 50 |
  | 7 | 14,000 | -180,119.23 | 464.120 | 0.0652 | 69.44 | 0.0028 | 0.6983 | 30 |
  | 8 | 16,000 | -300,724.04 | 594.292 | 0.0796 | 63.20 | 0.0468 | 0.6634 | 100 |
  | 9 | 18,000 | -294,386.35 | 557.837 | 0.0793 | 65.03 | 0.0081 | 0.6302 | 100 |

### 2.2 가중치 파일 상태
- **파일 경로**:
  - `data/models/resnet_moe_dqn.pth` (533,925 bytes, 최종 수정: Aug 21 01:59)
  - `data/models/REMO-DQN.pth` (533,661 bytes, 최종 수정: Aug 21 01:59)
- **상태 분석**:
  - `code/train_resnet.py`의 구현 구조상, 100개 에피소드 루프가 완전히 종료된 후 최종 행(Line 151)에서 가중치 저장이 수행됨.
  - 따라서 현재 디렉토리에 존재하는 `.pth` 가중치는 PID 97001 이전의 선행 실행 결과 파일이며, PID 97001(Ep 1~9)의 가중치는 저장되지 못하고 종료됨.

### 2.3 타 13개 베이스라인 모델 상태 (대조군 현황)
- `data/models/` 내 13개 베이스라인 모델은 **이미 100 에피소드 (101행) 완주 및 가중치 저장이 완료**되어 있음:
  - `ActorCritic`, `DDPG`, `DecisionTransformer`, `DoubleDQN`, `DuelingDQN`, `MAPPO`, `MoEDQN`, `PPO`, `QLearning`, `SAC`, `SARSA`, `TD3`, `VanillaDQN`
  - 각 모델별 `*_convergence.csv` 파일이 정확히 101행(헤더 포함)으로 준비되어 있음.

---

## 3. REMO-DQN 훈련 스크립트 상세 분석

### 3.1 코드 구조 및 설정
- **훈련 스크립트**: `code/train_resnet.py`
- **에이전트 구현**: `code/resnet_moe_agent.py` (`ResNetMoEAgent`, `ResNetMoEDQN`)
  - **상태 공간 (State)**: 5차원 관측치 ($dim=5$)
  - **특징 추출기 (ResNet Feature Extractor)**: 2개의 ResidualBlock (Hidden Dim 128)
  - **전문가 네트워크 (MoE)**: 3개의 `DuelingExpert` (각각 Value Stream과 Advantage Stream으로 분리)
  - **게이팅 네트워크 (Gating Network)**: Detached feature를 입력받는 Softmax 라우팅 구조 ($Linear \to ReLU \to Linear \to Softmax$)
  - **액션 공간 (Action Space)**: 24차원 ($4 \times 6 = 24$, 전송 주기 4단계 $\times$ 전송 전력 6단계 $[-5, 0, 5, 10, 15, 20]$ dBm)
  - **학습 메커니즘**: Double Dueling DQN, Target Network 매 에피소드 업데이트, Replay Buffer 크기 100,000, 배치 크기 64
- **시뮬레이션 환경 연동**: `code/sim_engine.py` (`SimulationRunner`, `urban_grid` 시나리오)
  - 에피소드당 스텝 수: `duration_steps=2000` (100 에피소드 시 총 200,000 스텝)
  - 동적 차량 밀도 (Random Density): 매 에피소드마다 `random.choice([30, 50, 100])` 적용
  - Epsilon 감쇠 스케줄: `epsilon_decay=0.95`, `min_epsilon=0.01` ($1.0 \times 0.95^{100} \approx 0.0059 \to 0.01$ 클리핑)
- **실행 속도 특성**:
  - 에피소드 1회당 약 70~80분 소요 (SUMO 물리 시뮬레이션 및 2000 스텝 세밀 제어)
  - 100 에피소드 완주 시 총 약 110~130시간 소요 추산.

---

## 4. 91~100 에피소드 수렴 여부 검증 요구사항

### 4.1 수렴 검증 스크립트 분석 (`code/verify_remo_convergence.py`)
- **검증 대상 데이터**: `data/models/REMO-DQN_convergence.csv`
- **필수 전제 조건**: `total_episodes >= 20` (초기 10 에피소드 + 최종 10 에피소드 비교를 위해 최소 20 에피소드 이상 필요, 목표 기준 100 에피소드)
- **핵심 수렴 평가 지표**:
  1. **Policy Improvement (보상 증가)**:
     $$\text{Mean Reward (Ep 91\sim 100)} > \text{Mean Reward (Ep 1\sim 10)}$$
  2. **Exploration Convergence (Epsilon 수렴)**:
     $$\text{Final Epsilon} \le 0.015$$
  3. **Statistical Significance (통계적 유의성)**:
     - Welch's One-tailed t-test 기준 $p\text{-value} < 0.05$ 또는 명확한 보상 상승 입증
- **현 상태 평가**:
  - 현재 9개 에피소드만 기록되어 있어 `verify_remo_convergence.py` 실행 시 `Total episodes (9) is less than required evaluation window (20)` 오류로 검증 불가.
  - 수렴 검증을 통과하고 논문용 시각화 및 비교 분석을 완성하기 위해서는 REMO-DQN의 100 에피소드 완주가 반드시 필요함.

---

## 5. 결론 및 후속 작업 제언

1. **상황 진단**:
   - 오리지널 요청에 언급된 PID 97001은 9개 에피소드(18,000 스텝) 완료 후 종료된 상태임.
   - 타 13개 베이스라인 모델(100 에피소드 데이터 및 가중치)은 이미 정상 준비되어 있으므로, 전체 파이프라인의 병목은 REMO-DQN의 100 에피소드 완료 및 수렴 검증임.
2. **권장 대응 조치**:
   - **체크포인트 주기적 저장 보강**: `train_resnet.py`에서 매 에피소드 또는 5/10 에피소드마다 `.pth` 가중치를 중간 저장하도록 보강하여 예기치 않은 중단 시 복구 가능하도록 설계.
   - **REMO-DQN 100 에피소드 훈련 재개/완료**: 백그라운드로 훈련을 재개하고, 완료 후 `verify_remo_convergence.py`를 실행하여 수렴성 입증.
   - **자원 활용**: 유휴 상태인 4장의 RTX 3090 및 20스레드 CPU 자원을 활용하여 시뮬레이션 가속화 검토.
