# coder 수정 기록 — 2026-08-31 (본훈련 진입 차단 결함)

담당 파일: `src/hot_swap_trainer.py`, `src/rl_interface.py`, `src/sumo/make_sumo_set.py`,
`src/dynamics_predictor.py`, `src/Communications.py` (+ 테스트)

## 실측 근거 (전부 실제 SUMO 구동)

### 물리 L1 — 장부 한 스텝 지연
Δ=0.1 s 전량 전송, density 25, 600스텝:

| | 수정 전(critic 실측) | 수정 후(내 실측) |
|---|---|---|
| mean_error | 0.8153 m | **0.0449 m** |
| 평균 속도 | 8.099 m/s | 6.905 m/s |
| v·step_length 바닥값 | 0.810 m (측정/예측 비 1.007) | 0.690 m (측정치는 그 6.5 %) |

### L5 / L2 — 보상 네 항의 실효 척도 (526 구간, 랜덤 정책)
가중 후 평균 기여도:

| 항 | 평균 | 최대 | 평균 페널티 중 비중 |
|---|---|---|---|
| w1·r_err | 0.678863 | 19.176 | **82.1 %** |
| w2·Norm(P_tx) | 0.080583 | 0.200 | 9.7 % |
| w4·I_redundant | 0.066160 | 0.100 | 8.0 % |
| w3·Norm(C_freq) | 0.000898 | 0.0027 | **0.11 %** |

가중 전 원시 범위: `r_err` [0, 38.35], `r_power` [0, 1.0], `cbr` [0, 0.0134], `i_redundant` {0,1}.
서브채널 CBR 평균 0.000885 / 최대 0.01344 / 고유값 4개.

### C2 — 집계 단위에 따른 순위 역전 (같은 데이터)

| Δ 구간 | n | 구간당 평균 | 초당 |
|---|---|---|---|
| [0.1, 0.5) | 117 | −0.1945 | **−0.7340** (최악) |
| [0.5, 2) | 147 | −0.1744 | −0.1697 |
| [2, 10) | 155 | −0.3121 | **−0.0635** (최선) |
| [10, 45.1) | 107 | **−3.1587** (최악) | −0.1549 |
| 전체 | 526 | −0.8265 | −0.1391 |

구간당 평균은 짧은 Δ를 최선, 긴 Δ를 16배 최악으로 매기고 시간당 비율은 그 순서를 뒤집는다.

### L4 — 재현성
같은 seed로 캐시 미스(재생성)와 캐시 히트를 각각 돌린 결과가 완전히 동일:
`mean_error 3.3891 / mean_aoi 3.9963 / packet_loss 0.1176 / tx_attempts 68 / tx_fails 8 /
coverage_outage_rate 0.422589` 양쪽 일치. 전역 `random` 스트림도 생성 여부와 무관해졌다.

### 커버리지 아웃티지
`coverage_outage_rate` 실측 0.35~0.42. 시나리오 기하 기대값 OUTAGE_ZONE/EDGE_LENGTH = 300/900 = 0.333.

## 산출 CSV
- `results/diagnostics/reward_term_scales_20260831.csv` (구간별 원시 기록)
- `results/diagnostics/reward_term_summary_20260831.csv` (항별 평균/최대/비중)
- `results/diagnostics/reward_by_delta_bucket_20260831.csv` (C2 근거)

## 테스트
전체 `pytest -q`: 수정 전 144 passed → 수정 후 **298 passed, 0 failed**.
(증가분은 나의 신규 59건과 다른 두 에이전트의 신규분이 섞여 있다.)
프로덕션 트리 오염: `logs/training`, `checkpoints`, `results`의 파일 내용 해시가 스위트 실행 전후로 동일.

## 추가 실측 (2026-09-01)

### 밀도별 그래디언트 예산 (baselines 담당 요청, 300스텝 고정)

| density | grad updates | swaps | 닫힌 구간 | 결정 수 | r/s | coverage_outage | n_obs |
|---|---|---|---|---|---|---|---|
| 5 | **2** | 0 | 88 | 89 | −0.0657 | 0.2773 | 3,315 |
| 25 | 27 | 1 | 316 | 316 | −0.1067 | 0.3495 | 11,741 |
| 50 | 36 | 1 | 414 | 415 | −0.1395 | 0.3372 | 15,555 |

밀도 5에서 300스텝당 그래디언트 갱신이 2회다(밀도 50 대비 18배 차이). 조용한 `None` 반환은
`is_ready(batch_size=32)` 게이트와 벽시계 경쟁이 겹친 결과다. 리플레이 버퍼는 에피소드마다
재생성되지 않고 `HotSwapTrainer` 수명 동안 유지되므로 20만 스텝 전체로는 버퍼가 찬다.

**초판의 해석 정정(baselines 담당 지적, 타당):** 밀도는 런 단위가 아니라 에피소드 단위로 순환하고
(`ep_density = density_schedule[ep % len]`) 모델·버퍼·탐험 스케줄은 하나로 공유된다. 따라서
"밀도 스윕이 교락됐다"는 표현은 틀렸다 — 논문 표의 밀도 스윕은 `evaluate.py`의 별도 벤치마크이고
`deterministic=True`에 학습이 없다. 실제로 남는 피해는 **훈련 데이터 혼합과 그 위의 갱신이 고밀도
쪽으로 기울어(닫힌 구간 88 대 414 ≈ 4.7배, 갱신 2 대 36 ≈ 18배) 학습된 정책이 저밀도 영역을
과소적합한다**는 것이다. 논문에서 방어할 문장은 "훈련 데이터 혼합이 밀도에 비례해 기울어 있다"다.

계측은 넣었다. `episodic_records`에 `grad_updates_this_episode` / `grad_updates_total`,
반환 요약에 `grad_updates_by_density`와 `zero_update_episodes`. 갱신 0회 에피소드는 warning을 남긴다.
비율 상한(H-1) 자체는 실행 시간 트레이드오프가 있어 착수하지 않고 질의로 올렸다.

### TensorBoard 부재
`from torch.utils.tensorboard import SummaryWriter` → `ModuleNotFoundError: No module named 'tensorboard'`.
`tensorboard` 패키지가 venv에 설치되어 있지 않아 `SummaryWriter is None`이고, 지금까지 모든 훈련이
로그 없이 끝났다. 종전에는 `except Exception: writer = None`으로 조용히 삼켜졌고, 이번에 추가한
`logging.error`가 드러냈다. `Conversation.md` 5절의 재통과 조건이 "텐서보드를 통한 5만 step 부근
수렴 확인"이므로 현 상태로는 그 조건을 충족할 수 없다. 설치는 환경 변경이라 착수하지 않았다.

## 백업 체크포인트 10개의 사용 불가 원인 (2026-09-01, 실측으로 원인 분리)

`backup/checkpoints_presmoke_20260828_155837/*_best.pt` 10개 전부의 저장된 입력 폭을 직접 읽었다.

```
현재 STATE_DIM = 17
CARLTON     trunk.0.weight(128, 18)      IHAMAPPO   actor_trunk.0.weight(128, 18)
MADDPGMT    actor.0.weight(128, 18)      RESMAPDDPG param_actor.inp.weight(128, 18)
SPAMD3QN    trunk.0.weight(128, 18)      MA2HDQN    q_trunk.0.weight(128, 18)
PPO         policy...policy_net.0.weight(64, 18)    SAC/TD3/HybridPPO 동일하게 18
전부 stored_state_dim = None (state_dim 기록 필드 도입 이전 산출물)
```

**10개 전부 입력 폭이 18이다.** 즉 `stop/start_imminent` 피처를 제거한 설계 결정 D4(18→17,
08-29)로 이미 전량 사용 불가 상태였고, 이는 baselines 담당의 어떤 변경보다도 앞선다.
`Missing key(s): total_updates / epsilon / per_beta`는 그 위에 **추가로** 얹힌 두 번째 사유이며
CARLTON·MADDPGMT·SPAMD3QN 3개에만 해당한다(H-2 수정으로 탐험 스칼라가 `register_buffer`가 되면서
state_dict 키가 늘어난 것 — 의도된 변경이고 그 키의 부재가 곧 H-2 결함이었다).

결론: 이 10개는 폐기 대상이고 회귀 기준으로 삼을 수 없다. `checkpoints/`는 비어 있으므로 현재
실행 경로에는 영향이 없다. 초판 보고에서 "6개 전부 로드 실패"라고만 적고 원인을 나누지 않은 것을
이 절로 정정한다.

## 체크포인트 스냅샷 원자성 (2026-09-01, 신규 발견)

`save_checkpoint`가 `act_model.state_dict()`와 `rest_model.state_dict()`를 **락 없이** 읽고 있었다.
백그라운드 스레드는 `update()`로 Rest 가중치를 계속 바꾸고 `hot_swap()`으로 Rest→Act를 파라미터
하나씩 복사하는데, 그 사이에 저장이 끼면 **찢어진(torn) 스냅샷** — 일부 텐서는 이전 정책, 일부는
새 정책 — 이 파일에 들어간다. 그런 체크포인트는 **한 번도 실행된 적 없는 정책**이고, 그 옆에
기록된 `best_reward`를 벌어들인 적도 없다.

`{model}_best.pt`가 논문 숫자의 출처이고 `evaluate.py`가 `act_state_dict`를 우선하는 근거가
"Act이 보고된 보상을 만든 검증된 사본"이라는 것이므로, 찢어진 스냅샷은 그 전제를 조용히 무효화한다.

수정: `BackgroundTrainer`에 `update_lock`을 두어 `rest_model.update()`를 감싸고,
`save_checkpoint`가 `update_lock` → `swap_lock` 순으로 잡은 뒤 텐서를 CPU로 clone해 스냅샷한다.
직렬화는 임계 구역 밖에서 하므로 트레이너는 복사 시간만 멈춘다. `train_step`은 `update_lock`을
놓은 뒤에야 `hot_swap`(=`swap_lock`)에 도달하므로 락 순서 역전이 없다.

검증: `TestCheckpointSnapshotIsAtomic`. 실제 `BackgroundTrainer` 워커를 돌리면서 40회 저장하고,
모든 파라미터가 항상 같은 스칼라라는 불변식으로 혼합을 탐지한다. **락을 제거하면 실제로 실패한다**
(`act_state_dict [2.0, 3.0]`, `rest_state_dict [31.0, 32.0]`). 탐지기가 눈먼 것이 아님을 보이는
테스트와, 스냅샷이 라이브 텐서를 alias하지 않는지 확인하는 테스트를 함께 넣었다.

## NaN 안전 가드가 건전하지 않았다 (2026-09-01, 신규 발견)

`DualModelHotSwapManager.hot_swap()`이 `validate_weights()`를 **아무 락 없이** 실행한 뒤에야
`swap_lock`을 잡고 복사했다. 그 사이에 그래디언트 스텝이 들어오면, 가드가 이미 "깨끗하다"고
판정한 **뒤에** Rest에 NaN이 쓰이고 그 NaN이 그대로 Act로 복사된다. `failed_swaps`는 0으로
남으므로 M7의 중단 로직도 발화하지 않고, 오염된 서빙 정책 위에서 실행이 계속된다.
`validate_weights` 자체도 절반만 쓰인 텐서를 읽어 존재한 적 없는 값에 대해 통과할 수 있었다.

수정: `update_lock`(`BackgroundTrainer.train_step`이 `rest_model.update()` 동안 잡는 락)을
`hot_swap()`이 검증+복사 전체에 대해 잡는다. 락 순서는 어디서나 `update_lock` → `swap_lock`이고
(`hot_swap`, `save_checkpoint` 동일), `train_step`은 `update_lock`을 놓은 뒤에야 `hot_swap`에
도달하므로 역전이 없다. 락은 `HotSwapTrainer`가 하나 만들어 매니저와 백그라운드 트레이너에
함께 넘긴다.

### 테스트 방법론 주의 (기록해 둘 가치가 있음)
처음에 쓴 동시성 테스트 2건은 **락을 제거해도 통과했다.** GIL과 짧은 update 창 때문에 문제의
인터리빙이 사실상 샘플링되지 않는다. 스레드를 그냥 경쟁시키는 테스트는 결함 유무와 무관하게
통과하므로 아무것도 증명하지 못한다. 그래서 `threading.Event`로 인터리빙을 **강제**하도록
다시 썼다 — 가드가 깨끗한 모델을 보고 판정한 직후 writer가 NaN을 쓰고, 그 상태에서 복사가
일어나게 만든다. 이제 락을 빼면 결정론적으로 실패한다:
`AssertionError: the NaN guard passed on a clean model and the copy then carried weights that
were poisoned after the check`. 탐지기가 눈멀지 않았음을 보이는 테스트와, 진짜 발산 모델을
여전히 거부하는지 보는 테스트를 함께 둔다.
