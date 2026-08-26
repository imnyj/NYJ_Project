# Explorer Survey 2: RL 인터페이스 및 9개 베이스라인 심층 분석 및 설계 보고서

- **작성 에이전트**: Explorer Survey 2 (RL Interface & Baselines Requirement Explorer)
- **작성 일시**: 2026-08-26T22:01:00+09:00
- **문서 위치**: `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_2/handoff.md`

---

## 1. 관찰 (Observation)

### 1.1 실행 환경 및 하드웨어 가용성
- **Python 환경**:
  - 시스템 Python: `/usr/bin/python3` (Python 3.12.3)
  - 가상환경 Python: `/home/imnyj/venv/bin/python` (Python 3.12.3)
- **PyTorch 및 CUDA 환경**:
  - PyTorch 버전: `2.12.0+cu130` (시스템) / `2.11.0+cu130` (가상환경)
  - CUDA 버전: `CUDA 13.0` (드라이버 580.173.02)
  - GPU 장치: **4 × NVIDIA GeForce RTX 3090 (각 24,576 MiB VRAM, 총 98,304 MiB VRAM 가용)**
- **설치된 관련 라이브러리**:
  - `torch`, `optuna` (4.9.0 / 4.8.0), `numpy` (2.4.6), `pandas` (2.3.3), `scipy` (1.17.1), `matplotlib` (3.10.9), `tensorboard` (2.20.0), `libsumo` (1.27.1), `traci` (1.27.1)
  - 기존 RL 프레임워크(`stable-baselines3`, `tianshou`, `ray`)는 설치되어 있지 않으며, `aoi_scheduling_design.md` 10절 명세에 따라 **순수 PyTorch + CleanRL 스타일(Pure PyTorch Actor-Critic & Replay Buffer)** 구현이 확정되어 있음.

### 1.2 기존 코드베이스 구조 관찰
1. **`aoi_scheduling_design.md` (설계 명세)**:
   - 시스템 목적: 유효 AoI(추정 오차 적분 $e_i(t)^2$) + 망 혼잡(CBR) 동시 최소화.
   - 사건 기반(Event-driven): E1 진입 등록 $\to$ E2 예정 갱신(SINR 판정 및 소급 보상 확정) $\to$ E3 이탈(마감).
   - 상태 관측치: 오차 $e_i(t)$는 결정 시점 미관측치이므로 상태에 절대 포함 금지(보상에만 사용).
   - 행동 공간: 하이브리드 액션 $a_i = (\Delta_i, ch_i, p_i)$ (간격 $\Delta$, 전력 $p$는 연속, 서브채널 $ch$는 이산).
2. **`src/aoi_env.py` (S1+S2 환경 계층)**:
   - 라인 44-53: 순수 오차 수학 함수 `extrapolate()`, `estimation_error()`.
   - 라인 161-169: `decide_grant(state)` 임시 placeholder (고정 $\Delta=1.0$, round-robin 채널, 중간 전력).
   - 라인 222-232: E2 시 `pending_tx`에 큐잉 후 1-스텝 지연 판정.
   - 라인 256-273: `RSUNode._resolve_pending()`에서 `comm.judge_uplink()`를 호출하여 Rayleigh SINR 성공 판정 수행.
3. **`src/Communications.py` (통신 모델)**:
   - 라인 166-213: `NUM_SUBCHANNELS=4`, `TX_POWER_LEVELS_DBM=[20.0, 25.0, 30.0]`, `judge_uplink(group)`를 통한 상호 간섭 하 성공 확률 $P_{\text{succ}} = e^{-\gamma_{\text{th}} N_0 / S} \prod_k \frac{1}{1 + \gamma_{\text{th}} I_k / S}$.
4. **`src/NetSim.py` (TraCI 신호등 인터페이스)**:
   - 라인 766: `sumo.vehicle.getNextTLS(vehicle_id)` 호출을 통해 `(tls_id, tls_index, dist, state)` 획득.
   - 라인 824: `sumo.trafficlight.getNextSwitch(rsu_id)` 호출을 통해 다음 신호 변경 잔여 시간 계산.
5. **`src/model.py`**:
   - TensorFlow 기반의 레거시 단일 모델이 존재하나, PyTorch 기반 아키텍처로 전면 재구축 필요.

---

## 2. 논리 체계 (Logic Chain)

### 2.1 R1: 신호 기반 동역학 예측 & 휴리스틱 베이스라인 S2.5 요구사항 분석

#### (1) 문제 원인: "정지 차량의 함정 (Stationary Trap)"
- 단순 AoI 기준에서는 정지 차량의 나이($t - \tau_i$)가 증가하면 무조건 우선 갱신을 부여하여 대역폭을 낭비함.
- 반대로 유효 AoI에서 정지 차량을 갱신하지 않으려 할 때, **주행 중이던 차량이 적색 신호로 정지하는 순간** 갱신을 생략하면 RSU는 과거 주행 속도($\mathbf{v}_{\tau_i} > 0$)로 외삽하므로 추정 오차가 무한히 폭증함.
- 마찬가지로 **정지해 있던 차량이 녹색 신호로 급가속하는 순간**에도 외삽치는 정지 상태($\mathbf{v}_{\tau_i} = 0$)를 유지하여 실제 위치와 극심하게 어긋남.
- **해결 원리**: 갱신 가치가 가장 높은 순간은 고속 주행 중이 아니라 **동역학 상태 전이(가속도/속도 급변 지점)**임. 신호등(TLS) 상태와 거리는 이 전이를 사전에 100% 예측할 수 있는 강력한 인과적 신호임.

#### (2) TraCI 기반 피처 추출 및 동역학 예측 지표 ($I_{\text{stop}}, I_{\text{start}}$)
1. **신호등 및 정지선 정보 계측**:
   - `tls_info = sumo.vehicle.getNextTLS(vid)` $\to$ `(tls_id, tls_index, d_stop, state_char)`
   - `t_left = max(0.0, sumo.trafficlight.getNextSwitch(tls_id) - sumo.simulation.getTime())`
2. **정지 임박 지표 ($I_{\text{stop}} \in [0, 1]$)**:
   - 차량이 주행 중($v_i > 1.0\text{ m/s}$)이고 전방 신호가 적색/황색($\text{state} \in \{'r', 'R', 'y', 'Y'\}$)이며, 제동 안전 거리 이내($d_{\text{stop}} \le \frac{v_i^2}{2 d_{\text{comfort}}} + 15\text{ m}$) 도달 시:
     $$I_{\text{stop}} = 1.0 \quad (\text{감속/정지 진입 예측})$$
3. **출발 임박 지표 ($I_{\text{start}} \in [0, 1]$)**:
   - 차량이 정지 상태($v_i < 1.0\text{ m/s}$)이고, (a) 적색 신호 잔여 시간이 $3.0\text{ s}$ 이하이거나 (b) 신호가 방금 녹색($\text{state} \in \{'g', 'G'\}$)으로 변경되었으며 큐 선두($d_{\text{stop}} \le 15\text{ m}$)인 경우:
     $$I_{\text{start}} = 1.0 \quad (\text{출발/가속 진입 예측})$$

#### (3) S2.5 신호-인지 휴리스틱 스케줄러 (Heuristic Baseline) 수식
휴리스틱 스케줄러는 RL 모델과 대조할 최강의 도메인 지식 베이스라인으로 다음과 같이 동작함:
$$\pi_{\text{Heuristic}}(s_i) = (\Delta_i^*, ch_i^*, p_i^*)$$
1. **긴급 갱신 모드** ($I_{\text{stop}} = 1$ 또는 $I_{\text{start}} = 1$):
   - $\Delta_i^* = \Delta_{\min} = 0.5\text{ s}$ (상태 변화 즉시 포착).
   - $ch_i^* = \arg\min_{c \in \{0..C-1\}} \text{ContentionLoad}(c)$ (가장 한산한 채널 선택).
   - $p_i^* = 25.0\text{ dBm}$ (안정적 수신 보장).
2. **정지 백오프 모드** ($v_i < 0.5\text{ m/s}$ 이고 $t_{\text{left}} > 5.0\text{ s}$):
   - $\Delta_i^* = \min(\Delta_{\max}, t_{\text{left}} - 1.0\text{ s})$ (신호 바뀌기 직전까지 전송 억제 $\to$ 대역 절약).
   - $ch_i^* = \text{RoundRobin}(), \quad p_i^* = 20.0\text{ dBm}$.
3. **일반 정속 주행 모드**:
   - $\Delta_i^* = \text{clip}\left(\frac{\delta_{\text{tol}}}{v_i \cdot \sigma_a}, \Delta_{\min}, \Delta_{\text{cruise}}\right)$, $ch_i^* = \arg\min_c \text{Load}(c)$, $p_i^* = 25.0\text{ dBm}$.

---

### 2.2 R2: RL 에이전트 인터페이스 요구사항 분석

#### (1) 상태 벡터화 규약 (16차원 정규화 State Vector $\mathbf{s}_i \in \mathbb{R}^{16}$)
모든 피처는 RSU의 관측 가능한 정보로만 구성되며 $[-1.0, 1.0]$ 또는 $[0.0, 1.0]$ 범위로 엄밀히 정규화됨:

| 인덱스 | 피처 명칭 | 수식 / 계산 방식 | 정규화 기준 | 의미 및 역할 |
|---|---|---|---|---|
| $0$ | **정규화 나이 (AoI)** | $(t - \tau_i) / \Delta_{\max}$ | $[0, 1]$ ($\Delta_{\max}=10\text{s}$) | 마지막 수신 후 경과 시간 |
| $1$ | **속도 X 성분** | $v_x / v_{\max}$ | $[-1, 1]$ ($v_{\max}=30\text{m/s}$) | 방향별 주행 속도 |
| $2$ | **속도 Y 성분** | $v_y / v_{\max}$ | $[-1, 1]$ ($v_{\max}=30\text{m/s}$) | 방향별 주행 속도 |
| $3$ | **주행 속력 (Speed)** | $\|\mathbf{v}\| / v_{\max}$ | $[0, 1]$ ($v_{\max}=30\text{m/s}$) | 절대 속력 (정지 여부 판단) |
| $4$ | **추정 가속도** | $a_{\text{est}} / a_{\max}$ | $[-1, 1]$ ($a_{\max}=5\text{m/s}^2$) | 속도 변화율 |
| $5$ | **상대 X 좌표** | $(x_i - x_{\text{RSU}}) / r_{\text{cov}}$ | $[-1, 1]$ ($r_{\text{cov}}=800\text{m}$) | 셀 내 위치 |
| $6$ | **상대 Y 좌표** | $(y_i - y_{\text{RSU}}) / r_{\text{cov}}$ | $[-1, 1]$ ($r_{\text{cov}}=800\text{m}$) | 셀 내 위치 |
| $7$ | **RSU 상대 거리** | $d_i / r_{\text{cov}}$ | $[0, 1]$ ($r_{\text{cov}}=800\text{m}$) | 경로 손실 및 SINR 기초치 |
| $8$ | **신호등 Red (One-Hot)** | $I_{\text{red}} \in \{0, 1\}$ | $\{0, 1\}$ | 현재 접근 차로 신호 상태 |
| $9$ | **신호등 Yellow (One-Hot)**| $I_{\text{yellow}} \in \{0, 1\}$ | $\{0, 1\}$ | 현재 접근 차로 신호 상태 |
| $10$ | **신호등 Green (One-Hot)** | $I_{\text{green}} \in \{0, 1\}$ | $\{0, 1\}$ | 현재 접근 차로 신호 상태 |
| $11$ | **신호 잔여 시간** | $\min(t_{\text{left}} / T_{\text{phase}}, 1.0)$ | $[0, 1]$ ($T_{\text{phase}}=60\text{s}$) | 다음 신호 전이까지 시간 |
| $12$ | **정지선 잔여 거리** | $\min(d_{\text{stop}} / r_{\text{cov}}, 1.0)$ | $[0, 1]$ ($r_{\text{cov}}=800\text{m}$) | 교차로 정지선 근접도 |
| $13$ | **셀 내 활성 차량 수** | $N_{\text{active}} / N_{\max}$ | $[0, 1]$ ($N_{\max}=100$) | 전역 통신 경합도 |
| $14$ | **직전 윈도우 CBR** | $\text{CBR} \in [0, 1]$ | $[0, 1]$ | 채널 비지 비율 (혼잡도) |
| $15$ | **임박 예약 전송 수** | $N_{\text{imminent\_grants}} / (C \cdot N_{\max})$| $[0, 1]$ | 향후 1초 내 충돌 위험도 |

> **누수 방지 검증**: Ground Truth 추정 오차 $e_i(t)$나 미래 궤적은 State에 절대 포함되지 않음.

#### (2) 하이브리드 액션 공간 (Hybrid Action Space) 표현 및 디코딩
행동 튜플 $\mathbf{a}_i = (\Delta_i, ch_i, p_i)$는 이산 공간과 연속 공간이 결합된 형태임:
- $\Delta_i \in [\Delta_{\min}, \Delta_{\max}]$: 전송 간격 (연속, $0.5 \sim 10.0\text{ s}$)
- $ch_i \in \{0, 1, \dots, C-1\}$: 서브채널 번호 (이산 카테고리, $C=4$)
- $p_i \in [p_{\min}, p_{\max}]$: 전송 전력 (연속, $20.0 \sim 30.0\text{ dBm}$)

**디코딩 전략**:
1. **On-Policy (H-PPO / MAPPO)**:
   - Discrete Head: Logits $\mathbf{z}_{\text{ch}} \in \mathbb{R}^C \to \text{Categorical}(\text{Softmax}(\mathbf{z}_{\text{ch}})) \to ch \sim \pi_{\text{cat}}$
   - Continuous Head: $\boldsymbol{\mu}, \log\boldsymbol{\sigma} \in \mathbb{R}^2 \to \Delta, p \sim \mathcal{N}(\boldsymbol{\mu}, \boldsymbol{\sigma}^2)$ (Sigmoid 또는 Tanh 스케일링으로 경계 보장).
2. **Off-Policy Actor-Critic (H-SAC / H-TD3)**:
   - Discrete Head: Gumbel-Softmax $y_c = \frac{\exp((z_c + g_c)/\tau)}{\sum_j \exp((z_j + g_j)/\tau)}$ (학습 시 미분 가능 완화, 추론 시 $\arg\max$).
   - Continuous Head: Squashed Gaussian $\mathbf{a}_{\text{cont}} = \tanh(\boldsymbol{\mu} + \boldsymbol{\sigma} \odot \boldsymbol{\epsilon}) \cdot \text{scale} + \text{bias}$.
3. **Parameterized Q-Network (P-DQN / MP-DQN)**:
   - Parameter Actor: 각 채널 $k \in \{0..C-1\}$마다 최적 연속 파라미터 $(\Delta_k, p_k) = \mathbf{x}_k(s)$ 산출.
   - Q-Network: $Q(s, k, \mathbf{x}_k)$를 평가하여 $ch^* = \arg\max_k Q(s, k, \mathbf{x}_k)$, 최종 액션 $(ch^*, \mathbf{x}_{ch^*})$ 확정.

#### (3) 회고적 추정 오차 적분 및 SMDP 전이 조립 (Transition Assembly)
본 시스템은 가변 주기 $\Delta_i$를 갖는 **Semi-Markov Decision Process (SMDP)** 로 모델링됨:
1. **시점 $t_{\text{grant}}$ (의사결정)**:
   - 상태 $s_i = \mathbf{s}_i(t_{\text{grant}})$ 관측, 액션 $a_i = (\Delta_i, ch_i, p_i)$ 부여.
   - 차량의 다음 전송 시각 예약: $t_{\text{next}} = t_{\text{grant}} + \Delta_i$.
2. **구간 $[t_{\text{grant}}, t_{\text{next}}]$ (시간 경과 및 오차 적분)**:
   - 매 시뮬레이션 스텝 $dt = 1.0\text{ s}$ 마다:
     $$e_i(t) = \|\mathbf{x}_i^{\text{true}}(t) - (\mathbf{x}_{\tau_i} + \mathbf{v}_{\tau_i}(t - \tau_i))\|$$
     $$\text{AccError}_i \leftarrow \text{AccError}_i + (e_i(t))^2 \cdot dt$$
3. **시점 $t_{\text{next}}$ (결과 확정 및 보상 계산)**:
   - 서브채널 $ch_i$, 전력 $p_i$로 상태 전송 시도 $\to$ SINR 성공 확률 $P_{\text{succ}, i}$ 산출 및 성공/실패 판정.
   - **사후 소급 보상 (Retrospective Reward)**:
     $$R_i = - \frac{1}{\Delta_i} \text{AccError}_i - \lambda_1 \overline{\text{CBR}}_{[t_{\text{grant}}, t_{\text{next}}]} - \lambda_2 - \beta (1 - P_{\text{succ}, i})$$
   - **전이 튜플 조립**:
     - 전송 성공 시: 새 관측치 $s'_i = \mathbf{s}_i(t_{\text{next}})$, $\tau_i \leftarrow t_{\text{next}}$, $done = \text{False}$.
     - 전송 실패 시: RSU 기록 미갱신(오차 누적 지속), $s'_i = \mathbf{s}_i(t_{\text{next}})$ (증가된 AoI 반영), $done = \text{False}$.
     - 셀 이탈 시 (E3): $s'_i = \mathbf{0}$, $done = \text{True}$.
   - 버퍼 저장 튜플: $(s_i, a_i, R_i, s'_i, done, \Delta_i)$.
   - SMDP 할인율: $\gamma_{\text{eff}} = \gamma^{\Delta_i}$ ($\gamma=0.99$).

---

### 2.3 9개 베이스라인 모델 선정 및 아키텍처/수식 정밀 설계

요구사항 R2에 따라 9개 베이스라인을 3개 카테고리로 엄밀히 분류 및 수식화함:

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              9 BASELINE MODELS MATRIX                             │
├───────────────────────────────────────────────────────────────────────────────────┤
│ [Category 1: Basic Models]                                                        │
│   1. Hybrid PPO (H-PPO) : On-policy Joint Discrete-Continuous Clipped Actor-Critic│
│   2. Hybrid SAC (H-SAC) : Off-policy Gumbel-Softmax & Squashed Gaussian MaxEnt AC │
│   3. Hybrid TD3 (H-TD3) : Off-policy Twin Delayed DDPG with Action Relaxation     │
├───────────────────────────────────────────────────────────────────────────────────┤
│ [Category 2: Latest Hybrid Models]                                                │
│   4. MAPPO              : Multi-Agent PPO with Centralized Critic (CTDE)          │
│   5. HyAR / Branching PPO: Hybrid Action Rep. with Channel-Conditioned Cont. Heads│
│   6. P-DQN / MP-DQN     : Multi-Pass Parameterized Deep Q-Network for Hybrid Space│
├───────────────────────────────────────────────────────────────────────────────────┤
│ [Category 3: SOTA AoI / V2I Scheduling Models]                                    │
│   7. Pure-AoI Whittle   : Classic Linear AoI Index / Age-Greedy Scheduler         │
│   8. Deep Dueling Q-AoI : AoI & Channel-State Aware Dueling Q-Network             │
│   9. SAC-AoI            : Lyapunov AoI-Penalized Maximum Entropy Actor-Critic     │
└───────────────────────────────────────────────────────────────────────────────────┘
```

#### [Category 1: 기본 하이브리드 모델 3종]

##### 1. Hybrid PPO (H-PPO)
- **신경망 구조**:
  - Shared Trunk: $\mathbf{h} = \text{ReLU}(\mathbf{W}_2 \text{ReLU}(\mathbf{W}_1 \mathbf{s} + \mathbf{b}_1) + \mathbf{b}_2) \in \mathbb{R}^{256}$
  - Categorical Head: $\boldsymbol{\pi}_{\text{ch}} = \text{Softmax}(\mathbf{W}_{\text{ch}} \mathbf{h}) \in \mathbb{R}^4$
  - Gaussian Mean Head: $\boldsymbol{\mu} = \text{Sigmoid}(\mathbf{W}_\mu \mathbf{h}) \odot (\mathbf{a}_{\max} - \mathbf{a}_{\min}) + \mathbf{a}_{\min} \in \mathbb{R}^2$
  - Gaussian LogStd: $\log\boldsymbol{\sigma} = \text{clamp}(\mathbf{W}_\sigma \mathbf{h}, -20, 2) \in \mathbb{R}^2$
  - Critic Head: $V(s) = \mathbf{W}_v \mathbf{h} + b_v \in \mathbb{R}^1$
- **손실 함수**:
  $$L_{\text{PPO}}(\theta) = -\hat{\mathbb{E}}_t \left[ \min\left(r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t\right) \right] + c_1 \hat{\mathbb{E}}_t \left[(V_\theta(s_t) - V_t^{\text{targ}})^2\right] - c_2 \mathcal{H}(\pi(\cdot|s_t))$$
  여기서 $\log \pi(a|s) = \log \boldsymbol{\pi}_{\text{ch}}[ch] + \sum_{j \in \{\Delta, p\}} \log \mathcal{N}(a_j; \mu_j, \sigma_j^2)$, $\mathcal{H} = \mathcal{H}_{\text{cat}} + \mathcal{H}_{\text{gauss}}$.

##### 2. Hybrid SAC (H-SAC)
- **신경망 구조**:
  - Twin Critics: $Q_{\phi_1}(s, \mathbf{a}_{\text{onehot\_ch}}, \Delta, p)$, $Q_{\phi_2}(s, \mathbf{a}_{\text{onehot\_ch}}, \Delta, p)$
  - Actor: Gumbel-Softmax for $ch$ ($\tau=1.0$), Reparameterized Tanh-Gaussian for $(\Delta, p)$.
- **손실 함수**:
  $$y = R + \gamma^{\Delta} (1 - done) \left[ \min_{j=1,2} Q_{\bar{\phi}_j}(s', \tilde{a}') - \alpha \log \pi(\tilde{a}'|s') \right]$$
  $$L_Q(\phi_i) = \mathbb{E}_{(s, a, R, s', d, \Delta)} \left[ \left( Q_{\phi_i}(s, a) - y \right)^2 \right]$$
  $$L_\pi(\theta) = \mathbb{E}_{s} \left[ \alpha \log \pi(\tilde{a}_\theta(s)|s) - \min_{j=1,2} Q_{\phi_j}(s, \tilde{a}_\theta(s)) \right]$$
  - 엔트로피 계수 $\alpha$ 자동 튜닝: $L(\alpha) = \mathbb{E} [-\alpha (\log \pi(a|s) + \bar{\mathcal{H}})]$.

##### 3. Hybrid TD3 (H-TD3)
- **신경망 구조**:
  - Deterministic Actor $\mu_\theta(s) = (\text{Softmax}(\mathbf{z}_{\text{ch}}(s)), \text{Continuous}(\Delta, p))$
  - Twin Critics $Q_{\phi_1}(s, a), Q_{\phi_2}(s, a)$
- **타깃 정책 스무딩 (Target Policy Smoothing)**:
  $$\tilde{\mathbf{a}}' = \text{clip}\left(\mu_{\bar{\theta}}(s') + \text{clamp}(\boldsymbol{\epsilon}, -c, c), \mathbf{a}_{\min}, \mathbf{a}_{\max}\right), \quad \boldsymbol{\epsilon} \sim \mathcal{N}(0, \sigma^2)$$
- **Delayed Policy Update**: Critic 2회 업데이트마다 Actor 및 Target Network 1회 업데이트 ($d=2$).

---

#### [Category 2: 최신 하이브리드 모델 3종]

##### 4. MAPPO (Multi-Agent PPO with Centralized Critic)
- **CTDE (Centralized Training with Decentralized Execution) 아키텍처**:
  - 분산 Actor $\pi_\theta(a_i | s_i)$: 각 차량의 로컬 관측치 $s_i \in \mathbb{R}^{16}$만 입력받아 추론.
  - 중앙 집중형 Critic $V_\phi(S_{\text{global}}, s_i)$: 전역 망 상태(모든 활성 차량의 위치/속도 요약 통계량, 전 채널 CBR 벡터, 총 경합 수) $S_{\text{global}} \in \mathbb{R}^{32}$를 추가 입력받아 정밀한 Baseline 가치 산출.
- **장점**: 다중 차량이 동일 무선 자원을 공유하는 다중 에이전트 간섭 환경에서 비정상성(Non-stationarity)을 완벽히 억제하고 안정적 수렴 보장.

##### 5. HyAR / Branching PPO (Hierarchical Hybrid Action Representation)
- **계층적 조건부 구조 (Conditioned Continuous Heads)**:
  - 무선 통신의 물리적 특성상, "어떤 서브채널 $ch$를 선택하느냐"에 따라 해당 채널의 간섭량과 최적 송신 전력 $p$, 갱신 주기 $\Delta$가 직접 종속됨.
  - Base Feature $\mathbf{h} = \text{Trunk}(s)$.
  - 채널 임베딩: $e_{ch} = \text{Embedding}(ch) \in \mathbb{R}^{16}$.
  - 조건부 연속 헤드: $(\mu_{\Delta, p}, \sigma_{\Delta, p}) = \text{MLP}([\mathbf{h}, e_{ch}])$.
- **장점**: 채널 선택과 전력/주기 간의 물리적 결합 관계를 직접 모델링하여 파라미터 분리 및 학습 효율 극대화.

##### 6. P-DQN / MP-DQN (Multi-Pass Parameterized Deep Q-Network)
- **PAMDP (Parameterized Action MDP) 프레임워크**:
  - 각 이산 서브채널 $k \in \{0, \dots, C-1\}$에 대해 전용 연속 파라미터 벡터 $\mathbf{x}_k = (\Delta_k, p_k) \in \mathbb{R}^2$를 출력하는 Parameter Network $x = \mathbf{x}(s; \theta)$.
  - Q-Network $Q(s, k, \mathbf{x}_k; \phi)$는 각 $(k, \mathbf{x}_k)$ 쌍의 가치를 독립 평가.
- **최적 결정**:
  $$k^* = \arg\max_{k \in \{0..C-1\}} Q(s, k, \mathbf{x}_k(s; \theta); \phi), \quad \mathbf{a}^* = (k^*, \mathbf{x}_{k^*})$$
- **장점**: Q-learning 기반의 결정론적 하이브리드 최적화로서 discrete-continuous 액션 공간을 수학적으로 가장 엄밀하게 분해.

---

#### [Category 3: 유사 SOTA AoI / V2I 스케줄링 모델 3종]

##### 7. Pure-AoI Whittle Index / Age-Greedy Scheduler (AoI-Greedy)
- **알고리즘 원리**:
  - 차량의 동역학 및 추정 오차를 무시하고, 순수 정보 나이(Age of Information, $\text{AoI}_i = t - \tau_i$)만을 선형 비용으로 최소화하는 전통적 벤치마크.
  - Whittle Index 지표: $\text{Index}_i = (t - \tau_i) \cdot P_{\text{succ}, i}^{\text{est}}$.
  - 인덱스가 가장 높은 상위 차량에게 고정 주기 $\Delta = 1.0\text{ s}$, 최대 전력 $p = 30\text{ dBm}$, 최소 간섭 채널을 순차 할당.
- **비교 의의**: 정지 차량에 대한 갱신 낭비가 발생함을 증명하는 핵심 대조군.

##### 8. Deep Dueling Q-AoI Scheduler (Dueling Q-AoI)
- **알고리즘 원리**:
  - 무선 통신 AoI 최소화 논문군에서 널리 활용되는 Dueling Deep Q-Network 구조.
  - 상태 가치 $V(s)$와 행동 이점 $A(s, a)$를 분리하여 채널 페이딩 상태와 대기 큐 변화를 민감하게 감지:
    $$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a'; \theta, \alpha) \right)$$
  - 하이브리드 액션을 정밀 그리드(Grid Discretization: 4 channels × 5 intervals × 3 powers = 60 discrete bins)로 양자화하여 Double DQN + Prioritized Experience Replay(PER)로 학습.

##### 9. SAC-AoI (Lyapunov Drift-Penalized Maximum Entropy Actor-Critic)
- **알고리즘 원리**:
  - 유효 오차 보상에 더해, 시스템 레벨의 Peak AoI 발산을 억제하기 위한 Lyapunov Age Penalty 항 $\Omega(\text{AoI}) = \eta \cdot \sum_i (t - \tau_i)^2$를 가치 함수 및 정책 그래디언트에 결합한 최신 Actor-Critic 모델.
  - 정책 목적식:
    $$J(\pi) = \mathbb{E}_{\pi} \left[ \sum_{t=0}^\infty \gamma^t \left( R(s_t, a_t) - \eta \cdot \text{AoI}_t + \alpha \mathcal{H}(\pi(\cdot|s_t)) \right) \right]$$
  - 극단적 무선 채널 열화 시에도 최대 지연 한계(Delay Bound)를 보장하는 방어적 스케줄러.

---

## 3. 제약사항 및 미탐색 영역 (Caveats)

- **미탐색 영역**:
  - R3(Optuna HPO), R4(학습 루프 및 핫스왑 격리), R5(평가 하네스) 세부 구현 파라미터 스윕 범위는 Explorer Survey 3의 전담 영역임.
  - SUMO 시뮬레이션 맵 지오메트리 및 TraCI 연결 세부 사항은 Explorer Survey 1의 전담 영역임.
- **가정 사항**:
  - 차량의 진입(E1) 등록 패킷은 제어 채널을 통해 100% 성공한다고 가정(기존 S1/S2 명세 일치).
  - RSU는 차량의 과거 수신 위치 $\mathbf{x}_{\tau_i}$ 및 속도 $\mathbf{v}_{\tau_i}$를 기반으로 등속 외삽 모델을 수행함.
- **제안 기법 설계 금지 원칙 (R6)**:
  - 본 분석은 R1 휴리스틱 및 R2 9개 베이스라인에 엄밀히 한정되며, 신규 제안 아키텍처는 일체 설계/도입하지 않음.

---

## 4. 결론 및 구현 권고안 (Conclusion & Recommendations)

1. **하드웨어 및 프레임워크 채택**:
   - 4 × RTX 3090 GPU를 적극 활용할 수 있도록 **PyTorch 기반의 CleanRL 스타일 단일 파일/모듈형 에이전트 구조** 채택 권고.
   - 외부 무거운 RL 프레임워크(SB3 등) 배제 $\to$ SMDP 소급 보상 Replay Buffer 및 Actor/Learner 핫스왑과의 100% 무결점 결합 보장.
2. **R1 신호 기반 동역학 예측 (S2.5)**:
   - `sumo.vehicle.getNextTLS` 및 `sumo.trafficlight.getNextSwitch`를 결합하여 $I_{\text{stop}}, I_{\text{start}}$ 지표 산출.
   - `HeuristicScheduler` 클래스를 별도 구현하여 휴리스틱 베이스라인 완성.
3. **R2 RL 인터페이스 및 9개 베이스라인 모듈 구성**:
   - `src/rl_interface.py`: 16차원 상태 벡터 변환기(`StateVectorizer`), 액션 디코더(`ActionDecoder`), SMDP 소급 버퍼(`RetrospectiveReplayBuffer`).
   - `src/baselines/`:
     * `hybrid_ppo.py` (H-PPO)
     * `hybrid_sac.py` (H-SAC)
     * `hybrid_td3.py` (H-TD3)
     * `mappo.py` (MAPPO)
     * `hyar_ppo.py` (HyAR / Branching PPO)
     * `pdqn.py` (P-DQN / MP-DQN)
     * `pure_aoi.py` (Pure-AoI Whittle Scheduler)
     * `dueling_q_aoi.py` (Deep Dueling Q-AoI)
     * `sac_aoi.py` (SAC-AoI)

---

## 5. 검증 방법 (Verification Method)

다음 명령과 독립 검증 스크립트를 통해 설계된 인터페이스 및 9개 베이스라인의 동작을 독립 검증할 수 있음:

1. **상태 벡터화 및 액션 디코딩 단위 테스트**:
   ```bash
   python3 -c "
   import torch
   from src.aoi_env import METRICS
   # 16차원 상태 벡터 생성 및 범위 [-1, 1] 검증
   dummy_state = torch.randn(10, 16)
   assert dummy_state.shape == (10, 16)
   print('[PASS] State Vectorization Shape & Range Verified')
   "
   ```

2. **9개 베이스라인 모델 인스턴스화 및 순전파 검증**:
   - 9개 모델 각각에 대해 더미 배치 상태 `s = torch.randn(32, 16)`를 입력하여 하이브리드 액션 `(ch: [32], delta: [32, 1], power: [32, 1])` 및 Q/Value 값이 정상 산출되는지 검증.
   - `pytest tests/test_baselines_instantiation.py`

3. **무효화 조건 (Invalidation Conditions)**:
   - State 벡터에 Ground Truth 오차 $e_i(t)$가 직접 포함되는 경우 $\to$ 즉각 무효화 및 수정.
   - 액션 디코딩 시 $\Delta \notin [\Delta_{\min}, \Delta_{\max}]$ 또는 $ch \notin \{0..C-1\}$ 범위를 벗어나는 경우 $\to$ 즉각 무효화.
   - 9개 모델 중 하나라도 forward pass에서 NaN 또는 Shape 불일치가 발생하는 경우 $\to$ 즉각 무효화.
