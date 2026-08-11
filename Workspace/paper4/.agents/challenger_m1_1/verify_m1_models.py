import os
import sys
import torch
import numpy as np
import pickle
import traceback
import pandas as pd

# Add code directory to path
sys.path.append("/home/imnyj/Workspace/paper4/code")

from run_parallel_evaluation import create_agent, rl_methods
from ai_dcc_hook import get_hook

MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"
CODE_DIR = "/home/imnyj/Workspace/paper4/code"

CODE_WEIGHT_MAP = {
    "QLearning": "qlearning_model.pkl",
    "SARSA": "sarsa_model.pkl",
    "ActorCritic": "actor_critic.pth",
    "VanillaDQN": "vanilla_dqn.pth",
    "DoubleDQN": "ddqn.pth",
    "DuelingDQN": "dueling_dqn.pth",
    "DDPG": "ddpg_model.pth",
    "PPO": "ppo.pth",
    "SAC": "sac.pth",
    "TD3": "td3.pth",
    "DecisionTransformer": "dt_model.pth",
    "MAPPO": "mappo.pth",
    "MoEDQN": "moe_dqn.pth",
    "REMO-DQN": "resnet_moe_dqn.pth"
}

def check_tensor_nan_inf(tensor):
    """Check PyTorch tensor or numpy array for NaN and Inf."""
    nan_found = False
    inf_found = False
    if isinstance(tensor, torch.Tensor):
        nan_found = bool(torch.isnan(tensor).any())
        inf_found = bool(torch.isinf(tensor).any())
    elif isinstance(tensor, np.ndarray):
        nan_found = bool(np.isnan(tensor).any())
        inf_found = bool(np.isinf(tensor).any())
    return nan_found, inf_found

def inspect_agent_parameters_recursive(obj, visited=None):
    """Recursively search object for PyTorch modules, parameters, buffers, and Q-tables."""
    if visited is None:
        visited = set()
    
    obj_id = id(obj)
    if obj_id in visited:
        return 0, 0, 0
    visited.add(obj_id)
    
    total_checked = 0
    nan_count = 0
    inf_count = 0
    
    if isinstance(obj, torch.nn.Module):
        for name, param in obj.named_parameters():
            total_checked += 1
            n, i = check_tensor_nan_inf(param)
            if n: nan_count += 1
            if i: inf_count += 1
        for name, buf in obj.named_buffers():
            total_checked += 1
            n, i = check_tensor_nan_inf(buf)
            if n: nan_count += 1
            if i: inf_count += 1
    elif hasattr(obj, 'q_table'):
        q = getattr(obj, 'q_table')
        if isinstance(q, dict):
            for k, v in q.items():
                total_checked += 1
                n, i = check_tensor_nan_inf(np.array(v))
                if n: nan_count += 1
                if i: inf_count += 1
        elif isinstance(q, (np.ndarray, torch.Tensor)):
            total_checked += 1
            n, i = check_tensor_nan_inf(q)
            if n: nan_count += 1
            if i: inf_count += 1
            
    # Inspect sub-attributes
    if hasattr(obj, '__dict__'):
        for attr_name, attr_val in obj.__dict__.items():
            if attr_name.startswith('_'): continue
            if isinstance(attr_val, (torch.nn.Module, torch.Tensor, np.ndarray, dict, object)) and not isinstance(attr_val, (str, int, float, bool, type(None))):
                sub_tot, sub_nan, sub_inf = inspect_agent_parameters_recursive(attr_val, visited)
                total_checked += sub_tot
                nan_count += sub_nan
                inf_count += sub_inf

    return total_checked, nan_count, inf_count

def run_inference_with_hook(agent, name, hook_name, num_tests=50):
    """Run random state inference through ai_dcc_hook interface and direct agent calls."""
    success_count = 0
    
    try:
        hook = get_hook(hook_name)
        hook.set_agent(agent)
        hook.is_training = False
        
        for i in range(num_tests):
            np.random.seed(i)
            cbr_g = float(np.random.uniform(0.1, 0.9))
            n_neigh = float(np.random.uniform(10, 100))
            v_norm = float(np.random.uniform(0.0, 1.0))
            dt_cam = float(np.random.uniform(0.1, 1.0))
            cbr_smooth = float(np.random.uniform(0.1, 0.9))
            vid = f"veh_{i}"
            
            t_act, p_act = hook.predict(cbr_g, n_neigh, v_norm, dt_cam, cbr_smooth, vid=vid)
            
            # Check outputs
            if not np.isnan(t_act) and not np.isinf(t_act) and not np.isnan(p_act) and not np.isinf(p_act):
                if 0.05 <= t_act <= 2.0 and 0.0 <= p_act <= 35.0:
                    success_count += 1
                else:
                    print(f"    [WARN] Out of bounds action: t_act={t_act}, p_act={p_act}")
    except Exception as e:
        print(f"    [ERROR] Hook inference failed: {e}")
        
    return success_count, num_tests

def main():
    print("==========================================================================")
    print(" PAPER4 M1 EMPIRICAL MODEL VERIFICATION HARNESS")
    print("==========================================================================")
    
    results = {}
    
    for name, hook_name in rl_methods:
        ext = ".pkl" if name in ["QLearning", "SARSA"] else ".pth"
        primary_path = os.path.join(MODELS_DIR, f"{name}{ext}")
        fallback_filename = CODE_WEIGHT_MAP.get(name, f"{name}{ext}")
        fallback_path = os.path.join(CODE_DIR, fallback_filename)
        
        in_data_models = os.path.exists(primary_path)
        in_code_dir = os.path.exists(fallback_path)
        
        res = {
            "name": name,
            "hook_name": hook_name,
            "in_data_models": in_data_models,
            "in_code_dir": in_code_dir,
            "load_status_data_models": "NOT_PRESENT",
            "load_status_fallback": "NOT_PRESENT",
            "nan_found": False,
            "inf_found": False,
            "tensors_checked": 0,
            "inference_rate": 0.0,
            "csv_max_ep": 0,
            "error": None
        }

        # Check CSV
        csv_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if not df.empty and "Episode" in df.columns:
                    res["csv_max_ep"] = int(df["Episode"].max())
            except Exception:
                pass

        # Test agent creation & load in data/models
        agent = None
        if in_data_models:
            try:
                agent = create_agent(name)
                agent.load(primary_path)
                res["load_status_data_models"] = "SUCCESS"
            except Exception as e:
                res["load_status_data_models"] = f"FAIL: {str(e)}"
        
        # Test load fallback in code/ if not in data/models or failed
        if agent is None and in_code_dir:
            try:
                agent = create_agent(name)
                agent.load(fallback_path)
                res["load_status_fallback"] = "SUCCESS"
            except Exception as e:
                res["load_status_fallback"] = f"FAIL: {str(e)}"

        if agent is not None:
            # Check Tensors / Parameters
            tot, n_cnt, i_cnt = inspect_agent_parameters_recursive(agent)
            res["tensors_checked"] = tot
            if n_cnt > 0: res["nan_found"] = True
            if i_cnt > 0: res["inf_found"] = True

            # Run Hook Inference Test
            succ, total = run_inference_with_hook(agent, name, hook_name, num_tests=50)
            res["inference_rate"] = succ / total
        else:
            res["error"] = "Agent could not be loaded from data/models or code/"

        results[name] = res

    # Output Detailed Report Matrix
    print("\n=================================================================================================")
    print(f"{'Model Name':20s} | {'data/models File':16s} | {'data/models Load':16s} | {'Fallback Load':16s} | {'NaN/Inf':8s} | {'Infer Rate':10s} | {'CSV MaxEp':8s}")
    print("-------------------------------------------------------------------------------------------------")
    
    all_models_ready = True
    for name, r in results.items():
        dm_file = "PRESENT" if r["in_data_models"] else "MISSING"
        dm_load = r["load_status_data_models"]
        if len(dm_load) > 16: dm_load = dm_load[:13] + "..."
        fb_load = r["load_status_fallback"]
        if len(fb_load) > 16: fb_load = fb_load[:13] + "..."
        
        nan_inf = "FAIL" if (r["nan_found"] or r["inf_found"]) else "PASS"
        inf_str = f"{r['inference_rate']*100:.0f}%"
        csv_ep = str(r["csv_max_ep"])
        
        print(f"{name:20s} | {dm_file:16s} | {dm_load:16s} | {fb_load:16s} | {nan_inf:8s} | {inf_str:10s} | {csv_ep:8s}")
        
        if not r["in_data_models"] or r["load_status_data_models"] != "SUCCESS" or r["nan_found"] or r["inf_found"] or r["inference_rate"] < 1.0:
            all_models_ready = False

    print("-------------------------------------------------------------------------------------------------")
    print("FINAL VERIFICATION DECISION:", "APPROVE" if all_models_ready else "REJECT")
    
    return 0 if all_models_ready else 1

if __name__ == "__main__":
    sys.exit(main())
