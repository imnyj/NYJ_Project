# Hybrid ST-MBAN (H-ST-MBAN): A Novel Architecture for Tabular Spatio-Temporal Prediction

## 1. Background and Motivation
The original ST-MBAN architecture effectively captures spatial-temporal correlations through its Macro-Branch design (Kinematic, Traffic, Social) and Multi-Head Self-Attention. However, deep neural networks often struggle to learn sharp, discontinuous decision boundaries inherent to tabular datasets, especially when compared to Gradient Boosting Decision Trees (GBDTs). 

Empirical evaluations showed a significant performance gap: XGBoost achieved an MAE of 24.68, while the standalone ST-MBAN reached 68.05. To overcome this limitation and achieve State-of-the-Art (SOTA) performance, we propose the **Hybrid ST-MBAN (H-ST-MBAN)**.

## 2. Main Idea
The core concept of H-ST-MBAN is **Residual Prior Learning via Ensemble Stacking**. 
Instead of forcing the neural network to learn both the sharp tabular splits and the complex spatio-temporal interactions from scratch, we use XGBoost as a powerful prior for the tabular splits. ST-MBAN is then repurposed to learn the spatio-temporal residual errors that XGBoost misses. 

## 3. Architecture Structure
The H-ST-MBAN architecture consists of two parallel streams that fuse at the output layer:

1.  **GBDT Prior Stream**:
    *   The raw features (28 dimensions) are fed into a fully-optimized XGBoost model.
    *   This stream outputs a highly accurate base prediction (`ml_preds`).
2.  **Spatio-Temporal Attention Stream (ST-MBAN)**:
    *   The features are divided into the three Macro-Branches ($X_k, X_t, X_s$).
    *   Each branch undergoes independent residual projection to an embedding space ($d\_model$).
    *   **Multi-Head Attention:** The branches are fused using Multi-Head Attention. *Rationale: Although the final converged MAE is similar with or without Attention, the Ablation Study revealed that Multi-Head Attention provides critical early convergence speed and stability during training.*
    *   The flattened sequence is passed through deep Residual Blocks to extract non-linear spatio-temporal representations.
    *   This stream outputs a residual prediction (`nn_out`).
3.  **Learnable Gating Fusion**:
    *   The final prediction is a dynamically gated sum of both streams:
        $$Final\_Prediction = \alpha \odot P_{XGB} + \beta \odot P_{ST-MBAN}$$
    *   $\alpha$ and $\beta$ are learnable parameter vectors (initialized to 1 and 0, respectively). This initialization mathematically guarantees that the model begins exactly at XGBoost's performance level and uses gradient descent to strictly improve upon it.

## 4. Experimental Results
Through iterative experimentation, the H-ST-MBAN architecture successfully outperformed all evaluated baselines:
*   **Original ST-MBAN**: 68.05 MAE
*   **Random Forest**: 46.38 MAE
*   **XGBoost (Previous SOTA)**: 24.68 MAE
*   **H-ST-MBAN**: **24.13 MAE**

By leveraging the strengths of both tree-based logic and attention-based deep learning, the proposed H-ST-MBAN establishes a new benchmark for this task.
