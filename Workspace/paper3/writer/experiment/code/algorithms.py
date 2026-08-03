"""
algorithms.py — 8 precaching algorithm implementations for CIoV benchmark.

All algorithms share the same interface:
    cache_decision_fn(vehicles, params, rng) -> dict{vehicle_id: set(content_ids)}

Implements the mathematical formulation from idea_spec.md:
  - Robust ILP (RILP) with Γ-budgeted uncertainty set
  - AoI-SLA constraints, LET constraints, outage constraints
  - Proper transmission time computation
  - Cache capacity with ceil(content_size)

Vehicle dict fields used:
    id, x, y, vx, vy, speed, cache (set), aoi (int),
    let (float, deterministic LET in slots),
    let_robust (float, worst-case LET = LET - gamma*delta_v),
    outage_end (int, slot when outage ends),
    delta_v (float, prediction error bound),
    t_gen (dict mapping content_id -> generation time slot)

Params dict fields used:
    catalog_size, cache_capacity, popularity (list), content_sizes (list, MB),
    tau_max, gamma, pred_error (float 0~1), v2i_bw (Mbps), v2v_bw (Mbps),
    sched_window (int), n_rsu, rsu_positions (list of (x,y)), current_step (int)

Algorithms:
    1. RILP          — Robust ILP (exact, PuLP/CBC; small scale only)
    2. RILP-Greedy   — Greedy approximation of RILP
    3. Nam2023b      — Set-Ranking based multi-vehicle selection (deterministic LET)
    4. Nam2025       — CIoV integrated storage+precaching (deterministic LET)
    5. Youn2026      — V2V Relay with deterministic LET
    6. V2I-Base      — V2I only baseline (most popular contents from RSU)
    7. V2V-Base      — V2V cooperative baseline (neighbor-based sharing)
    8. Random-K      — Random K content assignment
"""
import math

# Optional PuLP import for exact RILP solver
try:
    import pulp
    _HAS_PULP = True
except ImportError:
    _HAS_PULP = False


# ─────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────

def _transmission_time(content_id, content_sizes, bw_mbps):
    """
    Compute the transmission time (in slots) for content c over a link
    with bandwidth bw_mbps (Megabits per second).

    Each slot = 1 second.
    transmission_time(c) = max(1, ceil(content_sizes[c] * 8 / bw_mbps))

    Parameters
    ----------
    content_id : int
        Index into content_sizes.
    content_sizes : list[float]
        Per-content sizes in MB (megabytes).
    bw_mbps : float
        Link bandwidth in Mbps (megabits per second).

    Returns
    -------
    int
        Number of slots required for transmission.
    """
    size_mb = content_sizes[content_id]
    size_mbits = size_mb * 8.0  # convert MB to Megabits
    return max(1, math.ceil(size_mbits / bw_mbps))


def _content_slot_size(content_id, content_sizes):
    """
    Cache slot cost for a content item: ceil(size_in_MB).
    Used in cache capacity constraint: sum of ceil(s_c) <= cache_capacity.
    """
    return math.ceil(content_sizes[content_id])


def _is_let_feasible(content_id, content_sizes, bw_mbps, let_slots, outage_end):
    """
    Check if content c can be feasibly delivered to a vehicle.

    Feasibility requires:
      1. transmission_time(c) <= let_slots  (delivery completes within LET)
      2. outage_end <= let_slots            (vehicle is reachable after outage)

    Note: The delivery cannot start until outage_end, and must complete
    within let_slots. So the effective condition is:
      outage_end + transmission_time(c) <= let_slots  (start after outage)
    OR more conservatively, transmission_time alone must fit in LET.

    Per the spec: f_{v,c} = transmission_time(c), and we need:
      f_{v,c} <= let_slots  (LET constraint)
      f_{v,c} >= outage_end (outage constraint)

    So feasible if: outage_end <= transmission_time(c) <= let_slots
    OR if outage_end > transmission_time(c), then f_{v,c} = outage_end
    and we need outage_end <= let_slots.

    The actual delivery slot: f_{v,c} = max(outage_end, transmission_time(c))
    Feasible if: f_{v,c} <= let_slots

    Parameters
    ----------
    content_id : int
    content_sizes : list[float]
    bw_mbps : float
    let_slots : float
        LET in slots (deterministic or robust).
    outage_end : int
        Slot when outage ends (0 if no outage).

    Returns
    -------
    bool
    """
    tx_time = _transmission_time(content_id, content_sizes, bw_mbps)
    f_vc = max(outage_end, tx_time)
    return f_vc <= let_slots


def _delivery_slot(content_id, content_sizes, bw_mbps, outage_end):
    """
    Compute the earliest feasible delivery time slot for content c to vehicle v.

    f_{v,c} = max(outage_end(v), transmission_time(c))

    Returns
    -------
    int
        Earliest feasible delivery slot.
    """
    tx_time = _transmission_time(content_id, content_sizes, bw_mbps)
    return max(outage_end, tx_time)


def _safe_get(v, key, default):
    """Safely get a vehicle field with a fallback default."""
    val = v.get(key, default)
    if val is None:
        return default
    return val


# ─────────────────────────────────────────────────────────────
# 1. RILP — Robust ILP (exact, CBC)
# ─────────────────────────────────────────────────────────────

def rilp_decision(vehicles, params, rng):
    """
    Robust ILP (exact): PuLP/CBC solver for the RILP formulation
    from idea_spec.md Section 4.2.

    For small scale (density <= 5, i.e., few vehicles), uses PuLP/CBC.
    For larger scale or if PuLP is unavailable, falls back to RILP-Greedy.

    Decision variables:
        x_{v,c} ∈ {0,1}  — precache content c to vehicle v
        z_{v,c} ≥ 0      — AoI violation slack

    Objective:
        minimize  Σ_{v,c}  w_{v,c} · z_{v,c}
        where w_{v,c} = popularity[c]

    Constraints:
        [R1-robust] f_{v,c} ≤ floor(LET_v_robust) · x_{v,c}   (robust LET)
        [R2]        f_{v,c} ≥ outage_end(v) · x_{v,c}          (outage)
        [R3]        Σ_c x_{v,c} · ceil(s_c) ≤ cache_capacity   (capacity)
        [R6]        a_{v,c} ≤ τ_max + M·(1 - x_{v,c})          (AoI-SLA)
        [R7]        z_{v,c} ≥ a_{v,c} - τ_max                   (violation)
        [R8]        z_{v,c} ≥ 0
    """
    # Fall back to greedy if PuLP unavailable or scale too large
    if not _HAS_PULP or len(vehicles) > 5 * 25:  # density>5 => fallback
        return rilp_greedy_decision(vehicles, params, rng)

    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    tau_max = params['tau_max']
    v2i_bw = params['v2i_bw']
    sched_window = params.get('sched_window', 20)
    current_step = params.get('current_step', 0)

    # Big-M for AoI-SLA constraint: M = sched_window + tau_max
    M = sched_window + tau_max

    result = {}

    for v in vehicles:
        vid = v['id']
        let_robust = _safe_get(v, 'let_robust', _safe_get(v, 'let', float('inf')))
        outage_end = _safe_get(v, 'outage_end', 0)
        t_gen = _safe_get(v, 't_gen', {})
        let_robust_floor = math.floor(let_robust) if let_robust != float('inf') else sched_window

        # Create ILP problem for this vehicle
        prob = pulp.LpProblem(f"RILP_v{vid}", pulp.LpMinimize)

        # Decision variables
        x = {}  # x[c] ∈ {0,1}
        z = {}  # z[c] ≥ 0 (AoI violation slack)

        feasible_contents = []
        for c in range(catalog):
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            if f_vc <= let_robust_floor:
                feasible_contents.append(c)

        if not feasible_contents:
            result[vid] = set()
            continue

        for c in feasible_contents:
            x[c] = pulp.LpVariable(f"x_{c}", cat='Binary')
            z[c] = pulp.LpVariable(f"z_{c}", lowBound=0, cat='Continuous')

        # Objective: minimize Σ_c w_c · z_c
        prob += pulp.lpSum(popularity[c] * z[c] for c in feasible_contents)

        # [R3] Cache capacity: Σ_c x_c · ceil(s_c) <= cap
        prob += (
            pulp.lpSum(
                _content_slot_size(c, content_sizes) * x[c]
                for c in feasible_contents
            ) <= cap,
            "capacity"
        )

        # Per-content constraints
        for c in feasible_contents:
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            gen_time = t_gen.get(c, 0)

            # AoI at reception: a_{v,c} = (current_step + f_{v,c}) - t_gen(c)
            a_vc = (current_step + f_vc) - gen_time

            # [R6] AoI-SLA: a_{v,c} ≤ τ_max + M·(1 - x_c)
            #   => a_vc - M*(1 - x_c) <= tau_max
            #   => a_vc - M + M*x_c <= tau_max
            #   When x_c = 1: a_vc <= tau_max  (must satisfy SLA)
            #   When x_c = 0: a_vc <= tau_max + M  (vacuous)
            prob += (
                a_vc <= tau_max + M * (1 - x[c]),
                f"aoi_sla_{c}"
            )

            # [R7] z_c >= a_{v,c} - tau_max  (only meaningful when x_c=1)
            # z_c >= a_vc * x_c - tau_max * x_c  (linearization)
            # Since a_vc is a constant for given f_vc:
            prob += (z[c] >= (a_vc - tau_max) * x[c], f"viol_{c}")

            # Note: [R1] and [R2] are already enforced by pre-filtering
            # feasible_contents (f_vc <= let_robust_floor is checked above)

        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))

        chosen = set()
        if prob.status == pulp.constants.LpStatusOptimal:
            for c in feasible_contents:
                if x[c].varValue is not None and x[c].varValue > 0.5:
                    chosen.add(c)
        else:
            # Solver failed — fall back to greedy for this vehicle
            chosen = _greedy_single_vehicle(
                v, params, use_robust=True
            )

        result[vid] = chosen

    return result


def _greedy_single_vehicle(v, params, use_robust=True):
    """
    Greedy assignment for a single vehicle. Used as fallback when
    ILP solver fails or for individual vehicle processing.

    Returns set of content_ids.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    tau_max = params['tau_max']
    v2i_bw = params['v2i_bw']
    current_step = params.get('current_step', 0)

    if use_robust:
        let_val = _safe_get(v, 'let_robust', _safe_get(v, 'let', float('inf')))
    else:
        let_val = _safe_get(v, 'let', float('inf'))

    outage_end = _safe_get(v, 'outage_end', 0)
    t_gen = _safe_get(v, 't_gen', {})
    let_floor = math.floor(let_val) if let_val != float('inf') else 9999

    scored = []
    for c in range(catalog):
        f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
        if f_vc > let_floor:
            continue

        gen_time = t_gen.get(c, 0)
        a_vc_expected = (current_step + f_vc) - gen_time
        aoi_urgency = max(0.0, (a_vc_expected - tau_max) / max(1, tau_max))
        alpha = 0.5
        priority = let_val * popularity[c] * (1.0 + alpha * aoi_urgency)
        scored.append((priority, c))

    scored.sort(key=lambda x: (-x[0], x[1]))

    chosen = set()
    used_cap = 0
    for _, c in scored:
        slot_cost = _content_slot_size(c, content_sizes)
        if used_cap + slot_cost <= cap:
            chosen.add(c)
            used_cap += slot_cost
    return chosen


# ─────────────────────────────────────────────────────────────
# 2. RILP-Greedy — Greedy approximation of RILP
# ─────────────────────────────────────────────────────────────

def rilp_greedy_decision(vehicles, params, rng):
    """
    Greedy RILP approximation (Algorithm 1 from idea_spec.md §4.4).

    Uses worst-case (robust) LET: LET_v^robust = v['let_robust'].

    Priority scoring:
        priority(v, c) = LET_v^robust × pop_c × (1 + α · AoI_urgency(v,c))
        AoI_urgency(v,c) = max(0, (a_{v,c}^expected - τ_max) / τ_max)

    Steps:
        1. Compute worst-case LET for each vehicle
        2. For each (v,c) pair, check feasibility:
           delivery_slot(c) <= LET_v^robust (robust LET)
        3. Compute priority score
        4. Sort all (v,c) pairs descending by priority
        5. Greedily assign respecting per-vehicle capacity (ceil(s_c))

    Ties broken by content size (smaller first → higher slot efficiency).
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    tau_max = params['tau_max']
    v2i_bw = params['v2i_bw']
    current_step = params.get('current_step', 0)
    alpha = 0.5  # AoI emphasis parameter

    # Remaining capacity per vehicle
    remaining = {}
    result = {}
    for v in vehicles:
        vid = v['id']
        remaining[vid] = cap
        result[vid] = set()

    # Build and score all feasible (v, c) pairs
    scored_pairs = []
    for v in vehicles:
        vid = v['id']
        let_robust = _safe_get(v, 'let_robust', _safe_get(v, 'let', float('inf')))
        outage_end = _safe_get(v, 'outage_end', 0)
        t_gen = _safe_get(v, 't_gen', {})
        let_floor = math.floor(let_robust) if let_robust != float('inf') else 9999

        for c in range(catalog):
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)

            # Feasibility: delivery slot must fit within robust LET
            if f_vc > let_floor:
                continue

            # AoI at expected reception
            gen_time = t_gen.get(c, 0)
            a_vc_expected = (current_step + f_vc) - gen_time
            aoi_urgency = max(0.0, (a_vc_expected - tau_max) / max(1, tau_max))

            # Priority scoring from idea_spec.md §4.4
            priority = let_robust * popularity[c] * (1.0 + alpha * aoi_urgency)

            # Tie-breaker: smaller content first (negative size for sort)
            slot_cost = _content_slot_size(c, content_sizes)
            scored_pairs.append((priority, -slot_cost, vid, c, slot_cost))

    # Sort descending by priority, then by smaller content (slot_cost ascending)
    scored_pairs.sort(key=lambda x: (-x[0], x[1]))

    # Greedy assignment
    for priority, neg_cost, vid, c, slot_cost in scored_pairs:
        if remaining[vid] >= slot_cost and c not in result[vid]:
            result[vid].add(c)
            remaining[vid] -= slot_cost

    return result


# ─────────────────────────────────────────────────────────────
# 3. Nam2023b — Set-Ranking based vehicle selection
# ─────────────────────────────────────────────────────────────

def nam2023b_decision(vehicles, params, rng):
    """
    Nam2023b: Set-Ranking with deterministic LET (no uncertainty correction).

    Set ranking score = LET_v × popularity[c] with diversity penalty.
    - Uses deterministic LET: v['let']
    - No AoI tracking
    - Applies LET constraint: transmission_time(c) <= LET_v
    - Applies outage constraint: f_{v,c} >= outage_end(v)

    Diversity: penalize content already assigned to other vehicles
    (approximates the set-ranking approach from the original paper).

    For each vehicle:
        score(c) = LET_v × pop[c] × (1 / (1 + coverage_count[c]))
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']

    # Track how many vehicles have been assigned each content (diversity)
    content_coverage = [0] * catalog

    result = {}
    for v in vehicles:
        vid = v['id']
        let_det = _safe_get(v, 'let', float('inf'))
        outage_end = _safe_get(v, 'outage_end', 0)
        let_floor = math.floor(let_det) if let_det != float('inf') else 9999

        # Score each feasible content
        scored = []
        for c in range(catalog):
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            # LET constraint (deterministic)
            if f_vc > let_floor:
                continue

            # Set-ranking score with diversity penalty
            diversity_factor = 1.0 / (1.0 + content_coverage[c])
            score = let_det * popularity[c] * diversity_factor
            slot_cost = _content_slot_size(c, content_sizes)
            scored.append((score, -slot_cost, c, slot_cost))

        scored.sort(key=lambda x: (-x[0], x[1]))

        chosen = set()
        used_cap = 0
        for score, _, c, slot_cost in scored:
            if used_cap + slot_cost <= cap:
                chosen.add(c)
                used_cap += slot_cost

        # Update coverage counts
        for c in chosen:
            content_coverage[c] += 1

        result[vid] = chosen

    return result


# ─────────────────────────────────────────────────────────────
# 4. Nam2025 — CIoV integrated storage+precaching
# ─────────────────────────────────────────────────────────────

def nam2025_decision(vehicles, params, rng):
    """
    Nam2025: Storage-Aware ILP approximation with deterministic LET.

    Key characteristic: value density = popularity[c] / content_size[c].
    This reflects the storage-aware nature — prefer content with high
    popularity-per-byte (efficient use of limited cache capacity).

    - Uses deterministic LET: v['let']
    - No AoI tracking
    - Applies LET and outage constraints
    - Greedy by value density (fractional knapsack-style for integer items)
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']

    result = {}
    for v in vehicles:
        vid = v['id']
        let_det = _safe_get(v, 'let', float('inf'))
        outage_end = _safe_get(v, 'outage_end', 0)
        let_floor = math.floor(let_det) if let_det != float('inf') else 9999

        scored = []
        for c in range(catalog):
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            # LET constraint (deterministic)
            if f_vc > let_floor:
                continue

            # Value density = popularity / content_size
            size = content_sizes[c]
            value_density = popularity[c] / max(0.01, size)
            slot_cost = _content_slot_size(c, content_sizes)
            scored.append((value_density, -slot_cost, c, slot_cost))

        scored.sort(key=lambda x: (-x[0], x[1]))

        chosen = set()
        used_cap = 0
        for vd, _, c, slot_cost in scored:
            if used_cap + slot_cost <= cap:
                chosen.add(c)
                used_cap += slot_cost

        result[vid] = chosen

    return result


# ─────────────────────────────────────────────────────────────
# 5. Youn2026 — V2V Relay with deterministic LET
# ─────────────────────────────────────────────────────────────

def youn2026_decision(vehicles, params, rng):
    """
    Youn2026: V2V Relay with deterministic LET and outage zone modeling.

    Key characteristics:
    - Uses deterministic LET: v['let']
    - Top 30% LET vehicles are designated as "relay" vehicles
      → they get 1.5x effective bandwidth (V2V relay boost)
    - No AoI tracking
    - Applies LET and outage constraints

    Relay vehicles serve as V2V relays, enabling cooperative precaching.
    Their effective bandwidth for content delivery is boosted by combining
    V2I + V2V paths.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']
    v2v_bw = params.get('v2v_bw', v2i_bw * 0.5)

    # Determine relay vehicles: top 30% by deterministic LET
    veh_let_pairs = []
    for v in vehicles:
        let_det = _safe_get(v, 'let', 0.0)
        veh_let_pairs.append((let_det, v['id']))

    veh_let_pairs.sort(reverse=True)
    relay_count = max(1, math.ceil(len(veh_let_pairs) * 0.3))
    relay_ids = set(vid for _, vid in veh_let_pairs[:relay_count])

    result = {}
    for v in vehicles:
        vid = v['id']
        let_det = _safe_get(v, 'let', float('inf'))
        outage_end = _safe_get(v, 'outage_end', 0)
        let_floor = math.floor(let_det) if let_det != float('inf') else 9999

        # Relay vehicles get 1.5x bandwidth boost (V2I + V2V combined)
        if vid in relay_ids:
            effective_bw = v2i_bw * 1.5
        else:
            effective_bw = v2i_bw

        scored = []
        for c in range(catalog):
            f_vc = _delivery_slot(c, content_sizes, effective_bw, outage_end)
            # LET constraint (deterministic)
            if f_vc > let_floor:
                continue

            score = popularity[c]
            slot_cost = _content_slot_size(c, content_sizes)
            scored.append((score, -slot_cost, c, slot_cost))

        scored.sort(key=lambda x: (-x[0], x[1]))

        chosen = set()
        used_cap = 0
        for sc, _, c, slot_cost in scored:
            if used_cap + slot_cost <= cap:
                chosen.add(c)
                used_cap += slot_cost

        result[vid] = chosen

    return result


# ─────────────────────────────────────────────────────────────
# 6. V2I-Base — V2I only baseline
# ─────────────────────────────────────────────────────────────

def v2i_base_decision(vehicles, params, rng):
    """
    V2I-Base: V2I only baseline.

    Assigns globally top-K popular content to each vehicle.
    No V2V cooperation, no mobility-specific adaptation.
    Still applies LET feasibility check — if content cannot be delivered
    within the vehicle's LET, it is skipped and the next popular content
    is considered.

    Uses deterministic LET for feasibility.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']

    # Pre-sort content by popularity (global ranking)
    pop_ranking = sorted(range(catalog), key=lambda c: -popularity[c])

    result = {}
    for v in vehicles:
        vid = v['id']
        let_det = _safe_get(v, 'let', float('inf'))
        outage_end = _safe_get(v, 'outage_end', 0)
        let_floor = math.floor(let_det) if let_det != float('inf') else 9999

        chosen = set()
        used_cap = 0
        for c in pop_ranking:
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            if f_vc > let_floor:
                continue
            slot_cost = _content_slot_size(c, content_sizes)
            if used_cap + slot_cost <= cap:
                chosen.add(c)
                used_cap += slot_cost

        result[vid] = chosen

    return result


# ─────────────────────────────────────────────────────────────
# 7. V2V-Base — V2V cooperative baseline
# ─────────────────────────────────────────────────────────────

def v2v_base_decision(vehicles, params, rng):
    """
    V2V-Base: V2V cooperative baseline.

    Groups vehicles by nearest RSU. Within each RSU group, maximizes
    neighborhood content coverage by scoring:
        score(c) = popularity[c] / (1 + already_assigned_count[c])

    This ensures diversity across the RSU cell — different vehicles
    cache different content, maximizing the neighborhood's collective
    cache coverage.

    Applies LET and outage constraints.
    Uses deterministic LET.
    """
    cap = params['cache_capacity']
    popularity = params['popularity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']
    rsu_positions = params['rsu_positions']

    # Group vehicles by nearest RSU
    rsu_groups = {}
    for v in vehicles:
        vx, vy = v['x'], v['y']
        best_rsu = 0
        best_dist = float('inf')
        for i, (rx, ry) in enumerate(rsu_positions):
            d = math.hypot(vx - rx, vy - ry)
            if d < best_dist:
                best_dist = d
                best_rsu = i
        if best_rsu not in rsu_groups:
            rsu_groups[best_rsu] = []
        rsu_groups[best_rsu].append(v)

    result = {}

    for rsu_id, group in rsu_groups.items():
        # Track per-content assignment count within this RSU group
        content_assigned = [0] * catalog

        # Process vehicles sorted by AoI descending (most urgent first)
        sorted_group = sorted(group, key=lambda x: -x.get('aoi', 0))

        for v in sorted_group:
            vid = v['id']
            let_det = _safe_get(v, 'let', float('inf'))
            outage_end = _safe_get(v, 'outage_end', 0)
            let_floor = math.floor(let_det) if let_det != float('inf') else 9999

            scored = []
            for c in range(catalog):
                f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
                if f_vc > let_floor:
                    continue

                # Coverage-maximizing score
                score = popularity[c] / (1.0 + content_assigned[c])
                slot_cost = _content_slot_size(c, content_sizes)
                scored.append((score, -slot_cost, c, slot_cost))

            scored.sort(key=lambda x: (-x[0], x[1]))

            chosen = set()
            used_cap = 0
            for sc, _, c, slot_cost in scored:
                if used_cap + slot_cost <= cap:
                    chosen.add(c)
                    used_cap += slot_cost

            for c in chosen:
                content_assigned[c] += 1

            result[vid] = chosen

    # Safety: any vehicle not in a group (shouldn't happen) gets top-K
    if len(result) < len(vehicles):
        pop_ranking = sorted(range(catalog), key=lambda c: -popularity[c])
        for v in vehicles:
            if v['id'] not in result:
                chosen = set()
                used_cap = 0
                for c in pop_ranking:
                    slot_cost = _content_slot_size(c, content_sizes)
                    if used_cap + slot_cost <= cap:
                        chosen.add(c)
                        used_cap += slot_cost
                result[v['id']] = chosen

    return result


# ─────────────────────────────────────────────────────────────
# 8. Random-K — Random content assignment
# ─────────────────────────────────────────────────────────────

def random_k_decision(vehicles, params, rng):
    """
    Random-K: each vehicle randomly selects contents, filtered by
    LET feasibility.

    Randomly shuffles content, then greedily adds feasible items
    until cache is full. Uses deterministic LET for feasibility.
    """
    cap = params['cache_capacity']
    catalog = params['catalog_size']
    content_sizes = params['content_sizes']
    v2i_bw = params['v2i_bw']

    all_contents = list(range(catalog))

    result = {}
    for v in vehicles:
        vid = v['id']
        let_det = _safe_get(v, 'let', float('inf'))
        outage_end = _safe_get(v, 'outage_end', 0)
        let_floor = math.floor(let_det) if let_det != float('inf') else 9999

        # Shuffle for randomness
        shuffled = list(all_contents)
        rng.shuffle(shuffled)

        chosen = set()
        used_cap = 0
        for c in shuffled:
            f_vc = _delivery_slot(c, content_sizes, v2i_bw, outage_end)
            if f_vc > let_floor:
                continue
            slot_cost = _content_slot_size(c, content_sizes)
            if used_cap + slot_cost <= cap:
                chosen.add(c)
                used_cap += slot_cost

        result[vid] = chosen

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
