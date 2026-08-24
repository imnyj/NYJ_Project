"""
Inspect action_dim shapes across all saved checkpoints
Paper4 - Reviewer 1 Independent Verification
"""
import os
import glob
import torch

WORKSPACE = "/home/imnyj/Workspace/paper4"

checkpoints = glob.glob(os.path.join(WORKSPACE, "data/models", "*.pth")) + glob.glob(os.path.join(WORKSPACE, "code", "*.pth"))

print(f"Found {len(checkpoints)} .pth files across data/models and code/:\n")

for cp in sorted(checkpoints):
    rel_path = os.path.relpath(cp, WORKSPACE)
    try:
        sd = torch.load(cp, map_location="cpu")
        if not isinstance(sd, dict):
            print(f"[{rel_path}] Non-dict object: {type(sd)}")
            continue
            
        # Find output layer shapes
        out_shapes = []
        for k, v in sd.items():
            if isinstance(v, torch.Tensor):
                # check if shape has 16 or 24 or 6 or 4
                if v.ndim >= 1 and (v.shape[0] in [16, 24] or (v.ndim >= 2 and v.shape[1] in [16, 24])):
                    out_shapes.append((k, list(v.shape)))
            elif isinstance(v, dict):
                for subk, subv in v.items():
                    if isinstance(subv, torch.Tensor):
                        if subv.ndim >= 1 and (subv.shape[0] in [16, 24] or (subv.ndim >= 2 and subv.shape[1] in [16, 24])):
                            out_shapes.append((f"{k}.{subk}", list(subv.shape)))
        
        print(f"[{rel_path:45s}] Size: {os.path.getsize(cp)/1024:6.1f} KB | Relevant Layer Shapes: {out_shapes}")
    except Exception as e:
        print(f"[{rel_path:45s}] Error reading: {e}")
