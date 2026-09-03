# Original User Request

## 2026-09-02T01:55:10Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full Team

주식 자동 매매를 위한 Hybrid SL-RL 모델의 베이스라인(Baseline) 개발 및 Optuna 기반 하이퍼파라미터 최적화(HPO)를 수행합니다. 
`LiveLearningSimulator`에 가상의 스트리밍 데이터를 주입하여 시뮬레이션 환경을 구축하고, 연속형 비중 조절과 이산형 선택(Buy/Sell/Hold)이 결합된 하이브리드 액션 공간을 학습합니다. 최적화 결과를 CSV로 추출하여 향후 모델 고도화의 기준점(Benchmark)으로 활용합니다.

Working directory: /home/imnyj/Workspace/Auto_Stock
Integrity mode: benchmark

## Requirements

### R1. Hybrid Action Space Environment
`LiveLearningSimulator`를 래핑하거나 확장하여, OpenAI Gym (또는 Gymnasium) 호환 환경을 구축하세요.
행동 공간(Action Space)은 **이산형 선택(0: Hold, 1: Buy, 2: Sell)** 과 **연속형 비중 조절(0.0 ~ 1.0의 비율)** 이 결합된 하이브리드 형태(예: `spaces.Tuple` 혹은 `spaces.Dict`)여야 합니다.

### R2. SL & RL Baselines
외부 라이브러리(Stable-Baselines3, PyTorch 등)를 적극 활용하여, SL 특징 추출기(Feature Extractor)의 베이스라인(예: 단순 MLP 혹은 1D-CNN)과 RL 에이전트(예: PPO)의 베이스라인 코드를 작성하세요.

### R3. Optuna HPO Pipeline
`Optuna`를 사용하여 SL-RL 하이브리드 모델의 주요 하이퍼파라미터(예: 학습률, 배치 사이즈, 네트워크 차원 등)를 최적화하는 스크립트를 작성하세요. 
평가 지표는 에피소드 종료 시점의 총 수익금(Total Equity) 혹은 샤프 지수(Sharpe Ratio)로 설정하세요.

### R4. Results Export
Optuna Trial이 종료되면, 각 Trial의 파라미터 조합과 성능 평가 지표를 `etc/hpo_results/baseline_hpo.csv` 형태의 CSV 파일로 완벽하게 추출 및 저장하는 로직을 포함하세요.

## Acceptance Criteria

### Programmatic Verification (코드 기반 검증)
- [ ] 에이전트는 작성된 Optuna 스크립트를 `n_trials=3` 수준으로 시험 실행하는 자동화 검증 스크립트(`tests/test_hpo_pipeline.py` 또는 `make test-hpo`)를 작성하고 실행해야 합니다.
- [ ] 최적화 스크립트 실행 후 `baseline_hpo.csv` 파일이 정상적으로 생성되며, 3회 이상의 Trial 결과가 기록됨을 입증해야 합니다.
- [ ] 환경(Environment)의 `action_space` 타입이 이산형과 연속형을 모두 포함하는 구조(Tuple, Dict 등)임을 정적 분석 혹은 assert문으로 입증해야 합니다.
