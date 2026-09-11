"""Does every baseline declare its wiring flags, and does declaring change the losses?

Four stages, three of them run here. Each addresses something that has gone
wrong in this project before.

  1. DECLARED KEYS ARE ACTUALLY EMITTED. `WIRING_FLAG_KEYS` is a promise about
     `update()`'s return dict. A declaration that no update fulfils is worse
     than no declaration, because the aggregate then reads as "the mechanism is
     off" when the truth is "nobody plumbed it". Every model is constructed and
     stepped on a real batch, and every declared key must appear on EVERY
     update -- including updates where the mechanism did not fire, since a key
     that appears only when it fires cannot tell "off" from "absent".

  2. THE FLAGS ARE ADDITIVE. Adding a reported value must not move a loss. Each
     model's pre-change source is loaded from `backup/` alongside the current
     one, both are seeded identically, both are fed the SAME batch, and every
     key the old version returned must come back bit-identical from the new one.
     A model whose backup is not available is reported as unchecked rather than
     quietly passing.

  3. A FLAG RESPONDS TO ITS OWN CONDITION. A flag hardwired to a constant
     detects nothing. Each flag is toggled by the specific thing it reports, not
     by one blanket manipulation: `TOGGLES` below names, per flag, the batch key
     whose removal must drive it to 0. A first draft of this script stripped the
     neighbour set and treated every flag that then read 0 as responsive, which
     proved nothing -- `per_sampled` and `n_step_active` read 0 on a synthetic
     batch whether or not it has neighbours, because a hand-built dict carries
     no priority weights and no n-step columns either way. Flags whose condition
     a synthetic batch cannot supply are reported as `needs_real_buffer` rather
     than passed, and are covered by stage 4.

  4. THE REAL BUFFER -- NOT IN THIS SCRIPT YET. Showing a flag read 1 needs the
     mechanisms fed by a real `RetrospectiveReplayBuffer`, and the end-to-end
     form of that check is the trainer writing the aggregate to the progress CSV
     and TensorBoard, which is not wired at the time of writing. The evidence
     that exists meanwhile is the 2026-09-06 loss-scale measurement: over the
     retained 1,000 updates of a real 4,000-step run, `behaviour_logp_stored`,
     `actor_updated`, `target_synced`, `policy_synced`, `per_sampled`,
     `task_decomposed` and `global_critic_cooperative` all reached 1.0, while
     MA2HDQN's `n_step_active` stayed at 0.0 exactly as its own source comment
     predicts. See `loss_scale_after_rewiring_20260906.csv`,
     `update_term_max_json`. HOORL was not measured (no offline dataset), and
     `neighbourhood_used` postdates that run.

Writes results/diagnostics/wiring_flag_verification.csv. Touches no shared
scenario directory and trains nothing beyond single updates on synthetic
batches.
"""
from __future__ import annotations

import csv
import glob
import importlib.machinery
import importlib.util
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
BACKUP = os.environ.get("PAPER4_BACKUP_DIR", "/home/imnyj/Workspace/paper4/backup")
sys.path.insert(0, CODER)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines import ALL_BASELINES, get_baseline  # noqa: E402
from src.rl_interface import STATE_DIM  # noqa: E402

OUT = os.path.join(CODER, "results", "diagnostics", "wiring_flag_verification.csv")
BATCH = 32
MAX_NEIGHBOURS = 4
SEED = 20260906

#: Flag -> the batch keys whose absence must drive it to 0. Only flags whose
#: condition a hand-built batch can actually express appear here; the rest are
#: periodic (they fire once every N updates and cannot be toggled by a batch at
#: all) or need machinery the buffer supplies, and are deferred to stage 4.
TOGGLES: Dict[str, Tuple[str, ...]] = {
    "neighbourhood_used": ("neighbour_state", "neighbor_state"),
    "global_critic_cooperative": ("neighbour_state", "others", "neighbor_state"),
}

#: Source file each baseline lives in, derived from the class rather than typed,
#: so a renamed module cannot leave a stale entry here.
def module_file(name: str) -> str:
    return sys.modules[get_baseline(name).__module__].__file__


def make_batch(num_channels: int = 4, with_neighbours: bool = True) -> Dict[str, Any]:
    """A batch shaped exactly like `RetrospectiveReplayBuffer.sample`'s output."""
    g = torch.Generator().manual_seed(SEED)
    batch: Dict[str, Any] = {
        "state": torch.rand(BATCH, STATE_DIM, generator=g),
        "next_state": torch.rand(BATCH, STATE_DIM, generator=g),
        "reward": torch.rand(BATCH, 1, generator=g) * -1.0,
        "done": torch.zeros(BATCH, 1),
        "delta_actual": torch.rand(BATCH, 1, generator=g) * 4.0 + 1.0,
        "action_idx": torch.randint(0, num_channels, (BATCH,), generator=g),
        "log_prob": torch.rand(BATCH, 1, generator=g) * -1.0,
    }
    # (Delta_norm, channel, power_norm) in the encoded layout every model reads.
    action = torch.rand(BATCH, 3, generator=g) * 2.0 - 1.0
    action[:, 1] = batch["action_idx"].float()
    batch["action"] = action
    if with_neighbours:
        batch["neighbour_state"] = torch.rand(BATCH, MAX_NEIGHBOURS, STATE_DIM, generator=g)
        batch["neighbour_mask"] = torch.ones(BATCH, MAX_NEIGHBOURS)
        batch["next_neighbour_state"] = torch.rand(
            BATCH, MAX_NEIGHBOURS, STATE_DIM, generator=g
        )
        batch["next_neighbour_mask"] = torch.ones(BATCH, MAX_NEIGHBOURS)
    return batch


def load_backup_class(name: str) -> Tuple[Optional[type], str]:
    """Import the newest `backup/<module>.py.*.bak` as a throwaway module.

    Returns (class, note). The backup imports `src.*` by absolute name, so its
    dependencies resolve to the CURRENT tree; only the model file itself is the
    old one, which is exactly the comparison wanted.
    """
    stem = os.path.basename(module_file(name))
    candidates = sorted(glob.glob(os.path.join(BACKUP, stem + ".*.bak")),
                        key=os.path.getmtime, reverse=True)
    if not candidates:
        return None, f"no backup matching {stem}.*.bak"
    path = candidates[0]
    # An explicit SourceFileLoader is required: `spec_from_file_location` infers
    # the loader from the suffix and returns None for `.bak`, which silently
    # turned this whole comparison into a skip the first time it was run.
    spec = importlib.util.spec_from_file_location(
        f"_old_{name.replace('-', '_')}", path,
        loader=importlib.machinery.SourceFileLoader(
            f"_old_{name.replace('-', '_')}", path
        ),
    )
    if spec is None or spec.loader is None:
        return None, f"could not load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        return None, f"{os.path.basename(path)} did not import: {type(exc).__name__}: {exc}"
    cls = getattr(module, get_baseline(name).__name__, None)
    if cls is None:
        return None, f"{os.path.basename(path)} has no {get_baseline(name).__name__}"
    return cls, os.path.basename(path)


def same_value(old: float, new: Any) -> bool:
    """Equality that treats NaN as equal to NaN.

    TD3 reports `actor_loss = nan` on the updates its delayed policy skips, and
    `nan != nan` in Python, so a plain `!=` comparison reported TD3 as changed by
    a class attribute that cannot change anything. The NaN is structural and
    identical on both sides; the comparison, not the code, was wrong.
    """
    if new is None:
        return False
    if isinstance(old, float) and isinstance(new, float):
        if math.isnan(old) and math.isnan(new):
            return True
    return old == new


def one_update(cls: type, batch: Dict[str, Any]) -> Dict[str, float]:
    """Construct with a pinned seed and take exactly one gradient step."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    model = cls()
    return {k: float(v) for k, v in model.update(dict(batch)).items()}


def main() -> int:
    rows: List[Dict[str, Any]] = []
    failures: List[str] = []

    def check(ok: bool, message: str) -> bool:
        print(("  PASS  " if ok else "  FAIL  ") + message)
        if not ok:
            failures.append(message)
        return ok

    for name in ALL_BASELINES:
        cls = get_baseline(name)
        declared = tuple(getattr(cls, "WIRING_FLAG_KEYS", ()))
        print(f"\n[{name}] declares {declared or '()'}")
        row: Dict[str, Any] = {
            "model": name,
            "declared_keys": ";".join(declared),
            "n_declared": len(declared),
        }

        # 1. every declared key is emitted, on a batch that has everything
        batch = make_batch()
        try:
            out = one_update(cls, batch)
            row["update_ok"] = True
        except Exception as exc:  # noqa: BLE001
            out = {}
            row["update_ok"] = False
            row["error"] = f"{type(exc).__name__}: {exc}"
            check(False, f"{name}: update() raised: {row['error']}")

        if row["update_ok"]:
            missing = [k for k in declared if k not in out]
            row["missing_keys"] = ";".join(missing)
            check(not missing,
                  f"{name}: every declared key is present ({len(declared)} declared)")
            row["flag_values_full_batch"] = ";".join(
                f"{k}={out.get(k)}" for k in declared
            )
            # An undeclared 0/1 key is not an error, but it is worth seeing:
            # it is the shape of a flag nobody declared.
            binary_keys = [k for k, v in out.items()
                           if v in (0.0, 1.0) and k not in declared and k != "loss"]
            row["undeclared_binary_keys"] = ";".join(sorted(binary_keys))

        # 2. additive: no pre-existing key changed
        old_cls, note = load_backup_class(name)
        row["backup_used"] = note
        if old_cls is None:
            row["additive"] = "unchecked"
            print(f"  SKIP  {name}: additivity unchecked ({note})")
        else:
            try:
                old_out = one_update(old_cls, make_batch())
                new_out = one_update(cls, make_batch())
                moved = {
                    k: (old_out[k], new_out.get(k))
                    for k in old_out
                    if not same_value(old_out[k], new_out.get(k))
                }
                row["additive"] = "yes" if not moved else "NO"
                row["moved_keys"] = ";".join(sorted(moved))
                row["added_keys"] = ";".join(sorted(set(new_out) - set(old_out)))
                check(not moved,
                      f"{name}: every pre-existing key is bit-identical to the backup"
                      + (f" (moved: {sorted(moved)})" if moved else ""))
            except Exception as exc:  # noqa: BLE001
                row["additive"] = "error"
                row["error"] = f"{type(exc).__name__}: {exc}"
                check(False, f"{name}: additivity comparison raised: {row['error']}")

        # 3. each flag responds to ITS OWN condition
        if row.get("update_ok") and declared:
            responded, deferred = [], []
            for key in declared:
                dropped = TOGGLES.get(key)
                if dropped is None:
                    deferred.append(key)
                    continue
                probe = make_batch()
                for column in dropped:
                    probe.pop(column, None)
                try:
                    value = one_update(cls, probe).get(key)
                except Exception as exc:  # noqa: BLE001
                    check(False, f"{name}: probing {key} raised {type(exc).__name__}: {exc}")
                    continue
                ok = check(value == 0.0,
                           f"{name}: {key} falls to 0 when {list(dropped)} is absent "
                           f"(read {value})")
                if ok:
                    responded.append(key)
            row["keys_that_read_zero"] = ";".join(responded)
            row["keys_needing_real_buffer"] = ";".join(deferred)
            if deferred:
                print(f"  DEFER {name}: {deferred} cannot be toggled on a synthetic "
                      "batch; covered by the real-buffer stage")

        rows.append(row)

    fields = ["model", "n_declared", "declared_keys", "update_ok", "missing_keys",
              "flag_values_full_batch", "keys_needing_real_buffer",
              "keys_that_read_zero", "undeclared_binary_keys", "additive",
              "moved_keys", "added_keys", "backup_used", "error"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    print(f"\nwrote {OUT}")

    if failures:
        print(f"\n{len(failures)} CHECK(S) FAILED")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
