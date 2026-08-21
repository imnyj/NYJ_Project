## 2026-08-20T17:48:04+09:00

[역할 및 작업 지시]
당신은 Paper4 (REMO-DQN) 코드 수정 프로젝트의 Coder Worker입니다.
당신의 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_c1_c2/
프로젝트 루트: /home/imnyj/Workspace/paper4
참조 파일:
- /home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md
- /home/imnyj/Workspace/paper4/paper4_code_review_report.md
- /home/imnyj/Workspace/paper4/idea/paper4_code_fix_tasklist.md
- /home/imnyj/Workspace/paper4/.rules/coder.md
- /home/imnyj/GEMINI.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor/critic will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[수행할 작업: C-1 & C-2 평가 러너 DRL 모델 등록 및 가중치 로드/배선]
순차 실행 원칙에 따라, C-3 완료에 이어 **C-1**과 **C-2** 결함을 수정하고 독립 검증한 뒤 기록합니다.

1. **C-1: DRL 5종 모델 등록 및 Proposed(TinyMLP) 제거 (`code/sensitivity_runner.py`)**:
   - `code/sensitivity_runner.py`의 `methods_sa1` 및 SA2 `methods` 리스트에 5개 DRL 모델(`"VanillaDQN"`, `"DoubleDQN"`, `"DuelingDQN"`, `"MoEDQN"`, `"ResNetMoEDQN"`)을 등록합니다.
   - 기존의 `"Proposed"`(TinyMLP 매핑) 항목을 완전히 제거하고, 제안 모델 라벨을 `"ResNetMoEDQN"`으로 확정합니다.

2. **C-2: `setup_eval_hook(method)` 배선 구현 (`code/sensitivity_runner.py`)**:
   - 러너가 DRL 모델을 평가하기 전에 가중치(.pth)를 로드하고 에이전트를 hook에 주입하는 `setup_eval_hook(method)` 함수를 구현합니다:
     ```python
     def setup_eval_hook(method):
         # method에 따른 에이전트 인스턴스 생성 및 가중치(.pth) 로드
         # 파일 경로 탐색: code/ 및 data/models/ 둘 다 지원
         # agent.epsilon = 0.0 (평가 시 탐험 비활성화)
         # hook = get_hook(method)
         # hook.set_agent(agent)
         # hook.is_training = False (평가 중 transition 수집 및 오염 방지)
     ```
   - `DRL_SETUP` 딕셔너리를 정의하여 각 모델(`ResNetMoEDQN`, `MoEDQN`, `DuelingDQN`, `DoubleDQN`, `VanillaDQN` 등)의 에이전트 클래스, 생성 인자, 체크포인트 파일명을 명확히 매핑합니다.
   - 각 시뮬레이션 실행 전(`run_sa1_method`, `run_sa2_method` 등) `setup_eval_hook(method)`가 반드시 호출되도록 배선합니다.

3. **독립 검증 스크립트 작성 및 실행 (`code/test_c1_c2_wiring.py`)**:
   - `ResNetMoEDQN`, `MoEDQN`, `DuelingDQN`, `DoubleDQN`, `VanillaDQN`에 대해 `setup_eval_hook()`를 호출하고 짧은 시뮬레이션(예: `duration_steps=200~300`)을 실행합니다.
   - **핵심 검증**: `hook.predict()`가 내놓는 `action_idx`의 분포가 단일값(0 고정 폴백)이 아니라, 신경망에 의해 다양한 유효 액션을 정상 출력하는지 로그 및 assertion으로 입증합니다.
   - `hook.is_training == False` 및 `agent.epsilon == 0.0` 상태가 평가 중 유지되는지 확인합니다.
   - `python3 code/test_c1_c2_wiring.py`를 실행하여 100% 통과(Exit Code 0)함을 확인합니다.

4. **마스터 작업 목록 업데이트 (`idea/paper4_code_fix_tasklist.md`)**:
   - C-1 및 C-2 항목의 상태를 [x] 완료로 업데이트하고, 수정 파일, 배선 코드 스니펫, 가중치 로드 검증 결과, 액션 다양성 실측 로그를 한국어로 상세히 기록합니다.

5. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_c1_c2/handoff.md`에 수행 내용과 검증 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
