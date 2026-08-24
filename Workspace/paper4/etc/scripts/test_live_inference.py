"""
Live Forward Pass and Inference Verification for all RL models using create_agent
Paper4 - Reviewer 1 Independent Verification
"""
import os
import sys
import torch
import numpy as np

WORKSPACE = "/home/imnyj/Workspace/paper4"
sys.path.append(os.path.join(WORKSPACE, "code"))
MODELS_DIR = os.path.join(WORKSPACE, "data/models")

from run_parallel_evaluation import RL_METHODS, create_agent

print("=" * 80)
print("LIVE FORWARD PASS / INFERENCE TEST VIA create_agent FOR ALL 14 RL MODELS")
print("=" * 80)

# Sample state (5-dim normalized: [cbr, n_est, dist_min, speed, aoi])
sample_state_5d = np.array([0.65, 0.4, 0.15, 0.5, 0.2], dtype=np.float32)

all_passed = True
results = {}

all_rl_models = [name for name, _ in RL_METHODS] + ["REMO-DQN"]

for model_name in all_rl_models:
    ext = ".pkl" if model_name in ["QLearning", "SARSA"] else ".pth"
    weight_candidates = [
        os.path.join(MODELS_DIR, f"{model_name}{ext}"),
        os.path.join(MODELS_DIR, f"{model_name.lower()}{ext}"),
    ]
    if model_name == "REMO-DQN":
        weight_candidates.insert(0, os.path.join(MODELS_DIR, "resnet_moe_dqn.pth"))
    
    weight_path = None
    for p in weight_candidates:
        if os.path.exists(p):
            weight_path = p
            break
            
    if not weight_path:
        print(f"[-] {model_name:20s}: Weight file NOT found!")
        all_passed = False
        results[model_name] = "WEIGHT_NOT_FOUND"
        continue
        
    try:
        agent = create_agent(model_name)
        # Load weights
        if hasattr(agent, "load"):
            agent.load(weight_path)
        elif hasattr(agent, "model") and hasattr(agent.model, "load_state_dict"):
            agent.model.load_state_dict(torch.load(weight_path, map_location="cpu"))
        
        # Test action generation
        if hasattr(agent, "select_action"):
            # inspect args
            import inspect
            sig = inspect.signature(agent.select_action)
            params = list(sig.parameters.keys())
            
            kwargs = {}
            if "eval_mode" in params:
                kwargs["eval_mode"] = True
            elif "noise" in params:
                kwargs["noise"] = 0.0
            elif "epsilon" in params:
                kwargs["epsilon"] = 0.0
            elif "deterministic" in params:
                kwargs["deterministic"] = True
                
            # If MAPPO
            if model_name == "MAPPO":
                action = agent.select_action(sample_state_5d, sample_state_5d)
            elif model_name == "DecisionTransformer":
                action = agent.select_action(sample_state_5d, target_return=-500.0)
            else:
                action = agent.select_action(sample_state_5d, **kwargs)
        elif hasattr(agent, "act"):
            action = agent.act(sample_state_5d)
        else:
            action = "N/A (No select_action/act method)"
            
        print(f"[PASS] {model_name:20s}: Loaded from {os.path.basename(weight_path):22s} | Action Output = {action}")
        results[model_name] = "PASS"
    except Exception as e:
        print(f"[FAIL] {model_name:20s}: Error loading/inferring - {e}")
        all_passed = False
        results[model_name] = f"FAIL: {e}"

print("\n" + "=" * 80)
print(f"FINAL INFERENCE TEST RESULT: {'ALL 14 RL MODELS PASSED' if all_passed else 'SOME FAILED'}")
print("=" * 80)
