import os
import sys
import json
import pickle
import torch
import numpy as np
import pandas as pd

PROJECT_ROOT = "/home/imnyj/Workspace/paper4"
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MODELS_DIR = os.path.join(DATA_DIR, "models")
VIS_DIR = os.path.join(PROJECT_ROOT, "visualizer")

if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

report = {
    "model_checks": {},
    "csv_checks": {},
    "code_checks": {},
    "violations": []
}

print("=" * 60)
print("PHASE 1: MODEL CHECKPOINT AUDIT")
print("=" * 60)

model_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(('.pth', '.pkl'))]
print(f"Found {len(model_files)} model files in {MODELS_DIR}: {model_files}")

def extract_tensors_from_obj(obj, prefix=""):
    tensors = {}
    if isinstance(obj, torch.Tensor):
        tensors[prefix] = obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_k = f"{prefix}.{k}" if prefix else str(k)
            tensors.update(extract_tensors_from_obj(v, new_k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_k = f"{prefix}[{i}]"
            tensors.update(extract_tensors_from_obj(v, new_k))
    return tensors

for mf in sorted(model_files):
    mpath = os.path.join(MODELS_DIR, mf)
    size = os.path.getsize(mpath)
    info = {"size_bytes": size, "file": mf}
    
    if mf.endswith('.pth'):
        try:
            state = torch.load(mpath, map_location='cpu')
            tensors = extract_tensors_from_obj(state)
            
            total_params = 0
            zero_params = 0
            has_nan = False
            has_inf = False
            param_stats = {}
            
            for k, v in tensors.items():
                n = v.numel()
                total_params += n
                z = int((v == 0).sum().item())
                zero_params += z
                if torch.isnan(v).any().item():
                    has_nan = True
                if torch.isinf(v).any().item():
                    has_inf = True
                param_stats[k] = {
                    "shape": list(v.shape),
                    "mean": float(v.float().mean().item()),
                    "std": float(v.float().std().item()) if n > 1 else 0.0,
                    "min": float(v.float().min().item()),
                    "max": float(v.float().max().item())
                }
            
            info["type"] = f"PyTorch State ({type(state).__name__})"
            info["total_params"] = total_params
            info["zero_fraction"] = zero_params / max(1, total_params)
            info["has_nan"] = has_nan
            info["has_inf"] = has_inf
            info["num_tensors"] = len(tensors)
            info["tensor_names"] = list(tensors.keys())
            
            if total_params == 0:
                report["violations"].append(f"Model {mf} has 0 parameters!")
            if has_nan or has_inf:
                report["violations"].append(f"Model {mf} contains NaN or Inf!")
            if info["zero_fraction"] > 0.95:
                report["violations"].append(f"Model {mf} is mostly zeros ({info['zero_fraction']:.2%})!")
                
        except Exception as e:
            info["error"] = str(e)
            report["violations"].append(f"Failed to load .pth {mf}: {e}")
            
    elif mf.endswith('.pkl'):
        try:
            with open(mpath, 'rb') as f:
                data = pickle.load(f)
            info["type"] = f"Pickle Object ({type(data).__name__})"
            if isinstance(data, dict):
                info["keys"] = list(data.keys())[:10]
                info["dict_len"] = len(data)
                # Check for q-table or nested structures
                if "q_table" in data:
                    q_tab = data["q_table"]
                    if hasattr(q_tab, 'shape'):
                        info["q_table_shape"] = list(q_tab.shape)
                        info["q_table_nonzero"] = int(np.count_nonzero(q_tab))
                        info["q_table_mean"] = float(np.mean(q_tab))
                        info["q_table_std"] = float(np.std(q_tab))
                else:
                    # check if dictionary of state-action values
                    nonzero_count = sum(1 for v in data.values() if isinstance(v, (int, float, np.number)) and v != 0)
                    info["nonzero_values"] = nonzero_count
            elif isinstance(data, np.ndarray):
                info["array_shape"] = list(data.shape)
                info["nonzero"] = int(np.count_nonzero(data))
                info["mean"] = float(np.mean(data))
                info["std"] = float(np.std(data))
        except Exception as e:
            info["error"] = str(e)
            report["violations"].append(f"Failed to load .pkl {mf}: {e}")
            
    report["model_checks"][mf] = info
    print(f"  [{mf}] size: {size} bytes | type: {info.get('type')} | total_params: {info.get('total_params', 'N/A')} | tensors: {info.get('num_tensors', info.get('dict_len', 'N/A'))}")

print("\n" + "=" * 60)
print("PHASE 2: CSV DATA AUDIT")
print("=" * 60)

csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
for cf in sorted(csv_files):
    cpath = os.path.join(DATA_DIR, cf)
    try:
        df = pd.read_csv(cpath)
        info = {
            "rows": len(df),
            "cols": list(df.columns),
            "null_count": int(df.isnull().sum().sum()),
            "numeric_cols": list(df.select_dtypes(include=[np.number]).columns)
        }
        
        flat_cols = []
        for num_col in info["numeric_cols"]:
            std_val = float(df[num_col].std()) if len(df) > 1 else 0.0
            if std_val == 0.0 and len(df) > 5 and num_col not in ["Episode", "Global_Step", "Density", "Distance", "Time"]:
                flat_cols.append(num_col)
        
        info["flat_constant_columns"] = flat_cols
        report["csv_checks"][cf] = info
        print(f"  [{cf}] rows: {info['rows']}, cols: {len(info['cols'])}, nulls: {info['null_count']}, flat_cols: {flat_cols}")
    except Exception as e:
        report["csv_checks"][cf] = {"error": str(e)}
        report["violations"].append(f"Failed to read CSV {cf}: {e}")

print("\n" + "=" * 60)
print("PHASE 3: DETAILED STRUCTURE AUDIT FOR REMO-DQN")
print("=" * 60)

remo_path = os.path.join(MODELS_DIR, "REMO-DQN.pth")
if os.path.exists(remo_path):
    sd = torch.load(remo_path, map_location='cpu')
    tensors = extract_tensors_from_obj(sd)
    print(f"REMO-DQN.pth has {len(tensors)} tensors:")
    for k, t in tensors.items():
        print(f"  {k:45s} shape: {str(list(t.shape)):20s} std: {t.float().std().item():.6f}")
    
    keys = list(tensors.keys())
    has_resnet = any('res' in k.lower() or 'residual' in k.lower() or 'shortcut' in k.lower() or 'block' in k.lower() for k in keys)
    has_gating = any('gate' in k.lower() or 'gating' in k.lower() for k in keys)
    has_experts = any('expert' in k.lower() for k in keys)
    has_val_adv = any('val' in k.lower() or 'value' in k.lower() for k in keys) and any('adv' in k.lower() or 'advantage' in k.lower() for k in keys)
    
    print(f"\nArchitecture check for REMO-DQN:")
    print(f"  ResNet blocks: {has_resnet}")
    print(f"  MoE Gating:    {has_gating}")
    print(f"  MoE Experts:   {has_experts}")
    print(f"  Dueling Heads: {has_val_adv}")
    
    report["remo_architecture"] = {
        "has_resnet": has_resnet,
        "has_gating": has_gating,
        "has_experts": has_experts,
        "has_dueling": has_val_adv,
        "total_tensors": len(tensors)
    }
    
    if not (has_resnet and has_gating and has_experts and has_val_adv):
        report["violations"].append("REMO-DQN architecture does not contain all required ResNet + MoE + Dueling components!")
else:
    print("REMO-DQN.pth not found in models dir!")
    report["violations"].append("REMO-DQN.pth not found in models dir!")

out_path = "/home/imnyj/Workspace/paper4/.agents/auditor_1/forensic_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(f"\nAudit complete. Detailed JSON results saved to {out_path}")
