# Reviewer Memory

## [2026-04-29] [Validator] SUMO 통합 진위 검증

**검증 요청**: 사용자 ad-hoc 점검 (정식 파이프라인 외)
**검증 대상 파일**:
- workspace/paper/experiment/code/sim_core.py
- workspace/paper/experiment/code/run_scenario.py
- workspace/paper/experiment/code/algorithms.py
- workspace/paper/experiment/code/utils.py

**결과**: PASS
**판정**: libsumo 기반 SUMO 시뮬레이션이다

**핵심 발견사항**:
1. `import libsumo as sumo` 확인됨 (sim_core.py) — PASS
2. `import sumolib` 확인됨 (sim_core.py) — 단, dead import (WARNING)
3. `import traci` 단독 사용 없음 — PASS
4. SUMO 설정 파일 실제 존재: /home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/
   - generated.sumocfg, generated.net.xml (291.6KB), generated.rou.xml (49.4KB), rsu.poi.xml (1.6KB)
5. `sumo.start([..."-c", sumocfg...])` 호출 확인됨
6. `sumo.simulationStep()` main loop 내 존재 확인됨
7. `sumo.vehicle.getIDList()/getPosition()/getSpeed()/getAngle()` 실제 호출됨
8. 가짜 시뮬레이션 패턴(np.random 차량 생성, mock/stub) 없음

**이슈**:
- I-01 (WARNING): sumolib dead import — RSU 파싱에 활용 안 함
- I-02~I-04 (INFO): 경미한 설계 메모

**보고서 위치**: workspace/paper/validation/validation_report.json
**참고**: ad-hoc SUMO integrity check (정식 데이터 검증 파이프라인 외)
