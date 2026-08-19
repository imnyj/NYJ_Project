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

1. REMO-DQN (Proposed) : #FF0000, Bold
2. ReactDCC (ETSI Standard)
3. AdaptDCC (ETSI Standard)
4. MoEDQN
5. MAPPO
6. PPO
7. SAC
8. DDPG
9. TD3
10. ActorCritic
11. DecisionTransformer
12. DuelingDQN
13. DoubleDQN
14. VanillaDQN
15. QLearning
16. SARSA
17. Fixed 10Hz

---

## 3. 범례 색상 및 선 스타일 규정 (Color & Line Styles)
제안 방안을 가장 강렬하게 부각하고, 알고리즘 계열별로 유사한 톤을 부여하여 난잡함을 방지합니다.

- **제안 방안**
  - `REMO-DQN`: **Crimson (진한 빨강, `#DC143C`)** / 실선 (두껍게, `linewidth=2.5`)
- **ETSI 표준 기법 (Non-RL)**
  - `ReactDCC`, `AdaptDCC`: **Black (검정, `#000000`)** / 점선 및 파선 (`--`, `-.`)
- **최신/다중 에이전트 계열 (Actor-Critic & MoE)**
  - `MoEDQN`, `MAPPO`, `PPO`: **Blue 계열 (Navy, RoyalBlue, DodgerBlue)** / 실선
- **기능형/연속제어 계열 (SAC, DDPG, TD3)**
  - `SAC`, `DDPG`, `TD3`: **Purple/Magenta 계열** / 실선
- **기존 DQN 계열 (Dueling, Double, Vanilla)**
  - `DuelingDQN`, `DoubleDQN`, `VanillaDQN`: **Green/Teal 계열** / 실선
- **기타 구형 모델 (Q-Learning, SARSA, AC, DT)**
  - `QLearning`, `SARSA`, `ActorCritic`, `DecisionTransformer`: **Gray 계열 (회색, 은색)** / 투명도 부여 (`alpha=0.6`)

---

## 4. 시각화 스크립트를 통해 도출할 결과물 목록 (Target Output Plots)

1. `plot_1_convergence.pdf` (Line) : Episode vs. Cumulative Reward
2. `plot_2_cbr_trace.pdf` (Line) : Time Step vs. CBR (%)
3. `plot_3_pdr_density.pdf` (Bar or Line) : Density (veh/km) vs. PDR (%)
4. `plot_4_aoi_density.pdf` (Line) : Density vs. Average AoI (ms)
5. `plot_5_latency_flops.pdf` (Grouped Bar) : Model vs. Inference Latency (ms) / FLOPs
6. `plot_6_tsne_routing.png` (Scatter) : 2D t-SNE plot for MoE Gating choices
