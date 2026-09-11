# 시뮬레이션 코드 안내서

작성 2026-08-30 · Critic 에이전트 3인 검토 + Claude Code 재확인
개정 2026-09-05 · 코드 현행에 맞추어 줄 수·결함 현황·`divergence_guard.py` 반영
대상 독자: 이 코드를 처음 읽으며 구조를 파악하려는 사람

> [!IMPORTANT]
> **4장의 결함 목록은 2026-08-30 조사분이다.** 이후 2026-09-04 전수 조사에서 새 결함이
> 다수 발견되었으므로, 결함 현황을 확인할 때는 `review/full_audit_20260904.md`를 함께 볼 것.

이 문서는 두 부분이다. **1~3장**은 어떤 파일이 무엇을 하고 서로 어떻게 연결되는지,
**4장**은 그 과정에서 발견한 결함이다. 클래스·함수 단위 상세 요약은 `critic/` 아래 3개 파일에 있고
이 문서는 그것을 읽는 순서와 맥락을 준다.

---

## 1. 한 장으로 보는 전체 구조

SUMO가 실제 도로 위 차량을 굴리고, RSU 한 대가 통신 범위 안 차량 각각에게
**언제 다시 보고할지(Δ), 어느 서브채널로(ch), 얼마의 전력으로(p)** 를 정해 준다.
강화학습이 그 결정을 학습한다.

```
run_all.py                    훈련 진입점. 모델 이름을 받아 학습을 건다
   │
   └── src/hot_swap_trainer.py       ★ 파이프라인의 심장 (4,160줄)
         │   ├── AoiV2IEnv           SUMO 연동 환경. 관측과 보상의 유일한 정본
         │   ├── HotSwapRLScheduler  Act 모델 추론 전담 (관측·보상 안 만듦)
         │   ├── DualModelHotSwapManager  Act/Rest 무중단 교체
         │   ├── BackgroundTrainer   Rest 모델 백그라운드 학습 스레드
         │   └── run_hot_swap_training  이벤트 구동 SMDP 루프
         │
         ├── src/rl_interface.py     상태 17차원 / 액션 (Δ,ch,p) / SMDP 버퍼의 정본
         ├── src/divergence_guard.py 학습 발산·기울기 정지 감시 (2026-09-03 신설)
         ├── src/Communications.py   802.11p 물리계층 (경로손실·SINR·에어타임)
         ├── src/dynamics_predictor.py  신호등·앞차 등 차량 동역학 피처 추출
         ├── src/sumo/make_sumo_set.py  SUMO 격자망·차량흐름·신호등 생성
         └── src/baselines/          비교 방안 9종 + 공통 래퍼
```

평가와 하이퍼파라미터 탐색은 같은 환경을 재사용하는 별도 진입점이다.

```
src/evaluate.py   밀도 5종 × 시드 5종 벤치마크
src/hpo.py        Optuna 하이퍼파라미터 탐색
```

두 파일이 폐기된 옛 모델명을 참조해 9종을 하나도 인스턴스화하지 못하던 시기가 있었으나
(옛 결함 B-1·B-2), **2026-08-30에 해소되었다.** 지금은 둘 다 `src/baselines/__init__.py`의
레지스트리에서 목록과 분류를 유도한다(`evaluate.py`와 `hpo.py`가 각각
`ALL_BASELINES`·`BASELINE_CATEGORIES`·`get_baseline`을 임포트한다). 상세는 4장 A-9와 A-10이다.

### 데이터가 흐르는 순서 (한 스텝)

```
1. 새 결정이 필요한 차량에게 grant 발급        step() 1절
2. Δ가 만료된 grant만 전송 대기열에 넣음        step() 2절   ← 여기가 Δ가 살아있는 지점
3. libsumo.simulationStep()  실제 물리 1스텝    step() 3절
4. anti-mocking 단언 4종                        step() 3절
5. CBR 계산 (에어타임 × 전송 수 / 스텝 길이)     step() 4절
6. dead reckoning 오차 계산 + 구간 누적          step() 5절
7. judge_uplink 로 성공/실패 판정, 실패는 재시도  step() 6절
8. 구간이 닫힌 차량은 보상 확정 → 리플레이 버퍼   _finalize_interval
```

---

## 2. 파일별 역할

### 2-1. 실제로 돌아가는 파일 (9개)

줄 수는 2026-09-05 14:56에 `wc -l`로 실측한 값이다. 측정 당시 여러 에이전트가 같은 파일들을
동시에 수정하고 있어 값이 계속 움직였으므로, 정확한 값이 필요하면 `wc -l`을 다시 실행할 것.

| 파일 | 줄수 | 역할 | 상세 |
|---|---|---|---|
| `run_all.py` | 454 | 훈련 진입점. `--models`로 모델 지정, `--no-resume` 지원 | `critic/critic_baselines.md` |
| `src/hot_swap_trainer.py` | 4,160 | 환경·스케줄러·핫스왑·훈련루프 전부 | `critic/critic_core.md` |
| `src/rl_interface.py` | 913 | 상태/액션/버퍼의 정본. 모든 상수의 출처 | `critic/critic_core.md` |
| `src/divergence_guard.py` | 360 | 학습 발산·기울기 정지 감시 (2026-09-03 신설) | 아래 2-3절 |
| `src/Communications.py` | 462 | 802.11p PHY. 경로손실·Rayleigh SINR·에어타임 | `critic/critic_physics.md` |
| `src/dynamics_predictor.py` | 661 | TraCI로 신호등 상태·앞차·정지 임박 추출 | `critic/critic_physics.md` |
| `src/sumo/make_sumo_set.py` | 668 | 6×6 격자망·차량흐름·신호등 XML 생성 | `critic/critic_physics.md` |
| `src/heuristic_scheduler.py` | 244 | 규칙 기반 스케줄러. 평가 시 비교군 | `critic/critic_physics.md` |
| `src/baselines/` | 12개 파일 4,159줄 | 비교 방안 9종 + SB3 래퍼 | `critic/critic_baselines.md` |

`src/evaluate.py`(901줄)와 `src/hpo.py`(1,629줄)는 훈련 이후 단계의 진입점이며,
2026-08-30 레지스트리 연결 복구 이후 9종을 전부 다룬다.

### 2-2. 치워둔 파일 (2026-08-30, `coder/backup/unused_20260830_172551/`)

사용자 요청으로 격리했다. import 그래프를 실측해 **현재 파이프라인이 전혀 쓰지 않는 것**만 옮겼다.

| 파일 | 왜 안 쓰이나 |
|---|---|
| `8. V2V Precaching.py` | **다른 논문**("V2V Precaching in Outage Zone") 예제. 이 프로젝트와 무관 |
| `src/model.py` | TensorFlow/Keras PPO. 어디서도 import 안 됨. 실제 구현은 PyTorch |
| `src/aoi_env.py` | 감사받은 환경 클래스지만 **실행 경로가 아니었다.** D1에서 폐기 확정 |
| `src/NetSim.py` | `aoi_env.py` 전용 시뮬레이터. 현 파이프라인 import 0건 |
| `verify_environment.py` | `aoi_env.py` 전용 검증 스크립트 |
| `tests/test_aoi_env_genuine.py` | 위 클래스 검증 (11 tests) |
| `tests/test_tier4_simulation.py` | 위 클래스 검증 (3 tests) |
| `etc/scripts/test_adversarial_suite.py` | 위 클래스 대상 스트레스 테스트 |

> `NetSim.py`가 무엇이었나: 초기 설계의 SUMO 래퍼로, 차량·RSU를 노드 객체로 감싸 시뮬레이션을
> 돌리는 구조였다. 이후 `hot_swap_trainer.py`가 libsumo를 직접 호출하는 방식으로 재작성되면서
> 통째로 대체되었다. 주의할 점이 하나 있는데, `NetSim.pre_define()`이 `make_sumo_set`의 전역
> 상수(RSU_RANGE 등)를 덮어쓴다. 실수로 import하면 정본이 오염되므로 되살릴 때 주의해야 한다.

**테스트 119개 → 104개.** 사라진 15개는 전부 폐기된 클래스를 검증하던 것이다.
실사용 클래스의 anti-mocking 단언문은 `tests/test_hot_swap.py`와 `test_dummy_verification.py`가 계속 커버한다.
`tests/test_dynamics_predictor.py`는 폐기 모듈에 의존하던 부분만 떼어냈다. 그 과정에서 dead reckoning
계산이 실사용 코드에 인라인으로만 있던 것을 `rl_interface.estimation_error()`로 뽑아 정본을 하나로 만들었다.

### 2-3. `src/divergence_guard.py` — 발산 감시 (2026-09-03 신설, 360줄)

**왜 생겼는가.** 2026-09-02에 PPO baseline이 100 에피소드 실행의 11번째 에피소드에서 발산했다.
백그라운드 학습 스레드가 `sb3_ppo.update()`에서 NaN 파라미터 예외를 던지고 죽었는데, 그 스레드를
지켜보는 것이 파이프라인에 하나도 없었다. 에피소드 루프는 이후 8.8시간 동안 SUMO를 계속 굴려
89개 에피소드 행을 더 쓰고 체크포인트를 저장한 뒤, `total_steps: 200000, episodes: 100`이라는
요약을 반환했다. 예약 보고서는 그것을 `done 100/100`으로 불렀다.

**무엇을 하는가.** 손실이 폭주했는가, 기울기 갱신이 아예 멈췄는가, 학습 스레드가 조용히 죽었는가를
각각 별도로 감시하고, 조건에 걸리면 실행을 중단시킨다. 앞의 둘은 이 파일의 `DivergenceMonitor`가,
스레드 사망은 `hot_swap_trainer.BackgroundTrainer._worker_loop`가 맡는다.

**두 규칙.** 손실 판정에 절대 규칙과 상대 규칙을 함께 쓴다.

| 규칙 | 상수 | 값 | 왜 이 값인가 |
|---|---|---|---|
| 절대 하한 | `DEFAULT_LOSS_ABS_FLOOR` | 1.0e3 | 가장 나쁜 정상 에피소드(12.43)와 가장 약한 발산(285,247) 사이 네 자릿수 공백의 아래쪽 |
| 워밍업 중앙값 대비 배율 | `DEFAULT_LOSS_RATIO` | 1.0e3 | 모델마다 손실 척도가 네 자릿수 차이 나므로 자기 자신의 초기 중앙값과 비교 |
| 배율 규칙의 기준 구간 | `DEFAULT_WARMUP_EPISODES` | 5 | PPO는 11번과 17번 에피소드에서 이미 발산했으므로 5는 여유가 있다 |
| 연속 초과 요구 | `DEFAULT_LOSS_PATIENCE` | 3 | I-HAMAPPO가 한 에피소드 튀었다가 두 에피소드 뒤 회복한 사례가 있어 1회는 근거가 아니다 |
| 기울기 정지 | `DEFAULT_MAX_ZERO_UPDATE_EPISODES` | 3 | 정상 실행 18건은 이런 에피소드가 0회였고, 실패한 PPO 두 건은 실패 시점부터 끝까지 연속이었다 |

절대 규칙 하나만으로는 부족하다. 모델별 손실 척도가 SPAM-D3QN의 5e-4에서 CARLTON의 12까지
네 자릿수에 걸쳐 흩어져 있기 때문이다. 반대로 배율 규칙 하나만으로도 부족한데, PPO의 초기 손실
평균이 -0.09여서 배율만 보면 89.5 같은 평범한 잡음에도 발화하기 때문이다. 두 규칙을 함께 쓰고
연속 초과를 요구하는 구성이 여기서 나왔다.

> [!IMPORTANT]
> **기존 산출물에 소급 적용되지 않았다.** 이 모듈은 본훈련이 끝난 뒤에 만들어졌으므로,
> 그 이전에 생성된 체크포인트와 진척 CSV는 이 감시를 거치지 않았다. 다만 모듈이 torch 상태를
> 갖지 않고 트레이너에서 아무것도 임포트하지 않기 때문에, 실행 중 판정(`run_hot_swap_training`)과
> 사후 재생 판정(`etc/report_progress.py`가 진척 CSV를 훑는 경로)이 완전히 같은 규칙을 쓴다.
> 따라서 **과거 실행도 사후에 같은 기준으로 다시 판정할 수 있다.** 실제로 `review/full_audit_20260904.md`가
> 그 방식으로 18개 실행을 재판정했다.

---

## 3. 읽는 순서 (권장)

코드를 처음 본다면 이 순서가 가장 빠르다.

1. **`idea/design_spec_v2.md` 1·3·4·5절** — 무엇을 하려는 코드인지. 이걸 안 읽으면 나머지가 안 읽힌다.
2. **`src/rl_interface.py`** — 상태 17차원과 액션 3축이 무엇인지. 가장 짧고 자기완결적이다.
3. **`src/hot_swap_trainer.py::AoiV2IEnv.step()`** — 한 스텝에 무슨 일이 일어나는지. 1장의 8단계가 그대로 주석으로 붙어 있다.
4. **`src/Communications.py`** — 전송이 성공하는지 판정하는 물리. `judge_uplink`만 봐도 된다.
5. **`src/hot_swap_trainer.py::run_hot_swap_training()`** — 이벤트 구동 루프. gym이 아닌 이유가 여기 있다.
6. **`src/baselines/base_agent.py` → `sb3_ppo.py` 하나** — 모델이 환경과 맺는 계약.

### 이 코드에서 헷갈리기 쉬운 것 3가지

**(1) gym 환경이 아니다.** `env.step()`이 있지만 `model.learn(env)`로 돌릴 수 없다.
차량마다 결정 시점이 달라서(SMDP) 전역 (s,a,r,s') 틱이 존재하지 않는다.
`step_info["needs_decision"]`에 있는 차량에게만 새 grant를 주는 것이 핵심이다.

**(2) grant는 발급한 스텝에 발사되지 않는다.** Δ 후에 발사된다.
`pending_grant`에 저장되고 `next_update_t`에 도달해야 전송이 일어난다.
이걸 놓치고 매 스텝 전 차량에게 grant를 주면 Δ가 무의미해진다 (실제로 그런 버그가 있었다).

**(3) 상수는 전부 정본에서 파생된다.** 리터럴을 새로 쓰지 말 것.
- 상태 폭 → `rl_interface.STATE_DIM`
- Δ 상한 45s → net.xml의 실제 적색 시간에서 추출
- 속도 상한, `E_REF` 13.32m → net.xml의 실제 제한속도에서 추출
- RSU 반경 300m → `make_sumo_set.RSU_RANGE`

리터럴 하드코딩이 이 프로젝트에서 반복적으로 결함을 만들었다. 테스트가 `18`을 박아둬서 상태 차원을
17로 줄일 때 17건이 깨졌고, 계획서가 CSV 컬럼 번호를 박아둬서 지표 추가 후 엉뚱한 열을 보고 있었다.

---

## 4. 발견한 결함

Critic 3인이 독립 검토하고, 보고된 항목을 Claude Code가 **전부 직접 재확인**했다.
날조는 없었다. 아래 표시: `[수정완료]` / `[미수정]`

### A. 이번에 수정한 것

| # | 심각도 | 내용 | 위치 |
|---|---|---|---|
| A-1 | 중대 | **에너지 지표가 2.23배 과대평가.** `10^((p-30)/10) × 0.001`에서 0.001초는 근거 없는 리터럴. 실제 프레임 에어타임은 448 µs. 논문 결과표에 실리는 지표다 | `hot_swap_trainer.py` |
| A-2 | 중대 | **RSU 반경이 4곳에 리터럴 300.0.** 정본은 `make_sumo_set.RSU_RANGE`. 지금은 우연히 같지만 반경을 스윕하면 관측은 한 반경으로 정규화하고 환경은 다른 반경으로 차량을 받는 불일치가 조용히 생긴다 | `rl_interface.py`, `hot_swap_trainer.py` |
| A-3 | 경 | `noise_floor_mw()`가 `TOTAL_BW_HZ / n`으로 대역폭을 역산. 802.11p 표준 채널폭 10 MHz를 직접 써야 한다. n=4일 때만 우연히 일치 | `Communications.py` |
| A-4 | 경 | `MAX_SPEED`가 계산·재대입되지만 소비처 0건 | `make_sumo_set.py` |
| A-5 | 경 | `REDUNDANT_POS_EPS_M`가 정의만 되고 읽히지 않음. **주석은 "get_metrics에서 쓰인다"고 했으나 거짓** | `hot_swap_trainer.py` |
| A-6 | 경 | `TransitionStreamer.push_dict()` 죽은 공개 메서드 | `hot_swap_trainer.py` |
| A-7 | 경 | I_redundant 옛 정의(변위 기준) 주석이 새 정의(예측 오차 기준) 위에 그대로 남아 서로 모순 | `hot_swap_trainer.py` |
| A-8 | 경 | `heuristic_scheduler.py` 주석 3곳이 구버전 값 (0.5s/25dBm/20dBm vs 실제 0.1s/23/10) | `heuristic_scheduler.py` |
| A-9 | **치명** | **`evaluate.py`·`hpo.py`가 현행 9종을 하나도 못 돌렸다.** 폐기된 옛 모델명을 그대로 참조. 두 파일이 `src/baselines/__init__.py`의 레지스트리에서 목록·분류·클래스를 유도하도록 교체. 9종 전부 이름만으로 인스턴스화됨을 실측 확인 | `evaluate.py`, `hpo.py` |
| A-10 | **중대** | **Optuna 하이퍼파라미터가 모델에 도달하지 않았다.** 탐색 공간이 옛 이름으로 분기해 전부 폴백. 9종 각각의 **실제 생성자 시그니처**에 맞춰 재작성하고, 값이 런타임에 반영되는지까지 실측 확인 | `hpo.py` |
| A-11 | **중대** | **처리량 O(V²).** `_get_vehicle_state_dict`가 차량마다 `getIDList()` 전체를 받아 선형 검색 — 스텝당 1307회 호출, cProfile상 전체 시간의 55%. 스텝당 1회 캐시로 교체 | `hot_swap_trainer.py` |
| A-12 | **중대** | **시나리오 상수가 임포트 시 1회만 계산.** `DELTA_MAX`/`V_LIMIT`/`E_REF`가 net.xml 재생성을 따라가지 않았다. `refresh_scenario_constants()`를 신설해 `_init_sumo()`가 망 생성 직후 호출하고, `ActionDecoder`는 생성 시점에 해석하도록 변경(기본 인자는 정의 시점에 바인딩되므로 갱신이 안 닿았다) | `rl_interface.py`, `hot_swap_trainer.py` |
| A-13 | **중대** | **`decode_action()`이 선형 Δ 매핑.** 클래스 독스트링과 `delta_from_unit`은 기하인데 이 폴백만 선형이었다. logit 0에서 22.55s vs 2.12s로 10배 차이. 기하로 통일하고 `encode_action`도 역함수를 맞췄다. 두 경로 일치·왕복·해상도 균일성 테스트 3건 신설 | `rl_interface.py` |
| A-14 | 경 | **`Communications.py`의 절반이 레거시.** 802.11ac/광케이블 백홀 함수 10종이 폐기된 `NetSim.py` 전용으로 외부 호출 0건. 118줄 격리, 파일 411→311줄. 파일 헤더도 "CIoV precaching simulator"에서 현재 내용으로 교체 | `Communications.py` |
| A-15 | 경 | **포기된 갱신에 중복 페널티 부과 가능.** 재시도 10회를 소진해 구간이 닫힐 때 실제 오차로 `I_redundant`를 판정해, 예측이 우연히 정확하면 도달하지도 않은 갱신에 페널티가 붙었다. RSU가 아무것도 받지 못했으므로 "이미 알던 것"일 수 없다 — 명시적으로 미부과 | `hot_swap_trainer.py` |

### B. 아직 수정하지 않은 것

| # | 심각도 | 내용 |
|---|---|---|
| ~~B-1~~ | ~~치명~~ | **수정 완료.** 아래 A-9 참조 |
| ~~B-2~~ | ~~중대~~ | **수정 완료.** 아래 A-10 참조 |
| ~~B-3~~ | ~~중대~~ | **수정 완료.** 아래 A-11 참조 |
| ~~B-4~~ | ~~중대~~ | **수정 완료.** 아래 A-12 참조 |
| ~~B-5~~ | ~~중대~~ | **수정 완료.** 아래 A-13 참조 |
| ~~B-6~~ | ~~경~~ | **수정 완료.** 옛 값 잔재 전부 정리 |
| ~~B-7~~ | ~~확인필요~~ | **수정 완료.** 아래 A-15 참조 |

위 표의 B-1부터 B-7까지는 2026-08-30 시점의 목록이며 그 일곱 건은 전부 수정되었다.

> [!WARNING]
> **"B절은 비었다"고 읽지 말 것.** 이 표가 비어 보이는 것은 2026-08-30 조사에서 나온 결함만
> 담고 있기 때문이다. 그 뒤 **2026-09-04 전수 조사에서 새 결함이 다수 발견되었고 상당수가 아직
> 미해결이다.** 예를 들어 보상 오차 항의 mean 팔에서 초당 점수가 침묵에 유리하게 역전되는
> 문제(C5), 체크포인트가 밀도 5 에피소드에 몰려 선택되는 편향(M9), 발산한 실행이 정상 종료로
> 보고된 문제 등이 그때 드러났다.
>
> **상세 목록과 근거는 `review/full_audit_20260904.md`에 있다.** 이 문서만 보고 "남은 결함이
> 없다"고 판단하면 오판이므로, 결함 현황을 확인할 때는 반드시 그쪽을 함께 볼 것.
> 관련 후속 조치는 `review/STOP_NOTICE_20260905.md`에도 기록되어 있다.

### A-11 상세: 처리량 급락 — 가설 하나가 틀렸고 프로파일이 답을 줬다

측정(밀도 25, 시드 42, warmup 350 — 당시의 기본값이며 현행 기본값은 1200이다):

| 스텝 | 망 전체 차량 | 범위 내 | 수정 전 ms/step | 수정 후 ms/step |
|---|---|---|---|---|
| 100 | 527 | 32 | 17.9 | 5.0 |
| 500 | 1025 | 66 | 68.3 | 13.0 |
| 900 | 1485 | 92 | **148.1** | **21.3** |

범위 내 차량이 2.9배일 때 비용이 8.3배(2.9² = 8.4)라 제곱 증가였다.

**첫 가설은 틀렸다.** `_ledger_queue_count`가 차량마다 장부 전체를 훑는 O(V²)라고 보고
차선별 인덱스를 도입했으나 **개선은 3%에 그쳤다**(148.1 → 143.8 ms). 추측을 접고 cProfile을 돌렸다.

```
130733 calls   6.811 s   libsumo._libsumo.vehicle_getIDList      <- 전체 12.3초 중 55%
130433 calls   2.130 s   _get_vehicle_state_dict
   100 calls   0.742 s   libsumo simulation_step                  <- SUMO 자체는 6%뿐
```

**진짜 원인**: `_get_vehicle_state_dict`의 첫 줄이 `vid not in libsumo.vehicle.getIDList()`였다.
차량 하나를 조회할 때마다 SUMO에서 전체 ID 리스트를 새로 받아 마샬링하고 선형 검색한 것이다.
차량이 1155대면 스텝당 1307번 호출된다. 리스트를 **스텝당 한 번만** 받아 집합으로 캐시하도록 바꿨다.
anti-mocking 단언 2가 `simulationStep()` 직후 어차피 같은 리스트를 직접 받으므로 그 결과로 캐시를 채운다
(단언은 SUMO를 직접 질의해야 의미가 있으므로 그대로 두었다).

**결과: 900스텝 지점에서 6.75 → 46.98 steps/s, 약 7배.** 차량 수에 대한 증가도 제곱에서 선형에 가까워졌다.

첫 가설의 수정(차선 인덱스, `n_queue`를 관측 경로로 한정)도 유지한다. 병목은 아니었지만
한 스텝에 3번 하던 계산을 1번으로 줄인 것 자체는 타당하다. 다만 **그것이 병목이라는 진단은 틀렸고,
프로파일 없이 코드만 보고 추측한 결과였다는 점을 기록해 둔다.**

### C. 검증했으나 결함이 아니었던 것

억지로 결함을 만들지 않기 위해 기록한다. 아래는 실제로 확인해서 **정상**으로 판정한 것들이다.

- 물리 수식 전부: 경로손실, 잡음바닥 −95 dBm, 감도 −85 dBm, 에어타임 448 µs, 안테나 이득 반영,
  Rayleigh 성공확률식. 직접 재계산해 코드값과 일치 확인.
- 액션 범위: 9종 전부 Δ∈[0.1,45] / p∈[10,23] / ch∈{0..3} 준수. 극단 입력에서도.
- Δ 매핑: 9종 전부 기하 매핑 사용. 선형 폴백을 쓰는 모델 없음.
- 크레딧 할당: 과거 "이산 헤드 20개 중 4개만 학습" 버그 재발 없음.
- `optimizer.step()`이 실제로 가중치를 움직임 (state_dict 차분으로 확인, 9종 전부).
- 파라미터 수가 9종 전부 다름 (10,887 ~ 772,810). 과거 MAPPO=PPO 복제본 사건 재발 없음.
- 훈련·평가·HPO 세 루프 전부 이벤트 구동 (`needs_decision` 사용).
- 데이터 누수 없음. γ^Δ 할인 실제 동작.
- 단위 오류(dB/dBm, m/s vs km/h, µs vs s) 없음.

---

## 5. 상세 문서

| 파일 | 내용 |
|---|---|
| `STRUCTURE_FILES.md` | **파일 구조** — 어떤 파일이 어디에 있고 무엇을 담당하는가 |
| `STRUCTURE_CODE.md` | **구현 구조** — 파일 안의 클래스·함수가 어떻게 짜여 있는가 |
| `critic/critic_core.md` | `hot_swap_trainer.py` + `rl_interface.py` 전 클래스·함수 요약, 결함 11건 |
| `critic/critic_physics.md` | 물리·시나리오 6개 파일 요약, 물리 상수표, 결함 8건 |
| `critic/critic_baselines.md` | baseline 9종 + 진입점 3개 요약, 9종 비교표, 결함 4건 |
| `idea/design_spec_v2.md` | 설계 확정본. 무엇을 왜 이렇게 만들었는지 |
| `review/claude_audit_20260828.md` | 8-28에 발견한 결함 6건의 기록 (전부 수정 완료) |
| `review/full_audit_20260904.md` | **9-04 전수 조사.** 이 문서 4장 이후에 발견된 결함의 정본 |
| `review/STOP_NOTICE_20260905.md` | 위 조사에 따른 중단 결정과 후속 조치 |
| `simulation_plan.md` | 실행 계획과 현재 상태 |
