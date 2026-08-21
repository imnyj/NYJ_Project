# DISPATCH — 2026-08-20T17:30:47+09:00

## Mission Objective
Fix all 12 defects (C-1 through M-12) in /code/ following the strict recommended execution sequence:
C-3 -> C-1, C-2 -> H-4 -> H-5 -> H-6 -> M-7 -> M-8 -> M-9 -> M-10 -> M-11 -> M-12.

Each defect must follow the cycle: (수정 -> 검증 -> 기록) one by one. Do not batch modifications without independent verification!

## Key Confirmed Design Decisions
1. C-3: Channel model maintained. CBR_TARGET automatically measured per vehicle density via dedicated script (measure_cbr_target.py). Reward = -1.0*over - 0.5*osc - 0.3*stale - 0.05*cost. All DRL hooks predict() updated. prev_cbr dictionary reset on episode reset.
2. C-1: Register 5 DRL models (VanillaDQN, DoubleDQN, DuelingDQN, MoEDQN, ResNetMoEDQN) into sensitivity_runner.py SA1/SA2 methods. Remove 'Proposed' (TinyMLP).
3. C-2: Implement setup_eval_hook(method) wiring in sensitivity_runner.py.
4. H-4: PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20] in etsi_cam_layer.py and imported by all hooks. Remove 30 dBm.
5. H-5: 5-stage ablation (VanillaDQN -> DoubleDQN -> DuelingDQN -> MoEDQN -> ResNetMoEDQN). action_dim=24 across all agents.
6. H-6: Tabular state_bounds neighbor axis (0.0, 1.0) and train_step() no-op.
7. M-7: n_est local neighborhood verification.
8. M-8: Local CBR per vehicle passed to vdata["cbr"] in sim_engine.py.
9. M-9: Hardcoded paths removed in sim_engine.py and sensitivity_runner.py. Move aggregator.py and train_final.py to backup/.
10. M-10: num_episodes=500, epsilon_decay=0.995 in all training scripts.
11. M-11: train_7_models class count 25->24, rename label to REMO-DQN (Proposed).
12. M-12: Terminal transitions verified across all hooks.

## Process Requirements
- Initialize and update idea/paper4_code_fix_tasklist.md with real-time status, evidence, verification results for each of the 12 items.
- Write and execute independent test scripts in /code/ for each item.
- Move deprecated TinyMLP files and legacy scripts to backup/legacy_tinymlp/ and backup/legacy_scripts/.
- Conduct final Critic review per .rules/critic.md.
- Maintain progress.md and BRIEFING.md in your working directory.
- Report completion when all Acceptance Criteria are met.

## 2026-08-20T08:34:52Z

[PARENT_INSTRUCTION_RELAY]
Parent agent에서 다음 추가 지시사항이 전달되었습니다. 적극 반영하여 운영 바랍니다:

1. **API Quota (429 에러) 대응**: 작업 진행 중 API Quota 초과나 토큰 부족 현상이 감지될 경우, 작업을 억지로 진행하지 말고 5시간(18000초) 대기/휴식 상태로 전환한 뒤 자동으로 재개하도록 스케줄링할 것.
2. **정기 보고 지원**: 메인 에이전트가 00시, 06시, 12시, 18시에 정기 보고를 수행하므로, 각 시간 직전에 progress.md 및 BRIEFING.md를 최신 상태로 갱신하여 진척 상황이 잘 반영되도록 할 것.

## 2026-08-20T22:00:20+09:00

[RESUME_TASK]
API Quota 재설정이 완료되었습니다. M-11 작업(train_7_models 클래스 수 24 일치 및 REMO-DQN Proposed 라벨 정정)부터 재개하여 M-12, 레거시 정리, 최종 Critic 검토까지 순차적으로 완료해 주시기 바랍니다.


