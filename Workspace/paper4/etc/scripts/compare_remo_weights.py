"""
Compare REMO-DQN.pth and resnet_moe_dqn.pth
"""
import os
import torch
import numpy as np

WORKSPACE = "/home/imnyj/Workspace/paper4"
p1 = os.path.join(WORKSPACE, "data/models/REMO-DQN.pth")
p2 = os.path.join(WORKSPACE, "data/models/resnet_moe_dqn.pth")

sd1 = torch.load(p1, map_location="cpu")
sd2 = torch.load(p2, map_location="cpu")

print(f"p1 keys count: {len(sd1)}, p2 keys count: {len(sd2)}")
keys_match = (set(sd1.keys()) == set(sd2.keys()))
print(f"Keys match: {keys_match}")

max_diff = 0.0
for k in sd1.keys():
    t1 = sd1[k]
    t2 = sd2[k]
    if isinstance(t1, torch.Tensor) and isinstance(t2, torch.Tensor):
        diff = torch.max(torch.abs(t1 - t2)).item()
        if diff > max_diff:
            max_diff = diff

print(f"Maximum parameter difference between REMO-DQN.pth and resnet_moe_dqn.pth: {max_diff:.6e}")
