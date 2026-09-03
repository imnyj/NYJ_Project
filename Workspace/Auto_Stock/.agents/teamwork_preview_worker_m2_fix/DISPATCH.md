## 2026-09-02T02:24:13Z
당신은 Auto_Stock 프로젝트 Milestone 2 결함 수정 및 보강 담당 Worker (`teamwork_preview_worker_m2_fix`)입니다.

### 작업 환경
- Your Working Directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2_fix/
- Project Directory: /home/imnyj/Workspace/Auto_Stock
- Original Request File: /home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md
- Project Scope Document: /home/imnyj/Workspace/Auto_Stock/PROJECT.md
- Gate Review Feedback:
  - Reviewer 1 Handoff: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_m2_1/handoff.md
  - Reviewer 2 Handoff: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_m2_2/handoff.md

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 파일 소유권 (Write Ownership)
- `modules/models/feature_extractor.py`
- `modules/models/hybrid_policy.py`
- `tests/test_models.py`

### 수정 및 보강 요구사항
1. **`modules/models/hybrid_policy.py` 수정**:
   - `RolloutBuffer.compute_returns_and_advantages()`: `self.dones[step + 1]` 오프셋 오류를 수정하여, step $t$의 종료 여부 `self.dones[step]`에 따라 `next_non_terminal = 1.0 - self.dones[step]`이 정확히 적용되도록 수정. 에피소드 경계에서 가치 누수 방지.
   - `HybridActorCritic.extract_features()`: `try ... except (TypeError, AttributeError, ValueError):`로 예외를 포괄 처리하고, 단일 관측값(tuple, dict, tensor) 전달 시 백본에 안전하게 바인딩되도록 개선.
   - `SB3HybridPolicyAdapter.predict_hybrid()`: 2D 배치 액션(`raw_action.ndim == 2`)과 1D 액션을 모두 지원하도록 배치 차원 처리 추가.
2. **`modules/models/feature_extractor.py` 수정**:
   - `Temporal1DCNNFeatureExtractor.forward()`: 2D 텐서 판별 시 배치 크기가 `seq_len`(기본값 20)인 경우(`(20, in_channels)`) 평탄화된 배치로 오인식하지 않도록 명확한 차원 분기 로직 적용.
   - `DualStreamSLFeatureExtractor.forward()`: 단일 위치 인자 `forward(obs)`로 tuple `(temporal, tabular)` 또는 dict `{"temporal": ..., "tabular": ...}`가 유입될 때 안전하게 파싱하여 `AttributeError` 방어.
3. **`tests/test_models.py` 단위 테스트 보강**:
   - 상기 5개 결함 시나리오(GAE 에피소드 경계 단절 검증, DualStream 위치 인자 전달, B=20 2D 텐서 forward, SB3 2D 배치 예측)에 대한 회귀 방지 테스트 추가.
4. **전체 테스트 실행 및 검증**:
   - `/home/imnyj/venv/bin/pytest tests/test_models.py tests/test_hybrid_trading_env.py -v` 실행하여 100% 통과 확인.
5. **최종 보고서 작성**:
   - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2_fix/handoff.md`에 5-Component 형식으로 수정 내역과 테스트 로그를 기록하고 오케스트레이터에게 완료 메시지를 보내세요.
