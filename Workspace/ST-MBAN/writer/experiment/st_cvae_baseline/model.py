"""
ST-CVAE Baseline Model (PyTorch)
Structure: Posterior Encoder + Prior + Decoder + KL Divergence
Reference: ST-CVAE 구조.md
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


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
        self.norm1 = nn.LayerNorm(d)
        self.linear1 = nn.Linear(d, d * 2)
        self.reglu1 = ReGLU()
        self.dropout = nn.Dropout(dropout)
        self.norm2 = nn.LayerNorm(d)
        self.linear2 = nn.Linear(d, d * 2)
        self.reglu2 = ReGLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.reglu1(self.linear1(self.norm1(x)))
        out = self.dropout(out)
        out = self.reglu2(self.linear2(self.norm2(out)))
        return out + residual


class STCVAEEncoder(nn.Module):
    """
    Shared encoder structure for both Posterior and Prior.
    Posterior: input = [X, Y] (input_dim + target_dim)
    Prior:     input = [X]    (input_dim)
    Output: mu, log_var (log of variance, each of size latent_dim)
    Convention: log_var = log(sigma^2), so sigma = exp(0.5 * log_var)
    """
    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.res1 = ResBlock(hidden_dim)
        self.res2 = ResBlock(hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.mu_head = nn.Linear(hidden_dim, latent_dim)
        self.log_var_head = nn.Linear(hidden_dim, latent_dim)

    def forward(self, x: torch.Tensor):
        h = self.input_proj(x)
        h = self.res2(self.res1(h))
        h = self.norm(h)
        mu = self.mu_head(h)
        log_var = self.log_var_head(h).clamp(-10, 10)  # log variance
        return mu, log_var


class STCVAEDecoder(nn.Module):
    """
    Decoder: [X, Z] → Linear → ResBlock×3 → Linear → output
    """
    def __init__(self, input_dim: int, latent_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.input_proj = nn.Linear(input_dim + latent_dim, hidden_dim)
        self.res1 = ResBlock(hidden_dim)
        self.res2 = ResBlock(hidden_dim)
        self.res3 = ResBlock(hidden_dim)
        self.output_head = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(torch.cat([x, z], dim=-1))
        h = self.res3(self.res2(self.res1(h)))
        return self.output_head(h)


class STCVAE(nn.Module):
    """
    ST-CVAE: Spatio-Temporal Conditional Variational AutoEncoder
    - Training: Posterior encoder ([X,Y] → Z*) + Decoder ([X,Z*] → Y_hat)
    - Inference: Prior encoder ([X] → Z_mu) + Decoder ([X,Z_mu] → Y_hat)
    """
    def __init__(
        self,
        input_dim: int,
        target_dim: int = 2,
        hidden_dim: int = 128,
        latent_dim: int = 32,
    ):
        super().__init__()
        self.latent_dim = latent_dim
        # Posterior: [X, Y] → mu_psi, log_var_psi
        self.posterior = STCVAEEncoder(input_dim + target_dim, hidden_dim, latent_dim)
        # Prior: [X] → mu_phi, log_var_phi
        self.prior = STCVAEEncoder(input_dim, hidden_dim, latent_dim)
        # Decoder: [X, Z] → Y_hat
        self.decoder = STCVAEDecoder(input_dim, latent_dim, hidden_dim, target_dim)

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Z = mu + eps * exp(0.5 * log_var)"""
        if self.training:
            std = torch.exp(0.5 * log_var)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(self, x: torch.Tensor, y: torch.Tensor = None):
        """
        Training (y given): use posterior Z*
        Inference (y=None): use prior Z_mu (deterministic)
        """
        if y is not None:
            mu_psi, log_var_psi = self.posterior(torch.cat([x, y], dim=-1))
            z = self.reparameterize(mu_psi, log_var_psi)
        else:
            mu_phi, _ = self.prior(x)
            z = mu_phi
        return self.decoder(x, z)

    def compute_loss(self, x: torch.Tensor, y: torch.Tensor, beta: float = 1.0):
        """
        Total loss = Huber(y_pred, y) + beta * KL(posterior || prior)
        KL(N(mu_psi, var_psi) || N(mu_phi, var_phi))
          = 0.5 * sum( log_var_phi - log_var_psi - 1
                       + exp(log_var_psi - log_var_phi)
                       + (mu_psi - mu_phi)^2 * exp(-log_var_phi) )
        """
        # Posterior
        mu_psi, log_var_psi = self.posterior(torch.cat([x, y], dim=-1))
        z_star = self.reparameterize(mu_psi, log_var_psi)
        y_hat = self.decoder(x, z_star)

        # Prior
        mu_phi, log_var_phi = self.prior(x)

        # Reconstruction loss (Huber)
        recon_loss = F.huber_loss(y_hat, y, delta=1.0)

        # KL divergence (log_var convention)
        kl = 0.5 * (
            log_var_phi - log_var_psi
            - 1.0
            + torch.exp(log_var_psi - log_var_phi)
            + (mu_psi - mu_phi).pow(2) * torch.exp(-log_var_phi)
        ).sum(dim=-1).mean()

        total_loss = recon_loss + beta * kl
        return total_loss, recon_loss, kl

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """Deterministic inference using prior mean."""
        self.eval()
        with torch.no_grad():
            return self.forward(x, y=None)
