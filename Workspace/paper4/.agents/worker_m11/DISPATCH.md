## 2026-08-20T10:28:03Z

[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_m11/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: M-11 train_7_models.py 클래스 수 24 일치 및 제안 모델 라벨 정정]
순차 실행 원칙에 따라, M-10 완료에 이어 **M-11** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **`train_7_models.py` 및 복잡도 분석 스크립트 정합**:
   - `code/train_7_models.py`:
     * 클래스 수(액션 차원)를 기존 25에서 표준 `ACTION_DIM = 24` (`etsi_cam_layer` import)로 전면 일치시킵니다.
     * 제안 모델 라벨을 구버전 `"TinyMLP (Proposed)"`에서 `"REMO-DQN (Proposed)"` (또는 `"ResNetMoEDQN (Proposed)"`)으로 정정합니다.
     * 7대 비교 모델 구성을 논문과 일치하도록 정합합니다:
       1. `REMO-DQN (Proposed)` (ResNetMoEDQN, action_dim=24)
       2. `MoEDQN` (MoEDQN, action_dim=24)
       3. `DuelingDQN` (DuelingDQN, action_dim=24)
       4. `DoubleDQN` (DoubleDQN, action_dim=24)
       5. `VanillaDQN` (VanillaDQN, action_dim=24)
       6. `StdMLP` (표준 MLP 분류기, action_dim=24)
       7. `DecTree` (의사결정나무 분류기, 24개 클래스)
     * 합성 벤치마크 데이터 생성 시 `num_classes=24` 및 `state_dim=5`를 사용하여 추론 지연시간(Latency), 파라미터 수(Params), FLOPs를 정확히 측정하고 CSV/JSON으로 출력하도록 보장합니다.
   - `code/calc_flops.py`, `code/plot_complexity.py`도 `ACTION_DIM = 24` 및 `REMO-DQN` 라벨로 일관되게 정합합니다.

2. **독립 검증 스크립트 작성 및 실행 (`code/test_m11_benchmark_models.py`)**:
   - `code/test_m11_benchmark_models.py`를 작성하여:
     * `train_7_models.py` 내 클래스 수 / 액션 차원이 정확히 24이며 25클래스 잔존이 0건임을 검증.
     * 제안 모델 표기가 `"REMO-DQN (Proposed)"` 또는 `"ResNetMoEDQN"`으로 일치함을 검증.
     * 7개 벤치마크 모델 인스턴스화, forward pass(입력: (N, 5), 출력: (N, 24)), 파라미터 및 지연시간 측정이 정상 동작함을 assert.
     * `calc_flops.py`가 에러 없이 정상 실행되어 각 모델의 FLOPs를 계산하는지 assert.
   - `python3 code/test_m11_benchmark_models.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

3. **마스터 작업 목록 갱신 (`idea/paper4_code_fix_tasklist.md`)**:
   - M-11 항목의 상태를 [x] 완료로 변경하고 7대 모델 스펙, 클래스 수 정합, 복잡도 측정 결과 및 독립 검증 결과를 상세히 기록합니다.

4. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_m11/handoff.md`에 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
