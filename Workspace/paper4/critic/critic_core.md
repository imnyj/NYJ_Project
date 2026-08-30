# Critic 검토 — hot_swap_trainer.py / rl_interface.py
검토일: 2026-08-30 · 대조 문서: `idea/design_spec_v2.md` (1·4·5·9·10절)

---

# 산출물 1: 코드 구조 요약

## coder/src/rl_interface.py

```
모듈 상수: STATE_DIM=17, P_MIN=10.0, P_MAX=23.0, DELTA_MIN=0.1  [핵심] 액션/상태 폭의 단일 정본
def get_sumo_max_red_phase_duration(): generated.net.xml의 tlLogic 순회, 사이클 랩어라운드까지 고려해 최대 연속 적색 지속시간 계산 [핵심] Δ 상한의 근거
DELTA_MAX = get_sumo_max_red_phase_duration()  [핵심] 모듈 임포트 시 1회만 계산되어 고정됨 (결함 참조)
def get_sumo_max_edge_speed(): net.xml의 모든 non-internal edge에서 최고 차선 제한속도 추출 [핵심] v_max/E_REF의 근거
V_LIMIT = get_sumo_max_edge_speed()  [핵심] 마찬가지로 임포트 시 1회 고정
E_REF = V_LIMIT * 1.0  [핵심] 오차항 정규화 기준(D5)
def norm_sq_error(err_m, e_ref=0.0): e^2/(e^2+e_ref^2) 형태로 포화 없는 오차 정규화 [핵심] D2·D5의 유일한 정규화 함수

class StateVectorizer:  17차원 관측 벡터 생성 — 유일한 정본(P1)
    def __init__(): rsu_range/v_max(0이면 V_LIMIT로 대체)/a_max/queue_max 저장
    def state_dim (property): STATE_DIM을 반환 — 하드코딩 대신 이걸 읽으라는 계약
    def _extract_queue_count(): 명시적 n_queue 키 우선, 없으면 leader_gap/leader_speed로 근사 폴백
    def _compute_heading(): 속도벡터·RSU상대좌표의 코사인으로 접근(+1)/이탈(-1) 지표 계산
    def vectorize(): 노드 객체(vehicle_node/rsu_node)로부터 17차원 벡터 생성 — 테스트 전용 경로(운영 미사용, 구조 참조)
    def vectorize_from_dict(): 상태 딕셔너리로부터 17차원 벡터 생성 [핵심] 실제 파이프라인이 쓰는 유일한 벡터화 경로

class ActionDecoder:  하이브리드 액션(Δ, ch, p) 디코더/인코더
    def __init__(): num_channels/delta_min/delta_max/p_min/p_max 저장, 기하 매핑용 log(delta_max/delta_min) 계산
    def delta_from_unit(): u∈[0,1] → Δ 기하 매핑 (delta_min·exp(u·logratio)) [핵심] 설계서 승인 매핑, 9종 baseline이 실제로 쓰는 함수
    def unit_from_delta(): delta_from_unit의 역함수
    def _sigmoid/_logit (staticmethod): 표준 시그모이드/로짓
    def decode_action(): 원시 액션(dict/list/tensor)을 (Δ,ch,p)로 디코딩 — Δ를 **선형** 보간으로 매핑 (결함 참조)
    def encode_action(): (Δ,ch,p) → 원시 로짓 인코딩, decode_action과 동일한 선형식의 역함수(자기 일관적 쌍)

class RetrospectiveReplayBuffer:  SMDP 가변 할인 리플레이 버퍼 [핵심] γ^Δ 지원
    def __init__(): capacity/gamma 저장, 링버퍼 초기화
    def push(): (s,a,r,s',done,Δ,action_idx?) 저장, capacity 초과 시 순환 덮어쓰기
    def sample(): 무작위 배치 샘플링, discount=gamma**delta_t 계산 [핵심] 가변 할인 실제 적용 지점
    def is_ready(): 배치 크기 이상 쌓였는지
    def clear(): 버퍼 비우기
    def __len__(): 현재 저장 개수
```

## coder/src/hot_swap_trainer.py

```
def infer_state_dim(): StateVectorizer에서 관측 차원을 동적으로 읽음 (속성 탐색 → 빈 딕셔너리 프로브 → 최후 폴백 18) [핵심] 하드코딩 방지용 정본 조회. 폴백값 18은 결함 참조
def select_default_devices(): GPU 개수에 따라 (act_device, rest_device) 결정 — 멀티GPU면 분리, 아니면 공유

class DualModelHotSwapManager:  Act/Rest 모델 무중단 원자적 파라미터 교체
    def __init__(): act/rest 모델·디바이스·swap_lock 저장
    def validate_weights(): Rest 모델 파라미터·버퍼에 NaN/Inf 있는지 검사 [핵심] 안전 가드
    def hot_swap(): 검증 통과 시 mutex 하에 Rest→Act로 파라미터·버퍼 원자적 복사
    def get_stats(): swap 횟수/실패/평균·최대 지연시간 반환

class TransitionStreamer:  시뮬레이션→학습 스레드 간 비차단 큐
    def __init__(): maxsize 큐 생성
    def push(): 튜플을 dict로 감싸 non-blocking 큐잉, 가득 차면 drop
    def push_dict(): 미리 만든 dict를 그대로 큐잉 — 코드베이스 어디서도 호출되지 않음(결함 참조)
    def drain(): 큐에서 non-blocking으로 최대 N개 꺼냄
    def push_to_buffer(): drain한 항목을 ReplayBuffer.push로 이전 [핵심] 백그라운드 학습의 유일한 주입 경로
    def qsize/is_empty/clear(): 큐 상태 조회/초기화

class BackgroundTrainer:  Rest 모델 비동기 그래디언트 갱신 + 주기적 hot-swap
    def __init__(): rest_model/buffer/streamer/hot_swap_manager/batch_size 등 저장, 손실 이력 ring buffer
    def train_step(): 큐 배수→버퍼, 배치 샘플→디바이스 이동→rest_model.update()→swap_interval마다 hot_swap 트리거 [핵심] 실제 학습 1스텝
    def _worker_loop(): stop_event까지 train_step을 반복하는 백그라운드 스레드 본체
    def start/stop(): 워커 스레드 시작/정지(join)
    def get_metrics(): 최근 손실 평균과 hot-swap 통계 반환

class HotSwapRLScheduler:  Act 모델 추론 전담, 상태/보상은 만들지 않음(P1) [핵심]
    def __init__(): act_model/hot_swap_manager/streamer/vectorizer/decoder 저장, state_dim은 vectorizer에서 추론
    def decide_grant(): 환경이 만든 관측 벡터로 act_model.select_action 호출, 폭 불일치 시 assert [핵심] 순수 추론만 수행 (과거엔 여기서 재벡터화+자체 보상 계산을 했던 이중 정본 결함이 있었음, 지금은 제거됨)
    def push_transition(): 환경이 계산한 reward/delta_t를 그대로 streamer에 전달 (Δ 재계산 금지)
    def reset(): 추론 지연시간 이력 초기화
    def get_latency_stats(): 추론 지연시간 평균/50/95/99 퍼센타일

class HotSwapTrainer:  Act/Rest 모델 생애주기 마스터 오케스트레이터
    def __init__(): model_cls로 act/rest 인스턴스화, 디바이스 배치, hot_swap_manager/replay_buffer/streamer/background_trainer/scheduler 조립, 초기 Rest→Act 동기화
    def start/stop(): 백그라운드 학습 워커 시작/정지
    def step_training_sync(): 동기 방식으로 학습 1스텝 실행 (테스트/디버그 경로, 메인 루프는 비동기 사용)
    def save_checkpoint(): act/rest state_dict, 스텝/스왑 카운트, best_reward를 torch.save
    def load_checkpoint(): 체크포인트 복원, 카운터 복구

class AoiV2IEnv:  SUMO 실제 연동 환경. 관측·보상의 유일한 정본(D1) [핵심]
    def __init__(): density/seed/max_steps/warmup_steps/w1~w4 저장, vectorizer/decoder 생성, I_redundant·재시도·ledger 상수 정의(3.2m/10회/1.0s) [핵심]
    def _init_sumo(): make_sumo_files()로 SUMO 파일 재생성 후 libsumo.start, step_length를 SUMO에서 역으로 읽어옴
    def reset(): 전 상태 초기화, warmup_steps만큼 simulationStep 진행 후 가장 붐빈 RSU를 target으로 선정 [핵심] warmup 부족 시 관측 0건(과거 결함)
    def _count_active_vehicles(): RSU 반경 내 차량 수, sim_time 기준 캐싱 — 피처[13]
    def _get_vehicle_state_dict(): SUMO에서 위치/속도/가속도/TLS/CBR/n_active/n_queue 등 단일 상태 딕셔너리로 추출 [핵심] 관측이 만들어지는 유일한 지점
    def _ledger_queue_count(): RSU 장부 기반 n_queue, 신선도 가드(freshness OR 정지+적색) 적용 [핵심] D3 구현
    def _is_redundant_update(): 갱신 시점 오차 ≤ 3.2m 이면 1.0 (D6, "예측이 맞았으면 중복")
    def _register_vehicle(): 신규 차량의 장부 항목 개설(last_pred_err=0, lane 정보, was_stopped)
    def _get_observations(): 모든 활성 차량에 대해 vectorize_from_dict 호출 [핵심] 관측 벡터가 나가는 유일한 지점(P1)
    def _finalize_interval(): SMDP 구간 종료, D2 4항 보상 계산·재유도 검증용 record 반환 [핵심]
    def step(): 신규 결정 등록→만료된 grant 발화→SUMO 스텝→4개 안티모킹 단언→CBR 계산→오차 누적→judge_uplink로 성패 판정→재시도/포기 처리→보상 재유도 단언 [핵심] 이벤트 구동 SMDP 루프의 심장
    def get_metrics(): mean/peak/mean_peak AoI, packet loss, 오차, 전력, 에너지, Jain 공정성, n_observations 등 IEEE TWC 지표 산출
    def close(): libsumo 종료

def run_hot_swap_training(): 200k 스텝급 전체 학습 루프 — Act 서빙 + 백그라운드 학습 + TensorBoard + 체크포인트 + resume 지원 [핵심] 이벤트 구동 SMDP 루프(직접 구현, gym 아님)
```

---

# 산출물 2: 결함 검토

## [중대] `total_energy_joules` 계산에 잘못된 상수 시간을 사용 — 값이 체계적으로 왜곡됨
`src/hot_swap_trainer.py:1669`
```python
total_energy_j = float(sum(10.0 ** ((p - 30.0) / 10.0) * 0.001 for p in self.tx_powers))
```
`10**((p-30)/10)`은 dBm→Watt 변환식으로 그 자체가 이미 정확한 Watt 값이다(예: 23 dBm → 0.1995 W, 실제 802.11p 전력계급과 일치). 에너지(J) = 전력(W) × 지속시간(s)이 되려면 이 값에 실제 전송 지속시간을 곱해야 하는데, 곱해진 `0.001`은 근거 없는 리터럴이다. 같은 클래스가 이미 `self.frame_airtime_s = comm.frame_airtime_s(self.payload_bytes)`로 실측 프레임 에어타임(448 µs = 0.000448 s, `hot_swap_trainer.py:794`, CBR 계산에도 실제로 쓰임 — `1388`)을 정본으로 갖고 있음에도 그것을 쓰지 않았다. 0.001s vs 실제 0.000448s이므로 **`total_energy_joules`는 약 2.23배 과대평가**된다. 이 지표는 설계서 7절 "지표" 표에서 "실측/정상"으로 분류돼 있으나 실제로는 정상이 아니다. 논문 결과표에 그대로 실리는 값이므로 심각도 [중대].
**수정 방향(제안, 코드 미수정)**: `10.0 ** ((p - 30.0) / 10.0) * self.frame_airtime_s`.

## [중대] Δ 상한/속도 정규화 상수가 "실행 시점의 실제 시나리오"가 아니라 "임포트 시점에 디스크에 있던 파일"에서 고정됨
`src/rl_interface.py:110` (`DELTA_MAX = get_sumo_max_red_phase_duration()`), `:155` (`V_LIMIT = get_sumo_max_edge_speed()`), `:170` (`E_REF = V_LIMIT * 1.0`) — 전부 **모듈 임포트 시 1회만 평가되는 top-level 대입문**이다.
반면 `AoiV2IEnv._init_sumo()`(`hot_swap_trainer.py:882`)는 매 에피소드마다 `ss.make_sumo_files()`를 호출해 `generated.net.xml`을 **새 시드로 재생성**하고, `make_sumo_set.py:329-333`은 그 안에서 엣지 속도를 `random.uniform(SPEED*(1-0.2), SPEED*(1+0.2))`로 매번 다시 뽑는다. 즉 설계서 9절이 "이 구성의 강점"이라고 명시한 "net.xml에서 자동 추출해 시나리오를 항상 따라간다"는 주장이 실제로는 **파이썬 프로세스가 시작될 때 우연히 디스크에 있던 net.xml 한 장**만 반영하고, 이후 어떤 에피소드가 실제로 어떤 net.xml로 시뮬레이션되든 `DELTA_MAX`/`V_LIMIT`/`E_REF`는 갱신되지 않는다.
실측 확인: 현재 체크인된 `generated.net.xml`(240개 엣지)에서 `get_sumo_max_edge_speed()=13.32`, `get_sumo_max_red_phase_duration()=45.0`으로 설계서 수치와 일치했다 — 이는 엣지가 많아 균등분포 상한(13.32)에 수렴하는 통계적 우연이지 코드가 보장하는 성질이 아니다. `generated.net.xml`이 아예 없거나(첫 체크아웃), 다른 목적으로 먼저 생성된 net.xml이 남아 있는 상태로 학습을 시작하면 훈련 내내 실제 시나리오와 다른 상수로 정규화/액션 범위가 고정된다. [확인필요]로 낮출 수도 있으나, "정본은 net.xml"이라는 설계 원칙이 코드상 지켜지지 않는 구조적 결함이므로 [중대]로 보고한다.

## [중대] `ActionDecoder.decode_action()`이 자신의 클래스 독스트링과 반대로 **선형** Δ 매핑을 구현 — 폴백 경로에서 조용히 잘못된 해상도로 빠질 수 있음
`src/rl_interface.py:442-471`(클래스 독스트링)은 "Delta mapping is GEOMETRIC, not linear"라고 명시하고 `delta_from_unit`의 지수식을 근거로 제시한다. 그런데 같은 클래스의 `decode_action()`(`:548-550`)은
```python
sig_d = self._sigmoid(float(raw_delta))
delta = self.delta_min + sig_d * (self.delta_max - self.delta_min)
```
로 **선형 보간**을 한다. `delta_from_unit`(기하, 설계서 3절이 승인한 유일한 매핑)과 `decode_action`(선형)은 서로 다른 공식을 갖는 별개의 경로다.
`grep` 대조 결과 실제 운영 경로에서는 baseline 9종의 `select_action`이 이미 `delta_from_unit`으로 직접 디코딩한 3-튜플 grant를 만들어 `env.step(action_dict)`에 넘기고, `hot_swap_trainer.py:1256` `step()`은 `isinstance(raw_act, (tuple, list)) and len==3` 분기로 그것을 그대로 받아쓰므로 **현재는 `decode_action`이 학습 경로에서 호출되지 않는다**(`hot_swap_trainer.py:1282`의 `decode_action` 호출은 그 분기가 실패할 때만 실행되는 폴백). 즉 지금 당장 결과를 왜곡하지는 않지만, (a) 클래스 자신의 문서와 공개 메서드 구현이 모순되고 (b) 향후 새 baseline이 3-튜플이 아닌 원시 로짓을 그대로 넘기거나 `contract_adapters.py`류 테스트 더블이 이 경로를 타면, 어떤 에러도 없이 "우연히 선형으로 디코딩된 Δ"가 조용히 흘러들어간다. 설계서 3절이 강조한 "선형이면 0.5s 방출에 u≈0.0089 필요 → 해상도 붕괴" 문제가 그대로 재현되는 함정이다. 심각도는 현재 미발현이라 [중대]로 완화해 보고(치명 아님)하되, 문서·구현 불일치 자체는 실재하는 결함이다.

## [경] `REDUNDANT_POS_EPS_M`가 계산은 되지만 어디서도 읽히지 않음 — 주석의 "쓰인다"는 주장이 거짓
`src/hot_swap_trainer.py:770` `self.REDUNDANT_POS_EPS_M = 0.1`. 정의 시 주석(`:769`)은 "Kept for the standstill diagnostics reported in get_metrics()"라고 적혀 있으나, 전체 파일에서 `REDUNDANT_POS_EPS_M`는 정의문(`:770`)과 그 위 설명 주석(`:747`) 두 곳에만 등장하고 `get_metrics()`를 포함해 어디서도 참조되지 않는다(grep 확인). "저장만 되고 읽히지 않는 값" 패턴이며, 주석이 실제로 없는 소비처를 있다고 주장하는 점에서 향후 개발자를 오도할 수 있다.

## [경] `TransitionStreamer.push_dict()`가 코드베이스 전체에서 호출되지 않는 죽은 공개 메서드
`src/hot_swap_trainer.py:275-282`. `grep -rn "push_dict"` 결과 정의 지점 외 호출부가 전무하다(운영 코드·테스트 모두). 기능 자체는 정상으로 보이나 실제로 쓰이지 않는 API 표면.

## [경] 여러 곳의 독스트링/주석이 Δ 상한을 옛 값 "[0.1, 5.0] s"로 잘못 기술
- `src/rl_interface.py:9` (모듈 헤더 주석)
- `src/hot_swap_trainer.py:733` ("Delta in [0.1, 5.0] s, p in [10, 23] dBm")
- `src/hot_swap_trainer.py:696` (AoiV2IEnv 클래스 독스트링, 동일 문구)
실제 `DELTA_MAX`는 net.xml에서 동적으로 유도되어 45.0 s이고 액션 하한도 0.1 s는 맞지만 상한이 5.0이 아니라 45.0이다(design_spec_v2.md 3절과도 불일치). 계산 자체는 옳게 45.0을 쓰고 있어 동작에는 영향 없지만, 코드를 처음 읽는 사람에게 잘못된 액션 공간 폭을 각인시키는 반복된 오기다.

## [경] `AoiV2IEnv` 클래스 독스트링의 보상식이 D2 확정본이 아니라 예전 순간보상식
`src/hot_swap_trainer.py:697-700`:
```
Reward (Conversation.md section 3, approved ground truth):
    R_t = -( w1*Norm(e_t^2) + w2*Norm(P_tx) + w3*Norm(C_freq) + w4*I_redundant )
```
실제 구현(`_finalize_interval`, `:1200` 주석)은 design_spec_v2 D2가 확정한 "오차항만 구간 누적, 나머지 3항은 갱신 1회 임펄스" 형태(`R_k = -(w1·Σ Norm(e^2)·dt/1s + w2·Norm(P_tx) + w3·Norm(C_freq) + w4·I_red)`)이며 코드는 이를 올바르게 따른다. 클래스 상단 독스트링만 SMDP 재설계 이전의 순간보상식을 그대로 남겨 문서와 코드가 어긋난다.

## [경] `StateVectorizer` 클래스 독스트링이 "18-dimensional"이라 명시 — 실제 `STATE_DIM=17`과 불일치
`src/rl_interface.py:191` `"""18-dimensional normalized State Vectorizer."""`. 바로 아래 피처 목록은 `[0]~[16]`으로 17개가 정확히 나열되어 있어 실질 구현과 표는 맞지만 첫 줄의 숫자만 옛 값(D4 이전, stop_imminent 제거 전)으로 남아 있다.

## [경] `infer_state_dim()`의 최후 폴백이 옛 차원 18을 반환 — 정상 경로에서는 도달하지 않지만 값 자체가 stale
`src/hot_swap_trainer.py:91-95`:
```python
try:
    return int(len(vec.vectorize_from_dict({}, (0.0, 0.0))))
except Exception:
    # Last-resort fallback: the canonical design dimension (...16 base + n_queue + heading)
    return 18
```
`StateVectorizer.STATE_DIM=17` 클래스 속성이 있으므로 정상적으로는 함수 최상단의 속성 탐색 루프에서 17을 반환하고 이 폴백에는 도달하지 않는다. 다만 벡터라이저가 커스텀 서브클래스로 교체되어 속성도 없고 `vectorize_from_dict`도 예외를 던지는 극단적 상황이라면 17이 아닌 18이 조용히 반환된다. 사실상 도달 불가능에 가깝지만 값 자체가 D4 이전 것이라 방치하면 위험하다.

## [확인필요] 전송 실패가 재시도 상한(`MAX_TX_RETRIES=10`)에 도달해 구간이 강제 종료될 때 `transmitted=True`로 처리되어 전력·혼잡·중복 3항이 전부 과금됨
`src/hot_swap_trainer.py:1556-1565`. 10회 연속 실패 후 포기하는 마지막 전송도 `_finalize_interval(..., transmitted=True, ...)`로 넘어가 성공한 갱신과 동일하게 `r_power`/`r_cong`/`r_red`가 계산된다. 전력·혼잡은 "시도만으로 소모되는 비용"이라는 설계 취지(D2 표: "갱신 1회당 발생")에 부합한다고 볼 여지가 있으나, `_is_redundant_update`가 이때 쓰는 `err_at_update_m`은 "실제로 갱신이 들어간" 오차가 아니라 "끝내 갱신되지 못한 현재 추정오차"다. 이 값을 근거로 "중복 갱신"이라 부르는 것이 설계자의 의도인지 design_spec_v2.md에 명시적 문구가 없어 판단이 애매하다. 결함이라 단정하지 않고 확인 필요로 표시한다.

## [확인필요] `reset()`의 `.nod.xml` 파싱 실패를 `except Exception: pass`로 삼킴
`src/hot_swap_trainer.py:961-964`. RSU 노드/네트워크 경계 파싱이 실패하면 조용히 넘어가고 생성자 기본값(`target_rsu_pos=(1200,10800)`, `network_max_x/y=50000`)을 그대로 쓴다. 합리적인 방어적 폴백으로 보이나, 실제 net.xml 포맷이 바뀌어 파싱이 매번 실패하는 상황도 같은 방식으로 조용히 통과되므로 완전히 결백하다고 단정하기는 어렵다.

## 결함 아님으로 확인한 항목 (참고용)
- 오차항 시간 누적(`interval_accum`), `norm_sq_error`를 통한 D5 정규화, `_is_redundant_update`의 D6 재정의, `_ledger_queue_count`의 D3 신선도 가드, `MAX_TX_RETRIES`/`LEDGER_FRESH_S`/`REDUNDANT_ERR_EPS_M` 상수값은 모두 design_spec_v2.md 8·9절과 정확히 일치함을 확인했다.
- `RetrospectiveReplayBuffer.sample()`의 `gamma**delta_t` 가변 할인은 실제로 동작한다(설계서 1절이 우려한 "Δ=0.1 상수라 무의미" 상태가 이미 해소됨, delta_t가 다양한 값을 가짐을 코드 구조상 확인).
- `ActionDecoder.encode_action()`과 `decode_action()`은 서로 다른 (선형) 매핑을 쓰지만 이 둘끼리는 정확히 역함수 관계라 왕복 인코딩은 일관된다. 문제는 이 쌍과 `delta_from_unit`/`unit_from_delta` 쌍(기하)이 서로 다른 공식이라는 점이며, 이는 위 [중대] 항목에서 별도로 다뤘다.
- `StateVectorizer.vectorize()`(노드 객체 기반)는 운영 파이프라인에서 전혀 호출되지 않고 테스트에서만 쓰인다. `vectorize_from_dict()`와 로직이 중복 구현되어 있어 유지보수 시 한쪽만 고칠 위험(P1 취지에 반하는 잠재 리스크)이 있으나, 현재 두 구현이 서로 어긋나 있지는 않음을 확인했다 — 결함으로 단정하지 않고 구조 요약에만 기록.
