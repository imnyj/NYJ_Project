# Paper 4 Walkthrough & Task Planning

This document tracks the current status and the next steps for completing Paper 4, based on the `visualizer/evaluation_plan.md`.

## 1. Goal
To write and publish the paper "Paper 4" (REMO-DQN for V2X DCC) in IEEE Transactions on Wireless Communications (TWC).

## 2. 비교 방안(Baselines) 및 범례(Legend) 순서
그래프의 가독성과 제안 방안의 우수성 부각을 위해 범례는 다음 순서로 배치합니다.

1. REMO-DQN (Proposed) : #FF0000 (`alpha=1.0`), Bold
2. Fixed 10Hz: #0000FF (`alpha=0.6`)
3. ReactDCC (ETSI Standard): #4D96FF (`alpha=0.6`)
4. AdaptDCC (ETSI Standard): #2A4B7C (`alpha=0.6`)
5. MoEDQN: #9B5DE5 (`alpha=0.6`)
6. MAPPO: #D783FF (`alpha=0.6`)
7. PPO: #7A49A5 (`alpha=0.6`)
8. SAC: #00FF00 (`alpha=0.6`)
9. DDPG: #6BCB77 (`alpha=0.6`)
10. TD3: #2E8B57(`alpha=0.6`)
11. DuelingDQN: #FF9F1C (`alpha=0.6`)
12. DoubleDQN: #FFD166 (`alpha=0.6`)
13. VanillaDQN: #D67229 (`alpha=0.6`)
14. QLearning: #1A1A1A (`alpha=0.6`)
15. SARSA: #555555 (`alpha=0.6`)
16. ActorCritic: #888888 (`alpha=0.6`)
17. DecisionTransformer: #B5B5B5 (`alpha=0.6`)

## 3. 시각화 스크립트를 통해 도출할 결과물 목록 (Target Output Plots)
1. ablation study convergence curves
 * Structure
   - [x] REMO-DQN
   - [x] w/o ResNet
   - [x] w/o MoE
   - [x] w/o Dueling
 * Reward
   - [x] REMO-DQN
   - [x] w/o R1
   - [x] w/o R2
   - [x] w/o R3

2. sensitivity analysis table by optuna & saved as csv file
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

3. comparing reward convergence curves
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

4. tsne_routing or tsne clustering
 - [x] Low traffic
 - [x] Midium traffic
 - [x] High traffic

5. moe_routing
 - [x] Expert1
 - [x] Expert2
 - [x] Expert3

6. cbr_trace graph
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

7. pdr vs density graph
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

8. aoi vs density graph
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

9. pdr vs distance graph
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

10. aoi vs distance graph
 - [x] REMO-DQN (Proposed)
 - [x] Fixed 10Hz
 - [x] ReactDCC
 - [x] AdaptDCC
 - [x] MoEDQN
 - [x] MAPPO
 - [x] PPO
 - [x] SAC
 - [x] DDPG
 - [x] TD3
 - [x] DuelingDQN
 - [x] DoubleDQN
 - [x] VanillaDQN
 - [x] QLearning
 - [x] SARSA
 - [x] ActorCritic
 - [x] DecisionTransformer

11. hardware feasibility table of proposed REMO-DQN
 - [x] CPU
 - [x] RAM
 - [x] 추론 시간
 - [x] 학습 시간
 - [x] FLOPs
 - [x] 파라미터 크기
 - [x] 이외 필요한 지표