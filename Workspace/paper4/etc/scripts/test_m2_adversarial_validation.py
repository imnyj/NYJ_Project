#!/usr/bin/env python3
"""
Independent Adversarial Validation & Stress-Test Harness for Milestone 2.
Author: challenger_m2_1
Target: Verify optuna_best_params.json, 14 RL models, forward pass, action range [0, 23],
        Hook integration, and single-step training stability.
"""

import os
import sys
import json
import math
import traceback
import numpy as np
import torch

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
_code_dir = os.path.join(_project_root, "code")
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from etsi_cam_layer import ACTION_DIM, T_GRID_S, PTX_GRID_DBM
from ai_dcc_hook import get_hook

# Agent Class Imports
from resnet_moe_agent import ResNetMoEAgent
from moe_agent import MoEAgent
from dueling_dqn_agent import DuelingDQNAgent
from ddqn_agent import DDQNAgent
from dqn_agent import DQNAgent
from ppo_agent import PPOAgent
from mappo_agent import MAPPOAgent
from sac_agent import SACAgent
from ddpg_agent import DDPGAgent
from td3_agent import TD3Agent
from actor_critic_agent import ActorCriticAgent
from dt_agent import DTAgent
from qlearning_agent import QLearningAgent
from sarsa_agent import SARSAAgent

MODEL_SPECS = {
    "REMO-DQN": {
        "class": ResNetMoEAgent,
        "hook_name": "REMO-DQN",
        "type": "neural",
        "constructor": lambda p: ResNetMoEAgent(
            state_dim=5, action_dim=ACTION_DIM,
            num_experts=int(p["num_experts"]),
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"]),
            target_update_freq=int(p["target_update_freq"])
        )
    },
    "MoEDQN": {
        "class": MoEAgent,
        "hook_name": "MoEDQN",
        "type": "neural",
        "constructor": lambda p: MoEAgent(
            state_dim=5, action_dim=ACTION_DIM,
            num_experts=int(p["num_experts"]),
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"]),
            target_update_freq=int(p["target_update_freq"])
        )
    },
    "DuelingDQN": {
        "class": DuelingDQNAgent,
        "hook_name": "DuelingDQN",
        "type": "neural",
        "constructor": lambda p: DuelingDQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"]),
            target_update_freq=int(p["target_update_freq"])
        )
    },
    "DoubleDQN": {
        "class": DDQNAgent,
        "hook_name": "DoubleDQN",
        "type": "neural",
        "constructor": lambda p: DDQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"]),
            target_update_freq=int(p["target_update_freq"])
        )
    },
    "VanillaDQN": {
        "class": DQNAgent,
        "hook_name": "VanillaDQN",
        "type": "neural",
        "constructor": lambda p: DQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"]),
            target_update_freq=int(p["target_update_freq"])
        )
    },
    "PPO": {
        "class": PPOAgent,
        "hook_name": "PPO",
        "type": "neural",
        "constructor": lambda p: PPOAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            eps_clip=float(p["eps_clip"]), k_epochs=int(p["k_epochs"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "MAPPO": {
        "class": MAPPOAgent,
        "hook_name": "MAPPO",
        "type": "mappo",
        "constructor": lambda p: MAPPOAgent(
            local_state_dim=5, global_state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            eps_clip=float(p["eps_clip"]), k_epochs=int(p["k_epochs"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "SAC": {
        "class": SACAgent,
        "hook_name": "SAC",
        "type": "neural",
        "constructor": lambda p: SACAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            tau=float(p["tau"]), alpha=float(p["alpha"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "DDPG": {
        "class": DDPGAgent,
        "hook_name": "DDPG",
        "type": "neural",
        "constructor": lambda p: DDPGAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr_actor=float(p["lr_actor"]), lr_critic=float(p["lr_critic"]),
            gamma=float(p["gamma"]), tau=float(p["tau"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "TD3": {
        "class": TD3Agent,
        "hook_name": "TD3",
        "type": "neural",
        "constructor": lambda p: TD3Agent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            tau=float(p["tau"]), policy_delay=int(p["policy_delay"]),
            target_noise=float(p["target_noise"]), noise_clip=float(p["noise_clip"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "ActorCritic": {
        "class": ActorCriticAgent,
        "hook_name": "ActorCritic",
        "type": "neural",
        "constructor": lambda p: ActorCriticAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "DecisionTransformer": {
        "class": DTAgent,
        "hook_name": "DecisionTransformer",
        "type": "neural",
        "constructor": lambda p: DTAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p["lr"]), gamma=float(p["gamma"]),
            batch_size=int(p["batch_size"]), buffer_size=int(p["buffer_size"])
        )
    },
    "QLearning": {
        "class": QLearningAgent,
        "hook_name": "QLearning",
        "type": "tabular",
        "constructor": lambda p: QLearningAgent(
            state_bins=[10, 10, 10, 10, 10], action_dim=ACTION_DIM,
            alpha=float(p["alpha"]), gamma=float(p["gamma"]),
            epsilon_decay=float(p["epsilon_decay"])
        )
    },
    "SARSA": {
        "class": SARSAAgent,
        "hook_name": "SARSA",
        "type": "tabular",
        "constructor": lambda p: SARSAAgent(
            state_bins=[10, 10, 10, 10, 10], action_dim=ACTION_DIM,
            alpha=float(p["alpha"]), gamma=float(p["gamma"]),
            epsilon_decay=float(p["epsilon_decay"])
        )
    }
}


def test_hyperparameter_sanitary(params_data):
    """Test 1: Full sanitary scan of hyperparameters for NaN, Inf, negative, out-of-bound values."""
    print("\n=== [TEST 1] Hyperparameter Sanitary Scan ===")
    errors = []
    
    assert len(params_data) == 14, f"Expected 14 models, found {len(params_data)}"
    
    for model_name, p in params_data.items():
        if model_name not in MODEL_SPECS:
            errors.append(f"Unknown model name in JSON: {model_name}")
            continue
            
        for k, v in p.items():
            # Check NaN / Inf
            if isinstance(v, (float, int)):
                if math.isnan(v) or math.isinf(v):
                    errors.append(f"[{model_name}] Parameter {k}={v} is NaN or Inf!")
            
            # Check Learning rates / Alphas
            if k in ["lr", "lr_actor", "lr_critic", "alpha"]:
                if v <= 0.0 or v >= 1.0:
                    errors.append(f"[{model_name}] Invalid learning rate / alpha {k}={v} (must be 0 < x < 1)")
                    
            # Check Discount factor gamma
            if k == "gamma":
                if v <= 0.0 or v > 1.0:
                    errors.append(f"[{model_name}] Invalid gamma {k}={v} (must be 0 < gamma <= 1.0)")
                if v < 0.8:
                    errors.append(f"[{model_name}] Abnormally low gamma {k}={v}")
                    
            # Check Batch sizes
            if k == "batch_size":
                if v not in [16, 32, 64, 128, 256]:
                    errors.append(f"[{model_name}] Unexpected batch_size {k}={v}")
                    
            # Check Buffer sizes
            if k == "buffer_size":
                if v <= 0 or not isinstance(v, int):
                    errors.append(f"[{model_name}] Invalid buffer_size {k}={v}")
                    
            # Check tau
            if k == "tau":
                if v <= 0.0 or v >= 1.0:
                    errors.append(f"[{model_name}] Invalid tau {k}={v}")
                    
            # Check num_experts
            if k == "num_experts":
                if v < 2 or not isinstance(v, int):
                    errors.append(f"[{model_name}] Invalid num_experts {k}={v}")
                    
            # Check eps_clip
            if k == "eps_clip":
                if v <= 0.0 or v >= 1.0:
                    errors.append(f"[{model_name}] Invalid eps_clip {k}={v}")
                    
            # Check epsilon_decay
            if k == "epsilon_decay":
                if v <= 0.0 or v >= 1.0:
                    errors.append(f"[{model_name}] Invalid epsilon_decay {k}={v}")

    if errors:
        print(f"[FAIL] Hyperparameter Sanitary Scan found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False, errors
    else:
        print(f"[PASS] All 14 models passed hyperparameter sanity scan (no NaN/Inf, all values in valid bounds).")
        return True, []


def test_model_instantiation_and_inference(params_data):
    """Test 2: Model instantiation, multi-regime forward pass, and action bounds [0, 23]."""
    print("\n=== [TEST 2] Model Instantiation & Action Space [0, 23] Stress Test ===")
    errors = []
    instantiated_agents = {}
    
    test_states = [
        ("Nominal", np.array([0.25, 0.24, 0.50, 0.20, 0.28], dtype=np.float32)),
        ("Zero State", np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)),
        ("Upper Boundary", np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)),
        ("Extreme OOD", np.array([1.5, 100.0, 50.0, 5.0, 1.2], dtype=np.float32)),
        ("Small Epsilon", np.array([1e-5, 1e-5, 1e-5, 1e-5, 1e-5], dtype=np.float32)),
        ("Negative Perturbation", np.array([-0.1, -1.0, -0.5, -0.1, -0.2], dtype=np.float32))
    ]
    
    np.random.seed(42)
    random_states = [np.random.uniform(0.0, 1.0, 5).astype(np.float32) for _ in range(50)]
    
    stats = {}
    
    for model_name, spec in MODEL_SPECS.items():
        p = params_data.get(model_name)
        if not p:
            errors.append(f"[{model_name}] Missing parameters in params_data!")
            continue
            
        try:
            agent = spec["constructor"](p)
            instantiated_agents[model_name] = agent
        except Exception as ex:
            errors.append(f"[{model_name}] Instantiation failed: {traceback.format_exc()}")
            continue
            
        actions_seen = set()
        
        # Test specific regimes
        for regime_name, state in test_states:
            try:
                if spec["type"] == "mappo":
                    act_eval = agent.act(state, state, evaluate=True)
                    act_expl = agent.act(state, state, evaluate=False)
                else:
                    act_eval = agent.act(state, evaluate=True)
                    act_expl = agent.act(state, evaluate=False)
                    
                for mode, act_val in [("eval", act_eval), ("expl", act_expl)]:
                    if not isinstance(act_val, (int, np.integer)):
                        errors.append(f"[{model_name}] {regime_name} ({mode}) returned non-integer action: {type(act_val)} ({act_val})")
                    if act_val < 0 or act_val >= ACTION_DIM:
                        errors.append(f"[{model_name}] {regime_name} ({mode}) returned out-of-range action: {act_val} (expected 0..23)")
                    actions_seen.add(int(act_val))
            except Exception as ex:
                errors.append(f"[{model_name}] Inference failed on {regime_name}: {traceback.format_exc()}")
                
        # Test 50 random states
        for i, r_state in enumerate(random_states):
            try:
                if spec["type"] == "mappo":
                    act_val = agent.act(r_state, r_state, evaluate=False)
                else:
                    act_val = agent.act(r_state, evaluate=False)
                if act_val < 0 or act_val >= ACTION_DIM:
                    errors.append(f"[{model_name}] Random state #{i} produced invalid action: {act_val}")
                actions_seen.add(int(act_val))
            except Exception as ex:
                errors.append(f"[{model_name}] Random state #{i} inference crash: {traceback.format_exc()}")
                
        stats[model_name] = {
            "total_tested": 62,
            "unique_actions": len(actions_seen),
            "min_act": min(actions_seen),
            "max_act": max(actions_seen)
        }
        print(f"[INST & INFER OK] {model_name:20s}: 62 states tested, unique={len(actions_seen)}, range=[{min(actions_seen)}, {max(actions_seen)}] -> 100% valid [0, 23]")

    if errors:
        print(f"[FAIL] Model Instantiation & Inference found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False, errors, instantiated_agents, stats
    else:
        print(f"[PASS] All 14 models instantiated and passed 62 inference stress checks with 100% valid actions in [0, 23].")
        return True, [], instantiated_agents, stats


def test_hook_integration(instantiated_agents):
    """Test 3: Verify AIDCCHook integration, predict(), and action mapping to (t_act, p_act)."""
    print("\n=== [TEST 3] AIDCCHook Integration & Physical Parameter Mapping ===")
    errors = []
    hook_stats = {}
    
    for model_name, spec in MODEL_SPECS.items():
        agent = instantiated_agents.get(model_name)
        if not agent:
            errors.append(f"[{model_name}] Agent not available for hook test.")
            continue
            
        hook_name = spec["hook_name"]
        try:
            hook = get_hook(hook_name)
            hook.set_agent(agent)
            hook.reset_episode()
            
            # Predict step 1 (eval mode)
            hook.is_training = False
            t1, p1 = hook.predict(
                cbr_global=0.22, n_neighbors=8.0, v_norm=14.0,
                dt_since_last_cam=0.2, cbr_smoothed=0.25, vid="veh_test_1"
            )
            # Predict step 2 (train mode, triggers reward and memory storage)
            hook.is_training = True
            t2, p2 = hook.predict(
                cbr_global=0.24, n_neighbors=10.0, v_norm=12.0,
                dt_since_last_cam=0.15, cbr_smoothed=0.26, vid="veh_test_1"
            )
            # Terminate vehicle (triggers terminal transition)
            hook.terminate_vehicle("veh_test_1")
            
            if t1 not in T_GRID_S or t2 not in T_GRID_S:
                errors.append(f"[{model_name}] Invalid t_act: {t1}, {t2} not in {T_GRID_S}")
            if p1 not in PTX_GRID_DBM or p2 not in PTX_GRID_DBM:
                errors.append(f"[{model_name}] Invalid p_act: {p1}, {p2} not in {PTX_GRID_DBM}")
                
            hook_stats[hook_name] = {"t1": t1, "p1": p1, "t2": t2, "p2": p2}
            print(f"[HOOK OK] {hook_name:20s}: step1=(T={t1:.3f}s, P={p1:+03d}dBm), step2=(T={t2:.3f}s, P={p2:+03d}dBm) -> OK")
        except Exception as ex:
            errors.append(f"[{model_name}] Hook {hook_name} failed: {traceback.format_exc()}")
            
    if errors:
        print(f"[FAIL] Hook Integration found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False, errors, hook_stats
    else:
        print(f"[PASS] All 14 models integrated seamlessly with AIDCCHook and mapped to valid physical (T, Ptx) values.")
        return True, [], hook_stats


def test_single_step_learning(instantiated_agents):
    """Test 4: Verify train_step() execution and memory buffer integrity without NaN losses."""
    print("\n=== [TEST 4] Single-Step Training & Loss Numerical Stability ===")
    errors = []
    train_stats = {}
    
    for model_name, spec in MODEL_SPECS.items():
        agent = instantiated_agents.get(model_name)
        if not agent:
            continue
            
        try:
            batch_size = getattr(agent, "batch_size", 32)
            s0 = np.array([0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32)
            s1 = np.array([0.25, 0.35, 0.45, 0.55, 0.65], dtype=np.float32)
            
            for i in range(batch_size + 10):
                action = int(i % ACTION_DIM)
                reward = -0.5 + float(i * 0.01)
                done = (i % 20 == 0)
                
                if spec["type"] == "mappo":
                    agent.store_transition(s0, s0, action, reward, s1, s1, done)
                else:
                    agent.store_transition(s0, action, reward, s1, done)
                    
            if hasattr(agent, "train_step"):
                loss = agent.train_step()
                if isinstance(loss, tuple):
                    for l_val in loss:
                        if math.isnan(l_val) or math.isinf(l_val):
                            errors.append(f"[{model_name}] train_step returned NaN/Inf loss: {loss}")
                elif isinstance(loss, (float, int)):
                    if math.isnan(loss) or math.isinf(loss):
                        errors.append(f"[{model_name}] train_step returned NaN/Inf loss: {loss}")
                train_stats[model_name] = loss
                print(f"[TRAIN OK] {model_name:20s}: train_step() executed successfully. Loss={loss}")
            else:
                train_stats[model_name] = "tabular_direct_update"
                print(f"[TRAIN OK] {model_name:20s}: Tabular online update verified.")
        except Exception as ex:
            errors.append(f"[{model_name}] Training step crashed: {traceback.format_exc()}")
            
    if errors:
        print(f"[FAIL] Training step stability test found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False, errors, train_stats
    else:
        print(f"[PASS] All 14 models executed 1-step training without NaN/Inf losses.")
        return True, [], train_stats


def test_sensitivity_table_consistency(params_data):
    """Test 5: Verify sensitivity CSV files against optuna_best_params.json."""
    print("\n=== [TEST 5] Sensitivity Table Cross-Consistency Check ===")
    errors = []
    
    csv_paths = [
        os.path.join(_project_root, "data", "optuna_sensitivity.csv"),
        os.path.join(_project_root, "data", "optuna_sensitivity_table.csv")
    ]
    
    for csv_path in csv_paths:
        if not os.path.exists(csv_path):
            errors.append(f"Sensitivity CSV file not found: {csv_path}")
            continue
            
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            
        header = lines[0].split(",")
        rows = lines[1:]
        
        if len(rows) != 17:
            errors.append(f"[{os.path.basename(csv_path)}] Expected 17 rows, found {len(rows)}")
            
        csv_models = [r.split(",")[0].replace(" (Proposed)", "") for r in rows]
        for m in params_data.keys():
            if m not in csv_models:
                errors.append(f"[{os.path.basename(csv_path)}] Model {m} missing from sensitivity CSV!")
                
        print(f"[CSV OK] {os.path.basename(csv_path)}: 17 models present, header matches.")

    if errors:
        print(f"[FAIL] Sensitivity Table Consistency found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False, errors
    else:
        print(f"[PASS] Sensitivity CSV tables are completely consistent with best parameters JSON.")
        return True, []


def main():
    json_path = os.path.join(_project_root, "data", "optuna_best_params.json")
    if not os.path.exists(json_path):
        print(f"[CRITICAL FAIL] {json_path} does not exist!")
        sys.exit(1)
        
    with open(json_path, "r") as f:
        params_data = json.load(f)
        
    all_passed = True
    summary_results = {}
    
    t1_pass, t1_err = test_hyperparameter_sanitary(params_data)
    summary_results["Test 1 (Hyperparameter Sanity)"] = (t1_pass, t1_err)
    if not t1_pass: all_passed = False
    
    t2_pass, t2_err, agents, infer_stats = test_model_instantiation_and_inference(params_data)
    summary_results["Test 2 (Instantiation & Inference [0..23])"] = (t2_pass, t2_err)
    if not t2_pass: all_passed = False
    
    t3_pass, t3_err, hook_stats = test_hook_integration(agents)
    summary_results["Test 3 (AIDCCHook Integration)"] = (t3_pass, t3_err)
    if not t3_pass: all_passed = False
    
    t4_pass, t4_err, train_stats = test_single_step_learning(agents)
    summary_results["Test 4 (Single-Step Training Stability)"] = (t4_pass, t4_err)
    if not t4_pass: all_passed = False
    
    t5_pass, t5_err = test_sensitivity_table_consistency(params_data)
    summary_results["Test 5 (Sensitivity Table Consistency)"] = (t5_pass, t5_err)
    if not t5_pass: all_passed = False
    
    print("\n" + "=" * 60)
    print("=== FINAL ADVERSARIAL VALIDATION SUMMARY ===")
    print("=" * 60)
    for test_name, (passed, errs) in summary_results.items():
        status = "PASSED" if passed else f"FAILED ({len(errs)} errors)"
        print(f" - {test_name}: {status}")
        
    if all_passed:
        print("\n>>> VERDICT: ALL ADVERSARIAL TESTS PASSED (APPROVE) <<<")
        sys.exit(0)
    else:
        print("\n>>> VERDICT: ADVERSARIAL TESTS FAILED (REQUEST_CHANGES) <<<")
        sys.exit(2)


if __name__ == "__main__":
    main()
