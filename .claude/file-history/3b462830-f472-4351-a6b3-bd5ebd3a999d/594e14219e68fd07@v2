# Antigravity 작업 검토 + critic 전면 코드 재검토

## Context

Antigravity가 `review/antigravity_update_20260830.md`에서 두 가지 작업을 보고했다. (1) libsumo 메모리 누수 방지, (2) HPO 결과를 `run_all.py`에 반영. 이 중 (2)는 "HPO로 최적 파라미터를 찾아도 최종 훈련이 기본값으로만 학습하던 치명적 누락"을 고쳤다는 주장이다.

직접 확인한 결과 **보고된 두 작업 모두 실제로 코드에 반영되어 있으나, (2)의 핵심 목적이 절반만 달성되었다.** 보상 가중치 `w1~w4`가 환경이 아니라 모델 생성자로 흘러들어가 `**hparams`에 흡수되고 있어, HPO가 튜닝한 보상 형태가 200k 본훈련에 전혀 반영되지 않는다. 크래시가 나지 않기 때문에 25개 신규 테스트가 전부 통과했음에도 결함이 그대로 남았다.

또한 본훈련 직전 상태로서 몇 가지 위험이 있다. 현재 `optuna_best_params.csv`는 모델당 **3 trial / 35 step**짜리 스모크 HPO 산출물이며, `checkpoints/`에는 테스트가 남긴 스모크 체크포인트가 쌓여 있는데 `run_all.py`는 기본이 `resume=True`다.

목표는 (A) 위 결함을 수정해 200k 본훈련을 안전하게 출발시킬 수 있는 상태로 만들고, (B) critic 서브에이전트로 파이프라인 전체를 재검토해 보고서를 남기는 것이다.

---

## Part 1 — Antigravity 작업 검토 결과

### 검증된 사항 (보고 내용과 코드 일치)
- 메모리 누수 방지: `src/hot_swap_trainer.py:27` `import gc`, `:1782` `close()`, `:2002/2009-2010` `del env` + `gc.collect()`. `src/evaluate.py:254-256`, `src/hpo.py:390-392` 동일 패턴 확인.
- `--hparams-csv` CLI 인자 및 로딩 파이프라인: `run_all.py`에 `load_hparams_from_csv`, `get_hparams_for_model`, `normalize_model_name` 신규 추가, `run_hot_swap_training(hparams=...)`로 주입. `run_hot_swap_training`은 원래부터 `hparams` 인자를 받고 있었다(`hot_swap_trainer.py:1810`).
- 인수인계 사항 1(18차원 구형 체크포인트)은 **이미 해소된 상태**다. `checkpoints/*.pt`를 열어보면 전부 17차원(`trunk.0.weight (64, 17)`)이다.

### 결함 (심각도 순)

**F1. 보상 가중치가 환경에 전달되지 않음 — HPO 반영의 핵심 실패**
`w1~w4`는 `AoiV2IEnv.__init__`의 인자다(`hot_swap_trainer.py:721-724`). 그런데 `run_all.py`가 만든 hparams 딕셔너리는 `HotSwapTrainer`를 거쳐 `model_cls(state_dim=..., num_channels=..., **self.hparams)`로 들어간다(`hot_swap_trainer.py:597,600`). 아홉 개 베이스라인 생성자가 모두 `**hparams`로 끝나므로 `w1`, `w2`, `w3`, `w4`, `w1_raw~w4_raw`가 **조용히 삼켜진다**. 실제 증거로 `checkpoints/CARLTON_best.pt`의 저장된 hparams에 `'w1': 0.523336, 'w1_raw': 0.270...`이 그대로 들어있다. 한편 `run_hot_swap_training`이 만드는 환경은 `AoiV2IEnv(density, seed, max_steps, warmup_steps)`뿐이라(`hot_swap_trainer.py:1918-1923`) 가중치는 항상 기본값 0.5/0.2/0.2/0.1이다. `hpo.py:318-331`은 `REWARD_WEIGHT_KEYS`로 env에 제대로 넘긴다 — 즉 HPO 조건과 본훈련 조건이 서로 다른 보상함수를 쓴다.

**F2. 중복 행 선택 로직이 최적화 방향과 반대**
`optuna.create_study(direction="minimize")`(`hpo.py:488`)인데 `run_all.py`의 dedup은 `if prev_score is not None and score <= prev_score: continue` — 즉 **높은 값을 우수 trial로 취급**한다. 멀티 trial CSV를 넣으면 최악 trial을 고른다. 또한 새 행의 `score`가 `None`이면 조건을 통과해 기존 최적값을 덮어쓴다.

**F3. 테스트가 production 체크포인트 디렉토리를 오염**
`tests/test_run_all.py`의 `test_09~12`는 `subprocess`로 실제 `run_all.py`를 돌린다. `run_hot_swap_training`의 `checkpoint_dir` 기본값이 절대경로 하드코딩(`hot_swap_trainer.py:1812`)이라 `coder/checkpoints/`에 `PPO_ep001.pt`, `DummyPolicy_ep001.pt` 등이 실제로 생성됐다. `run_all.py`는 `--no-resume`가 없으면 `resume=True`이므로 200k 본훈련이 이 1-에피소드 스모크 체크포인트를 이어받고 `start_ep=1`이 되어 199 에피소드만 돈다. `logs/execution_notes.md`에도 resume 충돌을 인지했다고 적혀 있으나 기본값은 그대로다.

**F4. 컬럼 폴백이 무관한 키까지 주입**
`load_hparams_from_csv`의 3단계 폴백은 `ignored_cols`에 없는 모든 컬럼을 훑는다. `w1~w4`, `w1_raw~w4_raw`가 모든 행에서 non-NaN이므로 어느 모델이든 이 8개 키가 붙는다. F1과 합쳐져 모델 생성자로 흘러간다.

**F5. 별칭 키 중복 등록**
`hparams_by_model[raw_name] = clean_hparams`로 정규명과 원본명을 둘 다 넣는다. `get_hparams_for_model`이 이미 3단계 폴백을 하므로 불필요하고, `len(hparams_by_model)`을 쓰는 로그가 실제 모델 수를 부풀린다.

**F6. 사소한 것들**
`normalize_model_name`이 호출마다 `canonical_by_clean` 딕셔너리를 재구축. `_is_valid_hparam_value`에 list/ndarray가 들어오면 `pd.isna`가 배열을 반환해 `ValueError: truth value ambiguous`.

### 결함은 아니지만 본훈련 전 판단이 필요한 사항
- 현재 `optuna_best_params.csv`는 **모델당 3 trial**(`optuna_trials_*.csv` 행 수)이고 `--n-steps` 기본이 35다(`hpo.py:456,462`). 기본 `n_trials=15`에도 못 미치는 스모크 산출물이다.
- `results/hpo/`에 폐기된 베이스라인(HybridPPO, MAPPO, MPDQN, PureAoI, DuelingQAoI, SACAoI, HyARPPO)의 15-trial CSV가 남아 혼동을 준다.

---

## Part 2 — 적용할 수정

사용자 결정: **보상 가중치는 전 모델 공통 고정**, **테스트 격리와 체크포인트 정리 둘 다 수행**.

> 짚어둘 점: Optuna의 목적함수 `compute_composite_objective`(`hpo.py:271-296`)는 `w_error=1.0, w_aoi=0.5, w_outage=2.0, w_power=0.2`로 **고정**되어 있고 샘플링된 `w1~w4`와 무관하다. 즉 `w1~w4`는 "고정된 평가 지표에 대해 튜닝된 보상 형태(reward shaping)"라서 그 자체로는 방법론적으로 방어 가능했다. 공통 가중치로 고정하면 이 정보를 버리게 되고, 함께 선택된 모델 하이퍼파라미터는 "다른 보상 아래에서 고른 값"이 되어 짝이 맞지 않는다. 그래서 아래 5단계에 **`w*`를 탐색공간에서 제거한 HPO 재실행**을 포함한다. trial당 약 4초라 9모델 × 15 trial × 3 seed도 저렴하다.

1. **`w*` 키를 모델 hparams에서 분리** — `run_all.py`에 `REWARD_WEIGHT_KEYS`(`hpo.py:88`에서 import하거나 동일 상수 정의)와 `w1_raw~w4_raw`를 `ignored_cols`에 추가해 애초에 모델 hparams로 들어가지 않게 한다. F4 해소.
2. **방어선 이중화** — `HotSwapTrainer.__init__`(`hot_swap_trainer.py:589-600`)에서 `model_cls`에 넘기기 전 환경 전용 키를 걸러내고, 걸러진 키가 있으면 `logging.warning`으로 알린다. `**hparams`가 조용히 삼키는 문제를 다시 만들지 않기 위함. `hpo.py`의 `assert_hparams_reach_model` 가드와 같은 취지.
3. **공통 보상 가중치 상수화** — `AoiV2IEnv`의 현재 기본값 0.5/0.2/0.2/0.1을 그대로 단일 출처 상수(`hot_swap_trainer.py` 모듈 상수 `DEFAULT_REWARD_WEIGHTS`)로 승격하고, `run_hot_swap_training` → `AoiV2IEnv` 생성부(`:1918`), `evaluate.py:209`, `hpo.py:324`가 모두 같은 상수를 쓰게 한다. 훈련·평가·HPO가 동일 보상함수를 쓴다는 것이 코드로 보장된다.
4. **F2 dedup 방향 수정** — `direction="minimize"`에 맞춰 낮은 `best_value`를 채택하고, `score is None`인 행이 기존 최적을 덮어쓰지 않게 한다. F5 별칭 중복 등록 제거, F6 정리.
5. **HPO 재실행** — `sample_reward_weights` 호출을 objective에서 제거(또는 `--tune-reward-weights` 플래그로 기본 off), `python src/hpo.py --n-trials 15 --n-steps 350`으로 9개 베이스라인 재실행. `n_steps=35`는 측정 구간이 3.5 시뮬초에 불과하므로 `hot_swap_trainer.py:1816-1821` 주석이 근거로 드는 350으로 올린다. 기존 CSV는 `backup/` 프로토콜에 따라 백업 후 교체하고, 폐기 베이스라인의 stale `optuna_trials_*.csv`도 `backup/`으로 이동.
6. **F3 테스트 격리** — `run_all.py`에 `--checkpoint-dir` 인자를 추가해 `run_hot_swap_training`에 전달하고, `tests/test_run_all.py`의 `test_09~12`가 `tmp_path` 하위를 쓰게 한다. `tensorboard_dir`도 동일 처리.
7. **체크포인트 정리** — `checkpoints/*.pt` 전체를 `backup/preflight_<타임스탬프>/`로 옮기고, 본훈련은 `--no-resume`로 출발한다.

## Part 3 — critic 서브에이전트 전면 재검토

`.rules/critic.md`를 따른다. **critic은 직접 수정하지 않고 검토 결과만 파일로 남긴다.** 기존 `critic/critic_core.md`, `critic_baselines.md`, `critic_physics.md` 3분할 체계가 있으므로 이를 유지·갱신하고 파이프라인 축을 하나 추가한다.

Part 2 수정을 **먼저 적용한 뒤** critic을 돌린다. 그래야 이미 아는 결함으로 리포트가 채워지지 않고 새 결함을 찾는 데 집중된다.

네 개의 critic 에이전트를 병렬로 띄운다. 각 에이전트에는 `.rules/critic.md`, `Conversation.md`(설계 사양), `aoi_scheduling_design.md`, 그리고 담당 파일 목록을 컨텍스트로 준다.

| 에이전트 | 담당 | 산출물 |
|---|---|---|
| critic-core | `hot_swap_trainer.py` (2000+줄, 환경·SMDP 루프·핫스왑·체크포인트) | `critic/critic_core.md` 갱신 |
| critic-physics | `Communications.py`, `rl_interface.py`, `dynamics_predictor.py`, `sumo/` | `critic/critic_physics.md` 갱신 |
| critic-baselines | `baselines/` 9종 + `heuristic_scheduler.py` | `critic/critic_baselines.md` 갱신 |
| critic-pipeline | `run_all.py`, `hpo.py`, `evaluate.py`, `tests/` 전체 | `critic/critic_pipeline.md` 신규 |

각 리포트는 `.rules/critic.md`에 따라 다음을 명시적으로 다룬다. 빈 구현·`TODO`·`pass`, 설계 사양 대비 구현 일치 여부, 오타·변수명 오류, **데이터 누수**(훈련/평가 시드 및 환경 공유), 논리 결함. 발견 항목마다 `파일:줄` 근거를 달고, 심각도와 담당 에이전트(coder/visualizer)를 지정한다. 모호한 지점은 추측하지 말고 리포트에 질문으로 남긴다.

마지막에 네 리포트를 종합해 `review/claude_audit_20260831.md`를 작성한다. 기존 `claude_audit_20260827.md`, `claude_audit_20260828.md`와 같은 형식을 따르고, Part 1의 F1~F6 처리 결과를 함께 기록한다.

---

## Verification

1. `cd Workspace/paper4/coder && python -m pytest tests/ -q` — 기존 135개 + 신규 테스트 전체 통과.
2. **F1 회귀 테스트 신규 추가**: `run_all.py`가 만든 hparams에 `w1~w4`가 없음을 단언하고, `AoiV2IEnv`가 공통 가중치로 생성되는지 확인한다. 현재 25개 테스트 중 이를 잡는 것이 하나도 없다.
3. **F3 확인**: 테스트 스위트 실행 전후로 `ls coder/checkpoints/`를 비교해 신규 `.pt`가 생기지 않음을 확인.
4. **F2 확인**: 동일 모델 2행(각각 `best_value` 1.0과 2.0)짜리 CSV로 낮은 쪽이 선택되는지 단위 테스트.
5. **스모크 실행**: `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO --no-resume --checkpoint-dir /tmp/...` 정상 종료 및 로그에 HPO 파라미터 적용 확인.
6. **HPO 재실행 후**: 새 `optuna_best_params.csv`에 `w*` 컬럼이 없고 9개 모델 행이 모두 있으며 `best_value`가 각 `optuna_trials_*.csv`의 **최솟값**과 일치하는지 대조.
7. 본훈련 출발은 위 6단계가 전부 통과한 뒤 사용자 승인을 받고 진행한다.
