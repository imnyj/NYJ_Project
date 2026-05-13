#!/usr/bin/env python3
"""
setup_network.py - Generate SUMO 5x5 grid network for MAFAC simulation

Creates:
  - config/grid5x5.net.xml     : SUMO road network
  - config/vehicles.rou.xml    : Vehicle routes (flow-based for continuous presence)
  - config/sumo_config.sumocfg : SUMO configuration file

CHANGES from original:
  - build_routes_xml() now uses <flow> tags instead of <trip> tags
  - This ensures vehicles continuously respawn, maintaining num_vehicles_target
    vehicles throughout the simulation (including after warmup period)
"""

import os
import sys
import math
import random
import subprocess
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

GRID_N        = 5
BLOCK_LEN     = 250.0
LANES         = 2
SPEED_LIMIT   = 13.89
ACCEL         = 2.6
DECEL         = 4.5
SIGMA         = 0.5
TAU           = 1.0
MIN_GAP       = 2.5
STEP_LENGTH   = 0.1

RSU_JUNCTIONS = [(1, 1), (1, 2), (2, 1), (2, 2)]

SCRIPT_DIR    = Path(__file__).resolve().parent
CONFIG_DIR    = SCRIPT_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

NET_FILE    = CONFIG_DIR / "grid5x5.net.xml"
ROU_FILE    = CONFIG_DIR / "vehicles.rou.xml"
SUMO_CFG    = CONFIG_DIR / "sumo_config.sumocfg"

# Edge naming for netgenerate-created 5x5 grid
_COL_TO_LETTER = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E'}

def _edge_id(r1, c1, r2, c2):
    """Convert grid coordinates to netgenerate edge ID (e.g., A0B0)."""
    return f"{_COL_TO_LETTER[c1]}{r1}{_COL_TO_LETTER[c2]}{r2}"


def prettify(elem):
    rough = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ")


def build_network_xml(num_vehicles: int = 50, seed: int = 42):
    random.seed(seed)

    net = ET.Element("net", {
        "version": "1.16",
        "junctionCornerDetail": "5",
        "limitTurnSpeed": "5.50"
    })

    total = (GRID_N - 1) * BLOCK_LEN
    ET.SubElement(net, "location", {
        "netOffset": "0.00,0.00",
        "convBoundary": f"0.00,0.00,{total:.2f},{total:.2f}",
        "origBoundary": f"0.00,0.00,{total:.2f},{total:.2f}",
        "projParameter": "!"
    })

    ET.SubElement(net, "type", {
        "id": "urban",
        "priority": "2",
        "numLanes": str(LANES),
        "speed": str(SPEED_LIMIT),
        "oneway": "1"
    })

    def jid(r, c):
        return f"J_{r}_{c}"

    for r in range(GRID_N):
        for c in range(GRID_N):
            x = c * BLOCK_LEN
            y = r * BLOCK_LEN
            jtype = "traffic_light" if (r, c) in RSU_JUNCTIONS else "priority"
            ET.SubElement(net, "junction", {
                "id": jid(r, c),
                "type": jtype,
                "x": f"{x:.2f}",
                "y": f"{y:.2f}",
                "incLanes": "",
                "intLanes": "",
                "shape": ""
            })

    edge_list = []

    def add_edge(r1, c1, r2, c2):
        eid = f"E_{r1}_{c1}_to_{r2}_{c2}"
        edge_list.append((jid(r1, c1), jid(r2, c2), eid))
        edge = ET.SubElement(net, "edge", {
            "id": eid,
            "from": jid(r1, c1),
            "to": jid(r2, c2),
            "type": "urban",
            "priority": "2",
            "numLanes": str(LANES),
            "speed": str(SPEED_LIMIT)
        })
        for lane_idx in range(LANES):
            x1 = c1 * BLOCK_LEN
            y1 = r1 * BLOCK_LEN
            x2 = c2 * BLOCK_LEN
            y2 = r2 * BLOCK_LEN
            ET.SubElement(edge, "lane", {
                "id": f"{eid}_{lane_idx}",
                "index": str(lane_idx),
                "speed": str(SPEED_LIMIT),
                "length": str(BLOCK_LEN),
                "shape": f"{x1:.2f},{y1:.2f} {x2:.2f},{y2:.2f}"
            })

    for r in range(GRID_N):
        for c in range(GRID_N):
            if c + 1 < GRID_N:
                add_edge(r, c, r, c + 1)
                add_edge(r, c + 1, r, c)
            if r + 1 < GRID_N:
                add_edge(r, c, r + 1, c)
                add_edge(r + 1, c, r, c)

    for r in range(GRID_N):
        for c in range(GRID_N):
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                r2, c2 = r + dr, c + dc
                if 0 <= r2 < GRID_N and 0 <= c2 < GRID_N:
                    from_edge = f"E_{r}_{c}_to_{r2}_{c2}"
                    for dr2, dc2 in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if (dr2, dc2) == (-dr, -dc):
                            continue
                        r3, c3 = r2 + dr2, c2 + dc2
                        if 0 <= r3 < GRID_N and 0 <= c3 < GRID_N:
                            to_edge = f"E_{r2}_{c2}_to_{r3}_{c3}"
                            for lane_idx in range(LANES):
                                ET.SubElement(net, "connection", {
                                    "from": from_edge,
                                    "to": to_edge,
                                    "fromLane": str(lane_idx),
                                    "toLane": str(lane_idx),
                                    "pass": "1"
                                })

    xml_str = prettify(net)
    NET_FILE.write_text(xml_str)
    print(f"[setup_network] Written: {NET_FILE}")

    return edge_list


def build_routes_xml(edge_list, num_vehicles: int = 50, seed: int = 42,
                     duration_s: float = 600.0) -> None:
    """
    Generate vehicle flows using the edge list.

    CHANGED: Uses <flow> tags instead of <trip> tags so that vehicles are
    continuously regenerated throughout the simulation, ensuring
    num_vehicles_target vehicles are always present (even after warmup).

    Each flow generates vehicles periodically from begin=0 to end=duration_s.
    The period is estimated from average trip time so that at steady state
    roughly num_vehicles vehicles are active simultaneously.
    """
    random.seed(seed)

    routes = ET.Element("routes")

    vtype = ET.SubElement(routes, "vType", {
        "id": "car",
        "accel": str(ACCEL),
        "decel": str(DECEL),
        "sigma": str(SIGMA),
        "tau": str(TAU),
        "minGap": str(MIN_GAP),
        "maxSpeed": str(SPEED_LIMIT),
        "color": "1,1,0"
    })

    all_edges = [eid for (_, _, eid) in edge_list]
    if not all_edges:
        for r in range(GRID_N):
            for c in range(GRID_N):
                if c + 1 < GRID_N:
                    all_edges.append(_edge_id(r, c, r, c+1))
                    all_edges.append(_edge_id(r, c+1, r, c))
                if r + 1 < GRID_N:
                    all_edges.append(_edge_id(r, c, r+1, c))
                    all_edges.append(_edge_id(r+1, c, r, c))

    # Estimate average trip duration based on network size
    # On a 5x5 grid at 13.89 m/s, crossing ~4 blocks = ~72s
    avg_trip_time = max(60.0, GRID_N * BLOCK_LEN / SPEED_LIMIT)

    for i in range(num_vehicles):
        src_edge = random.choice(all_edges)
        dst_edge = random.choice([e for e in all_edges if e != src_edge])

        flow_id = f"flow_{i}"

        # flow: begin=0, end=duration_s, period=avg_trip_time
        # SUMO will generate a new vehicle from this flow every `period` seconds
        # ensuring continuous vehicle presence throughout the simulation
        ET.SubElement(routes, "flow", {
            "id": flow_id,
            "type": "car",
            "begin": "0",
            "end": str(int(duration_s)),
            "period": str(int(avg_trip_time)),
            "from": src_edge,
            "to": dst_edge,
            "departLane": "random",
            "departSpeed": "random"
        })

    xml_str = prettify(routes)
    ROU_FILE.write_text(xml_str)
    print(f"[setup_network] Written: {ROU_FILE}")
    print(f"[setup_network] Flow-based generation: {num_vehicles} flows, "
          f"period={int(avg_trip_time)}s, duration={int(duration_s)}s")


def build_sumo_config(num_vehicles: int = 50,
                      step_length: float = STEP_LENGTH,
                      end_time: float = 600.0) -> None:
    cfg = ET.Element("configuration")

    inp = ET.SubElement(cfg, "input")
    ET.SubElement(inp, "net-file",       {"value": "grid5x5.net.xml"})
    ET.SubElement(inp, "route-files",    {"value": "vehicles.rou.xml"})

    proc = ET.SubElement(cfg, "processing")
    ET.SubElement(proc, "step-length",   {"value": str(step_length)})
    ET.SubElement(proc, "collision.action", {"value": "warn"})
    ET.SubElement(proc, "time-to-teleport", {"value": "300"})

    time_elem = ET.SubElement(cfg, "time")
    ET.SubElement(time_elem, "begin",    {"value": "0"})
    ET.SubElement(time_elem, "end",      {"value": str(end_time)})

    rnd = ET.SubElement(cfg, "random")
    ET.SubElement(rnd, "seed",           {"value": "42"})

    xml_str = prettify(cfg)
    SUMO_CFG.write_text(xml_str)
    print(f"[setup_network] Written: {SUMO_CFG}")


def try_netgenerate(num_vehicles: int, seed: int) -> bool:
    try:
        net_file = str(NET_FILE)
        cmd = [
            "netgenerate",
            "--grid",
            f"--grid.number={GRID_N}",
            f"--grid.length={BLOCK_LEN}",
            f"--default.lanenumber={LANES}",
            f"--default.speed={SPEED_LIMIT}",
            f"--tls.set=J_1_1,J_1_2,J_2_1,J_2_2",
            f"--output-file={net_file}",
            f"--seed={seed}",
            "--no-turnarounds",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"[setup_network] netgenerate succeeded: {net_file}")
            return True
        else:
            print(f"[setup_network] netgenerate failed: {result.stderr[:200]}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[setup_network] netgenerate not available: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate SUMO 5x5 grid network")
    parser.add_argument("--num-vehicles", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration", type=float, default=600.0)
    parser.add_argument("--force-manual", action="store_true")
    args = parser.parse_args()

    print(f"[setup_network] Generating 5x5 grid network (N={GRID_N}, block={BLOCK_LEN}m)")
    print(f"[setup_network] Vehicles={args.num_vehicles}, seed={args.seed}")

    net_ok = False
    if not args.force_manual:
        net_ok = try_netgenerate(args.num_vehicles, args.seed)

    if not net_ok:
        print("[setup_network] Falling back to manual XML generation ...")
        edge_list = build_network_xml(args.num_vehicles, args.seed)
    else:
        edge_list = []
        for r in range(GRID_N):
            for c in range(GRID_N):
                if c + 1 < GRID_N:
                    edge_list.append((None, None, _edge_id(r, c, r, c+1)))
                    edge_list.append((None, None, _edge_id(r, c+1, r, c)))
                if r + 1 < GRID_N:
                    edge_list.append((None, None, _edge_id(r, c, r+1, c)))
                    edge_list.append((None, None, _edge_id(r+1, c, r, c)))

    build_routes_xml(edge_list, args.num_vehicles, args.seed, args.duration)
    build_sumo_config(args.num_vehicles, STEP_LENGTH, args.duration)

    print("[setup_network] Done. Files written to:", CONFIG_DIR)


if __name__ == "__main__":
    main()
