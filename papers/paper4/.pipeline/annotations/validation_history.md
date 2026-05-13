# Validation History

## [2026-05-09 13:XX] L1-A-1 — sim_engine.py / libsumo integration

- **Leaf ID**: L1-A-1
- **Reviewer**: Reviewer agent
- **Overall Result**: PASS (5/5 PASS)
- **Scope**: sim_engine.py libsumo integration validation
- **Trigger**: SA3 sweep anomaly — CBR≈0.0163, runtime≈0.25s/300s, all cbr_target values producing identical output

### Verdict per Question

| ID | Verdict | Key Line(s) | Summary |
|----|---------|-------------|---------|
| Q-A1 | PASS | 26 | `import libsumo` bare top-level, no try/except, no mock fallback |
| Q-A2 | PASS | 372-373 | `libsumo.simulationStep()` called unconditionally as first loop body statement |
| Q-A3 | PASS | 378 | `libsumo.vehicle.getIDList()` live libsumo call, no synthetic vehicle data |
| Q-A4 | PASS | 132, 415, 419 | `compute_cbr`, `simulate_receptions`, `reception_probability` all on active path |
| Q-A5 | PASS | 438-442 | `libsumo.close()` in finally block, guaranteed execution |

### Conclusion
- **libsumo mock/silent-fallback hypothesis: REJECTED**
- sim_engine.py is correctly wired to real libsumo. Anomaly root cause lies elsewhere.
- **Next**: L1-A-2 — inspect etsi_cam_layer.py for CAM generation rate bug and sensitivity_runner.py for cbr_target parameter forwarding.


## [2026-05-08 ABC-A] L1-B-3-validate — sim_engine.py 패치 후 정합성 검증

- **Leaf ID**: L1-B-3-validate
- **수행자**: Commander (Reviewer agent timeout 후 인계)
- **Overall Result**: PASS (Q-V1~Q-V5 모두 PASS)
- **Scope**: sim/sim_engine.py 정적 검증 + cross-file (etsi_cam_layer.py, sensitivity_runner.py) 키 일치성

### Verdict per Question

| ID | Verdict | 핵심 근거 |
|----|---------|----------|
| Q-V1 | PASS | SUMOCFG_PATH 절대 경로 + 자산 존재 + libsumo.start CLI 정합 |
| Q-V2 | PASS | 자체 net/route 생성 호출 모두 제거 (정의만 잔존) |
| Q-V3 | PASS | ETSICAMLayer/AoITracker 통합 정상; cbr_target 키 케이스 cross-file 일치 |
| Q-V4 | PASS | STEP_LENGTH/duration 계산 일관, 종료조건 SumoNetSim 자산에서 정상 동작 |
| Q-V5 | PASS | 반환 dict 키 ↔ sensitivity_runner CSV_COLUMNS 완전 일치 |

### 결론
- L1-B-3 패치는 정적으로 모든 통합 지점에서 무결.
- L1-A-2에서 발견된 cbr_target key-case bug는 이미 L1-B-1에서 해소됨이 확인됨.
- 사용자에게 RUNBOOK 명령 2-redo (B단계), 4-redo (C단계) 실행 권고.
