import torch
import torch.nn as nn

class ResidualBlock(nn.Module):
    def __init__(self, d_model, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.BatchNorm1d(d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model),
            nn.BatchNorm1d(d_model),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, d_model)
        )
    def forward(self, x):
        return x + self.net(x)

class Baseline_MLP(nn.Module):
    def __init__(self, in_dim=28, hidden_dim=128, num_layers=3, out_dim=2, dropout=0.0):
        super(Baseline_MLP, self).__init__()
        layers = []
        curr_dim = in_dim
        for _ in range(num_layers):
            layers.append(nn.Linear(curr_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            curr_dim = hidden_dim
        layers.append(nn.Linear(hidden_dim, out_dim))
        self.net = nn.Sequential(*layers)
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1)
        return self.net(x)

class Baseline_LSTM(nn.Module):
    def __init__(self, in_dim, hidden_dim=64, num_layers=2, dropout=0.1, out_dim=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_dim, out_dim)
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1).unsqueeze(-1) # (batch, 28, 1)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

class Baseline_GRU(nn.Module):
    def __init__(self, in_dim=28, hidden_dim=64, num_layers=2, out_dim=2, dropout=0.0):
        super().__init__()
        self.gru = nn.GRU(input_size=1, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_dim, out_dim)
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1).unsqueeze(-1) # (batch, 28, 1)
        out, _ = self.gru(x)
        return self.fc(out[:, -1, :])

class Baseline_FTT(nn.Module):
    def __init__(self, in_dim=28, d_model=32, n_heads=4, num_layers=2, out_dim=2):
        super().__init__()
        self.tokenizer = nn.ModuleList([nn.Linear(1, d_model) for _ in range(in_dim)])
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, out_dim)
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1) # (batch, 28)
        tokens = [self.tokenizer[i](x[:, i:i+1]).unsqueeze(1) for i in range(x.size(1))]
        x_seq = torch.cat(tokens, dim=1) # (batch, 28, d_model)
        cls_tokens = self.cls_token.expand(x.size(0), -1, -1) # (batch, 1, d_model)
        x_seq = torch.cat((cls_tokens, x_seq), dim=1) # (batch, 29, d_model)
        
        out = self.transformer(x_seq)
        return self.fc(out[:, 0, :])

class Baseline_TabR(nn.Module):
    def __init__(self, in_dim=28, hidden_dim=128, num_layers=2, out_dim=2):
        super().__init__()
        self.first = nn.Linear(in_dim, hidden_dim)
        self.blocks = nn.ModuleList([
            nn.Sequential(
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim)
            ) for _ in range(num_layers)
        ])
        self.head = nn.Sequential(
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, out_dim)
        )
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1)
        x = self.first(x)
        for block in self.blocks:
            x = x + block(x)
        return self.head(x)

class Baseline_ResNet(nn.Module):
    def __init__(self, in_dim=28, hidden_dim=128, num_layers=3, out_dim=2, dropout=0.1):
        super(Baseline_ResNet, self).__init__()
        self.proj = nn.Linear(in_dim, hidden_dim)
        
        self.res_blocks = nn.ModuleList([
            nn.Sequential(
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim)
            ) for _ in range(num_layers)
        ])
        
        self.out = nn.Sequential(
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, out_dim)
        )
        
    def forward(self, x_k, x_t, x_s):
        x = torch.cat([x_k, x_t, x_s], dim=1)
        x = self.proj(x)
        for block in self.res_blocks:
            x = x + block(x)
        return self.out(x)

class H_ST_MBAN(nn.Module):
    # Hybrid ST-MBAN combining NN with XGBoost priors (Formerly H_ST_MBAN)
    def __init__(self, k_dim=7, t_dim=4, s_dim=17, d_model=128, n_heads=4, num_layers=4, out_dim=2):
        super().__init__()
        # Basic Encoded Branches
        self.proj_k = nn.Sequential(nn.Linear(k_dim, d_model), ResidualBlock(d_model))
        self.proj_t = nn.Sequential(nn.Linear(t_dim, d_model), ResidualBlock(d_model))
        self.proj_s = nn.Sequential(nn.Linear(s_dim, d_model), ResidualBlock(d_model))
        
        self.attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=0.1)
        self.norm = nn.LayerNorm(d_model)
        
        combined_dim = d_model * 3
        
        # Deep Residual Blocks
        self.res_blocks = nn.ModuleList([
            ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)
        ])
        
        # Output Head
        self.out = nn.Sequential(
            nn.BatchNorm1d(combined_dim),
            nn.ReLU(),
            nn.Linear(combined_dim, 64),
            nn.ReLU(),
            nn.Linear(64, out_dim)
        )
        
        # Learnable gating for Hybrid (Initialize to 1 and 0.01 for Residual Prior Learning)
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))

    def forward(self, x_k, x_t, x_s, ml_preds=None):
        e_k = self.proj_k(x_k).unsqueeze(1)
        e_t = self.proj_t(x_t).unsqueeze(1)
        e_s = self.proj_s(x_s).unsqueeze(1)
        
        # Concatenate embeddings
        seq = torch.cat([e_k, e_t, e_s], dim=1)
        
        # Attention
        attn_out, _ = self.attn(seq, seq, seq)
        seq = self.norm(seq + attn_out)
        
        # Flatten and pass through Residual Blocks
        flat = seq.reshape(seq.size(0), -1)
        for block in self.res_blocks:
            flat = block(flat)
            
        nn_out = self.out(flat)
        
        if ml_preds is not None:
            return ml_preds * self.alpha + nn_out * self.beta
            
        return nn_out

class H_ST_MBAN_noAttn(nn.Module):
    def __init__(self, k_dim=7, t_dim=4, s_dim=17, d_model=128, num_layers=4, out_dim=2):
        super().__init__()
        self.proj_k = nn.Sequential(nn.Linear(k_dim, d_model), ResidualBlock(d_model))
        self.proj_t = nn.Sequential(nn.Linear(t_dim, d_model), ResidualBlock(d_model))
        self.proj_s = nn.Sequential(nn.Linear(s_dim, d_model), ResidualBlock(d_model))
        combined_dim = d_model * 3
        self.res_blocks = nn.ModuleList([ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)])
        self.out = nn.Sequential(nn.BatchNorm1d(combined_dim), nn.ReLU(), nn.Linear(combined_dim, 64), nn.ReLU(), nn.Linear(64, out_dim))
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))
    def forward(self, x_k, x_t, x_s, ml_preds=None):
        e_k, e_t, e_s = self.proj_k(x_k), self.proj_t(x_t), self.proj_s(x_s)
        flat = torch.cat([e_k, e_t, e_s], dim=1)
        for block in self.res_blocks: flat = block(flat)
        nn_out = self.out(flat)
        if ml_preds is not None: return ml_preds * self.alpha + nn_out * self.beta
        return nn_out

class H_ST_MBAN_EarlyFusion(nn.Module):
    def __init__(self, k_dim=7, t_dim=4, s_dim=17, d_model=128, num_layers=4, out_dim=2):
        super().__init__()
        in_dim = k_dim + t_dim + s_dim
        combined_dim = d_model * 3
        self.proj = nn.Sequential(nn.Linear(in_dim, combined_dim), ResidualBlock(combined_dim))
        self.res_blocks = nn.ModuleList([ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)])
        self.out = nn.Sequential(nn.BatchNorm1d(combined_dim), nn.ReLU(), nn.Linear(combined_dim, 64), nn.ReLU(), nn.Linear(64, out_dim))
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))
    def forward(self, x_k, x_t, x_s, ml_preds=None):
        flat = self.proj(torch.cat([x_k, x_t, x_s], dim=1))
        for block in self.res_blocks: flat = block(flat)
        nn_out = self.out(flat)
        if ml_preds is not None: return ml_preds * self.alpha + nn_out * self.beta
        return nn_out

class H_ST_MBAN_noS(nn.Module):
    def __init__(self, k_dim=7, t_dim=4, d_model=128, n_heads=4, num_layers=4, out_dim=2):
        super().__init__()
        self.proj_k = nn.Sequential(nn.Linear(k_dim, d_model), ResidualBlock(d_model))
        self.proj_t = nn.Sequential(nn.Linear(t_dim, d_model), ResidualBlock(d_model))
        self.attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=0.1)
        self.norm = nn.LayerNorm(d_model)
        combined_dim = d_model * 2
        self.res_blocks = nn.ModuleList([ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)])
        self.out = nn.Sequential(nn.BatchNorm1d(combined_dim), nn.ReLU(), nn.Linear(combined_dim, 64), nn.ReLU(), nn.Linear(64, out_dim))
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))
    def forward(self, x_k, x_t, x_s, ml_preds=None):
        seq = torch.cat([self.proj_k(x_k).unsqueeze(1), self.proj_t(x_t).unsqueeze(1)], dim=1)
        attn_out, _ = self.attn(seq, seq, seq)
        flat = self.norm(seq + attn_out).reshape(seq.size(0), -1)
        for block in self.res_blocks: flat = block(flat)
        nn_out = self.out(flat)
        if ml_preds is not None: return ml_preds * self.alpha + nn_out * self.beta
        return nn_out

class H_ST_MBAN_noT(nn.Module):
    def __init__(self, k_dim=7, s_dim=17, d_model=128, n_heads=4, num_layers=4, out_dim=2):
        super().__init__()
        self.proj_k = nn.Sequential(nn.Linear(k_dim, d_model), ResidualBlock(d_model))
        self.proj_s = nn.Sequential(nn.Linear(s_dim, d_model), ResidualBlock(d_model))
        self.attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=0.1)
        self.norm = nn.LayerNorm(d_model)
        combined_dim = d_model * 2
        self.res_blocks = nn.ModuleList([ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)])
        self.out = nn.Sequential(nn.BatchNorm1d(combined_dim), nn.ReLU(), nn.Linear(combined_dim, 64), nn.ReLU(), nn.Linear(64, out_dim))
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))
    def forward(self, x_k, x_t, x_s, ml_preds=None):
        seq = torch.cat([self.proj_k(x_k).unsqueeze(1), self.proj_s(x_s).unsqueeze(1)], dim=1)
        attn_out, _ = self.attn(seq, seq, seq)
        flat = self.norm(seq + attn_out).reshape(seq.size(0), -1)
        for block in self.res_blocks: flat = block(flat)
        nn_out = self.out(flat)
        if ml_preds is not None: return ml_preds * self.alpha + nn_out * self.beta
        return nn_out

class H_ST_MBAN_noK(nn.Module):
    def __init__(self, t_dim=4, s_dim=17, d_model=128, n_heads=4, num_layers=4, out_dim=2):
        super().__init__()
        self.proj_t = nn.Sequential(nn.Linear(t_dim, d_model), ResidualBlock(d_model))
        self.proj_s = nn.Sequential(nn.Linear(s_dim, d_model), ResidualBlock(d_model))
        self.attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=0.1)
        self.norm = nn.LayerNorm(d_model)
        combined_dim = d_model * 2
        self.res_blocks = nn.ModuleList([ResidualBlock(combined_dim, dropout=0.1) for _ in range(num_layers)])
        self.out = nn.Sequential(nn.BatchNorm1d(combined_dim), nn.ReLU(), nn.Linear(combined_dim, 64), nn.ReLU(), nn.Linear(64, out_dim))
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))
    def forward(self, x_k, x_t, x_s, ml_preds=None):
        seq = torch.cat([self.proj_t(x_t).unsqueeze(1), self.proj_s(x_s).unsqueeze(1)], dim=1)
        attn_out, _ = self.attn(seq, seq, seq)
        flat = self.norm(seq + attn_out).reshape(seq.size(0), -1)
        for block in self.res_blocks: flat = block(flat)
        nn_out = self.out(flat)
        if ml_preds is not None: return ml_preds * self.alpha + nn_out * self.beta
        return nn_out
