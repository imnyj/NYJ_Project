# BRIEFING — 2026-08-26T22:01:00+09:00

## Mission
Investigate Python environment, RL requirements (R1/R2), mathematical formulations, and architectural designs for 9 baseline RL models and the hybrid RL interface in paper4.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2
- Original parent: f92a0429-1190-4b31-8c7e-330da3ef61f8
- Milestone: Explorer Survey 2 - RL Interface & Baselines Requirement Exploration

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify existing source code.
- Write metadata and reports ONLY into /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/.
- Use Korean for report and findings.

## Current Parent
- Conversation ID: f92a0429-1190-4b31-8c7e-330da3ef61f8
- Updated: not yet

## Investigation State
- **Explored paths**:
  - Python Environment & Libraries (`/usr/bin/python3`, `/home/imnyj/venv/bin/python`, PyTorch 2.12.0/2.11.0, CUDA 13.0, 4x RTX 3090)
  - `aoi_scheduling_design.md` (System specifications, SMDP event-driven, hybrid actions, error integral)
  - `workflow.md`, `README_S1.md`, `README_S2.md`, `progress_sync.md`
  - `src/aoi_env.py` (S1/S2 environment, E1/E2/E3 events, RSU tracking, estimation error)
  - `src/Communications.py` (Rayleigh fading SINR, subchannel interference model)
  - `src/NetSim.py` (TraCI TLS extraction, `getNextTLS`, `getNextSwitch`, lane-TLS matching)
  - `src/model.py` (Legacy TF implementation analysis)
- **Key findings**:
  1. Hardware & Framework: 4x RTX 3090 GPUs (96GB total VRAM) available. Pure PyTorch + CleanRL style design is optimal.
  2. R1 Signal Prediction (S2.5): `sumo.vehicle.getNextTLS(vid)` and `sumo.trafficlight.getNextSwitch(tls_id)` provide exact TLS state, stopline distance, and time left. Solves the "Stationary Trap" by predicting acceleration/deceleration inflection points.
  3. R2 State Vectorization: 16-dimensional strictly causal RSU-observable state vector with rigorous normalization. Zero ground truth leakage.
  4. R2 Action Space & Retrospective Transitions: Hybrid action tuple $(\Delta, ch, p)$ formulated as Semi-Markov Decision Process (SMDP) with variable discount $\gamma^{\Delta}$ and retrospective error integration over $[t_{\text{prev}}, t_{\text{now}}]$.
  5. 9 Baseline RL Models: Categorized into (1) Basic Hybrid (H-PPO, H-SAC, H-TD3), (2) Advanced Hybrid (MAPPO, HyAR/Branching PPO, P-DQN), (3) AoI/V2I Domain SOTA (Pure-AoI Whittle/Greedy, Deep Dueling Q-AoI, SAC-AoI).
- **Unexplored areas**: None for Survey 2 scope. Ready for handoff synthesis.

## Key Decisions Made
- Formulated exact 16-dim state feature vector and SMDP transition structure.
- Designed comprehensive architectures, policy parameterizations, and loss functions for all 9 baseline models.
- Established clean mathematical equations and independent verification strategies.

## Artifact Index
- `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/DISPATCH.md` — Initial dispatch message
- `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/BRIEFING.md` — Persistent briefing state
- `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/progress.md` — Liveness heartbeat and progress
- `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/handoff.md` — Final 5-component handoff report
