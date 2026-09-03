## 2026-09-03T02:04:40Z
당신은 Auto_Stock Phase 6의 Milestone 1(SL 아키텍처 3종 구현) 전담 Worker (teamwork_preview_worker_p6_m1)입니다.

### 작업 환경
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p6_m1`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필수 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (반드시 먼저 정독할 것)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_6/SCOPE.md`
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_1/survey_models.md` (모델 아키텍처 상세 설계서)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_2/survey_rl_env.md` (RL 인터페이스 연동 설계서)
  - `/home/imnyj/GEMINI.md` (파일 락, 감사 로깅, etc 정리, 한국어 준수)

### 독점 파일 소유권 (Exclusive File Ownership)
당신은 오직 다음 파일들만 생성/수정할 권한이 있습니다:
- `modules/models/resnet.py` (신규 생성)
- `modules/models/transformer.py` (신규 생성)
- `modules/models/cvae.py` (신규 생성)
- `modules/models/__init__.py` (수정하여 신규 클래스 re-export, 기존 export 100% 보존)

### 핵심 작업 목표 (Milestone 1)
Explorer 1 및 2의 설계를 바탕으로 다음 3가지 SL 아키텍처 및 공통 인터페이스를 고품질 PyTorch 모듈로 완벽히 구현하십시오:
1. **공통 베이스 인터페이스 및 다형적 입력 어댑터**:
   - 일봉 `(B, seq_len=20, in_channels=10)`, 분봉 `(B, seq_len=60, in_channels=10)`, 정적/계좌 `(B, 4)` 뿐만 아니라, 단일 시계열 텐서 `(B, 20, 10)` 또는 단일 관측 벡터 `(B, 14)`가 입력되어도 결측/차원 불일치 없이 처리할 수 있는 유연한 어댑터 구현.
   - 모든 모델은 공통 특징 벡터 `(B, 64)`, 익일 기대 수익률 예측값 `(B, 1)`, 3클래스 추세 확률 `(B, 3)`, 그리고 잠재 벡터/이상치 점수 `(B, 1)`를 안정적으로 도출할 수 있어야 함.
2. **`TemporalResNetFeatureExtractor` (`modules/models/resnet.py`)**:
   - 1D-CNN 기반 `ResNet1DBlock` (Conv1d -> GroupNorm -> GELU -> Dropout -> Conv1d -> GroupNorm + Residual Connection / 1x1 Conv).
   - 다중 타임프레임 처리 및 특징 융합(Fusion) MLP를 통한 64차원 임베딩 생성.
3. **`TemporalTransformerFeatureExtractor` (`modules/models/transformer.py`)**:
   - Sinusoidal Positional Encoding + Pre-LN TransformerEncoderLayer(`norm_first=True`).
   - Self-Attention 및 `AttentionPooling1D`를 통한 시간 축 요약 및 64차원 특징 벡터 추출.
4. **`TemporalCVAEFeatureExtractor` (`modules/models/cvae.py`)**:
   - 조건부 변분 오토인코더: 인코더 $q(z|x, c)$, 디코더 $p(x|z, c)$, Reparameterization trick ($z = \mu + \sigma \odot \epsilon$).
   - 재건 오차와 KL 발산 기반 `AnomalyScore` 산출 메서드(`compute_anomaly_score`) 제공.
5. **안정성 및 호환성 방어**:
   - GPU/CPU 장치 자동 감지 (`.to(device)`), `torch.nan_to_num` 수치 안정성, eval 모드 동작, eval/train 전환 지원.
   - 기존 `modules/models/__init__.py`에서 새 클래스들을 노출하되 기존 `TabularMLPFeatureExtractor`, `DualStreamSLFeatureExtractor` 등이 깨지지 않도록 하위 호환성 유지.
