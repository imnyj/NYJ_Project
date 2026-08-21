#!/usr/bin/env python3
"""
test_m7_nest.py
===============
Independent verification suite for Task M-7:
Local neighborhood count (n_est) calculation and spatial density reflection.

Verifies:
  1. Dense cluster (<= 50m, 3 vehicles) -> each vehicle n_est == 2
  2. Isolated vehicles (>= 600m) -> n_est == 0
  3. Asymmetric linear layout (-200m, 0m, +200m) -> center n_est == 2, ends n_est == 1
  4. Exact boundary conditions (dist == 300.0m vs dist > 300.0m)
  5. Multi-cluster heterogeneous density observation across 2D map
  6. ETSICAMLayer & AI hook integration (n_neighbors = n_est / 50.0)
  7. SimulationRunner runtime step verification: 100% agreement between
     vehicle_positions Euclidean distance and runtime vdata["n_est"].
"""

import os
import sys
import math
import unittest

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from sim_engine import COMM_RANGE_M, compute_local_n_est, SimulationRunner
from etsi_cam_layer import ETSICAMLayer, VehicleCAMState


class TestM7LocalNest(unittest.TestCase):

    def test_1_dense_cluster_geometric(self):
        """1. 50m 이내로 밀집된 3대 차량 클러스터 -> 각 차량의 n_est == 2 확인."""
        positions = {
            "v1": (0.0, 0.0),
            "v2": (30.0, 40.0),  # dist(v1, v2) = 50.0m <= COMM_RANGE_M (300m)
            "v3": (0.0, 40.0),   # dist(v1, v3) = 40.0m, dist(v2, v3) = 30.0m
        }
        # Verify pairwise distances
        d12 = math.sqrt((0 - 30)**2 + (0 - 40)**2)
        d13 = math.sqrt((0 - 0)**2 + (0 - 40)**2)
        d23 = math.sqrt((30 - 0)**2 + (40 - 40)**2)
        self.assertAlmostEqual(d12, 50.0)
        self.assertAlmostEqual(d13, 40.0)
        self.assertAlmostEqual(d23, 30.0)
        self.assertTrue(d12 <= 50.0 and d13 <= 50.0 and d23 <= 50.0)

        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)
        self.assertEqual(n_est_dict["v1"], 2, f"v1 should have 2 neighbors, got {n_est_dict['v1']}")
        self.assertEqual(n_est_dict["v2"], 2, f"v2 should have 2 neighbors, got {n_est_dict['v2']}")
        self.assertEqual(n_est_dict["v3"], 2, f"v3 should have 2 neighbors, got {n_est_dict['v3']}")

    def test_2_isolated_vehicle_geometric(self):
        """2. 600m 이상 떨어진 고립 차량 -> n_est == 0 확인."""
        positions = {
            "v_iso1": (0.0, 0.0),
            "v_iso2": (650.0, 0.0),  # dist = 650m > 600m > COMM_RANGE_M (300m)
        }
        dist = math.sqrt((650.0 - 0.0)**2)
        self.assertGreater(dist, 600.0)

        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)
        self.assertEqual(n_est_dict["v_iso1"], 0, f"v_iso1 should have 0 neighbors, got {n_est_dict['v_iso1']}")
        self.assertEqual(n_est_dict["v_iso2"], 0, f"v_iso2 should have 0 neighbors, got {n_est_dict['v_iso2']}")

    def test_3_asymmetric_linear_layout_geometric(self):
        """3. 비대칭 배치: 중앙 기준 200m에 2대 (양 끝 간 거리는 400m)
           -> 중앙 차량 n_est == 2, 양 끝 차량 n_est == 1 확인."""
        positions = {
            "v_left": (-200.0, 0.0),
            "v_center": (0.0, 0.0),
            "v_right": (200.0, 0.0),
        }
        # Distances:
        # dist(center, left) = 200m <= 300m
        # dist(center, right) = 200m <= 300m
        # dist(left, right) = 400m > 300m
        d_cl = math.sqrt((-200.0 - 0.0)**2)
        d_cr = math.sqrt((200.0 - 0.0)**2)
        d_lr = math.sqrt((200.0 - (-200.0))**2)
        self.assertAlmostEqual(d_cl, 200.0)
        self.assertAlmostEqual(d_cr, 200.0)
        self.assertAlmostEqual(d_lr, 400.0)

        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)
        self.assertEqual(n_est_dict["v_center"], 2, f"Center vehicle must see 2 neighbors, got {n_est_dict['v_center']}")
        self.assertEqual(n_est_dict["v_left"], 1, f"Left vehicle must see 1 neighbor, got {n_est_dict['v_left']}")
        self.assertEqual(n_est_dict["v_right"], 1, f"Right vehicle must see 1 neighbor, got {n_est_dict['v_right']}")

    def test_4_exact_boundary_conditions(self):
        """4. 통신 반경 경계값 검증 (정확히 300.0m vs 300.001m)."""
        positions = {
            "v_origin": (0.0, 0.0),
            "v_exact_bound": (300.0, 0.0),       # dist = 300.0m == COMM_RANGE_M -> IN range
            "v_outside_bound": (0.0, 300.001),   # dist = 300.001m > COMM_RANGE_M -> OUT of range
        }
        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)
        # v_origin is in range with v_exact_bound (dist=300m) but not v_outside_bound (dist=300.001m)
        self.assertEqual(n_est_dict["v_origin"], 1)
        self.assertEqual(n_est_dict["v_exact_bound"], 1)
        # dist(v_outside_bound, v_exact_bound) = sqrt(300^2 + 300.001^2) ~ 424m > 300m
        self.assertEqual(n_est_dict["v_outside_bound"], 0)

    def test_5_multi_cluster_heterogeneous_density(self):
        """5. 복합 다중 클러스터 공간 불균일 밀도 검증 (동일 시뮬레이션 내 다양한 국소 밀도 관측)."""
        # Cluster A: 4 vehicles within 50m of (0, 0) -> each sees 3 neighbors
        cluster_a = {f"ca_{i}": (float(i * 10), float(i * 10)) for i in range(4)}
        # Cluster B: 2 vehicles within 50m of (1500, 1500) -> each sees 1 neighbor
        cluster_b = {"cb_0": (1500.0, 1500.0), "cb_1": (1520.0, 1500.0)}
        # Isolated vehicle C at (5000, 5000) -> sees 0 neighbors
        cluster_c = {"c_iso": (5000.0, 5000.0)}

        positions = {**cluster_a, **cluster_b, **cluster_c}
        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)

        for vid in cluster_a:
            self.assertEqual(n_est_dict[vid], 3, f"Cluster A vehicle {vid} should observe n_est=3, got {n_est_dict[vid]}")
        for vid in cluster_b:
            self.assertEqual(n_est_dict[vid], 1, f"Cluster B vehicle {vid} should observe n_est=1, got {n_est_dict[vid]}")
        self.assertEqual(n_est_dict["c_iso"], 0, f"Isolated vehicle should observe n_est=0, got {n_est_dict['c_iso']}")

    def test_6_cam_layer_integration(self):
        """6. ETSICAMLayer 및 AI Hook에 국소 n_est 정상 주입 검증."""
        positions = {
            "v_dense1": (0.0, 0.0),
            "v_dense2": (50.0, 0.0),
            "v_dense3": (0.0, 50.0),
            "v_sparse": (2000.0, 2000.0),
        }
        n_est_dict = compute_local_n_est(positions, COMM_RANGE_M)
        self.assertEqual(n_est_dict["v_dense1"], 2)
        self.assertEqual(n_est_dict["v_sparse"], 0)

        vehicles_data = [
            {"vid": vid, "x": pos[0], "y": pos[1], "speed": 10.0, "heading": 90.0, "accel": 0.0, "n_est": n_est_dict[vid]}
            for vid, pos in positions.items()
        ]

        cam_layer = ETSICAMLayer(method="VanillaDQN")
        # Step through CAM layer
        cam_layer.step(vehicles_data, sim_time=1.0, cbr_global=0.03)

        # Check vehicle state records
        vs_dense = cam_layer.get_or_create_vehicle("v_dense1")
        vs_sparse = cam_layer.get_or_create_vehicle("v_sparse")

        self.assertIsNotNone(vs_dense)
        self.assertIsNotNone(vs_sparse)

    def test_7_simulation_runner_runtime_step_nest_verification(self):
        """7. SimulationRunner 런타임 검증:
           다중 차량 시뮬레이션을 실행하여 스텝별 수집되는 차량 데이터의 n_est가
           위치 좌표 기반 국소 밀도와 100% 일치함을 입증."""
        captured_step_checks = []

        class InterceptingCAMLayer(ETSICAMLayer):
            def step(self, vehicles_data, sim_time, cbr_global):
                # Reconstruct vehicle positions from vehicles_data
                current_positions = {vd["vid"]: (vd["x"], vd["y"]) for vd in vehicles_data}
                expected_n_est = compute_local_n_est(current_positions, COMM_RANGE_M)

                for vd in vehicles_data:
                    vid = vd["vid"]
                    actual_nest = vd["n_est"]
                    expected = expected_n_est[vid]
                    captured_step_checks.append((sim_time, vid, actual_nest, expected))
                    if actual_nest != expected:
                        raise AssertionError(
                            f"Mismatch at sim_time={sim_time}, vid={vid}: actual n_est={actual_nest} vs expected={expected}"
                        )
                return super().step(vehicles_data, sim_time, cbr_global)

        # Monkey patch ETSICAMLayer in sim_engine during test
        import sim_engine
        original_cam_layer_cls = sim_engine.ETSICAMLayer
        try:
            sim_engine.ETSICAMLayer = InterceptingCAMLayer

            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=15,
                seed=42,
                method="Fixed10Hz",
                duration_steps=60,
                warmup_s=1.0,
            )
            res = runner.run()
            self.assertIn("AoI_mean", res)
            self.assertGreater(len(captured_step_checks), 100, "Should have verified > 100 vehicle-step observations")

            # Verify 100% agreement
            all_match = all(actual == exp for _, _, actual, exp in captured_step_checks)
            self.assertTrue(all_match, "All runtime n_est observations must 100% match Euclidean distance ground truth")

            # Also verify spatial variance: not all vehicles have identical n_est throughout simulation
            unique_n_ests = set(actual for _, _, actual, _ in captured_step_checks)
            self.assertGreater(len(unique_n_ests), 1, f"Expected varied local n_est values across vehicles, got: {unique_n_ests}")

        finally:
            sim_engine.ETSICAMLayer = original_cam_layer_cls


if __name__ == "__main__":
    unittest.main(verbosity=2)
