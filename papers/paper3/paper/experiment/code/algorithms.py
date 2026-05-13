"""
algorithms.py — 8 precaching algorithm implementations for CIoV benchmark.
All algorithms share the same interface:
    cache_decision_fn(vehicles, params, rng) -> dict{vehicle_id: set(content_ids)}

Algorithms:
    1. RILP          — Robust ILP (exact, PuLP/CBC; small scale only)
    2. RILP-Greedy   — Greedy approximation of RILP
    3. Nam2023b      — Set-Ranking based multi-vehicle selection (Nam et al. 2023)
    4. Nam2025       — CIoV integrated storage+precaching (Nam et al. 2025)
    5. Youn2026      — SAC-RL based vehicle selection (Youn et al. 2026, simulated)
    6. V2I-Base      — V2I only baseline (most popular contents from RSU)
    7. V2V-Base      — V2V only baseline (neighbor-based sharing)
    8. Random-K      — Random K content assignment
"""
import math
import random

# ─────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────
def _top_k_by_popularity(popularity, k):
    """Return indices of top-k popular contents."""
    indexed = sorted(enumerate(popularity), key=lambda x: -x[1])
    return set(idx for idx, _ in indexed[:k])

def _aoi_weight(v, tau_max, gamma):
    """RILP AoI robustness weight for vehicle v."""
    return 1.0 + gamma * max(0, v['aoi'] - tau_max)

# ─────────────────────────────────────────────────────────────
# 1. RILP — Robust ILP (exact, CBC)
# ─────────────────────────────────────────────────────────────
def rilp_decision(vehicles, params, rng):
    """
    Robust ILP (exact): maximize weighted CHR subject to cache capacity.

    Mathematical equivalence note (2026-05-06 patch):
        The original formulation has a single linear knapsack-like constraint
        (sum_c x_c <= cap) with binary x_c and per-content weight
            w(v,c) = popularity[c] * (1 + gamma * max(0, aoi_v - tau_max)).
        The optimal solution is therefore the top-`cap` items by w(v,c).
        Calling PuLP/CBC for every vehicle every scheduling window made each
        run take hours.  We replace the solver call with the analytically
        equivalent O(catalog log catalog) sort.  The numerical output is
        identical to the CBC solution on this problem family.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    tau_max = params['tau_max']
    gamma = params['gamma']
    catalog = params['catalog_size']

    result = {}
    for v in vehicles:
        aoi_w = 1.0 + gamma * max(0, v['aoi'] - tau_max)
        # Closed-form optimum of the LP relaxation == ILP optimum on a
        # single-cardinality-constraint knapsack with non-negative weights.
        scores = sorted(
            ((popularity[c] * aoi_w, c) for c in range(catalog)),
            reverse=True,
        )
        result[v['id']] = set(c for _, c in scores[:cap])
    return result

# ─────────────────────────────────────────────────────────────
# 2. RILP-Greedy — Greedy approximation of RILP
# ─────────────────────────────────────────────────────────────
def rilp_greedy_decision(vehicles, params, rng):
    """
    Greedy RILP approximation:
    Score(c,v) = popularity[c] * (1 + gamma * max(0, aoi_v - tau_max))
    Select top-K by score for each vehicle.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    tau_max = params['tau_max']
    gamma = params['gamma']
    catalog = params['catalog_size']
    alpha = params.get('alpha_greedy', 0.5)

    result = {}
    for v in vehicles:
        aoi_w = 1.0 + gamma * max(0, v['aoi'] - tau_max)
        scores = [(popularity[c] * aoi_w, c) for c in range(catalog)]
        scores.sort(reverse=True)
        chosen = set(c for _, c in scores[:cap])
        result[v['id']] = chosen
    return result

# ─────────────────────────────────────────────────────────────
# 3. Nam2023b — Set-Ranking based vehicle selection
# ─────────────────────────────────────────────────────────────
def nam2023b_decision(vehicles, params, rng):
    """
    Nam2023b: rank content by set-rank score (popularity * diversity),
    assign top-K to each vehicle considering neighbor overlap penalty.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']

    # Set-ranking: penalize contents already popular among neighbors
    content_coverage = [0] * catalog
    for v in vehicles:
        for c in v['cache']:
            content_coverage[c] += 1

    result = {}
    for v in vehicles:
        # Score = popularity - alpha * coverage (diversity)
        scores = []
        for c in range(catalog):
            diversity_penalty = content_coverage[c] / max(1, len(vehicles))
            score = popularity[c] - 0.3 * diversity_penalty
            scores.append((score, c))
        scores.sort(reverse=True)
        chosen = set(c for _, c in scores[:cap])
        result[v['id']] = chosen
    return result

# ─────────────────────────────────────────────────────────────
# 4. Nam2025 — CIoV integrated storage+precaching
# ─────────────────────────────────────────────────────────────
def nam2025_decision(vehicles, params, rng):
    """
    Nam2025: integrated storage selection with mobility-aware precaching.
    Considers vehicle's predicted dwell time in RSU coverage.
    High-mobility vehicles get more popular content (fast refresh).
    Low-mobility vehicles get diverse content.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    tau_max = params['tau_max']

    result = {}
    for v in vehicles:
        speed = math.sqrt(v['vx']**2 + v['vy']**2)
        mobility_factor = min(1.0, speed / 20.0)  # normalize 0~1

        scores = []
        for c in range(catalog):
            # High mobility → prefer high popularity (quick hits)
            # Low mobility → prefer coverage (diversity)
            score = mobility_factor * popularity[c] + (1 - mobility_factor) * (1.0 / (c + 1))
            # AoI urgency boost
            if v['aoi'] > tau_max:
                score *= 1.5
            scores.append((score, c))
        scores.sort(reverse=True)
        chosen = set(c for _, c in scores[:cap])
        result[v['id']] = chosen
    return result

# ─────────────────────────────────────────────────────────────
# 5. Youn2026 — SAC-RL based vehicle selection (simulated policy)
# ─────────────────────────────────────────────────────────────
def youn2026_decision(vehicles, params, rng):
    """
    Youn2026: SAC (Soft Actor-Critic) based vehicle selection.
    Since training is not feasible here, we simulate a trained policy:
    - State: (aoi, speed, cache_fullness, popularity_gap)
    - Policy approximation: adaptive weighted scoring with entropy regularization
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    tau_max = params['tau_max']
    catalog = params['catalog_size']
    gamma = params['gamma']

    result = {}
    for v in vehicles:
        speed = math.sqrt(v['vx']**2 + v['vy']**2)
        aoi_urgency = max(0, v['aoi'] - tau_max) / max(1, tau_max)
        cache_fullness = len(v['cache']) / cap

        scores = []
        for c in range(catalog):
            # SAC-inspired: policy = argmax(Q + alpha*entropy)
            q_value = popularity[c] * (1 + gamma * aoi_urgency)
            # Entropy bonus: prefer less-cached content (exploration)
            entropy_bonus = 0.1 * (1.0 - popularity[c])
            score = q_value + entropy_bonus
            # Speed adaptation
            score *= (1 + 0.2 * min(1.0, speed / 15.0))
            scores.append((score, c))
        scores.sort(reverse=True)
        chosen = set(c for _, c in scores[:cap])
        result[v['id']] = chosen
    return result

# ─────────────────────────────────────────────────────────────
# 6. V2I-Base — V2I only baseline
# ─────────────────────────────────────────────────────────────
def v2i_base_decision(vehicles, params, rng):
    """
    V2I-Base: all vehicles cache the top-K globally popular contents.
    No V2V cooperation, no mobility awareness.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']

    top_k = _top_k_by_popularity(popularity, cap)
    return {v['id']: set(top_k) for v in vehicles}

# ─────────────────────────────────────────────────────────────
# 7. V2V-Base — V2V cooperative baseline
# ─────────────────────────────────────────────────────────────
def v2v_base_decision(vehicles, params, rng):
    """
    V2V-Base: vehicles cache content to maximize neighborhood coverage.
    Each vehicle selects contents not already cached by neighbors.
    (Greedy coverage without RSU involvement)
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    rsu_positions = params['rsu_positions']
    comm_range = 800  # default

    # Group vehicles by nearest RSU
    rsu_groups = {}
    for v in vehicles:
        min_d = float('inf')
        best_rsu = 0
        for i, (rx, ry) in enumerate(rsu_positions):
            d = math.sqrt((v['x']-rx)**2 + (v['y']-ry)**2)
            if d < min_d:
                min_d = d
                best_rsu = i
        if best_rsu not in rsu_groups:
            rsu_groups[best_rsu] = []
        rsu_groups[best_rsu].append(v)

    result = {}
    for rsu_id, group in rsu_groups.items():
        # Assign content to maximize coverage in group
        content_assigned = {}  # content_id -> assigned_vehicle_count
        for c in range(catalog):
            content_assigned[c] = 0

        # Sort by popularity * (1/coverage)
        for v in sorted(group, key=lambda x: -x['aoi']):
            scores = []
            for c in range(catalog):
                score = popularity[c] / (1 + content_assigned[c])
                scores.append((score, c))
            scores.sort(reverse=True)
            chosen = set(c for _, c in scores[:cap])
            for c in chosen:
                content_assigned[c] += 1
            result[v['id']] = chosen

    # Vehicles not assigned (shouldn't happen)
    top_k = _top_k_by_popularity(popularity, cap)
    for v in vehicles:
        if v['id'] not in result:
            result[v['id']] = set(top_k)

    return result

# ─────────────────────────────────────────────────────────────
# 8. Random-K — Random content assignment
# ─────────────────────────────────────────────────────────────
def random_k_decision(vehicles, params, rng):
    """
    Random-K: each vehicle randomly selects K contents.
    """
    cap = params['cache_capacity']
    catalog = params['catalog_size']

    result = {}
    for v in vehicles:
        chosen = set(rng.sample(range(catalog), min(cap, catalog)))
        result[v['id']] = chosen
    return result

# ─────────────────────────────────────────────────────────────
# Algorithm registry
# ─────────────────────────────────────────────────────────────
ALGORITHMS = {
    'RILP':        rilp_decision,
    'RILP-Greedy': rilp_greedy_decision,
    'Nam2023b':    nam2023b_decision,
    'Nam2025':     nam2025_decision,
    'Youn2026':    youn2026_decision,
    'V2I-Base':    v2i_base_decision,
    'V2V-Base':    v2v_base_decision,
    'Random-K':    random_k_decision,
}
