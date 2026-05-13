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
Patched by: Experimenter agent (L1-B-3: SumoNetSim1.1.5 asset integration)
"""

import os
import math
import random
import csv
import time
import tempfile
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
# SumoNetSim1.1.5 asset paths  [L1-B-3 patch]
# ---------------------------------------------------------------------------
SUMOCFG_PATH = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg"
SUMO_NET_PATH = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.net.xml"


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
    # Simplified Nakagami CDF approximation
    ratio = snr_linear / snr_thresh_lin
    if ratio > 20:
        return 1.0
    # P_success ≈ 1 - exp(-m * ratio) for m=1; for m=3 use (1 - exp(-ratio))^m
    p = 1.0 - math.exp(-NAKAGAMI_M_PARAM * ratio / 3.0)
    return max(0.0, min(1.0, p))


def compute_cbr(vehicle_positions: Dict[str, Tuple[float, float]],
                cam_events_this_step: list,
                n_vehicles: int,
                step_duration_s: float = 0.1) -> float:
    """
    Estimate Channel Busy Ratio for this step.
    CBR = (total transmission time) / (step_duration * 1 channel)
    Approximation: each CAM uses TX_DURATION_S of channel time.
    With n_vehicles all transmitting, CBR = n_cams * TX_DURATION_S / step_duration
    """
    n_cams = len(cam_events_this_step)
    cbr = n_cams * TX_DURATION_S / step_duration_s
    return min(cbr, 1.0)


def simulate_receptions(cam_events: list,
                        vehicle_positions: Dict[str, Tuple[float, float]],
                        cbr: float,
                        rng: random.Random) -> List[Dict]:
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

        for rid in vehicle_ids:
            if rid == sid:
                continue
            rx, ry = vehicle_positions[rid]
            dist_m = math.sqrt((sx - rx)**2 + (sy - ry)**2)
            if dist_m > COMM_RANGE_M * 2:  # Skip far-away vehicles
                continue

            # Adjust reception probability for channel load (collisions)
            p_rx = reception_probability(dist_m, p_tx_dbm)
            # Channel collision reduction due to CBR
            collision_factor = max(0.0, 1.0 - cbr * 0.5)
            p_rx *= collision_factor

            if rng.random() < p_rx:
                # Propagation delay: negligible at these distances
                prop_delay_s = dist_m / 3e8  # ~1 us for 300m
                reception_events.append({
                    "sender": sid,
                    "receiver": rid,
                    "t_rx": t_gen + prop_delay_s,
                    "t_gen": t_gen,
                    "dist_m": dist_m,
                })

    return reception_events


# ---------------------------------------------------------------------------
# Network file generators (kept for API compatibility; NOT called in run())
# ---------------------------------------------------------------------------
def generate_urban_grid_net(output_path: str):
    """Generate a simple 3x3 grid network XML (no binary SUMO tools needed)."""
    # Use sumolib to generate via netgenerate command string
    # Since we have netgenerate in /home/imnyj/venv/bin, use it via os.system
    import os
    netgenerate = "/home/imnyj/venv/bin/netgenerate"
    cmd = (
        f"{netgenerate} --grid --grid.number=3 --grid.length=250 "
        f"--default.lanenumber=2 --default.speed=16.67 "
        f"--tls.guess=true --output-file={output_path} 2>/dev/null"
    )
    ret = os.system(cmd)
    return ret == 0


def generate_highway_net(output_path: str):
    """Generate a 5km 2-lane highway network."""
    import os
    netgenerate = "/home/imnyj/venv/bin/netgenerate"
    cmd = (
        f"{netgenerate} --grid --grid.number=1 --grid.y-number=1 "
        f"--grid.length=5000 --grid.y-length=3.75 "
        f"--default.lanenumber=2 --default.speed=36.11 "
        f"--output-file={output_path} 2>/dev/null"
    )
    ret = os.system(cmd)
    if ret != 0:
        # Fallback: generate a straight highway by hand
        return _generate_highway_net_manual(output_path)
    return True


def _generate_highway_net_manual(output_path: str) -> bool:
    """Fallback: generate minimal highway network XML manually."""
    net_xml = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">
    <location netOffset="0.00,0.00" convBoundary="0.00,0.00,5000.00,3.75" origBoundary="-180.0,-90.0,180.0,90.0" projParameter="!"/>
    <edge id="highway" from="entry" to="exit" priority="3" numLanes="2" speed="36.11">
        <lane id="highway_0" index="0" speed="36.11" length="5000.00" shape="0.00,-1.875 5000.00,-1.875"/>
        <lane id="highway_1" index="1" speed="36.11" length="5000.00" shape="0.00,1.875 5000.00,1.875"/>
    </edge>
    <edge id="highway_rev" from="exit" to="entry" priority="3" numLanes="2" speed="36.11">
        <lane id="highway_rev_0" index="0" speed="36.11" length="5000.00" shape="5000.00,1.875 0.00,1.875"/>
        <lane id="highway_rev_1" index="1" speed="36.11" length="5000.00" shape="5000.00,-1.875 0.00,-1.875"/>
    </edge>
    <junction id="entry" type="dead_end" x="0.00" y="0.00" incLanes="highway_rev_0 highway_rev_1" intLanes="" shape="-1.875,1.875 -1.875,-1.875"/>
    <junction id="exit" type="dead_end" x="5000.00" y="0.00" incLanes="highway_0 highway_1" intLanes="" shape="5001.875,-1.875 5001.875,1.875"/>
</net>
"""
    with open(output_path, 'w') as f:
        f.write(net_xml)
    return True


def generate_routes(net_path: str, route_path: str, n_vehicles: int,
                    duration_s: int, seed: int, scenario: str = "urban_grid"):
    """
    Generate a random routes file for the scenario.
    Uses sumolib to read the network, then creates random routes.
    """
    import sumolib
    import random as rnd
    rng = rnd.Random(seed)

    net = sumolib.net.readNet(net_path, withInternal=False)
    edges = [e for e in net.getEdges() if not e.getID().startswith(":")]
    # Filter to normal edges only
    normal_edges = [e for e in edges if len(e.getLanes()) > 0]

    routes_xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                        '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">']

    # Define vehicle type: Krauss model
    if scenario == "urban_grid":
        routes_xml_lines.append(
            '  <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" ' +
            'maxSpeed="16.67" minGap="2.5" speedFactor="1.0" speedDev="0.1"/>')
        speed_min, speed_max = 0.0, 16.67
    else:
        routes_xml_lines.append(
            '  <vType id="car" accel="2.6" decel="4.5" sigma="0.3" length="5.0" ' +
            'maxSpeed="36.11" minGap="5.0" speedFactor="1.0" speedDev="0.1"/>')
        speed_min, speed_max = 22.22, 36.11

    # Generate random routes (simple: pick random edge pairs)
    edge_ids = [e.getID() for e in normal_edges]
    if len(edge_ids) < 2:
        edge_ids = edge_ids * 3  # duplicate if too few

    for i in range(n_vehicles * 2):  # 2x stagger: compensate for trip completion/disappearance
        depart = rng.uniform(0, max(30, duration_s * 0.7))
        from_edge = rng.choice(edge_ids)
        to_edge = rng.choice(edge_ids)
        while to_edge == from_edge and len(edge_ids) > 1:
            to_edge = rng.choice(edge_ids)

        depart_speed = rng.uniform(speed_min * 0.5, speed_max * 0.8)

        routes_xml_lines.append(
            f'  <trip id="veh{i}" type="car" from="{from_edge}" to="{to_edge}" ' +
            f'depart="{depart:.1f}" departSpeed="{depart_speed:.2f}"/>')

    routes_xml_lines.append('</routes>')

    with open(route_path, 'w') as f:
        f.write('\n'.join(routes_xml_lines))


# ---------------------------------------------------------------------------
# SUMO config file generator (kept for API compatibility; NOT called in run())
# ---------------------------------------------------------------------------
def generate_sumocfg(net_path: str, route_path: str, cfg_path: str,
                     duration_steps: int, step_length: float = 0.1):
    """Generate a .sumocfg file for this run."""
    cfg_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{net_path}"/>
        <route-files value="{route_path}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{int(duration_steps * step_length)}"/>
        <step-length value="{step_length}"/>
    </time>
    <processing>
        <ignore-route-errors value="true"/>
        <collision.action value="warn"/>
    </processing>
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

    NOTE (L1-B-3 patch): self.scenario and self.n_vehicles are retained for
    signature compatibility. The simulation now uses the fixed SumoNetSim1.1.5
    asset (SUMOCFG_PATH). n_vehicles cap/filtering is handled in a later leaf.
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

        # [L1-B-3] Net/route/cfg generation calls removed.
        # Using fixed SumoNetSim1.1.5 asset via SUMOCFG_PATH.
        # self.scenario and self.n_vehicles are kept for signature compatibility only.

        # Initialise modules
        cam_layer = ETSICAMLayer(method=self.method, method_params=self.method_params)
        aoi_tracker = AoITracker(comm_range_m=COMM_RANGE_M,
                                  eval_start_time=self.warmup_s)
        rng = random.Random(self.seed * 31337)

        # Metrics accumulators
        cbr_history = []
        aoi_history = []

        # ---- libsumo simulation ---- [L1-B-3 patch: use SumoNetSim1.1.5 asset]
        libsumo.start(["sumo", "-c", SUMOCFG_PATH,
                       "--step-length", str(self.STEP_LENGTH),
                       "--seed", str(self.seed),
                       "--no-warnings", "true",
                       "--no-step-log", "true",
                       "--time-to-teleport", "-1",
                       "--collision.action", "warn"])

        try:
            step = 0
            while libsumo.simulation.getMinExpectedNumber() > 0 and step < self.duration_steps:
                libsumo.simulationStep()
                sim_time = step * self.STEP_LENGTH
                step += 1

                # Get active vehicles
                vehicle_ids = libsumo.vehicle.getIDList()
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
                        "n_est": len(vehicle_ids) - 1,
                    })

                if not vehicles_data:
                    continue

                # Compute CBR from previous step (bootstrapped)
                cbr_prev = cbr_history[-1] if cbr_history else 0.0

                # CAM layer step
                cam_events = cam_layer.step(vehicles_data, sim_time, cbr_prev)

                # Register CAM sends in AoI tracker
                for ev in cam_events:
                    aoi_tracker.on_cam_sent(ev["vid"], ev["t_gen"],
                                             ev["x"], ev["y"])

                # Compute CBR for this step
                cbr = compute_cbr(vehicle_positions, cam_events,
                                   len(vehicles_data), self.STEP_LENGTH)

                # Simulate receptions
                reception_evs = simulate_receptions(
                    cam_events, vehicle_positions, cbr, rng
                )
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
                    cbr_history.append(cbr)
                    if mean_aoi > 0:
                        aoi_history.append(mean_aoi)

        finally:
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

        return {
            "AoI_mean": round(aoi_mean, 3),
            "CBR_mean": round(cbr_mean, 4),
            "PDR_mean": round(pdr_mean, 2),
            "energy_efficiency": round(energy_eff, 4),
            "ETSI_compliance": round(etsi_comp, 2),
            "runtime_sec": round(runtime_sec, 2),
            "n_cam_events": len(cam_layer.cam_events),
        }
