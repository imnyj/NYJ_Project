# Experimenter Brain — sim_core.py 재작성 기록

## [2026-04-29] sim_core.py: CIoVSim (libsumo 기반) 재작성

### 클래스/메소드 시그니처

```python
class CIoVSim:
    def __init__(self,
                 seed=42,
                 density_per_cell=5,
                 rsu_grid=(5, 5),
                 comm_range_m=800.0,
                 outage_zone_m=800.0,
                 catalog_size=100,
                 cache_capacity=10,
                 tau_max=5,
                 gamma=2.0,
                 prediction_error_pct=0,
                 duration_steps=1800,
                 warmup_steps=300,
                 v2i_bw_mbps=20.0,
                 v2v_bw_mbps=10.0,
                 scheduling_window=20,
                 content_sizes_mb=None,
                 zipf_s=0.8,
                 sumo_dir=None,
                 sumo_gui=False): ...

    def build_params(self) -> dict: ...
    # Returns params dict compatible with algorithms.py interface.

    def run(self, cache_decision_fn) -> dict:
    # Returns: CHR, CDSR, AoI_violation_rate, PCO, RLBI, total_requests, total_hits

    # Internal helpers:
    def _zipf_popularity(self, n, s) -> list
    def _nearest_rsu(self, x, y) -> (rsu_index, dist_m)
    def _rsus_in_range(self, x, y) -> list[int]
    def _vehicles_near_rsu(self, rsu_idx, veh_states) -> list[dict]
    def _predict_position(self, v, horizon=5) -> (px, py)
    def _get_or_create_veh_state(self, vid, x, y, speed, angle) -> dict
    def _collect_vehicle_states_from_libsumo(self) -> list[str]
```

### libsumo 사용 부분 (어떤 API를 어디서 호출하는지)

| 위치 | libsumo API | 설명 |
|------|------------|------|
| 모듈 최상단 | `import libsumo as sumo` | 실패 시 SystemExit(1) |
| `run()` 시작 | `sumo.start(sumo_cmd)` | SUMO 프로세스 시작 (in-process) |
| `run()` 루프 | `sumo.simulationStep()` | 1초 스텝 진행 |
| `_collect_vehicle_states_from_libsumo()` | `sumo.vehicle.getIDList()` | 현재 활성 차량 ID 목록 |
| `_collect_vehicle_states_from_libsumo()` | `sumo.vehicle.getPosition(vid)` | (x, y) 좌표 (metres) |
| `_collect_vehicle_states_from_libsumo()` | `sumo.vehicle.getSpeed(vid)` | 속도 (m/s) |
| `_collect_vehicle_states_from_libsumo()` | `sumo.vehicle.getAngle(vid)` | 방향각 (도, SUMO 규약: N=0, CW) |
| `run()` 종료 (finally) | `sumo.close()` | SUMO 종료 (항상 실행) |

### SUMO 설정 파일 경로 가정

- 기본 경로: `/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/`
- 주요 파일:
  - `generated.sumocfg` — SUMO 설정 파일 (net/rou/add 파일 참조)
  - `generated.net.xml` — 도로망 (5×5 RSU 격자, 12km×12km)
  - `generated.rou.xml` — 차량 경로
  - `rsu.poi.xml` — RSU 위치 POI 정의 (25개 RSU, 1200~10800m 격자)
  - `generated.add.xml` — TAZ/추가 설정
- 경로 해결 순서: `sumo_dir` 인자 → 상대 경로 → 절대 fallback → `$SUMO_HOME`
- RSU 위치는 `rsu.poi.xml` 동적 파싱 + 정적 fallback (_RSU_POSITIONS_STATIC)

### RSU 위치 (SumoNetSim1.1.6 기준)

- 5×5 = 25개 RSU
- 격자 간격: 2400m (= RSU_RANGE 800 + OUTAGE 800 + RSU_RANGE 800)
- X 좌표: 1200, 3600, 6000, 8400, 10800 (m)
- Y 좌표: 1200, 3600, 6000, 8400, 10800 (m)
- Node ID: N7, N8, N9, N10, N11, N14..N18, N21..N25, N28..N32, N35..N39

### 알려진 제약

1. **Sandbox 실행 불가**: libsumo는 실제 SUMO 바이너리 필요 — 이 에이전트 환경에서는 실행 불가.
2. **사용자 환경 가정**: SUMO 설치 + libsumo Python 바인딩 + SUMO_HOME 환경변수 설정 필요.
3. **traci 사용 금지**: 모든 SUMO 제어는 libsumo API만 사용 (traci import 없음).
4. **sumolib**: 현재 구현에서는 RSU 위치 파싱에 ET(xml.etree) 사용; sumolib은 import 검증용.
5. **vehicle.getPosition()**: libsumo는 tuple (x, y) 반환 (traci와 동일 인터페이스).
6. **SUMO 헤딩 변환**: angle (deg, N=0, CW) → vx/vy: rad = radians(90 - angle).
7. **차량 수**: 실제 차량 수는 .rou.xml에서 결정됨 (density_per_cell은 legacy 파라미터).

### algorithms.py 호환성

- `cache_decision_fn(vehicles_list, params, rng)` 인터페이스 완전 유지
- `vehicles_list`: list of dict with keys: id, x, y, vx, vy, speed, cache, aoi, ...
- `params`: build_params() 반환값 — catalog_size, cache_capacity, popularity, content_sizes,
  tau_max, gamma, pred_error, v2i_bw, v2v_bw, sched_window, n_rsu, rsu_positions
- 8개 알고리즘 (RILP, RILP-Greedy, Nam2023b, Nam2025, Youn2026, V2I-Base, V2V-Base, Random-K) 모두 호환


---

## [2026-05-07] run_scenario.py: Heartbeat 진행 로그 추가

### 변경 이유
본 시뮬레이션 (시나리오 A~E, seeds 10개, duration_steps=1800) 실행 전, 장시간 실행 중 진행 상황을 확인할 수 있도록 heartbeat 로그 기능 추가. `tee` / `nohup` 환경에서 터미널 없이도 안심하고 모니터링 가능.

### 변경 파일
- `/home/imnyj/papers/paper3/paper/experiment/code/run_scenario.py`

### 추가된 함수
- `_heartbeat_interval(elapsed_s) -> int`
  - elapsed_s < 60 → 10 (10초 간격)
  - 60 <= elapsed_s < 600 → 60 (1분 간격)
  - elapsed_s >= 600 → 3600 (1시간 간격)
- `_fmt_elapsed(seconds) -> str`
  - 경과 시간을 "45s", "12m 30s", "2h 05m 10s" 형태로 포맷
- `_fmt_eta(seconds) -> str`
  - ETA를 "12m 30s", "2h 05m" 형태로 포맷

### 추가된 변수 (run_scenario 함수 내)
- `last_heartbeat_t`: 마지막 heartbeat 출력 시각 (time.time() 기준)
- `last_combo`: 가장 최근 완료된 (algo_name, density, epsilon, gamma, tau_max, seed) 튜플

### Heartbeat 출력 사양
1. 실행 시작 시 1회 "[HEARTBEAT] 시작" 출력 (total_runs, already_done 포함)
2. 매 run 완료 후 폴링: `now - last_heartbeat_t >= interval` 검사
3. 시나리오 종료 시 1회 "[HEARTBEAT] 종료" 출력 (총 경과, 완료/신규/재개 수 포함)

### 출력 예시
```
[HEARTBEAT] 시작 | 2026-05-07 14:23:05 | 시나리오=A | total_runs=1600 | already_done=0
[HEARTBEAT] 2026-05-07 14:23:15 | 경과=10s | 진행=3/1600 (0.2%) | 평균=3.2s/run | ETA=85m 26s | 최근완료: algo=RILP d=1 eps=0 g=0.0 tau=5 seed=44
[HEARTBEAT] 종료 | 2026-05-07 16:45:30 | 총 경과=2h 22m 25s | 완료=1600/1600 | 신규=1600 | 재개=0
```

### 주의사항
- 시뮬레이션 로직 (sim_core.py, algorithms.py) 미수정
- SCENARIO_CONFIGS, KEY_FIELDS, METRIC_FIELDS, CSV 포맷 미변경
- per-run 상세 출력 라인 유지 (디버깅용)
- 추가 import: `import datetime` (최상단)

### 작업자
- Experimenter (Stage 2: implement)
