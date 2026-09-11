# 4단계. 비교 방안의 성능 도출

## 목적

제안 방안을 개발하기 전에 비교 방안들의 성능을 공정한 조건에서 먼저 확보합니다. 하이퍼파라미터가 엉망이면 아무리 좋은 최신 모델도
성능이 떨어져 공정한 비교가 되지 않으므로, 방안마다 하이퍼파라미터를 최적화한 뒤 성능을 뽑습니다. 이 단계는 며칠씩 걸리지만,
학습이 도는 동안 사용자는 다른 작업을 할 수 있습니다.

## 들어가기 전 조건

- 3단계 완료 조건을 통과한 시뮬레이션이 있습니다.

## 참여 역할

coder(HPO, 학습, 평가 구현과 실행), critic(결과 검증), visualizer(모델 순서와 색상 규격), worker(파일 정리)

## 절차

1. **[사용자 결정]** 평가 지표를 정합니다. 제안 방안의 구조를 아직 모르더라도 기본 지표는 미리 정할 수 있습니다.
   - ML 지표: 지도 학습이면 MAE, MAPE, R2 Score 같은 정확도, 강화 학습이면 reward
   - 통신 지표: CBR, AoI, Delay, Traffic, PDR 등
   정한 지표와 뜻은 `performance_metrics.md` 에 적습니다.
2. **[사용자 결정]** 그래프에 쓸 모델 이름, 순서, 색상을 정해 `visualizer/config.md` 에 적습니다. 제안 방안은 보통 맨 뒤에 둡니다.
   예) Fixed 10Hz, ReactDCC, AdaptDCC, Q-Learning, SARSA, Actor-Critic, Vanilla DQN, Double DQN, DDPG, PPO, SAC, TD3, Decision Transformer, MAPPO, REMO-DQN(proposed)
3. 하이퍼파라미터 최적화(HPO)를 준비합니다. optuna 에 "각 방안의 하이퍼파라미터를 최적화해 달라" 고만 하면 learning rate 나 batch size 같은 공통 값만 건드립니다.
   그래서 방안마다 핵심이 되는 하이퍼파라미터와 탐색 범위를 `data/hpo/hparam_space.csv` 로 먼저 정리합니다(열 예: method, param, low, high, scale, 근거).
   **[사용자 결정]** 이 CSV 를 보여 주고 승인받습니다.
4. coder 가 CSV 를 읽어 방안별로 optuna 최적화를 돌리고, 방안별 최적값을 `data/hpo/best_params.csv` 에 저장합니다.
5. **[사용자 결정]** 학습 step 수와 본훈련 시작을 승인받습니다. 강화 학습은 reward 가 올라갔다가 수렴하는 지점까지 학습합니다. 사용자의 경험상 20만 step 이상이 필요했습니다.
6. 본훈련은 `long-running-jobs` 스킬대로 세션과 분리된 프로세스로 돌리고, GPU 네 장에 나누어 싣습니다. 컴퓨터가 비정상 종료되어도 이어서 실행할 수 있도록 체크포인트와 재개 기능을 갖춥니다.
7. 결과를 아래처럼 남깁니다.
   - 학습 곡선을 그릴 수 있도록 학습 중 지표를 일정 간격(에피소드마다 또는 N step 마다)으로 CSV 에 기록합니다(`data/<방안>/learning_curve.csv`).
     20만 step 이상을 step 마다 기록하면 파일이 지나치게 커지므로, 기록 간격은 `config.md` 에 적어 모든 방안에 똑같이 적용합니다.
   - 수렴한 모델을 저장합니다(`data/<방안>/model_best.*`). 나중에 통신 성능 같은 다른 실험을 할 때 다시 학습하는 번거로움을 줄이기 위해서입니다.
   - 저장한 수렴 모델로 성능 지표를 뽑아 CSV 로 저장합니다(`data/<방안>/metrics.csv`).
8. critic 이 CSV 와 로그를 직접 읽어 수치가 비정상적이지 않은지, 방안 사이의 조건이 같은지 검증합니다.

## 산출물

- `performance_metrics.md`, `visualizer/config.md`(모델 순서와 색상)
- `data/hpo/hparam_space.csv`, `data/hpo/best_params.csv`
- 방안별 `learning_curve.csv`, 수렴 모델, `metrics.csv`

## 완료 조건

- `comparative_methods.md` 의 모든 비교 방안에 최적 하이퍼파라미터, 수렴 모델, 학습 곡선 CSV, 성능 CSV 가 있습니다.
- critic 의 결과 검증 보고서가 `review/` 에 있습니다.

## 되돌아가기 조건

- 비정상적이거나 지나치게 이상적인 수치가 나오면 3단계로 돌아갑니다.

## 사용자 명령 예시

> 비교 방안들의 성능을 먼저 뽑고 제안 방안을 거기에 비교해 가면서 개발할 테니, 비교 방안들의 정해진 성능을 평가하기 위한 코드를 구현해 줘.
> 성능 지표는 CSV 로 저장하고, learning curve 를 그릴 테니 그 기록은 꼭 남겨 둬. HPO 가 끝나 학습한 모델도 저장하고, 중간에 꺼져도 이어서 실행할 수 있게 해.

> 비교 방안 전체에 대한 optuna 최적화를 진행하고, 각 방안별 최적화된 하이퍼파라미터를 csv 로 저장해.
