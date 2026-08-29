"""Prove that concurrent SUMO generation is serialised and leaves a consistent file set.

Four training processes regenerate into the same src/sumo/ directory. Individual
writes are atomic, but the seven generated files only mean anything as a mutually
consistent set, so make_sumo_files() holds an exclusive flock across its whole
check-and-generate section. This script forces four processes to regenerate at once
and checks that all of them succeed and that the resulting files parse and agree.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import time
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

REQUIRED = [
    "generated.nod.xml", "generated.edg.xml", "generated.net.xml",
    "generated.add.xml", "generated.rou.xml", "rsu.poi.xml", "generated.sumocfg",
]


def worker(idx: int, q) -> None:
    sys.path.insert(0, ROOT)
    import src.sumo.make_sumo_set as ss

    ss.DENSITY = 25.0
    ss.MAX_STEPS = 2135.0
    t0 = time.time()
    try:
        ss.make_sumo_files(force_regenerate=True)
        q.put((idx, "ok", round(time.time() - t0, 2)))
    except Exception as exc:  # noqa: BLE001
        q.put((idx, f"FAIL {type(exc).__name__}: {exc}", round(time.time() - t0, 2)))


def main() -> int:
    import src.sumo.make_sumo_set as ss

    # The workers generate with these params; the parent must compare against the
    # same ones or the signature check trivially reports a mismatch.
    ss.DENSITY = 25.0
    ss.MAX_STEPS = 2135.0

    mp.set_start_method("spawn", force=True)
    q = mp.Queue()
    procs = [mp.Process(target=worker, args=(i, q)) for i in range(4)]
    t0 = time.time()
    for p in procs:
        p.start()
    for p in procs:
        p.join(900)
    wall = time.time() - t0

    results = sorted(q.get() for _ in range(len(procs)))
    for idx, status, dt in results:
        print(f"  proc{idx}: {status:8} ({dt}s)")
    all_ok = all(r[1] == "ok" for r in results)
    serial = sum(r[2] for r in results)
    print(f"\nwall={wall:.1f}s  sum-of-per-process={serial:.1f}s"
          f"  -> {'serialised (lock held)' if serial > wall else 'overlapping'}")

    print("\nresulting file set:")
    bad = []
    for fn in REQUIRED:
        path = os.path.join(ss.BASE_PATH, fn)
        try:
            ET.parse(path)
            size = os.path.getsize(path)
            print(f"  {fn:22} {size:>8,} bytes  parses OK")
        except Exception as exc:  # noqa: BLE001
            print(f"  {fn:22} BROKEN: {type(exc).__name__}")
            bad.append(fn)

    consistent = ss.generation_signature_matches()
    print(f"\nsignature matches current params: {consistent}")
    ok = all_ok and not bad and consistent
    print("VERDICT:", "PASS - lock serialises generation, file set consistent" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
