# BRIEFING — 2026-08-27T01:54:21Z

## Mission
AoI 기반 V2I 상향링크 RL 스케줄링 파이프라인(R1: `src/hot_swap_trainer.py`, `src/aoi_env.py` 및 관련 테스트)의 아키텍처 결함 및 버그 조사/분석 보고서 작성

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1
- Original parent: 3d6a38f8-f0cb-48c4-98ea-b46062a1aceb
- Milestone: AoI-aware V2I uplink RL scheduling pipeline architectural fixes

## 🔒 Key Constraints
- Read-only investigation — do NOT modify source code directly
- Korean language for report/communication
- Follow 5-component handoff format (Observation, Logic Chain, Caveats, Conclusion, Verification Method)

## Current Parent
- Conversation ID: 3d6a38f8-f0cb-48c4-98ea-b46062a1aceb
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/aoi_env.py`, `src/hot_swap_trainer.py`, `src/rl_interface.py`
  - `tests/test_hot_swap.py`, `tests/test_aoi_env_genuine.py`, `tests/test_dummy_verification.py`, `tests/test_evaluation.py`
  - `ORIGINAL_REQUEST.md`, `Conversation.md`, `idea/scenario.md`
- **Key findings**:
  1. 4항 보상 수식 ($I_{redundant}$ 포함) 및 단언문 A4가 `src/aoi_env.py` 및 `src/hot_swap_trainer.py`에 적용되어 있으나, `src/aoi_env.py`의 `p_min, p_max` 기본값이 `20.0, 30.0`으로 남아있어 표준 상수(`P_MIN=10.0, P_MAX=23.0`)와 동기화 필요.
  2. 전력 크레딧 할당 버그(`tx_powers[-1]`)는 개별 `step_tx_power[vid]` 매핑으로 해소됨.
  3. Resume 로직에서 `save_checkpoint` 시 `best_reward` 미저장 및 `run_hot_swap_training` 재개 시 `best_reward = -inf`로 초기화되어 과거 `best.pt`를 덮어쓰는 결함 확인.
  4. 18차원 관측 벡터 확장 및 $\Delta \in [0.1, 45.0]\text{s}, P \in [10.0, 23.0]\text{dBm}$ 액션 바운드 변경에 따른 38개 테스트 실패 원인 규명.
- **Unexplored areas**: None (R1 조사 범위 100% 완료).

## Key Decisions Made
- `src/hot_swap_trainer.py`의 `save_checkpoint` / `load_checkpoint` / `run_hot_swap_training` 내 `best_reward` 영속화 및 복원 전략 수립.
- `handoff.md`에 5-Component 형식의 상세 조사 보고서 작성 완료.

## Artifact Index
- /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1/handoff.md — 최종 조사 보고서
- /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1/progress.md — 진행 상태 및 하트비트
- /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_1/DISPATCH.md — 디스패치 로그
