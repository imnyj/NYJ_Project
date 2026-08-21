## 2026-08-20T08:31:37Z
[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_c3/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 단일 작업: C-3 보상 함수 재설계 및 CBR_TARGET 자동 측정]
엄격한 순차 실행 원칙에 따라, 이번 단계에서는 오직 **C-3** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **CBR_TARGET 측정 스크립트 작성 및 실행**:
   - `code/measure_cbr_target.py`를 작성하여 다양한 차량 밀도(예: 10, 20, 30, 40, 50대 등)에서 기존 채널 모델(`code/sim_engine.py` 유지) 하의 실제 CBR 범위를 측정하고, 적정 `CBR_TARGET` 기준값을 도출합니다.
   - 스크립트를 직접 실행하여 실제 측정 결과를 확인하고 기록합니다.

2. **DRL Hook 보상 함수 수정 (`code/ai_dcc_hook.py`)**:
   - `ai_dcc_hook.py` 내의 모든 DRL hook(`DuelingDQNHook`, `SARSAHook`, `VanillaDQNHook`, `DoubleDQNHook`, `MoEDQNHook`, `ResNetMoEDQNHook` 등)의 `predict()` 보상 계산 로직을 확정된 설계대로 재설계합니다:
     ```python
     T_STALE = 0.5  # 노후화 임계치(초)
     over = max(0.0, cbr_smoothed - CBR_TARGET)                 # 목표 초과 혼잡 벌점
     osc = abs(cbr_smoothed - self.prev_cbr.get(vid, cbr_smoothed))  # 요동 벌점
     stale = max(0.0, dt_since_last_cam - T_STALE)              # 정보 노후화 벌점
     cost = 0.1 / max(T_GenCam, 1e-3)                          # 전송 빈도 비용
     reward = -1.0 * over - 0.5 * osc - 0.3 * stale - 0.05 * cost
     self.prev_cbr[vid] = cbr_smoothed
     ```
   - hook 클래스에 `self.prev_cbr = {}`를 초기화하고, 에피소드 리셋 또는 hook 초기화/리셋 시 `self.prev_cbr.clear()` 되도록 구현합니다.

3. **독립 검증 스크립트 작성 및 실행 (`code/test_c3_reward.py`)**:
   - 저밀도/고밀도 합성 시퀀스 및 다양한 T_GenCam 상황에서 보상이 정상 계산되는지 검증합니다.
   - 저밀도에서 "T_GenCam=0.1 (최대 전송)"이 무조건적인 유일 최적이 되지 않고, 빈도 비용과 노후화 간의 트레이드오프가 정상 작동함을 assert합니다.
   - `python3 code/test_c3_reward.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

4. **작업 목록 파일 생성 및 실시간 기록 (`idea/paper4_code_fix_tasklist.md`)**:
   - `/home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md`를 생성/초기화합니다.
   - 12개 전체 결함 항목(C-3 -> C-1, C-2 -> H-4 -> H-5 -> H-6 -> M-7 -> M-8 -> M-9 -> M-10 -> M-11 -> M-12)의 마스터 체크리스트를 한국어로 구성합니다.
   - **C-3** 항목에 대해 [x] 완료 표시와 함께 수정 파일 목록, 변경 내용 요약, CBR 측정 결과, 독립 검증 스크립트 실행 결과 로그를 상세히 기록합니다.

5. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_c3/handoff.md`에 수행 내용, 검증 결과(명령어 및 출력), 산출물 경로를 기록하고, 오케스트레이터에게 `send_message`로 완료를 보고하세요.
