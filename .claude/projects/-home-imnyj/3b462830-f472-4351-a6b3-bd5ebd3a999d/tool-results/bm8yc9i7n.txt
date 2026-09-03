# critic_pipeline — 실험 파이프라인 및 테스트 스위트 비판적 검증

- 작성: critic-pipeline agent
- 일자: 2026-08-31
- 검증 범위: `coder/run_all.py`, `coder/src/hpo.py`, `coder/src/evaluate.py`, `coder/tests/` 전체(144개), `pytest.ini`, `conftest.py`
- 검증 방식: 전 파일 정독 후 근거가 되는 `file:line`을 직접 확인했고, 판정이 갈리는 항목은 read-only 실행으로 수치를 측정했다. 소스와 테스트는 한 줄도 수정하지 않았다.

---

## 판정

**REJECT — 현 상태로 200,000-step 본훈련을 기동해서는 안 된다.** 훈련 코드 자체가 아니라 그 결과를 논문 수치로 바꾸는 하류 경로가 끊겨 있는 것이 이유다. 가장 결정적인 것은 `src/evaluate.py`가 체크포인트를 전혀 읽지 않는다는 사실이다. 벤치마크 하네스는 `instantiate_model`로 무작위 초기화된 새 모델을 만들어 그대로 평가하며, 파일 전체에 `torch.load`도 `state_dict`도 `checkpoint`라는 단어조차 없다. 즉 지금 200k step을 4장의 GPU로 2.4시간 돌려 체크포인트를 만들어도, 논문 표에 들어갈 숫자는 학습되지 않은 난수 가중치의 성능이다. 훈련 자체는 손해지만 복구 가능한 반면, 이 상태로 평가까지 진행해 표를 뽑으면 결과물 전체가 무의미해진다. 여기에 HPO 목적함수가 "아무것도 측정되지 않은 실행"을 전역 최소값 0.0으로 평가하는 구조적 결함, `evaluate.py`가 여전히 w1..w4를 모델 생성자에 흘려보내는 미완결 수정, HeuristicScheduler만 다른 행동 공간에서 평가되는 공정성 결함이 겹친다. 마지막으로 테스트 스위트 144개 중 상당수가 `tests/contract_adapters.py`의 그림자 구현을 검증하고 있어, 이 결함들이 전부 통과된 채 오늘까지 온 이유를 설명한다. C1과 C2를 고치기 전에는 기동 승인을 낼 수 없다. C1·C2·C3·H1만 해결되면 나머지는 훈련과 병행 수정이 가능하므로 그 시점에 CONDITIONAL로 재판정할 수 있다.

---

## 지적 사항

### CRITICAL

---

**C1 — `src/evaluate.py`는 학습된 체크포인트를 읽지 않는다. 벤치마크 전체가 난수 가중치를 평가한다.**

- 심각도: CRITICAL
- 근거:
  - `src/evaluate.py:301` — `model = instantiate_model(canonical_name, hparams)`
  - `src/evaluate.py:138-175` — `instantiate_model`은 `get_baseline(...)(state_dim=..., num_channels=..., **params)`로 새 객체를 만들 뿐이다
  - `src/evaluate.py` 전체에 `torch.load` / `load_state_dict` / `checkpoint` 문자열이 0회 등장한다(grep 확인)
  - 체크포인트는 `src/hot_swap_trainer.py:2097`(`{model}_ep{n}.pt`)와 `:2102`(`{model}_best.pt`)에 정상적으로 기록된다
  - `simulation_plan.md:240` — "벤치마크 평가 — `src/evaluate.py`. 5개 밀도 × 5개 시드"라고 명시되어 있으므로 이 하네스가 논문 표의 유일한 산출 경로다
- 무엇이 잘못되었나: 훈련 산출물과 평가 하네스 사이에 연결이 존재하지 않는다. `run_all.py`는 `checkpoints/`에 쓰고, `evaluate.py`는 그 디렉터리를 쳐다보지 않는다.
- 논문에 미치는 영향: 200k step 훈련의 결과가 표에 반영되지 않는다. 9개 baseline의 리더보드는 초기화 난수의 순위가 되며, HeuristicScheduler만 유일하게 실제 정책이므로 규칙 기반 baseline이 모든 RL 기법을 이기는 표가 나올 가능성이 높다. 그 표를 근거로 쓴 어떤 주장도 성립하지 않는다.
- coder에게: `instantiate_model`에 `checkpoint_path: Optional[str]` 인자를 추가하고, `run_full_benchmark`가 `checkpoint_dir`(기본 `coder/checkpoints`)에서 `{canonical_name}_best.pt`를 찾아 `load_state_dict`하도록 배선하라. 체크포인트가 없으면 `logger.warning` 후 조용히 넘어가지 말고 **예외를 던져 중단**해야 한다. 이 결함이 오늘까지 살아남은 이유가 정확히 "조용한 fallback"이기 때문이다. 아울러 `eval_raw_runs.csv`에 실제로 로드한 체크포인트 파일명과 그 파일의 episode 번호를 열로 남겨, 표의 각 행이 어느 가중치에서 나왔는지 사후 추적 가능하게 하라.

---

**C2 — HPO 목적함수는 "아무것도 측정되지 않은 실행"을 전역 최소값으로 평가한다.**

- 심각도: CRITICAL
- 근거:
  - `src/hpo.py:272-297` — `compute_composite_objective`. 네 항 모두 `metrics.get(key, 0.0)` 형태이며 유효성 검사가 없다
  - `src/hpo.py:286-289` — `mean_err`, `mean_aoi`, `outage_rate` 기본값 0.0
  - `src/hot_swap_trainer.py:1774-1792` — 관측이 하나도 없으면 `mean_aoi=0.0`, `mean_err=0.0`, `packet_loss=0/max(1,0)=0.0`, `avg_power`는 `decoder.p_min`(10.0 dBm)으로 fallback
  - `src/hpo.py:398-399` — `avg_p_norm = (10.0 - P_MIN)/(P_MAX - P_MIN) = 0.0`
  - 실측: `compute_composite_objective({"mean_error":0.0,"mean_aoi":0.0,"outage_rate":0.0,"avg_power_norm":0.0})` → **0.0**. 실제 정상 trial의 값은 `results/hpo/optuna_trials_PPO.csv`에서 1.209 / 1.315, 9개 모델 best_value가 0.887~1.220이다
  - `src/hpo.py:494-496` — `direction="minimize"`
- 무엇이 잘못되었나: 환경이 죽었거나 warmup이 부족해 관측이 0인 실행이 정상 실행보다 항상 좋은 점수를 받는다. `AoiV2IEnv.get_metrics`는 `n_observations`(`hot_swap_trainer.py:1834`)라는 공백 신호를 이미 계산해서 반환하는데, HPO는 이 값을 한 번도 읽지 않는다.
- 논문에 미치는 영향: TPE는 목적함수를 최소화하므로, 어떤 하이퍼파라미터 조합이 우연히 환경을 조기 종료시키거나 차량이 RSU 범위에 들지 못하게 만들면 그 조합이 "최적"으로 선택된다. 이 경로가 한 번이라도 발동하면 해당 모델의 tuned hparams는 성능이 아니라 실패를 선택한 결과다. 현재 커밋된 CSV는 35-step 탐색이었고, 코드 주석(`hpo.py:642-644`)이 스스로 "35 step은 어떤 차량도 RSU 원반에 도달하지 못한다"고 적고 있으므로 이 실패 모드는 가설이 아니라 이미 일어났을 가능성이 높다.
- coder에게: `evaluate_model_in_env`가 반환하기 직전에 `metrics["n_observations"]`와 `metrics["tx_attempts"]`를 검사하고, 둘 중 하나라도 0이면 `compute_composite_objective`를 호출하지 말고 실패 페널티(예: 100.0)를 반환하도록 하라. 동시에 `evaluate_trial_multiseed`가 seed별 `n_observations`를 `trial.set_user_attr`로 남겨 CSV에서 확인 가능하게 하라. `compute_composite_objective` 자체에도 `n_observations`가 인자로 들어오면 0일 때 `float("inf")`를 반환하는 방어선을 추가하는 편이 안전하다.

---

**C3 — `src/evaluate.py::load_optimal_hparams`는 w1..w4를 여전히 모델 생성자로 흘려보낸다. 오늘의 수정 #1이 절반만 적용되었다.**

- 심각도: CRITICAL
- 근거:
  - `src/evaluate.py:117-122` — 제외 목록이 `["model_name", "category", "best_value", "best_trial_number", "hparams_json"]`뿐이다. `ENV_ONLY_HPARAM_KEYS`도 `reward_weights_json`도 빠져 있다
  - `src/evaluate.py:110-114` — `hparams_json`을 그대로 `json.loads`한 뒤 아무 필터도 적용하지 않는다. 반면 `run_all.py:213-216`은 동일 위치에서 `if k not in ENV_ONLY_HPARAM_KEYS` 필터를 건다
  - `src/evaluate.py:120-121` — `params_` 접두어 제거 로직도 없다(`run_all.py:235-236`에는 있다)
  - 커밋된 `results/hpo/optuna_best_params.csv`의 `hparams_json` 안에 `"w1_raw": 0.116..., "w1": 0.079185` 등이 실제로 들어 있다
  - 실측(read-only): 실제 프로젝트 CSV로 `load_optimal_hparams`를 호출하면 9개 모델 **전부** `['reward_weights_json','w1','w1_raw','w2','w2_raw','w3','w3_raw','w4','w4_raw']`가 hparams에 남는다. PPO의 최종 키 15개 중 9개가 오염된 값이다
  - 실측: `instantiate_model("PPO", hparams)`는 예외 없이 성공하고 `hasattr(model,'w1')`은 `False`다. 즉 `**hparams`가 조용히 삼킨다
- 무엇이 잘못되었나: `run_all.py`에는 `ENV_ONLY_HPARAM_KEYS` 필터가 들어갔지만 `evaluate.py`는 자체 로더를 별도로 갖고 있고 그 로더는 손대지 않았다. `git diff` 기준 `src/evaluate.py`의 오늘 변경분은 6줄뿐이며 `load_optimal_hparams` 근처가 아니다.
- 논문에 미치는 영향: 평가 시 모델 생성자에 `reward_weights_json="{...}"` 같은 문자열까지 넘어간다. 지금은 조용히 삼켜지지만, 어떤 baseline이 향후 `**hparams`를 `dict` 병합이 아니라 SB3 kwargs로 전달하면 그 시점에 런타임 오류가 나거나 더 나쁘게는 잘못된 값이 들어간다. 무엇보다 "보상 가중치는 벤치마크의 속성이며 모델에 절대 전달되지 않는다"는 수정 #1의 불변식이 평가 경로에서만 깨져 있다는 것이 문제다.
- coder에게: `evaluate.py`의 자체 로더를 삭제하고 `run_all.load_hparams_from_csv`를 import해서 재사용하라. 로더가 두 벌 존재하는 것 자체가 이 결함의 원인이다. 단일화가 어렵다면 최소한 `ignored_cols`에 `ENV_ONLY_HPARAM_KEYS | {"reward_weights_json", ...}`을 합집합으로 넣고 `hparams_json` 파싱에도 동일 필터를 걸어라. 그리고 `tests/test_evaluation.py`에 `run_all.py`의 `test_26`과 대칭인 회귀 테스트(실제 프로젝트 CSV를 읽어 `ENV_ONLY_HPARAM_KEYS`와의 교집합이 비어 있음을 단언)를 추가하라.

---

### HIGH

---

**H1 — HeuristicScheduler만 다른 행동 공간에서 평가된다. Δ 범위가 RL baseline의 약 1/4.5이다.**

- 심각도: HIGH
- 근거:
  - `src/evaluate.py:163-164` — `delta_min=params.get("delta_min", 0.5)`, `delta_max=params.get("delta_max", 10.0)`
  - `src/heuristic_scheduler.py:35-36` — 클래스 자신의 기본값은 `delta_min=0.1, delta_max=45.0`
  - `src/rl_interface.py:541-550` — `ActionDecoder`는 `delta_max=0.0`을 "시나리오에서 지금 해석하라"는 sentinel로 쓰며 `DELTA_MAX`로 대체한다
  - 실측: `DELTA_MIN=0.1, DELTA_MAX=45.0`인 반면 `instantiate_model("HeuristicScheduler")`가 만든 객체는 `delta_min=0.5, delta_max=10.0`
  - HPO CSV에 `delta_min` / `delta_max` 열이 없으므로 `params.get`은 항상 이 리터럴 기본값을 쓴다
- 무엇이 잘못되었나: 9개 RL baseline은 `[0.1, 45.0]`초 안에서 Δ를 고르는데 규칙 기반 baseline만 `[0.5, 10.0]`초로 제한된다. 특히 `delta_max=10.0`은 적색 신호 대기 중 백오프 규칙(`heuristic_scheduler.py` 주석 8-10행이 설계 근거로 드는 바로 그 규칙)을 무력화한다. 45초 정지 구간에서 10초마다 갱신을 강제당하므로 전력과 혼잡 페널티를 부당하게 더 문다.
- 논문에 미치는 영향: 도메인 지식 baseline을 인위적으로 약화시킨 비교가 된다. IEEE TWC 심사에서 baseline 핸디캡은 치명적인 지적 사유이고, 반대로 이 값을 고쳤을 때 heuristic이 일부 RL 기법을 이긴다면 논문의 서사 자체를 다시 써야 한다. 어느 쪽이든 지금 알아야 한다.
- coder에게: `evaluate.py:163-164`의 기본값을 `ActionDecoder`가 해석한 `DELTA_MIN` / `DELTA_MAX`에서 읽어오도록 바꿔라. 리터럴을 다시 적지 말고 `from src.rl_interface import DELTA_MIN, DELTA_MAX` 후 `params.get("delta_min", DELTA_MIN)` 형태로 쓰되, `DELTA_MAX`는 `refresh_scenario_constants()` 이후 값이어야 하므로 환경 생성 이후 시점에 읽어야 한다. 아울러 `p_high/p_mid/p_low`도 `P_MIN`/`P_MAX`와 대조해 같은 종류의 리터럴 표류가 없는지 확인하라.

---

**H2 — 평가 결과가 SUMO 시나리오 캐시 상태에 의존한다. 동일 (model, density, seed)가 재현되지 않는다.**

- 심각도: HIGH
- 근거:
  - `src/hot_swap_trainer.py:929-933` — `ss.DENSITY = self.density; ss.MAX_STEPS = ...; random.seed(self.seed); np.random.seed(self.seed); ss.make_sumo_files()`
  - `src/sumo/make_sumo_set.py:277-282` — 서명이 일치하면 **아무 것도 하지 않고 즉시 return**한다
  - `src/sumo/make_sumo_set.py:332-336`, `:440` — 재생성 경로에서는 `random.uniform` / `random.randint`를 수백 번 소비한다
  - `src/hot_swap_trainer.py:1632` — 업링크 성공 판정이 `random.random() < prob`. 즉 전역 `random` 스트림을 재생성 여부와 공유한다
  - `src/sumo/make_sumo_set.py:204` — `MAX_STEPS`는 "캐시된 지평이 더 길기만 하면 재사용"이라 명시적으로 순서 의존을 허용한다
  - 실측(read-only, HeuristicScheduler, n_steps=40):
    - A1 (d=25, s=42, 캐시 적중) → `mean_error 0.3852`, `n_observations 933`
    - A2 (동일, 캐시 적중) → `mean_error 0.3852` (A1과 완전 동일)
    - B (d=15, s=42 → 재생성)
    - A3 (d=25, s=42, B가 재생성한 뒤) → `mean_error 0.3851` — **A1과 불일치**
- 무엇이 잘못되었나: `evaluate_single_run`의 결과가 `(model, density, seed)`의 순수 함수가 아니다. 앞선 실행이 시나리오를 재생성했는지 여부가 `random` 스트림 위치를 바꾸고, 그것이 업링크 성공 추첨을 바꾼다. `evaluate_single_run:206-207`이 `torch.manual_seed`와 `np.random.seed`만 걸고 `random.seed`를 걸지 않는 것도 같은 문제의 일부다(현재는 `_init_sumo`가 우연히 걸어주지만, 그 이후 소비량이 가변이다).
- 논문에 미치는 영향: 재현성이 깨진다. 위 실측의 차이는 소수 넷째 자리로 작지만, 이는 40 step 실행이기 때문이고 250회 × 100 step 전수 실행에서 누적되면 순위가 바뀔 수 있다. 더 심각한 것은 부분 재실행이다. 리더보드에서 한 모델만 다시 돌리면 그 모델은 다른 난수 스트림에서 측정되므로 나머지 8개와 비교 불가능해진다. 4-GPU 병렬 훈련에서도 각 프로세스가 자기 `ss` 전역을 갖지만 `generated.rou.xml`은 공유 파일이므로 동일 위험이 있다(생성 자체는 `make_sumo_set.py:235-256`의 flock으로 직렬화되어 파일 정합성은 지켜진다).
- 참고: 위 실측 때문에 현재 `src/sumo/.sumo_gen_signature.json`의 `MAX_STEPS`가 490.0으로 남아 있다(HEAD는 950.0, 세션 시작 시점은 850.0). 본훈련 기동 전에 의도한 파라미터로 재생성해야 한다. 이 파일이 세션마다 다른 값으로 바뀌어 있다는 사실 자체가 본 지적의 증거다.
- coder에게: 시나리오를 실행 중 재생성하지 말고 **한 번 생성해 동결**하라. 구체적으로 (1) 본훈련·평가 전에 `make_sumo_files(force_regenerate=True)`를 한 번 호출해 서명을 확정하고, (2) `AoiV2IEnv._init_sumo`는 서명 불일치 시 재생성 대신 예외를 던지는 `strict` 모드를 갖게 하며, (3) `evaluate_single_run:206` 근처에 `random.seed(seed)`를 `env` 생성 **이후**에 한 번 더 걸어 시나리오 생성 소비량과 무관하게 시뮬레이션 난수 스트림을 고정하라. (4) `eval_raw_runs.csv`에 `.sumo_gen_signature.json`의 해시를 열로 기록해 표의 모든 행이 같은 시나리오에서 나왔음을 증명 가능하게 하라.

---

**H3 — 평가 시드가 훈련 에피소드 시드 및 HPO 튜닝 시드와 겹친다.**

- 심각도: HIGH
- 근거:
  - `src/evaluate.py:72` — `DEFAULT_SEEDS = [42, 101, 2024, 777, 999]`
  - `src/hot_swap_trainer.py:1985` — 에피소드마다 `AoiV2IEnv(..., seed=seed + ep, ...)`
  - `run_all.py:281` — `--seed` 기본 42, `simulation_plan.md:137/143/149/155` — 4개 그룹 모두 `--seed 42`
  - 따라서 훈련은 seed 42~141의 100개 시나리오를 본다. 평가 시드 중 **42와 101이 이 구간 안에 있다**
  - `src/hpo.py:485`와 `:596` — HPO 기본 튜닝 시드 `[42, 101, 2024]`. 평가 시드 5개 중 **3개가 튜닝에 쓰인 시드**다
- 무엇이 잘못되었나: 평가 집합이 훈련 집합 및 튜닝 집합과 분리되어 있지 않다. seed 42·101 셀은 모델이 학습 중 실제로 본 교통 실현이고, seed 42·101·2024 셀은 하이퍼파라미터가 그 위에서 선택된 실현이다.
- 논문에 미치는 영향: 전형적인 data leakage다. 리더보드 5개 시드 중 최대 3개가 오염되어 있으므로 일반화 성능 주장이 성립하지 않는다. 심사자가 시드 목록 세 개를 나란히 놓기만 하면 즉시 드러난다.
- coder에게: 훈련·튜닝·평가 시드를 겹치지 않는 세 구간으로 분할하라. 예를 들어 훈련 `seed + ep` (42~141), HPO 튜닝 `[1001, 1002, 1003]`, 평가 `[5001, 5002, 5003, 5004, 5005]`처럼 상수로 명시하고 세 파일이 하나의 상수 모듈에서 읽게 하라. 세 집합의 교집합이 비어 있음을 단언하는 테스트를 추가하라. 이 수정은 훈련 기동 전에 확정해야 한다. 훈련이 끝난 뒤 평가 시드만 바꾸면 되지만, HPO 시드는 이미 CSV에 반영되어 있으므로 HPO 재실행 여부를 함께 결정해야 한다.

---

**H4 — "outage / packet loss"는 프레임 오류율이고, 실제 갱신 손실(`tx_abandoned`)은 표에 도달하지 않는다.**

- 심각도: HIGH
- 근거:
  - `src/hot_swap_trainer.py:1779` — `packet_loss = total_tx_fails / max(1, total_tx_attempts)`
  - `src/hot_swap_trainer.py:1615-1616` — 재시도마다 `total_tx_attempts += 1`
  - `src/hot_swap_trainer.py:1662-1663` — 실패마다 `total_tx_fails += 1`
  - `src/hot_swap_trainer.py:1671-1672` — `MAX_TX_RETRIES` 소진 시에만 `total_tx_abandoned += 1`. 이것이 "RSU가 끝내 갱신을 받지 못한" 사건이다
  - `src/hpo.py:402` — `metrics["outage_rate"] = metrics.get("packet_loss_rate", 0.0)`. 둘은 같은 값이다. `results/hpo/optuna_trials_PPO.csv`에서 `user_attrs_outage_rate`와 `user_attrs_packet_loss_rate`가 모두 0.0536으로 동일하다
  - `src/evaluate.py:321-333` — `agg_cols`에 `tx_abandoned`가 없다. `tx_attempts`/`tx_fails`도 없다
- 무엇이 잘못되었나: 파일 헤더(`evaluate.py:15-21`, `hpo.py:10-14`)는 outage와 packet loss를 별개 지표로 광고하지만 구현상 하나뿐이고, 그 하나는 링크 계층 프레임 오류율이다. 정보 갱신 관점의 손실률은 계산되어 반환되면서도 집계에서 탈락한다.
- 논문에 미치는 영향: AoI 논문에서 의미 있는 손실 지표는 "갱신이 끝내 전달되지 않은 비율"이지 "프레임 한 장이 깨진 비율"이 아니다. 재시도로 결국 성공한 전송은 AoI를 늘릴 뿐 정보 손실은 아니다. 현재 정의는 재시도를 많이 하는 정책에 불리하게 편향되어 있고, composite score에서 가중치 2.0으로 가장 크게 반영되므로(`evaluate.py:349`, `hpo.py:294`) 순위를 직접 왜곡한다. 또한 "6개 지표"라는 표현이 실제로는 5개이므로 원고 문구 자체가 부정확해진다.
- coder에게: `get_metrics`에 `update_loss_rate = total_tx_abandoned / n_intervals_closed`를 별도 키로 추가하고, `evaluate.py`의 `agg_cols`에 `tx_attempts`, `tx_fails`, `tx_abandoned`, `update_loss_rate`를 모두 넣어라. composite의 outage 항은 프레임 오류율이 아니라 `update_loss_rate`를 써야 한다. 두 지표를 표에 나란히 싣고 원고에서 어느 쪽이 outage이고 어느 쪽이 packet loss인지 명시하도록 writer에게 전달하라.

---

**H5 — 전력 지표가 전송 빈도를 반영하지 않는다. 에너지 효율 주장을 뒷받침할 수 없다.**

- 심각도: HIGH
- 근거:
  - `src/hot_swap_trainer.py:1788-1792` — `avg_power = np.mean(self.tx_powers)`. `tx_powers`는 전송 1회마다 하나씩 쌓인다(`:1427`)
  - `src/evaluate.py:345-351` — composite의 전력 항이 `avg_tx_power_dbm` 기반이다
  - `src/hpo.py:398-399` — HPO도 `avg_tx_power_dbm`을 정규화해 쓴다
  - `src/hot_swap_trainer.py:1797-1799` — 빈도를 반영하는 `total_energy_joules`는 계산되지만 어떤 목적함수에도 들어가지 않는다
- 무엇이 잘못되었나: 20 dBm으로 초당 10번 쏘는 정책과 20 dBm으로 10초에 1번 쏘는 정책의 `avg_tx_power_dbm`이 정확히 같다. 전송 빈도(Δ)를 제어하는 것이 이 논문의 핵심 행동인데, 전력 지표가 그 축에 완전히 둔감하다.
- 추가로, `src/evaluate.py:345`의 정규화가 `(avg_tx_power_dbm - 20.0).clip(lower=0)/10.0`으로 하드코딩되어 있다. 이는 코드베이스가 이미 폐기했다고 주석에 적어둔 `[20, 30]` dBm 창(`hot_swap_trainer.py:1786-1787`, `hpo.py:396-397`)의 잔재다. 실제 범위는 `[10, 23]`이므로 20 dBm 미만은 전부 0으로 눌리고, 리더보드의 전력 항은 사실상 20~23 dBm 구간에서만 작동한다. HPO는 `(p - 10)/13`을 쓰므로 **HPO가 최적화한 목적함수와 리더보드가 순위를 매기는 목적함수가 다르다.**
- 논문에 미치는 영향: "전력을 아낀다"는 주장을 뒷받침하는 지표가 그 주장을 측정하지 못한다. 그리고 HPO와 리더보드의 목적함수 불일치는 "튜닝된 모델이 리더보드에서 나쁘게 나온다"는 설명 불가능한 결과를 만들 수 있다.
- coder에게: composite의 전력 항을 `total_energy_joules`(또는 차량-초당 정규화 에너지)로 교체하라. 그리고 `evaluate.py`의 정규화 상수를 `hpo.py`와 동일하게 `(p - P_MIN)/(P_MAX - P_MIN)`으로 통일하되, 두 파일이 같은 헬퍼 함수를 import하도록 만들어 재발을 막아라. 리터럴 20.0과 10.0은 삭제 대상이다.

---

**H6 — `n_observations`가 집계에서 탈락해, 아무것도 측정되지 않은 실행이 표에서 보이지 않는다.**

- 심각도: HIGH
- 근거:
  - `src/hot_swap_trainer.py:1829-1835` — 주석이 이 키의 존재 이유를 명시한다: "모든 다른 지표는 관측이 없을 때 그럴듯한 숫자로 퇴화한다. `n_observations == 0`이 아무것도 측정되지 않았음을 분명히 말한다"
  - `src/evaluate.py:321-333` — `agg_cols`에 `n_observations`도 `n_vehicles_seen`도 없다
  - `src/evaluate.py:334`, `:342` — `groupby(...)[agg_cols].mean()`이므로 두 요약 CSV에서 완전히 사라진다
- 무엇이 잘못되었나: 공백 감지 신호를 만들어 놓고 논문 산출물 경로에서 버린다. `eval_raw_runs.csv`에는 남지만(`**metrics` 전개, `evaluate.py:313`), 사람이 실제로 보는 summary와 leaderboard에는 없다.
- 논문에 미치는 영향: 250회 실행 중 몇 개가 빈 실행이어도 리더보드는 정상으로 보인다. 이 저장소는 정확히 이 실패(warmup 35 → 관측 0)를 이미 한 번 겪었다.
- coder에게: `agg_cols`에 `n_observations`와 `n_vehicles_seen`을 추가하고(평균이 아니라 합계 또는 최소값이 적절하다), `run_full_benchmark` 말미에 `df_raw["n_observations"].min() == 0`이면 경고가 아니라 예외를 던지도록 하라.

---

**H7 — 테스트 스위트의 상당 부분이 `tests/contract_adapters.py`의 그림자 구현을 검증한다.**

- 심각도: HIGH
- 근거: 아래 "무의미하거나 오도하는 테스트 목록" 절에 `file:line` 단위로 전부 정리했다. 요약하면 다음 실측 결과가 핵심이다.
  - `tests/contract_adapters.py:99-105` — `HeuristicScheduler.decide_grant`의 위임 분기가 문자 그대로 `pass`다. `import src.heuristic_scheduler as hs`를 하고 `hasattr` 검사까지 한 뒤 아무것도 하지 않고, 바로 아래 자체 규칙(`:107-128`)을 실행한다
  - 실측: `ca.HeuristicScheduler is hs.HeuristicScheduler` → `False`, `ca.ActionDecoder is rli.ActionDecoder` → `False`, `ca.RetrospectiveReplayBuffer is rli.RetrospectiveReplayBuffer` → `False`
  - 실측: 동일 입력 `[0.0, 2.0, 0.0]`에 대해 `src.rl_interface.ActionDecoder`는 `(2.121, 2, 16.5)`, `contract_adapters.ActionDecoder`는 `(22.55, 2, 16.5)`를 반환한다. 실제 디코더는 기하 사상(`rl_interface.py:524-532`)이고 어댑터는 선형 사상이라 완전히 다른 함수다
  - `tests/contract_adapters.py:444-470` — `run_hpo_study`가 환경도 학습도 없이 `delta*0.1 + (p-10)*0.01`을 목적함수로 쓰는 가짜다
  - `tests/contract_adapters.py:508-552` — `calculate_metrics`가 `AoiV2IEnv.get_metrics`와 별개 구현이며, `peak_aoi`를 최대값이 아닌 **평균**으로 계산하고(`:525`), 에너지에 프로덕션 코드가 "출처 없는 대용값이며 2.23배 과대"라고 명시적으로 폐기한 `0.001`초를 그대로 쓴다(`:531` vs `hot_swap_trainer.py:1793-1799`)
  - 위임이 실제로 작동하는 것은 `StateVectorizer.vectorize`(`:159-166`), `predict_dynamics`(`:75-80`), `extract_tls_features`(`:28-33`), `DualModelHotSwapManager`(`:477-478`) 넷뿐이다
- 무엇이 잘못되었나: `contract_adapters.py`는 "동료 에이전트가 아직 모듈을 작성 중일 수 있으므로 100% 호환 구현을 제공한다"는 전제(`:5-8`)로 만들어졌는데, 그 전제는 오래전에 소멸했고 지금은 프로덕션 코드와 다르게 동작하는 병렬 구현이 테스트 대상으로 남았다. 게다가 `except (ImportError, AttributeError)`는 실제 모듈이 내부에서 `AttributeError`를 던져도 조용히 그림자로 넘어간다.
- 논문에 미치는 영향: 144개라는 테스트 수가 안전 근거로 인용될 수 없다. 실제로 C1(체크포인트 미로드), C2(공백 실행 최소값), C3(w1..w4 유출), H1(Δ 범위 불일치)이 전부 이 스위트를 통과했다.
- coder에게: `tests/contract_adapters.py`에서 `HeuristicScheduler`, `ActionDecoder`, `RetrospectiveReplayBuffer`, `run_hpo_study`, `sample_hparams`, `calculate_metrics`의 fallback 구현을 **삭제**하고 `src.*`에서 직접 재export하라. import가 실패하면 테스트가 실패해야 한다. `DummyPolicy`만 테스트 전용 모델로 남기는 것이 타당하다. 삭제 후 깨지는 테스트가 곧 그동안 아무것도 검증하지 않던 테스트이므로, 그 목록을 그대로 재작성 대상으로 삼으면 된다.

---

**H8 — HPO 롤아웃의 `model.update` 예외가 조용히 삼켜진다.**

- 심각도: HIGH
- 근거: `src/hpo.py:368-371`
  ```
  try:
      model.update(batch)
  except Exception:
      pass
  ```
- 무엇이 잘못되었나: 어떤 baseline의 `update`가 배치 형식 불일치 등으로 항상 예외를 던져도 HPO는 정상 종료하고 "튜닝 결과"를 낸다. 그 모델은 실제로는 학습 없이 초기 가중치로만 평가된 것이다.
- 논문에 미치는 영향: 9개 모델 중 어느 것이 실제로 학습했는지 알 수 없다. `evaluate_trial_multiseed:439-441`도 seed 단위 예외를 `logger.warning` 후 100.0으로 흡수하므로 (`hpo.py:439-441`), 3개 시드 중 2개가 터져도 study는 완주한다.
- coder에게: `except Exception: pass`를 제거하고 최소한 `logger.exception` 후 카운터를 올려라. `evaluate_model_in_env`가 `n_update_failures`를 반환하고, 0이 아니면 그 trial을 실패 처리하거나 `trial.set_user_attr`로 남겨 CSV에서 확인 가능하게 하라. `evaluate_trial_multiseed`의 100.0 흡수도 `n_failed_seeds`를 user_attr로 남겨야 한다.

---

### MEDIUM

---

**M1 — 커밋된 `optuna_best_params.csv`는 3-trial × 35-step 스모크 탐색 결과이며, 아홉 개의 서로 다른 보상 함수 아래에서 선택되었다.**

- 심각도: MEDIUM
- 근거:
  - `results/hpo/optuna_trials_*.csv` 9개 파일 모두 trial 3개
  - `optuna_trials_PPO.csv`의 trial 0 `duration`이 3.89초. 3개 시드 × 35 step에 해당한다
  - `optuna_best_params.csv`의 `hparams_json` 안에 `w1_raw`~`w4_raw`와 `w1`~`w4`가 그대로 들어 있다. 즉 이 CSV는 `tune_reward_weights`가 항상 켜져 있던 수정 전 코드의 산출물이다
  - 각 모델의 `w1`이 0.079(PPO)에서 0.855(MA2HDQN)까지 흩어져 있다
- 무엇이 잘못되었나: 지금의 `run_all.py`는 이 CSV의 w1..w4를 무시하고 `DEFAULT_REWARD_WEIGHTS`(0.5/0.2/0.2/0.1)로 학습한다. 그런데 CSV의 하이퍼파라미터는 각자 다른 보상 아래에서, 3회 탐색으로, 3.5 시뮬레이션 초 동안 측정해 고른 값이다. 선택 근거가 되었던 목적함수와 실제 학습에 쓸 목적함수가 다르다.
- 논문에 미치는 영향: "Optuna로 하이퍼파라미터를 최적화했다"는 문장을 쓸 수 없다. 3-trial TPE는 `n_startup_trials` 기본값(10) 미만이라 전부 무작위 샘플이며, 탐색이라 부를 수 없다.
- coder에게: 수정된 `hpo.py`(reward weight 고정, `n-steps` 350)로 HPO를 **재실행**한 뒤 CSV를 교체하라. 재실행 전에 C2(공백 실행 방어)를 반드시 먼저 적용해야 한다. 그렇지 않으면 재실행 결과도 신뢰할 수 없다. `--n-trials`는 최소 30 이상을 권한다(아래 M2 참조). 재실행이 시간상 불가능하다면 원고에서 "Optuna 최적화"라는 표현을 빼고 "문헌 기본값 사용"으로 정직하게 기술하도록 writer에게 전달하는 편이 낫다.

---

**M2 — HPO 탐색 예산과 대리 지표가 200k step 결과를 대표하지 못한다.**

- 심각도: MEDIUM
- 근거:
  - `src/hpo.py:458`, `:638` — `n_trials` 기본 15. TPESampler 기본 `n_startup_trials`가 10이므로 TPE가 실제로 안내하는 trial은 5개뿐이다
  - `src/hpo.py:462`, `:645` — `n_steps` 기본 350(35 시뮬레이션 초). 본훈련은 모델당 200,000 step
  - `src/hpo.py:433` — `train_steps_during_rollout=2`, 배치 16(`:367`). 350 step 동안 최대 700회 업데이트
  - `src/hpo.py:489-490` — `MedianPruner(n_startup_trials=3, n_warmup_steps=1)`가 설정되지만 objective 안에 `trial.report()` 호출이 없다. 프루너는 절대 발동하지 않는 죽은 설정이다
- 무엇이 잘못되었나: 350 step, 700 업데이트에서 좋은 학습률은 200,000 step에서 좋은 학습률과 체계적으로 다르다(짧은 예산은 큰 학습률을 선호한다). 탐색 예산 15회는 5~7차원 공간에서 무작위 탐색과 구분되지 않는다.
- coder에게: (1) `n_trials`를 30 이상으로 올리고, (2) `n_steps`를 최소 2,000(본훈련 1 에피소드 분량)으로 올리며, (3) `MedianPruner`를 쓰려면 objective 안에서 seed마다 `trial.report(partial_score, step=i)`와 `if trial.should_prune(): raise optuna.TrialPruned()`를 호출하라. 쓰지 않을 것이면 `pruner=optuna.pruners.NopPruner()`로 명시해 오해를 없애라. 비용이 문제라면 9개 모델 전부가 아니라 제안 기법과 대표 baseline 3종만 정직하게 튜닝하고 나머지는 원논문 값을 쓰는 편이 방어 가능하다.

---

**M3 — HPO는 확률적 정책으로, 평가는 결정적 정책으로 측정한다.**

- 심각도: MEDIUM
- 근거:
  - `src/hpo.py:344`, `:381` — `model.select_action(s_vec, deterministic=False)`
  - `src/evaluate.py:239` — `grant, _, _ = model.select_action(s_vec, deterministic=True)`
- 무엇이 잘못되었나: 하이퍼파라미터는 탐험이 켜진 행동 분포에서 선택되고, 리더보드는 탐험이 꺼진 분포에서 매겨진다. 엔트로피 계수처럼 탐험량을 직접 제어하는 파라미터는 두 분포에서 반대 방향으로 작용할 수 있다.
- coder에게: 어느 쪽이 벤치마크 규약인지 하나로 정하라. 학습 중 성능이 아니라 배치 후 성능을 보고하는 것이 표준이므로 HPO의 평가 롤아웃도 `deterministic=True`로 맞추는 편이 옳다. 다만 `train_steps_during_rollout > 0`인 학습 구간은 `deterministic=False`여야 하므로, 학습 롤아웃과 채점 롤아웃을 분리하는 것이 정확한 해법이다.

---

**M4 — 훈련 시드가 42 하나뿐이고, 요약 CSV에 분산 정보가 없다.**

- 심각도: MEDIUM
- 근거:
  - `simulation_plan.md:137/143/149/155` — 4개 그룹 전부 `--seed 42`
  - `run_all.py:281` — `--seed` 기본 42, 모델별로 다르게 주는 경로 없음
  - `src/evaluate.py:334`, `:342` — `.mean()`만 계산하고 `.std()` / 신뢰구간 / 시드별 개수를 남기지 않는다
- 무엇이 잘못되었나: 훈련 시드가 하나이므로 "이 모델이 저 모델보다 낫다"가 학습 분산 안의 잡음인지 구분할 수 없다. 평가 시드 5개는 환경 분산만 잡을 뿐 학습 분산은 잡지 못한다.
- 논문에 미치는 영향: IEEE TWC 급 심사에서 단일 시드 학습 결과에 오차 막대 없이 순위표를 제시하면 거의 확실히 지적받는다.
- coder에게: 최소 3개 훈련 시드(예: 42, 43, 44)로 돌릴 수 있는지 시간 예산을 idea/사용자와 협의하라. 2.42시간 × 3 = 7.3시간이므로 물리적으로 불가능하지는 않다. 불가능하다면 최소한 `df_summary`와 `df_leaderboard`에 `std`, `sem`, `n`을 열로 추가해 평가 시드 분산만이라도 보고하고, 원고에 "단일 학습 시드"임을 명시하라.

---

**M5 — 테스트가 여전히 프로덕션 트리에 씁니다. 수정 #3이 미완결이다.**

- 심각도: MEDIUM
- 근거:
  - `src/hot_swap_trainer.py:1908-1910` — `log_csv_path`가 `None`이면 `/home/imnyj/Workspace/paper4/coder/logs/training/{model}_progress.csv`로 하드코딩된다
  - `run_all.py:288-291` — `--checkpoint-dir`와 `--tensorboard-dir`는 추가되었으나 `--log-csv-path`는 없다. `run_all.py:355-359`의 `extra_dirs`에도 없다
  - `tests/` 전체에 `log_csv_path`를 넘기는 호출이 0건이다(grep 확인)
  - `logs/training/`이 git 미추적 상태로 새로 생겨 있다(생성 시각 08-31 00:13, 스모크 실행 시각과 일치)
  - `tests/test_hot_swap.py:437-448`도 `checkpoint_dir`/`tensorboard_dir`만 격리하고 `log_csv_path`는 넘기지 않는다
- 무엇이 잘못되었나: `pytest`를 한 번 돌릴 때마다 `logs/training/PPO_progress.csv`와 `logs/training/DummyPolicy_progress.csv`가 프로덕션 로그 디렉터리에 쓰인다. 본훈련 중 테스트를 돌리면 진행 로그가 오염된다.
- coder에게: `run_all.py`에 `--log-csv-dir`를 추가해 `extra_dirs`로 전달하고, `run_hot_swap_training`은 `log_csv_path`가 `None`일 때 `checkpoint_dir`의 형제 디렉터리를 쓰도록(즉 격리 인자 하나로 세 출력이 전부 따라가도록) 바꿔라. 그리고 `tests/conftest.py`에 프로덕션 `checkpoints/`, `logs/`, `results/` 아래 파일 목록을 세션 시작·종료 시점에 비교해 변화가 있으면 실패시키는 autouse fixture를 추가하라. 이런 종류의 누수를 사람이 매번 찾는 것은 지속 가능하지 않다.

---

**M6 — `run_full_benchmark`가 하나의 모델 인스턴스를 25개 셀 전부에 재사용한다.**

- 심각도: MEDIUM
- 근거: `src/evaluate.py:301` — `model = instantiate_model(...)`이 density/seed 이중 루프(`:303-304`) **바깥**에 있다
- 무엇이 잘못되었나: 리플레이 버퍼, epsilon 스케줄, 관측 정규화 통계 같은 내부 상태가 셀 사이를 넘어간다. 평가 중 학습은 하지 않지만 `select_action`이 내부 카운터를 진전시키는 구현이 있다면 (density=15, seed=42) 셀의 결과가 그 셀을 몇 번째로 실행했는지에 의존한다.
- coder에게: 셀마다 새 인스턴스를 만들고 체크포인트를 다시 로드하거나(C1 수정과 함께), 최소한 셀 진입 시 `model.reset()` 계약을 정의하라. 전자가 안전하다.

---

**M7 — 죽은 인자와 그것을 믿고 있는 테스트.**

- 심각도: MEDIUM
- 근거:
  - `src/evaluate.py:199-201` — `dt`, `rsu_pos` 인자가 함수 본문에서 한 번도 참조되지 않는다
  - `src/hpo.py:305-306` — `n_vehicles`, `rsu_pos` 동일
  - `tests/test_hpo.py:126` — `evaluate_model_in_env(..., n_vehicles=10, ...)`
  - `tests/test_hpo.py:152` — `evaluate_trial_multiseed(..., n_vehicles=8)`
- 무엇이 잘못되었나: 테스트가 차량 수를 통제한다고 믿고 인자를 넘기지만 아무 효과가 없다. 실제 차량 수는 `density`가 결정한다.
- coder에게: 사용하지 않는 인자는 삭제하라. 남겨야 한다면 `NotImplementedError`를 던지거나 최소한 `logger.warning`을 남겨라. 그리고 해당 테스트에서 인자를 제거하라.

---

### LOW

---

**L1 — HeuristicScheduler가 평가 시 `accel`을 받지 못한다.**

- 근거: `src/evaluate.py:227-236`이 만드는 `st_dict`에는 `vid`, `pos`, `speed`, `dist_to_rsu`, `current_time`만 있다. `src/heuristic_scheduler.py:96`은 `accel = float(state.get("accel", 0.0))`으로 항상 0을 읽고, 이 값이 `:120-128`의 `predict_stop_imminent`에 들어간다.
- 다만 `:101-106`에서 `tls_features`가 없으면 `extract_tls_features(libsumo, vid, ...)`로 직접 조회하므로 TLS 인지 자체는 살아 있다. `libsumo as sumo` import(`heuristic_scheduler.py:20-26`)가 동일 프로세스 싱글턴을 잡기 때문이다.
- coder에게: `st_dict`에 `accel`과 `tls_features`를 `env._get_vehicle_state_dict(vid)`에서 그대로 채워 넣어라. RL 모델은 이 정보를 상태 벡터 [4]로 받고 있으므로 형평성 문제이기도 하다.

---

**L2 — `evaluate.py`의 기본 `n_steps`가 100(10 시뮬레이션 초)이다.**

- 근거: `src/evaluate.py:198`, `:275`, `:389`. 반면 `warmup_steps=350`(`:217`)이고 `hpo.py:642-644` 주석은 "차량이 RSU 원반에 도달하는 데 35초가 걸린다"고 적고 있다.
- 무엇이 잘못되었나: warmup 이후 10초만 측정한다. 위 H2 실측에서 40 step으로도 933개 관측이 나왔으므로 완전히 비어 있지는 않으나, AoI 통계의 표본 창으로는 짧고 peak AoI가 과소 추정된다.
- coder에게: 논문 표용 실행에서는 `--n-steps`를 최소 2,000(200초)로 올려라. 250 run × 2,000 step의 시간 예산을 먼저 측정해 idea에게 보고하라.

---

**L3 — `low_speed_error` / `high_speed_error`의 경계가 하드코딩 2.0 m/s다.**

- 근거: `src/hot_swap_trainer.py:1571` — `if st["speed"] < 2.0:`
- coder에게: 모듈 상수로 올리고 원고에 그 값과 근거를 명시하라. 저속·고속 오차 분리는 논문의 주장 중 하나이므로 임계값이 임의 리터럴로 남아 있으면 안 된다.

---

**L4 — `evaluate.py`가 `random.seed`를 걸지 않는다.**

- 근거: `src/evaluate.py:206-207` — `torch.manual_seed(seed)`, `np.random.seed(seed)`만 있다. 환경의 업링크 추첨은 `random.random()`(`hot_swap_trainer.py:1632`)이다.
- 현재는 `_init_sumo:931`이 우연히 `random.seed(self.seed)`를 걸어주지만, 그 직후 `make_sumo_files()`의 소비량이 가변이라 H2의 원인이 된다.
- coder에게: H2 수정과 함께 처리하라.

---

**L5 — `evaluate.py:403`에 이모지가 들어 있다.**

- 근거: `print("🏆 IEEE TWC EVALUATION LEADERBOARD (Composite Ranking)")`
- 로그를 파일로 리디렉션하거나 비 UTF-8 터미널에서 실행하면 인코딩 오류가 날 수 있고, 프로젝트 문서 규약과도 어긋난다. 제거를 권한다.

---

## 오늘의 수정 #1~#4에 대한 감사 결과

**수정 #1 (w1..w4가 모델 hparams로 흘러들어가던 문제) — 절반만 완료.**
`run_all.py`는 정확하다. `ignored_cols`가 `ENV_ONLY_HPARAM_KEYS`를 합집합으로 포함하고(`:159-164`), `hparams_json` 파싱에도 동일 필터를 건다(`:213-216`). `reward_weights_json`을 병합하지 않는다는 주석(`:222-225`)도 코드와 일치한다. `hot_swap_trainer.py:83-98`의 상수 정의와 `split_env_hparams`(`:101-110`)도 올바르다. **그러나 `src/evaluate.py::load_optimal_hparams`에는 이 필터가 전혀 적용되지 않았다** — C3 참조. 실제 프로젝트 CSV로 실측한 결과 9개 모델 전부가 오염된다. 수정 #1은 미완결이다.

**수정 #2 (다중 행 CSV에서 최소 `best_value` 선택) — 정확하다.**
`run_all.py:194-201`의 분기를 세 경우로 나눠 검증했다. (a) 새 점수가 `None`이고 기존 점수가 있으면 `continue`로 건너뛴다 — 맞다. (b) 새 점수가 있고 기존보다 크거나 같으면 건너뛴다 — 최소값 유지, 맞다. (c) 기존 점수가 `None`이고 새 점수가 있으면 두 조건 모두 통과해 덮어쓴다 — 점수 있는 행이 점수 없는 행을 대체하므로 맞다. `best_score_by_model`은 점수가 있을 때만 갱신된다(`:250-251`) — 맞다. 행 순서에 무관하다는 것도 `test_30`(`tests/test_run_all.py:578-595`)이 양방향으로 확인한다. **새로 도입한 문제는 없다.**

**수정 #3 (통합 테스트가 프로덕션 `checkpoints/`에 쓰던 문제) — 부분 완료.**
`--checkpoint-dir` / `--tensorboard-dir`(`run_all.py:288-291`, `:355-359`)와 이를 사용하는 테스트들(`test_run_all.py:211-212, 229-230, 245-246, 264-265, 522-523, 648-649`, `test_hot_swap.py:446-447`)은 올바르다. `test_34`(`test_run_all.py:625-662`)가 프로덕션 `checkpoints/` 스냅샷을 전후 비교하는 것은 특히 좋은 설계다. **그러나 `log_csv_path`는 여전히 하드코딩 경로로 새어 나간다** — M5 참조. `logs/training/`이 미추적 상태로 실제로 생성되어 있는 것이 증거다.

**수정 #4 (`--tune-reward-weights` opt-in, `--n-steps` 35 → 350) — 논리적으로 정확하나 CSV가 뒤따르지 않았다.**
`hpo.py:509-514`의 분기는 옳고, `tune_reward_weights=False`일 때 `DEFAULT_REWARD_WEIGHTS`를 `user_attr`로 남겨 `save_study_results`(`:552-565`)가 `w1..w4` 열을 채울 수 있게 한 것도 일관적이다. `save_study_results`가 `best_params`에 보상 가중치를 병합하지 않는 것(`:566-569`)도 맞다. **다만 커밋된 `results/hpo/optuna_best_params.csv`는 수정 전 코드의 산출물이며 `hparams_json` 안에 `w1_raw`~`w4_raw`가 그대로 들어 있다.** 코드는 고쳤지만 데이터는 고치지 않았다 — M1 참조. 또한 `save_study_results`가 진짜 최소 trial을 내보내는지 검증하는 테스트가 스위트에 없다(`test_hpo.py:179-200`은 `len(record["best_params"]) > 0`만 본다). 코드 자체는 `study.best_trial` / `study.best_value`를 쓰므로 Optuna에 위임되어 정확하지만, 회귀 방어선이 없다.

---

## 무의미하거나 오도하는 테스트 목록

아래 목록은 (a) 검증한다고 주장하는 로직을 테스트 안에서 다시 구현한 것, (b) `is not None`만 보는 것, (c) 실패할 수 없는 단언, (d) 검증 대상을 모킹이나 그림자 구현으로 치환한 것을 모은 것이다. 판정 근거는 전부 직접 읽은 줄이다.

### (a) 프로덕션 로직을 테스트 안에서 재구현

| # | 위치 | 내용 |
|---|---|---|
| V1 | `tests/test_run_all.py:167-187` `test_08_cli_argument_parsing` | 테스트 안에서 `argparse.ArgumentParser`를 새로 만들고(`:174-180`) 그것에 대해 단언한다. `run_all.main`의 실제 파서를 한 번도 건드리지 않으므로 `run_all.py`를 삭제해도 통과한다. `sys.argv` 백업·복원(`:171-187`)까지 하지만 `sys.argv`를 읽는 코드가 없다 |
| V2 | `tests/test_run_all.py:449-478` `test_21_models_cli_all_keyword_expansion` | 자체 파서(`:456-462`)에 더해 `ALL` 확장 루프 전체(`:464-474`)를 `run_all.py:305-318`에서 그대로 베껴 재구현하고 그 사본에 단언한다. 프로덕션 확장 로직이 바뀌어도 이 테스트는 계속 통과한다 |
| V3 | `tests/test_run_all.py:480-493` `test_22_models_cli_comma_separated_parsing` | 동일. 자체 파서(`:484-485`) + 쉼표 분해 로직 재구현(`:487-492`) |

`test_24`(`:506-513`)와 `test_25`(`:515-525`)는 실제 `main(argv)`를 호출하므로 유효하다. `main`이 `argv`를 인자로 받도록 설계되어 있으므로(`run_all.py:275`) V1~V3도 같은 방식으로 고칠 수 있다.

### (b) `is not None` 및 실패할 수 없는 단언

| # | 위치 | 내용 |
|---|---|---|
| V4 | `tests/test_hpo.py:171-177` `test_06` | `study.best_value is not None`(`:172`), `study.best_trial.number in [0,1,2,3]`(`:174`)은 `n_trials=4`이므로 항상 참이다. `len(best_params) > 0`(`:177`)은 탐색 공간이 비지 않는 한 항상 참이다. 최적화가 실제로 일어났는지는 검사하지 않는다 |
| V5 | `tests/test_hpo.py:226-227` `test_09` | `study.best_trial is not None` |
| V6 | `tests/test_hpo.py:155-157` `test_05` | `assert score > 0.0`. `evaluate_trial_multiseed`는 모든 seed가 예외로 죽으면 100.0을 반환하므로(`hpo.py:439-443`) 완전 실패 경로도 통과한다. 이 테스트가 잡아야 할 유일한 실패 모드를 잡지 못한다 |
| V7 | `tests/test_hpo.py:179-200` `test_07` | `save_study_results`가 **진짜 최소값 trial**을 내보내는지 전혀 검사하지 않는다. `record["model_name"]`과 `len(best_params) > 0`만 본다. 상위 에이전트가 명시적으로 요청한 검증 항목인데 스위트에 존재하지 않는다 |
| V8 | `tests/test_evaluation.py:211` `test_09` | `df_leaderboard.iloc[0]["rank"] == 1`. `evaluate.py:354`가 `insert(0, "rank", range(1, ...))`로 넣으므로 구조적으로 항상 참이다. 정렬 정확성은 검사하지 않는다 |
| V9 | `tests/test_evaluation.py:96` `test_04` | `assert built is not None` |
| V10 | `tests/test_hot_swap.py:418-419, 429` | `trainer.act_model is not None`, `trainer.rest_model is not None`, `loss_dict is not None` |
| V11 | `tests/test_dummy_verification.py:125` `test_d3` | `loss_dict is not None` |
| V12 | `tests/test_evaluation.py:173` `test_08_density_scaling_contention_effect` | `high_density_run["tx_attempts"] >= low_density_run["tx_attempts"]`. 등호를 허용하므로 밀도가 전송 시도에 아무 영향이 없어도 통과한다. docstring은 "packet loss rate가 증가한다"고 주장하지만 packet loss는 단언하지 않는다 |
| V13 | `tests/test_dummy_verification.py:180-205` `test_d6` | 15초 벽시계 예산만 검사한다. 정확성 검증이 아니며 부하가 걸린 머신에서 무작위로 실패한다 |
| V14 | `tests/test_hot_swap.py:432-456` `test_run_hot_swap_training_end_to_end` | `total_steps == 80`, `elapsed > 0`, `swap_count >= 1` 등 배관 카운터만 본다. 80 step 동안 학습이 실제로 일어났는지(손실 감소, 파라미터 변화)는 검사하지 않는다 |

### (c) 공백 실행에서도 전부 통과하는 지표 단언

| # | 위치 | 내용 |
|---|---|---|
| V15 | `tests/test_evaluation.py:142-150` `test_06_single_evaluation_run_metrics` | `peak_aoi >= mean_aoi`(0 >= 0 참), `0 <= packet_loss <= 1`(0 참), `mean_error >= 0`(0 참), `max_error >= mean_error`(0 >= 0 참), `10.0 <= avg_tx_power_dbm <= 23.0`(공백 시 p_min=10.0 fallback으로 참), `0 < jains <= 1`(공백 시 1.0 반환으로 참). **관측이 0인 실행에서 여섯 단언이 모두 통과한다.** `n_observations`나 `tx_attempts`를 단언하지 않는다 |
| V16 | `tests/test_dummy_verification.py:174-178` `test_d5` | V15와 동일한 사각지대. `n_steps=10`으로 실행하면서 관측 유무를 검사하지 않는다 |
| V17 | `tests/test_dummy_verification.py:77-80` `test_d1` | `metrics["mean_aoi"] >= 0.0` 등 동일 패턴. 다만 `:61`의 상태 벡터 범위 검사와 `:72`의 `r <= 0.0`은 실질적이다 |

### (d) 그림자 구현을 검증 대상으로 치환

`tests/contract_adapters.py`의 fallback이 실제로 실행되는 경로다. 실측으로 `is` 비교와 반환값 차이를 확인했다.

| # | 위치 | 내용 |
|---|---|---|
| V18 | `tests/contract_adapters.py:99-105` | 위임 분기가 `pass`다. `import src.heuristic_scheduler as hs` 후 `hasattr` 검사까지 하고 아무것도 하지 않는다. 아래 V19~V21의 근본 원인 |
| V19 | `tests/test_tier1_features.py:64-79` `test_03_heuristic_scheduler_grants` | `contract_adapters.HeuristicScheduler`의 하드코딩 반환값 `(0.5, ch, 23.0)`(`:116`)과 `(interval, ch, 10.0)`(`:123`)을 단언한다. `src/heuristic_scheduler.py`는 실행되지 않는다. 생성자 시그니처마저 다르다(`num_channels` vs `num_subchannels`) |
| V20 | `tests/test_tier3_integration.py:32-58` `test_01_dynamics_and_heuristic_closed_loop` | 동일 그림자에 대해 4개 시나리오의 delta 범위를 단언한다(`:39-42`). "TLS dynamics → prediction → heuristic grant adaptation의 매끄러운 파이프라인"을 검증한다고 주장하지만 heuristic 부분이 가짜다 |
| V21 | `tests/test_dummy_verification.py:99-104` `test_d2` | 여기서는 `src.heuristic_scheduler.HeuristicScheduler`를 직접 import해서 쓴다(`test_dummy_verification.py:40`). 즉 같은 클래스 이름이 파일마다 다른 구현을 가리킨다. 유지보수 함정이다 |
| V22 | `tests/test_tier1_features.py:101-117` `test_05_hybrid_action_decoder_bounds` | `contract_adapters.ActionDecoder`(`:237-289`)를 검증한다. 실측으로 `[0.0, 2.0, 0.0]`에 대해 어댑터는 `22.55`, `src.rl_interface.ActionDecoder`는 `2.121`을 반환한다. 실제 디코더는 기하 사상(`rl_interface.py:524-532`), 어댑터는 선형 사상이라 다른 함수다. `src` 디코더의 `delta_max=0.0` sentinel 로직(`rl_interface.py:542-550`)은 이 테스트가 전혀 건드리지 않는다 |
| V23 | `tests/test_tier1_features.py:119-139` `test_06_retrospective_replay_buffer` | `contract_adapters.RetrospectiveReplayBuffer`(`:292-351`)를 검증한다. `src.rl_interface.RetrospectiveReplayBuffer`와 다른 객체임을 실측 확인했다 |
| V24 | `tests/test_tier2_boundaries.py:99-118` `test_05_replay_buffer_edge_cases` | 동일 그림자. `"Cannot sample from an empty buffer"` 메시지도 어댑터(`:325`)의 것이다 |
| V25 | `tests/test_tier1_features.py:158-164` `test_08_optuna_study_execution` | `contract_adapters.run_hpo_study`(`:444-470`)를 실행한다. 환경도 학습도 없고 목적함수는 `delta*0.1 + (p-10)*0.01`(`:466`)이다. `assert "lr" in study.best_params`(`:163`)는 어댑터의 fallback 탐색 공간(`:437`)을 확인할 뿐이다 |
| V26 | `tests/test_tier3_integration.py:134-163` `test_04_optuna_to_evaluation_pipeline` | "Optuna가 파라미터를 탐색 → 최적 모델 학습 → 6개 지표로 평가"를 검증한다고 주장하는데, HPO는 가짜(`:137`), 학습은 없고, 평가는 손으로 만든 딕셔너리 10개(`:149-156`)에 그림자 `calculate_metrics`를 적용한 것이다. 세 단계 전부 가짜다 |
| V27 | `tests/test_tier1_features.py:185-198` `test_10_benchmark_metrics_calculation` | `contract_adapters.calculate_metrics`(`:508-552`)를 검증한다. 이 구현은 `peak_aoi`를 최대값이 아니라 **평균**으로 계산하고(`:525`), 에너지에 프로덕션이 명시적으로 폐기한 `0.001`초 상수를 쓴다(`:531`). 즉 프로덕션이 고친 버그를 테스트 쪽 구현이 그대로 갖고 있고, 테스트는 그 버그를 단언한다 |
| V28 | `tests/test_e2e_pipeline.py:32-99` `test_full_e2e_pipeline_lifecycle` | "전체 체인 검증"을 표방하지만 `eval_records`를 루프 안에서 손으로 만들고(`:75-82`, `error`는 항상 0.2, `tx_fails`는 항상 0), 그림자 `calculate_metrics`로 채점한다(`:94`). `assert metrics["packet_loss_rate"] == 0.0`(`:96`)은 입력에 실패를 넣지 않았으니 항상 참이다. `AoiV2IEnv`도 `evaluate.py`도 실행되지 않는다 |

### (e) 낡은 이름을 단언해 사실상 죽은 테스트

| # | 위치 | 내용 |
|---|---|---|
| V29 | `tests/test_hpo.py:31-70` `test_01_search_space_definitions` | `CANONICAL_MODEL_NAMES`(현재 PPO, SAC, TD3, RES-MAPDDPG, MA2HDQN, I-HAMAPPO, SPAM-D3QN, CARLTON, MADDPG-MT)로 파라미터화되는데, 내부 분기는 전부 폐기된 이름을 검사한다: `HybridPPO/MAPPO/HyARPPO`(`:42`), `HybridSAC`(`:48`), `HybridTD3`(`:52`), `MPDQN`(`:57`), `PureAoI`(`:62`), `DuelingQAoI`(`:65`), `SACAoI`(`:68`). **어느 분기도 매치되지 않는다.** 실제로 남는 단언은 `isinstance(params, dict)`(`:38`)와 `len(params) > 0`(`:39`)뿐이다. 9개 파라미터화 테스트가 사실상 두 줄짜리 타입 검사다 |
| V30 | `tests/test_evaluation.py:62-78` `test_02_load_optimal_hparams_from_csv` | CSV에 `HybridPPO`와 `PureAoI`를 넣고(`:67-68`) 그 이름 그대로 로드되는지 단언한다(`:73-74`). 두 이름은 2026-08-28에 폐기되었고 `evaluate.normalize_model_name`은 매치 실패 시 입력을 그대로 돌려주므로(`evaluate.py:90`) 통과한다. 이 테스트는 로더가 **어떤 쓰레기 이름이든 받아들인다**는 사실을 굳히고 있다. 그리고 C3(w1..w4 유출)을 잡을 위치에 있었으면서 잡지 않았다 |

`tests/test_hpo.py:237-286`의 `TestHparamsActuallyReachModels` 세 테스트, `tests/test_rl_interface.py` 전체, `tests/test_dynamics_predictor.py`, `tests/test_run_all.py:528-662`의 `TestRewardWeightSeparation`, `tests/test_tier2_boundaries.py:44-97`의 통신 경계 테스트는 `src.*`를 직접 검증하는 유효한 테스트다. 특히 `test_hpo.py:269-286`의 `test_sampled_values_take_effect_at_runtime`은 "이름이 맞는 것만으로는 부족하고 값이 실제로 도달하는지 본다"는 올바른 발상이다. 이 패턴을 위 목록의 재작성 기준으로 삼기를 권한다.

---

## 질문

이하 항목은 요구사항이 모호하거나 설계 결정이 필요한 지점이다. critic이 임의로 판단하지 않고 남긴다.

1. **C1 관련.** 평가에 로드할 체크포인트는 `{model}_best.pt`인가 `{model}_ep100.pt`인가? `_best.pt`는 에피소드 평균 보상 기준으로 선택되는데(`hot_swap_trainer.py:2102` 부근), 보상은 w1..w4로 가중된 값이므로 "best reward"가 "best composite metric"과 일치하지 않는다. 논문 표는 최종 정책(`ep100`)을 보고하는 것이 통상적이다. 어느 쪽을 규약으로 삼을지 결정이 필요하다.

2. **H3 관련.** HPO를 재실행할 시간 예산이 있는가? 시드 분리를 제대로 하려면 HPO 시드도 평가 시드와 분리해야 하고, 그러려면 CSV를 다시 만들어야 한다. 재실행이 불가능하다면 (a) 현재 CSV를 버리고 문헌 기본값으로 훈련하거나 (b) 시드 겹침을 논문에 한계로 명시하는 두 선택지가 있는데, 이는 사용자 판단 사항이다.

3. **H4 관련.** 논문이 말하는 "outage"의 정의가 무엇인가? SINR이 임계값 미만인 사건의 비율인가, 재시도를 소진해 갱신이 전달되지 못한 비율인가, 아니면 차량이 RSU 커버리지 밖에 있는 시간 비율인가? `Conversation.md`와 `simulation_plan.md` 어디에도 명시적 정의를 찾지 못했다. 세 정의가 모두 문헌에 존재하며 값이 크게 다르므로 확정이 필요하다.

4. **M4 관련.** 훈련 시드를 3개로 늘릴 수 있는가? 계획서상 2.42시간이므로 3회 반복은 약 7.3시간이다. 단일 시드로 갈 경우 원고에 그 사실과 이유를 명시해야 하는데, 이를 한계로 적을지 아니면 시간을 더 쓸지 결정이 필요하다.

5. **훈련 밀도.** `run_hot_swap_training`은 `density=25.0` 고정으로 학습하고(`hot_swap_trainer.py:1864`, `run_all.py`가 이 인자를 넘기지 않음) 평가는 15~55에서 한다. 이것이 의도된 일반화 실험인가, 아니면 훈련도 밀도를 섞어야 하는가? 전자라면 논문에 "단일 밀도 학습, 다중 밀도 평가"임을 명시해야 하고, 후자라면 `run_all.py`에 `--density` 인자가 필요하다.

6. **H7 관련.** `tests/contract_adapters.py`의 fallback 구현을 삭제할 권한이 coder에게 있는가? 삭제하면 위 V19~V28의 테스트가 즉시 실패하고 재작성이 필요하다. 재작성 분량이 적지 않으므로(약 12개 테스트) 본훈련 기동과의 우선순위 조정이 필요하다. critic 의견으로는 C1·C2·C3·H1을 먼저 고쳐 훈련을 기동하고, 훈련이 도는 2.4시간 동안 테스트를 재작성하는 것이 시간을 가장 아끼는 순서다.

7. **`ENV_ONLY_HPARAM_KEYS`의 범위.** 현재 `w1..w4`와 `w1_raw..w4_raw`만 포함한다(`hot_swap_trainer.py:98`). `density`, `warmup_steps`, `max_steps`, `rsu_range`도 환경 인자인데 CSV에 이런 열이 생기면 동일한 방식으로 모델 생성자에 흘러든다. 방어적으로 화이트리스트(생성자 시그니처에 있는 키만 통과) 방식으로 뒤집는 것이 나은지 확인이 필요하다.
