# Forensic Audit Report — Paper4 M1 (Checkpoint Resume & Model Training)

**Audit Target**: `code/run_parallel_evaluation.py`, DRL Agent Implementations, Training Log Artifacts, and Process/Concurrency Compliance  
**Auditor Agent**: `auditor_m1_1`  
**Integrity Mode**: `benchmark` (Strict Benchmark Mode from `ORIGINAL_REQUEST.md`)  
**Date**: 2026-08-11  
**Verdict**: **CLEAN**  

---

## 1. Observation

### 1.1 Source Code Static Analysis (`code/run_parallel_evaluation.py`)
- **Checkpoint Resume Implementation**:
  Lines 129–139 of `code/run_parallel_evaluation.py` inspect existing `*_convergence.csv` logs, parse the maximum episode integer value `last_ep`, and assign `start_ep`:
  ```python
  start_ep = 0
  if os.path.exists(log_path):
      with open(log_path, 'r') as f:
          lines = [line.strip() for line in f.readlines() if line.strip()]
          if len(lines) > 1:
              try:
                  last_ep = int(lines[-1].split(',')[0])
                  start_ep = last_ep
              except (ValueError, IndexError):
                  start_ep = len(lines) - 1
  ```
- **Skipping Completed Models**:
  Line 140 checks `if start_ep >= TOTAL_EPISODES:` and skips training if model already completed 100 episodes.
- **Weight Checkpointing & Epsilon Recovery**:
  Lines 149–161 attempt `agent.load(model_path)` if checkpoint file exists. If missing but `start_ep > 0`, it decays `epsilon` proportionally (`agent.epsilon * (agent.epsilon_decay ** start_ep)`).
- **Append Mode CSV & Intermediate Saving**:
  Line 168 writes CSV headers only when `start_ep == 0`. Line 204 opens CSV in `'a'` append mode. Line 208 executes `agent.save(model_path)` inside the episode loop after every completed episode.
- **Multiprocessing Process Isolation**:
  Line 297 enforces `mp.set_start_method('spawn', force=True)` in `main()` to prevent C++ `libsumo` state collisions across parallel Python workers.

### 1.2 Model & Reward Authenticity Check
- **RL Agent Implementations**: Inspection of all 14 RL agent definitions (`resnet_moe_agent.py`, `qlearning_agent.py`, `sarsa_agent.py`, `actor_critic_agent.py`, `dqn_agent.py`, `ddqn_agent.py`, `dueling_dqn_agent.py`, `ddpg_agent.py`, `ppo_agent.py`, `sac_agent.py`, `td3_agent.py`, `dt_agent.py`, `mappo_agent.py`, `moe_agent.py`) verified genuine neural network / tabular algorithms:
  - `ResNetMoEAgent`: Uses `ResNetFeatureExtractor` (residual blocks), `DuelingExpert` streams, `Softmax` gating network with load balancing loss (`cv_squared`), target network updates, experience replay, and PyTorch Adam optimizer (`lr=1e-3`).
  - No dummy, hardcoded, or facade implementations were found in any of the 14 RL agents.
- **Dynamic Reward Computation**:
  Rewards are calculated dynamically inside `ai_dcc_hook.py` (e.g., `DuelingDQNHook.predict` line 159: `reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam`) based on real-time SUMO simulation metrics from `SimulationRunner`. No hardcoded reward arrays or pre-cooked metrics exist.

### 1.3 Behavioral & Runtime Verification
- **Active Process Tracking**:
  `ps aux | grep run_parallel_evaluation.py` confirmed parent process PID `891423` running `code/run_parallel_evaluation.py` with 4 worker child processes (PIDs `891449`, `891450`, `891451`, `891452`), accumulated CPU runtime ~1 hr 55 min each.
- **Data Model Artifacts**:
  Verified live progress in `/home/imnyj/Workspace/paper4/data/models/`:
  - `QLearning_convergence.csv` (68 rows, ep 68) & `QLearning.pkl` (6.4 MB)
  - `SARSA_convergence.csv` (68 rows, ep 68) & `SARSA.pkl` (6.4 MB)
  - `VanillaDQN_convergence.csv` (54 rows, ep 54) & `VanillaDQN.pth` (80.5 KB)
  - `ActorCritic_convergence.csv` (37 rows, ep 37) & `ActorCritic.pth` (81.6 KB)
  - Remaining 10 models: No pre-populated fake CSV/pth files exist (they will be queued as worker processes finish).

### 1.4 GEMINI Rules, Locking & Audit Logger Compliance
- **File Locking (`LockManager`)**:
  Inspected `/home/imnyj/Workspace/paper4/backup/`: Found 4 timestamped backup snapshots created by `LockManager` before code modifications:
  - `run_parallel_evaluation.py.1786429989.bak`
  - `run_parallel_evaluation.py.1786430096.bak`
  - `run_parallel_evaluation.py.1786430187.bak`
  - `run_parallel_evaluation.py.1786430315.bak`
- **Audit Logging (`AuditLogger`)**:
  Inspected `/tmp/agent_audit.log`: Verified 4 log entries recorded by `worker_m1`:
  - `1786429994`: `MODIFY` `run_parallel_evaluation.py` — "Implemented checkpoint resume and intermediate weight saving in train_worker"
  - `1786430103`: `MODIFY` `run_parallel_evaluation.py` — "Set mp start method to spawn in main()"
  - `1786430198`: `MODIFY` `run_parallel_evaluation.py` — "Updated episode progress print frequency to per-episode"
  - `1786430320`: `MODIFY` `run_parallel_evaluation.py` — "Added flush=True to episode progress logging in train_worker"

---

## 2. Logic Chain

1. **Premise**: In Benchmark Mode, a deliverable is valid ONLY IF code, training, and simulation logic are genuine, without hardcoding, facade patterns, or rule violations (file locking & audit logging).
2. **Observation**:
   - Code inspection of `run_parallel_evaluation.py` confirms real resume logic (reading CSV row count, appending without corrupting headers, restoring decay states).
   - PyTorch model definitions in `code/` implement real loss functions, optimizers, and network layers.
   - Reward computation in `ai_dcc_hook.py` relies on `SimulationRunner` SUMO step outputs (`cbr_smoothed`, `dt_since_last_cam`).
   - File backup snapshots in `backup/` prove `LockManager` was executed before modifying files.
   - JSON entries in `/tmp/agent_audit.log` prove `AuditLogger` registered all edits.
   - Runtime monitoring shows 4 active Python worker processes generating real weights and CSV records on disk.
3. **Deduction**: `worker_m1` fulfilled all M1 requirements authentically without taking prohibited shortcuts or violating system rules.
4. **Conclusion**: The M1 deliverable passes all integrity forensics checks under Benchmark Mode.

---

## 3. Caveats

1. **Non-M1 Heuristic Observation (`TinyMLPHook`)**:
   In `code/ai_dcc_hook.py` lines 45–59, `TinyMLPHook.predict()` computes neural network matrix multiplications (`W1`, `W2`, `W3`) but overrides the final output with a hardcoded rule (`if cbr_smoothed < 0.50`). `TinyMLPHook` is assigned to the non-RL `"Proposed"` baseline under `heuristic_methods` used during M2 evaluation sweeps. It does **NOT** affect M1 training of the 14 RL models. However, this should be remediated or noted prior to M2/M3 evaluation and graph generation.
2. **Execution Duration**:
   Full 100-episode training across all 14 models requires ~4–6 hours of total parallel wall-clock time due to dense SUMO V2X simulation steps (2000 steps per episode).

---

## 4. Conclusion

- **Verdict**: **CLEAN**
- All M1 requirements (Checkpoint Resume, Per-Episode Weight Saving, Process Isolation, real SUMO simulation training for 14 RL models) are authentically implemented and operating correctly.
- File locking (`LockManager`) and audit logging (`AuditLogger`) regulations were strictly respected.

---

## 5. Verification Method

To independently verify this audit verdict:

1. **Verify Python Syntax**:
   ```bash
   /home/imnyj/venv/bin/python -m py_compile /home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py
   ```
2. **Check Audit Log Records**:
   ```bash
   grep "worker_m1" /tmp/agent_audit.log
   ```
3. **Inspect Backups**:
   ```bash
   ls -la /home/imnyj/Workspace/paper4/backup/run_parallel_evaluation.py*
   ```
4. **Inspect Live Training Models & CSV Rows**:
   ```bash
   /home/imnyj/venv/bin/python -c "
   import os, pandas as pd
   models_dir = '/home/imnyj/Workspace/paper4/data/models'
   for f in sorted(os.listdir(models_dir)):
       if f.endswith('_convergence.csv'):
           df = pd.read_csv(os.path.join(models_dir, f))
           print(f'{f:30s}: {len(df)} rows | max ep={df[\"Episode\"].max()}')
   "
   ```
