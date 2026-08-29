#!/usr/bin/env python
"""
Verification harness for the three SB3-backed basic baselines
(src/baselines/sb3_ppo.py, sb3_sac.py, sb3_td3.py + sb3_wrapper.py).

Checks, for each of PPO / SAC / TD3:
  1. Construction via model_cls(state_dim=STATE_DIM, num_channels=NUM_CHANNELS),
     i.e. the exact signature HotSwapTrainer.__init__ uses.
  2. select_action() on a random STATE_DIM state decodes inside the action bounds.
  3. The GEOMETRIC Delta mapping survives the Box wrapper (min/max/midpoint).
  4. update() on a synthetic RetrospectiveReplayBuffer batch really steps the
     optimizers (before/after parameter diff).
  5. state_dict() round-trip moves weights A -> B (the hot-swap precondition).
  6. TD3 only: sampled subchannels actually vary, i.e. the dim-2 noise crosses
     bin boundaries.

Run:  /home/imnyj/venv/bin/python etc/scripts/verify_sb3_baselines.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter

import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.baselines.sb3_ppo import PPO
from src.baselines.sb3_sac import SAC
from src.baselines.sb3_td3 import TD3
from src.baselines.sb3_wrapper import DIM_DELTA, HybridActionBoxWrapper
from src.rl_interface import STATE_DIM, ActionDecoder, RetrospectiveReplayBuffer

NUM_CHANNELS = 4
BATCH = 32
FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAILURES.append(label)
    print(f"  [{status}] {label}{(' -- ' + detail) if detail else ''}")


def build_batch(model, n=BATCH):
    """Synthetic batch produced by the REAL RetrospectiveReplayBuffer."""
    buf = RetrospectiveReplayBuffer(capacity=n * 2, gamma=0.99)
    for _ in range(n):
        state = np.random.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        nxt = np.random.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        _, raw_action, _ = model.select_action(state, deterministic=False)
        buf.push(
            state=state,
            action=raw_action,
            reward=float(np.random.uniform(-2.0, 0.0)),
            next_state=nxt,
            done=bool(np.random.rand() < 0.1),
            delta_t=float(np.random.uniform(0.1, 5.0)),
        )
    return buf.sample(n)


def verify_geometric_mapping():
    print("\n[3] Geometric Delta mapping through the Box wrapper")
    dec = ActionDecoder(num_channels=NUM_CHANNELS)
    wrap = HybridActionBoxWrapper(dec)
    print(f"  decoder bounds: delta[{dec.delta_min}, {dec.delta_max}]  p[{dec.p_min}, {dec.p_max}]  ch={dec.num_channels}")

    lo = np.zeros(3, dtype=np.float32)
    lo[DIM_DELTA] = -1.0
    hi = np.zeros(3, dtype=np.float32)
    hi[DIM_DELTA] = 1.0
    mid = np.zeros(3, dtype=np.float32)
    mid[DIM_DELTA] = 0.0

    d_lo = wrap.to_grant(lo)[0]
    d_hi = wrap.to_grant(hi)[0]
    d_mid = wrap.to_grant(mid)[0]
    geo_mid = float(np.sqrt(dec.delta_min * dec.delta_max))
    lin_mid = 0.5 * (dec.delta_min + dec.delta_max)

    print(f"  dim0=-1 -> Delta={d_lo:.6f}   dim0=+1 -> Delta={d_hi:.6f}   dim0=0 -> Delta={d_mid:.6f}")
    print(f"  geometric midpoint sqrt(dmin*dmax)={geo_mid:.6f}   linear midpoint={lin_mid:.6f}")
    check("Delta(min) ~= delta_min", abs(d_lo - dec.delta_min) < 1e-6, f"{d_lo}")
    check("Delta(max) ~= delta_max", abs(d_hi - dec.delta_max) < 1e-6, f"{d_hi}")
    check("Delta(mid) ~= geometric midpoint (~2.12)", abs(d_mid - geo_mid) < 1e-3, f"{d_mid:.6f} vs {geo_mid:.6f}")
    check("Delta(mid) is NOT the linear midpoint (~22.5)", abs(d_mid - lin_mid) > 1.0, f"{d_mid:.6f} vs {lin_mid:.6f}")

    # Round-trip both ways over the whole space.
    max_err_d = max_err_p = 0.0
    ch_ok = True
    for u in np.linspace(0.0, 1.0, 51):
        d = dec.delta_from_unit(float(u))
        p = dec.p_min + float(u) * (dec.p_max - dec.p_min)
        for ch in range(NUM_CHANNELS):
            box = wrap.from_grant(d, ch, p)
            d2, ch2, p2 = wrap.to_grant(box)
            max_err_d = max(max_err_d, abs(d2 - d) / max(d, 1e-9))
            max_err_p = max(max_err_p, abs(p2 - p))
            ch_ok = ch_ok and (ch2 == ch)
    check("grant -> Box -> grant round-trip exact", max_err_d < 1e-5 and max_err_p < 1e-4 and ch_ok,
          f"rel_err(Delta)={max_err_d:.2e} abs_err(p)={max_err_p:.2e} ch_ok={ch_ok}")
    print(f"  channel bin width in Box units = {wrap.channel_bin_width}")


def verify_model(name, cls):
    print(f"\n{'=' * 72}\n{name}\n{'=' * 72}")
    dec = ActionDecoder(num_channels=NUM_CHANNELS)

    # --- 1. construction exactly as HotSwapTrainer does it -------------------
    print("[1] Construction  model_cls(state_dim=STATE_DIM, num_channels=4)")
    model = cls(state_dim=STATE_DIM, num_channels=NUM_CHANNELS)
    n_params = sum(p.numel() for p in model.parameters())
    n_tensors = len(list(model.parameters()))
    check("instantiated", True, f"{n_tensors} parameter tensors / {n_params} scalars visible to nn.Module")
    check("state_dict is non-empty", len(model.state_dict()) > 0, f"{len(model.state_dict())} entries")
    check(".to(cpu) works", model.to(torch.device("cpu")) is model)

    # --- 2. select_action in-range ------------------------------------------
    print("[2] select_action bounds over 500 random states")
    bad = []
    for _ in range(500):
        s = np.random.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        (delta, ch, power), raw, info = model.select_action(s, deterministic=False)
        if not (dec.delta_min - 1e-6 <= delta <= dec.delta_max + 1e-6):
            bad.append(("delta", delta))
        if not (dec.p_min - 1e-6 <= power <= dec.p_max + 1e-6):
            bad.append(("power", power))
        if ch not in range(NUM_CHANNELS):
            bad.append(("ch", ch))
        if np.asarray(raw).shape != (3,):
            bad.append(("raw_shape", np.asarray(raw).shape))
        if not isinstance(info, dict):
            bad.append(("info", type(info)))
    check("Delta in [delta_min, delta_max], p in [p_min, p_max], ch in {0..3}, raw is 3-dim",
          not bad, str(bad[:3]))
    (d0, c0, p0), raw0, info0 = model.select_action(np.zeros(STATE_DIM, dtype=np.float32), deterministic=True)
    print(f"  deterministic sample: Delta={d0:.4f}s ch={c0} p={p0:.4f}dBm raw={np.round(raw0, 4).tolist()}")
    print(f"  info keys: {sorted(info0.keys())}")

    # --- 4. update() actually steps the optimizer ---------------------------
    print("[4] update() moves weights")
    batch = build_batch(model)
    print(f"  batch keys: {sorted(batch.keys())}")
    print("  shapes: " + ", ".join(f"{k}={tuple(v.shape)}" for k, v in sorted(batch.items())))
    before = {k: v.detach().clone() for k, v in model.state_dict().items()}
    losses = model.update(batch)
    after = model.state_dict()
    moved = [k for k in before if not torch.allclose(before[k], after[k])]
    total_delta = sum(float((after[k] - before[k]).abs().sum()) for k in before)
    check("update() returned a dict with a 'loss' key", isinstance(losses, dict) and "loss" in losses)
    check("'loss' is finite", np.isfinite(losses.get("loss", np.nan)), f"loss={losses.get('loss')}")
    check("optimizer.step() changed parameters", len(moved) > 0,
          f"{len(moved)}/{len(before)} tensors changed, sum|delta|={total_delta:.6e}")
    print(f"  loss dict: { {k: (round(v, 6) if isinstance(v, float) else v) for k, v in losses.items()} }")
    print(f"  example changed tensors: {moved[:4]}")

    # --- 5. state_dict round-trip (hot-swap precondition) -------------------
    print("[5] state_dict() round-trip A -> B (hot-swap precondition)")
    other = cls(state_dim=STATE_DIM, num_channels=NUM_CHANNELS)
    sd_a, sd_b = model.state_dict(), other.state_dict()
    differed = [k for k in sd_a if not torch.allclose(sd_a[k], sd_b[k])]
    check("fresh model B starts with different weights", len(differed) > 0, f"{len(differed)} tensors differ")
    other.load_state_dict(model.state_dict())
    sd_b = other.state_dict()
    same = all(torch.allclose(sd_a[k], sd_b[k]) for k in sd_a)
    check("after load_state_dict every tensor matches", same)
    # And the positional zip that DualModelHotSwapManager.hot_swap() actually uses.
    third = cls(state_dim=STATE_DIM, num_channels=NUM_CHANNELS)
    with torch.no_grad():
        for p_dst, p_src in zip(third.parameters(), model.parameters()):
            p_dst.data.copy_(p_src.data)
    zip_ok = all(torch.allclose(a, b) for a, b in zip(third.parameters(), model.parameters()))
    check("positional parameters() zip-copy (the real hot_swap path) matches", zip_ok,
          f"{len(list(third.parameters()))} tensors")
    # save/load through the BaseRLModel helpers.
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", f"_verify_{name.lower()}.pt")
    model.save(path)
    fourth = cls(state_dim=STATE_DIM, num_channels=NUM_CHANNELS)
    fourth.load(path)
    check("BaseRLModel.save()/load() round-trip",
          all(torch.allclose(sd_a[k], v) for k, v in fourth.state_dict().items()))
    os.remove(path)

    return model


def verify_td3_channel_exploration(model):
    print("\n[6] TD3 subchannel exploration (noise must cross bin boundaries)")
    print(f"  per-dim noise sigma = {model.noise_sigma.tolist()}  (bin width = {model.wrapper.channel_bin_width})")
    s = np.random.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
    det_ch = model.select_action(s, deterministic=True)[0][1]
    counts = Counter(model.select_action(s, deterministic=False)[0][1] for _ in range(2000))
    print(f"  deterministic subchannel for this state: {det_ch}")
    print(f"  stochastic subchannel histogram over 2000 samples: {dict(sorted(counts.items()))}")
    check("more than one subchannel is reachable from a fixed state", len(counts) > 1,
          f"{len(counts)} distinct subchannels")
    check("all 4 subchannels reachable across varied states",
          len({model.select_action(np.random.uniform(-1, 1, STATE_DIM).astype(np.float32))[0][1]
               for _ in range(2000)}) == NUM_CHANNELS)
    # A deliberately tiny sigma must NOT cross bins -- proves the check is real.
    frozen = TD3(state_dim=STATE_DIM, num_channels=NUM_CHANNELS, channel_noise_sigma=1e-6)
    frozen_counts = Counter(frozen.select_action(s, deterministic=False)[0][1] for _ in range(500))
    print(f"  control: channel_noise_sigma=1e-6 -> {dict(frozen_counts)}")
    check("control: sigma << bin width freezes the subchannel", len(frozen_counts) == 1)


def main():
    np.random.seed(0)
    torch.manual_seed(0)
    print(f"STATE_DIM={STATE_DIM}  num_channels={NUM_CHANNELS}")
    print(f"torch={torch.__version__}")
    import stable_baselines3
    import gymnasium
    print(f"stable_baselines3={stable_baselines3.__version__}  gymnasium={gymnasium.__version__}")

    verify_geometric_mapping()
    verify_model("PPO", PPO)
    verify_model("SAC", SAC)
    td3 = verify_model("TD3", TD3)
    verify_td3_channel_exploration(td3)

    print("\n" + "=" * 72)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} CHECK(S) FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
