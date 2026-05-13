---
name: traffic-metrics
description: Use when defining or computing traffic/V2X performance metrics — throughput, queue length, delay, travel time, CO2 emissions, packet delivery ratio, latency. Provides correct formulas, units, and edge-case handling. Load this before writing metric code or when Reviewer checks metric correctness.
---

# Traffic Metrics Skill

## When to load
- Experimenter (DESIGNER mode) defining evaluation metrics in `experiment_spec.yaml`
- Experimenter (ENGINEER mode) computing metrics from `sim_results.npz`
- Reviewer (QA mode) verifying that reported metrics match their formal definitions

## Core traffic metrics

### Throughput (veh/h)
```
q = N_completed / T_observation_hours
```
- `N_completed`: vehicles that passed a detector / arrived at destination
- Common mistake: using `getIDList()` length as throughput (that's **density**, not flow)

### Density (veh/km)
```
k = N_on_link / link_length_km
```
Report as spot density from `getLastStepVehicleNumber()` / link length.

### Mean speed (km/h)
```
v̄ = (Σ v_i) / N       where v_i from libsumo in m/s
v̄_kmh = v̄ * 3.6
```
**Trap**: SUMO returns m/s. Always convert.

### Total travel time (s)
```
TTT = Σ (arrival_time - depart_time)     over all completed vehicles
```
Only count **completed** trips — vehicles still in the network skew the number.

### Waiting time (s)
SUMO `getWaitingTime()` accumulates time with speed < 0.1 m/s. Sum per vehicle, then average.

### Queue length (veh)
Use detectors:
```python
q_len = libsumo.lanearea.getJamLengthVehicle(detector_id)
```
Or count vehicles with `speed < threshold` on the link.

### CO2 emission (mg/s per vehicle, then aggregate)
```
E_total = Σ_t Σ_veh libsumo.vehicle.getCO2Emission(v)
```
Units: mg over the time step. Multiply by `deltaT` if you want per-second totals.

## V2X communication metrics

### Packet Delivery Ratio (PDR)
```
PDR = N_received / N_transmitted
```
- Must be tracked per-(sender, receiver) pair, then averaged.
- **Fairness check** (Reviewer's job): if PDR is averaged globally, vehicles that transmit more dominate. Use unweighted mean across pairs.

### End-to-end latency (ms)
```
L = t_received - t_transmitted
```
- Only report latency for packets that actually arrived.
- Separate mean, median, 95th percentile, and max. **A single number is misleading.**

### Channel Busy Ratio (CBR)
```
CBR = T_channel_busy / T_measurement_window
```
Typically computed in 100 ms windows per ETSI ITS-G5.

### Information Age / Age of Information (AoI)
```
AoI(t) = t - t_last_successful_update
```
Track per receiver. For safety-critical V2X, **peak AoI** matters more than mean.

## Fairness-aware aggregation

A frequent Reviewer complaint: "Your proposed scheme wins on average but loses on the 10th percentile." Always report:

1. Mean
2. Median
3. 10th and 90th percentile
4. Standard deviation
5. (For comparing schemes) 95 % confidence interval over random seeds

```python
import numpy as np

def summarize(values: np.ndarray) -> dict:
    return {
        "mean":   float(np.mean(values)),
        "median": float(np.median(values)),
        "p10":    float(np.percentile(values, 10)),
        "p90":    float(np.percentile(values, 90)),
        "std":    float(np.std(values, ddof=1)),
        "n":      int(values.size),
    }
```

## Common unit pitfalls (Reviewer checklist)

| Quantity | Correct unit | Frequent error |
|---|---|---|
| Speed | km/h (reported), m/s (raw) | Mixing them in one figure |
| Density | veh/km | Per-lane vs total lanes |
| Flow | veh/h | Per-lane vs total |
| CO2 | g (over scenario) or mg/s (rate) | Treating mg as g |
| Latency | ms | s vs ms swap |
| Range | m | Confusing with "distance traveled" |

## Multiple-seed statistical reporting

Never report a single run. Minimum 5 seeds; 10+ preferred. Report:

```
Metric: mean ± 95% CI (n = 10 seeds)
```

Use `scipy.stats.t.interval` for small-sample CI. See `statistical-tests` skill.
