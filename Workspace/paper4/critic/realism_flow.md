# 파이프라인 종단 검토: HPO → 훈련 → 평가 → 논문 표

작성 2026-09-02 / critic / 대상 `coder/run_all.py`, `coder/src/hpo.py`, `coder/src/evaluate.py`의 경계와 `coder/etc/`의 무인 운용 인프라

---

## 판정 요약

**본훈련 전 수정 필요.**

개별 모듈은 대체로 건강하고 사슬 자체는 실제로 이어진다. 짧은 종단간 실행으로 훈련에서 체크포인트를 만들어 평가까지 통과시켰고, 모델명 표기가 레지스트리와 파일명과 CSV 사이에서 아홉 종 전부 정확히 해소되는 것도 확인했다. 그러나 사슬의 입구에 있는 HPO 산출물이 현재 코드와 정합하지 않고, 출구에 있는 에피소드 기록이 비정상 종료 시 통째로 사라지며, 그 사라짐을 정기 보고가 감지하지 못한다. 세 가지 모두 실측으로 재현했고 수정 범위는 크지 않다.

수정이 필요한 항목은 네 가지다. 첫째, `results/hpo/optuna_best_params.csv`를 다시 만들어야 한다. 지금 파일은 모델마다 다른 보상 가중치 아래 튜닝된 것이고 현재 코드는 그 파일을 재생산할 수조차 없다. 둘째, 에피소드 진행 CSV를 에피소드마다 즉시 기록해야 한다. 지금은 함수가 정상 반환할 때만 기록되어 크래시 한 번에 그 모델의 곡선이 전부 날아간다. 셋째, 재개 시 그래디언트 갱신 계수가 초기화되지 않아 재개 직후 에피소드의 갱신 수가 크래시 이전 누적분만큼 부풀려진다. 넷째, `report_progress.py`가 진행 중인 모델을 전혀 보지 못한다.

**무인 실행 적합성: 조건부 적합.** 감시자, 재시작, 백업, SUMO 격리, GPU 감지는 잘 설계되어 있고 SIGKILL 복구가 실제로 동작하는 것을 확인했다. 그러나 현재 보고 체계로는 "정상 진행 중"과 "조용히 망가짐"을 구분할 수 없다. 위 둘째와 넷째를 고치기 전에는 무인 20시간을 돌리지 말 것을 권한다. 시간 예산으로도 20시간 창에는 보상 집계 한 팔 × 훈련 시드 하나와 그 평가까지만 들어간다.

---

## 1. 사슬의 연속성

### 1.1 HPO 산출물이 현재 코드와 불일치한다 (수정 필요)

`results/hpo/optuna_best_params.csv`는 `w1_raw`부터 `w4_raw`까지의 열을 담고 있고, 정규화된 `w1`~`w4`가 모델마다 다르다. PPO는 0.079/0.344/0.364/0.213이고 TD3는 0.724/0.057/0.096/0.123이다. 이 열들은 `sample_reward_weights`가 `trial.suggest_float`로 등록할 때만 생기므로, 이 파일은 `tune_reward_weights=True`로 생성됐다는 뜻이다. `optuna_trials_PPO.csv`의 헤더에 `params_w1_raw`가 있는 것으로 재확인했다.

문제는 현재 `src/hpo.py:667`의 기본값이 False이고 그 docstring이 "Turn it on only for a reward-shaping ablation, never for the numbers that go into the cross-model comparison table"이라고 스스로 못박고 있다는 점이다. 즉 디스크의 CSV는 지금 코드가 만들지 않을 물건이며, 아홉 모델이 각각 다른 목적함수 아래에서 하이퍼파라미터를 골랐다. 훈련은 `hot_swap_trainer.DEFAULT_REWARD_WEIGHTS`의 0.5/0.2/0.2/0.1로 고정되어 돌아가므로, 주입될 학습률과 감가율은 훈련에 쓰이지 않는 보상 아래에서 최적이던 값이다. TD3가 오차항 가중치 0.72 아래에서 고른 학습률을 0.5 아래에서 쓰는 셈인데, 이건 튜닝을 하지 않은 것보다 나은지조차 말할 수 없다.

더 결정적인 것은 재생산 불가능성이다. `AoiV2IEnv.__init__`에 `allow_custom_reward_weights` 가드가 들어갔고(`hot_swap_trainer.py:1252` 이하), 기본값 False에서 `DEFAULT_REWARD_WEIGHTS`와 다른 가중치로 환경을 만들면 ValueError가 난다. `hpo.evaluate_model_in_env`는 이 인자를 넘기지 않으므로, 지금 `--tune-reward-weights`로 HPO를 돌리면 즉시 예외로 죽는다. 다시 말해 현재 CSV는 코드가 만들 수 없는 상태의 유물이다. 고정 가중치로 HPO를 다시 돌려야 하며, 아홉 모델 × 15 트라이얼 × 3 시드 × 350 스텝이므로 비용은 크지 않다.

부수적으로, HPO는 트라이얼당 350 스텝 동안 환경 스텝마다 2회씩 약 700회의 갱신만 수행하고 밀도는 25 한 점에서만 평가한다. 본훈련은 20만 스텝에 밀도 5부터 50까지 열 점이다. 700회 갱신에서 좋았던 학습률이 20만 스텝에서도 좋으리라는 보장은 없고, 밀도 25에서 좋았던 설정이 밀도 5에서도 좋으리라는 보장도 없다. 이건 계산 예산상 흔히 받아들이는 타협이므로 수정 대상은 아니지만, 논문에는 한계로 적어야 한다.

### 1.2 모델명 표기는 모든 경계에서 정확히 해소된다 (문제 없음)

레지스트리의 `I-HAMAPPO`, 클래스명 `IHAMAPPO`, 체크포인트 파일 `IHAMAPPO_best.pt` 사이의 왕복을 아홉 종 전부에 대해 실제로 확인했다. `evaluate.checkpoint_stem`이 레지스트리를 통해 클래스명을 얻고, `find_checkpoint`가 디스크의 파일명을 다시 정규화해 대조하는 구조라 양방향 모두 성립한다.

```
PPO         stem=PPO        best=PPO_best.pt         last=PPO_ep100.pt
RES-MAPDDPG stem=RESMAPDDPG best=RESMAPDDPG_best.pt  last=RESMAPDDPG_ep100.pt
I-HAMAPPO   stem=IHAMAPPO   best=IHAMAPPO_best.pt    last=IHAMAPPO_ep100.pt
SPAM-D3QN   stem=SPAMD3QN   best=SPAMD3QN_best.pt    last=SPAMD3QN_ep100.pt
MADDPG-MT   stem=MADDPGMT   best=MADDPGMT_best.pt    last=MADDPGMT_ep100.pt
```

`run_all.normalize_model_name`, `evaluate.normalize_model_name`, `hpo.normalize_model_name` 세 함수가 모두 구두점 제거 후 소문자화라는 같은 규칙을 쓰고 레지스트리에서 대조표를 만들므로, 새 baseline이 추가되어도 세 곳이 함께 따라간다. 여기는 손댈 것이 없다.

### 1.3 종단간 실행은 통과한다

PPO를 2 에피소드 × 400 스텝으로 훈련해 `PPO_best.pt`와 `PPO_ep002.pt`를 만들고, 체크포인트 안에 `error_mode`, `best_reward`, `training_steps`가 들어 있는 것을 확인한 뒤, 같은 체크포인트를 `src.evaluate`로 넘겨 `eval_raw_runs.csv` / `eval_summary_by_density.csv` / `eval_leaderboard.csv` 세 개가 생성되는 것까지 확인했다. 평가 로그에 `PPO: loaded act_state_dict from PPO_best.pt (training_steps=86)`가 찍혔고 composite가 `coverage_outage_rate` 기준으로 계산됐다. HPO CSV의 하이퍼파라미터가 훈련에 주입되는 것도 로그로 확인했다(`Applying HPO hyperparameters for PPO: {'learning_rate': 0.000471..., 'n_epochs': 10}`). 형식과 단위는 경계에서 맞는다.

### 1.4 훈련에서 평가로 넘어가는 무인 경로가 없다

`coder/etc/`에는 훈련 관련 스크립트 넷만 있고 평가 스크립트가 없다. `evaluate.DEFAULT_CHECKPOINT_DIR`은 `coder/checkpoints`를 가리키는데 `run_main_training.sh`는 `runs/<arm>_seed<N>/ck`에만 쓴다. 훈련이 끝난 뒤 기본값으로 평가를 돌리면 아홉 모델 전부 `FileNotFoundError`로 죽는다. 요란하게 죽으니 조용한 실패보다는 낫지만, 무인 운용이라면 20시간 뒤에 사람이 와서 발견하게 된다. `--checkpoint-dir`를 지정해도 출력은 `results/eval/`로 가고 어느 팔에서 나왔는지 표시가 없어, 두 번째 팔의 평가가 첫 번째를 덮어쓴다.

---

## 2. Ablation 두 팔의 분리

### 2.1 코드에는 분리 장치가 없다

두 팔이 섞이는 것을 막는 장치가 코드 어디에도 없다는 점을 먼저 짚어야 한다. 체크포인트 파일명은 `f"{model_name_str}_ep{ep+1:03d}.pt"`이고(`hot_swap_trainer.py:3169`) 팔 이름이 들어가지 않는다. 진행 CSV 파일명은 `f"{model_name_str}_progress.csv"`이며(`:2795`) 역시 팔 이름이 없고, **CSV의 열에도 `error_mode`가 없다**. 실측한 26개 열 어디에도 없다. TensorBoard 디렉터리는 `{model}_seed{seed}_{timestamp}`로 시드는 있지만 팔은 없다. 평가 출력 세 파일에도 `error_mode` 열이 없다.

가장 중요한 것은 `load_checkpoint`의 정합성 검사다. `hot_swap_trainer.py:1098`부터의 `strict_hparams` 블록은 `hparams`, `state_dim`, `num_channels`, `reward_weights` 네 가지를 대조하는데 **`error_mode`는 대조하지 않는다**. 체크포인트는 `:1075`에서 `error_mode`를 성실히 저장하면서 읽을 때 쓰지 않는다. 저장 코드의 주석이 "The two ablation arms are not comparable, so a checkpoint that does not say which arm it belongs to is not usable evidence"라고 적어놓은 바로 그 값이다.

### 2.2 실측한 사고 재현

같은 디렉터리에 accumulate 팔로 2 에피소드를 훈련한 뒤, mean 팔을 기본 옵션(resume이 기본 True)으로 실행했다.

```
[INFO] Reward error mode: mean | density schedule: [25.0]
[INFO] Finished PPO | {'total_steps': 800, 'elapsed_seconds': 0.0062,
  'mean_reward_per_second': nan, 'grad_updates_by_density': {25.0: 0},
  'start_episode': 2, 'resumed_from_checkpoint': '.../PPO_ep002.pt',
  'error_mode': 'mean'}
[INFO] All 1 model(s) trained successfully.
```

6밀리초 만에 종료 코드 0으로 "성공"했다. 디스크에 남은 두 체크포인트는 여전히 `error_mode=accumulate`이고, 진행 CSV는 첫 팔의 두 행 그대로다. 20시간 무인 실행이라면 두 번째 팔 아홉 모델이 몇 초 만에 완주하고 첫 팔의 결과를 자기 결과로 보고한다. 요약 dict의 `error_mode: 'mean'`만 진실을 말하는데 그 dict는 로그 한 줄로 흘러갈 뿐 어디에도 저장되지 않는다.

### 2.3 운영 스크립트가 실질적으로 막고 있다

`run_main_training.sh`가 `RUN_ROOT="${CODER_DIR}/runs/${ARM}_seed${SEED}"`로 잡고 `ck`, `tb`, `lg`, `sumo`를 그 아래에 두므로, 정상 경로에서는 두 팔이 물리적으로 만나지 않는다. 이건 잘 만들어진 부분이고, 2.2의 사고는 정상 경로에서는 일어나지 않는다. 다만 방어가 디렉터리 규약 하나에만 걸려 있다는 점은 남는다. `run_all.py`를 직접 부르는 방식은 그 파일의 docstring이 안내하는 실행법이고, 그때 기본값은 여전히 공유 `checkpoints/`와 `logs/training/`이다. 감사나 재현 목적으로 누군가 손으로 한 번 돌리면 2.2가 그대로 재현되며, 그 사실이 산출물 어디에도 남지 않는다. 체크포인트에 이미 저장하고 있는 `error_mode`를 `load_checkpoint`의 대조 목록에 한 줄 추가하는 것만으로 이 경로가 닫힌다.

### 2.4 척도 비교를 막는 장치는 없다

두 팔의 보상은 척도가 달라 직접 비교하면 안 되는데, 그것을 막는 장치는 주석뿐이다. 산출물에 팔 표시가 없으므로 나중에 CSV만 보고는 구분이 불가능하고, 정기 보고서는 실행 이름(`accumulate_seed42`)으로 구분은 되지만 두 팔의 보상을 같은 표에 나란히 찍는다. 최소한 표 각주로 "팔 간 보상 수치는 비교 불가"를 명시해야 한다.

---

## 3. 논문 표에 필요한 것

### 3.1 나오는 것

여섯 지표와 밀도 스윕은 나온다. `eval_summary_by_density.csv`가 (모델 × 밀도) 격자로 `mean_aoi`, `peak_aoi`, `coverage_outage_rate`, `packet_loss_rate`, `mean_error`와 `max_error`와 저속·고속 분해, `avg_tx_power_dbm`, `total_energy_joules`, Jain 공정성 두 종을 준다. 평가 격자가 훈련과 같은 열 개 밀도로 바뀌었으므로 표의 모든 칸이 훈련 구간 안에 있고, 외삽 셀이 사라졌다. 휴리스틱 포함 열 종은 `CANONICAL_EVAL_MODELS = ["HeuristicScheduler"] + list(ALL_BASELINES)`로 레지스트리에서 파생되므로 목록이 어긋날 여지가 없다. 체크포인트 출처가 `checkpoint_file`, `checkpoint_episode`, `checkpoint_training_steps`, `checkpoint_weights` 네 열로 원시 CSV의 모든 행에 붙는다. 이건 심사에서 요구받으면 바로 내놓을 수 있는 수준의 추적성이다.

### 3.2 표준편차 열이 없다

`_aggregate`(`evaluate.py:648` 이하)는 평균과 합계와 최대만 만들고 표준편차를 만들지 않는다. 요약과 리더보드 어디에도 std 열이 없다. 다만 `eval_raw_runs.csv`가 (모델, 밀도, 시드) 조합을 한 행씩 그대로 남기므로 계산은 가능하다. 열 개 밀도 × 다섯 시드 × 열 종이면 500행이다. visualizer가 원시 CSV에서 직접 평균과 표준편차를 계산해야 한다는 사실을 명시해 인계할 것. 요약 CSV를 그대로 표로 옮기면 분산 없는 표가 나온다.

### 3.3 수렴 곡선의 원천이 취약하다

수렴 곡선을 그릴 CSV 원천은 `lg/*_progress.csv` 하나뿐인데, 이 파일은 `run_hot_swap_training`이 **정상 반환할 때만** 기록된다. 기록 지점이 `finally` 블록 **바깥**의 함수 본문 끝(`:3216` 이하)이라, 예외가 나면 `finally`를 통과한 뒤 CSV 쓰기에 도달하지 못하고 전파된다. SIGKILL이면 말할 것도 없다. 이것이 아래 5절의 실측 손실로 이어진다. TensorBoard 이벤트는 주기적으로 flush되어 살아남지만 재시작마다 새 디렉터리가 생기므로 곡선이 여러 디렉터리에 쪼개진다. `global_step`이 일관되므로 병합은 가능하다.

### 3.4 집계 방식에서 논문에 적어야 할 것

리더보드는 모델당 동일한 50개 셀(열 밀도 × 다섯 시드)의 단순평균이므로 셀 수 불균형에 의한 가중 왜곡은 없고, `n_runs` 열이 있어 검증도 된다. 비율 지표인 `coverage_outage_rate`와 `packet_loss_rate`는 셀 평균, 곧 비율의 평균이지만 분자와 분모(`outage_vehicle_steps`/`total_vehicle_steps`, `tx_attempts`/`tx_fails`)를 합계로 함께 남겨서 독자가 pooled 비율을 재계산할 수 있다. 이건 잘 처리됐다.

남는 것은 둘이다. `peak_aoi`를 평균하면 "최댓값들의 평균"이지 최댓값이 아니고, `max_error`도 마찬가지다. 표에서 어느 쪽 정의인지 각주로 밝혀야 한다. 그리고 `avg_tx_power_dbm`을 dBm이라는 로그 영역에서 평균한다. 평균 전력을 주장하려면 선형 와트로 환산해 평균한 뒤 다시 dBm으로 돌려야 맞고, 지금 값은 로그 평균이다. TWC 심사에서 지적당할 수 있는 지점이므로 정의를 바꾸거나 각주로 명시할 것.

---

## 4. 통계적 타당성

평가 쪽 근거 데이터는 충분히 남는다. 모든 모델이 동일한 (밀도, 시드) 격자에서 평가되고 시드별 원시값이 `eval_raw_runs.csv`에 그대로 저장되므로, 모델 간 차이에 대해 n=50의 대응표본 검정을 할 수 있다. 평균만 남기는 구조가 아니라는 점은 명확히 확인했다. 평가 시드가 5001~5005, 훈련 시드가 42부터 141, HPO 시드가 1001~1003으로 완전히 분리된 것도 확인했으며, 이건 이 파이프라인이 실제로 갖고 있던 누수를 막은 조치다.

진짜 약점은 훈련 시드가 하나라는 점이다. 모델당 학습된 정책이 한 개뿐이므로 다섯 개의 평가 시드는 평가 트래픽 실현의 분산만 재고 훈련 자체의 분산은 재지 않는다. "모델 A가 모델 B보다 낫다"는 주장이 각 모델의 단 한 번의 훈련 실행에 의존하게 되는데, 강화학습 비교 논문에서 이건 리뷰어가 거의 반드시 짚는 지점이고 통상 훈련 시드 3~5개를 요구한다. 다행히 인프라는 이미 지원한다. `run_main_training.sh <arm> <seed>`가 `runs/<arm>_seed<N>`으로 격리하므로 42, 43, 44를 각각 돌리면 체크포인트와 로그가 섞이지 않는다. 문제는 시간이고, 아래 6절의 예산으로는 20시간에 시드 하나가 겨우 들어간다. 시드 하나로 갈 것이라면 논문에 "단일 훈련 시드"를 명시적 한계로 적고, 평가 시드 다섯의 분산이 훈련 분산을 대변하지 않는다는 점을 숨기지 말아야 한다.

---

## 5. 무인 실행과 재개의 정합성 (실측)

### 5.1 정기 보고의 데이터 원천이 훈련 중에는 비어 있다

이것이 이번 검토에서 가장 중요한 발견이다. `report_progress.py`의 거의 모든 절, 곧 에피소드 진행률과 갱신 0회 횟수와 밀도별 편차와 최근 열 에피소드 추이와 비유한값 스캔과 플로지빌리티 검사가 전부 `run_dir/lg/*_progress.csv` 하나만 읽는다. 그런데 3.3에서 본 대로 그 파일은 모델 하나가 완주해야 생긴다. 감시자를 통해 실행한 지 50초 뒤의 상태를 찍어보면 이렇다.

```
=== T+50s: ck / lg contents ===
PPO_best.pt
PPO_ep010.pt
-- lg:
(비어 있음)
```

열 에피소드가 끝나 체크포인트가 둘이나 있는데 `lg/`는 비어 있다. 본훈련에서 모델 하나는 약 1.2시간이 걸리므로, **6시간 간격 보고 한 번마다 그 시점에 훈련 중인 모델은 항상 보이지 않는다.** 실제로 진행 중인 실행을 보고서에 넣어보면 이렇게 나온다.

```
- `mean_seed42` 진행 중, 전체 0/0 에피소드 (0.0%)
```

요약 표에 행조차 없다. 원인은 `scan_run`이 `ck/`를 세는 `rec["checkpoints"]` 계산을 CSV 순회 **안쪽**에 두었기 때문이다. CSV가 없으면 바로 옆에 있는 체크포인트도 보지 않는다.

### 5.2 세 가지 상태가 전부 "부재"로 보인다

그 결과 "훈련 중", "20회 재시도 끝에 포기", "아직 시작 안 함" 세 상태가 보고서에서 동일하게 부재로 나타난다. 예외로 죽은 모델은 CSV를 남기지 않으므로 영원히 부재다. `run_all.py`는 한 모델이 예외로 죽어도 잡아서 로그에 `Failed training <model>`을 남기고 다음 모델로 넘어가는데, 그 신호를 보고서가 읽지 않는다. 아홉 모델 중 하나가 계속 실패하고 있어도 보고서는 그 모델을 아예 언급하지 않는다.

### 5.3 stall 탐지가 거꾸로 작동한다

`csv_age_min > 60`이면 정체로 판정하는데, 완주한 모델의 CSV는 다시 갱신되지 않는다. 다음 모델이 1.2시간 걸리므로 **정상 진행 중에 직전 모델이 매번 정체로 오탐된다.** 반대로 실제로 멈춘 모델은 CSV가 없어서 무탐이다. 오탐과 무탐이 동시에 나는 구조다.

### 5.4 SIGKILL 재개 실측: 조용한 데이터 손실

감시자 로직을 그대로 쓰되 실행 루트와 에피소드 수만 바꾼 사본으로, 25 에피소드 실행 중 파이썬 프로세스를 SIGKILL했다. 감시자는 정확히 동작했다.

```
[04:04:16] attempt 1: starting FRESH
[04:05:02] attempt 1 exited rc=137; backing off 10s then resuming
[04:05:12] attempt 2: resuming from newest checkpoint if any
[04:05:51] run finished successfully on attempt 2
run_result.json: {"arm":"accumulate","seed":42,"exit_code":0,"attempts":2}
```

체크포인트는 `PPO_ep010.pt`, `PPO_ep020.pt`, `PPO_ep025.pt`, `PPO_best.pt`로 정상이다. 그런데 진행 CSV는 이렇게 남았다.

```
episode,global_step,reward_per_sec_selected
11,1650,-0.006518
12,1800,-0.050037
...
25,3750,-0.082462
```

**에피소드 1부터 10까지가 영구히 없다.** 25 에피소드를 실제로 전부 돌았는데 수렴 곡선은 11부터 시작한다. 중복 행은 생기지 않는다. 재개 시 `df_prev[df_prev["episode"] <= start_ep]`로 자르는 처리가 제대로 되어 있어서, 구멍만 생기고 중복은 없다. 문제는 구멍이 어디에도 보고되지 않는다는 것이다. 같은 상태를 보고 스크립트에 넣으면 이렇게 나온다.

```
| accumulate_seed42 | PPO | 15/25 | 2 | 3 | 0.2 |
...
- `accumulate_seed42` 정상 종료, 시도 2회, 2026-09-02T04:05:51+09:00
```

"15/25"와 "정상 종료"가 같은 보고서에 나란히 있고, 어떤 규칙도 이 모순을 잡지 않는다. 본훈련 규모로 환산하면 체크포인트가 열 에피소드마다이므로 크래시 한 번당 최대 열 에피소드가 곡선에서 사라지고, 재시도가 여러 번이면 누적된다.

### 5.5 재개 시 그래디언트 갱신 계수 오류 (코드 버그)

`hot_swap_trainer.py:2909`의 `grad_updates_before_ep = 0`이 무조건 0으로 초기화되는데, `load_checkpoint`는 `:1169`에서 `background_trainer.training_steps`를 체크포인트 값으로 복원한다. 따라서 재개 후 첫 에피소드의 `grad_updates_this_episode = training_steps - grad_updates_before_ep`는 크래시 이전 누적분 전부에 그 에피소드 몫을 더한 값이 된다. 위 실측의 보고서 출력에 그대로 드러났다.

```
밀도별 학습량: 편차 10.6배 — 5:85 10:8 15:8 20:10 25:17 30:8 35:8 40:8 45:9 50:8
```

재개 지점에 해당하는 밀도 5만 85로 튀었다. 다른 밀도는 8에서 17 사이다. 이 열은 정기 보고의 밀도별 학습량 진단이자 논문의 모델 간 공정성 근거인 `grad_updates_by_density`의 원천이므로, 재개가 한 번이라도 일어나면 그 근거가 오염된다. 수정은 한 줄이다. `:2909`를 `grad_updates_before_ep = int(trainer.background_trainer.training_steps)`로 바꾸면 되고, 신규 실행에서는 0이므로 기존 동작이 바뀌지 않는다.

### 5.6 백업이 지키려는 것을 지키지 못한다

`backup_runs.sh`는 `ck/`와 `lg/`를 15분마다 스냅샷하고, 주석은 "Checkpoints and per-episode progress CSVs are the run"이라고 적는다. 그러나 5.1에서 본 대로 `lg/`는 훈련 내내 비어 있다. 백업은 실질적으로 체크포인트만 지키고 있고, 진짜로 유실 위험이 있는 에피소드 기록은 애초에 디스크에 없어서 백업할 대상이 없다. 하드링크 방식과 `.snapshot_complete` 표식과 세대 정리는 모두 잘 설계되어 있으므로, 원천만 고쳐지면 백업은 그대로 제 역할을 한다.

### 5.7 stdout에 에피소드 단위 신호가 없다

25 에피소드를 2회 시도로 완주한 실행의 `sup/train.log`가 58줄이고, 그중 `Episode N` 패턴은 4줄인데 전부 갱신 0회 경고다. `run_all.py`와 `run_hot_swap_training`은 모델 경계에서만 INFO를 찍는다. 로그를 tail해도 진행을 알 수 없고, 모델 하나가 1.2시간이므로 그 사이 로그는 사실상 정지 상태로 보인다.

### 5.8 잘 만들어진 것들

`PAPER4_SUMO_DIR` 격리는 실측으로 확인했다. 실행 디렉터리 아래 `sumo/`에 `generated.net.xml`, `generated.rou.xml`, `.sumo_gen_signature.json`, `.sumo_gen.lock`이 실행별로 생성되어 동시 실행 시 시나리오 교차 오염이 없다. `make_sumo_set.py:105`가 임포트 시점에 환경변수를 읽고 감시자가 프로세스 시작 전에 설정하므로 순서도 맞다.

`run_main_training.sh`의 팔·시드 격리, `--fresh`를 첫 시도에만 적용하는 처리, `run_result.json` 기록, 지수 백오프와 상한은 모두 적절하다. `resume_all.sh`가 `pgrep`로 중복 기동을 막고 `exit_code:0`만 완료로 인정하는 판정도 맞다. `gpu_alloc.py`가 여유 메모리와 사용률을 함께 보는 것도 옳고, 한 장만 받아도 `hot_swap_trainer.py:268` 이하가 act와 rest를 같은 GPU로 안전하게 강등하므로 `--need 1`이 위험하지 않다. 체크포인트 저장 시 `update_lock` 다음 `swap_lock` 순서로 torn snapshot을 막는 처리도 확인했다.

### 5.9 남는 운영 위험 둘

첫째, 모델 단위 포기 규칙이 없다. `run_all.py`는 한 모델이 예외로 죽어도 나머지를 계속 돌리고 마지막에 rc=1을 낸다. 감시자는 rc가 0이 아닌 것만 보고 아홉 모델 전체를 재시작한다. 결정론적인 크래시라면 20회 시도 동안 같은 지점에서 계속 죽는데, 백오프가 60초에서 시작해 1800초 상한까지 커지므로 순수 대기만 약 8시간이고, 그동안 이미 끝난 여덟 모델은 매번 체크포인트를 로드하고 SUMO 시나리오를 준비한 뒤 0 에피소드를 돌고 끝나는 no-op 재개를 반복한다. 20시간 창을 통째로 날리는 현실적인 경로다.

둘째, `gpu_alloc.py`에 예약 기능이 없다. 동시에 뜬 감시자 둘은 각각 usable 목록 전체를 받아 같은 GPU에 올라탄다. `resume_all.sh`의 20초 stagger로는 부족한데, 모델이 작아 첫 실행이 시작된 뒤에도 여유 메모리 8GiB와 사용률 30% 조건이 여전히 통과하기 때문이다. 치명적이지는 않지만 "남의 작업을 건드리지 않는다"는 목표는 부분적으로만 달성되고, 두 실행이 서로 느려진다.

---

## 6. 시간 예산 (실측)

밀도 25, 600스텝 에피소드 기준으로 아홉 모델의 처리량을 측정했다.

| 모델 | steps/s | 600 스텝당 갱신 |
|---|---:|---:|
| CARLTON | 65.5 | 68 |
| PPO | 57.3 | 12 |
| SAC | 54.8 | 83 |
| MA2HDQN | 49.6 | 147 |
| SPAM-D3QN | 49.6 | 287 |
| I-HAMAPPO | 48.5 | 173 |
| TD3 | 38.9 | 596 |
| MADDPG-MT | 38.9 | 448 |
| RES-MAPDDPG | 35.7 | 320 |

평균 약 48 steps/s이므로 모델당 20만 스텝은 약 1.16시간이고, 팔 하나 시드 하나에 아홉 모델이면 약 10.4시간이다. 평가는 추론 전용이라 약 76 steps/s로 측정됐고, 열 모델 × 열 밀도 × 다섯 시드 × 2000 스텝은 100만 스텝이므로 약 3.7시간이다. 따라서 팔 하나 시드 하나에 평가까지 약 14시간으로 20시간 창에 들어간다. 두 팔이면 약 28시간, 두 팔 세 시드면 약 84시간으로 들어가지 않는다. 동시 실행으로 줄일 수 있지만 GPU 예약이 없어 서로 느려지므로 선형 이득을 기대하기 어렵다. **20시간 창에는 팔 하나 시드 하나가 현실적인 범위다.**

### 6.1 그래디언트 예산 불균형

위 표의 오른쪽 열이 보여주듯 최대와 최소의 비가 596 대 12, 곧 **약 50배**다. `run_main_training.sh`는 `--updates-per-env-step`을 넘기지 않으므로 기본값 None, 곧 무제한이자 wall-clock 종속이다. 지금 설정으로 나올 표는 TD3가 PPO보다 50배 많은 갱신을 받은 비교이고, 리뷰어가 반드시 짚는다.

주의할 점은 이 옵션이 천장일 뿐 바닥이 아니라는 것이다. `updates_allowed()`는 `training_steps < train_frequency * env_steps_seen`만 확인하므로, 상한을 크게 잡으면 아무것도 바뀌지 않고 작게 잡으면 전부 눌린다. PPO의 실측치 12/600 = 0.02에 맞추면 TD3가 50분의 1로 줄어 학습이 되지 않는다. 실질적인 선택지는 둘이다. 중간값, 예컨대 0.25/step으로 상한을 두고 실제로 걸렸는지 `grad_updates_this_episode`로 사후 검증하거나, 상한 없이 가되 논문에 "모든 방법이 동일한 20만 환경 스텝을 받았으며 갱신 횟수는 알고리즘 특성에 따라 다르고 표에 함께 보고한다"고 명시하는 것이다. 어느 쪽이든 **모델별 총 갱신 횟수를 표로 보고해야 한다**.

---

## 7. 정기 보고에 넣을 지표 제안

현재 `report_progress.py`가 고른 지표들 자체는 적절하다. 문제는 지표가 아니라 원천이다. 아래 0번이 선행되지 않으면 나머지 대부분이 무의미하다.

**0. (선행, 트레이너 수정) 에피소드마다 진행 CSV를 즉시 append할 것.** `ep_record`를 만든 직후 append 모드로 한 줄씩 쓰고 헤더는 첫 줄에만 붙인다. 이 하나로 5.1의 보고 사각지대, 5.4의 곡선 구멍, 5.6의 백업 공백, 3.3의 수렴 곡선 취약성이 동시에 해소된다. 보고 스크립트가 아니라 `hot_swap_trainer.py` 쪽 수정이지만 보고의 전제조건이라 여기 둔다.

그 위에서, 지금 없는 것들을 우선순위 순으로 적는다.

**1. 체크포인트 기반 진행률 폴백.** CSV가 없어도 `ck/{model}_ep(\d+).pt`의 최대 번호로 진행률을 말할 수 있다. `scan_run`의 순서를 뒤집어, 먼저 `ck/`를 스캔해 모델 목록과 진행률을 만들고 CSV는 있으면 추이를 덧붙이는 용도로 쓸 것. 이것 하나로 5.1과 5.2가 대부분 해결된다.

**2. 모델별 상태를 명시적으로 분류.** 각 모델을 미시작 / 훈련중 / 완료 / 실패 / 정체 중 하나로 판정해 표에 찍을 것. 실패 판정은 `sup/train.log`에서 `Failed training (\S+)`와 `\d+/\d+ model\(s\) failed`를 grep하면 된다. `run_all.py`가 확실히 찍는 문자열이다. "부재"가 세 가지를 뜻하는 지금 상태를 없애는 것이 목적이다.

**3. 에피소드 번호 연속성 검사.** CSV의 `episode` 열이 1부터 빠짐없이 이어지는지 확인하고 구멍이 있으면 구간을 적을 것. 예: `PPO: 에피소드 1-10 누락 (재개로 유실)`. 5.4를 잡는 유일한 방법이다. `run_result.json`의 `attempts > 1`이나 감시자 로그의 재시도 횟수와 교차 확인하면 원인까지 말할 수 있다.

**4. 재시작 횟수를 요약 최상단으로.** 지금은 완료 상태 절에 묻혀 있다. 재시작이 일어났다는 사실 자체가 곡선에 구멍이 있다는 신호이므로 맨 위 요약에 올릴 것. 진행 중에도 `sup/supervisor.log`에서 `attempt (\d+) exited rc=(\d+)`를 세면 알 수 있다.

**5. 정체 판정을 체크포인트 mtime 기준으로 교체.** 지금의 CSV mtime 기준(5.3)은 오탐과 무탐을 동시에 낸다. 대신 그 실행 디렉터리에서 가장 최근에 수정된 체크포인트의 나이를 쓸 것. 정상 진행이면 열 에피소드마다, 곧 약 7분마다 갱신된다. 임계값 30분이 적당하고, `run_result.json`의 exit_code가 0인 완료된 실행은 검사에서 제외할 것.

**6. 실측 처리량과 ETA.** 지금 코드에는 ETA가 없고 `csv_age_min`만 있다. `global_step` 차이를 체크포인트 mtime 차이로 나누어 실측 steps/s를 내고 남은 스텝으로 ETA를 계산할 것. 직전 보고 대비 절반 이하로 떨어졌으면 경고를 낼 것. 스와핑, GPU 경합, SUMO 자원 누수를 잡는다.

**7. `swap_count`와 `failed_swaps`.** 지금 빠져 있는데 트레이너 주석(`hot_swap_trainer.py:554` 이하)이 직접 경고하는 실패 유형이다. Rest 모델이 NaN으로 발산하면 스왑이 거부되어 Act가 마지막 정상 가중치로 얼어붙는데, 지표는 그럴듯하게 유지되고 보상 곡선은 오히려 더 안정적으로 보인다. 진행 CSV에 `swap_count`가 있으므로 "최근 열 에피소드 동안 `swap_count` 증가량 0"을 경고 조건으로 넣을 것. `failed_swaps`는 CSV 열에 없으니 TensorBoard의 `HotSwap/FailedSwaps`를 읽거나 CSV 열을 추가해 확보할 것.

**8. `n_observations`의 밀도별 하한 검사.** 빈 에피소드는 3연속이면 런타임 에러로 막히지만 2회까지는 통과하고 그 에피소드의 보상은 NaN이 된다. 밀도 5에서 특히 위험하다. 밀도별 평균 `n_observations`와 `n_vehicles_seen`을 표로 찍고, 밀도 5 셀이 0에 가까우면 경고할 것. 논문의 sparse regime 주장이 통째로 여기 걸려 있다.

**9. 행동 공간 포화 검사.** 정책이 행동 공간 한쪽 끝에 붙는 실패는 보상 곡선만으로는 보이지 않는다. `mean_delta`가 `DELTA_MIN` 또는 `DELTA_MAX`의 5% 이내에 최근 열 에피소드 연속으로 머물면 경고할 것. `avg_tx_power_dbm`이 P_MIN 또는 P_MAX에 붙는 경우도 같은 논리로 볼 것.

**10. 비유한값 스캔을 보상 열에 특화.** 지금 스캔은 전체 수치 열을 대상으로 `nonfinite_cells` 하나만 센다. `reward_per_sec_selected`의 NaN은 "빈 에피소드"라는 특정한 의미가 있으므로 따로 셀 것. 그리고 현재 구현은 `df.select_dtypes("number")`를 쓰는데, CSV 읽기에서 어떤 열이 object로 들어오면 그 열은 검사에서 빠진다. `pd.to_numeric(errors="coerce")`로 강제 변환한 뒤 검사할 것.

**11. 디스크 여유와 `runs/` 크기.** 체크포인트는 열 에피소드마다 갱신되므로 백업 세대 사이에 하드링크가 거의 걸리지 않는다. 여덟 세대면 실질적으로 여덟 벌이다. `df -h`와 `du -sh runs backup/runs_snapshots`를 찍고 여유가 10% 미만이면 경고할 것. 디스크가 차면 체크포인트 쓰기가 실패해 재개 지점을 잃는다.

**12. GPU 상태 한 줄.** `gpu_alloc.py --json`을 그대로 호출해 메모리와 사용률을 찍을 것. 느려진 원인이 남의 작업인지 우리 쪽인지 구분된다. 아울러 `act_device`와 `rest_device`가 가용 GPU 수에 따라 실행마다 달라질 수 있는데 지금 어디에도 기록되지 않는다. `run_config.json`에 추가하고 보고에 찍을 것.

**13. 두 팔의 보상을 같은 표에 놓지 말 것.** 표를 팔별로 분리하거나, 최소한 "팔 간 보상 수치는 척도가 달라 비교 불가"를 표 각주로 넣을 것.

**14. 평가 진입 조건 점검 한 줄.** 훈련이 끝나면 다음은 평가인데 지금 보고서는 훈련만 본다. 아홉 모델 전부에 `{stem}_best.pt`가 있는지, `results/hpo/optuna_best_params.csv`가 현재 코드와 정합한지(1.1 참조) 확인하는 줄을 넣을 것. 훈련이 끝난 시점에 평가가 못 돌아가는 상태라면 그것을 20시간 뒤가 아니라 지금 알아야 한다.

우선순위로는 0, 1, 2, 3, 5, 7, 8이 "조용히 망가짐"을 직접 잡는다. 나머지는 원인 진단용이다.

---

## 8. 본훈련 전 수정 목록

1. **HPO CSV 재생성.** `--tune-reward-weights` 없이 다시 돌려 아홉 모델을 같은 보상 아래에서 튜닝할 것. 현재 파일은 코드가 재생산할 수 없는 유물이다. (1.1)
2. **진행 CSV 즉시 flush.** `hot_swap_trainer.py`에서 에피소드마다 append. 네 가지 문제가 한 번에 풀린다. (3.3, 5.1, 5.4, 5.6)
3. **`grad_updates_before_ep` 재개 초기화.** `hot_swap_trainer.py:2909` 한 줄. (5.5)
4. **`report_progress.py`를 체크포인트 우선으로 재작성.** 7절 0~5번. (5.1~5.3)

권장하지만 차선인 것: `load_checkpoint`의 대조 목록에 `error_mode` 추가(2.1), `--updates-per-env-step` 값 결정 또는 갱신 횟수 표 보고(6.1), 모델 단위 포기 규칙(5.9), 평가용 무인 스크립트와 팔별 출력 디렉터리(1.4).

논문에 한계로 명시할 것: 단일 훈련 시드(4절), HPO의 짧은 예산과 단일 밀도(1.1), `peak_aoi`/`max_error`의 평균 정의와 dBm 로그 평균(3.4).

---

## 9. 질문

1. **훈련 시드를 몇 개로 갈 것인가.** 20시간 창에는 팔 하나 시드 하나가 한계다(6절). 선택지는 (가) accumulate 팔만 시드 셋으로 돌려 통계를 확보하고 mean 팔은 나중에, (나) 두 팔을 시드 하나씩 돌려 ablation을 확보하고 단일 시드를 한계로 명시, (다) 창을 40시간 이상으로 늘림. 논문의 주장 구조상 어느 쪽이 우선인가.

2. **그래디언트 예산 상한을 걸 것인가.** 50배 불균형을 그대로 두고 표에 갱신 횟수를 함께 보고할 것인지, 상한을 걸 것인지. 상한을 건다면 값은 얼마로 할 것인지. 상한이 실제로 걸렸는지 확인하려면 파일럿이 필요한데 그 시간을 쓸 것인가.

3. **HPO 재실행 범위.** 고정 가중치로 아홉 모델 전부 다시 돌릴 것인가, 아니면 현재 CSV를 폐기하고 라이브러리 기본값으로 본훈련에 들어갈 것인가. 후자라면 "하이퍼파라미터 튜닝을 수행했다"는 서술을 논문에서 빼야 한다.

4. **평가의 팔 구분을 어떻게 남길 것인가.** `evaluate.py`에 `--error-mode` 인자와 출력 CSV의 `error_mode` 열을 추가할 것인지, 아니면 출력 디렉터리를 팔별로 나누는 것으로 충분하다고 볼 것인지.

5. **`peak_aoi`의 정의.** 표에 실을 값이 "셀별 최대의 평균"인가 "전체 최대"인가. 전자라면 각주로 명시하면 되고, 후자라면 `_aggregate`의 집계 방식을 바꿔야 한다.
