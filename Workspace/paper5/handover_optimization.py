
import numpy as np
import optuna
import os
import sys

sys.path.append(os.path.abspath("/home/imnyj/Command/core"))
from lock_manager import LockManager
from audit_logger import AuditLogger

from environment import UAMEnvironment
from models import EVTOLVehicle, VehicleState, RoutePlanner, Building, CommunicationEnvironment
from main_sim import UAMSimulator

class ProactiveHandoverManager:
    def __init__(self, comm_env, lookahead_time=5.0, hysteresis_db=3.0, pref_weights=None):
        self.comm_env = comm_env
        self.lookahead_time = lookahead_time
        self.hysteresis_db = hysteresis_db
        self.pref_weights = pref_weights or {"data_rate": 0.5, "latency": 0.3, "snr": 0.2}

    def predict_position(self, vehicle: EVTOLVehicle) -> tuple:
        if np.linalg.norm(vehicle.velocity) < 0.1:
            return tuple(vehicle.position)
        future_pos = vehicle.position + vehicle.velocity * self.lookahead_time
        return tuple(future_pos)

    def evaluate_proactive_handover(self, vehicle: EVTOLVehicle, current_time: float) -> dict:
        future_pos = self.predict_position(vehicle)
        best_link = self.comm_env.find_best_connection(future_pos, self.pref_weights)

        if not best_link:
            return None

        current_node_id = vehicle.connected_node_id

        if current_node_id is None:
            vehicle.connected_node_id = best_link["node_id"]
            vehicle.connected_comm_type = best_link["node_type"]
            record = {
                "timestamp": current_time,
                "event": "INITIAL_CONNECT",
                "target_node": best_link["node_id"],
                "comm_type": best_link["node_type"],
                "metrics": best_link
            }
            vehicle.handover_history.append(record)
            return record

        if current_node_id != best_link["node_id"]:
            curr_node = self.comm_env.nodes.get(current_node_id)
            if curr_node:
                is_los = self.comm_env.check_line_of_sight(future_pos, tuple(curr_node.position))
                curr_metrics = curr_node.calculate_link_quality(future_pos, is_los=is_los)

                if not curr_metrics["in_range"] or (best_link["snr_db"] > curr_metrics["snr_db"] + self.hysteresis_db):
                    old_node = current_node_id
                    vehicle.connected_node_id = best_link["node_id"]
                    vehicle.connected_comm_type = best_link["node_type"]

                    record = {
                        "timestamp": current_time,
                        "event": "HANDOVER",
                        "from_node": old_node,
                        "to_node": best_link["node_id"],
                        "comm_type": best_link["node_type"],
                        "metrics": best_link
                    }
                    vehicle.handover_history.append(record)
                    return record
        return None

def objective(trial):
    lookahead_time = trial.suggest_float('lookahead_time', 1.0, 15.0)
    hysteresis_db = trial.suggest_float('hysteresis_db', 1.0, 10.0)
    w_data_rate = trial.suggest_float('w_data_rate', 0.1, 1.0)
    w_latency = trial.suggest_float('w_latency', 0.1, 1.0)
    w_snr = trial.suggest_float('w_snr', 0.1, 1.0)
    
    # Normalize weights
    total_w = w_data_rate + w_latency + w_snr
    pref_weights = {
        "data_rate": w_data_rate / total_w,
        "latency": w_latency / total_w,
        "snr": w_snr / total_w
    }

    sim = UAMSimulator(seed=42)
    model_buildings = [Building(building_id=b.id, x_min=b.x_min, x_max=b.x_max, y_min=b.y_min, y_max=b.y_max, height=b.height) for b in sim.env.buildings]
    comm_env = CommunicationEnvironment(buildings=model_buildings)
    for bs in sim.env.cellular_stations:
        # Dummy conversion to Cellular5G format expected in models.py
        from models import Cellular5G, RSU, Starlink
        node = Cellular5G(node_id=bs.id, position=bs.position)
        comm_env.add_node(node)
    for int_id, inter in sim.env.intersections.items():
        node = RSU(node_id=inter.rsu.id, position=inter.rsu.position)
        comm_env.add_node(node)
    
    starlink_node = Starlink(node_id="Starlink_1")
    comm_env.add_node(starlink_node)

    ho_manager = ProactiveHandoverManager(comm_env, lookahead_time, hysteresis_db, pref_weights)

    vp_ids = list(sim.env.vertiports.keys())
    sim.schedule_vehicle("V1", vp_ids[0], vp_ids[1], base_start_time=0.0, base_altitude=150.0)
    sim.schedule_vehicle("V2", vp_ids[2], vp_ids[3], base_start_time=10.0, base_altitude=200.0)

    total_handovers = 0
    total_latency = 0.0
    telemetry_count = 0

    while sim.current_time < 300.0:
        active = 0
        for v in sim.vehicles:
            if sim.current_time >= v.scheduled_start_time and v.state != VehicleState.ARRIVED:
                active += 1
                v.update(sim.dt)
                ho_record = ho_manager.evaluate_proactive_handover(v, sim.current_time)
                if ho_record and ho_record['event'] == 'HANDOVER':
                    total_handovers += 1
                
                # accumulate latency for penalty
                if v.connected_node_id:
                    curr_node = comm_env.nodes.get(v.connected_node_id)
                    if curr_node:
                        is_los = comm_env.check_line_of_sight(tuple(v.position), tuple(curr_node.position))
                        metrics = curr_node.calculate_link_quality(tuple(v.position), is_los=is_los)
                        total_latency += metrics['latency_ms']
                        telemetry_count += 1
        
        if active == 0 and sim.current_time > 150.0:
            break
        sim.current_time += sim.dt

    avg_latency = total_latency / max(1, telemetry_count)
    # Objective: minimize (avg_latency + penalty for too many handovers)
    score = avg_latency + (total_handovers * 5.0) 
    return score

def run_optimization():
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=15)
    
    print('Best trial:')
    print(f'  Value: {study.best_trial.value}')
    print(f'  Params:')
    for key, value in study.best_trial.params.items():
        print(f'    {key}: {value}')
        
    return study.best_trial.params

if __name__ == '__main__':
    lm = LockManager("/tmp/uam_locks", "/tmp/uam_backups")
    if lm.acquire(__file__, "optuna_agent", timeout=10):
        try:
            print("Running Optuna optimization...")
            best_params = run_optimization()
            
            with open("/home/imnyj/Workspace/paper5/optuna_results.txt", "w") as f:
                f.write(str(best_params))
        finally:
            lm.release(__file__, "optuna_agent")
