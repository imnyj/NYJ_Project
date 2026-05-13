# Code Change Tracker

## [2026-04-29] sim_core.py: CIoVSimFast (abstract) → CIoVSim (libsumo) 교체

### 변경 내용
- **파일**: `/home/imnyj/papers/paper3/paper/experiment/code/sim_core.py`
- **구 클래스**: `CIoVSimFast` — abstract random-walk 기반 (libsumo 미사용)
- **신 클래스**: `CIoVSim` — libsumo + SumoNetSim1.1.6 완전 연동

### 주요 변경 사항
1. libsumo 기반으로 완전 재작성 (traci 사용 금지 준수)
2. SUMO 네트워크 파일 사용: `/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/generated.sumocfg`
3. RSU 위치: `rsu.poi.xml` 동적 파싱 (25개 RSU, 5×5 격자, 2400m 간격)
4. 차량 이동: random-walk → libsumo 실제 차량 궤적 (`sumo.vehicle.getPosition/Speed/Angle`)
5. `cache_decision_fn(vehicles, params, rng)` 인터페이스 유지 (algorithms.py 호환)
6. 출력 5개 지표 유지: CHR, CDSR, AoI_violation_rate, PCO, RLBI
7. `duration_steps=1800`, `warmup_steps=300` 기본값 (결정2·3 반영)
8. libsumo import 실패 시 명시적 오류 메시지 + SystemExit(1)
9. sumolib import 실패 시 명시적 오류 메시지 + SystemExit(1)

### 새 파라미터 (추가됨)
- `sumo_dir`: SUMO 설정 파일 디렉터리 경로 (None=자동 해결)
- `sumo_gui`: sumo-gui 사용 여부 (기본 False)

### 제거된 파라미터
- 없음 (모든 기존 파라미터 유지, 단 `density_per_cell`은 legacy 호환용으로 유지)

### 작업자
- Experimenter (Stage 2: implement)

### 관련 결정
- 결정 2: run_scenario.py seeds [42..51] 복원 (다음 호출에서 처리 예정)
- 결정 3: duration_steps=1800, warmup_steps=300 (sim_core.py 기본값에 반영 완료)
- **[2026-05-07] run_scenario.py**: Heartbeat 진행 로그 추가 — `_heartbeat_interval()`, `_fmt_elapsed()`, `_fmt_eta()` 3개 함수 신규 추가; `run_scenario()` 내 `last_heartbeat_t`, `last_combo` 변수 추가; 시작/종료 메시지 + 폴링 방식 per-run 체크 (간격: <60s→10s, 60-600s→1min, >=600s→1h); `import datetime` 추가; 기존 로직/설정 미변경.
