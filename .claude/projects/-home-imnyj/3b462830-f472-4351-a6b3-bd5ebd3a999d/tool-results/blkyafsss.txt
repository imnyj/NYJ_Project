# Critic 리뷰 — 물리 계층 & 시나리오 생성

검토자: Critic 에이전트 (읽기 전용, 수정 없음)
검토일: 2026-08-30
기준 설계: `/home/imnyj/Workspace/paper4/idea/design_spec_v2.md`
검토 대상: `src/Communications.py`, `src/sumo/make_sumo_set.py`, `src/dynamics_predictor.py`,
`src/NetSim.py`, `src/heuristic_scheduler.py`, `src/model.py`

모든 주장은 실제 파일을 읽고(cat -n), 필요한 경우 `/home/imnyj/venv/bin/python3`로 직접 재계산하고,
`grep -rn`으로 생산자/소비자 양쪽을 확인한 뒤 작성했다.

---

## 산출물 1: 코드 구조 요약

### coder/src/Communications.py
**현재 파이프라인에서 쓰이는가?** 부분적으로 쓰인다. 실제 학습·평가·HPO 경로
(`src/hot_swap_trainer.py`, `src/hpo.py`, `src/heuristic_scheduler.py`)는 이 파일의
**PHY 함수 군**(`judge_uplink`, `frame_airtime_s`, `NUM_SUBCHANNELS`, `STATUS_UPDATE_BYTES` 등)을
직접 import해서 쓴다. 반면 파일 상단의 "Wi-Fi channel manager (802.11ac/ax)" 블록과
델레이/처리량 헬퍼(`wifi_transmission_delay`, `fiber_*`, `relay_bytes_per_step` 등)는
**레거시 `src/NetSim.py`/`src/aoi_env.py` 전용**이며 실제 학습 경로에서는 소비되지 않는다
(아래 함수별 표에 표시).

```
# 물리 상수 (파일 상단)
C_LIGHT, REFRACTIVE_INDEX_FIBER, FIBER_PROPAGATION_SPEED : 광섬유 구간 계산용. 학습 경로 미사용(NetSim 전용)
MAX_FRAME_SIZE, FRAG_LIMIT, STREAM_THRESHOLD             : NetSim 프레임 단편화 임계값. 학습 경로 미사용

class WiFiChannelManager                                  : [NetSim 전용, 학습 경로 미사용] 802.11ac 다중접속 채널 추상화
    def __init__()          : 채널 수(3)·MCS9~기본레이트 사다리·용량 상한 초기화
    def _rate_per_user()    : 동시 사용자 수만큼 레이트 사다리 인덱싱, 넘으면 2배씩 감쇠
    def _sum_rate_if_add_one(): 사용자 1명 추가 시 채널 합산 레이트와 추가 유저 레이트를 계산
    def allocate()          : 가장 여유 있는 채널을 골라 새 전송을 배정, 없으면 최소 부하 채널에 강제 배정
    def release()           : 채널에서 전송 1건 반환(스택 pop)
wifi_channel_manager (전역 싱글턴)                          : NetSim.Node.send_packet()이 참조하는 공용 매니저

def fiber_propagation_delay()      : 거리/광섬유 전파속도 = 전파지연(s). NetSim 전용
def wifi_propagation_delay()       : 거리/광속 = 전파지연(s). NetSim 전용
def wifi_transmission_delay()      : 프레임 비트수/데이터레이트 = 전송지연(s). NetSim 전용
def fiber_data_rate()              : Gbps -> bps 변환. NetSim 전용
def wifi_data_rate()               : Mbps -> bps 변환. NetSim 전용
def data_per_step()                : 스텝 동안 전송 가능한 바이트 수. 미사용(호출처 없음 — 죽은 함수)
def adjusted_bytes_per_step()      : 전파지연을 뺀 가용시간 기준 전송 가능 바이트. 미사용(호출처 없음 — 죽은 함수)
def fiber_fetch_bytes_per_step()   : 멀티홉 광섬유 페치의 스텝당 바이트. NetSim 전용, 학습 경로 미사용
def relay_bytes_per_step()         : Wi-Fi+광섬유 릴레이의 유효 레이트로 스텝당 바이트 계산. 미사용(호출처 없음 — 죽은 함수)

# --- Uplink PHY 모델 (S2) : 실제 학습 경로가 쓰는 부분 ---
FREQ_HZ, PL_EXP, _PL_REF_DB, NOISE_FIGURE_DB               : 링크버짓/잡음바닥 상수 (아래 물리상수 표 참조)
NUM_SUBCHANNELS, SUBCHANNEL_BW_HZ, TOTAL_BW_HZ             : 802.11p 10MHz x 4채널 = 40MHz
G_TX_DBI, G_RX_DBI                                         : 차량/RSU 안테나 이득
SHADOWING_SIGMA_DB                                         : 로그노멀 섀도잉 표준편차
TX_POWER_LEVELS_DBM                                        : [명시적으로 주석에 "레거시 aoi_env 전용, 여기서 링크버짓 읽지 말 것"으로 표기됨] 실제 aoi_env.py에서만 사용

OFDM_SYMBOL_TIME_S, PREAMBLE_SIGNAL_TIME_S, SERVICE_BITS, TAIL_BITS : 802.11p OFDM 프레이밍 상수
STATUS_UPDATE_BYTES                                        : ETSI CAM 페이로드 300B. hot_swap_trainer가 그대로 참조(정본)

@dataclass Mcs                                             : 802.11p MCS 1건 (레이트/변조/코드레이트/심볼당비트/요구SINR)
MCS_TABLE                                                  : 3~27 Mbps 8단 MCS 표
OPERATING_RATE_MBPS                                        : 실제 운용 레이트 6 Mbps (QPSK 1/2) — 이 상수 하나로 임계값/에어타임/민감도가 전부 연동

def get_mcs()                : 레이트로 Mcs 조회, 없으면 ValueError
SINR_TH_DB (모듈 로드시 계산) : get_mcs(OPERATING_RATE_MBPS).req_sinr_db 에서 유도 (10.0 dB)

def _db_to_lin()              : dB -> 선형 변환
def dbm_to_mw()                : dBm -> mW 변환
def path_loss_db()             : PL(d) = PL(1m) + 10*n*log10(max(d,1)) — d<1m은 1m으로 클램프(로그 발산 방지)

_DEFAULT_CHANNEL_SEED, _shadow_rng : 섀도잉/오버랩 전용 독립 RNG(전역 random과 분리, 결정성 보장)
def seed_channel()            : 섀도잉 RNG 재시드 (에피소드 리셋 시 호출)
def draw_shadowing_db()       : 로그노멀 섀도잉 1개 샘플(dB), sigma<=0이면 0
def draw_overlap()            : 취약구간 겹침 여부를 베르누이 확률(2*Tair/Tstep)로 판정

def rx_power_dbm()             : Ptx + Gtx + Grx - PL(d) - shadow
def rx_power_mw()               : 위 dBm값을 mW로 변환
def noise_floor_dbm()           : -174 + 10log10(BW) + NF
def noise_floor_mw()            : 위 dBm값을 mW로. 인자로 받은 num_subchannels로 TOTAL_BW_HZ를 나눠 대역폭 재계산(아래 결함 참조)
def sensitivity_dbm()           : 노이즈플로어 + 요구SINR = 수신 감도

def frame_symbols()             : (SERVICE+8*payload+TAIL) 비트를 MCS의 N_DBPS로 나눠 올림 = 심볼 수
def frame_airtime_s()           : 프리앰블(40us) + 심볼시간(8us)*심볼수 = 에어타임(s)
def phy_data_rate_bps()         : MCS 레이트를 bps로 변환

def rayleigh_success_prob()     : P(SINR>=th) 닫힌형: exp(-th*N0/S) * Π 1/(1+th*Ik/S) — Rayleigh 신호·간섭 모두에 대해 유효한 표준식
def judge_uplink()              : 그룹(동일 서브채널) 내 모든 링크에 대해 섀도잉 샘플링 후 상호 SINR 성공확률 딕셔너리 반환. hot_swap_trainer의 최종 성공 판정 지점
```

### coder/src/sumo/make_sumo_set.py
**현재 파이프라인에서 쓰이는가?** 그렇다. `src/hot_swap_trainer.py`, `src/hpo.py`,
`src/rl_interface.py`, `src/aoi_env.py`(레거시), `verify_environment.py` 등이 `import
src.sumo.make_sumo_set as ss` 형태로 모듈 전역 변수(`ss.RSU_RANGE`, `ss.DENSITY` 등)를 직접
읽고 쓰며 `ss.make_sumo_files()`를 호출한다. **정본(single source of truth)** 역할.

```
# 제어 변수 (모듈 전역, 외부에서 직접 override됨)
OUTAGE_ZONE      : RSU 커버리지 사이 미보급 구간 길이 (300 m)
AV_SPEED         : 평균 속도 km/h (40.0). 0이면 에피소드마다 임의 설정
DENSITY          : 평균 밀도 (/1km-lane, 20.0). 0이면 임의
P_GEN            : 차량 생성 확률(파생값, CalcP_GEN이 갱신)
NUM_BLOCKS       : 격자 블록 수 (6)
MAX_STEPS        : 흐름 종료 시각 (3600.0 s) — sumocfg의 <end>(360000)와는 별개 값(아래 결함 참조)
CORNER_SPEED_LIMIT: 교차로 회전 속도 제한 (50 km/h)
STEP_LENGTH      : SUMO 해상도 (0.1 s), 액션 최소 Δ와 동일해야 함(주석에 명시)

# 파생 환경 변수
RSU_RANGE        : RSU 통신반경 (300 m, "5.9GHz 도심 NLOS 200-300m 실측 범위" 근거 명시)
EDGE_LENGTH      : RSU_RANGE*2+OUTAGE_ZONE = 900 m (RSU간 거리)
GRID_SIZE        : NUM_BLOCKS * EDGE_LENGTH
NUM_LANES        : 2
SPEED            : AV_SPEED/3.6 (m/s)
DEL_SPEED        : 속도 편차 비율 (0.2)
MAX_SPEED        : (120/3.6)*(1+0.2) — 계산되지만 어디에도 소비되지 않음(죽은 값, 아래 결함 참조)
step             : GRID_SIZE/NUM_BLOCKS (블록 간격)
T_to_INIT, L_tot, L_path_avg : CalcP_GEN 내부에서 갱신되는 트래픽공식 중간값. 외부 소비처는 NetSim.py(레거시)뿐

def _atomic_write_text()        : 문자열을 임시파일에 쓰고 os.replace로 원자적 교체
def _atomic_write_tree()        : ElementTree를 동일한 방식으로 원자적 저장
def _is_valid_xml_file()        : 파일 존재·비어있지 않음·XML 파싱 가능 여부 확인
def are_sumo_files_valid()      : 7종 필수 SUMO 파일 전부 유효한지 확인
def current_generation_signature(): 현재 파라미터 스냅샷(dict) 생성 — 캐시 재사용 판단 기준
def _read_generation_signature() : 저장된 시그니처 JSON 로드
def _write_generation_signature(): 현재 시그니처를 JSON으로 기록
def generation_signature_matches(): 캐시된 파일이 현재 파라미터와 일치하는지 (MAX_STEPS는 "이상"이면 통과)
def CalcP_GEN()                  : 밀도(density)로부터 흐름 생성확률 P_GEN을 역산 (트래픽 공식, 아래 확인필요 참조)
def make_dead_end_nodes()        : netfile을 파싱해 지정된 경계 노드를 dead_end로 표시 후 재저장
def _generation_lock()           : 여러 프로세스의 동시 생성 경쟁을 막는 flock 컨텍스트 매니저
def _make_sumo_files_impl()      : 노드/엣지/넷/애드온/경로/POI/설정 7종 파일을 실제로 생성하는 본체
    (내부) _make_axis_positions() : 격자 X/Y축 좌표 계산 (첫/끝 블록만 절반 간격)
    (내부) generate_nodes_edges() : 노드·양방향 엣지 문자열 리스트 생성, 코너는 dead_end/traffic_light로 태깅
def make_sumo_files()            : 락을 획득한 뒤 _make_sumo_files_impl 호출(공개 진입점). 락 밖에서 먼저 캐시 적중 검사(빠른 경로)
```

### coder/src/dynamics_predictor.py
**현재 파이프라인에서 쓰이는가?** 그렇다. `src/heuristic_scheduler.py`, `src/hot_swap_trainer.py`,
`src/rl_interface.py`가 `extract_tls_features`를 직접 import해서 쓴다.

```
def predict_stop_imminent()   : 급감속(accel<=-1.2 & 정지시간<=5s 등) / 적·황신호 접근(제동거리 이내&잔여>1s) /
                                 앞차 정지 접근(gap<=max(10,2.5v)&leader_speed<=1) 중 하나면 I_stop=1.0, 이미 정지(<=0.3)면 0.0
def predict_start_imminent()  : 정지/서행 중(<=1.5) 상태에서 녹색+정지선 근접or대기중 / 적신호지만 곧 녹색(<=2s)&근접 /
                                 앞차 출발 / 스스로 가속(>=0.6) 중 하나면 I_start=1.0

HALTING_SPEED_THRESHOLD        : SUMO의 "정차" 정의(0.1 m/s)를 그대로 재사용 — n_queue와 SUMO 통계 정의 일치시킴

def extract_queue_features()   : TraCI로 ego 차선의 앞차 수(n_ahead)와 그 중 정차 중인 수(n_queue), 차선 전체 정차수/차량수 측정
def extract_tls_features()     : 속도·가속도·대기시간·리더차량 정보·다음 신호등(거리/상태/잔여시간)·I_stop·I_start·큐 정보를 한번에 종합해 dict로 반환. 예외 시 안전한 default_res로 폴백

class DynamicsPredictor         : TraCI 커넥션을 감싸는 얇은 헬퍼
    def __init__()              : sumo_conn 저장
    def get_features()          : extract_tls_features 위임
    def get_queue_features()    : extract_queue_features 위임(더 저렴한 큐 전용 조회)
    def get_n_queue()           : n_queue 정수만 반환
    def is_transition_imminent(): (I_stop>=0.5 or I_start>=0.5) 여부와 두 지표값을 튜플로 반환
```

### coder/src/NetSim.py
**현재 파이프라인에서 쓰이는가? 아니다.** `grep -rn "import.*NetSim"`으로 확인한 결과, 실제
학습/평가/HPO 경로(`hot_swap_trainer.py`, `rl_interface.py`, `evaluate.py`, `hpo.py`)는 이 파일을
전혀 import하지 않는다. 이 파일을 import하는 곳은 `src/aoi_env.py`(설계문서 D1에서
**"폐기"로 확정된 레거시 정본**), 그리고 저장소 최상위의 `8. V2V Precaching.py` 뿐이다.

`8. V2V Precaching.py`를 읽어보면 이 파일이 무엇인지 바로 드러난다 — 첫 줄 주석에
"이 예제는 V2V Precaching in Outage zone 논문을 기반으로 작성되었습니다"라고 명시되어 있다.
즉 **NetSim.py는 이번 AoI RL V2I 스케줄링 논문이 아니라, 이전/별도의 "outage zone에서의
V2V 콘텐츠 프리캐싱" 연구를 위해 만든 범용 이벤트 구동 네트워크 시뮬레이터**다. 802.11ac
Wi-Fi 채널매니저, 프래그멘테이션, 스트리밍, 광섬유 백홀 등 콘텐츠 딜리버리에 필요한
기능을 갖췄지만, 이번 AoI 스케줄링 문제(SMDP, 802.11p 업링크, Rayleigh SINR)에는 맞지 않아
`Communications.py`의 "Uplink PHY 모델 (S2)" 섹션이 별도로 신설되었고, 학습 루프는 `hot_swap_trainer.py`가
libsumo를 직접 구동하는 자체 이벤트 루프로 재작성되었다. NetSim.py는 그 이전 세대의 산출물이
그대로 남아 있는 것이며, 현재 아무 데도 연결되지 않은 **고아 모듈**이다(단, 완전히 죽은 것은
아니고 레거시 `aoi_env.py`와 무관한 옛 예제 스크립트가 계속 참조한다).

```
class Packet (dataclass)        : 패킷(타입/출발/도착/페이로드/크기/프래그먼트 메타)
def _fraction_inside_range()    : 이진탐색으로 두 지점 사이에서 반경 R을 벗어나는 지점 비율 추정
class PacketType (Enum)         : HELLO/REQUEST/DATA/ACK/PRECACHE/REPORT

class Node
    def __init__()              : id/위치/통신반경/RSU·서버 플래그/프래그먼트버퍼/속도이력 큐 초기화
    def distance_to()           : 유클리드 거리
    def send_packet()           : 크기별로 프래그먼트/스트리밍 분기 후 Wi-Fi 또는 광섬유로 전송 이벤트 예약
    def update_dwell()          : 훅(현재 아무 것도 안 함)
    def send_direct()           : 지연 없이 즉시 전달(테스트/직접경로용)
    def reset_runtime()         : 프래그먼트버퍼·이력 큐 초기화
    def _send_streaming()       : 대용량 페이로드를 스텝 단위로 분할 전송(범위 이탈 시 조기 종료 포함)
    def receive_packet()        : 프래그먼트 재조립 후 on_receive 호출
    def _fragment_packet()      : MAX_FRAME_SIZE 기준으로 패킷을 여러 조각으로 분할
    def on_receive()            : 패킷타입에 맞는 handle_* 메서드로 디스패치
    def broadcast()              : 통신범위 내 모든 노드에 브로드캐스트 전송
    def finding_rsu()            : 특정 핸들러를 가진 (RSU) 노드 탐색 후 전송
    def GetAvgSpeed()            : dwell 이력으로부터 평균 통과속도(km/h) 추정
    def GetAvgRate()             : 최근 세션들의 평균 전송률(Mbps)
    def GetVehiclesInRange()     : 통신범위 내 차량 id 목록
    def at_created()             : 노드 생성 훅(기본 no-op)

class Event                      : (시간, 핸들러, args) 이벤트 레코드, 힙 정렬용 __lt__
class EventSimulator
    def add_node()               : 노드 등록 + at_created 훅 호출
    def get_next_frag_id()       : 프래그먼트 ID 카운터
    def schedule_event()         : max_time 초과/정지 상태가 아니면 힙에 이벤트 push
    def _step_event()            : 다음 스텝 이벤트를 재귀적으로 예약
    def stop()                   : 시뮬레이션 강제 중단 플래그 설정
    def is_stopped (property)    : 중단 여부
    def run()                    : 이벤트 힙을 소진할 때까지 실행

class VehicleNode(Node), class RSUNode(Node) : handle_request no-op 스텁

def pre_define()                 : sumo_set 전역(RSU_RANGE/MAX_STEPS/OUTAGE_ZONE/NUM_BLOCKS/AV_SPEED/DENSITY)을
                                    이 레거시 실험용 값으로 덮어씀 — **주의: make_sumo_set.py 상단의 "정본" 값과
                                    다른 값(NUM_BLOCKS=5, AV_SPEED/DENSITY 난수)으로 재정의**
def InitSumoNetSim()             : pre_define 호출 + 클래스 등록(레거시 진입점)

class SumoNetSim
    def __init__()               : node/edge 파일 파싱, RSU 노드 생성, RSU 위치를 행렬 격자에 매핑
    def run()                    : 에피소드 루프 — SUMO 프로세스 기동, step_event로 차량 추적/신호 리라우팅/dwell 갱신

def GetSpeed/GetAcceleration/GetPosition/GetRoutes/GetNextRSU : TraCI 래퍼(예외 시 안전 기본값)
def _map_tls_state_char()        : R/Y/G 문자를 1/2/3 숫자로 매핑
def _match_tls_index_for_lane()  : 차선ID로 신호 링크 인덱스 역산
def _get_route_based_tls_index() : 차량 경로 기반으로 신호 그룹 인덱스 추정
def GetSignalState()             : 통신범위 내/외에 따라 TraCI 직접값 또는 경로기반 추정값으로 신호상태 반환
def GetSignalChangeTime()        : 다음 신호전환까지 남은 시간
```

### coder/src/heuristic_scheduler.py
**현재 파이프라인에서 쓰이는가?** 그렇다. `src/evaluate.py`가 베이스라인 정책으로 직접 사용하고,
다수의 테스트가 계약(contract) 검증에 사용한다.

```
class HeuristicScheduler
    def __init__()                    : Δ 최소/최대/순항구간, 3단계 전력(고/중/저), 서브채널 수, 라운드로빈 카운터 초기화
    def reset()                       : 채널 할당 카운터 초기화
    def _pick_least_loaded_channel()  : 할당 카운트가 가장 낮은 채널들 중 라운드로빈으로 하나 선택, 카운트 +1
    def decide_grant()                : (vid, state_dict) 또는 (state_dict) 두 시그니처 모두 지원.
                                         Rule1: I_stop/I_start>=0.5 → Δ=delta_min, p_high, 최소부하채널(즉시 재전송)
                                         Rule2: 정지+적/황+잔여>2s → Δ=min(delta_max, 잔여-1s), p_low(장시간 백오프)
                                         Rule3: 정지(그외)→Δ=2.0,p_low / 정속(|accel|<=0.3,v>3)→Δ=delta_cruise_steady,
                                         거리별 p_mid/p_high / 완만가감속→Δ=delta_cruise_accel,p_mid / 급가감속→Δ=1.0,p_high
```

### coder/src/model.py
**현재 파이프라인에서 쓰이는가? 아니다.** `grep -rln "src.model\|PPOAgent"` 결과 이 파일 자기 자신
외에 어디서도 import되지 않는다. TensorFlow/Keras 기반의 독립형 PPOAgent 구현으로, 실제 9종
베이스라인(`src/baselines/*.py`, PyTorch 기반, `BaseAgent`가 정본)에 의해 완전히 대체된
**죽은 파일**로 보인다.

```
class PPOAgent
    def __init__()          : 상태/행동 차원, 학습률, gamma/lambda/clip 등 PPO 하이퍼파라미터 저장 후 모델·버퍼 초기화
    def _build_models()     : Dense(128,128) 액터(로짓 출력)와 크리틱(가치 출력)을 Keras Functional API로 구성
    def _init_buffers()     : obs/act/rew/val/logp/done 버퍼를 빈 리스트로 초기화
    def get_action()        : 로짓→softmax→범주형 샘플링, log-prob과 크리틱 가치를 함께 반환
    def store_transition()  : 버퍼들에 전이 1건 append
    def finish_episode()    : GAE로 반환값/이점 계산 후 정규화, PPO-clip 손실로 여러 epoch 미니배치 업데이트, 버퍼 리셋
    def _compute_gae()      : 표준 GAE(λ) 역방향 재귀 계산
```

---

### 물리 상수 표 (값 · 근거 · 직접 재계산 검증)

| 상수 | 파일:줄 | 값 | 근거(주석/설계) | 직접 재계산 결과 |
|---|---|---|---|---|
| `FREQ_HZ` | Communications.py:175 | 5.9 GHz | US/EU ITS 5.9GHz 대역 | — |
| `PL_EXP` | Communications.py:176 | 2.3 | 반개방 도심도로 경로손실지수 | — |
| `_PL_REF_DB` (1m 기준 자유공간손실) | Communications.py:177 | 47.859 dB | Friis 공식 20log10(4πf/c) | 직접계산 47.8588 dB, 일치 |
| `NOISE_FIGURE_DB` | Communications.py:178 | 9.0 dB | RSU 수신기 잡음지수 | — |
| `NUM_SUBCHANNELS`/`SUBCHANNEL_BW_HZ` | Communications.py:182-184 | 4 / 10MHz | 802.11p 10MHz×4=40MHz(5.850-5.925GHz 대역에 맞음) | — |
| `G_TX_DBI` | Communications.py:188 | 3.0 dBi | 차량 루프탑 안테나 | — |
| `G_RX_DBI` | Communications.py:189 | 9.0 dBi | RSU 마스트 안테나 | — |
| `SHADOWING_SIGMA_DB` | Communications.py:194 | 4.0 dB | 도심/반개방 로그노멀 섀도잉 통상값 | — |
| `OFDM_SYMBOL_TIME_S` | Communications.py:204 | 8 µs | 6.4µs 유효+1.6µs GI (802.11p, half-clocked 802.11a) | — |
| `PREAMBLE_SIGNAL_TIME_S` | Communications.py:205 | 40 µs | 32µs PLCP 프리앰블 + 8µs SIGNAL 심볼 1개 | — |
| `SERVICE_BITS`/`TAIL_BITS` | Communications.py:206-207 | 16/6 | PLCP SERVICE 필드 / 컨볼루션 tail | — |
| `STATUS_UPDATE_BYTES` | Communications.py:211 | 300 B | ETSI CAM(위치·속도·헤딩) 실측 크기 | — |
| `MCS_TABLE` | Communications.py:236-245 | 3~27 Mbps, N_DBPS 24~216 | 802.11a 20MHz 표를 half-clock(10MHz)으로 반값화 | 6Mbps 항목 rate=N_DBPS/OFDM_SYMBOL_TIME=48/8µs=6.0Mbps, 자기일관성 확인 |
| `req_sinr_db` 사다리 | Communications.py:236-245 | 5/8/10/13/16/19/22/25 dB | "표준 OFDM MCS0-7 진행" | 문헌상 통상 사용되는 근사값과 일치(자체 검증 한계 있음, 아래 확인필요 참조) |
| `OPERATING_RATE_MBPS` | Communications.py:251 | 6.0 Mbps | ETSI ITS-G5 CAM/DENM 기본 레이트(QPSK 1/2) | — |
| `SINR_TH_DB` (파생) | Communications.py:268 | 10.0 dB | `get_mcs(6.0).req_sinr_db`에서 유도 | 코드상 하드코딩 아님, 확인됨 |
| noise floor @10MHz | 계산값 | -95.0 dBm | -174+10log10(10e6)+9 | 직접계산 -95.0 dBm, 일치 |
| sensitivity @6Mbps | 계산값 | -85.0 dBm | -95+10 | 직접계산 -85.0 dBm, 일치 |
| frame airtime @300B,6Mbps | 계산값 | 448 µs | 40µs+8µs×51심볼(2422비트/48=50.46→51) | 직접계산 448.0 µs, 일치. 설계문서 12절 수치와 정확히 일치 |
| 취약구간 겹침확률 | 계산값 | 0.896% | 2×448µs/100ms | 직접계산 0.896%, 설계문서 12절과 일치 |
| RSU 링크마진 @300m,23dBm | 계산값 | 15.17 dB | Ptx+Gtx+Grx-PL(300m) - sensitivity | 직접계산 -69.83dBm 수신, sensitivity -85dBm 대비 +15.17dB 여유. 안테나 이득이 실제로 반영되어 300m 경계에서도 충분한 마진 확보 확인 |
| `RSU_RANGE` | make_sumo_set.py:40 | 300 m | 5.9GHz 도심 NLOS 실측 200-300m | — |
| `OUTAGE_ZONE` | make_sumo_set.py:26 | 300 m | RSU_RANGE와 1:1 비율 유지(2/3 커버,1/3 아웃티지) | EDGE_LENGTH=900, 커버(300×2)/900=2/3 확인 |
| `AV_SPEED` | make_sumo_set.py:27 | 40 km/h | net.xml 실측 8.89~13.32m/s(32~48km/h) 재현 | SPEED×(1±0.2)=11.11×[0.8,1.2]=[8.89,13.33]m/s, 설계문서(v2 9절) 수치와 일치 |
| `STEP_LENGTH` | make_sumo_set.py:33 | 0.1 s | SUMO 해상도, 액션 최소Δ(0.1s)와 동일해야 함 | rl_interface의 Δ하한 0.1s와 일치(확인) |
| 신호등 적색 지속시간 | generated.net.xml 실측 | 45 s | netconvert 자동생성 tlLogic: green 42s+yellow 3s | `generated.net.xml`에서 42+3=45 직접 확인, 설계문서 Δ상한 45s의 근거와 정확히 일치 |

---

## 산출물 2: 결함 검토

### [경] 1. `AoiV2IEnv`/`StateVectorizer`/`evaluate_single_run`의 `rsu_range` 기본값이 `ss.RSU_RANGE`가 아니라 하드코딩 리터럴 `300.0`
- 파일: `src/hot_swap_trainer.py` (AoiV2IEnv 및 다른 클래스 생성자, 약 4곳), `src/rl_interface.py:229`(StateVectorizer), `src/evaluate.py:196`
- 이들 파일은 제 담당 범위 밖이지만, 문제의 물리량은 제 담당인 `make_sumo_set.RSU_RANGE`이므로 보고한다.
- 반례: 같은 값을 쓰는 `src/hpo.py:38`은 `DEFAULT_RSU_RANGE: float = float(getattr(ss, "RSU_RANGE", 300.0))`로 **정본에서 파생**시켜, 주석에 "HPO never drifts from the network that is actually built"라고 명시했다. 이 올바른 패턴이 다른 3곳에는 적용되지 않았다.
- 현재는 `ss.RSU_RANGE == 300.0`이라 수치가 우연히 일치해 결과를 왜곡하지 않는다. 하지만 이 프로젝트는 이미 `RSU_RANGE`를 800m→300m로 한 차례 바꾼 이력이 있고(주석: "The original design used OUTAGE_ZONE == RSU_RANGE (800/800)..."), 만약 향후 RSU 반경 민감도 스윕(밀도 스윕처럼)을 한다면 `hpo.py` 경로만 정확하고, `hot_swap_trainer.py`의 실제 학습 루프(1839행 부근, `AoiV2IEnv(...)` 호출 시 `rsu_range` 인자를 아예 넘기지 않음)와 `evaluate.py`의 평가 경로는 **여전히 300.0을 쓰는 채로 조용히 어긋난다** — 상태벡터 정규화(피처 5,6,7,12)가 실제 시나리오와 맞지 않게 된다.
- 확신도: 파일 직접 대조로 확인함(grep 결과 첨부: hpo.py만 `getattr(ss, "RSU_RANGE", 300.0)` 패턴을 씀). 심각도는 "현재 오작동 없음, 향후 리스크"이므로 [경]으로 표기.

### [경] 2. `make_sumo_set.MAX_SPEED`는 계산되지만 아무 데도 소비되지 않는다
- `MAX_SPEED = (120.0/3.6)*(1.0+DEL_SPEED)`가 `__init__` 시점과 `_make_sumo_files_impl()` 내부에서 두 번 계산되어 모듈 전역에 저장되지만, `grep -rn "MAX_SPEED"`로 전체 저장소를 확인한 결과 이 세 줄(정의 1회 + global 선언 1회 + 재계산 1회) 외에는 어디서도 읽히지 않는다. 실제 도로 속도 상한은 엣지별 `speed1/speed2 = random.uniform(SPEED*(1-DEL_SPEED), SPEED*(1+DEL_SPEED))`로 별도 결정되며 `MAX_SPEED`와 무관하다. vType에도 반영되지 않는다(생성된 `generated.rou.xml`에는 `<vType>` 자체가 없어 SUMO 기본 차량형이 쓰인다).
- 결과에 영향은 없다(죽은 값이라 계산 낭비만). 향후 "차량이 도로제한속도 이상으로 달릴 수 있는가"를 제약하려는 의도로 보이는데 실제로 그 역할을 하지 못하고 있다는 점만 지적한다.

### [경] 3. `heuristic_scheduler.py`의 인라인 주석이 실제 기본값과 다르다(3곳)
- `interval = self.delta_min  # 0.5s` (line 145) — 실제 기본값은 `delta_min=0.1`
- `power = self.p_high        # 25.0 dBm for high-reliability delivery` (line 146) — 실제 기본값은 `p_high=23.0`
- `power = self.p_low          # 20.0 dBm saves energy and avoids interference` (line 159) — 실제 기본값은 `p_low=10.0`(20.0은 `p_mid`의 값)
- 로직 자체는 `self.delta_min`/`self.p_high`/`self.p_low`를 올바르게 참조하므로 동작에는 문제가 없다. 다만 세 주석 모두 이전 버전의 상수(0.5s/25dBm/20dBm)를 그대로 남긴 것으로 보이며, 코드를 읽는 사람이 실제 튜닝값과 다르게 오인할 수 있다.

### [경] 4. `noise_floor_mw(num_subchannels)`가 대역폭을 `TOTAL_BW_HZ / num_subchannels`로 역산한다 — `num_subchannels`가 4가 아니면 802.11p 10MHz 채널 정의와 어긋난다
- `SUBCHANNEL_BW_HZ = 10e6`는 802.11p 표준이 정하는 고정된 채널폭이다. 그런데 `noise_floor_mw()`는 이 상수를 직접 쓰지 않고 `TOTAL_BW_HZ(40MHz) / num_subchannels`로 매번 재계산한다. `num_subchannels==NUM_SUBCHANNELS==4`일 때만 10MHz와 일치하고(실제로 코드베이스 전체에서 `num_channels`는 항상 4로 고정되어 있음을 `grep`으로 확인함), 만약 향후 서브채널 수를 바꾸는 실험을 한다면(design_spec_v2.md 10절이 "서브채널 4→1"을 검토했다가 채택하지 않은 대안으로 남겨둔 바 있다) 각 서브채널의 대역폭이 표준의 10MHz가 아니라 `40MHz/신규채널수`로 조용히 바뀌어 잡음바닥·SINR 임계가 물리적으로 잘못된 값이 된다.
- 현재는 발현되지 않는 잠재 결함이다(inert). 코드는 `SUBCHANNEL_BW_HZ`를 직접 쓰도록 고치는 편이 안전하다.

### [경] 5. `dynamics_predictor.py`의 광범위한 `except Exception: pass/continue`가 로그를 전혀 남기지 않는다
- 위치: 187, 312-313, 333행 등. 각각 "차선 정차수 조회 실패", "리더차량 조회 실패", "다음 신호전환시각 조회 실패" 시 안전한 기본값(0/None/inf)으로 폴백하는 합리적인 방어 코드다. 개별 차량의 일시적 TraCI 조회 실패(차량 이탈 등)에 대한 대응으로는 적절하다.
- 다만 로깅이 전혀 없어 "차량 개별 예외"와 "TraCI 연결 자체의 시스템적 열화"를 구분할 방법이 없다. 후자가 발생하면 `speed`/`accel`/`n_queue` 등 다수 피처가 조용히 0/기본값으로 굳어버릴 수 있는데, 설계문서 9절이 이미 "폴백이 결함을 정상으로 통과시킨 사례"(mean_aoi 1.0 폴백, warmup 부족)를 실제로 지적한 바 있어, 유사한 종류의 은폐 가능성으로 [경]에 표기한다. 결함이 실제로 존재한다는 증거는 찾지 못했다(확인 필요 수준).

### [경] 6. `src/model.py` 전체가 죽은 파일
- `grep -rln "src.model\|PPOAgent"` 결과 이 파일 자기 자신 외 어디서도 참조되지 않는다. TensorFlow/Keras 기반 PPO 구현으로, 실제 사용되는 PyTorch 기반 `src/baselines/*.py`(`base_agent.py`, `sb3_ppo.py` 등)와 완전히 별개다. 실행되지 않으므로 결과 왜곡 위험은 없다. 정리 대상 후보로 보고한다.

### [경] 7. `src/NetSim.py` 전체가 현재 파이프라인에서 고아 상태
- 브리핑에서 지시한 대로 확인한 결과: `grep -rn "import.*NetSim"`은 `src/aoi_env.py`(설계문서 D1에서 폐기 확정)와 저장소 최상위 `8. V2V Precaching.py`만을 반환한다. 후자는 파일 자체 주석에 "이 예제는 V2V Precaching in Outage zone 논문을 기반으로 작성되었습니다"라고 명시된 **별도 프로젝트의 예제 스크립트**다. 즉 `NetSim.py`는 이번 AoI 스케줄링 논문을 위해 작성된 것이 아니라 이전/별도 연구용 범용 이벤트 시뮬레이터이며, 실제 학습·평가·HPO 경로(`hot_swap_trainer.py`, `rl_interface.py`, `evaluate.py`, `hpo.py`)는 전부 이를 우회해 libsumo를 직접 구동한다.
- 부가로 확인된 점: `NetSim.pre_define()`은 `sumo_set.RSU_RANGE/MAX_STEPS/OUTAGE_ZONE/NUM_BLOCKS/AV_SPEED/DENSITY`를 이 레거시 실험 전용 값(`NUM_BLOCKS=5`, `AV_SPEED`/`DENSITY` 난수)으로 **덮어쓴다**. `NetSim.py`가 정말로 아무 데도 import되지 않는다면 무해하지만, 만약 같은 프로세스 안에서 실수로 `import src.NetSim`이 한 번이라도 일어나면(예: 디버깅 중 REPL) `make_sumo_set`의 모듈 전역 정본 값이 조용히 오염된다. 결과 자체를 왜곡한 증거는 없으나(현재 학습 경로가 NetSim을 import하지 않으므로) 잠재적 트랩으로 기록한다.
- 결론: 삭제/정리 대상으로 보이나, 삭제는 Critic의 권한 밖이므로 판단만 보고한다.

### [확인 필요] 8. `CalcP_GEN()`의 트래픽 생성확률 공식 도출 근거를 독립적으로 검증하지 못함
- `L_tot = 2*n*NUM_BLOCKS*EDGE_LENGTH*(2*NUM_LANES)`, `L_path_avg = EDGE_LENGTH*(1+2*(n²-1)/(3n))`, `P_GEN = dens*L_tot*v/(L_path_avg*n²*3600)` 식은 격자망에서의 평균 경로장·밀도로부터 흐름 확률을 역산하는 교통공학적 근사로 보이나, 원 유도 과정이 코드/주석에 없어 독립적으로 재현 검증할 수 없었다.
- 다만 설계문서 v2 10절의 밀도 스윕 실측표(density 15→55veh/km에 대해 실측 차량/스텝 30.6→59.4로 단조 증가, tx_attempts 3862→7602로 단조 증가)가 이 공식이 정성적으로는 올바르게 작동함을 뒷받침한다. 정량적 도출 근거는 "확인 필요"로 남긴다.

### 확인했으나 결함이 아닌 것 (오검출 방지를 위해 명시)
- 물리 수식 전부(경로손실, 잡음바닥, SINR 임계, 에어타임, 안테나이득, Rayleigh 성공확률)를 직접 재계산했고 코드값과 정확히 일치했다. 안테나 이득(G_TX/G_RX)이 `rx_power_dbm()`에 실제로 더해지는 것을 확인했다(과거 버전은 이것이 빠져 있었다고 파일 주석이 명시).
- `SINR_TH_DB`는 하드코딩이 아니라 `OPERATING_RATE_MBPS`에서 파생되어 레이트-임계값-에어타임이 항상 연동된다.
- `RSU_RANGE`(300m), `AV_SPEED`(40km/h), `STEP_LENGTH`(0.1s), Δ상한 45s(신호주기 42+3s) 모두 설계문서 수치와 실측 대조 결과 일치했다.
- `STATUS_UPDATE_BYTES`(300B)는 `Communications.py`에만 정의되어 있고 `hot_swap_trainer.py`가 그대로 참조해 이중정의가 없다. 다른 물리 상수(G_TX_DBI, G_RX_DBI, PL_EXP, FREQ_HZ, SHADOWING_SIGMA_DB, NOISE_FIGURE_DB, OPERATING_RATE_MBPS, SINR_TH_DB)도 전체 저장소에서 `Communications.py` 외 재정의를 찾지 못했다 — 물리상수 정본 원칙이 잘 지켜지고 있다.
- `heuristic_scheduler.py`, `dynamics_predictor.py`의 핵심 로직(Rule1~3, I_stop/I_start 판정)은 문서화된 임계값과 실제 코드가 일치했고, 하드 예외 은폐(`except: pass`)는 발견되지 않았다(전부 `except Exception:`이며 안전한 기본값 반환).
- `n_queue`는 `dynamics_predictor.extract_queue_features()`에서 SUMO 실측(`getLastStepHaltingNumber` 정의와 동일한 0.1 m/s 임계)으로 계산되며 상수 0으로 죽어있지 않다(설계문서 9절이 지적한 과거 문제는 `hot_swap_trainer._ledger_queue_count`쪽 개선으로 이미 해결된 것으로 확인됨, 단 그 파일은 제 담당 범위 밖).
