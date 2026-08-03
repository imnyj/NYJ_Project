## 다량의 프롬프트 요청 사항
1. TinyMLP는 내가 고안한 모델이므로 Discard 하자.

1. 시간이 오래 걸리더라도 Raw data를 뽑아서 실제 성능을 뽑아 csv로 관리하자. 모델 표현 및 구현, 평가 순서는 다음과 같이 진행해줘.
 * 평가 모델 순서
 [ ] Fixed 10Hz
 [ ] ReactDCC
 [ ] AdaptDCC
 [ ] Q-Learning
 [ ] SARSA
 [ ] Actor-Critic
 [ ] Vanilla DQN
 [ ] Double DQN
 [ ] DDPG
 [ ] PPO
 [ ] SAC
 [ ] TD3
 [ ] Decision Transformer
 [ ] MAPPO
 [ ] REMO-DQN

2. optuna로 최적화된 파라미터 값을 csv로 저장.

3. ablation study(수렴 그래프)를 더 잘게 쪼개 볼까? 어떻게 까지 쪼갤 수 있을까? 이것두 Raw data를 뽑아서 정확한 수치를 csv로 관리해.

4. tsne_clustering 그래프를 설명해보겠어? 그래프의 의미가 어떻게 되는지 데이터를 기반으로 분석해줘.

2. 학습과 추론 시간을 따로 표기하고 RSU인지 차량인지 표기해야 겠네.
6. 파라미터 크기에 대한 의혹 해명
- Vanilla DQN과 제안하는 REMO-DQN(ResNetMoEDQN)의 파라미터 수 및 연산량(FLOPs) 비교를 통해 파라미터 뻥튀기 의혹을 해명합니다.
- **Total Parameters**: Vanilla DQN은 19,205개, REMO-DQN은 127,253개로 총 파라미터 수는 약 6.6배 증가했습니다.
- **MoE Sparsity (희소성) 분석**: REMO-DQN의 핵심인 MoE 레이어(Experts)는 총 50,706개의 파라미터로 구성되어 있지만, 추론 시 Top-1 라우팅을 적용할 경우 단 1개의 Expert(16,902개 파라미터)만 활성화됩니다.
- **Active Parameters (활성 파라미터)**: 결과적으로 전체 파라미터 127,253개 중 실제 활성화되는 파라미터는 93,449개입니다. 즉, MoE 레이어 내에서 연산의 66%가 생략(Sparsity)되므로, 파라미터 크기 증가 대비 실제 연산량 증가는 억제되어 연산 효율성이 높습니다.
- **결론**: 단순히 파라미터를 늘려 성능을 올린 것이 아니라, 상태별로 가장 적합한 Expert만 선택적으로 활성화하여 최소한의 연산으로 최대의 효율을 내는 "MoE의 희소성"이 높은 성능의 근본적인 이유입니다.
