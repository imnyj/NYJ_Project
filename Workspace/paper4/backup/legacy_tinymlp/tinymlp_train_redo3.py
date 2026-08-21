#!/usr/bin/env python3
"""
E4-2-redo3 TinyMLP Behavior Cloning Training Script
Architecture: 5 → 8 → 8 → 16 (softmax)
Enhanced with: cost_function_version check, confusion matrix, class collapse guard
"""

import json
import os
import pickle
import random
import sys
import time
import math

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
DATASET_PATH = "/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv"
META_PATH = "/home/imnyj/papers/paper4/paper/data/oracle_dataset_meta.json"
OUTPUT_MODEL = "/home/imnyj/papers/paper4/sim/tinymlp_model.pkl"
OUTPUT_LOG = "/home/imnyj/papers/paper4/sim/train_log.json"

EPOCHS = 80
BATCH_SIZE = 256
LR = 0.001
HIDDEN_DIM = 8
SEED = 42
MAX_ROWS = 1_000_000  # Use 1M rows for speed
N_CLASSES = 16

FEATURE_COLS = ["cbr_global", "n_neighbors", "v_norm", "dt_since_last_cam", "cbr_smoothed"]
LABEL_COL = "action_idx"

REQUIRED_COST_VERSION = "3term_v2_state_exploration"

# ─────────────────────────────────────────────
# Reproducibility
# ─────────────────────────────────────────────
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)

set_seed(SEED)

# ─────────────────────────────────────────────
# Step 0: Verify oracle meta
# ─────────────────────────────────────────────
print("[STEP 0] Checking oracle meta...")
with open(META_PATH, "r") as f:
    meta = json.load(f)

cost_version = meta.get("cost_function_version", "UNKNOWN")
print(f"[META] cost_function_version = {cost_version}")

if cost_version != REQUIRED_COST_VERSION:
    print(f"[ABORT] cost_function_version mismatch! Expected {REQUIRED_COST_VERSION}, got {cost_version}")
    sys.exit(1)

print(f"[META] PASS - correct cost version")

# ─────────────────────────────────────────────
# Step 1: Load data
# ─────────────────────────────────────────────
print(f"\n[STEP 1] Loading data from {DATASET_PATH}...")
t0 = time.time()

needed_cols = FEATURE_COLS + [LABEL_COL]
df = pd.read_csv(DATASET_PATH, usecols=needed_cols, dtype="float32",
                 converters={LABEL_COL: lambda x: int(float(x))})

total_rows = len(df)
print(f"[DATA] Total rows: {total_rows:,}. Elapsed: {time.time()-t0:.1f}s")

if MAX_ROWS > 0 and total_rows > MAX_ROWS:
    print(f"[DATA] Sampling {MAX_ROWS:,} rows (seed={SEED})...")
    df = df.sample(n=MAX_ROWS, random_state=SEED)

X = df[FEATURE_COLS].values.astype(np.float32)
y = df[LABEL_COL].values.astype(np.int64)

print(f"[DATA] X shape: {X.shape}, y shape: {y.shape}")
unique, counts = np.unique(y, return_counts=True)
class_dist = {int(u): int(c) for u, c in zip(unique, counts)}
print(f"[DATA] y unique values: {unique.tolist()}")
print(f"[DATA] Class distribution: {class_dist}")
print(f"[DATA] Load time: {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────
# Step 2: Train/Val/Test split
# ─────────────────────────────────────────────
n = len(X)
idx = np.arange(n)
rng = np.random.default_rng(SEED)
rng.shuffle(idx)

n_train = int(n * 0.70)
n_val = int(n * 0.15)

train_idx = idx[:n_train]
val_idx = idx[n_train:n_train+n_val]
test_idx = idx[n_train+n_val:]

X_tr, y_tr = X[train_idx], y[train_idx]
X_val, y_val = X[val_idx], y[val_idx]
X_te, y_te = X[test_idx], y[test_idx]

print(f"[SPLIT] Train={len(X_tr):,} Val={len(X_val):,} Test={len(X_te):,}")

# ─────────────────────────────────────────────
# Step 3: NumpyMLP Implementation
# ─────────────────────────────────────────────
class NumpyMLP:
    """3-layer MLP: 5→8→8→16 with ReLU hidden, softmax output."""
    
    def __init__(self, in_dim=5, hidden_dim=8, n_classes=16, seed=42):
        rng = np.random.default_rng(seed)
        scale1 = math.sqrt(2.0 / in_dim)
        scale2 = math.sqrt(2.0 / hidden_dim)
        self.W1 = rng.standard_normal((hidden_dim, in_dim)).astype(np.float32) * scale1
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.W2 = rng.standard_normal((hidden_dim, hidden_dim)).astype(np.float32) * scale2
        self.b2 = np.zeros(hidden_dim, dtype=np.float32)
        self.W3 = rng.standard_normal((n_classes, hidden_dim)).astype(np.float32) * scale2
        self.b3 = np.zeros(n_classes, dtype=np.float32)
        
        self.params = [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t = 0
    
    def forward(self, x):
        z1 = x @ self.W1.T + self.b1
        a1 = np.maximum(0, z1)
        z2 = a1 @ self.W2.T + self.b2
        a2 = np.maximum(0, z2)
        z3 = a2 @ self.W3.T + self.b3
        z3_s = z3 - z3.max(axis=1, keepdims=True)
        exp_z = np.exp(z3_s)
        probs = exp_z / exp_z.sum(axis=1, keepdims=True)
        self._cache = (x, z1, a1, z2, a2, z3, probs)
        return probs
    
    def loss_and_acc(self, x, y_true):
        probs = self.forward(x)
        B = len(y_true)
        log_p = -np.log(probs[np.arange(B), y_true] + 1e-12)
        loss = log_p.mean()
        preds = probs.argmax(axis=1)
        acc = (preds == y_true).mean()
        return float(loss), float(acc), preds
    
    def backward(self, y_true, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8):
        x, z1, a1, z2, a2, z3, probs = self._cache
        B = len(y_true)
        self.t += 1
        
        dz3 = probs.copy()
        dz3[np.arange(B), y_true] -= 1
        dz3 /= B
        
        dW3 = dz3.T @ a2
        db3 = dz3.sum(axis=0)
        da2 = dz3 @ self.W3
        
        dz2 = da2 * (z2 > 0)
        dW2 = dz2.T @ a1
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self.W2
        
        dz1 = da1 * (z1 > 0)
        dW1 = dz1.T @ x
        db1 = dz1.sum(axis=0)
        
        grads = [dW1, db1, dW2, db2, dW3, db3]
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.m[i] = beta1 * self.m[i] + (1 - beta1) * g
            self.v[i] = beta2 * self.v[i] + (1 - beta2) * g**2
            m_hat = self.m[i] / (1 - beta1**self.t)
            v_hat = self.v[i] / (1 - beta2**self.t)
            p -= lr * m_hat / (np.sqrt(v_hat) + eps)
    
    def param_count(self):
        return sum(p.size for p in self.params)
    
    def get_weights(self):
        return {
            "W1": self.W1.copy(), "b1": self.b1.copy(),
            "W2": self.W2.copy(), "b2": self.b2.copy(),
            "W3": self.W3.copy(), "b3": self.b3.copy(),
        }

# ─────────────────────────────────────────────
# Step 4: Training loop
# ─────────────────────────────────────────────
print("\n[STEP 4] Training NumpyMLP...")
model = NumpyMLP(in_dim=5, hidden_dim=HIDDEN_DIM, n_classes=N_CLASSES, seed=SEED)
param_count = model.param_count()
print(f"[MODEL] param_count = {param_count}")
assert param_count < 2000, f"param_count={param_count} exceeds 2000!"

n_train = len(X_tr)
best_val_loss = float("inf")
patience = 10  # Increased from 5 to allow more training
no_improve = 0
loss_curve = []
early_stopped = False
best_weights = None
t_start = time.time()

for epoch in range(1, EPOCHS + 1):
    perm = np.random.permutation(n_train)
    X_sh = X_tr[perm]
    y_sh = y_tr[perm]
    
    running_loss = 0.0
    correct = 0
    
    for start in range(0, n_train, BATCH_SIZE):
        Xb = X_sh[start:start+BATCH_SIZE]
        yb = y_sh[start:start+BATCH_SIZE]
        probs = model.forward(Xb)
        B = len(yb)
        log_p = -np.log(probs[np.arange(B), yb] + 1e-12)
        running_loss += log_p.sum()
        correct += (probs.argmax(axis=1) == yb).sum()
        model.backward(yb, lr=LR)
    
    train_loss = running_loss / n_train
    train_acc = correct / n_train
    
    # Check for NaN
    if math.isnan(train_loss):
        print(f"[ABORT] NaN loss detected at epoch {epoch}!")
        sys.exit(1)
    
    val_loss, val_acc, val_preds = model.loss_and_acc(X_val, y_val)
    val_unique_classes = len(np.unique(val_preds))
    
    loss_curve.append({
        "epoch": epoch,
        "train_loss": round(float(train_loss), 6),
        "val_loss": round(float(val_loss), 6),
        "train_acc": round(float(train_acc), 6),
        "val_acc": round(float(val_acc), 6),
        "val_unique_classes": int(val_unique_classes),
    })
    
    elapsed = time.time() - t_start
    print(f"[Epoch {epoch:3d}/{EPOCHS}] "
          f"train_loss={float(train_loss):.4f} train_acc={float(train_acc):.4f} "
          f"val_loss={float(val_loss):.4f} val_acc={float(val_acc):.4f} "
          f"val_unique={val_unique_classes} elapsed={elapsed:.1f}s")
    
    if val_loss < best_val_loss - 1e-6:
        best_val_loss = val_loss
        no_improve = 0
        best_weights = model.get_weights()
    else:
        no_improve += 1
        if no_improve >= patience:
            print(f"[EARLY STOP] No improvement for {patience} epochs at epoch {epoch}.")
            early_stopped = True
            break

training_time = time.time() - t_start

# Restore best weights
if best_weights:
    for k, v in best_weights.items():
        getattr(model, k.split(".")[0] if "." in k else k)  # dummy
    model.W1[:] = best_weights["W1"]
    model.b1[:] = best_weights["b1"]
    model.W2[:] = best_weights["W2"]
    model.b2[:] = best_weights["b2"]
    model.W3[:] = best_weights["W3"]
    model.b3[:] = best_weights["b3"]

epochs_completed = len(loss_curve)
final = loss_curve[-1]
final_train_loss = final["train_loss"]
final_val_loss = final["val_loss"]
final_train_acc = final["train_acc"]
final_val_acc = final["val_acc"]

# ─────────────────────────────────────────────
# Step 5: Test set evaluation
# ─────────────────────────────────────────────
print("\n[STEP 5] Test set evaluation...")
_, test_acc, te_preds = model.loss_and_acc(X_te, y_te)

# Confusion matrix 16x16
cm = np.zeros((16, 16), dtype=int)
for t_, p_ in zip(y_te, te_preds):
    cm[int(t_)][int(p_)] += 1

# Val predictions for unique class check
_, _, val_preds_final = model.loss_and_acc(X_val, y_val)
val_unique_classes_final = len(np.unique(val_preds_final))

print(f"[RESULT] epochs_completed={epochs_completed}, early_stopped={early_stopped}")
print(f"[RESULT] final_train_loss={final_train_loss:.4f}, final_val_loss={final_val_loss:.4f}")
print(f"[RESULT] final_train_acc={final_train_acc:.4f}, final_val_acc={final_val_acc:.4f}")
print(f"[RESULT] final_test_acc={float(test_acc):.4f}")
print(f"[RESULT] param_count={param_count}")
print(f"[RESULT] training_time_sec={training_time:.1f}")
print(f"[RESULT] val_unique_classes={val_unique_classes_final}")

# Confusion matrix diagonal sum
cm_diag_sum = int(np.diag(cm).sum())
cm_total = int(cm.sum())
cm_diag_ratio = cm_diag_sum / cm_total if cm_total > 0 else 0.0
print(f"[RESULT] confusion_matrix diagonal ratio: {cm_diag_ratio:.4f}")

# ─────────────────────────────────────────────
# Step 6: Verdict
# ─────────────────────────────────────────────
verdict = "PASS"
issues = []

if final_train_loss >= 1.5:
    verdict = "FAIL"
    issues.append(f"final_train_loss={final_train_loss:.4f} >= 1.5")
if final_val_acc <= 0.45:
    verdict = "FAIL"
    issues.append(f"final_val_acc={final_val_acc:.4f} <= 0.45")
if final_val_acc >= 1.0:
    verdict = "FAIL_class_collapse"
    issues.append(f"final_val_acc={final_val_acc:.4f} == 1.0 (hallucination)")
if final_val_acc < 0.15:
    verdict = "FAIL"
    issues.append(f"final_val_acc={final_val_acc:.4f} < 0.15 (very low)")
if val_unique_classes_final < 8:
    if verdict == "PASS":
        verdict = "FAIL_class_collapse"
    issues.append(f"val_unique_classes={val_unique_classes_final} < 8")
gap = final_train_acc - final_val_acc
if gap > 0.25:
    issues.append(f"WARNING: train-val gap={gap:.4f} > 0.25 (overfitting)")

print(f"\n[VERDICT] {verdict}")
for issue in issues:
    print(f"  - {issue}")

# ─────────────────────────────────────────────
# Step 7: Save model
# ─────────────────────────────────────────────
weights = model.get_weights()

# Check NaN in weights
for k, w in weights.items():
    if np.isnan(w).any():
        print(f"[WARN] NaN detected in weight {k}!")

model_dict = {
    "arch": "5-8-8-16",
    "weights": weights,
    "activation": "relu",
    "param_count": param_count,
    "input_features": FEATURE_COLS,
    "action_grid": "16 actions (T_GenCam × p_tx)",
    "seed": SEED,
    "cost_function_version": cost_version,
}

os.makedirs(os.path.dirname(OUTPUT_MODEL), exist_ok=True)
with open(OUTPUT_MODEL, "wb") as f:
    pickle.dump(model_dict, f, protocol=4)

import os as os2
pkl_size = os2.path.getsize(OUTPUT_MODEL)
print(f"\n[SAVE] Model saved to {OUTPUT_MODEL} ({pkl_size} bytes)")
assert pkl_size < 10_240, f"pkl size {pkl_size} exceeds 10KB!"

# ─────────────────────────────────────────────
# Step 8: Save log
# ─────────────────────────────────────────────
log_dict = {
    "task_id": "E4-2-redo3",
    "framework": "numpy",
    "cost_function_version": cost_version,
    "oracle_meta": meta,
    "epochs_completed": epochs_completed,
    "final_train_loss": round(float(final_train_loss), 6),
    "final_val_loss": round(float(final_val_loss), 6),
    "final_train_acc": round(float(final_train_acc), 6),
    "final_val_acc": round(float(final_val_acc), 6),
    "final_test_acc": round(float(test_acc), 6),
    "param_count": param_count,
    "model_file_size_bytes": pkl_size,
    "training_time_sec": round(training_time, 2),
    "early_stopped": early_stopped,
    "val_unique_classes": val_unique_classes_final,
    "confusion_matrix_diag_ratio": round(cm_diag_ratio, 6),
    "confusion_matrix_16x16": cm.tolist(),
    "loss_curve": loss_curve,
    "class_distribution_train": class_dist,
    "hyperparams": {
        "lr": LR,
        "batch_size": BATCH_SIZE,
        "epochs": EPOCHS,
        "hidden_dim": HIDDEN_DIM,
        "seed": SEED,
        "max_rows": MAX_ROWS,
    },
    "input_features": FEATURE_COLS,
    "verdict": verdict,
    "issues": issues,
}

os.makedirs(os.path.dirname(OUTPUT_LOG), exist_ok=True)
with open(OUTPUT_LOG, "w") as f:
    json.dump(log_dict, f, indent=2)
print(f"[SAVE] Log saved to {OUTPUT_LOG}")

# ─────────────────────────────────────────────
# Final validation report
# ─────────────────────────────────────────────
print("\n=== VALIDATION SIGNALS ===")
print(f"  final_train_loss={final_train_loss:.4f} < 1.5? {final_train_loss < 1.5}")
print(f"  final_val_acc={final_val_acc:.4f} > 0.45? {final_val_acc > 0.45}")
print(f"  final_val_acc={final_val_acc:.4f} < 1.0? {final_val_acc < 1.0}")
print(f"  val_unique_classes={val_unique_classes_final} >= 8? {val_unique_classes_final >= 8}")
print(f"  train-val gap={gap:.4f} <= 0.25? {gap <= 0.25}")
print(f"  param_count={param_count} < 2000? {param_count < 2000}")
print(f"  pkl_size={pkl_size} < 10240? {pkl_size < 10240}")
print(f"\n=== FINAL VERDICT: {verdict} ===")
