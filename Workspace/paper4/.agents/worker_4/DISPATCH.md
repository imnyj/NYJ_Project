## 2026-08-21T14:10:30Z

당신은 17개 모델 전체 평가 데이터 파이프라인 및 최종 지표 CSV 생성을 전담하는 전문 Worker (Worker 4)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_4 (메타데이터용)
프로젝트 루트: /home/imnyj/Workspace/paper4

반드시 가장 먼저 `/home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md` 및 `evaluation_plan.md` 파일을 확인하여 사용자 요구사항을 숙지하세요.

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[상세 수행 목표 (R4)]
1. 17개 모델 전체 수렴 데이터 병합 검증:
   - `data/models/*_convergence.csv` (17개 모델: REMO-DQN + 13 RL + 3 non-RL) 데이터 확인
   - `data/reward_convergence.csv` (17개 모델 전체 100행 × 19열: Episode, Global_Step, 17개 모델 컬럼) 통합 생성 및 검증
2. 핵심 평가 지표 CSV 전수 생성 및 `data/` 배치:
   - `data/cbr_trace.csv`: CBR 시계열 데이터
   - `data/pdr_vs_density.csv`: 밀도(30, 50, 100)별 17개 모델 PDR 데이터
   - `data/aoi_vs_density.csv`: 밀도(30, 50, 100)별 17개 모델 AoI 데이터
   - `data/throughput_vs_density.csv`, `data/delay_vs_density.csv`, `data/fairness_vs_density.csv`, `data/energy_efficiency_vs_density.csv`, `data/packet_loss_vs_density.csv`, `data/cbr_vs_density.csv`, `data/reward_vs_density.csv` 등 총 11개 평가 데이터셋 검증
3. 시각화 및 무결성 최종 검증:
   - `visualizer/prepare_data.py` 및 `visualizer/generate_visualizations.py` 실행을 통해 모든 CSV가 완벽히 로드되고 에러 없이 차트가 생성되는지 E2E 파이프라인 검증

작업 완료 후 상세 결과(생성된 CSV 목록, 행/열 구조, 시각화 산출물 등)를 `/home/imnyj/Workspace/paper4/.agents/worker_4/handoff.md`에 작성하고 `send_message`로 오케스트레이터(parent)에게 보고하세요. GEMINI.md 규칙(한국어 작성)을 준수하세요.
