#!/usr/bin/env python3
import os
import sys
import argparse
import pandas as pd
import numpy as np
import pickle
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

FEATURE_COLS = ["cbr_global", "n_neighbors", "v_norm", "dt_since_last_cam", "cbr_smoothed"]
LABEL_COL = "action_idx"

def find_default_dataset():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    candidates = [
        os.path.join(project_root, "data", "oracle_dataset.csv"),
        os.path.join(project_root, "paper", "data", "oracle_dataset.csv"),
        os.path.join(script_dir, "data", "oracle_dataset.csv"),
        "data/oracle_dataset.csv",
        "../paper/data/oracle_dataset.csv"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

def train_models(dataset_path=None, output_dir="."):
    if dataset_path is None:
        dataset_path = find_default_dataset()
        
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}!")
        return None, None

    df = pd.read_csv(dataset_path)
    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train StdMLP (64x64x64)
    print("Training StdMLP...")
    mlp = MLPClassifier(hidden_layer_sizes=(64, 64, 64), max_iter=200, random_state=42)
    mlp.fit(X_train, y_train)
    acc_mlp = mlp.score(X_test, y_test)
    print(f"StdMLP Test Accuracy: {acc_mlp:.4f}")

    # Train DecTree
    print("Training DecTree...")
    dt = DecisionTreeClassifier(max_depth=10, random_state=42)
    dt.fit(X_train, y_train)
    acc_dt = dt.score(X_test, y_test)
    print(f"DecTree Test Accuracy: {acc_dt:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    mlp_path = os.path.join(output_dir, "stdmlp_model.pkl")
    dt_path = os.path.join(output_dir, "dectree_model.pkl")
    
    with open(mlp_path, "wb") as f:
        pickle.dump(mlp, f)
    with open(dt_path, "wb") as f:
        pickle.dump(dt, f)
    
    print(f"Models saved to {mlp_path} and {dt_path}.")
    return mlp, dt

def parse_args():
    parser = argparse.ArgumentParser(description="Train baseline supervised models (StdMLP, DecTree)")
    parser.add_argument("--dataset", type=str, default=None, help="Path to oracle dataset CSV")
    parser.add_argument("--output_dir", type=str, default=".", help="Output directory for pickle models")
    return parser.parse_args()

def main():
    args = parse_args()
    train_models(dataset_path=args.dataset, output_dir=args.output_dir)

if __name__ == "__main__":
    main()
