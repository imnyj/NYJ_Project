"""
modules/models/__init__.py
==========================
Auto Stock ML/RL Trader — Milestone 2: 신경망 모델 및 하이브리드 RL 정책 패키지.

- SL Feature Extractors:
  - TabularMLPFeatureExtractor: 펀더멘털 및 계좌 상태 MLP
  - Temporal1DCNNFeatureExtractor: 시계열 모멘텀/변동성 1D-CNN
  - DualStreamSLFeatureExtractor: 1D-CNN + MLP 멀티모달 퓨전 백본
  - SLPretrainer: 익일 수익률 및 방향성 분류 멀티태스크 사전학습
- Hybrid RL Policies & Agents:
  - HybridActorCritic: Discrete(3) + Continuous([0, 1]) + Critic V(s)
  - HybridPPO: Native PyTorch GAE Clipped PPO 에이전트
  - SB3CustomFeaturesExtractor: Stable-Baselines3 호환 커스텀 특징 추출기
  - SB3HybridPolicyAdapter: SB3 Continuous Wrapper 연동 브릿지
"""

from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
    get_activation_fn,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)

__all__ = [
    # Feature Extractors & SL
    "get_activation_fn",
    "TabularMLPFeatureExtractor",
    "Temporal1DCNNFeatureExtractor",
    "DualStreamSLFeatureExtractor",
    "SLPretrainer",
    # Hybrid RL Policy & PPO
    "HybridActorCritic",
    "RolloutBuffer",
    "HybridPPO",
    "SB3CustomFeaturesExtractor",
    "SB3HybridPolicyAdapter",
]
