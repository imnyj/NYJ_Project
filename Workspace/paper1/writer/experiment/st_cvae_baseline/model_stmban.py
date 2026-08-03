"""
ST-MBAN: Spatio-Temporal Multi-Branch Attention Network (PyTorch)
Architecture:
  - K Branch: Kinematic encoder (Linear → ResBlock)
  - T Branch: Traffic control encoder with Cyclical Temporal Encoding (CTE)
  - S Branch: Social encoder with SE-block (feature-wise attention)
  - MHA Fusion: Multi-Head Self-Attention over [Z_k, Z_t, Z_s]
  - Decoder: ResBlock × 2 → Linear(2)
Reference: 새로운 예측 모델 구조 설계.md
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

# ── 피처 분할 상수 ──────────────────────────────────────────────────────────
# FEATURE_COLS 순서: K(13) | T(6) | S(11) = 30 features
K_DIM      = 13   # X[:, :13]   (r_cov, dirct, d_l_c, d_e_n, d_l_n, d_rsu, v_c_a, v_n_a, v_ahead_avg, dist_leader, v_leader, est_travel_time, route_lane_changes)
T_DIM_RAW  = 6    # X[:, 13:19] (tls_c, tls_n, tlt_c, tlt_n, q_len_cur, q_len_nxt)
T_DIM_ENC  = 10   # CTE 적용 후: 4×2 + 2 = 10
S_DIM      = 11   # X[:, 19:]   (n_t_0~3, n_cur, n_nxt, n_ahead_cur, n_ahead_nxt, occ_cur, occ_nxt, n_merge_nxt)

# T Branch 내 신호 변수 인덱스 (T_raw 기준, T_raw = X[:, 13:19])
_TLS_C_IDX = 0   # tls_c  → CTE T_sig
_TLS_N_IDX = 1   # tls_n  → CTE T_sig
_TLT_C_IDX = 2   # tlt_c  → CTE T_phase
_TLT_N_IDX = 3   # tlt_n  → CTE T_phase
# q_len_cur = T_raw[:, 4], q_len_nxt = T_raw[:, 5]  → CTE 없음


# ── 재사용 가능 빌딩블록 ────────────────────────────────────────────────────

class ReGLU(nn.Module):
    """Rectified Gated Linear Unit: x_left * ReLU(x_right)"""
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1, x2 = x.chunk(2, dim=-1)
        return x1 * F.relu(x2)


class ResBlock(nn.Module):
    """
    ResBlock: LayerNorm → Linear(d→2d) → ReGLU → Dropout → LayerNorm → Linear(d→2d) → ReGLU
    + Skip Connection
    """
    def __init__(self, d: int, dropout: float = 0.1):
        super().__init__()
        self.norm1   = nn.LayerNorm(d)
        self.linear1 = nn.Linear(d, d * 2)
        self.reglu1  = ReGLU()
        self.dropout = nn.Dropout(dropout)
        self.norm2   = nn.LayerNorm(d)
        self.linear2 = nn.Linear(d, d * 2)
        self.reglu2  = ReGLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.reglu1(self.linear1(self.norm1(x)))
        out = self.dropout(out)
        out = self.reglu2(self.linear2(self.norm2(out)))
        return out + residual


# ── Cyclical Temporal Encoding ──────────────────────────────────────────────

class CyclicalTemporalEncoding(nn.Module):
    """
    φ(t, T) = (sin(2π·t/T), cos(2π·t/T))
    T_sig   : 신호 위상 주기 (tls_c, tls_n)
    T_phase : 위상까지 남은 시간 주기 (tlt_c, tlt_n)
    입력 shape: (batch, 6)  [tls_c, tls_n, tlt_c, tlt_n, q_len_cur, q_len_nxt]
    출력 shape: (batch, 10) [sin/cos×4 + q_len_cur + q_len_nxt]
    """
    def __init__(self, T_sig: float = 90.0, T_phase: float = 30.0):
        super().__init__()
        self.T_sig   = T_sig
        self.T_phase = T_phase

    def forward(self, t_raw: torch.Tensor) -> torch.Tensor:
        # t_raw: (batch, 6)
        tls_c    = t_raw[:, _TLS_C_IDX]
        tls_n    = t_raw[:, _TLS_N_IDX]
        tlt_c    = t_raw[:, _TLT_C_IDX]
        tlt_n    = t_raw[:, _TLT_N_IDX]
        q_cur    = t_raw[:, 4]
        q_nxt    = t_raw[:, 5]

        two_pi = 2.0 * math.pi
        sin_tls_c = torch.sin(two_pi * tls_c / self.T_sig)
        cos_tls_c = torch.cos(two_pi * tls_c / self.T_sig)
        sin_tls_n = torch.sin(two_pi * tls_n / self.T_sig)
        cos_tls_n = torch.cos(two_pi * tls_n / self.T_sig)
        sin_tlt_c = torch.sin(two_pi * tlt_c / self.T_phase)
        cos_tlt_c = torch.cos(two_pi * tlt_c / self.T_phase)
        sin_tlt_n = torch.sin(two_pi * tlt_n / self.T_phase)
        cos_tlt_n = torch.cos(two_pi * tlt_n / self.T_phase)

        # 출력: (batch, 10)
        out = torch.stack([
            sin_tls_c, cos_tls_c,
            sin_tls_n, cos_tls_n,
            sin_tlt_c, cos_tlt_c,
            sin_tlt_n, cos_tlt_n,
            q_cur, q_nxt,
        ], dim=-1)
        return out  # (batch, 10)


# ── Branch Encoders ─────────────────────────────────────────────────────────

class KBranchEncoder(nn.Module):
    """Kinematic Branch: Linear(12 → d) → ResBlock(d)"""
    def __init__(self, d: int, dropout: float = 0.1):
        super().__init__()
        self.proj    = nn.Linear(K_DIM, d)
        self.resblock = ResBlock(d, dropout)

    def forward(self, x_k: torch.Tensor) -> torch.Tensor:
        return self.resblock(self.proj(x_k))


class TBranchEncoder(nn.Module):
    """
    Traffic Control Branch:
    CTE(6→10) → Linear(10 → d) → ResBlock(d)
    """
    def __init__(self, d: int, dropout: float = 0.1,
                 T_sig: float = 90.0, T_phase: float = 30.0):
        super().__init__()
        self.cte      = CyclicalTemporalEncoding(T_sig, T_phase)
        self.proj     = nn.Linear(T_DIM_ENC, d)
        self.resblock = ResBlock(d, dropout)

    def forward(self, x_t: torch.Tensor) -> torch.Tensor:
        enc = self.cte(x_t)               # (batch, 10)
        return self.resblock(self.proj(enc))


class SEBlock(nn.Module):
    """
    Squeeze-and-Excitation block (Hu et al., SENet).
    Feature-wise attention:
      a = sigmoid(W2 · ReLU(W1 · x + b1) + b2)
      out = a ⊙ x
    Reduction ratio: 11 → 4 → 11
    """
    def __init__(self, in_dim: int = S_DIM, reduction: int = 4):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, reduction)
        self.fc2 = nn.Linear(reduction, in_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a = torch.sigmoid(self.fc2(F.relu(self.fc1(x))))
        return a * x


class SBranchEncoder(nn.Module):
    """
    Social Branch:
    SEBlock(9→9) → Linear(9 → d) → ResBlock(d)
    """
    def __init__(self, d: int, dropout: float = 0.1):
        super().__init__()
        self.se_block = SEBlock(in_dim=S_DIM, reduction=4)
        self.proj     = nn.Linear(S_DIM, d)
        self.resblock = ResBlock(d, dropout)

    def forward(self, x_s: torch.Tensor) -> torch.Tensor:
        x_attn = self.se_block(x_s)           # (batch, 9)
        return self.resblock(self.proj(x_attn))


# ── MHA Fusion ──────────────────────────────────────────────────────────────

class MHAFusion(nn.Module):
    """
    Multi-Head Self-Attention over 3 branch tokens.
    tokens: (batch, 3, d_branch) → H: (batch, 3, d_branch) → flatten: (batch, 3*d_branch)
    """
    def __init__(self, d: int, n_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(
            embed_dim=d,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(d)

    def forward(self, z_k: torch.Tensor,
                z_t: torch.Tensor,
                z_s: torch.Tensor) -> torch.Tensor:
        # (batch, 3, d)
        tokens = torch.stack([z_k, z_t, z_s], dim=1)
        # Self-attention with residual
        H, _ = self.attn(tokens, tokens, tokens)
        H = self.norm(H + tokens)          # residual + LayerNorm
        return H.flatten(1)                # (batch, 3*d)


# ── Main Model ──────────────────────────────────────────────────────────────

class STMBAN(nn.Module):
    """
    ST-MBAN: Spatio-Temporal Multi-Branch Attention Network

    Args:
        input_dim  : 총 입력 피처 수 (= K_DIM + T_DIM_RAW + S_DIM = 30)
        d_branch   : 각 branch 인코더 출력 차원 (default 64)
        n_heads    : MHA head 수 (default 4)
        dropout    : dropout 비율 (default 0.1)
        T_sig      : CTE 신호 위상 주기 (default 90.0초)
        T_phase    : CTE 위상 잔여 시간 주기 (default 30.0초)
    """
    def __init__(
        self,
        input_dim: int,
        d_branch: int   = 64,
        n_heads: int    = 4,
        dropout: float  = 0.1,
        T_sig: float    = 90.0,
        T_phase: float  = 30.0,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.d_branch  = d_branch

        # Branch encoders
        self.k_enc = KBranchEncoder(d_branch, dropout)
        self.t_enc = TBranchEncoder(d_branch, dropout, T_sig, T_phase)
        self.s_enc = SBranchEncoder(d_branch, dropout)

        # MHA Fusion
        self.fusion = MHAFusion(d_branch, n_heads, dropout)

        # Decoder
        self.proj     = nn.Linear(3 * d_branch, d_branch)
        self.proj_norm = nn.LayerNorm(d_branch)
        self.dec_res1 = ResBlock(d_branch, dropout)
        self.dec_res2 = ResBlock(d_branch, dropout)
        self.output_head = nn.Linear(d_branch, 2)

    def _split_input(self, x: torch.Tensor):
        """입력 텐서를 K, T, S 세 branch로 분할."""
        x_k = x[:, :K_DIM]                             # (batch, 13)
        x_t = x[:, K_DIM: K_DIM + T_DIM_RAW]          # (batch, 6)
        x_s = x[:, K_DIM + T_DIM_RAW:]                 # (batch, 11)
        return x_k, x_t, x_s

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, input_dim)
        Returns:
            y_hat: (batch, 2)  [dwell_cur, dwell_nxt]
        """
        x_k, x_t, x_s = self._split_input(x)

        # Branch encoding
        z_k = self.k_enc(x_k)   # (batch, d_branch)
        z_t = self.t_enc(x_t)   # (batch, d_branch)
        z_s = self.s_enc(x_s)   # (batch, d_branch)

        # MHA Fusion
        h_flat = self.fusion(z_k, z_t, z_s)  # (batch, 3*d_branch)

        # Projection + Decoder
        h = self.proj_norm(self.proj(h_flat))  # (batch, d_branch)
        h = self.dec_res1(h)
        h = self.dec_res2(h)
        y_hat = self.output_head(h)            # (batch, 2)
        return y_hat

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """eval 모드 결정론적 추론."""
        self.eval()
        with torch.no_grad():
            return self.forward(x)
