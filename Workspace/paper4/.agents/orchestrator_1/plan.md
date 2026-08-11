# Master Execution Plan — Paper4 Project

## Overview
V2X 환경에서의 하이브리드 DRL 기반 혼잡 제어 모델(ResNet-MoE-Dueling DQL) 및 13종 비교군 모델의 훈련 완료, 밀도/속도 평가, IEEE 스타일 시각화 생성 프로젝트.

## Milestones

### Phase 0: Survey & Initial Analysis
- [ ] Dispatch 3 parallel Explorers to analyze codebase structure, `run_parallel_evaluation.py`, existing checkpoints (around episode 52), evaluation scripts, and visualization dependencies.
- [ ] Synthesize Explorer reports into `PROJECT.md` (Feature Inventory, Architecture, Code Layout).

### Milestone 1 (M1): Checkpoint Resuming & Model Training
- [ ] Modify `run_parallel_evaluation.py` to support checkpoint resuming from episode 52.
- [ ] Run and complete training for all 14 models until reward convergence.
- [ ] Verify save of weight files (.pth/.pkl) and final logs.
- [ ] Verification: Build/test/log checks + Reviewer + Challenger + Forensic Auditor.

### Milestone 2 (M2): Performance Evaluation
- [ ] Run density and speed performance evaluation across all 14 models.
- [ ] Extract `eval_density_results.csv` and `eval_speed_results.csv`.
- [ ] Verify CSV outputs (complete metrics for PDR, CBR, AoI, energy; no null values).
- [ ] Verification: Gate review + Forensic Auditor.

### Milestone 3 (M3): IEEE Publication-Grade Visualization & Review
- [ ] Develop visualization script to generate publication-grade comparison plots (Convergence, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF, etc.).
- [ ] Run critic/evaluator agent review to verify IEEE style compliance (axis labels, legend, font, visual contrast).
- [ ] Final gate review & claim completion.
