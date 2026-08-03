import numpy as np
import pandas as pd
from sklearn.linear_model import SGDRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
from dataset import get_dataloaders
from G1_learning import DATA_DIRS
import warnings
warnings.filterwarnings('ignore')

def main():
    print("Loading datasets for LR fix...")
    train_loader, val_loader, scaler = get_dataloaders(DATA_DIRS, batch_size=4096)
    
    # Flatten datasets
    X_train_ml, y_train_ml = [], []
    for x_k, x_t, x_s, y in train_loader:
        X_train_ml.append(np.concatenate([x_k.numpy(), x_t.numpy(), x_s.numpy()], axis=1))
        y_train_ml.append(y.numpy())
    X_train_ml = np.vstack(X_train_ml)
    y_train_ml = np.concatenate(y_train_ml)
    
    X_val_ml, y_val_ml = [], []
    for x_k, x_t, x_s, y in val_loader:
        X_val_ml.append(np.concatenate([x_k.numpy(), x_t.numpy(), x_s.numpy()], axis=1))
        y_val_ml.append(y.numpy())
    X_val_ml = np.vstack(X_val_ml)
    y_val_ml = np.concatenate(y_val_ml)

    # Scale specifically for ML models
    scaler_ml = StandardScaler()
    X_train_ml = scaler_ml.fit_transform(X_train_ml)
    X_val_ml = scaler_ml.transform(X_val_ml)

    print("Training LR...")
    # Use very small learning rate to avoid exploding gradients
    lr_y1 = SGDRegressor(loss='squared_error', penalty='l2', alpha=1e-3, learning_rate='constant', eta0=1e-6, random_state=42)
    lr_y2 = SGDRegressor(loss='squared_error', penalty='l2', alpha=1e-3, learning_rate='constant', eta0=1e-6, random_state=42)
    
    results = []
    
    # Initialize weights with just 1 sample to simulate "Epoch 0 Untrained" state
    lr_y1.partial_fit(X_train_ml[0:1], y_train_ml[0:1, 0])
    lr_y2.partial_fit(X_train_ml[0:1], y_train_ml[0:1, 1])
    
    preds_y1_0 = lr_y1.predict(X_val_ml)
    preds_y2_0 = lr_y2.predict(X_val_ml)
    preds_0 = np.column_stack((preds_y1_0, preds_y2_0))
    val_mae_0 = mean_absolute_error(y_val_ml, preds_0)
    
    results.append({"Model": "LR", "Step": 0, "MAE": val_mae_0})
    print(f"[LR] Epoch 0/200 (Untrained) Val MAE: {val_mae_0:.4f}")
    
    # 200 epochs
    for ep in range(1, 201):
        idx = np.random.permutation(len(X_train_ml))
        lr_y1.partial_fit(X_train_ml[idx], y_train_ml[idx, 0])
        lr_y2.partial_fit(X_train_ml[idx], y_train_ml[idx, 1])
        
        preds_y1 = lr_y1.predict(X_val_ml)
        preds_y2 = lr_y2.predict(X_val_ml)
        preds = np.column_stack((preds_y1, preds_y2))
        val_mae = mean_absolute_error(y_val_ml, preds)
        
        results.append({"Model": "LR", "Step": ep, "MAE": val_mae})
        
        if ep % 20 == 0:
            print(f"[LR] Epoch {ep}/200 Val MAE: {val_mae:.4f}")

    df = pd.DataFrame(results)
    df.to_csv("/home/imnyj/papers/paper1/data/G1/LR_learning_curves.csv", index=False)
    print("Saved LR learning curves.")

    # Remove LR from LR_RF_learning_curves.csv
    lrrf_path = "/home/imnyj/papers/paper1/data/G1/LR_RF_learning_curves.csv"
    lrrf_df = pd.read_csv(lrrf_path)
    lrrf_df = lrrf_df[lrrf_df["Model"] != "LR"]
    lrrf_df.to_csv(lrrf_path, index=False)
    print("Removed LR from LR_RF_learning_curves.csv")

if __name__ == "__main__":
    main()
