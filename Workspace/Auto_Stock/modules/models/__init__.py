"""
modules/models/__init__.py
==========================
Auto Stock ML/RL Trader — Milestone 2 & Phase 6: 신경망 모델 및 하이브리드 RL 정책 패키지.

- SL Feature Extractors (Phase 2 & Phase 6):
  - TabularMLPFeatureExtractor: 펀더멘털 및 계좌 상태 MLP
  - Temporal1DCNNFeatureExtractor: 시계열 모멘텀/변동성 1D-CNN
  - DualStreamSLFeatureExtractor: 1D-CNN + MLP 멀티모달 퓨전 백본
  - SLPretrainer: 익일 수익률 및 방향성 분류 멀티태스크 사전학습
  - BaseSLFeatureExtractor: 다중 타임프레임 공통 베이스 인터페이스 및 다형적 입력 어댑터
  - ResNet1DBlock: 1D-CNN 잔차 연결 블록
  - TemporalResNetFeatureExtractor: Phase 6 1D-CNN ResNet 특징 추출기
  - SinusoidalPositionalEncoding: 시계열 위치 인코딩
  - AttentionPooling1D: 학습 가능 쿼리 기반 1D Attention Pooling
  - CrossTimeframeAttention: 일봉-분봉 교차 어텐션 모듈
  - TemporalTransformerFeatureExtractor: Phase 6 시계열 Attention 기반 Transformer 특징 추출기
  - TemporalCVAEFeatureExtractor: Phase 6 조건부 변분 오토인코더(CVAE) 이상치 탐지 특징 추출기
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
from modules.models.resnet import (
    BaseSLFeatureExtractor,
    ResNet1DBlock,
    TemporalResNetFeatureExtractor,
)
from modules.models.transformer import (
    AttentionPooling1D,
    CrossTimeframeAttention,
    SinusoidalPositionalEncoding,
    TemporalTransformerFeatureExtractor,
)
from modules.models.cvae import (
    TemporalCVAEFeatureExtractor,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)

__all__ = [
    # Feature Extractors & SL (Phase 2)
    "get_activation_fn",
    "TabularMLPFeatureExtractor",
    "Temporal1DCNNFeatureExtractor",
    "DualStreamSLFeatureExtractor",
    "SLPretrainer",
    # Feature Extractors & SL (Phase 6)
    "BaseSLFeatureExtractor",
    "ResNet1DBlock",
    "TemporalResNetFeatureExtractor",
    "SinusoidalPositionalEncoding",
    "AttentionPooling1D",
    "CrossTimeframeAttention",
    "TemporalTransformerFeatureExtractor",
    "TemporalCVAEFeatureExtractor",
    # Hybrid RL Policy & PPO
    "HybridActorCritic",
    "RolloutBuffer",
    "HybridPPO",
    "SB3CustomFeaturesExtractor",
    "SB3HybridPolicyAdapter",
]
