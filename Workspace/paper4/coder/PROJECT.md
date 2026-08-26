# Project: Genuine SUMO V2I AoI RL Scheduling Pipeline

## Architecture
- **Environment Layer (Genuine SUMO + Channel + Dynamics)**:
  - `src/sumo/make_sumo_set.py`: SUMO network, TAZ, RSU, route, and configuration generator (`netconvert`).
  - `src/NetSim.py`: SumoNetSim TraCI wrapper driving real SUMO micro-simulation, vehicle telemetry, coordinates, and traffic light signals.
  - `src/Communications.py`: 5.9 GHz Rayleigh fading wireless channel model computing interference and packet success probability $P_{\text{succ}}$ via `judge_uplink()`.
  - `src/aoi_env.py`: Genuine Gymnasium-style V2I AoI scheduling environment with 4 hardcoded anti-mocking assertions, stepping real SUMO at every action.
  - `verify_environment.py`: Standalone environment verification script testing coordinate changes ($\Delta x \ne 0$) and communication calls inside real SUMO.
  - `src/dynamics_predictor.py` & `src/heuristic_scheduler.py`: Signal state ($I_{\text{stop}}, I_{\text{start}}$) prediction & heuristic rule-based scheduler.
- **RL Agent Interface & Replay Buffer**:
  - `src/rl_interface.py`: 16-dimensional normalized State Vectorizer (RSU perspective), Hybrid Action Space Decoder $(\Delta \in [0.5, 10.0], ch \in \{0..3\}, p \in [20.0, 30.0])$, SMDP Retrospective Replay Buffer with $\gamma^{\Delta t}$ discounting.
- **9 Baseline RL Algorithms**:
  - Category 1 (Basic 3종): `H-PPO` (`hybrid_ppo.py`), `H-SAC` (`hybrid_sac.py`), `H-TD3` (`hybrid_td3.py`)
  - Category 2 (Latest/Hybrid 3종): `MAPPO` (`mappo.py`), `HyAR-PPO` (`hyar_ppo.py`), `MP-DQN` (`pdqn.py`)
  - Category 3 (SOTA AoI 3종): `Pure-AoI` (`pure_aoi.py`), `Dueling-Q-AoI` (`dueling_q_aoi.py`), `SAC-AoI` (`sac_aoi.py`)
- **Hyperparameter Optimization (Optuna HPO)**:
  - `src/hpo.py`: Optuna-based multi-seed HPO runner directly connected to `aoi_env.py` (synthetic code discarded), exporting to `results/hpo/`.
- **Dual-Model Hot-swap Training Pipeline (200k Steps Ready)**:
  - `src/hot_swap_trainer.py`: Act mode (fast serving) + Rest mode (background training) with hardware isolation, zero-downtime hot-swap, TensorBoard (`SummaryWriter`) logging, checkpointing (`checkpoints/`), and 200,000 steps (2,000 steps * 100 episodes) architecture.
- **Evaluation Harness & Benchmark**:
  - `src/evaluate.py`: Multi-density (15-55 veh/km) and multi-seed evaluation harness using real SUMO simulation, logging to `results/eval/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Genuine SUMO Env Integration | `aoi_env.py` driven by `make_sumo_set.py`, `NetSim.py`, and `Communications.py` | M1 | R1 |
| 2 | Hardcoded Anti-Bypass Assertions | 4 strict runtime assertions in `step()` verifying SUMO coordinate shift, channel calls & reward | M1 | R1 |
| 3 | `verify_environment.py` | Verification tool testing coordinate changes and real simulation integration | M1 | R1 / R4 |
| 4 | 16-dim State Vectorizer | Normalized observation vector from RSU perspective (no leakage) | M2 | R2 |
| 5 | Hybrid Action Space Decoder | Decoding $(\Delta, ch, p)$ for hybrid continuous/discrete action heads | M2 | R2 |
| 6 | SMDP Retrospective Replay Buffer | Variable-interval discounted transition tuple buffer | M2 | R2 |
| 7 | Category 1 Baselines (Basic 3종) | PyTorch implementations of H-PPO, H-SAC, H-TD3 | M2 | R2 |
| 8 | Category 2 Baselines (Latest 3종) | PyTorch implementations of MAPPO, HyAR-PPO, MP-DQN | M2 | R2 |
| 9 | Category 3 Baselines (SOTA AoI 3종) | PyTorch implementations of Pure-AoI, Dueling-Q-AoI, SAC-AoI | M2 | R2 |
| 10 | 200k-Step Training Pipeline | Scalable 200,000-step training loop with TensorBoard logging & checkpoints | M3 | R3 |
| 11 | Genuine Optuna HPO Setup | Optuna search spaces and objective directly connected to `aoi_env.py` | M3 | R3 |
| 12 | Dual-Model Hot-swap Pipeline | Zero-downtime Act/Rest dual model serving and background training | M3 | R3 / R4 |
| 13 | Short Dummy Verification (10-step) | End-to-end 10-step verification test verifying all 9 models and pipeline without crash | M4 | R4 |
| 14 | Pre-Compute Halt & User Review | Strict halt protocol awaiting user manual code review before 200k heavy run | M5 | R4 / R6 |
| 15 | Progress Sync & Handover | Comprehensive `progress_sync.md` documenting architecture, best params & next steps | M5 | R7 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Genuine SUMO Environment & Anti-Mocking Assertions | Features 1, 2, 3 (`src/aoi_env.py`, `verify_environment.py`) | Survey (M0) | DONE |
| M2 | 9 Hybrid Baseline RL Models & RL Interface | Features 4, 5, 6, 7, 8, 9 (`src/rl_interface.py`, `src/baselines/`) | M1 | DONE |
| M3 | 200k-step Training, Hot-swap & Optuna HPO Setup | Features 10, 11, 12 (`src/hot_swap_trainer.py`, `src/hpo.py`, `src/evaluate.py`) | M1, M2 | DONE |
| M4 | Short Dummy Verification (10-step) & E2E Testing | Feature 13 (`verify_environment.py`, `tests/test_dummy_verification.py`) | M1..M3 | DONE |
| M5 | Multi-Reviewer, Challenger & Forensic Audit Gate | Gate verification for M1..M4 | M4 | DONE |
| M6 | Pre-Compute Halt, Code Review Preparation & Handover | Features 14, 15 (`progress_sync.md`, User report) | M5 | DONE |

## Interface Contracts
### `src/aoi_env.py` ↔ RL Models & Trainers
- Class: `AoiV2IEnv` (Gymnasium-compatible)
  - `reset(seed=None, options=None) -> tuple[dict[str, np.ndarray], dict]`
  - `step(action_dict: dict[str, tuple | np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, float], dict[str, bool], dict[str, bool], dict]`
  - Enforces 4 hardcoded assertions on SUMO timestep advance, coordinate displacement, `Communications.judge_uplink()` invocation, and reward computation.

### `verify_environment.py`
- Standalone verification script:
  - Invokes `AoiV2IEnv` for 20 steps.
  - Asserts coordinate delta $\Delta x > 0$ for active moving vehicles.
  - Asserts channel calculations executed.
  - Exits with status code 0 on success.

## Code Layout
```
/home/imnyj/Workspace/paper4/coder/
├── PROJECT.md
├── ORIGINAL_REQUEST.md
├── progress_sync.md
├── verify_environment.py
├── src/
│   ├── sumo/
│   │   ├── make_sumo_set.py
│   │   ├── generated.sumocfg
│   │   └── ...
│   ├── aoi_env.py
│   ├── NetSim.py
│   ├── Communications.py
│   ├── dynamics_predictor.py
│   ├── heuristic_scheduler.py
│   ├── rl_interface.py
│   ├── baselines/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── hybrid_ppo.py
│   │   ├── hybrid_sac.py
│   │   ├── hybrid_td3.py
│   │   ├── mappo.py
│   │   ├── hyar_ppo.py
│   │   ├── pdqn.py
│   │   ├── pure_aoi.py
│   │   ├── dueling_q_aoi.py
│   │   └── sac_aoi.py
│   ├── hpo.py
│   ├── hot_swap_trainer.py
│   └── evaluate.py
├── tests/
│   ├── test_dynamics_predictor.py
│   ├── test_rl_interface.py
│   ├── test_baselines_instantiation.py
│   ├── test_hot_swap.py
│   ├── test_dummy_verification.py
│   └── ...
└── results/
    ├── hpo/
    │   ├── optuna_best_params.csv
    │   └── optuna_trials_*.csv
    └── eval/
        ├── eval_raw_runs.csv
        ├── eval_summary_by_density.csv
        └── eval_leaderboard.csv
```
