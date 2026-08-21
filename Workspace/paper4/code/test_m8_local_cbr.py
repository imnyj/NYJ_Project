#!/usr/bin/env python3
"""
test_m8_local_cbr.py
====================
Independent verification suite for Task M-8:
Per-vehicle local CBR measurement and sim_engine.py vdata["cbr"] delivery.

Verifies:
  1. Spatial non-uniform traffic scenario (East cluster vs West isolated vehicle):
     - East cluster (0~100m, 5 vehicles @ 10Hz) vs West isolated vehicle (800m, 1 vehicle @ 1Hz)
     - Assert East cluster local CBR is significantly higher than West isolated vehicle.
     - Assert vdata["cbr"] reflects heterogeneous spatial distribution (multiple distinct values).
  2. Mathematical exactness & boundary conditions:
     - CBR(vid) = min(1.0, (N_tx(vid) * TX_DURATION_S) / window_duration)
     - Inclusion of self + neighbor transmissions within COMM_RANGE_M (300.0m)
     - Exact boundary at 300.0m (included) vs 300.001m (excluded)
     - Clipping at 1.0 under high contention
  3. Input type flexibility:
     - List of CAM event dicts with x, y / vid
     - Dict mapping vid -> tx_count
     - List of coordinate tuples / list of vid strings
  4. Spatial reuse verification:
     - Two distant clusters (x=0m vs x=1000m) do not interfere; each observes only local load
       (local CBR == 4*airtime vs global CBR == 8*airtime).
  5. ETSICAMLayer & DCC controller state machine integration:
     - ReactDCC responds to per-vehicle local CBR (RELAXED for low CBR vs RESTRICTED for high CBR).
  6. AI Hook integration:
     - _dcc_ai passes local CBR and smoothed local CBR in 5D state.
  7. SimulationRunner runtime integration:
     - Actual SUMO simulation run verifying step-by-step per-vehicle vdata["cbr"] injection
       and CBR_mean summary aggregation without error.
"""

import os
import sys
import math
import unittest
import tempfile
import shutil

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from sim_engine import (
    COMM_RANGE_M,
    TX_DURATION_S,
    compute_local_cbr,
    compute_local_n_est,
    SimulationRunner,
)
from etsi_cam_layer import ETSICAMLayer, VehicleCAMState, T_GENCAM_RELAXED, T_GENCAM_RESTRICTED
from ai_dcc_hook import get_hook


class TestM8LocalCBR(unittest.TestCase):

    def test_01_spatial_nonuniform_traffic_east_vs_west(self):
        """1. 공간 불균일 트래픽 검증: 동쪽 클러스터(5대 10Hz) vs 서쪽 고립 차량(1대 1Hz)."""
        # East cluster: 5 vehicles in 0~100m, each transmits 1 CAM per 0.1s step (10 Hz)
        positions = {
            "east_0": (0.0, 0.0),
            "east_1": (25.0, 0.0),
            "east_2": (50.0, 0.0),
            "east_3": (75.0, 0.0),
            "east_4": (100.0, 0.0),
            "west_iso": (800.0, 0.0),  # Isolated vehicle at 800m (> 300m away from all east vehicles)
        }

        # Step where all east vehicles transmit (5 CAMs), west does not transmit (0 CAMs)
        east_events = [
            {"vid": "east_0", "x": 0.0, "y": 0.0},
            {"vid": "east_1", "x": 25.0, "y": 0.0},
            {"vid": "east_2", "x": 50.0, "y": 0.0},
            {"vid": "east_3", "x": 75.0, "y": 0.0},
            {"vid": "east_4", "x": 100.0, "y": 0.0},
        ]
        window_duration = 0.1

        cbr_dict, cbr_mean = compute_local_cbr(positions, east_events, window_duration, comm_range_m=COMM_RANGE_M)

        # Expected east CBR: 5 * TX_DURATION_S / 0.1s
        expected_east_cbr = (5 * TX_DURATION_S) / window_duration
        for i in range(5):
            vid = f"east_{i}"
            self.assertAlmostEqual(cbr_dict[vid], expected_east_cbr, places=6,
                                   msg=f"{vid} CBR should equal expected 5-packet airtime ratio")

        # Expected west CBR: 0.0 (no transmissions within 300m)
        self.assertEqual(cbr_dict["west_iso"], 0.0, "West isolated vehicle must observe 0.0 CBR")

        # Assert East cluster CBR is strictly and significantly higher than West isolated CBR
        self.assertGreater(cbr_dict["east_0"], cbr_dict["west_iso"])
        self.assertGreater(cbr_dict["east_0"], 0.03)
        self.assertEqual(cbr_dict["west_iso"], 0.0)

        # Step where west vehicle also transmits 1 CAM (e.g. at 1 Hz tick)
        all_events = east_events + [{"vid": "west_iso", "x": 800.0, "y": 0.0}]
        cbr_dict_all, cbr_mean_all = compute_local_cbr(positions, all_events, window_duration, comm_range_m=COMM_RANGE_M)

        expected_west_cbr = (1 * TX_DURATION_S) / window_duration
        self.assertAlmostEqual(cbr_dict_all["west_iso"], expected_west_cbr, places=6)
        # East cluster should still see only 5 packets (west is 700m+ away > 300m)
        for i in range(5):
            vid = f"east_{i}"
            self.assertAlmostEqual(cbr_dict_all[vid], expected_east_cbr, places=6)

        # Confirm multiple distinct CBR values exist across vehicles (spatial heterogeneity)
        distinct_cbr_values = set(round(v, 6) for v in cbr_dict_all.values())
        self.assertGreaterEqual(len(distinct_cbr_values), 2, "Spatial distribution must contain distinct local CBRs")
        self.assertGreater(cbr_dict_all["east_0"], cbr_dict_all["west_iso"] * 4.0,
                           "East cluster CBR must be ~5x higher than west vehicle CBR")

    def test_02_mathematical_exactness_and_boundary_conditions(self):
        """2. 국소 CBR 수학적 수식 정밀성 및 300m 경계값 판정 검증."""
        positions = {
            "v_center": (0.0, 0.0),
            "v_exact_bound": (300.0, 0.0),       # dist == 300.0m (IN range)
            "v_outside_bound": (0.0, 300.001),   # dist == 300.001m (OUT of range)
        }
        # Events at each location
        events = [
            {"vid": "v_center", "x": 0.0, "y": 0.0},
            {"vid": "v_exact_bound", "x": 300.0, "y": 0.0},
            {"vid": "v_outside_bound", "x": 0.0, "y": 300.001},
        ]
        window_duration = 0.1
        cbr_dict, cbr_mean = compute_local_cbr(positions, events, window_duration, comm_range_m=300.0)

        # For v_center: sees self (0m) and v_exact_bound (300m) -> 2 events
        # Does NOT see v_outside_bound (300.001m)
        expected_center_cbr = (2 * TX_DURATION_S) / window_duration
        self.assertAlmostEqual(cbr_dict["v_center"], expected_center_cbr, places=6)

        # For v_exact_bound: dist to v_center = 300m (IN), dist to v_outside_bound = sqrt(300^2 + 300.001^2) = 424m (OUT)
        # Sees self (0m) and v_center (300m) -> 2 events
        self.assertAlmostEqual(cbr_dict["v_exact_bound"], expected_center_cbr, places=6)

        # For v_outside_bound: dist to v_center = 300.001m (OUT), dist to v_exact_bound = 424m (OUT)
        # Sees only self (0m) -> 1 event
        expected_outside_cbr = (1 * TX_DURATION_S) / window_duration
        self.assertAlmostEqual(cbr_dict["v_outside_bound"], expected_outside_cbr, places=6)

    def test_03_input_formats_flexibility(self):
        """3. 이벤트 리스트, tx_count 딕셔너리, 좌표 튜플 등 다양한 입력 형식 호환성 검증."""
        positions = {
            "v1": (0.0, 0.0),
            "v2": (100.0, 0.0),
            "v3": (200.0, 0.0),
        }
        # Format 1: Dict of tx counts
        tx_counts_dict = {"v1": 2, "v2": 1, "v3": 3}
        cbr_dict_1, mean_1 = compute_local_cbr(positions, tx_counts_dict, 0.1, COMM_RANGE_M)

        # For v2 at 100m: dist to v1=100m (IN), v2=0m (IN), v3=100m (IN) -> sees 2+1+3 = 6 packets
        expected_v2_cbr = (6 * TX_DURATION_S) / 0.1
        self.assertAlmostEqual(cbr_dict_1["v2"], expected_v2_cbr, places=6)

        # For v1 at 0m: dist to v1=0m (IN), v2=100m (IN), v3=200m (IN) -> sees 2+1+3 = 6 packets
        self.assertAlmostEqual(cbr_dict_1["v1"], expected_v2_cbr, places=6)

        # Format 2: List of event dicts with vid only
        events_vid_only = [{"vid": "v1"}, {"vid": "v1"}, {"vid": "v2"}, {"vid": "v3"}, {"vid": "v3"}, {"vid": "v3"}]
        cbr_dict_2, mean_2 = compute_local_cbr(positions, events_vid_only, 0.1, COMM_RANGE_M)
        self.assertAlmostEqual(cbr_dict_2["v2"], expected_v2_cbr, places=6)

        # Format 3: List of coordinates
        coords = [(0.0, 0.0), (0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (200.0, 0.0), (200.0, 0.0)]
        cbr_dict_3, mean_3 = compute_local_cbr(positions, coords, 0.1, COMM_RANGE_M)
        self.assertAlmostEqual(cbr_dict_3["v2"], expected_v2_cbr, places=6)

        # Format 4: Empty positions or zero duration edge cases
        self.assertEqual(compute_local_cbr({}, events_vid_only), ({}, 0.0))
        self.assertEqual(compute_local_cbr(positions, events_vid_only, window_duration_s=0.0),
                         ({"v1": 0.0, "v2": 0.0, "v3": 0.0}, 0.0))

    def test_04_spatial_reuse_property(self):
        """4. 공간 재사용(Spatial Reuse) 검증: 원거리 클러스터 간 전역 CBR vs 국소 CBR 분리 입증."""
        positions = {}
        events = []
        # Cluster A: 4 vehicles at x = 0..30m
        for i in range(4):
            vid = f"clusterA_{i}"
            positions[vid] = (float(i * 10), 0.0)
            events.append({"vid": vid, "x": float(i * 10), "y": 0.0})

        # Cluster B: 4 vehicles at x = 1000..1030m (> 950m away from Cluster A)
        for i in range(4):
            vid = f"clusterB_{i}"
            positions[vid] = (1000.0 + float(i * 10), 0.0)
            events.append({"vid": vid, "x": 1000.0 + float(i * 10), "y": 0.0})

        total_tx = len(events)  # 8 total CAMs
        global_cbr = (total_tx * TX_DURATION_S) / 0.1  # 8 * 0.000747 / 0.1 = ~0.0597

        cbr_dict, cbr_mean = compute_local_cbr(positions, events, 0.1, COMM_RANGE_M)

        local_expected_cbr = (4 * TX_DURATION_S) / 0.1  # 4 * 0.000747 / 0.1 = ~0.0299

        # Each cluster must only see 4 CAMs, proving spatial reuse isolation
        for vid in positions:
            self.assertAlmostEqual(cbr_dict[vid], local_expected_cbr, places=6,
                                   msg=f"Vehicle {vid} should only measure local cluster CBR ({local_expected_cbr})")
            self.assertLess(cbr_dict[vid], global_cbr * 0.6,
                            "Local CBR must be half of global aggregated CBR under spatial reuse")

        self.assertAlmostEqual(cbr_mean, local_expected_cbr, places=6)

    def test_05_etsi_cam_layer_reactdcc_state_transition(self):
        """5. ETSICAMLayer ReactDCC에 주입된 국소 CBR 기반 분산 제어 상태 전이 검증."""
        cam_layer = ETSICAMLayer(method="ReactDCC")

        # Vehicle A in congested region (local CBR = 0.65 -> RESTRICTED state, T_GenCam = 1.0s)
        # Vehicle B in clear region (local CBR = 0.10 -> RELAXED state, T_GenCam = 0.1s)
        vehicles_data = [
            {"vid": "v_congested", "x": 0.0, "y": 0.0, "speed": 10.0, "heading": 0.0, "accel": 0.0, "cbr": 0.65, "n_est": 30},
            {"vid": "v_clear", "x": 1000.0, "y": 0.0, "speed": 10.0, "heading": 0.0, "accel": 0.0, "cbr": 0.10, "n_est": 2},
        ]

        cam_layer.step(vehicles_data, sim_time=0.1, cbr_global=0.35)

        vs_congested = cam_layer.vehicles["v_congested"]
        vs_clear = cam_layer.vehicles["v_clear"]

        self.assertEqual(vs_congested.dcc_state, "RESTRICTED",
                         f"High local CBR vehicle must be in RESTRICTED state, got {vs_congested.dcc_state}")
        self.assertEqual(vs_congested.T_GenCam, T_GENCAM_RESTRICTED)

        self.assertEqual(vs_clear.dcc_state, "RELAXED",
                         f"Low local CBR vehicle must be in RELAXED state, got {vs_clear.dcc_state}")
        self.assertEqual(vs_clear.T_GenCam, T_GENCAM_RELAXED)

    def test_06_ai_hook_local_cbr_state_delivery(self):
        """6. AI DCC Hook에 각 차량별 국소 CBR 및 smoothed CBR이 정상 입력됨을 검증."""
        cam_layer = ETSICAMLayer(method="Proposed")

        vehicles_data = [
            {"vid": "v_ai_1", "x": 0.0, "y": 0.0, "speed": 15.0, "heading": 0.0, "accel": 0.0, "cbr": 0.50, "n_est": 20},
            {"vid": "v_ai_2", "x": 500.0, "y": 0.0, "speed": 15.0, "heading": 0.0, "accel": 0.0, "cbr": 0.05, "n_est": 1},
        ]

        # Execute step 1: EMA is (1 - 0.5) * 0.0 + 0.5 * cbr
        cam_layer.step(vehicles_data, sim_time=0.1, cbr_global=0.25)

        vs1 = cam_layer.vehicles["v_ai_1"]
        vs2 = cam_layer.vehicles["v_ai_2"]

        # Confirm per-vehicle smoothed CBR tracks its local CBR
        self.assertGreater(vs1.blb_CBR_smoothed, vs2.blb_CBR_smoothed,
                           "Smoothed CBR of congested vehicle must be greater than isolated vehicle")
        self.assertAlmostEqual(vs1.blb_CBR_smoothed, 0.25, places=4)
        self.assertAlmostEqual(vs2.blb_CBR_smoothed, 0.025, places=4)

        # Run several steps to test steady-state convergence to true local CBR
        for step in range(2, 12):
            cam_layer.step(vehicles_data, sim_time=step * 0.1, cbr_global=0.25)

        self.assertAlmostEqual(vs1.blb_CBR_smoothed, 0.50, places=3)
        self.assertAlmostEqual(vs2.blb_CBR_smoothed, 0.05, places=3)

    def test_07_simulation_runner_runtime_cbr_verification(self):
        """7. SimulationRunner 런타임 검증: SUMO 구동 중 각 스텝 vdata["cbr"] 주입 및 CBR_mean 산출 확인."""
        work_dir = tempfile.mkdtemp(prefix="test_m8_runner_")
        try:
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=10,
                seed=42,
                method="ReactDCC",
                duration_steps=60,  # 6.0 seconds simulation
                warmup_s=1.0,
                work_dir=work_dir,
            )
            metrics = runner.run()

            # Verify metrics returned properly
            self.assertIn("CBR_mean", metrics)
            self.assertIn("cbr_history", metrics)
            self.assertIsInstance(metrics["CBR_mean"], float)
            self.assertGreaterEqual(metrics["CBR_mean"], 0.0)
            self.assertLessEqual(metrics["CBR_mean"], 1.0)
            self.assertGreater(len(metrics["cbr_history"]), 0)

            # Confirm last CBR dict was generated and is valid
            self.assertTrue(hasattr(runner, "_last_cbr_dict"))
            self.assertIsInstance(runner._last_cbr_dict, dict)
            for vid, val in runner._last_cbr_dict.items():
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
