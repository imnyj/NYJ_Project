# Dispatch Instructions — Reviewer R2 (Verify Zero Mock Data & Visual Spec)

## Identity
- Role: Visual & Pipeline Verification Reviewer (`reviewer_r2_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/reviewer_r2_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/prepare_data.py`
- `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`
- `/home/imnyj/Workspace/paper4/.agents/worker_r2_1/handoff.md`

## Review Tasks
1. Verify `visualizer/prepare_data.py`:
   - Confirm ZERO `np.random` mock data generation logic.
   - Verify data ingestion from `data/evaluation/eval_density_results.csv`, `data/models/*_convergence.csv`, `data/models/REMO-DQN.pth`.
2. Run `python3 visualizer/plot_all.py` and inspect all 22 outputs:
   - 9 PNGs at 350 DPI.
   - 2 tables in CSV & LaTeX.
   - 200,000 steps x-axes on `1_ablation_study.png` and `3_reward_convergence.png` with Phase I/II shading.
3. Write `review.md` and `handoff.md` with verdict: `APPROVE` or `REQUEST_CHANGES`.

## 2026-08-19T11:58:29Z
당신은 Paper4 프로젝트의 R1 무결성 조치 및 시각화 검증 Reviewer(reviewer_r2_1)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/reviewer_r2_1
디스패치 명세서: /home/imnyj/Workspace/paper4/.agents/reviewer_r2_1/DISPATCH.md
원본 요청서: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md

DISPATCH.md를 읽고, visualizer/prepare_data.py의 순수 실데이터 집계 로직(0% mock data)과 visualizer/plot_all.py 실행을 통한 11대 타겟 22개 산출물(350 DPI PNG, 200k 스텝 x축, Phase I/II 음영)을 전수 검토하십시오.
review.md 및 handoff.md에 판정(APPROVE 또는 REQUEST_CHANGES)을 작성하고 send_message로 보고하십시오.

