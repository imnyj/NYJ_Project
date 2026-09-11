"""Independent verification of the two fixes made on 2026-09-05.

Runs the real pipeline (real SUMO, real models) and writes what it measured to
CSV, rather than restating what the unit tests assert.

  A. Observation feature [13] (`n_active`) no longer saturates.
     Drives a genuine AoiV2IEnv at the top of the density grid, records the
     feature for every observation the environment emitted, and reports the
     clipped fraction under the new normaliser and under the old literal 100.0.

  B. `{model}_best.pt` is selected by a density-controlled held-out episode.
     Runs a short multi-density training, then checks against the progress CSV
     and the checkpoint on disk that
       - every validation ran at the same density, and that density is the
         median of the training schedule;
       - the stored `best_reward` is the best validation score, not the best
         training episode;
       - no validation transition reached the replay buffer;
       - the added cost is close to the intended fraction of the run.

Run with a PRIVATE scenario directory or a concurrent process will regenerate
the SUMO files underneath it:

    PAPER4_SUMO_DIR=/tmp/verify_sumo /home/imnyj/venv/bin/python \
        etc/scripts/verify_checkpoint_selection_and_contention.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.hot_swap_trainer as H  # noqa: E402
import src.rl_interface as rli  # noqa: E402
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402
from src.sumo.make_sumo_set import DENSITY_GRID  # noqa: E402

OUT_DIR = "/home/imnyj/Workspace/paper4/coder/results/diagnostics"


class ProbePolicy(nn.Module):
    """A real nn.Module with a real optimiser; the point is the pipeline, not it."""

    def __init__(self, state_dim: int = STATE_DIM, num_channels: int = 4,
                 gamma: float = 0.9, **hparams: Any) -> None:
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.gamma = float(gamma)
        self.hparams = hparams
        self.decoder = ActionDecoder(num_channels=num_channels)
        self.net = nn.Linear(self.state_dim, 3)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=1e-3)

    def select_action(self, state, deterministic: bool = False):
        s = torch.as_tensor(np.asarray(state, dtype=np.float32))
        with torch.no_grad():
            raw = self.net(s).numpy()
        if not deterministic:
            raw = raw + np.random.normal(0.0, 0.3, size=raw.shape).astype(np.float32)
        delta, ch, power = self.decoder.decode_action(raw)
        return (delta, ch, power), raw.astype(np.float32), {"action_idx": int(ch)}

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        pred = self.net(batch["state"])
        loss = ((pred - batch["action"]) ** 2).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return {"loss": float(loss.item())}


# ---------------------------------------------------------------------------
# A. Contention feature saturation
# ---------------------------------------------------------------------------
def check_contention_saturation(density: float, steps: int, warmup: int,
                                seed: int) -> pd.DataFrame:
    env = H.AoiV2IEnv(density=density, seed=seed, max_steps=steps, warmup_steps=warmup)
    obs, _info = env.reset()
    counts: List[float] = []
    try:
        action_dict = {vid: (1.0, 0, 15.0) for vid in obs}
        for _ in range(steps):
            counts.append(float(env._count_active_vehicles()))
            next_obs, _r, _t, _tr, step_info = env.step(action_dict)
            action_dict = {vid: (1.0, 0, 15.0) for vid in step_info["needs_decision"]
                           if vid in next_obs}
            obs = next_obs
        # Nothing here reads a reward, but closing with intervals open logs a
        # warning that would look like a leak in this script's output.
        env.finalize_open_intervals()
    finally:
        env.close()

    arr = np.asarray(counts, dtype=np.float64)
    rows = []
    for label, divisor in (("new (N_ACTIVE_MAX_OBS)", rli.N_ACTIVE_MAX_OBS),
                           ("old (literal 100.0)", 100.0)):
        feature = np.clip(arr / divisor, 0.0, 1.0)
        rows.append({
            "density": density,
            "normaliser": label,
            "divisor": divisor,
            "n_steps_observed": int(arr.size),
            "in_range_mean": round(float(arr.mean()), 3),
            "in_range_max": round(float(arr.max()), 3),
            "feature_mean": round(float(feature.mean()), 4),
            "feature_max": round(float(feature.max()), 4),
            "saturated_fraction": round(float((feature >= 1.0).mean()), 4),
            "distinct_values": int(np.unique(np.round(feature, 6)).size),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# B. Checkpoint selection
# ---------------------------------------------------------------------------
def check_selection(tmp_root: str, episodes: int, steps_per_ep: int,
                    warmup: int, validate_every: int, seed: int) -> Dict[str, Any]:
    schedule = [float(d) for d in DENSITY_GRID]
    ckpt_dir = os.path.join(tmp_root, "ckpt")
    log_dir = os.path.join(tmp_root, "logs")

    # Count every transition that reaches the buffer, tagged with whether the
    # background trainer was paused at the time. A validation episode runs under
    # the pause and pushes nothing, so any push seen while paused is a leak.
    leaks = {"while_paused": 0, "while_training": 0}
    original_streamer_push = H.TransitionStreamer.push

    def counting_push(self, *a, **k):
        leaks["while_paused" if _paused_now[0] else "while_training"] += 1
        return original_streamer_push(self, *a, **k)

    _paused_now = [False]
    original_pause = H.BackgroundTrainer.pause
    original_resume = H.BackgroundTrainer.resume

    def traced_pause(self, timeout: float = 10.0):
        _paused_now[0] = True
        return original_pause(self, timeout)

    def traced_resume(self):
        result = original_resume(self)
        if self._pause_depth == 0:
            _paused_now[0] = False
        return result

    H.TransitionStreamer.push = counting_push
    H.BackgroundTrainer.pause = traced_pause
    H.BackgroundTrainer.resume = traced_resume
    t0 = time.perf_counter()
    try:
        summary = H.run_hot_swap_training(
            model_name="VerifySelect", model_cls=ProbePolicy,
            total_steps=episodes * steps_per_ep, episodes=episodes,
            density=schedule, batch_size=16, swap_interval=5,
            seed=seed, warmup_steps=warmup,
            validate_every_episodes=validate_every,
            act_device="cpu", rest_device="cpu",
            checkpoint_dir=ckpt_dir, log_dir=log_dir,
            tensorboard_dir=os.path.join(tmp_root, "tb"),
        )
    finally:
        H.TransitionStreamer.push = original_streamer_push
        H.BackgroundTrainer.pause = original_pause
        H.BackgroundTrainer.resume = original_resume
    elapsed = time.perf_counter() - t0

    df = pd.read_csv(summary["log_csv_path"])
    val_rows = df[df["val_reward_per_sec"].notna()]
    best_path = os.path.join(ckpt_dir, "VerifySelect_best.pt")
    blob = torch.load(best_path, map_location="cpu", weights_only=False)

    n_val = len(val_rows)
    train_env_steps = episodes * (steps_per_ep + warmup)
    val_env_steps = n_val * (summary["validation_steps"] + warmup)

    return {
        "episodes": episodes,
        "steps_per_episode": steps_per_ep,
        "training_densities": ";".join(str(d) for d in sorted(df["density"].unique())),
        "n_validations": n_val,
        "validation_densities_seen": ";".join(
            str(d) for d in sorted(val_rows["val_density"].unique())),
        "validation_density_is_constant": bool(val_rows["val_density"].nunique() == 1),
        "validation_density_expected": H.resolve_validation_density(schedule),
        "validation_seed": summary["validation_seed"],
        "best_reward_stored": float(blob["best_reward"]),
        "best_reward_metric_stored": blob["best_reward_metric"],
        "best_validation_score": float(val_rows["val_reward_per_sec"].max()),
        "selection_matches_validation": bool(
            abs(float(blob["best_reward"])
                - float(val_rows["val_reward_per_sec"].max())) < 1e-6),
        "best_training_episode_score": float(df["reward_per_sec_selected"].max()),
        "old_rule_would_have_picked_density": float(
            df.loc[df["reward_per_sec_selected"].idxmax(), "density"]),
        "best_validation_episode": summary["best_validation_episode"],
        "transitions_pushed_while_training": leaks["while_training"],
        "transitions_pushed_while_paused": leaks["while_paused"],
        "validation_leak_free": bool(leaks["while_paused"] == 0),
        "train_env_steps_incl_warmup": train_env_steps,
        "validation_env_steps_incl_warmup": val_env_steps,
        "validation_overhead_fraction": round(val_env_steps / train_env_steps, 4),
        # The probe above is deliberately tiny (short episodes, long warm-up,
        # frequent validation), so its overhead is NOT the production figure.
        # This is what the same rule costs at run_all.py's setting: 100 episodes
        # of 2000 steps, warm-up DEFAULT_WARMUP_STEPS, validation every
        # DEFAULT_VALIDATE_EVERY_EPISODES episodes and one episode long.
        "production_overhead_fraction": round(
            (100 // H.DEFAULT_VALIDATE_EVERY_EPISODES) * (2000 + H.DEFAULT_WARMUP_STEPS)
            / (100 * (2000 + H.DEFAULT_WARMUP_STEPS)), 4),
        "wall_clock_seconds": round(elapsed, 1),
        "progress_csv": summary["log_csv_path"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--density", type=float, default=max(DENSITY_GRID))
    ap.add_argument("--saturation-steps", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=H.DEFAULT_WARMUP_STEPS)
    ap.add_argument("--episodes", type=int, default=7)
    ap.add_argument("--steps-per-episode", type=int, default=150)
    ap.add_argument("--selection-warmup", type=int, default=350)
    ap.add_argument("--validate-every", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tmp-root", type=str, default="/tmp/verify_selection")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(args.tmp_root, exist_ok=True)

    print(f"N_ACTIVE_MAX_OBS = {rli.N_ACTIVE_MAX_OBS} "
          f"(= max{tuple(DENSITY_GRID)} x coverage lane-km)")

    sat = check_contention_saturation(args.density, args.saturation_steps,
                                      args.warmup, args.seed)
    sat_path = os.path.join(OUT_DIR, "contention_feature_saturation.csv")
    sat.to_csv(sat_path, index=False)
    print(sat.to_string(index=False))
    print(f"-> {sat_path}")

    sel = check_selection(args.tmp_root, args.episodes, args.steps_per_episode,
                          args.selection_warmup, args.validate_every, args.seed)
    sel_path = os.path.join(OUT_DIR, "checkpoint_selection_verification.csv")
    pd.DataFrame([sel]).to_csv(sel_path, index=False)
    for k, v in sel.items():
        print(f"  {k}: {v}")
    print(f"-> {sel_path}")

    ok = (
        float(sat.loc[sat["normaliser"].str.startswith("new"), "saturated_fraction"].iloc[0]) == 0.0
        and sel["validation_density_is_constant"]
        and sel["selection_matches_validation"]
        and sel["validation_leak_free"]
    )
    print("VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
