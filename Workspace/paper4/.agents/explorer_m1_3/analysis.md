# Checkpoint & Convergence Log Analysis Report (M1 Explorer 3)

**Investigator**: Paper4 M1 Explorer 3  
**Date**: 2026-08-11  
**Target Directory**: `/home/imnyj/Workspace/paper4/data/models/`  
**Working Directory**: `/home/imnyj/Workspace/paper4/.agents/explorer_m1_3`  

---

## 1. Executive Summary

본 보고서는 V2X 환경 하이브리드 DRL 기반 혼잡 제어(ResNet-MoE-Dueling DQL, REMO-DQN) 및 13종 RL 비교군 모델 총 14개 모델의 체크포인트 가중치 파일(`.pth`/`.pkl`) 및 수렴 로그(`*_convergence.csv`) 현황을 전수 조사하고, M1 이행을 위한 모델 훈련 완료 검증 기준을 수립한 결과를 담고 있습니다.

### 핵심 조사 결과
1. **Convergence CSV 현황 (`/home/imnyj/Workspace/paper4/data/models/`)**:
   - 총 14개 RL 모델 중 **4개 모델만 수렴 로그가 존재**하며, 모두 목표 100 에피소드에 미달한 상태입니다.
     - `QLearning`: 에피소드 63 완료 (진행률 63%)
     - `SARSA`: 에피소드 63 완료 (진행률 63%)
     - `VanillaDQN`: 에피소드 50 완료 (진행률 50%)
     - `ActorCritic`: 에피소드 34 완료 (진행률 34%)
   - 나머지 **10개 모델** (`DoubleDQN`, `DuelingDQN`, `DDPG`, `PPO`, `SAC`, `TD3`, `DecisionTransformer`, `MAPPO`, `MoEDQN`, `REMO-DQN`)은 수렴 로그 파일이 **미존재(MISSING)** 상태입니다.

2. **모델 가중치 파일 현황 (`.pth` / `.pkl`)**:
   - 표준 저장 위치인 `data/models/`에는 14개 모델의 **가중치 파일이 전무(0개)**합니다. (훈련이 ep 100까지 완료되지 않아 final save가 수행되지 않음)
   - 레거시 개별 훈련 디렉토리인 `code/`에는 14개 모델의 가중치가 존재하나, `DuelingDQN` 가중치는 Key Mismatch 오류로 로드 불가하며, 나머지 13개는 정상 로드가 가능함을 확인했습니다. (다만 M1 재개/훈련을 통해 `data/models/` 디렉토리에 정합성 있는 가중치가 생성되어야 함)

3. **14개 모델 훈련 완료 검증 기준**:
   - 파일 존재, 100 에피소드 도달, Null/NaN/Inf 무결성, 가중치 로드 성공, 수렴 및 물리 지표 범위를 포함한 **5단계 게이트 검증 체계**를 확립하였습니다.

---

## 2. Convergence Log (`*_convergence.csv`) Detailed Audit

`data/models/` 디렉토리 내에 위치해야 하는 14개 RL 모델의 수렴 로그 파일 전수 조사 결과입니다.

| # | Model Name | Log File Path | File Found | Recorded Rows | Last Ep | Missing/Null/Inf | Progress Status |
|---|------------|---------------|------------|---------------|---------|------------------|-----------------|
| 1 | QLearning | `data/models/QLearning_convergence.csv` | **YES** | 63 | **63** | 0 / 0 / 0 | 63/100 (Incomplete) |
| 2 | SARSA | `data/models/SARSA_convergence.csv` | **YES** | 63 | **63** | 0 / 0 / 0 | 63/100 (Incomplete) |
| 3 | ActorCritic | `data/models/ActorCritic_convergence.csv` | **YES** | 34 | **34** | 0 / 0 / 0 | 34/100 (Incomplete) |
| 4 | VanillaDQN | `data/models/VanillaDQN_convergence.csv` | **YES** | 50 | **50** | 0 / 0 / 0 | 50/100 (Incomplete) |
| 5 | DoubleDQN | `data/models/DoubleDQN_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 6 | DuelingDQN | `data/models/DuelingDQN_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 7 | DDPG | `data/models/DDPG_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 8 | PPO | `data/models/PPO_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 9 | SAC | `data/models/SAC_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 10 | TD3 | `data/models/TD3_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 11 | DecisionTransformer | `data/models/DecisionTransformer_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 12 | MAPPO | `data/models/MAPPO_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 13 | MoEDQN | `data/models/MoEDQN_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |
| 14 | REMO-DQN | `data/models/REMO-DQN_convergence.csv` | **NO** | 0 | **N/A (0)** | N/A | 0/100 (Missing) |

### 4개 기존 수렴 로그의 세부 통계 (Summary Statistics)
- **QLearning** (ep 1~63): Reward Mean: `-942,122.8`, AoI Mean: `306.82`, CBR Mean: `0.0409`, PDR Mean: `79.62%`
- **SARSA** (ep 1~63): Reward Mean: `-942,123.0`, AoI Mean: `306.65`, CBR Mean: `0.0409`, PDR Mean: `79.63%`
- **ActorCritic** (ep 1~34): Reward Mean: `-935,185.6`, AoI Mean: `295.24`, CBR Mean: `0.0430`, PDR Mean: `78.75%`
- **VanillaDQN** (ep 1~50): Reward Mean: `-951,913.2`, AoI Mean: `492.55`, CBR Mean: `0.0398`, PDR Mean: `78.99%`
*(4개 로그 모두 Null, NaN, Inf가 전혀 없으나 ep 100에 도달하지 못해 훈련 재개가 필수적인 상태입니다.)*

---

## 3. Weight File Audit & Loadability Test (`.pth` / `.pkl`)

### 3.1 Standard Directory (`data/models/`) Audit
- `run_parallel_evaluation.py`의 `MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"` 상에서 14개 모델 가중치 파일 존재 여부: **전원 미존재 (0/14)**
- 사유: `train_worker` 함수가 100 에피소드 반복문 완수 시에만 `agent.save(model_path)`를 실행하는데, 세션 중단으로 100 ep 완수 전 프로세스가 종료되었기 때문입니다.

### 3.2 Legacy/Candidate Directory (`code/`) Audit & Programmatic Load Verification
`create_agent(display_name)`를 통해 인스턴스를 생성한 뒤 `agent.load(candidate_file_path)`를 실행하여 가중치 텐서 로드 가능 여부를 전수 검증했습니다.

| # | Model Name | Expected Weight File | Candidate File in `code/` | File Size | Load Test Result | Notes / Error Details |
|---|------------|----------------------|---------------------------|-----------|------------------|-----------------------|
| 1 | QLearning | `QLearning.pkl` | `code/qlearning_model.pkl` | 1,097,993 bytes | **SUCCESS** | Q-Table dict normal load |
| 2 | SARSA | `SARSA.pkl` | `code/sarsa_model.pkl` | 903,561 bytes | **SUCCESS** | Q-Table dict normal load |
| 3 | ActorCritic | `ActorCritic.pth` | `code/actor_critic.pth` | 81,625 bytes | **SUCCESS** | PyTorch state_dict ok |
| 4 | VanillaDQN | `VanillaDQN.pth` | `code/vanilla_dqn.pth` | 80,581 bytes | **SUCCESS** | PyTorch state_dict ok |
| 5 | DoubleDQN | `DoubleDQN.pth` | `code/ddqn.pth` | 42,865 bytes | **SUCCESS** | PyTorch state_dict ok |
| 6 | DuelingDQN | `DuelingDQN.pth` | `code/dueling_dqn.pth` | 42,865 bytes | **FAILED** | **Key Mismatch Error** (`fc1`, `val_fc`, `adv_fc` missing) |
| 7 | DDPG | `DDPG.pth` | `code/ddpg_model.pth` | 89,653 bytes | **SUCCESS** | PyTorch state_dict ok |
| 8 | PPO | `PPO.pth` | `code/ppo.pth` | 80,759 bytes | **SUCCESS** | PyTorch state_dict ok |
| 9 | SAC | `SAC.pth` | `code/sac.pth` | 125,965 bytes | **SUCCESS** | PyTorch state_dict ok |
| 10 | TD3 | `TD3.pth` | `code/td3.pth` | 134,669 bytes | **SUCCESS** | PyTorch state_dict ok |
| 11 | DecisionTransformer | `DecisionTransformer.pth` | `code/dt_model.pth` | 422,569 bytes | **SUCCESS** | PyTorch state_dict ok |
| 12 | MAPPO | `MAPPO.pth` | `code/mappo.pth` | 83,355 bytes | **SUCCESS** | PyTorch state_dict ok |
| 13 | MoEDQN | `MoEDQN.pth` | `code/moe_dqn.pth` | 218,215 bytes | **SUCCESS** | PyTorch state_dict ok |
| 14 | REMO-DQN | `REMO-DQN.pth` | `code/resnet_moe_dqn.pth` | 527,781 bytes | **SUCCESS** | PyTorch state_dict ok |

---

## 4. Standardized Model Training Completion Verification Criteria

M1 단계에서 14개 모델 훈련 완료 판정을 내리기 위한 **5단계 구체적 검증 기준 (Gate Protocol)**을 아래와 같이 수립합니다.

```
[1. File Existence] -> [2. Episode Progress] -> [3. Data Integrity] -> [4. Model Loadability] -> [5. Domain Sanity]
```

### Gate 1: File Existence & Naming Convention
- **경로**: `/home/imnyj/Workspace/paper4/data/models/`
- **수렴 로그**: `{model_name}_convergence.csv` (14개 전원)
- **가중치 파일**:
  - `QLearning.pkl`, `SARSA.pkl` (Pickle format)
  - `ActorCritic.pth`, `VanillaDQN.pth`, `DoubleDQN.pth`, `DuelingDQN.pth`, `DDPG.pth`, `PPO.pth`, `SAC.pth`, `TD3.pth`, `DecisionTransformer.pth`, `MAPPO.pth`, `MoEDQN.pth`, `REMO-DQN.pth` (PyTorch format)

### Gate 2: Episode Progress & Episode Continuity
- **최종 에피소드 번호**: `df['Episode'].max() >= 100` (정확히 에피소드 100 도달)
- **행 수 및 연속성**: `len(df) >= 100` 이며, `Episode` 컬럼이 1부터 100까지 단 한 개도 결번 없이 순차 증가해야 함.
- **누적 Step**: `Global_Step` 컬럼이 $100 \times 2000 = 200,000$ steps 이상 기록되어야 함.

### Gate 3: Data Integrity & Cleanliness
- **필수 컬럼 존재**: `['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean']` 6개 헤더 정확 매칭.
- **Null/NaN/None 비율**: 0건 (`df.isnull().sum().sum() == 0`).
- **Inf/-Inf 비율**: 0건 (`np.isinf(df.select_dtypes(include=np.number)).sum().sum() == 0`).

### Gate 4: Weight Loadability & Model Integrity
- **Load Test**: `agent = create_agent(model_name)` 후 `agent.load(model_path)` 수행 시 예외나 Key mismatch 없이 100% 성공.
- **Weight Tensor Sanity**: 가중치 Parameter 내 NaN / Inf 값 0건.

### Gate 5: Domain & Physical Metric Sanity
- **PDR (Packet Delivery Ratio)**: $0.0 \le \text{PDR\_mean} \le 100.0\%$ (또는 $0.0 \le \text{PDR} \le 1.0$)
- **CBR (Channel Busy Ratio)**: $0.0 \le \text{CBR\_mean} \le 1.0$ (또는 $0\% \sim 100\%$)
- **AoI (Age of Information)**: $\text{AoI\_mean} > 0.0$ (물리적 양수 지표)
- **Reward Convergence**: 마지막 10개 에피소드 (ep 91~100) 평균 Reward가 초반 (ep 1~10) 대비 발산하지 않고 정답 영역으로 지속 진동/수렴하는 경향성 확보.

---

## 5. Next Step Action Plan & Recommendations for M1 Resume Engine

1. **`run_parallel_evaluation.py` Resume 기능 보완**:
   - `data/models/{name}_convergence.csv` 파일이 존재할 경우, 마지막 recorded episode $N$을 감지하여 $N+1$부터 100 에피소드까지 연이어 학습하도록 로직 추가.
   - 중간 체크포인트 가중치 저장 기능 (e.g. 매 10 에피소드마다 intermediate weights 저장)을 추가하여 프로세스 강제 종료 시에도 가중치 손실 방지.

2. **DuelingDQN 모델 가중치 파일 호환성 해결**:
   - `code/dueling_dqn.pth`는 기존 모델 아키텍처와 Key 구조가 달라 로드에 실패하므로, M1 훈련 시 처음부터 또는 새로운 가중치 구조로 학습을 안전하게 시작/재개하도록 조치.

3. **자동화 검증 스크립트 구축**:
   - 본 보고서의 5단계 게이트 기준을 프로그램 코드로 자동 검증하는 스크립트 (`etc/scripts/verify_m1_completion.py`) 작성 권장.

