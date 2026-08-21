# Handoff Report — Task M-7: n_est 국소 이웃 수 계산 정합 및 공간 밀도 반영

## 1. Observation (직접 관찰 사실)
- **기존 전역 차량수 할당 결함**:
  과거 `code/sim_engine.py` (L397) 및 `code/oracle_generator.py` (L453)에서 `n_est`를 `len(vehicle_ids) - 1`로 계산하여 전역 맵 전체 차량 수를 모든 차량에 동일하게 일괄 할당하던 결함이 존재함. 이로 인해 차량의 지리적 위치나 주변 혼잡도와 무관하게 모든 차량이 동일한 이웃 수를 관측하여 "국소 공간 밀도" 특징이 완전히 상실되었음.
- **통신 반경 기준 국소 이웃 계산 요구**:
  IEEE 802.11p 및 ETSI DCC 규격 상 공칭 통신 반경(`COMM_RANGE_M = 300.0m`) 내의 실제 이웃 차량 수($dist(vid, oid) = \sqrt{(x_v - x_o)^2 + (y_v - y_o)^2} \le COMM\_RANGE\_M$)만 카운트하여 각 차량의 `vdata["n_est"]`에 주입해야 함.
- **모듈화 및 일관성 부재**:
  `sim_engine.py`와 `oracle_generator.py`에 공통으로 사용할 수 있는 표준 국소 이웃 계산 함수 `compute_local_n_est`가 독립적으로 정의되어 있지 않았음.

## 2. Logic Chain (논리적 추론 체계)
1. `compute_local_n_est(vehicle_positions: Dict[str, Tuple[float, float]], comm_range_m: float = COMM_RANGE_M) -> Dict[str, int]` 모듈 함수를 `code/sim_engine.py`에 정의함.
2. 모든 차량 쌍 간의 2차원 유클리드 거리를 계산하여 자신을 제외하고 $dist \le comm\_range\_m$ 범위 내에 존재하는 이웃 차량들의 개수를 정확히 집계함.
3. `SimulationRunner.run()` 루프 내에서 스텝마다 `n_est_dict = compute_local_n_est(vehicle_positions, COMM_RANGE_M)`를 호출하여 `vdata["n_est"] = n_est_dict.get(vid, 0)`로 주입함. 이를 통해 `ETSICAMLayer.step()` 및 AI Hook, Bhattacharyya DCC 제어기가 차량별 고유한 국소 밀도를 관측하도록 보장함.
4. `code/oracle_generator.py`에서도 `compute_local_n_est`를 import하여 `vehicles_data` 구성 및 오라클 상태 스냅샷 수집 시 동일한 국소 밀도를 계산하도록 통일함.
5. `code/test_m7_nest.py`를 작성하여 50m 클러스터, 600m 이상 고립 차량, 200m/400m 비대칭 배치, 300.0m 경계값, 복합 다중 클러스터, `SimulationRunner` 런타임 100% 인터셉션 검증을 수행함.

## 3. Caveats (주의사항 및 한계)
- No caveats. 모든 수정은 완벽히 동작하며 기하학적 배치 검증 및 런타임 시뮬레이션 검증 100% PASS를 달성하였음.

## 4. Conclusion (최종 결론)
- M-7 작업(통신 반경 300m 기준 국소 이웃 수 `n_est` 계산 정합 및 공간 밀도 반영)이 100% 성공적으로 완료됨.
- 신규 작성된 독립 검증 스위트 `code/test_m7_nest.py` (7개 테스트) 및 전체 회귀 테스트 스위트 (38개 테스트) 전체가 정상 통과(Exit Code 0)함을 입증함.
- 마스터 작업 목록 `idea/paper4_code_fix_tasklist.md`에 M-7 완료 상태 갱신 완료.

## 5. Verification Method (독립 검증 방법)
```bash
# 1. M-7 독립 검증 스위트 실행 (7개 테스트 100% PASS)
python3 code/test_m7_nest.py

# 2. 전체 회귀 테스트 스위트 일괄 실행 (모두 PASS)
python3 code/test_c3_reward.py && \
python3 code/test_c1_c2_wiring.py && \
python3 code/test_h4_grid.py && \
python3 code/test_h5_ablation.py && \
python3 code/test_h6_tabular.py && \
python3 code/test_m7_nest.py
```
