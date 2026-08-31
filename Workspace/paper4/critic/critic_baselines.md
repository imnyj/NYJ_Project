# Critic 검토 — src/baselines/ 9종 + heuristic_scheduler.py

검토일 2026-08-31. 대상 커밋: 워킹트리 현재 상태.
Python `/home/imnyj/venv/bin/python`. **코드 수정 없음**(Critic은 읽고 검증만 함).
`checkpoints/`, `logs/training/`, `results/` 는 건드리지 않았다. 실측은 모두 인메모리
인스턴스화와 `RetrospectiveReplayBuffer` 왕복으로만 수행했고, SUMO는 기동하지 않았다.
이전 리포트(git에 보존)에서 지적한 결함 1·2는 **해소되었음을 확인**했다. 그 대신 이번에
같은 계열의 더 깊은 결함이 새로 드러났다.

---

## 판정

**REJECT — 현재 상태로 200,000스텝 본훈련에 들어가면 안 된다.**

이전 감사가 잡아낸 두 가지 큰 구멍(`evaluate.py`/`hpo.py`가 9종에 연결되지 않은 문제,
`sample_hparams`의 이름 불일치)은 실제로 고쳐졌고 `assert_hparams_reach_model` 가드도
진짜로 동작한다. 그러나 이번 검토에서 그 가드가 원리적으로 볼 수 없는 층에 세 종류의
치명적 결함이 남아 있음을 실측으로 확인했다. 첫째, `ActionDecoder.encode_action`이
기하 매핑으로 바뀌었는데 `spam_d3qn.py`·`carlton.py`·`maddpg_mt.py` 세 모듈은 여전히
선형 매핑을 가정하고 역변환하므로, SPAM-D3QN과 CARLTON은 128개 행동 인덱스 중 **96개를
잘못 복구**한다. 즉 유사 모델 3종 중 2종이 Δ 축을 4분의 3의 확률로 엉뚱한 Q 슬롯에
학습시키고 있다. 둘째, 아홉 모델 전부 `gamma` 하이퍼파라미터가 실제 학습에 **아무 영향을
주지 않는다**. 리플레이 버퍼가 자기 자신의 `gamma=0.99`로 `discount`를 만들어 배치에
넣고, 모든 `update()`가 그 값을 그대로 쓰기 때문이다. 셋째, `evaluate.py`의 벤치마크
경로에는 체크포인트를 불러오는 코드가 한 줄도 없어서, 지금 벤치마크를 돌리면 **학습된
가중치가 아니라 방금 랜덤 초기화된 신경망 9개를 채점**하게 된다. 여기에 더해 이미
생성되어 있는 `results/hpo/optuna_best_params.csv`는 모델당 3 trial짜리이며 모델마다
보상 가중치 w1~w4가 서로 다르다. 이는 `run_hpo_study`의 docstring이 스스로 금지한
조건이다. 결함 1을 고치지 않은 채 8.8시간짜리 본훈련을 돌리면 비교 논문에서 가장
위험한 형태의 결과, 즉 "제안 기법이 이겼지만 경쟁 baseline이 망가져 있어서 이긴 것"이
그대로 산출된다. 아래 CRITICAL 4건과 HIGH 5건을 처리한 뒤 재검토를 요청한다.

---

## 결함 요약

| ID | 심각도 | 대상 | 한 줄 요약 |
|---|---|---|---|
| C-1 | CRITICAL | `spam_d3qn.py:268`, `carlton.py:263`, `maddpg_mt.py:262` | `encode_action` 기하화 이후에도 선형 역변환을 써서 Δ 크레딧 할당이 깨졌다 (96/128 오복구) |
| C-2 | CRITICAL | `src/evaluate.py:301` | 벤치마크가 체크포인트를 전혀 로드하지 않아 학습 안 된 모델을 채점한다 |
| C-3 | CRITICAL | `rl_interface.py:725` + 9종 `update()` 전부 | `gamma`가 버퍼의 `discount`에 덮여 아홉 모델 모두 실효가 없다 (실측 확인) |
| C-4 | CRITICAL | `results/hpo/optuna_best_params.csv` | 모델당 3 trial, 게다가 모델마다 보상 w1~w4가 달라 교차 비교 근거가 무효다 |
| H-1 | HIGH | `hot_swap_trainer.py:439-446` | 그래디언트 갱신 횟수가 백그라운드 스레드의 벽시계 경쟁으로 결정된다 |
| H-2 | HIGH | `spam_d3qn.py:150-158` | `epsilon`이 buffer가 아니라 평범한 속성이라 Act 모델에서 영원히 0.2로 고정된다 |
| H-3 | HIGH | 9종 전체 | 파라미터 수가 10,887 ~ 772,810으로 71배 차이나며 기본 3종은 폭을 탐색조차 못 한다 |
| H-4 | HIGH | `ma2hdqn.py:121`, `i_hamappo.py:117`, `carlton.py:157` | Optuna가 탐색하지만 학습에 전혀 쓰이지 않는 하이퍼파라미터 3개 (실측 확인) |
| H-5 | HIGH | `hpo.py:426-434` | HPO trial 1회의 학습량이 너무 적어 200k 스텝용 하이퍼파라미터를 구분할 수 없다 |
| M-1 | MEDIUM | `carlton.py:147,296` + `hpo.py:206` | `omega` 탐색범위 [0.1,0.9]가 기본값 10.0과 동떨어져 있고 탐험 정책이 붕괴할 수 있다 |
| M-2 | MEDIUM | `maddpg_mt.py:380-397`, `res_mapddpg.py:326`, `i_hamappo.py:331` | 인용 논문의 헤드라인 기여(태스크 분해, 중앙집중 크리틱)가 실행 경로에서 불활성이다 |
| M-3 | MEDIUM | `evaluate.py:345` | 리더보드 composite의 전력 정규화가 폐기된 [20,30]dBm을 하드코딩했다 |
| M-4 | MEDIUM | `evaluate.py:163-164`, `evaluate.py:229-241` | 휴리스틱이 Δ≤10s로 묶이고 `accel`을 못 받아 규칙 절반이 죽어 있다 |
| M-5 | MEDIUM | `evaluate.py:112-125` | CSV의 `w1..w4`·`w1_raw..`를 걸러내지 않고 모델 생성자에 흘려보낸다 |
| M-6 | MEDIUM | `hpo.py:365-367` | `except Exception: pass` 가 이전 리포트 이후 그대로 남아 있다 |
| L-1 | LOW | `spam_d3qn.py:122-124`, `carlton.py:90-91`, 세 모듈 docstring | 존재하지 않는 검증 스크립트를 인용하고, 선형 인코딩을 설명하는 주석이 사실과 다르다 |
| L-2 | LOW | `etc/scripts/verify_all_baselines.py`, `tests/test_hpo.py:269` | 두 검증 장치 모두 C-1과 C-3을 구조적으로 잡을 수 없다 |
| L-3 | LOW | `run_all.py:281` | 본훈련이 단일 시드(42)이므로 모델 간 차이를 시드 잡음과 분리할 수 없다 |

---

## C-1 [CRITICAL] `encode_action` 기하화 이후 세 모듈의 역변환이 깨졌다

**근거.** `src/rl_interface.py:635-645`의 `encode_action`은 이제 Δ를
`logit(unit_from_delta(delta))`로, 즉 **기하 단위좌표의 로짓**으로 인코딩한다.
같은 파일 `:616-622`의 주석이 "`decode_action`이 선형이었던 것을 기하로 고쳤다"고
스스로 기록하고 있다. 그런데 raw_action을 되돌리는 세 곳은 여전히 선형을 가정한다.

```
src/baselines/spam_d3qn.py:268
    delta = dec.delta_min + torch.sigmoid(acts[:, 0]) * (dec.delta_max - dec.delta_min)
src/baselines/carlton.py:263          (동일 코드)
src/baselines/maddpg_mt.py:262        (동일 코드, 이후 _unit_from_delta_t로 재변환)
```

**실측.** 결정자 기본 격자
`[0.100, 0.239, 0.573, 1.371, 3.282, 7.855, 18.801, 45.000]`에 대해
`encode_action` → `_infer_action_indices` 왕복을 128개 결합 인덱스 전부에 대해 돌렸다.

| 참 delta_idx | 참 Δ(s) | 복구된 Δ(s) | 복구된 delta_idx |
|---|---|---|---|
| 0 | 0.100 | 0.100 | 0 |
| 1 | 0.239 | 6.514 | 5 |
| 2 | 0.573 | 12.929 | 6 |
| 3 | 1.371 | 19.343 | 6 |
| 4 | 3.282 | 25.757 | 6 |
| 5 | 7.855 | 32.171 | 7 |
| 6 | 18.801 | 38.586 | 7 |
| 7 | 45.000 | 45.000 | 7 |

- `SPAM-D3QN`: **96/128 결합 인덱스 오복구** (8개 Δ 레벨 중 6개가 틀림 × 전력 4 × 채널 4)
- `CARLTON`: **96/128 브랜치 인덱스 삼중항 오복구**
- `MADDPG-MT`: `u_delta` 왕복이 (0.1→0.626), (0.3→0.804), (0.5→0.887), (0.9→0.983)로
  전 구간에서 상단으로 압축된다. 크리틱이 실제 실행된 Δ가 아닌 값을 조건으로 학습한다.

전력 축은 양쪽 모두 선형이라 정상이며, 채널 축도 정상이다. **오직 Δ 축만 깨져 있다.**

**왜 중요한가.** 이 논문의 주장 자체가 "Δ(갱신 타이밍)를 잘 고르는 것"이다. 유사 모델
3종 중 2종이 Δ에 대해 4분의 3의 확률로 다른 행동의 Q를 갱신하고 있다면, 그 두 baseline은
Δ를 학습할 수 없다. 제안 기법이 이들을 이기는 결과는 알고리즘 우열이 아니라 이 버그의
결과가 된다. 이것은 `Conversation.md` 5절이 기록한 과거 `DuelingQAoI` 크레딧 할당
버그(20개 출력 중 4개만 학습)와 **정확히 같은 계열의 재발**이며, 두 모듈의 docstring이
"그 버그는 고쳐졌고 assert로 검증된다"고 명시하고 있어 더 위험하다.

**Coder 지침.**
1. 세 곳 모두 `u = torch.sigmoid(acts[:, 0])` 를 **선형 정규화가 아니라 기하 단위좌표로**
   해석하도록 고칠 것. `spam_d3qn`/`carlton`은 `d_idx = argmin |u - u_grid|` 로 단위좌표
   공간에서 직접 스냅하는 편이 로그 변환보다 안전하다(`u_grid[i] = i/(n-1)`).
   `maddpg_mt`는 `u_delta = torch.sigmoid(acts[:, 0])` 한 줄로 끝난다.
2. 고친 뒤 128개 인덱스 전수 왕복 assert를 `etc/scripts/`의 검증 스크립트와 pytest에
   **동시에** 추가할 것. 왕복 실패 0건이 아니면 실패하도록.
3. `ActionDecoder`의 인코딩 규약이 다시 바뀔 때 이 세 곳이 자동으로 깨지지 않도록,
   역변환을 세 번 베껴 쓰지 말고 `ActionDecoder`에 `unit_from_raw(raw)` 같은 정본
   메서드를 하나 두고 세 모듈이 그것을 부르게 할 것.

---

## C-2 [CRITICAL] 벤치마크가 학습된 체크포인트를 전혀 로드하지 않는다

**근거.** `src/evaluate.py:301`

```python
model = instantiate_model(canonical_name, hparams)
```

`instantiate_model`(`:138-174`)은 `model_cls(state_dim=..., num_channels=..., **params)`로
**새 인스턴스를 만들 뿐**이며, `run_full_benchmark`(`:264-376`)와 `main()`(`:378-424`)
어디에도 체크포인트 경로 인자가 없다. 파일 전체 grep 결과 `.load(`, `load_state_dict`,
`checkpoints/` 문자열이 **0건**이다(실측). `BaseRLModel.load()`(`base_agent.py:99`)는
정의되어 있으나 호출하는 곳이 없다.

**왜 중요한가.** 9종 × 5밀도 × 5시드 = 225회 벤치마크를 돌려도 전부 랜덤 초기화 모델의
성능이다. 200,000스텝 훈련 결과가 논문의 표에 반영될 경로 자체가 없다. 지금 이 상태에서
벤치마크를 돌리면 "모든 모델이 비슷하게 나쁘다" 또는 "초기화 운에 따라 순위가 정해진다"가
나오며, 그 CSV는 논문에 그대로 실릴 수 있다.

**Coder 지침.** `run_full_benchmark`에 `checkpoint_dir` 인자를 추가하고,
`run_hot_swap_training`이 쓰는 파일명 규칙(`{model_cls.__name__}_ep{NNN}.pt`,
`hot_swap_trainer.py:1897`에서 클래스명 기반으로 정해짐)에 맞춰 최신 에피소드
체크포인트를 찾아 `model.load(path)`를 호출할 것. 체크포인트가 없으면 경고가 아니라
**예외로 중단**해야 한다. 조용히 랜덤 모델을 채점하는 것이 이 결함의 본질이므로,
"없으면 기본값으로 진행"은 같은 사고를 재발시킨다. 또한 체크포인트에 저장된
`hparams`(`base_agent.py:96`)와 CSV의 hparams가 다르면 `hidden_dim` 불일치로
`load_state_dict`가 터지므로, 저장된 쪽을 정본으로 삼을 것.

---

## C-3 [CRITICAL] `gamma`가 아홉 모델 전부에서 무효다

**근거.** `RetrospectiveReplayBuffer.sample()`은 항상 `discount` 키를 넣는다.

```
src/rl_interface.py:725   discounts = np.power(self.gamma, delta_ts).astype(np.float32)
src/rl_interface.py:734   "discount": torch.from_numpy(discounts),
```

이때 쓰이는 `self.gamma`는 **버퍼 생성 시점의 값**이고, 두 생성 지점 모두 인자를
넘기지 않아 기본값 0.99로 고정된다.

```
src/hot_swap_trainer.py:680   self.replay_buffer = RetrospectiveReplayBuffer(capacity=self.buffer_capacity)
src/hpo.py:335                buffer = RetrospectiveReplayBuffer(capacity=1000) if ...
```

아홉 모델의 `update()`는 예외 없이 `if "discount" in batch: discounts = batch["discount"]`
분기를 먼저 타므로(`sb3_wrapper.py:366`, `res_mapddpg.py:321`, `ma2hdqn.py:321`,
`i_hamappo.py:326`, `spam_d3qn.py:321`, `carlton.py:321`, `maddpg_mt.py:373`),
생성자로 받은 `gamma`는 SB3 객체에 저장만 되거나 `self.gamma`에 남을 뿐 사용되지 않는다.

**실측.** 동일 시드로 `gamma=0.95` 모델과 `gamma=0.999` 모델을 만들어 동일 배치로
`update()`를 1회 수행한 뒤 `state_dict()`를 비교했다.

| 모델 | 파라미터 수 | 배치에 `discount` 존재 | 배치에 `action_idx` 존재 | gamma 변경 후 가중치 동일 |
|---|---|---|---|---|
| PPO | 10,887 | True | False | **True (무효)** |
| SAC | 357,643 | True | False | **True (무효)** |
| TD3 | 772,810 | True | False | **True (무효)** |
| RES-MAPDDPG | 301,656 | True | False | **True (무효)** |
| MA2HDQN | 148,880 | True | False | **True (무효)** |
| I-HAMAPPO | 68,657 | True | False | **True (무효)** |
| SPAM-D3QN | 87,426 | True | False | **True (무효)** |
| CARLTON | 44,624 | True | False | **True (무효)** |
| MADDPG-MT | 222,748 | True | False | **True (무효)** |

**왜 중요한가.** `sample_hparams`는 아홉 모델 전부에 대해 `gamma`를 [0.95, 0.999]에서
샘플링하고(`hpo.py:141,152,161,...`), 그 값이 `optuna_best_params.csv`에 "최적값"으로
기록되어 논문 6절 표에 들어갈 예정이다. 실제로는 전부 0.99로 학습된다. 이것은 이전
감사가 잡은 결함 2와 완전히 같은 성격의 사고인데, `assert_hparams_reach_model`은
`gamma`가 진짜 생성자 인자이므로 **통과시킨다**. 가드가 이름 도달만 검사하고 값의 효과는
검사하지 않기 때문이다.

**Coder 지침.** 둘 중 하나를 선택하되 사용자에게 확인할 것.
(A) 모델별 `gamma`를 살리려면 `RetrospectiveReplayBuffer`를 모델의 `gamma`로 생성하도록
`HotSwapTrainer.__init__`과 `hpo.evaluate_model_in_env`를 고치고, 그러면 하나의 버퍼가
Act/Rest 한 쌍에 종속되므로 재개(resume) 시 gamma 일관성을 체크해야 한다.
(B) `gamma`를 벤치마크 상수로 못 박고 `sample_hparams`의 모든 `gamma` 항목을 **제거**한 뒤,
`DEFAULT_REWARD_WEIGHTS`처럼 `DEFAULT_GAMMA` 상수를 한 곳에 두고 버퍼가 그것을 읽게 할 것.
어느 쪽이든 `assert_hparams_reach_model`을 "이름이 생성자에 있는가"에서 "값을 바꾸면
1회 `update()` 후 가중치가 달라지는가"로 강화해 아홉 모델 전 키에 대해 돌려야 한다.
그 테스트가 있었다면 C-3과 H-4가 모두 잡혔다.

---

## C-4 [CRITICAL] 이미 산출된 HPO 결과가 교차 비교의 근거가 될 수 없다

**근거.** `results/hpo/optuna_trials_*.csv` 9개 파일 모두 헤더 포함 4행, 즉 **모델당
3 trial**이다. 그리고 `optuna_best_params.csv`의 `w1..w4` 열이 모델마다 다르다.

| model_name | best_value | w1 | w2 | w3 | w4 |
|---|---|---|---|---|---|
| PPO | 1.1890 | 0.079185 | 0.343749 | 0.363897 | 0.213169 |
| SAC | 1.2178 | 0.131131 | 0.436614 | 0.177244 | 0.255012 |
| TD3 | 0.9489 | 0.724342 | 0.056908 | 0.095643 | 0.123107 |
| RES-MAPDDPG | 0.8943 | 0.379438 | 0.027277 | 0.534774 | 0.058512 |
| MA2HDQN | 0.8874 | 0.854661 | 0.051764 | 0.046662 | 0.046913 |
| I-HAMAPPO | 1.0737 | 0.361346 | 0.015181 | 0.383314 | 0.240159 |
| SPAM-D3QN | 1.1226 | 0.680022 | 0.125741 | 0.042617 | 0.151620 |
| CARLTON | 1.2198 | 0.523336 | 0.104243 | 0.310203 | 0.062218 |
| MADDPG-MT | 0.9197 | 0.361346 | 0.015181 | 0.383314 | 0.240159 |

`optuna_trials_PPO.csv`에 `params_w1_raw` 열이 존재하므로 이 실행은
`tune_reward_weights=True`로 수행되었다. 그런데 `run_hpo_study`의 docstring
(`hpo.py:466-471`)은 스스로 이렇게 못 박고 있다. "Turn it on only for a reward-shaping
ablation, never for the numbers that go into the cross-model comparison table."

**왜 중요한가.** 세 가지가 동시에 무너진다. 첫째, MA2HDQN은 w1=0.855(오차 항 지배),
PPO는 w1=0.079(오차 항 거의 무시)로 **서로 다른 목적함수 아래에서** 최적화되었으므로
`best_value` 열끼리의 비교가 성립하지 않는다. 둘째, `run_all.py:159-164`가 CSV의
w1~w4를 `ENV_ONLY_HPARAM_KEYS`로 걸러내고 훈련은 `DEFAULT_REWARD_WEIGHTS`(0.5/0.2/0.2/0.1)로
수행하므로, **탐색 당시의 보상과 본훈련의 보상이 다르다**. 셋째, I-HAMAPPO와 MADDPG-MT의
w1~w4가 소수점 6자리까지 완전히 동일하다. `TPESampler(seed=42)`가 study마다 재설정되고
trial이 3개뿐이라 같은 점을 뽑은 것으로, 이 정도 trial 수에서는 탐색이 사실상 일어나지
않았음을 보여준다.

**Coder 지침.** `results/hpo/` 산출물 전체를 **폐기 대상으로 표시**하고 재실행할 것.
재실행 시 `tune_reward_weights=False`(현재 기본값)를 유지하고, trial 수는 3이 아니라
최소 `--n-trials 15`(코드 기본값) 이상으로 할 것. 다만 그전에 C-3과 H-5를 먼저 고치지
않으면 재실행해도 같은 품질의 결과가 나온다.

---

## H-1 [HIGH] 그래디언트 갱신 예산이 벽시계 경쟁으로 정해진다

**근거.** `BackgroundTrainer._worker_loop`(`hot_swap_trainer.py:439-446`)는 데몬 스레드에서
`train_step()`을 최대한 빨리 반복한다. 배치가 준비되면 0.0005초, 아니면 0.002초 쉬고
다시 돈다. 환경 스텝 수와의 동기화는 어디에도 없다.

**왜 중요한가.** 200,000 환경 스텝 동안 각 모델이 받는 `update()` 횟수는 그 모델
`update()`의 실행 시간에 반비례한다. CARLTON(44,624 파라미터, 브랜치 3개 MSE)은 빠르고
TD3(772,810 파라미터, 트윈 크리틱)과 PPO(내부 `n_epochs`=10회 역전파)는 느리다.
`Conversation.md` 5절이 기록한 2 에피소드 × 300스텝 스모크에서 이미 모델별
그래디언트 갱신이 **108~931회(8.6배 차이)**로 갈렸다. 즉 훈련 예산 자체가 모델 용량과
역상관으로 배분된다. 비교 논문에서 "동일 예산"은 반드시 방어해야 하는 항목인데, 현재는
동일 예산이 아닐 뿐 아니라 스레드 스케줄링에 좌우되어 **같은 시드로 재실행해도 재현되지
않는다**.

**Coder 지침.** `BackgroundTrainer`에 `updates_per_env_step`(또는 `train_frequency`를
실제로 사용하는) 상한을 두어, 환경 스텝 카운터를 공유하고 `training_steps`가
`env_steps * ratio`를 넘으면 대기하도록 바꿀 것. 그리고 훈련 종료 시 summary에
`training_steps`를 반드시 남겨, 아홉 모델의 갱신 횟수가 실제로 같은지 사후 검증
가능하게 할 것. 예산을 동일화하기 어렵다면 최소한 아홉 모델의 최종 `training_steps`를
논문에 표로 공개해야 한다.

---

## H-2 [HIGH] SPAM-D3QN의 탐험 스케줄이 Act 모델에 전달되지 않는다

**근거.** 핫스왑은 파라미터와 buffer만 복사한다(`hot_swap_trainer.py:252-263`).
그런데 모델마다 탐험 상태의 저장 방식이 다르다(실측한 `named_buffers()`).

| 모델 | 등록된 buffer | Act 모델에 전달되는가 |
|---|---|---|
| RES-MAPDDPG | `epsilon` | 예 |
| MA2HDQN | `epsilon`, `reward_ema`, `reward_ema_init`, `lr_scale`, `update_count` | 예 |
| SPAM-D3QN | (없음) | **아니오** |
| CARLTON | (없음) | 해당 없음(ε 미사용) |

`spam_d3qn.py:150,154,158`의 `self.epsilon`, `self.per_beta`, `self.total_updates`는
평범한 파이썬 속성이라 `state_dict()`에도 들어가지 않는다(실측: `"epsilon" in
s.state_dict()` → False). `update()`는 Rest 모델에서만 호출되므로(`BackgroundTrainer`),
**행동하는 Act 모델의 epsilon은 200,000스텝 내내 초기값 0.2에 머문다.**

**왜 중요한가.** SPAM-D3QN은 128개 결합 행동 중 20%를 끝까지 균등 무작위로 고른다.
RES-MAPDDPG와 MA2HDQN은 같은 `epsilon_decay`를 받아 0.01까지 감쇠한다. 동일 조건에서
비교한다는 전제가 깨지고, 특히 SPAM-D3QN은 이 논문에서 가장 가까운 경쟁자 중 하나다.
C-1과 겹쳐서 SPAM-D3QN은 이중으로 불리한 상태다. 부수적으로 `total_updates`가 Act
모델에서 0에 고정되는 것 자체는 무해하지만(타깃 동기화는 Rest에서 일어남), 체크포인트
저장·재개 시 `epsilon`과 `per_beta`가 복원되지 않아 **resume할 때마다 탐험률이 0.2로
되돌아간다**. 100 에피소드 × 재개 가능성을 고려하면 이것도 실질 결함이다.

**Coder 지침.** `spam_d3qn.py`의 `epsilon`, `per_beta`, `total_updates`를
`register_buffer`로 바꿀 것(`res_mapddpg.py:157`, `ma2hdqn.py:129-133`과 동일한 방식).
`carlton.py:159`와 `maddpg_mt.py:147`의 `total_updates`도 같은 이유로 buffer가 맞다.
그리고 "핫스왑을 넘어야 하는 스칼라는 전부 buffer"라는 규칙을 아홉 모델에 대해 검사하는
테스트를 추가할 것 — Act/Rest 두 모델을 만들고 Rest만 N회 update한 뒤 hot_swap 후
Act의 탐험 상태가 따라왔는지 확인하면 된다.

---

## H-3 [HIGH] 용량 파리티가 없고, 기본 3종은 폭을 탐색조차 못 한다

**근거.** 실측 파라미터 수는 10,887(PPO) / 357,643(SAC) / 772,810(TD3) / 301,656 /
148,880 / 68,657 / 87,426(SPAM-D3QN) / 44,624(CARLTON) / 222,748이다. 최소와 최대가
**71배** 차이난다. PPO·SAC·TD3의 폭은 SB3 기본 `net_arch`(각각 [64,64], [256,256],
[400,300])에서 오며, `sample_hparams`의 PPO/SAC/TD3 분기(`hpo.py:139-166`)에는
`hidden_dim`도 `policy_kwargs`도 없어서 **Optuna가 이 격차를 교정할 수단이 없다**.
반면 나머지 여섯은 `hidden_dim ∈ {64,128,256}`을 탐색한다.

**왜 중요한가.** PPO가 꼴찌로 나왔을 때 그것이 on-policy/off-policy 불일치(모듈
docstring이 정직하게 밝힌 근본 한계) 때문인지, 단순히 용량이 10.9k뿐이라서인지를
논문에서 분리할 수 없다. 심사자가 가장 먼저 찌를 지점이다.

**Coder 지침.** 세 SB3 모델에도 `net_arch`를 노출해 `policy_kwargs={"net_arch": [h, h]}`
형태로 `hidden_dim`을 받게 하고, `sample_hparams`의 세 분기에 `hidden_dim`을 추가할 것
(생성자에 `hidden_dim` 인자를 새로 만들어 내부에서 `policy_kwargs`로 옮기면
`assert_hparams_reach_model`도 통과한다). 그렇게 못 한다면 아홉 모델의 파라미터 수를
논문 표에 명시하고 "용량은 각 방법의 원 설정을 따랐다"를 명시적으로 방어할 것.

---

## H-4 [HIGH] Optuna가 탐색하지만 학습에 전혀 쓰이지 않는 하이퍼파라미터

**실측.** 동일 시드·동일 배치로 두 값을 비교해 1회 `update()` 후 가중치가 완전히
같은지 확인했다.

| 모델 | 키 | 비교 | 결과 |
|---|---|---|---|
| MA2HDQN | `n_step` | 1 vs 5 | 가중치 동일 → **무효** |
| I-HAMAPPO | `value_coef` | 0.2 vs 0.8 | 가중치 동일 → **무효** |
| CARLTON | `tau` | 0.001 vs 0.02 | 가중치 동일 → **무효** |
| SPAM-D3QN | `per_alpha` | 0.4 vs 0.8 | 가중치 상이 → 정상 |
| MADDPG-MT | `global_critic_weight` | 0.1 vs 0.9 | 가중치 상이 → 정상 |

원인은 각각 다음과 같다. `ma2hdqn.py:121`의 `self.n_step`은 저장만 되고 어디서도 읽히지
않는다. n-step 경로는 `self.n_step`이 아니라 배치에 `n_step_reward`/`n_step_discount`가
있는지로만 갈리는데(`:329-331`), 파이프라인 버퍼는 그 키를 만들지 않는다.
`i_hamappo.py:117`의 `value_coef`는 크리틱이 별도 옵티마이저를 쓰므로 손실 합성에
들어가지 않고, 오직 반환 dict의 `"loss"` 표시값에만 곱해진다(`:388`).
`carlton.py:157`의 `tau`는 `use_target_network=True`일 때만 쓰이는데(`:360-365`)
기본값이 False이고 `sample_hparams`는 그 스위치를 켜지 않는다(`hpo.py:203-209`).

**왜 중요한가.** 세 값 모두 `optuna_best_params.csv`에 "최적값"으로 실려 논문 6절에
들어간다. C-3과 합치면 아홉 모델 전부의 `gamma`, 그리고 이 세 개가 허수다.
`assert_hparams_reach_model`은 이름이 생성자에 있으므로 전부 통과시킨다.

**Coder 지침.** `n_step`은 실제로 구현하거나(버퍼가 n-step을 만들 수 없으므로 사실상
전자는 불가) `sample_hparams`에서 **제거**할 것. `value_coef`는 액터·크리틱 손실을
하나로 합쳐 단일 역전파로 바꾸거나 제거할 것. `carlton.tau`는 `use_target_network`를
같이 탐색 공간에 넣어(`suggest_categorical("use_target_network", [False, True])`,
`run_all.py:49-51`이 이미 bool 캐스팅을 지원한다) 조건부로 의미 있게 만들거나 제거할 것.
어느 경우든 C-3 지침의 "값이 실제로 효과를 내는지" 테스트를 함께 도입해야 재발이 막힌다.

---

## H-5 [HIGH] HPO trial의 학습량이 200k 스텝용 하이퍼파라미터를 구분할 수 없다

**근거.** `evaluate_trial_multiseed`(`hpo.py:426-434`)는 시드마다 모델을 **새로 만들고**
`train_steps_during_rollout=2`로 350스텝짜리 롤아웃을 돌린다. `evaluate_model_in_env`는
버퍼에 16개가 쌓인 뒤부터만 학습하고(`:364`), 트랜지션은 SMDP 구간이 닫힐 때만
생기므로 이벤트 구동 환경에서 그 수는 많아야 수백 개다. 즉 한 trial의 총
그래디언트 갱신은 대략 수십~수백 회다. 실측된 trial 소요시간도 이를 뒷받침한다:
아홉 모델 27개 trial 전부 1.48~3.89초다.

**왜 중요한가.** 그 시간 규모에서 원리적으로 관측 불가능한 값을 탐색하고 있다.
`SPAM-D3QN.target_update_freq ∈ {200,500,1000}`(`hpo.py:196`)은 trial 동안 타깃
동기화가 **한 번도 일어나지 않을** 수 있고, `MA2HDQN.target_sync_interval`도 같다.
`epsilon_decay ∈ [0.990, 0.9995]`는 수백 스텝으로는 감쇠 차이가 나타나지 않는다.
`tau`도 마찬가지다. 결과적으로 Optuna는 랜덤 초기화의 운을 최적화하고 있고, 거기서 나온
"최적 하이퍼파라미터"로 200,000스텝을 돌리는 것은 근거가 없다.

**Coder 지침.** trial당 학습량을 늘리는 것이 정공법이지만 비용이 크므로, 사용자와
비용/정확도 트레이드오프를 상의할 것. 최소한 (a) 시드마다 모델을 새로 만들지 말고
같은 모델로 시드를 이어 학습해 갱신 횟수를 3배로 만들고, (b) `n_steps`를 350에서
크게 올리거나 `train_steps_during_rollout`을 올리고, (c) trial 동안 실제로 수행된
`update()` 횟수를 `trial.set_user_attr`로 기록해 "탐색 대상이 관측 가능했는가"를
사후에 검증 가능하게 할 것. (c)는 비용이 0이므로 무조건 넣어야 한다.

---

## M-1 [MEDIUM] CARLTON의 `omega` 탐색 범위와 탐험 붕괴 위험

`carlton.py:147`의 기본값은 `omega=10.0`인데 `hpo.py:206`은 `omega ∈ [0.1, 0.9]`를
탐색한다. `omega`는 mellowmax 백업의 연산자 파라미터인 동시에
`select_action`(`:296`)의 Boltzmann 온도로 그대로 재사용된다. `omega`가 작으면
mellowmax는 max가 아니라 **평균**에 가까워지므로 백업이 사실상 균등 무작위 정책의 가치가
되고, 반대로 Q 값의 스케일이 크면 `softmax(omega * q)`가 argmax로 붕괴해 탐험이 완전히
사라진다. CARLTON에는 ε-greedy 대체 경로가 없어서 후자가 발생하면 회복 수단이 없다.
기본값 10.0과 탐색 범위 [0.1,0.9]가 겹치지 않는다는 점도 둘 중 하나가 근거 없이 정해진
값임을 시사한다. **지침**: 백업의 `omega`와 정책 온도 `beta`를 분리된 인자로 두고 둘 다
탐색하거나, 최소한 `update()` 반환 dict에 브랜치별 행동 엔트로피를 남겨 붕괴 여부를
텐서보드에서 확인할 수 있게 할 것. `omega` 범위 [0.1,0.9]의 근거를 문서화할 것.

## M-2 [MEDIUM] 인용 논문의 헤드라인 기여가 실행 경로에서 불활성이다

`maddpg_mt.py:380-392`의 태스크 분해는 배치에 `reward_terms`가 있을 때만 켜지고,
`:394-397`의 글로벌 크리틱은 `others`가 있을 때만 이웃을 본다. 파이프라인의
`push_transition`(`hot_swap_trainer.py:566-574`)은 스칼라 보상 하나만 흘려보내므로
**둘 다 항상 꺼져 있다**. 그러면 네 개 태스크 헤드는 `r/4`의 복사본이 되고 글로벌
크리틱은 로컬 크리틱의 두 번째 사본이 되어, Parvini et al.의 headline 기여(variant 2)가
실행되지 않는다. 같은 이유로 `res_mapddpg.py:326`과 `i_hamappo.py:331`의 중앙집중
크리틱도 이웃 집합이 자기 자신 하나로 퇴화한다. 세 모듈 docstring이 이를 정직하게
명시하고 있다는 점은 인정하지만, 비교 논문에서 "MADDPG-MT과 비교했다"고 쓰려면
이 상태를 반드시 본문에 적어야 한다. **지침**: `env.step`의 `completed` 레코드에
보상 4항을 그대로 실어 보내고 `push_transition`이 `reward_terms`로 버퍼에 넣도록
확장하는 것이 비용 대비 효과가 가장 크다. 보상 4항은 이미 환경이 계산하고 있으므로
배관만 이어붙이면 된다. `others`(동시 재차량 관측 집합)는 비용이 크므로 사용자 결정 사항이다.

## M-3 [MEDIUM] 리더보드 composite의 전력 정규화가 폐기된 범위를 쓴다

`evaluate.py:345`

```python
p_norm = (df_leaderboard_agg["avg_tx_power_dbm"] - 20.0).clip(lower=0.0) / 10.0
```

액션 범위는 [10, 23] dBm인데 이 식은 [20, 30] dBm을 가정한다. 평균 송신전력이 20 dBm
미만인 모델은 전부 `p_norm=0`으로 클립되어 전력 항이 사라지고, 23 dBm인 모델만 0.3을
받는다. 이것은 `Conversation.md` 5절이 결함 (C)로 지목하고 해소했다고 기록한 것과
같은 식이다. 리더보드 순위가 여기서 왜곡된다. **지침**: `hpo.py:517-519`가 이미
`(avg_p - P_MIN)/(P_MAX - P_MIN)`으로 올바르게 계산하므로 그 식을 그대로 쓸 것.
`src.rl_interface`의 `P_MIN`/`P_MAX`를 import해 하드코딩을 없앨 것.

## M-4 [MEDIUM] 휴리스틱이 straw man이 될 위험

`heuristic_scheduler.py` 자체는 straw man이 아니다. TLS 상태·정지선 거리·정지/출발
임박 예측·최소부하 채널 배정을 모두 쓰는 합리적 규칙 기반 참조다. 문제는 벤치마크에서의
호출 방식이다. 첫째, `evaluate.py:163-164`가 `delta_min=0.5, delta_max=10.0`으로
인스턴스화한다. 클래스 기본값은 (0.1, 45.0)이고 설계 승인 범위도 [0.1, 45.0]이다.
그 결과 Rule 2의 `interval = min(self.delta_max, backoff_t)`(`:158`)가 10초에서
잘려, **45초 적색 동안 정차 차량의 갱신을 억제한다는 이 논문의 핵심 시나리오를
휴리스틱만 수행할 수 없다**. 둘째, `evaluate.py:229-241`가 만드는 `st_dict`에
`accel`이 없어 `accel=0.0`으로 고정되고(`:96`), Rule 3의 "완만 가감속"과 "급기동"
분기(`:175-182`)가 절대 발동하지 않는다. 휴리스틱은 사실상 "정지·임박 규칙 + 고정 3.5초"가
된다. **지침**: `instantiate_model`의 두 기본값을 `ActionDecoder`의 `delta_min`/`delta_max`에서
읽어오도록 고치고, `st_dict`에 `accel`을 넣을 것(`extract_tls_features`가 이미
`accel`을 반환하므로 그 값을 쓰면 된다).

## M-5 [MEDIUM] `evaluate.load_optimal_hparams`가 환경 전용 키를 걸러내지 않는다

`evaluate.py:112-125`는 `hparams_json`을 통째로 파싱한 뒤 남은 모든 CSV 열을 병합한다.
`run_all.py:159-164`가 `ENV_ONLY_HPARAM_KEYS`로 걸러내는 것과 달리 필터가 없어서,
현재 CSV의 `w1`, `w2`, `w3`, `w4`, `w1_raw`~`w4_raw`가 모델 생성자로 넘어가
`**hparams`에 조용히 흡수된다. 실질 피해는 없지만 정확히 이전 감사가 지목한 사고
패턴이며, 언젠가 이름이 겹치면 진짜 사고가 된다. 같은 함수 `:125`의
`int_keys = ["hidden_dim", "embed_dim", "policy_freq"]`에서 `policy_freq`는 구세대
이름이다(TD3의 실제 인자는 `policy_delay`). **지침**: `run_all.py`와 동일하게
`ENV_ONLY_HPARAM_KEYS`를 import해 걸러내고, 정수 캐스팅 목록은
`run_all.INT_HPARAM_KEYS`를 재사용해 두 파일이 갈라지지 않게 할 것.

## M-6 [MEDIUM] 조용한 예외 흡수가 그대로 남아 있다

`hpo.py:365-367`

```python
try:
    model.update(batch)
except Exception:
    pass
```

이전 리포트의 결함 4가 미해결이다. 지금은 HPO 경로가 실제로 동작하므로 심각도가
올라간다. 어떤 모델이 배치 계약을 어겨 매번 예외를 던져도 그 trial은 "학습이 전혀
안 된 모델"의 점수를 정상 점수로 보고한다. C-1 같은 결함이 예외 형태로 나타났다면
이 줄이 그것을 삼켰을 것이다. **지침**: 최소한 예외를 카운트해
`trial.set_user_attr("update_failures", n)`으로 남기고, 실패율이 0이 아니면
`logger.warning`을 낼 것. 이상적으로는 첫 실패에서 trial을 실패 처리할 것.

## L-1 [LOW] 사실과 다른 주석

`spam_d3qn.py:122-124`와 `carlton.py:90-91`이 인용하는 `etc/scripts/verify_baselines_similar.py`는
여전히 존재하지 않는다(`etc/scripts/`에는 9개 파일이 있으나 그 이름은 없음). 더 나쁜 것은
`spam_d3qn.py:252-256`, `carlton.py:257-259`, `maddpg_mt.py:254-258`의 docstring이
raw_action을 "logit((delta - d_min)/(d_max - d_min))"로 설명한다는 점이다. C-1에서
확인했듯 `encode_action`은 더 이상 그렇게 인코딩하지 않는다. 주석이 코드보다 먼저
틀렸고, 그 주석 때문에 버그가 눈에 띄지 않았다.

## L-2 [LOW] 두 검증 장치의 사각지대

`etc/scripts/verify_all_baselines.py:46`은 아홉 모델 전부에 대해
`dec.encode_action(delta, ch, power)`로 배치를 만들지만, 복구된 인덱스가 참값과 같은지는
**assert하지 않는다**. `update()`가 가중치를 움직이는지만 본다. C-1이 통과된 이유다.
`tests/test_hpo.py:269-286`의 `test_sampled_values_take_effect_at_runtime`은 취지가 옳으나
PPO와 CARLTON 두 모델의 세 키만 확인하며, 그마저도 "생성자가 값을 저장했는가"를 볼 뿐
"학습이 달라지는가"를 보지 않는다. C-3과 H-4가 통과된 이유다.

## L-3 [LOW] 단일 시드 본훈련

`run_all.py:281`의 `--seed` 기본값이 42 하나다. 9종의 최종 성능 차이가 시드 잡음과
분리되지 않는다. 벤치마크 쪽은 5시드지만 그것은 평가 시드일 뿐 훈련 시드가 아니다.

---

## 모델별 "주장한 기법 vs 구현된 기법"

| 모델 | 논문이 약속하는 기법 | 실제 구현 | 판정 |
|---|---|---|---|
| PPO (Schulman 2017) | on-policy 클리핑 서로게이트, GAE | 클리핑 서로게이트 O. 그러나 behaviour log-prob이 없어 비율의 분모가 update 시작 시점 스냅샷이고, GAE는 λ=0(1-step SMDP TD). 모듈 헤더가 정직하게 명시 | **부분 (문서화됨)**. 용량 10,887로 최소(H-3) |
| SAC (Haarnoja 2018) | 트윈 크리틱, 자동 온도, tanh-가우시안 | SB3 `SAC.train()` 충실 이식. `log_ent_coef`를 `nn.Parameter`로 재등록해 핫스왑까지 처리. γ만 SMDP `discount`로 치환 | **충실**. `target_entropy` 미탐색은 남은 과제 |
| TD3 (Fujimoto 2018) | 타깃정책 스무딩, 클립 더블 Q, 지연 액터 | SB3 `TD3.train()` 충실 이식. 채널 차원 전용 탐색 노이즈(=1 bin 폭)를 별도로 둠 | **충실**. 이산 채널 탐험이 외부 주입임을 헤더가 명시 |
| RES-MAPDDPG (Li 2026) | 잔차 트렁크, 파라미터화 액션(P-DQN류), CTDE | `_ResidualBlock`/`_ResidualTrunk` 실재(`:83-109`). 채널별 파라미터 벡터 + argmax-Q O. 실행된 연속값을 해당 슬롯에 대입하는 크레딧 할당 O. NOMA 단계 폐기(문서화). 중앙집중 크리틱은 이웃 미공급으로 퇴화 | **부분**. 잔차·파라미터화 액션은 진짜, CTDE는 이름뿐(M-2) |
| MA2HDQN (Hong 2026) | MA-D3QN(듀얼링+더블) + i-DDPG 분기, 적응형 lr, n-step | 듀얼링 집계(`:229`) O, 더블 DQN(`:346-348`) O, i-DDPG 타깃 스무딩 O, 적응형 lr O(형태는 저자 재구성, 명시). **n-step은 완전 불활성이며 `n_step` 인자는 죽어 있다(H-4)** | **부분** |
| I-HAMAPPO (Chen 2026) | 하이브리드 Categorical+Gaussian, 중앙집중 크리틱, IEM | 두 갈래 분포와 결합 log-prob O, 스냅샷 대비 클리핑 O. 시맨틱/IEM 절반 미재현(명시). 크리틱은 이웃 미공급으로 퇴화. `value_coef` 무효(H-4) | **부분** |
| SPAM-D3QN (Bai 2024) | 듀얼링 더블 DQN + PER, 완전 이산 결합 헤드 | 구조는 전부 실재하고 배치 내 PER 재가중도 동작(`per_alpha` 실효 확인). 그러나 **Δ 크레딧이 128 중 96에서 잘못 할당된다(C-1)** + Act 모델 ε가 감쇠하지 않는다(H-2) | **불합격 — 수정 전 사용 불가** |
| CARLTON (Cohen 2025) | mellowmax 백업, 타깃망 불필요, CTDE | `mellowmax`(`:111-123`) 정확, 타깃망 미사용 기본값 O, 브랜칭 헤드는 우리측 확장(명시). 그러나 **Δ 브랜치 크레딧이 128 중 96에서 잘못 할당된다(C-1)** + `tau` 무효(H-4) + `omega` 범위 문제(M-1) | **불합격 — 수정 전 사용 불가** |
| MADDPG-MT (Parvini 2023) | 이중 크리틱(local+global), 태스크 분해, DDPG | 구조는 4-헤드 크리틱 2개로 정확히 구현. Gumbel-Softmax straight-through로 이산 채널에 그래디언트 O. 그러나 **태스크 분해와 글로벌 크리틱이 둘 다 불활성(M-2)** + 크리틱에 들어가는 `u_delta`가 왜곡된다(C-1) | **불합격 — 수정 전 사용 불가** |
| HeuristicScheduler | 규칙 기반 참조 | 클래스 자체는 합리적(TLS·정지선·임박예측·최소부하 채널). 그러나 벤치마크 호출 시 Δ가 10초로 잘리고 `accel`이 전달되지 않아 규칙 절반이 죽는다(M-4) | **부분 — straw man 위험** |

하이브리드 액션 요구사항 자체는 아홉 모델 전부 충족한다. 연속 Δ와 연속 전력, 이산
서브채널을 모두 내보내며, 이산 헤드로 그래디언트가 흐르는 경로도 각각 존재한다
(P-DQN의 argmax-Q, D3QN의 gather, Categorical의 log_prob, Box 차원 2의 가우시안
log_prob, Gumbel-Softmax straight-through, 브랜치 gather). `**hparams` 흡수 문제는
이름 층에서는 `assert_hparams_reach_model`이 아홉 모델 전부를 막아준다(테스트 20개
통과 실측). 문제는 이름이 아니라 값의 효과 층이며 그것이 C-3과 H-4다.

---

## 데이터 누수 검토 결과

의도적 누수는 발견하지 못했다. `base_agent.BaseRLModel`이 모든 모델에 공통으로 주는
것은 `state_dim`, `num_channels`, `ActionDecoder`뿐이며(`base_agent.py:46-51`), 어떤
모델도 환경 내부 상태나 다른 차량의 실제 미래를 읽지 않는다. 오히려 반대 방향의 문제,
즉 중앙집중 크리틱이 이웃 정보를 **못 받는** 쪽이 문제다(M-2). `evaluate_single_run`은
아홉 모델 전부를 `deterministic=True`로 호출하고 휴리스틱과 동일한 환경·동일 보상
가중치(`DEFAULT_REWARD_WEIGHTS`)로 평가하므로 평가 조건 자체는 대칭이다.
`hpo.py`의 `evaluate_model_in_env`가 학습과 평가를 같은 롤아웃에서 수행하는 것은
"학습 중 성능"을 목적함수로 삼는 설계 선택이며 누수는 아니지만, H-5에서 지적한 대로
그 목적함수가 사실상 초기화 운을 측정한다.

`RetrospectiveReplayBuffer`는 모델별로 별도 인스턴스이고 `push_transition`은
`raw_action`을 모델이 내놓은 그대로 저장하므로, 모델 간 표현이 섞이는 경로도 없다.
`SB3BaselineModel.unpack_batch`(`sb3_wrapper.py:386-391`)가 3차원이 아닌 액션을
거부하는 것도 좋은 방어다.

---

## 질문

1. **C-3의 방향 결정이 필요합니다.** `gamma`를 모델별 탐색 대상으로 살릴 것인지
   (버퍼를 모델 gamma로 생성), 아니면 벤치마크 상수로 못 박고 탐색 공간에서 뺄
   것인지는 결과를 바꾸는 결정입니다. 후자가 SMDP 설정에서는 더 방어하기 쉽다고
   보지만, 임의로 정하지 않고 여쭙습니다.

2. **C-4의 재실행 범위.** `results/hpo/`를 전부 폐기하고 `tune_reward_weights=False`,
   `--n-trials 15` 이상으로 재실행하는 것이 맞습니까? 아니면 보상 가중치 탐색은
   별도의 ablation study로 남기고 본 비교표용 HPO만 따로 돌립니까? 후자라면 어느
   쪽 결과를 `Conversation.md` 6절에 채웁니까?

3. **M-2의 배관 확장 승인.** 환경이 이미 계산하고 있는 보상 4항을 `push_transition`을
   통해 `reward_terms`로 버퍼에 실어 보내면 MADDPG-MT의 태스크 분해가 실제로 켜집니다.
   이는 버퍼 스키마 변경이라 아홉 모델 전부의 배치 계약에 영향을 주므로, 진행 여부를
   확인받아야 합니다. 켜지 않으면 논문에 "task decomposition은 비활성 상태로
   비교했다"를 명시해야 합니다.

4. **H-1의 예산 동일화 정책.** 그래디언트 갱신 횟수를 환경 스텝에 비례하도록
   상한을 걸면 훈련 시간이 늘어날 수 있습니다(느린 모델에 맞춰지는 것이 아니라 빠른
   모델이 대기). 8.8시간 추정치가 늘어나는 것을 감수합니까, 아니면 갱신 횟수를
   기록만 하고 논문에 공개하는 선에서 끝냅니까?

5. **`res_MAPDDPG`의 "res-" 해석.** 모듈 docstring(`res_mapddpg.py:64-68`)이
   "residual(잔차 MLP)"과 "resource-efficient(자원효율 정규화)" 두 해석 사이에서
   전자를 택했다고 스스로 flagging하고 있습니다. 원문 확인이 가능하다면
   librarian에게 확인을 요청해야 할 항목으로 남깁니다.

6. **CARLTON `omega` 범위 [0.1, 0.9]의 출처.** 기본값 10.0과 겹치지 않습니다.
   근거가 있는 값입니까, 아니면 다른 모델의 [0,1] 계열 파라미터를 따라 쓴 값입니까?

---

## 부록: 실측 로그

```bash
/home/imnyj/venv/bin/python -m pytest tests/test_hpo.py -q      # 20 passed
# 인메모리 검증(파일 생성 없음, SUMO 미기동):
#  (1) 9종 파라미터 수 + 배치 키 + gamma 무효성  -> C-3 표
#  (2) encode_action 왕복 128개 전수 검사        -> C-1 표 (SPAM 96/128, CARLTON 96/128)
#  (3) 하이퍼파라미터 값 변경 전후 state_dict 비교 -> H-4 표
#  (4) named_buffers() 열거                      -> H-2 표
# 정적 확인:
#  grep -rn "TODO|FIXME|pass$" src/baselines/ -> 0건 (except 절 4곳은 전부 정상 용도)
#  grep -n "load_state_dict|checkpoints/" src/evaluate.py -> 0건 (C-2 근거)
#  ls etc/scripts/ -> verify_baselines_similar.py 부재 (L-1 근거)
#  wc -l results/hpo/optuna_trials_*.csv -> 전부 4행 = 모델당 3 trial (C-4 근거)
```

`checkpoints/`는 검토 시작 시점과 동일하게 비어 있다. `results/`, `logs/`에 쓰기 없음.
