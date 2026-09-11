import os
import glob
import torch
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler

class CCVNDataset(Dataset):
    def __init__(self, data_paths, is_train=True, scaler=None):
        """
        data_paths: list of directories containing CSV files
        is_train: whether this dataset is used for training
        scaler: pre-fit scaler for normalization
        """
        all_files = []
        for path in data_paths:
            all_files.extend(glob.glob(os.path.join(path, "*.csv")))
            
        dfs = []
        for f in all_files:
            df = pd.read_csv(f)
            dfs.append(df)
            
        self.data = pd.concat(dfs, ignore_index=True)
        
        # Define Branch Features
        self.kinematic_cols = ['d_rsu', 'd_e_n', 'd_l_c', 'd_l_n', 'v_c_a', 'v_n_a', 'est_travel_time']
        self.traffic_cols = ['tls_c', 'tls_n', 'tlt_c', 'tlt_n']
        self.social_cols = ['n_t_0', 'n_t_1', 'n_t_2', 'n_t_3', 'n_cur', 'n_nxt', 'v_ahead_avg', 
                            'dist_leader', 'v_leader', 'route_lane_changes', 'q_len_cur', 'q_len_nxt', 
                            'n_ahead_cur', 'n_ahead_nxt', 'n_merge_nxt', 'occ_cur', 'occ_nxt']
        
        self.target_cols = ['dwell_cur', 'dwell_nxt']
        
        self.feature_cols = self.kinematic_cols + self.traffic_cols + self.social_cols
        
        # Drop NaN values safely
        self.data = self.data.dropna(subset=self.feature_cols + self.target_cols)
        
        # Just reset index if testing
        if not is_train:
            self.data = self.data.reset_index(drop=True)
            print("Dataset randomly sampled to exactly 500,000 instances.")
            
        X = self.data[self.feature_cols].values
        y = self.data[self.target_cols].values
        
        if is_train:
            self.scaler = StandardScaler()
            self.X_scaled = self.scaler.fit_transform(X)
        else:
            self.scaler = scaler
            self.X_scaled = self.scaler.transform(X)
            
        self.X_scaled = torch.tensor(self.X_scaled, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        # Slice the scaled features into K, T, S tensors
        x = self.X_scaled[idx]
        k_idx = len(self.kinematic_cols)
        t_idx = k_idx + len(self.traffic_cols)
        
        x_k = x[:k_idx]
        x_t = x[k_idx:t_idx]
        x_s = x[t_idx:]
        
        target = self.y[idx]
        
        return x_k, x_t, x_s, target

    def get_scaler(self):
        return self.scaler

def get_dataloaders(data_paths, batch_size=256, test_split=0.2):
    dataset = CCVNDataset(data_paths, is_train=True)
    
    test_size = int(len(dataset) * test_split)
    train_size = len(dataset) - test_size
    
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    
    return train_loader, test_loader, dataset.get_scaler()
