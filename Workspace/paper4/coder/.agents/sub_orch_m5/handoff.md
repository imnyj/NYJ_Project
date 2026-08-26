# Handoff Report — Milestone 5 (Evaluation Harness & Benchmark Verification)

- **Agent**: `sub_orch_m5` (Sub-Orchestrator for Milestone 5)
- **Target**: `orchestrator_1` (Parent Orchestrator)
- **Status**: Complete (Hard Handoff)
- **Date**: 2026-08-26T22:26:00+09:00

---

## 1. Observation

1. **최적 파라미터 로딩 및 10개 모델 인스턴스화**:
   - `results/hpo/optuna_best_params.csv` 파일로부터 9개 베이스라인 모델(`HybridPPO`, `HybridSAC`, `HybridTD3`, `MAPPO`, `HyARPPO`, `MPDQN`, `PureAoI`, `DuelingQAoI`, `SACAoI`)의 HPO 최적 하이퍼파라미터를 파싱하여 `HeuristicScheduler` 포함 총 10개 모델을 정상 초기화함.
2. **250회 대규모 평가 매트릭스 실행**:
   - 10개 모델 x 5개 차량 밀도 (15.0, 25.0, 35.0, 45.0, 55.0 veh/km) x 5개 시드 (42, 101, 2024, 777, 999) = 총 250회의 완전한 물리/무선/역학 시뮬레이션 평가를 수행함.
3. **6대 IEEE TWC 표준 성능 지표 계산 및 CSV 파일 생성**:
   - `results/eval/eval_raw_runs.csv`: 250회 전체 원시 시뮬레이션 결과 (250 행)
   - `results/eval/eval_summary_by_density.csv`: 밀도별 평균 및 집계 요약 (50 행)
   - `results/eval/eval_leaderboard.csv`: 10개 모델 전체 성능 순위 및 복합 평가 점수 리더보드 (10 행)
4. **테스트 및 린트 검증**:
   - `tests/test_evaluation.py` 내 21개 테스트를 포함하여 전체 테스트 스위트 100% 통과 (`174 passed in 4.90s`).
   - `ruff check src/evaluate.py tests/test_evaluation.py` 린트 검사 무결점 통과 (`All checks passed!`).

---

## 2. Logic Chain

1. **수치 검증 및 무결성(Integrity)**:
   - 하드코딩된 기대값이나 가짜 더미 결과를 일체 배제하고, `Communications.judge_uplink` 기반 레일리 페이딩 SINR 간섭 모델, TraCI 신호등 동역학, 추정 오차 적분 $e_i(t) = \|\mathbf{x}_i(t) - \hat{\mathbf{x}}_i(t)\|$, instantaneous 및 peak AoI, RF 에너지 $E = 10^{(p-30)/10} \times 0.001$, 제인의 공정도(Jain's Fairness Index)를 수치적 불변성(Invariants)에 따라 엄격히 계산함.
2. **밀도 증가에 따른 물리적 상호작용 검증**:
   - 차량 밀도 $\rho$가 15 $\to$ 55 veh/km로 증가함에 따라, 서브채널 충돌 확률 및 Outage/패킷 손실률이 자연스럽게 상승하며 AoI 및 위치 추정 오차가 비례하여 증가함을 확인 (`eval_summary_by_density.csv`).
3. **리더보드 분석 및 모델 특성 반영**:
   - **PureAoI** (Whittle 인덱스 기반 AoI 임계 스케줄러) 및 **HeuristicScheduler** (신호등 상태 전이 기반 급변점 강제 갱신)가 낮은 평균 AoI와 위치 추정 오차를 달성하며 상위권을 기록함.
   - RL 모델 중 **HybridPPO**, **MAPPO**, **HybridSAC**, **SACAoI**가 안정적인 성능을 보임.

---

## 3. Caveats

- 본 평가는 9개 베이스라인 RL 모델 및 Heuristic 스케줄러 간의 비교 벤치마크이며, **R6 규칙(Halt Before Proposed Method)**에 따라 사용자의 명시적 지시 전까지 새로운 제안 알고리즘(Proposed Novel Method)의 설계나 코드는 작성되지 않았습니다.

---

## 4. Conclusion

- 마일스톤 5 (S5 / R5: Evaluation Harness & Benchmark Verification)의 모든 목표가 100% 달성되었습니다.
- 10개 모델에 대한 250회 평가 매트릭스 완료, 3대 CSV 데이터셋 생성 완료, 174개 전체 테스트 통과 완료.

---

## 5. Verification Method

```bash
# 1. 평가 하네스 CLI 재현성 실행
/home/imnyj/venv/bin/python -m src.evaluate --hparams-csv /home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv --output-dir /home/imnyj/Workspace/paper4/coder/results/eval

# 2. 단위/통합 테스트 스위트 전체 실행
/home/imnyj/venv/bin/pytest tests/ -v

# 3. 린트 검사
/home/imnyj/venv/bin/ruff check src/evaluate.py tests/test_evaluation.py

# 4. CSV 산출물 데이터 확인
ls -la /home/imnyj/Workspace/paper4/coder/results/eval/
head -n 12 /home/imnyj/Workspace/paper4/coder/results/eval/eval_leaderboard.csv
```
