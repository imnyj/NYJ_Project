# Communications.py
# ============================================================================
# IEEE 802.11p physical layer for the V2I uplink (5.9 GHz ITS band).
#
# Answers one question for the scheduler: given a vehicle's transmit power and
# its distance from the RSU, and given who else was granted the same subchannel,
# does this update get through?
#
#   link budget   Ptx + G_tx + G_rx - PL(d) - shadowing
#   contention    co-channel frames overlap only within a vulnerable period,
#                 2 * T_air / T_step, drawn from a seeded stream
#   decoding      Rayleigh-faded SINR against the operating MCS threshold
#   occupancy     frame airtime, which is what makes CBR a measured quantity
#
# Every constant is derived from the standard rather than tuned: the noise floor
# from kTB + NF, the SINR threshold from the MCS table, the airtime from the OFDM
# symbol count. Change OPERATING_RATE_MBPS and threshold, sensitivity and airtime
# all follow.
# ============================================================================

import math
import random
from dataclasses import dataclass
from typing import Dict

# --------------------------------------------------------------------------
# Physical constants
# --------------------------------------------------------------------------
C_LIGHT = 3e8                                              # speed of light (m/s)

# REFRACTIVE_INDEX_FIBER / FIBER_PROPAGATION_SPEED (fibre backhaul) and
# MAX_FRAME_SIZE / FRAG_LIMIT / STREAM_THRESHOLD (NetSim fragmentation) were
# removed 2026-08-31: src/NetSim.py has been retired and a grep over src/,
# tests/ and run_all.py found zero external references. C_LIGHT stays because
# `_PL_REF_DB` is computed from it.

# ============================================================================
# Legacy 802.11ac/fibre backhaul layer -- REMOVED 2026-08-30.
#
# Everything between here and the V2I uplink model below served NetSim.py's
# content-precaching simulator: a WiFiChannelManager that split a shared rate
# among contending users, fibre propagation helpers, and byte-per-step
# accounting. NetSim.py was retired with src/aoi_env.py (design_spec_v2 D1),
# and a grep confirmed all ten symbols had zero callers outside this file.
#
# They are preserved in coder/backup/unused_20260830_180000/Communications_legacy.py.
# Do not revive them alongside the model below: that one charges airtime per
# 802.11p frame, while these split an aggregate rate among users, and the two
# would double-count channel occupancy.
# ============================================================================

# ============================================================================
# Uplink PHY model (S2) -- IEEE 802.11p (10 MHz OFDM) at 5.9 GHz,
# interference-aware and probabilistic.
#
# Vehicles transmit small status packets to the RSU on one of NUM_SUBCHANNELS.
# Transmissions overlapping on the SAME subchannel interfere. Success is judged
# under independent Rayleigh fading on the desired and every interfering link
# (standard closed form):
#     P_succ = exp(-th*N0/S) * PROD_k 1/(1 + th*I_k/S)
# Higher tx power raises one's own S (up) but also raises interference to others
# (down) -> a natural power/congestion trade-off. More co-channel contenders
# lower every success probability -> the congestion mechanism.
#
# Link budget (all dB):
#     Prx(d) = Ptx + G_tx + G_rx - PL(d) - X_shadow
# with PL(d) = PL(1 m) + 10*n*log10(d), free-space reference at 1 m, n = 2.3.
# The antenna gains are what make the budget a real one: a vehicle roof whip is
# ~3 dBi and an RSU mast antenna ~9 dBi, so a link that looks 12 dB short
# without them closes with them.
# ============================================================================
FREQ_HZ             = 5.9e9          # ITS band (US/EU 5.9 GHz DSRC/ITS-G5)
PL_EXP              = 2.3            # path-loss exponent (semi-open urban road)
_PL_REF_DB          = 20.0 * math.log10(4.0 * math.pi * FREQ_HZ / C_LIGHT)  # PL at 1 m
NOISE_FIGURE_DB     = 9.0            # RSU receiver noise figure

# 802.11p uses 10 MHz channels (half-clocked 802.11a). Four of them span
# 40 MHz, which fits inside the US 5.9 GHz ITS allocation (5.850-5.925 GHz).
NUM_SUBCHANNELS     = 4
SUBCHANNEL_BW_HZ    = 10e6
TOTAL_BW_HZ         = SUBCHANNEL_BW_HZ * NUM_SUBCHANNELS   # 40 MHz aggregate

# Antenna gains. Omitting these was the main physical omission of the previous
# model: it charged the full path loss to the transmit power alone.
G_TX_DBI            = 3.0            # vehicle roof-mounted omni whip
G_RX_DBI            = 9.0            # RSU mast-mounted omni with downtilt

# Log-normal shadowing standard deviation (dB). 4 dB is the usual figure for an
# urban/semi-open road link with partial obstruction; set to 0.0 to recover the
# pure path-loss + Rayleigh behaviour of the previous model.
SHADOWING_SIGMA_DB  = 4.0

# TX_POWER_LEVELS_DBM = [20, 25, 30] was removed 2026-08-31. It existed for
# src/aoi_env.py's discrete power ladder; that file is gone, it had no remaining
# referent, and it stated a POWER RANGE THAT NO LONGER EXISTS -- the action space
# is continuous [P_MIN, P_MAX] = [10, 23] dBm and is owned by
# src/rl_interface.py::ActionDecoder. A reader who trusted it would have
# mis-stated the paper's action space by 7 dB.

# --------------------------------------------------------------------------
# OFDM framing (IEEE 802.11p, 10 MHz channel = half-clocked 802.11a)
# --------------------------------------------------------------------------
OFDM_SYMBOL_TIME_S   = 8e-6     # 6.4 us useful + 1.6 us guard interval
PREAMBLE_SIGNAL_TIME_S = 40e-6  # 32 us PLCP preamble + one 8 us SIGNAL symbol
SERVICE_BITS         = 16       # PLCP SERVICE field, prepended to the PSDU
TAIL_BITS            = 6        # convolutional-code tail, appended to the PSDU

#: Default status-update payload. An ETSI CAM carrying position, speed, heading
#: and the basic vehicle container lands around 300 B on the wire.
STATUS_UPDATE_BYTES  = 300


@dataclass(frozen=True)
class Mcs:
    """One IEEE 802.11p modulation-and-coding scheme on a 10 MHz channel.

    `bits_per_symbol` is N_DBPS, the number of *data* bits an OFDM symbol
    carries: 48 data subcarriers x bits/subcarrier x code rate. It satisfies
    rate = bits_per_symbol / OFDM_SYMBOL_TIME_S by construction, which is what
    makes the airtime model and the rate label consistent with each other.

    `req_sinr_db` is the SINR the receiver needs to decode this MCS. The ladder
    is the standard 5/8/10/13/16/19/22/25 dB progression for OFDM MCS 0-7; the
    per-rate receiver sensitivity follows from it as noise floor + req_sinr_db
    (see `sensitivity_dbm`), e.g. QPSK 1/2 -> -95 + 10 = -85 dBm.
    """
    rate_mbps: float
    modulation: str
    code_rate: str
    bits_per_symbol: int
    req_sinr_db: float


#: The eight mandatory/optional rates of a 10 MHz 802.11p channel.
MCS_TABLE: dict[float, Mcs] = {
    3.0:  Mcs(3.0,  "BPSK",   "1/2",  24,  5.0),
    4.5:  Mcs(4.5,  "BPSK",   "3/4",  36,  8.0),
    6.0:  Mcs(6.0,  "QPSK",   "1/2",  48, 10.0),
    9.0:  Mcs(9.0,  "QPSK",   "3/4",  72, 13.0),
    12.0: Mcs(12.0, "16-QAM", "1/2",  96, 16.0),
    18.0: Mcs(18.0, "16-QAM", "3/4", 144, 19.0),
    24.0: Mcs(24.0, "64-QAM", "2/3", 192, 22.0),
    27.0: Mcs(27.0, "64-QAM", "3/4", 216, 25.0),
}

#: Operating rate of the V2I uplink. 6 Mbps (QPSK 1/2) is the 802.11p base rate
#: used by ETSI ITS-G5 for CAM/DENM: it is the most robust rate that still
#: clears a 300 B update inside half a millisecond. Change this one constant to
#: retune the whole link -- threshold, airtime and sensitivity all follow.
OPERATING_RATE_MBPS = 6.0


def get_mcs(rate_mbps: float = OPERATING_RATE_MBPS) -> Mcs:
    """Look up an MCS by its nominal rate; raises for an unsupported rate."""
    try:
        return MCS_TABLE[float(rate_mbps)]
    except KeyError:
        raise ValueError(
            f"{rate_mbps} Mbps is not an IEEE 802.11p 10 MHz rate; "
            f"choose one of {sorted(MCS_TABLE)}"
        ) from None


#: Decoding threshold gamma_th. Derived from the operating MCS rather than
#: being an independent literal, so the threshold can never drift away from the
#: rate the airtime model is charging for.
SINR_TH_DB = get_mcs(OPERATING_RATE_MBPS).req_sinr_db


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 10.0)

def dbm_to_mw(dbm: float) -> float:
    return 10.0 ** (dbm / 10.0)

def path_loss_db(distance_m: float) -> float:
    return _PL_REF_DB + 10.0 * PL_EXP * math.log10(max(distance_m, 1.0))


# --------------------------------------------------------------------------
# Log-normal shadowing
#
# A dedicated, explicitly seeded RNG. It must NOT be the `random` module's
# global stream: the environment consumes that stream for its own Bernoulli
# success draws, so sharing it would make channel realizations depend on how
# many vehicles happened to transmit earlier in the episode. A private
# generator keeps run-to-run determinism under a fixed seed.
# --------------------------------------------------------------------------
_DEFAULT_CHANNEL_SEED = 42
_shadow_rng = random.Random(_DEFAULT_CHANNEL_SEED)


def seed_channel(seed: int) -> None:
    """Reseed the shadowing generator. Call once per episode reset."""
    _shadow_rng.seed(int(seed))


# ----------------------------------------------------------------------------
# Spatial correlation of shadowing.
#
# Shadowing is caused by objects -- buildings, trucks, foliage -- and a vehicle
# that is behind one does not leave it within a few metres. 3GPP TR 37.885 Table
# 6.2.3-1 gives a decorrelation distance of 10-13 m for urban V2X.
#
# Drawing an independent sample per step made every retry an independent trial,
# so ten retries over one second (about 8 m of travel, i.e. well inside one
# correlation length) behaved like ten fresh channels. That turns a vehicle
# stuck in a shadow into one that almost always gets through: measured at 300 m
# and 10 dBm, the final delivery-failure rate was 0.08 % with independent draws
# against 7.06 % when the shadow persists -- an 88x difference on a quantity the
# paper reports.
#
# The state is a per-link AR(1) process with rho = exp(-d / d_corr), the standard
# Gudmundson model, so the marginal stays N(0, sigma^2) while successive samples
# stay correlated over the right distance.
SHADOWING_DECORR_M = 12.0

_shadow_state: Dict[str, float] = {}


def reset_shadowing_state() -> None:
    """Forget every link's shadowing history. Call on episode reset."""
    _shadow_state.clear()


def draw_shadowing_db_correlated(
    link_id: str,
    distance_moved_m: float,
    sigma_db: float = SHADOWING_SIGMA_DB,
    decorr_m: float = SHADOWING_DECORR_M,
) -> float:
    """Shadowing for one link, correlated with that link's previous sample.

    `distance_moved_m` is how far the vehicle travelled since the last draw on
    this link. A large move decorrelates (rho -> 0) and the sample is effectively
    fresh; a retry a few metres later keeps most of the previous value.
    """
    if sigma_db <= 0.0:
        return 0.0
    prev = _shadow_state.get(link_id)
    if prev is None or decorr_m <= 0.0:
        val = _shadow_rng.gauss(0.0, sigma_db)
        _shadow_state[link_id] = val
        return val
    rho = math.exp(-abs(float(distance_moved_m)) / float(decorr_m))
    # Innovation variance keeps the marginal at sigma^2 rather than letting it
    # shrink toward zero as rho -> 1.
    val = rho * prev + math.sqrt(max(0.0, 1.0 - rho * rho)) * _shadow_rng.gauss(0.0, sigma_db)
    _shadow_state[link_id] = val
    return val


def draw_shadowing_db(sigma_db: float = SHADOWING_SIGMA_DB) -> float:
    """One INDEPENDENT zero-mean log-normal shadowing sample, in dB.

    Kept for callers that genuinely want an uncorrelated draw (a fresh link, a
    one-shot calculation). Anything that re-evaluates the same link over time
    should use `draw_shadowing_db_correlated` instead.
    """
    if sigma_db <= 0.0:
        return 0.0
    return _shadow_rng.gauss(0.0, sigma_db)


def draw_overlap(p_overlap: float) -> bool:
    """True when a co-channel frame actually overlaps the tagged one in time.

    A grant fixes roughly when a vehicle transmits, not the exact instant inside the
    step, so two frames on the same subchannel collide only if their start times fall
    within one frame duration of each other. The caller supplies that vulnerable-period
    probability (2 * T_air / T_step); this draws from the same seeded stream as
    shadowing so a run stays reproducible.
    """
    if p_overlap >= 1.0:
        return True
    if p_overlap <= 0.0:
        return False
    return _shadow_rng.random() < p_overlap


def rx_power_dbm(tx_dbm: float, distance_m: float, shadow_db: float = 0.0) -> float:
    """Received power: Ptx + G_tx + G_rx - PL(d) - shadowing."""
    return tx_dbm + G_TX_DBI + G_RX_DBI - path_loss_db(distance_m) - shadow_db

def rx_power_mw(tx_dbm: float, distance_m: float, shadow_db: float = 0.0) -> float:
    return dbm_to_mw(rx_power_dbm(tx_dbm, distance_m, shadow_db))

def noise_floor_dbm(bandwidth_hz: float = SUBCHANNEL_BW_HZ) -> float:
    """kTB + NF. At 10 MHz with NF 9 dB this is -174 + 70 + 9 = -95.0 dBm."""
    return -174.0 + 10.0 * math.log10(bandwidth_hz) + NOISE_FIGURE_DB

def noise_floor_mw(num_subchannels: int = NUM_SUBCHANNELS) -> float:
    """Noise power in one subchannel, in mW.

    The bandwidth is SUBCHANNEL_BW_HZ, the 10 MHz an 802.11p channel occupies by
    standard -- not TOTAL_BW_HZ / num_subchannels. The two agree only while
    num_subchannels happens to be 4; dividing the aggregate would make a
    three-channel configuration report a 13.3 MHz channel that the PHY cannot
    produce, and the noise floor would be wrong by 1.2 dB for a reason no one
    would find. `num_subchannels` is kept in the signature for call-site
    compatibility and is deliberately unused.
    """
    del num_subchannels
    return dbm_to_mw(noise_floor_dbm(SUBCHANNEL_BW_HZ))

def sensitivity_dbm(rate_mbps: float = OPERATING_RATE_MBPS,
                    bandwidth_hz: float = SUBCHANNEL_BW_HZ) -> float:
    """Receiver sensitivity implied by the MCS threshold and the noise floor."""
    return noise_floor_dbm(bandwidth_hz) + get_mcs(rate_mbps).req_sinr_db


# --------------------------------------------------------------------------
# Frame airtime
# --------------------------------------------------------------------------
def frame_symbols(payload_bytes: int = STATUS_UPDATE_BYTES,
                  rate_mbps: float = OPERATING_RATE_MBPS) -> int:
    """Number of OFDM DATA symbols for an L-byte PSDU (IEEE 802.11 17.3.5.3)."""
    bits = SERVICE_BITS + 8 * int(payload_bytes) + TAIL_BITS
    return int(math.ceil(bits / get_mcs(rate_mbps).bits_per_symbol))

def frame_airtime_s(payload_bytes: int = STATUS_UPDATE_BYTES,
                    rate_mbps: float = OPERATING_RATE_MBPS) -> float:
    """Occupancy of the subchannel by one frame, in seconds.

        airtime = 40 us (preamble + SIGNAL) + 8 us * N_sym
    This is what couples the scheduler's update interval to channel load: a
    grant does not merely 'happen', it holds its subchannel for this long.
    """
    return PREAMBLE_SIGNAL_TIME_S + OFDM_SYMBOL_TIME_S * frame_symbols(payload_bytes, rate_mbps)

def phy_data_rate_bps(rate_mbps: float = OPERATING_RATE_MBPS) -> float:
    """Nominal PHY rate in bits/s (6 Mbps -> 6e6)."""
    return get_mcs(rate_mbps).rate_mbps * 1e6


# --------------------------------------------------------------------------
# Uplink judgement
# --------------------------------------------------------------------------
def rayleigh_success_prob(signal_mw: float, interferer_mws, noise_mw: float,
                          sinr_th_lin: float) -> float:
    """P(SINR >= th) under independent Rayleigh fading on all links."""
    if signal_mw <= 0.0:
        return 0.0
    p = math.exp(-sinr_th_lin * noise_mw / signal_mw)
    for i_mw in interferer_mws:
        p *= 1.0 / (1.0 + sinr_th_lin * (i_mw / signal_mw))
    return p

def judge_uplink(group, num_subchannels: int = NUM_SUBCHANNELS,
                 shadowing_sigma_db: float = SHADOWING_SIGMA_DB,
                 sinr_th_db: float = SINR_TH_DB,
                 interferers_of=None,
                 moved_of=None) -> dict:
    """group: list of (id, tx_dbm, distance_m), ALL on the same subchannel.
    Returns {id: success_probability} with mutual Rayleigh-SINR interference.

    One shadowing sample is drawn per link and reused for that link's role as
    both the desired signal and as interference at the RSU, because it is a
    property of the propagation path, not of the receiver's viewpoint.

    `interferers_of` (optional) maps a member id to the ids that actually overlap
    it in time; members not listed interfere with nobody. When omitted, every
    other member of the group interferes, which is the legacy behaviour.

    Why the mapping exists. The caller used to enforce the vulnerable-period
    overlap by calling this function once per tagged vehicle with a freshly drawn
    interferer list. That broke the guarantee in the paragraph above twice over:
    the same link got a DIFFERENT shadowing sample in every neighbour's
    judgement (the propagation path became a function of the receiver's
    viewpoint, exactly what the contract excludes), and the overlap event was
    drawn independently per ordered pair, so A's frame could collide with B's
    while B's did not collide with A's -- physically impossible. Passing a
    symmetric overlap graph in and resolving the whole group in ONE call fixes
    both: shadowing is drawn once per link, and the overlap relation is whatever
    the caller built, symmetric or not, but built once.
    """
    n0 = noise_floor_mw(num_subchannels)
    th = _db_to_lin(sinr_th_db)
    # `moved_of` maps a member id to how far it travelled since its last draw on
    # this link. With it the shadowing is spatially correlated, so a vehicle that
    # is behind an obstruction stays behind it across the retries within one
    # second -- which is the physical situation and the one that decides whether
    # an update is eventually delivered. Without it each draw is independent,
    # which is the legacy behaviour and is kept for callers with no position
    # history (unit tests, one-shot link-budget calculations).
    if moved_of is None:
        powers = {
            gid: rx_power_mw(tx, d, draw_shadowing_db(shadowing_sigma_db))
            for (gid, tx, d) in group
        }
    else:
        powers = {
            gid: rx_power_mw(
                tx, d,
                draw_shadowing_db_correlated(
                    str(gid), moved_of.get(gid, float("inf")), shadowing_sigma_db),
            )
            for (gid, tx, d) in group
        }
    out = {}
    for gid, tx, d in group:
        S = powers[gid]
        if interferers_of is None:
            interf = [powers[o] for (o, _, _) in group if o != gid]
        else:
            allowed = set(interferers_of.get(gid, ()))
            interf = [powers[o] for (o, _, _) in group if o != gid and o in allowed]
        out[gid] = rayleigh_success_prob(S, interf, n0, th)
    return out


def overlap_graph_from_start_times(ids, frame_airtime_s: float,
                                   step_length_s: float) -> dict:
    """Symmetric co-channel overlap graph, from actual frame start instants.

    WHY THIS EXISTS. The overlap used to be a single probability, 2*T_air/T_step,
    applied independently to each unordered pair. That is the textbook ALOHA
    vulnerable-period result, and it is derived for UNCOORDINATED transmitters
    whose start times are uniform over the period. Our channel is not that: the
    RSU issues grants, and every granted frame in a step is released at the same
    instant. Taken literally, simultaneous release means every co-channel pair
    collides -- probability 1, not the 0.9 % the formula returns. The scalar was
    therefore describing a system nobody had implemented, and every reported
    packet-loss number rested on it.

    Drawing an explicit start offset makes the assumption visible and true: the
    grant names a subchannel and a 100 ms period, and the exact instant within
    that period is not coordinated -- the same semantics as a C-V2X recommended
    resource. Two frames then collide exactly when their airtimes overlap, which
    is symmetric by construction rather than by careful pair-wise bookkeeping,
    and the marginal collision probability recovers 2*T_air/T_step as it should.
    """
    ids = list(ids)
    if not ids:
        return {}
    latest = max(0.0, float(step_length_s) - float(frame_airtime_s))
    starts = {i: _shadow_rng.uniform(0.0, latest) if latest > 0.0 else 0.0 for i in ids}
    graph = {i: [] for i in ids}
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ia, ib = ids[a], ids[b]
            if abs(starts[ia] - starts[ib]) < float(frame_airtime_s):
                graph[ia].append(ib)
                graph[ib].append(ia)
    return graph


def draw_overlap_graph(ids, p_overlap: float) -> dict:
    """Symmetric co-channel overlap graph over `ids`, one draw per unordered pair.

    Returns {id: [ids that overlap it]}. Drawing per unordered pair is what makes
    the relation symmetric: if A's frame hits B's, B's hits A's. The previous
    per-ordered-pair draw produced one-sided collisions.
    """
    ids = list(ids)
    graph = {i: [] for i in ids}
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if draw_overlap(p_overlap):
                graph[ids[a]].append(ids[b])
                graph[ids[b]].append(ids[a])
    return graph
