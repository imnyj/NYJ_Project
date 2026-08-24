# Project: Paper4 V2X DCC REMO-DQN Simulation & Publication Pipeline

## Architecture
- **Environment**: SUMO 6x6 Urban Grid (`make_sumo_set.py`) + `libsumo` 100ms step mobility.
- **Wireless Channel**: IEEE 802.11p Log-distance Path Loss ($\alpha=2.0, PL_0=47.85\text{dB}$) + Nakagami-$m$ ($m=3$) fading + Local CBR collision factor ($\max(0.1, 1.0 - 0.8\times CBR)$).
- **Communication Protocol**: ETSI EN 302 637-2 CAM generation & decentralized congestion control (DCC).
- **Proposed Model**: REMO-DQN (5D State $\to$ 2-block ResNet $\to$ Softmax Gating Network + 3 Dueling Experts, 24 Actions).
- **Baselines (16 models)**: 13 RL models (`MoEDQN`, `DuelingDQN`, `DoubleDQN`, `VanillaDQN`, `PPO`, `MAPPO`, `SAC`, `DDPG`, `TD3`, `ActorCritic`, `DecisionTransformer`, `QLearning`, `SARSA`) + 3 Non-RL models (`Fixed 10Hz`, `ReactDCC`, `AdaptDCC`).
- **Parallel Computing Engine**: 4x NVIDIA RTX 3090 GPUs (24GB each), 10C/20T CPU, 128GB RAM, `multiprocessing(num_workers=16)` with isolated SUMO environments.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Distance-AoI Metric Export | 6 distance bins (0~300m, 50m intervals) real AoI tracking in `aoi_tracker.py` & `sim_engine.py` | M1 | Survey 1 |
| 2 | CBR Time Trace Logging | Per-step CBR history tracking and JSON export in `sim_engine.py` | M1 | Survey 1 |
| 3 | Latent & Gating Activation Extraction | `ResNetMoEAgent.get_latent_and_gate(state)` API for 128D latent vector and 3D gate weights | M1 | Survey 1 |
| 4 | Fake Data & Model Purge | Delete all `data/models/*.pth`, `*.pkl`, fake CSVs, and mock formulas | M2 | Survey 2 |
| 5 | Optuna Hyperparameter Re-Optimization | Fix `action_dim=24` and re-optimize 13 RL models across 4 GPUs, generating real sensitivity table | M2 | Survey 2 |
| 6 | 17 Models Full Retraining | Train all 17 models for 100 episodes x 2000 steps on negative penalty reward structure | M3 | Survey 2 |
| 7 | Massive Parallel Sweep (17,000 Episodes) | Run `run_density_sweep_parallel.py` across 17 models x 10 densities x 100 episodes | M4 | Survey 3 |
| 8 | 6 Real Evaluation Artifacts Extraction | `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json` | M4 | Survey 3 |
| 9 | Mock-Free `prepare_data.py` Refactoring | 100% real data processing without `np.random`, hardcoded arrays, or analytical mock formulas | M5 | Survey 3 |
| 10 | 22 Publication-Grade Visualizations | Generate 11 datasets in `data/` and 22 visual files (11 PNG @ 350 DPI + 11 PDF/TeX) in `visualizer/` | M5 | Survey 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Sim Engine & Metrics Audit / Fix | Fix `aoi_tracker.py`, `sim_engine.py`, `resnet_moe_agent.py` to enable real metric & activation extraction | None | DONE |
| M2 | Fake Data Purge & Optuna Re-Optimization | Purge corrupt models/CSVs, fix `action_dim=24`, re-optimize 13 RL models on 4 GPUs | M1 | DONE |
| M3 | 17 Models Full Retraining | Retrain 17 models for 100 ep x 2000 steps with negative reward structure, save authentic checkpoints | M2 | IN_PROGRESS |
| M4 | 17,000-Episode Parallel Evaluation Sweep | Execute `run_density_sweep_parallel.py` (16 workers, 4 GPUs) and extract 6 real data files | M3 | PLANNED |
| M5 | Authentic Visualizations Generation | Refactor `prepare_data.py` (0 mock, 0 `np.random`), generate 11 datasets & 22 visual artifacts (350 DPI) | M4 | PLANNED |
| E2E | Verification & Forensic Integrity Audit | Opaque-box E2E test harness, acceptance criteria verification, and Forensic Audit verification | M5 | PLANNED |

## Code Layout
- `code/sim_engine.py`: SUMO simulation engine, channel model, packet delivery, and metric logging.
- `code/aoi_tracker.py`: AoI tracking across active vehicle pairs, distance binning.
- `code/etsi_cam_layer.py`: ETSI CAM generation rules and DCC state machines.
- `code/resnet_moe_agent.py`: REMO-DQN neural network, feature extraction, gating, expert modules.
- `code/run_optuna_all_baselines.py` (or `code/optimize.py`): Optuna tuning scripts for 13 RL models.
- `code/train.py` / `code/train_all.py`: Multi-GPU training pipeline for 17 models.
- `code/run_density_sweep_parallel.py`: High-performance 17,000-episode evaluation harness.
- `visualizer/prepare_data.py`: Genuine data preparation pipeline reading real evaluation files.
- `visualizer/generate_visualizations.py`: Publication-grade rendering (350 DPI PNG + PDF).
- `data/models/`: Real trained checkpoint files (`.pth`, `.pkl`).
- `data/evaluation/`: Real evaluation outputs (`eval_density_results.csv`, JSON traces).
- `visualizer/`: 22 output files (11 PNGs + 11 PDFs/TeX).

## Interface Contracts
### `sim_engine.py` ↔ `aoi_tracker.py`
- `aoi_tracker.step(sim_time, vehicle_positions, cam_events, received_events)`
- `aoi_tracker.get_distance_aoi()` $\to$ `Dict[str, List[float]]` (6 bins: 25m, 75m, 125m, 175m, 225m, 275m)

### `resnet_moe_agent.py` ↔ Evaluation Harness
- `agent.get_latent_and_gate(state: np.ndarray)` $\to$ `Tuple[np.ndarray (128,), np.ndarray (3,)]`
