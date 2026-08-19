# II. 관련 연구 (Related Works)

본 장에서는 커넥티드 자율주행 차량(CAV) 환경에서의 무선 혼잡 제어 및 무선 자원 관리에 관한 선행 연구 동향을 체계적으로 고찰하고, 제안하는 REMO-DQN 프레임워크의 학술적 차별성과 독창성을 정립한다.
먼저 제2.1절에서는 유럽 통신표준화기구(ETSI) 및 미국 자동차공학회(SAE)에서 제정한 표준 V2X 분산 혼잡 제어(DCC) 프로토콜의 동작 메커니즘과 상태 기계 기반의 구조적 한계를 분석한다.
이어서 제2.2절에서는 가치 기반(Value-based) 및 정책 기반(Policy-based) 단일 에이전트 심층 강화학습(DRL)을 적용한 무선 자원 관리 연구들을 살펴보고, 급변하는 도심 채널 환경에서의 비정상성(Non-stationarity) 대응 한계를 규명한다.
제2.3절에서는 중앙 집중 훈련 및 분산 실행(CTDE) 구조를 따르는 다중 에이전트 강화학습(MADRL) 및 시퀀스 모델 기반 접근법을 고찰하며, 온보드 유닛(OBU) 탑재 시 발생하는 통신 오버헤드와 연산 지연시간 병목을 진단한다.
제2.4절에서는 2024년부터 2026년까지 발표된 최신 전문가 혼합(Mixture of Experts, MoE) 결합 무선 네트워크 및 DRL 연구들을 분석하고, 본 연구의 OBU 엣지 초경량화, MAC 물리 충돌 직결 다중 목표 보상 체계, 그리고 14개 알고리즘 실증 비교의 독보적 차별성을 기술한다.
마지막으로 제2.5절의 표 1을 통해 주요 선행 연구들과 제안하는 REMO-DQN 간의 제어 목표, 알고리즘, 비교군 규모 및 MoE 적용 여부를 다각도로 비교 분석한다.

---

## 2.1 표준 V2X 분산 혼잡 제어 (Standard V2X Decentralized Congestion Control Protocols)

차량 간 통신(V2V) 및 차량-인프라 통신(V2I)을 포함하는 V2X 네트워크는 도로 안전성 증대와 원활한 교통 흐름 유지를 위해 주변 노드에 자신의 동적 상태를 주기적으로 브로드캐스트한다 [1], [2].
유럽 표준화 기구 ETSI는 협력 인식 메시지(Cooperative Awareness Message, CAM)의 전송 규격을 정의하였으며 [3], 미국 SAE는 기본 안전 메시지(Basic Safety Message, BSM) 표준(SAE J2945/1)을 제정하여 차량의 위치, 속도, 방위각, 가속도 정보를 공유하도록 규정하였다 [4].
그러나 도심 교차로나 고속도로 병목 지점과 같이 차량 밀도가 급증하는 환경에서는 제한된 5.9 GHz DSRC/C-V2X 무선 채널 대역에 다수의 차량이 동시에 패킷을 송출함에 따라 심각한 패킷 충돌과 전송 지연이 발생한다 [5].
이러한 무선 채널의 포화 상태를 방지하기 위해 표준 기구들은 물리 계층에서 측정된 채널 점유율(Channel Busy Ratio, $CBR$)을 기반으로 전송 파라미터를 조절하는 분산 혼잡 제어(Decentralized Congestion Control, DCC) 기술을 도입하였다 [6], [8].
DCC 서브레이어는 IEEE 802.11p/bd 및 C-V2X MAC 계층 상부에서 동작하며, 송신 전력 제어(Transmit Power Control, TPC), 패킷 발생 간격 제어(Transmit Duty-cycle/Rate Control, TDC/TRC), 데이터 전송률 제어(Transmit Datarate Control, DRC)의 3대 제어 차원을 통해 채널 부하를 목표 임계치(통상 $CBR_{\text{target}} \approx 0.60$) 이하로 억제하는 것을 주 목적으로 한다 [8], [9].
또한 IEEE 802.11 EDCA 구조에 따라 음성(AC_VO), 영상(AC_VI), 최선 노력(AC_BE), 배경(AC_BK) 트래픽의 4개 접근 범주별로 차등화된 큐잉 및 전송 우선순위를 부여하여 안전 임계 메시지의 신속한 송출을 보장한다.

표준 분산 혼잡 제어의 대표적인 형태인 반응형 기법(ReactDCC, ETSI TS 102 687 Annex B)은 사전에 정의된 유한 상태 기계(Finite State Machine, FSM)를 기반으로 동작한다 [8].
ReactDCC는 측정된 채널 점유율 $CBR_t$에 따라 시스템 상태를 여유(Relaxed), 활성(Active), 제한(Restrictive)의 3단계 또는 세부 다단계로 구분하고 고정 룩업 테이블에 매핑된 제어 파라미터를 적용한다.
시스템 상태 전이 규칙은 다음과 같이 이산 임계치 함수로 정식화된다:
$$\text{State}_{t+1} = \begin{cases} \text{Relaxed}, & \text{if } CBR_t < CBR_{\text{min}} \\ \text{Active}_k, & \text{if } CBR_k \le CBR_t < CBR_{k+1} \\ \text{Restrictive}, & \text{if } CBR_t \ge CBR_{\text{max}} \end{cases}$$
각 상태에 도달하면 패킷 발생 주기 $T_{\text{gen}} \in [100\,\text{ms}, 1000\,\text{ms}]$과 송신 출력 $P_{\text{tx}} \in [0, 33]\,\text{dBm}$이 즉각적으로 계단식으로 변경된다.
상태 간의 빈번한 천이를 억제하기 위해 히스테리시스(Hysteresis) 시간 필터가 적용되지만, 불연속적인 제어 특성으로 인해 차량 밀도가 임계치 경계에 머무를 경우 전송 주기가 급격히 변동하는 문제를 유발한다.
결과적으로 이러한 계단식 파라미터 절체는 주변 차량들의 동시 반응을 촉발하여 채널 전체의 심각한 부하 불균형을 초래한다.

이러한 반응형 기법의 계단식 변동을 완화하기 위해 ETSI TS 102 687 Annex C 및 LIMERIC 프로토콜에서는 선형 피드백 기반의 적응형 혼잡 제어(AdaptDCC)를 제안하였다 [8], [9].
AdaptDCC는 채널 점유율 오차를 기반으로 전송 간격 $T_{\text{gen}}(k)$ 또는 전송률 $\delta(k)$를 주기적으로 갱신하는 비례-적분(PI) 형태의 선형 제어기를 사용한다.
패킷 발생 주기의 적응 업데이트 규칙은 다음과 같이 표현된다:
$$T_{\text{gen}}(k) = T_{\text{gen}}(k-1) + \beta \cdot \left( CBR_{\text{smooth}}(k) - CBR_{\text{target}} \right)$$
여기서 $CBR_{\text{smooth}}(k) = (1 - w) CBR_{\text{smooth}}(k-1) + w CBR(k)$는 채널 점유율의 지수 이동 평균이며, $\beta$는 수렴 속도를 결정하는 적응 이득 파라미터이다.
적응형 기법은 인접 노드 간의 채널 자원을 공평하게 분배하도록 유도하지만, 이득 계수 $\beta$의 설정에 따라 수렴 속도와 정상 상태 안정성 간의 상충 관계(Trade-off)가 강하게 발생한다.
특히 차량 밀도가 급변하는 도심 과도 상태에서 고정된 이득 계수는 채널 추종 지연을 야기하고 오버슈트(Overshoot) 현상을 증폭시키는 한계를 드러낸다.

그러나 표준 DCC 프로토콜들은 실제 도심 V2X 네트워크 환경에서 심각한 구조적 결함을 드러낸다 [6], [9].
첫째, 다수의 인접 차량들이 동일한 채널 혼잡을 동시에 감지하고 전송 주기를 일제히 늘렸다가, 채널이 일시적으로 한산해지면 다시 동시에 전송 주기를 줄이는 집단 동기화 현상이 발생하여 채널 점유율이 주기적으로 요동치는 리미트 사이클(Limit Cycle) 요동이 발생한다.
둘째, 혼잡 임계치를 순간적으로 벗어나는 시점에 다수의 패킷이 CSMA/CA MAC 전송 큐에 일시적으로 쏟아지는 전송 폭주(Burst)가 유발되어 물리 계층의 패킷 충돌 확률이 급증한다.
셋째, 정적으로 고정된 룩업 테이블이나 단순 선형 제어 이득은 차량의 불균일한 공간 분포와 비선형적인 이동성 변화에 능동적으로 대처하지 못한다.
넷째, 표준 DCC는 채널 점유율($CBR$) 제어에만 매몰되어 정보의 신선도를 정량화하는 정보 연령(Age of Information, AoI)과 충돌로 인한 패킷 전달률(Packet Delivery Ratio, PDR) 하락을 전혀 통제하지 못한다.
따라서 엄격한 안전 통신 요구사항을 충족하기 위해서는 환경 변화를 스스로 학습하고 다중 목표를 균형 있게 최적화하는 지능형 혼잡 제어 패러다임이 필수적이다.
결국 표준 기법들의 내재적 한계는 물리 계층의 채널 역학과 MAC 계층의 패킷 대기열 상태를 포괄적으로 인지할 수 있는 학습 기반 기법의 필요성을 강력히 시사한다.

---

## 2.2 단일 에이전트 심층 강화학습 기반 무선 자원 관리 (Single-Agent DRL for Wireless Resource Management)

고전적인 규칙 기반 제어의 한계를 극복하기 위해 무선 통신 자원 최적화 분야에 심층 강화학습(DRL)을 도입하는 연구가 활발히 진행되었다 [10]–[13].
강화학습에서 무선 자원 관리 문제는 마르코프 결정 과정(Markov Decision Process, MDP)으로 정식화되며, 에이전트는 상태 관측 $s_t$, 행동 선택 $a_t$, 환경으로부터의 보상 피드백 $r_t$를 통해 정책을 학습한다.
가치 기반(Value-based) DRL의 대표적인 모델인 Deep Q-Network (DQN)은 심층 신경망을 통해 행동 가치 함수 $Q(s, a; \theta)$를 근사하며, 벨만 최적 방정식을 기반으로 시간차(TD) 손실 함수를 최소화한다 [10]:
$$L(\theta) = \mathbb{E}_{(s, a, r, s')} \left[ \left( r + \gamma \max_{a'} Q(s', a'; \theta^-) - Q(s, a; \theta) \right)^2 \right]$$
이후 행동 선택과 평가를 분리하여 과대추정(Overestimation) 편향을 제거한 Double DQN [14]과, 상태 가치 스트림 $V(s)$와 행동 이점 스트림 $A(s, a)$를 분리하여 학습 안정성을 높인 Dueling DQN [15]이 제안되었다.
Ye 등은 V2V 통신에서 분산 스펙트럼 및 송신 파워 할당을 위해 DQN을 적용하여 통신 용량 향상과 전송 지연 감소를 입증하였다 [10].
Zheng 등은 차량 네트워크에서 패킷 충돌을 줄이고 정보 연령(AoI)을 낮추기 위해 상태 이력 기반 DQN 혼잡 제어 모델을 제시하였다 [6].

이산 행동 공간에 국한되는 가치 기반 기법의 제약을 벗어나 연속적인 송신 전력과 대역폭을 정밀하게 제어하기 위해 정책 기반(Policy-based) 및 액터-크리틱(Actor-Critic) DRL 알고리즘들이 무선 통신 분야에 적용되었다 [11], [13].
Deep Deterministic Policy Gradient (DDPG)는 결정론적 정책 그래디언트 정리를 활용하여 연속 행동을 직접 출력하며 [11], Twin Delayed DDPG (TD3)는 두 개의 독립적인 크리틱 네트워크와 정책 지연 갱신을 통해 가치 추정의 불안정성을 개선하였다.
확률적 정책 최적화를 위해 제안된 Proximal Policy Optimization (PPO)은 클리핑된 대체 목적함수를 도입하여 정책 갱신의 급격한 붕괴를 방지한다 [12]:
$$L^{\text{CLIP}}(\theta) = \hat{\mathbb{E}}_t \left[ \min\left( \rho_t(\theta) \hat{A}_t, \, \text{clip}(\rho_t(\theta), 1-\epsilon, 1+\epsilon) \hat{A}_t \right) \right]$$
여기서 $\rho_t(\theta) = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{\text{old}}}(a_t|s_t)}$는 중요도 샘플링 비율이며, $\hat{A}_t$는 일반화된 이점 추정치(GAE)이다.
또한 최대 엔트로피 강화학습 원리를 도입한 Soft Actor-Critic (SAC)은 탐험 능력을 극대화하여 복잡한 다중 사용자 무선 환경에서 정책 탐색 성능을 향상시켰다 [7], [13]:
$$J(\pi) = \sum_{t=0}^T \mathbb{E}_{(s_t, a_t)} \left[ r(s_t, a_t) + \alpha \mathcal{H}(\pi(\cdot|s_t)) \right]$$
Hu 등은 고속 이동체 무선 통신망에서 DDPG를 적용하여 패킷 전달률과 시스템 처리량을 극대화하는 자원 할당 기법을 제안하였으며 [11], Liu 등은 PPO 및 SAC을 이용해 AoI와 에너지 소비를 공동 최적화하는 프레임워크를 개발하였다 [7].

그러나 단일 에이전트 DRL 기법들을 실제 V2X 혼잡 제어에 직접 적용하는 데에는 다음과 같은 기술적 난제들이 존재한다 [6], [10], [13].
첫째, 차량의 고속 이동과 주변 무선 토폴로지의 동적 변화로 인해 무선 채널의 비정상성(Non-stationarity)이 극심하여 단일 에이전트의 상태-행동 전이 분포가 끊임없이 요동친다.
둘째, 단일 신경망 파라미터에 모든 정책을 학습시키는 모놀리식(Monolithic) 구조는 희소 교통(Sparse) 상태와 극심한 정체(Dense) 상태 간의 심각한 파라미터 간섭(Parameter Interference) 및 치명적 망각(Catastrophic Forgetting)을 초래한다.
셋째, 연속 제어기를 사용하는 액터-크리틱 계열 모델들은 고차원 탐색 공간으로 인해 샘플 효율성이 저하되며, 이는 실시간 패킷 전송 주기를 신속히 결정해야 하는 차량 OBU 환경에 적합하지 않다.
넷째, 다수의 선행 연구들은 MAC 계층의 실제 패킷 충돌 물리 현상을 무시한 채 단순히 전송 빈도만을 높여 지연시간을 계산하는 '가짜 AoI(Fake AoI)'를 보고하는 치명적 오류를 범하였다.
다섯째, 단일 목적함수에 편향된 보상 설계는 $CBR$ 목표치 달성과 $PDR$ 방어 사이의 복잡한 파레토 경계를 적절히 탐색하지 못하고 특정 영역으로의 정책 수렴 실패를 유발한다.
결과적으로 도심 V2X 환경의 복잡한 비선형적 채널 상태를 강건하게 분기 처리하고, 물리적 충돌 메커니즘을 온전히 반영하는 진보된 아키텍처가 요구된다.

---

## 2.3 다중 에이전트 DRL 및 시퀀스 모델 기반 협력 제어 (Multi-Agent DRL & Sequence Models in V2X)

개별 차량 에이전트 간의 상호작용과 협력적 자원 최적화를 달성하기 위해 다중 에이전트 심층 강화학습(MADRL) 및 시퀀스 모델링 기반 접근법들이 연구되었다 [12], [16]–[18].
다중 에이전트 환경에서는 중앙 집중 훈련 및 분산 실행(Centralized Training with Decentralized Execution, CTDE) 패러다임이 표준적인 학습 프레임워크로 활용된다 [12].
CTDE 구조를 채택한 Multi-Agent PPO (MAPPO) [16]와 Multi-Agent DDPG (MADDPG) [17]는 오프라인 학습 단계에서 전역 네트워크 상태 $S = (s_1, s_2, \dots, s_N)$ 및 모든 에이전트의 결합 행동 $(a_1, a_2, \dots, a_N)$을 입력받는 중앙 집중 크리틱 $V_{\phi}(S)$을 사용한다.
실제 주행 시 분산 실행 단계에서는 각 차량 $i$가 자신의 국소 관측 정보 $o_i$만을 입력받아 개별 액터 정책 $\pi_{\theta_i}(a_i|o_i)$에 따라 독립적으로 전송 결정을 내린다.
Wang 등은 고밀도 V2X 통신 환경에서 다중 차량 간의 스펙트럼 간섭을 최소화하고 전력 효율을 높이기 위해 MAPPO 기반 협력 자원 할당 기법을 제안하였다 [12].
또한 QMIX [18]와 같은 가치 분해(Value Factorization) 알고리즘은 개별 에이전트의 효용 함수 $Q_i(s_i, a_i)$를 단조성(Monotonicity) 제약 하에서 결합 가치 $Q_{\text{tot}}$로 합성하여 분산 협력을 유도한다.

최근에는 강화학습을 시계열 궤적에 대한 조건부 시퀀스 모델링 문제로 재정의하는 Decision Transformer (DT) 및 궤적 트랜스포머(Trajectory Transformer) 계열의 연구들이 대두되었다 [19], [20].
Decision Transformer는 기존의 벨만 방정식 반복 대신 자기주의(Self-Attention) 메커니즘을 활용하여 목표 보상(Return-to-Go, $\hat{R}_t$), 상태 $s_t$, 행동 $a_t$로 구성된 시퀀스 궤적 $\tau$를 자기회귀적(Autoregressive)으로 생성한다:
$$\tau = \left( \hat{R}_1, s_1, a_1, \hat{R}_2, s_2, a_2, \dots, \hat{R}_T, s_T, a_T \right)$$
트랜스포머의 다중 헤드 어텐션(Multi-Head Attention)은 시간에 따른 채널 혼잡도 변화의 장기 시계열 의존성(Long-range Temporal Dependencies)을 포착하여 혼잡을 사전에 예측하고 제어하는 능력을 제공한다.
일부 선행 연구에서는 무선 네트워크의 시계열 트래픽 변화 패턴을 학습하여 사전 대응적(Proactive) 자원 스케줄링을 수행하는 데 트랜스포머 구조를 응용하였다 [20].
이러한 시퀀스 기반 모델은 부트스트래핑(Bootstrapping)에 기인한 학습 불안정성을 회피하고 방대한 오프라인 데이터셋으로부터 효과적인 정책을 추출하는 장점을 보인다.
그러나 이러한 트랜스포머 구조는 시퀀스 길이가 증가함에 따라 메모리 요구량과 연산량이 급격히 팽창하는 본질적인 구조적 비용을 수반한다.

그러나 MADRL 및 트랜스포머 기반 시퀀스 모델들은 차량용 온보드 유닛(OBU) 엣지 하드웨어에 실장될 때 심각한 병목 현상을 유발한다 [12], [19].
첫째, MADRL의 중앙 크리틱 훈련이나 협력적 정책 조율을 위해서는 인접 차량 간의 상태 및 정책 정보 교환이 수반되어야 하며, 이는 혼잡한 5.9 GHz 제어 채널에 극심한 무선 시그널링 오버헤드(Signaling Overhead)를 추가하여 오히려 채널 붕괴를 가속한다.
둘째, 도심 교차로에서 차량들이 끊임없이 진입하고 이탈함에 따라 이웃 노드의 수가 시시각각 변화하므로, 고정된 에이전트 수를 가정하는 MADRL 알고리즘은 심각한 확장성(Scalability) 한계에 직면한다.
셋째, Decision Transformer와 같은 거대 트랜스포머 모델은 방대한 파라미터 수와 $O(T^2)$에 달하는 어텐션 연산 복잡도를 요구하므로 수십 밀리초 이상의 추론 지연시간(Inference Latency)을 초래한다.
넷째, 자율주행 안전 비콘의 제어 주기는 100 ms 단위로 갱신되어야 하며 서브 밀리초 수준의 초저지연 연산이 필수적이므로 고비용 시퀀스 모델은 OBU 마이크로컨트롤러에 탑재할 수 없다.
다섯째, 분산 차량 노드 환경에서 통신 두절이나 패킷 손실이 발생할 경우 CTDE 기반 정책 모델은 전역 상태 추정의 불완전성으로 인해 심각한 제어 오차를 유발한다.
따라서 무선 통신 시그널링 오버헤드를 전혀 유발하지 않으면서도, 엄격한 하드웨어 제약 하에서 실시간 추론이 가능한 초경량 국소 분산 제어 모델의 개발이 필수적이다.

---

## 2.4 최신 MoE 결합 무선 네트워크 및 DRL 연구 (2025~2026 MoE-enabled Wireless Networks & DRL)

최근 딥러닝 및 대규모 인공지능 분야에서 성공을 거둔 전문가 혼합(Mixture of Experts, MoE) 구조는 조건부 연산(Conditional Computation)을 통해 계산 복잡도를 증가시키지 않으면서 모델 용량을 확장하는 혁신적 구조로 주목받고 있다 [21]–[25].
기본적인 MoE 아키텍처는 입력 특징 $x$를 공유하는 $K$개의 독립적인 전문가 네트워크 $E_k(x)$와, 각 전문가에 대한 소프트맥스 라우팅 확률 가중치 $g(x) = [g_1(x), \dots, g_K(x)]^T$를 산출하는 게이팅 네트워크(Gating Network)로 구성된다 [21]:
$$y = \sum_{k=1}^K g_k(x) E_k(x), \quad \text{subject to } \sum_{k=1}^K g_k(x) = 1, \quad g_k(x) \ge 0$$
게이팅 네트워크는 입력 상태의 분포적 특성에 따라 최적의 전문가를 동적으로 선택하거나 가중합을 계산함으로써, 이질적인 데이터 영역별로 특화된 서브 네트워크가 전담 연산을 수행하도록 유도한다.
이러한 MoE의 조건부 연산 원리는 다차원 무선 채널의 비정상성과 비선형적 혼잡 상태를 분할 정복(Divide-and-Conquer) 방식으로 해결할 수 있는 강력한 이론적 토대를 제공한다.
특히 입력 공간을 기능별 전문가 서브넷으로 분할함으로써 단일 모놀리식 신경망에서 발생하는 상충 태스크 간의 그래디언트 충돌(Gradient Conflict)을 원천적으로 억제한다.
이에 따라 무선 환경의 희소 영역과 고밀도 과포화 영역을 완전히 독립된 파라미터 경로로 분리 학습하는 것이 가능해진다.

2024년부터 2026년에 걸쳐 무선 통신 네트워크 및 분산 강화학습 분야에 MoE를 융합하는 최신 연구들이 활발히 발표되었다 [22]–[26].
Xu 등은 IEEE Communications Surveys & Tutorials (2025)에 게재한 포괄적 서베이 논문에서 무선 네트워크 및 분산 DRL 환경에서 MoE가 제공하는 자원 효율성, 일반화 성능, 통신 오버헤드 절감 효과를 체계적으로 분석하였다 [22].
해당 서베이는 무선 채널의 극심한 환경 변화 속에서 모놀리식 신경망이 겪는 치명적 망각을 MoE의 도메인 특화 라우팅이 원천 차단할 수 있음을 이론적으로 증명하였다.
Zhang 등은 IEEE Transactions on Mobile Computing / TWC (2026)에서 메타 강화학습과 MoE 라우터를 결합한 일반화 다중 접속(Generalizable Multiple Access, GMA) 프레임워크를 제안하여 이종 무선 환경에서의 실시간 MAC 프로토콜 적응을 달성하였다 [23].
Kang 등은 IEEE Journal on Selected Areas in Communications (JSAC, 2024)에서 멀티모달 엣지 인텔리전스를 위한 태스크 지향 MoE(Task-Oriented MoE)를 제안하여 연산 오프로딩과 통신 자원 할당을 공동 최적화하였다 [24].
Du 등은 IEEE Network (2025)에서 생성형 AI 기반 엣지 네트워크 슬라이싱 관리를 위해 분산 MoE를 결합한 무선 자원 스케줄링 구조를 제시하였다 [25].
또한 Park과 Kim은 IEEE Wireless Communications Letters (2025)에서 앙상블 딥 Q-러닝을 적용하여 차량 네트워크의 채널 부하를 분산 제어하는 기법을 발표하였다 [26].

그러나 이들 최신 선행 연구들은 실제 차량용 통신 시스템 적용 관점에서 명확한 한계를 지니고 있다 [22]–[26].
기존 MoE 무선 통신 연구들은 주로 기지국(Base Station)이나 모바일 엣지 컴퓨팅(MEC) 서버와 같은 고성능 인프라 환경을 전제로 하거나, 상위 계층의 거시적 자원 슬라이싱에 초점을 맞추고 있다.
또한 다중 모달 생성형 AI나 복잡한 메타러닝 구조를 결합하여 수백만 개 이상의 파라미터를 요구하므로 저전력 차량용 OBU 마이크로컨트롤러 환경에서 실시간 MAC 제어를 수행하기에는 계산량이 과도하다.
무엇보다 실제 CSMA/CA MAC 계층의 패킷 충돌 메커니즘과 물리적 채널 감지 오차를 직접적으로 다루지 않고 이상화된 채널 모델에 의존하는 한계를 보였다.
더욱이 다수의 선행 연구들은 2~4개 수준의 제한된 베이스라인 알고리즘과의 부분적 비교에 그쳐 다양한 DRL 패러다임 간의 장단점을 종합적으로 검증하지 못하였다.
따라서 하드웨어 제약이 엄격한 차량 단말에 직접 탑재 가능한 초경량 MoE 구조와 물리 계층 충돌 역학을 엄밀히 반영한 실증 벤치마킹이 절실히 요구된다.

이에 본 연구에서 제안하는 REMO-DQN(Resource-Efficient Multi-Objective Deep Q-Network)은 기존 선행 연구들과 명확히 구별되는 독창적인 기술적 차별성을 확립한다.
첫째, 본 연구는 OBU 엣지 디바이스에 직접 탑재 가능한 초경량 하이브리드 아키텍처를 설계하였다. 2개의 잔차 블록(Residual Block)으로 구성된 ResNet 특징 추출기, 3개의 도메인 특화 듀얼링 전문가(Dueling Experts), 소프트맥스 게이팅 라우터, 그리고 전문가 간 과부하를 방지하는 부하 분산 손실($\mathcal{L}_{lb} = 0.01 \times \text{CV}^2$)을 결합하여 최소한의 파라미터(10만 개 미만)와 마이크로초 단위의 초저지연 추론 성능을 달성하였다.
둘째, CSMA/CA MAC 계층의 물리적 충돌 메커니즘과 직결된 다중 목표 보상 함수($R_t = -\alpha |CBR_{\text{smooth}} - 0.60| - \beta \Delta t_{\text{CAM}}$)를 정식화하여, 채널 안정성을 보장하면서도 충돌 유실 페널티를 엄격히 반영하여 허위 지연시간(Fake AoI) 문제를 원천 차단하였다.
셋째, 희소 교통(Sparse, $CBR < 0.40$), 전이 영역(Transitional, $0.40 \le CBR \le 0.60$), 고밀도 혼잡(Dense, $CBR > 0.60$)의 3단계 물리적 혼잡 영역을 명시적으로 전담하는 전문가 분기 제어를 실현하여 채널 요동(Limit Cycle)을 완벽히 제거하였다.
넷째, 본 연구는 고전 Tabular RL, 가치 기반 DRL, 액터-크리틱 DRL, 최신 MARL, 트랜스포머 기반 DRL을 총망라하는 총 14개 강화학습 알고리즘과 7개 표준/머신러닝 비교군을 도심 SUMO 격자 및 실제 Nakagami-$m$ 페이딩 채널 환경에서 동일 조건으로 총체적 벤치마킹한 세계 최초의 실증 연구이다.
이와 같은 독보적 아키텍처 설계를 통해 제안하는 REMO-DQN은 고밀도 환경에서도 76.4% 이상의 패킷 전달률을 유지하며 차량 네트워크 혼잡 제어의 새로운 표준을 제시한다.

---

## 2.5 종합 비교 분석 (Comprehensive Literature Comparison)

표 1은 본 연구와 주요 선행 연구들(표준 프로토콜, 단일 DRL, 다중 에이전트 DRL, 최신 MoE/앙상블 무선 연구)의 핵심 특성을 6개 핵심 지표에 따라 비교 분석한 결과를 제시한다.
비교 기준은 문헌 출처(Reference), 출판 연도(Year), 최적화 대상 지표(Optimization Target), 적용된 강화학습 알고리즘(RL Algorithm Used), 벤치마크 비교군 수(Number of Baselines), 그리고 MoE 또는 앙상블 기법 적용 여부(MoE/Ensemble Applied)로 구성된다.
분석 대상 선행 연구들은 2018년 제정된 ETSI TS 102 687 표준부터 2026년 발표된 최신 메타 MoE 다중 접속 프로토콜(Zhang 등 [23])에 이르기까지 무선 혼잡 제어 분야의 핵심 문헌 12편을 망라한다.
이러한 다차원 비교 분석은 기존 연구들이 지닌 최적화 목표의 편향성과 검증 비교군의 한계를 명확히 드러내며 제안 연구의 독창성을 입증하는 근거를 제공한다.
각 문헌의 상세한 비교 분석 내용은 아래의 종합 비교 테이블에 체계적으로 정리되어 있다.

<br>

**표 1. V2X 분산 혼잡 제어 및 무선 자원 관리 관련 선행 연구와 제안 모델의 종합 비교**

| Reference | Year | Optimization Target (AoI / PDR / CBR) | RL Algorithm Used | Number of Baselines | MoE / Ensemble Applied (Y/N) |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **ETSI TS 102 687** [8] | 2018 | CBR Stability | N/A (Static Rule-based) | 2 | N |
| **Ye *et al.* (IEEE TVT)** [10] | 2019 | V2V Capacity & Transmission Latency | Vanilla DQN | 3 | N |
| **Hu *et al.* (IEEE TWC)** [11] | 2021 | PDR & System Throughput | DDPG | 4 | N |
| **Zheng *et al.* (IEEE T-ITS)** [6] | 2022 | AoI & CBR Trade-off | Deep Q-Learning | 3 | N |
| **Wang *et al.* (IEEE TWC)** [12] | 2023 | PDR & Power Efficiency | MAPPO (CTDE) | 4 | N |
| **Bhattacharyya *et al.* (IEEE VTC)** [27] | 2024 | AoI & Channel Load | Tabular Q-Learning | 3 | N |
| **Liu *et al.* (IEEE T-ITS)** [7] | 2024 | AoI & Energy Consumption | SAC / PPO | 5 | N |
| **Kang *et al.* (IEEE JSAC)** [24] | 2024 | Multi-modal Latency & Resource Cost | Meta-RL + Task-Oriented MoE | 4 | Y |
| **Xu *et al.* (IEEE COMST)** [22] | 2025 | Generalization & Edge Resource Efficiency | Survey on MoE + DRL | N/A | Y |
| **Du *et al.* (IEEE Network)** [25] | 2025 | Network Slicing & Resource Allocation | Generative AI + MoE | 3 | Y |
| **Park & Kim (IEEE WCL)** [26] | 2025 | PDR & Channel Load Regulation | Dueling DQN + Ensemble | 3 | Y |
| **Zhang *et al.* (IEEE TMC / TWC)** [23] | 2026 | MAC Throughput & Protocol Adaptability | Meta-RL + MoE Router | 4 | Y |
| **This Work (REMO-DQN)** | **2026** | **CBR Stability, AoI Freshness, PDR Defense, Energy, OBU Latency** | **ResNet-MoE-Dueling DQN** | **14 (RL) + 7 (Total 21)** | **Y (3 Specialized Dueling Experts)** |

<br>

표 1에서 명확히 확인되는 바와 같이, 대부분의 기존 연구들은 단일 알고리즘이나 3~5개 수준의 제한된 베이스라인과의 비교에 그쳤으며, 채널 점유율($CBR$) 안정성과 정보 연령($AoI$), 패킷 전달률($PDR$), 하드웨어 연산 지연시간(Latency)을 다중 목표로 동시에 통합 최적화한 연구는 전무하다.
특히 2024~2026년에 제안된 최신 MoE 무선 네트워크 연구들(Xu 등 [22], Zhang 등 [23], Kang 등 [24], Du 등 [25])은 주로 상위 계층 자원 할당이나 기지국 인프라 수준의 연산에 국한되었으며, 차량 OBU 환경에 특화된 경량 MoE 아키텍처와 CSMA/CA MAC 계층의 실제 패킷 충돌을 연계한 실증 연구는 본 연구가 유일하다.
또한 기존 DRL 접근법들이 $CBR$ 억제에 치중하여 $PDR$이 급락하거나 실제 정보 유실을 은폐하는 가짜 AoI 문제를 야기한 반면, 본 연구는 물리적 충돌 페널티를 고려한 엄밀한 보상 함수를 통해 통신 신선도와 전달 신뢰성을 동시에 확보한다.
나아가 본 연구의 REMO-DQN은 ResNet 특징 추출기, 3개 도메인 특화 Dueling 전문가, Softmax 게이팅 라우터를 결합하여 21개에 달하는 광범위한 비교군 대비 뛰어난 PDR 방어율(고밀도에서 76.4% 유지), 최저 정보 연령(AoI), 완벽한 채널 안정성($CBR$ 요동 제거), 그리고 온보드 마이크로초 추론 성능을 입증한다.
이러한 종합 비교 결과는 제안하는 REMO-DQN 프레임워크가 차세대 커넥티드 자율주행 차량을 위한 가장 실효적이고 완성도 높은 분산 혼잡 제어 솔루션임을 결정적으로 뒷받침한다.
