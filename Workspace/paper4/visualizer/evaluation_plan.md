# Paper 4 성능 평가 및 시각화 계획 (Evaluation & Visualization Plan)

이 문서는 논문에 포함될 성능 평가 결과의 추출 계획, 그래프 범례 순서, 색상 및 지표 순서를 정의합니다. 코멘트를 통해 수정 지시를 내려주시면 스크립트 설계에 반영하겠습니다.

---

## 1. 성능 평가 전개 순서 (Evaluation Order in Paper)
논문(제5장 성능 평가)의 흐름에 맞춰 다음과 같은 순서로 그래프를 도출합니다.

1. **학습 수렴도 (Reward Convergence)**
   - 에피소드 진행에 따른 누적 보상(Reward) 수렴 속도 및 안정성 비교 (14개 RL 모델 대상).
2. **채널 안정성 (Time-Series CBR Trace)**
   - 시뮬레이션 시간 흐름에 따른 CBR(Channel Busy Ratio)의 요동(Oscillation) 폭 비교. 제안 방안의 채널 안정화 능력 입증.
3. **차량 밀도별 패킷 전송 성공률 (PDR vs. Density)**
   - 차량 밀도(Density) 증가 시 혼잡 상황에서 PDR 방어 능력 대조.
4. **차량 밀도별 정보 연령 및 지연 (AoI & Fake AoI vs. Density)**
   - 혼잡 제어로 인해 발생하는 전송 주기 지연(Trade-off)과 실제 수신 데이터의 최신성(AoI) 분석.
5. **통신 에너지 소모량 (Energy Efficiency)**
   - 불필요한 비콘 전송을 억제하여 아낀 통신 에너지 효율 분석.
6. **하드웨어 추론 실효성 (Inference Latency & Complexity)**
   - MCU 탑재를 가정한 모델별 추론 지연시간(Latency)과 연산량(FLOPs) 비교 (Bar Plot).
7. **MoE 동적 라우팅 군집화 (Routing Dynamics & t-SNE)**
   - REMO-DQN 내부 전문가(Expert)들의 활성화 분포 및 혼잡 상태별 t-SNE 군집화 시각화 (Scatter Plot).

---

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
- 학습을 시킬 때는 20만번의 step을 진행하면서 수치가 전반적으로 상승하다가 수렴되는지를 확인해야 함.

1. ablation study convergence curves
 * Structure
   - [ ] REMO-DQN
   - [ ] w/o ResNet
   - [ ] w/o MoE
   - [ ] w/o Dueling
 * Reward
   - [ ] REMO-DQN
   - [ ] w/o R1
   - [ ] w/o R2
   - [ ] w/o R3

2. sensitivity analysis table by optuna & saved as csv file
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

3. comparing reward convergence curves
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

4. tsne_routing or tsne clustering
 - [ ] Low traffic
 - [ ] Midium traffic
 - [ ] High traffic

5. moe_routing
 - [ ] Expert1
 - [ ] Expert2
 - [ ] Expert3

6. cbr_trace graph
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

7. pdr vs density graph
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

8. aoi vs density graph
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

9. pdr vs distance graph
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

10. aoi vs distance graph
 - [ ] REMO-DQN (Proposed)
 - [ ] Fixed 10Hz
 - [ ] ReactDCC
 - [ ] AdaptDCC
 - [ ] MoEDQN
 - [ ] MAPPO
 - [ ] PPO
 - [ ] SAC
 - [ ] DDPG
 - [ ] TD3
 - [ ] DuelingDQN
 - [ ] DoubleDQN
 - [ ] VanillaDQN
 - [ ] QLearning
 - [ ] SARSA
 - [ ] ActorCritic
 - [ ] DecisionTransformer

11. hardware feasibility table of proposed REMO-DQN
 - [ ] CPU
 - [ ] RAM
 - [ ] 추론 시간
 - [ ] 학습 시간
 - [ ] FLOPs
 - [ ] 파라미터 크기
 - 이외 필요한 지표