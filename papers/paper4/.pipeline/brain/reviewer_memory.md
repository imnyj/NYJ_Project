# Reviewer Memory

## Session: L1-A-1 (2026-05-09)

### 작업 완료: L1-A-1 sim_engine.py libsumo 통합 검증

**결과**: PASS (5/5)

**핵심 판단**:
- `import libsumo` line 26: try/except 없는 강제 import → mock fallback 없음
- `libsumo.simulationStep()` line 373: 루프 최초 문장, 무조건 실행
- `libsumo.vehicle.getIDList()` line 378: 실제 libsumo 호출
- PHY/MAC 모델 (reception_probability, compute_cbr, simulate_receptions): lines 132, 415, 419 활성 경로
- `libsumo.close()` line 440: finally 블록 보장 실행

**가설 기각**: libsumo silent fallback/mock 경로 존재 가설 → REJECTED

**이상 현상 원인 방향**:
- CBR≈0.0163 이상 → etsi_cam_layer.py에서 CAM 생성 빈도가 너무 낮음 (step당 ~2.2대만 송신)
  - 50대 차량이 매 step(100ms) 송신한다면 CBR≈0.37이 정상
- 동일 AoI/CBR/PDR → sensitivity_runner.py에서 cbr_target 파라미터가 SimulationRunner/cam_layer에 
  실제로 전달되지 않을 가능성
- runtime≈0.25s → 루프가 조기 종료 (getMinExpectedNumber()=0 : 차량이 목적지 도달 후 모두 탈출)
  혹은 warmup 이후 step이 거의 없음

**다음 권고**:
- L1-A-2: etsi_cam_layer.py 검증 (CAM 생성 주기 로직, cbr_target 파라미터 수신 여부)
- L1-A-3: sensitivity_runner.py 검증 (cbr_target → method_params 전달 체인)

**산출물**:
- /home/imnyj/papers/paper4/paper/validation/validation_report.json
- /home/imnyj/papers/paper4/.pipeline/annotations/validation_history.md


## Session: L1-B-3-validate (2026-05-08 ABC-A 단계)

### 작업: sim_engine.py L1-B-3 패치 정합성 정적 검증

**결과**: PASS (Q-V1~Q-V5 모두 PASS, issues 없음)
**검증 주체**: Commander 직접 (Reviewer 30s timeout으로 중단된 작업 인계)

**핵심 확인 사항**:
- Q-V1: SUMOCFG_PATH(/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg) 존재 + libsumo.start CLI 인자 정상.
- Q-V2: SimulationRunner.run() 내부 자체 generate_routes/generate_urban_grid_net 호출 모두 제거됨. 함수 정의만 잔존.
- Q-V3: ETSICAMLayer/AoITracker 통합부 정상. method_params propagation OK. 
  · 핵심 cross-file: etsi_cam_layer.py L97 self.params.get('cbr_target', 0.60) (소문자, L1-B-1 패치 적용됨)
  · sensitivity_runner.py L135 method_params={'cbr_target': cbr_target} (소문자)
  · 키 케이스 일치 → SA3 sweep 무력화 버그(L1-A-2에서 발견된 root cause) 해소 확인.
- Q-V4: STEP_LENGTH=0.1 일관, while 종료조건(getMinExpectedNumber>0 and step<duration_steps) SumoNetSim1.1.5 자산에서 정상 동작 예상.
- Q-V5: run() 반환 dict 키 = sensitivity_runner CSV_COLUMNS 완전 일치 (AoI_mean, CBR_mean, PDR_mean, energy_efficiency, ETSI_compliance, runtime_sec, n_cam_events).

**산출물**:
- /home/imnyj/papers/paper4/paper/validation/validation_report.json (덮어쓰기)

**다음 단계 권고 (사용자에게 전달)**:
- B단계: RUNBOOK 명령 2-redo (BL-A 20대 30s SimulationRunner full run) — 사용자 직접 실행
- C단계: 명령 2-redo 정상 시 RUNBOOK 명령 4-redo (SA3 cbr_target 7값 sweep) — 사용자 직접 실행
