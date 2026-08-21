## 2026-08-20T09:57:07Z
[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_m8/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: M-8 차량별 국소 CBR 측정 및 sim_engine.py vdata["cbr"] 전달]
순차 실행 원칙에 따라, M-7 완료에 이어 M-8 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. 차량별 국소 CBR 계산 및 전달 구조 정합 (code/sim_engine.py):
   - code/sim_engine.py에서 기존에 맵 전체 전송량 기반의 단일 전역 스칼라 CBR을 모든 차량에 동일하게 전달하던 한계를 개선합니다.
   - 각 차량 vid에 대해, 통신 반경(COMM_RANGE_M = 300.0m) 내에 위치한 이웃 차량들(N(vid) U {vid})의 전송 패킷 수 및 에어타임(TX_DURATION_S)을 기반으로 차량별 국소 CBR을 계산하는 compute_local_cbr(vehicle_positions, tx_counts, window_duration, comm_range_m=COMM_RANGE_M) 함수를 구현/정합합니다.
   - SimulationRunner.run() 루프 내에서 각 차량의 vdata["cbr"]에 해당 차량의 국소 CBR 값을 정확히 주입합니다.
   - 공간적으로 밀집된 지역의 차량은 높은 국소 CBR을, 한적한 외곽의 차량은 낮은 국소 CBR을 관측하도록 보장하여 공간 재사용(spatial reuse) 특성을 반영합니다.
   - 요약 통계용 전역 지표(CBR_mean, CBR_p95 등)는 전체 차량의 국소 CBR 평균/분포로 정상 집계되도록 유지합니다.

2. 독립 검증 스크립트 작성 및 실행 (code/test_m8_local_cbr.py):
   - code/test_m8_local_cbr.py를 작성하여:
     * 공간 불균일 트래픽 시나리오 검증:
       1. 동쪽 클러스터(좌표 0~100m, 5대 차량이 10Hz 전송) vs 서쪽 고립 차량(좌표 800m, 1대 차량이 1Hz 전송).
       2. 동쪽 클러스터 차량들의 국소 CBR이 서쪽 고립 차량의 국소 CBR보다 확연히 높게 측정됨을 assert.
       3. 차량별 vdata["cbr"]가 단일 전역 상수값이 아닌 공간 분포를 반영하는 다중 값임을 검증.
     * SimulationRunner 런타임 연동 검증:
       - 실제 SUMO/시뮬레이터 구동 시 ETSICAMLayer와 AI Hook에 차량별 국소 CBR이 정상 전달되고 예외 없이 완료됨을 assert.
   - python3 code/test_m8_local_cbr.py를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

3. 마스터 작업 목록 갱신 (idea/paper4_code_fix_tasklist.md):
   - M-8 항목의 상태를 [x] 완료로 변경하고 수정 파일, 국소 CBR 계산 수식 및 독립 검증 결과를 상세히 기록합니다.

4. 핸드오프 보고서 작성 및 완료 알림:
   - /home/imnyj/Workspace/paper4/.agents/worker_m8/handoff.md에 결과를 기록하고 오케스트레이터에게 send_message로 완료를 보고하세요.
