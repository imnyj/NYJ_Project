"""
sim_core.py — CIoVSim: libsumo-based CIoV simulator
Replaces CIoVSimFast (abstract random-walk model) with a full SUMO/libsumo simulation
using the SumoNetSim1.1.6 network topology (5x5 RSU grid, 800m comm range, 2400m spacing).

Design decisions:
- Uses libsumo (NOT traci) for zero-overhead in-process SUMO control.
- SUMO config: /home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/generated.sumocfg
- RSU positions parsed from rsu.poi.xml (25 RSUs, exact coordinates from SumoNetSim1.1.6).
- Simulation step = 1 second.
- cache_decision_fn(vehicles, params, rng) interface preserved for algorithms.py compatibility.
- Metrics: CHR, CDSR, AoI_violation_rate, PCO, RLBI (identical to CIoVSimFast).
"""

import os
import math
import random
import xml.etree.ElementTree as ET

try:
    import libsumo as sumo
except ImportError:
    print("[sim_core.py] FATAL: libsumo not found. "
          "Install SUMO and ensure libsumo is on PYTHONPATH. "
          "Typically: export PYTHONPATH=$SUMO_HOME/tools:$SUMO_HOME/bin")
    raise SystemExit(1)

try:
    import sumolib
except ImportError:
    print("[sim_core.py] FATAL: sumolib not found. "
          "Install SUMO tools: export PYTHONPATH=$SUMO_HOME/tools")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Constants — SumoNetSim1.1.6 topology
# ---------------------------------------------------------------------------
_DEFAULT_SUMO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../../../SumoNetSim1.1.6/src/sumo"
)
_FALLBACK_SUMO_DIR = "/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo"

# RSU grid specification (from SumoNetSim1.1.6/rsu.poi.xml)
# 5 columns × 5 rows, spacing 2400m (= 800 comm_range + 800 outage + 800 next)
# Actual positions (x, y) in metres:
_RSU_POSITIONS_STATIC = [
    # (node_id, x, y)
    ("N7",  1200.0,  1200.0),
    ("N8",  1200.0,  3600.0),
    ("N9",  1200.0,  6000.0),
    ("N10", 1200.0,  8400.0),
    ("N11", 1200.0, 10800.0),
    ("N14", 3600.0,  1200.0),
    ("N15", 3600.0,  3600.0),
    ("N16", 3600.0,  6000.0),
    ("N17", 3600.0,  8400.0),
    ("N18", 3600.0, 10800.0),
    ("N21", 6000.0,  1200.0),
    ("N22", 6000.0,  3600.0),
    ("N23", 6000.0,  6000.0),
    ("N24", 6000.0,  8400.0),
    ("N25", 6000.0, 10800.0),
    ("N28", 8400.0,  1200.0),
    ("N29", 8400.0,  3600.0),
    ("N30", 8400.0,  6000.0),
    ("N31", 8400.0,  8400.0),
    ("N32", 8400.0, 10800.0),
    ("N35", 10800.0,  1200.0),
    ("N36", 10800.0,  3600.0),
    ("N37", 10800.0,  6000.0),
    ("N38", 10800.0,  8400.0),
    ("N39", 10800.0, 10800.0),
]


def _resolve_sumo_dir(sumo_dir=None):
    """Resolve the path to the SUMO config directory."""
    candidates = []
    if sumo_dir:
        candidates.append(sumo_dir)
    candidates.append(_DEFAULT_SUMO_DIR)
    candidates.append(_FALLBACK_SUMO_DIR)
    env_home = os.environ.get("SUMO_HOME", "")
    if env_home:
        candidates.append(os.path.join(env_home, "tools"))

    for d in candidates:
        cfg = os.path.join(d, "generated.sumocfg")
        if os.path.isfile(cfg):
            return d
    # Return fallback and let SUMO error naturally
    return _FALLBACK_SUMO_DIR


def _load_rsu_positions_from_poi(poi_path):
    """
    Parse rsu.poi.xml to extract RSU (x, y) coordinates.
    Returns list of (rsu_id_str, x_float, y_float).
    Falls back to static _RSU_POSITIONS_STATIC if file unreadable.
    """
    try:
        tree = ET.parse(poi_path)
        root = tree.getroot()
        positions = []
        for poi in root.findall("poi"):
            if poi.get("type") == "RSU":
                positions.append((
                    poi.get("id"),
                    float(poi.get("x")),
                    float(poi.get("y"))
                ))
        if positions:
            return positions
    except Exception as e:
        print(f"[sim_core.py] Warning: could not parse {poi_path}: {e}. "
              "Using static RSU positions.")
    return list(_RSU_POSITIONS_STATIC)


# ---------------------------------------------------------------------------
# Main simulator class
# ---------------------------------------------------------------------------
class CIoVSim:
    """
    CIoV simulator based on libsumo + SumoNetSim1.1.6 topology.

    Parameters
    ----------
    seed : int
        RNG seed (also passed to SUMO via --seed).
    density_per_cell : int
        Initial number of vehicles per RSU cell (used only for legacy
        compatibility; actual vehicle count comes from .rou.xml).
    rsu_grid : tuple (rows, cols)
        Expected RSU grid size; used for validation only (actual RSU
        positions come from rsu.poi.xml).
    comm_range_m : float
        V2I communication range in metres (default 800 m).
    outage_zone_m : float
        Outage zone radius in metres (default 800 m).
    catalog_size : int
        Number of content items.
    cache_capacity : int
        Max content items per vehicle cache.
    tau_max : int
        AoI violation threshold (slots).
    gamma : float
        RILP robustness parameter.
    prediction_error_pct : float
        Position prediction noise percentage.
    duration_steps : int
        Total simulation steps (seconds).
    warmup_steps : int
        Warm-up steps before metric collection.
    v2i_bw_mbps : float
        V2I bandwidth in Mbps.
    v2v_bw_mbps : float
        V2V bandwidth in Mbps.
    scheduling_window : int
        Slots between cache decision calls.
    content_sizes_mb : list or None
        Per-content sizes (MB); randomly generated if None.
    zipf_s : float
        Zipf distribution shape parameter.
    sumo_dir : str or None
        Path to directory containing generated.sumocfg. If None,
        auto-resolved.
    sumo_gui : bool
        Use sumo-gui instead of sumo (requires DISPLAY; default False).
    """

    def __init__(self,
                 seed=42,
                 density_per_cell=5,
                 rsu_grid=(5, 5),
                 comm_range_m=800.0,
                 outage_zone_m=800.0,
                 catalog_size=100,
                 cache_capacity=10,
                 tau_max=5,
                 gamma=2.0,
                 prediction_error_pct=0,
                 duration_steps=1800,
                 warmup_steps=300,
                 v2i_bw_mbps=20.0,
                 v2v_bw_mbps=10.0,
                 scheduling_window=20,
                 content_sizes_mb=None,
                 zipf_s=0.8,
                 sumo_dir=None,
                 sumo_gui=False):

        self.seed = seed
        self.rng = random.Random(seed)
        self.density = density_per_cell
        self.rsu_rows, self.rsu_cols = rsu_grid
        self.comm_range = comm_range_m
        self.outage_zone = outage_zone_m
        self.catalog_size = catalog_size
        self.cache_capacity = cache_capacity
        self.tau_max = tau_max
        self.gamma = gamma
        self.pred_error = prediction_error_pct / 100.0
        self.duration = duration_steps
        self.warmup = warmup_steps
        self.v2i_bw = v2i_bw_mbps
        self.v2v_bw = v2v_bw_mbps
        self.sched_window = scheduling_window
        self.sumo_gui = sumo_gui

        # Resolve SUMO config directory
        self._sumo_dir = _resolve_sumo_dir(sumo_dir)
        self._sumocfg = os.path.join(self._sumo_dir, "generated.sumocfg")
        self._poi_xml  = os.path.join(self._sumo_dir, "rsu.poi.xml")

        # Load RSU positions (from file or static fallback)
        rsu_raw = _load_rsu_positions_from_poi(self._poi_xml)
        self.rsu_ids = [r[0] for r in rsu_raw]
        self.rsu_positions = [(r[1], r[2]) for r in rsu_raw]  # list of (x, y)
        self.n_rsu = len(self.rsu_positions)

        # Content catalog
        if content_sizes_mb is None:
            self.content_sizes = [self.rng.uniform(1, 5) for _ in range(catalog_size)]
        else:
            self.content_sizes = list(content_sizes_mb)

        # Zipf popularity
        self.popularity = self._zipf_popularity(catalog_size, zipf_s)

        # Vehicle state dict: {veh_id: {...}} — populated at simulation start
        self._veh_state = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _zipf_popularity(self, n, s):
        weights = [1.0 / (i ** s) for i in range(1, n + 1)]
        total = sum(weights)
        return [w / total for w in weights]

    def _nearest_rsu(self, x, y):
        """Return (rsu_index, distance_m) of the nearest RSU to (x, y)."""
        best_idx = 0
        best_dist = float("inf")
        for i, (rx, ry) in enumerate(self.rsu_positions):
            d = math.hypot(x - rx, y - ry)
            if d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx, best_dist

    def _rsus_in_range(self, x, y):
        """Return list of rsu indices within comm_range of (x, y)."""
        return [i for i, (rx, ry) in enumerate(self.rsu_positions)
                if math.hypot(x - rx, y - ry) <= self.comm_range]

    def _vehicles_near_rsu(self, rsu_idx, veh_states):
        """
        Return list of vehicle state dicts whose current position is
        within comm_range of rsu_idx.
        """
        rx, ry = self.rsu_positions[rsu_idx]
        return [v for v in veh_states.values()
                if math.hypot(v["x"] - rx, v["y"] - ry) <= self.comm_range]

    def _predict_position(self, v, horizon=5):
        """Predict vehicle position `horizon` seconds ahead with optional noise."""
        err_x = (self.rng.gauss(0, self.pred_error * self.comm_range)
                 if self.pred_error > 0 else 0.0)
        err_y = (self.rng.gauss(0, self.pred_error * self.comm_range)
                 if self.pred_error > 0 else 0.0)
        px = v["x"] + v["vx"] * horizon + err_x
        py = v["y"] + v["vy"] * horizon + err_y
        return px, py

    def _get_or_create_veh_state(self, vid, x, y, speed, angle):
        """
        Return existing vehicle state or create a new entry.
        Speed (m/s) → vx/vy via heading angle.
        SUMO angle: 0=North, clockwise → convert to math convention.
        """
        if vid not in self._veh_state:
            # Convert SUMO heading (deg, N=0 clockwise) to (vx, vy)
            rad = math.radians(90.0 - angle)
            vx = speed * math.cos(rad)
            vy = speed * math.sin(rad)
            self._veh_state[vid] = {
                "id": vid,
                "x": x, "y": y,
                "vx": vx, "vy": vy,
                "speed": speed,
                "cache": set(),
                "aoi": self.rng.randint(0, self.tau_max),
                "requests": 0, "hits": 0, "v2v_hits": 0,
                "aoi_violations": 0, "total_slots": 0,
            }
        else:
            # Update position and velocity
            rad = math.radians(90.0 - angle)
            self._veh_state[vid]["x"] = x
            self._veh_state[vid]["y"] = y
            self._veh_state[vid]["vx"] = speed * math.cos(rad)
            self._veh_state[vid]["vy"] = speed * math.sin(rad)
            self._veh_state[vid]["speed"] = speed
        return self._veh_state[vid]

    def _collect_vehicle_states_from_libsumo(self):
        """
        Poll libsumo for all vehicles currently in the simulation.
        Updates self._veh_state and returns the list of currently active IDs.
        """
        active_ids = sumo.vehicle.getIDList()
        for vid in active_ids:
            x, y    = sumo.vehicle.getPosition(vid)      # (x, y) in metres
            speed   = sumo.vehicle.getSpeed(vid)          # m/s
            angle   = sumo.vehicle.getAngle(vid)          # degrees, SUMO convention
            self._get_or_create_veh_state(vid, x, y, speed, angle)

        # Remove departed vehicles from state tracking
        departed = set(self._veh_state.keys()) - set(active_ids)
        for vid in departed:
            del self._veh_state[vid]

        return list(active_ids)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_params(self):
        """
        Return the params dict passed to cache_decision_fn.
        Compatible with algorithms.py interface.
        """
        return {
            "catalog_size":    self.catalog_size,
            "cache_capacity":  self.cache_capacity,
            "popularity":      self.popularity,
            "content_sizes":   self.content_sizes,
            "tau_max":         self.tau_max,
            "gamma":           self.gamma,
            "pred_error":      self.pred_error,
            "v2i_bw":          self.v2i_bw,
            "v2v_bw":          self.v2v_bw,
            "sched_window":    self.sched_window,
            "n_rsu":           self.n_rsu,
            "rsu_positions":   self.rsu_positions,
        }

    def run(self, cache_decision_fn):
        """
        Run the full simulation using libsumo.

        Parameters
        ----------
        cache_decision_fn : callable
            Signature: fn(vehicles_list, params, rng) -> dict{vehicle_id: set(content_ids)}
            `vehicles_list` is a list of vehicle state dicts (same schema as
            CIoVSimFast).

        Returns
        -------
        dict with keys: CHR, CDSR, AoI_violation_rate, PCO, RLBI,
                        total_requests, total_hits
        """
        # ── SUMO startup ──────────────────────────────────────────────
        binary = "sumo-gui" if self.sumo_gui else "sumo"
        sumo_cmd = [
            binary,
            "-c", self._sumocfg,
            "--seed", str(self.seed),
            "--step-length", "1",
            "--no-warnings", "true",
            "--no-step-log", "true",
            "--collision.action", "none",
            "--time-to-teleport", "-1",
        ]
        sumo.start(sumo_cmd)

        params = self.build_params()

        # ── Metric accumulators ───────────────────────────────────────
        total_requests      = 0
        total_hits          = 0
        total_v2v_hits      = 0
        total_aoi_violations = 0
        total_slots         = 0
        pco_count           = 0     # precaching overhead (new items fetched)
        rlbi_sum            = 0.0   # residual link budget indicator

        try:
            for t in range(self.duration):
                # ── Advance simulation by 1 second ────────────────────
                sumo.simulationStep()

                # ── Collect vehicle states from libsumo ───────────────
                active_ids = self._collect_vehicle_states_from_libsumo()

                if t < self.warmup:
                    continue   # Skip metric collection during warm-up

                active_vehs = [self._veh_state[vid] for vid in active_ids
                               if vid in self._veh_state]

                if not active_vehs:
                    continue

                # ── Build per-step RSU bucket (O(N) once per step) ────
                # Replaces the original O(N^2) per-vehicle scan.  For each
                # vehicle, find the nearest RSU index AND populate that
                # RSU's neighbor bucket in a single pass over vehicles.
                rsu_pos = self.rsu_positions
                comm_r2 = self.comm_range * self.comm_range
                rsu_buckets = [[] for _ in range(self.n_rsu)]
                for v in active_vehs:
                    vx_, vy_ = v["x"], v["y"]
                    best_idx = 0
                    best_d2  = float("inf")
                    for i, (rx, ry) in enumerate(rsu_pos):
                        dx = vx_ - rx; dy = vy_ - ry
                        d2 = dx*dx + dy*dy
                        if d2 < best_d2:
                            best_d2 = d2
                            best_idx = i
                        if d2 <= comm_r2:
                            rsu_buckets[i].append(v)
                    v["_nearest_rsu"] = best_idx

                # ── Cache decision every scheduling_window steps ───────
                if (t - self.warmup) % self.sched_window == 0:
                    cache_assignments = cache_decision_fn(
                        active_vehs, params, self.rng)
                    for v in active_vehs:
                        new_cache = cache_assignments.get(v["id"], set())
                        new_items = new_cache - v["cache"]
                        pco_count += len(new_items)
                        v["cache"] = new_cache

                # ── Per-vehicle request + AoI tracking ────────────────
                for v in active_vehs:
                    # Zipf content request
                    content_id = self.rng.choices(
                        range(self.catalog_size),
                        weights=self.popularity)[0]
                    total_requests += 1
                    v["total_slots"] += 1
                    total_slots += 1

                    # V2I cache hit
                    if content_id in v["cache"]:
                        total_hits += 1
                        v["hits"] += 1
                        v["aoi"] = 0
                    else:
                        # V2V: look for nearby vehicle with the content
                        # Use the per-step bucket (O(1) lookup, O(k) scan
                        # where k = vehicles in this RSU cell).
                        nearby = rsu_buckets[v["_nearest_rsu"]]
                        v2v_hit = any(
                            content_id in nv["cache"] and nv["id"] != v["id"]
                            for nv in nearby)
                        if v2v_hit:
                            total_v2v_hits += 1
                            total_hits     += 1
                            v["hits"]      += 1
                            v["v2v_hits"]  += 1
                            v["aoi"]        = max(0, v["aoi"] - 1)
                        else:
                            v["aoi"] += 1

                    # AoI violation check
                    if v["aoi"] > self.tau_max:
                        total_aoi_violations += 1
                        v["aoi_violations"]  += 1

                    # RLBI: fraction of cache capacity used
                    rlbi_sum += len(v["cache"]) / max(1, self.cache_capacity)

        finally:
            # ── Always close SUMO ─────────────────────────────────────
            sumo.close()

        # ── Compute metrics ───────────────────────────────────────────
        n          = max(1, total_requests)
        post_slots = max(1, total_slots)
        n_veh_est  = max(1, len(self._veh_state))
        n_decisions = max(1,
            (self.duration - self.warmup) // self.sched_window * n_veh_est)

        chr_val   = total_hits          / n
        cdsr_val  = total_v2v_hits      / n
        aoi_viol  = total_aoi_violations / post_slots
        pco_val   = pco_count           / n_decisions
        rlbi_val  = rlbi_sum            / post_slots

        return {
            "CHR":               chr_val,
            "CDSR":              cdsr_val,
            "AoI_violation_rate": aoi_viol,
            "PCO":               pco_val,
            "RLBI":              rlbi_val,
            "total_requests":    total_requests,
            "total_hits":        total_hits,
        }


# ---------------------------------------------------------------------------
# Quick self-test (does NOT run SUMO — only checks import and class init)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[sim_core.py] Import OK. CIoVSim class loaded.")
    print(f"  libsumo version : {sumo.version.VERSION}")
    print(f"  SUMO config dir : {_FALLBACK_SUMO_DIR}")
    print(f"  RSU count (static): {len(_RSU_POSITIONS_STATIC)}")
    print("To run simulation:")
    print("  from sim_core import CIoVSim")
    print("  from algorithms import rilp_greedy_decision")
    print("  sim = CIoVSim(seed=42, duration_steps=1800, warmup_steps=300)")
    print("  metrics = sim.run(rilp_greedy_decision)")
    print("  print(metrics)")
