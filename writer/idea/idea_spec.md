# Research Idea Specification
## NDN-based AoI-Optimal Content Delivery with Multi-Agent Federated Actor-Critic in Vehicular Networks

**Target Journal:** IEEE Transactions on Wireless Communications (TWC)  
**Date:** 2026-04-15  
**Research Gap Verified:** NDN + AoI + MARL 3-way combination — NO existing paper found (Librarian confirmed 2026-04-14)

---

## 1. Problem Statement

In Cognitive Internet of Vehicles (CIoV), time-sensitive information (e.g., cooperative awareness messages, sensor data, HD map updates) must be delivered with minimal staleness. The **Age of Information (AoI)**, defined as the elapsed time since the last received update was generated, has emerged as a key metric for information freshness. However, existing AoI optimization studies face four critical challenges in vehicular networks:

1. **IP-centric Architecture Limitation:** Traditional IP-based vehicular networks lack native in-network caching. Named Data Networking (NDN) provides content store (CS), pending interest table (PIT), and forwarding information base (FIB) that can fundamentally reshape AoI dynamics through in-network caching—yet the interplay between NDN caching and AoI has not been mathematically characterized.

2. **Freshness-Availability Tradeoff in NDN Caching:** NDN's in-network caching improves content availability but may serve stale content. The tradeoff between cache hit ratio (availability) and content freshness (AoI) requires rigorous mathematical analysis that accounts for cache replacement policies, content popularity, and update rates.

3. **Physical Layer Neglect:** Most NDN-vehicular studies operate at the network/application layer, ignoring channel fading (Rician for V2V, Nakagami-m for V2I), SINR dynamics, transmission success probability, and MAC-layer resource contention (C-V2X Mode 4 / NR-V2X sidelink). For TWC-level contributions, a cross-layer model integrating physical/MAC/network layers is essential.

4. **Centralized Optimization Infeasibility:** The joint optimization of forwarding strategy, caching decision, transmit power, and subchannel allocation is a combinatorial problem with exponential state-action space. Centralized approaches cannot scale in dynamic vehicular topologies with fast-varying channels. A distributed multi-agent approach with federated model sharing is needed.

**Research Question:** *How can we jointly optimize AoI-aware content forwarding, caching, power control, and resource allocation in NDN-based vehicular networks using a distributed MARL framework with mathematical convergence guarantees?*

---

## 2. Core Contributions (3)

### C1: Cross-Layer NDN-AoI Mathematical Framework
- **Closed-form analysis** of average AoI and peak AoI in NDN vehicular networks, incorporating:
  - Cache hit probability as a function of content popularity (Zipf), cache size, and TTL-based replacement
  - Rician fading (V2V, K-factor dependent) and Nakagami-m fading (V2I) channel models
  - Transmission success probability via Marcum Q-function
  - C-V2X Mode 4 semi-persistent scheduling (SPS) with collision probability
- **Theorem 1 (NDN Caching AoI Reduction Bound):** Proves that NDN in-network caching reduces network-wide average AoI by a factor related to aggregate cache hit probability and channel reliability.
- **Theorem 2 (Freshness-Availability Tradeoff):** Characterizes the Pareto frontier between cache hit ratio and AoI, deriving optimal TTL as a function of content update rate and request rate.

### C2: Constrained MDP Formulation & MAFAC Algorithm
- **Constrained Markov Decision Process (CMDP)** formulation with:
  - 4-dimensional decision vector: (forwarding, caching, power, subchannel)
  - 5 constraints: energy budget, cache capacity, peak AoI QoS, channel busy ratio (CBR), NDN loop-free
- **Lagrangian relaxation** converting CMDP to unconstrained dual problem
- **Multi-Agent Federated Actor-Critic (MAFAC)** algorithm:
  - Each vehicle/RSU as an independent agent with local observation
  - Actor: policy gradient with Lagrangian advantage function
  - Critic: temporal difference learning for value estimation
  - Dual variable: online update via constraint violation feedback
  - **Factored action space** reducing complexity from O(|A₁|×|A₂|×|A₃|×|A₄|) to O(|A₁|+|A₂|+|A₃|+|A₄|)
- **Theorem 3 (Convergence):** Under standard assumptions (bounded rewards, Lipschitz policy), MAFAC converges to a locally optimal feasible policy of the CMDP.

### C3: Federated Aggregation for Non-IID Vehicular Environments
- **Critic-only federated aggregation** protocol:
  - Vehicles share only critic parameters (not actor) to preserve policy diversity
  - RSU-level aggregation with **importance-weighted averaging** based on local data quality (inverse AoI weighting)
  - Inter-RSU aggregation for network-wide knowledge sharing
- **Theorem 4 (Federated Convergence Rate):** Convergence rate bound of O(1/√(KT)) where K = number of agents, T = communication rounds, under non-IID data distributions.
- **Privacy:** Only value function parameters are shared, preserving local policy privacy.

---

## 3. Novelty vs. Prior Work

| Dimension | Zhang et al. 2022 (NDN+AoI) | Wang et al. 2024 (AoI+MARL+V2X) | Game-Theoretic DRL (NDN+MARL) | **Ours (MAFAC)** |
|-----------|-----|-----|-----|-----|
| NDN Architecture | ✅ | ❌ | ✅ | ✅ |
| AoI Metric | ✅ | ✅ | ❌ | ✅ |
| MARL | ❌ | ✅ | ✅ | ✅ |
| Physical Layer Model | ❌ | Partial | ❌ | ✅ (Rician/Nakagami) |
| Channel Fading | ❌ | ❌ | ❌ | ✅ |
| MAC Protocol (C-V2X) | ❌ | ❌ | ❌ | ✅ |
| Federated Learning | ❌ | ❌ | ❌ | ✅ |
| Mathematical Proofs | Partial | ❌ | ❌ | ✅ (4 Theorems) |
| Cross-Layer Optimization | ❌ | ❌ | ❌ | ✅ (PHY+MAC+NET) |

**Key Novelty Statement:** This is the **first paper** to:
1. Mathematically characterize AoI dynamics in NDN vehicular networks with physical layer effects
2. Formulate the joint forwarding-caching-power-channel problem as a CMDP
3. Solve it via a federated multi-agent actor-critic with provable convergence

---

## 4. Proposed Approach

### 4.1 System Model

**Network Topology:**
- Set of RSUs: R = {r₁, r₂, ..., r_M} deployed along road segments
- Set of vehicles at time t: V(t) = {v₁(t), v₂(t), ..., v_N(t)(t)}, where N(t) is time-varying
- Each RSU r_m covers area with radius d_cov
- Each vehicle v_n equipped with NDN protocol stack: Content Store (CS_n), Pending Interest Table (PIT_n), Forwarding Information Base (FIB_n)
- Content universe: K = {k₁, k₂, ..., k_K}; content k has generation rate λ_k (Poisson process)
- Request process: Each vehicle requests content k with rate μ_{n,k}, following Zipf popularity distribution: P(k) = k^{-α} / Σ_{j=1}^{K} j^{-α}

**Vehicle Mobility:**
- Simulated via libsumo with Krauss car-following model
- Position of vehicle n at time t: p_n(t) = (x_n(t), y_n(t))
- Velocity: v_n(t), acceleration: a_n(t)

**Time Slotting:**
- Discrete time slots: t ∈ {1, 2, ..., T}, slot duration τ (e.g., 100 ms aligned with C-V2X scheduling)

### 4.2 AoI Formulation in NDN Context

**Standard AoI Definition:**
For destination d requesting content k:
  Δ_{d,k}(t) = t − u_{d,k}(t)
where u_{d,k}(t) is the generation timestamp of the freshest received update of content k at node d by time t.

**NDN-Specific Cache-Aware AoI:**
In NDN, content can be received from:
1. Original producer (fresh, AoI = network delay)
2. Intermediate cache (potentially stale)

Define effective AoI:
  Δ^{NDN}_{d,k}(t) = t − max{u^{direct}_{d,k}(t), u^{cache}_{d,k}(t)}

where u^{direct} is the timestamp from producer path and u^{cache} from cache path.

**Average Network AoI:**
  Δ̄ = (1/T) Σ_{t=1}^{T} (1/|D|) Σ_{d∈D} Σ_{k∈K} w_k · Δ^{NDN}_{d,k}(t)

where w_k is the importance weight of content k (e.g., safety-critical content has higher weight).

**Peak AoI:**
  Δ^{peak}_{d,k} = max_t Δ^{NDN}_{d,k}(t)

**Value of Information (VoI):**
  VoI_{d,k}(t) = w_k · f(Δ^{NDN}_{d,k}(t))

where f(·) is a non-decreasing penalty function (e.g., f(x) = x for linear, f(x) = x² for quadratic, f(x) = 1 − e^{-βx} for exponential).

**NDN Cache Freshness Probability:**
For a cache node c serving content k with TTL-based policy:
  P^{fresh}_{c,k} = P(Δ^{cache}_{c,k} ≤ TTL_k) = 1 − e^{-λ_k · TTL_k}

(assuming Poisson update arrivals)

**Cache Hit Probability:**
Under LRU replacement with Zipf(α) popularity and cache size C_n:
  p^{hit}_{n,k} ≈ (C_n / K) · k^{-α} / Σ_{j=1}^{K} j^{-α}

(Che's approximation for large cache regime)

**Theorem 1 (NDN Caching AoI Reduction Bound):**
*Let Δ̄^{no-cache} be the average AoI without in-network caching, and Δ̄^{cache} with NDN caching. Then:*
  Δ̄^{cache} ≤ Δ̄^{no-cache} · (1 − p̄^{hit} · P̄^{fresh} · p̄^{succ})

*where p̄^{hit} is the aggregate cache hit probability, P̄^{fresh} is the average freshness probability, and p̄^{succ} is the average transmission success probability.*

**Theorem 2 (Optimal TTL for Freshness-Availability Tradeoff):**
*The optimal TTL that minimizes the weighted sum of AoI and cache miss rate satisfies:*
  TTL*_k = (1/λ_k) · ln(1 + w_k · λ_k / (c_miss · μ_k))

*where c_miss is the cache miss penalty and μ_k is the request rate for content k.*

### 4.3 Channel Model & Physical Layer

**Path Loss (3GPP TR 36.885/37.885):**
- V2V LOS: PL^{LOS}_{V2V}(d) = 38.77 + 16.7·log₁₀(d) + 18.2·log₁₀(f_c) [dB]
- V2V NLOS: PL^{NLOS}_{V2V}(d) = 36.85 + 30·log₁₀(d) + 18.9·log₁₀(f_c) [dB]
- V2I LOS: PL^{LOS}_{V2I}(d) = 32.4 + 20·log₁₀(d) + 20·log₁₀(f_c) [dB]
- LOS probability: P^{LOS}(d) = min(d₀/d, 1)·(1 − e^{-d/d₁}) + e^{-d/d₁}

**Small-Scale Fading:**
- V2V: Rician fading with K-factor κ
  - PDF: f_{|h|}(x) = 2x(1+κ)/Ω · e^{-κ-(1+κ)x²/Ω} · I₀(2x√(κ(1+κ)/Ω))
  - where I₀(·) is the modified Bessel function of first kind, Ω = E[|h|²]
- V2I: Nakagami-m fading with shape parameter m
  - PDF: f_{|h|}(x) = (2m^m)/(Γ(m)Ω^m) · x^{2m-1} · e^{-mx²/Ω}

**SINR:**
For vehicle n transmitting to node j on subchannel s at time slot t:
  γ_{n,j,s}(t) = (P_n(t) · G_{n,j,s}(t) · |h_{n,j,s}(t)|²) / (Σ_{i≠n} P_i(t) · G_{i,j,s}(t) · |h_{i,j,s}(t)|² + σ²)

where:
- P_n(t): transmit power of node n
- G_{n,j,s}(t) = 10^{-PL(d_{n,j}(t))/10}: large-scale path gain
- |h_{n,j,s}(t)|²: small-scale fading power gain
- σ²: thermal noise power (σ² = N₀ · B_s, where B_s is subchannel bandwidth)

**Transmission Success Probability:**
  p^{succ}_{n,j,s}(t) = P(γ_{n,j,s}(t) ≥ γ_th)

For Rician fading (V2V):
  p^{succ}_{n,j,s} = Q₁(√(2κ), √(2(1+κ)γ_th·(I₀+σ²)/(P_n·G_{n,j,s})))

where Q₁(·,·) is the Marcum Q-function.

For Nakagami-m fading (V2I):
  p^{succ}_{n,j,s} = 1 − γ_inc(m, m·γ_th·(I₀+σ²)/(P_n·G_{n,j,s}·Ω)) / Γ(m)

where γ_inc is the lower incomplete gamma function.

**Achievable Rate:**
  R_{n,j,s}(t) = B_s · log₂(1 + γ_{n,j,s}(t)) [bps]

**Packet Error Rate (Finite Blocklength Regime):**
For short packets (typical in V2X):
  ε_{n,j,s} ≈ Q(√(n_bl/V(γ)) · (C(γ) − R/n_bl) · ln2)

where:
- n_bl: blocklength (symbols)
- C(γ) = log₂(1+γ): Shannon capacity
- V(γ) = (1 − 1/(1+γ)²) · (log₂(e))²: channel dispersion
- Q(·): Gaussian Q-function

**C-V2X Mode 4 / NR-V2X Sidelink MAC:**
- Semi-Persistent Scheduling (SPS): resource reservation interval T_SPS
- Resource collision probability:
  P^{col}(N_v, N_sub) = 1 − (1 − 1/N_sub)^{N_v−1}

where N_v is the number of competing vehicles, N_sub is the number of subchannels.

- Channel Busy Ratio (CBR):
  CBR(t) = (1/(N_sub·T_w)) · Σ_{s,τ} 𝟙(RSSI_{s,τ} > P_th)

where T_w is the sensing window.

### 4.4 Optimization Problem Formulation

**Decision Variables (per agent n, per time slot t):**
1. **Forwarding strategy** f_n(t) ∈ {0,1}^{|Neighbors|}: which neighbor(s) to forward Interest/Data
2. **Caching decision** c_n(t) ∈ {0,1}^K: which content to cache
3. **Transmit power** P_n(t) ∈ [0, P_max]
4. **Subchannel selection** s_n(t) ∈ {1, 2, ..., N_sub}

**Objective:** Minimize network-wide weighted average AoI:
  min_{f,c,P,s} (1/T) Σ_{t=1}^{T} Σ_{d∈D} Σ_{k∈K} w_k · Δ^{NDN}_{d,k}(t)

**Subject to Constraints:**

(C1) Energy budget:
  (1/T) Σ_{t=1}^{T} P_n(t) ≤ P̄_n,  ∀n ∈ V

(C2) Cache capacity:
  Σ_{k=1}^{K} c_{n,k}(t) · s_k ≤ C_n,  ∀n, ∀t
  where s_k is the size of content k.

(C3) Peak AoI QoS:
  Δ^{peak}_{d,k} ≤ Δ_max,  ∀d ∈ D, ∀k ∈ K_critical

(C4) CBR congestion control:
  CBR_n(t) ≤ CBR_th,  ∀n, ∀t

(C5) NDN loop-free:
  Data packet follows reverse Interest path (PIT-based, inherently loop-free in NDN).

**CMDP Formulation:**

*State space* (per agent n):
  o_n(t) = [Δ_local(t), CS_status(t), PIT_status(t), p_n(t), v_n(t), CBR_n(t), N_neighbors(t), channel_state(t)]

- Δ_local(t): local AoI vector for top-K contents
- CS_status(t): cache occupancy and freshness
- PIT_status(t): pending interest count
- p_n(t), v_n(t): position, velocity
- CBR_n(t): current channel busy ratio
- N_neighbors(t): number of 1-hop neighbors
- channel_state(t): estimated SINR of each subchannel

*Action space* (per agent n):
  a_n(t) = (f_n(t), c_n(t), P_n(t), s_n(t))

*Reward:*
  r_n(t) = −Σ_k w_k · Δ^{NDN}_{n,k}(t) + bonus · 𝟙(cache_hit) − penalty · 𝟙(AoI > Δ_max)

*Constraint costs:*
  g₁(t) = max(P_n(t) − P̄_n, 0)  (energy)
  g₂(t) = max(Σ_k c_{n,k}·s_k − C_n, 0)  (cache)
  g₃(t) = max(Δ^{peak} − Δ_max, 0)  (QoS)
  g₄(t) = max(CBR_n(t) − CBR_th, 0)  (congestion)

**Lagrangian Relaxation:**
  L(π, λ) = E_π[Σ_t r(t)] − Σ_{i=1}^{4} λ_i · E_π[Σ_t g_i(t)]

  max_λ≥0 min_π L(π, λ)

### 4.5 MAFAC Algorithm Design

**Architecture (per agent n):**
- **Actor** π_θn(a|o): parameterized policy network (input: o_n, output: action distribution)
  - Factored into sub-actors: π^f_θ (forwarding) × π^c_θ (caching) × π^P_θ (power) × π^s_θ (subchannel)
  - Reduces action space from O(|A₁|×|A₂|×|A₃|×|A₄|) to O(|A₁|+|A₂|+|A₃|+|A₄|)
- **Critic** V_ϕn(o): value function estimator
- **Lagrange multipliers** λ_n = (λ₁, λ₂, λ₃, λ₄): dual variables for constraints

**Actor Update (Policy Gradient with Lagrangian Advantage):**
  ∇_θ J(θ) = E[∇_θ log π_θ(a|o) · A^L(o,a)]

where Lagrangian advantage:
  A^L(o,a) = r(o,a) − Σ_i λ_i · g_i(o,a) + γ·V_ϕ(o') − V_ϕ(o)

**Critic Update (TD Learning):**
  L(ϕ) = E[(r + γ·V_ϕ⁻(o') − V_ϕ(o))²]

with target network V_ϕ⁻ updated via Polyak averaging: ϕ⁻ ← τ·ϕ + (1−τ)·ϕ⁻

**Lagrange Multiplier Update (Dual Ascent):**
  λ_i ← max(0, λ_i + η_λ · g_i(t))

where η_λ is the dual learning rate.

### 4.6 Federated Aggregation

**5-Step Protocol per Communication Round:**
1. **Local Training:** Each agent n trains actor θ_n and critic ϕ_n for E local episodes
2. **Upload:** Vehicle n uploads critic parameters ϕ_n to associated RSU r_m
3. **RSU Aggregation:** RSU r_m computes weighted average:
   ϕ̄_m = Σ_{n∈V_m} w_n · ϕ_n / Σ_{n∈V_m} w_n
   where w_n = 1/Δ̄_n (inverse AoI weighting — agents with fresher information contribute more)
4. **Download:** RSU broadcasts ϕ̄_m to all vehicles in coverage
5. **Inter-RSU Aggregation:** Adjacent RSUs exchange ϕ̄ for network-wide consistency

**Key Design Choices:**
- **Critic-only sharing:** Actors remain local → preserves policy diversity and reduces communication
- **Inverse AoI weighting:** Agents with more up-to-date observations have higher aggregation weight
- **Partial participation:** Only vehicles with sufficient local training (E ≥ E_min) participate

---

## 5. Mathematical Analysis Plan

The following theorems/propositions will be formally proved in the paper:

| # | Type | Statement | Proof Technique |
|---|------|-----------|-----------------|
| 1 | **Theorem** | NDN Caching AoI Reduction Bound: Δ̄^{cache} ≤ Δ̄^{no-cache}·(1−p̄^{hit}·P̄^{fresh}·p̄^{succ}) | Stochastic analysis, renewal theory |
| 2 | **Theorem** | Optimal TTL: TTL*_k = (1/λ_k)·ln(1 + w_k·λ_k/(c_miss·μ_k)) | KKT conditions on TTL optimization |
| 3 | **Proposition** | Transmission Success Probability closed-form for Rician and Nakagami channels | Marcum Q-function, incomplete gamma |
| 4 | **Theorem** | MAFAC Convergence: Under Lipschitz policy, bounded rewards, and diminishing step sizes, MAFAC converges to a locally optimal feasible point of the CMDP | Two-timescale stochastic approximation |
| 5 | **Theorem** | Federated Convergence Rate: O(1/√(KT)) under non-IID data | Extension of FedAvg analysis to actor-critic |
| 6 | **Proposition** | Complexity Analysis: Per-agent per-step complexity is O(|O|·(|A₁|+|A₂|+|A₃|+|A₄|)) due to factored action space | Direct computation |
| 7 | **Lemma** | NDN Loop-Free Guarantee: PIT-based forwarding ensures no Data packet loops | By construction (NDN architecture) |

**Additional Mathematical Elements:**
- Lyapunov drift analysis for constraint satisfaction
- Regret bound analysis comparing MAFAC to optimal oracle policy
- Sensitivity analysis of AoI w.r.t. cache size, channel quality, vehicle density

---

## 6. Expected Impact

### Academic Impact
1. **First cross-layer AoI framework for NDN vehicular networks** — fills a clear research gap
2. **4 formal theorems** providing mathematical foundations for NDN-AoI-MARL integration
3. **Federated MARL** with privacy-preserving critic sharing and convergence guarantees
4. Publishable in **IEEE TWC** due to heavy physical/MAC layer analysis and optimization theory

### Practical Impact
1. **Reduced information staleness** in safety-critical vehicular applications (expected 30-50% AoI reduction)
2. **Distributed implementation** — no central controller needed, scalable to dense traffic
3. **Backward compatible** with C-V2X Mode 4 / NR-V2X standards
4. **libsumo-based validation** with realistic traffic scenarios

### Comparison Targets (Performance Evaluation)
- vs. No-cache baseline (pure V2X AoI optimization)
- vs. NDN with random/LRU caching (no AoI awareness)
- vs. Centralized AoI optimization (performance upper bound)
- vs. Independent Q-learning (no federated aggregation)
- vs. SAC/TD3 single-agent (no multi-agent coordination)

---

## 7. Storyline

### Paper Flow:

**Section I: Introduction**
- Motivation: Time-sensitive vehicular applications → AoI as key metric
- Gap: NDN's caching can help but also hurt AoI (stale cache); no existing work combines NDN+AoI+MARL
- Contribution list (C1, C2, C3)

**Section II: Related Work**
- AoI in vehicular networks (IP-based studies)
- NDN in vehicular networks (caching, forwarding)
- MARL for vehicular resource management
- Gap table showing our unique 3-way intersection

**Section III: System Model and Problem Formulation**
- 3.1 Network model (RSU, vehicles, NDN stack, content model)
- 3.2 Channel model (path loss, Rician/Nakagami fading, SINR)
- 3.3 C-V2X MAC model (SPS, collision probability, CBR)
- 3.4 NDN-AoI formulation (Δ^{NDN}, cache-aware AoI, Theorems 1-2)
- 3.5 CMDP formulation (state, action, reward, constraints, Lagrangian)

**Section IV: MAFAC Algorithm**
- 4.1 Factored actor-critic architecture
- 4.2 Policy gradient with Lagrangian advantage
- 4.3 Federated critic aggregation (inverse AoI weighting)
- 4.4 Convergence analysis (Theorems 3-5)
- 4.5 Complexity analysis (Proposition 6)

**Section V: Performance Evaluation**
- 5.1 Simulation setup (libsumo, channel parameters, NDN parameters)
- 5.2 Model verification (validate Theorems 1-2 against simulation)
- 5.3 Convergence behavior (training curves, constraint satisfaction)
- 5.4 AoI performance comparison (vs. 5 baselines)
- 5.5 Ablation study (caching effect, federated effect, factored action effect)
- 5.6 Sensitivity analysis (vehicle density, cache size, channel quality)

**Section VI: Conclusion**
- Summary of contributions and key findings
- Future work: extension to multi-hop, UAV relay, 6G THz channels
