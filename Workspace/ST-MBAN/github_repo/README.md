# H-ST-MBAN (Hybrid Spatio-Temporal Multi-Branch Attention Network)

This repository contains the official PyTorch implementation and a cleaned sample dataset for the paper:
**"Edge-Assisted Content Precaching via Hybrid Spatio-Temporal Multi-Branched Attention Networks in CCVNs"**
*(To be submitted to IEEE Transactions on Intelligent Transportation Systems)*

## Overview
In Content-Centric Vehicular Networks (CCVNs), proactive edge caching requires precise vehicle dwell time prediction at the Road-Side Unit (RSU). Existing sequence-based models struggle with single-snapshot inference and suffer from continuous uplink delays. 

**H-ST-MBAN** solves this by:
1. **Multi-Branch Partitioning**: Separating heterogeneous tabular data into Kinematic, Traffic Control, and Social branches to prevent gradient conflicts.
2. **Domain-Level Attention Fusion**: Integrating domain tokens via a Multi-Head Attention (MHA) layer.
3. **Hybrid Tabular Prior**: Fusing a Gradient-Boosted Decision Tree (XGBoost) prior with the neural network using a learnable gating mechanism to capture sharp decision boundaries.

## Repository Structure
- `model.py`: Contains the PyTorch implementation of `H_ST_MBAN` and the required `ResidualBlock`.
- `train.py`: A simple training script demonstrating how to load the dataset, train the XGBoost prior, and train the H-ST-MBAN PyTorch model using Optuna-optimized hyperparameters.
- `dataset_sample.csv`: A cleaned and sampled dataset (85k rows) generated from SUMO traffic simulations. Outliers with exceedingly long dwell times (> 400s) have been filtered out to ensure stable training.

## Data Schema
The input features are 30-dimensional vectors categorized into:
- **Kinematic (K)**: Vehicle velocities, distances (e.g., $d_{\text{rsu}}$, $v_{c,a}$).
- **Traffic Control (T)**: Signal phases, timing to next phase (e.g., $\text{tls}_{c}$, $\text{tlt}_{c}$).
- **Social (S)**: Queue lengths, vehicle densities (e.g., $n_{\text{cur}}$, $\text{occ}_{\text{cur}}$).

Targets:
- `dwell_cur`: Real-measured dwell time at the current RSU.
- `dwell_nxt`: Real-measured dwell time at the next expected RSU.

## Usage
You can initialize the model and pass your partitioned tensors along with the XGBoost priors:
```python
import torch
from model import H_ST_MBAN

# Initialize model
model = H_ST_MBAN(k_dim=7, t_dim=4, s_dim=17)

# Dummy inputs (batch_size=32)
x_k = torch.randn(32, 7)
x_t = torch.randn(32, 4)
x_s = torch.randn(32, 17)

# XGBoost priors (optional but recommended for optimal performance)
xgb_priors = torch.randn(32, 2)

# Forward pass
predictions = model(x_k, x_t, x_s, ml_preds=xgb_priors)
```

## Citation
If you find this code or dataset useful in your research, please cite our upcoming paper in IEEE T-ITS.
