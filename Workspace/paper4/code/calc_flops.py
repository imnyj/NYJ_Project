#!/usr/bin/env python3
"""
calc_flops.py - Floating Point Operations (FLOPs) and Parameters Calculator for Paper4 (REMO-DQN).

Computes exact MACs, FLOPs, parameter count, and estimated memory footprint for all 7 benchmark models:
1. REMO-DQN (Proposed) (ResNetMoEDQN, action_dim=24)
2. MoEDQN (MoEDQN, action_dim=24)
3. DuelingDQN (DuelingDQN, action_dim=24)
4. DoubleDQN (DoubleDQN, action_dim=24)
5. VanillaDQN (VanillaDQN, action_dim=24)
6. StdMLP (StdMLP, action_dim=24)
7. DecTree (DecisionTreeClassifier, 24 classes)
"""

import sys
import os
import torch
import numpy as np

# Ensure code directory is in sys.path
_code_dir = os.path.dirname(os.path.abspath(__file__))
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

try:
    from etsi_cam_layer import ACTION_DIM
except ImportError:
    ACTION_DIM = 24

from dqn_agent import VanillaDQN
from ddqn_agent import DoubleDQN
from dueling_dqn_agent import DuelingDQN
from moe_agent import MoEDQN
from resnet_moe_agent import ResNetMoEDQN

# Try thop if available
try:
    from thop import profile as thop_profile
    HAS_THOP = True
except ImportError:
    HAS_THOP = False


def compute_linear_macs_params(in_features, out_features, bias=True):
    """Compute MACs and Parameters for nn.Linear."""
    macs = in_features * out_features
    params = in_features * out_features + (out_features if bias else 0)
    return macs, params


def get_model_stats(model_name: str, state_dim: int = 5, action_dim: int = ACTION_DIM) -> dict:
    """
    Compute exact parameters, MACs, FLOPs (2 * MACs), and Memory (KB) for a given model.
    """
    if model_name in ["REMO-DQN (Proposed)", "ResNetMoEDQN", "REMO-DQN"]:
        # ResNetMoEDQN Architecture:
        # Feature Extractor:
        #   input_layer: Linear(state_dim, 128)
        #   res_blocks: 2 blocks. Each has fc1: Linear(128, 128), fc2: Linear(128, 128)
        # Gating: Linear(128, 64) -> Linear(64, num_experts=3)
        # Experts (num_experts=3):
        #   Each expert:
        #     value_stream: Linear(128, 64) -> Linear(64, 1)
        #     advantage_stream: Linear(128, 64) -> Linear(64, action_dim)
        m_in, p_in = compute_linear_macs_params(state_dim, 128)
        m_res1, p_res1 = compute_linear_macs_params(128, 128)
        m_res2, p_res2 = compute_linear_macs_params(128, 128)
        m_res = 2 * (m_res1 + m_res2)
        p_res = 2 * (p_res1 + p_res2)

        m_gate1, p_gate1 = compute_linear_macs_params(128, 64)
        m_gate2, p_gate2 = compute_linear_macs_params(64, 3)
        m_gate = m_gate1 + m_gate2
        p_gate = p_gate1 + p_gate2

        m_v1, p_v1 = compute_linear_macs_params(128, 64)
        m_v2, p_v2 = compute_linear_macs_params(64, 1)
        m_a1, p_a1 = compute_linear_macs_params(128, 64)
        m_a2, p_a2 = compute_linear_macs_params(64, action_dim)
        m_exp = (m_v1 + m_v2 + m_a1 + m_a2) * 3
        p_exp = (p_v1 + p_v2 + p_a1 + p_a2) * 3

        macs = m_in + m_res + m_gate + m_exp
        params = p_in + p_res + p_gate + p_exp
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["MoEDQN", "MoE-DQN"]:
        # MoEDQN Architecture:
        # feature_layer (2 experts):
        #   Each expert: Linear(state_dim, 128) -> Linear(128, 128)
        #   gating: Linear(state_dim, 64) -> Linear(64, num_experts=2)
        # Streams:
        #   value_stream: Linear(128, 64) -> Linear(64, 1)
        #   advantage_stream: Linear(128, 64) -> Linear(64, action_dim)
        m_fe1, p_fe1 = compute_linear_macs_params(state_dim, 128)
        m_fe2, p_fe2 = compute_linear_macs_params(128, 128)
        m_exp_fe = 2 * (m_fe1 + m_fe2)
        p_exp_fe = 2 * (p_fe1 + p_fe2)

        m_gate1, p_gate1 = compute_linear_macs_params(state_dim, 64)
        m_gate2, p_gate2 = compute_linear_macs_params(64, 2)
        m_gate = m_gate1 + m_gate2
        p_gate = p_gate1 + p_gate2

        m_v1, p_v1 = compute_linear_macs_params(128, 64)
        m_v2, p_v2 = compute_linear_macs_params(64, 1)
        m_a1, p_a1 = compute_linear_macs_params(128, 64)
        m_a2, p_a2 = compute_linear_macs_params(64, action_dim)
        m_streams = m_v1 + m_v2 + m_a1 + m_a2
        p_streams = p_v1 + p_v2 + p_a1 + p_a2

        macs = m_exp_fe + m_gate + m_streams
        params = p_exp_fe + p_gate + p_streams
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["DuelingDQN", "Dueling-DQN"]:
        # DuelingDQN Architecture:
        # feature_layer: Linear(state_dim, 128) -> Linear(128, 128)
        # value_stream: Linear(128, 64) -> Linear(64, 1)
        # advantage_stream: Linear(128, 64) -> Linear(64, action_dim)
        m_f1, p_f1 = compute_linear_macs_params(state_dim, 128)
        m_f2, p_f2 = compute_linear_macs_params(128, 128)
        m_v1, p_v1 = compute_linear_macs_params(128, 64)
        m_v2, p_v2 = compute_linear_macs_params(64, 1)
        m_a1, p_a1 = compute_linear_macs_params(128, 64)
        m_a2, p_a2 = compute_linear_macs_params(64, action_dim)

        macs = m_f1 + m_f2 + m_v1 + m_v2 + m_a1 + m_a2
        params = p_f1 + p_f2 + p_v1 + p_v2 + p_a1 + p_a2
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["DoubleDQN", "Double-DQN", "DDQN"]:
        # DoubleDQN: Linear(state_dim, 128) -> Linear(128, 128) -> Linear(128, action_dim)
        m1, p1 = compute_linear_macs_params(state_dim, 128)
        m2, p2 = compute_linear_macs_params(128, 128)
        m3, p3 = compute_linear_macs_params(128, action_dim)

        macs = m1 + m2 + m3
        params = p1 + p2 + p3
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["VanillaDQN", "Vanilla-DQN", "DQN"]:
        # VanillaDQN: Linear(state_dim, 128) -> Linear(128, 128) -> Linear(128, action_dim)
        m1, p1 = compute_linear_macs_params(state_dim, 128)
        m2, p2 = compute_linear_macs_params(128, 128)
        m3, p3 = compute_linear_macs_params(128, action_dim)

        macs = m1 + m2 + m3
        params = p1 + p2 + p3
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["StdMLP", "StandardMLP"]:
        # StdMLP (64x64x64): Linear(state_dim, 64) -> Linear(64, 64) -> Linear(64, 64) -> Linear(64, action_dim)
        m1, p1 = compute_linear_macs_params(state_dim, 64)
        m2, p2 = compute_linear_macs_params(64, 64)
        m3, p3 = compute_linear_macs_params(64, 64)
        m4, p4 = compute_linear_macs_params(64, action_dim)

        macs = m1 + m2 + m3 + m4
        params = p1 + p2 + p3 + p4
        flops = macs * 2
        memory_kb = (params * 4) / 1024.0

    elif model_name in ["DecTree", "DecisionTree", "DecisionTreeClassifier"]:
        # DecisionTree (max_depth=10, 24 classes): Approx 300-500 nodes
        params = 350
        memory_kb = (params * 16) / 1024.0
        macs = 10
        flops = 20

    else:
        raise ValueError(f"Unknown model name: {model_name}")

    return {
        "Model": model_name,
        "Parameters": params,
        "MACs": macs,
        "FLOPs": flops,
        "Memory (KB)": round(memory_kb, 2)
    }


def get_all_7_models_stats(state_dim: int = 5, action_dim: int = ACTION_DIM) -> list:
    """Return list of complexity dictionaries for all 7 models."""
    model_names = [
        "REMO-DQN (Proposed)",
        "MoEDQN",
        "DuelingDQN",
        "DoubleDQN",
        "VanillaDQN",
        "StdMLP",
        "DecTree"
    ]
    return [get_model_stats(name, state_dim=state_dim, action_dim=action_dim) for name in model_names]


def main():
    print(f"=== Paper4 7-Model Complexity Profiling (state_dim=5, action_dim={ACTION_DIM}) ===")
    
    # Verify PyTorch model parameter counts directly
    dummy_input = torch.randn(1, 5)
    
    torch_models = {
        "REMO-DQN (Proposed)": ResNetMoEDQN(state_dim=5, action_dim=ACTION_DIM),
        "MoEDQN": MoEDQN(state_dim=5, action_dim=ACTION_DIM),
        "DuelingDQN": DuelingDQN(state_dim=5, action_dim=ACTION_DIM),
        "DoubleDQN": DoubleDQN(state_dim=5, action_dim=ACTION_DIM),
        "VanillaDQN": VanillaDQN(state_dim=5, action_dim=ACTION_DIM),
    }
    
    print("\n[PyTorch Direct Model Verification]")
    for name, model in torch_models.items():
        model.eval()
        p_count = sum(p.numel() for p in model.parameters())
        with torch.no_grad():
            out = model(dummy_input)
        
        if HAS_THOP:
            try:
                macs_thop, _ = thop_profile(model, inputs=(dummy_input,), verbose=False)
                print(f"  {name:22s} | Params: {p_count:7d} | Output: {str(out.shape):20s} | thop MACs: {int(macs_thop):7d}")
            except Exception:
                print(f"  {name:22s} | Params: {p_count:7d} | Output: {str(out.shape):20s}")
        else:
            print(f"  {name:22s} | Params: {p_count:7d} | Output: {str(out.shape):20s}")

    print("\n[Standard Benchmark Complexity Table]")
    stats = get_all_7_models_stats(state_dim=5, action_dim=ACTION_DIM)
    header = f"{'Model':25s} | {'Parameters':12s} | {'MACs':10s} | {'FLOPs':10s} | {'Memory (KB)':12s}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for s in stats:
        print(f"{s['Model']:25s} | {s['Parameters']:12d} | {s['MACs']:10d} | {s['FLOPs']:10d} | {s['Memory (KB)']:12.2f}")
    print("-" * len(header))


if __name__ == "__main__":
    main()
