"""Contract conformance check for all nine comparison baselines.

Each baseline is a reimplementation of a published method adapted to this project's
hybrid action space, so the thing that actually matters is whether it satisfies the
BaseRLModel contract the trainer and evaluator rely on. This script checks that
directly rather than trusting the implementation report:

  1. constructs via model_cls(state_dim=STATE_DIM, num_channels=4)
  2. select_action returns a decoded (delta, ch, power) inside the approved bounds
  3. the discrete head actually explores all subchannels rather than collapsing
  4. update() moves weights (i.e. optimizer.step() is real, not a no-op)
  5. update() survives a batch with and without the optional action_idx key
  6. state_dict() round-trips, which the Act/Rest hot swap depends on

Written under etc/scripts per the project's workspace-cleanliness rule.
"""
from __future__ import annotations

import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines import ALL_BASELINES, get_baseline  # noqa: E402
from src.rl_interface import STATE_DIM, ActionDecoder, RetrospectiveReplayBuffer  # noqa: E402

NUM_CH = 4
N_SAMPLES = 300
BATCH = 32


def make_batch(with_idx: bool):
    buf = RetrospectiveReplayBuffer(capacity=256)
    dec = ActionDecoder(num_channels=NUM_CH)
    rng = np.random.default_rng(0)
    for i in range(BATCH * 2):
        s = rng.random(STATE_DIM).astype(np.float32)
        ns = rng.random(STATE_DIM).astype(np.float32)
        delta = float(dec.delta_min * (dec.delta_max / dec.delta_min) ** rng.random())
        power = float(dec.p_min + (dec.p_max - dec.p_min) * rng.random())
        ch = int(i % NUM_CH)
        raw = dec.encode_action(delta, ch, power)
        kw = {"action_idx": int(rng.integers(0, NUM_CH * 5))} if with_idx else {}
        buf.push(s, raw, float(-rng.random()), ns, False, delta, **kw)
    return buf.sample(BATCH)


def snapshot(model):
    return {k: v.detach().clone() for k, v in model.state_dict().items()
            if v.dtype.is_floating_point}


def moved(before, model):
    after = model.state_dict()
    return sum(1 for k, v in before.items() if not torch.allclose(v, after[k].detach()))


def check(name):
    cls = get_baseline(name)
    dec = ActionDecoder(num_channels=NUM_CH)
    rows = []

    model = cls(state_dim=STATE_DIM, num_channels=NUM_CH)
    n_params = sum(p.numel() for p in model.parameters())

    # 2 + 3: action bounds and discrete-head exploration
    rng = np.random.default_rng(1)
    chans, deltas, powers = [], [], []
    for _ in range(N_SAMPLES):
        st = rng.random(STATE_DIM).astype(np.float32)
        decoded, raw, info = model.select_action(st, deterministic=False)
        d, ch, p = decoded
        deltas.append(d)
        chans.append(int(ch))
        powers.append(p)
    bounds_ok = (
        dec.delta_min - 1e-6 <= min(deltas) and max(deltas) <= dec.delta_max + 1e-6
        and dec.p_min - 1e-6 <= min(powers) and max(powers) <= dec.p_max + 1e-6
        and set(chans) <= set(range(NUM_CH))
    )
    rows.append(("bounds", bounds_ok,
                 f"delta[{min(deltas):.3f},{max(deltas):.2f}] p[{min(powers):.2f},{max(powers):.2f}]"))
    explored = sorted(set(chans))
    rows.append(("explore", len(explored) == NUM_CH,
                 f"channels used {explored} {dict(Counter(chans))}"))

    # 4 + 5: update moves weights, with and without action_idx
    for with_idx in (True, False):
        m = cls(state_dim=STATE_DIM, num_channels=NUM_CH)
        before = snapshot(m)
        try:
            out = m.update(make_batch(with_idx))
            n_moved = moved(before, m)
            has_loss = isinstance(out, dict) and "loss" in out
            rows.append((f"update[idx={with_idx}]", n_moved > 0 and has_loss,
                         f"{n_moved}/{len(before)} tensors moved, keys={sorted(out)[:5] if isinstance(out,dict) else out}"))
        except Exception as exc:  # noqa: BLE001
            rows.append((f"update[idx={with_idx}]", False, f"{type(exc).__name__}: {exc}"))

    # 6: state_dict round-trip (hot swap depends on it)
    a = cls(state_dim=STATE_DIM, num_channels=NUM_CH)
    b = cls(state_dim=STATE_DIM, num_channels=NUM_CH)
    b.load_state_dict(a.state_dict())
    same = all(torch.allclose(v, b.state_dict()[k]) for k, v in a.state_dict().items()
               if v.dtype.is_floating_point)
    rows.append(("hotswap", same, "state_dict copy A->B identical"))

    return n_params, rows


def main():
    print(f"STATE_DIM={STATE_DIM}  num_channels={NUM_CH}")
    dec = ActionDecoder(num_channels=NUM_CH)
    print(f"bounds: delta=[{dec.delta_min}, {dec.delta_max}]  p=[{dec.p_min}, {dec.p_max}]\n")
    failures = []
    for name in ALL_BASELINES:
        try:
            n_params, rows = check(name)
        except Exception as exc:  # noqa: BLE001
            print(f"{name:14} CONSTRUCTION FAILED: {type(exc).__name__}: {exc}")
            failures.append((name, "construction", str(exc)))
            continue
        bad = [r for r in rows if not r[1]]
        flag = "PASS" if not bad else "FAIL"
        print(f"{name:14} [{flag}] params={n_params:,}")
        for label, okk, note in rows:
            if not okk:
                print(f"                 x {label}: {note}")
                failures.append((name, label, note))
    print("\n" + "=" * 72)
    if failures:
        print(f"FAILURES: {len(failures)}")
        for n, label, note in failures:
            print(f"  {n} / {label}: {note[:110]}")
        return 1
    print("ALL 9 BASELINES PASS THE CONTRACT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
