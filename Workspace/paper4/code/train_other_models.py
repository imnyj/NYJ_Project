#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import pickle
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

FEATURE_COLS = ["cbr_global", "n_neighbors", "v_norm", "dt_since_last_cam", "cbr_smoothed"]
LABEL_COL = "action_idx"

def train_models():
    dataset_path = "../paper/data/oracle_dataset.csv"
    if not os.path.exists(dataset_path):
        print("Dataset not found!")
        return

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

    # Save models
    with open("stdmlp_model.pkl", "wb") as f:
        pickle.dump(mlp, f)
    with open("dectree_model.pkl", "wb") as f:
        pickle.dump(dt, f)
    
    print("Models saved.")

if __name__ == "__main__":
    train_models()
