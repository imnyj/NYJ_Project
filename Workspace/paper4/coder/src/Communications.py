# Communications.py
# ============================================================================
# Link-layer communication model for the CIoV precaching simulator.
#
#   - Air interface (V2V / V2I) : IEEE 802.11ac/ax Wi-Fi   <-- replaces WAVE
#   - Backhaul (RSU <-> RSU, RSU <-> content server) : optical fiber
#
# NetSim.Node.send_packet() selects the medium by endpoint type and calls the
# helpers below. Public contract expected by NetSim:
#     wifi_channel_manager.allocate() -> (channel_index, rate_mbps)
#     wifi_channel_manager.release(channel_index)
#     wifi_data_rate(rate_mbps)           -> bits per second
#     wifi_transmission_delay(bytes, bps) -> seconds
#     wifi_propagation_delay(distance_m)  -> seconds
#     fiber_data_rate(), fiber_propagation_delay(distance_m)   (unchanged)
# ============================================================================

import math
from typing import Tuple, Optional

# --------------------------------------------------------------------------
# Physical constants
# --------------------------------------------------------------------------
C_LIGHT = 3e8                                              # speed of light (m/s)
REFRACTIVE_INDEX_FIBER = 1.4682                            # single-mode fiber
FIBER_PROPAGATION_SPEED = C_LIGHT / REFRACTIVE_INDEX_FIBER # ~2.044e8 m/s

# --------------------------------------------------------------------------
# Framing / streaming thresholds (unchanged so NetSim fragmentation and
# streaming behaviour is preserved)
# --------------------------------------------------------------------------
MAX_FRAME_SIZE   = 8192               # bytes per frame; larger -> fragmented
FRAG_LIMIT       = 5000              # > this many fragments -> stream instead
STREAM_THRESHOLD = 1 * 1024 * 1024   # >= 1 MiB payload -> stream instead

# ============================================================================
# Wi-Fi channel manager (IEEE 802.11ac/ax abstraction)
#
# Models the shared, contention-based air interface. Several non-overlapping
# channels are available; each carries a limited number of concurrent
# transmissions before the per-user rate is downshifted (MCS drop + airtime
# sharing under CSMA/CA). allocate() assigns a new transmission to the
# least-loaded channel and returns the per-user rate; release() frees it.
#
# Rate ladder approximates 802.11ac VHT80, 1 spatial stream: 1 user ~ MCS9
# (433 Mbps), degrading as contenders are added; beyond the ladder the rate
# halves per extra user down to a basic-rate floor. The numbers are a
# deliberate simulation abstraction and are straightforward to retune.
# ============================================================================
class WiFiChannelManager:
    def __init__(self, num_channels: int = 3) -> None:
        self.num_channels = num_channels
        self.channels: list[list[object]] = [[] for _ in range(num_channels)]
        # per-user rate (Mbps) indexed by concurrent user count (802.11ac VHT80, 1SS)
        self.speeds = [433.3, 292.5, 195.0, 97.5]
        self.min_rate = 6.0            # basic-rate floor (Mbps)
        self.capacity = 2000.0         # aggregate cap per channel (non-binding safety cap; MCS ladder governs)

    def _rate_per_user(self, users: int) -> float:
        if users <= 0:
            return 0.0
        if users <= len(self.speeds):
            return self.speeds[users - 1]
        extra = users - len(self.speeds)
        extra = min(extra, 30)         # clamp to avoid 2**extra overflow
        return max(self.speeds[-1] / (2.0 ** float(extra)), self.min_rate)

    def _sum_rate_if_add_one(self, users_now: int) -> tuple[float, float]:
        current_rate = self._rate_per_user(users_now)
        sum_now = users_now * current_rate
        add_rate = self._rate_per_user(users_now + 1)
        return sum_now, add_rate

    def allocate(self) -> tuple[int, float]:
        candidates = []
        for i in range(self.num_channels):
            u = len(self.channels[i])
            sum_now, add_rate = self._sum_rate_if_add_one(u)
            candidates.append((i, sum_now, add_rate))
        candidates.sort(key=lambda x: x[1])
        for i, sum_now, add_rate in candidates:
            if sum_now + add_rate <= self.capacity + 1e-9:
                self.channels[i].append(object())
                return i, add_rate
        i_min = min(range(self.num_channels), key=lambda k: len(self.channels[k]))
        self.channels[i_min].append(object())
        leftover = max(self.capacity - self._sum_rate_if_add_one(len(self.channels[i_min]) - 1)[0], 0.0)
        rate = max(self.min_rate, min(leftover, self.speeds[0]))
        return i_min, rate

    def release(self, ch_idx: int) -> None:
        if 0 <= ch_idx < self.num_channels and self.channels[ch_idx]:
            self.channels[ch_idx].pop()


wifi_channel_manager: WiFiChannelManager = WiFiChannelManager()

# --------------------------------------------------------------------------
# Delay models
# --------------------------------------------------------------------------
def fiber_propagation_delay(distance_m: float, propagation_speed: float = FIBER_PROPAGATION_SPEED) -> float:
    return distance_m / propagation_speed

def wifi_propagation_delay(distance_m: float, propagation_speed: float = C_LIGHT) -> float:
    return distance_m / propagation_speed

def wifi_transmission_delay(frame_size_bytes: float, data_rate_bps: float) -> float:
    return (frame_size_bytes * 8) / data_rate_bps

# --------------------------------------------------------------------------
# Data-rate models
# --------------------------------------------------------------------------
def fiber_data_rate(rate_gbps: float = 10.0) -> float:
    return rate_gbps * 1e9

def wifi_data_rate(rate_mbps: float = 200.0) -> float:
    return rate_mbps * 1e6

# --------------------------------------------------------------------------
# Throughput-per-step helpers (generic)
# --------------------------------------------------------------------------
def data_per_step(data_rate_bps: float, step_duration_sec: float = 1.0) -> float:
    return (data_rate_bps * step_duration_sec) / 8

def adjusted_bytes_per_step(distance_m: float, data_rate_bps: float,
                            step_duration_sec: float = 1.0, propagation_speed: float = C_LIGHT) -> float:
    avail_time = step_duration_sec - (distance_m / propagation_speed)
    if avail_time <= 0:
        return 0.0
    return (data_rate_bps * avail_time) / 8

def fiber_fetch_bytes_per_step(distance_m: float, step_duration_sec: float = 1.0,
                               rate_gbps: float = 10.0, hop_count: int = 1,
                               propagation_speed: float = FIBER_PROPAGATION_SPEED) -> float:
    data_rate = fiber_data_rate(rate_gbps)
    avail_time = step_duration_sec - hop_count * (distance_m / propagation_speed)
    if avail_time <= 0:
        return 0.0
    return (data_rate * avail_time) / 8

def relay_bytes_per_step(distance_wifi_m: float, distance_fiber_m: float,
                         step_duration_sec: float = 1.0, wifi_rate_mbps: float = 200.0,
                         fiber_rate_gbps: float = 10.0, prop_speed_wifi: float = C_LIGHT,
                         prop_speed_fiber: float = FIBER_PROPAGATION_SPEED) -> float:
    r_wifi = wifi_data_rate(wifi_rate_mbps)
    r_fiber = fiber_data_rate(fiber_rate_gbps)
    eff_rate = (r_wifi * r_fiber) / (r_wifi + r_fiber)
    avail_time = step_duration_sec - ((distance_wifi_m / prop_speed_wifi) + (distance_fiber_m / prop_speed_fiber))
    if avail_time <= 0:
        return 0.0
    return (eff_rate * avail_time) / 8


# ============================================================================
# Uplink SINR model (S2) -- probabilistic, interference-aware
#
# Vehicles transmit small state packets to the RSU on one of NUM_SUBCHANNELS.
# Transmissions overlapping on the SAME subchannel interfere. Success is judged
# probabilistically under independent Rayleigh fading on desired and interfering
# links (standard closed form):
#     P_succ = exp(-th*N0/S) * PROD_k 1/(1 + th*I_k/S)
# Higher tx power raises one's own S (up) but also raises interference to others
# (down) -> a natural power/congestion trade-off. More co-channel contenders
# lower every success probability -> the congestion mechanism.
# ============================================================================
FREQ_HZ             = 5.9e9          # ITS band
PL_EXP              = 2.3            # path-loss exponent (semi-open road)
_PL_REF_DB          = 20.0 * math.log10(4.0 * math.pi * FREQ_HZ / C_LIGHT)  # PL at 1 m
NOISE_FIGURE_DB     = 9.0
TOTAL_BW_HZ         = 20e6
NUM_SUBCHANNELS     = 4
SINR_TH_DB          = 0.0           # decoding threshold gamma_th
TX_POWER_LEVELS_DBM = [20.0, 25.0, 30.0]


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 10.0)

def dbm_to_mw(dbm: float) -> float:
    return 10.0 ** (dbm / 10.0)

def path_loss_db(distance_m: float) -> float:
    return _PL_REF_DB + 10.0 * PL_EXP * math.log10(max(distance_m, 1.0))

def rx_power_mw(tx_dbm: float, distance_m: float) -> float:
    return dbm_to_mw(tx_dbm - path_loss_db(distance_m))

def noise_floor_mw(num_subchannels: int = NUM_SUBCHANNELS) -> float:
    bw = TOTAL_BW_HZ / max(num_subchannels, 1)
    return dbm_to_mw(-174.0 + 10.0 * math.log10(bw) + NOISE_FIGURE_DB)

def rayleigh_success_prob(signal_mw: float, interferer_mws, noise_mw: float,
                          sinr_th_lin: float) -> float:
    """P(SINR >= th) under independent Rayleigh fading on all links."""
    if signal_mw <= 0.0:
        return 0.0
    p = math.exp(-sinr_th_lin * noise_mw / signal_mw)
    for I in interferer_mws:
        p *= 1.0 / (1.0 + sinr_th_lin * (I / signal_mw))
    return p

def judge_uplink(group, num_subchannels: int = NUM_SUBCHANNELS) -> dict:
    """group: list of (id, tx_dbm, distance_m), ALL on the same subchannel.
    Returns {id: success_probability} with mutual Rayleigh-SINR interference."""
    n0 = noise_floor_mw(num_subchannels)
    th = _db_to_lin(SINR_TH_DB)
    powers = {gid: rx_power_mw(tx, d) for (gid, tx, d) in group}
    out = {}
    for gid, tx, d in group:
        S = powers[gid]
        interf = [powers[o] for (o, _, _) in group if o != gid]
        out[gid] = rayleigh_success_prob(S, interf, n0, th)
    return out
