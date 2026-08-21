#!/usr/bin/env python3
"""
sim_engine.py
=============
Core simulation engine using libsumo.

Manages:
  - SUMO network/route file generation (urban_grid, highway)
  - libsumo simulation lifecycle
  - 802.11p channel model (SumoNetSim-style: Nakagami-m + path loss)
  - CAM reception simulation (distance-based probabilistic model)
  - Metric collection and CSV export

Author: Experimenter agent (Stage 2: implement)
"""

import os
import math
import random
import csv
import time
import tempfile
import re
import subprocess
import shutil
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import libsumo

# Import our modules
import sys
_sim_dir = os.path.dirname(os.path.abspath(__file__))
if _sim_dir not in sys.path:
    sys.path.insert(0, _sim_dir)

from etsi_cam_layer import ETSICAMLayer, T_GENCAM_MIN, T_GENCAM_MAX
from aoi_tracker import AoITracker


# ---------------------------------------------------------------------------
# 802.11p channel model (SumoNetSim-style)
# ---------------------------------------------------------------------------
COMM_RANGE_M = 300.0      # nominal 802.11p range at +20 dBm
CHANNEL_BW_HZ = 10e6      # 10 MHz
DATA_RATE_BPS = 3_000_000  # 3 Mbps (BPSK 1/2)
PATH_LOSS_EXP = 2.0        # free-space-like urban
NAKAGAMI_M_PARAM = 3.0     # Nakagami-m fading parameter (urban ITS)
CAM_PACKET_BYTES = 280     # basic CAM ~280 bytes
TX_DURATION_S = (CAM_PACKET_BYTES * 8) / DATA_RATE_BPS  # ~0.747 ms


def reception_probability(dist_m: float, p_tx_dbm: float = 20.0) -> float:
    """
    Simplified distance-based reception probability:
      - Uses log-distance path loss + Nakagami-m fading
      - Returns P(reception) in [0, 1]
    """
    if dist_m < 1.0:
        return 1.0

    # Reference distance 1 m, reference path loss at 5.9 GHz
    # PL(d) = PL_0 + 10*alpha*log10(d/d0)
    # Use simplified: SNR decreases with distance
    # p_rx (dBm) = p_tx - path_loss
    # p_tx in mW: linear scale
    d0 = 1.0
    PL_0_dB = 20 * math.log10(4 * math.pi * d0 * 5.9e9 / 3e8)  # ~47 dB at 1m, 5.9 GHz
    PL_d = PL_0_dB + 10 * PATH_LOSS_EXP * math.log10(dist_m / d0)
    p_rx_dbm = p_tx_dbm - PL_d
    # Thermal noise: -174 dBm/Hz + 10*log10(BW) + NF(10dB)
    noise_dbm = -174 + 10 * math.log10(CHANNEL_BW_HZ) + 10
    snr_db = p_rx_dbm - noise_dbm
    snr_linear = 10 ** (snr_db / 10.0)

    # Nakagami-m CDF: P(SNR >= threshold) ~ simplified sigmoid
    snr_threshold_db = 5.0  # ~3 Mbps BPSK 1/2 requires ~3-5 dB SNR
    snr_thresh_lin = 10 ** (snr_threshold_db / 10.0)

    # Nakagami-m reception prob with m=3
    # P_success = 1 - regularized_gamma(m, m*snr_thresh/snr_avg)
    # Simplified: use exponential approximation
    if snr_linear <= 0:
        return 0.0
        
    ratio = snr_linear / snr_thresh_lin
    if ratio > 50:
        return 1.0
        
    # Exact Nakagami-m CCDF for m=3
    # P_success = P(SNR_instant >= threshold)
    x = NAKAGAMI_M_PARAM / ratio
    p = math.exp(-x) * (1.0 + x + 0.5 * (x ** 2))
    return max(0.0, min(1.0, p))


def compute_local_cbr(vehicle_positions: Dict[str, Tuple[float, float]],
                      cam_events_this_step: list,
                      step_duration_s: float = 0.1,
                      sense_range_m: float = 500.0) -> Tuple[Dict[str, float], float]:
    """
    Estimate local Channel Busy Ratio for each vehicle.
    For each vehicle, count CAMs generated within sense_range_m.
    """
    cbr_dict = {}
    cams_info = [(ev["x"], ev["y"]) for ev in cam_events_this_step]
    
    for vid, (x, y) in vehicle_positions.items():
        n_cams = 0
        for cx, cy in cams_info:
            if math.sqrt((x - cx)**2 + (y - cy)**2) <= sense_range_m:
                n_cams += 1
        cbr = n_cams * TX_DURATION_S / step_duration_s
        cbr_dict[vid] = min(cbr, 1.0)
        
    cbr_mean = sum(cbr_dict.values()) / len(cbr_dict) if cbr_dict else 0.0
    return cbr_dict, cbr_mean


def simulate_receptions(cam_events: list,
                        vehicle_positions: Dict[str, Tuple[float, float]],
                        cbr_dict: Dict[str, float],
                        rng: random.Random,
                        dist_tx_counts: list,
                        dist_rx_counts: list,
                        is_warmup: bool = False) -> List[Dict]:
    """
    Simulate CAM reception by nearby vehicles.
    Returns list of reception events: {sender, receiver, t_rx, t_gen, dist_m}
    """
    reception_events = []
    vehicle_ids = list(vehicle_positions.keys())

    for ev in cam_events:
        sid = ev["vid"]
        sx, sy = vehicle_positions.get(sid, (ev["x"], ev["y"]))
        t_gen = ev["t_gen"]
        p_tx_dbm = ev["p_tx"]
        in_range_count = 0

        for rid in vehicle_ids:
            if rid == sid:
                continue
            rx, ry = vehicle_positions[rid]
            dist_m = math.sqrt((sx - rx)**2 + (sy - ry)**2)
            
            if dist_m <= COMM_RANGE_M:
                in_range_count += 1
                
            if not is_warmup:
                bin_idx = min(int(dist_m / 50.0), 5)
                if dist_m <= COMM_RANGE_M:
                    dist_tx_counts[bin_idx] += 1

            if dist_m > COMM_RANGE_M * 2:  # Skip far-away vehicles
                continue

            # Adjust reception probability for channel load (collisions)
            p_rx = reception_probability(dist_m, p_tx_dbm)
            # MAC layer contention: modified to avoid excessive penalty and reflect density variations
            receiver_cbr = cbr_dict.get(rid, 0.0)
            collision_factor = max(0.1, 1.0 - receiver_cbr * 0.8)
            p_rx *= collision_factor

            if rng.random() < p_rx:
                if not is_warmup and dist_m <= COMM_RANGE_M:
                    dist_rx_counts[bin_idx] += 1
                # Propagation delay: negligible at these distances
                prop_delay_s = dist_m / 3e8  # ~1 us for 300m
                reception_events.append({
                    "sender": sid,
                    "receiver": rid,
                    "t_rx": t_gen + prop_delay_s,
                    "t_gen": t_gen,
                    "dist_m": dist_m,
                })
        
        ev["in_range_count"] = in_range_count

    return reception_events


# ---------------------------------------------------------------------------
# Network file generators
# ---------------------------------------------------------------------------
def load_config(config_path: str) -> dict:
    config = {}
    if not os.path.exists(config_path):
        return config
    with open(config_path, 'r') as f:
        for line in f:
            if line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    key, val = parts[1], parts[2]
                    if key in ['Variable', '---']:
                        continue
                    try:
                        config[key] = float(val) if '.' in val else int(val)
                    except ValueError:
                        pass
    return config

def generate_sumonetsim_files(work_dir: str, config: dict, seed: int):
    source_script = "/home/imnyj/SumoNetSim1.1.5/src/sumo/make_sumo_set.py"
    if not os.path.exists(source_script):
        return False
        
    with open(source_script, 'r') as f:
        code = f.read()
        
    for k, v in config.items():
        code = re.sub(rf"^{k}\s*=.*", f"{k} = {v}", code, flags=re.MULTILINE)
        
    # Inject seed to restore reproducibility
    code = f"import random\nrandom.seed({seed})\n" + code
        
    script_path = os.path.join(work_dir, "make_sumo_set.py")
    with open(script_path, 'w') as f:
        f.write(code)
        
    if "__main__" not in code:
        with open(script_path, 'a') as f:
            f.write("\n\nif __name__ == '__main__':\n    make_sumo_files()\n")
            
    rsu_source = "/home/imnyj/SumoNetSim1.1.5/src/sumo/rsu.poi.xml"
    if os.path.exists(rsu_source):
        shutil.copy(rsu_source, os.path.join(work_dir, "rsu.poi.xml"))
        
    env = os.environ.copy()
    env["PATH"] = "/home/imnyj/venv/bin:" + env.get("PATH", "")
    
    try:
        subprocess.check_call(["python3", "make_sumo_set.py"], cwd=work_dir, env=env)
        return True
    except subprocess.CalledProcessError:
        return False


# ---------------------------------------------------------------------------
# SUMO config file generator
# ---------------------------------------------------------------------------
def generate_sumocfg(net_path: str, route_path: str, cfg_path: str,
                     duration_steps: int, step_length: float = 0.1,
                     add_paths: Optional[List[str]] = None):
    """Generate a .sumocfg file for this run."""
    add_str = ""
    if add_paths:
        add_val = ",".join(os.path.basename(p) for p in add_paths)
        add_str = f'\n        <additional-files value="{add_val}"/>'

    cfg_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{os.path.basename(net_path)}"/>
        <route-files value="{os.path.basename(route_path)}"/>{add_str}
    </input>
    <time>
        <begin value="0"/>
        <end value="{int(duration_steps * step_length)}"/>
        <step-length value="{step_length}"/>
    </time>
</configuration>
"""
    with open(cfg_path, 'w') as f:
        f.write(cfg_xml)


# ---------------------------------------------------------------------------
# Main simulation runner
# ---------------------------------------------------------------------------
class SimulationRunner:
    """
    Runs one simulation episode using libsumo.

    Returns dict of metrics: AoI_mean, CBR_mean, PDR_mean, energy_efficiency,
                              ETSI_compliance, runtime_sec
    """

    STEP_LENGTH = 0.1  # 100 ms

    def __init__(self, scenario: str, n_vehicles: int, seed: int,
                 method: str = "BL-A", method_params: Optional[dict] = None,
                 duration_steps: int = 3000, warmup_s: float = 30.0,
                 work_dir: Optional[str] = None):
        self.scenario = scenario
        self.n_vehicles = n_vehicles
        self.seed = seed
        self.method = method
        self.method_params = method_params or {}
        self.duration_steps = duration_steps
        self.warmup_s = warmup_s
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="sumo_run_")

    def run(self) -> dict:
        """Execute the simulation and return metrics."""
        t_start = time.time()
        os.makedirs(self.work_dir, exist_ok=True)

        # Load config.md (prioritizing project root, then local code/config.md)
        config_path = os.path.join(_sim_dir, "..", "config.md")
        if not os.path.exists(config_path):
            config_path = os.path.join(_sim_dir, "config.md")
        config = load_config(config_path)

        # Override config DENSITY and AV_SPEED ONLY if explicitly passed as a sweep variable
        if self.method_params and 'n_vehicles_sweep' in self.method_params:
            config["DENSITY"] = self.method_params['n_vehicles_sweep']
        if self.method_params and 'speed' in self.method_params:
            config["AV_SPEED"] = self.method_params['speed']

        # Generate network and route files using make_sumo_set.py based on config
        ok = generate_sumonetsim_files(self.work_dir, config, self.seed)
        if not ok:
            raise RuntimeError("Failed to generate SUMO files using make_sumo_set.py")

        net_path = os.path.join(self.work_dir, "generated.net.xml")
        route_path = os.path.join(self.work_dir, "generated.rou.xml")
        add_path = os.path.join(self.work_dir, "generated.add.xml")
        cfg_path = os.path.join(self.work_dir, f"{self.scenario}_{self.n_vehicles}_{self.seed}.sumocfg")

        add_paths = []
        if os.path.exists(add_path):
            add_paths.append(add_path)
        rsu_path = os.path.join(self.work_dir, "rsu.poi.xml")
        if os.path.exists(rsu_path):
            add_paths.append(rsu_path)

        # Generate SUMO config
        generate_sumocfg(net_path, route_path, cfg_path,
                         self.duration_steps, self.STEP_LENGTH,
                         add_paths=add_paths)

        # Initialise modules
        cam_layer = ETSICAMLayer(method=self.method, method_params=self.method_params)
        aoi_tracker = AoITracker(comm_range_m=COMM_RANGE_M,
                                  eval_start_time=self.warmup_s)
        rng = random.Random(self.seed * 31337)

        # Metrics accumulators
        cbr_history = []
        aoi_history = []
        dist_tx_counts = [0]*6
        dist_rx_counts = [0]*6

        # ---- libsumo simulation ----
        sumo_cmd = ["/home/imnyj/venv/bin/sumo",
                       "--net-file", net_path,
                       "--route-files", route_path,
                       "--step-length", str(self.STEP_LENGTH),
                       "--begin", "0",
                       "--end", str(int(self.duration_steps * self.STEP_LENGTH)),
                       "--seed", str(self.seed),
                       "--ignore-route-errors", "true",
                       "--no-warnings", "true",
                       "--no-step-log", "true",
                       "--collision.action", "warn"]
        if add_paths:
            sumo_cmd.extend(["--additional-files", ",".join(add_paths)])
            
        libsumo.start(sumo_cmd)

        try:
            step = 0
            previous_vehicle_ids = set()
            while libsumo.simulation.getMinExpectedNumber() > 0 and step < self.duration_steps:
                libsumo.simulationStep()
                sim_time = step * self.STEP_LENGTH
                step += 1

                # Get active vehicles
                vehicle_ids = libsumo.vehicle.getIDList()
                
                vehicle_ids_set = set(vehicle_ids)
                departed_vids = previous_vehicle_ids - vehicle_ids_set
                for vid in departed_vids:
                    cam_layer.remove_vehicle(vid)
                    aoi_tracker.remove_vehicle(vid)
                previous_vehicle_ids = vehicle_ids_set

                if not vehicle_ids:
                    continue

                vehicles_data = []
                vehicle_positions = {}
                for vid in vehicle_ids:
                    try:
                        x, y = libsumo.vehicle.getPosition(vid)
                        speed = libsumo.vehicle.getSpeed(vid)
                        heading = libsumo.vehicle.getAngle(vid)
                        accel = libsumo.vehicle.getAcceleration(vid)
                    except Exception:
                        continue
                    vehicle_positions[vid] = (x, y)
                    vehicles_data.append({
                        "vid": vid, "x": x, "y": y,
                        "speed": speed, "heading": heading,
                        "accel": accel,
                    })

                if not vehicles_data:
                    continue

                cbr_dict_prev = getattr(self, "_last_cbr_dict", {})
                for vdata in vehicles_data:
                    vid = vdata["vid"]
                    x, y = vdata["x"], vdata["y"]
                    vdata["cbr"] = cbr_dict_prev.get(vid, 0.0)
                    
                    # Local n_est
                    n_est = 0
                    for ovid, (ox, oy) in vehicle_positions.items():
                        if ovid != vid:
                            if math.sqrt((x-ox)**2 + (y-oy)**2) <= COMM_RANGE_M:
                                n_est += 1
                    vdata["n_est"] = n_est

                # Compute CBR from previous step (bootstrapped)
                cbr_prev_mean = cbr_history[-1] if cbr_history else 0.0

                # CAM layer step
                cam_events = cam_layer.step(vehicles_data, sim_time, cbr_prev_mean)

                # Compute CBR for this step
                cbr_dict, cbr_mean = compute_local_cbr(vehicle_positions, cam_events, self.STEP_LENGTH)
                self._last_cbr_dict = cbr_dict

                is_warmup = (sim_time < self.warmup_s)
                aoi_tracker._in_warmup = is_warmup

                # Simulate receptions
                reception_evs = simulate_receptions(
                    cam_events, vehicle_positions, cbr_dict, rng,
                    dist_tx_counts, dist_rx_counts, is_warmup
                )

                # Register CAM sends in AoI tracker
                for ev in cam_events:
                    aoi_tracker.on_cam_sent(ev["vid"], ev["t_gen"],
                                             ev["x"], ev["y"], ev.get("in_range_count", 0))
                for rx_ev in reception_evs:
                    aoi_tracker.on_cam_received(
                        rx_ev["sender"], rx_ev["receiver"],
                        rx_ev["t_rx"], rx_ev["t_gen"],
                        rx_ev["dist_m"]
                    )

                # AoI step update
                mean_aoi = aoi_tracker.step(sim_time, vehicle_positions)

                # Record metrics (after warmup)
                if sim_time >= self.warmup_s:
                    cbr_history.append(cbr_mean)
                    if mean_aoi > 0:
                        aoi_history.append(mean_aoi)

        finally:
            for vid in list(cam_layer.vehicles.keys()):
                cam_layer.remove_vehicle(vid)
                aoi_tracker.remove_vehicle(vid)
            try:
                libsumo.close()
            except Exception:
                pass

        # Aggregate metrics
        aoi_mean = sum(aoi_history) / len(aoi_history) if aoi_history else 0.0
        cbr_mean = sum(cbr_history) / len(cbr_history) if cbr_history else 0.0
        pdr_mean = aoi_tracker.get_pdr()
        energy_eff = cam_layer.get_energy_efficiency()
        etsi_comp = cam_layer.get_etsi_compliance()

        runtime_sec = time.time() - t_start

        distance_pdr = []
        for b in range(6):
            if dist_tx_counts[b] > 0:
                distance_pdr.append(dist_rx_counts[b] / dist_tx_counts[b] * 100.0)
            else:
                distance_pdr.append(0.0)
                
        return {
            "AoI_mean": round(aoi_mean, 3),
            "CBR_mean": round(cbr_mean, 4),
            "PDR_mean": round(pdr_mean, 2),
            "energy_efficiency": round(energy_eff, 4),
            "ETSI_compliance": round(etsi_comp, 2),
            "runtime_sec": round(runtime_sec, 2),
            "n_cam_events": len(cam_layer.cam_events),
            "cbr_history": cbr_history,
            "distance_pdr": distance_pdr,
        }
