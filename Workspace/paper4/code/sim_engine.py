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
import numpy as np
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


def compute_local_n_est(vehicle_positions: Dict[str, Tuple[float, float]],
                        comm_range_m: float = COMM_RANGE_M) -> Dict[str, int]:
    """
    Compute local neighbor count (n_est) for each vehicle within comm_range_m.

    For vehicle vid at (x, y):
      n_est = sum(1 for ovid, (ox, oy) in vehicle_positions.items()
                  if ovid != vid and dist((x, y), (ox, oy)) <= comm_range_m)
    """
    if not vehicle_positions:
        return {}
    vids = list(vehicle_positions.keys())
    n = len(vids)
    if n < 2:
        return {vids[0]: 0} if n == 1 else {}
    coords = np.array([vehicle_positions[vid] for vid in vids], dtype=np.float32)
    diff = coords[:, None, :] - coords[None, :, :]
    dist_sq = np.sum(diff**2, axis=-1)
    counts = np.sum(dist_sq <= (comm_range_m ** 2), axis=1) - 1
    return {vids[i]: int(counts[i]) for i in range(n)}


def compute_local_cbr(vehicle_positions: Dict[str, Tuple[float, float]],
                      tx_counts_or_events,
                      window_duration_s: float = 0.1,
                      comm_range_m: float = COMM_RANGE_M,
                      tx_duration_s: float = TX_DURATION_S,
                      **kwargs) -> Tuple[Dict[str, float], float]:
    """
    Compute local Channel Busy Ratio (CBR) for each vehicle within comm_range_m.

    For each vehicle vid at (x, y), CBR is calculated based on all CAM packets
    transmitted by vehicles in its sensing/communication neighborhood:
      S(vid) = { ovid in vehicle_positions | dist((x, y), (ox, oy)) <= comm_range_m }
      (Note: S(vid) includes vid itself, i.e., N(vid) U {vid})

    Formula:
      CBR(vid) = min(1.0, (N_tx(vid) * tx_duration_s) / window_duration_s)
      where N_tx(vid) = sum(tx_count(ovid) for ovid in S(vid))
    """
    if "window_duration" in kwargs:
        window_duration_s = kwargs["window_duration"]
    elif "step_duration_s" in kwargs:
        window_duration_s = kwargs["step_duration_s"]
    if "sense_range_m" in kwargs and "comm_range_m" not in kwargs:
        comm_range_m = kwargs["sense_range_m"]

    if not vehicle_positions:
        return {}, 0.0

    if window_duration_s <= 0.0:
        return {vid: 0.0 for vid in vehicle_positions}, 0.0

    vids = list(vehicle_positions.keys())
    n = len(vids)
    if n == 0:
        return {}, 0.0

    coords = np.array([vehicle_positions[vid] for vid in vids], dtype=np.float32)

    if isinstance(tx_counts_or_events, dict):
        tx_arr = np.array([tx_counts_or_events.get(vid, 0) for vid in vids], dtype=np.float32)
        diff = coords[:, None, :] - coords[None, :, :]
        dist_sq = np.sum(diff**2, axis=-1)
        in_range = (dist_sq <= comm_range_m**2)
        n_cams = in_range @ tx_arr
        cbr_vals = np.clip((n_cams * tx_duration_s) / window_duration_s, 0.0, 1.0)
        cbr_dict = {vids[i]: float(cbr_vals[i]) for i in range(n)}

    elif isinstance(tx_counts_or_events, (list, tuple, set)):
        cams_info = []
        for ev in tx_counts_or_events:
            if isinstance(ev, dict):
                if "x" in ev and "y" in ev:
                    cams_info.append((ev["x"], ev["y"]))
                elif "vid" in ev and ev["vid"] in vehicle_positions:
                    cams_info.append(vehicle_positions[ev["vid"]])
            elif isinstance(ev, (tuple, list)) and len(ev) >= 2:
                cams_info.append((ev[0], ev[1]))
            elif isinstance(ev, str) and ev in vehicle_positions:
                cams_info.append(vehicle_positions[ev])

        if not cams_info:
            return {vid: 0.0 for vid in vids}, 0.0

        cams_arr = np.array(cams_info, dtype=np.float32)
        diff = coords[:, None, :] - cams_arr[None, :, :]
        dist_sq = np.sum(diff**2, axis=-1)
        in_range_counts = np.sum(dist_sq <= comm_range_m**2, axis=1)
        cbr_vals = np.clip((in_range_counts * tx_duration_s) / window_duration_s, 0.0, 1.0)
        cbr_dict = {vids[i]: float(cbr_vals[i]) for i in range(n)}
    else:
        cbr_dict = {vid: 0.0 for vid in vids}

    cbr_mean = float(np.mean(list(cbr_dict.values()))) if cbr_dict else 0.0
    return cbr_dict, cbr_mean


def reception_probability_vec(dists: np.ndarray, p_tx_dbm: float = 20.0) -> np.ndarray:
    """Vectorized Nakagami-m reception probability computation."""
    d0 = 1.0
    PL_0_dB = 20.0 * math.log10(4.0 * math.pi * d0 * 5.9e9 / 3e8)
    PL_d = PL_0_dB + 10.0 * PATH_LOSS_EXP * np.log10(np.maximum(dists, 1.0) / d0)
    p_rx_dbm = p_tx_dbm - PL_d
    noise_dbm = -174.0 + 10.0 * math.log10(CHANNEL_BW_HZ) + 10.0
    snr_db = p_rx_dbm - noise_dbm
    snr_linear = 10.0 ** (snr_db / 10.0)
    snr_thresh_lin = 10.0 ** (5.0 / 10.0)
    ratio = np.maximum(snr_linear / snr_thresh_lin, 1e-12)
    x = NAKAGAMI_M_PARAM / ratio
    p = np.where(ratio > 50.0, 1.0, np.exp(-x) * (1.0 + x + 0.5 * (x ** 2)))
    return np.clip(p, 0.0, 1.0)


def simulate_receptions(cam_events: list,
                        vehicle_positions: Dict[str, Tuple[float, float]],
                        cbr_dict: Dict[str, float],
                        rng: random.Random,
                        dist_tx_counts: list,
                        dist_rx_counts: list,
                        is_warmup: bool = False) -> List[Dict]:
    """
    Simulate CAM reception by nearby vehicles with vectorized distance/fading checks.
    Returns list of reception events: {sender, receiver, t_rx, t_gen, dist_m}
    """
    reception_events = []
    if not cam_events or not vehicle_positions:
        return reception_events

    vehicle_ids = list(vehicle_positions.keys())
    n = len(vehicle_ids)
    if n == 0:
        return reception_events

    vid_to_idx = {vid: i for i, vid in enumerate(vehicle_ids)}
    coords = np.array([vehicle_positions[vid] for vid in vehicle_ids], dtype=np.float32)

    for ev in cam_events:
        sid = ev["vid"]
        sx, sy = vehicle_positions.get(sid, (ev.get("x", 0.0), ev.get("y", 0.0)))
        t_gen = ev["t_gen"]
        p_tx_dbm = ev["p_tx"]

        s_coord = np.array([sx, sy], dtype=np.float32)
        dists = np.linalg.norm(coords - s_coord, axis=1)
        
        in_range_mask = (dists <= COMM_RANGE_M)
        in_range_count = int(np.sum(in_range_mask))
        if sid in vehicle_positions:
            in_range_count = max(0, in_range_count - 1)
        ev["in_range_count"] = in_range_count

        cand_mask = (dists <= COMM_RANGE_M * 2)
        if sid in vid_to_idx:
            cand_mask[vid_to_idx[sid]] = False
        cand_indices = np.where(cand_mask)[0]
        if len(cand_indices) == 0:
            continue

        cand_dists = dists[cand_indices]
        p_rx_arr = reception_probability_vec(cand_dists, p_tx_dbm)
        rcv_cbrs = np.array([cbr_dict.get(vehicle_ids[i], 0.0) for i in cand_indices], dtype=np.float32)
        col_factors = np.maximum(0.1, 1.0 - rcv_cbrs * 0.8)
        p_success = p_rx_arr * col_factors

        rand_vals = np.array([rng.random() for _ in range(len(cand_indices))], dtype=np.float32)
        rx_success = (rand_vals < p_success)

        if not is_warmup:
            in_range_cand = (cand_dists <= COMM_RANGE_M)
            for d in cand_dists[in_range_cand]:
                bin_idx = min(int(d / 50.0), 5)
                dist_tx_counts[bin_idx] += 1
            for d in cand_dists[in_range_cand & rx_success]:
                bin_idx = min(int(d / 50.0), 5)
                dist_rx_counts[bin_idx] += 1

        for idx_c in np.where(rx_success)[0]:
            rid = vehicle_ids[cand_indices[idx_c]]
            dist_m = float(cand_dists[idx_c])
            prop_delay_s = dist_m / 3e8
            reception_events.append({
                "sender": sid,
                "receiver": rid,
                "t_rx": t_gen + prop_delay_s,
                "t_gen": t_gen,
                "dist_m": dist_m,
            })

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

def find_executable(name: str) -> Optional[str]:
    """Dynamically locate an executable without hardcoded absolute paths."""
    path = shutil.which(name)
    if path:
        return path

    search_dirs = []
    if "VIRTUAL_ENV" in os.environ:
        search_dirs.append(os.path.join(os.environ["VIRTUAL_ENV"], "bin"))
    if "SUMO_HOME" in os.environ:
        search_dirs.append(os.path.join(os.environ["SUMO_HOME"], "bin"))
        search_dirs.append(os.environ["SUMO_HOME"])

    search_dirs.append(os.path.dirname(sys.executable))
    search_dirs.append(os.path.join(sys.prefix, "bin"))
    search_dirs.append(os.path.join(os.path.expanduser("~"), "venv", "bin"))
    search_dirs.append(os.path.join(os.path.expanduser("~"), ".local", "bin"))
    search_dirs.append("/usr/local/bin")
    search_dirs.append("/usr/bin")

    for sdir in search_dirs:
        candidate = os.path.join(sdir, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        if os.path.isfile(candidate + ".exe") and os.access(candidate + ".exe", os.X_OK):
            return candidate + ".exe"
    return None


def get_sumo_env() -> dict:
    """Build environment dictionary with dynamic search paths for SUMO tools."""
    env = os.environ.copy()
    extra_paths = []
    if "VIRTUAL_ENV" in env:
        extra_paths.append(os.path.join(env["VIRTUAL_ENV"], "bin"))
    if "SUMO_HOME" in env:
        extra_paths.append(os.path.join(env["SUMO_HOME"], "bin"))
    extra_paths.append(os.path.dirname(sys.executable))
    extra_paths.append(os.path.join(sys.prefix, "bin"))
    extra_paths.append(os.path.join(os.path.expanduser("~"), "venv", "bin"))
    extra_paths.append(os.path.join(os.path.expanduser("~"), ".local", "bin"))

    existing_path = env.get("PATH", "")
    new_path_entries = [p for p in extra_paths if os.path.exists(p) and p not in existing_path]
    if new_path_entries:
        env["PATH"] = os.pathsep.join(new_path_entries) + os.pathsep + existing_path
    return env


def get_sumonetsim_paths() -> Tuple[Optional[str], Optional[str]]:
    """Dynamically locate make_sumo_set.py and rsu.poi.xml without hardcoded paths."""
    search_roots = []
    if "SUMONETSIM_DIR" in os.environ:
        search_roots.append(os.environ["SUMONETSIM_DIR"])

    code_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(code_dir)
    search_roots.append(os.path.join(project_root, "SumoNetSim"))
    search_roots.append(os.path.join(project_root, "SumoNetSim1.1.5"))

    user_home = os.path.expanduser("~")
    search_roots.append(os.path.join(user_home, "SumoNetSim1.1.5"))
    search_roots.append(os.path.join(user_home, "SumoNetSim1.1.6"))
    search_roots.append(os.path.join(user_home, "etc", "SumoNetSim1.1.6"))
    search_roots.append(os.path.join(user_home, "SumoNetSim"))

    source_script = None
    rsu_source = None
    for root in search_roots:
        cand_script = os.path.join(root, "src", "sumo", "make_sumo_set.py") if not root.endswith("make_sumo_set.py") else root
        if os.path.exists(cand_script):
            source_script = cand_script
            cand_rsu = os.path.join(os.path.dirname(cand_script), "rsu.poi.xml")
            if os.path.exists(cand_rsu):
                rsu_source = cand_rsu
            break

    return source_script, rsu_source


def generate_sumonetsim_files(work_dir: str, config: dict, seed: int):
    source_script, rsu_source = get_sumonetsim_paths()
    if not source_script or not os.path.exists(source_script):
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

    if rsu_source and os.path.exists(rsu_source):
        shutil.copy(rsu_source, os.path.join(work_dir, "rsu.poi.xml"))

    env = get_sumo_env()
    python_bin = sys.executable or shutil.which("python3") or "python3"

    try:
        subprocess.check_call([python_bin, "make_sumo_set.py"], cwd=work_dir, env=env)
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
        sumo_bin = find_executable("sumo") or "sumo"
        sumo_cmd = [sumo_bin,
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
                n_est_dict = compute_local_n_est(vehicle_positions, COMM_RANGE_M)
                for vdata in vehicles_data:
                    vid = vdata["vid"]
                    vdata["cbr"] = cbr_dict_prev.get(vid, 0.0)
                    vdata["n_est"] = n_est_dict.get(vid, 0)

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

        distance_aoi = aoi_tracker.get_distance_aoi()
                
        return {
            "AoI_mean": round(aoi_mean, 3),
            "M1_mean_AoI": round(aoi_mean, 3),
            "CBR_mean": round(cbr_mean, 4),
            "PDR_mean": round(pdr_mean, 2),
            "energy_efficiency": round(energy_eff, 4),
            "ETSI_compliance": round(etsi_comp, 2),
            "runtime_sec": round(runtime_sec, 2),
            "n_cam_events": len(cam_layer.cam_events),
            "cbr_history": cbr_history,
            "distance_pdr": distance_pdr,
            "distance_aoi": distance_aoi,
        }
