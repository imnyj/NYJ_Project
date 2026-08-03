"""
AoI-Guaranteed Robust ILP Precaching in CIoV — Core Simulation Engine
Stage 2 Implementation
Author: Experimenter Agent
Date: 2026-05-21

Architecture:
  - CIoVSimulator: main simulation environment (libsumo-based mobility model, trajectory caching)
  - RILPSolver, GreedyPrecaching, Baselines in algorithms.py
  - MetricCollector: CHR, CDSR, AoI_violation_rate, PCO, RLBI
"""

import random
import math
import time
import os
import pickle
from collections import defaultdict

try:
    import libsumo
    _HAS_LIBSUMO = True
except ImportError:
    _HAS_LIBSUMO = False

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

_RSU_POSITIONS_STATIC = [
    ('N7',  1200.0,  1200.0), ('N8',  1200.0,  3600.0), ('N9',  1200.0,  6000.0),
    ('N10', 1200.0,  8400.0), ('N11', 1200.0, 10800.0),
    ('N14', 3600.0,  1200.0), ('N15', 3600.0,  3600.0), ('N16', 3600.0,  6000.0),
    ('N17', 3600.0,  8400.0), ('N18', 3600.0, 10800.0),
    ('N21', 6000.0,  1200.0), ('N22', 6000.0,  3600.0), ('N23', 6000.0,  6000.0),
    ('N24', 6000.0,  8400.0), ('N25', 6000.0, 10800.0),
    ('N28', 8400.0,  1200.0), ('N29', 8400.0,  3600.0), ('N30', 8400.0,  6000.0),
    ('N31', 8400.0,  8400.0), ('N32', 8400.0, 10800.0),
    ('N35', 10800.0,  1200.0), ('N36', 10800.0,  3600.0), ('N37', 10800.0,  6000.0),
    ('N38', 10800.0,  8400.0), ('N39', 10800.0, 10800.0),
]

def compute_zipf_weights(C, s=0.8, rng=None):
    ranks = list(range(1, C + 1))
    weights = [1.0 / (r ** s) for r in ranks]
    total = sum(weights)
    return [w / total for w in weights]

# ─────────────────────────────────────────────────────────────
# Simulation Environment
# ─────────────────────────────────────────────────────────────
class CIoVSim:
    def __init__(self, seed=42, density_per_cell=5, prediction_error_pct=10, 
                 gamma=2.0, tau_max=5, duration_steps=1800, warmup_steps=300,
                 sumo_dir=None, mode='simulate', trajectory_path=None, 
                 checkpoint_dir=None, run_id=None):
        self.seed = seed
        self.density_per_cell = density_per_cell
        self.n_vehicles = density_per_cell * 25  # Fixed to static RSU array size
        self.prediction_error_pct = prediction_error_pct
        self.gamma = gamma
        self.tau_max = tau_max
        self.duration_steps = duration_steps
        self.warmup_steps = warmup_steps
        
        self.mode = mode
        self.trajectory_path = trajectory_path
        self.checkpoint_dir = checkpoint_dir
        self.run_id = run_id
        
        self.rng = random.Random(seed)
        
        # Content catalog setup
        C = PARAMS["content_catalog_size"]
        self.content_sizes = [self.rng.uniform(*PARAMS["content_size_range"]) for _ in range(C)]
        self.popularity = compute_zipf_weights(C, s=PARAMS["zipf_s"], rng=self.rng)
        
        # SUMO setup
        self.sumo_dir = sumo_dir
        if not self.sumo_dir:
            self.sumo_dir = "/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo"
            
        self.rsu_positions = [(r[1], r[2]) for r in _RSU_POSITIONS_STATIC]
        
        # State
        self.vehicles = {} # vid -> {'x', 'y', 'vx', 'vy', 'speed', 'cache': {cid: age_at_delivery}}
        self.trajectories = []  # List of lists of vehicle dicts
        self.tracked_vids = set()
        self.current_step = 0
        
        self.metrics = {
            'requests': 0,
            'hits_v2i': 0,
            'hits_v2v': 0,
            'cdsr_num': 0,
            'cdsr_den': 0,
            'aoi_viol_num': 0,
            'aoi_viol_den': 0,
            'pco_data': 0,
            'rlbi_loads': defaultdict(float)
        }
        
        self._pending_deliveries = {} # (vid, cid) -> delivery_step
        self._t_gen = {}
        
        # Checkpoint restore logic
        self.restored_from_checkpoint = False
        if self.mode == 'simulate':
            self._load_trajectory()
            if self.checkpoint_dir and self.run_id:
                ckpt_file = os.path.join(self.checkpoint_dir, f"ckpt_{self.run_id}.pkl")
                if os.path.exists(ckpt_file):
                    self._load_checkpoint(ckpt_file)
                    self.restored_from_checkpoint = True

    def _save_checkpoint(self, filepath):
        state = {
            'current_step': self.current_step,
            'vehicles': self.vehicles,
            'metrics': self.metrics,
            '_pending_deliveries': self._pending_deliveries,
            '_t_gen': self._t_gen,
            'rng_state': self.rng.getstate()
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

    def _load_checkpoint(self, filepath):
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        self.current_step = state['current_step']
        self.vehicles = state['vehicles']
        self.metrics = state['metrics']
        self._pending_deliveries = state['_pending_deliveries']
        self._t_gen = state['_t_gen']
        self.rng.setstate(state['rng_state'])

    def _run_sumo_and_save_trajectory(self):
        """Phase 1: Run SUMO and cache trajectory to disk."""
        if not _HAS_LIBSUMO:
            raise ImportError("libsumo is required to generate trajectories.")
            
        sumocfg = os.path.join(self.sumo_dir, "generated.sumocfg")
        if not os.path.exists(sumocfg):
            raise FileNotFoundError(f"SUMO config not found: {sumocfg}")
            
        libsumo.start(["sumo", "-c", sumocfg, "--step-length", "1.0", "--no-warnings"])
        
        trajectories = []
        for step in range(self.duration_steps):
            libsumo.simulationStep()
            step_vehicles = []
            
            # Grab all vehicles without artificial truncation
            vids = libsumo.vehicle.getIDList()
            for vid in vids:
                x, y = libsumo.vehicle.getPosition(vid)
                speed = libsumo.vehicle.getSpeed(vid)
                angle = libsumo.vehicle.getAngle(vid)
                vx = speed * math.cos(math.radians(angle))
                vy = speed * math.sin(math.radians(angle))
                
                step_vehicles.append({
                    'id': vid,
                    'x': x,
                    'y': y,
                    'vx': vx,
                    'vy': vy,
                    'speed': speed
                })
                
            trajectories.append(step_vehicles)
            
        libsumo.close()
        
        if self.trajectory_path:
            traj_dir = os.path.dirname(self.trajectory_path)
            if traj_dir:
                os.makedirs(traj_dir, exist_ok=True)
            with open(self.trajectory_path, 'wb') as f:
                pickle.dump(trajectories, f)
                
        return trajectories

    def _load_trajectory(self):
        """Phase 2: Load trajectory from disk and sample vehicles based on density."""
        if not self.trajectory_path or not os.path.exists(self.trajectory_path):
            raise FileNotFoundError(f"Trajectory file not found: {self.trajectory_path}")
            
        with open(self.trajectory_path, 'rb') as f:
            self.trajectories = pickle.load(f)
            
        # Sampling vehicles to reflect true physical density globally
        # MAX_DENSITY = 20 vehicles per cell (RSU). 
        # Keep probability p = density / 20.0
        p_keep = min(1.0, self.density_per_cell / 20.0)
        
        all_vids = set()
        for step_vehicles in self.trajectories:
            for v in step_vehicles:
                all_vids.add(v['id'])
                
        sorted_vids = sorted(list(all_vids))
        self.rng.shuffle(sorted_vids)
        keep_count = int(len(sorted_vids) * p_keep)
        self.tracked_vids = set(sorted_vids[:keep_count])

    def _calculate_let_and_outage(self, v):
        """Calculate LET (slots) and outage_end (slots) for a vehicle."""
        vx, vy = v['x'], v['y']
        speed = v['speed']
        dx, dy = v['vx'], v['vy']
        R = PARAMS['rsu_comm_range']
        O = PARAMS['outage_zone_m']
        sw = PARAMS['scheduling_window']
        
        # Find nearest RSU
        best_rsu = 0
        best_dist = float('inf')
        for i, (rx, ry) in enumerate(self.rsu_positions):
            dist = math.hypot(vx - rx, vy - ry)
            if dist < best_dist:
                best_dist = dist
                best_rsu = i
                
        rx, ry = self.rsu_positions[best_rsu]
        
        # Outage end calculation
        outage_end = 0
        if best_dist > R:
            if best_dist <= R + O:
                # In outage zone. Estimate time to enter comm range
                dist_to_comm = best_dist - R
                outage_end = math.ceil(dist_to_comm / max(speed, 0.1))
            else:
                # Outside both comm and outage zone
                outage_end = sw # effectively unreachable
                
        # LET calculation (time to exit circle)
        rel_x = vx - rx
        rel_y = vy - ry
        a = dx**2 + dy**2
        b = 2 * (rel_x * dx + rel_y * dy)
        c_val = rel_x**2 + rel_y**2 - R**2
        
        discriminant = b**2 - 4 * a * c_val
        let = sw # Default to max window
        
        if best_dist <= R:
            if discriminant < 0 or a < 1e-6:
                let = sw
            else:
                t_exit = (-b + math.sqrt(discriminant)) / (2 * a)
                if t_exit > 0:
                    let = max(1, min(math.ceil(t_exit), sw))
        else:
            let = 0 # Currently outside
            
        return let, outage_end

    def run(self, cache_decision_fn):
        if self.mode == 'generate':
            self._run_sumo_and_save_trajectory()
            return None
            
        # Simulate mode
        # Main simulation loop
        sw = PARAMS['scheduling_window']
        start_step = self.current_step
        
        for step in range(start_step, self.duration_steps):
            self.current_step = step
            step_idx = min(step, len(self.trajectories) - 1)
            traj_snapshot = self.trajectories[step_idx]
            
            # Update vehicle states from trajectory
            active_vids_this_step = []
            for v_data in traj_snapshot:
                vid = v_data['id']
                if vid not in self.tracked_vids:
                    continue
                active_vids_this_step.append(vid)
                if vid not in self.vehicles:
                    self.vehicles[vid] = {'id': vid, 'cache': {}}
                
                v = self.vehicles[vid]
                v['x'] = v_data['x']
                v['y'] = v_data['y']
                v['vx'] = v_data['vx']
                v['vy'] = v_data['vy']
                v['speed'] = v_data['speed']
                    
            # 1. Check pending deliveries
            completed = []
            for (vid, cid), delivery_step in self._pending_deliveries.items():
                if step >= delivery_step:
                    if vid in self.vehicles and vid in active_vids_this_step:
                        v = self.vehicles[vid]
                        let, _ = self._calculate_let_and_outage(v)
                        # Successful delivery if vehicle is in RSU range
                        if let > 0:
                            # Record the AoI of the item at the time of delivery
                            # age = delivery_step - generation_time
                            age_at_delivery = delivery_step - self._t_gen.get(cid, 0)
                            v['cache'][cid] = age_at_delivery
                    completed.append((vid, cid))
                    
            for key in completed:
                del self._pending_deliveries[key]
                    
            # 2. Precaching Decisions (every scheduling window)
            if step % sw == 0 and step >= self.warmup_steps:
                # Update LET, Outage, t_gen
                algo_vehicles = []
                for vid in active_vids_this_step:
                    v = self.vehicles[vid]
                    true_let, true_outage_end = self._calculate_let_and_outage(v)
                    
                    # Inject prediction error bounded by prediction_error_pct
                    error_magnitude = (self.prediction_error_pct / 100.0) * true_let
                    
                    # The prediction fluctuates uniformly within [-error_magnitude, error_magnitude]
                    let_pred = true_let + error_magnitude * self.rng.uniform(-1, 1)
                    let_pred = max(0.0, let_pred)
                    
                    # RILP uses robust LET (conservatively bound the error)
                    # Use the absolute max error magnitude to ensure safety
                    let_robust = max(0.0, let_pred - self.gamma * error_magnitude)
                    
                    v['let'] = let_pred            # Baselines see the FLAWED prediction
                    v['let_robust'] = let_robust   # RILP uses the SAFE lower bound
                    v['delta_v'] = error_magnitude # Pass the maximum error margin to algorithms
                    v['outage_end'] = true_outage_end
                    
                    # Convert dict cache to set for the algorithm interface
                    v_interface = v.copy()
                    v_interface['cache'] = set(v['cache'].keys())
                    algo_vehicles.append(v_interface)
                    
                # Reset t_gen
                for c in range(PARAMS['content_catalog_size']):
                    self._t_gen[c] = step
                    
                params = {
                    'catalog_size': PARAMS['content_catalog_size'],
                    'cache_capacity': PARAMS['cache_cap'],
                    'popularity': self.popularity,
                    'content_sizes': self.content_sizes,
                    'tau_max': self.tau_max,
                    'gamma': self.gamma,
                    'pred_error': self.prediction_error_pct / 100.0,
                    'v2i_bw': PARAMS['v2i_bw_mbps'],
                    'v2v_bw': PARAMS['v2v_bw_mbps'],
                    'sched_window': sw,
                    'n_rsu': 25,
                    'rsu_positions': self.rsu_positions,
                    'current_step': step
                }
                
                # Get decisions
                if cache_decision_fn:
                    decisions = cache_decision_fn(algo_vehicles, params, self.rng)
                    
                    # Process decisions and schedule deliveries
                    for vid, cids in decisions.items():
                        if vid not in self.vehicles:
                            continue
                        v = self.vehicles[vid]
                        cids = list(cids)
                        self.rng.shuffle(cids) # Randomize to avoid bias
                        cap_used = 0
                        v['cache'] = {} # Evict old cache
                        
                        for cid in cids:
                            size = math.ceil(self.content_sizes[cid])
                            if cap_used + size <= PARAMS['cache_cap']:
                                tx_time = math.ceil((self.content_sizes[cid] * 8) / PARAMS['v2i_bw_mbps'])
                                delivery_time = max(tx_time, v['outage_end'])
                                delivery_step = step + delivery_time
                                self._pending_deliveries[(vid, cid)] = delivery_step
                                cap_used += size
                                
                                # CDSR
                                self.metrics['cdsr_den'] += 1
                                if delivery_time <= v['let'] and delivery_time >= v['outage_end']:
                                    self.metrics['cdsr_num'] += 1
                                    
                                # PCO
                                self.metrics['pco_data'] += self.content_sizes[cid]

            # 3. Request Generation & Evaluation
            if step >= self.warmup_steps:
                # Per-vehicle request probability (e.g., 10% chance per slot per active vehicle)
                for vid in active_vids_this_step:
                    if self.rng.random() < 0.1:
                        cid = self.rng.choices(list(range(PARAMS['content_catalog_size'])), 
                                               weights=self.popularity, k=1)[0]
                        
                        v = self.vehicles[vid]
                        self.metrics['requests'] += 1
                        
                        v2v_hit = False
                        best_neighbor = None
                        
                        if cid in v['cache']:
                            # V2I Hit
                            self.metrics['hits_v2i'] += 1
                            # AoI is the age of the content when it was delivered
                            if v['cache'][cid] > self.tau_max:
                                self.metrics['aoi_viol_num'] += 1
                        else:
                            # Check neighbors for V2V Hit
                            best_dist = float('inf')
                            
                            for nid in active_vids_this_step:
                                nv = self.vehicles[nid]
                                if nid != vid and cid in nv['cache']:
                                    dist = math.hypot(v['x'] - nv['x'], v['y'] - nv['y'])
                                    if dist < PARAMS['rsu_comm_range']: # V2V range same as RSU for simplicity
                                        if dist < best_dist:
                                            best_dist = dist
                                            best_neighbor = nid
                                            
                            if best_neighbor is not None:
                                self.metrics['hits_v2v'] += 1
                                v2v_hit = True
                                self.metrics['rlbi_loads'][best_neighbor] += self.content_sizes[cid]
                                # AoI for V2V assumes extra 1 slot delay
                                if self.vehicles[best_neighbor]['cache'][cid] + 1 > self.tau_max:
                                    self.metrics['aoi_viol_num'] += 1
                                    
                            if not v2v_hit:
                                # Miss - Must fetch from cloud. Backhaul delay >> tau_max.
                                self.metrics['aoi_viol_num'] += 1
                                
                        self.metrics['aoi_viol_den'] += 1
                        
            # Checkpoint logic
            if self.checkpoint_dir and self.run_id and step % 100 == 0 and step > 0:
                ckpt_file = os.path.join(self.checkpoint_dir, f"ckpt_{self.run_id}.pkl")
                self._save_checkpoint(ckpt_file)
                
        # End of simulation
        
        # Calculate final metrics
        chr_val = (self.metrics['hits_v2i'] + self.metrics['hits_v2v']) / max(1, self.metrics['requests'])
        cdsr_val = self.metrics['cdsr_num'] / max(1, self.metrics['cdsr_den'])
        aoi_viol_val = self.metrics['aoi_viol_num'] / max(1, self.metrics['aoi_viol_den'])
        
        # PCO (normalized)
        baseline_data = self.metrics['requests'] * sum(self.content_sizes) / PARAMS['content_catalog_size']
        pco_val = self.metrics['pco_data'] / max(1e-6, baseline_data)
        
        # RLBI
        loads = list(self.metrics['rlbi_loads'].values())
        if loads:
            sum_l = sum(loads)
            sum_l2 = sum(l**2 for l in loads)
            rlbi_val = (sum_l**2) / (len(loads) * sum_l2) if sum_l2 > 0 else 1.0
        else:
            rlbi_val = 1.0
            
        # Clean up checkpoint
        if self.checkpoint_dir and self.run_id:
            ckpt_file = os.path.join(self.checkpoint_dir, f"ckpt_{self.run_id}.pkl")
            if os.path.exists(ckpt_file):
                os.remove(ckpt_file)
                
        return {
            'CHR': chr_val,
            'CDSR': cdsr_val,
            'AoI_violation_rate': aoi_viol_val,
            'PCO': pco_val,
            'RLBI': rlbi_val
        }
