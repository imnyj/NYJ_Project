# DISPATCH — 2026-08-20T14:03:41Z

## 2026-08-20T14:03:41Z
당신은 Milestone 1 (R1. REMO-DQN 우선 학습 및 수렴 검증) 구현 및 실행을 담당하는 Worker입니다.

### 작업 정보
- 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_m1_remo
- 프로젝트 루트: /home/imnyj/Workspace/paper4
- 원본 요청: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md
- 상세 요구사항: /home/imnyj/.gemini/antigravity-cli/brain/4c546ebc-ef10-4f86-8d8f-a76a42c04f5f/prompt_draft.md
- 선행 조사 보고서: /home/imnyj/Workspace/paper4/.agents/explorer_eval_survey_1/handoff.md

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 수행 과업
1. **`code/train_resnet.py` 수정 및 파라미터 적용**:
   - `num_episodes=100`, `duration_steps=2000`, `epsilon_decay=0.95`, `min_epsilon=0.01` 기본값 및 CLI 인자 지원
   - 매 에피소드 루프에서 무작위 차량 밀도(30, 50, 100)를 선택하여 `SimulationRunner(..., n_vehicles=density, method_params={'n_vehicles_sweep': density}, ...)`에 올바르게 주입
   - 가중치 저장 경로: `data/models/resnet_moe_dqn.pth` 및 `data/models/REMO-DQN.pth` (디렉토리 자동 생성 포함)
   - 훈련 로그 CSV 저장: `data/models/REMO-DQN_convergence.csv` (컬럼: `Episode,Global_Step,Reward,AoI_mean,CBR_mean,PDR_mean,Loss,Epsilon,Density`) 및 `code/resnet_train_log.csv`
2. **REMO-DQN 훈련 실행**:
   - 수정된 스크립트를 실행하여 100 에피소드(총 200,000 스텝) 훈련을 완료하고 가중치 및 로그 CSV가 정상 생성되었는지 확인
3. **수렴성 프로그램 검증 스크립트 작성 및 실행 (`code/verify_remo_convergence.py`)**:
   - `data/models/REMO-DQN_convergence.csv`를 읽어 초기 10 에피소드($ep \in [1, 10]$) 평균 보상 대비 마지막 10 에피소드($ep \in [91, 100]$) 평균 보상이 유의미하게 상승하고 안정화되었는지(수렴) 판정
   - 실행 시 exit code 0 및 통계 요약(초기 평균 보상, 최종 평균 보상, 상승률, 최종 엡실론 등) 출력
4. **결과 문서화**:
   - 작업 디렉토리에 `handoff.md`를 작성하고 오케스트레이터에게 완료 보고를 보내십시오.
