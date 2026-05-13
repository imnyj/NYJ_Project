# Idea Memory

## [2026-04-15] Research Context Analysis & Idea Specification

### 연구 방향 확정
- **주제**: NDN-based AoI-Optimal Content Delivery with Multi-Agent Federated Actor-Critic (MAFAC) in Vehicular Networks
- **목표 저널**: IEEE Transactions on Wireless Communications (TWC)
- **Research Gap**: NDN + AoI + MARL 3중 조합 논문 미발견 (Librarian 2026-04-14 검증)

### 핵심 기여 (3가지)
1. **C1: Cross-Layer NDN-AoI Mathematical Framework**
   - Closed-form AoI 분석 (cache hit probability, Rician/Nakagami fading, Marcum Q-function)
   - Theorem 1: NDN Caching AoI Reduction Bound
   - Theorem 2: Optimal TTL for Freshness-Availability Tradeoff
2. **C2: Constrained MDP + MAFAC Algorithm**
   - 4차원 결정변수: forwarding, caching, power, subchannel
   - 5개 제약: energy, cache, peak AoI, CBR, loop-free
   - Lagrangian relaxation, factored action space
   - Theorem 3: MAFAC Convergence
3. **C3: Federated Aggregation for Non-IID Vehicular Env**
   - Critic-only sharing, inverse AoI weighting
   - Theorem 4: Federated Convergence Rate O(1/√(KT))

### 수학적 분석 계획 (7개 정리/명제)
1. Theorem: NDN Caching AoI Reduction Bound
2. Theorem: Optimal TTL
3. Proposition: Transmission Success Probability (Rician/Nakagami)
4. Theorem: MAFAC Convergence (two-timescale stochastic approximation)
5. Theorem: Federated Convergence Rate
6. Proposition: Complexity Analysis
7. Lemma: NDN Loop-Free Guarantee

### 물리계층 모델 (2nd Layer 강조)
- 3GPP TR 36.885/37.885 path loss
- Rician fading (V2V), Nakagami-m fading (V2I)
- SINR, transmission success probability
- Finite blocklength PER
- C-V2X Mode 4 SPS, collision probability, CBR

### 비교 대상 (5개 baseline)
1. No-cache baseline
2. NDN random/LRU caching
3. Centralized AoI optimization
4. Independent Q-learning
5. SAC/TD3 single-agent

### 파일 생성 완료
- idea_spec.md: home/nyj/0_paper/paper/idea/idea_spec.md (19,471자)
