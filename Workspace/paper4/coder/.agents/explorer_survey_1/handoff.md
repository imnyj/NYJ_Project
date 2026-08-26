# Explorer Survey 1 — 코드베이스 구조 및 시뮬레이션 환경 종합 분석 보고서

**작성자**: Explorer Survey 1 (Codebase Structure & Simulation Environment Explorer)  
**작성 일시**: 2026-08-26T22:02:00+09:00  
**대상 디렉토리**: `/home/imnyj/Workspace/paper4/coder`  
**관련 요구사항**: R1 (S2.5) ~ R7 (S5) 전반의 기존 코드베이스 분석 및 인터페이스 매핑

---

## 1. Observation (직접 관측 내용)

### 1.1 전체 파일 트리 및 구성
`/home/imnyj/Workspace/paper4/coder` 디렉토리 내의 파일 및 모듈 구성은 다음과 같습니다:

```
/home/imnyj/Workspace/paper4/coder/
├── ORIGINAL_REQUEST.md          # 최상위 사용자 요구사항 및 R1~R7 체크리스트
├── workflow.md                  # 논문 워크플로우 및 S1~S5 로드맵 요약
├── README_S1.md                 # S1 (환경 계층, 이벤트 E1~E3, 회고적 오차 적분) 상세 명세
├── README_S2.md                 # S2 (확률적 SINR 업링크, 전력/서브채널 간섭) 상세 명세
├── progress_sync.md             # 프로젝트 공통 진행 현황 동기화 문서
├── 8. V2V Precaching.py        # 레거시 V2V 프리캐싱 예제 스크립트 (참고용)
└── src/
    ├── aoi_env.py               # [핵심] S1+S2 통합 AoI 환경 계층 (VehicleNode, RSUNode, Metrics)
    ├── NetSim.py                # [핵심] Headless SumoNetSim 코어 (이벤트 시뮬레이터 + TraCI/libsumo 래퍼)
    ├── Communications.py        # [핵심] 무선 채널 모델 (WiFi 802.11ac, 광섬유, S2 Rayleigh SINR)
    ├── model.py                 # [레거시] TensorFlow 기반 PPOAgent (PyTorch 전환 대상)
    ├── install_list.txt         # 패키지 설치 가이드 메모
    └── sumo/
        ├── make_sumo_set.py     # SUMO 네트워크 절차적 생성 스크립트 (netconvert 연동)
        ├── generated.sumocfg    # SUMO 시뮬레이션 설정 파일
        ├── generated.net.xml    # SUMO 도로망 파일
        ├── generated.nod.xml    # 노드 정의 (신호등 교차로 및 dead_end)
        ├── generated.edg.xml    # 엣지 정의
        ├── generated.add.xml    # 추가 설정 (TAZ 정의)
        ├── generated.rou.xml    # 교통 흐름 (flow) 정의
        └── rsu.poi.xml          # RSU POI 정의 파일
```

---

### 1.2 실행 런타임 및 하드웨어 환경 실측
- **OS**: Linux (x86_64)
- **Python**: 3.12.3 (`/home/imnyj/venv/bin/python`)
- **SUMO / TraCI**:
  - SUMO 바이너리: `/home/imnyj/venv/bin/sumo`
  - netconvert 바이너리: `/home/imnyj/venv/bin/netconvert`
  - `SUMO_HOME`: `/home/imnyj/venv/lib/python3.12/site-packages/sumo`
  - `libsumo`: 1.27.1 (고속 C++ 바인딩 활성화: `SUMO_USE_LIBSUMO=1`)
  - `traci`: 1.27.1, `sumolib`: 1.27.1
- **딥러닝 / RL 환경**:
  - `PyTorch`: **2.11.0+cu130** (CUDA 지원 활성화)
  - `GPU`: **4x NVIDIA GeForce RTX 3090** (24GB VRAM each, 총 96GB VRAM)
  - `Optuna`: **4.9.0** (하이퍼파라미터 최적화 라이브러리)
  - `NumPy`: 2.4.6, `SciPy`: 1.17.1, `Pandas`: 2.3.3, `Matplotlib`: 3.10.9
  - *특이사항*: `tensorflow`는 미설치 상태이므로, 기존 `src/model.py`의 TF 코드는 PyTorch 기반 모듈로 리팩토링되어야 함.

---

### 1.3 기존 핵심 모듈 분석

#### 1) `src/aoi_env.py` (S1+S2 환경 계층)
- **핵심 역할**: 차량 진입(E1) - 갱신 전송(E2) - 이탈(E3)의 이벤트 주도 시뮬레이션 및 유효 AoI(추정 오차 적분), SINR 업링크 판정.
- **수학적 외삽 및 오차 계산**:
  - `extrapolate(pos, vel, dt)`: $\hat{x}(t) = pos + vel \cdot dt$ (등속 외삽)
  - `estimation_error(true_pos, last_pos, last_vel, age)`: $e(t) = \|\text{true\_pos} - \hat{x}(t)\|$
  - 정지/등속 차량은 $e(t) \approx 0$, 가속/감속/회전 차량은 오차가 급격히 증가함.
- **주요 클래스**:
  - `VehicleNode(net.Node)`:
    - 속도 추정 `_estimate_velocity(t)`, 그랜트 수신 및 다음 갱신 예약 `_apply_grant(t)`.
    - 매 스텝 `update_dwell(current_time)`에서 E1 진입 등록 및 E2 전송 시도(`pending_tx`에 큐잉).
  - `RSUNode(net.Node)`:
    - 단일 타깃 RSU 셀 운영 (`WARMUP_S = 25.0`초 이후 트래픽 최다 RSU 자동 선정).
    - `on_update(vid, pos, vel, t, is_entry)`: 갱신 성공 시 이전 구간의 오차 적분량(`err_integral`)을 회고적(retrospective)으로 확정 및 기록.
    - `_resolve_pending()`: 이전 스텝에 큐잉된 전송 시도들을 서브채널별로 묶어 `comm.judge_uplink()`로 SINR 확률 판정 (1-step processing delay 적용).
  - `Metrics`:
    - `registrations_E1`, `updates_E2`, `exits_E3`, `interval_err_integrals`, `tx_attempts`, `tx_fail`, `tx_success_rate`, `mean_contenders_per_ch` 등 로깅.

#### 2) `src/Communications.py` (무선 통신 및 S2 SINR 모델)
- **물리 계층 파라미터**:
  - 중심 주파수: `FREQ_HZ = 5.9e9` (5.9 GHz ITS 대역)
  - 경로 손실 지수: `PL_EXP = 2.3` (준개방 도로 환경)
  - 잡음 지수: `NOISE_FIGURE_DB = 9.0`, 대역폭: `TOTAL_BW_HZ = 20e6` (20 MHz)
  - 서브채널 수: `NUM_SUBCHANNELS = 4` (서브채널당 5 MHz)
  - 복조 임계값: `SINR_TH_DB = 0.0 dB` ($\gamma_{th} = 1.0$)
  - 전송 전력 레벨: `TX_POWER_LEVELS_DBM = [20.0, 25.0, 30.0]` (100mW, 316mW, 1000mW)
- **Rayleigh Fading SINR 폐형식 판정 (`judge_uplink`)**:
  $$P_{\text{succ}} = \exp\left(-\gamma_{th} \frac{N_0}{S}\right) \prod_{k \in \text{interferers}} \frac{1}{1 + \gamma_{th} \frac{I_k}{S}}$$
  - 동일 서브채널에 동시 전송하는 차량 수가 증가할수록 $P_{\text{succ}}$ 급감 (간섭 모델링).

#### 3) `src/NetSim.py` (시뮬레이터 코어 및 TraCI 인터페이스)
- `SumoNetSim`: SUMO 프로세스를 `libsumo.start()`로 기동하고, 매 초 `libsumo.simulationStep()`을 호출하여 차량 위치 및 상태를 동기화.
- 기 구현된 TraCI 보조 함수:
  - `GetSpeed(vid)`, `GetAcceleration(vid)`, `GetPosition(vid)`
  - `GetRoutes(vid)`, `GetNextRSU(vid)`
  - `GetSignalState(rsu_id, vehicle_id)`: 신호등 상태 ('r': 1.0, 'y': 2.0, 'g'/'G': 3.0)
  - `GetSignalChangeTime(rsu_id)`: 잔여 위상 시간 반환

---

### 1.4 TraCI 신호등 및 정지선 접근 인터페이스 실측 검증
실제 SUMO 시뮬레이션 환경에서 TraCI/libsumo 호출 결과를 검증한 결과:
1. `sumo.vehicle.getNextTLS(vid)`:
   - 반환 구조: `[(tls_id, tls_index, dist_to_stopline, state_char), ...]`
   - 예시: `('N19', 13, 1166.65, 'r')`
   - `dist_to_stopline`: 현재 차량 위치에서 해당 신호등 정지선까지의 거리 (미터 단위 정밀 float).
   - `state_char`: 현재 신호 상태 (`'r'`, `'y'`, `'g'`, `'G'`).
2. `sumo.trafficlight.getNextSwitch(tls_id)`:
   - 다음 신호 위상 전환 시각 ($t_{\text{switch}}$) 반환.
   - 잔여 시간: $\Delta t_{\text{left}} = \max(0.0, t_{\text{switch}} - t_{\text{current}})$.
3. 동역학 예측 파라미터 (차량 단위):
   - 선행 차량 추적: `sumo.vehicle.getLeader(vid, max_dist)` -> `(leader_vid, gap)`
   - 대기 시간: `sumo.vehicle.getWaitingTime(vid)` (정체/정지 대기 시간)
   - 가속도: `sumo.vehicle.getAcceleration(vid)`

---

## 2. Logic Chain (논리적 연결고리 및 아키텍처 분석)

```
[SUMO / libsumo 1.27.1]
       │ (Step 1.0s, getNextTLS, getSpeed, getPosition)
       ▼
[NetSim.py (SumoNetSim)]
       │ (VehicleNode.update_dwell, RSUNode.update_dwell)
       ▼
[aoi_env.py (S1 + S2 + S2.5)]
  ├─ S1: E1 진입 / E2 갱신 / E3 이탈 + 등속 외삽 오차 적분 e(t)
  ├─ S2: 3-튜플 그랜트 (Δ, ch, p) + Communications.py Rayleigh SINR 성공 판정
  └─ S2.5: 신호등 상태, 정지선 거리, 잔여 위상 기반 동역학 예측
       │
       ▼
[RL Agent Interface (S3)]
  ├─ State Vectorization & Normalization (차량별/RSU 관측 상태)
  ├─ Hybrid Action Decoding (연속 Δ/p + 이산 ch)
  └─ Transition Buffer: (s_t, a_t, r_t, s_{t+1}, d_t) with Retrospective Reward
       │
       ▼
[Optuna HPO (R3) & 9 RL Baselines (R2)]
  ├─ Basic (3종): PPO, SAC, TD3
  ├─ Latest (3종): MAPPO, IPPO / HAPPO 등
  └─ SOTA/Similar (3종): DDPG/A2C/REMO-DQN 등
       │
       ▼
[Dual-Model Hot-swap Training Loop (S4 / R4)]
  ├─ Serving Worker (Inference / Env Interaction)
  └─ Learner Process (PyTorch GPU Training, RTX 3090, Model Hot-swap)
       │
       ▼
[Evaluation Harness (S5 / R5)]
  └─ Density & Seed Sweep Benchmark (RL Baselines vs Heuristic vs Static) -> CSV Output
```

### 2.1 S2.5 동역학 예측 및 휴리스틱 트리거 (R1)
- **동기**: S1/S2 실측에서 "정지 차량은 오차가 0에 가까워 갱신이 불필요"하지만, "이동 중이던 차량이 정지하는 순간" RSU가 이를 모르면 낡은 속도로 외삽하여 추정 위치가 교차로를 지나쳐 날아가는 심각한 오차(Ghost Car)가 발생함.
- **해결 원리**:
  1. `STOP_IMMINENT` (정지 임박): $v > 1.0\,\text{m/s}$ 이고 (신호가 'r'/'y' 이며 정지선 거리 $d \le v^2 / (2 a_{\text{decel}})$ 또는 $d \le 30\,\text{m}$).
  2. `START_IMMINENT` (출발 임박): $v < 0.5\,\text{m/s}$ 이고 (신호가 'g'/'G'로 변경되었거나 잔여 빨간불 시간 $\le 2.0\,\text{s}$).
- **휴리스틱 베이스라인 (Heuristic Policy)**:
  - 위 상태 변화 트리거 발생 시 즉시 강제 전송(`forced_update = True`, $\Delta = 0.5\text{s}$), 평시 정속/정지 상태에서는 백오프 ($\Delta = 3.0\sim 5.0\text{s}$) 적용.

### 2.2 RL State / Action / Reward 명세 (S3 / R2)
1. **State Space ($s_t$)**:
   - 나이: $\tau_{\text{age}} = t - t_{\text{last\_update}}$ (정규화: $\tau / 10.0$)
   - 동역학: 속도 $v / v_{\max}$, 가속도 $a / a_{\max}$
   - 신호 맥락: 신호 상태 one-hot (`[is_red, is_yellow, is_green]`), 정지선 거리 $d_{\text{tls}} / 500.0$, 잔여 위상 시간 $t_{\text{phase\_left}} / 30.0$, 예측 플래그 `[stop_imminent, start_imminent]`
   - 로컬/채널: RSU와의 거리 $d_{\text{rsu}} / R_{\text{comm}}$, 직전 전송 성공 여부
   - 전역 혼잡: RSU 관측 차량 수 $N_{\text{active}} / N_{\max}$, CBR(채널 사용률)
2. **Action Space ($a_t$)**:
   - 하이브리드 액션: $(\Delta, ch, p)$
   - $\Delta \in [\Delta_{\min}, \Delta_{\max}]$: 연속 갱신 주기 (예: $[0.2, 5.0]$초)
   - $ch \in \{0, 1, \dots, C-1\}$: 이산 서브채널 선택 (4개)
   - $p \in [p_{\min}, p_{\max}]$: 연속 전송 전력 (예: $[20.0, 30.0]$ dBm)
3. **Reward ($r_t$)**:
   - 소급 오차 적분 및 혼잡/실패 페널티:
     $$r_t = -\int_{t_{\text{prev}}}^{t} e(t) dt - \lambda_1 \cdot \text{CBR} - \lambda_2 \cdot \mathbb{I}(\text{tx}) - \beta \cdot (1 - P_{\text{succ}})$$

---

## 3. Caveats (주의사항 및 위험 요소)

1. **환경 변수 및 바이너리 경로**:
   - SUMO 및 netconvert가 `/home/imnyj/venv/bin`에 위치하므로, 모든 실행 스크립트는 반드시 `export PATH="/home/imnyj/venv/bin:$PATH"` 및 `export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"`를 설정하거나 `/home/imnyj/venv/bin/python` 인터프리터를 직접 사용해야 합니다.
2. **`make_sumo_set.py` 파라미터 초기화 주의점**:
   - `step`, `GRID_SIZE`, `EDGE_LENGTH` 등은 모듈 import 시점에 1회 계산되므로, 외부에서 `OUTAGE_ZONE` 등을 수정한 후에는 반드시 기하 구조 파생 변수를 재계산해야 합니다. (S1/S2 기본 2400m 격자 유지 권장)
3. **`libsumo` 단일 스레드 제약**:
   - `libsumo`는 프로세스 내 단일 인스턴스만 지원합니다. 다중 시뮬레이션을 병렬 실행(예: Optuna HPO, 평가 하네스 병렬화)할 때는 `multiprocessing`을 통해 개별 프로세스로 SUMO를 격리 기동해야 합니다.
4. **PyTorch 기반 통일**:
   - 시스템에 PyTorch 2.11.0+cu130이 정상 설치되어 있고 RTX 3090 GPU가 4장 할당되어 있으므로, 9개 베이스라인 모델은 모두 PyTorch로 구현하는 것이 안정성과 성능 측면에서 최적입니다.
5. **R6 제약 준수 (Critical)**:
   - 9개 베이스라인 구축, Optuna 최적화, S4/S5 평가 하네스 검증이 완전히 완료되기 전까지는 독자적인 제안 기법(Proposed Method) 개발에 착수하지 않고 사용자 승인을 대기해야 합니다.

---

## 4. Conclusion (최종 종합 결론)

1. **코드베이스 및 시뮬레이션 환경 조사 완료**:
   - S1(유효 AoI 오차 계산) 및 S2(Rayleigh SINR 통신 모델)가 `src/aoi_env.py` 및 `src/Communications.py`에 완전하고 정합성 있게 구축되어 있음을 확인하였습니다.
2. **S2.5 인터페이스 검증 완료**:
   - TraCI의 `getNextTLS`, `getNextSwitch`, `getLeader` 등을 통해 신호등 상태, 정지선 거리, 잔여 시간 및 동역학 예측을 즉각 추출할 수 있음을 실측으로 검증하였습니다.
3. **9개 베이스라인 및 파이프라인 개발 준비 완료**:
   - 하이브리드 액션 공간 지원이 가능한 PyTorch RL 구조(Actor-Critic 기반 하이브리드 정책 헤드 분기)와 Optuna HPO, Act/Rest 분리 핫스왑 학습 루프 및 평가 하네스 구축을 위한 기술적 준비가 완료되었습니다.

---

## 5. Verification Method (독립 검증 방법)

### 5.1 S1+S2 환경 동작 검증
다음 명령어로 S1+S2 환경의 정상 동작을 즉시 검증할 수 있습니다:

```bash
export PATH="/home/imnyj/venv/bin:$PATH"
export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"
/home/imnyj/venv/bin/python -c "
import random
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
ss.RSU_RANGE=800.0; ss.AV_SPEED=45.0; ss.DENSITY=25.0; ss.MAX_STEPS=40.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
random.seed(5); env.WARMUP_S=10.0; env.reset_env()
sim=net.SumoNetSim(VehicleClass=env.VehicleNode, RSUClass=env.RSUNode,
                   start_message_fn=env.start_message)
sim.run()
print('Simulation summary:', env.METRICS.summary())
"
```

### 5.2 TraCI 신호등 및 동역학 데이터 추출 검증
```bash
export PATH="/home/imnyj/venv/bin:$PATH"
export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"
/home/imnyj/venv/bin/python -c "
import libsumo as sumo
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
ss.RSU_RANGE=800.0; ss.AV_SPEED=45.0; ss.DENSITY=25.0; ss.MAX_STEPS=30.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
env.WARMUP_S=5.0; env.reset_env()

class TestVehicle(env.VehicleNode):
    def update_dwell(self, current_time: float):
        super().update_dwell(current_time)
        tls = sumo.vehicle.getNextTLS(self.id)
        if tls and current_time == 20.0:
            print(f'Vehicle {self.id}: speed={self.speed():.2f}, next_tls={tls[0]}')

sim = net.SumoNetSim(VehicleClass=TestVehicle, RSUClass=env.RSUNode)
sim.run()
"
```
