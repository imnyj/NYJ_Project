# Required Graphs (결과 분석 필수 그래프)

제안하는 GNN-Transformer-PPO 모델의 우수성을 12개의 비교 모델 및 기존 제안 방안(CNN-LSTM+PPO)과 대비하여 입증하기 위해 다음의 그래프(Plots)를 도출해야 합니다.

1. **Learning Curve (학습 수렴 곡선)**
   - **X축:** Episode (학습 에피소드 수)
   - **Y축:** Cumulative Reward (누적 보상) 또는 Total Score
   - **의미:** 제안 모델이 기존 모델들(CNN-LSTM+PPO, PPO-GNN, TD3-Transformer 등)에 비해 빠르게 수렴하고, 안정적인 학습 성능을 보임을 증명합니다.

2. **Average Handover Delay by Vehicle Speed (비행 속도에 따른 평균 핸드오버 지연 시간)**
   - **X축:** UAM Velocity (속도, km/h)
   - **Y축:** Handover Delay (ms)
   - **의미:** 기체의 속도가 빨라져 토폴로지가 급변하더라도, Transformer 기반의 예측과 GNN 공간 분석을 통해 지연 시간이 현저히 적음을 나타냅니다.

3. **Ping-Pong Rate Comparison (핑퐁 비율 비교 Bar Chart)**
   - **X축:** Models (제안 모델 vs. 기존 비교 모델 12종 주요 모델 그룹)
   - **Y축:** Ping-Pong Handover Count / Rate
   - **의미:** 불필요한 네트워크 스위칭 빈도가 제안 모델에서 가장 적음을 가시적으로 보여줍니다.

4. **Network Utilization Rate in SAGIN (통신망 점유/활용 비율 분석)**
   - **X축:** Time Step 또는 UAM Trajectory Sequence
   - **Y축:** Connected Network Type (Cellular, RSU, Starlink)
   - **의미:** 고도 및 건물 장애물 상황에 따라 제안 모델이 언제 지상망(Cellular/RSU)을 쓰고 언제 위성(Starlink)으로 Proactive하게 넘어가는지 궤적에 따른 전환 패턴을 분석합니다.

5. **Throughput / Packet Delivery Ratio (PDR) CDF (누적 분포 함수)**
   - **X축:** Throughput (Mbps) 또는 PDR (%)
   - **Y축:** CDF (Cumulative Distribution Function)
   - **의미:** 통신 품질 측면에서 제안 방안이 하위 퍼센타일에서도 끊김 없는(High Reliability) 서비스를 제공함을 입증합니다.
