# SMOKE_DIAGNOSIS.md — Smoke test가 너무 오래 걸리는 이유 + 패치 안내

작성: 2026-05-06 (Commander 직접 진단)
대상 사용자: "smoke 조차 너무 오래 걸리는데?" 보고에 대한 답신.

---

## 1. 결론 (TL;DR)

**현재 smoke = 사실상 본 실험 1 run 과 동일한 부하**. 빠를 리가 없습니다.

- `quickstart.sh smoke` → `CIoVSim(duration_steps=1800, warmup_steps=300)` 호출
- 본 시나리오 A~E 의 한 run 도 정확히 `duration_steps=1800, warmup_steps=300`
- 즉 "1 run smoke" = "본 실험 1 run"

만약 1 run 이 5분~수십 분 걸리는 환경이라면, smoke 도 동일하게 그만큼 걸립니다.
이건 smoke 의 정의 자체가 잘못 잡힌 것이며, 동시에 1 run 의 절대 시간이
너무 길어서 6,400 runs (시나리오 A) 가 사실상 며칠 걸릴 위험도 있습니다.

---

## 2. 1 run 이 오래 걸리는 3가지 원인 (정량 분석)

### 원인 ①: SUMO 자체 부하가 매우 큼

`/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/generated.rou.xml`:
- 12km × 12km 도로망 (5×5 RSU grid, 2400m spacing)
- **380 개 flow**, 각각 `probability=0.0221`, `begin=0, end=3600`
- 1초당 기대 출발 차량 수 ≈ 380 × 0.0221 = **8.4 대/초**
- 1800초 시뮬 동안 누적 출발 ≈ 15,000 대
- 도로 길이가 길어 동시 활성 차량 수가 정상상태에서 **수백~수천 대**

SUMO 가 매 step 마다 이 수천 대를 라우팅·충돌검사·이동 처리합니다.
순수 SUMO 비용만으로 1 run 에 1~10분 소요 가능 (CPU 한 코어 기준).

### 원인 ②: Python 측 O(N²) 핫스팟

`sim_core.py::run()` 내부, warm-up 후 **매 step × 매 vehicle** 마다:

```python
rsu_idx, _ = self._nearest_rsu(v["x"], v["y"])           # 25 RSU 선형 검색
nearby = self._vehicles_near_rsu(rsu_idx, self._veh_state)  # 전체 차량 선형 검색!
```

`_vehicles_near_rsu` 는 dict 의 모든 차량을 순회해 거리 계산 → **O(N)**.
이게 매 step 의 매 차량에 대해 호출되므로 step 당 비용 = **O(N²)**.

| 동시 활성 차량 N | step 당 거리 계산 횟수 | 1500 metric step × N² |
|---|---|---|
| 200 | 40,000 | 60,000,000 |
| 1000 | 1,000,000 | **1.5×10⁹** |
| 2000 | 4,000,000 | **6×10⁹** |

Python 순수 루프로 6×10⁹ 회 거리계산은 **수십 분~수 시간** 걸립니다.

### 원인 ③: libsumo polling 도 step 당 4·N 회 IPC

`_collect_vehicle_states_from_libsumo` 가 매 step 마다
`getIDList`, `getPosition`, `getSpeed`, `getAngle` 를 차량별로 호출.
libsumo 는 in-process 라 traci 보다 빠르지만, 그래도 N=2000 이면 step 당 8,000 호출.
1800 step → **1,440 만 호출**. 이것만으로도 분 단위 시간이 추가됩니다.

---

## 3. 즉시 적용 가능한 3단계 처방

### 처방 A — Smoke 를 "진짜 smoke" 로 축소 (5초~30초 목표)

`quickstart.sh smoke` 가 호출하는 파이썬 블록의
`duration_steps=1800, warmup_steps=300` →
**`duration_steps=180, warmup_steps=30`** 으로 변경 (10배 단축).

이러면 SUMO 자체 비용도 1/10, 동시 활성 차량 수도 정상상태 도달 전에 끝나므로
**전체 비용은 1/10 보다 더 줄어듦** (15~50초 예상).

이 변경으로 잡고 싶은 것:
- libsumo / SUMO config / sim_core import 경로 / algorithm 호출이 정상 동작하는지.
- 본 실험과 동일한 통계 결과를 얻으려는 게 아님 (그건 본 실험에서).

### 처방 B — sim_core 의 O(N²) → O(N) 패치

`_vehicles_near_rsu` 를 **per-step 캐시** 로 바꿉니다.
매 step 시작 시 한 번만:
- 차량을 RSU 별 bucket 에 분류 (RSU 25 개 × 차량 N 개 = O(N))
- per-vehicle request 처리 시 본인 RSU 의 bucket 만 조회 → O(1)

step 당 비용 O(N²) → O(N). N=2000 일 때 **3,000~5,000배 빠름**.

### 처방 C — Trajectory 사전생성 (선택, 가장 효과 큼)

알고리즘 8개 × seed 10개 × 다른 파라미터 모두 동일한 SUMO trajectory 를 공유 가능.
→ SUMO 를 **seed 10개에 대해 단 1회씩 미리 돌려** trajectory CSV 로 저장.
→ 알고리즘 비교 run 은 trajectory 재생만 → libsumo 호출 0회, SUMO 가동 0회.
→ 한 run 비용이 SUMO 부하 빠지면서 **5~50배 빨라짐**.

이 처방은 코드 구조 변경이 크므로, 처방 A·B 로 우선 smoke 가 확인되면 별도 진행 권장.

---

## 4. 사용자가 지금 할 일 (1단계)

1. **smoke 만 가볍게**: `quickstart.sh smoke` 가 더이상 1800 step 이 아니라 180 step 만
   돌도록 수정한 새 smoke 가 `quickstart.sh quick` 로 추가됨 (commander 가 패치 예정).
2. quick smoke 가 1분 안에 PASS 하는지 확인.
3. 1분 안에 끝나면 → 처방 B (O(N²) 패치) 적용 검토 후 본 실험 가능 여부 평가.
4. 1분이 지나도 결과 없으면 → SUMO 자체가 너무 무거운 것이므로 처방 C 필수.

Commander 가 이어서 quickstart.sh 와 sim_core.py 를 패치합니다 (별도 보고).
