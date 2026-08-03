import sys
import os
import time
import math
import numpy as np
from typing import List, Dict, Tuple

sys.path.append(os.path.abspath("/home/imnyj/Command/core"))
from lock_manager import LockManager
from audit_logger import AuditLogger

from environment import UAMEnvironment
from models import EVTOLVehicle, VehicleState, RoutePlanner, Building

class UAMSimulator:
    def __init__(self, seed: int = 42):
        self.env = UAMEnvironment(width=None, height=None, seed=seed)
        self.env.generate_buildings(num_buildings=30, seed=seed)
        self.vertiports = self.env.generate_vertiports(num_vertiports=4, seed=seed)
        
        self.vehicles: List[EVTOLVehicle] = []
        
        # Centralized vertiport occupancy scheduling
        # map vertiport_id -> list of (start_time, end_time)
        self.vertiport_reservations = {vp.id: [] for vp in self.vertiports}
        self.vertiport_capacities = {vp.id: vp.capacity for vp in self.vertiports}
        
        # Scheduled trajectories for V2V collision avoidance
        # List of dicts with pre-calculated 4D trajectories (t, x, y, z)
        self.scheduled_trajectories = []
        
        self.audit_logger = AuditLogger("/home/imnyj/Workspace/paper5/sim_audit.log")
        self.lock_manager = LockManager("/tmp/uam_locks", "/tmp/uam_backups")
        
        self.current_time = 0.0
        self.dt = 1.0

    def reserve_vertiport(self, vp_id: str, t_start: float, t_end: float) -> bool:
        capacity = self.vertiport_capacities[vp_id]
        reservations = self.vertiport_reservations[vp_id]
        
        overlap_count = 0
        for (rs, re) in reservations:
            if not (t_end <= rs or t_start >= re):
                overlap_count += 1
                
        if overlap_count < capacity:
            reservations.append((t_start, t_end))
            return True
        return False

    def predict_trajectory(self, waypoints: np.ndarray, start_time: float, speed: float) -> List[Tuple[float, np.ndarray]]:
        # Simplified prediction based on average speed
        traj = []
        t = start_time
        pos = np.array(waypoints[0])
        traj.append((t, pos))
        
        for i in range(1, len(waypoints)):
            wp_prev = np.array(waypoints[i-1])
            wp_next = np.array(waypoints[i])
            dist = np.linalg.norm(wp_next - wp_prev)
            dt = dist / speed if speed > 0 else 0
            
            # Sub-sample every 5 seconds for collision check
            steps = max(1, int(dt / 5.0))
            for s in range(1, steps + 1):
                fraction = s / steps
                interp_pos = wp_prev + (wp_next - wp_prev) * fraction
                interp_t = t + dt * fraction
                traj.append((interp_t, interp_pos))
                
            t += dt
        return traj

    def check_v2v_collision(self, traj: List[Tuple[float, np.ndarray]], min_dist: float = 50.0) -> bool:
        for scheduled_traj in self.scheduled_trajectories:
            for t1, pos1 in traj:
                # Find closest point in time in scheduled_traj
                for t2, pos2 in scheduled_traj:
                    if abs(t1 - t2) < 2.5: # 5 sec interval / 2
                        dist = np.linalg.norm(pos1 - pos2)
                        if dist < min_dist:
                            return True
        return False

    def schedule_vehicle(self, v_id: str, start_vp: str, end_vp: str, base_start_time: float, base_altitude: float):
        start_pos = self.env.vertiports[start_vp].position
        end_pos = self.env.vertiports[end_vp].position
        
        planner = RoutePlanner()
        
        # Try scheduling with modifications if collisions detected
        max_attempts = 5
        current_start_time = base_start_time
        current_altitude = base_altitude
        
        model_buildings = [Building(building_id=b.id, x_min=b.x_min, x_max=b.x_max, y_min=b.y_min, y_max=b.y_max, height=b.height) for b in self.env.buildings]
        
        for attempt in range(max_attempts):
            waypoints = planner.plan_3d_route(start_pos, end_pos, buildings=model_buildings, cruise_altitude=current_altitude)
            
            # Rough flight time estimate
            total_dist = 0.0
            for i in range(1, len(waypoints)):
                total_dist += np.linalg.norm(np.array(waypoints[i]) - np.array(waypoints[i-1]))
            est_flight_time = total_dist / 30.0 # roughly 30m/s
            
            # Check vertiport availability
            if not self.reserve_vertiport(start_vp, current_start_time, current_start_time + 60.0):
                current_start_time += 60.0 # Delay departure
                continue
                
            if not self.reserve_vertiport(end_vp, current_start_time + est_flight_time, current_start_time + est_flight_time + 60.0):
                current_start_time += 60.0 # Delay departure
                continue
                
            # Check V2V collisions
            traj = self.predict_trajectory(waypoints, current_start_time, speed=30.0)
            if self.check_v2v_collision(traj):
                if attempt % 2 == 0:
                    current_altitude += 50.0 # change altitude
                else:
                    current_start_time += 30.0 # delay time
                continue
                
            # Successfully scheduled
            self.scheduled_trajectories.append(traj)
            
            vehicle = EVTOLVehicle(vehicle_id=v_id)
            vehicle.position = np.array(start_pos, dtype=float)
            vehicle.set_route(waypoints)
            # Store start time in vehicle object as a custom attribute
            vehicle.scheduled_start_time = current_start_time
            self.vehicles.append(vehicle)
            
            self.audit_logger.log_action("sim_manager", "SCHEDULE", v_id, f"Scheduled from {start_vp} to {end_vp} at t={current_start_time}, alt={current_altitude}", None)
            print(f"[{v_id}] Scheduled successfully: start={current_start_time}s, altitude={current_altitude}m")
            return True
            
        print(f"[{v_id}] Failed to schedule after {max_attempts} attempts.")
        return False

    def run(self, max_time: float = 600.0):
        print("Starting Simulation...")
        with open("/home/imnyj/Workspace/paper5/sim_results.log", "w") as f:
            f.write("Time,VehicleID,X,Y,Z,State\n")
            
        while self.current_time < max_time:
            active_vehicles = 0
            
            for vehicle in self.vehicles:
                if self.current_time >= vehicle.scheduled_start_time:
                    if vehicle.state != VehicleState.ARRIVED:
                        active_vehicles += 1
                        vehicle.update(self.dt)
                        
                        # Log results
                        with open("/home/imnyj/Workspace/paper5/sim_results.log", "a") as f:
                            pos = vehicle.position
                            f.write(f"{self.current_time},{vehicle.vehicle_id},{pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f},{vehicle.state.value}\n")
                            
            if active_vehicles == 0 and self.current_time > max_time/2:
                # All vehicles arrived
                print(f"All vehicles arrived at time {self.current_time}.")
                break
                
            self.current_time += self.dt

if __name__ == "__main__":
    sim = UAMSimulator()
    
    vp_ids = list(sim.env.vertiports.keys())
    
    lm = LockManager("/tmp/uam_locks", "/tmp/uam_backups")
    if lm.acquire("/home/imnyj/Workspace/paper5/main_sim.py", "sim_manager", timeout=10):
        try:
            # Schedule multiple vehicles
            sim.schedule_vehicle("V1", vp_ids[0], vp_ids[1], base_start_time=0.0, base_altitude=150.0)
            sim.schedule_vehicle("V2", vp_ids[0], vp_ids[1], base_start_time=10.0, base_altitude=150.0)
            sim.schedule_vehicle("V3", vp_ids[2], vp_ids[3], base_start_time=0.0, base_altitude=200.0)
            sim.schedule_vehicle("V4", vp_ids[1], vp_ids[0], base_start_time=0.0, base_altitude=150.0)
            
            sim.run(max_time=1000.0)
            print("Simulation finished. Results saved to sim_results.log")
        finally:
            lm.release("/home/imnyj/Workspace/paper5/main_sim.py", "sim_manager")
    else:
        print("Could not acquire lock for simulation.")
