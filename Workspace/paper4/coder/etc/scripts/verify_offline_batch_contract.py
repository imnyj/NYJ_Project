#!/usr/bin/env python3
# etc/scripts/verify_offline_batch_contract.py
# ============================================================================
# Measure, do not trust, the claim in `OfflineDataset`'s docstring that its
# `sample()` emits "EXACTLY the key set and tensor shapes" that
# `RetrospectiveReplayBuffer.sample()` emits.
#
# The two are compared by building both containers from the SAME synthetic
# transitions and diffing the resulting dictionaries key by key, including
# every value's shape and dtype. A docstring is not evidence; this is.
#
# Also reports what the buffer does when `action_idx` / `behaviour_log_prob` are
# absent, because the buffer drops those keys all-or-nothing while the dataset
# always emits them -- a difference the docstring does not mention.
# ============================================================================

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.rl_interface import STATE_DIM, RetrospectiveReplayBuffer  # noqa: E402
from src.hoorl_offline import ARRAY_KEYS, OfflineDataset  # noqa: E402


def describe(batch):
    out = {}
    for k, v in batch.items():
        out[k] = {"shape": tuple(v.shape), "dtype": str(v.dtype)}
    return out


def build_pair(n=32, with_optional=True, gamma=0.99):
    rng = np.random.default_rng(0)
    states = rng.normal(size=(n, STATE_DIM)).astype(np.float32)
    next_states = rng.normal(size=(n, STATE_DIM)).astype(np.float32)
    actions = rng.normal(size=(n, 3)).astype(np.float32)
    rewards = rng.normal(size=n).astype(np.float32)
    dones = (rng.random(n) < 0.1).astype(np.float32)
    delta_t = rng.uniform(0.1, 45.0, size=n).astype(np.float32)
    action_idx = rng.integers(0, 4, size=n).astype(np.int64)
    logp = np.full(n, -np.log(4.0), dtype=np.float32)

    buf = RetrospectiveReplayBuffer(capacity=n, gamma=gamma)
    for i in range(n):
        buf.push(
            states[i], actions[i], float(rewards[i]), next_states[i],
            bool(dones[i]), float(delta_t[i]),
            action_idx=int(action_idx[i]) if with_optional else None,
            behaviour_log_prob=float(logp[i]) if with_optional else None,
        )

    arrays = {
        "state": states, "action": actions, "reward": rewards,
        "next_state": next_states, "done": dones, "delta_t": delta_t,
        "action_idx": action_idx, "behaviour_log_prob": logp,
    }
    ds = OfflineDataset(arrays, metadata={"state_dim": STATE_DIM}, gamma=gamma)
    return buf, ds


def compare(n=32, with_optional=True):
    buf, ds = build_pair(n=n, with_optional=with_optional)
    torch.manual_seed(0)
    np.random.seed(0)
    b_batch = buf.sample(n)
    np.random.seed(0)
    d_batch = ds.sample(n)

    b_desc, d_desc = describe(b_batch), describe(d_batch)
    b_keys, d_keys = set(b_desc), set(d_desc)
    report = {
        "with_optional": with_optional,
        "buffer_keys": sorted(b_keys),
        "dataset_keys": sorted(d_keys),
        "only_in_buffer": sorted(b_keys - d_keys),
        "only_in_dataset": sorted(d_keys - b_keys),
        "shape_or_dtype_mismatch": {},
        "buffer_desc": b_desc,
        "dataset_desc": d_desc,
    }
    for k in sorted(b_keys & d_keys):
        if b_desc[k] != d_desc[k]:
            report["shape_or_dtype_mismatch"][k] = {"buffer": b_desc[k], "dataset": d_desc[k]}
    return report


def discount_check():
    """`discount` must be gamma ** delta_t in BOTH, elementwise."""
    buf, ds = build_pair(n=16)
    b = buf.sample(16)
    d = ds.sample(16)
    ok_b = torch.allclose(b["discount"], torch.pow(torch.tensor(0.99), b["delta_t"]), atol=1e-6)
    ok_d = torch.allclose(d["discount"], torch.pow(torch.tensor(0.99), d["delta_t"]), atol=1e-6)
    return {"buffer_discount_is_gamma_pow_delta_t": bool(ok_b),
            "dataset_discount_is_gamma_pow_delta_t": bool(ok_d)}


def sampling_check():
    """Both draw WITHOUT replacement and clamp the batch to the container size."""
    buf, ds = build_pair(n=8)
    b = buf.sample(100)
    d = ds.sample(100)
    return {"buffer_batch_when_asked_100_of_8": int(b["state"].shape[0]),
            "dataset_batch_when_asked_100_of_8": int(d["state"].shape[0])}


def main() -> int:
    result = {
        "STATE_DIM": int(STATE_DIM),
        "ARRAY_KEYS": list(ARRAY_KEYS),
        "full": compare(with_optional=True),
        "without_optional_fields_in_buffer": compare(with_optional=False),
        "discount": discount_check(),
        "size_clamp": sampling_check(),
    }
    print(json.dumps(result, indent=2))
    full = result["full"]
    identical = (not full["only_in_buffer"] and not full["only_in_dataset"]
                 and not full["shape_or_dtype_mismatch"])
    print("\nVERDICT (both containers carrying action_idx and behaviour_log_prob): "
          + ("IDENTICAL contract" if identical else "CONTRACTS DIFFER"))
    partial = result["without_optional_fields_in_buffer"]
    print("VERDICT (buffer filled WITHOUT the optional fields): "
          + ("IDENTICAL contract" if (not partial["only_in_buffer"]
                                      and not partial["only_in_dataset"]
                                      and not partial["shape_or_dtype_mismatch"])
             else f"CONTRACTS DIFFER; dataset-only keys {partial['only_in_dataset']}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
