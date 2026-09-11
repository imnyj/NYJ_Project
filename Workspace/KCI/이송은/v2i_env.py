import os
import sys
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import traci
import math
import random
import logging
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class V2I_Env(gym.Env):
    """
    V2I Precaching Decision DRL Environment
    이송은 연구원 모델 구현: RSU 환경 내에서 Next RSU로의 Precaching 여부를 결정.
    """
    metadata = {"render_modes": ["human", "none"], "render_fps": 1}

    def __init__(self, sumo_cfg_file, render_mode="none", density_scale=1.0, ablation_mode=False):
        super(V2I_Env, self).__init__()
        
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
        
        self.rsu_radius = 300.0
        self.c_step = 0.75
        self.c_total_range = (10.0, 20.0)
        
        self.R_base = 10.0
        self.P_base = 10.0
        self.alpha = 10.0
        self.beta = 10.0
        self.gamma = 10.0
        self.delta = 10.0
        
        self.min_history_required = 5
        self.history_capacity = 20
        self.rsu_entry_times = {}
        self.rsu_avg_velocities = {}
        
        low = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        high = np.array([self.rsu_radius, 40.0, 30.0, 10.0, 1.0, 100.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        
        # SB3 SAC/TD3를 위해 Continuous Action Space로 변경 (-1.0 to 1.0)
        # 0 초과면 Precache(1), 0 이하면 No Precache(0)으로 매핑
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        
        self.traci_started = False
        self.target_vehicle = None
        self.current_rsu = None
        self.next_rsu = None
        
        self.request_start_time = 0.0
        
        self.rsus = {}
        self._load_rsus()
        
    def _load_rsus(self):
        coords = [450.0, 1350.0, 2250.0, 3150.0, 4050.0]
        rsu_id = 1
        for x in coords:
            for y in coords:
                rid = f"RSU_{rsu_id}"
                self.rsus[rid] = (x, y)
                self.rsu_avg_velocities[rid] = deque(maxlen=self.history_capacity)
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
            try:
                traci.close()
            except:
                pass
        traci.start(self.sumo_cmd)
        self.traci_started = True
        self.rsu_entry_times.clear()
        for q in self.rsu_avg_velocities.values():
            q.clear()

    def _update_rsu_trackers(self, current_time):
        current_vids = set(traci.vehicle.getIDList())
        for vid in current_vids:
            pos = traci.vehicle.getPosition(vid)
            nearest_rsu, dist = self._find_nearest_rsu(pos)
            in_rsu = (dist <= self.rsu_radius)
            if vid in self.rsu_entry_times:
                prev_rsu, entry_time = self.rsu_entry_times[vid]
                if not in_rsu or prev_rsu != nearest_rsu:
                    dwell_time = current_time - entry_time
                    if dwell_time > 0:
                        avg_vel = (self.rsu_radius * 2) / dwell_time
                        self.rsu_avg_velocities[prev_rsu].append(avg_vel)
                    del self.rsu_entry_times[vid]
                    if in_rsu:
                        self.rsu_entry_times[vid] = (nearest_rsu, current_time)
            else:
                if in_rsu:
                    self.rsu_entry_times[vid] = (nearest_rsu, current_time)
        stale_vids = set(self.rsu_entry_times.keys()) - current_vids
        for svid in stale_vids:
            del self.rsu_entry_times[svid]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if not self.traci_started:
            self._start_sumo()
        
        self.target_vehicle = None
        self.current_rsu = None
        self.next_rsu = None
        self.remained_content_size = random.uniform(self.c_total_range[0], self.c_total_range[1])
        self.total_content_size = self.remained_content_size
        
        while True:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            if traci.simulation.getMinExpectedNumber() <= 0:
                self._start_sumo()
                continue
                
            self._update_rsu_trackers(current_time)
            veh_ids = traci.vehicle.getIDList()
            if not veh_ids: continue
                
            for vid in random.sample(veh_ids, len(veh_ids)):
                pos = traci.vehicle.getPosition(vid)
                nearest_rsu, dist = self._find_nearest_rsu(pos)
                if dist <= self.rsu_radius:
                    if len(self.rsu_avg_velocities[nearest_rsu]) >= self.min_history_required:
                        self.target_vehicle = vid
                        self.current_rsu = nearest_rsu
                        self.request_start_time = current_time
                        break
            if self.target_vehicle is not None:
                break
        return self._get_state(), {}

    def _get_state(self):
        if self.target_vehicle not in traci.vehicle.getIDList():
            return np.zeros(6, dtype=np.float32)
        pos = traci.vehicle.getPosition(self.target_vehicle)
        rsu_pos = self.rsus[self.current_rsu]
        dist_to_rsu = self._get_distance(pos, rsu_pos)
        
        rsu_history = self.rsu_avg_velocities[self.current_rsu]
        rsu_avg_velocity = sum(rsu_history) / len(rsu_history) if rsu_history else 10.0
        
        tl_phase = 1.0 
        tl_rem_time = 10.0 
        next_tls = traci.vehicle.getNextTLS(self.target_vehicle)
        if len(next_tls) > 0:
            tl_id, tl_link, tl_dist, tl_state = next_tls[0]
            if tl_state.lower() in ['r', 'y']:
                tl_phase = 0.0
            
        state = np.array([
            dist_to_rsu,
            rsu_avg_velocity,
            self.remained_content_size,
            self.c_step * (1.0 / 1.0),
            tl_phase,
            tl_rem_time
        ], dtype=np.float32)
        return state

    def step(self, action_array):
        # Continuous action을 Binary 로 매핑 (0초과면 Precache)
        discrete_action = 1 if action_array[0] > 0.0 else 0
        
        done = False
        reward = 0.0
        is_download_complete = False
        completed_in_rsu = None
        N_rem = 0
        c_next_downloaded = 0.0
        access_delay = 0.0
        
        while not done:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            
            if traci.simulation.getMinExpectedNumber() <= 0:
                done = True
                break
            self._update_rsu_trackers(current_time)
            
            if self.target_vehicle not in traci.vehicle.getIDList():
                done = True
                reward = -self.P_base
                break
                
            pos = traci.vehicle.getPosition(self.target_vehicle)
            nearest_rsu, dist = self._find_nearest_rsu(pos)
            
            if dist <= self.rsu_radius:
                if nearest_rsu != self.current_rsu and self.next_rsu is None:
                    self.next_rsu = nearest_rsu
                active_rsu = nearest_rsu
                
                if not is_download_complete:
                    if active_rsu == self.current_rsu:
                        self.remained_content_size -= self.c_step
                    elif active_rsu == self.next_rsu:
                        if discrete_action == 1:
                            self.remained_content_size -= self.c_step
                            c_next_downloaded += self.c_step
                            
                    if self.remained_content_size <= 0:
                        is_download_complete = True
                        completed_in_rsu = active_rsu
                        access_delay = current_time - self.request_start_time
                        
                        if discrete_action == 0 and completed_in_rsu == self.next_rsu:
                            done = True
                            W_curr = 0
                            c_missed = abs(self.remained_content_size) + self.c_step
                            if self.ablation_mode:
                                reward = -self.P_base
                            else:
                                reward = -self.P_base - self.delta * (c_missed / self.total_content_size)
                            break
                else:
                    if active_rsu == self.current_rsu and completed_in_rsu == self.current_rsu:
                        N_rem += 1
            else:
                if is_download_complete:
                    if completed_in_rsu == self.current_rsu:
                        W_curr = N_rem * self.c_step
                        if discrete_action == 1:
                            reward = -self.P_base if self.ablation_mode else -self.P_base - self.beta * (W_curr / self.total_content_size)
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

        state = self._get_state() if not done else np.zeros(6, dtype=np.float32)
        
        # 다운로드를 완료하지 못하고 중단된 경우의 Delay는 현 시점까지의 시간으로 기록
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
