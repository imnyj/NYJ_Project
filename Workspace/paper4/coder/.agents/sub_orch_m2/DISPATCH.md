# DISPATCH LOG

## 2026-08-26T22:08:42Z
You are the Sub-Orchestrator for Milestone 2: RL Agent Interface & 9 Baselines.

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/sub_orch_m2/
Project root: /home/imnyj/Workspace/paper4/coder
Original Request: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md
Project Plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md
Test Spec: /home/imnyj/Workspace/paper4/coder/TEST_READY.md

Your Mission (Milestone 2):
1. Implement `src/rl_interface.py`:
   - `StateVectorizer`: 16-dimensional normalized observation vector $[-1.0, 1.0]$ or $[0.0, 1.0]$ from RSU perspective (Age, velocities, speed, accel, relative coords, RSU dist, TLS state one-hot, phase time left, stopline dist, active vehs, CBR, imminent grants). Strictly NO future/ground-truth error leakage.
   - `ActionDecoder`: Decode hybrid action space into $(\Delta_i \in [0.5, 10.0]\text{s}, ch_i \in \{0, 1, 2, 3\}, p_i \in [20.0, 30.0]\text{dBm})$.
   - `RetrospectiveReplayBuffer`: SMDP retrospective transition assembly $(s, a, R, s', done, \Delta)$ with variable-interval discount $\gamma^{\Delta}$.
2. Implement all 9 PyTorch baseline models in `src/baselines/`:
   - Category 1 (Basic 3종):
     * `hybrid_ppo.py`: Hybrid PPO with discrete Categorical head and continuous Gaussian heads.
     * `hybrid_sac.py`: Hybrid SAC with Gumbel-Softmax discrete head and Squashed Gaussian continuous heads, auto-tuned alpha.
     * `hybrid_td3.py`: Hybrid TD3 with twin delayed Q-networks and target action smoothing.
   - Category 2 (Latest 3종):
     * `mappo.py`: Multi-Agent PPO with Centralized Critic (CTDE).
     * `hyar_ppo.py`: HyAR / Branching PPO with channel-conditioned continuous action heads.
     * `pdqn.py`: Multi-Pass Parameterized Action DQN (P-DQN / MP-DQN).
   - Category 3 (SOTA AoI 3종):
     * `pure_aoi.py`: Pure-AoI Whittle Index / Age-Greedy Scheduler baseline.
     * `dueling_q_aoi.py`: Deep Dueling Q-Network with quantized state-action value separation.
     * `sac_aoi.py`: Lyapunov AoI-penalized Maximum Entropy Actor-Critic.
   - `base_agent.py` and `__init__.py`: Clean unified class hierarchy (`select_action`, `update`, `save`, `load`).
3. Write comprehensive unit & integration tests in `tests/test_rl_interface.py` and `tests/test_baselines_instantiation.py`.
4. Run `/home/imnyj/venv/bin/pytest tests/ -v` and ensure all tests pass (including existing Tier 1-4 tests).
5. Ensure zero-tolerance integrity rules (genuine implementations, no hardcoding).
6. Write `handoff.md` and report back when Milestone 2 is complete.
