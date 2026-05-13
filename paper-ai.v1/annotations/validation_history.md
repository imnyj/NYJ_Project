# Validation History

## [2026-04-29] SUMO 통합 진위 검증 (ad-hoc)

- **검증 ID**: VAL-2026-04-29-SUMO-INTEGRITY
- **모드**: Validator (사용자 직접 요청)
- **결과**: PASS
- **판정**: libsumo 기반 SUMO 시뮬레이션이다
- **대상**: sim_core.py, run_scenario.py, algorithms.py, utils.py
- **SUMO 파일 경로**: /home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo/
- **주요 발견**:
  - `import libsumo as sumo` 실제 사용 (PASS)
  - `import sumolib` 존재하나 dead import (WARNING)
  - `sumo.start()`, `sumo.simulationStep()`, `sumo.vehicle.*` API 실제 호출됨
  - SUMO 입력 파일(.sumocfg, .net.xml, .rou.xml) 모두 디스크 존재
  - 가짜 시뮬레이션 패턴 없음
- **보고서**: workspace/paper/validation/validation_report.json
- **참고**: ad-hoc 점검 (정식 파이프라인 외)
