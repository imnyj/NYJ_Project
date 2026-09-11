import os
import sys
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import traci
import math
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class V2V_Env(gym.Env):
    """
    Outage Zone V2V Precaching Decision DRL Environment
    나준상 연구원 모델 구현: RSU 음영지역 진입 시 대비하여 주변 후보 차량들에게 V2V용 프리캐싱을 할지 결정.
    """
    metadata = {"render_modes": ["human", "none"], "render_fps": 1}

    def __init__(self, sumo_cfg_file, render_mode="none", density_scale=1.0, ablation_mode=False):
        super(V2V_Env, self).__init__()
        
        self.sumo_cfg_file = sumo_cfg_file
        self.render_mode = render_mode
        self.density_scale = density_scale
        self.ablation_mode = ablation_mode
        
        self.sumo_cmd = [
            "sumo-gui" if render_mode == "human" else "sumo", 
            "-c", self.sumo_cfg_file, 
            "--step-length", "1.0", 
            "--scale", str(self.density_scale),
            "--no-warnings"
        ]
        
        self.rsu_radius = 300.0  # meters
        self.v2v_radius = 50.0   # meters
        self.c_step = 0.75  # 6Mbps
        self.c_total_range = (10.0, 20.0) # MB
        
        self.R_base = 10.0
        self.P_base = 10.0
        self.alpha = 10.0
        self.beta = 10.0
        self.gamma = 10.0
        self.delta = 10.0
        
        low = np.array([0.0, 0.0, 0.0, 0.0, 0.0, -40.0, 0.0, 0.0, 0.0], dtype=np.float32)
        high = np.array([self.rsu_radius, 40.0, 20.0, 200.0, 100.0, 40.0, 30.0, 1.0, 100.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        
        # SB3 SAC/TD3를 위해 Continuous Action Space 적용 (-1 to 1)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        
        self.traci_started = False
        self.target_vehicle = None
        self.current_rsu = None
        self.candidate_vehicles = []
        
        self.request_start_time = 0.0
        
        self.rsus = {}
        self._load_rsus()
        
    def _load_rsus(self):
        coords = [450.0, 1350.0, 2250.0, 3150.0, 4050.0]
        rsu_id = 1
        for x in coords:
            for y in coords:
                self.rsus[f"RSU_{rsu_id}"] = (x, y)
                rsu_id += 1

    def _get_distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _find_nearest_rsu(self, pos):
        min_dist = float('inf')
        nearest = None
        for rid, rpos in self.rsus.items():
            d = self._get_distance(pos, rpos)
            if d < min_dist:
                min_dist = d
                nearest = rid
        return nearest, min_dist

    def _start_sumo(self):
        if self.traci_started:
            try: traci.close()
            except: pass
        traci.start(self.sumo_cmd)
        self.traci_started = True

    def _find_candidates(self, target_vid):
        edge_id = traci.vehicle.getRoadID(target_vid)
        target_pos = traci.vehicle.getPosition(target_vid)
        candidates = []
        for vid in traci.vehicle.getIDList():
            if vid != target_vid and traci.vehicle.getRoadID(vid) == edge_id:
                dist = self._get_distance(target_pos, traci.vehicle.getPosition(vid))
                if dist <= 150.0:
                    candidates.append(vid)
        return candidates

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        if not self.traci_started:
            self._start_sumo()
        
        self.target_vehicle = None
        self.current_rsu = None
        self.candidate_vehicles = []
        
        self.remained_content_size = random.uniform(self.c_total_range[0], self.c_total_range[1])
        self.total_content_size = self.remained_content_size
        
        while True:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            if traci.simulation.getMinExpectedNumber() <= 0:
                self._start_sumo()
                continue
                
            veh_ids = traci.vehicle.getIDList()
            if not veh_ids: continue
                
            for vid in random.sample(veh_ids, len(veh_ids)):
                pos = traci.vehicle.getPosition(vid)
                nearest_rsu, dist = self._find_nearest_rsu(pos)
                if dist <= self.rsu_radius:
                    candidates = self._find_candidates(vid)
                    if len(candidates) > 0:
                        self.target_vehicle = vid
                        self.current_rsu = nearest_rsu
                        self.candidate_vehicles = candidates
                        self.request_start_time = current_time
                        break
            if self.target_vehicle is not None:
                break
        return self._get_state(), {}

    def _get_state(self):
        if self.target_vehicle not in traci.vehicle.getIDList():
            return np.zeros(9, dtype=np.float32)
            
        pos = traci.vehicle.getPosition(self.target_vehicle)
        vel = traci.vehicle.getSpeed(self.target_vehicle)
        rsu_pos = self.rsus[self.current_rsu]
        dist_to_rsu = self._get_distance(pos, rsu_pos)
        
        valid_cands = [v for v in self.candidate_vehicles if v in traci.vehicle.getIDList()]
        num_candidates = len(valid_cands)
        
        if num_candidates > 0:
            dists = [self._get_distance(pos, traci.vehicle.getPosition(v)) for v in valid_cands]
            vels = [traci.vehicle.getSpeed(v) - vel for v in valid_cands]
            avg_rel_dist = np.mean(dists)
            std_rel_dist = np.std(dists)
            avg_rel_vel = np.mean(vels)
        else:
            avg_rel_dist = 0.0; std_rel_dist = 0.0; avg_rel_vel = 0.0
        
        tl_phase = 1.0 
        tl_rem_time = 10.0 
        next_tls = traci.vehicle.getNextTLS(self.target_vehicle)
        if len(next_tls) > 0:
            tl_id, tl_link, tl_dist, tl_state = next_tls[0]
            if tl_state.lower() in ['r', 'y']:
                tl_phase = 0.0
            
        state = np.array([
            dist_to_rsu, max(0.0, vel), float(num_candidates),
            avg_rel_dist, std_rel_dist, avg_rel_vel,
            self.remained_content_size, tl_phase, tl_rem_time
        ], dtype=np.float32)
        return state

    def step(self, action_array):
        discrete_action = 1 if action_array[0] > 0.0 else 0
        
        done = False
        reward = 0.0
        is_download_complete = False
        N_rem = 0
        c_v2v_downloaded = 0.0
        access_delay = 0.0
        
        while not done:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            
            if self.target_vehicle not in traci.vehicle.getIDList():
                done = True
                reward = -self.P_base
                break
                
            pos = traci.vehicle.getPosition(self.target_vehicle)
            nearest_rsu, dist = self._find_nearest_rsu(pos)
            
            if dist <= self.rsu_radius and nearest_rsu == self.current_rsu:
                if not is_download_complete:
                    self.remained_content_size -= self.c_step
                    if self.remained_content_size <= 0:
                        is_download_complete = True
                        access_delay = current_time - self.request_start_time
                else:
                    N_rem += 1
            else:
                if is_download_complete:
                    W_curr = N_rem * self.c_step
                    if discrete_action == 1:
                        num_cands = len(self.candidate_vehicles)
                        reward = -self.P_base if self.ablation_mode else -self.P_base - self.beta * ((W_curr * num_cands) / self.total_content_size)
                    else:
                        reward = self.R_base if self.ablation_mode else self.R_base + self.gamma * (W_curr / self.total_content_size)
                    done = True
                    break
                else:
                    if discrete_action == 0:
                        c_missed = self.remained_content_size
                        reward = -self.P_base if self.ablation_mode else -self.P_base - self.delta * (c_missed / self.total_content_size)
                        done = True
                        break
                    else:
                        valid_cands = [v for v in self.candidate_vehicles if v in traci.vehicle.getIDList()]
                        v2v_connected = False
                        for cvid in valid_cands:
                            c_dist = self._get_distance(pos, traci.vehicle.getPosition(cvid))
                            if c_dist <= self.v2v_radius:
                                v2v_connected = True
                                break
                                
                        if v2v_connected:
                            self.remained_content_size -= self.c_step
                            c_v2v_downloaded += self.c_step
                            if self.remained_content_size <= 0:
                                reward = self.R_base if self.ablation_mode else self.R_base + self.alpha * (c_v2v_downloaded / self.total_content_size)
                                is_download_complete = True
                                access_delay = current_time - self.request_start_time
                                done = True
                                break
                        else:
                            c_missed = self.remained_content_size
                            reward = -self.P_base if self.ablation_mode else -self.P_base - self.delta * (c_missed / self.total_content_size)
                            done = True
                            break

        state = self._get_state() if not done else np.zeros(9, dtype=np.float32)
        
        if not is_download_complete:
            access_delay = current_time - self.request_start_time
            
        info = {
            "W_curr": N_rem * self.c_step, 
            "remained_content": max(0.0, self.remained_content_size),
            "access_delay": access_delay,
            "success": is_download_complete
        }
        return state, float(reward), done, False, info

    def close(self):
        if self.traci_started:
            try: traci.close()
            except: pass
        self.traci_started = False
