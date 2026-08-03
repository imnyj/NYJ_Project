# Performance Metrics

제안하는 GNN-Transformer-PPO 모델의 성능 및 Contributions를 입증하기 위해 다음과 같은 평가 지표(Metrics)를 활용합니다.

1. **Handover Delay (핸드오버 지연 시간)**
   - 핸드오버 결정부터 타겟 네트워크에 완전히 접속되어 데이터 전송이 재개되기까지 소요되는 시간입니다. 통신 끊김 현상을 방지하기 위해 최소화해야 하는 핵심 지표입니다.

2. **Ping-Pong Rate (핑퐁 비율)**
   - 짧은 시간 내에 두 기지국 사이를 불필요하게 왕복하며 핸드오버하는 횟수의 비율입니다. 통신 오버헤드와 불안정성을 나타내며, 낮을수록 우수합니다.

3. **Packet Delivery Ratio (PDR, 패킷 전송 성공률)**
   - 송신된 패킷 중 수신지에 성공적으로 도달한 패킷의 비율입니다. 복잡한 3D Map 및 혼합망(SAGIN) 환경에서도 지속적인 연결을 유지하는지 평가합니다.

4. **Throughput (처리량)**
   - 단위 시간당 성공적으로 전송된 데이터의 양입니다. 핸드오버 과정에서 대역폭이 보장되는지 확인합니다.

5. **Total Handover Cost (종합 핸드오버 비용 / Score)**
   - Handover Delay와 Ping-Pong Effect에 가중치를 부여한 종합 점수입니다. 
   - *Score = (Handover Delay) + 2 * (Ping-Pong Effect)* (낮을수록 우수함)
