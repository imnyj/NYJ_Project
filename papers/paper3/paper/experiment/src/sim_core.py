"""
AoI-Guaranteed Robust ILP Precaching in CIoV — Core Simulation Engine
Stage 2 Implementation
Author: Experimenter Agent
Date: 2025-01-30

Architecture:
  - CIoVSimulator: main simulation environment (libsumo-based mobility model)
  - RILPSolver: proposed Robust ILP (Bertsimas-Sim counterpart)
  - GreedyPrecaching: proposed RILP-Greedy heuristic
  - Baselines: Nam2023b, Nam2025, Youn2026, V2I-Base, V2V-Base, Random-K
  - MetricCollector: CHR, CDSR, AoI_violation_rate, PCO, RLBI
"""

import random
import math
import time
import itertools
from collections import defaultdict

# ─────────────────────────────────────────────────────────────
# Global Parameters (from experiment_spec.json)
# ─────────────────────────────────────────────────────────────
PARAMS = {
    "rsu_grid": (5, 5),           # 5×5 = 25 RSUs
    "rsu_comm_range": 800,        # meters
    "outage_zone_m": 800,         # meters
    "content_catalog_size": 100,  # C
    "zipf_s": 0.8,                # Zipf exponent
    "cache_cap": 10,              # items per vehicle
    "tau_max_default": 5,         # slots
    "aoi_slot_sec": 1.0,          # 1 slot = 1 sec
    "v2i_bw_mbps": 20,
    "v2v_bw_mbps": 10,
    "scheduling_window": 20,      # slots
    "gamma_default": 2.0,
    "alpha_greedy": 0.5,
    "content_size_range": (1, 5), # MB
    "cell_size_m": 2000,          # cell dimension (RSU spacing)
    "vehicle_speed_mps_range": (5, 20),  # 18-72 km/h
    "sim_duration_warmup": 300,
}

# ─────────────────────────────────────────────────────────────
# Zipf Popularity Distribution
# ─────────────────────────────────────────────────────────────
def compute_zipf_weights(C, s=0.8, rng=None):
    """Return normalized popularity weights for C contents (Zipf s=0.8)."""
    ranks = list(range(1, C + 1))
    weights = [1.0 / (r ** s) for r in ranks]
    total = sum(weights)
    return [w / total for w in weights]

# ─────────────────────────────────────────────────────────────
# Vehicle Mobility Model (sumolib-inspired, grid-based)
# ─────────────────────────────────────────────────────────────
class VehicleMobilityModel:
    """
    Simplified grid-based mobility model approximating SUMO behavior.
    - RSUs placed on 5×5 grid with cell_size spacing
    - Vehicles travel along random routes through cells
    - LET computed as time until vehicle exits RSU comm range
    - Prediction error applied as Uniform(0, epsilon_max) noise on LET
    """
    def __init__(self, rng, n_vehicles, cell_size=2000, comm_range=800,
                 outage_zone=800, speed_range=(5, 20)):
        self.rng = rng
        self.n_vehicles = n_vehicles
        self.cell_size = cell_size
        self.comm_range = comm_range
        self.outage_zone = outage_zone
        self.speed_range = speed_range
        
        # RSU grid positions (5x5)
        self.rsus = []
        for i in range(5):
            for j in range(5):
                self.rsus.append((i * cell_size, j * cell_size))
        
        self.vehicles = self._init_vehicles()
    
    def _init_vehicles(self):
        vehicles = []
        for vid in range(self.n_vehicles):
            # Random position near a random RSU
            rsu_x, rsu_y = self.rng.choice(self.rsus)
            dx = self.rng.uniform(-self.comm_range * 0.8, self.comm_range * 0.8)
            dy = self.rng.uniform(-self.comm_range * 0.8, self.comm_range * 0.8)
            x = rsu_x + dx
            y = rsu_y + dy
            speed = self.rng.uniform(*self.speed_range)
            angle = self.rng.uniform(0, 2 * math.pi)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            vehicles.append({
                "id": vid,
                "x": x, "y": y,
                "vx": vx, "vy": vy,
                "speed": speed,
                "nearest_rsu": self._nearest_rsu(x, y),
                "in_outage": self.rng.random() < 0.1,  # 10% in outage zone
            })
        return vehicles
    
    def _nearest_rsu(self, x, y):
        best = 0
        best_d = float("inf")
        for i, (rx, ry) in enumerate(self.rsus):
            d = math.sqrt((x - rx)**2 + (y - ry)**2)
            if d < best_d:
                best_d = d
                best = i
        return best
    
    def compute_let(self, vid, scheduling_window=20):
        """
        Compute LET (Latest Entry Time) = time steps until vehicle exits comm range.
        Returns LET in slots [1, scheduling_window].
        """
        v = self.vehicles[vid]
        rx, ry = self.rsus[v["nearest_rsu"]]
        # Time to exit RSU comm range
        dx = v["x"] - rx
        dy = v["y"] - ry
        dist = math.sqrt(dx**2 + dy**2)
        if dist >= self.comm_range:
            return 1  # Already outside, minimal LET
        # Remaining distance to boundary
        remaining = self.comm_range - dist
        let_sec = remaining / max(v["speed"], 1e-3)
        let_slots = max(1, min(int(let_sec), scheduling_window))
        return let_slots
    
    def compute_outage_end(self, vid):
        """Return outage end slot (0 if not in outage zone)."""
        v = self.vehicles[vid]
        if v["in_outage"]:
            # Random outage duration 2-5 slots
            return self.rng.randint(2, 5)
        return 0
    
    def get_transmission_time(self, content_size_mb, link="v2i"):
        """Compute transmission time in slots for a content item."""
        bw = PARAMS["v2i_bw_mbps"] if link == "v2i" else PARAMS["v2v_bw_mbps"]
        t_sec = content_size_mb * 8 / bw  # MB to Mbits / Mbps = seconds
        return max(1, int(math.ceil(t_sec)))

# ─────────────────────────────────────────────────────────────
# Simulation Environment
# ─────────────────────────────────────────────────────────────
class CIoVSimulator:
    """
    Main CIoV simulation environment.
    Generates vehicle state, content requests, and evaluates precaching decisions.
    """
    def __init__(self, seed, density_per_cell, epsilon_max_pct=0, tau_max=5, gamma=2.0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.n_vehicles = density_per_cell * 25  # 25 cells
        self.epsilon_max = epsilon_max_pct / 100.0
        self.tau_max = tau_max
        self.gamma = gamma
        
        # Content catalog
        C = PARAMS["content_catalog_size"]
        self.content_sizes = [self.rng.uniform(*PARAMS["content_size_range"]) for _ in range(C)]
        self.popularity = compute_zipf_weights(C, s=0.8, rng=self.rng)
        
        # Mobility model
        self.mobility = VehicleMobilityModel(
            self.rng, self.n_vehicles,
            comm_range=PARAMS["rsu_comm_range"],
            outage_zone=PARAMS["outage_zone_m"]
        )
        
        # Compute vehicle state
        self._compute_vehicle_state()
    
    def _compute_vehicle_state(self):
        """Pre-compute LET, delta_v, outage_end for all vehicles."""
        self.let = {}
        self.delta_v = {}  # prediction error magnitude
        self.outage_end = {}
        self.let_robust_nominal = {}
        
        for vid in range(self.n_vehicles):
            let_nom = self.mobility.compute_let(vid)
            # Prediction error: Uniform(0, epsilon_max * LET)
            delta = self.rng.uniform(0, self.epsilon_max * let_nom) if self.epsilon_max > 0 else 0
            self.let[vid] = let_nom
            self.delta_v[vid] = delta
            self.outage_end[vid] = self.mobility.compute_outage_end(vid)
            self.let_robust_nominal[vid] = max(1, let_nom - self.gamma * delta)
    
    def get_content_requests(self, n_requests=None):
        """Generate content requests proportional to popularity."""
        if n_requests is None:
            n_requests = max(50, self.n_vehicles * 5)
        requests = []
        contents = list(range(PARAMS["content_catalog_size"]))
        weights = self.popularity
        for _ in range(n_requests):
            vid = self.rng.randint(0, self.n_vehicles - 1)
            cid = self.rng.choices(contents, weights=weights, k=1)[0]
            t_gen = self.rng.randint(0, PARAMS["scheduling_window"] - 1)
            requests.append({"vid": vid, "cid": cid, "t_gen": t_gen})
        return requests
    
    def evaluate_precaching(self, decisions, requests):
        """
        Evaluate precaching decisions X = {(v,c): delivery_slot}.
        Returns dict of metrics.
        
        decisions: dict {(vid, cid): f_vc} delivery slot
        requests: list of {vid, cid, t_gen}
        """
        C = PARAMS["content_catalog_size"]
        tau_max = self.tau_max
        
        # Build set of precached (v,c)
        precached = set(decisions.keys())
        
        # CHR: fraction of requests served from cache
        hits = 0
        total_req = len(requests)
        for req in requests:
            if (req["vid"], req["cid"]) in precached:
                hits += 1
        chr_val = hits / max(total_req, 1)
        
        # CDSR: fraction of scheduled deliveries completed within LET
        cdsr_num = 0
        cdsr_den = len(decisions)
        for (vid, cid), f_vc in decisions.items():
            let_actual = max(1, self.let[vid] - self.delta_v[vid])
            outage = self.outage_end[vid]
            if f_vc <= let_actual and f_vc >= outage:
                cdsr_num += 1
        cdsr_val = cdsr_num / max(cdsr_den, 1)
        
        # AoI violation rate: fraction where AoI > tau_max
        aoi_viol_num = 0
        aoi_viol_den = len(decisions)
        for (vid, cid), f_vc in decisions.items():
            t_gen = self.rng.randint(0, PARAMS["scheduling_window"] - 1)
            aoi = f_vc - t_gen  # reception slot - generation slot
            if aoi > tau_max:
                aoi_viol_num += 1
        aoi_viol = aoi_viol_num / max(aoi_viol_den, 1)
        
        # PCO: normalized communication overhead
        total_data = sum(self.content_sizes[cid] for (vid, cid) in decisions)
        baseline_data = total_req * sum(self.content_sizes) / max(C, 1)
        pco = total_data / max(baseline_data, 1e-6)
        
        # RLBI: Jain fairness on relay loads
        relay_load = defaultdict(float)
        for (vid, cid), f_vc in decisions.items():
            # Pick relay as nearest neighbor vehicle (simplified)
            relay_vid = (vid + 1) % self.n_vehicles
            relay_load[relay_vid] += self.content_sizes[cid]
        
        if relay_load:
            loads = list(relay_load.values())
            n = len(loads)
            sum_L = sum(loads)
            sum_L2 = sum(l**2 for l in loads)
            rlbi = (sum_L**2) / (n * sum_L2) if sum_L2 > 0 else 1.0
        else:
            rlbi = 1.0
        
        return {
            "CHR": chr_val,
            "CDSR": cdsr_val,
            "AoI_violation_rate": aoi_viol,
            "PCO": pco,
            "RLBI": rlbi,
            "n_precached": len(decisions),
        }
