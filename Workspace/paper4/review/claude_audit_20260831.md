# Claude Code 독립 검증 보고 (2026-08-31)

검증 대상: (1) Antigravity가 `review/antigravity_update_20260830.md`에 보고한 작업, (2) 파이프라인 전체.
방식: Antigravity 작업은 내가 직접 검토·수정했고, 전체 코드는 critic 에이전트 4종을 `.rules/critic.md`
규칙 아래 병렬로 운용해 검증했다. critic은 코드를 수정하지 않고 리포트만 남겼으며, 각 리포트의 최상위
주장은 내가 다시 직접 재현해 확인했다.

**판정: 본훈련 착수 불가.** 오늘 고친 결함과 무관하게, 하류 경로가 끊겨 있다. 지금 20만 스텝을 4장의
GPU로 돌려 체크포인트를 만들어도 `src/evaluate.py`가 그것을 읽지 않으므로 논문 표에는 학습되지 않은
난수 가중치의 성능이 들어간다. 이 한 가지만으로 기동 승인을 낼 수 없다.

---

## 1부 — Antigravity 작업 검토

### 보고 내용과 코드가 일치하는 부분

메모리 누수 방지는 보고대로 반영되어 있다. `hot_swap_trainer.py:27`의 `import gc`, `:1782`의 `close()`,
에피소드 종료 지점의 `del env` + `gc.collect()`, 그리고 `evaluate.py:254-256`과 `hpo.py:390-392`의
동일 패턴을 모두 확인했다. `--hparams-csv` 인자와 로딩 파이프라인도 실제로 추가되어 있다. 다만
`run_hot_swap_training`은 원래부터 `hparams` 인자를 받고 있었으므로(`hot_swap_trainer.py:1810`)
새로 만든 것은 CSV를 읽어 그 인자를 채우는 부분이다.

인수인계 사항 1번(18차원 구형 체크포인트 정리 필요)은 이미 해소된 상태였다. 당시 `checkpoints/*.pt`를
열어보니 전부 17차원(`trunk.0.weight (64, 17)`)이었다.

### 발견한 결함과 처리

Antigravity가 "치명적 누락을 해결했다"고 보고한 HPO 반영은 **절반만 달성되어 있었다.** 보상 가중치
`w1~w4`는 `AoiV2IEnv.__init__`의 인자인데, CSV에서 읽힌 이 값들이 모델 생성자로 흘러갔다. 아홉 개
베이스라인 생성자가 모두 `**hparams`로 끝나므로 조용히 삼켜졌고, 정작 환경은 언제나 기본값
0.5/0.2/0.2/0.1로 훈련되었다. 증거는 `checkpoints/CARLTON_best.pt`에 저장된 hparams에 `'w1': 0.523336`이
그대로 들어 있었다는 것이다. 보상 가중치가 모델의 체크포인트 안에 앉아 있었다. 크래시가 나지 않기
때문에 신규 테스트 25개가 전부 통과했음에도 결함이 남았다.

| ID | 결함 | 처리 |
|---|---|---|
| F1 | `w1~w4`가 환경 대신 모델 생성자로 유입, HPO 반영의 핵심 실패 | 수정 완료 |
| F2 | 중복 행 dedup이 최고값을 선택. Optuna는 `direction="minimize"` | 수정 완료 |
| F3 | 통합 테스트가 production `checkpoints/`를 오염, `resume=True`가 기본 | 수정 완료 |
| F4 | 컬럼 폴백이 `w*` 8개 키를 모든 모델에 주입 | 수정 완료 |
| F5 | 별칭 키 중복 등록으로 로그의 모델 수가 부풀려짐 | 수정 완료 |
| F6 | `normalize_model_name` 딕셔너리 매 호출 재구축, `pd.isna` 컨테이너 예외 | 수정 완료 |

적용한 수정은 다음과 같다. `hot_swap_trainer.py`에 `DEFAULT_REWARD_WEIGHTS`, `ENV_ONLY_HPARAM_KEYS`,
`split_env_hparams()`를 신설해 훈련·평가·HPO가 하나의 상수를 읽게 했다. `HotSwapTrainer`는 모델에
넘기기 전 환경 전용 키를 걸러내고 경고를 남긴다. `run_hot_swap_training`은 가중치를 `AoiV2IEnv`에
명시적으로 전달한다. `hpo.py`는 `w1~w4` 튜닝을 `--tune-reward-weights` 옵트인으로 내렸고 `--n-steps`
기본값을 35에서 350으로 올렸다. `run_all.py`는 dedup 방향을 뒤집고 `--checkpoint-dir` / `--tensorboard-dir`을
받는다.

런타임으로 확인했다. `w1~w4`가 담긴 hparams로 훈련을 시작하면 `PPO: dropped environment-only key(s)
['w1','w2','w3','w4']` 경고가 뜨고 환경은 `{'w1': 0.5, 'w2': 0.2, 'w3': 0.2, 'w4': 0.1}`을 받는다.

테스트는 144개 전체가 통과한다. 회귀 테스트 9개(`test_26`~`test_34`)를 새로 넣었다. 기존 `test_14`와
`test_15`는 결함을 명세로 굳혀둔 것이어서 올바른 계약으로 다시 썼다. F3는 `test_run_all.py` 외에
`test_hot_swap.py::test_run_hot_swap_training_end_to_end`도 원인이었는데, 파일명이 같아 목록 비교로는
잡히지 않아 mtime으로 찾았다. 스모크 체크포인트 17개는 `backup/preflight_ckpt_20260831_103136/`으로,
폐기된 베이스라인의 stale HPO CSV 9개는 `backup/stale_hpo_.../`로 옮겼다.

### 사용자 결정 사항

보상 가중치는 전 모델 공통 고정으로 정했다. 짚어둘 점은 Optuna의 목적함수
`compute_composite_objective`가 `w_error=1.0, w_aoi=0.5, w_outage=2.0, w_power=0.2`로 고정되어 있고
샘플링된 `w1~w4`와 무관하다는 것이다. 즉 `w1~w4`는 고정된 평가 지표에 대해 튜닝된 reward shaping이라
그 자체로는 방어 가능한 설계였다. 공통 고정을 택했으므로 함께 선택된 모델 하이퍼파라미터는 "다른 보상
아래에서 고른 값"이 되어 짝이 맞지 않고, 따라서 HPO 재실행이 필요하다.

---

## 2부 — critic 4종 검증 결과

critic-core는 API 한도로 첫 시도가 중단되어 재실행 중이다. 아래는 완료된 세 축의 결과이며, 각 축의
최상위 주장은 내가 직접 재현했다.

| 축 | 판정 | 리포트 |
|---|---|---|
| critic-pipeline | REJECT | `critic/critic_pipeline.md` |
| critic-baselines | REJECT | `critic/critic_baselines.md` |
| critic-physics | CONDITIONAL | `critic/critic_physics.md` |
| critic-core | 재실행 중 | `critic/critic_core.md` |

### 내가 직접 재현해 확인한 CRITICAL 4건

**A. `src/evaluate.py`가 학습된 체크포인트를 전혀 읽지 않는다.** 파일 전체에 `torch.load`도
`state_dict`도 `checkpoint`도 `.pt`도 없다(grep 0건). `instantiate_model`(`evaluate.py:138`)은 새
모델을 무작위 초기화해 그대로 평가한다. 이것이 본훈련을 막는 단 하나의 결정적 이유다. 훈련 자체는
돌려도 손해에 그치지만, 이 상태로 평가까지 진행하면 논문 표 전체가 난수 가중치의 성능이 된다.

**B. HPO 목적함수가 "아무것도 측정되지 않은 실행"을 전역 최소값으로 평가한다.**
`compute_composite_objective({'mean_error':0,'mean_aoi':0,'outage_rate':0,'avg_power_norm':0})`을
실행하면 **0.0**이 나온다. 정상 trial은 0.887~1.459 범위다. `direction="minimize"`이므로 환경이
죽거나 차량이 RSU 범위에 들지 못한 조합이 언제나 "최적"으로 뽑힌다.

여기서 critic-pipeline의 서술을 한 가지 정정한다. 리포트는 이 실패 모드가 "이미 일어났을 가능성이
높다"고 적었으나, 커밋된 27개 trial의 값을 전수 확인한 결과 최솟값이 0.887이고 0.01 이하는 하나도
없다. **아직 발동하지 않았다.** 다만 trial 수를 15로 늘려 재실행하면 발동 확률이 올라가므로 방어선을
먼저 넣어야 한다.

**C. `gamma`가 아홉 모델 전부에서 무효다.** `RetrospectiveReplayBuffer`가 자기 자신의
`gamma=0.99`로 `discount`를 계산해 배치에 넣고(`rl_interface.py:725`), 모든 베이스라인의
`update()`가 `if "discount" in batch:`로 그 값을 우선 사용한다(예: `carlton.py:321-322`,
`spam_d3qn.py:321-322`). `self.gamma`를 쓰는 `else` 분기는 도달하지 않는다. 버퍼는
`hot_swap_trainer.py:680`에서 `gamma` 없이 생성되므로 항상 0.99다. HPO가 `gamma`를 탐색해 CSV에
기록한 값이 학습에 아무 영향을 주지 못한다.

**D. `ActionDecoder`의 Δ 매핑이 기하인데 세 베이스라인이 선형으로 역변환한다.** 디코더의 정방향은
`delta_min * exp(u * log_ratio)`(`rl_interface.py:570`)로 기하인데, `spam_d3qn.py:268`은
`delta_min + sigmoid(raw) * (delta_max - delta_min)`으로 선형 복원한다. 같은 함수의 docstring이
"sigmoid()가 각 연속 필드를 정확히 역변환한다"고 적고 있으나 사실이 아니다. 복원된 Δ가 틀리므로
argmin 스냅이 엉뚱한 그리드 슬롯을 고른다. critic-baselines의 전수 검사로는 SPAM-D3QN과 CARLTON이
128개 인덱스 중 96개를 잘못 복구한다.

### 그 밖의 주요 지적

**내 수정의 미완결 (critic-pipeline C3, critic-baselines M-5).** `evaluate.py`에는
`load_optimal_hparams`라는 **별도의 CSV 로더**가 있고(`evaluate.py:93`), 그 무시 목록
(`:118`)은 `model_name`, `category`, `best_value`, `best_trial_number`, `hparams_json`뿐이라
`w1~w4`를 여전히 모델 생성자로 흘려보낸다. 오늘 내가 고친 것은 `run_all.py` 경로뿐이었다. 확인했고,
사실이다. 수정 대상에 포함해야 한다.

**물리 계층의 한 스텝 지연 (critic-physics L1, CRITICAL).** 전송 성공 시 RSU 장부를 갱신하는
`hot_swap_trainer.py:1651-1655`가 `simulationStep()` 이전에 읽은 위치(`item["pos"]`)를 스텝 이후의
시각(`self.sim_time`)과 짝지어 저장한다. 같은 파일의 `_register_vehicle:1267`은
`self.sim_time - self.step_length`라는 올바른 관례를 이미 쓰고 있다. 두 곳의 관례가 다르다는 것이
의도가 아니라 누락임을 보여준다. critic의 실측으로는 Δ=0.1 s 전량 전송 시 `mean_error` 0.8153 m 중
0.810 m가 이 지연에서 온다. 논문의 대표 지표에 속도 비례 바닥값이 깔린다.

**공정성 결함 두 건.** HeuristicScheduler만 Δ 범위가 RL 베이스라인의 약 1/4.5인 다른 행동 공간에서
평가된다(critic-pipeline H1). 그리고 그래디언트 갱신 예산이 벽시계 경쟁으로 정해져 모델마다 다른
학습량을 받는다(critic-baselines H-1). 둘 다 비교 논문에서는 치명적이다.

**테스트 스위트의 신뢰성 (critic-pipeline H7).** 144개 중 상당수가 `tests/contract_adapters.py`의
그림자 구현을 검증하고 있어, 위 결함들이 전부 통과된 채 오늘까지 온 이유를 설명한다. 내가 1부에서
지적한 `test_08`/`test_21`/`test_22`가 같은 계열이다. 이들은 테스트 안에서 `argparse.ArgumentParser`를
직접 만들어 검증하므로 `run_all.py`를 지워도 통과한다.

**HPO 결과의 대표성 (critic-baselines C-4, critic-pipeline M1/M2).** 커밋된 CSV는 3-trial × 35-step
스모크 산출물이고, 아홉 개의 서로 다른 보상 함수 아래에서 선택되었다. 교차 비교의 근거가 될 수 없다.
코드 주석(`hpo.py:642-644`)이 스스로 "35 step은 어떤 차량도 RSU 원반에 도달하지 못한다"고 적고 있다.

### 부수 사항

critic-physics가 진단을 위해 SUMO를 구동해 `src/sumo/generated.*.xml`과 `.sumo_gen_signature.json`이
재생성되었다. 서명이 어차피 불일치 상태(MAX_STEPS 490 < 본훈련 요구 2450)라 다음 실행에서 자동
재생성되므로 무해하다고 판단했다. 고정 파일셋을 유지해야 할 사정이 있으면 알려주기 바란다.

`evaluate.py`의 ruff 오류 5건(F821 `env`)은 내 수정 이전부터 있었다. Antigravity가 넣은 `del env`가
원인인데, `env`는 한 줄 뒤 함수 종료로 어차피 해제되므로 실효가 없고 ruff만 깨뜨린다. 실제 효과를
내는 것은 `gc.collect()` 쪽이다.

---

## 3부 — 본훈련 전 수정 순서

critic 셋이 공통으로 지목한 순서를 따른다. 위 A와 B, 그리고 D를 고치기 전에는 HPO 재실행도 무의미하다.

1. **A (체크포인트 미로드)** — `evaluate.py`에 체크포인트 로딩 경로를 만든다. 이것 없이는 본훈련
   자체가 성립하지 않는다.
2. **B (빈 실행 방어)** — `evaluate_model_in_env`가 `n_observations` 또는 `tx_attempts`가 0이면
   실패 페널티를 반환하게 한다. `get_metrics`는 이미 `n_observations`를 계산해 반환하는데
   (`hot_swap_trainer.py:1834`) HPO가 읽지 않는다.
3. **D (Δ 역변환)** — `spam_d3qn.py`, `carlton.py`, `maddpg_mt.py`의 선형 복원을
   `decoder.unit_from_delta` 경유로 통일한다.
4. **C (gamma 무효)** — 버퍼가 모델의 `gamma`를 쓰도록 배선하거나, 모델이 배치의 `discount`를
   무시하고 자기 `gamma`로 재계산하게 한다. 어느 쪽이든 단일 출처로 만들어야 한다.
5. **내 수정의 미완결** — `evaluate.py::load_optimal_hparams`가 `ENV_ONLY_HPARAM_KEYS`를 쓰도록
   고친다. 아울러 critic이 제안한 대로 무시 목록(블랙리스트) 대신 생성자 시그니처 기반
   화이트리스트로 뒤집는 편이 안전한지 검토한다. `density`, `warmup_steps`, `rsu_range`도 환경
   인자라 CSV에 열이 생기면 같은 방식으로 새어 들어간다.
6. **물리 L1 (한 스텝 지연)** — 장부의 `(pos, vel, t_update)` 삼중항을 같은 시각으로 맞춘다.
   회귀 기준은 Δ=0.1 s 전량 전송에서 `mean_error`가 1 m대에서 0.01 m대로 떨어지는지다.
7. **공정성 두 건** — HeuristicScheduler의 Δ 범위 일치, 갱신 예산의 결정론화.
8. **HPO 재실행** — 위가 끝난 뒤 `--n-trials 15 --n-steps 350`으로 한 번만 돌린다. 측정 결과
   trial당 약 81초이므로 9모델 × 15 trial이면 약 3시간이다. 지금 돌리면 버리게 되므로 보류했다.
9. **테스트 재작성** — `contract_adapters.py` 그림자 구현에 의존하는 테스트들을 실제 구현 검증으로
   바꾼다. critic-pipeline의 의견대로 훈련이 도는 동안 병행하는 것이 시간을 가장 아낀다.

---

## 사용자 확인이 필요한 사항

각 critic 리포트의 "질문" 절에 상세가 있다. 결정이 필요한 것만 모으면 다음과 같다.

첫째, outage의 정의다. SINR이 임계값 미만인 사건의 비율인지, 재시도를 소진해 갱신이 전달되지 못한
비율인지, 차량이 커버리지 밖에 있는 시간 비율인지 `Conversation.md`와 `simulation_plan.md` 어디에도
명시가 없다. 세 정의가 모두 문헌에 존재하고 값이 크게 다르다.

둘째, 훈련 밀도다. 현재 `density=25.0` 고정으로 학습하고 평가는 15~55에서 한다. 의도된 일반화
실험이면 논문에 "단일 밀도 학습, 다중 밀도 평가"임을 명시해야 하고, 아니라면 `run_all.py`에
`--density` 인자가 필요하다.

셋째, 훈련 시드다. 현재 42 하나뿐이다. 3회 반복이면 약 7.3시간인데, 단일 시드로 갈 경우 원고에
그 사실과 이유를 명시해야 한다.

넷째, seed가 무엇을 랜덤화하는지다. 현재 도로망 생성 서명에 seed가 없어 같은 밀도면 모든 seed가
같은 도로망을 쓰고 seed는 SUMO 교통 난수만 바꾼다.

다섯째, `tests/contract_adapters.py`의 fallback 구현을 삭제할 권한이 coder에게 있는지다. 삭제하면
약 12개 테스트가 즉시 실패하고 재작성이 필요하다.
