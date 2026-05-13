"""
mafac_agent.py
==============
Multi-Agent Federated Actor-Critic (MAFAC) - Proposed Algorithm.

Architecture:
  - Factored Actor: separate sub-actors for each action dimension
    (forwarding, caching, power, subchannel)
  - Critic: centralized value function with Lagrangian advantage
  - Lagrange multipliers: dual ascent for constraint satisfaction
  - Federated: critic-only aggregation with inverse-AoI weighting

References:
  - Factored MDP: Guestrin et al. (2003)
  - Lagrangian CMDP: Altman (1999)
  - FedAvg: McMahan et al. (2017)

CHANGES (GPU/Speed Refactor):
  - __init__: `device` 파라미터 추가. actor, critic, critic_target 모두 .to(self.device).
  - select_action: torch.from_numpy().float().unsqueeze(0).to(self.device)
  - _update_torch: 완전 재작성.
      * 모든 텐서 .to(self.device)
      * next_action 계산: 기존 256번 단일 forward → 1번 batch forward (Categorical sampling)
      * actor update advantage: Q(s, a_sampled) - Q(s, a_old) 각 1회 critic 호출로 통합
      * _onehot_actions_torch(): numpy 경유 없이 GPU 상에서 직접 one-hot 인코딩
  - save_checkpoint / load_checkpoint: actor_opt, critic_opt state_dict 및
      lagrange_lambda, total_steps 포함.
"""

import math
import random
import copy
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import deque

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[mafac_agent] WARNING: PyTorch not available. Using numpy fallback.")


# ─────────────────────────────────────────────────────────────────────────────
# Neural Network Modules
# ─────────────────────────────────────────────────────────────────────────────
if TORCH_AVAILABLE:
    class MLP(nn.Module):
        """Generic Multi-Layer Perceptron."""
        def __init__(self, input_dim: int, hidden_dims: List[int],
                     output_dim: int, activation=nn.ReLU):
            super().__init__()
            layers = []
            prev = input_dim
            for h in hidden_dims:
                layers += [nn.Linear(prev, h), activation()]
                prev = h
            layers.append(nn.Linear(prev, output_dim))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)

    class FactoredActor(nn.Module):
        """
        Factored action-space actor.
        Outputs independent logits for each sub-action:
          - forwarding (3 choices)
          - caching    (2 choices)
          - power      (5 choices)
          - subchannel (NUM_SUBCH choices)
        """
        def __init__(self, obs_dim: int,
                     action_dims: Tuple[int, int, int, int],
                     hidden_dims: List[int] = [128, 128]):
            super().__init__()
            self.action_dims = action_dims
            # Shared encoder
            self.encoder = MLP(obs_dim, hidden_dims[:-1], hidden_dims[-1])
            # Sub-actor heads
            self.head_fwd   = nn.Linear(hidden_dims[-1], action_dims[0])
            self.head_cache = nn.Linear(hidden_dims[-1], action_dims[1])
            self.head_power = nn.Linear(hidden_dims[-1], action_dims[2])
            self.head_subch = nn.Linear(hidden_dims[-1], action_dims[3])

        def forward(self, obs: torch.Tensor
                    ) -> Tuple[torch.Tensor, ...]:
            """Returns logits for each sub-action. Works for both (D,) and (B, D) inputs."""
            h = F.relu(self.encoder(obs))
            return (self.head_fwd(h),
                    self.head_cache(h),
                    self.head_power(h),
                    self.head_subch(h))

        def get_action(self, obs: torch.Tensor, deterministic: bool = False
                       ) -> Tuple[np.ndarray, torch.Tensor]:
            """Sample or argmax action for a SINGLE observation, return (action_array, log_prob).
            obs should be shape (1, obs_dim) — used only at inference time."""
            logits = self.forward(obs)
            actions = []
            log_probs = []
            for lgts in logits:
                dist = torch.distributions.Categorical(logits=lgts)
                if deterministic:
                    a = lgts.argmax(dim=-1)
                else:
                    a = dist.sample()
                log_probs.append(dist.log_prob(a))
                actions.append(a)
            # Combined log-prob (factored → sum of independent log-probs)
            total_log_prob = sum(log_probs)
            action_np = np.array([a.item() for a in actions], dtype=np.int32)
            return action_np, total_log_prob

    class CentralizedCritic(nn.Module):
        """
        Critic network for value estimation.
        Input: concatenated [obs, action_onehot]
        Output: scalar V(s) or Q(s,a)
        """
        def __init__(self, obs_dim: int,
                     action_dims: Tuple[int, int, int, int],
                     hidden_dims: List[int] = [256, 256]):
            super().__init__()
            total_action_dim = sum(action_dims)
            self.net = MLP(obs_dim + total_action_dim,
                           hidden_dims, 1)

        def forward(self, obs: torch.Tensor,
                    actions_oh: torch.Tensor) -> torch.Tensor:
            x = torch.cat([obs, actions_oh], dim=-1)
            return self.net(x).squeeze(-1)


# ─────────────────────────────────────────────────────────────────────────────
# Numpy Fallback (when PyTorch unavailable)
# ─────────────────────────────────────────────────────────────────────────────
class NumpyPolicy:
    """Simple softmax policy implemented with numpy (fallback)."""
    def __init__(self, obs_dim: int,
                 action_dims: Tuple[int, int, int, int],
                 seed: int = 42):
        self.action_dims = action_dims
        self._rng = np.random.default_rng(seed)
        # Random weights for each sub-action
        self._weights = [
            self._rng.standard_normal((obs_dim, d)) * 0.01
            for d in action_dims
        ]

    def get_action(self, obs: np.ndarray,
                   deterministic: bool = False) -> np.ndarray:
        actions = []
        for w in self._weights:
            logits = obs @ w
            if deterministic:
                a = np.argmax(logits)
            else:
                probs = np.exp(logits - logits.max())
                probs /= probs.sum()
                a = self._rng.choice(len(probs), p=probs)
            actions.append(a)
        return np.array(actions, dtype=np.int32)

    def get_state_dict(self):
        return {"weights": [w.copy() for w in self._weights]}

    def load_state_dict(self, d):
        self._weights = [w.copy() for w in d["weights"]]


# ─────────────────────────────────────────────────────────────────────────────
# Replay Buffer
# ─────────────────────────────────────────────────────────────────────────────
class ReplayBuffer:
    def __init__(self, capacity: int = 100000):
        self._buf = deque(maxlen=capacity)

    def push(self, obs, action, reward, next_obs, done,
             constraint_violation: float = 0.0):
        self._buf.append((obs, action, reward, next_obs, done,
                          constraint_violation))

    def sample(self, batch_size: int):
        idxs = random.sample(range(len(self._buf)), batch_size)
        batch = [self._buf[i] for i in idxs]
        obs, acts, rews, next_obs, dones, cvs = zip(*batch)
        return (np.array(obs, dtype=np.float32),
                np.array(acts, dtype=np.int32),
                np.array(rews, dtype=np.float32),
                np.array(next_obs, dtype=np.float32),
                np.array(dones, dtype=np.float32),
                np.array(cvs, dtype=np.float32))

    def state_dict(self) -> list:
        """Return a serialisable snapshot of the buffer (list of tuples)."""
        return list(self._buf)

    def load_state_dict(self, data: list):
        """Restore buffer from a snapshot."""
        self._buf = deque(data, maxlen=self._buf.maxlen)

    def __len__(self):
        return len(self._buf)


# ─────────────────────────────────────────────────────────────────────────────
# MAFAC Agent
# ─────────────────────────────────────────────────────────────────────────────
class MAFACAgent:
    """
    Per-vehicle MAFAC agent.
    Each vehicle maintains its own actor; critics are federated.

    GPU 지원:
      - device 파라미터로 "cuda" / "cpu" 지정 (None이면 자동 감지).
      - actor, critic, critic_target 모두 self.device로 이동.
      - _update_torch()는 모든 텐서를 GPU에서 처리.
    """

    def __init__(
        self,
        agent_id: str,
        obs_dim: int,
        action_dims: Tuple[int, int, int, int],
        actor_lr: float = 3e-4,
        critic_lr: float = 1e-3,
        lagrange_lr: float = 0.01,
        gamma: float = 0.99,
        tau: float = 0.005,
        batch_size: int = 256,
        buffer_size: int = 100000,
        constraint_threshold: float = 0.65,  # CBR threshold
        seed: int = 42,
        device: str = None,  # NEW: GPU device string
        entropy_coef: float = 0.01,  # NEW: entropy bonus coefficient
    ):
        self.agent_id    = agent_id
        self.obs_dim     = obs_dim
        self.action_dims = action_dims
        self.gamma       = gamma
        self.tau         = tau
        self.batch_size  = batch_size
        self.constraint_threshold = constraint_threshold
        self._rng        = random.Random(seed)
        self.entropy_coef = entropy_coef

        # ── Device setup ───────────────────────────────────────────────────
        if TORCH_AVAILABLE:
            if device is not None:
                self.device = torch.device(device)
            else:
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = None

        # Replay buffer
        self.buffer = ReplayBuffer(buffer_size)

        # ── Actor ──────────────────────────────────────────────────────────
        if TORCH_AVAILABLE:
            self.actor = FactoredActor(obs_dim, action_dims).to(self.device)
            self.actor_opt = optim.Adam(self.actor.parameters(), lr=actor_lr)

            # Critic + target (both moved to device)
            self.critic = CentralizedCritic(obs_dim, action_dims).to(self.device)
            self.critic_target = copy.deepcopy(self.critic).to(self.device)
            self.critic_opt = optim.Adam(self.critic.parameters(), lr=critic_lr)
        else:
            self.actor = NumpyPolicy(obs_dim, action_dims, seed)
            self.critic = None
            self.critic_target = None
            self.device = None

        # ── Lagrange multiplier ────────────────────────────────────────────
        self.lagrange_lambda = 0.0  # multiplier for CBR constraint
        self.lagrange_lr     = lagrange_lr

        # ── Statistics ────────────────────────────────────────────────────
        self.total_steps     = 0
        self.total_updates   = 0
        self.actor_loss_hist  = []
        self.critic_loss_hist = []
        self.lambda_hist      = []

    # ── Action Selection ──────────────────────────────────────────────────────
    def select_action(self, obs: np.ndarray,
                      deterministic: bool = False) -> np.ndarray:
        """Select factored action for current observation."""
        if TORCH_AVAILABLE:
            # GPU 전송 포함
            obs_t = torch.from_numpy(obs).float().unsqueeze(0).to(self.device)
            with torch.no_grad():
                action, _ = self.actor.get_action(obs_t, deterministic)
            return action
        else:
            return self.actor.get_action(obs, deterministic)

    # ── Experience Storage ────────────────────────────────────────────────────
    def store_experience(self, obs, action, reward, next_obs, done,
                         constraint_violation: float = 0.0):
        self.buffer.push(obs, action, reward, next_obs, done, constraint_violation)
        self.total_steps += 1

    # ── Training ─────────────────────────────────────────────────────────────
    def update(self) -> Optional[dict]:
        """Perform one gradient update step."""
        if len(self.buffer) < self.batch_size:
            return None

        if not TORCH_AVAILABLE:
            return self._update_numpy()

        return self._update_torch()

    def _onehot_actions_torch(self, acts_np: np.ndarray) -> torch.Tensor:
        """
        GPU-native one-hot encoding.
        acts_np: (B, 4) int32 numpy array
        Returns: (B, sum(action_dims)) float32 tensor on self.device
        """
        B = acts_np.shape[0]
        total_dim = sum(self.action_dims)
        result = torch.zeros(B, total_dim, dtype=torch.float32, device=self.device)
        offset = 0
        acts_t = torch.from_numpy(acts_np.astype(np.int64)).to(self.device)
        for i, d in enumerate(self.action_dims):
            col = acts_t[:, i].clamp(0, d - 1)
            result.scatter_(1, (col + offset).unsqueeze(1), 1.0)
            offset += d
        return result

    def _update_torch(self) -> dict:
        """
        완전 재작성 (GPU 벡터화).

        핵심 개선:
          1) 모든 텐서 → self.device (GPU)
          2) next_action 계산: 256번 단일 forward → 1번 batch forward
          3) actor update advantage: Q(s, a_sampled) - Q(s, a_old) 각 1회 호출로 통합
          4) one-hot 인코딩 GPU 직접 수행 (numpy 왕복 없음)
        """
        obs, acts, rews, next_obs, dones, cvs = self.buffer.sample(self.batch_size)

        # ── 모든 기본 텐서 GPU로 ──────────────────────────────────────────
        obs_t      = torch.from_numpy(obs).float().to(self.device)       # (B, obs_dim)
        next_obs_t = torch.from_numpy(next_obs).float().to(self.device)  # (B, obs_dim)
        rews_t     = torch.from_numpy(rews).float().to(self.device)      # (B,)
        dones_t    = torch.from_numpy(dones).float().to(self.device)     # (B,)
        cvs_t      = torch.from_numpy(cvs).float().to(self.device)       # (B,)

        # ── One-hot encode current actions (GPU 직접) ─────────────────────
        acts_oh_t = self._onehot_actions_torch(acts)  # (B, sum(dims))

        # ── Critic update ──────────────────────────────────────────────────
        with torch.no_grad():
            # [개선] next_action: 기존 256번 단일 forward → 1번 batch forward
            next_logits = self.actor(next_obs_t)  # tuple of (B, d_i), single pass
            next_acts_list = []
            for lgts in next_logits:
                dist = torch.distributions.Categorical(logits=lgts)
                next_acts_list.append(dist.sample())  # (B,)
            next_acts = torch.stack(next_acts_list, dim=1)  # (B, 4)

            # One-hot for next actions (GPU)
            next_acts_np = next_acts.cpu().numpy().astype(np.int32)
            next_acts_oh = self._onehot_actions_torch(next_acts_np)  # (B, sum(dims))

            # Target value with Lagrangian correction
            target_v = self.critic_target(next_obs_t, next_acts_oh)  # (B,)
            # Lagrangian: subtract lambda * constraint violation from reward
            target_q = (rews_t - self.lagrange_lambda * cvs_t
                        + self.gamma * (1.0 - dones_t) * target_v)   # (B,)

        current_q = self.critic(obs_t, acts_oh_t)  # (B,)
        critic_loss = F.mse_loss(current_q, target_q.detach())

        self.critic_opt.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), 1.0)
        self.critic_opt.step()

        # ── Soft update target critic ─────────────────────────────────────
        for tp, p in zip(self.critic_target.parameters(),
                         self.critic.parameters()):
            tp.data.copy_(self.tau * p.data + (1.0 - self.tau) * tp.data)

        # ── Actor update ───────────────────────────────────────────────────
        # Actor update — unbiased on-policy advantage + entropy bonus
        logits = self.actor(obs_t)  # tuple of (B, d_i)

        with torch.no_grad():
            # 모든 sub-action을 current policy에서 샘플링 (advantage 계산용)
            onpolicy_samples = []
            for lgts in logits:
                dist = torch.distributions.Categorical(logits=lgts)
                onpolicy_samples.append(dist.sample())
            onpolicy_acts = torch.stack(onpolicy_samples, dim=1)  # (B, 4)
            onpolicy_oh = self._onehot_actions_torch(onpolicy_acts.cpu().numpy().astype('int32'))
            onpolicy_q = self.critic(obs_t, onpolicy_oh)
            baseline_q = self.critic(obs_t, acts_oh_t)
            advantage = (onpolicy_q - baseline_q).detach()

        # Policy gradient (REINFORCE-style) + entropy
        actor_loss_parts = []
        entropy_total = 0.0
        for i, lgts in enumerate(logits):
            dist = torch.distributions.Categorical(logits=lgts)
            log_p = dist.log_prob(onpolicy_samples[i])  # 그래프 연결됨
            actor_loss_parts.append(-(log_p * advantage).mean())
            entropy_total = entropy_total + dist.entropy().mean()

        actor_loss = sum(actor_loss_parts) - self.entropy_coef * entropy_total

        self.actor_opt.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.actor.parameters(), 1.0)
        self.actor_opt.step()

        # ── Lagrange multiplier update ────────────────────────────────────
        # Dual ascent: lambda += lr * E[constraint_violation - threshold]
        mean_cv = cvs_t.mean().item()
        grad_lambda = mean_cv - self.constraint_threshold
        self.lagrange_lambda = max(0.0,
            self.lagrange_lambda + self.lagrange_lr * grad_lambda)

        # ── Logging ────────────────────────────────────────────────────────
        c_loss = critic_loss.item()
        a_loss = actor_loss.item()
        self.critic_loss_hist.append(c_loss)
        self.actor_loss_hist.append(a_loss)
        self.lambda_hist.append(self.lagrange_lambda)
        self.total_updates += 1

        return {
            "critic_loss":  c_loss,
            "actor_loss":   a_loss,
            "lambda":       self.lagrange_lambda,
            "mean_cv":      mean_cv,
        }

    def _update_numpy(self) -> dict:
        """Numpy-based update (no gradients)."""
        obs, acts, rews, next_obs, dones, cvs = self.buffer.sample(self.batch_size)
        mean_cv = float(np.mean(cvs))
        self.lagrange_lambda = max(0.0,
            self.lagrange_lambda + self.lagrange_lr * (mean_cv - self.constraint_threshold))
        self.total_updates += 1
        self.lambda_hist.append(self.lagrange_lambda)
        return {"critic_loss": 0.0, "actor_loss": 0.0,
                "lambda": self.lagrange_lambda, "mean_cv": mean_cv}

    def _onehot_actions(self, acts: np.ndarray) -> np.ndarray:
        """Convert integer action array (B, 4) to one-hot (B, sum(dims)).
        Kept for backward compatibility; internal code uses _onehot_actions_torch()."""
        B = acts.shape[0]
        result = np.zeros((B, sum(self.action_dims)), dtype=np.float32)
        offset = 0
        for i, d in enumerate(self.action_dims):
            for b in range(B):
                a = min(acts[b, i], d - 1)
                result[b, offset + a] = 1.0
            offset += d
        return result

    # ── Model State ──────────────────────────────────────────────────────────
    def get_critic_params(self):
        """Return critic parameters for federated aggregation."""
        if TORCH_AVAILABLE and self.critic is not None:
            return {k: v.cpu().clone() for k, v in self.critic.state_dict().items()}
        else:
            return {}

    def set_critic_params(self, params: dict):
        """Load aggregated critic parameters."""
        if TORCH_AVAILABLE and self.critic is not None:
            self.critic.load_state_dict(params)
            self.critic_target.load_state_dict(params)
            # Move loaded params to correct device
            self.critic.to(self.device)
            self.critic_target.to(self.device)

    def get_actor_params(self):
        if TORCH_AVAILABLE:
            return {k: v.cpu().clone() for k, v in self.actor.state_dict().items()}
        else:
            return self.actor.get_state_dict()

    def load_checkpoint(self, path: str):
        """Load full checkpoint including optimizer states and metadata."""
        if TORCH_AVAILABLE:
            ckpt = torch.load(path, map_location=self.device)
            self.actor.load_state_dict(ckpt["actor"])
            self.actor.to(self.device)
            if "actor_opt" in ckpt:
                self.actor_opt.load_state_dict(ckpt["actor_opt"])
            if "critic" in ckpt and self.critic is not None:
                self.critic.load_state_dict(ckpt["critic"])
                self.critic_target.load_state_dict(ckpt.get("critic_target",
                                                             ckpt["critic"]))
                self.critic.to(self.device)
                self.critic_target.to(self.device)
            if "critic_opt" in ckpt and self.critic_opt is not None:
                self.critic_opt.load_state_dict(ckpt["critic_opt"])
            self.lagrange_lambda = ckpt.get("lambda", 0.0)
            self.total_steps     = ckpt.get("total_steps", self.total_steps)

    def save_checkpoint(self, path: str):
        """Save full checkpoint including optimizer states and metadata."""
        if TORCH_AVAILABLE:
            ckpt = {
                "actor":        self.actor.state_dict(),
                "actor_opt":    self.actor_opt.state_dict(),
                "critic":       self.critic.state_dict() if self.critic else {},
                "critic_target": self.critic_target.state_dict() if self.critic_target else {},
                "critic_opt":   self.critic_opt.state_dict() if self.critic_opt else {},
                "lambda":       self.lagrange_lambda,
                "total_steps":  self.total_steps,
            }
            torch.save(ckpt, path)

    def save_lightweight_checkpoint(self, path: str):
        """Save lightweight checkpoint (state dicts only, no replay buffer).
        Used for 'latest.pt' after every episode."""
        if TORCH_AVAILABLE:
            ckpt = {
                "actor":       self.actor.state_dict(),
                "actor_opt":   self.actor_opt.state_dict(),
                "critic":      self.critic.state_dict() if self.critic else {},
                "critic_opt":  self.critic_opt.state_dict() if self.critic_opt else {},
                "lambda":      self.lagrange_lambda,
                "total_steps": self.total_steps,
            }
            torch.save(ckpt, path)

    def save_full_checkpoint(self, path: str):
        """Save full checkpoint including replay buffer (used every 10 episodes)."""
        if TORCH_AVAILABLE:
            ckpt = {
                "actor":        self.actor.state_dict(),
                "actor_opt":    self.actor_opt.state_dict(),
                "critic":       self.critic.state_dict() if self.critic else {},
                "critic_target": self.critic_target.state_dict() if self.critic_target else {},
                "critic_opt":   self.critic_opt.state_dict() if self.critic_opt else {},
                "lambda":       self.lagrange_lambda,
                "total_steps":  self.total_steps,
                "replay_buffer": self.buffer.state_dict(),
            }
            torch.save(ckpt, path)

    def load_full_checkpoint(self, path: str):
        """Load full checkpoint including replay buffer."""
        if TORCH_AVAILABLE:
            ckpt = torch.load(path, map_location=self.device)
            self.actor.load_state_dict(ckpt["actor"])
            self.actor.to(self.device)
            if "actor_opt" in ckpt:
                self.actor_opt.load_state_dict(ckpt["actor_opt"])
            if "critic" in ckpt and self.critic is not None:
                self.critic.load_state_dict(ckpt["critic"])
                if "critic_target" in ckpt:
                    self.critic_target.load_state_dict(ckpt["critic_target"])
                else:
                    self.critic_target.load_state_dict(ckpt["critic"])
                self.critic.to(self.device)
                self.critic_target.to(self.device)
            if "critic_opt" in ckpt:
                self.critic_opt.load_state_dict(ckpt["critic_opt"])
            self.lagrange_lambda = ckpt.get("lambda", 0.0)
            self.total_steps     = ckpt.get("total_steps", self.total_steps)
            if "replay_buffer" in ckpt:
                self.buffer.load_state_dict(ckpt["replay_buffer"])

    def __repr__(self):
        dev = str(self.device) if self.device else "numpy"
        return (f"MAFACAgent({self.agent_id}, "
                f"steps={self.total_steps}, lambda={self.lagrange_lambda:.4f}, "
                f"device={dev})")
