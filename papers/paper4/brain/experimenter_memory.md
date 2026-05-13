# Experimenter Memory — brain/experimenter_memory.md

---

## [2026-05-08] [Stage 1: skeleton] 세션 요약
- paper4 sim/ 디렉토리 구조 생성
- 모듈 스켈레톤 작성 완료

---

## [2026-05-08] [Stage 2: implement] 세션 1

### 작성 완료 모듈 (5개)

#### sim_engine.py (461 lines)
- **위치**: `/home/imnyj/papers/paper4/sim/sim_engine.py`
- **핵심 클래스**: `SimulationRunner(scenario, n_vehicles, seed, method, method_params, duration_steps, warmup_s, work_dir)`
- **의존성**: libsumo, etsi_cam_layer, aoi_tracker
- **채널 모델**: 802.11p Nakagami-m (m=3) + log-distance path loss, 5.9 GHz, 3 Mbps BPSK 1/2
- **주요 함수**:
  - `reception_probability(dist_m, p_tx_dbm)` — Nakagami-m 기반 수신 확률
  - `compute_cbr(vehicle_positions, cam_events, n_vehicles, step_len)` — CBR 추정
  - `simulate_receptions(cam_events, vehicle_positions, cbr, rng)` — 채널 수신 시뮬
  - `generate_urban_grid_net(output_path)` — 500m 그리드 SUMO 네트워크 생성
  - `generate_highway_net(output_path)` — 고속도로 시나리오 네트워크 생성
  - `generate_routes(net_path, route_path, n_vehicles, duration, seed, scenario)` — 차량 라우팅
  - `generate_sumocfg(...)` — SUMO config 파일 생성
- **반환 메트릭**: AoI_mean, CBR_mean, PDR_mean, energy_efficiency, ETSI_compliance, runtime_sec, n_cam_events

#### etsi_cam_layer.py
- **위치**: `/home/imnyj/papers/paper4/sim/etsi_cam_layer.py`
- **핵심 클래스**: `ETSICAMLayer(method, method_params)`, `VehicleCAMState`
- **구현된 방법론**:
  - **BL-A**: ETSI DCC Reactive (3-state: Relaxed/Active/Restricted, CBR 임계값 0.40/0.60)
  - **BL-B**: Simplified Adaptive (CBR-tracking proportional controller, cbr_target 파라미터)
  - **BL-C**: Bhattacharyya2024 Variable Beacon (CBR + neighbour density lookup table)
  - **BL-D**: Fixed 10 Hz (T_GenCam = 0.1 s 고정)
- **ETSI 트리거 조건**: ΔHeading≥4°, ΔPos≥4m, ΔSpeed≥0.5m/s, T_GenCam 타이머 만료
- **상수**: T_GENCAM_MIN=0.1s, T_GENCAM_MAX=1.0s, PTX_DEFAULT=+20 dBm

#### aoi_tracker.py
- **위치**: `/home/imnyj/papers/paper4/sim/aoi_tracker.py`
- **핵심 클래스**: `AoITracker(comm_range_m, eval_start_time)`
- **AoI 정의**: AoI_ij(t) = t_rx - t_gen (수신 측 staleness 누적)
- **메서드**: on_cam_sent(), on_cam_received(), step(), get_mean_aoi(), get_pdr()
- **평가 시작**: warmup 이후(eval_start_time=30.0s)부터 집계

#### sumo_networks/urban_grid.net.xml
- **위치**: `/home/imnyj/papers/paper4/sim/sumo_networks/urban_grid.net.xml`
- **구조**: 500m × 500m 그리드, 신호등 교차로
- **용도**: urban_grid 시나리오 기본 네트워크

#### sensitivity_runner.py (새로 작성, 이번 세션)
- **위치**: `/home/imnyj/papers/paper4/sim/sensitivity_runner.py`
- **역할**: SA1~SA4 민감도 분석 오케스트레이터
- **주요 함수**: `define_sweeps()`, `run_one()`, `run_sweep()`, `compute_summary()`, `save_summary()`
- **SA1**: n_vehicles ∈ [10, 20, 30, 50, 75, 100], method=BL-A, 3 seeds → 18 runs
- **SA2**: method ∈ [BL-A, BL-B, BL-C, BL-D], n=30, 3 seeds → 12 runs
- **SA3**: cbr_target ∈ [0.30, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70], BL-B, n=30, 3 seeds → 21 runs
- **SA4**: scenario ∈ [urban_grid, highway] × n ∈ [20, 30, 50] × 3 seeds → 18 runs

---

### SUMO 설정

| 항목 | 값 |
|------|-----|
| step-length | 0.1 s (100 ms) |
| duration | 3000 steps = 300 s |
| warmup | 30 s (ignore metrics during this period) |
| n_vehicles (base) | 30 |
| routing | random OD pairs, vehicle depart time uniform [0, duration/2] |
| collision | warn (non-fatal) |
| seed | per-run random seed |

---

### 출력 CSV 구조

**파일**: `/home/imnyj/papers/paper4/paper/data/{sweep_id}_results.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| sweep_id | str | SA1/SA2/SA3/SA4 |
| param_name | str | 변화시킨 파라미터 이름 |
| param_value | str | 해당 파라미터 값 |
| seed | int | 랜덤 시드 |
| AoI_mean | float | 평균 Age-of-Information (s) |
| CBR_mean | float | 평균 Channel Busy Ratio |
| PDR_mean | float | 평균 Packet Delivery Ratio |
| energy_efficiency | float | 에너지 효율 지표 |
| ETSI_compliance | float | ETSI EN 302 637-2 준수율 |
| runtime_sec | float | 실행 시간 (s) |
| n_cam_events | int | 총 CAM 이벤트 수 |
| status | str | ok / error |
| error | str | 오류 메시지 (ok면 빈 문자열) |

**집계 JSON**: `/home/imnyj/papers/paper4/paper/data/sensitivity_summary.json`
- 구조: `{sweep_id: {by_param_value: {pv: {AoI_mean_mean, AoI_mean_std, CBR_mean_mean, ...}}}}`

---

### 의존성

| 패키지 | 버전/비고 |
|--------|-----------|
| libsumo | SUMO Python bindings (libsumo.start, libsumo.simulationStep, ...) |
| sumolib | SUMO 네트워크 파싱 보조 |
| Python | 3.8+ |
| SUMO | 1.18+ (네트워크 생성 netconvert 또는 XML 직접 작성) |

---

### 백그라운드 실행 상태

- **SA3 sweep started at 12:59:40** (KST)
- **PID**: (nohup 백그라운드, start_new_session)
- **Log**: `/tmp/sa3.log`
- **예상 완료 시간**: SA3 = 21 runs × ~30-60s/run = ~10-20분
- **출력 예정**: `/home/imnyj/papers/paper4/paper/data/SA3_results.csv`
- **다음 호출에서**: `/tmp/sa3.log` 확인, SA3_results.csv 검증, SA1/SA2/SA4 실행 결정

---

### 다음 단계 (Stage 2 세션 2 예정)
1. `/tmp/sa3.log` 읽어 SA3 결과 확인
2. SA3 오류 없으면 SA1, SA2 실행 → CSV 수집
3. SA4 (highway 시나리오) 실행
4. 모든 sweep 완료 후 → Stage 3 (분석/시각화) 진입

---
*Last updated: 2026-05-08 13:00*

---

## [2026-05-08] L1-B-2 — sim_engine.py generate_routes() 패치 설계 및 적용

### 진단 결과 (R1 정적 분석)
- `generate_routes()` line 243-244 확인:
  - `for i in range(n_vehicles):` + `depart = rng.uniform(0, min(30, duration_s * 0.1))`
  - duration_s=300 → `min(30, 30)=30` → **모든 차량이 [0, 30s] warmup 구간에만 출발**
  - post-warmup(30s~)에는 차량들이 이미 trip 완료 후 소멸 → 채널이 거의 빈 상태
  - 결과: BL-B가 cbr_target에 무관하게 항상 같은 출력 → SA3 sweep 무의미

### 패치 설계 (R2)
옵션 3 변형 (가장 단순, 변경 라인 2개):
- (a) depart 분포 확장: `max(30, duration_s * 0.7)` → [0, 210s] 균등 출발
- (b) 차량 밀도 보상: `n_vehicles * 2` 루프 → trip 완료 소멸 보완

예상 개선:
- n_vehicles=30, urban_grid: ~13 대 동시 active (기존 ~0)
- n_vehicles=30, highway: ~34 대 동시 active (기존 ~0)
- CBR_mean 기대값: 0.05~0.4 (기존 0.014)
- n_cam_events 기대값: 30,000+ (기존 3,000)

### 패치 적용 완료 (R3)
- 백업: `sim/sim_engine.py.bak_L1B2`
- 변경 파일: `sim/sim_engine.py`

```diff
--- a/sim/sim_engine.py  (line 243-244)
+++ b/sim/sim_engine.py
-    for i in range(n_vehicles):
-        depart = rng.uniform(0, min(30, duration_s * 0.1))
+    for i in range(n_vehicles * 2):  # 2x stagger: compensate for trip completion/disappearance
+        depart = rng.uniform(0, max(30, duration_s * 0.7))
```

### 자체 검증 (R4 SELF-RUN)
- syntax check (`ast.parse`): PASS
- import check (`from sim_engine import SimulationRunner`): PASS

### 다음 단계
- [USER-RUN] 명령 6: smoke test (n=20, 600 steps) — 패치 효과 확인
- [USER-RUN] 명령 7: SA3 풀 sweep 재실행 (7개 cbr_target 구분 여부 확인)

*Last updated: 2026-05-08 (L1-B-2 완료)*

---

## L1-B-3 완료 (2026-05-08 22:41+)

### 작업 내용
SumoNetSim1.1.5 SUMO 자산을 사용하도록 sim_engine.py 패치

### 핵심 변경
1. **SUMOCFG_PATH 상수 신설** (Line 39-42):
   ```python
   SUMOCFG_PATH = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg"
   SUMO_NET_PATH = "/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.net.xml"
   ```

2. **libsumo.start() 완전 교체** (Line 347-353):
   - 기존: `--net-file ... --route-files ... --begin 0 --end N --ignore-route-errors`
   - 신규: `-c SUMOCFG_PATH --time-to-teleport -1` (sumocfg가 begin/end/net/route 정의)

3. **자체 생성 호출 완전 제거** (SimulationRunner.run() 내):
   - net_path, route_path, cfg_path 변수 삭제
   - generate_urban_grid_net(), generate_routes(), generate_sumocfg() 호출 삭제
   - 함수 정의는 API 호환성 위해 존재 유지

### 백업
- `sim/sim_engine.py.bak_L1B3`

### Smoke Test (SELF-RUN)
- 환경: libsumo 직접 호출 (ETSICAMLayer/AoITracker 없이 순수 SUMO 루프)
- 300 steps (30초 시뮬레이션 시간) 정상 완주
- avg vehicles/step: 88.3 (SumoNetSim1.1.5 rou.xml 풍부한 차량 확인)
- total_cam_events proxy: 26,492 → PASS (≥200)
- CBR_mean: 0.7296 → PASS (≥0.05)
- runtime_sec: 0.20s (libsumo 고속, 비정상 신호 아님)

### SumoNetSim1.1.5 자산 정보
- generated.sumocfg: begin=0, end=360000
- generated.net.xml: 291.7KB (실제 도시 네트워크)
- generated.rou.xml: 49.4KB (풍부한 차량 경로)
- 원본 폴더: 읽기 전용 취급 (수정 없음)

### 다음 단계
- n_vehicles 캡/필터링 (후속 leaf)
- 완전한 SimulationRunner.run() 호출 (ETSICAMLayer + AoITracker 포함)

*Last updated: 2026-05-08 (L1-B-3 완료)*
