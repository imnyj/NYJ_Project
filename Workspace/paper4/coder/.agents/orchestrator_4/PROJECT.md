# Project: AoI-Aware V2I Uplink RL Scheduling Pipeline

## Architecture
- **Environment**: SUMO 1.20+ / libsumo micro-traffic simulation with TraCI integration (`src/aoi_env.py`, `src/sumo/`).
- **Physical/Channel**: C-V2X 5.9 GHz uplink, RSU Range = 300.0 m, step-length = 0.1 s (`src/NetSim.py`, `src/sumo/make_sumo_set.py`).
- **RL Interface**: Observation space $\in \mathbb{R}^{18}$ (`StateVectorizer`), Action space $\Delta \in [0.1, 45.0]\text{ s}, P \in [10.0, 23.0]\text{ dBm}$ (`ActionDecoder`) (`src/rl_interface.py`).
- **Reward Function**: 4-term penalized reward $R_t = -(w_1 \cdot \text{Norm}(e_t^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant})$ with Anti-Mocking Assertion A4.
- **Training & Hot-Swap**: Dual-model shadow hot-swap trainer with persistent `best_reward` in checkpoint `.pt` (`src/hot_swap_trainer.py`).
- **HPO & Evaluation**: Multi-seed Optuna search with $w_1 \dots w_4$ weight optimization and real vehicle speed tracking (`src/hpo.py`, `src/evaluate.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 4-term Reward & A4 Assertion | Re-add $I_{\text{redundant}}$, verify normalized $[0, 1]$ bounds, $R_t \le 0$, isclose match | M1 | Conversation.md:21-27, R1 |
| 2 | Generalized Power Norm | `(p - p_min) / (p_max - p_min)` with `P_MIN=10.0, P_MAX=23.0` | M1 | Conversation.md, R1 |
| 3 | Per-Vehicle Transmission Power | Eliminate `tx_powers[-1]` global bug, map per vehicle | M1 | Conversation.md, R1 |
| 4 | Checkpoint Resume `best_reward` | Persist `best_reward` in `.pt` checkpoint to prevent overwriting `best.pt` | M1 | R1 |
| 5 | Action Bounds Single Source of Truth | $P \in [10.0, 23.0]$ dBm, $\Delta \in [0.1, 45.0]$ s dynamically linked to SUMO Red phase | M2 | Conversation.md, R2 |
| 6 | 18D State Vectorizer | Strict 18 dimensions including `n_queue` and `heading` | M2 | Conversation.md:S1, R2 |
| 7 | RSU Range 300m Alignment | `RSU_RANGE = 300.0` across `NetSim.py`, `aoi_env.py`, `hot_swap_trainer.py`, `evaluate.py`, `rl_interface.py` | M3 | Conversation.md, R3 |
| 8 | SUMO step-length 0.1s Alignment | Fix `--step-length 1.0` CLI args to `0.1` across `NetSim.py`, `hot_swap_trainer.py`, `aoi_env.py` | M3 | Conversation.md, R3 |
| 9 | Real Vehicle Speed in Evaluation | Replace `"speed": 10.0` with `env.last_speeds.get(vid, 0.0)` in `evaluate.py` | M3 | R3 |
| 10 | Optuna $w_1 \dots w_4$ HPO | Add reward weights $w_1, w_2, w_3, w_4$ into Optuna search space in `hpo.py` | M3 | Conversation.md:31, R3 |
| 11 | Baseline Scraping | Delete `src/baselines/` directory and remove all imports/registry lookups | M4 | R4 |
| 12 | Test Suite Adaptation & E2E Audit | Adapt tests for 18D, clean up baseline tests, pass `pytest tests/`, Challenger & Forensic Audit | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Trainer & Env Core Fixes | `src/hot_swap_trainer.py`, `src/aoi_env.py` | none | IN_PROGRESS |
| M2 | Action & State Bounds | `src/rl_interface.py` | none | IN_PROGRESS |
| M3 | Knobs & HPO Alignment | `src/NetSim.py`, `src/sumo/make_sumo_set.py`, `src/evaluate.py`, `src/hpo.py` | M1, M2 | PLANNED |
| M4 | Baseline Scraping & Cleanup | `src/baselines/`, `run_all.py`, `evaluate.py`, `hpo.py`, `tests/` | M1, M2, M3 | PLANNED |
| M5 | E2E Verification & Forensic Audit | `tests/`, Adversarial Challenger, Forensic Auditor | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### `src/rl_interface.py` ↔ `src/aoi_env.py` & `src/hot_swap_trainer.py`
- `STATE_DIM = 18`
- `P_MIN = 10.0`, `P_MAX = 23.0`
- `DELTA_MIN = 0.1`, `DELTA_MAX = get_sumo_max_red_phase_duration()` (defaults to 45.0)
- `ActionDecoder(delta_min, delta_max, p_min, p_max, num_channels)`
- `StateVectorizer(rsu_range=300.0, v_max=30.0, a_max=5.0)` -> `(18,)` ndarray

### `src/aoi_env.py` & `src/hot_swap_trainer.py` ↔ Checkpoint
- Checkpoint dict keys: `"model_name"`, `"hparams"`, `"rest_state_dict"`, `"act_state_dict"`, `"training_steps"`, `"swap_count"`, `"best_reward"`

## Code Layout
- `src/aoi_env.py`: Gym/PettingZoo-compatible AoI V2I simulation environment.
- `src/hot_swap_trainer.py`: Shadow hot-swap RL trainer.
- `src/rl_interface.py`: State vectorizer (18D) and action decoder.
- `src/NetSim.py`: Network simulation and SUMO initialization interface.
- `src/sumo/`: SUMO configuration generator and network XML.
- `src/evaluate.py`: Evaluation runner and heuristic scheduler.
- `src/hpo.py`: Optuna hyperparameter optimization.
- `tests/`: Pytest unit and integration test suite.
