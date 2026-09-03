# src/hot_swap_trainer.py
# ============================================================================
# Dual-Model Hot-Swap Training Pipeline (S4 / R4)
#
# Implements:
# 1. DualModelHotSwapManager: Zero-downtime atomic hot-swap manager with
#    strict NaN/Inf validation, cross-device support, and thread-safe mutex.
# 2. TransitionStreamer: High-throughput non-blocking thread-safe queue
#    streaming transitions from simulation/serving steps to background trainer.
# 3. BackgroundTrainer: Dedicated background training worker executing
#    gradient updates on Rest model and triggering periodic hot-swaps.
# 4. HotSwapRLScheduler: Act-model inference and transition forwarding. It does
#    NOT build observations or price rewards -- see design_spec_v2 principle P1.
# 5. HotSwapTrainer: Master orchestrator for Act/Rest model lifecycle.
# 6. AoiV2IEnv: Genuine SUMO environment integration with 4 anti-mocking
#    assertions. Sole owner of the observation vector and the reward function.
# 7. run_hot_swap_training: Full end-to-end training loop execution function
#    supporting 200,000 steps, TensorBoard logging, and checkpointing.
#
# The loop is EVENT-DRIVEN, not a gym rollout: each vehicle has its own decision
# epochs spaced by the Delta the policy chose for it, so there is no single
# global (s, a, r, s') tick. A grant fires when the clock reaches its deadline,
# not on the step it was issued. See design_spec_v2.md sections 1, 5 and 9.
# ============================================================================

from __future__ import annotations
import gc
import glob
import logging
import math
import os
import queue
import random
import re
import threading
import time
import xml.etree.ElementTree as ET
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    SummaryWriter = None

try:
    import libsumo
except ImportError:
    libsumo = None

import src.Communications as comm
import src.sumo.make_sumo_set as ss
from src.dynamics_predictor import extract_tls_features
from src.rl_interface import (
    RSU_RANGE,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    StateVectorizer,
    estimation_error,
    norm_sq_error,
    refresh_scenario_constants,
)


# ----------------------------------------------------------------------------
# Reward weights are a property of the BENCHMARK, not of any single model.
# Training (`run_hot_swap_training`), evaluation (`src/evaluate.py`) and the
# hyper-parameter search (`src/hpo.py`) all read these same four numbers, so
# every baseline is optimised and scored against one identical reward. Tuning
# them per model would give each baseline a different objective and make the
# cross-model comparison in the paper meaningless.
#
# They are also the reason `HotSwapTrainer` filters them out of `hparams`:
# w1..w4 are `AoiV2IEnv.__init__` arguments, and every baseline constructor
# ends in `**hparams`, so a stray `w1` would be silently swallowed by the model
# and never reach the reward at all.
# ----------------------------------------------------------------------------
REWARD_WEIGHT_KEYS: Tuple[str, ...] = ("w1", "w2", "w3", "w4")

DEFAULT_REWARD_WEIGHTS: Dict[str, float] = {
    "w1": 0.5,   # normalised squared estimation error
    "w2": 0.2,   # transmit power
    "w3": 0.2,   # channel congestion
    "w4": 0.1,   # redundant-update indicator
}

# Raw (un-normalised) Optuna samples for the weights above. They are recorded in
# the HPO CSV for provenance and must never be forwarded to a model either.
RAW_REWARD_WEIGHT_KEYS: Tuple[str, ...] = tuple(f"{k}_raw" for k in REWARD_WEIGHT_KEYS)

# Every key here belongs to the environment or the benchmark, never to a model
# constructor. `HotSwapTrainer` strips them from `hparams` and warns.
ENV_ONLY_HPARAM_KEYS: frozenset = frozenset(REWARD_WEIGHT_KEYS + RAW_REWARD_WEIGHT_KEYS)


def split_env_hparams(hparams: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split a flat hparams dict into (model kwargs, environment-only kwargs).

    Returns two dicts: the first is safe to hand to a baseline constructor, the
    second holds the `ENV_ONLY_HPARAM_KEYS` that were pulled out.
    """
    model_hparams: Dict[str, Any] = {}
    env_hparams: Dict[str, Any] = {}
    for key, value in (hparams or {}).items():
        if key in ENV_ONLY_HPARAM_KEYS:
            env_hparams[key] = value
        else:
            model_hparams[key] = value
    return model_hparams, env_hparams


def infer_state_dim(vectorizer: Optional[StateVectorizer] = None) -> int:
    """
    Resolves the observation vector dimension from `StateVectorizer` itself.

    The state layout is owned by `src/rl_interface.py::StateVectorizer`; this
    module must never hardcode it (it grew from 16 to 18 dims when `n_queue`
    and `heading` were added). Resolution order:
      1. an explicit dimension attribute exposed by the vectorizer, if any;
      2. otherwise probe the real vectorizer with an empty state dict and
         measure the length of the vector it actually produces.

    Returns the measured dimension; never guesses a literal unless both the
    attribute and the probe are unavailable.
    """
    vec = vectorizer if vectorizer is not None else StateVectorizer()
    for attr in ("STATE_DIM", "state_dim", "dim", "n_features", "num_features"):
        val = getattr(vec, attr, None)
        if callable(val):
            try:
                val = val()
            except Exception:
                val = None
        if isinstance(val, (int, np.integer)) and int(val) > 0:
            return int(val)
    try:
        return int(len(vec.vectorize_from_dict({}, (0.0, 0.0))))
    except Exception:
        # Last-resort fallback: the canonical design dimension (Conversation.md
        # section 1: 16 base features + n_queue + heading).
        # Last resort. Import the canonical width rather than restating it: a
        # literal here silently disagreed with STATE_DIM when the vector went
        # from 18 to 17 dimensions.
        from src.rl_interface import STATE_DIM as _CANONICAL_STATE_DIM

        return _CANONICAL_STATE_DIM


def select_default_devices() -> Tuple[torch.device, torch.device]:
    """
    Selects optimal PyTorch devices for Act and Rest models based on available hardware.
    
    Returns:
        (act_device, rest_device)
        - Multi-GPU (>=2 GPUs): Act on cuda:0, Rest on cuda:1 (Complete hardware isolation)
        - Single GPU: Act on cuda:0, Rest on cuda:0
        - CPU: Act on cpu, Rest on cpu
    """
    if torch.cuda.is_available():
        num_devices = torch.cuda.device_count()
        act_device = torch.device("cuda:0")
        if num_devices >= 2:
            rest_device = torch.device("cuda:1")
        else:
            rest_device = torch.device("cuda:0")
    else:
        act_device = torch.device("cpu")
        rest_device = torch.device("cpu")
    return act_device, rest_device


class DualModelHotSwapManager:
    """
    Manages atomic zero-downtime parameter synchronization between Act and Rest models.
    
    Guarantees:
    1. Safety: Strict NaN/Inf guard validates Rest model weights before transfer.
    2. Zero-Downtime: Fast serving thread reads Act model with minimal mutex overhead.
    3. Cross-Device Support: Seamless tensor copying across different GPU/CPU devices.
    4. Integrity: Copies all module parameters and buffers in-place.
    """

    def __init__(
        self,
        act_model: nn.Module,
        rest_model: nn.Module,
        act_device: Optional[Union[str, torch.device]] = None,
        rest_device: Optional[Union[str, torch.device]] = None,
        swap_lock: Optional[threading.Lock] = None,
        on_swap_callback: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.act_model = act_model
        self.rest_model = rest_model
        self.act_device = (
            torch.device(act_device)
            if act_device is not None
            else next(act_model.parameters()).device
            if list(act_model.parameters())
            else torch.device("cpu")
        )
        self.rest_device = (
            torch.device(rest_device)
            if rest_device is not None
            else next(rest_model.parameters()).device
            if list(rest_model.parameters())
            else torch.device("cpu")
        )

        self.swap_lock = swap_lock if swap_lock is not None else threading.Lock()
        self.on_swap_callback = on_swap_callback

        self.swap_count = 0
        self.failed_swaps = 0
        self.last_swap_time = 0.0
        self.swap_latencies_ms: List[float] = []

    def validate_weights(self) -> bool:
        """
        Validates all parameters and buffers in Rest model against NaN and Inf.
        Returns True if all tensors are clean and finite, False otherwise.
        """
        for name, p in self.rest_model.named_parameters():
            if torch.isnan(p).any() or torch.isinf(p).any():
                return False
        for name, b in self.rest_model.named_buffers():
            if torch.isnan(b).any() or torch.isinf(b).any():
                return False
        return True

    def hot_swap(self) -> bool:
        """
        Atomically copies Rest model parameters & buffers into Act model in-place.
        
        Returns:
            bool: True if hot-swap succeeded, False if rejected by safety guard.
        """
        # 1. NaN / Inf Safety Guard
        if not self.validate_weights():
            self.failed_swaps += 1
            return False

        # 2. Atomic In-Place Parameter Transfer under Mutex
        t0 = time.perf_counter()
        with self.swap_lock:
            with torch.no_grad():
                # Copy parameters
                for p_act, p_rest in zip(self.act_model.parameters(), self.rest_model.parameters()):
                    if p_act.device == p_rest.device:
                        p_act.data.copy_(p_rest.data)
                    else:
                        p_act.data.copy_(p_rest.data.to(p_act.device))

                # Copy named buffers (e.g., running stats)
                for b_act, b_rest in zip(self.act_model.buffers(), self.rest_model.buffers()):
                    if b_act.device == b_rest.device:
                        b_act.data.copy_(b_rest.data)
                    else:
                        b_act.data.copy_(b_rest.data.to(b_act.device))

        latency_ms = (time.perf_counter() - t0) * 1000.0
        self.swap_latencies_ms.append(latency_ms)
        self.swap_count += 1
        self.last_swap_time = time.time()

        if self.on_swap_callback is not None:
            try:
                self.on_swap_callback(self.swap_count)
            except Exception:
                pass

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Returns hot-swap execution statistics."""
        mean_lat = float(np.mean(self.swap_latencies_ms)) if self.swap_latencies_ms else 0.0
        max_lat = float(np.max(self.swap_latencies_ms)) if self.swap_latencies_ms else 0.0
        return {
            "swap_count": self.swap_count,
            "failed_swaps": self.failed_swaps,
            "last_swap_time": self.last_swap_time,
            "mean_swap_latency_ms": round(mean_lat, 4),
            "max_swap_latency_ms": round(max_lat, 4),
        }


class TransitionStreamer:
    """
    Thread-safe non-blocking queue for streaming transition tuples from simulation to trainer.
    """

    def __init__(self, maxsize: int = 20000) -> None:
        self.maxsize = int(maxsize)
        self.queue: queue.Queue = queue.Queue(maxsize=self.maxsize)
        self.pushed_count = 0
        self.dropped_count = 0
        self.drained_count = 0

    def push(
        self,
        state: Union[np.ndarray, List[float]],
        action: Union[np.ndarray, List[float], Tuple[float, ...]],
        reward: float,
        next_state: Union[np.ndarray, List[float]],
        done: bool,
        delta_t: float,
    ) -> bool:
        """
        Non-blocking transition push. Drops item if queue is full to preserve simulation speed.
        """
        item = {
            "state": state,
            "action": action,
            "reward": float(reward),
            "next_state": next_state,
            "done": bool(done),
            "delta_t": float(delta_t),
        }
        try:
            self.queue.put_nowait(item)
            self.pushed_count += 1
            return True
        except queue.Full:
            self.dropped_count += 1
            return False

    def drain(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """Drains pending transitions from queue without blocking."""
        items: List[Dict[str, Any]] = []
        limit = max_items if max_items is not None else self.queue.qsize() + 100
        for _ in range(limit):
            try:
                item = self.queue.get_nowait()
                items.append(item)
                self.queue.task_done()
            except queue.Empty:
                break
        self.drained_count += len(items)
        return items

    def push_to_buffer(self, replay_buffer: RetrospectiveReplayBuffer, max_items: Optional[int] = None) -> int:
        """Drains transitions from queue and directly inserts into replay buffer."""
        items = self.drain(max_items=max_items)
        for it in items:
            replay_buffer.push(
                state=it["state"],
                action=it["action"],
                reward=it["reward"],
                next_state=it["next_state"],
                done=it["done"],
                delta_t=it["delta_t"],
            )
        return len(items)

    def qsize(self) -> int:
        return self.queue.qsize()

    def is_empty(self) -> bool:
        return self.queue.empty()

    def clear(self) -> None:
        self.drain()
        self.pushed_count = 0
        self.dropped_count = 0
        self.drained_count = 0


class BackgroundTrainer:
    """
    Dedicated background training worker that consumes transitions from ReplayBuffer,
    performs gradient updates on Rest model, and triggers periodic atomic hot-swaps.
    """

    def __init__(
        self,
        rest_model: nn.Module,
        replay_buffer: RetrospectiveReplayBuffer,
        streamer: TransitionStreamer,
        hot_swap_manager: DualModelHotSwapManager,
        batch_size: int = 32,
        train_frequency: int = 1,
        swap_interval_steps: int = 20,
        rest_device: Optional[torch.device] = None,
        loss_history_maxlen: int = 1000,
    ) -> None:
        self.rest_model = rest_model
        self.replay_buffer = replay_buffer
        self.streamer = streamer
        self.hot_swap_manager = hot_swap_manager
        self.batch_size = int(batch_size)
        self.train_frequency = int(train_frequency)
        self.swap_interval_steps = int(swap_interval_steps)
        self.rest_device = rest_device or (
            next(rest_model.parameters()).device if list(rest_model.parameters()) else torch.device("cpu")
        )

        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.training_steps = 0
        # Bounded ring buffer: over a 200,000-step run an unbounded list would grow
        # without limit while only the last 50 entries are ever read.
        self.loss_history_maxlen = int(loss_history_maxlen)
        self.loss_history: Deque[Dict[str, float]] = deque(maxlen=self.loss_history_maxlen)
        self.lock = threading.Lock()

    def train_step(self) -> Optional[Dict[str, float]]:
        """
        Executes one gradient update step on Rest model and performs hot-swap if scheduled.
        """
        # Drain any pending transitions into replay buffer
        self.streamer.push_to_buffer(self.replay_buffer)

        if not self.replay_buffer.is_ready(self.batch_size):
            return None

        batch = self.replay_buffer.sample(self.batch_size)

        # Move batch tensors to Rest model's device
        if self.rest_device is not None:
            batch = {k: v.to(self.rest_device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

        self.rest_model.train()
        loss_dict = self.rest_model.update(batch)

        with self.lock:
            self.training_steps += 1
            self.loss_history.append(loss_dict)

            # Scheduled Hot-swap
            if self.training_steps % self.swap_interval_steps == 0:
                self.hot_swap_manager.hot_swap()

        return loss_dict

    def _worker_loop(self) -> None:
        """Background thread execution loop."""
        while not self.stop_event.is_set():
            loss_dict = self.train_step()
            if loss_dict is None:
                time.sleep(0.002)
            else:
                time.sleep(0.0005)

    def start(self) -> None:
        """Starts background training thread."""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        """Stops background training thread and joins."""
        if self.worker_thread is None:
            return
        self.stop_event.set()
        self.worker_thread.join(timeout=timeout)
        self.worker_thread = None

    def get_metrics(self) -> Dict[str, Any]:
        """Returns background trainer performance and loss summary."""
        with self.lock:
            # deque does not support slicing; materialize the bounded window first.
            recent_losses = list(self.loss_history)[-50:] if self.loss_history else []
            mean_loss = (
                float(np.mean([entry["loss"] for entry in recent_losses if "loss" in entry]))
                if recent_losses
                else 0.0
            )
            return {
                "training_steps": self.training_steps,
                # Retained window length (capped at loss_history_maxlen);
                # `training_steps` remains the uncapped total update count.
                "loss_history_len": len(self.loss_history),
                "loss_history_maxlen": self.loss_history_maxlen,
                "mean_recent_loss": round(mean_loss, 4),
                "hot_swap_stats": self.hot_swap_manager.get_stats(),
            }


class HotSwapRLScheduler:
    """
    S1/S2/S3 compliant RL scheduler that serves uplink grants using the fast Act model
    and streams retrospective transitions to the background trainer.
    """

    def __init__(
        self,
        act_model: nn.Module,
        hot_swap_manager: DualModelHotSwapManager,
        streamer: TransitionStreamer,
        vectorizer: Optional[StateVectorizer] = None,
        rsu_range: float = RSU_RANGE,
        decoder: Optional[ActionDecoder] = None,
    ) -> None:
        self.act_model = act_model
        self.hot_swap_manager = hot_swap_manager
        self.streamer = streamer
        self.vectorizer = vectorizer or StateVectorizer(rsu_range=rsu_range)
        # Single source of truth for the action ranges: src/rl_interface.py::ActionDecoder.
        self.decoder = decoder or ActionDecoder()
        # Observation width is read from the vectorizer, never hardcoded.
        self.state_dim = infer_state_dim(self.vectorizer)
        self.rsu_range = float(rsu_range)
        # The reward weights that used to live here (alpha_aoi / beta_error /
        # gamma_power) are gone. The scheduler does not price transitions any
        # more -- the environment owns the one reward function (design_spec_v2 P1).
        self.inference_latencies_ms: List[float] = []
        self.total_inferences = 0

    def decide_grant(
        self,
        vid: str,
        state_vec: np.ndarray,
    ) -> Tuple[Tuple[float, int, float], Any]:
        """Run the Act model on an observation the ENVIRONMENT produced.

        This method is pure inference. It used to also (a) build its own state
        vector from a partial dict and (b) compute its own three-term reward,
        which is what the replay buffer was actually trained on. Both are gone:

          (a) it re-vectorised from `{vid, current_time, pos, speed}`, so 15 of
              the 18 dimensions fell back to defaults and reached the model as
              constants -- traffic light, distance to RSU, CBR, heading, age.
              The rich vector the environment builds was discarded by the caller.
          (b) its reward was `-(0.1*dt + 1.0*err + 0.01*power)` with `err`
              permanently 0 (the key was never passed) and `dt` permanently 0.1,
              i.e. the only live training signal in the whole pipeline was
              transmit power. The approved four-term reward went to the log file.

        Both now have exactly one owner, the environment (design_spec_v2 P1/P2).

        Returns the decoded grant and the raw action, which the caller stores so
        the transition can be pushed with the action the policy actually emitted.
        """
        s = np.asarray(state_vec, dtype=np.float32)
        assert s.shape == (self.state_dim,), (
            f"FATAL: observation for {vid} has width {s.shape}, expected ({self.state_dim},). "
            "The environment is the only legitimate source of observations."
        )

        t0 = time.perf_counter()
        self.act_model.eval()
        with self.hot_swap_manager.swap_lock:
            grant, raw_action, info = self.act_model.select_action(s, deterministic=False)

        self.inference_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        self.total_inferences += 1
        return grant, raw_action

    def push_transition(
        self,
        state: np.ndarray,
        raw_action: Any,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        delta_t: float,
    ) -> None:
        """Stream one closed SMDP interval to the background trainer.

        `reward` and `delta_t` come from the environment: the reward is the
        four-term interval reward and `delta_t` is the MEASURED interval, which
        differs from the requested Delta whenever a failed uplink was retried.
        The buffer discounts by gamma**delta_t, so feeding it the requested value
        would misprice exactly the intervals that went wrong.
        """
        self.streamer.push(
            state=state,
            action=raw_action,
            reward=float(reward),
            next_state=next_state,
            done=bool(done),
            delta_t=float(delta_t),
        )


    def reset(self) -> None:
        """Resets per-episode state."""
        self.inference_latencies_ms.clear()

    def get_latency_stats(self) -> Dict[str, float]:
        """Returns serving inference latency percentiles in ms."""
        if not self.inference_latencies_ms:
            return {"mean_latency_ms": 0.0, "p50_latency_ms": 0.0, "p95_latency_ms": 0.0, "p99_latency_ms": 0.0}
        arr = np.array(self.inference_latencies_ms)
        return {
            "mean_latency_ms": round(float(np.mean(arr)), 4),
            "p50_latency_ms": round(float(np.percentile(arr, 50)), 4),
            "p95_latency_ms": round(float(np.percentile(arr, 95)), 4),
            "p99_latency_ms": round(float(np.percentile(arr, 99)), 4),
        }


class HotSwapTrainer:
    """
    Master Orchestrator for Dual-Model Hot-Swap Training.
    Manages Act model, Rest model, ReplayBuffer, Streamer, Worker, and Hot-Swap synchronization.
    """

    def __init__(
        self,
        model_name: Union[str, type, Callable] = "GenericPolicy",
        model_cls: Optional[Callable] = None,
        state_dim: Optional[int] = None,
        num_channels: int = 4,
        buffer_capacity: int = 10000,
        batch_size: int = 32,
        swap_interval: int = 20,
        act_device: Optional[Union[str, torch.device]] = None,
        rest_device: Optional[Union[str, torch.device]] = None,
        hparams: Optional[Dict[str, Any]] = None,
    ) -> None:
        if model_cls is None:
            if callable(model_name) and not isinstance(model_name, str):
                model_cls = model_name
                self.model_name = getattr(model_cls, "__name__", "CustomModel")
            else:
                raise NotImplementedError(
                    f"Baseline models scraped. New IEEE baselines to be provided. Cannot instantiate '{model_name}' without model_cls."
                )
        else:
            self.model_name = str(model_name) if isinstance(model_name, str) else getattr(model_name, "__name__", "CustomModel")

        # `state_dim=None` (default) reads the width straight off StateVectorizer so
        # this orchestrator tracks the state layout automatically; an explicit int is
        # still honoured for backward compatibility.
        self.state_dim = int(state_dim) if state_dim is not None else infer_state_dim()
        self.num_channels = int(num_channels)
        self.buffer_capacity = int(buffer_capacity)
        self.batch_size = int(batch_size)
        self.swap_interval = int(swap_interval)

        # w1..w4 are AoiV2IEnv arguments, not model arguments. Every baseline
        # constructor ends in `**hparams`, so leaving them in here would have
        # them absorbed by the model and silently dropped from the reward --
        # exactly the failure this split exists to prevent.
        self.hparams, self.env_hparams = split_env_hparams(hparams)
        if self.env_hparams:
            logging.warning(
                "%s: dropped environment-only key(s) %s from model hyperparameters; "
                "reward weights come from DEFAULT_REWARD_WEIGHTS and are not tuned per model.",
                self.model_name, sorted(self.env_hparams),
            )

        # Device Placement
        default_act_dev, default_rest_dev = select_default_devices()
        self.act_device = torch.device(act_device) if act_device is not None else default_act_dev
        self.rest_device = torch.device(rest_device) if rest_device is not None else default_rest_dev

        # Instantiate Models
        self.act_model = model_cls(state_dim=self.state_dim, num_channels=self.num_channels, **self.hparams).to(
            self.act_device
        )
        self.rest_model = model_cls(state_dim=self.state_dim, num_channels=self.num_channels, **self.hparams).to(
            self.rest_device
        )

        # Set operational modes
        self.act_model.eval()
        self.rest_model.train()

        # Shared synchronization & infrastructure
        self.swap_lock = threading.Lock()
        self.hot_swap_manager = DualModelHotSwapManager(
            act_model=self.act_model,
            rest_model=self.rest_model,
            act_device=self.act_device,
            rest_device=self.rest_device,
            swap_lock=self.swap_lock,
        )

        # Initial weight sync (Rest -> Act)
        self.hot_swap_manager.hot_swap()

        self.replay_buffer = RetrospectiveReplayBuffer(capacity=self.buffer_capacity)
        self.streamer = TransitionStreamer(maxsize=self.buffer_capacity * 2)

        self.background_trainer = BackgroundTrainer(
            rest_model=self.rest_model,
            replay_buffer=self.replay_buffer,
            streamer=self.streamer,
            hot_swap_manager=self.hot_swap_manager,
            batch_size=self.batch_size,
            swap_interval_steps=self.swap_interval,
            rest_device=self.rest_device,
        )

        self.scheduler = HotSwapRLScheduler(
            act_model=self.act_model,
            hot_swap_manager=self.hot_swap_manager,
            streamer=self.streamer,
        )

    def start(self) -> None:
        """Starts background training worker."""
        self.background_trainer.start()

    def stop(self) -> None:
        """Stops background training worker."""
        self.background_trainer.stop()

    def step_training_sync(self) -> Optional[Dict[str, float]]:
        """Executes a single synchronous training update."""
        return self.background_trainer.train_step()

    def save_checkpoint(self, filepath: str, best_reward: Optional[float] = None) -> None:
        """Saves model checkpoint."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        checkpoint = {
            "model_name": self.model_name,
            "hparams": self.hparams,
            "rest_state_dict": self.rest_model.state_dict(),
            "act_state_dict": self.act_model.state_dict(),
            "training_steps": self.background_trainer.training_steps,
            "swap_count": self.hot_swap_manager.swap_count,
            "best_reward": best_reward,
        }
        torch.save(checkpoint, filepath)

    def load_checkpoint(self, filepath: str) -> Dict[str, Any]:
        """Loads model checkpoint and restores training/hot-swap counters."""
        checkpoint = torch.load(filepath, map_location=self.rest_device)
        self.rest_model.load_state_dict(checkpoint["rest_state_dict"])
        self.act_model.load_state_dict(checkpoint["act_state_dict"])
        # Restore counters so a resumed run keeps its hot-swap cadence and stats.
        self.background_trainer.training_steps = int(checkpoint.get("training_steps", 0))
        self.hot_swap_manager.swap_count = int(checkpoint.get("swap_count", 0))
        return checkpoint


class AoiV2IEnv:
    """
    Genuine Gymnasium-compatible SUMO Environment for AoI-aware V2I Uplink Scheduling.
    Interacts directly with libsumo/TraCI, extracting live vehicle telemetry and traffic light signals,
    resolving Rayleigh fading contention, and calculating SMDP estimation error rewards.

    This class is the ONLY environment in the pipeline and the sole owner of both
    the observation vector and the reward (design_spec_v2 principle P1). It exposes
    a density-parameterised constructor, per-vehicle terminated/truncated dicts and
    the IEEE TWC `get_metrics()` summary that `run_hot_swap_training`, `src/hpo.py`
    and `src/evaluate.py` all depend on.

    Reward, per SMDP interval [t_k, t_k+1) (design_spec_v2 D2):

        R_k = -( w1 * SUM_t Norm(e^2(t)) * dt/1s     <- accrues across the interval
                 + w2 * Norm(P_tx)                    <- charged once, at the update
                 + w3 * Norm(C_freq)                  <- charged once, at the update
                 + w4 * I_redundant )                 <- charged once, at the update

    Only the error term accumulates, and that asymmetry is the Delta trade-off:
    leaving a moving vehicle unaddressed bills every step, while a stopped one
    costs nothing however long the interval, because its dead-reckoned position
    stays right. Default weights w1..w4 = 0.5/0.2/0.2/0.1, all four terms
    normalized before weighting. Optuna searches the weights (`src/hpo.py`).
    Action ranges (Conversation.md section 2) are owned by
    `src/rl_interface.py::ActionDecoder` (Delta in [DELTA_MIN, DELTA_MAX] s, p in [P_MIN, P_MAX] dBm);
    this class reads `decoder.p_min` / `decoder.p_max` rather than duplicating them.

    It carries all FOUR anti-mocking runtime assertions, so the code that runs is
    the code that was audited:
      1. Time advance / regression check         (step, section 3)
      2. Vehicle coordinate & displacement check (step, section 3)
      3. Rayleigh SINR P_succ validation         (step, section 6)
      4. Reward formula re-derivation, R <= 0    (step, after section 6)
    """

    def __init__(
        self,
        density: float = 25.0,
        seed: int = 42,
        max_steps: int = 2000,
        num_channels: int = comm.NUM_SUBCHANNELS,
        rsu_range: float = RSU_RANGE,
        warmup_steps: int = 350,
        w1: float = DEFAULT_REWARD_WEIGHTS["w1"],
        w2: float = DEFAULT_REWARD_WEIGHTS["w2"],
        w3: float = DEFAULT_REWARD_WEIGHTS["w3"],
        w4: float = DEFAULT_REWARD_WEIGHTS["w4"],
    ) -> None:
        self.density = float(density)
        self.seed = int(seed)
        self.max_steps = int(max_steps)
        self.num_channels = int(num_channels)
        self.rsu_range = float(rsu_range)
        self.warmup_steps = int(warmup_steps)
        self.w1 = float(w1)
        self.w2 = float(w2)
        self.w3 = float(w3)
        self.w4 = float(w4)

        self.vectorizer = StateVectorizer(rsu_range=self.rsu_range)
        # The decoder is the single source of truth for the hybrid action ranges
        # (bounds live on the decoder -- Conversation.md section 2).
        # No range literal is duplicated here; the reward reads p_min/p_max off it.
        self.decoder = ActionDecoder(num_channels=self.num_channels)
        self.state_dim = infer_state_dim(self.vectorizer)

        # --------------------------------------------------------------------
        # I_redundant threshold (Conversation.md L27: "물리적 상태 불변 시 갱신을
        # 시도할 때 부과되는 강력한 명시적 패널티").
        #
        # design_spec_v2 D6: the indicator no longer asks "was the vehicle
        # standing still" but "was the RSU's prediction already right". That
        # covers steady cruising as well as standstill -- every case where the
        # update carried no information the RSU did not already have.
        #   I_red = 1  iff  e(t_update) <= REDUNDANT_ERR_EPS_M
        # 3.2 m is the SUMO default lane width: below it the RSU already had the
        # vehicle in the right lane, which is the accuracy V2X applications ask
        # for. Deliberately NOT tied to rl_interface.E_REF (13.32 m) -- that one
        # scales the *continuous* error penalty, this one is a hard "was this
        # transmission worth its power" threshold and wants to be stricter.
        self.REDUNDANT_ERR_EPS_M = 3.2
        # Standstill threshold. Only the speed bound is still read: it decides the
        # `was_stopped` flag that lets a stale ledger entry stay usable for the
        # n_queue count (D3). The position bound belonged to the pre-D6 indicator
        # and now has no consumer, so it is gone rather than left as a decoy.
        self.REDUNDANT_SPEED_EPS_MPS = 0.1

        # design_spec_v2 D7: a failed uplink is retried on the next step as a
        # continuation of the SAME decision (the model is not queried again).
        # The cap stops a vehicle in a deep fade from retrying forever; when it
        # is hit the interval is closed anyway and the model gets to decide again.
        self.MAX_TX_RETRIES = 10

        # design_spec_v2 D3: how long a ledger entry stays usable for the
        # n_queue count without any freshness argument of its own.
        self.LEDGER_FRESH_S = 1.0

        # --------------------------------------------------------------------
        # Channel occupancy (Communications.py, IEEE 802.11p 10 MHz).
        #
        # Every granted uplink holds its subchannel for one frame airtime, so a
        # step's Channel Busy Ratio is a measured quantity:
        #     CBR[ch] = (grants on ch) * frame_airtime / step_length
        # `step_length` is the SUMO --step-length; it is re-read from
        # libsumo.simulation.getDeltaT() after start so the two can never drift.
        # --------------------------------------------------------------------
        self.step_length = 0.1
        self.payload_bytes = comm.STATUS_UPDATE_BYTES
        self.frame_airtime_s = comm.frame_airtime_s(self.payload_bytes)
        self.subchannel_cbr: List[float] = [0.0] * self.num_channels
        self.cbr = 0.0
        # Cached count of vehicles inside the RSU disc, refreshed once per
        # simulated instant (observation feature [13]).
        self._n_active_at: float = -1.0
        self._n_active_cache: int = 0
        self.recorded_cbrs: List[float] = []

        self.target_rsu_pos = (1200.0, 10800.0)
        self.target_rsu_id = "N11"
        self.current_step = 0
        self.sim_time = 0.0
        self.is_running = False

        # Telemetry & State tracking
        self.vehicle_tracks: Dict[str, Dict[str, Any]] = {}
        self.prev_positions: Dict[str, Tuple[float, float]] = {}
        self.scheduled_tx: Dict[str, Dict[str, Any]] = {}

        # --------------------------------------------------------------------
        # SMDP interval state (design_spec_v2 D1/D2). This is what makes Delta a
        # real decision variable: a grant does not fire on the step it is issued,
        # it fires when the clock reaches `next_update_t`. Until then the vehicle
        # is silent and its dead-reckoning error accrues into `interval_accum`.
        # --------------------------------------------------------------------
        #: vid -> simulated time at which this vehicle's next uplink is due.
        self.next_update_t: Dict[str, float] = {}
        #: vid -> the grant currently being executed: {"ch", "p", "retries"}.
        self.pending_grant: Dict[str, Dict[str, Any]] = {}
        #: vid -> sum over the interval of Norm(e^2) * (step_length / 1 s).
        self.interval_accum: Dict[str, float] = {}
        #: vid -> simulated time the current interval opened at.
        self.interval_start_t: Dict[str, float] = {}
        #: Diagnostics: how many intervals ended in abandonment vs. success.
        self.total_tx_abandoned = 0
        #: Per-step lane index for the ledger n_queue, rebuilt once per simulated
        #: instant. Without it the count is O(V) per vehicle and O(V^2) per step.
        self._lane_index: Dict[Any, List[Tuple[float, float, bool]]] = {}
        self._lane_index_at: float = -1.0
        #: Active vehicle ids, cached per simulated instant. `getIDList()` builds
        #: and marshals the whole list on every call, and the per-vehicle
        #: membership test used to call it once per vehicle per lookup -- 1307
        #: calls per step at 1155 vehicles, 55 % of total step time by cProfile.
        self._active_ids: set = set()
        self._active_ids_at: float = -1.0

        # 6 IEEE TWC Metrics Accumulators
        self.recorded_errors: List[float] = []
        self.low_speed_errors: List[float] = []
        self.high_speed_errors: List[float] = []
        self.recorded_aois: List[float] = []
        self.peak_aois: List[float] = []
        self.tx_powers: List[float] = []
        self.total_tx_attempts = 0
        self.total_tx_fails = 0
        self.per_vehicle_aois: Dict[str, List[float]] = {}
        self.per_vehicle_errors: Dict[str, List[float]] = {}

        # Last live SUMO speed (m/s) per vehicle, refreshed by _get_vehicle_state_dict().
        self.last_speeds: Dict[str, float] = {}

        # --------------------------------------------------------------------
        # Anti-Mocking tracking state.
        # Ported from src/aoi_env.py::AoiV2IEnv.__init__ (~L440-443) so this
        # class carries the SAME four runtime assertions as the audited class.
        # --------------------------------------------------------------------
        self._prev_sim_time = 0.0
        self._prev_all_positions: Dict[str, Tuple[float, float]] = {}
        self.network_max_x = 50000.0
        self.network_max_y = 50000.0

    def _init_sumo(self) -> None:
        """Initializes SUMO files and starts libsumo simulation."""
        if libsumo is None:
            raise RuntimeError("libsumo is required for genuine SUMO environment execution.")

        try:
            libsumo.close()
        except Exception:
            pass

        # Reset NUM_BLOCKS so it stays 6 deterministically
        ss.NUM_BLOCKS = 5
        ss.DENSITY = self.density
        ss.MAX_STEPS = self.max_steps + self.warmup_steps + 100
        random.seed(self.seed)
        np.random.seed(self.seed)
        ss.make_sumo_files()
        # The network on disk is what DELTA_MAX / V_LIMIT / E_REF describe, so
        # re-derive them now that it has been (re)written. Without this the
        # action range and the error normaliser would still describe whatever
        # network happened to exist when the module was first imported.
        refresh_scenario_constants()
        # The decoder resolves delta_max at construction, so rebuild it against
        # the refreshed constants rather than keeping one built at __init__ time.
        self.decoder = ActionDecoder(num_channels=self.num_channels)
        self.vectorizer = StateVectorizer(rsu_range=self.rsu_range)

        cmd = [
            "sumo",
            "-c",
            "src/sumo/generated.sumocfg",
            "--step-length",
            str(self.step_length),
            "--no-step-log",
            "true",
            "--duration-log.disable",
            "true",
            "--quit-on-end",
            "false",
            "--seed",
            str(self.seed),
        ]
        libsumo.start(cmd)
        self.is_running = True

        # Take the step length back from SUMO itself rather than trusting the
        # command line: it is the denominator of every CBR, so a silent
        # mismatch would scale the whole congestion signal.
        delta_t = float(libsumo.simulation.getDeltaT())
        assert delta_t > 0.0, f"FATAL: SUMO reported a non-positive step length {delta_t}"
        self.step_length = delta_t

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Resets the SUMO simulation and warms up traffic flow."""
        if seed is not None:
            self.seed = int(seed)

        self.current_step = 0
        self.sim_time = 0.0
        self.vehicle_tracks.clear()
        self.prev_positions.clear()
        self.scheduled_tx.clear()
        self.next_update_t.clear()
        self.pending_grant.clear()
        self.interval_accum.clear()
        self.interval_start_t.clear()
        self.total_tx_abandoned = 0
        self._lane_index.clear()
        self._lane_index_at = -1.0

        self.recorded_errors.clear()
        self.low_speed_errors.clear()
        self.high_speed_errors.clear()
        self.recorded_aois.clear()
        self.peak_aois.clear()
        self.tx_powers.clear()
        self.total_tx_attempts = 0
        self.total_tx_fails = 0
        self.per_vehicle_aois.clear()
        self.per_vehicle_errors.clear()
        self.last_speeds.clear()

        # Reset anti-mocking tracking state (mirrors src/aoi_env.py reset ~L532-533).
        self._prev_sim_time = 0.0
        self._prev_all_positions.clear()

        # Channel state. The shadowing generator is reseeded from the episode
        # seed so a replayed episode replays the same propagation realizations;
        # it is private to Communications and never touches the global `random`
        # stream that drives the Bernoulli success draws.
        self.subchannel_cbr = [0.0] * self.num_channels
        self.cbr = 0.0
        self.recorded_cbrs.clear()
        # sim_time restarts at 0 on reset, so a stale cache keyed on it would be
        # served to the first step of the new episode.
        self._n_active_at = -1.0
        self._n_active_cache = 0
        comm.seed_channel(self.seed)

        self._init_sumo()

        # Parse RSU coordinates from nodes (and network bounds for Assertion 2)
        rsu_nodes = []
        try:
            tree = ET.parse("src/sumo/generated.nod.xml")
            root = tree.getroot()
            xs, ys = [], []
            for node in root.findall("node"):
                nx, ny = float(node.get("x")), float(node.get("y"))
                xs.append(nx)
                ys.append(ny)
                if node.get("type") == "traffic_light":
                    rsu_nodes.append((node.get("id"), nx, ny))
            # Mirrors src/aoi_env.py::_load_rsus (~L488-490)
            if xs and ys:
                self.network_max_x = max(xs)
                self.network_max_y = max(ys)
        except Exception:
            pass

        # Run warmup steps and identify busiest RSU
        rsu_hits = {r[0]: 0 for r in rsu_nodes}
        for _ in range(self.warmup_steps):
            libsumo.simulationStep()
            self.sim_time = float(libsumo.simulation.getTime())
            vids = libsumo.vehicle.getIDList()
            for vid in vids:
                x, y = libsumo.vehicle.getPosition(vid)
                self._prev_all_positions[vid] = (float(x), float(y))
                for rid, rx, ry in rsu_nodes:
                    if math.hypot(x - rx, y - ry) <= self.rsu_range:
                        rsu_hits[rid] += 1

        if any(rsu_hits.values()):
            best_id = max(rsu_hits, key=rsu_hits.get)
            best_node = [r for r in rsu_nodes if r[0] == best_id][0]
            self.target_rsu_id, rx, ry = best_node
            self.target_rsu_pos = (rx, ry)
        elif rsu_nodes:
            self.target_rsu_id, rx, ry = rsu_nodes[0]
            self.target_rsu_pos = (rx, ry)

        # Anti-Mocking Assertion 1: Verify SUMO simulation time advanced
        assert (
            isinstance(self.sim_time, (int, float)) and self.sim_time > 0.0
        ), f"Anti-mocking violation: SUMO simulation time did not advance ({self.sim_time})"

        # Baseline for the per-step time-regression check in step()
        # (mirrors src/aoi_env.py reset ~L565).
        self._prev_sim_time = self.sim_time

        obs = self._get_observations(is_initial=True)
        info = {
            "sim_time": self.sim_time,
            "active_vehicles": len(obs),
            "target_rsu_pos": self.target_rsu_pos,
        }
        return obs, info

    def _count_active_vehicles(self) -> int:
        """How many vehicles are inside the RSU's coverage right now.

        This is design feature [11] of the observation: the contention level the
        scheduler is up against. It was previously never supplied, so the vectorizer
        fell back to its default of 1 and the feature sat at a constant 0.01 for
        every vehicle in every step. Cached per simulated instant because the same
        step asks for it once per vehicle.
        """
        if not self.is_running:
            return 0
        if self._n_active_at == self.sim_time:
            return self._n_active_cache
        rx, ry = self.target_rsu_pos
        n = 0
        for other in self._active_vehicle_ids():
            ox, oy = libsumo.vehicle.getPosition(other)
            if math.hypot(ox - rx, oy - ry) <= self.rsu_range:
                n += 1
        self._n_active_at = self.sim_time
        self._n_active_cache = n
        return n

    def _active_vehicle_ids(self) -> set:
        """Ids of every vehicle in the network, cached per simulated instant."""
        if self._active_ids_at != self.sim_time:
            self._active_ids = set(libsumo.vehicle.getIDList())
            self._active_ids_at = self.sim_time
        return self._active_ids

    def _get_vehicle_state_dict(
        self, vid: str, with_queue: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extracts live telemetry from SUMO for a specific vehicle."""
        if not self.is_running or vid not in self._active_vehicle_ids():
            return None

        x, y = libsumo.vehicle.getPosition(vid)
        spd = float(libsumo.vehicle.getSpeed(vid))
        dist_rsu = math.hypot(x - self.target_rsu_pos[0], y - self.target_rsu_pos[1])

        if dist_rsu > self.rsu_range:
            return None

        # Supplementary coordinate-type check (full Assertion 2 lives in step()).
        assert isinstance(x, float) and isinstance(
            y, float
        ), f"Anti-mocking violation: Invalid coordinate types for {vid}"

        # Velocity vector in m/s, taken straight from SUMO's own heading rather than
        # differencing positions. The previous position-difference form was wrong twice
        # over: this method is called three times per step (observations, reward, and
        # scheduling), and each call overwrote prev_positions immediately, so every call
        # after the first in a given step saw prev == current and reported (0.0, 0.0).
        # That silently zeroed the velocity-X/Y features and the heading feature. The
        # difference was also a per-step displacement in metres, not a velocity, so it
        # was off by a factor of 1/step_length even when it was non-zero.
        # SUMO angle is degrees clockwise from north, so x is the sine component.
        angle_deg = float(libsumo.vehicle.getAngle(vid))
        angle_rad = math.radians(angle_deg)
        vx = spd * math.sin(angle_rad)
        vy = spd * math.cos(angle_rad)
        self.prev_positions[vid] = (x, y)
        # Cache live SUMO speed so external callers (trainer/eval loops) can use the
        # real per-vehicle speed instead of a hardcoded constant.
        self.last_speeds[vid] = spd

        tls_info = extract_tls_features(libsumo, vid, current_time=self.sim_time)
        last_upd = self.vehicle_tracks.get(vid, {}).get("t_update", self.sim_time)

        return {
            "vid": vid,
            "pos": (x, y),
            "vel": (vx, vy),
            "speed": spd,
            # Feature [4]. Was hardcoded to 0.0, which made the acceleration
            # dimension a constant; SUMO reports it directly.
            "accel": float(libsumo.vehicle.getAcceleration(vid)),
            "dist_to_rsu": dist_rsu,
            "current_time": self.sim_time,
            "last_update_time": last_upd,
            # Feature [0] of StateVectorizer.
            "last_pred_err": float(self.vehicle_tracks.get(vid, {}).get("last_pred_err", 0.0)),
            "tls_features": tls_info,
            # Feature [14] of StateVectorizer. This is the measured airtime
            # occupancy of the last resolved step, averaged over subchannels;
            # the vehicle cannot know which subchannel it will be granted next,
            # so it observes the network-level load, not one channel's.
            "cbr": self.cbr,
            # Feature [13] of StateVectorizer: vehicles currently in RSU range.
            "n_active": self._count_active_vehicles(),
            # Feature [15]: queue ahead, reconstructed from the RSU ledger (D3)
            # rather than read out of SUMO, which an RSU could not do.
            #
            # Computed only for the observation path. This method is called three
            # times per vehicle per step (grant firing, error accounting, ledger
            # refresh) and only one of those feeds the state vector, so counting
            # every time was two thirds wasted -- and each count walks the lane,
            # which is what made the step cost grow with the square of the
            # vehicle population.
            "n_queue": (
                self._ledger_queue_count(vid, {"tls_features": tls_info})
                if with_queue else 0
            ),
        }

    def _ledger_queue_count(self, vid: str, st: Dict[str, Any]) -> int:
        """n_queue from the RSU's own ledger, with a freshness guard (D3).

        The count must be something an RSU can actually produce. Asking SUMO
        directly (`n_queue` out of the TLS feature dict) is information no real
        roadside unit has, so this reconstructs it from what the RSU was told:
        the last position report of every vehicle it is tracking.

        A ledger entry for vehicle `j` counts towards `vid`'s queue when it is on
        the same lane, ahead of `vid`, and still trustworthy:

            age(j) <= LEDGER_FRESH_S
              OR ( j was stopped when it last reported
                   AND the signal for this lane is still red )

        The second clause is this paper's own thesis applied to the RSU's
        bookkeeping: a stopped vehicle's stale record is still correct. It is
        gated on the light still being red so the belief cannot outlive its
        reason -- without that gate a vehicle believed stopped would be believed
        stopped forever, which is circular.
        """
        tls = st.get("tls_features") or {}
        lane_id = tls.get("lane_id")
        lane_pos = tls.get("lane_position")
        if not lane_id or lane_pos is None:
            return 0
        # "Still red" is free for the RSU: it is wired to the signal controller.
        lane_is_red = str(tls.get("state", "")).lower() in ("r", "red")

        # The ledger is grouped by lane once per simulated instant. Scanning the
        # whole ledger per vehicle instead made the step O(V^2): measured 17.9 ms
        # at 32 vehicles in range and 148.1 ms at 92 (2.9x more vehicles, 8.3x the
        # cost), which is what made long episodes collapse to 4 steps/s.
        self._rebuild_lane_index()
        count = 0
        for other, other_pos, was_stopped, age in self._lane_index.get(lane_id, ()):
            if other == vid or other_pos <= float(lane_pos):
                continue  # behind us, or level with us
            if age <= self.LEDGER_FRESH_S or (was_stopped and lane_is_red):
                count += 1
        return count

    def _rebuild_lane_index(self) -> None:
        """Group the RSU ledger by lane, once per simulated instant."""
        if self._lane_index_at == self.sim_time:
            return
        index: Dict[Any, List[Tuple[str, float, bool, float]]] = {}
        for other, rec in self.vehicle_tracks.items():
            lane = rec.get("lane_id")
            pos = rec.get("lane_position")
            if not lane or pos is None:
                continue
            index.setdefault(lane, []).append((
                other,
                float(pos),
                bool(rec.get("was_stopped", False)),
                self.sim_time - float(rec.get("t_update", self.sim_time)),
            ))
        self._lane_index = index
        self._lane_index_at = self.sim_time

    def _is_redundant_update(self, err_at_update_m: float) -> float:
        """I_redundant for an update that has just been delivered (D6).

        1.0 iff the RSU's dead-reckoned belief was already within
        `REDUNDANT_ERR_EPS_M` of the truth at the instant the update landed --
        i.e. the transmission spent power and airtime to tell the RSU something
        it already knew.

        Evaluated from the error measured AFTER `libsumo.simulationStep()` and
        BEFORE the ledger is refreshed. The previous implementation ran before
        the SUMO step against a `t_update >= sim_time` guard, which silently
        returned 0.0 for every vehicle that had updated on the preceding step --
        that is, for exactly the vehicles the penalty exists to catch.
        """
        return 1.0 if float(err_at_update_m) <= self.REDUNDANT_ERR_EPS_M else 0.0

    def _register_vehicle(self, vid: str, st: Dict[str, Any], is_initial: bool = False) -> None:
        """Open the RSU's ledger entry for a vehicle that just came into range."""
        self._lane_index_at = -1.0  # ledger changed; the lane index is now stale
        self.vehicle_tracks[vid] = {
            "pos": st["pos"],
            "vel": st["vel"],
            "t_update": self.sim_time if is_initial else self.sim_time - self.step_length,
            # Feature [0]: how wrong the RSU's prediction was at the last update.
            # A vehicle the RSU has never heard from has no prediction history.
            "last_pred_err": 0.0,
            # Lane bookkeeping for the ledger-based n_queue (D3).
            "lane_id": (st.get("tls_features") or {}).get("lane_id"),
            "lane_position": (st.get("tls_features") or {}).get("lane_position"),
            "was_stopped": bool(float(st.get("speed", 0.0)) <= self.REDUNDANT_SPEED_EPS_MPS),
        }

    def _get_observations(self, is_initial: bool = False) -> Dict[str, np.ndarray]:
        """Gathers the normalized observation vector (width = StateVectorizer's own
        dimension, see `self.state_dim`) for each active vehicle in range.

        This is the ONLY place an observation vector is produced (design_spec_v2
        principle P1). Nothing downstream may re-vectorize from a partial state
        dict: doing so used to silently feed the model 15 constant dimensions
        out of 18 while this method's own output -- the one that was verified for
        liveness -- was discarded by the training loop.
        """
        obs = {}
        for vid in self._active_vehicle_ids():
            st = self._get_vehicle_state_dict(vid, with_queue=True)
            if st is not None:
                obs[vid] = self.vectorizer.vectorize_from_dict(st, self.target_rsu_pos)
                if vid not in self.vehicle_tracks:
                    self._register_vehicle(vid, st, is_initial=is_initial)
        return obs

    def _finalize_interval(
        self,
        vid: str,
        *,
        transmitted: bool,
        power_dbm: float,
        channel: Optional[int],
        err_at_update_m: float,
        done: bool,
    ) -> Dict[str, Any]:
        """Close one SMDP interval and produce its reward (design_spec_v2 D2).

            R_k = -( w1 * SUM_t Norm(e^2(t)) * dt/1s        <- accrues all interval
                     + w2 * Norm(P_tx)                       <- one per update
                     + w3 * Norm(CBR[ch])                    <- one per update
                     + w4 * I_redundant )                    <- one per update

        Only the error term accumulates over time. That asymmetry IS the Delta
        trade-off: leave a *moving* vehicle unaddressed and the error term bills
        you every step, while a stopped vehicle costs nothing no matter how long
        the interval, because its dead-reckoned position stays right. A vehicle
        whose interval ends without a transmission (it left the RSU's range) pays
        the accrued error only -- it burnt no power and occupied no airtime.
        """
        r_err = float(self.interval_accum.get(vid, 0.0))

        # `transmitted` means the radio was used, not that the update landed. An
        # abandoned interval passes err = inf so I_redundant evaluates to 0.
        if transmitted:
            p_lo = float(getattr(self.decoder, "p_min", 10.0))
            p_hi = float(getattr(self.decoder, "p_max", 23.0))
            r_power = min(1.0, max(0.0, (float(power_dbm) - p_lo) / max(1e-6, p_hi - p_lo)))
            ch_idx = int(channel) if channel is not None else 0
            r_cong = min(1.0, max(0.0, float(self.subchannel_cbr[ch_idx])))
            r_red = self._is_redundant_update(err_at_update_m)
        else:
            r_power = 0.0
            r_cong = 0.0
            r_red = 0.0

        reward_val = -(
            self.w1 * r_err + self.w2 * r_power + self.w3 * r_cong + self.w4 * r_red
        )
        assert not math.isnan(reward_val) and not math.isinf(reward_val), (
            f"Anti-mocking violation: NaN/Inf reward {reward_val}"
        )

        t0 = float(self.interval_start_t.get(vid, self.sim_time))
        delta_actual = max(self.step_length, self.sim_time - t0)

        record = {
            "vid": vid,
            "reward": float(reward_val),
            "delta_actual": float(delta_actual),
            "done": bool(done),
            "transmitted": bool(transmitted),
            "r_err": float(r_err),
            "r_power": float(r_power),
            "cbr": float(r_cong),
            "i_redundant": float(r_red),
            "error": float(err_at_update_m),
        }

        # The interval is closed; the next decision opens a new one.
        self.interval_accum.pop(vid, None)
        self.interval_start_t.pop(vid, None)
        self.pending_grant.pop(vid, None)
        self.next_update_t.pop(vid, None)
        return record

    def step(
        self, action_dict: Dict[str, Any]
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, float], Dict[str, bool], Dict[str, bool], Dict[str, Any]]:
        """
        Advances the scenario by one SUMO step under the standing grants.

        `action_dict` carries grants ONLY for vehicles that need a new decision
        (a new arrival, or one whose interval just closed). A grant does not fire
        on the step it is issued: it is stored and fires when the simulated clock
        reaches `t_issue + Delta`. Between those instants the vehicle transmits
        nothing and its dead-reckoning error accrues.

        Returns `rewards` for the vehicles whose SMDP interval CLOSED on this
        step, and `info["completed"]` with the matching (reward, actual Delta,
        done) records the caller needs to build a transition.
        """
        assert self.is_running, "Environment is not running. Call reset() first."
        self.current_step += 1

        # ====================================================================
        # 1. Register the new decisions
        # ====================================================================
        for vid, raw_act in action_dict.items():
            if isinstance(raw_act, (tuple, list)) and len(raw_act) == 3:
                delta, ch, p = float(raw_act[0]), int(raw_act[1]), float(raw_act[2])
            else:
                delta, ch, p = self.decoder.decode_action(raw_act)

            # The decoder owns the ranges; a grant outside them would silently
            # create a phantom subchannel with its own CBR, or an interval the
            # action space cannot express.
            assert 0 <= ch < self.num_channels, (
                f"FATAL: grant for {vid} names subchannel {ch}, outside [0, {self.num_channels})"
            )
            d_lo = float(getattr(self.decoder, "delta_min", 0.1))
            d_hi = float(getattr(self.decoder, "delta_max", 45.0))
            assert d_lo - 1e-6 <= delta <= d_hi + 1e-6, (
                f"FATAL: grant for {vid} names Delta {delta}s, outside [{d_lo}, {d_hi}]"
            )

            self.pending_grant[vid] = {"ch": int(ch), "p": float(p),
                                       "delta": float(delta), "retries": 0}
            self.next_update_t[vid] = self.sim_time + float(delta)
            self.interval_accum[vid] = 0.0
            self.interval_start_t[vid] = self.sim_time

        # ====================================================================
        # 2. Which standing grants are due to fire on this step
        # ====================================================================
        pending_transmissions: Dict[int, List[Dict[str, Any]]] = {}
        step_tx_power: Dict[str, float] = {}
        step_channel: Dict[str, int] = {}

        for vid, grant in list(self.pending_grant.items()):
            if self.sim_time < self.next_update_t.get(vid, math.inf):
                continue  # still inside its Delta -- stays silent
            st = self._get_vehicle_state_dict(vid)
            if st is None:
                continue  # out of range; handled as an exit below
            ch = int(grant["ch"])
            p = float(grant["p"])
            self.tx_powers.append(p)
            step_tx_power[vid] = p
            step_channel[vid] = ch
            pending_transmissions.setdefault(ch, []).append({
                "vid": vid,
                "pos": st["pos"],
                "vel": st["vel"],
                "tx_dbm": p,
                "dist": st["dist_to_rsu"],
                "ch": ch,
            })

        # ====================================================================
        # 3. Step SUMO simulation
        # ====================================================================
        libsumo.simulationStep()
        self.sim_time = float(libsumo.simulation.getTime())

        # ====================================================================
        # ANTI-MOCKING ASSERTION 1: TraCI / libsumo Time Advance Verification
        # Ported verbatim from src/aoi_env.py::AoiV2IEnv.step (L687-696).
        # ====================================================================
        assert libsumo is not None, "FATAL: libsumo/traci is not imported or initialized!"
        assert self.sim_time > self._prev_sim_time, (
            f"FATAL: Simulation time regression/freeze detected: {self.sim_time} <= {self._prev_sim_time}"
        )
        assert hasattr(libsumo.simulation, "getLoadedNumber") or hasattr(libsumo.simulation, "getTime"), (
            "FATAL: Fake sumo module detected!"
        )

        # ====================================================================
        # ANTI-MOCKING ASSERTION 2: Actual SUMO Vehicle Coordinates & Motion
        # Ported verbatim from src/aoi_env.py::AoiV2IEnv.step (L698-725).
        # ====================================================================
        raw_vehicle_ids = libsumo.vehicle.getIDList()
        assert isinstance(raw_vehicle_ids, (list, tuple)), (
            "FATAL: sumo.vehicle.getIDList() did not return a valid list!"
        )
        active_ids = set(raw_vehicle_ids)
        # This assertion deliberately queries SUMO directly -- that is what makes
        # it an anti-mocking check -- and it runs immediately after the step, so
        # its result is also the freshest possible fill for the per-instant cache.
        self._active_ids = active_ids
        self._active_ids_at = self.sim_time

        for vid in raw_vehicle_ids:
            v_pos = libsumo.vehicle.getPosition(vid)
            v_spd = libsumo.vehicle.getSpeed(vid)

            assert isinstance(v_pos[0], float) and isinstance(v_pos[1], float), (
                f"FATAL: Vehicle {vid} position coordinates must be floats, got {v_pos}"
            )
            assert isinstance(v_spd, float), f"FATAL: Vehicle {vid} speed must be float, got {v_spd}"
            assert (
                -5000.0 <= v_pos[0] <= self.network_max_x + 5000.0
                and -5000.0 <= v_pos[1] <= self.network_max_y + 5000.0
            ), (
                f"FATAL: Vehicle {vid} position {v_pos} is out of SUMO grid bounds [0, {self.network_max_x}]!"
            )

            if vid in self._prev_all_positions and v_spd > 1.0:
                p_prev = self._prev_all_positions[vid]
                dist_moved = math.hypot(v_pos[0] - p_prev[0], v_pos[1] - p_prev[1])
                assert dist_moved > 0.0, (
                    f"FATAL: Vehicle {vid} speed is {v_spd} m/s but coordinate did not change from {p_prev}!"
                )
            self._prev_all_positions[vid] = (float(v_pos[0]), float(v_pos[1]))

        # ====================================================================
        # 4. Channel Busy Ratio, measured from real 802.11p airtime.
        #        CBR[ch] = n_grants[ch] * frame_airtime / step_length
        #    Occupancy is charged on the grant, before the SINR outcome is known:
        #    a failed frame still burns its airtime.
        # ====================================================================
        busy_time_s = [0.0] * self.num_channels
        for ch_idx, group in pending_transmissions.items():
            busy_time_s[ch_idx] += len(group) * self.frame_airtime_s
        self.subchannel_cbr = [
            min(1.0, b / max(self.step_length, 1e-9)) for b in busy_time_s
        ]
        self.cbr = float(sum(self.subchannel_cbr) / max(1, self.num_channels))
        self.recorded_cbrs.append(self.cbr)
        cbr = self.cbr

        # ====================================================================
        # 5. Age, dead-reckoning error, and SMDP interval accrual.
        #    `age` is the true elapsed time since this vehicle's last successful
        #    update. It is NOT clamped: the former max(1.0, .) floor pinned 98.8%
        #    of samples to 1.0, which flattened the AoI metric to a constant and
        #    made the extrapolation predict 1 s ahead of a 0.1 s reality.
        # ====================================================================
        rewards: Dict[str, float] = {}
        terminateds: Dict[str, bool] = {}
        truncateds: Dict[str, bool] = {}
        reward_details: Dict[str, Dict[str, float]] = {}
        completed: List[Dict[str, Any]] = []
        err_now: Dict[str, float] = {}

        is_truncated = self.current_step >= self.max_steps

        for vid in list(self.vehicle_tracks.keys()):
            if vid not in active_ids:
                # Vehicle left the network: close any open interval as terminal.
                if vid in self.interval_start_t:
                    rec = self._finalize_interval(
                        vid, transmitted=False, power_dbm=0.0, channel=None,
                        err_at_update_m=0.0, done=True,
                    )
                    completed.append(rec)
                    rewards[vid] = rec["reward"]
                    reward_details[vid] = rec
                self.vehicle_tracks.pop(vid, None)
                self._lane_index_at = -1.0
                self.last_speeds.pop(vid, None)
                terminateds[vid] = True
                truncateds[vid] = False
                continue

            track = self.vehicle_tracks[vid]
            st = self._get_vehicle_state_dict(vid)
            if st is None:
                # Still in the simulation but outside the RSU disc -- same exit path.
                if vid in self.interval_start_t:
                    rec = self._finalize_interval(
                        vid, transmitted=False, power_dbm=0.0, channel=None,
                        err_at_update_m=0.0, done=True,
                    )
                    completed.append(rec)
                    rewards[vid] = rec["reward"]
                    reward_details[vid] = rec
                self.vehicle_tracks.pop(vid, None)
                self._lane_index_at = -1.0
                terminateds[vid] = True
                truncateds[vid] = False
                continue

            age = max(0.0, self.sim_time - float(track["t_update"]))
            err = estimation_error(st["pos"], track["pos"], track["vel"], age)
            err_now[vid] = err

            self.recorded_errors.append(err)
            self.recorded_aois.append(age)
            self.per_vehicle_aois.setdefault(vid, []).append(age)
            self.per_vehicle_errors.setdefault(vid, []).append(err)
            if st["speed"] < 2.0:
                self.low_speed_errors.append(err)
            else:
                self.high_speed_errors.append(err)

            # Interval accrual: the error term of the SMDP reward (D2).
            if vid in self.interval_accum:
                self.interval_accum[vid] += norm_sq_error(err) * (self.step_length / 1.0)

            terminateds[vid] = False
            truncateds[vid] = is_truncated

        # ====================================================================
        # 6. Resolve the uplinks that fired, via Communications.judge_uplink.
        # ====================================================================
        assert hasattr(comm, "judge_uplink"), "FATAL: Communications.judge_uplink is missing!"
        judge_called = False
        n_pending_tx = sum(len(g) for g in pending_transmissions.values())
        n_probs_evaluated = 0

        # Two grants on the same subchannel in the same step do not necessarily
        # collide: a frame is 448 us at 6 Mbps while a step is 100 ms, so a tagged
        # frame is hit only by frames starting within one frame duration of it.
        # Each co-channel grant therefore interferes with probability
        # 2*T_air/T_step (the classic vulnerable period), drawn from the seeded
        # channel RNG. judge_uplink's Rayleigh-SINR physics is untouched; only the
        # temporal overlap it is asked about changes.
        p_overlap = min(1.0, 2.0 * self.frame_airtime_s / max(self.step_length, 1e-9))
        self._last_p_overlap = p_overlap

        for ch, group in pending_transmissions.items():
            comm_group = [(item["vid"], item["tx_dbm"], item["dist"]) for item in group]
            succ_probs = {}
            for tagged in comm_group:
                interferers = [
                    other for other in comm_group
                    if other[0] != tagged[0] and comm.draw_overlap(p_overlap)
                ]
                probs = comm.judge_uplink(
                    [tagged] + interferers, num_subchannels=self.num_channels
                )
                succ_probs[tagged[0]] = probs[tagged[0]]
            judge_called = True

            for item in group:
                self.total_tx_attempts += 1
                vid = item["vid"]
                assert vid in succ_probs, (
                    f"FATAL: judge_uplink did not evaluate transmitting vehicle {vid}!"
                )
                prob = succ_probs[vid]
                # ============================================================
                # ANTI-MOCKING ASSERTION 3: Rayleigh SINR value validation
                # ============================================================
                assert 0.0 <= prob <= 1.0, (
                    f"FATAL: Uplink success probability {prob} for {vid} out of [0, 1]!"
                )
                assert not math.isnan(prob) and not math.isinf(prob), (
                    f"FATAL: Uplink success probability {prob} is NaN/Inf!"
                )
                n_probs_evaluated += 1
                is_succ = random.random() < prob

                last_t = float(self.vehicle_tracks.get(vid, {}).get("t_update", self.sim_time))
                self.peak_aois.append(max(0.0, self.sim_time - last_t))

                if is_succ:
                    e_upd = err_now.get(vid, 0.0)
                    rec = self._finalize_interval(
                        vid, transmitted=True, power_dbm=item["tx_dbm"],
                        channel=item["ch"], err_at_update_m=e_upd, done=False,
                    )
                    completed.append(rec)
                    rewards[vid] = rec["reward"]
                    reward_details[vid] = rec

                    # Refresh the ledger with what the vehicle just reported.
                    st_after = self._get_vehicle_state_dict(vid)
                    tls_after = (st_after or {}).get("tls_features") or {}
                    self._lane_index_at = -1.0
                    self.vehicle_tracks[vid] = {
                        "pos": item["pos"],
                        "vel": item["vel"],
                        "t_update": self.sim_time,
                        "last_pred_err": float(e_upd),
                        "lane_id": tls_after.get("lane_id"),
                        "lane_position": tls_after.get("lane_position"),
                        "was_stopped": bool(
                            float((st_after or {}).get("speed", 0.0)) <= self.REDUNDANT_SPEED_EPS_MPS
                        ),
                    }
                else:
                    self.total_tx_fails += 1
                    # D7: retry on the next step as a continuation of the SAME
                    # decision -- the model is not queried again, so this is one
                    # SMDP interval that simply ran longer than the Delta asked for.
                    grant = self.pending_grant.get(vid)
                    if grant is None:
                        continue
                    grant["retries"] = int(grant.get("retries", 0)) + 1
                    if grant["retries"] >= self.MAX_TX_RETRIES:
                        self.total_tx_abandoned += 1
                        # The interval is closed without the update ever landing.
                        # It still pays power and congestion -- the radio really
                        # did transmit, MAX_TX_RETRIES times over -- but it cannot
                        # pay I_redundant: that penalty is for telling the RSU
                        # something it already knew, and here the RSU was told
                        # nothing at all. Passing infinity makes that explicit
                        # rather than letting the live error decide, which would
                        # brand an undelivered update "redundant" whenever dead
                        # reckoning happened to be accurate at that instant.
                        rec = self._finalize_interval(
                            vid, transmitted=True, power_dbm=item["tx_dbm"],
                            channel=item["ch"],
                            err_at_update_m=float("inf"),
                            done=False,
                        )
                        completed.append(rec)
                        rewards[vid] = rec["reward"]
                        reward_details[vid] = rec
                    else:
                        self.next_update_t[vid] = self.sim_time  # due again next step

        if pending_transmissions:
            assert judge_called, "Anti-mocking violation: Communications.judge_uplink was bypassed"
            assert n_probs_evaluated == n_pending_tx, (
                "FATAL: judge_uplink did not evaluate all transmitting vehicles! "
                f"({n_probs_evaluated} != {n_pending_tx})"
            )

        # ====================================================================
        # ANTI-MOCKING ASSERTION 4: Reward Mathematical Specification Check
        # Every normalized penalty component must lie in its declared range, the
        # emitted reward must re-derive exactly from the weighted 4-term formula,
        # and a penalty-based reward must be <= 0. The congestion term is
        # re-derived from the raw grant list and the Communications airtime model
        # rather than trusting the cached subchannel_cbr array.
        # ====================================================================
        air = comm.frame_airtime_s(self.payload_bytes)
        assert air > 0.0, f"FATAL: Communications reported non-positive frame airtime {air}"
        re_cbr = [
            min(1.0, len(pending_transmissions.get(c, [])) * air / max(self.step_length, 1e-9))
            for c in range(self.num_channels)
        ]
        for vid, r_info in reward_details.items():
            re_ = r_info["r_err"]
            rp_ = r_info["r_power"]
            rc_ = r_info["cbr"]
            ir_ = r_info["i_redundant"]
            assert re_ >= 0.0, f"FATAL: accrued error penalty for {vid} is negative: {re_}"
            assert 0.0 <= rp_ <= 1.0, f"FATAL: power term for {vid} out of [0,1]: {rp_}"
            assert 0.0 <= rc_ <= 1.0, f"FATAL: congestion term for {vid} out of [0,1]: {rc_}"
            assert ir_ in (0.0, 1.0), f"FATAL: I_redundant for {vid} is not binary: {ir_}"
            if r_info["transmitted"] and vid in step_channel:
                exp_cbr = re_cbr[step_channel[vid]]
                assert math.isclose(rc_, exp_cbr, abs_tol=1e-9), (
                    f"FATAL: CBR term for {vid} does not re-derive from measured airtime: "
                    f"{rc_} != {exp_cbr}"
                )
            expected = -(self.w1 * re_ + self.w2 * rp_ + self.w3 * rc_ + self.w4 * ir_)
            assert math.isclose(r_info["reward"], expected, abs_tol=1e-9), (
                f"FATAL: reward for {vid} does not re-derive from the 4-term formula: "
                f"{r_info['reward']} != {expected}"
            )
            assert r_info["reward"] <= 0.0, (
                f"FATAL: penalty-based reward must be <= 0, got {r_info['reward']} for {vid}"
            )

        next_obs = self._get_observations()

        # Finalize step state for the next time-regression check (Assertion 1).
        self._prev_sim_time = self.sim_time

        info = {
            "sim_time": self.sim_time,
            "step": self.current_step,
            "cbr": cbr,
            "subchannel_cbr": list(self.subchannel_cbr),
            "frame_airtime_s": self.frame_airtime_s,
            "tx_attempts": self.total_tx_attempts,
            "tx_fails": self.total_tx_fails,
            "tx_abandoned": self.total_tx_abandoned,
            # Vehicles whose SMDP interval closed on this step. The caller builds
            # one transition per entry and asks the model for the next grant.
            "completed": completed,
            # Vehicles that currently hold no standing grant and therefore need
            # a decision on the next call.
            "needs_decision": [
                vid for vid in next_obs if vid not in self.pending_grant
            ],
            "reward_details": reward_details,
        }

        return next_obs, rewards, terminateds, truncateds, info


    def get_metrics(self) -> Dict[str, Any]:
        """Calculates 6 IEEE TWC standard metrics."""
        # design_spec_v2 D8: Peak AoI is the MAXIMUM age reached, over every
        # vehicle and every instant -- not the mean of the per-update peaks. The
        # mean of the peaks is reported alongside it as `mean_peak_aoi` because
        # both conventions appear in the literature and the paper must say which
        # one its table uses.
        mean_aoi = float(np.mean(self.recorded_aois)) if self.recorded_aois else 0.0
        all_peaks = list(self.peak_aois) + list(self.recorded_aois)
        peak_aoi = float(np.max(all_peaks)) if all_peaks else 0.0
        mean_peak_aoi = float(np.mean(self.peak_aois)) if self.peak_aois else 0.0

        packet_loss = float(self.total_tx_fails / max(1, self.total_tx_attempts))
        mean_err = float(np.mean(self.recorded_errors)) if self.recorded_errors else 0.0
        max_err = float(np.max(self.recorded_errors)) if self.recorded_errors else 0.0
        low_spd_err = float(np.mean(self.low_speed_errors)) if self.low_speed_errors else mean_err
        high_spd_err = float(np.mean(self.high_speed_errors)) if self.high_speed_errors else mean_err

        # With zero transmissions there is no measured power; fall back to the
        # decoder's minimum (no power spent) rather than a literal that assumed
        # the old [20, 30] dBm range.
        avg_power = (
            float(np.mean(self.tx_powers))
            if self.tx_powers
            else float(getattr(self.decoder, "p_min", 10.0))
        )
        # Energy = power x time, and the time a transmission actually occupies is
        # the 802.11p frame airtime this same class charges CBR for (448 us for a
        # 300 B frame at 6 Mbps). The former literal 0.001 s was an unsourced
        # stand-in that overstated every energy figure by 0.001/0.000448 = 2.23x.
        total_energy_j = float(
            sum(10.0 ** ((p - 30.0) / 10.0) * self.frame_airtime_s for p in self.tx_powers)
        )

        # Jain's fairness
        def jains(vals: List[float]) -> float:
            if not vals:
                return 1.0
            s, sq = sum(vals), sum(v ** 2 for v in vals)
            if sq <= 1e-12:
                return 1.0
            return float(np.clip((s ** 2) / (len(vals) * sq), 0.0, 1.0))

        veh_aoi_means = [float(np.mean(v)) for v in self.per_vehicle_aois.values() if v]
        veh_err_means = [float(np.mean(v)) for v in self.per_vehicle_errors.values() if v]

        return {
            "mean_aoi": round(mean_aoi, 4),
            "peak_aoi": round(peak_aoi, 4),
            "mean_peak_aoi": round(mean_peak_aoi, 4),
            "packet_loss_rate": round(packet_loss, 4),
            "mean_error": round(mean_err, 4),
            "max_error": round(max_err, 4),
            "low_speed_error": round(low_spd_err, 4),
            "high_speed_error": round(high_spd_err, 4),
            "avg_tx_power_dbm": round(avg_power, 4),
            "total_energy_joules": round(total_energy_j, 6),
            "jains_fairness_aoi": round(jains(veh_aoi_means), 4),
            "jains_fairness_err": round(jains(veh_err_means), 4),
            "tx_attempts": self.total_tx_attempts,
            "tx_fails": self.total_tx_fails,
            "tx_abandoned": self.total_tx_abandoned,
            # Emptiness signal. Every other metric degrades to a plausible-looking
            # number when no vehicle was ever in range (mean_aoi 0.0, power at the
            # decoder floor), and a run like that used to pass as a healthy one --
            # warmup_steps=35 produced exactly that and went unnoticed.
            # `n_observations == 0` says plainly that nothing was measured.
            "n_observations": len(self.recorded_aois),
            "n_vehicles_seen": len(self.per_vehicle_aois),
            # Measured airtime occupancy over the episode (network mean per step).
            "mean_cbr": round(float(np.mean(self.recorded_cbrs)) if self.recorded_cbrs else 0.0, 6),
            "max_cbr": round(float(np.max(self.recorded_cbrs)) if self.recorded_cbrs else 0.0, 6),
        }

    def close(self) -> None:
        """Closes SUMO cleanly and releases resources to prevent memory leaks."""
        if self.is_running and libsumo is not None:
            try:
                libsumo.close()
            except Exception:
                pass
            self.is_running = False

        self.vehicle_tracks.clear()
        self.prev_positions.clear()
        self.scheduled_tx.clear()
        self.next_update_t.clear()
        self.pending_grant.clear()
        self.interval_accum.clear()
        self.interval_start_t.clear()


def run_hot_swap_training(
    model_name: Union[str, type, Callable] = "GenericPolicy",
    model_cls: Optional[Callable] = None,
    total_steps: int = 2000,
    episodes: int = 1,
    density: float = 25.0,
    batch_size: int = 32,
    swap_interval: int = 20,
    act_device: Optional[Union[str, torch.device]] = None,
    rest_device: Optional[Union[str, torch.device]] = None,
    hparams: Optional[Dict[str, Any]] = None,
    seed: int = 42,
    checkpoint_dir: str = "/home/imnyj/Workspace/paper4/coder/checkpoints",
    tensorboard_dir: str = "/home/imnyj/Workspace/paper4/coder/logs/tensorboard",
    log_csv_path: Optional[str] = None,
    num_vehicles: Optional[int] = None,
    # 350 steps = 35 simulated seconds. The former 35 (3.5 s) was not long
    # enough for ANY vehicle to reach the RSU disc from its spawn edge, so a run
    # started with it observed nothing at all -- measured: 0 vehicles in range at
    # 3.5 s, 1 at 15 s, 22 at 35 s. Short smoke runs looked healthy anyway
    # because the empty-case metric fallbacks returned plausible numbers.
    warmup_steps: int = 350,
    resume: bool = False,
    start_episode: int = 0,
) -> Dict[str, Any]:
    """
    Full end-to-end hot-swap training loop integrating Act model serving,
    asynchronous background training, TensorBoard logging, and periodic checkpoints.
    Supports 200,000 steps (e.g. 2,000 steps x 100 episodes).

    Args:
        resume: When True, locate the highest-numbered `{model_name}_ep*.pt`
            checkpoint in `checkpoint_dir`, load it, and continue the episode
            loop from the episode after it. Default False preserves the
            previous fresh-start behaviour exactly.
        start_episode: Explicit 0-based episode index to start from. Ignored
            (overridden) when `resume` successfully locates a checkpoint.
    """
    model_name_str = model_name if isinstance(model_name, str) else getattr(model_name, "__name__", "CustomModel")

    # Seed configuration
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(tensorboard_dir, exist_ok=True)
    if log_csv_path is None:
        os.makedirs("/home/imnyj/Workspace/paper4/coder/logs/training", exist_ok=True)
        log_csv_path = f"/home/imnyj/Workspace/paper4/coder/logs/training/{model_name_str}_progress.csv"

    # Initialize TensorBoard Writer
    writer = None
    if SummaryWriter is not None:
        try:
            writer = SummaryWriter(log_dir=os.path.join(tensorboard_dir, f"{model_name_str}_seed{seed}_{int(time.time())}"))
        except Exception:
            writer = None

    trainer = HotSwapTrainer(
        model_name=model_name_str,
        model_cls=model_cls if model_cls is not None else (model_name if callable(model_name) and not isinstance(model_name, str) else None),
        batch_size=batch_size,
        swap_interval=swap_interval,
        act_device=act_device,
        rest_device=rest_device,
        hparams=hparams,
    )

    # Steps per episode calculation
    steps_per_ep = max(10, total_steps // max(1, episodes))

    # --- Resume support -----------------------------------------------------
    # Default (resume=False, start_episode=0) is byte-for-byte the old behaviour.
    start_ep = max(0, int(start_episode))
    resumed_from: Optional[str] = None
    best_reward = -float("inf")
    if resume:
        ckpt_glob = os.path.join(checkpoint_dir, f"{model_name_str}_ep*.pt")
        candidates: List[Tuple[int, str]] = []
        for path in glob.glob(ckpt_glob):
            m = re.search(rf"{re.escape(model_name_str)}_ep(\d+)\.pt$", os.path.basename(path))
            if m:
                candidates.append((int(m.group(1)), path))
        if candidates:
            last_ep_1based, resumed_from = max(candidates, key=lambda c: c[0])
            loaded_ckpt = trainer.load_checkpoint(resumed_from)
            if "best_reward" in loaded_ckpt and loaded_ckpt["best_reward"] is not None:
                best_reward = float(loaded_ckpt["best_reward"])
            # Checkpoints are named with 1-based episode numbers (`_ep010.pt`
            # is written after episode index 9), so resume at that index.
            start_ep = min(int(last_ep_1based), int(episodes))

        best_ckpt_candidate = os.path.join(checkpoint_dir, f"{model_name_str}_best.pt")
        if os.path.exists(best_ckpt_candidate):
            try:
                best_ckpt_data = torch.load(best_ckpt_candidate, map_location="cpu")
                if "best_reward" in best_ckpt_data and best_ckpt_data["best_reward"] is not None:
                    best_reward = max(best_reward, float(best_ckpt_data["best_reward"]))
            except Exception:
                pass

    trainer.start()

    t_start = time.perf_counter()
    # Account for the steps already consumed by the completed episodes so the
    # `total_steps` budget is not spent twice.
    global_step = min(int(start_ep) * steps_per_ep, total_steps)
    episodic_records: List[Dict[str, Any]] = []

    # One reward for every baseline. Passed explicitly rather than relying on the
    # AoiV2IEnv defaults so that a reader of this loop can see which reward the
    # 200k-step runs were trained against, and so it stays pinned to the same
    # constant `src/evaluate.py` and `src/hpo.py` read.
    env_reward_weights = {k: float(v) for k, v in DEFAULT_REWARD_WEIGHTS.items()}

    try:
        for ep in range(start_ep, episodes):
            if global_step >= total_steps:
                break

            # Create genuine SUMO environment for this episode
            env = AoiV2IEnv(
                density=density,
                seed=seed + ep,
                max_steps=steps_per_ep,
                warmup_steps=warmup_steps,
                **env_reward_weights,
            )
            obs, info = env.reset()

            ep_rewards: List[float] = []
            ep_deltas: List[float] = []

            # ----------------------------------------------------------------
            # Event-driven SMDP loop (design_spec_v2, "structure").
            #
            # Not a gym rollout: each vehicle has its OWN decision epochs, spaced
            # by the Delta the policy chose for it, so there is no single global
            # (s, a, r, s') tick. `open_decision[vid]` holds the observation and
            # raw action of the interval currently in flight for that vehicle;
            # when the environment reports that interval closed, the transition
            # is assembled and the vehicle is asked for its next grant.
            # ----------------------------------------------------------------
            trainer.scheduler.reset()
            open_decision: Dict[str, Dict[str, Any]] = {}

            # Everyone in range at reset needs an opening decision.
            action_dict: Dict[str, Any] = {}
            for vid, s_vec in obs.items():
                grant, raw_action = trainer.scheduler.decide_grant(vid, s_vec)
                open_decision[vid] = {"state": np.asarray(s_vec, dtype=np.float32),
                                      "raw_action": raw_action}
                action_dict[vid] = grant
                ep_deltas.append(float(grant[0]))

            for step in range(steps_per_ep):
                if global_step >= total_steps:
                    break
                global_step += 1

                next_obs, rewards, terminateds, truncateds, step_info = env.step(action_dict)

                # 1. Close every interval the environment finished this step.
                action_dict = {}
                for rec in step_info["completed"]:
                    vid = rec["vid"]
                    prev = open_decision.pop(vid, None)
                    if prev is None:
                        continue
                    s2 = next_obs.get(vid)
                    if s2 is None:
                        # Vehicle is gone: terminal transition with a zero next state.
                        s2 = np.zeros(trainer.scheduler.state_dim, dtype=np.float32)
                        done = True
                    else:
                        done = bool(rec["done"])
                    trainer.scheduler.push_transition(
                        state=prev["state"],
                        raw_action=prev["raw_action"],
                        reward=rec["reward"],
                        next_state=np.asarray(s2, dtype=np.float32),
                        done=done,
                        delta_t=rec["delta_actual"],
                    )
                    ep_rewards.append(float(rec["reward"]))

                # 2. Ask the policy for a grant for every vehicle that now holds
                #    none -- new arrivals and the intervals just closed.
                for vid in step_info["needs_decision"]:
                    s_vec = next_obs.get(vid)
                    if s_vec is None:
                        continue
                    grant, raw_action = trainer.scheduler.decide_grant(vid, s_vec)
                    open_decision[vid] = {"state": np.asarray(s_vec, dtype=np.float32),
                                          "raw_action": raw_action}
                    action_dict[vid] = grant
                    ep_deltas.append(float(grant[0]))

                # 3. Drop bookkeeping for vehicles that left without closing.
                for vid in [v for v in open_decision if v not in next_obs]:
                    open_decision.pop(vid, None)

                obs = next_obs

                # Memory management & background yield
                if global_step % 100 == 0:
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

            # Episode summary
            metrics = env.get_metrics()
            env.close()
            del env
            gc.collect()

            ep_mean_r = float(np.mean(ep_rewards)) if ep_rewards else 0.0
            trainer_metrics = trainer.background_trainer.get_metrics()

            # TensorBoard logging
            if writer is not None:
                writer.add_scalar("Reward/EpisodicMean", ep_mean_r, global_step)
                writer.add_scalar("Loss/MeanRecent", trainer_metrics["mean_recent_loss"], global_step)
                writer.add_scalar("AoI/Mean", metrics["mean_aoi"], global_step)
                writer.add_scalar("AoI/Peak", metrics["peak_aoi"], global_step)
                if ep_deltas:
                    writer.add_scalar("Action/MeanDelta", float(np.mean(ep_deltas)), global_step)
                writer.add_scalar("Error/Mean", metrics["mean_error"], global_step)
                writer.add_scalar("Error/Max", metrics["max_error"], global_step)
                writer.add_scalar("Outage/Rate", metrics["packet_loss_rate"], global_step)
                writer.add_scalar("Power/Avg_dBm", metrics["avg_tx_power_dbm"], global_step)
                writer.add_scalar("HotSwap/Count", trainer_metrics["hot_swap_stats"]["swap_count"], global_step)

            # Periodic and Best Checkpointing
            if (ep + 1) % 10 == 0 or (ep + 1) == episodes:
                ckpt_path = os.path.join(checkpoint_dir, f"{model_name_str}_ep{ep+1:03d}.pt")
                trainer.save_checkpoint(ckpt_path, best_reward=best_reward)

            if ep_rewards and ep_mean_r > best_reward:
                best_reward = ep_mean_r
                best_ckpt_path = os.path.join(checkpoint_dir, f"{model_name_str}_best.pt")
                trainer.save_checkpoint(best_ckpt_path, best_reward=best_reward)

            ep_record = {
                "episode": ep + 1,
                "global_step": global_step,
                "mean_reward": round(ep_mean_r, 4),
                "mean_loss": trainer_metrics["mean_recent_loss"],
                "swap_count": trainer_metrics["hot_swap_stats"]["swap_count"],
                # The Delta the policy actually asked for. Distinct from
                # `mean_aoi`, which is the age the RSU actually observed.
                "mean_delta": round(float(np.mean(ep_deltas)), 4) if ep_deltas else 0.0,
                "n_decisions": len(ep_deltas),
                **metrics,
            }
            episodic_records.append(ep_record)

    finally:
        trainer.stop()
        if writer is not None:
            writer.close()

    # Save episodic progress CSV
    df_progress = pd.DataFrame(episodic_records)
    if resumed_from is not None and os.path.exists(log_csv_path):
        # Preserve the pre-resume history instead of truncating the log.
        try:
            df_prev = pd.read_csv(log_csv_path)
            if "episode" in df_prev.columns:
                df_prev = df_prev[df_prev["episode"] <= start_ep]
            df_progress = pd.concat([df_prev, df_progress], ignore_index=True)
        except Exception:
            pass
    df_progress.to_csv(log_csv_path, index=False)

    elapsed_s = max(1e-4, time.perf_counter() - t_start)
    latency_stats = trainer.scheduler.get_latency_stats()
    hot_swap_stats = trainer.hot_swap_manager.get_stats()
    final_metrics = trainer.background_trainer.get_metrics()

    return {
        "model_name": model_name,
        "total_steps": global_step,
        "episodes": episodes,
        "elapsed_seconds": round(elapsed_s, 4),
        "throughput_steps_per_sec": round(global_step / elapsed_s, 2),
        "mean_step_reward": round(float(np.mean([r["mean_reward"] for r in episodic_records])), 4)
        if episodic_records
        else 0.0,
        # Mean AoI actually measured, and the mean Delta the policy actually
        # asked for. These were the same number before: `mean_scheduled_delta`
        # was reading `mean_aoi` while the real Delta was collected and dropped.
        "mean_aoi": round(float(np.mean([r["mean_aoi"] for r in episodic_records])), 4)
        if episodic_records
        else 0.0,
        "mean_scheduled_delta": round(float(np.mean([r["mean_delta"] for r in episodic_records])), 4)
        if episodic_records
        else 0.0,
        "training_steps": final_metrics["training_steps"],
        "mean_recent_loss": final_metrics["mean_recent_loss"],
        "swap_count": hot_swap_stats["swap_count"],
        "failed_swaps": hot_swap_stats["failed_swaps"],
        "mean_swap_latency_ms": hot_swap_stats["mean_swap_latency_ms"],
        "inference_latency": latency_stats,
        "act_device": str(trainer.act_device),
        "rest_device": str(trainer.rest_device),
        "log_csv_path": log_csv_path,
        "start_episode": start_ep,
        "resumed_from_checkpoint": resumed_from,
    }
