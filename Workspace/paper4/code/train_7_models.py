#!/usr/bin/env python3
"""
train_7_models.py - Edge AI 7-Model Profiling Benchmark for Paper4 (REMO-DQN).

Benchmarks training time, single-sample inference latency (us), parameter count,
memory footprint (KB), and FLOPs/MACs across all 7 benchmark models:
1. REMO-DQN (Proposed) (ResNetMoEDQN, action_dim=24)
2. MoEDQN (MoEDQN, action_dim=24)
3. DuelingDQN (DuelingDQN, action_dim=24)
4. DoubleDQN (DoubleDQN, action_dim=24)
5. VanillaDQN (VanillaDQN, action_dim=24)
6. StdMLP (MLPClassifier 64x64x64, action_dim=24)
7. DecTree (DecisionTreeClassifier max_depth=10, 24 classes)
"""

import sys
import os
import time
import json
import argparse
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

# Scikit-learn models
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier

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
from calc_flops import get_model_stats


def run_benchmark(n_samples: int = 10000, n_test: int = 1000, epochs: int = 5, batch_size: int = 64, output_dir: str = None):
    """Run edge AI profiling benchmark across all 7 models."""
    print("=" * 70)
    print(f"Generating synthetic dataset for Edge AI benchmark (num_classes={ACTION_DIM}, state_dim=5)...")
    np.random.seed(42)
    torch.manual_seed(42)
    
    # 5 features: ['cbr_global', 'n_neighbors', 'v_norm', 'dt_since_last_cam', 'cbr_smoothed']
    X = np.random.rand(n_samples, 5).astype(np.float32)
    y = np.random.randint(0, ACTION_DIM, n_samples).astype(np.int64)
    print(f"Dataset shape: X={X.shape}, y={y.shape} (y min={y.min()}, max={y.max()})")
    
    X_test = X[:n_test]
    y_test = y[:n_test]
    
    # Define the 7 models
    # PyTorch DRL neural networks
    torch_models = {
        "REMO-DQN (Proposed)": ResNetMoEDQN(state_dim=5, action_dim=ACTION_DIM, num_experts=3, hidden_dim=128),
        "MoEDQN": MoEDQN(state_dim=5, action_dim=ACTION_DIM, num_experts=2),
        "DuelingDQN": DuelingDQN(state_dim=5, action_dim=ACTION_DIM),
        "DoubleDQN": DoubleDQN(state_dim=5, action_dim=ACTION_DIM),
        "VanillaDQN": VanillaDQN(state_dim=5, action_dim=ACTION_DIM),
    }
    
    # Sklearn models
    sklearn_models = {
        "StdMLP": MLPClassifier(hidden_layer_sizes=(64, 64, 64), max_iter=100, random_state=42),
        "DecTree": DecisionTreeClassifier(max_depth=10, random_state=42)
    }
    
    results = []
    
    # 1. Benchmark PyTorch Models
    device = torch.device("cpu") # Measure Edge CPU latency
    tensor_x = torch.from_numpy(X).to(device)
    tensor_y = torch.from_numpy(y).to(device)
    train_dataset = TensorDataset(tensor_x, tensor_y)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    tensor_x_test = torch.from_numpy(X_test).to(device)
    
    for name, model in torch_models.items():
        model.to(device)
        model.train()
        optimizer = optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.CrossEntropyLoss()
        
        print(f"\nTraining PyTorch model: {name} ({epochs} epochs)...")
        t0 = time.perf_counter()
        for epoch in range(epochs):
            for bx, by in train_loader:
                optimizer.zero_grad()
                out = model(bx)
                loss = criterion(out, by)
                loss.backward()
                optimizer.step()
        train_time = time.perf_counter() - t0
        
        # Measure Inference Latency (single-sample pass on CPU)
        model.eval()
        with torch.no_grad():
            # Warm-up
            for i in range(min(50, n_test)):
                _ = model(tensor_x_test[i:i+1])
            
            t1 = time.perf_counter()
            for i in range(n_test):
                _ = model(tensor_x_test[i:i+1])
            t2 = time.perf_counter()
            
        latency_us = ((t2 - t1) / n_test) * 1e6
        
        stats = get_model_stats(name, state_dim=5, action_dim=ACTION_DIM)
        
        results.append({
            "Model": name,
            "Parameters": stats["Parameters"],
            "Memory (KB)": stats["Memory (KB)"],
            "MACs": stats["MACs"],
            "FLOPs": stats["FLOPs"],
            "Latency (us)": round(latency_us, 2),
            "Train Time (s)": round(train_time, 3)
        })
        print(f"  -> Params: {stats['Parameters']}, FLOPs: {stats['FLOPs']}, Latency: {latency_us:.2f} us, Train Time: {train_time:.3f} s")
        
    # 2. Benchmark Sklearn Models
    for name, model in sklearn_models.items():
        print(f"\nTraining Scikit-learn model: {name}...")
        t0 = time.perf_counter()
        try:
            model.fit(X, y)
        except Exception as e:
            print(f"Failed to train {name}: {e}")
            continue
        train_time = time.perf_counter() - t0
        
        # Measure Inference Latency
        # Warm-up
        for i in range(min(50, n_test)):
            _ = model.predict(X_test[i:i+1])
            
        t1 = time.perf_counter()
        for i in range(n_test):
            _ = model.predict(X_test[i:i+1])
        t2 = time.perf_counter()
        
        latency_us = ((t2 - t1) / n_test) * 1e6
        
        stats = get_model_stats(name, state_dim=5, action_dim=ACTION_DIM)
        if isinstance(model, DecisionTreeClassifier):
            # Use actual node count from trained tree
            params = model.tree_.node_count
            memory_kb = (params * 16) / 1024.0
            flops = model.get_depth() * 2
            macs = model.get_depth()
        else:
            params = stats["Parameters"]
            memory_kb = stats["Memory (KB)"]
            flops = stats["FLOPs"]
            macs = stats["MACs"]
            
        results.append({
            "Model": name,
            "Parameters": params,
            "Memory (KB)": round(memory_kb, 2),
            "MACs": macs,
            "FLOPs": flops,
            "Latency (us)": round(latency_us, 2),
            "Train Time (s)": round(train_time, 3)
        })
        print(f"  -> Params: {params}, FLOPs: {flops}, Latency: {latency_us:.2f} us, Train Time: {train_time:.3f} s")
        
    df_res = pd.DataFrame(results)
    print("\n" + "=" * 70)
    print("=== Edge AI Profiling Benchmark Summary (7 Models) ===")
    print("=" * 70)
    print(df_res.to_string(index=False))
    print("=" * 70)
    
    # Save output CSV and JSON
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)
    
    if output_dir is None:
        target_dir = os.path.join(_project_root, "data")
    else:
        target_dir = output_dir
        
    os.makedirs(target_dir, exist_ok=True)
    csv_path = os.path.join(target_dir, "edge_profiling_benchmark.csv")
    json_path = os.path.join(target_dir, "edge_profiling_benchmark.json")
    
    df_res.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Benchmark results saved to:\n  - {csv_path}\n  - {json_path}")
    
    # Also save to paper/data if directory exists
    paper_data_dir = os.path.join(_project_root, "paper", "data")
    if os.path.exists(paper_data_dir):
        paper_csv = os.path.join(paper_data_dir, "edge_profiling_benchmark.csv")
        df_res.to_csv(paper_csv, index=False)
        print(f"  - {paper_csv}")
        
    return df_res, results


def parse_args():
    parser = argparse.ArgumentParser(description="Train and profile 7 Edge AI models (ACTION_DIM=24)")
    parser.add_argument("--samples", type=int, default=10000, help="Number of synthetic training samples")
    parser.add_argument("--test_samples", type=int, default=1000, help="Number of test samples for latency benchmark")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs for PyTorch models")
    parser.add_argument("--batch_size", type=int, default=64, help="Mini-batch size")
    parser.add_argument("--output_dir", type=str, default=None, help="Output directory for CSV/JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    run_benchmark(
        n_samples=args.samples,
        n_test=args.test_samples,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
