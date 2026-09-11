# Section III. System Model

## III. System Model

We consider a Content-Centric Vehicular Network (CCVN) in which a set of Road-Side Units (RSUs) $\mathcal{R} = \{r_1, r_2, \ldots, r_M\}$ are deployed at fixed intervals along a road segment. Each RSU $r_i$ maintains a circular communication coverage of radius $\rho$, enabling Vehicle-to-Infrastructure (V2I) communication with any vehicle within its range. Vehicles traverse the road following a unidirectional mobility model, passing through successive RSU coverage zones in sequence. At any given time instant $t$, a vehicle $v$ is associated with at most one RSU, referred to as the *current RSU* $r_\text{cur}$, while the immediately subsequent RSU in the vehicle's trajectory is denoted the *next RSU* $r_\text{nxt}$.

Given the vehicle's state observed at time $t_0$, the prediction task is defined as estimating two scalar dwell times: the *current RSU dwell time* $\tau_\text{cur} = t_\text{cur\_out} - t_0$, representing the remaining time until the vehicle exits the coverage of $r_\text{cur}$, and the *next RSU dwell time* $\tau_\text{nxt} = t_\text{nxt\_out} - t_\text{nxt\_in}$, representing the full sojourn duration within $r_\text{nxt}$. The prediction target is thus the vector $\mathbf{y} = [\tau_\text{cur},\, \tau_\text{nxt}]^\top \in \mathbb{R}^2$. To support this prediction, the input observation $\mathbf{X}$ is decomposed into three semantically distinct branches: a kinematic branch $\mathbf{X}^K$ encoding vehicle speed and distance-to-boundary features, a traffic-control branch $\mathbf{X}^T$ capturing traffic signal states and associated waiting times, and a social branch $\mathbf{X}^S$ representing surrounding vehicle density and queue lengths. This decomposition forms the structural basis of the proposed ST-MBAN architecture.

Prediction is triggered exclusively by content request events: when a vehicle issues a content request to $r_\text{cur}$, a snapshot of the vehicle's current state is captured and fed to the model. This event-driven design avoids periodic inference overhead and ensures that computational resources are consumed only at decision-relevant moments. Furthermore, each RSU trains its own model instance independently, using only the observations collected within its communication coverage. This eliminates any dependency on a central server, reducing inference latency to the RSU level, and allows each model to implicitly internalize the local traffic characteristics of its intersection — including signal cycle timing and road geometry — without explicit parameterization of such factors.

### A. Input Variables

The input feature vector $\mathbf{X} = [\mathbf{X}^K,\, \mathbf{X}^T,\, \mathbf{X}^S]$ aggregates 25 variables across three branches. Table I enumerates each variable, its physical interpretation, and its branch assignment. Variables marked with a historical queue suffix are maintained as short-horizon running averages to smooth transient fluctuations.

**Table I: Input Feature Variables**

| Variable | Description | Branch |
|---|---|---|
| $r_\text{cov}$ | RSU communication coverage radius | K |
| $d_\text{rsu}$ | Inter-RSU distance | K |
| $\text{direct}$ | Vehicle direction relative to RSU ($-1$: approaching, $+1$: departing) | K |
| $d_{l,c}$ | Remaining distance to current RSU boundary | K |
| $d_{e,n}$ | Remaining distance to next RSU entry point | K |
| $d_{l,n}$ | Distance to next RSU exit boundary | K |
| $v_{c,a}$, $v_{n,a}$ | Mean vehicle speed within current/next RSU coverage (historical queue) | K |
| $v_\text{ahead\_avg}$ | Mean speed of vehicles ahead on the same edge | K |
| $d_\text{leader}$ | Distance to the leading vehicle | K |
| $v_\text{leader}$ | Speed of the leading vehicle | K |
| $t_\text{est}$ | SUMO-estimated traversal time for current edge | K |
| $\Delta_\text{lane}$ | Required lane changes to reach next RSU | K |
| $s_{c}$, $s_{n}$ | Traffic signal state at current/next RSU intersection (cyclical encoding) | T |
| $\Delta t_{c}$, $\Delta t_{n}$ | Time remaining until next signal phase change at current/next RSU | T |
| $q_{c}$, $q_{n}$ | Number of halting vehicles at current/next RSU intersection | T |
| $n_{t,0\text{--}3}$ | Vehicle count heading to next RSU from current and neighboring RSUs | S |
| $n_\text{cur}$, $n_\text{nxt}$ | Total vehicle count within current/next RSU coverage | S |
| $n_\text{ahead}$ | Number of vehicles ahead of the requesting vehicle on current edge | S |
| $\text{occ}_\text{cur}$, $\text{occ}_\text{nxt}$ | Lane occupancy rate at current/next RSU ($\in [0,1]$) | S |

### B. Prediction Target and Output Design

The model regresses directly onto $\mathbf{y} = [\tau_\text{cur},\, \tau_\text{nxt}]^\top$, where both components correspond to semantically self-contained sojourn durations that are the quantities of direct relevance to precaching decisions at the RSU level. This output design is a deliberate departure from the three-output formulation of the predecessor model, which predicts the current dwell time, the next RSU entry time, and the next RSU departure time as independent scalar outputs. That formulation introduces *uncertainty compounding*: the prediction errors of the entry and departure times accumulate when the usable sojourn duration at $r_\text{nxt}$ is computed as their difference, yielding a quantity whose error variance is strictly greater than that of either constituent prediction. We address this by directly targeting $\tau_\text{cur}$ and $\tau_\text{nxt}$, which eliminates error accumulation across dependent predictions and removes physically inconsistent outputs that arise from independently regressing correlated time points. The resulting two-dimensional output space is both more compact and more directly interpretable by the content prefetching scheduler.

---
*작성: Writer 에이전트 | Phase 1-B-2 | 2026-04-07*
