# Original User Request

## 2026-08-20T13:57:30Z

/home/imnyj/.gemini/antigravity-cli/brain/4c546ebc-ef10-4f86-8d8f-a76a42c04f5f/prompt_draft.md 에 작성된 프롬프트 내용에 따라 17개 모델 전체 훈련 및 시각화 데이터(CSV) 추출 파이프라인을 실행하세요. R1(REMO-DQN 수렴 검증) 통과 후 R2, R3를 순차적으로 진행해야 합니다.

## 2026-08-21T05:00:21Z

# Teamwork Project Prompt — Continuation (Quota Recovery)

> Status: Launched
> Goal: Complete the full 17-model evaluation pipeline (continuation after quota crash)
> Requested team: Full team

Working directory: /home/imnyj/Workspace/paper4
Integrity mode: development

## Critical Context — Current State (as of restart)

### REMO-DQN Training is STILL RUNNING (DO NOT KILL)
- **PID 97001** is alive and has been running for 10+ hours
- Command: `python3 code/train_resnet.py --episodes 100 --duration_steps 2000 --epsilon_decay 0.95 --output_model data/models/resnet_moe_dqn.pth --output_log data/models/REMO-DQN_convergence.csv`
- Progress: **9 out of 100 episodes completed** (≈70 min per episode)
- CSV output: `code/resnet_train_log.csv` and `data/models/REMO-DQN_convergence.csv` (identical content)
- **DO NOT restart this process. Let it continue running.**

### Already Completed Work
1. **15 model weights saved** in `data/models/`: ResNetMoEDQN, VanillaDQN, DoubleDQN, DuelingDQN, MoEDQN, PPO, SAC, DDPG, TD3, MAPPO, ActorCritic, DecisionTransformer, QLearning, SARSA, REMO-DQN
2. **13 models have 5-episode training logs** in `code/` directory (sarsa, ddqn, qlearning, moe, sac, ddpg, ppo, dt, td3, mappo, actor_critic train_log.csv files)
3. **Ablation structure data**: wo_MoE, wo_Dueling, wo_ResNet, REMO-DQN — each with 2 episodes of train_log and eval_metrics CSVs in `data/ablation_structure/`
4. **Ablation reward data**: Base — 1 episode in `data/ablation_reward/`

### What Still Needs to Be Done

## Requirements

### R1. Monitor REMO-DQN Training Completion
- PID 97001 is still running. Monitor it periodically (check CSV row count).
- When it finishes all 100 episodes, verify convergence: last 10 episodes' mean reward should be significantly higher than first 10 episodes' mean reward.
- The model weight will be auto-saved to `data/models/resnet_moe_dqn.pth`.

### R2. Complete Remaining Model Training (100 episodes each, 2000 steps)
- The existing 5-episode logs for 13 models need to be EXTENDED to 100 episodes.
- Each model must be trained for 100 episodes × 2000 steps with epsilon_decay=0.95 and random density (30/50/100).
- All training logs must be CSV files with columns: Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density
- All trained model weights must be saved/updated in `data/models/`.
- Non-RL models (Fixed10Hz, ReactDCC, AdaptDCC) need simulation-based evaluation runs, not training.

### R3. Complete Ablation Study (evaluation_plan.md Item 1)
- **Structure ablation**: Extend wo_MoE, wo_Dueling, wo_ResNet training to 100 episodes each.
- **Reward ablation**: Complete w/o R1, w/o R2, w/o R3 runs (100 episodes each).
- Generate merged ablation CSV for convergence comparison.

### R4. Generate Evaluation CSVs (evaluation_plan.md Item 3)
- Merge all 17 models' reward convergence data into a single CSV for plotting.
- Generate CBR trace data, PDR vs density, AoI vs density CSVs.
- All CSVs must be in `data/` directory with clear naming.

## Acceptance Criteria

### R1 Verification
- [ ] REMO-DQN `resnet_train_log.csv` contains 100 rows of episode data.
- [ ] Convergence verified: mean reward of episodes 91-100 > mean reward of episodes 1-10.

### R2 Verification
- [ ] Each of the 17 models has a training/evaluation log CSV with 100 episodes of data.
- [ ] All DRL model weights (`.pth` or `.pkl`) exist in `data/models/`.

### R3 Verification
- [ ] Ablation structure CSVs (REMO-DQN, wo_ResNet, wo_MoE, wo_Dueling) each have 100 episodes.
- [ ] Ablation reward CSVs (REMO-DQN, wo_R1, wo_R2, wo_R3) each have 100 episodes.
- [ ] Merged ablation CSV exists.

### R4 Verification
- [ ] Merged 17-model convergence CSV exists with all models represented.
- [ ] CBR trace, PDR vs density, AoI vs density CSVs exist with all 17 models.
