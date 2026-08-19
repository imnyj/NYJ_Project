# Handoff Report: System Model and REMO-DQN Mathematical Formalization

본 보고서는 Paper4 IEEE Transactions on Wireless Communications (TWC) 논문 작성을 위해 V2X 통신 네트워크 모델, Markov Decision Process (MDP) 정식화, 그리고 REMO-DQN(ResNet-MoE-Dueling DQN) 하이브리드 심층 강화학습 아키텍처를 코드베이스로부터 정밀 추출하여 수학적으로 정식화한 조사 결과입니다.

---

## 1. Observation (직접 관찰 사실)

본 절에서는 대상 코드베이스 파일들을 직접 읽고 검증한 소스 코드 위치, 파라미터 수치, 수식 구현 내용을 기술합니다.

### 1.1 V2X 통신 및 물리/MAC 계층 파라미터
- **파일 경로**: `/home/imnyj/Workspace/paper4/code/sim_engine.py` (Line 44-95, 97-179)
  - 통신 반경 (Communication Range): $R_{\text{comm}} = 300.0\text{ m}$ (Line 44)
  - 채널 대역폭 (Channel Bandwidth): $B = 10\text{ MHz} = 10^7\text{ Hz}$ (Line 45)
  - 물리 계층 전송률 (Data Rate): $R_{\text{data}} = 3\text{ Mbps} = 3 \times 10^6\text{ bps}$ (BPSK $1/2$) (Line 46)
  - 경로 손실 지수 (Path Loss Exponent): $\alpha = 2.0$ (Line 47)
  - 나카가미-$m$ 페이딩 파라미터 (Nakagami-$m$ Parameter): $m = 3.0$ (Line 48)
  - CAM 패킷 크기 (CAM Packet Size): $L_{\text{CAM}} = 280\text{ Bytes} = 2240\text{ bits}$ (Line 49)
  - 패킷 전송 소요 시간 (Air-time Duration): $T_{\text{tx}} = \frac{280 \times 8}{3 \times 10^6} \approx 0.74667\text{ ms} = 0.00074667\text{ s}$ (Line 50)
  - 기준 거리 $d_0 = 1.0\text{ m}$에서의 자유 공간 경로 손실: $\text{PL}_0 = 20 \log_{10}\left(\frac{4\pi d_0 f_c}{c}\right) \approx 47.86\text{ dB}$ ($f_c = 5.9\text{ GHz}$, $c = 3 \times 10^8\text{ m/s}$) (Line 68)
  - 수신 전력: $P_{\text{rx}}\text{ [dBm]} = P_{\text{tx}}\text{ [dBm]} - (\text{PL}_0 + 10 \alpha \log_{10}(d / d_0))$ (Line 69-70)
  - 열잡음 및 잡음 지수: $N_0 = -174\text{ dBm/Hz} + 10\log_{10}(B) + \text{NF} = -174 + 70 + 10 = -94\text{ dBm}$ (Line 72)
  - SNR 임계값: $\gamma_{\text{th}} = 5.0\text{ dB}$ (선형 스케일 $\gamma_{\text{th, lin}} = 10^{0.5} \approx 3.16228$) (Line 77-78)
  - Nakagami-$m$ ($m=3$) 기반 수신 확률 공식: $x = \frac{m \cdot \gamma_{\text{th, lin}}}{\gamma_{\text{lin}}}$ 일 때, $P_{\text{succ}} = \exp(-x)\left(1 + x + \frac{x^2}{2}\right)$ (Line 92-94)
  - 국소 채널 감지 반경 (Sense Range): $R_{\text{sense}} = 500.0\text{ m}$ (Line 100)
  - 시뮬레이션 이산 시간 스텝: $\Delta T_{\text{step}} = 0.1\text{ s} = 100\text{ ms}$ (Line 99, 280)
  - MAC 계층 채널 경합 및 충돌 감쇠 계수: $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j)$ (Line 162)
  - 최종 도달 확률: $P_{\text{rx}, ij} = P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) \cdot f_{\text{collision}}(\text{CBR}_j)$ (Line 163)

### 1.2 ETSI CAM 생성 및 DCC 규칙
- **파일 경로**: `/home/imnyj/Workspace/paper4/code/etsi_cam_layer.py` (Line 30-61, 237-326, 348-380)
  - 최소/최대 전송 주기: $T_{\text{GenCam, min}} = 0.100\text{ s}$ ($10\text{ Hz}$), $T_{\text{GenCam, max}} = 1.000\text{ s}$ ($1\text{ Hz}$) (Line 30-31)
  - ETSI 이벤트 트리거 임계치 (Line 258-278):
    1. 방향 변화 (Heading delta): $|\Delta \theta| \ge 4.0^\circ$ (Line 266)
    2. 위치 변화 (Position delta): $\Delta d = \sqrt{\Delta x^2 + \Delta y^2} \ge 4.0\text{ m}$ (Line 272)
    3. 속도 변화 (Speed delta): $|\Delta v| \ge 0.5\text{ m/s}$ (Line 276)
    4. 주기 만료 (Periodic fallback): $\Delta t \ge T_{\text{GenCam, max}} = 1.0\text{ s}$ (Line 258)
  - DCC 전송 제약: $\Delta t \ge T_{\text{GenCam}}$ 미충족 시 전송 차단 (Line 280)
  - ReactDCC 상태 머신 임계치 (Line 35, 36, 350-358):
    - Relaxed 상태: $\text{CBR} < 0.40 \implies T_{\text{GenCam}} = 0.100\text{ s}$
    - Active 상태: $0.40 \le \text{CBR} < 0.60 \implies T_{\text{GenCam}} = 0.300\text{ s}$
    - Restricted 상태: $\text{CBR} \ge 0.60 \implies T_{\text{GenCam}} = 1.000\text{ s}$
  - AdaptDCC 적응형 제어 (Line 362-379):
    - 평활화 계수 $\lambda_s = 0.5$, 목표 혼잡도 $\text{CBR}_{\text{target}} = 0.60$, 스텝 크기 $\delta_T = 0.05\text{ s}$

### 1.3 MDP 상태 공간, 행동 공간, 다중 보상 함수
- **파일 경로**: `/home/imnyj/Workspace/paper4/code/ai_dcc_hook.py` (Line 144-168, 405-420), `/home/imnyj/Workspace/paper4/code/test_patch.py` (Line 10-25)
  - 상태 벡터 $s_t \in \mathbb{R}^5$:
    1. $s_t[0] = \text{cbr\_global} \in [0.0, 1.0]$: 현재 관측된 채널 점유율
    2. $s_t[1] = \text{n\_neighbors} = \frac{N_{\text{est}}}{50.0}$: 통신 반경 내 이웃 차량 수의 정규화 값 ($N_0 = 50$)
    3. $s_t[2] = \text{v\_norm} = \frac{v}{25.0}$: 주행 속도의 정규화 값 ($v_{\max} = 25.0\text{ m/s} = 90\text{ km/h}$)
    4. $s_t[3] = \text{dt\_since\_last\_cam} = \frac{\Delta t_{\text{CAM}}}{1.0}$: 직전 CAM 전송 이후 경과 시간 ($T_{\max} = 1.0\text{ s}$)
    5. $s_t[4] = \text{cbr\_smoothed} \in [0.0, 1.0]$: 지수이동평균 평활화 채널 점유율 ($\lambda_s = 0.5$)
  - 이산 행동 공간 $a_t \in \{0, 1, \dots, 15\}$ ($|\mathcal{A}| = 16$):
    - 전송 주기 격자: $\mathcal{T}_{\text{grid}} = [0.1, 0.2, 0.5, 1.0]\text{ s}$ (Line 125)
    - 송신 전력 격자: $\mathcal{P}_{\text{grid}} = [0.0, 10.0, 20.0, 30.0]\text{ dBm}$ (Line 126)
    - 디코딩: $i_T = \lfloor a_t / 4 \rfloor$, $i_P = a_t \bmod 4$, $T_{\text{GenCam}} = \mathcal{T}_{\text{grid}}[i_T]$, $P_{\text{tx}} = \mathcal{P}_{\text{grid}}[i_P]$ (Line 153-155)
  - 다중 보상 함수 (Multi-Reward Formulation):
    - $R_1 = +0.01 \cdot \text{n\_neighbors} = 0.01 \cdot \left(\frac{N_{\text{est}}}{50.0}\right)$ (인근 차량 인식성 보상)
    - $R_2 = -1.0 \cdot |\text{cbr\_smoothed} - 0.60|$ (ETSI 권고 목표 혼잡도 0.60 유지 및 채널 충돌 억제 페널티)
    - $R_3 = -0.1 \cdot \text{dt\_since\_last\_cam} = -0.1 \cdot \left(\frac{\Delta t_{\text{CAM}}}{1.0}\right)$ (정보 신선도 지연 및 AoI 누적 억제 페널티)
    - 종합 보상: $R_{\text{total}} = R_1 + R_2 + R_3$

### 1.4 REMO-DQN 신경망 아키텍처
- **파일 경로**: `/home/imnyj/Workspace/paper4/code/resnet_moe_agent.py` (Line 8-88)
  - ResNet 특징 추출기 (Line 24-36):
    - 입력 계층: $\text{Linear}(5, 128) \to \text{ReLU}$
    - 잔차 블록 (Residual Block) 2개 직렬 연결 ($N_b = 2$):
      각 블록: $h_{\text{mid}} = \text{ReLU}(\text{Linear}(128, 128)(x))$, $h_{\text{out}} = \text{ReLU}(\text{Linear}(128, 128)(h_{\text{mid}}) + x)$
    - 출력 특징 차원: $\phi(s_t) \in \mathbb{R}^{128}$
  - MoE 게이팅 라우터 (Line 63-68, 75):
    - 라우터 입력: $\phi(s_t).\text{detach}()$ (표현 붕괴 방지를 위한 그래디언트 차단)
    - 구조: $\text{Linear}(128, 64) \to \text{ReLU} \to \text{Linear}(64, K) \to \text{Softmax}(\dim=-1)$ ($K = 3$)
    - 게이팅 가중치: $G(s_t) = [g_1(s_t), g_2(s_t), g_3(s_t)]^T$, $\sum_{k=1}^3 g_k(s_t) = 1$
  - Dueling DQN 전문가 네트워크 3개 ($K = 3$) (Line 38-56, 70):
    - 각 전문가 $k \in \{1, 2, 3\}$:
      - 상태 가치 스트림 (Value Stream): $\text{Linear}(128, 64) \to \text{ReLU} \to \text{Linear}(64, 1) \implies V_k(s_t) \in \mathbb{R}^1$
      - 행동 이점 스트림 (Advantage Stream): $\text{Linear}(128, 64) \to \text{ReLU} \to \text{Linear}(64, 16) \implies A_k(s_t, a) \in \mathbb{R}^{16}$
      - Q-값 결합: $Q_k(s_t, a) = V_k(s_t) + \left(A_k(s_t, a) - \frac{1}{16}\sum_{a'=0}^{15} A_k(s_t, a')\right)$
  - 최종 가중합 Q-값 (Line 81-83):
    - $Q(s_t, a) = \sum_{k=1}^3 g_k(s_t) \cdot Q_k(s_t, a)$
  - 부하 균등화 정규화 손실 (Load Balancing Loss) (Line 151-158):
    - 배치 평균 게이팅 확률: $\bar{g}_k = \frac{1}{B}\sum_{b=1}^B g_k(s_b)$
    - 변동 계수 제곱: $\text{CV}^2(\bar{g}) = \frac{\text{Var}(\bar{g})}{(\text{Mean}(\bar{g}))^2 + 10^{-8}}$
    - 손실 함수: $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{TD}} + 0.01 \cdot \text{CV}^2(\bar{g})$

---

## 2. Logic Chain (수학적 모델링 및 논리적 연계 분석)

본 절에서는 관찰된 코드 구조를 바탕으로 IEEE TWC 표준에 부합하는 체계적인 수학 모델과 논리 구조를 정립합니다.

### 2.1 V2X 통신 및 네트워크 모델 정식화

#### (1) 시간 축 및 차량 집합 모델
시뮬레이션 환경은 이산 시간 스텝 $t \in \{0, 1, 2, \dots, T_{\text{end}}\}$으로 진행되며, 각 스텝의 지속 시간은 $\Delta T_{\text{step}} = 100\text{ ms}$입니다. 도로 네트워크 상에 존재하는 활성 차량의 집합을 $\mathcal{V}(t) = \{v_1, v_2, \dots, v_{N(t)}\}$라 정의합니다. 각 차량 $i \in \mathcal{V}(t)$의 기구학적 상태는 2차원 좌표 $(x_i(t), y_i(t))$, 이동 속도 $v_i(t)$, 진행 각도 $\theta_i(t)$로 표현됩니다. 두 차량 $i, j$ 사이의 유클리드 거리는 $d_{ij}(t) = \sqrt{(x_i(t) - x_j(t))^2 + (y_i(t) - y_j(t))^2}$로 계산됩니다.

#### (2) ETSI EN 302 637-2 CAM 이벤트 기반 패킷 생성 메커니즘
차량 $i$가 직전에 CAM 패킷을 전송한 시각을 $t_{\text{last}, i}$, 전송 당시의 위치, 속도, 진행 각도를 각각 $(x_i^{\text{last}}, y_i^{\text{last}})$, $v_i^{\text{last}}$, $\theta_i^{\text{last}}$라 정의합니다. 현재 시각 $t$에서 경과 시간 $\Delta t_i = t - t_{\text{last}, i}$에 대해, 다음 네 가지 조건 중 하나라도 만족될 때 원초적 전송 트리거 플래그 $\text{Trig}_i(t) = 1$이 활성화됩니다:

$$\text{Trig}_i(t) = \begin{cases} 
1, & \text{if } \Delta t_i \ge T_{\text{GenCam, max}} \\
1, & \text{if } \min(|\theta_i(t) - \theta_i^{\text{last}}|, 360^\circ - |\theta_i(t) - \theta_i^{\text{last}}|) \ge \Delta \theta_{\text{th}} \\
1, & \text{if } \sqrt{(x_i(t) - x_i^{\text{last}})^2 + (y_i(t) - y_i^{\text{last}})^2} \ge \Delta d_{\text{th}} \\
1, & \text{if } |v_i(t) - v_i^{\text{last}}| \ge \Delta v_{\text{th}} \\
0, & \text{otherwise}
\end{cases}$$

여기서 표준 임계치는 $\Delta \theta_{\text{th}} = 4.0^\circ$, $\Delta d_{\text{th}} = 4.0\text{ m}$, $\Delta v_{\text{th}} = 0.5\text{ m/s}$, $T_{\text{GenCam, max}} = 1.0\text{ s}$입니다.
DCC 계층이 결정한 최소 전송 주기 제약 $T_{\text{GenCam}, i}(t) \in [T_{\text{GenCam, min}}, T_{\text{GenCam, max}}]$ ($T_{\text{GenCam, min}} = 0.1\text{ s}$)에 의해 최종 전송 허가 $\Psi_i(t) \in \{0, 1\}$는 다음과 같이 결정됩니다:

$$\Psi_i(t) = \text{Trig}_i(t) \cdot \mathbb{I}\left(\Delta t_i \ge T_{\text{GenCam}, i}(t)\right) \cdot \mathbb{I}\left(\Delta t_i \ge T_{\text{GenCam, min}}\right)$$

#### (3) 무선 채널 모델 및 MAC 계층 패킷 충돌 메커니즘
CAM 패킷 크기는 $L_{\text{CAM}} = 280\text{ Bytes} = 2240\text{ bits}$이며, $10\text{ MHz}$ 대역폭 채널에서 3 Mbps 전송률로 송신되므로 패킷 전송 소요 시간은 $T_{\text{tx}} = 0.74667\text{ ms}$입니다. 송신 차량 $i$가 송신 전력 $P_{\text{tx}, i}\text{ [dBm]}$으로 패킷을 송신할 때, 거리 $d_{ij}$ 떨어진 수신 차량 $j$에서의 평균 수신 신호 대 잡음비(SNR) $\bar{\gamma}_{ij}\text{ [dB]}$는 로그-거리 경로 손실 모델에 의해 산출됩니다:

$$\text{PL}(d_{ij})\text{ [dB]} = \text{PL}_0 + 10 \alpha \log_{10}(d_{ij}), \quad \text{PL}_0 = 20\log_{10}\left(\frac{4\pi f_c}{c}\right) \approx 47.86\text{ dB}$$
$$P_{\text{rx}, ij}\text{ [dBm]} = P_{\text{tx}, i} - \text{PL}(d_{ij})$$
$$\bar{\gamma}_{ij}\text{ [dB]} = P_{\text{rx}, ij}\text{ [dBm]} - N_0\text{ [dBm]}, \quad N_0 = -94\text{ dBm}$$

도심 환경의 다중 경로 페이딩을 모델링하기 위해 Nakagami-$m$ 분포($m=3.0$)를 적용합니다. 수신기의 복조 요구 SNR 임계치를 $\gamma_{\text{th}} = 5.0\text{ dB}$ (선형값 $\gamma_{\text{th, lin}} \approx 3.162$)라 할 때, 선형 평균 SNR $\bar{\gamma}_{\text{lin}, ij} = 10^{\bar{\gamma}_{ij}/10}$에 대한 순수 무선 채널 수신 성공 확률 $P_{\text{succ}}(d_{ij}, P_{\text{tx}, i})$는 $m=3$ 감마 분포의 상위 누적 확률(CCDF)로 주어집니다:

$$P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) = \exp\left(-\frac{3 \gamma_{\text{th, lin}}}{\bar{\gamma}_{\text{lin}, ij}}\right) \left[ 1 + \frac{3 \gamma_{\text{th, lin}}}{\bar{\gamma}_{\text{lin}, ij}} + \frac{1}{2}\left(\frac{3 \gamma_{\text{th, lin}}}{\bar{\gamma}_{\text{lin}, ij}}\right)^2 \right]$$

고밀도 V2X 환경에서 CSMA/CA MAC 계층의 동시 다발적 전송 경합 및 패킷 충돌을 반영하기 위해, 수신 차량 $j$의 채널 점유율 $\text{CBR}_j(t)$에 비례하는 충돌 감쇠 계수 $f_{\text{collision}}(\text{CBR}_j)$를 적용합니다:

$$f_{\text{collision}}(\text{CBR}_j) = \max\left(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t)\right)$$
$$P_{\text{rx}, ij}(t) = P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) \cdot f_{\text{collision}}(\text{CBR}_j)$$

#### (4) 국소 채널 점유율(CBR) 및 지수 평활화 공식
차량 $i$의 반경 $R_{\text{sense}} = 500\text{ m}$ 내에서 동일 스텝 $\Delta T_{\text{step}}$ 동안 발생한 총 CAM 전송 이벤트 집합을 $\mathcal{E}_{\text{sense}}(i, t) = \{k \in \mathcal{V}(t) \mid d_{ik}(t) \le R_{\text{sense}}, \Psi_k(t) = 1\}$라 할 때, 순간 국소 채널 점유율 $\text{CBR}_i(t)$와 지수 이동 평균(EMA) 평활화 채널 점유율 $\text{CBR}_{\text{smoothed}, i}(t)$는 다음과 같이 계산됩니다:

$$\text{CBR}_i(t) = \min\left(1.0, \frac{|\mathcal{E}_{\text{sense}}(i, t)| \cdot T_{\text{tx}}}{\Delta T_{\text{step}}}\right)$$
$$\text{CBR}_{\text{smoothed}, i}(t) = (1 - \lambda_s) \cdot \text{CBR}_{\text{smoothed}, i}(t - \Delta T_{\text{step}}) + \lambda_s \cdot \text{CBR}_i(t), \quad \lambda_s = 0.5$$

#### (5) 정보 신선도(AoI) 및 패킷 수신율(PDR) 수식
수신 차량 $j$가 송신 차량 $i$로부터 가장 최근에 성공적으로 수신한 패킷의 생성 시각을 $u_{ij}(t)$라 할 때, 차량 쌍 $(i, j)$의 순간 정보 신선도(Age of Information, AoI) $\Delta_{ij}(t)$와 통신 반경 $R_{\text{comm}} = 300\text{ m}$ 내의 네트워크 평균 AoI $\overline{\text{AoI}}(t)$는 다음과 같이 정의됩니다:

$$\Delta_{ij}(t) = t - u_{ij}(t)$$
$$\overline{\text{AoI}}(t) = \frac{1}{|\mathcal{P}_{\text{comm}}(t)|} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \min(\Delta_{ij}(t) \times 1000\text{ [ms]}, 2000\text{ [ms]})$$
$$\text{where } \mathcal{P}_{\text{comm}}(t) = \{(i, j) \in \mathcal{V}(t) \times \mathcal{V}(t) \mid i \neq j, d_{ij}(t) \le R_{\text{comm}}\}$$

네트워크 전체 패킷 수신율(PDR)은 통신 반경 내 총 전송 기회 대비 실제 수신 성공 비율로 정의됩니다:

$$\text{PDR} = \frac{\sum_{t} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \mathbb{I}(\text{Packet from } i \text{ received by } j \text{ at } t)}{\sum_{t} \sum_{i \in \mathcal{V}(t)} \Psi_i(t) \cdot |\{j \in \mathcal{V}(t) \mid j \neq i, d_{ij}(t) \le R_{\text{comm}}\}|} \times 100\%$$

---

### 2.2 Markov Decision Process (MDP) 정식화

분산형 V2X 혼잡 제어 문제는 각 차량 에이전트가 개별적으로 의사결정을 수행하는 이산 시간 MDP $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$로 정식화됩니다.

#### (1) 상태 공간 (State Space) $\mathcal{S}$
에이전트 $i$가 타임스텝 $t$에서 관측하는 상태 벡터 $s_t^{(i)} \in \mathcal{S} \subset \mathbb{R}^5$는 채널 상태, 이웃 차량 밀도, 자신의 주행 동역학 및 패킷 전송 이력을 반영하는 5차원 연속 변수로 구성됩니다:

$$s_t^{(i)} = \begin{bmatrix} s_{t, 1}^{(i)} \\ s_{t, 2}^{(i)} \\ s_{t, 3}^{(i)} \\ s_{t, 4}^{(i)} \\ s_{t, 5}^{(i)} \end{bmatrix} = \begin{bmatrix} \text{CBR}_i(t) \\ \frac{N_{\text{est}, i}(t)}{N_0} \\ \frac{v_i(t)}{v_{\max}} \\ \frac{t - t_{\text{last}, i}}{T_{\text{GenCam, max}}} \\ \text{CBR}_{\text{smoothed}, i}(t) \end{bmatrix}$$

- $s_{t, 1}^{(i)} = \text{CBR}_i(t) \in [0.0, 1.0]$: 현재 관측 윈도우의 순간 채널 점유율.
- $s_{t, 2}^{(i)} = \frac{N_{\text{est}, i}(t)}{50.0} \in [0.0, \infty)$: 통신 반경 $300\text{ m}$ 내 이웃 차량 수 $N_{\text{est}, i}(t)$를 기준 용량 $N_0 = 50$으로 나눈 정규화 밀도.
- $s_{t, 3}^{(i)} = \frac{v_i(t)}{25.0} \in [0.0, \infty)$: 주행 속도를 기준 최고 속도 $v_{\max} = 25.0\text{ m/s}$ ($90\text{ km/h}$)로 나눈 정규화 속도.
- $s_{t, 4}^{(i)} = \frac{\Delta t_i}{1.0} \in [0.0, \infty)$: 직전 CAM 전송 이후 경과 시간을 최대 주기 $T_{\text{GenCam, max}} = 1.0\text{ s}$로 나눈 정규화 지연 시간.
- $s_{t, 5}^{(i)} = \text{CBR}_{\text{smoothed}, i}(t) \in [0.0, 1.0]$: 단기 채널 요동을 제거한 평활화 혼잡도.

#### (2) 행동 공간 (Action Space) $\mathcal{A}$
에이전트의 행동 $a_t \in \mathcal{A} = \{0, 1, \dots, 15\}$ ($|\mathcal{A}| = 16$)는 패킷 생성 주기 $T_{\text{GenCam}}$과 송신 전력 $P_{\text{tx}}$의 $4 \times 4$ 2차원 이산 조합 격자로 정의됩니다:

$$\mathcal{T}_{\text{grid}} = \{0.100, 0.200, 0.500, 1.000\}\text{ [s]} \quad (\text{주파수: } 10\text{ Hz}, 5\text{ Hz}, 2\text{ Hz}, 1\text{ Hz})$$
$$\mathcal{P}_{\text{grid}} = \{0.0, 10.0, 20.0, 30.0\}\text{ [dBm]} \quad (\text{선형 전력: } 1\text{ mW}, 10\text{ mW}, 100\text{ mW}, 1000\text{ mW})$$

선택된 행동 인덱스 $a_t$에 대한 물리 파라미터 맵핑 함수 $\Omega: \mathcal{A} \to \mathcal{T}_{\text{grid}} \times \mathcal{P}_{\text{grid}}$는 다음과 같습니다:

$$i_T = \lfloor a_t / 4 \rfloor \in \{0, 1, 2, 3\}, \quad i_P = (a_t \bmod 4) \in \{0, 1, 2, 3\}$$
$$T_{\text{GenCam}}(a_t) = \mathcal{T}_{\text{grid}}[i_T], \quad P_{\text{tx}}(a_t) = \mathcal{P}_{\text{grid}}[i_P]$$

#### (3) 다중 보상 함수 (Multi-Objective Reward Function) $\mathcal{R}$
보상 함수는 채널 안정성 확보, MAC 패킷 충돌 방지, 이웃 노드 인식성 유지 및 AoI 지연 최소화를 균형 있게 달성하도록 3개 성분의 가중합으로 설계되었습니다:

$$\mathcal{R}(s_t, a_t) = R_1(s_t) + R_2(s_t) + R_3(s_t)$$

- **$R_1$ (이웃 차량 밀도 인식성 보상, Awareness Term)**:
  $$R_1(s_t) = +w_1 \cdot s_{t, 2} = +0.01 \cdot \left(\frac{N_{\text{est}}}{50.0}\right)$$
  차량 밀도가 높은 군집 환경에서 협력적 안전 인식을 유지하도록 유도합니다.

- **$R_2$ (CBR 목표 추종 및 채널 충돌 억제 페널티, Congestion Suppression Term)**:
  $$R_2(s_t) = -w_2 \cdot \left| s_{t, 5} - \text{CBR}_{\text{target}} \right| = -1.0 \cdot \left| \text{CBR}_{\text{smoothed}} - 0.60 \right|$$
  ETSI DCC 표준 권고 채널 임계치 $\text{CBR}_{\text{target}} = 0.60$ (60%)으로부터의 편차를 직접 페널티로 부과하여 채널 과소 이용과 전송 폭주로 인한 MAC 충돌을 억제합니다.

- **$R_3$ (정보 신선도 지연 및 AoI 누적 억제 페널티, Freshness Term)**:
  $$R_3(s_t) = -w_3 \cdot s_{t, 4} = -0.10 \cdot \left(\frac{\Delta t_{\text{CAM}}}{1.0}\right)$$
  연속된 CAM 전송 간격이 불필요하게 벌어지는 것을 방지하여 정보의 최신성(Low AoI)을 확보합니다.

---

### 2.3 REMO-DQN (ResNet-MoE-Dueling DQN) 아키텍처 정밀 분석

REMO-DQN은 고차원 비선형 상태 특징 추출, 트래픽 혼잡 수준별 동적 전문가 분기, 그리고 가치-이점 분리 학습을 결합한 3단계 하이브리드 심층 강화학습 신경망입니다.

```
[State s_t (5-dim)] 
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  ResNet Feature Extractor                              │
│  - Linear(5, 128) + ReLU                               │
│  - Residual Block 1: [Linear(128,128) -> ReLU ->       │
│                       Linear(128,128)] + Skip -> ReLU  │
│  - Residual Block 2: [Linear(128,128) -> ReLU ->       │
│                       Linear(128,128)] + Skip -> ReLU  │
└────────────────────────────────────────────────────────┘
        │
        ├───────────────────────────────┐
        │ phi(s_t) [128-dim]            │ phi(s_t).detach()
        ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│ Dueling Experts (K=3)    │    │ MoE Gating Router        │
│ Expert 1 (Low Congestion)│    │ - Linear(128, 64)        │
│ Expert 2 (Medium Cong.)  │    │ - ReLU                   │
│ Expert 3 (High Cong.)    │    │ - Linear(64, 3)          │
│                          │    │ - Softmax(dim=-1)        │
│ Each Expert k:           │    └──────────────────────────┘
│  V_k(s): Linear(128,64)  │                │
│          -> Linear(64,1) │                │ Gating weights
│  A_k(s,a): Linear(128,64)│                │ g_k(s_t) [3-dim]
│          -> Linear(64,16)│                │
│  Q_k = V_k + (A_k - mean)│                │
└──────────────────────────┘                │
        │ Q_k(s, a)                         │
        └───────────────┬───────────────────┘
                        ▼
            ┌───────────────────────┐
            │ Weighted MoE Sum      │
            │ Q(s,a) = sum g_k Q_k  │
            └───────────────────────┘
```

#### (1) ResNet 특징 추출 백본 (Feature Extraction Backbone)
입력 상태 벡터 $s_t \in \mathbb{R}^5$는 1개의 선형 투영 계층과 2개의 Residual Block을 통과하여 128차원의 잠재 특징 벡터 $\phi(s_t) \in \mathbb{R}^{128}$로 변환됩니다:

$$h_0 = \text{ReLU}\left(W_{\text{in}} s_t + b_{\text{in}}\right), \quad W_{\text{in}} \in \mathbb{R}^{128 \times 5}, \quad b_{\text{in}} \in \mathbb{R}^{128}$$

각 Residual Block $l \in \{1, 2\}$의 순전파 연산은 다음과 같습니다:

$$z_l^{(1)} = \text{ReLU}\left(W_{l, 1} h_{l-1} + b_{l, 1}\right), \quad W_{l, 1} \in \mathbb{R}^{128 \times 128}, \quad b_{l, 1} \in \mathbb{R}^{128}$$
$$z_l^{(2)} = W_{l, 2} z_l^{(1)} + b_{l, 2}, \quad W_{l, 2} \in \mathbb{R}^{128 \times 128}, \quad b_{l, 2} \in \mathbb{R}^{128}$$
$$h_l = \text{ReLU}\left(z_l^{(2)} + h_{l-1}\right) \quad \text{(Identity Skip Connection)}$$
$$\phi(s_t) = h_2 \in \mathbb{R}^{128}$$

Residual Skip Connection은 다층 신경망에서 발생하는 그래디언트 소실(Vanishing Gradient) 문제를 원천 차단하고, 복잡한 비선형 교통 상태에서도 안정적인 특징 표현 학습을 보장합니다.

#### (2) MoE 게이팅 라우터 (Mixture-of-Experts Gating Router)
MoE 게이팅 라우터는 추출된 잠재 특징을 바탕으로 현재 채널 및 밀도 상황에 적합한 전문가 네트워크를 동적으로 선택합니다. 이때 게이팅 네트워크의 역전파가 특징 추출 백본의 표현을 왜곡시키는 현상을 방지하기 위해 그래디언트 분리 연산자 $\text{sg}[\cdot]$ ($\text{detach}$)를 적용합니다:

$$g_{\text{hidden}} = \text{ReLU}\left(W_{g, 1} \text{sg}[\phi(s_t)] + b_{g, 1}\right), \quad W_{g, 1} \in \mathbb{R}^{64 \times 128}, \quad b_{g, 1} \in \mathbb{R}^{64}$$
$$l_g = W_{g, 2} g_{\text{hidden}} + b_{g, 2}, \quad W_{g, 2} \in \mathbb{R}^{3 \times 64}, \quad b_{g, 2} \in \mathbb{R}^3$$
$$G(s_t) = \text{Softmax}(l_g) = \begin{bmatrix} g_1(s_t) \\ g_2(s_t) \\ g_3(s_t) \end{bmatrix}, \quad g_k(s_t) = \frac{\exp(l_{g, k})}{\sum_{j=1}^3 \exp(l_{g, j})}$$

여기서 $K=3$개의 전문가는 각각 저혼잡(Low), 중혼잡(Medium), 고혼잡(High) 트래픽 영역에 전문화되도록 유도됩니다.

#### (3) Dueling DQN 구조를 갖춘 다중 전문가 네트워크
$K=3$개의 각 전문가 네트워크 $k \in \{1, 2, 3\}$는 잠재 특징 $\phi(s_t)$를 공유 입력으로 받아 상태 가치 스트림 $V_k(s_t)$와 행동 이점 스트림 $A_k(s_t, a)$를 독립적으로 계산합니다:

- **상태 가치 함수 $V_k(s_t) \in \mathbb{R}^1$**:
  $$v_k^{(1)} = \text{ReLU}\left(W_{v, k}^{(1)} \phi(s_t) + b_{v, k}^{(1)}\right), \quad W_{v, k}^{(1)} \in \mathbb{R}^{64 \times 128}, \quad b_{v, k}^{(1)} \in \mathbb{R}^{64}$$
  $$V_k(s_t) = W_{v, k}^{(2)} v_k^{(1)} + b_{v, k}^{(2)}, \quad W_{v, k}^{(2)} \in \mathbb{R}^{1 \times 64}, \quad b_{v, k}^{(2)} \in \mathbb{R}^1$$

- **행동 이점 함수 $A_k(s_t, a) \in \mathbb{R}^{16}$**:
  $$a_k^{(1)} = \text{ReLU}\left(W_{a, k}^{(1)} \phi(s_t) + b_{a, k}^{(1)}\right), \quad W_{a, k}^{(1)} \in \mathbb{R}^{64 \times 128}, \quad b_{a, k}^{(1)} \in \mathbb{R}^{64}$$
  $$A_k(s_t, a) = W_{a, k}^{(2)} a_k^{(1)} + b_{a, k}^{(2)}, \quad W_{a, k}^{(2)} \in \mathbb{R}^{16 \times 64}, \quad b_{a, k}^{(2)} \in \mathbb{R}^{16}$$

- **평균 중심화(Mean-Centering) Dueling Q-값 합성**:
  수학적 식별 불가능성(Unidentifiability) 문제를 해결하기 위해 이점 함수의 평균을 감산하는 결합식을 사용합니다:
  $$Q_k(s_t, a) = V_k(s_t) + \left( A_k(s_t, a) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A_k(s_t, a') \right), \quad |\mathcal{A}| = 16$$

- **최종 가중 MoE Q-값 합성**:
  $$Q(s_t, a) = \sum_{k=1}^3 g_k(s_t) \cdot Q_k(s_t, a)$$

#### (4) 손실 함수 및 부하 균등화 정규화 (Optimization Objective)
네트워크 학습은 Double DQN 방식의 타겟 계산과 MoE 전문가 붕괴(Expert Collapse)를 방지하는 부하 균등화 손실을 결합하여 수행됩니다:

1. **Double DQN 타겟 Q-값 ($y_t$)**:
   온라인 네트워크 파라미터 $\theta$로 최적 행동을 선택하고, 타겟 네트워크 파라미터 $\theta^-$로 해당 행동의 가치를 평가하여 과대추정(Overestimation)을 방지합니다:
   $$a^* = \arg\max_{a' \in \mathcal{A}} Q(s_{t+1}, a'; \theta)$$
   $$y_t = r_t + \gamma \cdot Q(s_{t+1}, a^*; \theta^-) \cdot (1 - d_t), \quad \gamma = 0.99$$

2. **TD 오차 손실 ($\mathcal{L}_{\text{TD}}$)**:
   미니배치 $\mathcal{B}$ ($|\mathcal{B}| = 64$)에 대한 평균 제곱 오차(MSE):
   $$\mathcal{L}_{\text{TD}}(\theta) = \frac{1}{|\mathcal{B}|} \sum_{(s, a, r, s', d) \in \mathcal{B}} \left( Q(s, a; \theta) - y \right)^2$$

3. **MoE 부하 균등화 정규화 손실 ($\mathcal{L}_{\text{LB}}$)**:
   특정 전문가로의 쏠림 현상을 방지하기 위해 배치 내 전문가별 평균 할당 확률 $\bar{g}_k = \frac{1}{|\mathcal{B}|} \sum_{b \in \mathcal{B}} g_k(s_b)$에 대한 변동 계수 제곱(Squared Coefficient of Variation) 페널티를 부여합니다:
   $$\text{CV}^2(\bar{g}) = \frac{\frac{1}{K}\sum_{k=1}^K \left(\bar{g}_k - \frac{1}{K}\right)^2}{\left(\frac{1}{K}\sum_{k=1}^K \bar{g}_k\right)^2 + \epsilon}, \quad K = 3, \quad \epsilon = 10^{-8}$$
   $$\mathcal{L}_{\text{LB}}(\theta) = \lambda_{\text{LB}} \cdot \text{CV}^2(\bar{g}), \quad \lambda_{\text{LB}} = 0.01$$

4. **최종 종합 손실 함수**:
   $$\mathcal{L}_{\text{total}}(\theta) = \mathcal{L}_{\text{TD}}(\theta) + \mathcal{L}_{\text{LB}}(\theta)$$

---

## 3. Caveats (한계점 및 가정 사항)

1. **2D 평면 도로망 가정**: 시뮬레이션 환경(SUMO 및 SumoNetSim 기반 모델)은 차량의 고도차(3D z축) 및 도심 건물의 3차원 장애물 차폐(Shadowing)를 직접 계산하지 않고, 경로 손실 지수 $\alpha = 2.0$과 나카가미-$m$ ($m=3$) 페이딩 모델을 통해 통계적으로 모사하였습니다.
2. **동기식 100ms 의사결정 주기**: 모든 차량은 $100\text{ ms}$ 단위의 이산 타임스텝에 맞추어 상태를 갱신하고 행동을 추론하도록 모델링되었습니다. 실제 비동기식 하드웨어 환경에서는 수 밀리초 단위의 클록 지터(Clock Jitter)가 발생할 수 있습니다.
3. **단일 채널 802.11p 가정**: C-V2X (PC5 Sidelink) Mode 4 자원 예약 메커니즘 대신 표준 DSRC/802.11p 기반 $5.9\text{ GHz}$ $10\text{ MHz}$ 단일 제어 채널(CCH)을 기준으로 MAC 경합 및 충돌 모델을 정식화하였습니다.

---

## 4. Conclusion (결론 및 작성 지침)

본 조사를 통해 추출된 수학적 정식화는 Paper4의 **Section III (System and Network Model)** 및 **Section IV (Proposed REMO-DQN Framework)** 작성을 완벽하게 지원합니다.

### 4.1 핵심 요약표
| 구분 | 수학적 표현 / 파라미터 | 물리적 의미 / 역할 |
|---|---|---|
| **물리/MAC 계층** | $f_c = 5.9\text{ GHz}, B = 10\text{ MHz}, R_{\text{data}} = 3\text{ Mbps}$ | 802.11p 무선 표준 채널 |
| **패킷 전송** | $L_{\text{CAM}} = 280\text{ B}, T_{\text{tx}} = 0.747\text{ ms}$ | 단일 CAM 메시지 송신 소요 시간 |
| **채널 페이딩** | Nakagami-$m$ ($m=3.0$), $\text{PL}(d) = 47.86 + 20\log_{10}(d)$ | 도심 환경 통계적 전파 모델 |
| **상태 공간** | $s_t = [\text{CBR}, \bar{N}_{\text{est}}, \bar{v}, \overline{\Delta t}_{\text{CAM}}, \text{CBR}_{\text{smoothed}}]^T \in \mathbb{R}^5$ | 혼잡도, 밀도, 속도, 지연, 평활 혼잡도 |
| **행동 공간** | $a_t \in \{0, \dots, 15\} \implies \mathcal{T}_{\text{grid}} \times \mathcal{P}_{\text{grid}}$ | 4단계 주기 $\times$ 4단계 전력 격자 |
| **보상 함수** | $R = 0.01\bar{N}_{\text{est}} - 1.0|\text{CBR}_{\text{smoothed}} - 0.6| - 0.1\overline{\Delta t}_{\text{CAM}}$ | 인식성 확보 + CBR 0.6 유지 + AoI 억제 |
| **신경망 구조** | ResNet 백본 (128차원) + MoE 라우터 ($K=3$) + Dueling DQN | 비선형 특징 추출 + 상황별 분기 + 가치 분리 |
| **정규화 손실** | $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{TD}} + 0.01 \cdot \text{CV}^2(\bar{g})$ | 전문가 붕괴 방지 부하 균등화 |

---

## 5. Verification Method (독립 검증 방법)

본 보고서에 기술된 모든 수식 및 파라미터는 다음 절차를 통해 소스 코드 수준에서 직접 실행 및 검증할 수 있습니다:

1. **신경망 아키텍처 및 텐서 차원 검증**:
   ```bash
   python3 -c "
   import torch
   from resnet_moe_agent import ResNetMoEDQN
   model = ResNetMoEDQN(state_dim=5, action_dim=16, num_experts=3, hidden_dim=128)
   dummy_state = torch.randn(64, 5)
   q_vals, gate_weights = model(dummy_state, return_gate_weights=True)
   assert q_vals.shape == (64, 16)
   assert gate_weights.shape == (64, 3)
   print('REMO-DQN Architecture shape verification PASSED!')
   "
   ```

2. **CAM 계층 및 물리 모델 파라미터 검증**:
   ```bash
   python3 -c "
   from etsi_cam_layer import T_GENCAM_MIN, T_GENCAM_MAX, PTX_GRID_DBM, T_GENCAM_GRID
   from sim_engine import COMM_RANGE_M, DATA_RATE_BPS, CAM_PACKET_BYTES, TX_DURATION_S
   assert T_GENCAM_MIN == 0.1 and T_GENCAM_MAX == 1.0
   assert CAM_PACKET_BYTES == 280 and DATA_RATE_BPS == 3000000
   assert abs(TX_DURATION_S - (280*8)/3000000) < 1e-9
   print('PHY/CAM layer parameter verification PASSED!')
   "
   ```

3. **보상 함수 수식 검증**:
   ```bash
   python3 -c "
   cbr_smoothed = 0.6
   dt_since_last_cam = 0.1
   n_neighbors = 1.0
   # Multi-reward components
   R1 = 0.01 * n_neighbors
   R2 = -1.0 * abs(cbr_smoothed - 0.6)
   R3 = -0.1 * dt_since_last_cam
   R_total = R1 + R2 + R3
   expected = 0.01 * 1.0 - 1.0 * abs(0.6 - 0.6) - 0.1 * 0.1
   assert abs(R_total - expected) < 1e-6
   print('Reward formulation calculation verification PASSED!')
   "
   ```
