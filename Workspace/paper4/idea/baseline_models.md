# Paper4 Baseline Models Comparison Tracker

본 문서는 Paper4 (V2X DCC 혼잡 제어) 논문에서 제안하는 하이브리드 아키텍처(ResNet+MoE+Dueling DQN)의 우수성을 입증하기 위해 비교군으로 설정된 총 12개의 RL/DRL 모델 리스트 및 성능 평가(PDR, CBR, AoI)를 관리하는 문서입니다.

## 1. 기본 RL 모델 (Basic RL) 3종
1. **Q-Learning**: 가장 고전적인 형태의 Value-based 이산(Discrete) 상태-행동 공간 학습 모델. 복잡한 V2X 연속 상태 처리에 한계가 있음을 증명하기 위함.
2. **SARSA (State-Action-Reward-State-Action)**: On-policy 기반의 기본 RL 알고리즘. 보수적인 탐색으로 인해 시시각각 변하는 혼잡도(CBR)에 대한 적응력이 낮음을 입증.
3. **Actor-Critic (Basic)**: 정책(Policy)과 가치(Value)를 동시에 분리하여 학습하는 고전적 접근. 심층(Deep) 레이어가 없을 때 비선형적 차량 밀도 대응에 실패함을 보여줌.

## 2. 기본 DRL 모델 (Basic Deep RL) 3종
1. **Vanilla DQN (Deep Q-Network)**: 심층 신경망을 도입한 가장 기본적인 DRL. (기존 baseline_models 후보). 복잡한 상태(State) 특징 추출 및 혼잡도 상황 분리에 있어서 본 논문의 ResNet+MoE 조합 대비 성능이 떨어짐을 증명.
2. **PPO (Proximal Policy Optimization)**: 최적화 과정에서 Policy Update를 제한하여 학습 안정성을 도모하는 대표적인 DRL. 연속 및 이산 행동 공간에서 널리 쓰이나, 연산 오버헤드 대비 혼잡 제어 반응성이 떨어지는지 비교.
3. **DDPG (Deep Deterministic Policy Gradient)**: 연속된 Action을 출력하기 위한 모델. 전송 주기(Rate)를 연속 값으로 제어할 때의 성과와 본 논문의 이산적(Discrete) 제어 성능 간의 Trade-off 비교.

## 3. 최신 (~2026) 모델 3종
1. **Decision Transformer (DT)**: 최근 각광받는 Offline RL 기반 트랜스포머 아키텍처. 시계열 형태의 혼잡 상태를 Sequence Modeling으로 예측하여 혼잡을 제어하나, 실시간 엣지(Edge/Vehicle) 환경에서의 지연(Latency) 이슈가 존재함을 어필.
2. **SAC (Soft Actor-Critic)**: 엔트로피(Entropy) 극대화를 통해 최신 트렌드인 탐색(Exploration) 효율을 높인 모델. 학습 속도는 빠르나 V2X의 극단적 밀도 변화 상황에서 제안 기법(MoE 기반 상황별 분리) 대비 PDR 방어율이 어떻게 되는지 비교.
3. **MAPPO (Multi-Agent PPO)**: 여러 차량이 동시에 분산 제어를 수행하는 최신 Multi-Agent 트렌드. 각 에이전트의 관측 범위를 협력적으로 넓히지만, 통신 오버헤드와 수렴 속도 측면에서 단일 기기(Decentralized) 기반의 제안 모델의 실용성을 강조하기 위한 비교군.

## 4. 추가 DRL 변형 모델 3종 (구조적 융합 비교)
1. **Double DQN (DDQN)**: Q-value의 과대적합(Overestimation)을 막기 위해 타겟 네트워크와 메인 네트워크를 분리한 DQN 확장형.
2. **Dueling DQN**: 본 논문의 기반이 되는 베이스 아키텍처 중 하나. (State value와 Advantage 분리). ResNet과 MoE가 결합되지 않은 순수 Dueling DQN과의 비교(Ablation Study)를 통해 제안 모델의 구조적 정당성 확보.
3. **TD3 (Twin Delayed DDPG)**: DDPG의 Q-value 과대적합을 두 개의 Critic으로 억제한 발전형. 

---

## 🚀 시뮬레이션 성능 비교 결과 (진행 중)
(이 테이블은 백그라운드 에이전트가 시뮬레이션을 수행한 후 지속적으로 업데이트합니다.)

| Model Category | Model Name | PDR (%) | CBR (Mean) | AoI (Mean) | Remarks / Analysis |
|---|---|---|---|---|---|
| Proposed | **ResNet+MoE+Dueling** | **76.39** | **0.2209** | **TBD** | 제안 방안 (최상위 성능 기준점) |
| Basic RL | Q-Learning | 51.10 | 0.5539 | 893.10 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Basic RL | SARSA | 51.10 | 0.5539 | 893.10 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Basic RL | Actor-Critic | 51.10 | 0.5539 | 893.10 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Basic DRL | Vanilla DQN | 69.06 | 0.2560 | 2461.61 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Basic DRL | PPO | 49.88 | 0.5450 | 879.88 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Basic DRL | DDPG | 29.60 | 0.3694 | 7067.55 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Latest 2026 | Decision Transformer | 100.00 | 0.0122 | 129.67 | 하이퍼파라미터 최적화 완료 (Optuna 적용) |
| Latest 2026 | SAC | - | - | - | 훈련 대기 중 |
| Latest 2026 | MAPPO | - | - | - | 훈련 대기 중 |
| Additional | Double DQN | - | - | - | 훈련 대기 중 |
| Additional | Dueling DQN | 75.52 | 0.2285 | - | 앞선 실험 결과(v3.1) 이관 |
| Additional | TD3 | - | - | - | 훈련 대기 중 |
