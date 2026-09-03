# Project: Auto_Stock Phase 6 - Main Model Architecture & Parallel Exploration

## Architecture Overview
Phase 6는 Auto_Stock 트레이딩 시스템의 본 모델(Main Model) 아키텍처 개발 및 대규모 병렬 HPO를 목표로 합니다.
1. **다중 지도학습(SL) 특징 추출기 계층 (`modules/models/`)**:
   - `TemporalResNetFeatureExtractor`: 1D-CNN 기반 Residual Block 및 Skip Connection 구조.
   - `TemporalTransformerFeatureExtractor`: Sinusoidal Positional Encoding + Multi-Head Self/Cross Attention + Context Attention Pooling.
   - `TemporalCVAEFeatureExtractor`: 조건부 변분 오토인코더(CVAE) 기반 잠재 특징 추출 및 재건 오차/KL 발산 기반 Anomaly Score 생성.
   - 다형적 입력 어댑터: 일봉 `(B, 20, 10)`, 분봉 `(B, 60, 10)`, 정적/계좌 `(B, 4)` 및 단일 텐서 `(B, 14)` 또는 `(B, 20, 10)`를 모두 수용하는 일관된 텐서 인터페이스.
2. **하이브리드 강화학습(RL) 통합 계층 (`modules/models/`, `modules/engine/`)**:
   - `SLEnrichedTradingEnvWrapper`: SL 모델의 예측 타겟(익일 기대 수익률 1차원, 3클래스 추세 확률 3차원, CVAE 이상치 점수 1차원)을 환경의 관측치에 동적으로 결합하여 18~19차원 확장 상태 $S_t^{aug}$ 생성.
   - `HybridActorCritic`: ResNet, Transformer, CVAE 인코더를 직접 백본으로 주입받아 PPO 기반 매수/매도/관망 및 비중 결정을 수행.
3. **대규모 HPO 파이프라인 계층 (`modules/hpo/`)**:
   - `optuna_pipeline.py`: 모델 아키텍처별 전용 탐색 공간(`suggest_model_params`) 및 하이브리드 목적함수(`objective_main_models`).
   - `exporter.py`: 기존 20개 컬럼 회귀 방지 보존 + `MAIN_MODELS_CSV_COLUMNS` 분리 정의, `fcntl.flock` 기반 `etc/hpo_results/main_models_hpo.csv` 안전 원자적 누적 저장.
4. **검증 및 감사 계층 (`tests/`)**:
   - `tests/test_phase6_models.py`: 3종 SL 모델의 동일 텐서 입력 대비 정상 Shape 출력 및 PPO 정책 결합 검증.
   - `tests/test_phase6_hpo.py`: 각 아키텍처별 Optuna n_trials=2 이상 크래시 없는 완주 및 `main_models_hpo.csv` 파일 생성 검증.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | F-P6-01 | 1D-CNN ResNet 특징 추출기 (`TemporalResNetFeatureExtractor`) | M1 | User Request R1 |
| 2 | F-P6-02 | 시계열 Attention Transformer (`TemporalTransformerFeatureExtractor`) | M1 | User Request R1 |
| 3 | F-P6-03 | 잠재 이상치 탐지 CVAE (`TemporalCVAEFeatureExtractor`) | M1 | User Request R1 |
| 4 | F-P6-04 | 다중 타임프레임 텐서 입력 공통 어댑터 및 베이스 인터페이스 | M1 | Survey Explorer 1/2 |
| 5 | F-P6-05 | SL 예측값 기반 관측치 확장 래퍼 (`SLEnrichedTradingEnvWrapper`) | M2 | User Request R2 |
| 6 | F-P6-06 | PPO Hybrid Actor-Critic 백본 결합 및 가중치 전이/고정 인터페이스 | M2 | User Request R2 |
| 7 | F-P6-07 | ResNet/Transformer/CVAE 아키텍처별 Optuna 탐색 공간 정의 | M3 | User Request R3 |
| 8 | F-P6-08 | HPO 결과 `etc/hpo_results/main_models_hpo.csv` 원자적 누적 저장기 | M3 | User Request R3 |
| 9 | F-P6-09 | SL 모델 입력/출력 텐서 Shape 자동화 테스트 (`tests/test_phase6_models.py`) | M4 | Acceptance Criteria |
| 10 | F-P6-10 | HPO 파이프라인 실행 및 CSV 저장 자동화 테스트 (`tests/test_phase6_hpo.py`) | M4 | Acceptance Criteria |
| 11 | F-P6-11 | 코드 리뷰, 적대적 챌린지 및 포렌식 무결성 전수 감사 | M5 | Acceptance Criteria & GEMINI |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | SL Architectures Implementation | `modules/models/resnet.py`, `transformer.py`, `cvae.py`, `__init__.py` | none | IN_PROGRESS |
| M2 | Hybrid RL Integration | `modules/models/hybrid_policy.py`, `modules/engine/hybrid_trading_env.py` | M1 | PLANNED |
| M3 | Large-scale HPO Pipeline | `modules/hpo/optuna_pipeline.py`, `modules/hpo/exporter.py` | M1, M2 | PLANNED |
| M4 | Automated Verification Test Suites | `tests/test_phase6_models.py`, `tests/test_phase6_hpo.py`, regression verification | M1, M2, M3 | PLANNED |
| M5 | Multi-Layer Audit & Review | Reviewers (2), Challengers (2), Forensic Auditor (1) | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### SL Models ↔ Gymnasium Env & Actor-Critic
- **입력**: `x: torch.Tensor (B, seq_len=20, in_channels=10)` 또는 `(B, 14)`
- **출력**: `features: torch.Tensor (B, feature_dim=64)`, `returns: torch.Tensor (B, 1)`, `trend_probs: torch.Tensor (B, 3)`, `anomaly_score: torch.Tensor (B, 1)`
- **Actor-Critic 연동**: `HybridActorCritic(feature_dim=64, action_dim=3, continuous_dim=1, feature_extractor=model)`
### HPO Exporter Contract
- **저장 경로**: `etc/hpo_results/main_models_hpo.csv`
- **동시성 안전**: `fcntl.flock(fd, fcntl.LOCK_EX)` + `threading.Lock()`
