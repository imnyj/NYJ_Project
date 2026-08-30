# 구현 구조

작성 2026-08-30 · 짝 문서: `STRUCTURE_FILES.md` (파일이 어디에 있는가)

이 문서는 **파일 안이 어떻게 짜여 있는가**만 다룬다. 클래스와 함수 단위로,
각각 한 줄씩 무엇을 하는지 붙였다. `[핵심]`은 이해에 반드시 필요한 것이다.

---

## 0. 한 스텝에 무슨 일이 일어나는가

구조를 읽기 전에 이 흐름을 머리에 넣어두면 나머지가 쉽다.
번호는 `AoiV2IEnv.step()`의 주석 절 번호와 일치한다.

```
① 새 결정 등록      결정이 필요한 차량에게 grant (Δ, ch, p) 발급
                     → pending_grant 에 저장, next_update_t = 지금 + Δ
② 만료분 발사        next_update_t 에 도달한 grant만 전송 대기열로
                     ★ Δ가 살아 있는 지점. 나머지 차량은 침묵
③ SUMO 1스텝         libsumo.simulationStep() + anti-mocking 단언 1·2
④ CBR 측정           에어타임 × 채널별 전송 수 / 스텝 길이
⑤ 오차 누적          dead reckoning 오차를 구간에 적립 (보상의 오차항)
⑥ 성패 판정          judge_uplink → 성공하면 장부 갱신, 실패하면 재시도
                     anti-mocking 단언 3
⑦ 구간 종료          닫힌 차량만 _finalize_interval 로 보상 확정
                     anti-mocking 단언 4
⑧ 관측 생성          _get_observations 로 17차원 벡터 → 모델에게
```

바깥 루프(`run_hot_swap_training`)는 ⑦에서 닫힌 차량의 전이를 버퍼에 넣고,
⑧의 관측으로 그 차량에게 다음 grant를 묻는다. 차량마다 이 주기가 따로 돈다.

---

## 1. `src/rl_interface.py` — 상태·액션·버퍼의 정본 (754줄)

모든 상수와 자료구조의 유일한 출처. 다른 파일은 여기서 읽어 쓴다.

```
# 모듈 상수
STATE_DIM = 17            [핵심] 관측 벡터 폭
P_MIN, P_MAX = 10, 23     전송전력 범위 (3GPP power-class-3)
DELTA_MIN = 0.1           ETSI CAM 최소 생성 주기
DELTA_MAX                 [핵심] Δ 상한. net.xml의 실제 최대 적색 시간에서 추출
V_LIMIT                   시나리오 제한속도. net.xml의 최대 차선 속도에서 추출
E_REF = V_LIMIT × 1s      [핵심] 오차 정규화 기준. "1초분의 무지"

def get_sumo_max_red_phase_duration(): tlLogic을 순회해 최대 연속 적색 시간 계산 (사이클 랩어라운드 고려)
def get_sumo_max_edge_speed():         net.xml의 non-internal edge 중 최고 제한속도
def refresh_scenario_constants():      [핵심] 위 셋을 재계산. 환경이 망을 새로 만들 때마다 호출

def extrapolate():      p_hat = p_last + v_last × age. RSU의 dead reckoning 믿음
def estimation_error(): [핵심] 실제 위치와 위 예측의 거리. 논문의 e
def norm_sq_error():    [핵심] e²/(e² + E_REF²). 포화 없는 정규화 (D5)

class StateVectorizer:   17차원 관측 생성 — 유일한 정본
    __init__():             rsu_range·v_max는 0이면 시나리오에서 유도
    state_dim (property):   STATE_DIM 반환. 하드코딩 대신 이걸 읽으라는 계약
    _extract_queue_count(): n_queue를 명시 키 → TLS dict → 앞차 정보 순으로 회수
    _compute_heading():     속도와 RSU 방향의 코사인. +1 접근, -1 이탈
    vectorize():            노드 객체에서 생성 (테스트 경로)
    vectorize_from_dict():  [핵심] 상태 dict에서 생성. 파이프라인이 쓰는 유일한 경로

class ActionDecoder:     하이브리드 액션 (Δ, ch, p)
    __init__():          범위 저장. delta_max는 0이면 지금 해석
    delta_from_unit():   [핵심] u∈[0,1] → Δ 기하 매핑. 9종 baseline이 쓰는 함수
    unit_from_delta():   그 역함수
    decode_action():     원시 액션 → (Δ, ch, p). 기하 매핑 사용
    encode_action():     그 역. Δ는 기하, 전력은 선형(dBm이 이미 로그)

class RetrospectiveReplayBuffer:   SMDP 버퍼
    push():      (s, a, r, s', done, Δ) 저장
    sample():    [핵심] discount = gamma**Δ 계산. 가변 할인이 실제 적용되는 지점
    is_ready() / clear() / __len__()
```

### 상태 17차원

| # | 피처 | 정규화 | 무엇을 위한 것 |
|---|---|---|---|
| 0 | 마지막 예측 오차 | `norm_sq_error` | 이 차량이 얼마나 예측 가능한가 → Δ 결정 |
| 1,2 | 속도 X, Y | /V_LIMIT | dead reckoning 입력 |
| 3 | 속력 | /V_LIMIT | 정지 판단 |
| 4 | 가속도 | /a_max | 출발 시점 추론 |
| 5,6 | RSU 상대좌표 | /RSU_range | 위치 |
| 7 | RSU까지 거리 | /RSU_range | **전력 결정의 물리적 근거** |
| 8,9,10 | 신호등 R/Y/G | one-hot | **정지 추론 1차 근거** |
| 11 | 신호 전환까지 | /60s | 출발 시점 추론 |
| 12 | 정지선 거리 | /RSU_range | 통과할지 정지할지 |
| 13 | 범위 내 차량 수 | /100 | 혼잡 예측 |
| 14 | CBR | 그대로 | 혼잡 실측 |
| 15 | 앞 대기 차량 수 | /queue_max | 출발 지연 |
| 16 | heading | [-1,1] | 접근/이탈 |

> 피처 [0]은 원래 AoI(age)였으나, SMDP에서는 결정 시점이 항상 갱신 직후라
> age가 구조적으로 0이다. 실측 결과 상수였고, 마지막 예측 오차로 교체했다.

---

## 2. `src/hot_swap_trainer.py` — 파이프라인의 심장 (2,095줄)

전체의 4분의 1이 이 파일이다. 6개 클래스가 각자 다른 층을 맡는다.

```
def infer_state_dim():        StateVectorizer에서 관측 폭을 동적으로 읽음
def select_default_devices(): GPU 수에 따라 Act/Rest 디바이스 결정

class DualModelHotSwapManager:   Act/Rest 무중단 교체
    validate_weights(): Rest 모델에 NaN/Inf가 없는지 검사
    hot_swap():         [핵심] mutex 하에 Rest → Act 파라미터 원자적 복사
    get_stats():        교체 횟수·실패·지연

class TransitionStreamer:        시뮬레이션 → 학습 스레드 큐
    push():             전이를 non-blocking 큐잉. 가득 차면 버림
    drain():            최대 N개 꺼냄
    push_to_buffer():   [핵심] 꺼낸 것을 리플레이 버퍼로. 학습의 유일한 주입 경로

class BackgroundTrainer:         Rest 모델 비동기 학습
    train_step():       [핵심] 큐 배수 → 배치 샘플 → update() → 주기마다 hot_swap
    _worker_loop():     정지 신호까지 train_step 반복
    start() / stop() / get_metrics()

class HotSwapRLScheduler:        Act 모델 추론 전담
    decide_grant():     [핵심] 환경이 준 관측 벡터로 추론. 폭이 다르면 assert
                        관측을 만들지도, 보상을 매기지도 않는다 (원칙 P1)
    push_transition():  환경이 계산한 보상·실측 Δ를 그대로 전달
    get_latency_stats(): 추론 지연 p50/p95/p99

class HotSwapTrainer:            Act/Rest 생애주기 조립
    __init__():         두 모델 인스턴스화, 디바이스 배치, 매니저·버퍼·스케줄러 조립
    save_checkpoint() / load_checkpoint()

class AoiV2IEnv:                 ★ SUMO 환경. 관측과 보상의 유일한 정본
    __init__():                 밀도·시드·보상가중치, 상수 정의 (ε 3.2m, 재시도 10, 신선도 1s)
    _init_sumo():               SUMO 파일 생성 → 상수 갱신 → libsumo.start
    reset():                    warmup 진행 후 가장 붐비는 RSU를 target으로 선정
    _active_vehicle_ids():      [핵심] 활성 ID를 스텝당 1회만 조회 (성능)
    _get_vehicle_state_dict():  [핵심] SUMO에서 상태 dict 추출. 관측이 만들어지는 곳
    _ledger_queue_count():      RSU 장부 기반 n_queue + 신선도 가드 (D3)
    _rebuild_lane_index():      장부를 차선별로 묶음 (스텝당 1회)
    _is_redundant_update():     갱신 시점 오차 ≤ 3.2m이면 1.0 (D6)
    _register_vehicle():        신규 차량의 장부 항목 개설
    _get_observations():        [핵심] 17차원 벡터가 나가는 유일한 지점
    _finalize_interval():       [핵심] SMDP 구간 종료, 4항 보상 확정
    step():                     [핵심] 위 0장의 8단계 전부
    get_metrics():              AoI·손실·오차·전력·에너지·Jain·CBR + 빈실행 지표
    close()

def run_hot_swap_training():    [핵심] 이벤트 구동 SMDP 루프. gym 아님
```

### 보상 (D2 확정본)

$$R_k = -\Big(w_1 \sum_{t \in [t_k, t_{k+1})} \mathrm{Norm}(e^2(t))\frac{\delta t}{1s} + w_2 \mathrm{Norm}(P_{tx}) + w_3 \mathrm{Norm}(C_{freq}) + w_4 \mathbb{I}_{red}\Big)$$

**오차항만 구간 내내 쌓이고, 나머지 셋은 갱신 순간 1회.** 이 비대칭이 Δ 트레이드오프의 전부다.
움직이는 차를 방치하면 매 스텝 벌점이 쌓이지만, 정지한 차는 예측이 맞으므로
아무리 오래 두어도 0이다. 그래서 정지 차량에게는 긴 Δ가, 움직이는 차량에게는 짧은 Δ가 유리하다.

### 훈련 루프가 gym이 아닌 이유

차량마다 결정 시점이 다르다. 차량 A의 다음 상태는 A의 다음 갱신 때 생기지,
다른 차량의 스텝과 무관하다. 그래서 전역 (s,a,r,s') 틱이 존재하지 않는다.

```python
action_dict = {처음 범위에 들어온 차량: grant}
for step in range(steps):
    next_obs, rewards, term, trunc, info = env.step(action_dict)

    for rec in info["completed"]:        # 이번에 구간이 닫힌 차량만
        push_transition(보상, 실측 Δ)     # 요청 Δ가 아니라 실측값

    action_dict = {}
    for vid in info["needs_decision"]:   # grant가 없는 차량만
        action_dict[vid] = decide_grant(next_obs[vid])
```

`needs_decision`을 무시하고 매 스텝 전 차량에게 grant를 주면 Δ가 무의미해진다.
실제로 그런 상태였고, 그때는 9종 baseline이 전부 같은 전송 횟수를 냈다.

---

## 3. `src/Communications.py` — 802.11p 물리계층 (311줄)

"이 전송이 성공하는가"에 답하는 것이 전부다.

```
# 물리 상수 (전부 규격에서 유도, 튜닝값 아님)
FREQ_HZ = 5.9e9              ITS 대역
PL_EXP = 2.3                 준개방 도심 경로손실 지수
NOISE_FIGURE_DB = 9.0        RSU 수신기 잡음지수
NUM_SUBCHANNELS = 4          10 MHz × 4 = 40 MHz (미국 ITS 할당 내)
G_TX_DBI=3, G_RX_DBI=9       차량 휩 / RSU 마스트 안테나
SHADOWING_SIGMA_DB = 4.0     로그정규 섀도잉
OPERATING_RATE_MBPS = 6.0    QPSK 1/2, ETSI ITS-G5 기본 레이트
SINR_TH_DB                   MCS 테이블에서 유도 (리터럴 아님)

@dataclass Mcs:              하나의 변조·부호화 방식
MCS_TABLE                    802.11p 8단 레이트. rate = bits_per_symbol / 8µs 강제

def get_mcs():               레이트로 MCS 조회
def path_loss_db():          PL(1m) + 10·n·log10(d)
def rx_power_dbm():          [핵심] Ptx + G_tx + G_rx - PL(d) - 섀도잉
def noise_floor_dbm():       kTB + NF = -174 + 10log10(10MHz) + 9 = -95.0 dBm
def sensitivity_dbm():       잡음바닥 + MCS 임계 = -85 dBm
def frame_symbols():         (16 + 8L + 6) / bits_per_symbol 올림
def frame_airtime_s():       [핵심] 40µs + 8µs × 심볼수. 300B → 448µs
def seed_channel():          섀도잉 전용 RNG 시드 (전역 random과 분리)
def draw_shadowing_db():     로그정규 샘플 1개
def draw_overlap():          [핵심] 취약구간 2·T_air/T_step 확률로 겹침 판정
def rayleigh_success_prob(): P(SINR ≥ 임계), 모든 링크 독립 Rayleigh
def judge_uplink():          [핵심] 같은 채널 그룹의 상호 간섭을 물려 성공확률 산출
```

### 겹침 확률이 왜 필요한가

프레임은 448 µs인데 스텝은 100 ms다. 같은 채널의 두 grant가 실제로 시간상 겹칠 확률은
`2·T_air/T_step = 0.896%`에 불과하다. 이걸 100%로 취급하면 CBR이 0.7%인데 패킷손실이
89%가 나오는 자기모순이 생긴다. 실제로 그런 상태였고, 겹침을 확률로 모델링한 뒤
손실이 19.5%로 떨어져 거리·전력에 따른 잡음 제한이 되었다.

---

## 4. `src/sumo/make_sumo_set.py` — 시나리오 생성 (502줄)

```
# 기하 상수
RSU_RANGE = 300.0                    [핵심] 통신 반경의 정본
OUTAGE_ZONE, EDGE_LENGTH = R×2 + O   RSU 간 거리 900 m
NUM_BLOCKS = 6, GRID_SIZE            6×6 격자, 4500 m
AV_SPEED = 40 km/h, DEL_SPEED = 0.2  차선 속도를 이 범위에서 랜덤 배정
DENSITY                              차량 밀도 (/km/lane)

def CalcP_GEN():                 밀도로부터 flow 생성확률 산출
def make_dead_end_nodes():       격자 외곽의 dead-end 노드
def current_generation_signature(): 파라미터 지문. 바뀌면 재생성
def generation_signature_matches(): 캐시 유효성 검사
def _generation_lock():          [핵심] 프로세스 간 배타 락. 4그룹 동시 실행 대비
def _atomic_write_text/_tree():  임시파일 → rename. 부분 기록 방지
def are_sumo_files_valid():      7개 XML의 상호 일관성
def _make_sumo_files_impl():     노드·엣지·신호등·flow·RSU POI 생성 후 netconvert
def make_sumo_files():           [핵심] 위를 락으로 감싼 공개 진입점
```

생성되는 파일: `generated.nod/edg/net/rou/add/sumocfg` + `rsu.poi.xml`.
신호 주기는 green 42 s + yellow 3 s이며, 여기서 한 방향의 적색 45 s가 나온다.
**Δ 상한 45초가 이 값에서 유도된다** — 정지 차량이 물리적으로 멈춰 있을 수 있는 최대 시간이다.

---

## 5. `src/dynamics_predictor.py` — 동역학 피처 (410줄)

```
def predict_stop_imminent():   신호·거리·속도로 곧 정지할 확률
def predict_start_imminent():  적색 잔여시간과 앞차 수로 곧 출발할 확률
def extract_queue_features():  같은 차선 앞쪽의 대기 차량 수 등
def extract_tls_features():    [핵심] TraCI로 신호 상태·잔여시간·정지선거리·차선 정보
class DynamicsPredictor:       위 함수들의 캐싱 래퍼
```

관측 [8]~[12]와 [15]가 여기서 온다. 정지 추론의 인과 사슬이 이 파일에 있다.

---

## 6. `src/baselines/` — 비교 방안 9종 (3,740줄)

```
__init__.py
    BASELINE_REGISTRY   [핵심] 이름 → 클래스. evaluate/hpo/run_all이 전부 여기서 조회
    BASELINE_CATEGORIES 기본/최신/유사 3분류
    get_baseline()      이름으로 클래스 조회. 없으면 목록과 함께 예외

base_agent.py
class BaseRLModel:      9종 공통 계약
    _prepare_state_tensor(): numpy → 모델 디바이스의 2D 텐서
    select_action():         [핵심] 관측 → (Δ, ch, p) + 원시 액션
    update():                [핵심] 배치로 가중치 갱신
    save() / load():         핫스왑용 state_dict 왕복

sb3_wrapper.py          기본 3종 공통. 하이브리드 액션을 3차원 Box로 노출
                        SB3 policy를 nn.Module 서브모듈로 등록 (핫스왑 요건)
```

| 모델 | 분류 | 원 논문 | 파라미터 |
|---|---|---|---|
| PPO | 기본 | Schulman 2017 | 10,887 |
| SAC | 기본 | Haarnoja ICML 2018 | 357,643 |
| TD3 | 기본 | Fujimoto ICML 2018 | 772,810 |
| RES-MAPDDPG | 최신 | Li, IEEE TVT 2026 | 301,656 |
| MA2HDQN | 최신 | Hong, IEEE TVT 2026 | 148,880 |
| I-HAMAPPO | 최신 | Chen, IEEE TWC 2026 | 68,657 |
| SPAM-D3QN | 유사 | Bai, IEEE TVT 2024 | 87,426 |
| CARLTON | 유사 | Cohen, IEEE TWC 2025 | 44,624 |
| MADDPG-MT | 유사 | Parvini, IEEE TVT 2023 | 222,748 |

파라미터 수가 전부 다르다. 과거 한 모델이 다른 모델의 구조적 복제본이었던 사건이 있어
이 표가 검증 항목이 되었다. 9종 전부 Δ를 기하 매핑(`delta_from_unit`)으로 디코딩한다.

---

## 7. 진입점 3종

```
run_all.py
def main():   --models로 모델 지정, --episodes/--steps-per-episode/--no-resume
              레지스트리에서 클래스를 받아 run_hot_swap_training 호출

src/evaluate.py
def normalize_model_name():   별칭 → 정본 이름 (레지스트리 기반)
def instantiate_model():      이름 또는 클래스 → 인스턴스
def evaluate_single_run():    [핵심] 밀도·시드 하나에 대한 이벤트 구동 롤아웃
def run_full_benchmark():     5 밀도 × 5 시드 × 10 모델
def calculate_jains_fairness(): 공정성 지수
def load_optimal_hparams():   HPO 결과 CSV 로드

src/hpo.py
def sample_hparams():             [핵심] 모델별 탐색공간. 실제 생성자 시그니처 기준
def assert_hparams_reach_model(): [핵심] 샘플한 키가 생성자에 실제로 닿는지 검사
def sample_reward_weights():      w1~w4 샘플 후 합 1로 정규화
def compute_composite_objective(): 오차·AoI·손실·전력의 가중합
def evaluate_model_in_env():      이벤트 구동 롤아웃 + 학습
def evaluate_trial_multiseed():   여러 시드 평균
def run_hpo_study():              Optuna study 1개 실행
def run_all_baselines_hpo():      9종 전체
```

> `assert_hparams_reach_model`은 방어용이다. 9종 생성자가 전부 `**hparams`로 끝나서,
> 이름이 틀린 키는 **오류 없이 삼켜진다.** 실제로 탐색공간이 옛 모델명으로 분기해
> 전부 폴백되던 시기가 있었고, Optuna는 "최적 학습률"을 보고했지만 모델은 기본값으로
> 학습하고 있었다. 이제 테스트가 9종 전부에 대해 이 검사를 돌린다.

---

## 8. 이 코드에서 헷갈리기 쉬운 것

**gym 환경이 아니다.** `env.step()`이 있어도 `model.learn(env)`로 못 돌린다.
SMDP라 전역 틱이 없다. `needs_decision`에 있는 차량에게만 새 grant를 준다.

**grant는 발급한 스텝에 발사되지 않는다.** Δ 후에 발사된다.
`pending_grant`에 저장되고 `next_update_t`에 도달해야 전송이 일어난다.

**`transmitted=True`는 "전파를 썼다"이지 "도착했다"가 아니다.**
재시도 10회를 다 쓰고 포기한 구간도 전력과 혼잡은 문다(실제로 10번 송신했으므로).
다만 I_redundant는 물지 않는다 — RSU가 아무것도 받지 못했으니 "이미 알던 것"일 수 없다.

**보상은 스텝이 아니라 구간에 매겨진다.** `step()`이 돌려주는 `rewards`에는
이번 스텝에 **구간이 닫힌** 차량만 들어 있다. 나머지는 아직 진행 중이다.

**상수는 전부 정본에서 파생된다.** 리터럴을 새로 쓰지 말 것.
정본 목록은 `STRUCTURE_FILES.md` 5장에 있다.
