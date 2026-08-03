# Contributions

본 논문은 UAM 환경에서의 빈번한 Handover로 인한 통신 지연(Delay) 및 Ping-Pong 현상을 최소화하기 위한 사전 예측적(Proactive) 핸드오버 최적화 방안을 제안하며, 다음과 같은 주요 기여를 가집니다.

1. **3D Map 시뮬레이션 기반 SAGIN 네트워크 환경 구축**
   - 3차원 빌딩 맵과 고도, 현실적인 비행 궤적 및 속도(수직/수평)를 반영한 고도화된 UAM 시뮬레이션 환경을 설계하였습니다.
   - 통신 커버리지 홀(Coverage Hole)을 극복하기 위해 지상망(Cellular, 5G), 노변 기지국(RSU), 위성망(Starlink LEO)을 혼합한 다중 계층(Multi-tier) SAGIN(Space-Air-Ground Integrated Networks) 환경을 구성하여 핸드오버 시나리오의 현실성을 극대화하였습니다.

2. **GNN-Transformer-PPO 기반 Proactive Handover 모델 제안**
   - **GNN (Graph Neural Network):** UAM 기체, 기지국, 장애물(건물) 간의 동적인 토폴로지 변화와 공간적 상호작용을 완벽히 모델링하여 핸드오버 시그널링 간섭 및 Ping-Pong 현상을 감소시킵니다.
   - **Transformer (Self-Attention):** 복잡하고 긴 비행 궤적의 시계열 데이터를 병렬적으로 처리하여, 기존 LSTM의 장기 의존성(Long-term Dependency) 학습 한계를 극복하고 예측 지연 시간을 극한으로 단축합니다.
   - **PPO (Proximal Policy Optimization):** 공간적(GNN) 및 시계열적(Transformer) 임베딩을 바탕으로 안정적이고 최적화된 핸드오버 정책(Action)을 결정합니다.

3. **기존 모델 대비 압도적인 성능 개선 입증**
   - 최신 논문(2025~2026) 및 강화학습 모델 12종과의 비교 실험(Optuna 최적화)을 통해 제안 방안이 Handover Delay 및 Ping-Pong Effect를 최소화하는 데 있어 1위를 달성함을 수치적으로 입증하였습니다.
