import os

filepath = "/home/imnyj/papers/paper4/sim/sim_engine.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Update simulate_receptions signature
content = content.replace(
"""def simulate_receptions(cam_events: list,
                        vehicle_positions: Dict[str, Tuple[float, float]],
                        cbr: float,
                        rng: random.Random) -> List[Dict]:""",
"""def simulate_receptions(cam_events: list,
                        vehicle_positions: Dict[str, Tuple[float, float]],
                        cbr: float,
                        rng: random.Random,
                        dist_tx_counts: list,
                        dist_rx_counts: list) -> List[Dict]:"""
)

# 2. Update simulate_receptions logic
old_logic = """            if dist_m > COMM_RANGE_M * 2:  # Skip far-away vehicles
                continue

            # Adjust reception probability for channel load (collisions)
            p_rx = reception_probability(dist_m, p_tx_dbm)
            # Channel collision reduction due to CBR
            collision_factor = max(0.0, 1.0 - cbr * 0.5)
            p_rx *= collision_factor

            if rng.random() < p_rx:"""

new_logic = """            if dist_m > COMM_RANGE_M:  # Only track up to COMM_RANGE_M for PDR
                continue
                
            bucket_idx = int(dist_m // 50)
            if bucket_idx >= 6:
                bucket_idx = 5
            dist_tx_counts[bucket_idx] += 1

            # Adjust reception probability for channel load (collisions)
            p_rx = reception_probability(dist_m, p_tx_dbm)
            # Channel collision reduction due to CBR
            collision_factor = max(0.0, 1.0 - cbr * 0.5)
            p_rx *= collision_factor

            if rng.random() < p_rx:
                dist_rx_counts[bucket_idx] += 1"""

content = content.replace(old_logic, new_logic)

# 3. Update run() method signature to initialize arrays
old_run = """        aoi_history = []
        cbr_history = []
        
        t_start = time.time()"""
new_run = """        aoi_history = []
        cbr_history = []
        dist_tx_counts = [0]*6
        dist_rx_counts = [0]*6
        
        t_start = time.time()"""
content = content.replace(old_run, new_run)

# 4. Update simulate_receptions call
old_call = """                # Simulate receptions
                reception_evs = simulate_receptions(
                    cam_events, vehicle_positions, cbr, rng
                )"""
new_call = """                # Simulate receptions
                reception_evs = simulate_receptions(
                    cam_events, vehicle_positions, cbr, rng,
                    dist_tx_counts, dist_rx_counts
                )"""
content = content.replace(old_call, new_call)

# 5. Update return dict
old_return = """        return {
            "AoI_mean": round(aoi_mean, 3),
            "CBR_mean": round(cbr_mean, 4),
            "PDR_mean": round(pdr_mean, 2),
            "energy_efficiency": round(energy_eff, 4),
            "ETSI_compliance": round(etsi_comp, 2),
            "runtime_sec": round(runtime_sec, 2),
            "n_cam_events": len(cam_layer.cam_events),
        }"""
new_return = """        distance_pdr = []
        for b in range(6):
            if dist_tx_counts[b] > 0:
                distance_pdr.append(dist_rx_counts[b] / dist_tx_counts[b] * 100.0)
            else:
                distance_pdr.append(0.0)
                
        return {
            "AoI_mean": round(aoi_mean, 3),
            "CBR_mean": round(cbr_mean, 4),
            "PDR_mean": round(pdr_mean, 2),
            "energy_efficiency": round(energy_eff, 4),
            "ETSI_compliance": round(etsi_comp, 2),
            "runtime_sec": round(runtime_sec, 2),
            "n_cam_events": len(cam_layer.cam_events),
            "cbr_history": cbr_history,
            "distance_pdr": distance_pdr,
        }"""
content = content.replace(old_return, new_return)

with open(filepath, "w") as f:
    f.write(content)
print("sim_engine.py patched successfully.")
