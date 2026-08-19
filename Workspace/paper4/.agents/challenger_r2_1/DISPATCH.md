# Dispatch Instructions — Challenger R2 (Empirical Verification & Stress-Test)

## Identity
- Role: Empirical & Stress-Test Challenger (`challenger_r2_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/challenger_r2_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`

## Challenge Tasks
1. Perform empirical verification of 350 DPI on all 9 PNG files using PIL.
2. Empirically verify that data in `data/pdr_vs_density.csv`, `data/aoi_vs_density.csv`, `data/reward_convergence.csv`, `data/cbr_trace.csv` strictly matches the raw simulation data in `data/evaluation/eval_density_results.csv` and `data/models/*_convergence.csv`.
3. Test pipeline idempotency (run `plot_all.py` multiple times and check for 0-byte or corrupted files).
4. Write `challenge_report.md` and `handoff.md` with verdict: `APPROVE` or `REJECT`.

## 2026-08-19T11:58:29Z
당신은 Paper4 프로젝트의 실데이터 일치성 및 350 DPI 실증 Challenger(challenger_r2_1)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/challenger_r2_1
디스패치 명세서: /home/imnyj/Workspace/paper4/.agents/challenger_r2_1/DISPATCH.md
원본 요청서: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md

DISPATCH.md를 읽고, PIL 라이브러리로 9개 PNG 파일 전체의 350 DPI 해상도를 실측하고, visualizer가 사용하는 데이터가 data/evaluation/eval_density_results.csv 및 data/models/*_convergence.csv 원본 실데이터와 오차 없이 일치하는지 적대적으로 검증하십시오.
결과를 challenge_report.md와 handoff.md에 기록하고 판정(APPROVE 또는 REJECT)을 send_message로 보고하십시오.

