"""
channel_model.py
================
Physical-layer channel model for C-V2X vehicular networks.

Models implemented:
  - 3GPP TR 36.885 path loss (V2V LOS/NLOS, V2I Urban)
  - Rician fading (V2V links)
  - Nakagami-m fading (V2I links)
  - SINR calculation
  - Transmission success probability
  - C-V2X Mode 4 collision probability
  - Channel Busy Ratio (CBR)

All distances in metres, frequencies in GHz, power in dBm.
"""

import math
import random
import numpy as np
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Physical Constants & Default Parameters
# ─────────────────────────────────────────────────────────────────────────────
FC_GHZ            = 5.9          # Carrier frequency (GHz)
BW_MHZ            = 10.0         # Total bandwidth (MHz)
NUM_SUBCHANNELS   = 50           # Number of sub-channels
SUBCHANNEL_BW_KHZ = 180.0        # Sub-channel bandwidth (kHz)
MAX_TX_POWER_DBM  = 23.0         # Max transmit power (dBm)
NOISE_FIGURE_DB   = 9.0          # Receiver noise figure (dB)
THERMAL_NOISE_DBM_HZ = -174.0    # Thermal noise density (dBm/Hz)
SINR_THRESH_DB    = 3.0          # SINR threshold for success (dB)
CBR_THRESH        = 0.65         # Channel busy ratio threshold

# Derived noise power per sub-channel
_NOISE_POWER_DBM = (
    THERMAL_NOISE_DBM_HZ
    + 10 * math.log10(SUBCHANNEL_BW_KHZ * 1e3)
    + NOISE_FIGURE_DB
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: dB ↔ linear
# ─────────────────────────────────────────────────────────────────────────────
def db2lin(x_db: float) -> float:
    return 10.0 ** (x_db / 10.0)


def lin2db(x: float) -> float:
    if x <= 0:
        return -200.0
    return 10.0 * math.log10(x)


# ─────────────────────────────────────────────────────────────────────────────
# 3GPP TR 36.885 Path Loss Models
# ─────────────────────────────────────────────────────────────────────────────
def path_loss_v2v_los(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    """V2V LOS path loss (dB). d_m >= 3 m."""
    d = max(d_m, 3.0)
    return 38.77 + 16.7 * math.log10(d) + 18.2 * math.log10(fc_ghz)


def path_loss_v2v_nlos(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    """V2V NLOS path loss (dB). d_m >= 3 m."""
    d = max(d_m, 3.0)
    return 36.85 + 30.0 * math.log10(d) + 18.9 * math.log10(fc_ghz)


def path_loss_v2i(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    """V2I Urban Macro path loss (dB). d_m >= 10 m."""
    d = max(d_m, 10.0)
    return 32.4 + 20.0 * math.log10(d) + 20.0 * math.log10(fc_ghz)


# ─────────────────────────────────────────────────────────────────────────────
# Rician Fading (V2V)
# ─────────────────────────────────────────────────────────────────────────────
def rician_fading_gain_db(K_db: float, rng: Optional[random.Random] = None) -> float:
    """
    Sample instantaneous Rician fading gain (dB).
    K_db: Rician K-factor in dB.
    Returns gain in dB (mean ≈ 0 dB when K→0, improves as K increases).
    """
    if rng is None:
        rng = random

    K = db2lin(K_db)
    # Rician: envelope R with E[R²]=1, K-factor = s²/(2σ²)
    # Generate using Rice distribution
    # sigma² = 1/(2*(K+1)), s² = K/(K+1)
    sigma = math.sqrt(1.0 / (2.0 * (K + 1)))
    s     = math.sqrt(K / (K + 1))

    # Two independent Gaussian components
    xi   = rng.gauss(s, sigma)
    eta  = rng.gauss(0.0, sigma)
    R    = math.sqrt(xi**2 + eta**2)  # Rician envelope

    # Power gain (R²), return in dB
    power_lin = R * R
    return lin2db(power_lin)


def rician_fading_gain_db_array(K_db: float, n: int, seed: int = 42) -> np.ndarray:
    """Vectorised Rician fading gain (dB) using numpy."""
    K     = db2lin(K_db)
    sigma = math.sqrt(1.0 / (2.0 * (K + 1)))
    s     = math.sqrt(K / (K + 1))
    rng   = np.random.default_rng(seed)

    xi  = rng.normal(s,   sigma, n)
    eta = rng.normal(0.0, sigma, n)
    R2  = xi**2 + eta**2
    # Avoid log(0)
    R2  = np.maximum(R2, 1e-12)
    return 10.0 * np.log10(R2)


# ─────────────────────────────────────────────────────────────────────────────
# Nakagami-m Fading (V2I)
# ─────────────────────────────────────────────────────────────────────────────
def nakagami_fading_gain_db(m: float, rng: Optional[random.Random] = None) -> float:
    """
    Sample Nakagami-m fading gain (dB).
    m: shape parameter (m=1 → Rayleigh, m→∞ → AWGN).
    Envelope Omega = 1 (unit mean square).
    """
    if rng is None:
        rng = random

    # Nakagami-m envelope: R ~ sqrt(Gamma(m, Omega/m))
    # Power W = R² ~ Gamma(m, Omega/m) with Omega=1
    # Use numpy for Gamma sampling
    shape = m
    scale = 1.0 / m  # Omega/m = 1/m
    W = 0.0
    for _ in range(int(round(m * 2))):
        # Approximate: sum of exponentials
        W += -scale * math.log(max(rng.random(), 1e-15))
    W /= 2.0  # rough approximation for integer m
    # More accurate: use 2*m chi-squared draws
    W = max(W, 1e-12)
    return lin2db(W)


def nakagami_fading_gain_db_accurate(m: float, seed: int = 42) -> float:
    """
    Accurate Nakagami-m sample using numpy Gamma distribution.
    """
    rng = np.random.default_rng(seed)
    # Power W ~ Gamma(m, 1/m)
    W = rng.gamma(shape=m, scale=1.0/m)
    W = max(W, 1e-12)
    return lin2db(W)


# ─────────────────────────────────────────────────────────────────────────────
# SINR Calculation
# ─────────────────────────────────────────────────────────────────────────────
class ChannelModel:
    """
    Per-link SINR calculator with path loss + fading.
    """

    def __init__(
        self,
        fc_ghz: float = FC_GHZ,
        K_db: float = 7.0,       # Rician K-factor (V2V)
        nakagami_m: float = 3.0, # Nakagami-m param (V2I)
        sinr_thresh_db: float = SINR_THRESH_DB,
        max_tx_power_dbm: float = MAX_TX_POWER_DBM,
        num_subchannels: int = NUM_SUBCHANNELS,
        seed: int = 42,
    ):
        self.fc_ghz         = fc_ghz
        self.K_db           = K_db
        self.nakagami_m     = nakagami_m
        self.sinr_thresh_db = sinr_thresh_db
        self.sinr_thresh    = db2lin(sinr_thresh_db)
        self.max_tx_dbm     = max_tx_power_dbm
        self.num_subch      = num_subchannels
        self.noise_dbm      = _NOISE_POWER_DBM

        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

        # CBR tracking: fraction of busy subchannels
        self._subchannel_busy = [False] * num_subchannels
        self._cbr_window: list = []  # recent (tx_success, subchannel_idx)

    # ── Path Loss ─────────────────────────────────────────────────────────────
    def compute_path_loss(self, d_m: float, link_type: str = "v2v",
                          los: bool = True) -> float:
        """Return path loss in dB."""
        if link_type == "v2v":
            return path_loss_v2v_los(d_m, self.fc_ghz) if los                    else path_loss_v2v_nlos(d_m, self.fc_ghz)
        else:  # v2i
            return path_loss_v2i(d_m, self.fc_ghz)

    # ── Fading ────────────────────────────────────────────────────────────────
    def sample_fading(self, link_type: str = "v2v") -> float:
        """Return a fading gain sample (dB)."""
        if link_type == "v2v":
            return rician_fading_gain_db(self.K_db, self._rng)
        else:
            return nakagami_fading_gain_db(self.nakagami_m, self._rng)

    # ── Received Power ────────────────────────────────────────────────────────
    def received_power_dbm(self, tx_power_dbm: float, d_m: float,
                           link_type: str = "v2v", los: bool = True) -> float:
        """Received signal power in dBm."""
        pl   = self.compute_path_loss(d_m, link_type, los)
        fade = self.sample_fading(link_type)
        return tx_power_dbm - pl + fade

    # ── SINR ──────────────────────────────────────────────────────────────────
    def compute_sinr(
        self,
        tx_power_dbm: float,
        d_m: float,
        interference_dbm_list: list,
        link_type: str = "v2v",
        los: bool = True,
    ) -> float:
        """
        Compute post-fading SINR.
        interference_dbm_list: list of received interference power (dBm).
        Returns SINR in linear scale.
        """
        rx_dbm = self.received_power_dbm(tx_power_dbm, d_m, link_type, los)
        rx_lin = db2lin(rx_dbm - 30)  # convert dBm → Watts

        # Noise
        noise_lin = db2lin(self.noise_dbm - 30)

        # Aggregate interference
        intf_lin = sum(db2lin(p - 30) for p in interference_dbm_list)

        sinr = rx_lin / (noise_lin + intf_lin + 1e-20)
        return sinr

    def sinr_db(self, tx_power_dbm: float, d_m: float,
                interference_dbm_list: list = None,
                link_type: str = "v2v", los: bool = True) -> float:
        if interference_dbm_list is None:
            interference_dbm_list = []
        return lin2db(self.compute_sinr(
            tx_power_dbm, d_m, interference_dbm_list, link_type, los))

    # ── Transmission Success ──────────────────────────────────────────────────
    def tx_success(self, tx_power_dbm: float, d_m: float,
                   interference_dbm_list: list = None,
                   link_type: str = "v2v", los: bool = True) -> bool:
        """Returns True if transmission succeeds (SINR >= threshold)."""
        if interference_dbm_list is None:
            interference_dbm_list = []
        sinr = self.compute_sinr(tx_power_dbm, d_m, interference_dbm_list,
                                 link_type, los)
        return sinr >= self.sinr_thresh

    def tx_success_prob_analytical(self, tx_power_dbm: float, d_m: float,
                                   link_type: str = "v2v",
                                   los: bool = True,
                                   num_samples: int = 200) -> float:
        """
        Estimate transmission success probability via Monte-Carlo.
        For analytical use; returns a float in [0,1].
        """
        successes = 0
        for _ in range(num_samples):
            if self.tx_success(tx_power_dbm, d_m, [], link_type, los):
                successes += 1
        return successes / num_samples

    # ── C-V2X Mode 4 Collision Probability ───────────────────────────────────
    def collision_probability_cv2x(
        self,
        num_vehicles: int,
        num_subchannels: int = None,
        selection_window: int = 100,
    ) -> float:
        """
        Approximate C-V2X Mode 4 SPS collision probability.
        Based on: Molina-Masegosa & Gozalvez (2017), WCNC.
        P_col ≈ 1 - (1 - 1/C)^(N-1) where C = available resource candidates
        """
        if num_subchannels is None:
            num_subchannels = self.num_subch
        # Candidates within selection window
        C = max(1, selection_window // 2 * num_subchannels)  # simplified
        N = max(1, num_vehicles)
        p_col = 1.0 - (1.0 - 1.0 / C) ** (N - 1)
        return min(p_col, 1.0)

    # ── CBR ───────────────────────────────────────────────────────────────────
    def compute_cbr(self, active_tx_count: int,
                    num_subchannels: int = None) -> float:
        """
        Channel Busy Ratio approximation.
        CBR = fraction of subchannels occupied.
        """
        if num_subchannels is None:
            num_subchannels = self.num_subch
        return min(1.0, active_tx_count / max(1, num_subchannels))

    # ── Throughput ────────────────────────────────────────────────────────────
    def shannon_capacity_mbps(self, sinr_linear: float,
                              bw_mhz: float = SUBCHANNEL_BW_KHZ / 1000) -> float:
        """Shannon capacity in Mbps for a single sub-channel."""
        return bw_mhz * math.log2(1.0 + max(sinr_linear, 0.0))

    # ── V2V Range Check ───────────────────────────────────────────────────────
    def in_v2v_range(self, d_m: float, comm_range_m: float = 300.0) -> bool:
        return d_m <= comm_range_m

    def in_v2i_range(self, d_m: float, comm_range_m: float = 500.0) -> bool:
        return d_m <= comm_range_m
