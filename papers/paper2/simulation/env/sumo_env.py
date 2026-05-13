"""
sumo_env.py
===========
libsumo-based SUMO environment for MAFAC simulation.
Provides a Gym-like interface for multi-agent RL.

IMPORTANT: Uses `import libsumo` (NOT traci).

Observation space per agent (vehicle):
  [x_norm, y_norm, speed_norm, heading_sin, heading_cos,
   avg_aoi_own, cache_fill_ratio, cbr, num_neighbors,
   aoi_neighbor_1..K (nearest K vehicles)]

Action space per agent (factored):
  [forwarding_action, caching_action, power_level, subchannel_idx]

CHANGES from original:
  - Added _get_all_edges() helper to retrieve valid network edges
  - Added _respawn_vehicle(vid) to re-insert arrived vehicles
  - Added _ensure_vehicle_population() to guarantee min vehicle count
  - Modified _update_vehicle_state() to call _respawn_vehicle on arrived vehicles
  - Modified _run_warmup() to call _ensure_vehicle_population() after warmup
  - Modified step() to handle empty vehicle list gracefully
  - Modified get_observations() and get_rewards() to handle empty vehicle list
"""

import os
import sys
import math
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# ── libsumo import ────────────────────────────────────────────────────────────
try:
    import libsumo
    LIBSUMO_AVAILABLE = True
except ImportError:
    LIBSUMO_AVAILABLE = False
    print("[sumo_env] WARNING: libsumo not available. Using mock mode.")

# ── Local imports ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

from env.ndn_layer    import NDNNetwork, NDNNode, InterestPacket, DataPacket, ZipfContentModel
from env.channel_model import ChannelModel
from env.aoi_tracker  import AoITracker


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
GRID_N        = 5
BLOCK_LEN     = 250.0
STEP_LENGTH   = 0.1
MAX_SPEED     = 13.89
WARMUP_STEPS  = 1000
NUM_SUBCH     = 50
MAX_TX_DBM    = 23.0
CBR_THRESH    = 0.65
SINR_THRESH   = 3.0
CONTENT_SIZE  = 1500  # bytes

# Edge naming helper for netgenerate-created 5x5 grid
_COL_TO_LETTER = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E'}

def _edge_id(r1, c1, r2, c2):
    """Convert grid coordinates to netgenerate edge ID (e.g., A0B0)."""
    return f"{_COL_TO_LETTER[c1]}{r1}{_COL_TO_LETTER[c2]}{r2}"

# RSU positions (corners of central 2x2 grid)
RSU_POSITIONS = [
    (1 * BLOCK_LEN, 1 * BLOCK_LEN),
    (1 * BLOCK_LEN, 2 * BLOCK_LEN),
    (2 * BLOCK_LEN, 1 * BLOCK_LEN),
    (2 * BLOCK_LEN, 2 * BLOCK_LEN),
]
RSU_IDS = ["RSU_0", "RSU_1", "RSU_2", "RSU_3"]

# Observation & action dimensions
OBS_DIMS_PER_VEHICLE = 9 + 5  # base + up-to-5 neighbors
ACTION_DIM_FORWARDING = 3   # 0=drop, 1=v2v, 2=v2i
ACTION_DIM_CACHING    = 2   # 0=no cache, 1=cache
ACTION_DIM_POWER      = 5   # power levels 0..4 -> dBm
ACTION_DIM_SUBCHANNEL = NUM_SUBCH

POWER_LEVELS_DBM = [5.0, 10.0, 15.0, 20.0, 23.0]

# FIB update period (in steps)
FIB_UPDATE_PERIOD = 100  # every 10 seconds

# Minimum vehicles to maintain in simulation
MIN_VEHICLES_RATIO = 0.5  # at least 50% of target


# ─────────────────────────────────────────────────────────────────────────────
# Mock SUMO state (used when libsumo unavailable)
# NOTE (워크스테이션 실행 환경):
#   이 Mock 분기는 libsumo가 설치되지 않은 환경(개발 PC, CI 등)을 위한 fallback이며,
#   워크스테이션에서는 libsumo를 직접 사용합니다 (LIBSUMO_AVAILABLE=True).
#   코드 자체는 테스트/개발 목적으로 유지합니다.
# ─────────────────────────────────────────────────────────────────────────────
class MockSUMO:
    """Lightweight mock of libsumo API for testing without SUMO."""

    def __init__(self, num_vehicles: int = 50, seed: int = 42):
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)
        self._step = 0
        self._vehicles: Dict[str, dict] = {}
        self._num_vehicles = num_vehicles
        total = (GRID_N - 1) * BLOCK_LEN

        for i in range(num_vehicles):
            vid = f"veh_{i}"
            self._vehicles[vid] = {
                "x":      self._rng.uniform(0, total),
                "y":      self._rng.uniform(0, total),
                "speed":  self._rng.uniform(0, MAX_SPEED),
                "angle":  self._rng.uniform(0, 360),
                "edge":   "A0B0",
                "lane":   0,
            }

    def simulation_step(self):
        self._step += 1
        total = (GRID_N - 1) * BLOCK_LEN
        for vid, state in self._vehicles.items():
            angle_rad = math.radians(state["angle"])
            spd = state["speed"]
            state["x"] = max(0, min(total, state["x"] + spd * STEP_LENGTH * math.cos(angle_rad)))
            state["y"] = max(0, min(total, state["y"] + spd * STEP_LENGTH * math.sin(angle_rad)))
            state["speed"] = max(0, min(MAX_SPEED, state["speed"] + self._rng.gauss(0, 0.5)))
            state["angle"] = (state["angle"] + self._rng.gauss(0, 5)) % 360

    def get_vehicle_ids(self) -> List[str]:
        return list(self._vehicles.keys())

    def get_vehicle_position(self, vid: str) -> Tuple[float, float]:
        v = self._vehicles.get(vid)
        if v:
            return v["x"], v["y"]
        return 0.0, 0.0

    def get_vehicle_speed(self, vid: str) -> float:
        v = self._vehicles.get(vid)
        return v["speed"] if v else 0.0

    def get_vehicle_angle(self, vid: str) -> float:
        v = self._vehicles.get(vid)
        return v["angle"] if v else 0.0

    def get_sim_time(self) -> float:
        return self._step * STEP_LENGTH

    def simulation_get_departed_id_list(self) -> List[str]:
        return []

    def simulation_get_arrived_id_list(self) -> List[str]:
        return []

    def add_vehicle(self, vid: str, x: float, y: float):
        """Add a new vehicle to mock simulation (for respawn support)."""
        self._vehicles[vid] = {
            "x":      x,
            "y":      y,
            "speed":  self._rng.uniform(0, MAX_SPEED),
            "angle":  self._rng.uniform(0, 360),
            "edge":   "A0B0",
            "lane":   0,
        }

    def remove_vehicle(self, vid: str):
        """Remove a vehicle from mock simulation."""
        self._vehicles.pop(vid, None)


# ─────────────────────────────────────────────────────────────────────────────
# SUMO Environment
# ─────────────────────────────────────────────────────────────────────────────
class SUMOEnv:
    """
    libsumo-based SUMO environment.
    Provides reset(), step(actions), get_observations(), get_rewards().
    """

    def __init__(
        self,
        sumo_cfg: str = None,
        num_vehicles: int = 50,
        cache_size: int = 50,
        num_contents: int = 200,
        zipf_alpha: float = 1.0,
        content_update_rate: float = 0.5,
        rician_K_db: float = 7.0,
        nakagami_m: float = 3.0,
        episode_duration_s: float = 300.0,
        warmup_steps: int = WARMUP_STEPS,
        seed: int = 42,
        use_gui: bool = False,
        headless: bool = True,
    ):
        self.sumo_cfg            = sumo_cfg
        self.num_vehicles_target = num_vehicles
        self.cache_size          = cache_size
        self.num_contents        = num_contents
        self.zipf_alpha          = zipf_alpha
        self.content_update_rate = content_update_rate
        self.rician_K_db         = rician_K_db
        self.nakagami_m          = nakagami_m
        self.episode_duration_s  = episode_duration_s
        self.warmup_steps        = warmup_steps
        self.seed                = seed
        self.use_gui             = use_gui and not headless
        self.headless            = headless

        self._rng = random.Random(seed)
        np.random.seed(seed)

        # SUMO state
        self._sumo        = None
        self._use_mock    = not LIBSUMO_AVAILABLE
        self._step_count  = 0
        self._sim_time    = 0.0
        self._running     = False

        # Vehicle state
        self._vehicle_ids: List[str]          = []
        self._vehicle_pos: Dict[str, Tuple]   = {}
        self._vehicle_speed: Dict[str, float] = {}
        self._vehicle_angle: Dict[str, float] = {}

        # Cache of valid network edges (populated on first call)
        self._cached_edges: Optional[List[str]] = None

        # Counter for unique route/vehicle IDs during respawn
        self._respawn_counter: int = 0

        # NDN layer
        self.ndn = NDNNetwork(
            cache_size=cache_size,
            num_contents=num_contents,
            zipf_alpha=zipf_alpha,
            content_update_rate=content_update_rate,
            seed=seed,
        )

        # Channel model
        self.channel = ChannelModel(
            K_db=rician_K_db,
            nakagami_m=nakagami_m,
            seed=seed,
        )

        # AoI tracker
        self.aoi_tracker = AoITracker(num_contents=num_contents)

        # Content model for generating requests
        self.zipf_model = ZipfContentModel(num_contents, zipf_alpha, seed)

        # Episode tracking
        self.episode_reward: Dict[str, float]  = {}
        self.episode_metrics: dict             = {}
        self._total_tx     = 0
        self._total_tx_ok  = 0
        self._total_bits   = 0.0

        # Add RSUs to NDN
        for rsu_id, (rx, ry) in zip(RSU_IDS, RSU_POSITIONS):
            self.ndn.add_node(rsu_id, is_rsu=True, x=rx, y=ry)

    # ── SUMO Lifecycle ────────────────────────────────────────────────────────
    def _start_sumo(self):
        """Start libsumo simulation."""
        if self._use_mock:
            self._sumo = MockSUMO(self.num_vehicles_target, self.seed)
            return

        if self.sumo_cfg is None:
            cfg_candidates = [
                Path(__file__).parent.parent / "config" / "sumo_config.sumocfg",
                Path("config") / "sumo_config.sumocfg",
            ]
            for c in cfg_candidates:
                if c.exists():
                    self.sumo_cfg = str(c)
                    break

        if self.sumo_cfg is None or not Path(self.sumo_cfg).exists():
            print("[sumo_env] Config not found, falling back to mock mode")
            self._use_mock = True
            self._sumo = MockSUMO(self.num_vehicles_target, self.seed)
            return

        try:
            cmd = [
                "--configuration-file", self.sumo_cfg,
                "--no-step-log", "true",
                "--seed", str(self.seed),
                "--step-length", str(STEP_LENGTH),
                "--collision.action", "warn",
                "--time-to-teleport", "300",
            ]
            if self.headless or not self.use_gui:
                libsumo.start(["sumo"] + cmd)
            else:
                libsumo.start(["sumo-gui"] + cmd)
            self._running = True
            # Invalidate edge cache on new simulation start
            self._cached_edges = None
        except Exception as e:
            print(f"[sumo_env] libsumo.start failed: {e}. Using mock mode.")
            self._use_mock = True
            self._sumo = MockSUMO(self.num_vehicles_target, self.seed)

    def _stop_sumo(self):
        """Stop libsumo simulation."""
        if not self._use_mock and self._running:
            try:
                libsumo.close()
            except Exception:
                pass
        self._running = False

    # ── Gym Interface ─────────────────────────────────────────────────────────
    def reset(self) -> Dict[str, np.ndarray]:
        """Reset environment and return initial observations."""
        if self._running:
            self._stop_sumo()

        # Reset state
        self._step_count  = 0
        self._sim_time    = 0.0
        self._vehicle_ids = []
        self._vehicle_pos = {}
        self._vehicle_speed = {}
        self._vehicle_angle = {}
        self._total_tx = 0
        self._total_tx_ok = 0
        self._total_bits = 0.0
        self.episode_reward = {}
        self._cached_edges = None
        self._respawn_counter = 0

        # Reset NDN (keep RSUs, clear vehicles)
        veh_ids = [nid for nid in list(self.ndn.nodes.keys())
                   if not nid.startswith("RSU")]
        for vid in veh_ids:
            self.ndn.remove_node(vid)

        # Reset AoI tracker
        self.aoi_tracker.reset()

        # Start SUMO
        self._start_sumo()

        # Warmup
        self._run_warmup()

        # Get initial observations
        self._update_vehicle_state()
        obs = self.get_observations()

        return obs

    def _run_warmup(self):
        """Run warmup steps to populate the simulation."""
        for _ in range(self.warmup_steps):
            if self._use_mock:
                self._sumo.simulation_step()
            else:
                libsumo.simulationStep()
            self._step_count += 1
            self._sim_time    = self._step_count * STEP_LENGTH

        # After warmup, verify and ensure sufficient vehicle population
        self._update_vehicle_state()
        self._ensure_vehicle_population()

    def _get_all_edges(self) -> List[str]:
        """
        Return all valid (non-internal) edge IDs from the simulation network.

        Internal edges start with ':' and cannot be used as route endpoints.
        Results are cached after first call for performance.
        """
        if self._cached_edges is not None:
            return self._cached_edges

        if self._use_mock:
            # Mock mode: generate the 5x5 grid edge list manually
            edges = []
            for r in range(GRID_N):
                for c in range(GRID_N):
                    if c + 1 < GRID_N:
                        edges.append(_edge_id(r, c, r, c+1))
                        edges.append(_edge_id(r, c+1, r, c))
                    if r + 1 < GRID_N:
                        edges.append(_edge_id(r, c, r+1, c))
                        edges.append(_edge_id(r+1, c, r, c))
            self._cached_edges = edges
        else:
            # libsumo: get edge list excluding internal junction edges
            try:
                all_edges = libsumo.edge.getIDList()
                self._cached_edges = [e for e in all_edges if not e.startswith(':')]
            except Exception as e:
                print(f"[sumo_env] _get_all_edges error: {e}. Using fallback edge list.")
                edges = []
                for r in range(GRID_N):
                    for c in range(GRID_N):
                        if c + 1 < GRID_N:
                            edges.append(_edge_id(r, c, r, c+1))
                            edges.append(_edge_id(r, c+1, r, c))
                        if r + 1 < GRID_N:
                            edges.append(_edge_id(r, c, r+1, c))
                            edges.append(_edge_id(r+1, c, r, c))
                self._cached_edges = edges

        return self._cached_edges

    def _respawn_vehicle(self, vid: str) -> bool:
        """
        Re-insert an arrived vehicle back into the simulation at a new random location.

        For libsumo: creates a new route and adds the vehicle.
        For MockSUMO: adds vehicle at random position.

        Returns True if successful, False otherwise.
        """
        if self._use_mock:
            # MockSUMO: vehicle stays alive, but if called explicitly add it back
            total = (GRID_N - 1) * BLOCK_LEN
            x = self._rng.uniform(0, total)
            y = self._rng.uniform(0, total)
            self._sumo.add_vehicle(vid, x, y)
            return True

        all_edges = self._get_all_edges()
        if len(all_edges) < 2:
            return False

        src_edge = self._rng.choice(all_edges)
        # Pick destination different from source
        dst_candidates = [e for e in all_edges if e != src_edge]
        if not dst_candidates:
            return False
        dst_edge = self._rng.choice(dst_candidates)

        self._respawn_counter += 1
        route_id = f"respawn_route_{vid}_{self._respawn_counter}"

        try:
            # Register a new route with source and destination
            libsumo.route.add(route_id, [src_edge, dst_edge])
            # Add the vehicle with the new route
            libsumo.vehicle.add(
                vid,
                route_id,
                typeID="car",
                departLane="random",
                departSpeed="random",
            )
            return True
        except Exception as e:
            # Try with a single-edge route as fallback
            try:
                route_id_fallback = f"respawn_route_{vid}_{self._respawn_counter}_fb"
                libsumo.route.add(route_id_fallback, [src_edge])
                libsumo.vehicle.add(
                    vid,
                    route_id_fallback,
                    typeID="car",
                    departLane="random",
                    departSpeed="random",
                )
                # Set destination after adding
                libsumo.vehicle.changeTarget(vid, dst_edge)
                return True
            except Exception as e2:
                print(f"[sumo_env] _respawn_vehicle({vid}) failed: {e2}")
                return False

    def _ensure_vehicle_population(self):
        """
        Check current vehicle count and spawn new vehicles if below minimum threshold.

        This is called after warmup to guarantee that the simulation has enough
        vehicles for meaningful agent interaction.
        """
        if self._use_mock:
            # MockSUMO always maintains its vehicle pool
            return

        current_count = len(self._vehicle_ids)
        min_count = max(1, int(self.num_vehicles_target * MIN_VEHICLES_RATIO))

        if current_count >= min_count:
            return

        deficit = self.num_vehicles_target - current_count
        print(f"[sumo_env] Vehicle population low ({current_count}/{self.num_vehicles_target}). "
              f"Spawning {deficit} replacement vehicles...")

        all_edges = self._get_all_edges()
        if not all_edges:
            print("[sumo_env] No edges available for vehicle spawning!")
            return

        spawned = 0
        for i in range(deficit):
            new_vid = f"respawned_{self._step_count}_{i}"
            if self._respawn_vehicle(new_vid):
                spawned += 1

        if spawned > 0:
            # Run a few steps to let new vehicles enter the simulation
            for _ in range(10):
                try:
                    libsumo.simulationStep()
                    self._step_count += 1
                    self._sim_time = self._step_count * STEP_LENGTH
                except Exception:
                    break

            # Refresh vehicle state
            try:
                curr_ids = set(libsumo.vehicle.getIDList())
                for vid in curr_ids - set(self._vehicle_ids):
                    x, y = libsumo.vehicle.getPosition(vid)
                    if vid not in self.ndn.nodes:
                        self.ndn.add_node(vid, is_rsu=False, x=x, y=y)
                self._vehicle_ids = list(curr_ids)
                for vid in self._vehicle_ids:
                    x, y  = libsumo.vehicle.getPosition(vid)
                    speed = libsumo.vehicle.getSpeed(vid)
                    angle = libsumo.vehicle.getAngle(vid)
                    self._vehicle_pos[vid]   = (x, y)
                    self._vehicle_speed[vid] = speed
                    self._vehicle_angle[vid] = angle
                    self.ndn.update_node_position(vid, x, y)
            except Exception as e:
                print(f"[sumo_env] _ensure_vehicle_population refresh error: {e}")

        print(f"[sumo_env] After population check: {len(self._vehicle_ids)} vehicles active")

    def step(self, actions: Dict[str, np.ndarray]
             ) -> Tuple[Dict, Dict, Dict, bool, dict]:
        """
        Execute one simulation step.
        actions: dict of vid -> [forwarding, caching, power, subchannel]
        Returns: (obs, rewards, dones, truncated, info)
        """
        # 1. Advance SUMO
        if self._use_mock:
            self._sumo.simulation_step()
        else:
            libsumo.simulationStep()
        self._step_count += 1
        self._sim_time   = self._step_count * STEP_LENGTH

        # 2. Update vehicle state from SUMO
        self._update_vehicle_state()

        # 3. Handle empty vehicle population gracefully
        if not self._vehicle_ids:
            obs    = {}
            rewards = {}
            dones  = {}
            trunc  = self._sim_time >= self.episode_duration_s
            info   = self._get_info({})
            return obs, rewards, dones, trunc, info

        # 4. Update NDN content versions
        self.ndn.update_content_versions(self._sim_time, STEP_LENGTH)

        # 5. Update FIB periodically
        if self._step_count % FIB_UPDATE_PERIOD == 0:
            self.ndn.update_fib(self._sim_time)

        # 6. Process actions and simulate communication
        tx_results = self._process_actions(actions)

        # 7. Update AoI tracker
        node_ids = [vid for vid in self._vehicle_ids] + RSU_IDS
        self.aoi_tracker.tick(self._sim_time, node_ids, STEP_LENGTH)

        # 8. Clean up NDN tables
        for node in self.ndn.nodes.values():
            node.cs.evict_expired(self._sim_time)
            node.pit.cleanup_expired(self._sim_time)

        # 9. Compute observations, rewards, dones
        obs     = self.get_observations()
        rewards = self.get_rewards(actions, tx_results)
        dones   = {vid: False for vid in self._vehicle_ids}
        trunc   = self._sim_time >= self.episode_duration_s

        # Update episode rewards
        for vid, r in rewards.items():
            self.episode_reward[vid] = self.episode_reward.get(vid, 0.0) + r

        info = self._get_info(tx_results)

        return obs, rewards, dones, trunc, info

    # ── Vehicle State ─────────────────────────────────────────────────────────
    def _update_vehicle_state(self):
        """
        Pull vehicle positions/speeds from SUMO.

        CHANGED: When vehicles have arrived (disappeared), calls _respawn_vehicle()
        to re-insert them at a new location, maintaining vehicle population.
        After respawn, refreshes curr_ids to include newly added vehicles.
        """
        if self._use_mock:
            prev_ids = set(self._vehicle_ids)
            curr_ids = set(self._sumo.get_vehicle_ids())
        else:
            prev_ids = set(self._vehicle_ids)
            curr_ids = set(libsumo.vehicle.getIDList())

        # Departed vehicles (new to simulation this step)
        departed = curr_ids - prev_ids
        for vid in departed:
            if self._use_mock:
                x, y = self._sumo.get_vehicle_position(vid)
            else:
                try:
                    x, y = libsumo.vehicle.getPosition(vid)
                except Exception:
                    x, y = 0.0, 0.0
            if vid not in self.ndn.nodes:
                self.ndn.add_node(vid, is_rsu=False, x=x, y=y)

        # Arrived (left) vehicles -> clean up and respawn
        arrived = prev_ids - curr_ids
        for vid in arrived:
            self.ndn.remove_node(vid)
            self.aoi_tracker.reset_node(vid)
            # Attempt to respawn the vehicle at a new location
            self._respawn_vehicle(vid)

        # After respawn attempts, refresh curr_ids to include newly added vehicles
        # Note: vehicles added this step may not appear in getIDList() until next step
        if not self._use_mock and arrived:
            try:
                curr_ids = set(libsumo.vehicle.getIDList())
            except Exception:
                pass

        # Update positions for all current vehicles
        self._vehicle_ids = list(curr_ids)
        stale_ids = []
        for vid in self._vehicle_ids:
            try:
                if self._use_mock:
                    x, y    = self._sumo.get_vehicle_position(vid)
                    speed   = self._sumo.get_vehicle_speed(vid)
                    angle   = self._sumo.get_vehicle_angle(vid)
                else:
                    x, y    = libsumo.vehicle.getPosition(vid)
                    speed   = libsumo.vehicle.getSpeed(vid)
                    angle   = libsumo.vehicle.getAngle(vid)

                self._vehicle_pos[vid]   = (x, y)
                self._vehicle_speed[vid] = speed
                self._vehicle_angle[vid] = angle
                self.ndn.update_node_position(vid, x, y)
            except Exception as e:
                # Vehicle may have left simulation between getIDList and getPosition
                stale_ids.append(vid)

        # Remove stale vehicles that couldn't be queried
        for vid in stale_ids:
            self._vehicle_ids.remove(vid)
            self._vehicle_pos.pop(vid, None)
            self._vehicle_speed.pop(vid, None)
            self._vehicle_angle.pop(vid, None)

    # ── Action Processing ─────────────────────────────────────────────────────
    def _process_actions(self, actions: Dict[str, np.ndarray]) -> dict:
        """
        Simulate communication based on agent actions.
        Returns per-vehicle transmission results.
        """
        results = {}

        if not self._vehicle_ids:
            return results

        for vid in self._vehicle_ids:
            if vid not in actions:
                continue
            action = actions[vid]
            fwd_act  = int(action[0]) % ACTION_DIM_FORWARDING
            cache_act = int(action[1]) % ACTION_DIM_CACHING
            pwr_idx  = int(action[2]) % ACTION_DIM_POWER
            subch    = int(action[3]) % ACTION_DIM_SUBCHANNEL

            tx_power_dbm = POWER_LEVELS_DBM[pwr_idx]
            x1, y1 = self._vehicle_pos.get(vid, (0, 0))

            ctype = self.zipf_model.sample_content()

            if fwd_act == 2:  # V2I
                best_rsu, best_dist = self._nearest_rsu(x1, y1)
                if best_rsu is None or best_dist > 500.0:
                    results[vid] = {"success": False, "aoi": None, "cache_hit": False}
                    continue
                target_id = best_rsu
                link_type = "v2i"
                d = best_dist
            elif fwd_act == 1:  # V2V
                best_neighbor, best_dist = self._nearest_vehicle(vid, x1, y1)
                if best_neighbor is None or best_dist > 300.0:
                    results[vid] = {"success": False, "aoi": None, "cache_hit": False}
                    continue
                target_id = best_neighbor
                link_type = "v2v"
                d = best_dist
            else:  # drop
                results[vid] = {"success": False, "aoi": None, "cache_hit": False}
                continue

            interferers = self._get_interferers(vid, subch, tx_power_dbm)
            success = self.channel.tx_success(
                tx_power_dbm, d, interferers, link_type, los=True)

            self._total_tx   += 1
            cache_hit = False
            aoi_val   = None

            if success:
                self._total_tx_ok += 1
                self._total_bits  += CONTENT_SIZE * 8

                content_name = self.ndn.make_content_name(target_id, ctype)

                target_node = self.ndn.nodes.get(target_id)
                if target_node:
                    cached_pkt = target_node.cs.lookup(content_name, self._sim_time)
                    if cached_pkt is not None:
                        cache_hit = True
                        aoi_val = self._sim_time - cached_pkt.generation_time
                        self.aoi_tracker.record_update(
                            vid, ctype, cached_pkt.generation_time, self._sim_time)
                    else:
                        gen_t = self.ndn._content_gen_times.get(ctype, self._sim_time)
                        pkt = DataPacket(
                            name=content_name, content_type=ctype,
                            version=self.ndn._content_versions.get(ctype, 0),
                            producer_id=target_id, generation_time=gen_t,
                            size_bytes=CONTENT_SIZE)
                        pkt.rx_time = self._sim_time
                        aoi_val = self._sim_time - gen_t

                        if cache_act == 1:
                            requester_node = self.ndn.nodes.get(vid)
                            if requester_node:
                                ttl = NDNNode.optimal_ttl(
                                    self.content_update_rate, 1.0, 0.1,
                                    self.zipf_model.popularity(ctype) + 1e-9)
                                requester_node.cs.insert(pkt, self._sim_time, ttl)

                        self.aoi_tracker.record_update(
                            vid, ctype, gen_t, self._sim_time)

                self.ndn.total_tx_success += 1

            if cache_hit:
                self.ndn.total_cache_hits += 1
            else:
                self.ndn.total_cache_misses += 1

            results[vid] = {
                "success":   success,
                "aoi":       aoi_val,
                "cache_hit": cache_hit,
                "d":         d,
                "link_type": link_type,
                "tx_power":  tx_power_dbm,
                "subchannel": subch,
            }

        return results

    def _nearest_rsu(self, x: float, y: float) -> Tuple[Optional[str], float]:
        best_id, best_d = None, float("inf")
        for rsu_id, (rx, ry) in zip(RSU_IDS, RSU_POSITIONS):
            d = math.sqrt((x - rx)**2 + (y - ry)**2)
            if d < best_d:
                best_id, best_d = rsu_id, d
        return best_id, best_d

    def _nearest_vehicle(self, vid: str, x: float, y: float
                         ) -> Tuple[Optional[str], float]:
        best_id, best_d = None, float("inf")
        for other_id in self._vehicle_ids:
            if other_id == vid:
                continue
            ox, oy = self._vehicle_pos.get(other_id, (0, 0))
            d = math.sqrt((x - ox)**2 + (y - oy)**2)
            if d < best_d:
                best_id, best_d = other_id, d
        return best_id, best_d

    def _get_interferers(self, vid: str, subchannel: int,
                         tx_power_dbm: float) -> List[float]:
        """Get interference from other active transmitters on the same subchannel."""
        x0, y0 = self._vehicle_pos.get(vid, (0, 0))
        interferers = []
        for other_id in self._vehicle_ids:
            if other_id == vid:
                continue
            if self._rng.random() < 0.1:
                ox, oy = self._vehicle_pos.get(other_id, (0, 0))
                d = math.sqrt((x0 - ox)**2 + (y0 - oy)**2)
                if d < 1.0:
                    d = 1.0
                intf_power = tx_power_dbm - (38.77 + 16.7 * math.log10(d) +
                             18.2 * math.log10(5.9))
                interferers.append(intf_power)
        return interferers

    # ── Observations ──────────────────────────────────────────────────────────
    def get_observations(self) -> Dict[str, np.ndarray]:
        """
        Build observation vector for each vehicle.
        Returns empty dict if no vehicles are present.
        """
        obs = {}

        if not self._vehicle_ids:
            return obs

        total_len = (GRID_N - 1) * BLOCK_LEN  # 1000 m

        for vid in self._vehicle_ids:
            x, y  = self._vehicle_pos.get(vid, (0.0, 0.0))
            speed = self._vehicle_speed.get(vid, 0.0)
            angle = self._vehicle_angle.get(vid, 0.0)

            x_norm     = x / total_len
            y_norm     = y / total_len
            speed_norm = speed / MAX_SPEED
            ang_rad    = math.radians(angle)
            ang_sin    = math.sin(ang_rad)
            ang_cos    = math.cos(ang_rad)

            aoi_own = 0.0
            for cid in range(min(10, self.num_contents)):
                aoi_own += self.aoi_tracker.get_aoi(vid, cid, self._sim_time)
            aoi_own = (aoi_own / min(10, self.num_contents)) / max(self.episode_duration_s, 1.0)

            node = self.ndn.nodes.get(vid)
            cache_ratio = node.cs.size / max(1, self.cache_size) if node else 0.0

            cbr = self.channel.compute_cbr(len(self._vehicle_ids))

            neighbors = []
            for other_id in self._vehicle_ids:
                if other_id == vid:
                    continue
                ox, oy = self._vehicle_pos.get(other_id, (0, 0))
                d = math.sqrt((x - ox)**2 + (y - oy)**2)
                if d <= 300.0:
                    neighbors.append((d, other_id))
            neighbors.sort()
            num_neighbors = len(neighbors) / max(1, len(self._vehicle_ids))

            K = 5
            neighbor_aoi = []
            for d, nid in neighbors[:K]:
                aoi_n = 0.0
                for cid in range(min(5, self.num_contents)):
                    aoi_n += self.aoi_tracker.get_aoi(nid, cid, self._sim_time)
                aoi_n /= max(1, min(5, self.num_contents))
                neighbor_aoi.append(min(aoi_n / self.episode_duration_s, 1.0))
            while len(neighbor_aoi) < K:
                neighbor_aoi.append(1.0)

            obs_vec = np.array([
                x_norm, y_norm, speed_norm, ang_sin, ang_cos,
                min(aoi_own, 1.0),
                min(cache_ratio, 1.0),
                min(cbr, 1.0),
                min(num_neighbors, 1.0),
            ] + neighbor_aoi, dtype=np.float32)

            obs[vid] = obs_vec

        return obs

    # ── Rewards ───────────────────────────────────────────────────────────────
    def get_rewards(self, actions: Dict[str, np.ndarray],
                    tx_results: dict) -> Dict[str, float]:
        """
        Compute per-agent rewards.
        Returns empty dict if no vehicles are present.
        """
        rewards = {}

        if not self._vehicle_ids:
            return rewards

        cbr = self.channel.compute_cbr(len(self._vehicle_ids))
        cbr_penalty = max(0.0, cbr - CBR_THRESH)

        for vid in self._vehicle_ids:
            res = tx_results.get(vid, {})
            success   = res.get("success", False)
            aoi_val   = res.get("aoi", None)
            cache_hit = res.get("cache_hit", False)

            aoi_now = self.aoi_tracker.get_aoi(
                vid, 0, self._sim_time)
            r = -aoi_now / max(self.episode_duration_s, 1.0)

            if success and aoi_val is not None:
                r += 0.5 * (1.0 - min(aoi_val / self.episode_duration_s, 1.0))

            if cache_hit:
                r += 0.1

            r -= 0.2 * cbr_penalty

            rewards[vid] = float(r)

        return rewards

    # ── Info ──────────────────────────────────────────────────────────────────
    def _get_info(self, tx_results: dict) -> dict:
        """Collect episode info metrics."""
        aoi_stats = self.aoi_tracker.get_stats(self._sim_time)
        tsr = self._total_tx_ok / max(1, self._total_tx)
        throughput = self._total_bits / max(1e-9, self._sim_time) / 1e6

        hits   = sum(1 for r in tx_results.values() if r.get("cache_hit"))
        misses = sum(1 for r in tx_results.values() if not r.get("cache_hit"))
        chr_ep = hits / max(1, hits + misses)

        cbr = self.channel.compute_cbr(len(self._vehicle_ids))
        cvr = 1.0 if cbr > CBR_THRESH else 0.0

        return {
            "sim_time":         self._sim_time,
            "num_vehicles":     len(self._vehicle_ids),
            "average_aoi":      aoi_stats["average_aoi"],
            "peak_aoi":         aoi_stats["peak_aoi"],
            "tx_success_rate":  tsr,
            "tx_successes":     self._total_tx_ok,
            "tx_total":         self._total_tx,
            "throughput_mbps":  throughput,
            "bits_delivered":   self._total_bits,
            "cache_hit_ratio":  chr_ep,
            "cache_hits":       hits,
            "cache_total":      hits + misses,
            "cbr":              cbr,
            "constraint_violation": cvr,
        }

    # ── Properties ────────────────────────────────────────────────────────────
    @property
    def sim_time(self) -> float:
        return self._sim_time

    @property
    def vehicle_ids(self) -> List[str]:
        return list(self._vehicle_ids)

    @property
    def obs_dim(self) -> int:
        return OBS_DIMS_PER_VEHICLE

    @property
    def action_dims(self) -> Tuple[int, int, int, int]:
        return (ACTION_DIM_FORWARDING, ACTION_DIM_CACHING,
                ACTION_DIM_POWER, ACTION_DIM_SUBCHANNEL)

    def close(self):
        """Clean up resources."""
        self._stop_sumo()

    def __repr__(self):
        return (f"SUMOEnv(vehicles={len(self._vehicle_ids)}, "
                f"t={self._sim_time:.1f}s, "
                f"cache={self.cache_size}, contents={self.num_contents})")
