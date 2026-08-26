# Handoff Report — explorer_survey_genuine_3

## 1. Observation (직접 관찰 결과)
1. **`src/hpo.py` 관찰**:
   - 9개 베이스라인 알고리즘에 대한 Optuna 파라미터 샘플링 함수 `sample_hparams`(lines 92-182)와 복합 목적함수 `compute_composite_objective`(lines 185-211)가 구현되어 있음.
   - 그러나 lines 213-276에 `class SyntheticVehicle` 및 자체 더미 롤아웃 루프(`evaluate_model_in_env`)가 존재하여, `ORIGINAL_REQUEST.md` Follow-up R1/R3의 "실제 SUMO 환경 기반 정직한 HPO 수행" 요구사항과 불일치함.
   - `save_study_results` 및 `run_all_baselines_hpo`(lines 559-628)를 통해 `optuna_best_params.csv` 및 `optuna_trials_<model>.csv`가 정상적으로 저장되는 구조를 갖춤.
2. **`src/hot_swap_trainer.py` 관찰**:
   - `DualModelHotSwapManager`(lines 57-157)에 NaN/Inf 검증 가드(`validate_weights`), 스레드 락(`swap_lock`), `torch.no_grad()` 기반 파라미터/버퍼 복사 및 `select_default_devices`(lines 34-54) 멀티 GPU 분기(`cuda:0`, `cuda:1`)가 정상 구현되어 있음.
   - 그러나 `run_hot_swap_training` 내부(lines 614-660)에 `v_pos = {v: np.array([float(i * 30.0), ...])}`와 같은 하드코딩된 더미 트래픽 루프가 존재하며, SUMO/`aoi_env.py`와의 실제 연동이 누락되어 있음.
   - `torch.utils.tensorboard.SummaryWriter`를 통한 텐서보드 로깅 코드 및 에피소드별 자동 체크포인팅(`checkpoints/` 저장) 코드가 존재하지 않음 (`grep_search` 결과 일치 항목 0건).
3. **`src/evaluate.py` 관찰**:
   - 10개 모델(HeuristicScheduler + 9 RL)에 대해 5개 밀도 $\times$ 5개 시드(250회 런)를 수행하고 6대 IEEE TWC 메트릭을 계산하여 3종의 CSV(`eval_raw_runs.csv`, `eval_summary_by_density.csv`, `eval_leaderboard.csv`)를 출력하는 구조(lines 507-605)가 완성되어 있음.
4. **테스트 스위트 관찰**:
   - `/home/imnyj/venv/bin/pytest` 실행 결과, 12개 테스트 파일 내 174개 테스트 항목이 5.43초 만에 100% 성공 통과함 (`174 passed in 5.43s`).

---

## 2. Logic Chain (추론 과정)
1. **[근거: 관찰 1, 2]** `hpo.py`와 `hot_swap_trainer.py`에 잔존하는 `SyntheticVehicle` 및 로컬 딕셔너리 기반 kinematic 루프는 가짜 환경(Mocking)을 전면 배제하고 실제 SUMO(`NetSim.py`, `Communications.py`, `make_sumo_set.py`)와 연동하라는 `ORIGINAL_REQUEST.md` Follow-up 지침에 위배됨.
   $\to$ 따라서 HPO 롤아웃과 핫스왑 훈련 루프의 진입점을 `aoi_env.py` 및 `SumoNetSim`의 실제 스텝 루프로 전면 교체해야 함.
2. **[근거: 관찰 2]** 200,000 스텝(2,000 steps $\times$ 100 episodes) 동안의 수렴 분석 및 장애 복구를 위해서는 실시간 모니터링용 TensorBoard (`SummaryWriter`) 스칼라 기록과 주기적 가중치 체크포인팅 (`checkpoints/<model>_ep{ep:03d}.pt`, `best_model.pt`)이 필수적임.
3. **[근거: 관찰 1, 4]** 200,000 스텝의 막대한 컴퓨팅 연산(수십 시간 소요 가능)을 시작하기 전에 파이프라인의 전체 무결성을 보장하기 위해, 15초 이내에 SUMO 연동 $\to$ 9개 모델 추론 $\to$ 1회 핫스왑 $\to$ 1 Trial HPO $\to$ 1회 Eval을 수행하는 **Short Dummy Run (10-step)** 하네스를 구축해야 함.
4. **[근거: 지침 R4, R6]** 더미 런 검증 완료 후, 시스템은 반드시 실행을 자동 중단(Halt)하고 사용자에게 코드 검토 승인을 요청하는 프로토콜을 준수해야 함.

---

## 3. Caveats (제약 사항 및 가정)
- 본 조사는 읽기 전용(Read-only) 조사이므로 실제 소스 코드를 수정하지 않았으며 분석 및 설계 보고서만을 작성함.
- `libsumo` / `sumo` 프로세스가 100 에피소드(200,000 스텝) 동안 장기 실행될 때 발생할 수 있는 메모리 누수나 파일 디스크립터 고갈을 방지하기 위해, 에피소드 단위의 명시적 `traci.close()` 및 `torch.cuda.empty_cache()` 호출이 필요함.

---

## 4. Conclusion (최종 결론)
1. **훈련 파이프라인 개편**: `hpo.py`, `hot_swap_trainer.py`, `evaluate.py` 내의 더미 차량 루프를 제거하고 `aoi_env.py` (실제 SUMO)로 통합.
2. **200k 준비성 인프라 탑재**: `hot_swap_trainer.py`에 TensorBoard (`SummaryWriter`) 및 `checkpoints/` 저장 체계 구축.
3. **Short Dummy Run 하네스 구축**: 15초 내에 전 구간을 10스텝으로 검증하는 `tests/test_dummy_verification.py` 구성.
4. **Halt & User Review 프로토콜 준수**: 더미 검증 완료 후 대규모 연산을 시작하지 않고 실행을 즉시 Halt하여 사용자에게 코드 리뷰를 요청하도록 설계 완료.

---

## 5. Verification Method (독립 검증 방법)
1. **테스트 스위트 검증**:
   ```bash
   /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/ -v
   ```
   (174개 기존 테스트 전체 통과 확인)
2. **보고서 파일 무결성 검증**:
   - `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_3/analysis.md`
   - `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_3/handoff.md`
3. **무효화 조건 (Invalidation Conditions)**:
   - 200,000 스텝 훈련 루프가 실제 SUMO를 호출하지 않고 더미 딕셔너리로 우회하는 경우.
   - 사용자 승인 없이 200,000 스텝 훈련이 자동으로 즉시 실행되는 경우.
