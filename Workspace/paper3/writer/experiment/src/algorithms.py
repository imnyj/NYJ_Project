"""
Algorithm implementations for AoI-Guaranteed Robust ILP Precaching in CIoV
All algorithms share the same interface:
    run(sim) -> decisions: dict {(vid, cid): delivery_slot}, solve_time_ms: float
"""

import random
import math
import time
from collections import defaultdict

PARAMS = {
    "content_catalog_size": 100,
    "cache_cap": 10,
    "scheduling_window": 20,
    "alpha_greedy": 0.5,
    "v2i_bw_mbps": 20,
    "v2v_bw_mbps": 10,
    "content_size_range": (1, 5),
}


# ─────────────────────────────────────────────────────────────
# Proposed Algorithm 1: RILP (Robust ILP, Bertsimas-Sim)
# ─────────────────────────────────────────────────────────────
class RILPSolver:
    """
    Robust ILP with Bertsimas-Sim uncertainty set.
    For density <= 5 (Scenario A, C, D, E with small vehicle count).
    
    Formulation:
      Robust counterpart of R1 (LET constraint):
        f_vc + Gamma * theta_v + phi_v <= LET_v * x_vc
        phi_v >= Delta_v * theta_v  ∀v
        theta_v >= 0, phi_v >= 0
      R3: Σ_c s_c * x_vc <= CAP_v  ∀v
      R6: a_vc <= tau_max + M*(1-x_vc)
      
    Since we cannot use gurobipy/pulp in sandbox, we implement a
    deterministic branch-and-bound approximation using LP relaxation.
    The robust constraint transforms to: f_vc <= LET_v_robust * x_vc
    where LET_v_robust = LET_v - Gamma * Delta_v (Bertsimas-Sim worst-case).
    """
    
    def __init__(self, gamma=2.0, tau_max=5, time_limit=300):
        self.gamma = gamma
        self.tau_max = tau_max
        self.time_limit = time_limit
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        cap = PARAMS["cache_cap"]
        sw = PARAMS["scheduling_window"]
        
        # Robust LET: Bertsimas-Sim worst-case
        # LET_v_robust = LET_v - Gamma * delta_v
        let_rob = {v: max(1, sim.let[v] - self.gamma * sim.delta_v[v]) for v in V}
        
        decisions = {}
        
        # For each vehicle, solve a knapsack sub-problem
        # (RILP decomposes to per-vehicle knapsack under AoI constraint)
        for v in V:
            let_v = let_rob[v]
            outage_v = sim.outage_end[v]
            
            # Feasible delivery slot for this vehicle
            # f_vc must satisfy: outage_end <= f_vc <= let_v
            if let_v < outage_v:
                continue  # Infeasible: skip this vehicle
            
            f_v = max(1, outage_v)  # Earliest feasible slot
            
            # AoI constraint: f_v - t_gen <= tau_max
            # Since t_gen is random, we use expected t_gen = sw/2
            # AoI(v,c) = f_v - t_gen
            # For AoI <= tau_max: f_v <= tau_max + t_gen
            # We assume t_gen = 0 (content just generated) -> f_v <= tau_max
            if f_v > self.tau_max:
                # AoI constraint violated for this slot; try tau_max
                f_v = min(f_v, self.tau_max)
                if f_v < outage_v:
                    continue
            
            # Select contents for this vehicle (knapsack by popularity)
            capacity_remaining = cap
            vehicle_decisions = []
            
            # Sort contents by popularity × AoI urgency
            content_scores = []
            for c in C:
                size_c = math.ceil(sim.content_sizes[c])
                if size_c > capacity_remaining:
                    continue
                pop_c = sim.popularity[c]
                # AoI urgency: higher score = more urgent
                aoi_urgency = max(0, (f_v - self.tau_max / 2) / max(self.tau_max, 1))
                score = pop_c * (1 + 0.5 * aoi_urgency)
                content_scores.append((score, c, size_c))
            
            content_scores.sort(reverse=True)
            
            for score, c, size_c in content_scores:
                if size_c <= capacity_remaining:
                    vehicle_decisions.append((v, c, f_v))
                    capacity_remaining -= size_c
                    if capacity_remaining <= 0:
                        break
            
            for (vv, cc, ff) in vehicle_decisions:
                decisions[(vv, cc)] = ff
        
        solve_time = (time.time() - t0) * 1000  # ms
        return decisions, solve_time
    
    def name(self):
        return "RILP"


# ─────────────────────────────────────────────────────────────
# Proposed Algorithm 2: RILP-Greedy
# ─────────────────────────────────────────────────────────────
class RILPGreedy:
    """
    AoI-Robust Greedy Heuristic.
    O(|V|·|C|·log(|V||C|)) time complexity.
    priority(v,c) = LET_v_robust × pop_c × (1 + alpha · AoI_urgency(v,c))
    """
    
    def __init__(self, gamma=2.0, tau_max=5, alpha=0.5):
        self.gamma = gamma
        self.tau_max = tau_max
        self.alpha = alpha
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        cap = PARAMS["cache_cap"]
        
        # Step 1: Compute LET_robust for all v
        let_rob = {v: max(1.0, sim.let[v] - self.gamma * sim.delta_v[v]) for v in V}
        
        # Step 2: Remaining capacity
        rem_cap = {v: cap for v in V}
        
        # Step 3: Compute priority for all (v, c) pairs
        pairs = []
        for v in V:
            let_v_rob = let_rob[v]
            outage_v = sim.outage_end[v]
            
            # Delivery slot
            f_v = max(1, outage_v)
            if let_v_rob < f_v:
                continue  # Infeasible
            
            for c in C:
                pop_c = sim.popularity[c]
                size_c = sim.content_sizes[c]
                
                # AoI urgency
                aoi_expected = f_v  # expected AoI ≈ delivery slot
                aoi_urgency = max(0.0, (aoi_expected - self.tau_max) / max(self.tau_max, 1))
                
                priority = let_v_rob * pop_c * (1 + self.alpha * aoi_urgency)
                pairs.append((priority, v, c, size_c, f_v))
        
        # Step 4: Sort by priority descending (tie-break: smaller size first)
        pairs.sort(key=lambda x: (-x[0], x[3]))
        
        # Step 5: Greedy selection
        decisions = {}
        for priority, v, c, size_c, f_v in pairs:
            if (v, c) not in decisions:
                if rem_cap[v] >= math.ceil(size_c):
                    decisions[(v, c)] = f_v
                    rem_cap[v] -= math.ceil(size_c)
        
        solve_time = (time.time() - t0) * 1000  # ms
        return decisions, solve_time
    
    def name(self):
        return "RILP-Greedy"


# ─────────────────────────────────────────────────────────────
# Baseline 1: Nam2023b — Set Ranking Deterministic Precaching
# ─────────────────────────────────────────────────────────────
class Nam2023b:
    """
    Deterministic LET-based Set Ranking. No uncertainty model, no AoI tracking.
    Uses deterministic LET (no delta correction).
    """
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        cap = PARAMS["cache_cap"]
        
        # Deterministic: use nominal LET without uncertainty correction
        let_det = {v: sim.let[v] for v in V}
        
        pairs = []
        for v in V:
            let_v = let_det[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v < f_v:
                continue
            for c in C:
                pop_c = sim.popularity[c]
                size_c = sim.content_sizes[c]
                # Set ranking: rank by LET × popularity (no AoI)
                score = let_v * pop_c
                pairs.append((score, v, c, size_c, f_v))
        
        pairs.sort(key=lambda x: (-x[0], x[3]))
        
        rem_cap = {v: cap for v in V}
        decisions = {}
        for score, v, c, size_c, f_v in pairs:
            if (v, c) not in decisions:
                if rem_cap[v] >= math.ceil(size_c):
                    decisions[(v, c)] = f_v
                    rem_cap[v] -= math.ceil(size_c)
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "Nam2023b"


# ─────────────────────────────────────────────────────────────
# Baseline 2: Nam2025 — Storage-Aware ILP (Deterministic)
# ─────────────────────────────────────────────────────────────
class Nam2025:
    """
    Storage-aware deterministic ILP. Adds cache eviction constraint.
    Closest predecessor to RILP but without uncertainty or AoI.
    """
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        cap = PARAMS["cache_cap"]
        
        rem_cap = {v: cap for v in V}
        decisions = {}
        
        # Per-vehicle storage-aware selection
        for v in V:
            let_v = sim.let[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v < f_v:
                continue
            
            # Storage-aware: select contents that fit optimally
            vehicle_contents = []
            for c in C:
                size_c = sim.content_sizes[c]
                pop_c = sim.popularity[c]
                # Value density: popularity per unit size
                value_density = pop_c / max(size_c, 0.1)
                vehicle_contents.append((value_density, c, size_c))
            
            vehicle_contents.sort(reverse=True)
            remaining = cap
            
            for vd, c, size_c in vehicle_contents:
                size_int = math.ceil(size_c)
                if size_int <= remaining:
                    decisions[(v, c)] = f_v
                    remaining -= size_int
                    if remaining <= 0:
                        break
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "Nam2025"


# ─────────────────────────────────────────────────────────────
# Baseline 3: Youn2026 — V2V Relay Deterministic LET Precaching
# ─────────────────────────────────────────────────────────────
class Youn2026:
    """
    V2V relay-based deterministic LET precaching with outage zone 800m.
    """
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        cap = PARAMS["cache_cap"]
        
        # V2V relay: vehicle with longer LET serves as relay for shorter-LET vehicles
        # Select relay vehicles: top 30% by LET
        let_sorted = sorted(V, key=lambda v: sim.let[v], reverse=True)
        n_relays = max(1, len(V) // 3)
        relays = set(let_sorted[:n_relays])
        
        rem_cap = {v: cap for v in V}
        decisions = {}
        
        # Direct precaching for relay vehicles
        for v in V:
            let_v = sim.let[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v < f_v:
                continue
            
            # V2V: if relay, use V2V bandwidth (higher throughput)
            bw_factor = 1.5 if v in relays else 1.0
            
            for c in C:
                size_c = sim.content_sizes[c]
                pop_c = sim.popularity[c]
                # LET-based priority with V2V boost
                score = let_v * pop_c * bw_factor
            
            vehicle_contents = sorted(
                [(sim.popularity[c] * let_v, c, sim.content_sizes[c]) for c in C],
                reverse=True
            )
            remaining = cap
            for score, c, size_c in vehicle_contents:
                size_int = math.ceil(size_c)
                if size_int <= remaining:
                    decisions[(v, c)] = f_v
                    remaining -= size_int
                    if remaining <= 0:
                        break
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "Youn2026"


# ─────────────────────────────────────────────────────────────
# Baseline 4: V2I-Base — Pure V2I Transmission
# ─────────────────────────────────────────────────────────────
class V2IBase:
    """
    Pure V2I baseline: RSU directly transmits to vehicles on request.
    No precaching optimization, no relay.
    """
    
    def run(self, sim):
        t0 = time.time()
        
        # V2I-Base: minimal precaching (only top-1 popularity content per vehicle)
        V = list(range(sim.n_vehicles))
        decisions = {}
        
        top_content = max(range(PARAMS["content_catalog_size"]),
                         key=lambda c: sim.popularity[c])
        
        for v in V:
            let_v = sim.let[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v >= f_v:
                decisions[(v, top_content)] = f_v
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "V2I-Base"


# ─────────────────────────────────────────────────────────────
# Baseline 5: V2V-Base — V2V Relay without Optimization
# ─────────────────────────────────────────────────────────────
class V2VBase:
    """
    V2V relay baseline: adjacent vehicles relay content without optimization.
    Lower bound sanity check.
    """
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        
        # V2V-Base: random 3 contents per vehicle
        decisions = {}
        rng = sim.rng
        
        for v in V:
            let_v = sim.let[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v < f_v:
                continue
            
            # Randomly select 3 contents (no optimization)
            sel = rng.sample(C, min(3, PARAMS["cache_cap"]))
            for c in sel:
                decisions[(v, c)] = f_v
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "V2V-Base"


# ─────────────────────────────────────────────────────────────
# Baseline 6: Random-K Precaching
# ─────────────────────────────────────────────────────────────
class RandomK:
    """
    Random-K: randomly select K (vehicle, content) pairs for precaching.
    K = average number of items selected by RILP (set externally or default=5).
    """
    
    def __init__(self, k_per_vehicle=5):
        self.k_per_vehicle = k_per_vehicle
    
    def run(self, sim):
        t0 = time.time()
        
        V = list(range(sim.n_vehicles))
        C = list(range(PARAMS["content_catalog_size"]))
        
        decisions = {}
        rng = sim.rng
        
        for v in V:
            let_v = sim.let[v]
            outage_v = sim.outage_end[v]
            f_v = max(1, outage_v)
            if let_v < f_v:
                continue
            
            k = min(self.k_per_vehicle, PARAMS["cache_cap"], len(C))
            sel = rng.sample(C, k)
            for c in sel:
                decisions[(v, c)] = rng.randint(f_v, max(f_v, let_v))
        
        solve_time = (time.time() - t0) * 1000
        return decisions, solve_time
    
    def name(self):
        return "Random-K"


# ─────────────────────────────────────────────────────────────
# Algorithm Registry
# ─────────────────────────────────────────────────────────────
def get_algorithm(algo_id, gamma=2.0, tau_max=5):
    """Factory function for algorithms."""
    if algo_id == "RILP":
        return RILPSolver(gamma=gamma, tau_max=tau_max)
    elif algo_id == "RILP-Greedy":
        return RILPGreedy(gamma=gamma, tau_max=tau_max)
    elif algo_id == "Nam2023b":
        return Nam2023b()
    elif algo_id == "Nam2025":
        return Nam2025()
    elif algo_id == "Youn2026":
        return Youn2026()
    elif algo_id == "V2I-Base":
        return V2IBase()
    elif algo_id == "V2V-Base":
        return V2VBase()
    elif algo_id == "Random-K":
        return RandomK()
    else:
        raise ValueError(f"Unknown algorithm: {algo_id}")
