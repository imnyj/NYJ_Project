#!/usr/bin/env python3
"""
oracle_generator.py
===================
Oracle (supervised label) generator for TinyMLP-AI-DCC.

Runs BL-A baseline simulation (libsumo + ETSICAMLayer) and performs
16-action grid search to produce (state → best_action) labels for BC training.

Output CSV: /home/imnyj/papers/paper4/paper/data/oracle_dataset.csv
Columns:
  vid, sim_time, cbr_global, n_neighbors, v_norm, dt_since_last_cam,
  cbr_smoothed, action_idx (0~15), T_GenCam_chosen, p_tx_chosen, cost, alpha

Usage:
  python3 oracle_generator.py [--duration_steps 6000] [--alpha 0.5]
      [--cbr_target 0.55] [--seed 42]
      [--output /home/imnyj/papers/paper4/paper/data/oracle_dataset.csv]

Author: Experimenter agent (E4-impl-1)
"""

import os
import sys
import math
import random
import csv
import time
import argparse
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ── libsumo ──────────────────────────────────────────────────────────────────
import libsumo

# ── local imports ─────────────────────────────────────────────────────────────
_sim_dir = os.path.dirname(os.path.abspath(__file__))
if _sim_dir not in sys.path:
    sys.path.insert(0, _sim_dir)

from etsi_cam_layer import ETSICAMLayer, T_GENCAM_MIN, T_GENCAM_MAX, dbm_to_linear

# ─────────────────────────────────────────────────────────────────────────────
# Constants (mirror sim_engine.py)
# ─────────────────────────────────────────────────────────────────────────────
SUMOCFG_PATH  = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg"
STEP_LENGTH   = 0.1          # 100 ms per simulation step
COMM_RANGE_M  = 300.0        # 802.11p nominal range (m)

# ── Action grid (4×4 = 16 actions) ───────────────────────────────────────────
T_GENCAM_GRID_S  = [0.1, 0.2, 0.5, 1.0]   # seconds
P_TX_GRID_DBM    = [-10, 0, 10, 20]         # dBm

# Build flat action list: action_idx = row*4 + col
# row = T_GenCam index, col = p_tx index
ACTIONS: List[Tuple[float, float]] = [
    (t, p)
    for t in T_GENCAM_GRID_S
    for p in P_TX_GRID_DBM
]  # 16 entries, index 0..15

# ── 802.11p TX params (for CBR_pred normalisation) ───────────────────────────
CAM_PACKET_BYTES = 280
DATA_RATE_BPS    = 3_000_000
TX_DURATION_S    = (CAM_PACKET_BYTES * 8) / DATA_RATE_BPS  # ~0.747 ms

# ── EMA smoothing ─────────────────────────────────────────────────────────────
EMA_LAMBDA = 0.5   # for cbr_smoothed_local (§5 spec)

# ── State normalisation constants ─────────────────────────────────────────────
V_NORM_SCALE   = 25.0   # m/s  (§5)
N_NORM_SCALE   = 50.0   # vehicles (§5)
DT_NORM_SCALE  = 1.0    # s (§5)

# ─────────────────────────────────────────────────────────────────────────────
# Per-vehicle local state (for state 5D extraction)
# ─────────────────────────────────────────────────────────────────────────────
class VehicleOracleState:
    """Tracks per-vehicle oracle features between steps."""

    def __init__(self, vid: str):
        self.vid             = vid
        self.last_cam_time   = 0.0    # sim_time of last outgoing CAM
        self.cbr_smoothed    = 0.0    # EMA of cbr_global at each step
        self.prev_T_GenCam   = T_GENCAM_MIN   # current BL-A T_GenCam (for CBR_pred)
        self.prev_p_tx       = 20.0           # current BL-A p_tx (dBm)

    def update_ema(self, cbr_global: float):
        """Update EMA-smoothed CBR (lambda=0.5)."""
        self.cbr_smoothed = (
            EMA_LAMBDA * cbr_global
            + (1.0 - EMA_LAMBDA) * self.cbr_smoothed
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cost function for grid-search labelling
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_action(
    t_action: float,
    p_action_dbm: float,
    cbr_global: float,
    t_current: float,
    p_current_dbm: float,
    cbr_target: float,
    alpha: float,
) -> float:
    """
    Single-step virtual evaluation of (t_action, p_action).

    AoI_pred = T_GenCam_action * 1000  [ms, approximate max AoI]

    CBR_pred  = cbr_global
                × (T_GenCam_current / T_GenCam_action)
                × (linear_power(p_action) / linear_power(p_current))
    (proportional: lower period → more transmissions → higher CBR;
     higher power → longer effective range → more collisions → higher CBR)

    cost = alpha * AoI_pred + (1 - alpha) * |CBR_pred - cbr_target|
    """
    # Avoid division by zero
    t_action   = max(t_action,   1e-6)
    t_current  = max(t_current,  1e-6)

    # AoI prediction (ms)
    aoi_pred = t_action * 1000.0

    # CBR prediction
    p_action_lin  = dbm_to_linear(p_action_dbm)
    p_current_lin = dbm_to_linear(p_current_dbm)

    if p_current_lin < 1e-12:
        p_current_lin = 1e-12  # guard against near-zero

    cbr_pred = (
        cbr_global
        * (t_current / t_action)
        * (p_action_lin / p_current_lin)
    )
    cbr_pred = max(0.0, min(cbr_pred, 1.0))

    cost = alpha * aoi_pred + (1.0 - alpha) * abs(cbr_pred - cbr_target)
    return cost


# ─────────────────────────────────────────────────────────────────────────────
# Main oracle generation loop
# ─────────────────────────────────────────────────────────────────────────────
def run_oracle(
    duration_steps: int = 6000,
    alpha: float = 0.5,
    cbr_target: float = 0.55,
    seed: int = 42,
    warmup_s: float = 30.0,
    snapshot_every_n_steps: int = 1,   # collect at every step (100ms)
    output_csv: str = "/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv",
) -> dict:
    """
    Run BL-A simulation and produce oracle dataset.

    Returns summary dict.
    """
    t_start = time.time()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # ── Init modules ──────────────────────────────────────────────────────────
    cam_layer = ETSICAMLayer(method="BL-A")
    rng       = random.Random(seed)

    # Per-vehicle oracle state
    oracle_states: Dict[str, VehicleOracleState] = {}

    # CBR history (for compute_cbr approximation)
    cbr_prev = 0.0

    # Action distribution counter
    action_dist = defaultdict(int)

    # Accumulated rows to write
    rows: List[dict] = []
    n_states_collected = 0

    # ── Open CSV ──────────────────────────────────────────────────────────────
    fieldnames = [
        "vid", "sim_time",
        "cbr_global", "n_neighbors", "v_norm",
        "dt_since_last_cam", "cbr_smoothed",
        "action_idx", "T_GenCam_chosen", "p_tx_chosen",
        "cost", "alpha",
    ]

    csv_file   = open(output_csv, "w", newline="")
    csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    csv_writer.writeheader()

    # ── Start libsumo ─────────────────────────────────────────────────────────
    libsumo.start([
        "sumo",
        "-c", SUMOCFG_PATH,
        "--step-length", str(STEP_LENGTH),
        "--seed", str(seed),
        "--no-warnings", "true",
        "--no-step-log", "true",
        "--time-to-teleport", "-1",
        "--collision.action", "warn",
    ])

    try:
        step = 0
        while (
            libsumo.simulation.getMinExpectedNumber() > 0
            and step < duration_steps
        ):
            libsumo.simulationStep()
            sim_time = step * STEP_LENGTH
            step    += 1

            # ── Fetch vehicle data ────────────────────────────────────────────
            vehicle_ids = libsumo.vehicle.getIDList()
            if not vehicle_ids:
                continue

            vehicles_data    = []
            vehicle_positions: Dict[str, Tuple[float, float]] = {}

            for vid in vehicle_ids:
                try:
                    x, y  = libsumo.vehicle.getPosition(vid)
                    speed = libsumo.vehicle.getSpeed(vid)
                    heading = libsumo.vehicle.getAngle(vid)
                    accel   = libsumo.vehicle.getAcceleration(vid)
                except Exception:
                    continue
                vehicle_positions[vid] = (x, y)
                vehicles_data.append({
                    "vid":     vid,
                    "x":       x,
                    "y":       y,
                    "speed":   speed,
                    "heading": heading,
                    "accel":   accel,
                    "n_est":   len(vehicle_ids) - 1,
                })

            if not vehicles_data:
                continue

            # ── CAM layer step (BL-A) ─────────────────────────────────────────
            cam_events = cam_layer.step(vehicles_data, sim_time, cbr_prev)

            # ── Compute CBR for this step ─────────────────────────────────────
            n_cams = len(cam_events)
            cbr_global = min(n_cams * TX_DURATION_S / STEP_LENGTH, 1.0)
            cbr_prev   = cbr_global

            # ── Update per-vehicle oracle states ──────────────────────────────
            # Note: cam_events already occurred; update last_cam_time + EMA
            cam_senders = {ev["vid"]: ev for ev in cam_events}

            for vdata in vehicles_data:
                vid = vdata["vid"]
                if vid not in oracle_states:
                    oracle_states[vid] = VehicleOracleState(vid)
                ovs = oracle_states[vid]

                # EMA update
                ovs.update_ema(cbr_global)

                # If this vehicle sent a CAM this step, update last_cam_time
                # and record current BL-A T_GenCam/p_tx
                if vid in cam_senders:
                    ovs.last_cam_time = sim_time
                    cam_ev = cam_senders[vid]
                    ovs.prev_T_GenCam = cam_ev["T_GenCam"]
                    ovs.prev_p_tx     = cam_ev["p_tx"]

            # ── State snapshot & label collection (after warmup) ──────────────
            if sim_time >= warmup_s and (step % snapshot_every_n_steps == 0):

                # Compute n_neighbors for each vehicle (within COMM_RANGE_M)
                n_neighbors_map: Dict[str, int] = {}
                vids_list = list(vehicle_positions.keys())
                for vid in vids_list:
                    px, py = vehicle_positions[vid]
                    cnt = 0
                    for ovid in vids_list:
                        if ovid == vid:
                            continue
                        ox, oy = vehicle_positions[ovid]
                        dist = math.sqrt((px - ox)**2 + (py - oy)**2)
                        if dist <= COMM_RANGE_M:
                            cnt += 1
                    n_neighbors_map[vid] = cnt

                for vdata in vehicles_data:
                    vid   = vdata["vid"]
                    speed = vdata["speed"]

                    ovs = oracle_states[vid]

                    # ── Build state 5D ────────────────────────────────────────
                    cbr_g         = cbr_global
                    n_neigh       = n_neighbors_map.get(vid, 0)
                    n_neigh_norm  = n_neigh / N_NORM_SCALE
                    v_norm        = speed / V_NORM_SCALE
                    dt_since      = (sim_time - ovs.last_cam_time) / DT_NORM_SCALE
                    cbr_smoothed  = ovs.cbr_smoothed

                    # ── Grid search over 16 actions ───────────────────────────
                    best_idx  = 0
                    best_cost = float("inf")

                    for a_idx, (t_act, p_act) in enumerate(ACTIONS):
                        c = evaluate_action(
                            t_action       = t_act,
                            p_action_dbm   = p_act,
                            cbr_global     = cbr_g,
                            t_current      = ovs.prev_T_GenCam,
                            p_current_dbm  = ovs.prev_p_tx,
                            cbr_target     = cbr_target,
                            alpha          = alpha,
                        )
                        if c < best_cost:
                            best_cost = c
                            best_idx  = a_idx

                    best_t, best_p = ACTIONS[best_idx]

                    row = {
                        "vid":              vid,
                        "sim_time":         round(sim_time, 2),
                        "cbr_global":       round(cbr_g, 6),
                        "n_neighbors":      round(n_neigh_norm, 6),
                        "v_norm":           round(v_norm, 6),
                        "dt_since_last_cam": round(dt_since, 6),
                        "cbr_smoothed":     round(cbr_smoothed, 6),
                        "action_idx":       best_idx,
                        "T_GenCam_chosen":  best_t,
                        "p_tx_chosen":      best_p,
                        "cost":             round(best_cost, 6),
                        "alpha":            alpha,
                    }
                    csv_writer.writerow(row)
                    action_dist[best_idx] += 1
                    n_states_collected   += 1

            # ── Progress log ─────────────────────────────────────────────────
            if step % 1000 == 0:
                print(f"[oracle] step={step} collected={n_states_collected}")

    finally:
        csv_file.close()
        try:
            libsumo.close()
        except Exception:
            pass

    elapsed = time.time() - t_start

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n[oracle] ===== DONE =====")
    print(f"  n_states_collected : {n_states_collected}")
    print(f"  elapsed_sec        : {elapsed:.1f}")
    print(f"  action_distribution:")
    for idx in range(len(ACTIONS)):
        t_a, p_a = ACTIONS[idx]
        cnt = action_dist.get(idx, 0)
        print(f"    action[{idx:2d}] T={t_a:.1f}s p={p_a:+.0f}dBm -> {cnt:>8d}")
    print(f"  output CSV: {output_csv}")

    return {
        "n_states_collected": n_states_collected,
        "action_distribution": dict(action_dist),
        "elapsed_sec": round(elapsed, 1),
        "output_csv": output_csv,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Oracle label generator for TinyMLP-AI-DCC (E4-impl-1)"
    )
    p.add_argument("--duration_steps", type=int,   default=6000,
                   help="Simulation steps (default: 6000 = 600s)")
    p.add_argument("--alpha",          type=float, default=0.5,
                   help="AoI/CBR trade-off weight (default: 0.5)")
    p.add_argument("--cbr_target",     type=float, default=0.55,
                   help="Target CBR (default: 0.55)")
    p.add_argument("--seed",           type=int,   default=42,
                   help="Random seed (default: 42)")
    p.add_argument("--warmup_s",       type=float, default=30.0,
                   help="Warm-up period in seconds before collecting (default: 30)")
    p.add_argument("--output", type=str,
                   default="/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv",
                   help="Output CSV path")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_oracle(
        duration_steps = args.duration_steps,
        alpha          = args.alpha,
        cbr_target     = args.cbr_target,
        seed           = args.seed,
        warmup_s       = args.warmup_s,
        output_csv     = args.output,
    )
