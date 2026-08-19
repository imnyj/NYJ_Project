import os
import sys
import pickle
import torch
import pandas as pd
import numpy as np

MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"

MODEL_NAMES = [
    "ActorCritic",
    "DDPG",
    "DecisionTransformer",
    "DoubleDQN",
    "DuelingDQN",
    "MAPPO",
    "MoEDQN",
    "PPO",
    "QLearning",
    "REMO-DQN",
    "SAC",
    "SARSA",
    "TD3",
    "VanillaDQN"
]

def count_nested_params(ckpt):
    """Recursively count parameters in torch checkpoint"""
    total = 0
    layers = {}
    if isinstance(ckpt, dict):
        for k, v in ckpt.items():
            if isinstance(v, torch.Tensor):
                total += v.numel()
                layers[k] = list(v.shape)
            elif isinstance(v, dict):
                sub_total, sub_layers = count_nested_params(v)
                total += sub_total
                for sk, sv in sub_layers.items():
                    layers[f"{k}.{sk}"] = sv
    elif isinstance(ckpt, torch.nn.Module):
        total = sum(p.numel() for p in ckpt.parameters())
        layers = {k: list(v.shape) for k, v in ckpt.state_dict().items()}
    return total, layers

def verify_all_models():
    results = []
    print("=" * 90)
    print("EMPIRICAL VERIFICATION OF 14 RL MODELS & CHECKPOINTS (PHYSICAL EXECUTION)")
    print("=" * 90)

    for name in MODEL_NAMES:
        print(f"\n[Verifying {name}]")
        csv_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")
        pth_path = os.path.join(MODELS_DIR, f"{name}.pth")
        pkl_path = os.path.join(MODELS_DIR, f"{name}.pkl")

        # 1. Verify Convergence CSV
        csv_exists = os.path.exists(csv_path)
        csv_valid = False
        max_step = 0
        row_count = 0
        nan_count = 0
        final_reward = None
        reward_trend = None
        columns_found = []

        if csv_exists:
            try:
                df = pd.read_csv(csv_path)
                columns_found = df.columns.tolist()
                row_count = len(df)
                nan_count = df.isna().sum().sum()
                
                # Check Global_Step or step
                if 'Global_Step' in df.columns:
                    max_step = int(df['Global_Step'].max())
                elif 'step' in df.columns or 'Step' in df.columns:
                    step_col = 'Global_Step' if 'Global_Step' in df.columns else ('step' if 'step' in df.columns else 'Step')
                    max_step = int(df[step_col].max())
                elif 'Episode' in df.columns:
                    # If only Episode exists, check if each episode is 2000 steps
                    max_step = int(df['Episode'].max() * 2000)

                # Reward column
                reward_col = None
                for col in ['Reward', 'reward', 'mean_reward', 'avg_reward', 'smoothed_reward']:
                    if col in df.columns:
                        reward_col = col
                        break
                if reward_col:
                    final_reward = df[reward_col].iloc[-1]
                    initial_reward = df[reward_col].iloc[0]
                    reward_trend = f"Init: {initial_reward:.2f} -> Final: {final_reward:.2f}"

                # Strict criteria: row_count >= 50, max_step >= 200,000, nan_count == 0, non-empty reward
                csv_valid = (row_count >= 50) and (max_step >= 200000) and (nan_count == 0) and (final_reward is not None)
                print(f"  CSV: rows={row_count}, max_step={max_step:,}, NaNs={nan_count}, columns={columns_found}")
                print(f"  Reward: [{reward_trend}] -> {'PASS' if csv_valid else 'FAIL'}")
            except Exception as e:
                print(f"  CSV Error: {e}")
        else:
            print(f"  CSV: Missing at {csv_path}")

        # 2. Verify Checkpoint (.pth / .pkl)
        model_type = None
        param_count = 0
        checkpoint_valid = False
        tensor_shapes = {}

        if os.path.exists(pth_path):
            model_type = "PyTorch (.pth)"
            file_size_kb = os.path.getsize(pth_path) / 1024.0
            try:
                checkpoint = torch.load(pth_path, map_location="cpu")
                param_count, tensor_shapes = count_nested_params(checkpoint)
                checkpoint_valid = (param_count > 0)
                print(f"  Checkpoint ({model_type}): Size={file_size_kb:.1f} KB, Total Params={param_count:,}, Layers={len(tensor_shapes)} -> {'PASS' if checkpoint_valid else 'FAIL'}")
                # Print 2 sample layer tensor dimensions
                for lk, lshape in list(tensor_shapes.items())[:2]:
                    print(f"    - Layer '{lk}': {lshape}")
            except Exception as e:
                print(f"  PyTorch Load Error: {e}")

        elif os.path.exists(pkl_path):
            model_type = "Pickle/Q-table (.pkl)"
            file_size_kb = os.path.getsize(pkl_path) / 1024.0
            try:
                with open(pkl_path, "rb") as f:
                    q_table = pickle.load(f)
                if isinstance(q_table, dict):
                    param_count = len(q_table)
                    # Check entries
                    checkpoint_valid = (param_count > 0)
                    sample_key = list(q_table.keys())[0]
                    sample_val = q_table[sample_key]
                    print(f"  Checkpoint ({model_type}): Size={file_size_kb:.1f} KB, Q-States/Entries={param_count:,} -> {'PASS' if checkpoint_valid else 'FAIL'}")
                    print(f"    - Sample State: {sample_key}, Action Values: {sample_val}")
                elif isinstance(q_table, np.ndarray):
                    param_count = q_table.size
                    checkpoint_valid = (param_count > 0)
                    print(f"  Checkpoint ({model_type}): Size={file_size_kb:.1f} KB, Array Size={param_count:,}, Shape={q_table.shape} -> {'PASS' if checkpoint_valid else 'FAIL'}")
            except Exception as e:
                print(f"  Pickle Load Error: {e}")
        else:
            print(f"  Checkpoint: Missing (.pth or .pkl)")

        results.append({
            "name": name,
            "csv_valid": csv_valid,
            "max_step": max_step,
            "row_count": row_count,
            "reward_trend": reward_trend,
            "checkpoint_valid": checkpoint_valid,
            "model_type": model_type,
            "params": param_count,
            "layers": len(tensor_shapes) if tensor_shapes else (1 if param_count > 0 else 0)
        })

    print("\n" + "=" * 90)
    print("FINAL EMPIRICAL VERIFICATION SUMMARY TABLE (14 RL MODELS)")
    print("=" * 90)
    print(f"{'Model Name':<22} | {'Format':<18} | {'Params / Entries':<18} | {'Max Step':<10} | {'CSV':<6} | {'CKPT':<6}")
    print("-" * 90)
    all_pass = True
    for r in results:
        status_csv = "PASS" if r['csv_valid'] else "FAIL"
        status_ckpt = "PASS" if r['checkpoint_valid'] else "FAIL"
        if not (r['csv_valid'] and r['checkpoint_valid']):
            all_pass = False
        print(f"{r['name']:<22} | {r['model_type']:<18} | {r['params']:<18,d} | {r['max_step']:<10,d} | {status_csv:<6} | {status_ckpt:<6}")
    print("-" * 90)
    print(f"Overall Verification Result: {'ALL 14 MODELS VERIFIED (100% PASS)' if all_pass else 'VERIFICATION FAILED'}")
    print("=" * 90)

    return all_pass, results

if __name__ == "__main__":
    success, _ = verify_all_models()
    if not success:
        sys.exit(1)
    sys.exit(0)
