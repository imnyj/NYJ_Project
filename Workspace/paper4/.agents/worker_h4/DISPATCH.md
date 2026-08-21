## 2026-08-20T08:55:42Z
[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_h4/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: H-4 송신 전력 p_tx 그리드 통일 및 30 dBm 불공정 액션 제거]
순차 실행 원칙에 따라, C-3 및 C-1, C-2 완료에 이어 **H-4** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **송신 전력 그리드 단일 상수화 (`code/etsi_cam_layer.py`)**:
   - `code/etsi_cam_layer.py`에 표준 전력 그리드 상수를 정의합니다:
     ```python
     PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20]  # 6단계 (최대 20 dBm = 100mW)
     T_GRID_S = [0.1, 0.2, 0.5, 1.0]        # 4단계
     ACTION_DIM = len(T_GRID_S) * len(PTX_GRID_DBM)  # 24
     ```
   - 30 dBm(1W)은 베이스라인 최대 전력(20 dBm)을 초과하여 제안 모델에만 부당한 이득을 주므로 완전히 제거합니다.

2. **모든 Hook 및 모듈의 그리드 참조 통일 (`code/ai_dcc_hook.py` 등)**:
   - `code/ai_dcc_hook.py` 내의 모든 DRL/AI hook 클래스가 `etsi_cam_layer`의 `PTX_GRID_DBM`, `T_GRID_S`, `ACTION_DIM`을 import하여 사용하도록 전면 리팩터링합니다.
   - hook 내부에 개별 정의되어 있던 `[0.0, 15.0, 30.0]`, `[0.0, 10.0, 20.0, 30.0]`, `[-10, 0, 10, 20]` 등의 파편화된 그리드와 30 dBm 하드코딩을 전부 제거합니다.
   - 액션 인덱스 디코딩 로직을 `(t_idx, p_idx) = (action_idx // len(PTX_GRID_DBM), action_idx % len(PTX_GRID_DBM))`로 일원화합니다.

3. **독립 검증 스크립트 작성 및 실행 (`code/test_h4_grid.py`)**:
   - `code/test_h4_grid.py`를 작성하여:
     - `etsi_cam_layer.PTX_GRID_DBM`이 정확히 `[-5, 0, 5, 10, 15, 20]`인지 확인.
     - `code/ai_dcc_hook.py`의 모든 Hook 인스턴스를 순회하며 p_tx 그리드가 단일 상수를 참조하고, 최대 전력이 20 dBm 이하임을 assert.
     - 모든 Hook의 action 공간 크기가 24인지 assert.
     - `grep` 또는 AST 분석으로 `code/` 내 30 dBm p_tx 액션 정의가 0건임을 확인.
   - `python3 code/test_h4_grid.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

4. **마스터 작업 목록 갱신 (`idea/paper4_code_fix_tasklist.md`)**:
   - H-4 항목의 상태를 [x] 완료로 변경하고 수정 파일 목록, 통일된 그리드 스펙, 독립 검증 결과를 기록합니다.

5. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_h4/handoff.md`에 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
