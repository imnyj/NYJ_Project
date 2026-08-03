# Paper4 Architecture Experiment Tracker

본 문서는 Paper4(V2X DCC 혼잡 제어) 강학학습 에이전트의 '모델 구조 최적화' 과정을 기록하기 위한 로그 문서입니다.

| Date/Time | Version | Architecture Idea | Objective / Hypothesis | Status / Result (AoI, PDR, CBR) | Remarks |
|---|---|---|---|---|---|
| 2026-07-30 23:00 | v3.0_DQL_Baseline | 지도학습(TinyMLP) -> 심층강화학습(DQN) 전환 | 휴리스틱(AdaptDCC)의 불법적인 전송 폭주(Burst) 및 CBR 요동(Oscillation) 방어 | 진행 중 | 기본 DQN 구조. 향후 MoE, ResNet 등 결합 예정 |
| 2026-07-30 23:02 | v3.1_Dueling_DQN | Dueling DQN Architecture | Split State Value and Advantage streams to better estimate actions in stable congestion states | 완료 (PDR 75.52%, CBR 0.2285) | |
| 2026-07-30 23:07 | v3.2_MoE_DQN | Mixture of Experts (MoE) DQN | Separate Expert networks for High/Low CBR domains, gated by a router network | 완료 (PDR 76.65%, CBR 0.2271) | MoE router splits regimes well |
| 2026-07-30 23:09 | v3.3_ResNet_MoE_Dueling | ResNet + MoE + Dueling DQN | Use residual connections in the feature extractor to capture non-linear relations, then route through MoE to Dueling heads | 완료 (PDR 76.39%, CBR 0.2209, 최고 수준 복잡도 및 최적 균형) | 최종 최적 아키텍처 선정 |
