## 다량의 프롬프트 요청 사항
1. 시뮬레이션의 신뢰성부터 확보하고 싶어. coder에게 코딩을 맡기고, critics에게 검증을 맡기고, 고칠 것이 없을 때까지 구현을 계속 반복하도록 해.
 1) sumo 파일을 기반으로 한 네트워크 환경 세팅 검증 (SumoNetSim1.1.5/src/sumo 내의 파일및 환경 세팅값 사용)
    사용자가 편하게 환경변수 세팅을 변경할 수 있도록 config.md 운용할 것
    차량 속도나 밀도 = 0은 랜덤 설정.
 2) 통신 모듈 구현 검증
 3) 비교 모델들의 구현 검증
 4) 제안 모델의 구현 검증

2. 평가 모델 순서는 다음과 같이 세팅하도록 해.
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
 [ ] REMO-DQN (proposed)

3. 성능 평가 구현의 순서는 다음과 같이 가도록 하자. 이것도 마찬가지로 coder에게 구현을 맡기고, critics에게 검증을 맡겨서 더 고칠 것이 없을 때까지 반복하도록 해. 그래프를 그릴 때만 visualizer의 개입을 열도록 해. 시간이 오래 걸리더라도 Raw data를 뽑아서 실제 성능을 뽑아 csv로 관리하자.
 1) 구조의 ablation study로 모델의 구조 정당성 (ResNet+MoE+Dueling, w/o ResNet, w/o MoE, w/o Dueling)
 2) reward의 ablation study로 모델의 보상 함수 정당성 (REMO-DQN, w/o R1, w/o R2, ...)
 3) state에 대한 ablation study로 모델의 state 설계에 대한 정당성
 4) optuna로 최적의 하이퍼파라미터를 csv로 저장
 5) 비교 방안 전체에 대한 optuna 최적화 진행 및 각 방안별 최적화된 하이퍼파라미터를 csv로 저장
 6) 비교 방안들부터 데이터 fix하기
  - 모델별 reward convergence: step은 상승 후 수렴이 되는 부분까지 뽑도록 하기. 경험 상 20만번 이상이었음. 수렴된 모델들은 저장할 것
  - 저장된 수렴된 모델을 활용하여 이후 실험 진행
    - 모델별로 시간 흐름에 따른 성능 지표들(PDR, CBR, AoI 등)
    - 모델별로 환경 파라미터에 따른 시간 흐름에 대한 성능 변화 (차량 수, 차량의 속도 등)
 7) 제안 방안 데이터 수집하기
  - reward convergence: step은 상승 후 수렴이 되는 부분까지 뽑도록 하기. 경험 상 20만번 이상이었음. 수렴된 모델은 저장할 것
  - 저장된 수렴된 모델을 활용하여 이후 실험 진행
    - 시간 흐름에 따른 성능 지표들(PDR, CBR, AoI 등)
    - 환경 파라미터에 따른 시간 흐름에 대한 성능 변화 (차량 수, 차량의 속도 등)
 8) 수집된 데이터들을 기반으로 그래프 하나씩 그려보기

4. moe routing 그래프를 설명해보겠어? 그래프의 의미가 어떻게 되는지 데이터를 기반으로 분석해줘.

5. tsne_clustering 그래프를 설명해보겠어? 그래프의 의미가 어떻게 되는지 데이터를 기반으로 분석해줘.