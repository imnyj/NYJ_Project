## 2026-09-03T02:15:07Z

당신은 Auto_Stock Phase 6의 Milestone 2(하이브리드 강화학습 통합 - Hybrid RL Integration) 전담 Worker (teamwork_preview_worker_p6_m2)입니다.

### 작업 환경
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m2`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필수 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (반드시 먼저 정독할 것)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_6/SCOPE.md`
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/survey_rl_env.md` (RL 인터페이스 상세 연동 설계서)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m1/handoff.md` (M1에서 완성된 SL 아키텍처 3종 명세서)
  - `/home/imnyj/GEMINI.md` (파일 락, 감사 로깅, etc 정리, 한국어 준수)

### 독점 파일 소유권 (Exclusive File Ownership)
당신은 오직 다음 파일들만 생성/수정할 권한이 있습니다:
- `modules/engine/hybrid_trading_env.py` (또는 필요시 `modules/engine/sl_wrapper.py` 등 engine 패키지 내 신규 모듈)
- `modules/engine/__init__.py`
- `modules/models/hybrid_policy.py`

### 핵심 작업 목표 (Milestone 2 - Requirement R2)
Explorer 2의 연동 설계와 M1에서 완성된 3종 SL 모델(`TemporalResNetFeatureExtractor`, `TemporalTransformerFeatureExtractor`, `TemporalCVAEFeatureExtractor`)을 바탕으로 PPO 강화학습과의 완벽한 End-to-End 결합을 구현하십시오:

1. **SL 예측값 기반 관측치 확장 환경 래퍼 (`SLEnrichedTradingEnvWrapper`)**:
   - `modules/engine/hybrid_trading_env.py` (또는 연동 래퍼 모듈)에 구현.
   - Gymnasium 1.2.0 규격의 `gym.Wrapper` 상속.
   - SL 모델(ResNet, Transformer, CVAE 등 임의의 `BaseSLFeatureExtractor`)을 주입받아, 환경의 각 step마다:
     - 시계열/시장 관측치를 SL 모델에 전달하여 예측값(익일 기대 수익률 1D, 3클래스 추세 확률 3D, CVAE AnomalyScore 1D)을 계산.
     - 원본 14차원 관측치와 이 예측값들을 결합(Concatenate)하여 18~19차원의 확장된 상태 벡터 $S_t^{aug}$를 생성.
     - `observation_space`를 확장된 차원에 맞게 자동으로 갱신 (`Box(low=-inf, high=inf, shape=(18,), dtype=np.float32)` 등).
     - 결측치/NaN 방어 (`np.nan_to_num`) 및 `eval()` 모드 `torch.no_grad()` 환경에서 안정적으로 동작.

2. **`HybridActorCritic`의 다중 SL 백본 지원 및 End-to-End 결합 (`modules/models/hybrid_policy.py`)**:
   - `HybridActorCritic`이 기존 `TabularMLPFeatureExtractor`뿐만 아니라, M1에서 구현된 3종 SL 모델(`TemporalResNetFeatureExtractor`, `TemporalTransformerFeatureExtractor`, `TemporalCVAEFeatureExtractor`)을 `feature_extractor` 백본으로 자연스럽게 수용할 수 있도록 리팩토링 및 고도화.
   - 텐서 차원 불일치 방어: `forward`, `evaluate_actions`, `get_action_and_value` 메서드에서 다중 타임프레임/배치 차원을 안전하게 처리.
   - 가중치 동결 및 전이학습 지원: SL 사전학습 가중치를 로드하고 `freeze_feature_extractor()` 메서드를 통해 백본 가중치를 고정하거나 fine-tuning할 수 있도록 지원.
   - 팩토리 함수 `create_hybrid_agent(sl_model_type, ...)` 제공: "resnet", "transformer", "cvae" 문자열을 인자로 전달하면 해당 SL 백본이 결합된 PPO 에이전트(`HybridActorCritic`)를 원라인으로 생성할 수 있도록 구현.

3. **안정성 및 회귀 방지**:
   - 기존 `HybridTradingEnv` 및 `HybridActorCritic`의 기존 기능, 액션 공간(Discrete(3) + Box(1)), 1KRW 회계 불변식이 절대로 깨지지 않아야 함.
   - 기존 테스트 스위트(`tests/test_trading_env.py`, `tests/test_models.py`, `tests/test_adversarial_m2_rl_challenger.py`)가 100% Pass 상태를 유지해야 함.
