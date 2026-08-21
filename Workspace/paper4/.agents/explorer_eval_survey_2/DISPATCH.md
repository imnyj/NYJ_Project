## 2026-08-20T13:59:38Z
당신은 16개 베이스라인 모델 훈련 및 데이터 수집 파이프라인 분석을 담당하는 Explorer입니다.

### 작업 정보
- 작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/explorer_eval_survey_2
- 프로젝트 루트: /home/imnyj/Workspace/paper4
- 원본 요청: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md
- 상세 요구사항: /home/imnyj/.gemini/antigravity-cli/brain/4c546ebc-ef10-4f86-8d8f-a76a42c04f5f/prompt_draft.md
- 평가 계획서: /home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md

### 조사 목표 (R2. 16개 모델 전수 파이프라인)
1. 16개 모델의 목록과 각각의 훈련/실행 스크립트 매핑 조사:
   - 17개 전체 모델: REMO-DQN(R1), Fixed 10Hz, ReactDCC, AdaptDCC, MoEDQN, MAPPO, PPO, SAC, DDPG, TD3, DuelingDQN, DoubleDQN, VanillaDQN, QLearning, SARSA, ActorCritic, DecisionTransformer
   - 기존 `code/` 내 개별 훈련 스크립트 (`train_moe.py`, `train_dueling_dqn.py`, `train_ddqn.py`, `train_dqn.py`, `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`, `run_full_evaluation.py`, `train_7_models.py` 등) 및 표준/비RL 알고리즘(Fixed 10Hz, ReactDCC, AdaptDCC)의 실행 메커니즘 분석
2. 16개 모델 전수 실행 및 가중치/로그 저장 표준화:
   - 100 에피소드, 2000 스텝, 랜덤 밀도(30/50/100) 조건 통일 방안
   - 모든 DRL 모델의 가중치 저장 경로 (`data/models/*.pth`, `*.pkl`) 확인
   - 각 모델의 실행 결과(Episode, Cumulative_Steps, Reward, Loss 등) 개별 CSV 파일 저장 위치 및 형식 일관성 조사
