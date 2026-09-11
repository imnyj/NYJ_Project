"""SUMO Network and Simulation Configuration Generator.

Procedurally generates SUMO grid networks, traffic route definitions,
RSU POI additional files, and sumocfg files with atomic file writing
and robust concurrency guarantees.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import random
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple, Union

# ============= Control Variables ===============
# OUTAGE_ZONE is the uncovered gap between the coverage discs of two adjacent
# RSUs. The original design used OUTAGE_ZONE == RSU_RANGE (800/800), i.e. an
# edge is 2/3 covered and 1/3 outage. That 1:1 ratio is preserved when the
# range is reduced to a realistic 5.9 GHz urban value (see RSU_RANGE below).
OUTAGE_ZONE: float = 300.0
AV_SPEED: float = 40.0           # 평균 속도 (km/h). 0이면 에피소드마다 임의로 설정
DENSITY: float = 20.0            # 평균 밀도 (/1km-lane). 0이면 에피소드마다 임의로 설정
# The traffic densities the whole study is defined over (veh/km/lane).
#
# It lives here, beside the generator that consumes it, because three separate
# consumers had been restating it as a literal list: `run_all.py --density`
# (the training schedule), `evaluate.py DEFAULT_DENSITIES` (the benchmark grid)
# and the observation normaliser for feature [13]. A grid that disagrees between
# any two of those is silent -- the models train on one support and the table
# reports another, or the contention feature is normalised against a ceiling the
# scenario never reaches.
#
# It stops at 35 because that is where the ROAD saturates, not where interest
# stops. Measured in-range vehicle counts against requested density: 22.2, 36.7,
# 68.2, 91.5, 123.0, 138.3, 141.7 for 5..35, then 138.5, 138.9, 134.0 for 40, 45
# and 50 -- flat, and non-monotone at (35, 40) and (45, 50). Past saturation a
# larger request does not produce a busier network (user decision 2026-09-02).
DENSITY_GRID: Tuple[float, ...] = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0)
P_GEN: float = 0.005
NUM_BLOCKS: int = 6
# Horizon written into the `end=` attribute of every <flow>. rou.xml `end=` is in
# SECONDS, and the caller used to assign a STEP COUNT to it (hot_swap_trainer set
# `ss.MAX_STEPS = max_steps + warmup + 100`), which at a 0.1 s step made the flows
# 10x longer than intended. Harmless in that direction, but the sign flips the
# moment the step length changes, and vehicle generation would then stop partway
# through an episode. The name now says the unit.
FLOW_END_S: float = 3600.0
#: Deprecated alias kept for external scripts; `FLOW_END_S` is the live value.
MAX_STEPS: float = FLOW_END_S
CORNER_SPEED_LIMIT: float = 50.0 / 3.6
STEP_LENGTH: float = 0.1         # SUMO simulation resolution (s). Must be <= the
                                 # minimum action update interval Delta = 0.1 s.

# ----------------------------------------------------------------------------
# Explicit vehicle type.
#
# Without a <vType> the flows inherit SUMO's DEFAULT_VEHTYPE, whose speedFactor
# is drawn from `normc(1, 0.1, 0.2, 2)` -- a truncated normal whose UPPER bound
# is 2.0. Vehicles therefore exceed the lane speed limit by an amount with no
# deterministic ceiling, and `rl_interface.get_sumo_max_edge_speed()` (which
# reads the *lane* limit out of net.xml) is not the observable maximum. Measured
# on this scenario: fastest observed vehicle 14.768 m/s against a 13.32 m/s lane
# limit (+11 %), with 8.62 % of all observations clipped to exactly 1.0 in the
# normalised speed feature -- i.e. the fastest vehicles, whose constant-velocity
# extrapolation decays quickest and which this paper most needs to tell apart,
# were indistinguishable from one another.
#
# Truncating at +/- 2 sigma keeps the same mean and spread (so the traffic stays
# heterogeneous) while making the ceiling a declared, reproducible property of
# the scenario file: max observable speed = 1.20 * lane limit.
# `rl_interface.get_sumo_max_speed_factor()` reads this bound back.
#
# `maxSpeed` is deliberately NOT pinned here. The binding constraint is
# lane_limit * speedFactor (15.98 m/s in this scenario); the SUMO passenger
# default maxSpeed is 55.55 m/s and is nowhere near binding. Pinning it would
# make it the binding constraint the moment anyone raises AV_SPEED, and the
# observation normaliser would then silently disagree with the simulation.
VTYPE_ID: str = "v2i"
SPEED_FACTOR_MEAN: float = 1.00
SPEED_FACTOR_DEV: float = 0.10
SPEED_FACTOR_MIN: float = 0.80
SPEED_FACTOR_MAX: float = 1.20

# ============= Environment Variables ===============
# 300 m is the defensible upper bound for an ITS-G5 / C-V2X 5.9 GHz RSU in an
# urban NLOS-prone environment with path-loss exponent 2.3 (typical reported
# reliable range 200-300 m). The previous 800 m was not defensible.
RSU_RANGE: float = 300.0                           # Communication range of RSU
EDGE_LENGTH: float = RSU_RANGE * 2.0 + OUTAGE_ZONE # Distance between RSUs (900m)
GRID_SIZE: float = NUM_BLOCKS * EDGE_LENGTH        # Network Size
NUM_LANES: int = 2                                 # Lane Number
SPEED: float = AV_SPEED / 3.6                      # average speed of vehicles
DEL_SPEED: float = 0.2                             # delta speed variance
# NOTE: the per-edge speed limits are drawn as SPEED * (1 +/- DEL_SPEED) when the
# network is written, so the effective ceiling is a property of the generated
# net.xml (read back by rl_interface.get_sumo_max_edge_speed), not of a constant
# here. A former MAX_SPEED literal sat at this spot, was recomputed on every
# make_sumo_files() call, and was never read by anything.
step: float = GRID_SIZE / NUM_BLOCKS

#: Number of road arms meeting at the RSU's junction.
#:
#: The RSU is placed on a `traffic_light` node of the grid and the busiest one is
#: selected (`AoiV2IEnv.reset`), which in a NUM_BLOCKS x NUM_BLOCKS grid is an
#: interior four-way junction. A boundary junction has fewer arms, so 4 is the
#: upper bound and using it makes the derived capacity below a ceiling rather
#: than an estimate -- which is what a normaliser must be.
RSU_JUNCTION_ARMS: int = 4


def rsu_coverage_lane_km() -> float:
    """Lane-kilometres of road inside the RSU's coverage disc.

    Geometry, not measurement: the disc has radius RSU_RANGE around a junction,
    each arm carries one edge per direction and NUM_LANES lanes per edge, and the
    next junction is EDGE_LENGTH = 2*RSU_RANGE + OUTAGE_ZONE away, so the disc
    never reaches it and each arm contributes exactly RSU_RANGE metres.

        arms * RSU_RANGE * (2 directions * NUM_LANES) / 1000

    In the current scenario that is 4 * 300 * 4 / 1000 = 4.8 lane-km. Multiplying
    it by a requested density gives the expected number of vehicles the RSU can
    see, which is what feature [13] has to be normalised against. Checked against
    the measured in-range counts (22.2, 36.7, 68.2, 91.5, 123.0, 138.3, 141.7 for
    densities 5..35): the prediction 24, 48, 72, 96, 120, 144, 168 tracks them to
    within 15 % up to 30 and over-predicts only at 35, where the road is already
    saturated -- i.e. it is a true upper envelope.

    Read at call time, not snapshotted, so a swept RSU_RANGE or NUM_LANES is
    followed instead of silently ignored.
    """
    return float(RSU_JUNCTION_ARMS) * float(RSU_RANGE) * (2.0 * float(NUM_LANES)) / 1000.0


# Where the generated scenario files live.
#
# This used to be unconditionally the package directory, which made every process
# on the machine share ONE `generated.net.xml` / `generated.rou.xml` /
# `.sumo_gen_signature.json`. Generation itself is serialised by a file lock, but
# that only prevents a torn write: if process A generates for density 25 and
# process B then regenerates for density 20, A's `libsumo.start()` silently reads
# B's network. No error, no warning, and the run reports metrics for a scenario
# it never asked for. It was observed in practice on 2026-09-01 when two
# measurement processes overlapped.
#
# That makes a parallel run -- nine models spread over four GPUs, which is the
# whole point of having four -- unable to produce trustworthy numbers. Setting
# PAPER4_SUMO_DIR gives a process its own scenario directory; leaving it unset
# keeps the original single-process behaviour byte for byte.
BASE_PATH: str = os.environ.get("PAPER4_SUMO_DIR") or os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(BASE_PATH):
    os.makedirs(BASE_PATH, exist_ok=True)


def resolve_base_path(base_path: Optional[str] = None) -> str:
    """The ONE place a scenario directory is resolved. Every path derives from it.

    The environment variable above isolates a whole PROCESS, which is enough for
    the parallel HPO groups but not for a caller inside one process that wants
    its own scenario -- a test, a preflight check, a benchmark sweep. Passing
    `base_path` is that second mechanism, and it used to be half-implemented in a
    way that was worse than not having it at all: `_generation_lock`,
    `are_sumo_files_valid`, `generation_signature_matches` and
    `_write_generation_signature` all honoured the argument, while
    `_make_sumo_files_impl` -- the function that actually writes the seven files
    -- read the module global directly for every one of its paths. The lock was
    therefore taken in the caller's directory and the SCENARIO was written into
    the shared one. Measured on 2026-09-05: a pytest run given an explicit path
    created only `.sumo_gen.lock` there and overwrote `coder/src/sumo/`, which
    corrupted another session's experiment.

    The repair is structural rather than local. Resolution happens here and
    nowhere else; every other function takes the resolved string and joins onto
    it, so fixing one function can no longer leave a sibling reading the global.

    `None` means the process default, byte for byte the previous behaviour. The
    global is read at CALL time, so a test that monkeypatches `BASE_PATH` still
    works. A relative argument is made absolute, because the working directory
    changes between callers and a scenario directory that moves with it is not a
    scenario directory.
    """
    if base_path:
        return os.path.abspath(str(base_path))
    return BASE_PATH

T_to_INIT: float = 0.0
L_tot: float = 0.0
L_path_avg: float = 0.0

# ----------------------------------------------------------------------------
# Network generation randomness.
#
# The per-edge speed limits used to be drawn from the `random` module's GLOBAL
# stream. That made every downstream consumer of that stream depend on whether
# the cached SUMO files happened to be reusable: regenerating consumed exactly
# 200 `random.uniform` draws, a cache hit consumed none, so the environment's
# Bernoulli uplink-success draws (`random.random()`) started from a different
# stream position on episode 1 (signature miss -> regenerate) than on episode 2
# (cache hit). Same seed, different channel realisations, i.e. the runs were not
# reproducible at all. A private generator is the same remedy
# `Communications._shadow_rng` already applies for shadowing.
GENERATION_SEED: int = 42
_gen_rng: random.Random = random.Random(GENERATION_SEED)


def seed_generation(seed: int) -> None:
    """Reseed the private network-generation RNG. Call before make_sumo_files()."""
    global GENERATION_SEED
    GENERATION_SEED = int(seed)
    _gen_rng.seed(int(seed))


# ---------------------------------------------------------------------------
# The road network as a FUNCTION of (density, cycle)
# ---------------------------------------------------------------------------
#: Base of the road-network seed. NOT a training seed, NOT an evaluation seed,
#: and deliberately not called `SEED` or `BASE_SEED`: it decides the SHAPE OF THE
#: ROAD and nothing else. Traffic, channel realisations and torch initialisation
#: are seeded elsewhere and never through this.
#:
#: The value is arbitrary and is meant to stay put. Changing it changes every
#: road in the experiment.
ROAD_NETWORK_BASE_SEED: int = 970000

#: Spacing between consecutive cycles in the seed space. Larger than any density
#: in the grid so that `(density, cycle)` maps injectively: cycle 1 at density 5
#: can never collide with cycle 0 at density 35.
_ROAD_SEED_CYCLE_STRIDE: int = 1000


def road_seed(density: float, cycle: int = 0) -> int:
    """The generation seed for one (density, cycle). Readable and reproducible.

    ---------------------------------------------------------------------------
    WHY THE ROAD HAD TO BECOME A FUNCTION OF SOMETHING
    ---------------------------------------------------------------------------
    Until 2026-09-06 nothing decided the road. `_gen_rng` is a module global,
    `seed_generation` is the only thing that reseeds it, and only
    `prepare_scenario` called that. `AoiV2IEnv._init_sumo` reaches
    `make_sumo_files` directly, so the road a scenario got was a function of how
    many networks the PROCESS had already generated.

    Measured that day (`etc/scripts/measure_road_network_provenance.py`), over
    nine models by seven densities:

      * TRAINING reseeded once per run, so all nine models walked one identical
        road sequence -- fair and reproducible, but by accident of call order;
      * EVALUATION and the SEARCH never reseeded, so the same density produced
        five to seven different roads depending on which model came first. The
        nine baselines were being scored on different roads.

    A seed derived from the request itself removes the dependency on call order
    entirely: whoever asks for (density, cycle), in whatever order, from whatever
    process, gets the same road.

    ---------------------------------------------------------------------------
    WHY `cycle` AND NOT DENSITY ALONE
    ---------------------------------------------------------------------------
    Because one road per density would change the experiment rather than repair
    it. Training runs 100 episodes over 7 densities, so it already visits each
    density about fourteen times, and each visit regenerated -- measured, eight
    distinct roads in the first three passes. That is a road CURRICULUM, and it
    is doing work: 100 episodes x 2000 steps on a single road is 200k steps of
    exposure to one geometry, ample to memorise it, and a comparison run that way
    would be measuring memorisation as much as scheduling.

    So the cycle index is kept as an explicit argument. Each caller says which
    pass it is on:

        training    cycles 0..13    (100 episodes / 7 densities)
        collection  cycles 0..2     (overlaps the first passes training sees)
        evaluation  cycle 15        (a road TRAINING NEVER USED)

    Evaluation on an unused road is the point of separating them. This paper
    claims the policy learns predictability and chooses silence intervals in
    advance; that claim is only distinguishable from having memorised a road if
    the score comes from a road the model never trained on. It also equalises the
    nine baselines, whose exposure to any particular training road would
    otherwise differ.

    ---------------------------------------------------------------------------
    THE MAPPING
    ---------------------------------------------------------------------------
        seed = ROAD_NETWORK_BASE_SEED + cycle * 1000 + round(density * 10)

    Arithmetic on the arguments, so a human can recompute any road's seed with a
    pencil and reproduce it years later. `hash()` is NOT used: Python randomises
    string hashing per process, so a hash-derived road would differ between runs
    of the same code. Density is multiplied by ten before rounding so that the
    grid's integer densities and any half-step a future grid might add both land
    on distinct seeds. The stride exceeds `max(DENSITY_GRID) * 10`, which is what
    makes the two-argument mapping injective.
    """
    d = int(round(float(density) * 10.0))
    if d < 0:
        raise ValueError(f"density must be non-negative, got {density}")
    if d >= _ROAD_SEED_CYCLE_STRIDE:
        raise ValueError(
            f"density {density} maps to offset {d}, which is not below the cycle "
            f"stride {_ROAD_SEED_CYCLE_STRIDE}; two different (density, cycle) "
            "pairs would share a road. Raise the stride."
        )
    if int(cycle) < 0:
        raise ValueError(f"cycle must be non-negative, got {cycle}")
    return int(ROAD_NETWORK_BASE_SEED + int(cycle) * _ROAD_SEED_CYCLE_STRIDE + d)


def seed_road_network(density: float, cycle: int = 0) -> int:
    """Seed `_gen_rng` for one (density, cycle) and return the seed used.

    The single call every entry point should make before generating. Returning
    the seed rather than discarding it is what lets a caller record in its own
    metadata which road it ran on, instead of that being recoverable only by
    re-deriving the arithmetic.
    """
    seed = road_seed(density, cycle)
    seed_generation(seed)
    return seed


def _atomic_write_text(file_path: str, content: str) -> None:
    """Atomically writes string content to target file via temporary file replacement."""
    target_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(target_dir, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target_dir,
        delete=False,
        prefix=".tmp_sumo_",
        suffix=".tmp",
    )
    temp_path = temp_file.name
    try:
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def _atomic_write_tree(file_path: str, tree: ET.ElementTree) -> None:
    """Atomically writes an ElementTree to target file with xml_declaration and UTF-8 encoding."""
    target_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(target_dir, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=target_dir,
        delete=False,
        prefix=".tmp_sumo_tree_",
        suffix=".tmp",
    )
    temp_path = temp_file.name
    try:
        tree.write(temp_file, encoding="utf-8", xml_declaration=True)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def _is_valid_xml_file(filepath: str) -> bool:
    """Check if file exists, is non-empty, and is a well-formed XML document."""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return False
    try:
        ET.parse(filepath)
        return True
    except Exception:
        return False


def are_sumo_files_valid(base_path: Optional[str] = None) -> bool:
    """Check if all 7 required SUMO files exist, are non-empty, and are valid XML documents."""
    target_dir = resolve_base_path(base_path)
    required_files = [
        "generated.nod.xml",
        "generated.edg.xml",
        "generated.net.xml",
        "generated.rou.xml",
        "generated.add.xml",
        "generated.sumocfg",
        "rsu.poi.xml",
    ]
    return all(_is_valid_xml_file(os.path.join(target_dir, f)) for f in required_files)


SIGNATURE_FILE: str = ".sumo_gen_signature.json"

# Parameters that must match EXACTLY for the cached SUMO files to be reusable.
# DENSITY is included because it is baked into the per-flow `probability`
# attribute of generated.rou.xml; without this check a caller that changes
# `ss.DENSITY` silently keeps the previously generated traffic demand, which
# makes any density sweep a no-op.
_SIGNATURE_EXACT_KEYS = (
    "RSU_RANGE",
    "OUTAGE_ZONE",
    "NUM_BLOCKS",
    "NUM_LANES",
    "DENSITY",
    "AV_SPEED",
    "DEL_SPEED",
    "STEP_LENGTH",
    # The speedFactor bounds are written into generated.rou.xml and are read back
    # by rl_interface.get_sumo_max_speed_factor() as the observation normaliser,
    # so a cached file set generated under different bounds is NOT reusable.
    "SPEED_FACTOR_MEAN",
    "SPEED_FACTOR_DEV",
    "SPEED_FACTOR_MIN",
    "SPEED_FACTOR_MAX",
)


def current_generation_signature(
    num_blocks: Optional[int] = None,
    density: Optional[float] = None,
    flow_end_s: Optional[float] = None,
) -> Dict[str, float]:
    """Snapshot of every knob that changes the generated SUMO files.

    `density` and `flow_end_s` are THIS RUN's values, handed down the call path.
    Each falls back to the module global when the caller names none, so a call
    with no arguments behaves exactly as it always did.

    Passing them rather than assigning them is the whole point. `prepare_scenario`
    used to do `ss.FLOW_END_S = (max_steps + warmup + 100) * STEP_LENGTH` and
    `ss.DENSITY = density`, and those values then outlived the run twice over:
    once in the module, where the next call in the same process compared against
    them, and once on disk, because this function writes FLOW_END_S into the
    signature file. Observed consequence on 2026-09-05: the shared scenario
    directory carried flow horizons of 131 s and 138 s -- the values a 10-step and
    an 80-step pytest rollout produce against a 1200-step warm-up -- where 3600 s
    was expected, so anything reading it next measured a road that had already
    stopped generating traffic.
    """
    nb = int(num_blocks) if num_blocks is not None else int(NUM_BLOCKS)
    if num_blocks is None and nb == 5:
        nb = 6  # mirrors the legacy normalisation performed by make_sumo_files()
    elif nb < 2:
        nb = 6
    sig: Dict[str, float] = {k: float(globals()[k]) for k in _SIGNATURE_EXACT_KEYS}
    sig["NUM_BLOCKS"] = float(nb)
    if density is not None:
        sig["DENSITY"] = float(density)
    sig["FLOW_END_S"] = float(FLOW_END_S if flow_end_s is None else flow_end_s)
    # THE SEED THE NETWORK WAS DRAWN WITH, added 2026-09-06.
    #
    # Its absence was recorded in `prepare_scenario` as an open design question
    # -- "does a seed re-roll the road network, or only the traffic?" -- and on
    # that day it produced a real defect. Without it the cache answers "these
    # files match your parameters" while the files were drawn from a different
    # generator state, so a caller that asks for a specific road silently gets
    # whichever one is already on disk. That is precisely the failure
    # `road_seed()` exists to remove, and the seed has to be part of the cache
    # key for the removal to hold.
    #
    # It is compared EXACTLY, not leniently like FLOW_END_S: a road drawn from
    # another seed is a different road, never a sufficient one.
    #
    # It is NOT in `_SIGNATURE_EXACT_KEYS`, though, and this comment said it was
    # until 2026-09-06. That tuple is built by reading module globals of the same
    # name, and `ROAD_SEED` is not one -- the value comes from `GENERATION_SEED`.
    # `generation_signature_matches` appends it to the comparison list instead.
    # The behaviour is right and the description was wrong, which is the harder
    # kind to catch: a reader checking the tuple concludes the seed is unchecked.
    #
    # Consequence, stated because it is not free: every signature file written
    # before this lacks the key, so `generation_signature_matches` returns False
    # for it and the first call regenerates. One regeneration per scenario
    # directory, once.
    sig["ROAD_SEED"] = float(GENERATION_SEED)
    return sig


def _read_generation_signature(base_path: Optional[str] = None) -> Optional[Dict[str, float]]:
    path = os.path.join(resolve_base_path(base_path), SIGNATURE_FILE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {str(k): float(v) for k, v in data.items()}
    except Exception:
        return None


def _write_generation_signature(
    base_path: Optional[str] = None,
    num_blocks: Optional[int] = None,
    density: Optional[float] = None,
    flow_end_s: Optional[float] = None,
) -> None:
    path = os.path.join(resolve_base_path(base_path), SIGNATURE_FILE)
    sig = current_generation_signature(
        num_blocks=num_blocks, density=density, flow_end_s=flow_end_s
    )
    _atomic_write_text(path, json.dumps(sig, indent=2, sort_keys=True))


def generation_signature_matches(
    base_path: Optional[str] = None,
    num_blocks: Optional[int] = None,
    density: Optional[float] = None,
    flow_end_s: Optional[float] = None,
) -> bool:
    """True when the cached SUMO files were generated with the current parameters.

    All geometry/demand knobs must match exactly. `FLOW_END_S` only sets the flow
    `end=` horizon, so a cached file whose horizon is at least as long as the one
    now requested is still usable; this avoids regenerating on every episode just
    because a caller shortened its step budget.
    """
    stored = _read_generation_signature(base_path)
    if stored is None:
        return False
    wanted = current_generation_signature(
        num_blocks=num_blocks, density=density, flow_end_s=flow_end_s
    )
    for key in _SIGNATURE_EXACT_KEYS + ("NUM_BLOCKS", "ROAD_SEED"):
        if key not in stored or abs(stored[key] - wanted[key]) > 1e-9:
            return False
    if stored.get("FLOW_END_S", -1.0) + 1e-9 < wanted["FLOW_END_S"]:
        return False
    return True


def CalcP_GEN(density: float) -> float:
    """Calculate vehicle generation probability based on traffic density."""
    global L_tot, L_path_avg, T_to_INIT
    n = max(NUM_BLOCKS - 1, 1)
    L_tot = 2.0 * n * NUM_BLOCKS * EDGE_LENGTH * (2.0 * NUM_LANES)
    L_path_avg = EDGE_LENGTH * (1.0 + (2.0 * (n * n - 1.0)) / (3.0 * n))
    v = float(AV_SPEED) if AV_SPEED > 0 else 40.0
    dens = float(density) if density > 0 else 10.0
    T_to_INIT = 3.6 * (L_path_avg / v)
    return (dens * L_tot * v) / (L_path_avg * n * n * 3600.0)


def make_dead_end_nodes(netfile: str, dead_end_nodes: Union[Dict[str, Any], set, list]) -> None:
    """Parse netfile, mark specified boundary junctions as dead_end, and write back atomically."""
    tree = ET.parse(netfile)
    root = tree.getroot()
    for node in root.findall("junction"):
        node_id = node.get("id")
        if node_id in dead_end_nodes:
            node.set("type", "dead_end")
    _atomic_write_tree(netfile, tree)


GENERATION_LOCK_FILE: str = ".sumo_gen.lock"


@contextlib.contextmanager
def _generation_lock(base_path: Optional[str] = None):
    """Serialise SUMO file generation across processes.

    Every training process regenerates into the same src/sumo/ directory, and the
    seven generated files only make sense as a mutually consistent set. Individual
    writes are atomic, but without a lock two processes running different densities
    can interleave and leave, say, a net.xml from one parameter set beside a
    rou.xml from another. An exclusive flock over the whole check-and-generate
    section makes the set consistent; the lock file is never deleted, so the
    inode stays stable for concurrent openers.

    The parent directory is created here rather than trusted to exist. `O_CREAT`
    creates the file only, so an absent directory makes `os.open` raise
    FileNotFoundError, and this is the FIRST thing `make_sumo_files` touches --
    the failure lands before any of the generation helpers, every one of which
    does call `os.makedirs`. `BASE_PATH` is created once at import, which is not
    enough for a long-running process: on 2026-09-04 at 14:07:30 the g1 HPO group
    lost `results/hpo_parallel/g1/sumo/` two and a half hours into its run, and
    every remaining rollout died here -- 62 of them, taking the whole SAC study
    with it (logs/hpo_parallel/g1.log). Ensuring the directory at the gate makes
    the generation path self-healing instead, and it covers the callers that pass
    an explicit `base_path` the import-time creation never saw.
    """
    directory = resolve_base_path(base_path)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, GENERATION_LOCK_FILE)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _make_sumo_files_impl(force_regenerate: bool = False, num_blocks: Optional[int] = None,
                          base_path: Optional[str] = None,
                          density: Optional[float] = None,
                          flow_end_s: Optional[float] = None) -> None:
    """Generate all SUMO network, route, add, poi, and configuration files atomically.

    If force_regenerate is False and all required SUMO files already exist with valid
    content AND were generated from the current parameter set (see
    `generation_signature_matches`), re-generation is skipped to prevent unnecessary
    I/O overhead and race conditions. A changed DENSITY / RSU_RANGE / NUM_BLOCKS /
    STEP_LENGTH forces regeneration, so callers that sweep those knobs actually get
    a network and demand matching what they asked for.

    Every path below derives from `target_dir`, which is resolved ONCE. This
    function used to read the module-level `BASE_PATH` directly for all seven
    outputs, the netconvert temporary file and both cache checks, while its
    caller took the lock in the directory it had been given -- so an explicit
    `base_path` produced a lock in one place and a scenario in another. See
    `resolve_base_path`.
    """
    global NUM_BLOCKS, GRID_SIZE, step, SPEED, EDGE_LENGTH

    # This run's demand and flow horizon, resolved once as LOCALS. Everything
    # below reads these, never `DENSITY` / `FLOW_END_S` again, so generating a
    # short scenario for one caller cannot change what the next caller generates.
    dens = float(DENSITY if density is None else density)
    flow_end = float(FLOW_END_S if flow_end_s is None else flow_end_s)

    target_dir = resolve_base_path(base_path)
    os.makedirs(target_dir, exist_ok=True)

    # EDGE_LENGTH is fully derived from RSU_RANGE / OUTAGE_ZONE. Re-derive it here so
    # external callers that override those module globals (e.g. src/NetSim.py) get a
    # consistent geometry instead of a stale import-time value.
    EDGE_LENGTH = RSU_RANGE * 2.0 + OUTAGE_ZONE

    # Check if existing files are complete, valid, and generated from these parameters
    if (
        not force_regenerate
        and are_sumo_files_valid(target_dir)
        and generation_signature_matches(
            target_dir, num_blocks=num_blocks, density=dens, flow_end_s=flow_end
        )
    ):
        return

    # Normalize NUM_BLOCKS cleanly and consistently
    if num_blocks is not None:
        NUM_BLOCKS = int(num_blocks)
    elif NUM_BLOCKS == 5:
        # Legacy compatibility: if externally set to 5 expecting NUM_BLOCKS += 1, fix to 6
        NUM_BLOCKS = 6
    elif NUM_BLOCKS < 2:
        NUM_BLOCKS = 6

    # Refresh derived geometry
    GRID_SIZE = NUM_BLOCKS * EDGE_LENGTH
    step = GRID_SIZE / NUM_BLOCKS
    SPEED = (AV_SPEED / 3.6) if AV_SPEED > 0 else (40.0 / 3.6)

    def _make_axis_positions() -> Tuple[List[float], List[float]]:
        xs = [0.0] * (NUM_BLOCKS + 1)
        ys = [0.0] * (NUM_BLOCKS + 1)
        for i in range(1, NUM_BLOCKS + 1):
            inc = step / 2.0 if (i == 1 or i == NUM_BLOCKS) else step
            xs[i] = xs[i - 1] + inc
            ys[i] = ys[i - 1] + inc
        return xs, ys

    def generate_nodes_edges() -> Tuple[List[str], List[str]]:
        nodes: List[str] = []
        edges: List[str] = []
        temp_N: Dict[Tuple[int, int], str] = {}
        xs, ys = _make_axis_positions()
        ndx = 1
        for i in range(NUM_BLOCKS + 1):
            for j in range(NUM_BLOCKS + 1):
                if (i == 0 and (j == 0 or j == NUM_BLOCKS)) or (i == NUM_BLOCKS and (j == 0 or j == NUM_BLOCKS)):
                    continue
                x = xs[i]
                y = ys[j]
                types_ = "dead_end" if i == 0 or j == 0 or i == NUM_BLOCKS or j == NUM_BLOCKS else "traffic_light"
                nodes.append(f'<node id="N{ndx}" x="{x}" y="{y}" type="{types_}"/>')
                temp_N[(i, j)] = f"N{ndx}"
                ndx += 1

        edge_id = 0
        chk_edge: Dict[Tuple[str, str], int] = {}
        for i in range(1, NUM_BLOCKS):
            for j in range(1, NUM_BLOCKS):
                from_node = temp_N[(i, j)]
                for dx, dy in [[0, 1], [1, 0], [0, -1], [-1, 0]]:
                    to_node = temp_N[(i + dx, j + dy)]
                    if SPEED == 0:
                        speed1 = _gen_rng.uniform(10.0 / 3.6, 120.0 / 3.6)
                        speed2 = _gen_rng.uniform(10.0 / 3.6, 120.0 / 3.6)
                    else:
                        speed1 = _gen_rng.uniform(SPEED * (1.0 - DEL_SPEED), SPEED * (1.0 + DEL_SPEED))
                        speed2 = _gen_rng.uniform(SPEED * (1.0 - DEL_SPEED), SPEED * (1.0 + DEL_SPEED))
                    ed1 = f'<edge id="E{edge_id}" from="{from_node}" to="{to_node}" numLanes="{NUM_LANES}" speed="{speed1}"/>'
                    ed2 = f'<edge id="-E{edge_id}" from="{to_node}" to="{from_node}" numLanes="{NUM_LANES}" speed="{speed2}"/>'
                    if (from_node, to_node) not in chk_edge:
                        edges.append(ed1)
                        chk_edge[(from_node, to_node)] = edge_id
                    if (to_node, from_node) not in chk_edge:
                        edges.append(ed2)
                        chk_edge[(to_node, from_node)] = edge_id * -1
                    edge_id += 1
        return nodes, edges

    nodes, edges = generate_nodes_edges()
    nodefile = os.path.join(target_dir, "generated.nod.xml")
    edgefile = os.path.join(target_dir, "generated.edg.xml")
    gen_netfile = os.path.join(target_dir, "generated.net.xml")

    # 1. Write node and edge XML files atomically
    _atomic_write_text(nodefile, "<nodes>\n" + "\n".join(nodes) + "\n</nodes>\n")
    _atomic_write_text(edgefile, "<edges>\n" + "\n".join(edges) + "\n</edges>\n")

    # 2. Run netconvert to compile network XML into temporary file first, then atomically update dead-end nodes
    netconvert_bin = shutil.which("netconvert") or "/home/imnyj/venv/bin/netconvert"
    temp_net = tempfile.NamedTemporaryFile(dir=target_dir, delete=False, prefix=".tmp_net_", suffix=".net.xml")
    temp_net_path = temp_net.name
    temp_net.close()

    try:
        subprocess.check_call([
            netconvert_bin,
            "-n", nodefile,
            "-e", edgefile,
            "-o", temp_net_path,
            "--no-turnarounds",
            "--junctions.limit-turn-speed", str(CORNER_SPEED_LIMIT),
        ])

        # 3. Parse nodefile for dead_end border nodes and edgefile for TAZ mappings
        tree_nod = ET.parse(nodefile)
        root_nod = tree_nod.getroot()
        border_nodes: Dict[str, Tuple[float, float]] = {}
        for node in root_nod.findall("node"):
            nid = node.get("id")
            x = float(node.get("x"))
            y = float(node.get("y"))
            if node.get("type") == "dead_end":
                border_nodes[nid] = (x, y)

        # Apply dead_end node modifications and atomically replace gen_netfile
        tree_net = ET.parse(temp_net_path)
        root_net = tree_net.getroot()
        for junction in root_net.findall("junction"):
            jid = junction.get("id")
            if jid in border_nodes:
                junction.set("type", "dead_end")
        _atomic_write_tree(gen_netfile, tree_net)
    finally:
        if os.path.exists(temp_net_path):
            try:
                os.remove(temp_net_path)
            except OSError:
                pass

    # 4. Generate and atomically write generated.add.xml (TAZs)
    tree_e = ET.parse(edgefile)
    root_e = tree_e.getroot()
    taz_sources: List[str] = []
    taz_sinks: List[str] = []
    taz_point: Dict[str, str] = {}
    NT: Dict[int, Tuple[float, float]] = {}
    for edge in root_e.findall("edge"):
        eid = edge.get("id")
        from_node = edge.get("from")
        to_node = edge.get("to")
        if from_node in border_nodes:
            taz_sources.append(eid)
            taz_point[eid] = from_node
        if to_node in border_nodes:
            taz_sinks.append(eid)
            taz_point[eid] = to_node

    add_content: List[str] = ["<tazs>"]
    for idx, i in enumerate(sorted([int(e.split("E")[1]) for e in taz_sinks])):
        x, y = border_nodes[taz_point[f"E{i}"]]
        NT[idx] = (x, y)
        shp = " ".join([f"{x+dx},{y+dy}" for dx, dy in [[0, -10], [-10, 0], [0, 10], [10, 0], [0, -10]]])
        add_content.append(f'  <taz id="taz_{idx}" shape="{shp}" color="blue">')
        add_content.append(f'    <tazSource id="E{i}" weight="1.0"/>')
        add_content.append(f'    <tazSink id="E{i}" weight="1.0"/>')
        add_content.append(f'    <tazSource id="-E{i}" weight="1.0"/>')
        add_content.append(f'    <tazSink id="-E{i}" weight="1.0"/>')
        add_content.append("  </taz>")
    add_content.append("</tazs>\n")
    _atomic_write_text(os.path.join(target_dir, "generated.add.xml"), "\n".join(add_content))

    # 5. Generate and atomically write generated.rou.xml (traffic flows)
    rou_content: List[str] = ["<routes>"]
    rou_content.append(
        f'  <vType id="{VTYPE_ID}" vClass="passenger" '
        f'speedFactor="normc({SPEED_FACTOR_MEAN:.2f},{SPEED_FACTOR_DEV:.2f},'
        f'{SPEED_FACTOR_MIN:.2f},{SPEED_FACTOR_MAX:.2f})"/>'
    )
    CalcP_GEN(dens)
    global P_GEN
    taz_len = len(taz_sinks)
    for i in range(taz_len):
        for j in range(taz_len):
            if i == j:
                continue
            P_GEN = CalcP_GEN(dens) if dens > 0 else CalcP_GEN(_gen_rng.randint(1, 20))
            prob = P_GEN / (taz_len - 1) if (taz_len - 1) > 0 else 0.0
            rou_content.append(
                # departSpeed="max" enters each vehicle at the fastest speed that is
                # safe behind its leader, instead of SUMO's default of 0.
                #
                # Starting every vehicle at rest throttles the boundary: an entering
                # vehicle occupies the insertion point until it accelerates away, so
                # the edge admits far less than the demand asks for. Measured at
                # requested density 50, 47 % of the demanded vehicles were never
                # inserted, and the realised in-range count stopped tracking the
                # request and then went NON-MONOTONIC -- request 30 gave 144.2
                # vehicles, request 40 gave 132.0. A density axis that is not
                # monotone in the requested density cannot be the x-axis of the
                # results table.
                f'  <flow id="F{i}_{j}" begin="0.00" departLane="random" departSpeed="max" '
                f'type="{VTYPE_ID}" fromTaz="taz_{i}" toTaz="taz_{j}" end="{flow_end}" probability="{prob}"/>'
            )
    rou_content.append("</routes>\n")
    _atomic_write_text(os.path.join(target_dir, "generated.rou.xml"), "\n".join(rou_content))

    # 6. Generate and atomically write rsu.poi.xml
    poi_content: List[str] = ["<additional>"]
    for node in root_nod.findall("node"):
        if node.get("type") == "traffic_light":
            nid = node.get("id")
            x = float(node.get("x"))
            y = float(node.get("y"))
            poi_content.append(f'  <poi id="{nid}" x="{x}" y="{y}" type="RSU" color="1,0,0"/>')
    poi_content.append("</additional>\n")
    _atomic_write_text(os.path.join(target_dir, "rsu.poi.xml"), "\n".join(poi_content))

    # 7. Generate and atomically write generated.sumocfg
    cfg_content = f"""<?xml version="1.0" encoding="UTF-8"?>

<!-- generated for SUMO simulation -->

<sumoConfiguration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

    <input>
        <net-file value="generated.net.xml"/>
        <route-files value="generated.rou.xml"/>
        <additional-files value="generated.add.xml, rsu.poi.xml"/>
    </input>

    <time>
        <begin value="0"/>
        <end value="360000"/>
        <!-- Resolution must be <= the minimum action update interval (Delta = 0.1 s). -->
        <step-length value="{STEP_LENGTH}"/>
    </time>

</sumoConfiguration>
"""
    _atomic_write_text(os.path.join(target_dir, "generated.sumocfg"), cfg_content)
    # The signature records what was ACTUALLY written, which is this run's demand
    # and horizon, not whatever the module globals happen to hold.
    _write_generation_signature(target_dir, density=dens, flow_end_s=flow_end)


def make_sumo_files(force_regenerate: bool = False, num_blocks: Optional[int] = None,
                    base_path: Optional[str] = None,
                    density: Optional[float] = None,
                    flow_end_s: Optional[float] = None) -> str:
    """Generate the SUMO file set into `base_path`, serialised against other processes.

    Training runs in parallel across GPUs all regenerate into the same directory,
    so the check-and-generate section is held under an exclusive lock. The cheap
    "already valid for these parameters" test runs once before taking the lock to
    keep the common case lock-free, and again inside it because another process may
    have generated exactly what we needed while we waited.

    The directory is resolved ONCE here and the resolved string is handed to all
    four callees, so the lock, both cache checks and the writer cannot disagree
    about where the scenario is. Returns it, so a caller can point `libsumo` at
    the same place instead of re-deriving it from the module global -- which is
    how `AoiV2IEnv` could read a `generated.sumocfg` from one directory while it
    had asked for a scenario in another.

    `base_path=None` is the process default (`PAPER4_SUMO_DIR` or the package
    directory) and is byte-for-byte the previous behaviour. `density=None` and
    `flow_end_s=None` behave the same way: they fall back to the module globals,
    so an existing caller that names neither is unaffected. A caller that DOES
    name them gets a scenario built from its own values without those values
    being written anywhere another run can read them -- see
    `current_generation_signature` for what that cost us.
    """
    target_dir = resolve_base_path(base_path)
    if (
        not force_regenerate
        and are_sumo_files_valid(target_dir)
        and generation_signature_matches(
            target_dir, num_blocks=num_blocks, density=density, flow_end_s=flow_end_s
        )
    ):
        return target_dir
    with _generation_lock(target_dir):
        _make_sumo_files_impl(force_regenerate=force_regenerate, num_blocks=num_blocks,
                              base_path=target_dir, density=density, flow_end_s=flow_end_s)
    return target_dir
