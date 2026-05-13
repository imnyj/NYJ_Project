---
name: libsumo-simulation
description: Use when implementing traffic or V2X communication simulations with libsumo/TraCI. Covers SUMO setup, step-by-step simulation loop, vehicle/route injection, traffic light control, and data extraction patterns. Load this before writing any .py file that imports libsumo or traci.
---

# libsumo Simulation Skill

## When to load
Invoke this skill when the Experimenter (ENGINEER mode) is about to write code that:
- `import libsumo` or `import traci`
- Creates or runs a SUMO `.sumocfg` / `.net.xml` / `.rou.xml`
- Extracts metrics like throughput, queue length, CO2, or delay from SUMO
- Implements V2X message exchange on top of SUMO's communication layer

## Setup checklist (WSL2 / Ubuntu)

```bash
sudo apt install sumo sumo-tools sumo-doc
export SUMO_HOME=/usr/share/sumo
# libsumo ships with the SUMO package, no pip install needed for core
# For pip fallback: pip install eclipse-sumo traci
```

Verify:
```python
import libsumo
print(libsumo.__file__)  # should resolve
```

## Canonical simulation loop

```python
import libsumo

def run_simulation(sumocfg_path: str, duration: int, seed: int = 42) -> dict:
    """Run a single SUMO scenario and return per-step metrics."""
    libsumo.start([
        "sumo", "-c", sumocfg_path,
        "--seed", str(seed),
        "--no-step-log", "true",
        "--no-warnings", "true",
        "--duration-log.disable", "true",
    ])
    try:
        results = {"step": [], "n_vehicles": [], "mean_speed": [],
                   "total_waiting": [], "co2": []}
        while libsumo.simulation.getTime() < duration:
            libsumo.simulationStep()
            veh_ids = libsumo.vehicle.getIDList()
            if veh_ids:
                speeds = [libsumo.vehicle.getSpeed(v) for v in veh_ids]
                waits = [libsumo.vehicle.getWaitingTime(v) for v in veh_ids]
                co2 = [libsumo.vehicle.getCO2Emission(v) for v in veh_ids]
                mean_speed = sum(speeds) / len(speeds)
                total_wait = sum(waits)
                total_co2 = sum(co2)
            else:
                mean_speed = total_wait = total_co2 = 0.0
            results["step"].append(libsumo.simulation.getTime())
            results["n_vehicles"].append(len(veh_ids))
            results["mean_speed"].append(mean_speed)
            results["total_waiting"].append(total_wait)
            results["co2"].append(total_co2)
        return results
    finally:
        libsumo.close()
```

## Why libsumo vs traci

- **libsumo**: direct Python bindings, ~10–50× faster than TraCI, but single-process only.
- **traci**: TCP-based, slower but supports remote/multi-client scenarios.

**Default to libsumo unless multi-client/debugging is required.**

## Common pitfalls

1. **`libsumo.start()` without `"sumo"` first arg** → raises obscure error. Always pass `"sumo"` (or `"sumo-gui"`) as position 0 of the list.
2. **Missing `libsumo.close()`** → leaks simulation state, next test will start poisoned. Use `try/finally`.
3. **Calling TraCI after libsumo.close()** → undefined behavior. Start a fresh process for each scenario.
4. **Seeding**: SUMO uses `--seed` for routes; for Python-side RNG (e.g. V2X packet drops), seed `random` and `numpy.random` separately.
5. **Unit confusion**: SUMO speeds are **m/s**, not km/h. Multiply by 3.6 before reporting.

## V2X communication layer pattern

SUMO does not simulate wireless natively. Layer your own on top:

```python
class V2XChannel:
    def __init__(self, p_loss: float, max_range_m: float):
        self.p_loss = p_loss
        self.max_range = max_range_m

    def can_deliver(self, tx_id: str, rx_id: str) -> bool:
        tx = libsumo.vehicle.getPosition(tx_id)
        rx = libsumo.vehicle.getPosition(rx_id)
        d = ((tx[0]-rx[0])**2 + (tx[1]-rx[1])**2) ** 0.5
        if d > self.max_range:
            return False
        import random
        return random.random() > self.p_loss
```

## Output format for downstream

Save as `.npz` so Visualization and Reviewer can load without re-running:

```python
import numpy as np
np.savez_compressed(
    "output/code/sim_results.npz",
    **{k: np.array(v) for k, v in results.items()},
    # metadata
    _seed=np.array(seed),
    _duration=np.array(duration),
    _scenario=np.array(sumocfg_path, dtype=object),
)
```
