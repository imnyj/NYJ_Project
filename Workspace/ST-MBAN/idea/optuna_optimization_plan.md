# Comprehensive Optuna Optimization Plan (종합 최적화 계획서)

모든 13개 비교 모델에 대해 가장 공정한 성능 평가(Fairness)를 달성하기 위해, 단순한 Depth/Layer뿐만 아니라 모델 특성에 맞는 **학습률(lr), 정규화(weight_decay, L2), 트리 구조(gamma, subsample)** 등 필수 하이퍼파라미터 공간을 전면적으로 탐색합니다.

---

## 1. Deep Learning Models (딥러닝 기반)
기본적으로 모든 딥러닝 모델은 Adam/AdamW 옵티마이저를 사용하며, 다음 파라미터들을 공통 및 개별적으로 튜닝합니다.

| Model | Hyperparameters to Tune | Search Space (Range / Categories) | Description |
| :--- | :--- | :--- | :--- |
| **ST-MBAN** (제안) | `d_model` <br> `num_layers` <br> `n_heads` <br> `lr` <br> `weight_decay` | [64, 128, 256, 512] <br> [2, 3, 4, 5, 6] <br> [2, 4, 8] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | 제안 방안의 어텐션 차원, 깊이 및 정규화 규제 최적화 |
| **MLP** | `hidden_dim` <br> `num_layers` <br> `dropout` <br> `lr` <br> `weight_decay` | [64, 128, 256, 512] <br> [2, 3, 4, 5, 6] <br> [0.0 ~ 0.5] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | 다층 퍼셉트론의 비대해짐을 막기 위한 Dropout 포함 |
| **LSTM / GRU** | `hidden_dim` <br> `num_layers` <br> `dropout` <br> `lr` <br> `weight_decay` | [32, 64, 128, 256] <br> [1, 2, 3, 4] <br> [0.0 ~ 0.5] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | 시계열 모델 특성상 과적합 방지를 위한 구조 최적화 |
| **TabR** | `hidden_dim` <br> `num_layers` <br> `lr` <br> `weight_decay` | [64, 128, 256, 512] <br> [1, 2, 3, 4] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | 정형 데이터 특화 딥러닝 모델의 Block Size 및 Depth |
| **FTT** | `d_model` <br> `num_layers` <br> `n_heads` <br> `lr` <br> `weight_decay` | [32, 64, 128, 256] <br> [1, 2, 3, 4] <br> [2, 4, 8] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | Feature Tokenizer Transformer의 임베딩 차원 및 어텐션 노드 |
| **ResNet** | `hidden_dim` <br> `num_layers` <br> `dropout` <br> `lr` <br> `weight_decay` | [64, 128, 256, 512] <br> [2, 3, 4, 5, 6] <br> [0.0 ~ 0.5] <br> [1e-5 ~ 1e-2] (log) <br> [1e-6 ~ 1e-2] (log) | 잔차 연결(Residual) 블록 수와 폭 조절 |

---

## 2. Machine Learning Models (트리/앙상블 기반)
머신러닝 모델들은 구조가 다르므로 트리 성장 및 가지치기와 관련된 파라미터들을 심층적으로 탐색합니다.

| Model | Hyperparameters to Tune | Search Space (Range / Categories) | Description |
| :--- | :--- | :--- | :--- |
| **XGBoost** | `n_estimators` <br> `max_depth` <br> `learning_rate` <br> `subsample` <br> `colsample_bytree` <br> `gamma` | [50 ~ 500] <br> [3 ~ 15] <br> [1e-3 ~ 0.3] (log) <br> [0.5 ~ 1.0] <br> [0.5 ~ 1.0] <br> [0 ~ 5] | 트리 개수, 깊이, 샘플링 비율, 최소 손실 감소(gamma) 등 포괄적 튜닝 |
| **RandomForest**| `n_estimators` <br> `max_depth` <br> `min_samples_split` <br> `min_samples_leaf` | [50 ~ 500] <br> [5 ~ 30] <br> [2 ~ 10] <br> [1 ~ 10] | 앙상블 다양성 확보 및 과적합 제어 (가지치기) |
| **CatBoost** | `iterations` <br> `depth` <br> `learning_rate` <br> `l2_leaf_reg` | [50 ~ 500] <br> [4 ~ 10] <br> [1e-3 ~ 0.3] (log) <br> [1 ~ 10] | 범주형 데이터 처리 트리의 뎁스 및 L2 정규화 |
| **NGBoost** | `n_estimators` <br> `learning_rate` <br> `minibatch_frac` | [50 ~ 500] <br> [1e-3 ~ 0.3] (log) <br> [0.5 ~ 1.0] | 자연 기울기 부스팅의 학습률 및 배치 샘플링 |
| **TabPFN** | `N/A` (사전 학습 모델) | `N/A` | TabPFN은 in-context learning을 수행하므로 하이퍼파라미터 튜닝 대상에서 제외 |
| **LR (Ridge)** | `alpha` (L2 Penalty) | [1e-4 ~ 1e2] (log) | 기본 선형 회귀에 L2 규제를 도입하여 최적화 |

---

## 3. 평가 방식 및 소요 시간 예상
* **지표**: Validation Set에 대한 MSE(Mean Squared Error)를 Objective로 하여 최소화.
* **조기 종료(Pruning)**: 딥러닝 모델의 경우 Optuna의 `MedianPruner`를 도입하여, 초반 Epoch에서 수렴 가능성이 없는 Trial은 과감히 버려 연산 시간을 절약.
* **Trial 수**: 각 모델당 **20 ~ 30회**의 폭넓은 탐색 수행.

위 계획서에 동의하시면 해당 스페이스를 바탕으로 최적화 스크립트를 재작성하여 백그라운드 구동을 시작하겠습니다! 추가하거나 빼고 싶은 파라미터가 있으신가요?
