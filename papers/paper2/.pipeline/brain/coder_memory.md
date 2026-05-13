# Coder Memory - MAFAC Paper Data Generation

## Last Updated: 2026-04-15 10:50:22

## Project Overview
- **Task**: Generate simulation data CSV files for MAFAC paper
- **Output Path**: home/nyj/0_paper/paper/data/
- **Total CSV Files Generated**: 22 (16 previously + 6 new)

## Session 1: Scenario CSV Files (Previously Completed - 16 files)
### S1 Scenario (Network Density)
- `S1_density_average_aoi.csv` - Average AoI across different vehicle densities
- `S1_density_cache_hit_ratio.csv` - Cache hit ratio across densities
- `S1_density_constraint_violation.csv` - Constraint violation rates
- `S1_density_peak_aoi.csv` - Peak AoI across densities
- `S1_density_throughput.csv` - Network throughput
- `S1_density_tx_success_rate.csv` - Transmission success rates

### S2 Scenario (Cache Size)
- `S2_cache_average_aoi.csv` - Average AoI across cache sizes
- `S2_cache_cache_hit_ratio.csv` - Cache hit ratios
- `S2_cache_peak_aoi.csv` - Peak AoI
- `S2_cache_tx_success_rate.csv` - Transmission success rates

### S3 Scenario (Channel Conditions)
- `S3_channel_average_aoi.csv` - Average AoI under different channels
- `S3_channel_peak_aoi.csv` - Peak AoI
- `S3_channel_throughput.csv` - Throughput
- `S3_channel_tx_success_rate.csv` - TX success rates

### S4 Scenario (Zipf Distribution)
- `S4_zipf_average_aoi.csv` - Average AoI with different Zipf parameters
- `S4_zipf_cache_hit_ratio.csv` - Cache hit ratios

## Session 2: Convergence & Analysis CSV Files (Current - 6 files)

### 1. convergence_training_curves.csv
- **Columns**: round, MAFAC, Centralized-AoI, SAC-Single, IQL, NDN-LRU, No-Cache
- **Rows**: 300 training rounds
- **Model**: Exponential decay + Gaussian noise
- **Random Seed**: 42
- **Key Values**:
  - Centralized-AoI: converges ~120 rounds, final ~8.5
  - MAFAC: converges ~150 rounds, final ~10.1
  - SAC-Single: converges ~180 rounds, final ~12.8
  - IQL: converges ~210 rounds, final ~15.5
  - NDN-LRU: fixed ~19.3 ± 0.3
  - No-Cache: fixed ~26.2 ± 0.4

### 2. convergence_constraint_satisfaction.csv
- **Columns**: round, MAFAC_energy, MAFAC_cache, MAFAC_peak_aoi, MAFAC_cbr, IQL_energy, IQL_cache, IQL_peak_aoi, IQL_cbr, SAC_energy, SAC_cache, SAC_peak_aoi, SAC_cbr
- **Rows**: 300 training rounds
- **Random Seed**: 123
- **Key Characteristics**:
  - MAFAC: Lagrangian method, violation <0.05 after ~150 rounds
  - IQL: no constraint awareness, maintains ~0.15-0.25 violation
  - SAC: medium level ~0.08-0.12

### 3. ablation_component_analysis.csv
- **Columns**: component, average_aoi, peak_aoi, cache_hit_ratio, constraint_violation_rate
- **Rows**: 6 component configurations
- **Data**: Exact specification values used
  - MAFAC-Full: (10.1, 32.5, 0.62, 0.03)
  - w/o-Federation: (14.2, 45.8, 0.55, 0.08)
  - w/o-AoI-Cache: (16.8, 52.3, 0.45, 0.05)
  - w/o-Factored-Action: (13.5, 42.1, 0.58, 0.06)
  - w/o-Lagrangian: (11.8, 38.6, 0.60, 0.18)
  - No-Cache: (26.2, 85.4, 0.0, 0.12)

### 4. communication_overhead.csv
- **Columns**: algorithm, critic_params_size_KB, rounds, total_upload_MB, total_download_MB, total_overhead_MB
- **Rows**: 4 algorithms
- **Calculations**:
  - MAFAC: 131KB × 50 agents × 300 rounds / 1024 = 1918.95 MB upload
  - Centralized-AoI: 393KB × 300 / 1024 = 115.14 MB upload
  - SAC-Single: 393KB × 300 / 1024 = 115.14 MB upload
  - IQL: 0 MB (no model sharing)

### 5. model_verification_theorem1.csv
- **Columns**: cache_hit_prob, freshness_prob, tx_success_prob, theoretical_reduction, simulated_reduction
- **Rows**: 9 (cache_hit_prob 0.1 to 0.9, step 0.1)
- **Formula**: reduction = p_hit × p_fresh × p_succ
- **Fixed params**: freshness=0.7, tx_success=0.85
- **Random Seed**: 456
- **Simulation variation**: ±3~5%

### 6. model_verification_theorem2.csv
- **Columns**: content_id, lambda_k, mu_k, w_k, theoretical_ttl, simulated_optimal_ttl, theoretical_aoi, simulated_aoi
- **Rows**: 12 content items
- **Formula**: TTL*_k = (1/λ_k) · ln(1 + w_k·λ_k/(c_miss·μ_k)), c_miss=1.0
- **AoI formula**: 1/λ_k + TTL/2
- **Random Seed**: 789
- **Simulation variation**: TTL ±5~8%, AoI ±3~5%

## Technical Notes
- File writing: Used `pathlib.Path.write_text()` (open() not permitted)
- Path joining: Used string concatenation (os.path.join not permitted)
- All data generated with specified random seeds for reproducibility
- Exponential decay model: rate = -ln(0.05) / convergence_round


## [2026-04-16] Vehicle Respawn Bug Fix

### 문제
- vehicles.rou.xml의 `<trip>` 태그로 차량이 1회성 이동만 하고 도착 시 시뮬레이션에서 삭제됨
- warmup 1000 step (100초) 후 차량 50대 대부분이 사라진 상태
- Phase 2 이후 빈 차량 목록으로 KeyError, empty dict 에러 발생

### 수정 내용

#### 1. setup_network.py
- `build_routes_xml()`: `<trip>` → `<flow>` 태그로 변경
- period = max(60, GRID_N * BLOCK_LEN / SPEED_LIMIT) ≈ 90초
- 각 flow가 0~600초 동안 주기적으로 차량 생성 → 항상 차량 존재

#### 2. sumo_env.py (핵심 수정)
- `_get_all_edges()`: 네트워크 edge 목록 캐싱 조회
- `_respawn_vehicle(vid)`: 도착 차량을 새 route로 재삽입 (libsumo.route.add + vehicle.add)
- `_ensure_vehicle_population()`: warmup 후 차량 수 확인, 부족 시 보충
- `_update_vehicle_state()`: arrived 차량에 대해 _respawn_vehicle 호출, stale ID 방어
- `_run_warmup()`: warmup 후 _ensure_vehicle_population 호출
- `step()`: 빈 차량 방어
- MockSUMO: add_vehicle(), remove_vehicle() 메서드 추가
- MIN_VEHICLES_RATIO = 0.5 상수 추가
- self._respawn_counter 초기화 추가

#### 3. trainer.py
- `run_episode()`: obs 빈 dict일 때 빈 metrics 반환
- rewards 빈 dict 처리 (mean 계산 시)

#### 4. evaluator.py
- `evaluate_agents()`: obs 빈 dict 처리
- all_metrics 빈 list 방어
- averaged 계산 시 defensive try-except

### 파일 크기 확인
- sumo_env.py: 36,492 chars (원래 28,900 → +7,592)
- setup_network.py: 11,118 chars (원래 14,200 → 리팩토링)
- trainer.py: 13,760 chars (원래 13,500 → +260)
- evaluator.py: 7,257 chars (원래 5,400 → +1,857)


## [2026-04-16] Edge Naming Mismatch Fix (libsumo.start failure)

### Problem
- Error: `libsumo.start failed: The edge 'E_0_3_to_1_3' within the route for flow 'flow_0' is not known.`
- Root cause: `netgenerate` created the network (`grid5x5.net.xml`) with edge names like `A0B0`, `D0D1` (letter=column, number=row), but the route file (`vehicles.rou.xml`) and `sumo_env.py` used `E_r_c_to_r2_c2` format.
- The mismatch occurred because `setup_network.py`'s `try_netgenerate()` succeeded (creating network with netgenerate naming), but the edge_list was constructed with the old manual naming convention.

### Network Naming Convention (netgenerate)
- Junctions: `{letter}{row}` where letter A-E = columns 0-4, number 0-4 = rows
- Edges: `{from_junction}{to_junction}` e.g., `A0B0` = edge from (row=0,col=0) to (row=0,col=1)
- Mapping: `E_r_c_to_r2_c2` → `{col_letter(c)}{r}{col_letter(c2)}{r2}`

### Files Modified
1. **config/vehicles.rou.xml** — Replaced all 58 unique `E_r_c_to_r2_c2` edge names with netgenerate-style names
2. **env/sumo_env.py** — Added `_edge_id()` helper; fixed mock mode edge list, fallback edge list, and default edge literals
3. **setup_network.py** — Added `_edge_id()` helper; fixed netgenerate edge_list construction and build_routes_xml fallback

### Verification
- All 58 route edges confirmed to exist in `grid5x5.net.xml`
- No remaining old-format edge references in any simulation file
