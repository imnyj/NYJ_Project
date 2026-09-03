# Milestone 2 독립 코드 리뷰 및 적대적 평가 보고서 (Handoff Report)

- **Reviewer**: 독립 리뷰어 2 (`teamwork_preview_reviewer_m2_2`)
- **Review Scope**: `modules/models/feature_extractor.py`, `modules/models/hybrid_policy.py`, `tests/test_models.py`
- **Verdict**: 🛑 **REQUEST_CHANGES**

---

## 1. Observation (직접 관찰 결과)

### 1.1 단위 및 통합 테스트 실행 결과
실행 명령어: `/home/imnyj/venv/bin/pytest tests/test_models.py tests/test_hybrid_trading_env.py -v`
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- /home/imnyj/venv/bin/python3
rootdir: /home/imnyj/Workspace/Auto_Stock
plugins: cov-7.1.0, asyncio-1.3.0, anyio-4.13.0, langsmith-0.7.33
collected 31 items

tests/test_models.py::TestSLFeatureExtractors::test_activation_function_factory PASSED [  3%]
tests/test_models.py::TestSLFeatureExtractors::test_tabular_mlp_forward_backward_and_residuals PASSED [  6%]
tests/test_models.py::TestSLFeatureExtractors::test_temporal_1dcnn_various_shapes_and_pooling PASSED [  9%]
tests/test_models.py::TestSLFeatureExtractors::test_dual_stream_sl_feature_extractor_fusion PASSED [ 12%]
tests/test_models.py::TestSLFeatureExtractors::test_sl_pretrainer_multitask_training_and_serialization PASSED [ 16%]
tests/test_models.py::TestHybridActorCriticAndPolicy::test_hybrid_actor_critic_beta_distribution PASSED [ 19%]
tests/test_models.py::TestHybridActorCriticAndPolicy::test_hybrid_actor_critic_gaussian_distribution PASSED [ 22%]
tests/test_models.py::TestHybridActorCriticAndPolicy::test_hybrid_actor_critic_evaluate_actions_and_entropy PASSED [ 25%]
tests/test_models.py::TestHybridActorCriticAndPolicy::test_sl_to_rl_weight_transfer_and_freezing PASSED [ 29%]
tests/test_models.py::TestHybridPPOAgent::test_rollout_buffer_gae_computation PASSED [ 32%]
tests/test_models.py::TestHybridPPOAgent::test_hybrid_ppo_training_loop_and_convergence PASSED [ 35%]
tests/test_models.py::TestHybridPPOAgent::test_hybrid_ppo_save_and_load PASSED [ 38%]
tests/test_models.py::TestSB3HybridAdapter::test_sb3_custom_features_extractor_forward PASSED [ 41%]
tests/test_models.py::TestSB3HybridAdapter::test_sb3_hybrid_adapter_train_and_predict PASSED [ 45%]
tests/test_models.py::TestModelsDeepHardeningAndEdgeCases::test_feature_extractor_exceptions_and_edge_paths PASSED [ 48%]
tests/test_models.py::TestModelsDeepHardeningAndEdgeCases::test_sl_pretrainer_mse_and_dict_and_tuple_batch PASSED [ 51%]
tests/test_models.py::TestModelsDeepHardeningAndEdgeCases::test_hybrid_policy_action_tensor_and_clip_vf_and_callbacks PASSED [ 54%]
tests/test_models.py::TestModelsDeepHardeningAndEdgeCases::test_sb3_custom_extractor_loading_and_weights_sync PASSED [ 58%]
tests/test_hybrid_trading_env.py::... (13 tests PASSED)

======================== 31 passed, 6 warnings in 5.68s ========================
```

### 1.2 코드 커버리지 측정 결과
실행 명령어: `/home/imnyj/venv/bin/coverage run --source=modules/models -m pytest tests/test_models.py -v && /home/imnyj/venv/bin/coverage report -m`
```text
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
modules/models/__init__.py                3      0   100%
modules/models/feature_extractor.py     403     38    91%   91, 202, 253-254, 258-259, 267-268, 273, 407, 410-411, 417, 420-424, 433, 439, 449, 451, 533-536, 551, 567, 599, 607, 615, 725, 733-737, 745, 760, 789
modules/models/hybrid_policy.py         436     50    89%   72-73, 83, 174-184, 201-211, 255-256, 277-284, 306-307, 343-345, 351, 356, 411, 489, 509-510, 514-517, 591, 619-621, 664, 725-726, 752, 768, 829, 831
-------------------------------------------------------------------
TOTAL                                   842     88    90%
```

### 1.3 적대적 스트레스 테스트 수행 중 직접 관찰된 런타임 크래시
독립 검증 스크립트: `.agents/teamwork_preview_reviewer_m2_2/test_adversarial_m2.py`
실행 결과 원문:
```text
Traceback (most recent call last):
  File "/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_m2_2/test_adversarial_m2.py", line 181, in test_sl_to_rl_weight_transfer_and_gradients
    feat_policy = policy.extract_features((t_x, tab_x))
  File "/home/imnyj/Workspace/Auto_Stock/modules/models/hybrid_policy.py", line 200, in extract_features
    feats = self.feature_extractor(obs)
  File "/home/imnyj/venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/imnyj/venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/imnyj/Workspace/Auto_Stock/modules/models/feature_extractor.py", line 416, in forward
    if temporal_x.dim() == 1:
AttributeError: 'tuple' object has no attribute 'dim'
```

---

## 2. Logic Chain & Detailed Findings

```
[Observation 1.3: DualStreamSLFeatureExtractor 위치 인자 전달 시 AttributeError 크래시 발생]
       │
       ▼ (Step 1: 매개변수 바인딩 불일치 분석)
  - modules/models/feature_extractor.py:373:
    `def forward(self, temporal_x=None, tabular_x=None, x=None)`
  - `model(obs)`로 호출 시 `obs`가 (tuple / dict / tensor) 형태여도 파이썬 위치 인자 규칙에 따라 첫 번째 매개변수인 `temporal_x`에 할당됨.
  - 389행의 분기 `if x is not None:`은 `x`가 `None`이므로 실행되지 않음.
  - 416행 `if temporal_x.dim() == 1:`에서 `tuple` 또는 `dict`에 대해 `.dim()`을 호출하여 `AttributeError` 발생.
       │
       ▼ (Step 2: 상위 호출자 예외 처리 누락 분석)
  - modules/models/hybrid_policy.py:198-210:
    `HybridActorCritic.extract_features`에서 `try: feats = self.feature_extractor(obs)`를 실행함.
    그러나 `except TypeError:`만 catch하도록 작성되어 있어, 내부에서 발생한 `AttributeError`가 잡히지 않고 외부로 전파되어 시스템 전체 크래시 유발.
       │
       ▼ (Step 3: 결론 도출)
  - 복합 관측값(Tuple, Dict)을 사용하는 환경 또는 RL 에이전트 연동 시 런타임 치명적 장애가 발생하므로 REQUEST_CHANGES 판정 필수.
```

### [Critical] Finding 1: `DualStreamSLFeatureExtractor.forward` 위치 인자 매핑 결함
- **Where**: `modules/models/feature_extractor.py:374-416`
- **Why**: 파이토치 모델에 단일 관측값(튜플, 딕셔너리, 복합 텐서)을 `model(obs)` 형태로 호출할 때, 첫 번째 위치 인수인 `temporal_x`에 바인딩되면서 `temporal_x.dim()` 호출 시 `AttributeError`가 발생합니다.
- **Suggestion**:
  `forward` 메서드 초입에 위치 인자로 전달된 튜플/딕셔너리/단일 텐서를 `x`로 자동 라우팅하는 안전 가드를 추가하세요:
  ```python
  if x is None and temporal_x is not None:
      if isinstance(temporal_x, (dict, tuple, list)) or (isinstance(temporal_x, torch.Tensor) and tabular_x is None):
          x = temporal_x
          temporal_x = None
  ```

### [Major] Finding 2: `HybridActorCritic.extract_features`의 예외 포착 범위 협소
- **Where**: `modules/models/hybrid_policy.py:198-210`
- **Why**: `try: feats = self.feature_extractor(obs)` 블록에서 오직 `except TypeError:`만 처리하고 있어, 특징 추출기 내부의 `AttributeError`, `ValueError` 등 파라미터 불일치 예외 발생 시 fallback 분기로 진입하지 못하고 크래시됩니다.
- **Suggestion**:
  `except (TypeError, AttributeError, ValueError):`로 포괄 처리하거나, `obs`의 타입(`isinstance(obs, (tuple, dict, ...))`)을 선제적으로 검사하여 적절한 인자 명칭으로 호출하도록 수정하세요.

### [Minor] Finding 3: `SB3HybridPolicyAdapter.predict_hybrid`의 배치 관측값 미지원
- **Where**: `modules/models/hybrid_policy.py:824-835`
- **Why**: `signal = float(raw_action[0])`으로 스칼라 변환을 강제하고 있어, 2D 배치 관측값 `(B, obs_dim)` 입력 시 `raw_action`이 `(B, 2)` 형태가 되어 `TypeError: only size-1 arrays can be converted to Python scalars` 에러가 발생합니다.
- **Suggestion**:
  단일 관측값(`raw_action.ndim == 1`)과 배치 관측값(`raw_action.ndim == 2`)을 모두 지원하도록 벡터화 디코딩 분기를 추가하세요.

### [Minor] Finding 4: `HybridActorCritic.load_from_sl_pretrainer`의 가중치 불일치 무음 통과
- **Where**: `modules/models/hybrid_policy.py:186-192`
- **Why**: 사전학습 가중치 로드 시 `strict=False`로 로드하면서 실제로 로드된 파라미터의 키 일치 여부를 검증하지 않아, 서로 다른 아키텍처의 백본이 전달되었을 때 아무런 경고 없이 전이학습이 누락될 수 있습니다.
- **Suggestion**:
  `incompatible_keys.missing_keys` 및 `unexpected_keys`를 확인하여 매핑된 파라미터가 전혀 없는 경우 경고 로그를 출력하도록 개선하세요.

---

## 3. Verified Claims & Robustness Highlights

독립 적대적 테스트를 통해 검증된 양호한 구현 사항:
- **수치적 안정성**:
  - `TabularMLPFeatureExtractor` 및 `Temporal1DCNNFeatureExtractor`에 `nan`, `inf`, `-inf`, `1e12` 등의 극단적 값을 전달했을 때 `torch.nan_to_num` 가드로 인해 안전하게 처리됨을 확인.
- **Beta / Gaussian 분포 경계 조건**:
  - Beta 분포 concentration 파라미터 `alpha, beta = F.softplus(...) + 1.0 + 1e-6` 적용으로 단봉성(Unimodal, $\alpha, \beta > 1$)이 엄격히 보장됨.
  - `torch.clamp(cont_act, 1e-6, 1.0 - 1e-6)` 가드로 경계값($0.0, 1.0$)에서의 log_prob 발산이 원천 차단됨.
- **단일 관측값 GroupNorm 내결함성**:
  - `Temporal1DCNNFeatureExtractor`에서 `GroupNorm`을 기본 적용하여 배치 크기 1 ($B=1$) 또는 unbatched 관측값에서도 분산 계산 오류 없이 정상 동작 확인.
- **GAE 무결성 및 어드밴티지 제로 분산 방어**:
  - 어드밴티지 표준편차가 0인 경우에도 `adv_std = adv.std() + 1e-8` 가드가 적용되어 Zero-Division 오류 없음 확인.

---

## 4. Caveats (주의사항 및 한계)

- **리뷰 전용 원칙 준수**: 리뷰어는 프로토콜에 따라 구현 코드를 직접 수정하지 않고, Worker가 정확한 위치와 수정 코드를 식별하여 교정할 수 있도록 상세한 가이드를 제공합니다.
- **SB3 GPU 경고**: SB3 PPO 실행 시 발생하는 GPU 권장 안내 경고(`UserWarning`)는 SB3의 자체 메시지이며 알고리즘 무결성에는 영향이 없습니다.

---

## 5. Conclusion (최종 판정 및 조치 권고)

- **Verdict**: 🛑 **`REQUEST_CHANGES`**
- **Action Items**:
  1. `modules/models/feature_extractor.py`: `DualStreamSLFeatureExtractor.forward`에서 위치 인자로 전달된 튜플/딕셔너리/단일 텐서에 대한 자동 `x` 라우팅 가드 추가.
  2. `modules/models/hybrid_policy.py`: `HybridActorCritic.extract_features`의 예외 포착 범위 확장 및 `SB3HybridPolicyAdapter.predict_hybrid` 배치 입력 지원.
  3. 수정 완료 후 `tests/test_models.py` 및 적대적 스트레스 테스트 재실행 확인.

---

## 6. Verification Method (독립 재현 검증 방법)

다음 명령어를 통해 본 보고서에서 지적한 버그 및 검증 항목을 재현할 수 있습니다:

```bash
# 1. 적대적 스트레스 테스트 실행 (현재 Finding 1로 인해 실패 재현)
/home/imnyj/venv/bin/python3 /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_m2_2/test_adversarial_m2.py

# 2. 기존 단위 및 통합 테스트 스위트 실행
/home/imnyj/venv/bin/pytest tests/test_models.py tests/test_hybrid_trading_env.py -v

# 3. 모델 커버리지 측정
/home/imnyj/venv/bin/coverage run --source=modules/models -m pytest tests/test_models.py -v && /home/imnyj/venv/bin/coverage report -m
```
