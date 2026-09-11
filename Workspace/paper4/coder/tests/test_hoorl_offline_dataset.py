# tests/test_hoorl_offline_dataset.py
# ============================================================================
# The offline dataset's contract with everything that consumes it.
#
# ---------------------------------------------------------------------------
# WHAT THIS FILE IS FOR
# ---------------------------------------------------------------------------
# `src/hoorl_wiring.py` refuses to construct HOORL without an offline dataset,
# which makes the dataset a hard dependency of the pipeline rather than an
# artefact somebody produces once. A hard dependency needs its contract pinned,
# and the contract has four parts:
#
#   * the SHAPE contract -- the batch a model draws from the dataset is
#     indistinguishable from the batch it draws from the replay buffer, for every
#     key the model actually reads;
#   * the VALIDITY contract -- a dataset collected under a different observation
#     normalisation is refused rather than silently used;
#   * the HONESTY contract -- the synthetic fixture can never be mistaken for
#     collected data, and no path that reports numbers can consume it by
#     accident;
#   * the NO-INVENTION contract -- a transition whose behaviour probability is
#     unknown is rejected, not defaulted. `log_prob = 0.0` is the assertion that
#     the behaviour policy chose that action with probability one, which is a
#     claim about the data, not a placeholder.
#
# Every test here runs in milliseconds and starts no SUMO episode. The question
# "does a real run enter the offline stage" belongs to
# `etc/scripts/verify_hoorl_offline_wiring.py`, which costs a live episode.
# ============================================================================

from __future__ import annotations

import json
import math
import os

from typing import Any, List

import numpy as np
import pytest
import torch

from src.hoorl_offline import (
    ARRAY_KEYS,
    FixedPeriodBehaviourPolicy,
    OfflineDataset,
    dataset_from_buffer,
    observation_constants,
)
from src.hoorl_offline_synthetic import (
    SYNTHETIC_POLICY_KIND,
    assert_not_synthetic,
    build_synthetic_dataset,
    is_synthetic,
    write_synthetic_dataset,
)
from src.rl_interface import ActionDecoder, RetrospectiveReplayBuffer, STATE_DIM

BATCH = 32


@pytest.fixture(scope="module", autouse=True)
def _scenario_exists():
    """Generate a SUMO network before anything reads the observation normalisers.

    `V_MAX_OBS`, `E_REF` and `DELTA_MAX` are computed from the network on disk
    when `src.rl_interface` is imported and refreshed by `prepare_scenario`.
    Without a network they are the import-time fallbacks, which
    `observation_constants` now refuses to report rather than let them be written
    into a dataset that would claim a normalisation nothing ever used. Every test
    in this module reads those constants, so the scenario is a precondition of
    the module rather than of one test.
    """
    from src.hot_swap_trainer import prepare_scenario

    prepare_scenario(density=20.0, max_steps=200, warmup_steps=100, seed=2001)


# ---------------------------------------------------------------------------
# Shape contract
# ---------------------------------------------------------------------------
def _buffer_like_the_trainer_fills_it(n: int = 64) -> RetrospectiveReplayBuffer:
    """A buffer holding exactly the keys `run_hot_swap_training` pushes.

    Transcribed from the `push_transition` call in `hot_swap_trainer.py`. If that
    call site gains or loses a column this fixture goes stale, which is why the
    test below compares against it rather than asserting a literal key list: the
    comparison fails when the two diverge, and a literal would not.
    """
    buf = RetrospectiveReplayBuffer(capacity=n * 2, gamma=0.99)
    rng = np.random.default_rng(7)
    for i in range(n):
        buf.push(
            state=rng.uniform(-1, 1, STATE_DIM).astype(np.float32),
            action=rng.uniform(0, 1, 3).astype(np.float32),
            reward=-float(rng.uniform(0, 1)),
            next_state=rng.uniform(-1, 1, STATE_DIM).astype(np.float32),
            done=bool(i % 20 == 0),
            delta_t=float(rng.uniform(0.5, 10.0)),
            action_idx=int(i % 4),
            behaviour_log_prob=-math.log(4.0),
        )
    return buf


def test_dataset_batch_matches_the_buffer_batch_key_for_key():
    """Same keys, same shapes, same dtypes for every column both sides carry.

    The offline and the online stage of HOORL consume ONE batch contract. If they
    did not, the model would take a different code path in each stage -- notably
    `_discrete_index`, which prefers a verbatim `action_idx` and otherwise
    re-derives one from the continuous action -- and the offline stage would be
    optimising a different objective from the online one while every number
    looked healthy.
    """
    dataset = build_synthetic_dataset(n_transitions=256)
    buffer = _buffer_like_the_trainer_fills_it()

    d_batch = dataset.sample(BATCH)
    b_batch = buffer.sample(BATCH)

    shared = set(d_batch) & set(b_batch)
    assert set(d_batch) <= set(b_batch), (
        f"the dataset emits {set(d_batch) - set(b_batch)}, which the buffer does "
        "not. A model would see a column offline that never appears online."
    )
    for key in sorted(shared):
        assert d_batch[key].shape[1:] == b_batch[key].shape[1:], (
            f"{key}: dataset {tuple(d_batch[key].shape)}, buffer {tuple(b_batch[key].shape)}"
        )
        assert d_batch[key].dtype == b_batch[key].dtype, (
            f"{key}: dataset {d_batch[key].dtype}, buffer {b_batch[key].dtype}"
        )
        assert d_batch[key].shape[0] == BATCH


def test_hoorl_reads_no_key_the_offline_batch_lacks():
    """The keys HOORL touches must all exist in an offline batch.

    The buffer carries five columns the dataset does not -- `reward_terms` and
    the four neighbourhood tensors -- because the trainer pushes them and the
    collection does not store them. That difference is harmless if and only if
    HOORL never reads them, and "harmless if and only if" is a thing to check
    rather than to believe. The batch is wrapped in a dict that records every
    lookup, so this measures what the model DID read, not what its source
    appears to read.
    """
    from src.baselines.hoorl import HOORL

    class RecordingBatch(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.touched = set()

        def __getitem__(self, key):
            self.touched.add(key)
            return super().__getitem__(key)

        def get(self, key, default=None):
            self.touched.add(key)
            return super().get(key, default)

        def __contains__(self, key):
            self.touched.add(key)
            return super().__contains__(key)

    dataset = build_synthetic_dataset(n_transitions=256)
    available = set(dataset.sample(BATCH).keys())

    model = HOORL(state_dim=STATE_DIM, hidden_dim=64, offline_algorithm="iql")
    model.set_phase("offline")
    offline_batch = RecordingBatch(dataset.sample(BATCH))
    model.offline_update(offline_batch)

    model.finish_offline_phase()
    online_batch = RecordingBatch(dataset.sample(BATCH))
    model.online_update(online_batch)

    for batch, stage in ((offline_batch, "offline"), (online_batch, "online")):
        # Non-vacuity. If a future refactor copied the batch into a plain dict
        # before using it, `touched` would be empty and the subset assertion
        # below would pass while measuring nothing. Measured on 2026-09-06, both
        # stages read eight keys: state, action, action_idx, reward, next_state,
        # done, delta_t and behaviour_log_prob.
        assert len(batch.touched) >= 6, (
            f"the {stage} update recorded only {sorted(batch.touched)}, so this "
            "test is no longer observing what the model reads"
        )
        unavailable = batch.touched - available
        assert not unavailable, (
            f"during the {stage} update HOORL read {sorted(unavailable)}, which an "
            "offline batch does not carry. Either the collection must store those "
            "columns or the model must stop reading them; a silent fallback makes "
            "the two stages optimise different objectives."
        )


def test_discount_column_tracks_delta_t_and_gamma():
    """`discount == gamma ** delta_t`, elementwise, and it is not constant.

    The SMDP discount is the one column the dataset computes rather than stores,
    so it is the one that can silently disagree with the buffer's.
    """
    dataset = build_synthetic_dataset(n_transitions=256, gamma=0.97)
    batch = dataset.sample(BATCH)
    expected = torch.pow(torch.tensor(0.97), batch["delta_t"])
    assert torch.allclose(batch["discount"], expected, atol=1e-6)
    assert batch["discount"].std().item() > 0.0, (
        "the discount column is constant, so a consumer that ignored delta_t "
        "entirely would pass every test in this file"
    )


# ---------------------------------------------------------------------------
# Validity contract
# ---------------------------------------------------------------------------
def test_observation_constants_cover_every_normaliser_in_the_vectoriser():
    """Every constant that changes what an observation MEANS must be recorded.

    A constant that the vectoriser divides by but the metadata omits is a way for
    the dataset to go stale without `verify_compatibility` noticing, which is the
    single failure this metadata exists to prevent. `a_max`, `queue_max` and
    `rsu_range` were omitted for exactly that reason and are named here so the
    omission cannot recur silently.
    """
    consts = observation_constants()
    required = {
        "N_ACTIVE_MAX_OBS", "V_MAX_OBS", "E_REF", "DELTA_MAX", "DELTA_MIN",
        "RSU_RANGE", "A_MAX", "QUEUE_MAX", "PHASE_REMAINING_REF_S",
    }
    missing = required - set(consts)
    assert not missing, f"observation_constants() does not record {sorted(missing)}"
    for key, value in consts.items():
        assert isinstance(value, float), f"{key} is {type(value)}, not a float"
        assert not math.isnan(value), f"{key} is NaN, so no comparison against it can fail"


def test_phase_remaining_reference_is_measured_not_mirrored():
    """The feature-11 divisor is read out of the vectoriser, not copied beside it.

    It WAS a literal inside `vectorize_from_dict` with no module constant to
    read, so `observation_constants` recovered it by inverting the vectoriser's
    answer. It is `PHASE_REMAINING_REF_S` as of 2026-09-06 and is read directly.
    """
    from src.rl_interface import PHASE_REMAINING_REF_S, StateVectorizer

    ref = observation_constants()["PHASE_REMAINING_REF_S"]
    assert ref == pytest.approx(PHASE_REMAINING_REF_S)
    # Still driven THROUGH the vectoriser rather than only compared against the
    # constant: the claim is that the recorded number is the one feature [11] is
    # divided by, and reading one global twice would not establish that.
    vec = StateVectorizer().vectorize_from_dict(
        {"tls_features": {"state": "g", "time_to_switch": ref / 2.0}}
    )
    assert vec[11] == pytest.approx(0.5, abs=1e-6)


def test_a_dataset_from_other_constants_is_refused():
    """`verify_compatibility` must raise, not warn, on a changed normaliser."""
    dataset = build_synthetic_dataset(n_transitions=64)
    dataset.metadata["observation_constants"]["N_ACTIVE_MAX_OBS"] = 100.0
    with pytest.raises(ValueError, match="different observation definition"):
        dataset.verify_compatibility(strict=True)
    problems = dataset.verify_compatibility(strict=False)
    assert any("N_ACTIVE_MAX_OBS" in p for p in problems)


def test_a_missing_constant_is_a_problem_not_a_pass():
    """An absent key must not read as agreement."""
    dataset = build_synthetic_dataset(n_transitions=64)
    dataset.metadata["observation_constants"].pop("E_REF")
    problems = dataset.verify_compatibility(strict=False)
    assert any("E_REF" in p and "not recorded" in p for p in problems)


def test_constants_read_before_any_scenario_are_refused(monkeypatch, tmp_path):
    """The import-time fallbacks must never be written into a dataset.

    Read before `prepare_scenario`, V_MAX_OBS is 13.32 -- the `default_speed` of
    `get_sumo_max_edge_speed` when no `generated.net.xml` exists -- against about
    15.9 afterwards. Stored, that is indistinguishable from a constant a real
    scenario produced, and it surfaces later as a 17 % mismatch that reads like a
    changed observation definition rather than as a file written too early.
    """
    from src.hoorl_offline import ScenarioNotGenerated, scenario_provenance
    import src.rl_interface as rli

    empty = str(tmp_path / "no_scenario")
    os.makedirs(empty, exist_ok=True)
    monkeypatch.setattr(rli, "scenario_dir", lambda base_path=None: empty)

    assert scenario_provenance()["network_present"] is False
    with pytest.raises(ScenarioNotGenerated, match="fallback"):
        observation_constants()
    # The escape hatch exists, is explicit, and returns the fallbacks it names.
    assert observation_constants(require_scenario=False)["V_MAX_OBS"] > 0.0


def test_a_dataset_recorded_before_its_scenario_is_refused():
    """`scenario_provenance.network_present == False` voids the dataset."""
    dataset = build_synthetic_dataset(n_transitions=32)
    dataset.metadata["scenario_provenance"] = {
        "scenario_dir": "/nowhere", "network_path": "/nowhere/generated.net.xml",
        "network_present": False,
    }
    problems = dataset.verify_compatibility(strict=False)
    assert any("recorded before any SUMO network existed" in p for p in problems)


def test_a_seed_sized_difference_in_the_speed_constants_is_tolerated():
    """0.756 % between two seeds must not void a dataset; 25 % must.

    The tolerance is not a convenience. `V_MAX_OBS` and `E_REF` are drawn from
    the generated road network and were measured over 90 scenarios to depend only
    on the seed, spanning 0.756 %. `measure_normalisation_drift_effect.py` then
    measured what a drift of that size does to the state distribution: 0.035 of
    the split-half sampling floor, i.e. an order of magnitude below the noise a
    finite sample already shows. A drift only becomes detectable near 25 %.
    """
    from src.hoorl_offline import SCENARIO_CONSTANT_REL_TOL

    assert SCENARIO_CONSTANT_REL_TOL >= 0.00756, (
        "the tolerance is tighter than the measured spread between seeds, so a "
        "dataset collected on one seed would be refused against another"
    )
    dataset = build_synthetic_dataset(n_transitions=32)
    live = observation_constants()

    dataset.metadata["observation_constants"]["V_MAX_OBS"] = live["V_MAX_OBS"] * 1.00756
    assert dataset.verify_compatibility(strict=False) == []

    dataset.metadata["observation_constants"]["V_MAX_OBS"] = live["V_MAX_OBS"] * 1.25
    problems = dataset.verify_compatibility(strict=False)
    assert any("V_MAX_OBS" in p for p in problems)


def test_a_code_constant_is_still_compared_exactly():
    """The tolerance applies to the scenario draws only, never to the code ones."""
    dataset = build_synthetic_dataset(n_transitions=32)
    live = observation_constants()
    dataset.metadata["observation_constants"]["N_ACTIVE_MAX_OBS"] = \
        live["N_ACTIVE_MAX_OBS"] * 1.001
    problems = dataset.verify_compatibility(strict=False)
    assert any("N_ACTIVE_MAX_OBS" in p for p in problems), (
        "a 0.1 % change in a code-level constant must still void the dataset"
    )


def test_round_trip_through_disk_preserves_columns_and_metadata(tmp_path):
    npz = os.path.join(str(tmp_path), "syn", "hoorl_offline.npz")
    npz_path, meta_path = write_synthetic_dataset(npz, n_transitions=128)
    assert os.path.exists(npz_path) and os.path.exists(meta_path)

    loaded = OfflineDataset.load(npz_path, gamma=0.99)
    original = build_synthetic_dataset(n_transitions=128)
    assert len(loaded) == len(original)
    for key in ARRAY_KEYS:
        np.testing.assert_allclose(loaded.arrays[key], original.arrays[key], rtol=0, atol=0)
    with open(meta_path) as fh:
        assert json.load(fh)["state_dim"] == STATE_DIM
    loaded.verify_compatibility(strict=True)


def test_a_dataset_without_metadata_is_refused(tmp_path):
    """An npz with no sibling metadata is not a usable offline dataset."""
    npz = os.path.join(str(tmp_path), "orphan.npz")
    build_synthetic_dataset(n_transitions=32).save(npz)
    os.remove(os.path.splitext(npz)[0] + ".meta.json")
    with pytest.raises(FileNotFoundError, match="no sibling metadata"):
        OfflineDataset.load(npz)


# ---------------------------------------------------------------------------
# Honesty contract
# ---------------------------------------------------------------------------
def test_the_fixture_declares_itself_synthetic():
    dataset = build_synthetic_dataset(n_transitions=32)
    assert dataset.metadata["synthetic"] is True
    assert dataset.metadata["not_for_results"] is True
    assert dataset.metadata["behaviour_policy"]["kind"] == SYNTHETIC_POLICY_KIND
    assert is_synthetic(dataset)
    with pytest.raises(ValueError, match="SYNTHETIC"):
        assert_not_synthetic(dataset, context="unit test")


def test_a_collected_dataset_is_not_flagged_synthetic():
    """The detector must key on the metadata, not on anything a real run sets.

    Built from a hand-made buffer with a real behaviour policy's metadata, i.e.
    the shape a collection produces, so a false positive here would mean a real
    collection could be rejected as a fixture.
    """
    buffer = _buffer_like_the_trainer_fills_it(n=16)
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=2.236, num_channels=4, p_min=0.0, p_max=1.0, delta_log_halfwidth=1.498,
    )
    metadata = {
        "state_dim": STATE_DIM,
        "observation_constants": observation_constants(),
        "behaviour_policy": {"kind": "fixed_period_uniform_channel_power",
                             "delta_fixed": policy.delta_fixed},
    }
    dataset = dataset_from_buffer(buffer, metadata)
    assert not is_synthetic(dataset)
    assert_not_synthetic(dataset)  # must not raise
    dataset.verify_compatibility(strict=True)


# ---------------------------------------------------------------------------
# No-invention contract
# ---------------------------------------------------------------------------
def test_a_transition_without_a_behaviour_log_prob_is_rejected():
    """Missing is not zero. `log_prob == 0` means probability one.

    Filling an unknown behaviour probability with 0.0 does not mark it unknown;
    it asserts that the logging policy chose that action deterministically, which
    makes every importance ratio formed from it wrong by the factor the ratio was
    supposed to correct for. The dataset must refuse the transition instead.
    """
    buffer = RetrospectiveReplayBuffer(capacity=8, gamma=0.99)
    buffer.push(
        state=np.zeros(STATE_DIM, dtype=np.float32),
        action=np.zeros(3, dtype=np.float32),
        reward=-0.5,
        next_state=np.zeros(STATE_DIM, dtype=np.float32),
        done=False,
        delta_t=1.0,
        action_idx=2,
    )
    with pytest.raises(ValueError, match="behaviour_log_prob"):
        dataset_from_buffer(buffer, {"state_dim": STATE_DIM,
                                     "observation_constants": observation_constants()})


def test_action_index_zero_is_kept_and_a_missing_one_is_rejected():
    """Channel 0 is a real channel; `or 0` treated it as absent.

    `int(item.get("action_idx") or 0)` maps both a missing index and a genuine
    index of 0 to 0, so a whole dataset of missing indices reads as "everything
    used channel 0" -- which is a claim, and a false one.
    """
    buffer = RetrospectiveReplayBuffer(capacity=8, gamma=0.99)
    buffer.push(
        state=np.zeros(STATE_DIM, dtype=np.float32),
        action=np.zeros(3, dtype=np.float32),
        reward=-0.5,
        next_state=np.zeros(STATE_DIM, dtype=np.float32),
        done=False,
        delta_t=1.0,
        action_idx=0,
        behaviour_log_prob=-math.log(4.0),
    )
    meta = {"state_dim": STATE_DIM, "observation_constants": observation_constants()}
    dataset = dataset_from_buffer(buffer, meta)
    assert int(dataset.arrays["action_idx"][0]) == 0

    buffer2 = RetrospectiveReplayBuffer(capacity=8, gamma=0.99)
    buffer2.push(
        state=np.zeros(STATE_DIM, dtype=np.float32),
        action=np.zeros(3, dtype=np.float32),
        reward=-0.5,
        next_state=np.zeros(STATE_DIM, dtype=np.float32),
        done=False,
        delta_t=1.0,
        behaviour_log_prob=-math.log(4.0),
    )
    with pytest.raises(ValueError, match="action_idx"):
        dataset_from_buffer(buffer2, meta)


# ---------------------------------------------------------------------------
# Behaviour policy
# ---------------------------------------------------------------------------
def test_a_degenerate_delta_has_no_density_and_says_so():
    """Zero jitter is a point mass: no finite log density exists for Delta."""
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=2.0, num_channels=4, p_min=0.0, p_max=1.0, delta_log_halfwidth=0.0,
    )
    assert policy.delta_component_defined is False
    decoder = ActionDecoder(num_channels=4)
    assert policy.delta_band(decoder) == (2.0, 2.0)
    assert policy.log_prob() == pytest.approx(-math.log(4.0))


def test_a_jittered_delta_band_is_clipped_to_the_decoder_range():
    """The band can never leave the action space the decoder can express."""
    decoder = ActionDecoder(num_channels=4)
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=2.236, num_channels=4, p_min=0.0, p_max=1.0, delta_log_halfwidth=10.0,
    )
    lo, hi = policy.delta_band(decoder)
    assert lo >= decoder.delta_min - 1e-9
    assert hi <= decoder.delta_max + 1e-9
    assert policy.delta_component_defined is True


def test_the_recommended_band_is_expressible_and_round_trips():
    """[0.5, 10] s as (delta_fixed, delta_jitter), to the precision it is stored at.

    The band chosen from `results/hoorl_offline/delta_band_error_curve_transmitted.csv`
    has to survive the existing two-parameter parametrisation, since that is what
    the metadata records and what a re-collection would be driven from.
    """
    lo, hi = 0.5, 10.0
    centre = math.sqrt(lo * hi)
    jitter = 0.5 * math.log(hi / lo)
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=centre, num_channels=4, p_min=0.0, p_max=1.0, delta_log_halfwidth=jitter,
    )
    band_lo, band_hi = policy.delta_band(ActionDecoder(num_channels=4))
    assert band_lo == pytest.approx(lo, rel=1e-9)
    assert band_hi == pytest.approx(hi, rel=1e-9)


def test_sampled_deltas_stay_inside_the_band():
    decoder = ActionDecoder(num_channels=4)
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=math.sqrt(5.0), num_channels=4,
        p_min=float(decoder.p_min), p_max=float(decoder.p_max),
        delta_log_halfwidth=0.5 * math.log(20.0),
    )
    rng = np.random.default_rng(3)
    lo, hi = policy.delta_band(decoder)
    for _ in range(500):
        (delta, ch, power), idx, logp = policy.sample(rng, decoder)
        assert lo - 1e-9 <= delta <= hi + 1e-9
        assert 0 <= ch < 4 and ch == idx
        assert decoder.p_min <= power <= decoder.p_max
        assert logp == pytest.approx(-math.log(4.0))


# ---------------------------------------------------------------------------
# Raw storage: the normalisation is reversible and it is the SAME normalisation
# ---------------------------------------------------------------------------
def _collect_tiny(tmp_path, monkeypatch):
    """One very small real collection, with the vectoriser instrumented.

    Costs three short SUMO episodes. Shared by the two tests below because both
    need the same artefact and collecting it twice doubles the cost for nothing.
    """
    import src.rl_interface as rli
    from src.hoorl_offline import collect_offline_dataset

    produced: List[Any] = []
    original = rli.StateVectorizer.vectorize_from_dict

    def recording(self, state_dict, rsu_pos=(0.0, 0.0)):
        vec = original(self, state_dict, rsu_pos)
        produced.append(np.asarray(vec, dtype=np.float32).copy())
        return vec

    monkeypatch.setattr(rli.StateVectorizer, "vectorize_from_dict", recording)
    # TWO cells, not one, and that is the whole design of this fixture.
    #
    # With a single cell `per_cell[0]` IS the live constant set, so a
    # reconstruction that ignored `cell_index` and used the live constants would
    # agree exactly and the join would go unchecked. The check below states that
    # using live constants leaves the other cells wrong by about 3.2e-3 -- a
    # single-cell fixture cannot produce that error, so the check would have been
    # asserting a property it could not have observed failing.
    #
    # Two densities give two roads and therefore two values of `V_MAX_OBS` and
    # `E_REF`. `test_the_cell_index_join_is_load_bearing` then removes the join
    # and requires the failure to appear.
    dataset = collect_offline_dataset(
        delta_band_center=math.sqrt(5.0), delta_log_halfwidth=0.5 * math.log(20.0),
        densities=[20.0, 25.0], seeds=[2001], steps_per_episode=120,
        warmup_steps=200, road_seed=42, n_cells=2,
        sumo_dir=str(tmp_path / "sumo"), num_threads=1,
    )
    return dataset, produced


@pytest.mark.slow
def test_the_offline_states_come_from_the_one_vectoriser(tmp_path, monkeypatch):
    """Every stored state is a vector `StateVectorizer` produced. Shown by running.

    THE CLAIM THIS REPLACES. "The collector reuses `AoiV2IEnv.step`, so it must
    be using the same normalisation" is a claim about code, and this project has
    had several such claims turn out false. This one is measured: the vectoriser
    is wrapped, a real collection is run, and every row the dataset stored is
    matched against the set of vectors the wrapper saw.

    WHY IT STAYS AFTER PASSING ONCE. Because the failure it guards against is a
    LATER one. Nothing today builds an observation outside `AoiV2IEnv`, but a
    shortcut added to the offline path -- re-vectorising a stored raw row, say,
    to avoid a SUMO step -- would diverge silently the moment the two
    normalisation sites stopped agreeing. The same defect has already occurred
    in this project's history, where a second vectorisation path fed a model 15
    constant dimensions out of 18.
    """
    dataset, produced = _collect_tiny(tmp_path, monkeypatch)
    assert len(dataset) > 0, "the collection produced nothing to check"
    assert produced, "the vectoriser was never called; the wrapper is not in the path"

    seen = {v.tobytes() for v in produced}
    states = dataset.arrays["state"]
    missing = sum(1 for row in states
                  if np.asarray(row, dtype=np.float32).tobytes() not in seen)
    assert missing == 0, (
        f"{missing} of {len(states)} stored states were never produced by "
        "StateVectorizer.vectorize_from_dict, so the offline path builds "
        "observations of its own"
    )


@pytest.mark.slow
def test_normalising_the_raw_columns_reproduces_the_stored_vector(tmp_path, monkeypatch):
    """The raw columns rebuild the stored vector, THROUGH THE PRODUCTION FUNCTION.

    This test used to carry its own copy of the reconstruction arithmetic. That
    made it a check on a formula written in the test file, not on the code a run
    would execute, and the two could drift apart the moment a bound moved: the
    test would keep passing against its own copy while the shipped path did
    something else. `src.rl_interface.renormalise_states` is now the one
    implementation, `OfflineDataset.renormalised_states` and
    `hoorl_offline_stats.states_from_npz` both call it, and this drives the same
    entry point.

    Rebuilding with the constants the data was COLLECTED under has to reproduce
    the stored vector exactly. That is what makes the raw columns usable for
    their actual purpose, which is rebuilding under DIFFERENT constants: if the
    identity case does not reproduce, nothing about the changed case can be
    trusted either.
    """
    dataset, _ = _collect_tiny(tmp_path, monkeypatch)
    assert "state_raw" in dataset.optional_columns
    assert "cell_index" in dataset.optional_columns

    report = dataset.verify_raw_columns()
    assert report["matches"], (
        f"worst absolute error {report['worst_abs_error']:.3e} at feature "
        f"{report['worst_feature']}; per feature {report['per_feature_abs_error']}"
    )

    # The five features NOT rebuilt are the ones with no normalising constant:
    # the signal one-hot, the clipped mean CBR and the heading cosine. Named here
    # so that a feature quietly dropping out of `RENORMALISABLE_FEATURES` shows up.
    from src.rl_interface import RENORMALISABLE_FEATURES

    rebuilt = {j for j, _ in RENORMALISABLE_FEATURES}
    assert rebuilt | {8, 9, 10, 14, 16} == set(range(21))

    # And the point of storing raw at all: a bound can move on READ. Raising the
    # stop-line bound must remove the clipping without touching a feature that
    # does not use it.
    from src.rl_interface import observation_constants_live

    target = observation_constants_live()
    target["RSU_RANGE"] = target["RSU_RANGE"] * 3.0
    widened = dataset.renormalised_states(target)
    stored = dataset.arrays["state"]
    assert (widened[:, 12] >= 1.0).mean() <= (stored[:, 12] >= 1.0).mean()
    np.testing.assert_allclose(widened[:, [8, 9, 10, 14, 16]],
                               stored[:, [8, 9, 10, 14, 16]], atol=0)


@pytest.mark.slow
def test_a_constant_with_a_second_role_is_not_re_derived(tmp_path, monkeypatch):
    """`E_REF` must keep its collection value even when the live one differs.

    It normalises feature [0] and it is also the reward's error term. Re-deriving
    [0] under a new value while `reward` keeps the number computed under the old
    one leaves an offline learner reading a pair that describes two different
    scales, and the pair is exactly what it learns from. So the feature stays put
    while everything with a single role moves.

    The property is asserted on the FEATURE, not on the report, because the
    report saying "kept" and the array moving anyway is the failure that actually
    happened: the first version substituted the single value recorded in the
    file's metadata, and a collection that spans several roads was normalised
    per cell, so every other cell came back shifted.
    """
    from src.rl_interface import RENORMALISABLE_FEATURES, constants_safe_to_rescale

    dataset, _ = _collect_tiny(tmp_path, monkeypatch)
    dual = {n for _j, n in RENORMALISABLE_FEATURES if n} - set(constants_safe_to_rescale())
    assert "E_REF" in dual, (
        "E_REF is no longer classified as carrying a second role, so this test "
        "guards nothing. Check CONSTANT_ROLES.")

    # Move one single-role constant and one dual-role constant at once, so the
    # test distinguishes "nothing was renormalised" from "the right thing was".
    stored = dict(dataset.metadata["observation_constants"])
    before = np.array(dataset.arrays["state"])
    import src.rl_interface as rli

    original = rli.observation_constants_live

    def _moved():
        c = dict(original())
        c["E_REF"] = float(stored["E_REF"]) * 1.005      # inside the scenario tolerance
        c["N_ACTIVE_MAX_OBS"] = float(stored["N_ACTIVE_MAX_OBS"]) * 1.5
        return c

    monkeypatch.setattr(rli, "observation_constants_live", _moved)
    report = dataset.reconcile_to_current_constants()

    assert "E_REF" in report["constants_kept_at_collection_value"]
    assert "N_ACTIVE_MAX_OBS" in report["constants_moved"]
    after = np.asarray(dataset.arrays["state"])
    # Feature [0] uses E_REF: unchanged but for float32 rounding.
    np.testing.assert_allclose(after[:, 0], before[:, 0], atol=1e-6)
    # Feature [13] uses N_ACTIVE_MAX_OBS: it must actually have moved, or the
    # first assertion is satisfied by nothing having happened at all.
    assert not np.allclose(after[:, 13], before[:, 13], atol=1e-6)
    # And the metadata records what the vectors now carry.
    assert dataset.metadata["observation_constants"]["E_REF"] == pytest.approx(
        float(stored["E_REF"]))


def test_a_terminal_row_with_no_successor_keeps_its_stored_vector():
    """A transition whose `next_state_raw` is entirely NaN must not be rebuilt.

    This is the defect that reached HOORL. A terminal transition has no successor
    to observe, so all nineteen raw fields are NaN and the stored `next_state` is
    the zero vector, which the Bellman target multiplies by (1 - done) anyway.
    Reconciliation rebuilt those rows from raw and produced NaN in every
    renormalised feature; the IQL losses were NaN from the first update, the
    actor's channel logits became NaN, and the rollout died inside
    `torch.multinomial`. On the real collection it was 3,639 of 128,223 rows,
    exactly those with `done` set.

    The distinction the guard draws is the point of the test: an ENTIRELY absent
    observation is substituted, while a row with one unexplained NaN is a fault
    that must be raised rather than filled in.
    """
    from src.rl_interface import (RAW_OBSERVATION_FIELDS,
                                  observation_constants_live, renormalise_states)

    live = observation_constants_live()
    stored = np.zeros((3, STATE_DIM), dtype=np.float32)
    stored[:, 8] = 1.0                      # a signal is showing, so [11]/[12] rebuild
    raw = np.zeros((3, len(RAW_OBSERVATION_FIELDS)), dtype=np.float64)
    raw[:, RAW_OBSERVATION_FIELDS.index("speed_mps")] = 8.0
    raw[2, :] = np.nan                      # the terminal row: nothing was observed

    out = renormalise_states(stored, raw, live)
    assert np.isfinite(out).all(), "a rebuilt batch may never contain NaN"
    np.testing.assert_array_equal(out[2], stored[2])
    assert out[0, 3] > 0.0, "the ordinary rows must still be rebuilt"


def test_one_unexplained_nan_is_raised_rather_than_filled():
    """A partially absent raw row is a fault, and silence would be the failure.

    The terminal-row guard is narrow on purpose. If it were written as "replace
    any NaN with the stored value" it would also absorb a collector that had
    started dropping a single field, and every load would then repair the damage
    and report nothing. `speed_mps` is used here because it has no no-signal
    convention: [8] and [9] of the raw vector legitimately carry NaN when there
    is no signal ahead, and those are handled where they are documented.
    """
    from src.rl_interface import (RAW_OBSERVATION_FIELDS,
                                  observation_constants_live, renormalise_states)

    live = observation_constants_live()
    stored = np.zeros((2, STATE_DIM), dtype=np.float32)
    raw = np.zeros((2, len(RAW_OBSERVATION_FIELDS)), dtype=np.float64)
    raw[1, RAW_OBSERVATION_FIELDS.index("speed_mps")] = np.nan

    with pytest.raises(ValueError, match="non-finite"):
        renormalise_states(stored, raw, live)


@pytest.mark.slow
def test_the_verification_covers_both_halves_of_a_transition(tmp_path, monkeypatch):
    """`verify_raw_columns` must check `next_state`, not only `state`.

    It checked `state` alone until 2026-09-07, and the half it skipped was the
    half that was broken. A verification that covers one of two symmetric columns
    reports on whichever one happens to be right, and it did: the report said the
    raw columns matched while the successors were being rebuilt as NaN.
    """
    dataset, _ = _collect_tiny(tmp_path, monkeypatch)
    report = dataset.verify_raw_columns()
    assert report["next_state"] is not None, "the successor half was not checked"
    assert report["next_state"]["matches"], report["next_state"]["worst_abs_error"]
    assert report["matches"]

    # And the combined verdict must actually depend on the successor half.
    dataset.arrays["next_state"] = dataset.arrays["next_state"] + 0.5
    broken = dataset.verify_raw_columns()
    assert broken["state_only_matches"], "the ego half was not the one damaged"
    assert not broken["next_state"]["matches"]
    assert not broken["matches"], (
        "damaging the successors left the overall verdict green, which is the "
        "condition this test exists to forbid")


@pytest.mark.slow
def test_the_cell_index_join_is_load_bearing(tmp_path, monkeypatch):
    """Dropping the `cell_index` join must break the reconstruction.

    A check that cannot fail says nothing, and this one very nearly could not.
    The reconstruction test above passed for weeks against a single-cell fixture,
    where the one cell's constants and the live constants are the same object and
    the join is therefore free to be wrong.

    So this asserts the failure directly. It rebuilds twice -- once joining each
    row to its own cell's constants, once with the live constants for every row,
    the mistake the join exists to prevent -- and requires the first to match and
    the SECOND NOT TO. If the second also matched, the two cells would have drawn
    the same road, the fixture would be back to being single-cell in effect, and
    the message says so rather than letting a green result stand.
    """
    from src.rl_interface import (observation_constants_live, renormalise_states,
                                  verify_renormalisation)

    dataset, _ = _collect_tiny(tmp_path, monkeypatch)
    cells = sorted({int(c) for c in dataset.arrays["cell_index"]})
    assert len(cells) >= 2, f"the fixture produced {len(cells)} cell(s), not two"

    per_row = dataset.per_row_constants()
    distinct = {round(float(v), 9) for v in per_row["V_MAX_OBS"]}
    assert len(distinct) >= 2, (
        f"both cells drew the same V_MAX_OBS ({distinct}), so this fixture cannot "
        "distinguish a correct join from a missing one. Separate the densities "
        "further, or pick cells whose roads differ."
    )

    correct = verify_renormalisation(
        dataset.arrays["state"], dataset.arrays["state_raw"], per_row)
    assert correct["matches"], (
        f"the joined reconstruction should be exact; worst {correct['worst_abs_error']:.3e} "
        f"at feature {correct['worst_feature']}"
    )

    # The same call with the join removed: one constant set for every row.
    naive = renormalise_states(dataset.arrays["state"], dataset.arrays["state_raw"],
                               observation_constants_live())
    worst = float(np.abs(naive.astype(np.float64)
                         - dataset.arrays["state"].astype(np.float64)).max())
    assert worst > 1e-5, (
        "ignoring cell_index reproduced the stored vectors exactly, so this test "
        "is not observing the join. That happens when every cell shares one set "
        "of scenario constants, and it means the reconstruction check above is "
        "passing for a reason unrelated to the join being correct."
    )
