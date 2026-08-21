# Handoff Report — 16개 베이스라인 모델 훈련 및 데이터 수집 파이프라인 분석

> **Handoff Type**: Hard (Investigation Complete)  
> **Agent Directory**: `/home/imnyj/Workspace/paper4/.agents/explorer_eval_survey_2`  
> **Target Milestone**: R2. 16개 모델 전수 파이프라인 조사  
> **Target Audience**: Orchestrator / Coder

---

## 1. Observation (관측 사실)

1. **17개 모델 전체 목록 및 요구사항**:
   - `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md` (Lines 30-46): 
     ```
     1. REMO-DQN (Proposed)
     2. Fixed 10Hz
     3. ReactDCC (ETSI Standard)
     4. AdaptDCC (ETSI Standard)
     5. MoEDQN
     6. MAPPO
     7. PPO
     8. SAC
     9. DDPG
     10. TD3
     11. DuelingDQN
     12. DoubleDQN
     13. VanillaDQN
     14. QLearning
     15. SARSA
     16. ActorCritic
     17. DecisionTransformer
     ```
   - `/home/imnyj/.gemini/antigravity-cli/brain/4c546ebc-ef10-4f86-8d8f-a76a42c04f5f/prompt_draft.md` (Lines 17-21, R2): 
     ```
     100 에피소드, 2000 스텝, 매 에피소드 랜덤 차량 밀도(30/50/100) 조건으로 16개 모델(총 17개) 전수 훈련/실행, 가중치는 data/models/ 저장, 개별 CSV 저장.
     ```

2. **비RL 알고리즘 구현 코드**:
   - `/home/imnyj/Workspace/paper4/code/etsi_cam_layer.py`:
     - Line 359: `def _dcc_reactive(self, vs: VehicleCAMState, cbr: float):` (ReactDCC 3-state 머신: RELAXED 0.1s, ACTIVE 0.4s, RESTRICTED 1.0s)
     - Line 373: `def _dcc_simplified_adaptive(self, vs: VehicleCAMState, cbr: float):` (AdaptDCC 폐루프 적응 제어: $\delta_T = 0.05s$)
     - Line 405: `def _dcc_fixed_10hz(self, vs: VehicleCAMState):` (Fixed 10Hz: $T_{GenCam} = 0.1s$)

3. **RL 알고리즘 및 훅(Hook) 매핑**:
   - `/home/imnyj/Workspace/paper4/code/ai_dcc_hook.py`:
     - Lines 417-459: `get_hook()` 함수에 14개 RL 방법(`ResNetMoEDQN`, `MoEDQN`, `DuelingDQN`, `DoubleDQN`, `VanillaDQN`, `QLearning`, `SARSA`, `ActorCritic`, `PPO`, `SAC`, `DDPG`, `TD3`, `MAPPO`, `DecisionTransformer`)의 훅 클래스가 모두 등록되어 있음.
   - 각 에이전트 클래스:
     - `resnet_moe_agent.py` (`ResNetMoEAgent`), `moe_agent.py` (`MoEAgent`), `dueling_dqn_agent.py` (`DuelingDQNAgent`), `ddqn_agent.py` (`DDQNAgent`), `dqn_agent.py` (`DQNAgent`), `qlearning_agent.py` (`QLearningAgent`), `sarsa_agent.py` (`SARSAAgent`), `actor_critic_agent.py` (`ActorCriticAgent`), `ppo_agent.py` (`PPOAgent`), `sac_agent.py` (`SACAgent`), `ddpg_agent.py` (`DDPGAgent`), `td3_agent.py` (`TD3Agent`), `mappo_agent.py` (`MAPPOAgent`), `dt_agent.py` (`DTAgent`).

4. **기존 훈련 스크립트 파라미터 불일치**:
   - 개별 스크립트(`train_resnet.py`, `train_moe.py`, `train_dueling_dqn.py`, `train_ddqn.py`, `train_dqn.py`, `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`):
     - `num_episodes=500` (기본값)
     - `duration_steps=1000` (기본값)
     - `n_vehicles=50` (고정)
     - 저장 경로: `code/*.pth`, `code/*_train_log.csv`
   - 배치 러너(`run_parallel_evaluation.py`):
     - Lines 126-127: `TOTAL_EPISODES = 100`, `STEPS_PER_EP = 2000`
     - Line 184: `n_vehicles=50` (고정 $\rightarrow$ 랜덤 밀도 30/50/100 미적용)
     - 저장 경로: `data/models/{ModelName}.pth` (또는 `.pkl`), `data/models/{ModelName}_convergence.csv`

5. **현재 `data/models/` 내 파일 현황**:
   - `ActorCritic.pth` (81.6KB), `ActorCritic_convergence.csv` (101 lines)
   - `DDPG.pth` (88.8KB), `DDPG_convergence.csv` (101 lines)
   - `DecisionTransformer.pth` (423KB), `DecisionTransformer_convergence.csv` (101 lines)
   - `DoubleDQN.pth` (43.4KB), `DoubleDQN_convergence.csv` (101 lines)
   - `DuelingDQN.pth` (44.2KB), `DuelingDQN_convergence.csv` (101 lines)
   - `MAPPO.pth` (83.4KB), `MAPPO_convergence.csv` (101 lines)
   - `MoEDQN.pth` (218KB), `MoEDQN_convergence.csv` (101 lines)
   - `PPO.pth` (80.8KB), `PPO_convergence.csv` (101 lines)
   - `QLearning.pkl` (6.4MB), `QLearning_convergence.csv` (101 lines)
   - `REMO-DQN.pth` (528KB), `REMO-DQN_convergence.csv` (101 lines)
   - `SAC.pth` (126KB), `SAC_convergence.csv` (101 lines)
   - `SARSA.pkl` (6.4MB), `SARSA_convergence.csv` (101 lines)
   - `TD3.pth` (135KB), `TD3_convergence.csv` (101 lines)
   - `VanillaDQN.pth` (80.6KB), `VanillaDQN_convergence.csv` (101 lines)

---

## 2. Logic Chain (논리적 추론 체계)

1. **[Observation 1, 3] $\rightarrow$ 17개 모델 식별 및 완전성 검증**:
   - `evaluation_plan.md`에 명시된 17개 모델 목록은 1개의 제안 모델(REMO-DQN), 13개의 RL/DRL 베이스라인, 3개의 비RL 표준/휴리스틱 베이스라인으로 완벽하게 구성되어 있으며, `ai_dcc_hook.py`와 각 에이전트 클래스에 이미 100% 매핑되어 있습니다.

2. **[Observation 2] $\rightarrow$ 비RL 베이스라인 실행 전략 수립**:
   - `Fixed 10Hz`, `ReactDCC`, `AdaptDCC`는 가중치 학습이 필요 없으므로 `ETSICAMLayer` 내장 로직으로 동작합니다. 따라서 100 에피소드 수렴 비교 그래프 도출 시에는 동일한 시드와 랜덤 차량 밀도(30/50/100) 조건으로 100 에피소드 시뮬레이션을 수행하여 에피소드별 보상 $R$을 기록해야 합니다.

3. **[Observation 4] $\rightarrow$ 파이프라인 통일점 및 수정 소요 식별**:
   - 기존 개별 스크립트와 `run_parallel_evaluation.py`의 가장 핵심적인 결함은 **차량 밀도가 `n_vehicles=50`으로 고정되어 있다는 점**입니다.
   - R1 및 R2 조건에 맞춰 `n_vehicles = int(np.random.choice([30, 50, 100]))`로 매 에피소드 동적 추출하도록 변경해야 합니다.
   - 개별 스크립트의 파라미터(500 에피소드/1000 스텝) 대신, `run_parallel_evaluation.py`의 기준인 `TOTAL_EPISODES=100`, `STEPS_PER_EP=2000` (총 200,000 스텝)으로 전수 통일되어야 합니다.

4. **[Observation 4, 5] $\rightarrow$ 가중치 및 로그 저장 표준화**:
   - 모든 DRL 모델 가중치는 `data/models/{ModelName}.pth`, Tabular RL 모델은 `data/models/{ModelName}.pkl`에 저장되어야 합니다.
   - 모든 개별 수렴 로그는 `data/models/{ModelName}_convergence.csv` (`Episode,Global_Step,Reward,AoI_mean,CBR_mean,PDR_mean`) 포맷으로 일원화되어야 합니다.
   - 17개 모델의 학습/실행 로그가 완성되면 `data/reward_convergence.csv` (17개 모델 통합) 및 `data/ablation_study.csv` (5개 모델 통합)로 병합되어 R3 요구사항으로 직결됩니다.

---

## 3. Caveats (주의사항 및 한계점)

1. **본 조사는 Read-Only 분석**:
   - 본 Explorer는 코드를 직접 수정하거나 모델 훈련을 직접 실행하지 않았습니다.
2. **Tabular RL 모델 파일 크기**:
   - `QLearning.pkl` 및 `SARSA.pkl`은 상태 이산화 그리드($10^5$ 상태)로 인해 각 6.4MB 수준의 크기를 차지하므로, 저장 공간 관리에 유의해야 합니다.
3. **PPO / DecisionTransformer의 에피소드별 가중치 저장**:
   - Transformer 및 On-policy PPO 모델은 에피소드 종료 시 메모리 클리어 및 안정적인 체크포인팅이 필요합니다.

---

## 4. Conclusion (결론 및 후속 조치 권고)

1. **17개 모델 아키텍처 및 훈련 파이프라인 분석 완료**:
   - 17개 전수 모델의 클래스, 훅, 실행 메커니즘 매핑이 완벽하게 완료되었습니다.
2. **Coder 에이전트를 위한 표준 실행 가이드**:
   - `run_parallel_evaluation.py` (또는 통합 훈련 러너)에서 `n_vehicles = int(np.random.choice([30, 50, 100]))` 적용.
   - `TOTAL_EPISODES = 100`, `STEPS_PER_EP = 2000` 설정.
   - 14개 RL 모델 가중치를 `data/models/*.pth` / `*.pkl`에 저장하고, 각 모델의 수렴 로그를 `data/models/*_convergence.csv`로 저장.
   - 3개 비RL 모델의 100 에피소드 기준선 데이터를 추출하여 `data/reward_convergence.csv`에 취합.

---

## 5. Verification Method (검증 방법)

1. **파일 무결성 검증**:
   - `view_file`을 통해 `/home/imnyj/Workspace/paper4/.agents/explorer_eval_survey_2/analysis.md` 확인.
2. **가중치 파일 존재 여부 검증 명령어**:
   ```bash
   ls -lh /home/imnyj/Workspace/paper4/data/models/*.pth /home/imnyj/Workspace/paper4/data/models/*.pkl
   ```
3. **수렴 로그 행 수(101 lines: header + 100 episodes) 검증 명령어**:
   ```bash
   wc -l /home/imnyj/Workspace/paper4/data/models/*_convergence.csv
   ```
4. **통합 CSV 생성 여부 검증 명령어**:
   ```bash
   head -n 5 /home/imnyj/Workspace/paper4/data/reward_convergence.csv
   head -n 5 /home/imnyj/Workspace/paper4/data/ablation_study.csv
   ```
