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

class H_ST_MBAN(nn.Module):
    """
    Hybrid Spatio-Temporal Multi-Branch Attention Network (H-ST-MBAN)
    
    This model processes tabular data by partitioning features into three branches:
    Kinematic (K), Traffic Control (T), and Social (S). It uses pre-activation 
    residual blocks to prevent gradient conflicts and fuses them with a 
    Multi-Head Attention (MHA) layer. Finally, it uses a learnable gating 
    mechanism to combine the neural network output with an XGBoost-based prior.
    """
    def __init__(self, k_dim=7, t_dim=4, s_dim=17, d_model=128, n_heads=4, num_layers=4, out_dim=2):
        super().__init__()
        # Basic Encoded Branches
        self.proj_k = nn.Sequential(nn.Linear(k_dim, d_model), ResidualBlock(d_model))
        self.proj_t = nn.Sequential(nn.Linear(t_dim, d_model), ResidualBlock(d_model))
        self.proj_s = nn.Sequential(nn.Linear(s_dim, d_model), ResidualBlock(d_model))
        
        # Cross-Domain Attention Fusion
        self.attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=0.1)
        self.norm = nn.LayerNorm(d_model)
        
        combined_dim = d_model * 3
        
        # Deep Residual Blocks for Decoder
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
        
        # Learnable gating for Hybrid Prior Learning
        # Alpha scales the GBDT (XGBoost) prior, Beta scales the NN residual
        self.alpha = nn.Parameter(torch.tensor(0.01))
        self.beta = nn.Parameter(torch.tensor(1.0))

    def forward(self, x_k, x_t, x_s, ml_preds=None):
        e_k = self.proj_k(x_k).unsqueeze(1)
        e_t = self.proj_t(x_t).unsqueeze(1)
        e_s = self.proj_s(x_s).unsqueeze(1)
        
        # Sequence formulation: 3 tokens representing 3 domains
        seq = torch.cat([e_k, e_t, e_s], dim=1)
        
        # Domain-level Multi-Head Attention Fusion
        attn_out, _ = self.attn(seq, seq, seq)
        seq = self.norm(seq + attn_out)
        
        # Flatten and pass through Residual Blocks
        flat = seq.reshape(seq.size(0), -1)
        for block in self.res_blocks:
            flat = block(flat)
            
        nn_out = self.out(flat)
        
        # Gated fusion with ML prior if provided
        if ml_preds is not None:
            return ml_preds * self.alpha + nn_out * self.beta
            
        return nn_out
