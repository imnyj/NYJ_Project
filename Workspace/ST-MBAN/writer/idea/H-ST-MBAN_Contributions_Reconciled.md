# H-ST-MBAN Contributions & Reconciliation (Updated based on models.py)

## 1. Reconciled Differences (Theory vs. Code)
*   **Loss Function**: 
    *   *Theoretical*: Huber Loss
    *   *Actual Code*: L1Loss (MAE)
    *   *Reconciliation*: L1 Loss is utilized to guarantee robust learning against extreme traffic outliers, such as unexpected jams or sudden sensor anomalies.
*   **Hybrid Gating Mechanism**:
    *   *Theoretical*: $\alpha=1.0$, $\beta=0.0$
    *   *Actual Code*: `ml_preds * 0.01 + nn_out * 1.0`
    *   *Reconciliation*: The Neural Network (NN) acts as the primary driver for complex non-linear spatial-temporal regression ($\beta=1.0$). The Machine Learning (ML) prediction (e.g., XGBoost) is downscaled ($\alpha=0.01$) to serve as a stable structural prior/bias, anchoring the NN's learning process.
*   **Temporal Encoding**:
    *   *Theoretical*: Cyclical Temporal Encoding (CTE)
    *   *Actual Code*: Direct processing via Residual Blocks
    *   *Reconciliation*: Instead of fixed cyclical encoding, the model leverages deep Residual Blocks (ResBlocks) on the raw traffic features. This maximizes representation power and allows the network to learn optimal, data-driven domain representations.
*   **Decoder Type**:
    *   *Theoretical*: Generative approaches 
    *   *Actual Code*: Flatten -> ResBlocks -> Output Head (Deterministic)
    *   *Reconciliation*: The model is explicitly designed as a robust deterministic forecaster.

## 2. Compiled Academic Contributions

1.  **Hybrid Architecture with ML Prior (Hybrid)**
    *   *Structure*: A gating integration where the final prediction is formed by $0.01 \times \text{ML\_Pred} + 1.0 \times \text{NN\_Pred}$.
    *   *Operation*: Combines the broad generalization of classical tree-based ML models with the deep feature extraction of neural networks.
    *   *Reasoning*: The ML model acts as a residual prior that stabilizes the loss landscape, allowing the NN to focus purely on complex spatial-temporal dynamics without drifting during early training phases.
2.  **3-Branch Feature Extraction via Deep ResBlocks (3-Branch)**
    *   *Structure*: Three independent branches for Kinematic (K=7), Topological (T=4), and Spatial (S=17) inputs. Each branch consists of a Linear layer followed by a ResBlock (BatchNorm1d -> ReLU -> Linear -> Dropout).
    *   *Operation*: Projects varying input dimensions into a uniform hidden dimension ($d_{model}$) while preserving domain-specific characteristics.
    *   *Reasoning*: Bypassing rigid cyclical encoders, the ResBlocks provide high representation capacity, preventing gradient vanishing and ensuring each domain is deeply encoded before fusion.
3.  **Domain-Level Multi-Head Attention Fusion (MHA Fusion)**
    *   *Structure*: Encoded K, T, and S features are concatenated into a sequence `(batch, 3, d_model)` and fed into a Multi-Head Attention block (4 heads) with Residual connection and LayerNorm.
    *   *Operation*: Treats the three feature domains as sequential tokens.
    *   *Reasoning*: MHA dynamically computes the inter-dependencies across domains. It adaptively weights how topological constraints influence spatial traffic flow and kinematic states, yielding a richly fused representation.
4.  **Robust Deterministic Decoding with L1 Loss (Deterministic Decoder)**
    *   *Structure*: The fused `(batch, 3, d_model)` tensor is flattened to 384 dimensions, processed through 4 stacked ResBlocks, and mapped to the final output via an MLP head. Optimized via L1Loss.
    *   *Operation*: Directly maps the fused latent representation to deterministic traffic forecasts.
    *   *Reasoning*: Prioritizes stable, reliable point-estimate predictions. The multi-layer ResBlock decoder ensures sufficient depth to untangle the fused features, while L1 Loss provides strong robustness against noisy sensor data and extreme traffic anomalies.
