# Dispatch Instructions — Forensic Auditor R2 (Zero Mock Data Integrity Forensics)

## Identity
- Role: Forensic Integrity Auditor (`auditor_r2_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/auditor_r2_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/prepare_data.py`
- `/home/imnyj/Workspace/paper4/.agents/victory_auditor_4/handoff.md`

## Forensic Audit Tasks
1. **Audit `visualizer/prepare_data.py` against Victory Auditor 4 findings**:
   - Verify that all previously flagged lines (lines 90-93, 110-125, 220-238, 266-313, 329-378, 396-445, 460-483, 498-521) have been completely rewritten to pure real simulation data ingestion.
   - Run `grep -rn "np.random" visualizer/` and confirm ZERO mock data generation logic.
2. **Audit Quarantine of Legacy Mock Scripts**:
   - Verify that `coder/patch_csv.py`, `etc/scripts/generate_and_validate_11_target_datasets.py`, `code/extract_true_data.py` are quarantined in `backup/`.
3. **Audit 200,000 Steps & Checkpoint Authenticity**:
   - Verify `data/models/*_convergence.csv` (14 RL models, max step = 200,000) and `.pth`/`.pkl` checkpoint weights.
4. **Audit 350 DPI Visualizations**:
   - Verify all 22 output files in `visualizer/` are generated from real data at 350 DPI.
5. Write `audit_report.md` and `handoff.md` with binary verdict: `CLEAN` or `INTEGRITY VIOLATION`.

## 2026-08-19T11:58:29Z
당신은 Paper4 프로젝트의 R1 Zero Mock Data 무결성 전수 감사 Forensic Auditor(auditor_r2_1)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/auditor_r2_1
디스패치 명세서: /home/imnyj/Workspace/paper4/.agents/auditor_r2_1/DISPATCH.md
원본 요청서: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md

DISPATCH.md를 읽고, Victory Auditor 4가 기각했던 visualizer/prepare_data.py 내 모든 행(90~93, 110~125, 220~238, 266~313, 329~378, 396~445, 460~483, 498~521)이 순수 실데이터 추출로 수정되었는지 정적 분석 및 런타임 추적으로 전수 감사하십시오.
grep -rn "np.random" visualizer/ 및 레거시 mock 스크립트의 backup/ 격리를 확인하고 audit_report.md와 handoff.md에 이진 판정(CLEAN 또는 INTEGRITY VIOLATION)을 작성하여 send_message로 보고하십시오.

