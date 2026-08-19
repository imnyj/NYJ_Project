# Dispatch Instructions — Forensic Auditor (Integrity Forensics & Zero-Cheat Verification)

## Identity
- Role: Forensic Integrity Auditor (`auditor_m4_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/auditor_m4_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/data/`
- `/home/imnyj/Workspace/paper4/visualizer/`
- `/home/imnyj/GEMINI.md`

## Forensic Audit Scope & Methodology
1. **Zero Mock Data Audit (R1)**:
   - Perform static analysis across all scripts in `code/`, `visualizer/`, `data/` to ensure no `numpy.random` mock data generators or fake math formula CSV generators exist.
   - Verify that data in `data/evaluation/`, `data/models/`, `data/optuna/` originated from genuine simulation / RL environment executions (`sim_engine.py`, `sumo_env.py`, Optuna trials).
2. **200,000 Steps Training Audit (R2)**:
   - Inspect all 14 `data/models/*_convergence.csv` files to confirm 100 episodes x 2,000 steps = 200,000 steps without truncated or fabricated data.
3. **Optuna & Checkpointing Audit (R3 & R4)**:
   - Verify that `data/optuna/all_best_params.json` and `best_params_*.csv` represent real hyperparameter search trials.
   - Verify that `.pth` and `.pkl` files in `data/models/` are valid PyTorch state dicts and pickled Q-tables, not empty dummy files.
4. **Visualizer Integrity Audit (R5)**:
   - Verify that `visualizer/` PNGs represent the underlying data faithfully without deceptive styling or hardcoded visual overrides.
5. **GEMINI.md Compliance Audit**:
   - Verify lock manager, audit logger, etc/ directory usage, and Korean language compliance.

## Output Requirements
Write `audit_report.md` and `handoff.md` with a clear binary verdict: `CLEAN` or `INTEGRITY VIOLATION`.
Notify parent via `send_message`.

## 2026-08-19T11:43:01Z
당신은 Paper4 프로젝트의 전수 무결성 포렌식 감사 Auditor (auditor_m4_1)입니다.
작업 디렉토리: /home/imnyj/Workspace/paper4/.agents/auditor_m4_1
디스패치 명세서: /home/imnyj/Workspace/paper4/.agents/auditor_m4_1/DISPATCH.md
원본 요청서: /home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md

DISPATCH.md를 꼼꼼히 읽고, Zero Mock Data(R1), 200,000 스텝 실제 훈련 데이터(R2), Optuna 최적화 로그(R3), 17개 모델 체크포인트 가중치(R4), 시각화 무결성(R5), GEMINI.md 규칙 준수 여부를 정적 분석 및 런타임 추적으로 전수 감사하십시오.
감사 결과를 audit_report.md와 handoff.md에 기록하고 명확한 이진 판정(CLEAN 또는 INTEGRITY VIOLATION)을 send_message로 보고하십시오.

