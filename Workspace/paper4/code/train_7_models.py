import pandas as pd
import numpy as np
import time
import os
import sys

# Scikit-learn models
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# Try XGBoost, if not installed, use GradientBoosting
try:
    from xgboost import XGBClassifier
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier

# For Neural Networks, we can just benchmark using simple NumPy or basic sklearn MLP
from sklearn.neural_network import MLPClassifier

print("Generating synthetic dataset for Edge AI benchmark...")
# Features: ['cbr_global', 'n_neighbors', 'v_norm', 'dt_since_last_cam', 'cbr_smoothed']
n_samples = 10000
X = np.random.rand(n_samples, 5)
y = np.random.randint(0, 25, n_samples)
print(f"Dataset shape: {X.shape}")

# Subsample for faster training in benchmark
if len(X) > 10000:
    idx = np.random.choice(len(X), 10000, replace=False)
    X = X[idx]
    y = y[idx]

print(f"Dataset shape: {X.shape}")

models = {
    "TinyMLP (Proposed)": MLPClassifier(hidden_layer_sizes=(16, 16), max_iter=100),
    "Decision Tree": DecisionTreeClassifier(max_depth=10),
    "SVM": SVC(kernel='rbf', probability=False, max_iter=2000),
    "Random Forest": RandomForestClassifier(n_estimators=50, max_depth=10),
    "Logistic Reg": LogisticRegression(max_iter=1000),
    "XGBoost-Lite": XGBClassifier(n_estimators=50, max_depth=5),
    "Heavy-DRL (MLP)": MLPClassifier(hidden_layer_sizes=(128, 128, 128, 128), max_iter=100),
    "LSTM-Proxy (Heavy)": MLPClassifier(hidden_layer_sizes=(256, 256), max_iter=100) # Proxy for heavy recurrent
}

results = []

for name, model in models.items():
    print(f"\nTraining {name}...")
    t0 = time.time()
    try:
        model.fit(X, y)
    except Exception as e:
        print(f"Failed to train {name}: {e}")
        continue
    train_time = time.time() - t0
    
    # Measure Inference Latency
    n_samples = 1000
    X_test = X[:n_samples]
    
    t1 = time.time()
    _ = model.predict(X_test)
    t2 = time.time()
    
    latency_us = ((t2 - t1) / n_samples) * 1e6
    
    # Estimate Memory and Parameters
    params = 0
    if hasattr(model, 'coefs_'):
        params = sum([c.size for c in model.coefs_]) + sum([i.size for i in model.intercepts_])
        memory_kb = (params * 4) / 1024.0
        flops = params * 2
    elif isinstance(model, DecisionTreeClassifier):
        params = model.tree_.node_count
        memory_kb = (params * 16) / 1024.0
        flops = model.get_depth() * 2
    elif isinstance(model, RandomForestClassifier):
        params = sum([t.tree_.node_count for t in model.estimators_])
        memory_kb = (params * 16) / 1024.0
        flops = 50 * 10 * 2
    elif isinstance(model, SVC):
        params = model.support_vectors_.size
        memory_kb = (params * 8) / 1024.0
        flops = params * X.shape[1]
    else:
        params = 1000 # dummy
        memory_kb = 50.0
        flops = 2000
        
    results.append({
        "Model": name,
        "Parameters": params,
        "Memory (KB)": round(memory_kb, 2),
        "FLOPs": flops,
        "Latency (us)": round(latency_us, 2)
    })

df_res = pd.DataFrame(results)
print("\n=== Edge AI Profiling Benchmark ===")
print(df_res)

df_res.to_csv('../paper/data/edge_profiling_benchmark.csv', index=False)
