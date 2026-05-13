"""
trainer.py
==========
Training loop for MAFAC and all baseline algorithms.

Handles:
  - Episode execution (warmup -> training -> evaluation)
  - Federated learning round management
  - Checkpoint saving
  - Training curve logging

CHANGES from original:
  - run_episode(): handle empty obs dict returned when no vehicles are present
  - _select_actions(): handle empty agent pool gracefully
  - _store_experiences(): skip if obs/next_obs is empty
  - ep_reward accumulation: skip when rewards is empty dict

CHANGES (GPU/Resume Refactor):
  - __init__: `device` パラメータ추가 → make_agent에 전달.
  - __init__: `resume_from` 파라미터 추가.
  - train(): start_episode 처리, 체크포인트 로드 로직 포함.
  - 체크포인트 정책 개선:
      * 매 episode: lightweight checkpoint (latest.pt, agent state_dict 만)
      * 매 10 episode: full checkpoint (replay buffer 포함, ep{N:05d}_full.pt)
      * 매 episode: trainer_state.json 갱신 (episode, federated round_count 등)
  - _save_checkpoints: try/except의 pass → 명시적 에러 로그로 교체.
"""

import os
import sys
import math
import random
import time
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE))

from env.sumo_env     import SUMOEnv, RSU_POSITIONS, RSU_IDS
from agents.mafac_agent      import MAFACAgent
from agents.centralized_agent import CentralizedAgent
from agents.sac_agent        import SACAgent
from agents.iql_agent        import IQLAgent
from agents.ndn_lru_agent    import NDNLRUAgent
from agents.no_cache_agent   import NoCacheAgent
from agents.federated        import FederatedAggregator
from utils.metrics           import EpisodeMetrics
from utils.logger            import ExperimentLogger

logger = logging.getLogger(__name__)



# ─────────────────────────────────────────────────────────────────────────────
# Adaptive Progress Logger — prints status at increasing intervals
# ─────────────────────────────────────────────────────────────────────────────
# Interval rule (elapsed time since training start):
#   - 0   ≤ t < 60s    : every 10s
#   - 60s ≤ t < 600s   : every 60s
#   - 600s≤ t < 3600s  : every 600s
#   - 3600s≤ t        : every 3600s
# Each log line includes wall-clock datetime (YYYY-MM-DD HH:MM:SS).
# ─────────────────────────────────────────────────────────────────────────────
class AdaptiveProgressLogger:
    def __init__(self, log_path: Optional[str] = None):
        self.start_time   = time.time()
        self.last_log_t   = self.start_time
        self.log_path     = log_path

    @staticmethod
    def _interval_for(elapsed: float) -> float:
        if elapsed < 60.0:        # < 1 min
            return 10.0
        elif elapsed < 600.0:     # < 10 min
            return 60.0
        elif elapsed < 3600.0:    # < 1 hour
            return 600.0
        else:                     # >= 1 hour
            return 3600.0

    def should_log(self) -> bool:
        now     = time.time()
        elapsed = now - self.start_time
        gap     = now - self.last_log_t
        return gap >= self._interval_for(elapsed)

    def emit(self, msg: str, force: bool = False):
        """Print msg with timestamp if interval elapsed (or force=True)."""
        now = time.time()
        if not force and not self.should_log():
            return
        self.last_log_t = now
        elapsed = now - self.start_time
        wallclock = time.strftime("%Y-%m-%d %H:%M:%S")
        # Format elapsed nicely
        if elapsed < 60:
            el = f"{elapsed:5.1f}s"
        elif elapsed < 3600:
            el = f"{elapsed/60:5.1f}m"
        else:
            el = f"{elapsed/3600:5.2f}h"
        line = f"[{wallclock}] [+{el}] {msg}"
        print(line, flush=True)
        if self.log_path:
            try:
                with open(self.log_path, "a") as f:
                    f.write(line + "\n")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Algorithm factory
# ─────────────────────────────────────────────────────────────────────────────
def make_agent(algorithm: str, agent_id: str, obs_dim: int,
               action_dims, seed: int = 42, device: str = None):
    """Create an RL agent. device is forwarded to MAFACAgent (and future GPU-aware agents)."""
    alg = algorithm.lower()
    if alg == "mafac":
        return MAFACAgent(agent_id, obs_dim, action_dims, seed=seed, device=device)
    elif alg in ("centralized", "centralized-aoi"):
        return CentralizedAgent(obs_dim, action_dims, seed=seed)
    elif alg in ("sac", "sac-single"):
        return SACAgent(agent_id, obs_dim, action_dims, seed=seed)
    elif alg == "iql":
        return IQLAgent(agent_id, obs_dim, action_dims, seed=seed)
    elif alg in ("ndn-lru", "ndnlru"):
        return NDNLRUAgent(agent_id, action_dims, seed=seed)
    elif alg in ("no-cache", "nocache"):
        return NoCacheAgent(agent_id, action_dims, seed=seed)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


# ─────────────────────────────────────────────────────────────────────────────
# Trainer
# ─────────────────────────────────────────────────────────────────────────────
class Trainer:
    """
    Main training loop for MAFAC simulation.

    Supports:
      - Single agent or multi-agent
      - Federated learning rounds
      - Checkpointing: lightweight every episode, full every 10 episodes
      - Resume from checkpoint (--resume flag)
      - Logging to CSV
    """

    def __init__(
        self,
        algorithm: str = "MAFAC",
        env_config: dict = None,
        total_episodes: int = 500,
        federated_round_interval: int = 10,  # every E=10 episodes
        checkpoint_dir: str = "checkpoints",
        output_dir: str = "home/nyj/0_paper/paper/data",
        seed: int = 42,
        verbose: bool = True,
        device: str = None,          # NEW: e.g. "cuda" or "cpu"
        resume_from: str = None,     # NEW: path to MAFAC checkpoint dir to resume
        update_every: int = 10,      # NEW: gradient update frequency (every N steps)
    ):
        self.algorithm               = algorithm
        self.env_config              = env_config or {}
        self.total_episodes          = total_episodes
        self.federated_round_interval = federated_round_interval
        self.checkpoint_dir          = Path(checkpoint_dir)
        self.output_dir              = Path(output_dir)
        self.seed                    = seed
        self.verbose                 = verbose
        self.device                  = device
        self.resume_from             = resume_from
        self.update_every            = update_every

        # Adaptive progress logger (prints status at expanding intervals)
        # Log path: simulation/simulation_log.txt (alongside trainer.py's parent)
        _sim_log = Path(__file__).resolve().parent.parent / "simulation_log.txt"
        self.progress_logger = AdaptiveProgressLogger(log_path=str(_sim_log))

        random.seed(seed)
        np.random.seed(seed)

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build environment
        self.env = SUMOEnv(seed=seed, **self.env_config)

        # Agent pool (populated at reset)
        self.agents: Dict[str, Any] = {}

        # Federated aggregator (only for MAFAC + IQL variants)
        self.federated = None
        if algorithm.upper() in ("MAFAC", "IQL"):
            rsu_pos = {rid: pos for rid, pos in zip(RSU_IDS, RSU_POSITIONS)}
            self.federated = FederatedAggregator(
                num_rsus=4, rsu_ids=RSU_IDS,
                aoi_tracker=self.env.aoi_tracker)

        # Logger
        self.logger = ExperimentLogger(str(self.output_dir))

        # Training history
        self.reward_history: List[float]  = []
        self.metrics_history: List[dict]  = []
        self.episode_count: int           = 0

    # ── Agent Management ──────────────────────────────────────────────────────
    def _ensure_agents(self, obs: Dict[str, np.ndarray]):
        """Create agents for any new vehicles."""
        if not obs:
            # No vehicles active; nothing to do
            return

        obs_dim     = self.env.obs_dim
        action_dims = self.env.action_dims

        for vid in list(obs.keys()):
            if vid not in self.agents:
                self.agents[vid] = make_agent(
                    self.algorithm, vid, obs_dim, action_dims,
                    seed=self.seed + hash(vid) % 10000,
                    device=self.device)


    def _select_actions(self, obs: Dict[str, np.ndarray],
                        deterministic: bool = False) -> Dict[str, np.ndarray]:
        """Select actions for all active vehicles. Returns empty dict if no agents."""
        actions = {}
        if not obs or not self.agents:
            return actions
        for vid, agent in self.agents.items():
            if vid in obs:
                actions[vid] = agent.select_action(obs[vid], deterministic)
        return actions

    def _store_experiences(self, obs, actions, rewards, next_obs, dones,
                           info: dict):
        if not obs or not next_obs:
            return
        cbr = info.get("cbr", 0.0)
        cv  = 1.0 if cbr > 0.65 else 0.0
        for vid in list(obs.keys()):
            if vid not in self.agents:
                continue
            if vid not in next_obs:
                continue
            r = rewards.get(vid, 0.0)
            d = dones.get(vid, False)
            self.agents[vid].store_experience(
                obs[vid], actions.get(vid, np.zeros(4, dtype=np.int32)),
                r, next_obs[vid], float(d), float(cv))

    def _update_agents(self) -> dict:
        losses = {}
        for vid, agent in self.agents.items():
            result = agent.update()
            if result:
                losses[vid] = result
        return losses

    # ── Episode Runner ────────────────────────────────────────────────────────
    def run_episode(self, eval_mode: bool = False) -> dict:
        """
        Run one complete episode.
        Returns episode metric dict.

        CHANGED: Handles empty obs dict gracefully when no vehicles are present.
        If initial obs is empty (no vehicles after warmup), returns a minimal
        metrics dict rather than crashing.
        """
        obs = self.env.reset()
        self._ensure_agents(obs)

        # If no vehicles are present after reset+warmup, return empty metrics
        if not obs:
            if self.verbose:
                print("[Trainer] WARNING: No vehicles after reset. "
                      "Returning empty episode metrics.")
            ep_metrics = EpisodeMetrics()
            episode_duration_s = self.env_config.get("episode_duration_s", 300.0)
            return ep_metrics.finalize(episode_duration_s)

        ep_metrics  = EpisodeMetrics()
        step_count  = 0
        ep_reward   = 0.0
        loss_dict   = {}

        episode_duration_s = self.env_config.get("episode_duration_s", 300.0)
        max_steps          = int(episode_duration_s / 0.1)

        while step_count < max_steps:
            # Select actions (returns {} if no agents/obs)
            actions = self._select_actions(obs, deterministic=eval_mode)

            # Environment step
            try:
                next_obs, rewards, dones, truncated, info = self.env.step(actions)
            except Exception as e:
                if self.verbose:
                    print(f"[Trainer] env.step error at step {step_count}: {e}")
                break

            # Update agents for new vehicles
            self._ensure_agents(next_obs)

            if not eval_mode:
                self._store_experiences(obs, actions, rewards, next_obs, dones, info)
                if step_count % self.update_every == 0:
                    loss_dict = self._update_agents()
            else:
                loss_dict = {}

            # Collect metrics
            ep_metrics.update(info, rewards)

            # Accumulate reward (handle empty rewards dict)
            if rewards:
                ep_reward += float(np.mean(list(rewards.values())))

            obs = next_obs
            step_count += 1

            # Adaptive in-episode progress log (10s → 1m → 10m → 1h cadence).
            # Avoids long silent stretches during slow episodes.
            if hasattr(self, "progress_logger") and self.progress_logger.should_log():
                cur_ep = getattr(self, "_current_episode", 0)
                cur_ep_total = getattr(self, "total_episodes", 0)
                # Compute light running stats without disturbing the simulation
                running_aoi = float(np.mean(ep_metrics.aoi_samples)) if getattr(ep_metrics, "aoi_samples", None) else 0.0
                self.progress_logger.emit(
                    f"Ep {cur_ep}/{cur_ep_total} step {step_count}/{max_steps} "
                    f"| n_veh={len(obs)} "
                    f"| running_AoI={running_aoi:.3f}s "
                    f"| running_R={ep_reward / max(1, step_count):.4f} "
                    f"| eval={eval_mode}")

            if truncated:
                break

        # Finalize metrics
        final = ep_metrics.finalize(episode_duration_s)

        # Add loss info
        if loss_dict:
            losses = list(loss_dict.values())
            final["actor_loss"]    = float(np.mean([
                l.get("actor_loss", 0) for l in losses if l]))
            final["critic_loss"]   = float(np.mean([
                l.get("critic_loss", 0) for l in losses if l]))
            final["lagrange_lambda"] = float(np.mean([
                getattr(self.agents[vid], "lagrange_lambda", 0)
                for vid in self.agents]))
        else:
            final["actor_loss"]      = 0.0
            final["critic_loss"]     = 0.0
            final["lagrange_lambda"] = 0.0

        final["mean_reward"] = ep_reward / max(1, step_count)
        return final

    # ── Checkpoint Helpers ────────────────────────────────────────────────────
    def _ckpt_dir_for_algo(self) -> Path:
        """Return the base checkpoint directory for the current algorithm."""
        return self.checkpoint_dir / self.algorithm

    def _save_trainer_state(self, episode: int):
        """Persist trainer global state (episode counter, federated round count) to JSON."""
        state = {
            "episode": episode,
            "federated_round_count": self.federated.round_count if self.federated else 0,
            "reward_history": self.reward_history,
        }
        state_path = self._ckpt_dir_for_algo() / "trainer_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    def _load_trainer_state(self) -> dict:
        """Load trainer global state from JSON. Returns {} if not found."""
        state_path = self._ckpt_dir_for_algo() / "trainer_state.json"
        if state_path.exists():
            with open(state_path, "r") as f:
                return json.load(f)
        return {}

    def _latest_full_ckpt_episode(self) -> Optional[int]:
        """Scan checkpoint dir for the most recent full checkpoint episode number."""
        base = self._ckpt_dir_for_algo()
        if not base.exists():
            return None
        episodes = []
        for d in base.iterdir():
            if d.is_dir() and d.name.startswith("ep") and d.name.endswith("_full"):
                try:
                    ep_num = int(d.name[2:].replace("_full", ""))
                    episodes.append(ep_num)
                except ValueError:
                    pass
        return max(episodes) if episodes else None

    def _save_checkpoints(self, episode: int, full: bool = False):
        """
        Save checkpoints.

        Strategy:
          - Every episode: save lightweight checkpoint (agent weights + opt + lambda)
            as checkpoints/ALGO/latest/<vid>.pt
          - Every 10 episodes: save full checkpoint (including replay buffer)
            as checkpoints/ALGO/ep{N:05d}_full/<vid>.pt

        Errors are now explicitly logged (no silent pass).
        """
        try:
            base = self._ckpt_dir_for_algo()

            # ── Lightweight: every episode → latest/
            latest_dir = base / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            for vid, agent in list(self.agents.items())[:10]:
                if hasattr(agent, "save_lightweight_checkpoint"):
                    safe_vid = vid.replace("/", "_")
                    agent.save_lightweight_checkpoint(
                        str(latest_dir / f"{safe_vid}.pt"))
                elif hasattr(agent, "save_checkpoint"):
                    safe_vid = vid.replace("/", "_")
                    agent.save_checkpoint(str(latest_dir / f"{safe_vid}.pt"))

            # ── Full: every 10 episodes (or forced)
            if full:
                full_dir = base / f"ep{episode:05d}_full"
                full_dir.mkdir(parents=True, exist_ok=True)
                for vid, agent in list(self.agents.items())[:10]:
                    safe_vid = vid.replace("/", "_")
                    if hasattr(agent, "save_full_checkpoint"):
                        agent.save_full_checkpoint(
                            str(full_dir / f"{safe_vid}.pt"))
                    elif hasattr(agent, "save_checkpoint"):
                        agent.save_checkpoint(str(full_dir / f"{safe_vid}.pt"))

            # ── Global trainer state
            self._save_trainer_state(episode)

        except Exception as e:
            # 명시적 에러 로그 (기존 pass 제거)
            error_msg = f"[Trainer] WARNING: checkpoint save failed at ep={episode}: {e}"
            print(error_msg)
            logger.warning(error_msg, exc_info=True)

    def _resume_from_checkpoint(self) -> int:
        """
        Load the latest checkpoint and return the episode to start from.

        1. Reads trainer_state.json to get last episode.
        2. Loads agent weights from latest/ checkpoint dir.
        3. Restores reward_history and federated.round_count.
        4. Returns start_episode = last_episode + 1.
        """
        print(f"[Trainer] Attempting to resume from: {self._ckpt_dir_for_algo()}")
        state = self._load_trainer_state()

        if not state:
            print("[Trainer] No trainer_state.json found. Starting from episode 1.")
            return 1

        last_ep = state.get("episode", 0)
        self.reward_history = state.get("reward_history", [])
        start_ep = last_ep + 1

        # Restore federated round count
        if self.federated is not None:
            self.federated.round_count = state.get("federated_round_count", 0)

        print(f"[Trainer] Resumed. Last completed episode: {last_ep}. "
              f"Resuming from episode {start_ep}.")

        # Load agent checkpoints from latest/
        latest_dir = self._ckpt_dir_for_algo() / "latest"
        if latest_dir.exists():
            for ckpt_file in latest_dir.glob("*.pt"):
                vid = ckpt_file.stem.replace("_", "/", 1)
                # We need obs_dim and action_dims from env
                obs_dim     = self.env.obs_dim
                action_dims = self.env.action_dims
                if vid not in self.agents:
                    agent = make_agent(
                        self.algorithm, vid, obs_dim, action_dims,
                        seed=self.seed + hash(vid) % 10000,
                        device=self.device)
                    self.agents[vid] = agent
                try:
                    if hasattr(self.agents[vid], "load_checkpoint"):
                        self.agents[vid].load_checkpoint(str(ckpt_file))
                    print(f"[Trainer]   Loaded checkpoint for {vid}")
                except Exception as e:
                    print(f"[Trainer]   WARNING: failed to load {ckpt_file}: {e}")
        else:
            print("[Trainer] WARNING: latest/ checkpoint dir not found. "
                  "Agents will start fresh but episode counter is restored.")

        return start_ep

    # ── Full Training Loop ────────────────────────────────────────────────────
    def train(self) -> List[dict]:
        """
        Run complete training loop.
        If self.resume_from is set, loads checkpoint and continues from last episode.
        Returns list of per-episode metric dicts.
        """
        # ── Resume handling ──────────────────────────────────────────────
        if self.resume_from is not None:
            start_episode = self._resume_from_checkpoint()
        else:
            start_episode = 1

        print(f"[Trainer] Starting training: algorithm={self.algorithm}, "
              f"episodes={start_episode}..{self.total_episodes}, "
              f"device={self.device}")
        # Force first adaptive log so the user immediately sees that training started
        self.progress_logger.emit(
            f"TRAIN START | algo={self.algorithm} | ep {start_episode}/{self.total_episodes} | device={self.device}",
            force=True)
        # Track current episode so run_episode can include it in mid-episode logs
        self._current_episode = start_episode

        all_metrics = []

        for ep in range(start_episode, self.total_episodes + 1):
            self._current_episode = ep
            t0 = time.time()
            ep_metrics = self.run_episode(eval_mode=False)
            ep_time    = time.time() - t0

            self.episode_count += 1
            all_metrics.append(ep_metrics)
            self.metrics_history.append(ep_metrics)
            self.reward_history.append(ep_metrics.get("mean_reward", 0.0))

            # ── Federated aggregation ────────────────────────────────────
            if (self.federated is not None and
                    ep % self.federated_round_interval == 0 and
                    self.agents):
                veh_pos = {vid: self.env._vehicle_pos.get(vid, (0,0))
                           for vid in self.agents}
                rsu_pos = {rid: pos for rid, pos in zip(RSU_IDS, RSU_POSITIONS)}
                v2r = FederatedAggregator.assign_vehicles_to_rsus(veh_pos, rsu_pos)
                self.federated.run_federation_round(
                    self.agents, v2r, self.env.sim_time)

            # ── Logging ──────────────────────────────────────────────────
            self.logger.log_training(ep, self.algorithm, ep_metrics)

            cbr = ep_metrics.get("cbr", 0.0)
            self.logger.log_constraint(ep, self.algorithm, {
                "cbr":               cbr,
                "constraint_satisfied": int(cbr <= 0.65),
                "lagrange_lambda":   ep_metrics.get("lagrange_lambda", 0.0),
                "energy_constraint": 1,
                "aoi_qos_constraint": int(ep_metrics.get("average_aoi", 999) < 30.0),
            })

            # ── Checkpointing ─────────────────────────────────────────────
            # Every episode: lightweight (agent state dicts only → latest/)
            # Every 10 episodes: full (including replay buffer → ep{N:05d}_full/)
            is_full = (ep % 10 == 0) or (ep == self.total_episodes)
            self._save_checkpoints(ep, full=is_full)

            # ── Progress print ────────────────────────────────────────────
            # Adaptive progress log (10s → 1m → 10m → 1h cadence)
            self.progress_logger.emit(
                f"Ep {ep:4d}/{self.total_episodes} done "
                f"| AoI={ep_metrics.get('average_aoi', 0):.3f}s "
                f"| CHR={ep_metrics.get('cache_hit_ratio', 0):.3f} "
                f"| TSR={ep_metrics.get('tx_success_rate', 0):.3f} "
                f"| R={ep_metrics.get('mean_reward', 0):.4f} "
                f"| λ={ep_metrics.get('lagrange_lambda', 0):.4f} "
                f"| ep_time={ep_time:.1f}s")
            if self.verbose and ep % 10 == 0:
                print(f"[Trainer] Ep {ep:4d}/{self.total_episodes} "
                      f"| AoI={ep_metrics.get('average_aoi', 0):.3f}s "
                      f"| CHR={ep_metrics.get('cache_hit_ratio', 0):.3f} "
                      f"| TSR={ep_metrics.get('tx_success_rate', 0):.3f} "
                      f"| R={ep_metrics.get('mean_reward', 0):.4f} "
                      f"| λ={ep_metrics.get('lagrange_lambda', 0):.4f} "
                      f"| t={ep_time:.1f}s")

        # Final checkpoint (full)
        self._save_checkpoints(self.total_episodes, full=True)

        # Log federated overhead
        if self.federated:
            ov = self.federated.get_overhead_stats()
            self.logger.log_overhead(self.federated.round_count,
                                      self.algorithm, {
                "num_agents":    len(self.agents),
                "num_rsus":      4,
                "bytes_per_round": ov["bytes_per_round"],
                "cumulative_mb": ov["total_mb"],
                "time_s":        self.env.sim_time,
            })

        # Final force log so the user clearly sees completion
        self.progress_logger.emit(
            f"TRAIN END | algo={self.algorithm} | "
            f"completed {self.total_episodes} episodes",
            force=True)

        self.logger.close_all()
        self.env.close()
        return all_metrics

    def __repr__(self):
        return (f"Trainer(algo={self.algorithm}, "
                f"ep={self.episode_count}/{self.total_episodes}, "
                f"device={self.device})")
