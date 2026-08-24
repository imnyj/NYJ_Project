# Worker 3 Dispatch

## 2026-08-21T05:08:43Z
당신은 Ablation Study (Structure & Reward) 수행 및 데이터 생성을 전담하는 전문 Worker (Worker 3)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/worker_3 (메타데이터용)
프로젝트 루트: /home/imnyj/Workspace/paper4

반드시 가장 먼저 `/home/imnyj/Workspace/paper4/ORIGINAL_REQUEST.md` 및 `evaluation_plan.md` 파일을 확인하여 사용자 요구사항을 숙지하세요.

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[담당 파일 소유권 (Write Ownership)]
- `code/ai_dcc_hook.py` (reward_variant 지원 보완)
- `code/run_ablation_structure.py`
- `code/run_ablation_reward.py`
- `data/ablation_study.csv`, `data/ablation_structure.csv`, `data/ablation_reward.csv`

[상세 수행 목표 (R3)]
1. `code/ai_dcc_hook.py` 보완:
   - `AIDCCHookBase`에 `reward_variant` 파라미터 및 R1(w/o AoI penalty), R2(w/o CBR penalty), R3(w/o PDR reward), Full Reward(REMO-DQN) 분기 수식 완벽 지원
2. Structure Ablation 4종 실행 (100 에피소드 × 2000 스텝, ACTION_DIM=24, random density):
   - 대상: `wo_MoE`, `wo_Dueling`, `wo_ResNet`, `REMO-DQN`
   - GPU 3을 활용하여 100 에피소드 완주 훈련 및 로그 생성
3. Reward Ablation 4종 실행 (100 에피소드 × 2000 스텝, ACTION_DIM=24, random density):
   - 대상: `w/o R1`, `w/o R2`, `w/o R3`, `REMO-DQN`
   - GPU 3을 활용하여 100 에피소드 완주 훈련 및 로그 생성
4. 병합된 Ablation CSV 생성:
   - `data/ablation_study.csv` (또는 `data/ablation_structure.csv`, `data/ablation_reward.csv`)를 `data/` 디렉토리에 정확한 100행 구조로 병합 생성


## 2026-08-21T09:00:12Z
**Context**: Ablation Study 8종 진행 상황 점검
**Content**: Worker 3님, Structure Ablation 4종 및 Reward Ablation 4종 100에피소드 훈련/평가 및 `data/ablation_study.csv` 병합 진행 상태가 어떻게 되는지 확인 부탁드립니다.
**Action**: 현재 진행 상태 및 남은 작업, 또는 완료 여부를 보고해 주시기 바랍니다.

## 2026-08-21T14:00:12Z
**Context**: Ablation Study 8종 훈련 및 병합 CSV 생성 완료 확인
**Content**: Worker 3님, Structure Ablation 4종 및 Reward Ablation 4종의 100에피소드 완주 여부 및 `data/ablation_study.csv`, `data/ablation_structure.csv`, `data/ablation_reward.csv` 병합 생성 현황을 확인하여 최종 보고(handoff.md)를 전달해 주시기 바랍니다.
**Action**: 최종 완료 보고서 및 handoff.md 제출 부탁드립니다.
