import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from model import H_ST_MBAN

class CCVNDataset(Dataset):
    def __init__(self, df):
        # Kinematic (7), Traffic (4), Social (17)
        self.k_features = df[['v_c_a', 'v_n_a', 'v_ahead_avg', 'dist_leader', 'v_leader', 'd_rsu', 'd_e_n']].values
        self.t_features = df[['tls_c', 'tls_n', 'tlt_c', 'tlt_n']].values
        self.s_features = df[['n_t_0', 'n_t_1', 'n_t_2', 'n_t_3', 'd_l_c', 'd_l_n', 'n_cur', 'n_nxt', 
                              'route_lane_changes', 'q_len_cur', 'q_len_nxt', 'n_ahead_cur', 
                              'n_ahead_nxt', 'n_merge_nxt', 'occ_cur', 'occ_nxt', 'est_travel_time']].values
        
        # Targets
        self.targets = df[['dwell_cur', 'dwell_nxt']].values
        
        # All features combined for XGBoost
        self.all_features = np.hstack([self.k_features, self.t_features, self.s_features])

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.k_features[idx], dtype=torch.float32),
            torch.tensor(self.t_features[idx], dtype=torch.float32),
            torch.tensor(self.s_features[idx], dtype=torch.float32),
            torch.tensor(self.all_features[idx], dtype=torch.float32),
            torch.tensor(self.targets[idx], dtype=torch.float32)
        )

def train():
    print("Loading dataset...")
    df = pd.read_csv("dataset_sample.csv")
    
    # Simple split
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
    
    # Normalization
    scaler = StandardScaler()
    feature_cols = [c for c in df.columns if c not in ['veh_id', 'cur_rsu', 'next_rsu', 'dirct', 'dwell_cur', 'dwell_nxt']]
    
    train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])
    
    train_dataset = CCVNDataset(train_df)
    test_dataset = CCVNDataset(test_df)
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)
    
    # Train XGBoost Prior
    print("Training XGBoost Prior...")
    xgb_prior = XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=42)
    xgb_prior.fit(train_dataset.all_features, train_dataset.targets)
    
    # Optuna Optimized Hyperparameters for H-ST-MBAN
    d_model = 256
    n_heads = 8
    lr = 0.002823
    
    print("Initializing H-ST-MBAN model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = H_ST_MBAN(k_dim=7, t_dim=4, s_dim=17, d_model=d_model, n_heads=n_heads, num_layers=4, out_dim=2).to(device)
    
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.L1Loss() # MAE Loss
    
    epochs = 10
    print("Starting training...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        
        for k, t, s, all_f, targets in train_loader:
            k, t, s, targets = k.to(device), t.to(device), s.to(device), targets.to(device)
            
            # Get ML prior predictions
            with torch.no_grad():
                ml_preds = torch.tensor(xgb_prior.predict(all_f.numpy()), dtype=torch.float32).to(device)
            
            optimizer.zero_grad()
            outputs = model(k, t, s, ml_preds=ml_preds)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            
        print(f"Epoch {epoch+1}/{epochs} | Train MAE Loss: {train_loss/len(train_loader):.4f}")

if __name__ == "__main__":
    train()
