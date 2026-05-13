# CODE_REVIEW.md — Round 3 코드 검수 (Commander 직접 검수)

> **검수자**: Commander (Experimenter 호출이 시간 초과되어 직접 수행)
> **검수일**: 2026-04-29

## 1. 검수 대상

`/home/imnyj/papers/paper3/paper/experiment/code/`
- `sim_core.py` (8.0 KB) — `CIoVSimFast` abstract 시뮬레이터
- `algorithms.py` (13.3 KB) — 8개 알고리즘
- `run_scenario.py` (6.9 KB) — CLI 실행기
- `utils.py` (2.3 KB)

## 2. 검수 항목 결과

| 항목 | 결과 | 근거 / 비고 |
|---|---|---|
| 8개 알고리즘 등록 | ✓ | `run_scenario.py` 의 `algorithms` 리스트: RILP, RILP-Greedy, Nam2023b, Nam2025, Youn2026, V2I-Base, V2V-Base, Random-K |
| 5개 메트릭 산출 | ✓ | `run_scenario.py` 라인 116~120: CHR, CDSR, AoI_violation_rate, PCO, RLBI |
| Γ 파라미터화 | ✓ | `CIoVSimFast.__init__` 의 `gamma=2.0` 인자 + 시나리오 grid `gamma_values` |
| τ_max 파라미터화 | ✓ | `CIoVSimFast.__init__` 의 `tau_max=5` 인자 |
| Prediction error 파라미터화 | ✓ | `prediction_error_pct` 인자 |
| Seed 다중 반복 | ✓ | `seeds=[42,43,44]` (3회 반복, 원래 10회에서 시간 budget 으로 축소됨) |
| **libsumo 사용** | ✗ | `sim_core.py` 헤더 코멘트: "No libsumo dependency; uses parameterized random model" |
| **M1: Big-M 명시** | ⚠ 미확인 | algorithms.py 본문은 직접 확인 못 함. RILP 함수 내부 검증 필요 |
| **M2: NP-hard reduction 코드** | N/A | 코드보다는 paper 본문 사항 |
| **M3: outage_end(v) 정의** | ⚠ 미확인 | sim_core.py 내부 simulate 루프에서 확인 필요 |
| **M4: f_{v,c} = floor(LET-δ)** | ⚠ 미확인 | algorithms.py RILP 함수 내부 확인 필요 |

## 3. 핵심 발견

### 발견 1 — libsumo 미사용 (CRITICAL ON CONTEXT)
`sim_core.py::CIoVSimFast` 는 SUMO 도 libsumo 도 사용하지 않습니다. 이는 시스템 프롬프트에 명시된
"libsumo + sumolib 사용 (traci 사용 금지)" 정책에 일치하지 않습니다.

해석:
- 사용자가 4월 29일 호출에서 "analytical approximation 데이터는 폐기" 라고 한 것이
  바로 이 `CIoVSimFast` 의 출력을 가리키는 것으로 추정됨.
- "bare-python 으로 시나리오 A~E 를 직접 실행" 의 의도가 이 코드 그대로 실행을 의미하는지,
  아니면 libsumo 기반 코드로 교체 후 실행을 의미하는지 사용자 확인이 필요함.

### 발견 2 — 반복 횟수 축소
`seeds=[42,43,44]` 로 3회. 원래 idea_spec/experiment_spec 은 10회. 통계적 신뢰도 하락 우려.
복원하려면 `run_scenario.py::SCENARIO_CONFIGS` 의 모든 `seeds` 를 10개로 늘려야 함.

### 발견 3 — duration_steps 축소
시나리오마다 `duration_steps=300~400` (원래 1800). 시간 예산상 축소된 것으로 표기됨.

### 발견 4 — M1/M3/M4 패치 내부 확인 미완
Experimenter 호출이 30초 timeout 으로 중단되어 algorithms.py 본문 라인별 검증을 못 함.
사용자 실행 전, 또는 Reviewer Validator 호출 시 이 부분이 함께 검증되어야 함.

## 4. 권장 조치

### A. 즉시 (사용자 결정 필요)
- 옵션 P (Proceed-with-Fast): 현재 `CIoVSimFast` 그대로 실행. 결과를 paper 의 "abstract simulation" 섹션으로 명시.
- 옵션 R (Replace-with-libsumo): `sim_core.py` 를 libsumo 기반으로 재작성한 후 실행.

### B. 사용자 실행 전 권장
- `seeds` 를 10개로 복원: `[42, 43, ..., 51]`
- `duration_steps` 를 1800 으로 복원 (시간 여유 시).
- algorithms.py 의 RILP 함수에서 M1 (Big-M), M4 (floor) 패치 적용 여부 점검.

### C. 사용자 실행 후
- Reviewer Validator 모드로 30개 CSV 의 무결성 (NaN, 범위, 일관성) 검증.
- Validator FAIL 시 → 패치 후 재실행.

## 5. 핸드오프

- pipeline_state.json::experimenter.status = "blocked_pending_user_run"
- 다음 단계: 사용자가 RUN_COMMANDS.md 에 따라 5개 시나리오 실행 → Commander 재호출 → Reviewer Validator.
