# Comparative Methods (비교 모델 12종 + 1종 특징 정리)

총 13종의 모델(기존 제안 및 12개 비교 모델)의 특징을 분석하여 성능 비교의 근거로 삼습니다. (평가 지표: Score = Handover Delay + 2 * Ping-Pong Effect)

## A. 최신 모델 (2025~2026)
1. **PPO-GNN (Score: 28.34)**
   - *특징:* 그래프 신경망(GNN)을 활용해 네트워크 노드 간 공간적 관계를 파악하나, 시계열적 궤적 변화(Transformer) 예측이 부족하여 한계가 존재합니다.
2. **TD3-Transformer (Score: 31.59)**
   - *특징:* 연속 행동 공간에 강한 TD3에 Transformer를 결합하였으나, 이산 행동(네트워크 선택) 환경인 핸드오버 매핑 시 효율성이 떨어집니다.
3. **MARL-Attention (Score: 31.08)**
   - *특징:* 다중 에이전트 및 Attention 메커니즘을 사용하지만, 복잡한 3D 공간 제약(건물 등) 처리 면에서 제안 방안보다 학습 안정성이 부족합니다.

## B. 기존 딥러닝/강화학습 제안 방안
4. **CNN-LSTM + PPO (Score: 26.01)**
   - *특징:* 기존에 제안되었던 방식으로, 궤적을 예측하지만 격자 기반 CNN의 한계와 긴 시계열 데이터에서 LSTM의 기울기 소실 문제로 동적 토폴로지 적응이 느립니다.

## C. 추가 DRL 모델군
5. **A2C (Advantage Actor-Critic, Score: 41.20)**
   - *특징:* PPO의 이전 버전 격으로 동기식(Synchronous) 업데이트를 수행하나 성능 변동폭이 큽니다.
6. **MAC (Multi-Agent Actor-Critic, Score: 41.36)**
   - *특징:* 여러 UAM 에이전트 간의 협력 학습을 시도하나, 복잡성 증가로 인해 최적화 점수가 상대적으로 낮습니다.
7. **TRPO (Trust Region Policy Optimization, Score: 43.98)**
   - *특징:* 안정적인 정책 업데이트를 보장하나 연산량이 과도하여 실시간 핸드오버 적용에 병목이 발생합니다.

## D. 기본 DRL (Deep Reinforcement Learning) 모델
8. **SAC (Soft Actor-Critic, Score: 48.44)**: 탐험(Exploration)을 극대화하는 Entropy 기반 모델이나, 빠른 수렴이 어려움.
9. **DDPG (Score: 48.90)**: 연속 제어용 모델로, 핸드오버 네트워크 선택(이산화)에 적용 시 성능이 매우 낮음.
10. **DQN (Score: 48.97)**: 가치 기반(Value-based)의 대표적 심층 모델이지만, 고차원 상태 공간 처리에서 PPO에 밀림.

## E. 기본 RL (전통적 기법)
11. **SARSA (Score: 63.61)**: On-policy 방식의 테이블 기반 학습으로, 연속적 상태 변수 환경 적용 불가.
12. **Q-Learning (Score: 63.67)**: Off-policy 방식의 테이블 기반 학습. 딥러닝 부재로 확장성(Scalability) 0.
13. **Monte Carlo (Score: 67.98)**: 에피소드가 끝나야만 학습하므로 실시간 결정(핸드오버)에는 부적합한 최하위 모델.
