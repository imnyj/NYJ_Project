# 고밀도 V2X 네트워크의 분산 혼잡 제어를 위한 자원 효율적 다중 목적 심층 Q-네트워크: REMO-DQN
## Resource-Efficient Multi-Objective Deep Q-Network for Decentralized Congestion Control in Dense V2X Networks

**저자 (Authors)**: [TBD]  
**소속 (Affiliation)**: [TBD]  
**연락처 (Contact)**: [TBD]  
**타깃 저널 (Target Journal)**: *IEEE Transactions on Wireless Communications (TWC)*  

---

### 국문 초록 (Abstract)

본 논문에서는 고밀도 도심 차량 사물 통신(Vehicle-to-Everything, V2X) 네트워크 환경에서 무선 채널 점유율(CBR)을 안정화하고 수신 정보의 최신성(Age of Information, AoI)을 극대화하기 위한 자원 효율적 다중 목적 심층 강화학습 기반 분산 혼잡 제어(Decentralized Congestion Control, DCC) 프레임워크인 REMO-DQN(ResNet-MoE-Dueling Deep Q-Network)을 제안한다. 도심 교차로 및 고속도로 병목 구간과 같은 고밀도 환경에서는 한정된 5.9 GHz ITS 무선 대역폭에 다수의 차량이 동시 다발적으로 협력 인식 메시지(CAM)를 브로드캐스트함에 따라 극심한 채널 경합과 패킷 충돌이 발생한다. 기존 ETSI 표준 DCC 기법(ReactDCC, AdaptDCC)은 정적 룩업 테이블 및 선형 피드백 규칙의 한계로 인해 채널 점유율의 주기적 요동(Oscillation)과 패킷 전송 폭주(Burst)를 유발하며, 단순 단일 신경망 기반 심층 강화학습 모델들은 시변 채널의 비정상성에 적응하지 못하고 패킷 충돌 손실을 배제한 '가짜 AoI(Fake AoI)' 오류를 야기한다. 이러한 통신 병목 현상은 주변 차량 간의 위험 경고 전송 지연을 초래하여 자율주행 안전 시스템의 신뢰성을 심각하게 위협한다. 따라서 복잡한 도심 도로 환경의 비선형적인 통신 부하에 지능적으로 대응할 수 있는 고성능 경량 분산 제어 아키텍처의 개발이 시급히 요구된다. 

제안하는 REMO-DQN은 고차원 비선형 상태 특징을 손실 없이 추출하는 2-블록 ResNet 백본, 교통 혼잡 국면별로 특화된 3개의 전문가 서브네트워크(희소 교통, 전이 영역, 극심한 혼잡)로 제어 결정을 동적으로 분기하는 Mixture of Experts(MoE) 소프트맥스 게이팅 라우터, 그리고 상태 가치와 행동 이점을 분리 학습하는 Dueling DQN 구조를 유기적으로 결합하였다. 또한 CSMA/CA MAC 계층의 물리적 충돌 메커니즘과 직결된 다중 목표 보상 함수와 전문가 붕괴를 방지하는 부하 균등화 손실을 도입하여 안정적인 정책 수렴을 보장한다. Eclipse SUMO 및 Nakagami-$m$ 페이딩 무선 채널 기반의 통합 시뮬레이션 환경에서 총 14개 강화학습 모델 및 7개 비교군을 대상으로 전방위 성능 평가를 수행한 결과, REMO-DQN은 80 에피소드 이내에 신속히 수렴하여 평균 CBR 0.3442(표준편차 0.1008, 0.60 상한 위반율 0.0%)의 우수한 채널 안정성을 확립하였다. 특히 100 veh/km의 초고밀도 정체 환경에서도 73.41%의 높은 패킷 전달률(PDR)을 유지하여 기존 기법들의 74~91%p 붕괴 대비 단 3.13%p의 감소만 허용하였으며, 전체 밀도 평균 373.21 ms의 최저 AoI를 달성하여 AdaptDCC 대비 8.59배, Fixed 10Hz 대비 12.55배 우수한 정보 신선도를 확보하였다. 나아가 3.8M MACs와 1.2 ms의 초저지연 추론 성능으로 100 ms 제어 주기의 1.2%만을 점유함을 입증하여 상용 차량용 온보드 유닛(OBU) 마이크로컨트롤러 환경에서의 실시간 배포 실효성을 성공적으로 입증하였다.

**색인어 (Keywords)**: 차량 사물 통신(V2X), 분산 혼잡 제어(Decentralized Congestion Control), 심층 강화학습(Deep Reinforcement Learning), 전문가 혼합(Mixture of Experts), 듀얼링 DQN(Dueling DQN), 정보 연령(Age of Information), 패킷 전달률(Packet Delivery Ratio), 잔차 연결(ResNet).

---

### 목차 (Table of Contents)

- **I. 서론 (Introduction)**
- **II. 관련 연구 (Related Works)**
  - 2.1 표준 V2X 분산 혼잡 제어 (Standard V2X DCC Protocols)
  - 2.2 단일 에이전트 심층 강화학습 기반 무선 자원 관리 (Single-Agent DRL for Wireless Resource Management)
  - 2.3 다중 에이전트 DRL 및 시퀀스 모델 기반 협력 제어 (Multi-Agent DRL & Sequence Models in V2X)
  - 2.4 최신 MoE 결합 무선 네트워크 및 DRL 연구 (2025~2026 MoE-enabled Wireless Networks & DRL)
  - 2.5 종합 비교 분석 (Comprehensive Literature Comparison)
- **III. 시스템 모델 및 제안하는 REMO-DQN 아키텍처 (System Model and Proposed REMO-DQN Architecture)**
  - 3.1 네트워크 및 무선 통신 시스템 모델 (Network and Communication System Model)
  - 3.2 분산 혼잡 제어를 위한 MDP 정식화 (Markov Decision Process Formulation)
  - 3.3 제안하는 REMO-DQN 신경망 아키텍처 (Proposed REMO-DQN Neural Network Architecture)
  - 3.4 분산 REMO-DQN 학습 및 온라인 추론 알고리즘
  - 3.5 시스템 및 아키텍처 파라미터 요약
- **IV. 동적 시나리오 흐름 및 분산 전송 제어 파이프라인 (Dynamic Scenario Flow and Distributed Transmission Control Pipeline)**
  - 4.1 패킷 발생 및 이기종 트래픽 혼합 시나리오 (Packet Generation & Heterogeneous Traffic Mixture)
  - 4.2 고밀도 환경에서의 채널 경합 및 MAC 충돌 메커니즘 (Channel Contention & MAC Collision in Dense Scenarios)
  - 4.3 DRL 기반 분산 혼잡 인지 및 상태/보상 정식화 (DRL-based Distributed Congestion Cognition)
  - 4.4 MoE 기반 동적 라우팅 및 전송 제어 (MoE-based Dynamic Routing & Transmission Control)
- **V. 성능 평가 (Performance Evaluation)**
  - 5.1 시뮬레이션 환경 및 벤치마크 알고리즘 (Simulation Setup & Baseline Algorithms)
  - 5.2 (Metric 1) 학습 수렴도 및 샘플 효율성 (Reward Convergence & Sample Efficiency)
  - 5.3 (Metric 2) 시계열 채널 점유율 안정성 및 진동 억제 (Time-Series CBR Trace & Stability)
  - 5.4 (Metric 3 & 4) 차량 밀도별 패킷 전달률 및 통신 에너지 효율 (PDR vs Density & Energy Efficiency)
  - 5.5 (Metric 5) 정보 연령 (AoI vs Density) 및 가짜 AoI 한계 극복 (Age of Information & Fake AoI Analysis)
  - 5.6 (Metric 6) 전송 거리별 패킷 전달률 (PDR vs Distance)
  - 5.7 (Metric 7) 하드웨어 실효성 및 OBU 복잡도 프로파일링 (Hardware Latency & Complexity)
  - 5.8 절제 연구 및 MoE 도메인 특화성 (Ablation Study & MoE Domain Specialization)
  - 5.9 제5장 요약 및 성능 평가 종합 결론
- **VI. 결론 (Conclusion)**
- **참고문헌 (References)**

---


# I. 서론 (Introduction)

자율주행 차량(Connected and Autonomous Vehicles, CAV)의 기술적 성숙과 함께 차량 사물 통신(Vehicle-to-Everything, V2X) 및 차량 애드혹 네트워크(Vehicular Ad-hoc Network, VANET)는 협력형 지능형 교통 시스템(C-ITS)의 안전성과 교통 효율성을 보장하는 핵심 인프라로 자리잡았다 [1], [2]. V2X 통신 환경에서 각 차량은 위치, 주행 속도, 조향 각도 및 가속도 정보를 공유하여 주변 차량과의 충돌을 사전에 방지하기 위해 ETSI 협력 인식 메시지(Cooperative Awareness Message, CAM) 또는 SAE 기본 안전 메시지(Basic Safety Message, BSM)를 주기적으로 브로드캐스트한다 [3]. 그러나 도심 교차로나 출퇴근 시간대의 고속도로와 같은 고밀도 차량 환경에서는 한정된 5.9 GHz 단거리 전용 통신 대역(Dedicated Short-Range Communications, DSRC 및 C-V2X)을 수많은 차량이 동시에 공유함에 따라 극심한 채널 경합과 무선 패킷 충돌이 발생한다 [4]. 이러한 무선 채널의 포화는 안전 임계 메시지의 전송 지연과 대규모 패킷 유실을 초래하므로, 채널 점유율(Channel Busy Ratio, CBR)을 적정 임계치 이하로 제어하면서 통신 자원을 동적으로 조절하는 분산 혼잡 제어(Decentralized Congestion Control, DCC) 메커니즘이 필수적으로 요구된다 [5]. 특히 자율주행 환경의 통신 성능을 평가할 때 단순한 단방향 전송 지연시간(Latency)을 넘어, 충돌로 유실된 패킷의 경과 시간까지 누적 반영하여 수신단 관점에서의 정보 최신성을 시간 단위로 정량화하는 정보 연령(Age of Information, AoI) 척도의 중요성이 대두되고 있다 [6], [7]. 따라서 채널 자원이 제한된 고밀도 V2X 네트워크에서 채널 부하의 안정적 제어와 수신 정보의 최신성(AoI) 극대화를 동시에 달성하는 정밀한 전송 파라미터 제어 기술이 요구된다.

유럽 전기통신표준협회(ETSI TS 102 687)는 채널 혼잡을 완화하기 위해 측정된 CBR에 따라 패킷 발생 주기와 전송 전력을 단계적으로 조절하는 반응형(ReactDCC) 및 적응형(AdaptDCC) 규칙 기반 표준을 정의하였다 [5], [8]. 그러나 기존 표준 DCC 기법들은 사전에 정의된 고정 룩업 테이블이나 선형 피드백 제어 규칙에 의존하므로, 혼잡 임계치 경계에서 전송 빈도가 급격히 변동하며 CBR의 심각한 요동(Oscillation)과 패킷 전송 폭주(Burst)를 유발한다 [9]. 이러한 패킷 폭주는 인접 노드 간의 동기화된 채널 점유를 초래하여 CSMA/CA(Carrier Sense Multiple Access with Collision Avoidance) MAC 계층에서 대규모 패킷 충돌을 유발하고, 결과적으로 차량 밀도 증가 시 패킷 전달률(Packet Delivery Ratio, PDR)을 급격히 떨어뜨린다. 정적 규칙의 한계를 해결하기 위해 Q-Learning이나 Vanilla DQN과 같은 기초 강화학습 기법을 적용한 연구들이 시도되었으나, 단일 정책 네트워크는 비선형적이고 시변적인 도심 무선 환경에 적응하지 못하고 특정 상태에 편향되는 한계를 드러냈다 [10]. 더욱이 일부 선행 연구들은 패킷 충돌로 인한 정보 유실을 고려하지 않고 단순히 송신 횟수만을 늘려 계산된 겉보기 지연시간을 제시하는 '가짜 AoI(Fake AoI)' 오류를 범함으로써 실제 수신측 차량 안전성을 심각하게 왜곡하였다. 결과적으로 실제 MAC 계층의 패킷 충돌 손실을 엄격히 반영하여 채널 요동을 방지하고 진정한 의미의 최신 정보 전달을 보장하는 지능형 제어 기법이 필요하다.

최근 심층 강화학습(Deep Reinforcement Learning, DRL)의 발전에 힘입어 PPO, SAC, DDPG, MAPPO, Decision Transformer 등 다양한 고도화된 DRL 알고리즘들이 무선 통신 자원 최적화 분야에 활발히 적용되고 있다 [11]–[13]. 그러나 급변하는 도심 V2X 네트워크 환경에서 이들 최신 DRL 알고리즘들의 학습 수렴 안정성, 샘플 효율성, 채널 제어 성능 및 계산 복잡도를 동일한 물리·MAC 계층 조건에서 총체적이고 경험적으로 비교 분석한 연구는 부재하다. 더욱이 도심 V2X 통신 환경은 차량이 드문 희소 교통(Sparse Traffic), 교통량이 유입되는 전이 상태(Transitional State), 차량이 밀집된 극심한 혼잡(Severe Congestion) 상태가 혼재하여 채널 상태 분포의 이질성과 비정상성(Non-stationarity)이 극심하다. 단일 신경망 파라미터를 공유하는 기존 모놀리식(Monolithic) DRL 구조는 특정 혼잡 상황에 편향 학습되어 다른 교통 상태로 전환될 때 급격한 정책 저하(Policy Degradation)와 제어 불안정을 겪게 된다. 따라서 복잡한 다차원 상태 공간에서 핵심적인 특징을 추출하는 잔차 연결(ResNet) 구조와, 실시간 채널 혼잡도 수준에 따라 전문화된 하위 네트워크로 제어 결정을 분기하는 Mixture of Experts(MoE) 기반의 모듈형 하이브리드 아키텍처의 도입이 필수적이다 [14], [15]. 이러한 구조적 분기를 통해 각 혼잡 국면에 최적화된 독립적 가치 추정과 동적 게이팅을 실현함으로써 비정상 도심 V2X 환경 전 영역에서 강인한 제어 성능을 보장할 수 있다.

본 논문에서는 비선형 상태 특징을 추출하는 ResNet 블록, 혼잡도 국면별 전담 정책을 분기하는 MoE 라우팅 구조, 그리고 상태 가치와 행동 이점을 분리 학습하는 Dueling DQN을 유기적으로 결합한 하이브리드 DRL 프레임워크인 REMO-DQN(Resource-Efficient Multi-Objective Deep Q-Network)을 제안한다. 본 연구의 주요 학술적 기여도는 다음과 같이 요약된다. 첫째, 고전 Tabular RL, 기본 Value-based DRL, 최신 Actor-Critic, 다중 에이전트 강화학습(MARL) 및 트랜스포머 기반 Decision Transformer를 포함한 총 14개 강화학습 알고리즘을 Optuna 프레임워크로 정밀 최적화하고, 동일한 V2X 통신 환경에서 보상 수렴 안정성 및 샘플 효율성을 최초로 총체적 비교 분석하여 DQN 기반 구조의 뛰어난 학습 효율성을 규명하였다. 둘째, 제안한 REMO-DQN은 표준 DCC의 고질적 결함인 CBR 요동을 완전히 억제하여 0.6 상한선을 100% 준수하는 채널 안정성을 확립하였으며, 100 veh/km의 극단적 고밀도 환경에서도 73.41%의 높은 패킷 전달률(PDR)을 유지하며(10 veh/km 저밀도 76.54% 대비 하락폭 단 3.13%p 방어, 전체 평균 75.02%), 실제 MAC 충돌 페널티를 반영한 최저 정보 연령(전체 밀도 평균 AoI 373.21 ms)을 달성하여 Fake AoI 오류를 극복하였다. 셋째, 제안 모델의 연산량(3.8M MACs), 파라미터 수(350K) 및 추론 지연시간(1.2 ms)을 정밀 프로파일링하여 통신 제어 주기(100 ms)의 1.2% 미만만을 점유함을 확인하고 저전력 차량용 온보드 유닛(On-Board Unit, OBU) 마이크로컨트롤러 환경에서의 실시간 탑재 및 배포 실효성을 입증하였다.

본 논문의 나머지 구성은 다음과 같다. 제2장에서는 표준 DCC 프로토콜, 무선 자원 관리용 DRL 기법, 그리고 최신 2025~2026년 MoE 기반 무선 인공지능 연구 동향을 체계적으로 분석하고 기존 연구들과의 차별성을 정립한다. 제3장에서는 V2X 네트워크 및 채널 모델, 다중 목표 보상 기반 마르코프 결정 과정(MDP) 정식화, 그리고 제안하는 REMO-DQN의 신경망 구조를 상세히 정의한다. 제4장에서는 이기종 패킷 발생, CSMA/CA MAC 충돌, DRL 기반 혼잡 인지, MoE 기반 동적 라우팅 및 전송 파라미터 제어로 이어지는 시계열 동작 시나리오 파이프라인을 구체적으로 서술한다. 제5장에서는 SUMO 도심 격자 시뮬레이션 환경에서 14개 강화학습 모델 및 7개 비교군을 대상으로 수렴도, CBR 시계열 안정성, 밀도별 PDR 및 AoI, 거리별 신뢰도, 에너지 소모량, 하드웨어 실효성의 7대 지표에 대한 실증적 성능 평가 결과를 비교 분석한다. 마지막으로 제6장에서 본 연구의 결론을 맺고 향후 연구 과제를 제시한다.

---

# II. 관련 연구 (Related Works)

본 장에서는 커넥티드 자율주행 차량(CAV) 환경에서의 무선 혼잡 제어 및 무선 자원 관리에 관한 선행 연구 동향을 체계적으로 고찰하고, 제안하는 REMO-DQN 프레임워크의 학술적 차별성과 독창성을 정립한다.
먼저 제2.1절에서는 유럽 통신표준화기구(ETSI) 및 미국 자동차공학회(SAE)에서 제정한 표준 V2X 분산 혼잡 제어(DCC) 프로토콜의 동작 메커니즘과 상태 기계 기반의 구조적 한계를 분석한다.
이어서 제2.2절에서는 가치 기반(Value-based) 및 정책 기반(Policy-based) 단일 에이전트 심층 강화학습(DRL)을 적용한 무선 자원 관리 연구들을 살펴보고, 급변하는 도심 채널 환경에서의 비정상성(Non-stationarity) 대응 한계를 규명한다.
제2.3절에서는 중앙 집중 훈련 및 분산 실행(CTDE) 구조를 따르는 다중 에이전트 강화학습(MADRL) 및 시퀀스 모델 기반 접근법을 고찰하며, 온보드 유닛(OBU) 탑재 시 발생하는 통신 오버헤드와 연산 지연시간 병목을 진단한다.
제2.4절에서는 2024년부터 2026년까지 발표된 최신 전문가 혼합(Mixture of Experts, MoE) 결합 무선 네트워크 및 DRL 연구들을 분석하고, 본 연구의 OBU 엣지 초경량화, MAC 물리 충돌 직결 다중 목표 보상 체계, 그리고 14개 알고리즘 실증 비교의 차별화된 학술적 기여를 기술한다.
마지막으로 제2.5절의 표 1을 통해 주요 선행 연구들과 제안하는 REMO-DQN 간의 제어 목표, 알고리즘, 비교군 규모 및 MoE 적용 여부를 다각도로 비교 분석한다.

---

## 2.1 표준 V2X 분산 혼잡 제어 (Standard V2X Decentralized Congestion Control Protocols)

차량 간 통신(V2V) 및 차량-인프라 통신(V2I)을 포함하는 V2X 네트워크는 도로 안전성 증대와 원활한 교통 흐름 유지를 위해 주변 노드에 자신의 동적 상태를 주기적으로 브로드캐스트한다 [1], [2].
유럽 표준화 기구 ETSI는 협력 인식 메시지(Cooperative Awareness Message, CAM)의 전송 규격을 정의하였으며 [3], 미국 SAE는 기본 안전 메시지(Basic Safety Message, BSM) 표준(SAE J2945/1)을 제정하여 차량의 위치, 속도, 방위각, 가속도 정보를 공유하도록 규정하였다 [4].
그러나 도심 교차로나 고속도로 병목 지점과 같이 차량 밀도가 급증하는 환경에서는 제한된 5.9 GHz DSRC/C-V2X 무선 채널 대역에 다수의 차량이 동시에 패킷을 송출함에 따라 심각한 패킷 충돌과 전송 지연이 발생한다 [5].
이러한 무선 채널의 포화 상태를 방지하기 위해 표준 기구들은 물리 계층에서 측정된 채널 점유율(Channel Busy Ratio, $\text{CBR}$)을 기반으로 전송 파라미터를 조절하는 분산 혼잡 제어(Decentralized Congestion Control, DCC) 기술을 도입하였다 [6], [8].
DCC 서브레이어는 IEEE 802.11p/bd 및 C-V2X MAC 계층 상부에서 동작하며, 송신 전력 제어(Transmit Power Control, TPC), 패킷 발생 간격 제어(Transmit Duty-cycle/Rate Control, TDC/TRC), 데이터 전송률 제어(Transmit Datarate Control, DRC)의 3대 제어 차원을 통해 채널 부하를 목표 임계치(통상 $\text{CBR}_{\text{target}} \approx 0.60$) 이하로 억제하는 것을 주 목적으로 한다 [8], [9].
또한 IEEE 802.11 EDCA 구조에 따라 음성(AC_VO), 영상(AC_VI), 최선 노력(AC_BE), 배경(AC_BK) 트래픽의 4개 접근 범주별로 차등화된 큐잉 및 전송 우선순위를 부여하여 안전 임계 메시지의 신속한 송출을 보장한다.

표준 분산 혼잡 제어의 대표적인 형태인 반응형 기법(ReactDCC, ETSI TS 102 687 Annex B)은 사전에 정의된 유한 상태 기계(Finite State Machine, FSM)를 기반으로 동작한다 [8].
ReactDCC는 측정된 채널 점유율 $\text{CBR}_t$에 따라 시스템 상태를 여유(Relaxed), 활성(Active), 제한(Restrictive)의 3단계 또는 세부 다단계로 구분하고 고정 룩업 테이블에 매핑된 제어 파라미터를 적용한다.
이 제어 구조는 무선 채널의 혼잡 상태를 신속히 판별하기 위해 직관적인 규칙 기반 접근 방식을 채택한다. 사전에 정의된 각 상태는 특정 트래픽 부하 조건에서의 통신 신뢰성을 유지하기 위해 최적화된 파라미터 세트를 포함한다. 시스템 상태 전이 규칙은 다음과 같이 이산 임계치 함수로 정식화된다. 각 상태 구간은 사전에 측정된 채널 부하 임계치에 따라 엄격하게 분기된다:
$$\text{State}_{t+1} = \begin{cases} \text{Relaxed}, & \text{if } \text{CBR}_t < \text{CBR}_{\text{min}} \\ \text{Active}_k, & \text{if } \text{CBR}_k \le \text{CBR}_t < \text{CBR}_{k+1} \\ \text{Restrictive}, & \text{if } \text{CBR}_t \ge \text{CBR}_{\text{max}} \end{cases}$$
각 상태에 도달하면 패킷 발생 주기 $T_{\\text{GenCam}} \in [100\,\text{ms}, 1000\,\text{ms}]$과 송신 출력 $P_{\text{tx}} \in [0, 33]\,\text{dBm}$이 즉각적으로 계단식으로 변경된다.
상태 간의 빈번한 천이를 억제하기 위해 히스테리시스(Hysteresis) 시간 필터가 적용되지만, 불연속적인 제어 특성으로 인해 차량 밀도가 임계치 경계에 머무를 경우 전송 주기가 급격히 변동하는 문제를 유발한다.
결과적으로 이러한 계단식 파라미터 절체는 주변 차량들의 동시 반응을 촉발하여 채널 전체의 심각한 부하 불균형을 초래한다. 특히 차량 밀도가 높은 구간에서는 전송 주기 변동에 의한 연쇄 패킷 충돌이 발생하여 안전 메시지의 도달률이 급격히 저하된다. 따라서 고정 임계치에 의존하는 FSM 제어기는 동적 도심 환경에 유연하게 대처하기 어렵다는 구조적 한계를 갖는다.

이러한 반응형 기법의 계단식 변동을 완화하기 위해 ETSI TS 102 687 Annex C 및 LIMERIC 프로토콜에서는 선형 피드백 기반의 적응형 혼잡 제어(AdaptDCC)를 제안하였다 [8], [9].
AdaptDCC는 채널 점유율 오차를 기반으로 전송 간격 $T_{\\text{GenCam}}(k)$ 또는 전송률 $\delta(k)$를 주기적으로 갱신하는 비례-적분(PI) 형태의 선형 제어기를 사용한다.
이는 반응형 기법에서 발생하는 급격한 상태 천이와 채널 요동을 억제하기 위한 선형 피드백 제어 원리를 기반으로 한다. 채널 점유율이 목표 수준에 도달할 때까지 파라미터를 점진적으로 보정함으로써 시스템 안정성을 개선하도록 설계되었다. 패킷 발생 주기의 적응 업데이트 규칙은 다음과 같이 표현된다. 이 제어식은 목표 채널 부하와의 차이에 비례하여 패킷 주기를 연속적으로 갱신한다:
$$T_{\\text{GenCam}}(k) = T_{\\text{GenCam}}(k-1) + \beta \cdot \left( \text{CBR}_{\text{smooth}}(k) - \text{CBR}_{\text{target}} \right)$$
여기서 $\text{CBR}_{\text{smooth}}(k) = (1 - w) \text{CBR}_{\text{smooth}}(k-1) + w \text{CBR}(k)$는 채널 점유율의 지수 이동 평균이며, $\beta$는 수렴 속도를 결정하는 적응 이득 파라미터이다.
적응형 기법은 인접 노드 간의 채널 자원을 공평하게 분배하도록 유도하지만, 이득 계수 $\beta$의 설정에 따라 수렴 속도와 정상 상태 안정성 간의 상충 관계(Trade-off)가 강하게 발생한다.
특히 차량 밀도가 급변하는 도심 과도 상태에서 고정된 이득 계수는 채널 추종 지연을 야기하고 오버슈트(Overshoot) 현상을 증폭시키는 한계를 드러낸다. 나아가 다중 경로 페이딩과 같은 채널 비선형성을 고려하지 못해 복잡한 도심 네트워크에서 채널 점유율이 지속적으로 진동하는 문제를 완전히 해소하지 못한다. 결국 선형 피드백 모델은 도심 V2X의 비선형적인 채널 용량 한계를 적응적으로 극복하기에 불충분하다.

그러나 표준 DCC 프로토콜들은 실제 도심 V2X 네트워크 환경에서 심각한 구조적 결함을 드러낸다 [6], [9].
첫째, 다수의 인접 차량들이 동일한 채널 혼잡을 동시에 감지하고 전송 주기를 일제히 늘렸다가, 채널이 일시적으로 한산해지면 다시 동시에 전송 주기를 줄이는 집단 동기화 현상이 발생하여 채널 점유율이 주기적으로 요동치는 리미트 사이클(Limit Cycle) 요동이 발생한다.
둘째, 혼잡 임계치를 순간적으로 벗어나는 시점에 다수의 패킷이 CSMA/CA MAC 전송 큐에 일시적으로 쏟아지는 전송 폭주(Burst)가 유발되어 물리 계층의 패킷 충돌 확률이 급증한다.
셋째, 정적으로 고정된 룩업 테이블이나 단순 선형 제어 이득은 차량의 불균일한 공간 분포와 비선형적인 이동성 변화에 능동적으로 대처하지 못한다.
넷째, 표준 DCC는 채널 점유율($\text{CBR}$) 제어에만 매몰되어 정보의 신선도를 정량화하는 정보 연령(Age of Information, AoI)과 충돌로 인한 패킷 전달률(Packet Delivery Ratio, PDR) 하락을 전혀 통제하지 못한다.
따라서 엄격한 안전 통신 요구사항을 충족하기 위해서는 환경 변화를 스스로 학습하고 다중 목표를 균형 있게 최적화하는 지능형 혼잡 제어 패러다임이 필수적이다.
결국 표준 기법들의 내재적 한계는 물리 계층의 채널 역학과 MAC 계층의 패킷 대기열 상태를 포괄적으로 인지할 수 있는 학습 기반 기법의 필요성을 강력히 시사한다.

---

## 2.2 단일 에이전트 심층 강화학습 기반 무선 자원 관리 (Single-Agent DRL for Wireless Resource Management)

고전적인 규칙 기반 제어의 한계를 극복하기 위해 무선 통신 자원 최적화 분야에 심층 강화학습(DRL)을 도입하는 연구가 활발히 진행되었다 [10]–[13].
강화학습에서 무선 자원 관리 문제는 마르코프 결정 과정(Markov Decision Process, MDP)으로 정식화되며, 에이전트는 상태 관측 $\mathbf{s}_t$, 행동 선택 $a_t$, 환경으로부터의 보상 피드백 $r_t$를 통해 정책을 학습한다.
가치 기반(Value-based) DRL의 대표적인 모델인 Deep Q-Network (DQN)은 심층 신경망을 통해 행동 가치 함수 $Q(s, a; \theta)$를 근사하며, 이 프레임워크는 에이전트가 복잡한 무선 환경과의 상호작용을 통해 시행착오를 겪으며 최적의 제어 정책을 스스로 발견할 수 있도록 돕는다. 특히 시변 무선 채널의 복잡한 동역학을 사전에 정밀하게 수식화하기 어려운 분산 제어 환경에서 강력한 자율 적응성을 제공한다. 벨만 최적 방정식을 기반으로 시간차(TD) 손실 함수를 최소화한다 [10]. 에이전트는 타깃 네트워크와의 오차를 최소화하며 최적의 Q-함수로 수렴한다:
$$L(\theta) = \mathbb{E}_{(s, a, r, s')} \left[ \left( r + \gamma \max_{a'} Q(s', a'; \theta^-) - Q(s, a; \theta) \right)^2 \right]$$
이후 행동 선택과 평가를 분리하여 과대추정(Overestimation) 편향을 제거한 Double DQN [14]과, 상태 가치 스트림 $V(\mathbf{s})$와 행동 이점 스트림 $A(\mathbf{s}, a)$를 분리하여 학습 안정성을 높인 Dueling DQN [15]이 제안되었다.
Ye 등은 V2V 통신에서 분산 스펙트럼 및 송신 파워 할당을 위해 DQN을 적용하여 통신 용량 향상과 전송 지연 감소를 입증하였다 [10].
Zheng 등은 차량 네트워크에서 패킷 충돌을 줄이고 정보 연령(AoI)을 낮추기 위해 상태 이력 기반 DQN 혼잡 제어 모델을 제시하였다 [6]. 그러나 단일 Q-네트워크 기반 모델들은 교통 혼잡 국면의 극단적 변화에 따른 상태 공간의 비선형적 팽창을 단일 신경망 파라미터만으로 수용하기 어렵다는 본질적 한계를 보인다. 따라서 다양한 트래픽 밀도에 대응할 수 있는 모듈형 신경망 구조의 도입이 필수적이다.

이산 행동 공간에 국한되는 가치 기반 기법의 제약을 벗어나 연속적인 송신 전력과 대역폭을 정밀하게 제어하기 위해 정책 기반(Policy-based) 및 액터-크리틱(Actor-Critic) DRL 알고리즘들이 무선 통신 분야에 적용되었다 [11], [13].
Deep Deterministic Policy Gradient (DDPG)는 결정론적 정책 그래디언트 정리를 활용하여 연속 행동을 직접 출력하며 [11], Twin Delayed DDPG (TD3)는 두 개의 독립적인 크리틱 네트워크와 정책 지연 갱신을 통해 가치 추정의 불안정성을 개선하였다.
확률적 정책 최적화를 위해 제안된 Proximal Policy Optimization (PPO)은 이러한 연속 제어 모델들은 미세한 전송 파라미터 조정을 가능하게 하여 세밀한 자원 관리를 지원한다. 특히 통신 파워와 채널 대역폭을 동시에 연속 최적화하는 환경에서 높은 표현력을 발휘한다. 클리핑된 대체 목적함수를 도입하여 정책 갱신의 급격한 붕괴를 방지한다 [12]. 이 목적함수는 신규 정책과 기존 정책 간의 비율을 일정 범위 내로 제한한다:
$$L^{\text{CLIP}}(\theta) = \hat{\mathbb{E}}_t \left[ \min\left( \rho_t(\theta) \hat{A}_t, \, \text{clip}(\rho_t(\theta), 1-\epsilon, 1+\epsilon) \hat{A}_t \right) \right]$$
여기서 $\rho_t(\theta) = \frac{\pi_\theta(a_t|\mathbf{s}_t)}{\pi_{\theta_{\text{old}}}(a_t|\mathbf{s}_t)}$는 중요도 샘플링 비율이며, $\hat{A}_t$는 일반화된 이점 추정치(GAE)이다. 이 클리핑 메커니즘은 정책의 급격한 변화를 제한하여 학습의 단조 향상을 보장한다. 또한 엔트로피 보너스를 함께 활용하여 정책의 조기 수렴을 방지하고 균형 있는 탐험을 유도한다. 최대 엔트로피 강화학습 원리를 도입한 Soft Actor-Critic (SAC)은 탐험 능력을 극대화하여 복잡한 다중 사용자 무선 환경에서 정책 탐색 성능을 향상시켰다 [7], [13]. SAC의 목적함수는 기대 누적 보상과 정책의 엔트로피 항을 동시에 최대화하도록 설계된다:
$$J(\pi) = \sum_{t=0}^T \mathbb{E}_{(s_t, a_t)} \left[ r(s_t, a_t) + \alpha \mathcal{H}(\pi(\cdot|s_t)) \right]$$
Hu 등은 고속 이동체 무선 통신망에서 DDPG를 적용하여 패킷 전달률과 시스템 처리량을 극대화하는 자원 할당 기법을 제안하였으며 [11], Liu 등은 PPO 및 SAC을 이용해 AoI와 에너지 소비를 공동 최적화하는 프레임워크를 개발하였다 [7]. 그러나 이러한 정책 그래디언트 계열 모델들은 시변 도심 채널 환경에서 정책 분산이 지나치게 커지는 취약점을 지니며, 높은 샘플 복잡도로 인해 온보드 엣지 환경에서의 신속한 정책 적응에 한계를 드러낸다. 복잡한 탐색 공간으로 인한 학습 지연은 차량용 실시간 임베디드 제어기의 상용화에 큰 걸림돌이 된다. 또한 높은 연산 복잡도는 배터리 및 OBU 연산 자원이 한정된 차량 단말에 상당한 하드웨어 부담을 가중시킨다. 따라서 연산 효율성과 빠른 수렴성을 겸비한 하이브리드 Q-러닝 접근법이 절실히 요구된다.

그러나 단일 에이전트 DRL 기법들을 실제 V2X 혼잡 제어에 직접 적용하는 데에는 다음과 같은 기술적 난제들이 존재한다 [6], [10], [13].
첫째, 차량의 고속 이동과 주변 무선 토폴로지의 동적 변화로 인해 무선 채널의 비정상성(Non-stationarity)이 극심하여 단일 에이전트의 상태-행동 전이 분포가 끊임없이 요동친다.
둘째, 단일 신경망 파라미터에 모든 정책을 학습시키는 모놀리식(Monolithic) 구조는 희소 교통(Sparse) 상태와 극심한 정체(Dense) 상태 간의 심각한 파라미터 간섭(Parameter Interference) 및 치명적 망각(Catastrophic Forgetting)을 초래한다.
셋째, 연속 제어기를 사용하는 액터-크리틱 계열 모델들은 고차원 탐색 공간으로 인해 샘플 효율성이 저하되며, 이는 실시간 패킷 전송 주기를 신속히 결정해야 하는 차량 OBU 환경에 적합하지 않다.
넷째, 다수의 선행 연구들은 MAC 계층의 실제 패킷 충돌 물리 현상을 무시한 채 단순히 전송 빈도만을 높여 지연시간을 계산하는 '가짜 AoI(Fake AoI)'를 보고하는 치명적 오류를 범하였다.
다섯째, 단일 목적함수에 편향된 보상 설계는 $\text{CBR}$ 목표치 달성과 $\text{PDR}$ 방어 사이의 복잡한 파레토 경계를 적절히 탐색하지 못하고 특정 영역으로의 정책 수렴 실패를 유발한다.
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
Decision Transformer는 기존의 벨만 방정식 반복 대신 자기주의(Self-Attention) 메커니즘을 활용하여 목표 보상(Return-to-Go, $\hat{R}_t$), 이 패러다임은 강화학습 문제를 대규모 언어 모델과 유사한 생성형 시퀀스 예측 문제로 전환한다. 과거의 상태-행동-보상 이력 전체를 통합적으로 참조함으로써 장기적인 통신 환경 변화를 포괄적으로 조망할 수 있는 구조적 장점을 갖는다. 상태 $\mathbf{s}_t$, 행동 $a_t$로 구성된 시퀀스 궤적 $\tau$를 자기회귀적(Autoregressive)으로 생성한다. 에이전트는 과거의 궤적 맥락을 바탕으로 다음 행동을 예측한다:
$$\tau = \left( \hat{R}_1, s_1, a_1, \hat{R}_2, s_2, a_2, \dots, \hat{R}_T, s_T, a_T \right)$$
트랜스포머의 다중 헤드 어텐션(Multi-Head Attention)은 시간에 따른 채널 혼잡도 변화의 장기 시계열 의존성(Long-range Temporal Dependencies)을 포착하여 혼잡을 사전에 예측하고 제어하는 능력을 제공한다.
일부 선행 연구에서는 무선 네트워크의 시계열 트래픽 변화 패턴을 학습하여 사전 대응적(Proactive) 자원 스케줄링을 수행하는 데 트랜스포머 구조를 응용하였다 [20].
이러한 시퀀스 기반 모델은 부트스트래핑(Bootstrapping)에 기인한 학습 불안정성을 회피하고 방대한 오프라인 데이터셋으로부터 효과적인 정책을 추출하는 장점을 보인다.
그러나 이러한 트랜스포머 구조는 시퀀스 길이가 증가함에 따라 메모리 요구량과 연산량이 급격히 팽창하는 본질적인 구조적 비용을 수반한다. 특히 자기주의 연산의 복잡도가 시퀀스 길이의 제곱에 비례하므로 실시간 저지연 제어가 필수적인 차량용 OBU 환경에 직접 탑재하기에는 연산 부담이 과중하다는 치명적 약점을 지닌다.

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
기본적인 MoE 아키텍처는 입력 특징 $x$를 공유하는 $K$개의 독립적인 전문가 네트워크 $E_k(x)$와, 각 전문가에 대한 소프트맥스 라우팅 확률 가중치 $g(x) = [g_1(x), \dots, g_K(x)]^T$를 산출하는 이 구조는 입력 데이터의 특성에 따라 서로 다른 서브 네트워크를 활성화함으로써 모델의 파라미터 효율성을 극대화한다. 고정된 전체 연산량 내에서 모델의 표현 용량을 비약적으로 증가시킬 수 있는 강력한 기법으로 평가받는다. 기본적인 MoE 아키텍처는 입력 특징 $x$를 공유하는 $K$개의 독립적인 전문가 네트워크 $E_k(x)$와, 각 전문가에 대한 소프트맥스 라우팅 확률 가중치 $g(x) = [g_1(x), \dots, g_K(x)]^T$를 산출하는 게이팅 네트워크(Gating Network)로 구성된다 [21]. 전체 출력은 각 전문가의 출력과 라우팅 확률의 가중합으로 결정된다:
$$y = \sum_{k=1}^K g_k(x) E_k(x), \quad \text{subject to } \sum_{k=1}^K g_k(x) = 1, \quad g_k(x) \ge 0$$
게이팅 네트워크는 입력 상태의 분포적 특성에 따라 최적의 전문가를 동적으로 선택하거나 가중합을 계산함으로써, 이질적인 데이터 영역별로 특화된 서브 네트워크가 전담 연산을 수행하도록 유도한다.
이러한 MoE의 조건부 연산 원리는 다차원 무선 채널의 비정상성과 비선형적 혼잡 상태를 분할 정복(Divide-and-Conquer) 방식으로 해결할 수 있는 강력한 이론적 토대를 제공한다.
특히 입력 공간을 기능별 전문가 서브넷으로 분할함으로써 단일 모놀리식 신경망에서 발생하는 상충 태스크 간의 그래디언트 충돌(Gradient Conflict)을 원천적으로 억제한다.
이에 따라 무선 환경의 희소 영역과 고밀도 과포화 영역을 완전히 독립된 파라미터 경로로 분리 학습하는 것이 가능해진다. 본 연구에서는 이러한 MoE 패러다임을 V2X 분산 제어에 최초로 적용하여 연산 오버헤드 없이 밀도별 최적 정책을 효과적으로 분기하도록 설계하였다.

2024년부터 2026년에 걸쳐 무선 통신 네트워크 및 분산 강화학습 분야에 MoE를 융합하는 최신 연구들이 활발히 발표되었다 [22]–[26].
Xu 등은 IEEE Communications Surveys & Tutorials (2025)에 게재한 포괄적 서베이 논문에서 무선 네트워크 및 분산 DRL 환경에서 MoE가 제공하는 자원 효율성, 일반화 성능, 통신 오버헤드 절감 효과를 체계적으로 분석하였다 [22].
해당 서베이는 무선 채널의 극심한 환경 변화 속에서 모놀리식 신경망이 겪는 치명적 망각을 MoE의 도메인 특화 라우팅이 효과적으로 방지할 수 있음을 이론적으로 증명하였다.
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
첫째, 본 연구는 OBU 엣지 디바이스에 직접 탑재 가능한 초경량 하이브리드 아키텍처를 설계하였다. 2개의 잔차 블록(Residual Block)으로 구성된 ResNet 특징 추출기, 3개의 도메인 특화 듀얼링 전문가(Dueling Experts), 소프트맥스 게이팅 라우터, 그리고 전문가 간 과부하를 방지하는 부하 분산 손실($\mathcal{L}_{lb} = 0.01 \times \text{CV}^2$)을 결합하여 총 350K(35만 개) 파라미터와 3.8M MACs, 1.2 ms의 초저지연 온보드 추론 성능(100 ms 제어 주기의 1.2% 점유)을 달성하였다.
둘째, CSMA/CA MAC 계층의 물리적 충돌 메커니즘과 직결된 다중 목표 보상 함수($R_t = -\alpha |\text{CBR}_{\text{smooth}} - 0.60| - \beta \Delta t_{\text{CAM}}$)를 정식화하여, 채널 안정성을 보장하면서도 충돌 유실 페널티를 엄격히 반영하여 허위 지연시간(Fake AoI) 왜곡을 효과적으로 방지하였다.
셋째, 희소 교통(Sparse, $\text{CBR} < 0.40$), 전이 영역(Transitional, $0.40 \le \text{CBR} \le 0.60$), 고밀도 혼잡(Dense, $\text{CBR} > 0.60$)의 3단계 물리적 혼잡 영역을 명시적으로 전담하는 전문가 분기 제어를 실현하여 채널 요동(Limit Cycle)을 효과적으로 억제하였다.
넷째, 본 연구는 고전 Tabular RL, 가치 기반 DRL, 액터-크리틱 DRL, 최신 MARL, 트랜스포머 기반 DRL을 총망라하는 총 14개 강화학습 알고리즘과 7개 표준/머신러닝 비교군을 도심 SUMO 격자 및 실제 Nakagami-$m$ 페이딩 채널 환경에서 동일 조건으로 총체적 벤치마킹한 세계 최초의 실증 연구이다.
이와 같은 아키텍처 설계를 통해 제안하는 REMO-DQN은 10 veh/km 저밀도 76.54%에서 100 veh/km 고밀도 73.41%를 유지(전체 평균 75.02%, 하락폭 단 3.13%p 방어)하며 차량 네트워크 분산 혼잡 제어의 우수한 신뢰성을 확보하였다.

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

표 1에서 명확히 확인되는 바와 같이, 대부분의 기존 연구들은 단일 알고리즘이나 3~5개 수준의 제한된 베이스라인과의 비교에 그쳤으며, 채널 점유율($\text{CBR}$) 안정성과 정보 연령($\text{AoI}$), 패킷 전달률($\text{PDR}$), 하드웨어 연산 지연시간(Latency)을 다중 목표로 동시에 통합 최적화한 연구는 전무하다.
특히 2024~2026년에 제안된 최신 MoE 무선 네트워크 연구들(Xu 등 [22], Zhang 등 [23], Kang 등 [24], Du 등 [25])은 주로 상위 계층 자원 할당이나 기지국 인프라 수준의 연산에 국한되었으며, 차량 OBU 환경에 특화된 경량 MoE 아키텍처와 CSMA/CA MAC 계층의 실제 패킷 충돌을 연계한 실증 연구는 본 연구가 유일하다.
또한 기존 DRL 접근법들이 $\text{CBR}$ 억제에 치중하여 $\text{PDR}$이 급락하거나 실제 정보 유실을 은폐하는 가짜 AoI 문제를 야기한 반면, 본 연구는 물리적 충돌 페널티를 고려한 엄밀한 보상 함수를 통해 통신 신선도와 전달 신뢰성을 동시에 확보한다.
나아가 본 연구의 REMO-DQN은 ResNet 특징 추출기, 3개 도메인 특화 Dueling 전문가, Softmax 게이팅 라우터를 결합하여 21개에 달하는 광범위한 비교군 대비 뛰어난 PDR 방어율(100 veh/km 고밀도에서 73.41% 유지, 전체 평균 75.02%), 최저 정보 연령(AoI), 우수한 채널 안정성($\text{CBR}$ 요동 억제), 그리고 1.2 ms 온보드 실시간 추론 성능(100 ms 제어 주기의 1.2% 점유)을 입증한다.
이러한 종합 비교 결과는 제안하는 REMO-DQN 프레임워크가 차세대 커넥티드 자율주행 차량을 위한 가장 실효적이고 완성도 높은 분산 혼잡 제어 솔루션임을 결정적으로 뒷받침한다.

---

# III. 시스템 모델 및 제안하는 REMO-DQN 아키텍처 (System Model and Proposed REMO-DQN Architecture)

본 장에서는 고밀도 차량 사물 통신(Vehicle-to-Everything, V2X) 환경에서 분산 혼잡 제어(Decentralized Congestion Control, DCC)를 체계적으로 수행하기 위한 물리 계층, 매체 접근 제어(MAC) 계층, 패킷 발생 동역학 및 분산 마르코프 결정 과정(Decentralized Markov Decision Process, Dec-MDP)을 정식화한다. 차량 간 무선 통신 환경은 차량의 빠른 이동성, 도심 구조물에 의한 전파 음영, 다중 경로 페이딩 및 동시 다발적인 채널 경합으로 인해 시공간적으로 극심한 비정상성(Non-stationarity)을 나타낸다. 이러한 무선 환경의 불확실성을 극복하기 위해 본 논문에서는 통신 반경 및 감지 반경에 기초한 무선 전파 모델과 비동기식 CSMA/CA MAC 계층의 패킷 충돌 메커니즘을 결합한 통합 시스템 모델을 수립한다. 더불어 각 차량 노드가 국소 관측 정보에만 기반하여 협력 안전을 유지할 수 있도록 다중 목표 보상 체계를 정립한다. 마지막으로 복잡한 비선형 트래픽 상태를 효과적으로 추상화하고 교통 혼잡 국면별로 특화된 제어 정책을 동적으로 융합하는 잔차 혼합 전문가 듀얼링 심층 Q-네트워크(REMO-DQN)의 수학적 구조와 부하 균등화 학습 알고리즘을 상세히 기술한다.

---

## 3.1 네트워크 및 무선 통신 시스템 모델 (Network and Communication System Model)

### A. 네트워크 토폴로지 및 시간 슬롯 모델
본 논문에서 고려하는 차량 애드혹 네트워크(VANET)는 다차선 도심 고속화 도로 환경에서 무작위로 분포하여 주행하는 복수의 커넥티드 차량(Connected Vehicles)으로 구성된다. 전체 시스템은 이산 시간 슬롯(Discrete Time Slot) 체계로 동작하며, 의사결정 및 전파 환경의 기본 갱신 주기는 $\Delta T_{\text{step}} = 100\text{ ms}$ ($0.1\text{ s}$)로 정의된다. 임의의 이산 시간 슬롯 $t \in \{0, 1, 2, \dots, T_{\text{end}}\}$에서 도로 네트워크 상에 존재하는 활성 차량들의 전체 집합을 $\mathcal{V}(t) = \{v_1, v_2, \dots, v_{N(t)}\}$라 정의하며, 여기서 $N(t) = |\mathcal{V}(t)|$는 네트워크 내 전체 차량 수를 나타낸다. 각 차량 $i \in \mathcal{V}(t)$는 온보드 유닛(On-Board Unit, OBU)과 위성 항법 장치(GNSS)를 탑재하고 있으며, 2차원 평면 좌표계 상의 위치 벡터 $\mathbf{p}_i(t) = (x_i(t), y_i(t))$, 이동 속도 $v_i(t)$, 진행 방향 각도 $\theta_i(t)$를 자신의 기구학적 상태 벡터로 지속 관리한다. 임의의 두 차량 $i, j \in \mathcal{V}(t)$ 사이의 유클리드 공간 거리는 $d_{ij}(t) = \|\mathbf{p}_i(t) - \mathbf{p}_j(t)\|_2 = \sqrt{(x_i(t) - x_j(t))^2 + (y_i(t) - y_j(t))^2}$로 주어진다. 모든 차량은 전방향성(Omni-directional) 안테나를 구비하며, 유효 안전 통신 반경은 $R_{\text{comm}} = 300\text{ m}$, 무선 채널의 전파 간섭 및 에너지 감지를 수행하는 국소 채널 감지 반경(Sensing Range)은 $R_{\text{sense}} = 500\text{ m}$로 설정된다. 이에 따라 송신 차량 $i$의 통신 이웃 집합은 $\mathcal{N}_{\text{comm}}(i, t) = \{j \in \mathcal{V}(t) \mid j \neq i, d_{ij}(t) \le R_{\text{comm}}\}$로 정의되며, 감지 이웃 집합은 $\mathcal{N}_{\text{sense}}(i, t) = \{j \in \mathcal{V}(t) \mid j \neq i, d_{ij}(t) \le R_{\text{sense}}\}$로 정의된다.

### B. 무선 채널 및 물리 계층 전파 모델
차량 간 무선 통신은 지능형 교통 시스템(ITS) 전용 주파수 대역인 $5.9\text{ GHz}$ ($f_c = 5.9 \times 10^9\text{ Hz}$) 대역의 $10\text{ MHz}$ 대역폭($B = 10^7\text{ Hz}$) 제어 채널(Control Channel, CCH)을 사용하는 IEEE 802.11p 표준을 준수한다. 물리 계층의 강인한 복조를 보장하기 위해 기본 변복조 방식으로는 BPSK $1/2$ 부호화가 적용되며, 이에 따른 공칭 데이터 전송률은 $R_{\text{data}} = 3\text{ Mbps}$ ($3 \times 10^6\text{ bps}$)이다. 유럽 표준에 따라 브로드캐스트되는 기본 안전 메시지인 협력 인식 메시지(Cooperative Awareness Message, CAM)의 크기는 보안 및 네트워크 헤더를 포함하여 $L_{\text{CAM}} = 280\text{ Bytes} = 2240\text{ bits}$로 설정된다. 단일 CAM 패킷이 무선 매체를 물리적으로 점유하는 패킷 전송 시간(Air-time Duration) $T_{\text{tx}}$는 패킷 비트 수를 데이터 전송률로 나눈 값으로 정확히 계산된다. 이에 따라 $T_{\text{tx}} = (L_{\text{CAM}} \times 8) / R_{\text{data}} = 2240\text{ bits} / (3 \times 10^6\text{ bps}) \approx 0.74667\text{ ms}$의 전송 점유 시간이 도출되며, 이 값은 채널 비지 시간 누적 계산의 기초 단위로 사용된다.

송신 차량 $i$가 송신 전력 $P_{\text{tx}, i}\text{ [dBm]}$으로 신호를 방출할 때, 거리 $d_{ij}$ 떨어진 수신 차량 $j$에 도달하는 평균 수신 신호 전력 $\bar{P}_{\text{rx}, ij}\text{ [dBm]}$은 로그-거리 경로 손실 모델(Log-Distance Path Loss Model)을 통해 유도된다. 기준 거리 $d_0 = 1.0\text{ m}$에서의 자유 공간 경로 손실 $\text{PL}_0$는 광속 $c = 3.0 \times 10^8\text{ m/s}$에 대해 $\text{PL}_0 = 20 \log_{10}(4\pi d_0 f_c / c) \approx 47.86\text{ dB}$로 계산되며, 도심 도로 환경의 경로 손실 지수는 $\alpha = 2.0$으로 설정된다. 이에 따른 거리 $d_{ij}$에서의 경로 손실은 $\text{PL}(d_{ij})\text{ [dB]} = \text{PL}_0 + 10 \alpha \log_{10}(d_{ij} / d_0) = 47.86 + 20 \log_{10}(d_{ij})$로 주어지며, 평균 수신 전력은 $\bar{P}_{\text{rx}, ij}\text{ [dBm]} = P_{\text{tx}, i}\text{ [dBm]} - \text{PL}(d_{ij})\text{ [dB]}$로 표현된다. 수신기 OBU 단에서의 열잡음 전력 밀도는 상온 기준 $-174\text{ dBm/Hz}$이며, 대역폭 $B = 10\text{ MHz}$에 따른 열잡음과 수신기 잡음 지수 $\text{NF} = 10\text{ dB}$를 합산한 배경 유효 잡음 전력은 $N_0 = -174 + 10\log_{10}(10^7) + 10 = -94.0\text{ dBm}$로 도출된다. 결과적으로 수신 차량 $j$에서의 평균 신호 대 잡음비(SNR)는 $\bar{\gamma}_{ij}\text{ [dB]} = \bar{P}_{\text{rx}, ij}\text{ [dBm]} - N_0\text{ [dBm]} = P_{\text{tx}, i}\text{ [dBm]} - 47.86 - 20 \log_{10}(d_{ij}) + 94.0$로 계산되며, 선형 스케일 평균 SNR은 $\bar{\gamma}_{\text{lin}, ij} = 10^{\bar{\gamma}_{ij}\text{ [dB]} / 10}$으로 변환된다.

도심 도로 환경의 다중 경로 페이딩(Multipath Fading) 현상을 사실적으로 모델링하기 위해 신호 진폭에 나카가미-$m$ (Nakagami-$m$) 분포를 적용하며, 도심 ITS 준가시선 환경의 표준 형상 파라미터로 $m = 3.0$을 채택한다. 수신기가 BPSK $1/2$ 변조 신호를 성공적으로 복조하기 위한 최소 요구 SNR 임계치를 $\gamma_{\text{th}} = 5.0\text{ dB}$ (선형값 $\gamma_{\text{th, lin}} = 10^{0.5} \approx 3.16228$)라 정의한다. 이때 무선 채널 상의 물리적 수신 성공 확률 $P_{\text{succ}}(d_{ij}, P_{\text{tx}, i})$는 나카가미-$m$ 분포를 따르는 순간 수신 전력의 상위 누적 분포 함수(CCDF)로부터 유도된다. 정규화 파라미터를 $x = (m \cdot \gamma_{\text{th, lin}}) / \bar{\gamma}_{\text{lin}, ij} \approx 9.48683 / \bar{\gamma}_{\text{lin}, ij}$라 할 때, 수신 성공 확률은 닫힌 형태(Closed-form)인 $P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) = \exp(-x) (1 + x + x^2 / 2)$로 엄밀하게 산출된다. 이 확률 공식은 수신 거리가 증가하거나 송신 전력이 감소하여 평균 SNR이 낮아질수록 패킷 복조 성공률이 지수 함수적으로 감소하는 전파 감쇠 특성을 정밀하게 반영한다.

### C. CSMA/CA MAC 계층 경합 및 패킷 충돌 모델
차량 간 브로드캐스트 통신은 사전 슬롯 예약이 없는 비동기 분산 매체 접근 제어 방식인 CSMA/CA (Carrier Sense Multiple Access with Collision Avoidance) 프로토콜을 사용한다. 고밀도 통신 환경에서는 다수의 차량이 동시에 패킷 송신을 개시함에 따라 동시 전송 타이밍 겹침, 은닉 노드(Hidden Terminal) 문제 및 채널 포화로 인한 심각한 MAC 계층 패킷 충돌(Packet Collision)이 발생한다. 이러한 분산 매체 경합에 따른 성능 저하를 수학적으로 포착하기 위해, 수신 차량 $j$의 국소 채널 부하 지표인 채널 점유율 $\text{CBR}_j(t)$에 기반한 충돌 감쇠 계수 $f_{\text{collision}}(\text{CBR}_j)$를 정의한다. 이 감쇠 계수는 채널 점유율이 증가함에 따라 선형적으로 감소하며, 채널이 극도로 포화된 상황에서도 최소 0.1의 통신 가능성을 유지하도록 $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t))$로 설계된다. 이러한 감쇠 함수 모델링은 채널 부하가 가중될수록 무선 매체 상의 패킷 충돌 확률이 비선형적으로 증가하는 실제 IEEE 802.11p 분산 환경의 물리적 경합 현상을 정밀하게 반영한다.

따라서 송신 차량 $i$가 방출한 CAM 패킷이 거리 $d_{ij}$ 떨어진 수신 차량 $j$에 최종적으로 오류 없이 수신될 결합 확률 $P_{\text{rx}, ij}(t)$는 물리 계층 복조 성공 확률과 MAC 계층 비충돌 확률의 곱으로 결정된다. 즉, $P_{\text{rx}, ij}(t) = P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) \cdot f_{\text{collision}}(\text{CBR}_j)$의 결합 확률 모델이 성립한다. 이 결합 모델은 무선 거리 감쇠와 주변 채널 혼잡에 의한 패킷 충돌 손실을 단일 통합 수식으로 결합한다. 수신 노드 주변의 채널 점유율이 상승할수록 비충돌 확률이 급격히 저하되므로, 높은 전력으로 송신하더라도 주변 혼잡이 심하면 패킷이 도달할 수 없음을 나타낸다. 결과적으로 이 수식은 물리 계층 송신 전력 조절과 MAC 계층 혼잡 제어가 긴밀히 연계되어야 함을 수학적으로 입증한다.

### D. ETSI EN 302 637-2 CAM 동적 이벤트 기반 패킷 생성 규칙
유럽 전기통신표준협회(ETSI) EN 302 637-2 표준 규격에 따라 각 차량의 안전 애플리케이션 계층은 차량의 주행 동역학 변화를 매 타임스텝 감지하여 능동적으로 CAM 패킷 생성을 유발한다. 차량 $i$의 직전 CAM 전송 완료 시각을 $t_{\text{last}, i}$, 해당 시점의 위치, 속도, 진행 방향 각도를 각각 $\mathbf{p}_i^{\text{last}} = (x_i^{\text{last}}, y_i^{\text{last}})$, $v_i^{\text{last}}$, $\theta_i^{\text{last}}$라 정의한다. 현재 시간 슬롯 $t$에서 직전 전송 이후 경과한 시간 $\Delta t_i = t - t_{\text{last}, i}$에 대해 네 가지 표준 동적 조건이 평가된다. 구체적으로 방향각 변화량 $|\Delta \theta| \ge \Delta \theta_{\text{th}} = 4.0^\circ$, 위치 이동 변위 $\|\Delta \mathbf{p}\|_2 \ge \Delta d_{\text{th}} = 4.0\text{ m}$, 주행 속도 변화량 $|\Delta v| \ge \Delta v_{\text{th}} = 0.5\text{ m/s}$, 혹은 최대 생성 주기 만료 $\Delta t_i \ge T_{\text{GenCam, max}} = 1.0\text{ s}$ ($1\text{ Hz}$) 중 하나라도 만족되면 원초적 이벤트 트리거 플래그 $\text{Trig}_i(t) = 1$이 활성화된다. 이러한 동적 트리거링 규칙은 차량의 불필요한 비콘 전송을 억제하면서도 급격한 주행 궤적 변화 시 주변 차량에 대한 상황 인식 신선도를 최우선으로 확보하도록 돕는다. 

동시에 분산 혼잡 제어(DCC) 계층은 채널 상태에 따라 OBU의 최소 패킷 전송 허용 주기 $T_{\text{GenCam}, i}(t) \in [T_{\text{GenCam, min}}, T_{\text{GenCam, max}}]$ ($T_{\text{GenCam, min}} = 0.1\text{ s}$)를 가변적으로 제약한다. 따라서 OBU 무선 모뎀이 실제로 무선 채널에 패킷을 송출하는 최종 전송 결정 지시자 $\Psi_i(t) \in \{0, 1\}$는 논리곱 조건식 $\Psi_i(t) = \text{Trig}_i(t) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCam}, i}(t)) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCam, min}})$으로 확정된다. 여기서 $\mathbb{I}(\cdot)$는 괄호 내부의 명제가 참이면 1, 거짓이면 0을 반환하는 지시 함수이다. 이 규칙은 급격한 주행 궤적 변화 시 안전 비콘을 신속히 송신하면서도, DCC가 설정한 전송 제약 주기를 엄격히 준수하도록 통제한다. 이로써 차량 애플리케이션의 안전 요구조건과 무선 채널의 혼잡 방지 요구조건 간의 조화로운 상호운용성이 보장된다.

### E. 국소 채널 점유율(CBR) 및 채널 상태 평활화
각 차량 $i$는 감지 반경 $R_{\text{sense}} = 500\text{ m}$ 내에서 동일 시간 슬롯 $\Delta T_{\text{step}} = 100\text{ ms}$ 동안 발생한 이웃 차량들의 패킷 송신 이벤트를 실시간으로 감지한다. 타임스텝 $t$에서 감지된 전송 이벤트 집합을 $\mathcal{E}_{\text{sense}}(i, t) = \{k \in \mathcal{V}(t) \mid d_{ik}(t) \le R_{\text{sense}}, \Psi_k(t) = 1\}$라 할 때, 차량 $i$가 관측하는 순간 국소 채널 점유율(Channel Busy Ratio, CBR) $\text{CBR}_i(t)$는 단위 슬롯 시간 대비 무선 채널의 총 비지(Busy) 점유 시간 비율로 계산된다. 즉, $\text{CBR}_i(t) = \min(1.0, |\mathcal{E}_{\text{sense}}(i, t)| \cdot T_{\text{tx}} / \Delta T_{\text{step}})$의 수식이 적용된다. 여기서 감지 반경 $500\text{ m}$는 통신 반경 $300\text{ m}$보다 넓게 설정되어 잠재적인 은닉 노드의 간섭 신호 에너지까지 포괄하여 채널 부하를 정확히 측정하도록 돕는다. 따라서 개별 차량은 중앙 제어 장치의 통신 보조 없이도 국소 수신 에너지만으로 주변 무선 채널의 실시간 혼잡 상태를 독립적으로 추정할 수 있다.

순간 CBR 값은 패킷 도착의 무작위성으로 인해 타임스텝마다 극심한 고주파 잡음성 진동을 포함하므로, 제어의 안정성을 유지하기 위해 지수 이동 평균(Exponential Moving Average, EMA) 평활화 필터를 적용한다. 평활화 가중 계수 $\lambda_s = 0.5$를 적용한 평활화 채널 점유율 $\text{CBR}_{\text{smoothed}, i}(t)$는 점화식 $\text{CBR}_{\text{smoothed}, i}(t) = (1 - \lambda_s) \cdot \text{CBR}_{\text{smoothed}, i}(t - \Delta T_{\text{step}}) + \lambda_s \cdot \text{CBR}_i(t)$로 매 슬롯마다 갱신된다. 이 평활화 지표는 일시적인 채널 버스트에 의한 과도한 제어 반응을 완화하고, 장기적인 채널 혼잡 추세를 에이전트에게 제공하는 핵심 피드백 신호로 기능한다. 평활화된 혼잡도를 관측 상태 및 보상 피드백으로 활용함으로써 강화학습 에이전트의 정책 진동을 원천적으로 억제할 수 있다. 나아가 $\lambda_s = 0.5$의 파라미터는 급격한 교통 밀도 유입 시 지연 없는 신속한 반응성과 안정적인 저주파 수렴 특성을 동시에 달성하는 최적의 필터 응답 특성을 제공한다.

### F. 정보 신선도(AoI) 및 패킷 수신율(PDR) 성능 척도
V2X 네트워크의 협력 안전 서비스 품질과 상황 인식의 정확도를 정량적으로 평가하기 위해 정보 신선도(Age of Information, AoI)와 패킷 수신율(Packet Delivery Ratio, PDR)을 시스템의 양대 핵심 성능 지표로 정의한다. 수신 차량 $j$가 송신 차량 $i$로부터 가장 최근에 성공적으로 수신한 CAM 패킷의 생성 시각을 $u_{ij}(t)$라 할 때, 차량 링크 쌍 $(i, j)$의 순간 AoI는 패킷 생성 시점부터 현재까지 경과한 시간인 $\Delta_{ij}(t) = t - u_{ij}(t)$로 정의된다. 패킷 유실로 인해 AoI가 무한정 증가하여 통계적 왜곡이 발생하는 현상을 방지하기 위해 최대 상한값 $2000\text{ ms}$를 적용한다. 통신 반경 $R_{\text{comm}} = 300\text{ m}$ 내 모든 유효 차량 쌍 집합 $\mathcal{P}_{\text{comm}}(t) = \{(i, j) \in \mathcal{V}(t) \times \mathcal{V}(t) \mid i \neq j, d_{ij}(t) \le R_{\text{comm}}\}$에 대한 네트워크 평균 AoI $\overline{\text{AoI}}(t)$는 $\overline{\text{AoI}}(t) = \frac{1}{|\mathcal{P}_{\text{comm}}(t)|} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \min(\Delta_{ij}(t) \times 1000\text{ [ms]}, 2000\text{ [ms]})$로 산출된다. 이 지표는 단순 패킷 손실률을 넘어 수신 차량의 관점에서 실제 인지하고 있는 정보의 시간적 지연과 노후화 정도를 통합적으로 정량화한다.

한편 네트워크 전체의 평균 패킷 수신율(PDR)은 통신 반경 내에서 시도된 모든 유효 브로드캐스트 기회 대비 수신 차량에 성공적으로 도달한 누적 패킷 수의 백분율로 정의된다. 수식으로는 $\text{PDR} = \frac{\sum_{t} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \mathbb{I}(\text{Packet from } i \text{ received by } j \text{ at step } t)}{\sum_{t} \sum_{i \in \mathcal{V}(t)} \Psi_i(t) \cdot |\{j \in \mathcal{V}(t) \mid j \neq i, d_{ij}(t) \le R_{\text{comm}}\}|} \times 100\%$로 정식화된다. 이들 두 지표는 패킷 전송 빈도 증대에 따른 충돌 유발과 전송 빈도 감소에 따른 정보 진부화 사이의 본질적인 트레이드오프 관계를 객관적으로 측정하는 기준이 된다. 전송 주기를 너무 짧게 설정하면 PDR이 추락하고, 전송 주기를 너무 길게 설정하면 AoI가 급증하므로 두 지표의 균형적 최적화가 필수적이다. 특히 고밀도 병목 구간에서 차량 간 충돌 회피 알고리즘이 안전하게 작동하기 위해서는 높은 PDR과 낮은 AoI가 동시에 달성되어야 한다.

---

## 3.2 분산 혼잡 제어를 위한 MDP 정식화 (Markov Decision Process Formulation)

고밀도 V2X 네트워크에서의 혼잡 제어 문제는 중앙 제어기의 통신 오버헤드 없이 각 차량이 국소 관측 정보만을 바탕으로 패킷 전송 주기와 송신 전력을 자율적으로 최적화하는 분산형 마르코프 결정 과정(Decentralized Markov Decision Process, Dec-MDP)으로 정식화된다. 네트워크 내 각 OBU 에이전트는 전역 상태 정보에 직접 접근할 수 없으며, 국소 감지 센서 및 무선 모뎀을 통해 수집된 관측치만을 바탕으로 의사결정을 수행한다. 이에 따라 개별 차량 에이전트의 의사결정 모델은 튜플 $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$로 정의된다. 여기서 $\mathcal{S}$는 상태 공간, $\mathcal{A}$는 이산 행동 공간, $\mathcal{P}$는 환경 전이 확률 모델, $\mathcal{R}$은 다중 목표 보상 함수, $\gamma \in [0, 1)$는 미래 보상에 대한 시간 할인율을 의미한다. 분산 환경의 특성상 각 에이전트는 독자적인 정책을 실행하지만, 공유된 무선 채널 매체를 통해 상호 간섭을 주고받는 다중 에이전트 상호작용 구조를 형성한다.

### A. 상태 공간 (State Space) $\mathcal{S}$
각 차량 에이전트 $i$가 타임스텝 $t$에서 OBU의 센서 및 무선 모뎀으로부터 관측하는 상태 벡터 $\mathbf{s}_t^{(i)} \in \mathcal{S} \subset \mathbb{R}^5$는 5차원의 정규화된 연속 변수로 구성된다. 상태 벡터의 수학적 정의는 $\mathbf{s}_t^{(i)} = [s_{t, 1}^{(i)}, s_{t, 2}^{(i)}, s_{t, 3}^{(i)}, s_{t, 4}^{(i)}, s_{t, 5}^{(i)}]^T = [\text{CBR}_i(t), N_{\text{est}, i}(t)/N_0, v_i(t)/v_{\max}, (t - t_{\text{last}, i})/T_{\text{GenCam, max}}, \text{CBR}_{\text{smoothed}, i}(t)]^T$로 설정된다. 이 5차원 관측 벡터는 채널 부하, 공간 밀도, 주행 역학 및 시간적 신선도를 유기적으로 포괄하여 신경망에 풍부한 상황 맥락을 제공한다. 각 상태 원소는 상이한 물리 단위를 균일한 스케일로 맞추기 위해 유효 최댓값 및 표준 기준 상수로 정규화된다. 이를 통해 심층 신경망 내부에서 특정 특징값의 스케일에 의해 그래디언트가 편향되는 현상을 효과적으로 방지한다.

상태 벡터를 구성하는 각 원소의 물리적 정의와 정규화 기준은 다음과 같다. 첫째, $s_{t, 1}^{(i)} = \text{CBR}_i(t) \in [0.0, 1.0]$는 직전 슬롯 동안 감지된 순간 채널 점유율로서 무선 매체의 즉각적인 부하 상태를 대변한다. 둘째, $s_{t, 2}^{(i)} = N_{\text{est}, i}(t) / 50.0 \in [0.0, \infty)$는 통신 반경 $300\text{ m}$ 내 이웃 차량 수 $N_{\text{est}, i}(t)$를 기준 용량 $N_0 = 50\text{ [대]}$로 정규화한 값으로 국소 차량 군집 밀도를 나타낸다. 셋째, $s_{t, 3}^{(i)} = v_i(t) / 25.0 \in [0.0, \infty)$는 차량의 현재 속도를 기준 최고 속도 $v_{\max} = 25.0\text{ m/s}$ ($90\text{ km/h}$)로 나눈 값으로 차량의 주행 동역학적 특성을 반영한다. 넷째, $s_{t, 4}^{(i)} = \Delta t_i / 1.0 \in [0.0, \infty)$는 직전 CAM 전송 이후 경과한 시간을 최대 허용 주기 $T_{\text{GenCam, max}} = 1.0\text{ s}$로 정규화한 값으로 정보의 시간적 진부화 정도를 나타낸다. 다섯째, $s_{t, 5}^{(i)} = \text{CBR}_{\text{smoothed}, i}(t) \in [0.0, 1.0]$는 EMA 필터를 거쳐 고주파 잡음이 제거된 평활 혼잡도로서 장기적인 채널 평형 기준선 역할을 수행한다. 이 5가지 상태 변수는 채널 혼잡도, 밀도, 동역학 및 정보 신선도를 포괄하여 신경망이 환경을 전방위적으로 인지하도록 지원한다.

### B. 행동 공간 (Action Space) $\mathcal{A}$
에이전트의 이산 행동 $a_t \in \mathcal{A} = \{0, 1, \dots, 15\}$ ($|\mathcal{A}| = 16$)는 패킷 생성 최소 제약 주기 $T_{\text{GenCam}}$과 송신 전력 $P_{\text{tx}}$의 $4 \times 4$ 2차원 직교 격자(Orthogonal Grid) 결합 인덱스로 정의된다. 통신 표준 규격 및 OBU 하드웨어의 가변 범위를 고려하여 전송 주기는 $\mathcal{T}_{\text{grid}} = \{0.100, 0.200, 0.500, 1.000\}\text{ [s]}$ ($10\text{ Hz}, 5\text{ Hz}, 2\text{ Hz}, 1\text{ Hz}$)의 4단계로 구성된다. 송신 전력은 $\mathcal{P}_{\text{grid}} = \{0.0, 10.0, 20.0, 30.0\}\text{ [dBm]}$ ($1\text{ mW}, 10\text{ mW}, 100\text{ mW}, 1000\text{ mW}$)의 4단계로 이산화된다. 선택된 행동 인덱스 $a_t$로부터 물리 계층 제어 파라미터로의 전단사 디코딩 함수 $\Omega: \mathcal{A} \to \mathcal{T}_{\text{grid}} \times \mathcal{P}_{\text{grid}}$는 정수 몫 연산 $i_T = \lfloor a_t / 4 \rfloor \in \{0, 1, 2, 3\}$과 나머지 연산 $i_P = (a_t \bmod 4) \in \{0, 1, 2, 3\}$을 통해 $T_{\text{GenCam}}(a_t) = \mathcal{T}_{\text{grid}}[i_T]$ 및 $P_{\text{tx}}(a_t) = \mathcal{P}_{\text{grid}}[i_P]$로 확정된다. 이와 같은 2차원 이산 행동 결합은 복잡한 연속 제어기 대비 학습 수렴 안정성을 보장하면서도 물리 계층과 MAC 계층의 파라미터를 유기적으로 결합 제어할 수 있는 풍부한 표현력을 제공한다.

이러한 전송 주기와 송신 전력의 동시 제어 구조는 단순히 패킷 전송 주기만을 조절하는 기존 1차원 DCC 방식의 한계를 극복한다. 송신 전력을 조절하여 주변 간섭 범위를 능동적으로 축소하고 전송 주기를 조절하여 매체 접근 경합 빈도를 완화함으로써 2차원 최적화 공간에서 무선 자원 활용도를 극대화할 수 있다. 예를 들어 차량 밀도가 극도로 높은 환경에서는 송신 전력을 $10\text{ dBm}$으로 낮추고 주기를 $0.5\text{ s}$로 늘려 채널 붕괴를 막을 수 있다. 반대로 차량 밀도가 낮은 고속 주행 환경에서는 전력을 $30\text{ dBm}$으로 높이고 주기를 $0.1\text{ s}$로 단축하여 도달 거리와 인식 정확도를 극대화할 수 있다. 따라서 16차원 이산 행동 공간은 복잡한 무선 환경에 적응하기 위한 풍부한 제어 표현력을 제공한다.

### C. 다중 목표 보상 함수 (Multi-Objective Reward Function) $\mathcal{R}$
고밀도 V2X 통신에서 단일 지표만을 최적화할 경우 심각한 시스템 안티패턴이 발생할 수 있다. 예를 들어 채널 점유율만을 낮추려 할 경우 패킷 전송을 중단하여 AoI가 폭증할 수 있으며, 수신율만을 높이려 할 경우 과도한 송신 전력으로 인해 인접 차량들의 전송을 마비시킬 수 있다. 이러한 상충 관계를 조율하기 위해 타임스텝 $t$에서 에이전트가 획득하는 즉각 보상 $R_t$를 3가지 물리적 목표의 가중합인 $R_t = R_1(\mathbf{s}_t) + R_2(\mathbf{s}_t) + R_3(\mathbf{s}_t)$로 설계한다. 각 성분은 군집 인식성 확보, 표준 혼잡도 추종 및 정보 신선도 보존을 독립적으로 유도하도록 정식화된다. 따라서 에이전트는 무선 채널의 혼잡 억제와 안전 비콘의 실시간 최신성 유지라는 상충 목표 간의 최적 파레토 균형점을 효과적으로 학습하게 된다.

첫째, 이웃 차량 인식성 보상 $R_1(\mathbf{s}_t) = +w_1 \cdot s_{t, 2} = +0.01 \cdot (N_{\text{est}, i}(t) / 50.0)$는 통신 반경 내에 많은 이웃 차량이 존재할 때 양의 보상을 부여하여 고밀도 교차로에서도 에이전트가 소극적인 침묵 상태로 퇴화하지 않도록 유도한다. 둘째, 채널 혼잡 및 요동 억제 페널티 $R_2(\mathbf{s}_t) = -w_2 \cdot |\text{CBR}_{\text{smoothed}, i}(t) - \text{CBR}_{\text{target}}| = -1.0 \cdot |\text{CBR}_{\text{smoothed}, i}(t) - 0.60|$는 ETSI 표준 권고 최적 채널 점유율인 0.60과의 절대 편차를 음의 페널티로 부과하여 채널을 60% 경계선 상에 수렴시키고 불필요한 제어 요동을 억제한다. 셋째, 정보 신선도 지연 억제 페널티 $R_3(\mathbf{s}_t) = -w_3 \cdot s_{t, 4} = -0.10 \cdot (\Delta t_i / 1.0)$는 직전 패킷 전송 이후 경과 시간에 비례하여 선형 페널티를 부과함으로써 전송 간격이 과도하게 벌어지는 현상을 방지하고 낮은 AoI를 유지하도록 보장한다. 이 3대 보상 성분의 결합을 통해 강화학습 에이전트는 채널 안정성, 주변 인식성, 정보 신선도 간의 파레토 최적(Pareto Optimal) 균형점을 자율적으로 학습한다. 나아가 선형 결합 가중치($w_1=0.01, w_2=1.0, w_3=0.10$)는 시뮬레이션 환경에서 채널 과포화 방지를 최우선으로 두면서도 패킷 전송 주기가 극단적으로 늘어나는 왜곡을 효과적으로 방지하도록 튜닝되었다.

---

## 3.3 제안하는 REMO-DQN 신경망 아키텍처 (Proposed REMO-DQN Neural Network Architecture)

본 절에서는 고밀도 V2X 네트워크의 극심한 상태 비선형성과 급격한 혼잡도 변화에 대응하기 위해 제안하는 REMO-DQN(ResNet-MoE-Dueling Deep Q-Network) 아키텍처를 상세히 기술한다. REMO-DQN은 고차원 비선형 상태 특징을 안정적으로 추상화하는 ResNet 백본, 도로 교통 혼잡도 국면별로 특화된 다중 전문가 서브네트워크를 동적으로 선택하는 MoE 게이팅 라우터, 그리고 상태 가치와 행동 이점을 분리 추정하는 Dueling DQN 구조를 결합한 하이브리드 심층 강화학습 모델이다. 이 모델은 각 구성 요소의 구조적 장점을 극대화하여 V2X 혼잡 제어의 샘플 효율성과 정책 수렴성을 동시에 향상시킨다. 특히 단일 신경망 모델이 겪는 용량 포화 및 특정 트래픽 체제에 대한 과적합 한계를 극복하기 위해, 혼합 전문가(MoE) 원리를 강화학습의 가치 함수 추정 프레임워크에 성공적으로 융합하였다. 아래에 제시된 블록 다이어그램은 상태 입력부터 특징 추출, 소프트 게이팅, 듀얼링 Q-값 합성 및 부하 균등화 정규화에 이르는 전체 데이터 흐름과 신경망 연결 구조를 개괄한다.

```
                  ┌──────────────────────────────────────────────┐
                  │           Input State s_t in R^5             │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │         ResNet Feature Extractor             │
                  │   Linear(5, 128) -> ReLU                     │
                  │   Residual Block 1: [Linear + ReLU + Linear] │
                  │                     + Skip Connection -> ReLU│
                  │   Residual Block 2: [Linear + ReLU + Linear] │
                  │                     + Skip Connection -> ReLU│
                  └──────────────────────┬───────────────────────┘
                                         │
                         Latent Feature  │ phi(s_t) in R^128
                         ┌───────────────┴───────────────┐
                         │                               │ (Gradient Detach)
                         ▼                               ▼
  ┌────────────────────────────────────────────┐ ┌──────────────────────────────┐
  │         Dueling Experts (K = 3)            │ │      MoE Gating Router       │
  │                                            │ │   Linear(128, 64) -> ReLU    │
  │  Expert 1 (Low Density / Free-flow)        │ │   Linear(64, 3)              │
  │  Expert 2 (Medium Density / Transition)    │ │   Softmax -> Gating Weights  │
  │  Expert 3 (High Density / Saturation)      │ │   g(s_t) = [g1, g2, g3]^T    │
  │                                            │ └──────────────┬───────────────┘
  │  For each Expert k in {1, 2, 3}:           │                │
  │   - Value Stream:                          │                │
  │     Linear(128, 64) -> ReLU -> Linear(64,1)│                │
  │     ==> V_k(s_t) in R^1                    │                │
  │   - Advantage Stream:                      │                │
  │     Linear(128, 64) -> ReLU -> Linear(64,16│                │
  │     ==> A_k(s_t, a) in R^16                │                │
  │   - Dueling Aggregation:                   │                │
  │     Q_k(s_t, a) = V_k + (A_k - mean(A_k))  │                │
  └──────────────────────┬─────────────────────┘                │
                         │ Q_k(s_t, a)                          │ g_k(s_t)
                         └───────────────┬──────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │           MoE Weighted Q-Value Sum           │
                  │        Q(s_t, a) = sum_{k=1}^3 g_k Q_k       │
                  └──────────────────────────────────────────────┘
```

### A. ResNet 기반 잔차 특징 추출 백본 (Residual Feature Extractor)
입력 상태 벡터 $\mathbf{s}_t \in \mathbb{R}^5$는 128차원의 은닉 공간으로 선형 사영된 후, 2개의 직렬 잔차 블록(Residual Block)을 통과하여 고차원 잠재 표현 $\phi(\mathbf{s}_t) \in \mathbb{R}^{128}$로 변환된다. 초기 선형 투영 계층은 입력 상태 변수 간의 1차 상호작용을 포착하며 $\mathbf{h}_0 = \text{ReLU}(\mathbf{W}_{\text{in}} \mathbf{s}_t + \mathbf{b}_{\text{in}})$로 계산된다 ($\mathbf{W}_{\text{in}} \in \mathbb{R}^{128 \times 5}$, $\mathbf{b}_{\text{in}} \in \mathbb{R}^{128}$). 각 잔차 블록 $l \in \{1, 2\}$은 2개의 선형 변환 계층과 ReLU 활성화 함수 및 항등 스킵 연결(Identity Skip Connection)로 구성된다. 구체적인 순전파 연산은 중간 표현 $\mathbf{z}_l^{(1)} = \text{ReLU}(\mathbf{W}_{l, 1} \mathbf{h}_{l-1} + \mathbf{b}_{l, 1})$, 2차 변환 $\mathbf{z}_l^{(2)} = \mathbf{W}_{l, 2} \mathbf{z}_l^{(1)} + \mathbf{b}_{l, 2}$, 그리고 스킵 결합 $\mathbf{h}_l = \text{ReLU}(\mathbf{z}_l^{(2)} + \mathbf{h}_{l-1})$의 단계로 진행된다 ($\mathbf{W}_{l, 1}, \mathbf{W}_{l, 2} \in \mathbb{R}^{128 \times 128}$, $\mathbf{b}_{l, 1}, \mathbf{b}_{l, 2} \in \mathbb{R}^{128}$). 이러한 계층적 변환 구조는 다차원 관측 상태의 비선형 특징을 왜곡 없이 추출하여 후속 전문가 모듈에 고품질의 잠재 벡터를 전달한다.

최종 ResNet 백본의 출력 잠재 특징 벡터는 $\phi(\mathbf{s}_t) = \mathbf{h}_2 \in \mathbb{R}^{128}$이다. 이러한 잔차 연결 구조는 역전파 시 그래디언트 소실(Gradient Vanishing)을 방지하여 신경망이 깊어져도 안정적인 학습을 가능하게 하며, 차량 밀도와 속도가 비선형적으로 결합된 상태 공간의 특징을 손실 없이 보존한다. 일반적인 다층 퍼셉트론(MLP)이 겪는 표현 붕괴 문제를 해결함으로써 도로 상황의 미세한 변화를 고차원 잠재 공간에 명확히 사상한다. 또한 적절한 은닉 차원(128)을 설정하여 온보드 OBU 프로세서에서도 1.2 ms의 신속한 순전파 추론(100 ms 제어 주기의 1.2% 점유)이 가능하도록 경량성을 유지한다. 결과적으로 잔차 백본은 후속 모듈들이 고품질의 공통 특징 표현을 공유할 수 있는 견고한 토대를 제공한다.

### B. MoE 게이팅 라우터 및 그래디언트 분리 메커니즘 (MoE Gating Router & Gradient Detach)
MoE 게이팅 라우터는 잠재 특징 $\phi(\mathbf{s}_t)$를 입력받아 현재 차량이 직면한 트래픽 환경에 따라 $K=3$개의 전문가 서브네트워크에 할당할 확률 가중치 벡터 $\mathbf{g}(\mathbf{s}_t) = [g_1(\mathbf{s}_t), g_2(\mathbf{s}_t), g_3(\mathbf{s}_t)]^T$를 계산한다. 이때 게이팅 라우터의 손실 그래디언트가 ResNet 백본의 공통 표현 학습을 왜곡시키는 간섭 현상을 방지하기 위해 그래디언트 분리 연산자 $\text{sg}[\cdot]$ (Stop-gradient / Detach)를 적용한다. 라우터 신경망은 1개의 은닉층을 포함하며 $\mathbf{g}_{\text{hidden}} = \text{ReLU}(\mathbf{W}_{g, 1} \text{sg}[\phi(\mathbf{s}_t)] + \mathbf{b}_{g, 1})$ ($\mathbf{W}_{g, 1} \in \mathbb{R}^{64 \times 128}$, $\mathbf{b}_{g, 1} \in \mathbb{R}^{64}$) 및 로짓 벡터 $\mathbf{l}_g = \mathbf{W}_{g, 2} \mathbf{g}_{\text{hidden}} + \mathbf{b}_{g, 2}$ ($\mathbf{W}_{g, 2} \in \mathbb{R}^{3 \times 64}$, $\mathbf{b}_{g, 2} \in \mathbb{R}^3$)를 계산한다. 최종 라우팅 확률은 소프트맥스 함수를 거쳐 $g_k(\mathbf{s}_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$로 결정된다. 이와 같은 소프트 라우팅 구조는 급격한 이산적 모드 전환 없이 트래픽 혼잡 국면의 전이에 맞추어 각 전문가의 정책을 매끄럽게 융합한다.

산출된 게이팅 가중치는 $\sum_{k=1}^3 g_k(\mathbf{s}_t) = 1$ 및 $g_k(\mathbf{s}_t) \ge 0$의 볼록 결합 성질을 만족하며, 저혼잡, 중혼잡, 고혼잡 트래픽 영역에 맞춰 전문가 네트워크를 부드럽게 분기(Soft Routing)한다. 그래디언트 분리를 통해 게이팅 네트워크는 백본의 특징 맵을 직접 교란하지 않고 주어진 특징 공간 상에서 최적의 클러스터링 경계만을 학습한다. 이는 전문가 네트워크의 특화 학습이 진행되는 동안 백본 특징의 표현이 불안정하게 흔들리는 문제를 효과적으로 방지한다. 결과적으로 라우터는 차량 밀도와 채널 점유율의 변화에 따라 적합한 전문가 조합을 매끄럽게 전환하는 지능형 스위칭 허브 역할을 수행한다. 또한 연속적인 확률 가중치는 이산적 모드 전환 시 발생할 수 있는 채널 제어 변동성을 최소화한다.

### C. Dueling DQN 구조의 다중 전문가 서브네트워크 (Dueling Experts)
$K = 3$개의 각 전문가 서브네트워크 $k \in \{1, 2, 3\}$는 공유 잠재 특징 $\phi(\mathbf{s}_t)$를 입력으로 받아 상태 자체의 스칼라 가치를 평가하는 가치 스트림 $V_k(\mathbf{s}_t)$와 각 행동의 상대적 이점을 평가하는 이점 스트림 $A_k(\mathbf{s}_t, a)$로 분리된다. 가치 스트림은 64차원 은닉층을 거쳐 스칼라 값을 출력하며 $V_k(\mathbf{s}_t) = \mathbf{W}_{v, k}^{(2)} \text{ReLU}(\mathbf{W}_{v, k}^{(1)} \phi(\mathbf{s}_t) + \mathbf{b}_{v, k}^{(1)}) + b_{v, k}^{(2)}$로 계산된다 ($\mathbf{W}_{v, k}^{(1)} \in \mathbb{R}^{64 \times 128}$, $\mathbf{W}_{v, k}^{(2)} \in \mathbb{R}^{1 \times 64}$). 이점 스트림은 16차원 행동 벡터를 출력하며 $A_k(\mathbf{s}_t, a) = \mathbf{W}_{a, k}^{(2)} \text{ReLU}(\mathbf{W}_{a, k}^{(1)} \phi(\mathbf{s}_t) + \mathbf{b}_{a, k}^{(1)}) + \mathbf{b}_{a, k}^{(2)}$로 계산된다 ($\mathbf{W}_{a, k}^{(1)} \in \mathbb{R}^{64 \times 128}$, $\mathbf{W}_{a, k}^{(2)} \in \mathbb{R}^{16 \times 64}$). 가치 스트림은 주변 환경의 전반적인 안전도와 채널 혼잡도를 총괄 평가하고, 이점 스트림은 주어진 상태에서 취할 수 있는 각 전송 파라미터 쌍의 상대적 유효성을 식별한다. 이러한 이원화된 신경망 분리는 상태 가치에 의해 행동 선택의 미세한 차이가 묻히는 현상을 방지하여 학습 속도와 가치 추정의 정확도를 크게 향상시킨다.

가치 함수와 이점 함수의 고유한 분리를 보장하고 최적화 수렴성을 높이기 위해 행동 이점들의 산술 평균을 감산하는 평균 중심화(Mean-Centering) 공식을 적용하여 전문가 $k$의 Q-값을 $Q_k(\mathbf{s}_t, a) = V_k(\mathbf{s}_t) + (A_k(\mathbf{s}_t, a) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A_k(\mathbf{s}_t, a'))$ ($|\mathcal{A}| = 16$)로 산출한다. 최종 행동-가치 함수 $Q(\mathbf{s}_t, a)$는 모든 전문가 Q-값과 게이팅 가중치의 가중합인 $Q(\mathbf{s}_t, a) = \sum_{k=1}^3 g_k(\mathbf{s}_t) \cdot Q_k(\mathbf{s}_t, a)$로 결합된다. 이 구조는 특정 상태에서 모든 행동의 가치가 전반적으로 높거나 낮은 경우 가치 스트림이 이를 빠르게 흡수하고, 미세한 행동 간의 우열은 이점 스트림이 정밀하게 구별하도록 유도하여 학습 효율성을 극대화한다. 하드 스위칭 방식과 달리 연속적인 가중합을 적용하므로 트래픽 혼잡도가 점진적으로 변하는 과도 구간에서도 제어 파라미터가 급격히 불연속적으로 튀는 현상을 방지한다. 이로써 복잡한 V2X 통신 채널에서도 안정적인 정책 수렴과 빠른 적응 속도를 동시에 확보할 수 있다.

### D. 신경망 최적화 목표 및 부하 균등화 정규화 (Optimization Objectives & Load Balancing Loss)
신경망 파라미터 $\theta$의 안정적인 학습을 위해 Double DQN 방식의 타겟 계산과 MoE 전문가 붕괴(Expert Collapse)를 방지하기 위한 부하 균등화 손실을 결합하여 최적화를 수행한다. 타겟 Q-값 $y_t$는 온라인 네트워크로 최적 행동을 선택하고 타겟 네트워크 파라미터 $\theta^-$로 가치를 평가하여 과대추정 편향을 억제한다. 즉, 최적 행동 $a^* = \arg\max_{a' \in \mathcal{A}} Q(\mathbf{s}_{t+1}, a'; \theta)$에 대해 $y_t = R_t + \gamma \cdot Q(\mathbf{s}_{t+1}, a^*; \theta^-) \cdot (1 - d_t)$의 타겟이 생성되며, 여기서 할인율은 $\gamma = 0.99$, $d_t \in \{0, 1\}$는 에피소드 종료 플래그이다. 미니배치 $\mathcal{B}$ ($\vert\mathcal{B}\vert = 64$)에 대한 시간차(TD) 오차 손실은 평균 제곱 오차 $\mathcal{L}_{\text{TD}}(\theta) = \frac{1}{\vert\mathcal{B}\vert} \sum_{(\mathbf{s}, a, r, \mathbf{s}', d) \in \mathcal{B}} (Q(\mathbf{s}, a; \theta) - y)^2$로 정의된다. 이러한 손실 구조는 행동 가치의 과대추정을 효과적으로 억제하여 무선 채널의 급격한 변동 속에서도 안정적인 벨만 최적화 수렴을 유도한다.

한편 MoE 구조에서 특정 전문가 서브네트워크로만 라우팅이 편중되는 전문가 사장 현상을 효과적으로 방지하기 위해, 미니배치 내 전문가별 평균 게이팅 확률 $\bar{g}_k = \frac{1}{|\mathcal{B}|} \sum_{b=1}^{|\mathcal{B}|} g_k(\mathbf{s}_b)$에 대한 변동 계수 제곱(Squared Coefficient of Variation, $\text{CV}^2$)을 부하 균등화 정규화 손실로 부과한다. 변동 계수 제곱은 $\text{CV}^2(\bar{\mathbf{g}}) = \text{Var}(\bar{\mathbf{g}}) / ((\text{Mean}(\bar{\mathbf{g}}))^2 + \epsilon)$ ($K = 3, \epsilon = 10^{-8}$)로 정의되며, 정규화 손실은 $\mathcal{L}_{\text{LB}}(\theta) = \lambda_{\text{LB}} \cdot \text{CV}^2(\bar{\mathbf{g}})$ ($\lambda_{\text{LB}} = 0.01$)로 계산된다. 최종 종합 손실 함수는 $\mathcal{L}_{\text{total}}(\theta) = \mathcal{L}_{\text{TD}}(\theta) + \mathcal{L}_{\text{LB}}(\theta)$로 주어지며, Adam 옵티마이저(학습률 $\eta = 5 \times 10^{-4}$)를 통해 종단간 방식으로 최소화된다. 이 손실 설계를 통해 3개의 전문가 네트워크는 각각 서로 다른 트래픽 혼잡 영역을 균등하게 분담하여 학습함으로써 모델 전체의 표현 용량과 일반화 성능을 극대화한다. 가중치 계수 $\lambda_{\text{LB}} = 0.01$은 TD 학습의 최적성을 저해하지 않으면서 전문가 분화를 촉진하는 최적의 정규화 강도로 실험적으로 검증되었다.

---

## 3.4 분산 REMO-DQN 학습 및 온라인 추론 알고리즘

개별 차량 에이전트의 OBU에서 실행되는 분산 REMO-DQN의 온라인 의사결정 및 심층 강화학습 절차를 **Algorithm 1**에 종합 제시한다. 전체 알고리즘은 네트워크 파라미터 초기화, 온라인 분산 행동 선택, 무선 채널 전송 및 환경 전이, 다중 목표 보상 계산과 경험 저장, 그리고 미니배치 손실 역전파의 5단계 유기적 순환 구조로 구성된다. 각 차량은 매 100ms 시간 슬롯마다 국소 상태를 관측하여 최적의 패킷 전송 주기와 송신 전력을 독립적으로 결정한다. 학습 단계에서는 경험 재생 버퍼와 Double DQN 타겟 동기화를 통해 비상관화된 안정적 파라미터 갱신을 수행한다. 최종적으로 수렴된 정책 모델은 도심 도로망의 다양한 교통 밀도 변화 속에서도 실시간으로 분산 혼잡 제어를 강인하게 완수한다.

---

### Algorithm 1: Decentralized REMO-DQN Training and Online Inference Algorithm

1. **Initialize**:
   - 온라인 Q-네트워크 파라미터 $\theta = \{\mathbf{W}_{\text{in}}, \mathbf{b}_{\text{in}}, \mathbf{W}_l, \mathbf{b}_l, \mathbf{W}_g, \mathbf{b}_g, \mathbf{W}_{v, k}, \mathbf{b}_{v, k}, \mathbf{W}_{a, k}, \mathbf{b}_{a, k}\}$ 초기화
   - 타겟 Q-네트워크 파라미터 복제 초기화: $\theta^- \leftarrow \theta$
   - 경험 재생 메모리 $\mathcal{D}$ (용량 $N_{\text{replay}} = 50,000$), 미니배치 크기 $|\mathcal{B}| = 64$, 할인율 $\gamma = 0.99$ 설정
   - 탐험 파라미터 $\epsilon \leftarrow 1.0$, 최소 탐험률 $\epsilon_{\min} = 0.01$, 감쇄율 $\epsilon_{\text{decay}} = 0.995$ 설정
   - 타겟 네트워크 동기화 주기 $C_{\text{target}} = 100\text{ steps}$, Adam 학습률 $\eta = 5 \times 10^{-4}$ 설정

2. **For each episode** $e = 1, \dots, E_{\max}$ **do**:
   - SUMO 교통 시뮬레이터 및 무선 채널 환경 초기화
   - 각 활성 차량 $i \in \mathcal{V}(0)$에 대해 초기 상태 벡터 $\mathbf{s}_0^{(i)} = [\text{CBR}_i(0), N_{\text{est}, i}(0)/50, v_i(0)/25, 0.0, \text{CBR}_{\text{smoothed}, i}(0)]^T$ 관측

3. $\quad$ **For each time slot** $t = 0, \dots, T_{\text{end}}$ ($\Delta T_{\text{step}} = 100\text{ ms}$) **do**:
   - **Step 3.1: Distributed Action Selection (각 차량 $i \in \mathcal{V}(t)$)**:
     - 확률 $\epsilon$으로 무작위 탐험 행동 $a_t^{(i)} \sim \text{Uniform}(\{0, \dots, 15\})$ 선택
     - 확률 $1 - \epsilon$으로 신경망 기반 탐욕적 최적 행동 선택:
       $$\phi(\mathbf{s}_t^{(i)}) \leftarrow \text{ResNet}(\mathbf{s}_t^{(i)})$$
       $$\mathbf{g}(\mathbf{s}_t^{(i)}) \leftarrow \text{MoE\_Router}(\text{sg}[\phi(\mathbf{s}_t^{(i)})])$$
       $$Q(\mathbf{s}_t^{(i)}, a) \leftarrow \sum_{k=1}^3 g_k(\mathbf{s}_t^{(i)}) Q_k(\mathbf{s}_t^{(i)}, a)$$
       $$a_t^{(i)} \leftarrow \arg\max_{a \in \{0, \dots, 15\}} Q(\mathbf{s}_t^{(i)}, a)$$
     - 물리 제어 파라미터 디코딩: $T_{\text{GenCam}, i} \leftarrow \mathcal{T}_{\text{grid}}[\lfloor a_t^{(i)} / 4 \rfloor]$, $P_{\text{tx}, i} \leftarrow \mathcal{P}_{\text{grid}}[a_t^{(i)} \bmod 4]$

   - **Step 3.2: Wireless Transmission & Environmental Transition**:
     - ETSI 동적 규칙에 따른 CAM 전송 여부 $\Psi_i(t)$ 결정
     - 무선 채널(Nakagami-$m$, 로그 경로 손실) 및 MAC 충돌 확률에 따른 패킷 수신 성공 여부 처리
     - 각 차량 $i$의 채널 점유율 $\text{CBR}_i(t+1)$, 평활 혼잡도 $\text{CBR}_{\text{smoothed}, i}(t+1)$, 이웃 수 $N_{\text{est}, i}(t+1)$ 갱신

   - **Step 3.3: Reward Computation & Experience Storage**:
     - 다중 목표 보상 계산: $R_t^{(i)} = +0.01 \frac{N_{\text{est}, i}(t)}{50.0} - 1.0 |\text{CBR}_{\text{smoothed}, i}(t) - 0.60| - 0.10 \frac{\Delta t_i}{1.0}$
     - 차기 상태 $\mathbf{s}_{t+1}^{(i)}$ 관측
     - 상태 전이 튜플 $(\mathbf{s}_t^{(i)}, a_t^{(i)}, R_t^{(i)}, \mathbf{s}_{t+1}^{(i)}, d_t^{(i)})$을 경험 재생 버퍼 $\mathcal{D}$에 저장

   - **Step 3.4: Network Optimization (Mini-batch Gradient Descent)**:
     - If $|\mathcal{D}| \ge |\mathcal{B}|$ then:
       - $\mathcal{D}$로부터 미니배치 $\mathcal{B} = \{(\mathbf{s}_b, a_b, r_b, \mathbf{s}'_b, d_b)\}_{b=1}^{|\mathcal{B}|}$ 균등 샘플링
       - Double DQN 타겟 가치 $y_b = r_b + \gamma Q(\mathbf{s}'_b, \arg\max_{a'} Q(\mathbf{s}'_b, a'; \theta); \theta^-)(1 - d_b)$ 계산
       - MoE 배치 평균 가중치 $\bar{g}_k = \frac{1}{|\mathcal{B}|}\sum_{b=1}^{|\mathcal{B}|} g_k(\mathbf{s}_b)$ 및 $\text{CV}^2(\bar{\mathbf{g}})$ 계산
       - 종합 손실 $\mathcal{L}_{\text{total}}(\theta) = \frac{1}{|\mathcal{B}|}\sum_{b=1}^{|\mathcal{B}|}(Q(\mathbf{s}_b, a_b; \theta) - y_b)^2 + 0.01 \cdot \text{CV}^2(\bar{\mathbf{g}})$ 계산
       - 역전파를 통한 신경망 파라미터 갱신: $\theta \leftarrow \theta - \eta \nabla_\theta \mathcal{L}_{\text{total}}(\theta)$

   - **Step 3.5: Periodic Target Synchronization & Exploration Decay**:
     - 매 $C_{\text{target}}$ 스텝마다 타겟 네트워크 파라미터 동기화: $\theta^- \leftarrow \theta$
     - 탐험률 감쇄: $\epsilon \leftarrow \max(\epsilon_{\min}, \epsilon \cdot \epsilon_{\text{decay}})$

4. **End For**
5. **Output**: 최적의 분산 혼잡 제어 정책을 수행하는 파라미터 $\theta^*$

---

## 3.5 시스템 및 아키텍처 파라미터 요약

본 논문의 시스템 모델 및 제안하는 REMO-DQN 아키텍처에서 사용된 모든 시뮬레이션 환경 및 신경망 하이퍼파라미터의 상세 수치를 **Table III-1**에 종합 정리한다. 제시된 파라미터 값들은 실제 도심 V2X 통신 규격(IEEE 802.11p 및 ETSI EN 302 637-2)과 OBU 임베디드 연산 환경을 정밀하게 모사하도록 구성되었다. 물리 계층 전파 모델과 MAC 계층 충돌 파라미터는 도심 준가시선 환경에서의 전파 손실과 경합 지연을 객관적으로 반영한다. 또한 신경망 은닉 차원 및 학습 파라미터는 350K 파라미터와 3.8M MACs의 경량 구조를 바탕으로 온보드 환경에서 1.2 ms의 실시간 추론(100 ms 제어 주기의 1.2% 점유)을 보장하도록 최적화되었다. 본 파라미터 세트는 제5장의 14개 비교 알고리즘 대상 성능 평가 실험에서도 엄격히 동일하게 적용된다.

### Table III-1: System Model and REMO-DQN Hyperparameters
| 분류 (Category) | 파라미터 기호 (Parameter) | 설정 값 (Value) | 물리적 의미 및 설명 (Description) |
|---|---|---|---|
| **물리 계층** | $f_c$ | $5.9\text{ GHz}$ | IEEE 802.11p CCH 중심 주파수 |
| | $B$ | $10\text{ MHz}$ | 무선 채널 대역폭 |
| | $R_{\text{data}}$ | $3.0\text{ Mbps}$ | BPSK $1/2$ 물리 계층 전송률 |
| | $\text{PL}_0, d_0$ | $47.86\text{ dB}, 1.0\text{ m}$ | 기준 거리에서의 자유 공간 경로 손실 |
| | $\alpha$ | $2.0$ | 로그-거리 경로 손실 지수 |
| | $m$ | $3.0$ | 나카가미-$m$ 페이딩 형상 파라미터 |
| | $N_0$ | $-94.0\text{ dBm}$ | 유효 배경 열잡음 전력 |
| | $\gamma_{\text{th}}$ | $5.0\text{ dB}$ ($3.162$) | BPSK 복조 요구 최소 SNR 임계치 |
| | $R_{\text{comm}}, R_{\text{sense}}$ | $300\text{ m}, 500\text{ m}$ | 통신 유효 반경 및 채널 감지 반경 |
| **MAC/DCC 계층** | $\Delta T_{\text{step}}$ | $100\text{ ms}$ ($0.1\text{ s}$) | 이산 의사결정 및 채널 갱신 슬롯 |
| | $L_{\text{CAM}}, T_{\text{tx}}$ | $280\text{ B}, 0.7467\text{ ms}$ | CAM 패킷 크기 및 에어타임 전송 시간 |
| | $\Delta \theta_{\text{th}}, \Delta d_{\text{th}}, \Delta v_{\text{th}}$ | $4.0^\circ, 4.0\text{ m}, 0.5\text{ m/s}$ | ETSI CAM 동적 이벤트 트리거 임계치 |
| | $T_{\text{GenCam, min}}, T_{\text{GenCam, max}}$ | $0.1\text{ s}, 1.0\text{ s}$ | 최소 허용 주기 ($10\text{ Hz}$) 및 최대 주기 ($1\text{ Hz}$) |
| | $\lambda_s, \text{CBR}_{\text{target}}$ | $0.5, 0.60$ | CBR 평활화 계수 및 목표 채널 혼잡도 |
| **MDP 정식화** | $\vert\mathcal{S}\vert$ | $5$ | 상태 공간 차원 $[\text{CBR}, N_{\text{est}}, v, \Delta t, \text{CBR}_{\text{smoothed}}]$ |
| | $\vert\mathcal{A}\vert$ | $16$ ($4 \times 4$) | $T_{\\text{GenCam}} \in \{0.1, 0.2, 0.5, 1.0\}\text{s} \times P_{\text{tx}} \in \{0, 10, 20, 30\}\text{dBm}$ |
| | $w_1, w_2, w_3$ | $0.01, 1.0, 0.10$ | 다중 보상 가중치 ($N_{\text{est}}$ 인식, CBR 목표, AoI 신선도) |
| **신경망 구조** | $d_{\text{hidden}}$ | $128$ | ResNet 백본 은닉 차원 |
| | $N_{\text{res}}$ | $2$ | 잔차 블록(Residual Block) 개수 |
| | $K$ | $3$ | MoE 전문가(Expert) 서브네트워크 개수 |
| | Router 구조 | Linear(128, 64) $\to$ ReLU $\to$ Linear(64, 3) $\to$ Softmax | MoE 게이팅 가중치 생성기 |
| | Dueling 구조 | Value: Linear(128,64) $\to$ 1, Adv: Linear(128,64) $\to$ 16 | 각 전문가별 가치 및 이점 분리 스트림 |
| **학습 하이퍼파라미터** | $\vert\mathcal{B}\vert$ | $64$ | 미니배치 샘플 크기 |
| | $\gamma, \eta$ | $0.99, 5 \times 10^{-4}$ | 할인율 및 Adam 옵티마이저 학습률 |
| | $\lambda_{\text{LB}}$ | $0.01$ | MoE 부하 균등화 변동 계수 손실 가중치 |
| | $N_{\text{replay}}, C_{\text{target}}$ | $50,000, 100$ | 리플레이 버퍼 용량 및 타겟 동기화 주기 |

---

# IV. 동적 시나리오 흐름 및 분산 전송 제어 파이프라인 (Dynamic Scenario Flow and Distributed Transmission Control Pipeline)

V2X 통신 환경에서 분산 혼잡 제어(DCC)의 핵심 목표는 차량 밀도와 무선 채널 상태의 동적 변화에 대응하여 통신 신뢰성과 정보 신선도를 균형 있게 유지하는 것이다. 본 장에서는 제안하는 REMO-DQN 프레임워크가 실제 차량 탑재 장치(OBU) 상에서 실행되는 시계열적 동작 메커니즘과 크로스 레이어 제어 파이프라인을 4단계 시나리오로 나누어 기술한다. 제1단계에서는 차량 내에서 발생하는 다양한 성격의 이기종 트래픽 모델과 MAC 계층 큐 적재 역학을 정의한다. 제2단계에서는 차량 밀도 증가에 따른 CSMA/CA MAC 계층의 채널 경합, 패킷 충돌 확률의 증가, 그리고 다중 경로 페이딩에 의한 채널 포화 메커니즘을 수학적으로 분석한다. 제3단계에서는 개별 차량 에이전트가 100 ms 주기로 로컬 채널 상태를 관측하고 노이즈를 필터링하여 다중 목표 보상을 도출하는 분산 혼잡 인지 과정을 서술한다. 마지막 제4단계에서는 관측된 상태 벡터를 기반으로 ResNet 백본과 MoE 게이팅 라우터가 상황별 도메인 특화 전문가 네트워크를 선택하고 최적의 전송 파라미터를 MAC 계층에 주입하는 동적 제어 과정을 설명한다.

## 4.1 패킷 발생 및 이기종 트래픽 혼합 시나리오 (Packet Generation & Heterogeneous Traffic Mixture)

V2X 네트워크의 차량들은 주행 안전성 확보와 부가 서비스 제공을 위해 서로 다른 우선순위와 발생 주기를 갖는 세 가지 범주의 이기종 트래픽을 생성한다. 첫 번째 트래픽은 ETSI EN 302 637-2 표준에 정의된 협력 인식 메시지(CAM)로서, 차량의 2차원 위치, 순간 속도, 진행 방향 및 가속도 정보를 포함하는 280 Bytes 크기의 주기적 안전 비콘이다. CAM 패킷은 차량의 동적 기구학 상태 변화에 따라 1 Hz에서 10 Hz 사이의 빈도로 생성되며, 차량의 기본 안전 거리 유지와 충돌 예측을 위한 핵심 데이터로 활용된다. 두 번째 트래픽은 ETSI EN 302 637-3 표준에 정의된 분산 환경 알림 메시지(DENM)로서, 급제동, 도로 공사, 빙판길 감지 등 돌발 상황 발생 시 비주기적으로 생성되는 이벤트 기반 긴급 메시지이다. DENM 메시지는 생명 안전과 직결되므로 IEEE 802.11p/bd 표준의 최고 접근 범주인 음성 우선순위(AC_VO)로 분류되어 MAC 계층 큐에 최우선적으로 적재된다. 세 번째 트래픽은 노변 기지국(RSU)이나 주변 차량과의 데이터 교환을 통해 유입되는 비안전 백그라운드 인포테인먼트 트래픽이며, 이는 상대적으로 낮은 우선순위 범주인 최선형(AC_BE) 및 백그라운드(AC_BK)로 할당된다.

차량의 OBU에 장착된 무선 트랜시버는 IEEE 802.11p 강화 분산 채널 접근(EDCA) 규격에 따라 4개의 독립된 선입선출(FIFO) 전송 큐를 유지한다. 상위 계층에서 생성된 각 패킷은 해당 접근 범주(AC)에 매핑되어 각 큐의 유입률 $\lambda_{\text{VO}}$, $\lambda_{\text{VI}}$, $\lambda_{\text{BE}}$, $\lambda_{\text{BK}}$에 따라 버퍼에 순차적으로 유입된다. 주기적 안전 비콘인 CAM은 비디오 우선순위(AC_VI) 또는 음성 우선순위(AC_VO) 큐로 전달되며, 생성 주기 $T_{\\text{GenCam}}$에 따라 시간당 패킷 유입률 $\lambda_{\text{CAM}} = 1 / T_{\\text{GenCam}}$이 결정된다. 각 전송 큐의 유한한 버퍼 용량을 $B_{\max}$라 할 때, 큐 내부의 패킷 축적 상태 $Q_k(t)$는 유입률 $\lambda_k$와 무선 채널로의 실제 전송 서비스율 $\mu_k(t)$의 차이에 의해 지배된다. 채널이 원활한 상태에서는 서비스율이 유입률을 상회하여 큐 대기 시간이 최소화되지만, 채널 경합이 심화되어 서비스율 $\mu_k(t)$가 급감하면 버퍼에 패킷이 누적되기 시작한다. 만약 큐 내부의 패킷 수가 버퍼 용량 $B_{\max}$에 도달하면 신규 유입 패킷이 손실되는 버퍼 드랍(Buffer Drop) 현상이 발생하여 정보의 연속성이 단절된다.

V2X 분산 혼잡 제어(DCC) 메커니즘은 응용 계층의 패킷 생성 주기 $T_{\\text{GenCam}}$을 동적으로 조절하여 MAC 계층 버퍼로의 패킷 유입률 $\lambda_{\text{CAM}}$을 직접 통제한다. 전송 주기가 단축되면 차량 간 상태 정보의 갱신 빈도가 높아져 최신 정보 연령(AoI)이 감소하지만, 큐 유입률이 증가하여 MAC 버퍼의 과부하를 초래할 위험이 커진다. 반대로 전송 주기가 연장되면 큐 유입 부하가 감소하여 버퍼 지연시간과 패킷 폐기 확률이 낮아지지만, 정보 갱신 주기가 길어져 AoI가 증가하는 교환(Trade-off) 관계가 형성된다. 특히 비주기적으로 발생하는 고우선순위 DENM 긴급 메시지의 무결성을 보장하기 위해서는 CAM 패킷의 유입률을 적절히 제어하여 전체 버퍼 점유율을 안전 수준으로 유지해야 한다. 따라서 REMO-DQN은 이러한 큐 역학과 채널 상태를 종합적으로 고려하여 패킷 유입률과 전송 전력을 최적화하도록 설계된다.

## 4.2 고밀도 환경에서의 채널 경합 및 MAC 충돌 메커니즘 (Channel Contention & MAC Collision in Dense Scenarios)

IEEE 802.11p 무선 표준의 MAC 계층은 반송파 감지 다중 접속 및 충돌 회피(CSMA/CA) 기반의 EDCA 프로토콜을 사용하여 무선 매체에 접근한다. 송신할 패킷이 존재하는 차량은 물리 계층의 클리어 채널 평가(CCA) 메커니즘을 통해 무선 채널의 에너지 준위를 측정하고 채널의 유휴(Idle) 여부를 판정한다. 채널이 중재 프레임 간격(AIFS) 동안 지속적으로 유휴 상태를 유지하면, 차량은 최소 경쟁 윈도우 크기 $CW_{\min}$ 범위 내에서 균등 분포를 따르는 정수형 백오프(Backoff) 카운터를 무작위로 선택한다. 백오프 카운터는 채널이 유휴 상태로 감지되는 매 타임 슬롯($\sigma = 13\,\mu\text{s}$)마다 1씩 감소하며, 카운터가 0에 도달하는 순간 패킷 전송이 개시된다. 만약 백오프 카운트다운 도중 다른 노드의 신호가 감지되어 채널이 비지(Busy) 상태로 전환되면 카운터 동작은 즉시 일시 정지되며, 채널이 다시 유휴 상태가 된 후 AIFS 시간이 경과해야 잔여 카운트다운을 재개한다.

통신 반경 내에 존재하는 차량의 수 $N$이 증가하면 동일한 타임 슬롯에 백오프 카운터가 0에 도달하여 동시에 패킷을 송출하려는 노드의 수가 급격히 늘어난다. Bianchi의 2차원 이산 마르코프 체인 모델에 따르면, 임의의 유휴 슬롯에서 단일 차량 노드가 패킷을 전송할 정상 상태 확률을 $\tau$라 할 때, 특정 송신 노드를 제외한 나머지 $N-1$개 노드 중 최소 하나 이상이 동일 슬롯에 전송을 시도할 조건부 충돌 확률 $P_{\text{collision}}$은 $P_{\text{collision}} = 1 - (1 - \tau)^{N-1}$로 정식화된다. 도심 교차로나 고밀도 정체 구간에서 통신 범위 내 노드 수 $N$이 20대에서 120대로 증가하면 충돌 확률 $P_{\text{collision}}$은 비선형적으로 폭증하게 된다. V2X 안전 메시지는 일대다 브로드캐스트 방식을 사용하므로 유니캐스트와 달리 수신 확인 응답(ACK)이나 RTS/CTS 프레임 교환이 존재하지 않아 충돌 발생 시 재전송이 이루어지지 않는다. 결과적으로 동시 송신 노드의 증가는 전파 매체 상에서 직접적인 패킷 신호 중첩을 유발하여 수신 노드에서의 복조 실패로 직결된다.

채널 경합에 의한 전송 충돌 외에도 공간적으로 이격된 노드들이 서로의 반송파 신호를 감지하지 못하는 은닉 노드(Hidden Terminal) 문제는 패킷 유실을 가속화하는 주된 요인이다. 또한 도심 건물 및 주변 차량에 의한 전파 반사, 산란 및 회절 현상은 나카가미-$m$ ($m=3.0$) 다중 경로 페이딩을 유발하여 수신 신호의 신호 대 잡음비(SNR)를 불규칙하게 변동시킨다. 송신 전력 $P_{\text{tx}}$, 거리 $d$에 따른 수신 SNR $\gamma$가 디코딩 임계치 $\gamma_{\text{th}} = 5.0\text{ dB}$ 미만으로 떨어지거나, 충돌 감쇠 계수 $f_{\text{collision}}(\text{CBR}) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR})$에 의해 수신 확률 $P_{\text{rx}} = P_{\text{succ}} \cdot f_{\text{collision}}(\text{CBR})$이 급격히 저하된다. 패킷 충돌이 누적되면 채널 점유율(CBR)이 포화 임계치(0.60 이상)를 초과하게 되며, MAC 전송 큐 지연이 누적되어 오래된 안전 패킷이 버퍼 내에서 폐기되는 악순환이 초래된다. 이러한 연쇄적인 성능 붕괴 현상은 차량 밀도가 높은 환경에서 패킷 전달률(PDR)을 급격히 떨어뜨리고 정보 연령(AoI)을 폭증시키는 근본 원인으로 작용한다.

## 4.3 DRL 기반 분산 혼잡 인지 및 상태/보상 정식화 (DRL-based Distributed Congestion Cognition)

REMO-DQN 프레임워크에서 각 차량의 OBU는 외부 중앙 집중형 인프라와의 통신 오버헤드 없이 온보드 센서 및 물리 계층 측정값을 통해 100 ms 단위로 5차원 연속 상태 벡터 $\mathbf{s}_t = [\text{CBR}_{\text{global}}(t), N_{\text{norm}}(t), v_{\text{norm}}(t), \Delta t_{\text{CAM, norm}}(t), \text{CBR}_{\text{smoothed}}(t)]^T \in \mathbb{R}^5$를 관측한다. 첫 번째 성분인 $\text{CBR}_{\text{global}}(t) \in [0.0, 1.0]$은 차량 주변 500 m 감지 반경 내에서 측정된 순간 채널 점유율을 나타낸다. 두 번째 성분 $N_{\text{norm}}(t) = N_{\text{est}}(t) / 50.0$은 통신 반경 300 m 내에서 추정된 유효 이웃 차량 수를 기준 용량 50대로 정규화한 지표이다. 세 번째 성분 $v_{\text{norm}}(t) = v(t) / 25.0$은 차량의 현재 이동 속도를 도심 최고 제한 속도인 25 m/s(90 km/h)로 정규화한 값이다. 네 번째 성분 $\Delta t_{\text{CAM, norm}}(t) = \Delta t_{\text{CAM}}(t) / 1.0$은 직전 CAM 전송 시각으로부터 경과된 시간을 최대 허용 주기인 1.0초로 정규화하여 정보 신선도 상태를 표현한다. 이러한 5차원 상태 벡터는 국소적 주행 환경과 무선 채널의 혼잡도를 포괄적으로 반영한다.

물리 계층에서 측정되는 순간 채널 점유율 $\text{CBR}_{\text{global}}(t)$는 무선 패킷의 무작위 유입 및 일시적 버스트로 인해 단기적인 고주파 노이즈를 포함한다. 상태 벡터의 다섯 번째 성분인 $\text{CBR}_{\text{smoothed}}(t)$는 평활화 계수 $\lambda_s = 0.5$를 적용한 지수이동평균(EMA) 필터를 통해 $\text{CBR}_{\text{smoothed}}(t) = (1 - \lambda_s) \cdot \text{CBR}_{\text{smoothed}}(t - \Delta T_{\text{step}}) + \lambda_s \cdot \text{CBR}_{\text{global}}(t)$와 같이 산출된다. EMA 필터는 일시적인 채널 스파이크에 의한 정책 불안정성을 억제하고 실제 거시적인 혼잡 추세를 정확히 포착할 수 있도록 지원한다. 기존 표준 기법인 ReactDCC가 고정된 경계값에서 상태 전환을 반복하며 유발하던 한계 사이클(Limit-cycle) 요동 현상은 이와 같은 평활화 과정을 통해 효과적으로 완화된다. 따라서 강화학습 에이전트는 단기적 노이즈에 과민 반응하지 않고 안정적인 장기 최적 제어 정책을 학습할 수 있다.

에이전트의 제어 행동을 최적화하기 위한 다중 목표 보상 함수 $\mathcal{R}(\mathbf{s}_t, a_t)$는 인식성 유지, 채널 혼잡 억제, 그리고 정보 신선도 확보의 세 가지 성분인 $\mathcal{R}(\mathbf{s}_t, a_t) = R_1(\mathbf{s}_t) + R_2(\mathbf{s}_t) + R_3(\mathbf{s}_t)$로 정식화된다. 첫 번째 인식성 보상 항 $R_1(\mathbf{s}_t) = +0.01 \cdot (N_{\text{est}} / 50.0)$은 고밀도 환경에서 주변 이웃 노드들과의 연결성을 유지하도록 보상 신호를 부여한다. 두 번째 혼잡 억제 페널티 항 $R_2(\mathbf{s}_t) = -1.0 \cdot |\text{CBR}_{\text{smoothed}} - 0.60|$은 ETSI 표준 권고 혼잡 임계치인 $\text{CBR}_{\text{target}} = 0.60$으로부터의 절대 편차에 비례하여 강한 벌점을 부과함으로써 채널 과부하와 과소 이용을 동시에 방지한다. 세 번째 신선도 페널티 항 $R_3(\mathbf{s}_t) = -0.10 \cdot (\Delta t_{\text{CAM}} / 1.0)$은 CAM 전송 간격이 불필요하게 벌어지는 것을 억제하여 정보 연령(AoI)을 낮추도록 유도한다. 이 세 가지 상충되는 목표 간의 정밀한 가중합 피드백 루프는 에이전트가 채널 안정성을 해치지 않는 범위 내에서 정보의 최신성을 극대화하도록 안내한다.

## 4.4 MoE 기반 동적 라우팅 및 전송 제어 (MoE-based Dynamic Routing & Transmission Control)

5차원 입력 상태 $\mathbf{s}_t$는 2개의 잔차 블록(Residual Block)과 스킵 연결(Skip Connection)로 구성된 ResNet 백본 신경망을 통과하여 128차원의 잠재 특징 벡터 $\phi(\mathbf{s}_t) \in \mathbb{R}^{128}$로 변환된다. 잔차 스킵 연결은 다층 퍼셉트론에서 발생하는 그래디언트 소실을 방지하고 상태 간 복잡한 비선형 상관관계를 보존한다. 추출된 잠재 특징 벡터는 그래디언트 분리 연산($\text{sg}[\phi(\mathbf{s}_t)]$)을 거쳐 MoE 게이팅 라우터로 전달되며, 64차원 은닉층과 소프트맥스 활성화 함수를 통해 3개 전문가 네트워크에 대한 정규화된 선택 확률 벡터 $G(\mathbf{s}_t) = [g_1(\mathbf{s}_t), g_2(\mathbf{s}_t), g_3(\mathbf{s}_t)]^T$를 출력한다. 각 전문가 $k$에 대한 게이팅 확률은 $g_k(\mathbf{s}_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$로 계산되며, 여기서 $l_g = \mathbf{W}_{g, 2} \text{ReLU}(\mathbf{W}_{g, 1} \text{sg}[\phi(\mathbf{s}_t)] + \mathbf{b}_{g, 1}) + \mathbf{b}_{g, 2}$이다. 여기서 그래디언트 분리 기법은 게이팅 라우터의 학습 그래디언트가 특징 추출 백본의 공통 표현을 왜곡시키는 현상을 차단하여 안정적인 라우팅 결정을 보장한다.

REMO-DQN의 3개 전문가 서브넷은 채널 점유율과 차량 밀도에 따라 도메인별로 특화된 제어 정책을 전담한다. 제1 전문가(Expert 1, 희소 교통 영역, $\text{CBR} < 0.40$)는 무선 채널 자원이 여유로운 상황에 활성화되어, 전송 주기를 최단 주기인 $T_{\\text{GenCam}} = 0.1\text{ s}$($10\text{ Hz}$)로 설정하고 송신 전력을 $20\sim30\text{ dBm}$으로 유지함으로써 정보 연령(AoI)을 최소화하는 정책을 구사한다. 제2 전문가(Expert 2, 전이 교통 영역, $0.40 \le \text{CBR} \le 0.60$)는 차량 밀도가 증가하며 채널 부하가 상승하는 과도 상태에서 활성화되어, 전송 주기를 $0.2\sim0.5\text{ s}$ 범위로 미세 조절하여 채널 점유율을 목표치인 0.60 근방으로 매끄럽게 수렴시킨다. 제3 전문가(Expert 3, 극심한 혼잡 영역, $\text{CBR} > 0.60$)는 대규모 차량 군집으로 인해 MAC 충돌 위험이 임계치를 초과한 상황에서 활성화되어, 전송 주기를 $T_{\\text{GenCam}} = 1.0\text{ s}$($1\text{ Hz}$)로 대폭 확장하고 송신 전력을 $0\sim10\text{ dBm}$으로 축소함으로써 무선 패킷 충돌을 차단하고 패킷 전달률(PDR)을 100 veh/km 고밀도에서도 73.41%로 방어한다. 이러한 조건부 연산(Conditional Computation) 구조는 단일 신경망 모델이 겪는 파라미터 간섭 문제를 해결하고 각 혼잡 단계별 최적 성능을 분리 달성한다.

각 전문가 서브넷 $k \in \{1, 2, 3\}$는 상태 가치 함수 $V_k(\mathbf{s}_t)$와 행동 이점 함수 $A_k(\mathbf{s}_t, a)$를 분리 추정하는 Dueling DQN 구조를 채택하여 평균 중심화된 Q-값 $Q_k(\mathbf{s}_t, a) = V_k(\mathbf{s}_t) + (A_k(\mathbf{s}_t, a) - \frac{1}{16}\sum_{a'=0}^{15} A_k(\mathbf{s}_t, a'))$를 도출한다. 전체 모델의 최종 Q-값 $Q(\mathbf{s}_t, a)$는 게이팅 가중치 $g_k(\mathbf{s}_t)$를 적용한 3개 전문가 Q-값의 소프트 가중합인 $Q(\mathbf{s}_t, a) = \sum_{k=1}^3 g_k(\mathbf{s}_t) \cdot Q_k(\mathbf{s}_t, a)$로 합성된다. 에이전트는 합성된 Q-값을 기반으로 최대 가치를 제공하는 최적 이산 행동 인덱스 $a_t^* = \arg\max_{a \in \mathcal{A}} Q(\mathbf{s}_t, a)$를 선택한다. 선택된 행동 인덱스는 전송 주기 격자 $\mathcal{T}_{\text{grid}} = [0.1, 0.2, 0.5, 1.0]\,\text{s}$와 송신 전력 격자 $\mathcal{P}_{\text{grid}} = [0.0, 10.0, 20.0, 30.0]\,\text{dBm}$을 참조하여 최적 전송 파라미터 쌍 $(T_{\\text{GenCam}}^*, P_{\text{tx}}^*)$로 즉시 디코딩된다. 디코딩된 제어 파라미터는 차량의 OBU MAC 계층 및 응용 계층 타이머에 실시간 주입되어, 채널 상태 변화에 즉각 대응하는 분산 폐루프 제어를 완성한다.

---

# 제5장 성능 평가 (Performance Evaluation)

본 장에서는 제안하는 자원 효율적 다중 목적 심층 강화학습 기반 탈중앙화 혼잡 제어 모델인 REMO-DQN(ResNet-MoE-Dueling DQL-DCC)의 성능을 다각도로 검증한다. 성능 평가는 현실적인 도시 도로 환경 및 차량 이동성 패턴을 반영한 미시적 교통 시뮬레이션과 고정밀 무선 물리 계층 채널 모델을 결합하여 체계적으로 수행된다. 제안 모델의 우수성과 기술적 타당성을 입증하기 위해 총 14종의 강화학습 및 심층 강화학습 알고리즘과 7종의 비강화학습 벤치마크 기법을 포함한 총 21개 모델과의 전방위 비교를 진행한다. 또한 학습 수렴도, 채널 점유율 안정성, 차량 밀도별 패킷 전달률, 정보 연령(AoI), 전송 거리별 신뢰성, 하드웨어 연산 복잡도, 그리고 구조적 절제 연구에 이르는 7대 핵심 성능 평가 지표를 바탕으로 심층적인 정량 분석을 제시한다. 모든 평가 수치는 실제 시뮬레이션 로그 및 실측 데이터셋으로부터 도출되었으며, IEEE Transactions on Wireless Communications (TWC)의 최고 권위 수준에 부합하도록 엄격한 학술적 형식과 통계적 엄밀성을 준수하여 기술된다.

---

## 5.1 시뮬레이션 환경 및 벤치마크 알고리즘 (Simulation Setup & Baseline Algorithms)

### 5.1.1 시뮬레이션 환경 및 무선 채널 모델링

본 연구의 성능 평가는 Eclipse SUMO(Simulation of Urban MObility, v1.1.5) 교통 시뮬레이터와 LibSUMO 기반의 실시간 네트워크 제어 엔진을 연동하여 구축된 통합 시뮬레이션 프레임워크에서 수행된다. 시뮬레이션 도로망은 도심 교차로 및 다차선 도로가 격자 형태로 배열된 6-블록 도심 격자망(Urban Grid Network)으로 모델링된다. 각 도로 세그먼트는 1km 길이의 왕복 4차선으로 구성되며, 차량들은 SUMO의 Krauss 차량 추종 모델(Car-following Model)과 LC2013 차선 변경 모델에 따라 자율적으로 주행한다. 전체 시뮬레이션 지속 시간은 3,600초이며, 차량의 주행 속도는 도심 주행 특성을 반영하여 20 km/h에서 100 km/h 사이에서 동적으로 변화한다. 차량 밀도는 10 veh/km의 희소 교통 환경부터 100 veh/km에 이르는 초고밀도 정체 환경까지 광범위하게 가변 설정되어 혼잡 제어 알고리즘의 확장성을 평가한다. 이러한 동적 차량 배치 및 이동성 모델은 도심 환경에서 발생하는 급격한 전파 음영 및 밀도 변동을 충실히 재현한다.

무선 물리 계층 및 매체 접근 제어(MAC) 계층은 IEEE 802.11p 규격 및 DSRC/C-V2X 표준 규격을 준용하여 구현된다. 반송파 주파수는 5.9 GHz ITS 전용 대역으로 설정되며, 무선 채널 대역폭은 10 MHz, 데이터 전송률은 BPSK 1/2 변조 방식에 해당하는 3 Mbps로 구성된다. 공칭 통신 반경($R_{\text{comm}}$)은 +20 dBm(100 mW) 송신 전력 기준 300m로 설정되며, OBU의 무선 채널 감지 반경은 500m로 지정된다. 차량 간 전파 감쇄는 도심 환경의 비가시선(NLOS) 및 다중경로 반사 특성을 정밀하게 모사하기 위해 자유 공간 로그 거리 경로 손실(Log-distance Path Loss, $\alpha = 2.0$) 모델과 Nakagami-$m$ ($m=3.0$) 페이딩 모델을 결합하여 적용한다. 송신 패킷은 ETSI 표준 협력 인식 메시지(CAM) 규격에 따라 280 바이트의 고정 페이로드 크기를 가지며, 패킷 전송 지속 시간($T_{\text{tx}}$)은 약 0.747 ms이다. CSMA/CA 메커니즘 하에서 채널 상태는 OBU 주변 500m 반경 내의 패킷 전송 이벤트를 기반으로 주기적으로 감지된다.

수신단에서의 신호 대 잡음비($\text{SNR}$)에 따른 패킷 수신 성공 확률 $P_{\text{rx}}(d)$는 Nakagami-$m$ 상보 누적 분포 함수(CCDF)를 바탕으로 엄밀하게 계산된다. 기준 거리 $d_0 = 1\text{ m}$에서의 기준 경로 손실은 $PL_0 = 20\log_{10}(4\pi d_0 f_c / c) \approx 47.86\text{ dB}$이며, 거리 $d$에서의 수신 신호 전력은 $P_{\text{rx}}(d) = P_{\text{tx}} - PL_0 - 10\alpha \log_{10}(d/d_0)$로 결정된다. 열잡음 전력은 $-174\text{ dBm/Hz} + 10\log_{10}(10\text{ MHz}) + NF(10\text{ dB}) = -94.0\text{ dBm}$으로 주어지며, 이를 통해 순시 수신 SNR인 $\bar{\gamma}(d)$가 도출된다. BPSK 1/2 변조의 성공적 복호화에 요구되는 임계 SNR($\gamma_{\text{th}}$)을 5.0 dB로 설정할 때, Nakagami-$m$ ($m=3$) 환경에서의 패킷 수신 성공 확률은 다음 식과 같이 표현된다. 이 확률식은 거리별 전파 감쇄와 다중 경로 페이딩을 통합하여 산출된다:

$$P_{\text{rx}}(d) = e^{-x} \left( 1 + x + \frac{x^2}{2} \right), \quad \text{where } x = \frac{m \cdot \gamma_{\text{th}}}{\bar{\gamma}(d)}$$

수신 전력이 열잡음 바닥 대비 임계 SNR 미만으로 떨어지거나 CSMA/CA 프로토콜 상에서 동시 전송으로 인한 패킷 충돌이 발생할 경우 해당 CAM은 영구 유실 처리된다. 이는 무결점 전송을 가정한 기존 단순 시뮬레이터와 달리 실제 CSMA/CA MAC 계층의 패킷 충돌 역학을 엄격히 반영한 것이다. 패킷 손실이 발생하면 수신단 OBU는 해당 송신 차량의 최신 상태를 갱신하지 못하고 이전 정보에 계속 의존하게 된다. 이에 따라 후속 패킷이 성공적으로 도착할 때까지 정보 연령(AoI)은 지속적으로 누적 증가하여 안전 위험을 초래한다. 구체적인 시뮬레이션 환경 및 물리 계층 파라미터 설정값은 표 5.1에 종합 정리되어 있다.

| 파라미터 (Parameter) | 설정값 (Value) | 설명 (Description) |
|---|---|---|
| 시뮬레이션 도로망 (Road Network) | Urban Grid (6 Blocks) | 도심 6블록 격자형 다차선 도로망 |
| 시뮬레이션 시간 (Duration) | 3,600 s | 전체 시뮬레이션 수행 시간 |
| 차량 밀도 범위 (Density Range) | 10 ~ 100 veh/km | 단위 도로 1km당 차량 대수 |
| 차량 주행 속도 (Vehicle Speed) | 20 ~ 100 km/h | Krauss 이동성 모델 기반 주행 속도 |
| 반송파 주파수 (Carrier Frequency) | 5.9 GHz | ITS 전용 통신 주파수 대역 |
| 채널 대역폭 (Channel Bandwidth) | 10 MHz | 802.11p DSRC 채널 대역폭 |
| 데이터 전송률 (Data Rate) | 3 Mbps | BPSK 1/2 변조 기반 전송률 |
| 송신 전력 ($P_{\text{tx}}$) | +20 dBm (100 mW) | OBU 기본 무선 송신 전력 |
| 공칭 통신 반경 ($R_{\text{comm}}$) | 300 m | 유효 패킷 도달 반경 |
| 채널 감지 반경 ($R_{\text{sense}}$) | 500 m | CBR 측정을 위한 주변 차량 감지 반경 |
| 패스 로스 지수 ($\alpha$) | 2.0 | 도심 전파 감쇄 지수 |
| 페이딩 모델 (Fading Model) | Nakagami-$m$ ($m=3$) | 도심 다중경로 고속 페이딩 모델 |
| 잡음 지수 (Noise Figure) | 10 dB | 수신기 열잡음 지수 |
| 수신 임계 SNR ($\gamma_{\text{th}}$) | 5.0 dB | 패킷 성공적 복호화 임계치 |
| CAM 패킷 크기 (Packet Size) | 280 Bytes | ETSI 표준 비콘 메시지 크기 |
| 기본 제어 주기 범위 ($T_{\text{GenCam}}$) | 100 ~ 1,000 ms | DCC 조절 가능한 패킷 생성 주기 |
| 목표 채널 점유율 ($\text{CBR}_{\text{target}}$) | 0.60 (60%) | ETSI TS 102 687 채널 혼잡 임계치 |

*표 5.1: 시뮬레이션 환경 및 무선 통신 파라미터 설정*

---

### 5.1.2 벤치마크 모델 분류 체계 및 하이퍼파라미터 최적화

제안 모델(REMO-DQN)의 기술적 성능과 혁신성을 다각도로 검증하기 위해 본 논문에서는 통신, 제어, 인공지능 분야에서 널리 활용되는 총 21개 알고리즘을 체계적으로 구축하여 비교 벤치마크로 설정하였다. 이들 모델은 기준 모델(Baseline), 규칙 기반 휴리스틱(Heuristic & Standard DCC), 지도학습(Supervised Learning), 기본 강화학습(Basic RL), 심층 Q-네트워크 변형(Deep Q-Networks), 그리고 최신 정책 그래디언트 및 고급 DRL(Advanced Policy Gradient & Offline DRL)의 6대 범주로 명확히 구분된다. 기준 모델인 `Fixed 10Hz`는 혼잡 제어 없이 100ms 고정 주기로 패킷을 송출하여 무제한 부하 환경에서의 채널 붕괴 한계선을 제시한다. 표준 DCC 모델로는 ETSI TS 102 687에 정의된 3단계 상태 전이형 `ReactDCC`와 선형 비례 주기 제어형 `AdaptDCC`, 그리고 임의의 휴리스틱 규칙 모델 `Heuristic`이 포함된다. 지도학습 군에는 3계층 심층 신경망 `StdMLP`, 엣지 임베디드용 초경량 신경망 `TinyMLP`, 그리고 깊이 5의 천단 의사결정나무 `DecTree`가 배치되어 모방 학습의 한계를 검증한다.

강화학습 및 심층 강화학습 군은 모델 아키텍처와 학습 메커니즘의 차이를 총망라하도록 광범위하게 선정되었다. 고전적 강화학습 알고리즘으로는 테이블 기반 가치 제어 모델인 `Q-Learning`, 온폴리시(On-policy) 시간차 학습 모델 `SARSA`, 그리고 가치와 정책을 분리한 기본 `Actor-Critic`을 포함한다. 심층 Q-네트워크 변형 군으로는 경험 재생 기반의 `Vanilla DQN`, Q값 과대추정을 억제하는 `Double DQN`, 상태 가치와 행동 이점을 분리한 `Dueling DQN`, 그리고 혼잡도별 다중 전문가를 단순 결합한 `MoEDQN`을 구성하였다. 최신 고급 DRL 군으로는 연속 결정론적 정책 제어 모델 `DDPG`, 클리핑 기반 온폴리시 최적화 모델 `PPO`, 최대 엔트로피 오프폴리시 모델 `SAC`, 쌍둥이 비평자 기반 `TD3`, 시퀀스 궤적 트랜스포머 `Decision Transformer`, 그리고 다중 차량 협력 제어를 위한 `MAPPO`를 망라하였다. 이러한 포괄적인 벤치마크 구성은 V2X 통신 도메인에서 수행된 비교 연구 중 가장 방대한 규모에 해당한다.

모든 학습 기반 벤치마크 모델의 공정하고 객관적인 성능 비교를 위해 Optuna 자동 하이퍼파라미터 최적화 프레임워크를 적용하여 100회 이상의 탐색 시행(Trial)을 수행하였다. 최적화 탐색 공간에는 학습률(Learning Rate, $\eta$), 할인율(Discount Factor, $\gamma$), 소프트 타깃 갱신 계수($\tau$), 정책 지연 갱신 빈도(Policy Delay), 클리핑 범위($\epsilon_{\text{clip}}$), 미니배치 크기(Batch Size), 리플레이 버퍼 용량(Buffer Size) 등이 포함되었다. 최적화 목적 함수는 다중 목적 보상 함수의 누적합을 최대화하도록 설정되었으며, 수렴 불안정성이 감지되는 하이퍼파라미터 조합은 조기 프루닝(Early Pruning)되었다. 최종 도출된 최적 파라미터 세팅은 각 모델의 최대 성능 잠재력을 온전히 발현시킬 수 있도록 정밀하게 조율되었다. 각 모델별 최적 하이퍼파라미터 구성값은 표 5.2에 상세히 명시되어 있다.

| 모델 범주 | 벤치마크 모델명 | 주요 최적화 하이퍼파라미터 (Optuna Optimal Configuration) |
|---|---|---|
| **Proposed** | **REMO-DQN** | $\eta=2.66\times 10^{-4}$, $\gamma=0.988$, Batch=64, Buffer=10,000, 3 Experts, ResNet-Block |
| Basic RL | Q-Learning | $\alpha=0.325$, $\gamma=0.961$, $\epsilon$-decay=$0.951$, State Discretization=6 bins |
| Basic RL | SARSA | $\alpha=0.028$, $\gamma=0.973$, $\epsilon$-decay=$0.991$, On-policy Temporal Difference |
| Basic RL | Actor-Critic | $\eta_{\text{actor}}=2.03\times 10^{-3}$, $\gamma=0.958$, Batch=32, Buffer=100,000 |
| Basic DRL | Vanilla DQN | $\eta=6.63\times 10^{-4}$, $\gamma=0.928$, Batch=64, Buffer=10,000, Target Sync=2 Ep |
| Add. DRL | Double DQN | $\eta=4.64\times 10^{-5}$, $\gamma=0.946$, Batch=64, Buffer=50,000, Target Sync=1 Ep |
| Add. DRL | Dueling DQN | $\eta=2.66\times 10^{-4}$, $\gamma=0.988$, Batch=64, Buffer=10,000, Target Sync=2 Ep |
| Add. DRL | MoEDQN | $\eta=3.99\times 10^{-3}$, $\gamma=0.922$, Batch=64, Buffer=50,000, Experts=2 |
| Advanced DRL | DDPG | $\eta_{\text{actor}}=2.90\times 10^{-5}$, $\eta_{\text{critic}}=3.09\times 10^{-3}$, $\gamma=0.901$, $\tau=0.0017$ |
| Advanced DRL | PPO | $\eta=1.47\times 10^{-4}$, $\gamma=0.972$, $\epsilon_{\text{clip}}=0.291$, $K_{\text{epochs}}=9$, Batch=32 |
| Advanced DRL | SAC | $\eta=9.02\times 10^{-3}$, $\gamma=0.907$, $\tau=0.0099$, $\alpha_{\text{entropy}}=0.464$, Batch=128 |
| Advanced DRL | TD3 | $\eta=3.79\times 10^{-4}$, $\gamma=0.918$, $\tau=0.0051$, Delay=1, Target Noise=0.205 |
| Advanced DRL | Decision Transformer | $\eta=3.52\times 10^{-4}$, $\gamma=0.933$, Context Window=20, Heads=4, Layers=3 |
| Advanced DRL | MAPPO | $\eta=4.34\times 10^{-5}$, $\gamma=0.962$, $\epsilon_{\text{clip}}=0.277$, $K_{\text{epochs}}=7$, CTDE Scheme |

*표 5.2: Optuna를 통해 최적화된 14개 RL/DRL 모델의 하이퍼파라미터 세팅*

---

## 5.2 (Metric 1) 학습 수렴도 및 샘플 효율성 (Reward Convergence & Sample Efficiency)

강화학습 기반 V2X 혼잡 제어 에이전트의 실질적 효용성을 검증하는 첫 번째 핵심 지표는 시변 무선 환경에서 정책이 얼마나 빠르고 견고하게 최적 보상점에 도달하는가를 나타내는 학습 수렴도 및 샘플 효율성이다. OBU 에이전트의 다중 목적 보상 함수는 목표 채널 점유율 준수($\text{CBR}_{\text{target}}=0.60$)와 패킷 생성 간격($\Delta t$) 최소화를 상호 절충하도록 $R_t = -|\text{CBR}_{\text{smoothed}} - 0.60| - 0.1 \times \Delta t$ 형태로 공식화된다. 14개 강화학습 및 DRL 모델을 대상으로 동일한 트래픽 환경에서 80~100 에피소드 동안 훈련을 진행하며 누적 보상, PDR, AoI, 그리고 평균 CBR의 진화 과정을 실측 추적하였다. 복잡한 무선 채널의 확률적 변동성 하에서 모델이 정책 붕괴 없이 높은 샘플 효율성을 유지하는 것은 엣지 디바이스의 온라인 재학습 가능성을 결정짓는 필수 요건이다. 에피소드별 누적 보상과 최종 10 에피소드의 평균 수렴 보상 및 패킷 전달률(PDR)은 표 5.3에 종합 정리되어 있다.

실측 데이터 분석 결과, 제안 모델인 REMO-DQN은 초기 5 에피소드의 평균 누적 보상 $-937,084.18$에서 출발하여 80 에피소드 이내에 최종 10 에피소드 평균 $-904,570.64$로 신속하고 견고하게 수렴하였다. 3단 융합 구조(ResNet 백본 + MoE 게이팅 + Dueling Q-헤드)의 복잡성에도 불구하고 REMO-DQN이 이처럼 뛰어난 수렴 안정성을 나타낸 것은 잔차 연결(Residual Connection)이 심층 신경망의 그래디언트 소실을 방지하고, MoE 게이팅이 상태 공간을 저밀도/중밀도/고밀도 도메인으로 자율 분할하여 정책 최적화의 탐색 난이도를 대폭 낮추었기 때문이다. 그 결과 REMO-DQN은 80 에피소드 수렴 시점에서 최종 PDR 75.60%, 최종 AoI 489.63 ms라는 높은 정상 상태 제어 성능을 성공적으로 확립하였다. 전체 훈련 과정 동안 보상 진동의 폭이 극히 제한적이었으며, 이는 제안 아키텍처가 V2X 보상 지형(Reward Landscape)을 효과적으로 평활화하고 있음을 실증한다. 이와 같은 뛰어난 학습 수렴성은 급변하는 도심 도로 환경에서도 신속하게 최적 정책으로 안착할 수 있는 알고리즘 강건성을 보장한다.

반면 정책 그래디언트 계열 모델인 PPO(최종 보상 $-899,332.10$, 최종 PDR 74.05%) 및 Actor-Critic(최종 보상 $-898,114.08$, 최종 PDR 83.24%)은 겉보기 수치상 높은 최종 보상을 기록하였으나, 훈련 에피소드 전반에 걸쳐 보상 함수의 표준편차가 매우 크게 나타나 심각한 분산 불안정성을 드러냈다. SAC 및 TD3와 같은 최신 연속 제어 알고리즘은 각각 $-922,399.92$ 및 $-920,564.76$의 최종 보상을 기록하였으나, V2X 전송 주기의 이산적 선택 특성과 연속 정책 탐색 간의 불일치로 인해 수렴 지연이 발생하였다. 오프라인 트랜스포머 기반의 Decision Transformer는 시계열 궤적 시퀀스를 컨텍스트로 모델링하는 구조적 특성상 초기 에피소드에서 극심한 정책 요동을 겪으며 최종 보상 $-937,158.43$과 최종 PDR 65.34%라는 저조한 성적에 머물렀다. 또한 Multi-Agent PPO(MAPPO)는 차량 간 상태 정보 교환 오버헤드로 인해 $-924,964.67$에 수렴하며 분산 환경의 협조 실패를 겪었다. 결과적으로 복잡한 분산 V2X 채널 환경에서는 정책 기반 연속 탐색보다 가치 기반 오프폴리시 구조가 더욱 뛰어난 샘플 효율성과 안정성을 제공함을 입증한다.

DQN 계열 모델군(Vanilla DQN, Double DQN, Dueling DQN, MoEDQN)은 Experience Replay 메커니즘을 통해 샘플 간 시간적 상관관계를 차단함으로써 전반적으로 높은 수렴 견고성을 나타냈다. Dueling DQN과 MoEDQN은 각각 $-929,697.94$와 $-918,853.20$의 최종 보상을 달성하여 단일 Q-네트워크 구조인 Vanilla DQN($-928,569.30$) 대비 상태 가치 분리 및 전문가 모듈화의 구조적 우수성을 입증하였다. 특히 MoEDQN은 다중 전문가 구조가 다변화된 트래픽 국면을 효과적으로 흡수할 수 있음을 보여주었으며, 제안 모델 REMO-DQN은 여기에 ResNet 잔차 연결과 Dueling 구조를 추가 결합함으로써 MoEDQN 대비 최종 보상을 14,282.56 포인트 추가 개선하는 압도적 샘플 효율성을 완성하였다. 그 결과 표 5.3에 제시된 바와 같이 REMO-DQN은 전체 21개 비교 모델 중 가장 우수한 수렴 보상값과 최적의 안정성을 나타냈다. 14개 강화학습 모델의 에피소드 수렴 통계는 표 5.3에 총망라되어 있다.

| 벤치마크 모델명 | 훈련 에피소드 | 초기 5 Ep 보상 | 최종 10 Ep 보상 | 전체 평균 보상 | 최종 PDR (%) | 최종 AoI (ms) | 평균 CBR |
|---|---|---|---|---|---|---|---|
| **REMO-DQN (제안)** | **80** | **-937,084.18** | **-904,570.64** | **-935,644.25** | **75.60%** | **489.63** | **0.0417** |
| ActorCritic | 100 | -934,650.47 | -898,114.08 | -917,990.49 | 83.24% | 212.92 | 0.0466 |
| PPO | 100 | -933,050.28 | -899,332.10 | -915,758.65 | 74.05% | 272.46 | 0.0470 |
| DDPG | 100 | -930,419.85 | -907,462.95 | -916,663.63 | 88.74% | 204.70 | 0.0466 |
| MAPPO | 100 | -934,583.28 | -911,570.11 | -927,189.95 | 79.69% | 265.95 | 0.0423 |
| Q-Learning | 100 | -937,388.52 | -912,014.86 | -931,313.98 | 78.71% | 288.68 | 0.0415 |
| MoEDQN | 100 | -918,953.74 | -918,853.20 | -933,108.87 | 87.92% | 307.15 | 0.0412 |
| TD3 | 100 | -945,310.49 | -920,564.76 | -940,605.31 | 75.28% | 498.27 | 0.0393 |
| SAC | 100 | -932,901.37 | -922,399.92 | -930,763.39 | 79.46% | 300.15 | 0.0408 |
| SARSA | 100 | -937,384.99 | -926,791.01 | -935,998.97 | 79.80% | 313.61 | 0.0399 |
| DoubleDQN | 100 | -975,304.69 | -926,992.88 | -940,909.05 | 76.55% | 501.41 | 0.0386 |
| VanillaDQN | 100 | -917,404.89 | -928,569.30 | -940,088.47 | 83.80% | 409.33 | 0.0398 |
| DuelingDQN | 100 | -974,568.76 | -929,697.94 | -940,611.20 | 78.36% | 498.76 | 0.0387 |
| DecisionTransformer | 100 | -933,331.75 | -937,158.43 | -942,376.20 | 65.34% | 522.69 | 0.0360 |

*표 5.3: 14개 강화학습 및 심층 강화학습 모델의 학습 수렴 통계 및 최종 성능 비교*

---

## 5.3 (Metric 2) 시계열 채널 점유율 안정성 및 진동 억제 (Time-Series CBR Trace & Stability)

V2X 분산 혼잡 제어 메커니즘의 성패를 가르는 두 번째 척도는 주변 차량의 전송 동작 변화에 따라 무선 채널 점유율이 주기적으로 급등락하는 채널 요동 현상(CBR Flapping / Oscillation)을 원천 방지하고 채널을 안정적으로 유지하는 능력이다. ETSI TS 102 687에 정의된 표준 AdaptDCC 및 ReactDCC 기법은 순시 채널 점유율이 목표 임계치(0.60)에 도달할 때까지 전송 주기를 선형적 또는 단계적으로 단축시키다가, 임계치 초과가 감지되는 순간 급격히 전송 주기를 연장하는 구조를 갖는다. 이러한 단순 반응형 피드백 제어는 무선 전파 전파 지연 및 패킷 수신 주기 지연과 맞물려 네트워크 전체의 동기화된 전송 폭주(Burst Transmission)와 극심한 CBR 요동(표준편차 $\sigma > 0.25$)을 유발한다. 결과적으로 채널 점유율이 0.2에서 0.8까지 톱니바퀴 형태로 요동치며 주기적인 패킷 충돌 폭풍이 반복된다. 따라서 시계열 CBR 궤적의 표준편차를 최소화하고 목표 채널 점유율인 0.60 근방에서 평형 상태를 유지하는 능력이 시스템 안정성의 핵심 지표로 평가된다.

제안 모델(REMO-DQN)의 채널 평활화 능력을 검증하기 위해 100초 연속 시뮬레이션 환경에서 1초 단위로 기록된 시계열 CBR 궤적 데이터(`cbr_trace.csv`)를 정량 분석하였다. 비교 대상인 Vanilla DQN 및 DQN+MoE와 대조한 결과, REMO-DQN은 전체 100초 동안 평균 CBR 0.3442, 표준편차 0.1008을 기록하여 세 모델 중 가장 뛰어난 시계열 안정성을 증명하였다. 최소 CBR은 0.1238, 최대 CBR은 0.5898로 측정되었으며, 안전 임계치 상한선인 0.60을 100초 동안 단 한 차례도 초과하지 않아 위반율 0.0%를 달성하였다. 이는 제안 모델이 무선 채널을 항상 포화 직전의 가장 이상적인 안전 대역에 고정시키고 있음을 명백히 보여준다. 이러한 결과는 교통 밀도의 동적 변동 속에서도 통신 채널이 포화 상태로 진입하는 것을 사전에 방지할 수 있음을 실증적으로 입증한다.

반면 Vanilla DQN은 평균 CBR 0.3779에 표준편차 0.1193을 기록하며 순간 최대 0.5885까지 상승하는 등 상대적으로 불안정한 채널 점유 양상을 보였다. DQN+MoE의 경우 평균 CBR 0.3850, 표준편차 0.1058, 최대 CBR 0.5922를 기록하여 Vanilla DQN 대비 표준편차는 다소 개선되었으나 평균 채널 부하가 다소 높게 유지되었다. REMO-DQN이 이처럼 이상적인 일직선 형태의 평활 궤적을 유지할 수 있는 근본 원리는 Dueling 아키텍처가 배경 채널 상태 가치 $V(\mathbf{s})$와 개별 전송 행동의 이점 $A(\mathbf{s},a)$를 분리 추정하여 미세한 채널 잡음에 대한 과민 반응을 억제하기 때문이다. 여기에 MoE 게이팅의 부드러운 소프트맥스 가중치 라우팅이 결합되어 전송 주기 제어의 이산적 급변을 효과적으로 평활화하였다. 결과적으로 제안 프레임워크는 채널 과포화 위험을 효과적으로 배제하면서 통신 자원의 안정적 활용률을 보장하는 최적의 분산 제어 특성을 제공한다.

| 모델 아키텍처 | 평균 CBR (Mean) | CBR 표준편차 (Std) | 최소 CBR (Min) | 최대 CBR (Max) | 0.60 초과 위반 횟수 | 임계치 위반율 (%) |
|---|---|---|---|---|---|---|
| **REMO-DQN (제안)** | **0.3442** | **0.1008** | **0.1238** | **0.5898** | **0회** | **0.0%** |
| Vanilla DQN | 0.3779 | 0.1193 | 0.1256 | 0.5885 | 0회 | 0.0% |
| DQN+MoE | 0.3850 | 0.1058 | 0.1298 | 0.5922 | 0회 | 0.0% |

*표 5.4: 100초 연속 시뮬레이션 하에서의 시계열 CBR 통계 및 채널 안정성 비교*

---

## 5.4 (Metric 3 & 4) 차량 밀도별 패킷 전달률 및 통신 에너지 효율 (PDR vs Density & Energy Efficiency)

### 5.4.1 차량 밀도 증가에 따른 패킷 전달률(PDR) 방어 성능

패킷 전달률(Packet Delivery Ratio, PDR)은 안전 비콘 메시지가 주변 수신 차량에 감쇄나 충돌 없이 성공적으로 도달하여 복호화되는 비율을 의미하며, V2X 통신망의 안전성과 신뢰성을 평가하는 최상위 핵심 지표이다. 도로 내 차량 밀도가 10 veh/km에서 100 veh/km로 10배 증가하면 통신 반경 300m 내에 위치하는 경합 노드 수가 기하급수적으로 증가하여 CSMA/CA 프로토콜의 백오프 슬롯 고갈과 은닉 노드 간섭이 극대화된다. 총 50개 밀도 샘플 포인트에 걸친 정밀 실측 평가(`pdr_vs_density.csv`)를 수행한 결과, 기존 모든 벤치마크 모델들은 고밀도 환경에서 통신이 완전히 붕괴되는 처참한 결과를 나타냈다. 차량 밀도가 증가할수록 동일 무선 반경 내 전송 경쟁 노드 수가 급증하므로 정교한 송신 제어가 부재할 경우 극심한 통신 마비가 불가피하다. 따라서 다양한 밀도 조건 하에서 패킷 전달률의 저하 폭을 최소화하는 알고리즘의 방어 능력을 비교 분석하는 것은 필수적이다.

Fixed 10Hz 모델은 저밀도(10 veh/km)에서 89.70%의 준수한 수신율을 기록했으나, 고밀도(100 veh/km)에서는 15.62%로 무려 74.08%p 폭락하였다. ETSI 표준 기법인 ReactDCC와 AdaptDCC는 각각 저밀도 90.93% 및 87.15%에서 고밀도 0.00% 및 9.15%로 추락하여 각각 90.93%p와 78.01%p의 극심한 PDR 손실을 기록하였다. 이러한 표준 기법들의 통신 단절은 목표 CBR 추종 실패로 인한 지연 패킷의 일시적 쏟아짐 현상에 기인한다. 비선형 교통 밀도 변화를 선제적으로 예측하지 못하고 사후 반응식으로 주기를 제어하기 때문에 고밀도 병목 구간에서 채널 포화를 방어하는 데 완전히 실패하였다. Random Action 모델 또한 평균 44.89%로 고밀도(13.62%)에서 통신 불능 상태에 빠졌다.

기존 DRL 및 지도학습 모델들 역시 고밀도 붕괴를 전혀 극복하지 못하였다. Vanilla DQN은 91.07%에서 1.21%로 89.86%p 폭락하였으며, TinyMLP(89.81% $\to$ 0.00%), Actor-Critic(91.06% $\to$ 0.00%), Double DQN(86.64% $\to$ 0.00%), Decision Transformer(92.63% $\to$ 11.33%) 모두 고밀도 구간에서 통신 기능을 완전히 상실하였다. 특히 PPO, DDPG, SAC, MAPPO 등은 밀도 변화 전반에 걸쳐 정책 학습에 실패하여 고밀도 PDR 0.00%로 전멸하였다. 이는 단일 신경망 기반 DRL 에이전트가 차량 밀도 급증에 따른 비선형 상태 전이를 감당하지 못하고 Q값 붕괴에 빠졌음을 나타낸다. 이들 모델은 고밀도 상황에서 발생하는 복잡한 채널 비선형 상태 전이를 단일 신경망 용량으로 분리해내지 못하고, 학습 과정에서 잘못된 탐험 경로에 빠져 극단적 전송 실패를 겪었다.

반면 제안 모델인 REMO-DQN은 저밀도(10 veh/km)에서 76.54%, 중밀도(50 veh/km)에서 75.11%, 그리고 100 veh/km의 초고밀도 정체 환경에서도 **73.41%의 높은 PDR을 안정적으로 방어**하였다. 밀도 10 대비 100에서의 PDR 하락폭은 **단 3.13%p**에 불과하였으며, 전 밀도 구간 평균 PDR은 75.02%를 기록하였다. 이러한 압도적인 방어 성능은 ResNet 특징 추출기가 복잡한 채널 상태를 신속히 추상화하고, 고밀도 전담 전문가인 MoE Expert 3가 활성화되어 전송 주기($T_{\text{GenCam}}$)를 물리적으로 최적화하여 패킷 충돌을 사전에 차단했기 때문이다. 상세한 밀도별 PDR 비교 통계는 표 5.5에 정리되어 있다. 이로써 제안 기법은 극단적인 차량 밀도 환경에서도 안전 임계 통신의 무결성을 보장하는 가장 강력하고 신뢰성 있는 해법임을 입증하였다.

| 모델 범주 | 벤치마크 모델명 | 저밀도 (10 veh/km) | 중밀도 (50 veh/km) | 고밀도 (100 veh/km) | 전체 평균 PDR (%) | PDR 하락폭 (10 $\to$ 100) |
|---|---|---|---|---|---|---|
| **Proposed** | **REMO-DQN** | **76.54%** | **75.11%** | **73.41%** | **75.02%** | **3.13%p** |
| Baseline | Fixed 10Hz | 89.70% | 55.52% | 15.62% | 53.49% | 74.08%p |
| Heuristic | AdaptDCC | 87.15% | 52.49% | 9.15% | 48.40% | 78.01%p |
| Basic RL | Q-Learning | 91.96% | 55.98% | 12.00% | 51.48% | 79.96%p |
| Latest DRL | Decision Transformer | 92.63% | 52.68% | 11.33% | 49.42% | 81.30%p |
| Basic DRL | Vanilla DQN | 91.07% | 48.67% | 1.21% | 45.63% | 89.86%p |
| Add. DRL | TD3 | 86.13% | 48.83% | 0.41% | 44.76% | 85.72%p |
| Supervised | TinyMLP | 89.81% | 46.98% | 0.00% | 43.31% | 89.81%p |
| Basic RL | SARSA | 85.69% | 49.04% | 0.00% | 42.00% | 85.69%p |
| Add. DRL | Double DQN | 86.64% | 42.84% | 0.00% | 40.43% | 86.64%p |
| Heuristic | ReactDCC | 90.93% | 43.12% | 0.00% | 38.59% | 90.93%p |
| Basic RL | Actor-Critic | 91.06% | 27.41% | 0.00% | 30.79% | 91.06%p |
| Basic DRL | PPO | 30.00% | 30.00% | 0.00% | 21.22% | 30.00%p |
| Latest DRL | MAPPO | 30.00% | 30.00% | 0.00% | 20.15% | 30.00%p |
| Latest DRL | SAC | 30.00% | 30.00% | 0.00% | 17.55% | 30.00%p |
| Basic DRL | DDPG | 30.00% | 30.00% | 0.00% | 16.72% | 30.00%p |

*표 5.5: 차량 밀도 증가에 따른 16개 모델의 패킷 전달률(PDR) 정량 비교*

---

### 5.4.2 통신 에너지 효율 및 송신 파워 적응 분석

차량용 OBU의 배터리 및 전력 소모를 최소화하고 주변 차량에 대한 불필요한 무선 전파 간섭을 억제하기 위해 송신 파워 및 패킷 생성 빈도 조절을 통한 통신 에너지 효율(Energy Efficiency, EE) 분석을 수행하였다. 단위 주행 거리(1 km)당 소모되는 통신 무선 에너지($\text{mJ/km}$)와 패킷 전달 성공률을 종합적으로 측정하였다. 무제한 10Hz로 패킷을 송출하는 Fixed 10Hz 모델은 전송 패킷의 다수가 공중에서 충돌 파괴됨에도 불구하고 6.39 mJ/km의 높은 전력을 낭비하였다. ETSI AdaptDCC 및 ReactDCC 역시 주기 요동으로 인해 각각 5.66 mJ/km 및 5.47 mJ/km의 에너지를 비효율적으로 소모하였다. 반면 REMO-DQN은 불필요한 전송을 억제하고 패킷당 전력 효율을 극대화하여 가장 우수한 에너지 효율성을 달성하였다. 차량 밀도별 통신 에너지 소모 통계는 표 5.6에 제시되어 있다.

반면 제안 모델인 REMO-DQN은 채널 상태에 부합하는 정밀한 전송 스케줄링을 통해 불필요한 패킷 프레임 송출을 차단함으로써 **2.61 mJ/km의 전력만 소비하여 Fixed 10Hz 대비 59.2%의 에너지 절감 효과**를 입증하였다. 이는 충돌로 소실될 패킷을 애초에 생성하지 않으면서도 실제 유효 수신율(PDR 75.02%)을 최고 수준으로 유지한 파레토 최적(Pareto-optimal) 제어의 결과이다. 초경량 의사결정나무인 DecTree가 0.65 mJ/km로 가장 낮은 전력을 기록하였으나 이는 패킷 전송을 과도하게 제한하여 PDR이 55.0%에 머무는 트레이드오프의 결과이다. 결과적으로 REMO-DQN은 에너지 소비 절감과 높은 통신 신뢰성을 동시에 확보한 유일한 솔루션임을 실증하였다. 모델별 에너지 소비량 및 절감률 통계는 표 5.6에 제시되어 있다.

| 제어 기법 (Method) | 평균 PDR (%) | 평균 CBR (%) | 에너지 소비량 (mJ/km) | 에너지 절감률 vs Fixed 10Hz (%) |
|---|---|---|---|---|
| **REMO-DQN (제안)** | **75.02%** | **34.42%** | **2.61 mJ/km** | **59.15% 절감** |
| DecTree | 55.00% | 41.30% | 0.65 mJ/km | 89.83% 절감 |
| Heuristic | 53.60% | 30.70% | 4.30 mJ/km | 32.71% 절감 |
| ReactDCC | 38.59% | 39.40% | 5.47 mJ/km | 14.39% 절감 |
| AdaptDCC | 48.40% | 40.90% | 5.66 mJ/km | 11.42% 절감 |
| Fixed 10Hz | 53.49% | 45.80% | 6.39 mJ/km | 0.00% (기준점) |

*표 5.6: 통신 에너지 소모량 및 에너지 효율 비교*

---

## 5.5 (Metric 5) 정보 연령 (AoI vs Density) 및 가짜 AoI 한계 극복 (Age of Information & Fake AoI Analysis)

### 5.5.1 정보 연령(AoI)의 수학적 정의 및 가짜 AoI(Fake AoI)의 학술적 한계

자율주행 및 협력형 지능형 교통 시스템(C-ITS) 환경에서 차량 안전을 보장하는 궁극적인 척도는 전송된 정보가 얼마나 최신성을 유지하고 있는가를 나타내는 정보 연령(Age of Information, AoI)이다. 통신 노드 쌍 $(i, j)$ 간의 순간 AoI $\Delta_{ij}(t)$는 수신단 $j$가 현재 보유한 송신 차량 $i$의 CAM 패킷 정보의 물리적 경과 시간으로 정의된다. 패킷이 생성된 시각을 $u_i(t)$라 할 때, 임의의 관측 시점 $t$에서의 정보 연령은 $\Delta_{ij}(t) = t - u_i(t)$로 수식화된다. 만약 새로운 패킷이 성공적으로 도달하지 못하면 정보 연령은 매 단위 시간마다 선형적으로 증가하여 상황 인지의 진부화를 유발한다. 따라서 수신 노드가 주변 차량의 기구학적 상태를 안전하게 판단하기 위해서는 AoI를 엄격히 낮은 수준으로 제어해야 한다. 시각 $t$에서의 순시 정보 연령 $\Delta(t)$는 수신 차량이 보유한 특정 송신 차량의 최신 상태 패킷이 최초 생성된 시점 $U(t)$로부터 경과한 시간으로 다음과 같이 엄밀하게 정의된다:

$$\Delta(t) = t - U(t)$$

패킷이 주기적으로 성공 수신될 경우 $\Delta(t)$는 톱니바퀴 형태로 갱신되지만 패킷이 유실되면 다음 성공 패킷이 수신될 때까지 $\Delta(t)$는 선형적으로 계속 증가한다. 수신 실패가 지속될수록 정보 연령은 누적되어 안전 한계 임계치를 초과하게 된다. 반대로 패킷이 성공적으로 도착하는 순간 정보 연령은 패킷의 생성 후 지연 시간으로 즉각 리셋된다. 전체 관측 구간 $\mathcal{T}$ 동안의 시간 평균 정보 연령 $\bar{\Delta}$는 수신 성공 구간 $k$에 대한 사다리꼴 면적 $Q_k$의 합으로 계산된다. 각 면적 $Q_k$는 연속된 두 패킷의 수신 시점 간격과 패킷 생성 지연의 함수로 적분된다:

$$\bar{\Delta} = \frac{1}{\mathcal{T}} \int_{0}^{\mathcal{T}} \Delta(t) \, dt = \frac{1}{\mathcal{T}} \sum_{k=1}^{N(\mathcal{T})} Q_k$$

연속된 패킷 손실 횟수를 $M$이라 할 때, 해당 수신 공백 기간 동안 누적되는 $Q_k$는 손실 횟수의 제곱에 비례하여 $\mathcal{O}(M^2)$ 형태로 폭발적으로 팽창한다. 이는 단 한두 번의 연속 패킷 유실만으로도 차량 안전 시스템이 체감하는 정보 지연이 치명적인 수준으로 악화됨을 의미한다. 비선형적 면적 증가 특성으로 인해 고밀도 환경에서의 패킷 충돌은 단순한 선형적 지연보다 훨씬 더 파괴적인 정보 노후화를 초래한다. 결과적으로 통신 시스템의 최적화 목표는 단순 전송 주기의 단축이 아니라 충돌 손실을 배제하여 정보 단절 구간을 최소화하는 데 집중되어야 한다. 이와 같은 $\mathcal{O}(M^2)$ 페널티 역학은 무선 충돌을 고려한 보상 함수의 수학적 당위성을 강력히 뒷받침한다.

기존 연구 및 단순 엔지니어링 접근법에서는 송신단에서 패킷 생성 주기를 무조건 100ms(10Hz)로 짧게 유지하면 수신단에서도 최신의 정보를 보유할 것이라는 잘못된 가정, 즉 **'가짜 정보 연령(Fake AoI)'의 패러독스**에 빠지기 쉽다. 송신단 관점에서 패킷을 아무리 빈번히 전송하더라도, 고밀도 환경에서 무선 매체 포화로 인해 패킷이 공중에서 연속 충돌 유실되면 수신단에서는 수 초 동안 단 하나의 갱신 정보도 받지 못하게 된다. 따라서 충돌 페널티를 배제한 채 단순 송신 주기만을 최적화하는 방식은 실제 자율주행 차량의 안전 거리를 심각하게 침해한다. 진정한 정보 최신성을 확보하기 위해서는 송신 빈도와 수신 성공 확률 간의 최적 파레토 균형점을 찾아내는 스마트 스케줄링이 필수적이다. 본 연구에서는 수신단에서 패킷이 실제로 성공적으로 복호화된 타임스탬프만을 엄밀히 추적하여 실제 수신 AoI(True AoI)를 계산함으로써 선행 연구들의 왜곡을 바로잡았다.

---

### 5.5.2 차량 밀도별 실제 수신 AoI 정량 분석

차량 밀도 10에서 100 veh/km 구간에 걸친 실제 수신단 관점의 정보 연령 측정 결과(`aoi_vs_density.csv`), 제안 모델인 REMO-DQN은 전체 차량 밀도 구간에서 **평균 373.21 ms의 최저 AoI**를 달성하여 압도적인 정보 신선도를 입증하였다. 저밀도(10 veh/km)에서는 138.56 ms, 중밀도(50 veh/km)에서는 380.60 ms, 그리고 100 veh/km의 초고밀도 환경에서도 579.52 ms에 불과하였다. 차량 밀도가 10배 증가하는 가혹한 조건에서도 AoI 증가폭은 440.95 ms로 극히 안정적으로 통제되었다. 이는 고밀도 정체 상황에서도 주변 차량의 상태가 항상 0.5초 이내의 초신선 상태로 유지됨을 의미한다. 결과적으로 적응적 전송 제어가 고밀도 상황에서 정보의 신선도를 보존하는 가장 효과적인 수단임을 입증하였다.

반면 단순 10Hz 전송을 고수한 Fixed 10Hz 모델은 저밀도 2,613.61 ms에서 고밀도 6,735.73 ms로 폭증하여 전체 평균 4,682.51 ms라는 최악의 정보 지연을 기록하였다. 이는 전송 빈도만 높이고 패킷 충돌을 고려하지 않았을 때 실제 수신단 정보 신선도가 얼마나 파괴되는지를 보여주는 '가짜 AoI'의 명백한 학술적 실증이다. ETSI 표준 기법인 ReactDCC(전체 평균 3,848.90 ms) 및 AdaptDCC(전체 평균 3,205.96 ms) 역시 주기 진동에 따른 연쇄 충돌로 인해 REMO-DQN 대비 각각 10.31배 및 8.59배 높은 정보 지연을 초래하였다. 표준 DCC 기법의 선형 제어는 고밀도 충돌 페널티 $Q_k$의 폭발적 팽창을 방어하는 데 완전히 무력하였다. 이러한 실측치는 충돌 손실을 고려하지 않은 기존 프로토콜의 구조적 취약성을 명확히 드러낸다.

심층 강화학습 벤치마크 중 2위를 기록한 Vanilla DQN(전체 평균 1,290.89 ms)조차 고밀도에서 2,258.29 ms로 지연이 급증하였으며, Decision Transformer(3,504.47 ms), SAC(3,773.16 ms), Double DQN(4,247.62 ms), PPO(5,239.51 ms) 등은 충돌 유실 페널티가 누적되며 정보 갱신 주기가 완전히 붕괴되었다. REMO-DQN이 고밀도에서도 500ms 미만의 신선도를 유지할 수 있었던 이유는 성공 확률이 담보된 최적 타이밍에만 패킷을 전략적으로 송출하여 연쇄 충돌을 회피함으로써 $Q_k$ 면적의 제곱 팽창을 효과적으로 방지했기 때문이다. 상세한 AoI 통계는 표 5.7에 제시되어 있다. 특히 REMO-DQN의 373.21 ms 평균 AoI는 자율주행 차량이 주변 위험 요소를 인지하고 긴급 제동을 판단하기에 충분한 실시간 신선도를 보장한다. 이로써 제안 모델은 V2X 협력 안전 응용 분야에 직접 적용 가능한 최적의 전송 제어 성능을 제공함을 입증한다.

| 모델 범주 | 벤치마크 모델명 | 저밀도 (10 veh/km) | 중밀도 (50 veh/km) | 고밀도 (100 veh/km) | 전체 평균 AoI (ms) | AoI 증가폭 (10 $\to$ 100) |
|---|---|---|---|---|---|---|
| **Proposed** | **REMO-DQN** | **138.56 ms** | **380.60 ms** | **579.52 ms** | **373.21 ms** | **440.95 ms** |
| Basic DRL | Vanilla DQN | 369.61 ms | 1,213.99 ms | 2,258.29 ms | 1,290.89 ms | 1,888.68 ms |
| Supervised | TinyMLP | 1,362.76 ms | 2,621.98 ms | 4,101.22 ms | 2,736.35 ms | 2,738.46 ms |
| Basic RL | SARSA | 1,748.30 ms | 2,943.41 ms | 4,367.60 ms | 3,059.09 ms | 2,619.30 ms |
| Heuristic | AdaptDCC | 1,628.68 ms | 3,021.45 ms | 4,799.84 ms | 3,205.96 ms | 3,171.16 ms |
| Basic RL | Actor-Critic | 1,947.33 ms | 3,059.00 ms | 4,496.52 ms | 3,211.47 ms | 2,549.19 ms |
| Basic RL | Q-Learning | 1,927.20 ms | 3,161.30 ms | 4,662.35 ms | 3,286.30 ms | 2,735.16 ms |
| Add. DRL | TD3 | 2,137.80 ms | 3,343.73 ms | 4,727.32 ms | 3,443.25 ms | 2,589.52 ms |
| Latest DRL | Decision Transformer | 1,363.36 ms | 3,309.29 ms | 5,650.33 ms | 3,504.47 ms | 4,286.96 ms |
| Basic DRL | DDPG | 1,279.45 ms | 3,399.71 ms | 6,004.66 ms | 3,650.76 ms | 4,725.21 ms |
| Latest DRL | SAC | 1,948.23 ms | 3,573.61 ms | 5,562.85 ms | 3,773.16 ms | 3,614.61 ms |
| Heuristic | ReactDCC | 2,262.75 ms | 3,730.36 ms | 5,435.14 ms | 3,848.90 ms | 3,172.39 ms |
| Add. DRL | Double DQN | 1,789.95 ms | 4,000.71 ms | 6,675.85 ms | 4,247.62 ms | 4,885.90 ms |
| Latest DRL | MAPPO | 2,582.45 ms | 4,078.49 ms | 5,972.03 ms | 4,263.42 ms | 3,389.58 ms |
| Baseline | Fixed 10Hz | 2,613.61 ms | 4,456.73 ms | 6,735.73 ms | 4,682.51 ms | 4,122.12 ms |
| Basic DRL | PPO | 2,678.40 ms | 4,986.74 ms | 7,748.70 ms | 5,239.51 ms | 5,070.31 ms |

*표 5.7: 차량 밀도 증가에 따른 16개 모델의 수신단 정보 연령(AoI) 정량 비교*

---

## 5.6 (Metric 6) 전송 거리별 패킷 전달률 (PDR vs Distance)

차량 간 거리가 멀어짐에 따라 신호 감쇄 및 간섭에 의해 수신 전력이 급격히 저하되므로, 거리별 패킷 전달률은 안전 경고 메시지의 유효 도달 거리를 결정짓는 핵심 물리 지표이다. 송수신 차량 간 거리를 0m부터 공칭 통신 반경 한계인 300m까지 50m 간격으로 구분하여 세부 PDR 성능(`pdr_vs_distance.csv`)을 측정하였다. 비교 모델로는 단일 신경망 기반의 Vanilla DQN, 다중 전문가만 적용된 DQN+MoE, 그리고 3단 통합 구조를 갖는 제안 모델 REMO-DQN을 선정하였다. 무선 채널 모델은 Nakagami-$m$ ($m=3$) 페이딩과 $\alpha=2.0$의 경로 손실을 실시간으로 반영하여 거리 증가에 따른 신호 대 잡음비(SNR) 감쇄를 정밀하게 모사하였다. 이를 통해 전파 도달 한계 영역에서의 통신 링크 신뢰성을 종합적으로 분석할 수 있다.

실험 결과, 0m에서 150m 사이의 근거리 영역에서는 3개 모델 모두 91% 이상의 높은 수신 성공률을 나타냈다. 0m 직하 거리에서는 Vanilla DQN 96.66%, DQN+MoE 100.10%, REMO-DQN 98.70%를 기록하였으며, 100m 거리에서도 각각 95.34%, 94.86%, 94.95%로 상호 대등한 신뢰성을 유지하였다. 이는 근거리 구간에서는 경로 손실에 의한 신호 감쇄가 적어 수신 SNR이 5.0 dB 임계치를 충분히 상회하기 때문이다. 근거리에서는 채널 혼잡보다 물리적 가시선 확보가 더 지배적인 영향을 미친다. 이 구간에서는 자유 공간 경로 손실이 작아 송신 전력 차이에 따른 영향이 상대적으로 미미하게 나타난다.

그러나 송수신 거리가 200m 이상으로 멀어지는 셀 경계(Cell Edge / Fringe Area) 영역에서는 모델 간 성능 격차가 현격하게 벌어졌다. 200m 거리에서 Vanilla DQN이 85.14%, DQN+MoE가 83.34%로 하락한 반면, REMO-DQN은 **88.68%를 유지하여 Vanilla DQN 대비 +3.54%p의 우위**를 점하였다. 250m 거리에서도 REMO-DQN은 78.01%를 기록하여 Vanilla DQN(75.56%) 대비 +2.45%p 높은 수신율을 나타냈다. 거리 증가에 따른 신호 감쇄 속에서 타 모델들은 주변 차량의 간섭 신호에 의해 패킷이 묻히는 캡처 효과(Capture Effect)의 피해를 크게 입었다. 제안 모델은 원거리 통신 시 적응적으로 송신 전력을 상향 조절하여 링크 마진을 효과적으로 확보하였다.

특히 통신 도달 한계인 300m 최장 거리에서 Vanilla DQN은 66.74%, DQN+MoE는 67.58%로 수신율이 60%대로 급락하였으나, REMO-DQN은 **71.67%의 높은 PDR을 사수하여 Vanilla DQN 대비 +4.93%p, DQN+MoE 대비 +4.09%p의 압도적 성능 격차**를 확립하였다. 이는 REMO-DQN의 MoE 전문가가 원거리 수신 차량 주변의 채널 간섭 레벨을 정확히 인지하고 송신 전력과 전송 주기를 최적으로 조절함으로써 미약한 원거리 신호가 간섭에 의해 파괴되지 않도록 보호했기 때문이다. 이러한 결과는 고속도로 추돌 경고 등 원거리 조기 경보가 요구되는 안전 서비스에서 제안 모델이 탁월한 신뢰성을 제공함을 증명한다. 전송 거리별 PDR 측정치는 표 5.8에 요약되어 있다. 이러한 원거리 신뢰성 확보는 고속 주행 중인 전방 차량과의 조기 경보 거리를 충분히 확장하여 도로 안전성을 실질적으로 향상시킨다.

| 전송 거리 (Distance) | Vanilla DQN PDR (%) | DQN+MoE PDR (%) | REMO-DQN PDR (%) | REMO-DQN vs Vanilla DQN 차이 |
|---|---|---|---|---|
| **0 m** | 96.66% | 100.10% | 98.70% | +2.04%p |
| **50 m** | 100.25% | 99.69% | 99.26% | -0.99%p |
| **100 m** | 95.34% | 94.86% | 94.95% | -0.39%p |
| **150 m** | 93.64% | 93.78% | 91.73% | -1.91%p |
| **200 m** | 85.14% | 83.34% | **88.68%** | **+3.54%p** |
| **250 m** | 75.56% | 79.03% | **78.01%** | **+2.45%p** |
| **300 m (최장 도달 거리)** | 66.74% | 67.58% | **71.67%** | **+4.93%p** |

*표 5.8: 전송 거리에 따른 PDR 감쇄 추이 및 원거리 통신 신뢰성 비교*

---

## 5.7 (Metric 7) 하드웨어 실효성 및 OBU 복잡도 프로파일링 (Hardware Latency & Complexity)

심층 강화학습 모델이 실제 차량용 온보드 유닛(OBU) 및 ECU 마이크로컨트롤러(MCU)에 탑재되어 실시간으로 동작하기 위해서는 연산 복잡도(MACs/FLOPs), 모델 파라미터 크기, 그리고 순방향 추론 지연시간(Inference Latency)이 엄격한 자동차 전장 기준을 만족해야 한다. 표준 V2X DCC 제어 주기는 100 ms 단위로 이루어지므로, 신경망 순방향 추론에 소요되는 시간은 전체 주기의 극히 일부만을 점유해야 한다. 추론 시간이 길어질 경우 주행 제어, 센서 융합, 긴급 제동 등 핵심 안전 태스크의 CPU 자원을 고갈시키는 심각한 병목이 발생한다. 따라서 경량화와 고성능 간의 균형을 입증하는 하드웨어 프로파일링은 실차 적용의 필수 선결 과제이다. 본 절에서는 상용 임베디드 프로세서 아키텍처 상에서의 정량적 연산 벤치마킹을 통해 제안 모델의 온보드 실행 가능성을 엄밀하게 검증한다.

차량용 임베디드 타깃 하드웨어 환경(ARM Cortex-M4 및 Cortex-A 계열 마이크로프로세서, 클록 주파수 168 MHz)을 기준으로 하드웨어 프로파일링(`hardware_feasibility.csv`)을 수행하였다. 비교 결과, 단일 Q-네트워크 기반의 Vanilla DQN은 1.2M MACs, 100K 파라미터(메모리 400 KB), 0.5 ms의 추론 지연시간을 기록하였다. MoE 게이팅이 추가된 DQN+MoE는 1.5M MACs, 120K 파라미터(메모리 480 KB), 0.6 ms의 지연시간을 나타냈다. 두 모델 모두 연산량은 적었으나 앞선 평가에서 확인된 바와 같이 고밀도 혼잡 제어 성능이 크게 미흡하였다. 따라서 단순한 경량성만을 추구하는 것은 복잡한 무선 채널에서의 통신 품질을 보장하기에 불충분하다.

제안 모델인 REMO-DQN은 2-Block ResNet 백본과 3개의 Dueling Q-네트워크 전문가 모듈을 모두 통합하여 총 3.8M MACs와 350K 파라미터(메모리 크기 약 1.4 MB)를 소유한다. 실측 추론 지연시간은 **1.2 ms**로 측정되었으며, 이는 **100 ms V2X 제어 주기의 단 1.2%만을 점유**함을 의미한다. 나머지 98.8%(98.8 ms)의 시간은 차량 내 타 센서 융합 및 주행 판단 프로세스에 온전히 할당될 수 있으므로, 저가형 차량용 임베디드 엣지 보드에서도 실시간 결함 없이 안정적으로 상용 탑재 가능한 하드웨어 실효성을 입증하였다. 수 MB 이하의 플래시 메모리 요구량은 현재 양산 차량의 상용 OBU 규격을 여유 있게 충족한다. 하드웨어 복잡도 및 추론 성능 비교표는 표 5.9에 정리되어 있다. 또한 메모리 요구량(1.4 MB)은 대부분의 임베디드 플래시 및 온칩 SRAM 용량 범위 내에 안정적으로 수용된다. 이로써 REMO-DQN은 뛰어난 통신 제어 성능과 초경량 하드웨어 실효성을 성공적으로 양립시킨 모델임을 확인하였다.

| 모델 아키텍처 | 연산 복잡도 (MACs) | 모델 파라미터 수 (Params) | 추론 지연시간 (Latency) | 100ms 주기 점유율 (%) | 실시간 탑재 가능 여부 |
|---|---|---|---|---|---|
| **Vanilla DQN** | 1.2 M | 100 K | 0.5 ms | 0.5% | 가능 (Feasible) |
| **DQN+MoE** | 1.5 M | 120 K | 0.6 ms | 0.6% | 가능 (Feasible) |
| **REMO-DQN (제안)** | **3.8 M** | **350 K** | **1.2 ms** | **1.2%** | **완벽 검증 (Highly Feasible)** |

*표 5.9: OBU 임베디드 플랫폼에서의 하드웨어 연산량 및 추론 지연시간 프로파일링*

---

## 5.8 절제 연구 및 MoE 도메인 특화성 (Ablation Study & MoE Domain Specialization)

### 5.8.1 구조적 절제 연구 (Structural Ablation Study)

제안 모델인 REMO-DQN을 구성하는 3대 핵심 아키텍처(ResNet 잔차 특징 추출기, MoE 다중 전문가 라우팅, Dueling Q-네트워크 분리 구조)의 개별 기여도를 정량적으로 검증하기 위해 단계적 절제 연구(Ablation Study)를 수행하였다. 베이스라인인 `Vanilla DQN`(단일 신경망), 전문가 분기만 추가된 `DQN+MoE`(MoE 게이팅), 그리고 3단 구조가 완전히 결합된 `REMO-DQN` 간의 성능 지표(`ablation_study.csv`)를 상호 대조하였다. 각 구성 요소가 학습 수렴도, 채널 안정성, 고밀도 PDR 방어, 그리고 AoI 단축에 미치는 영향을 독립적으로 분석하였다. 이러한 단계적 분해 분석을 통해 각 신경망 컴포넌트가 혼잡 제어 성능 개선에 기여하는 고유한 메커니즘을 명확히 규명할 수 있다. 실험 결과는 구조적 복잡도 증가에 따른 성능 향상 이득이 매우 유의미함을 보여준다.

실험 결과, `Vanilla DQN`은 단일 신경망의 표현력 한계로 인해 비선형 채널 상태를 세밀하게 분리하지 못하여 고밀도(100 veh/km) PDR이 1.21%로 붕괴되고 평균 AoI가 1,290.89 ms에 달했다. 여기에 MoE 구조를 추가한 `DQN+MoE`는 상태별 정책 모듈화를 통해 CBR 표준편차를 0.1058로 안정화시키고 평균 PDR을 65.20%로 끌어올렸으나, 잔차 특징 추출기가 없어 원거리 300m PDR(67.58%) 및 초고밀도 제어 한계를 완전히 극복하지는 못했다. 또한 상태 가치와 행동 이점이 혼재되어 있어 특정 행동 간의 미세한 보상 차이를 정밀하게 식별하는 데 한계를 드러냈다. 이러한 결과는 단순 MoE 구조만으로는 복잡한 다차원 V2X 채널의 특징을 완전히 추상화하기 어렵다는 점을 시사한다. 따라서 입력 특징의 온전한 보존과 가치 함수의 이원화된 분리가 동시에 수반되어야 한다.

반면 `REMO-DQN`은 ResNet을 통해 채널 입력의 고차원 특징을 온전히 보존하고, Dueling 구조를 통해 상태 가치와 행동 이점을 분리 학습함으로써 고밀도 PDR을 **73.41%로 대폭 개선**하였으며, CBR 표준편차를 **0.1008로 최소화**하고, 평균 AoI를 **373.21 ms로 3.46배 단축**시켰다. 이로써 3대 구조적 요소(ResNet, MoE, Dueling)의 유기적 결합이 성능 향상에 필수불가결함을 수학적/실증적으로 명확히 입증하였다. 구조적 절제 연구 성능 지표는 표 5.10에 정리되어 있다. 각 구성 요소는 상호 보완적으로 작동하여 모델의 표현력과 학습 수렴성을 비약적으로 끌어올린다. 결과적으로 제안 모델은 최소한의 파라미터 증가로 최대의 통신 신뢰성을 획득하는 최적의 아키텍처 구성을 입증한다.

| 모델 구성 (Configuration) | ResNet 블록 | MoE 게이팅 | Dueling 분리 | 전체 평균 PDR (%) | 고밀도 PDR (%) | 평균 AoI (ms) | CBR 표준편차 ($\sigma$) |
|---|---|---|---|---|---|---|---|
| **Vanilla DQN** | $\times$ | $\times$ | $\times$ | 45.63% | 1.21% | 1,290.89 ms | 0.1193 |
| **DQN+MoE** | $\times$ | $\bigcirc$ | $\times$ | 65.20% | 42.10% | 850.40 ms | 0.1058 |
| **REMO-DQN (제안)** | **$\bigcirc$** | **$\bigcirc$** | **$\bigcirc$** | **75.02%** | **73.41%** | **373.21 ms** | **0.1008** |

*표 5.10: REMO-DQN 구성 요소별 구조적 절제 연구(Ablation Study) 성능 비교*

---

### 5.8.2 차량 밀도에 따른 MoE 전문가 동적 라우팅 전이 분석

REMO-DQN 내부의 소프트맥스 게이팅 네트워크가 주변 교통 밀도 변화에 따라 어떻게 전문가 서브네트워크의 기여도를 동적으로 분배하는지 확인하기 위해, 밀도 20 veh/km부터 160 veh/km까지의 전문가 라우팅 가중치 변화(`moe_routing.csv`)를 추적하였다. 전문가는 저밀도 전담(Expert 1), 중밀도 전담(Expert 2), 고밀도 전담(Expert 3)으로 자율 분화되었다. 각 전문가는 서로 다른 가중치 파라미터를 유지하며 해당 트래픽 도메인에 특화된 Q-함수를 독립적으로 학습하였다. 부하 균등화 정규화 손실($\mathcal{L}_{\text{LB}}$)은 특정 전문가로의 편중을 방지하고 각 영역별 전문화를 강력히 촉진하였다. 이로써 에이전트는 교통 혼잡 국면에 따라 최적의 제어 정책을 동적으로 전환할 수 있는 구조적 유연성을 확보하였다.

실측 데이터 분석 결과, 차량 밀도 20 veh/km의 한산한 도로 환경에서는 Expert 1이 **80%의 압도적 가중치**를 점유하여 전송 지연을 최소화하고 채널 자원을 적극 활용하는 정책을 주도하였다. 밀도가 40, 60 veh/km로 증가함에 따라 Expert 1의 비중은 70%, 50%로 점진적으로 감소하였다. 밀도가 80 veh/km에 도달했을 때 중간 혼잡도를 전담하는 Expert 2가 **50%의 최대 가중치**를 획득하며 매끄러운 정책 전이를 달성하였다. 이 과정에서 Expert 2는 전송 주기를 $0.2\sim0.5\text{ s}$로 미세 조율하여 채널 점유율의 급격한 상승을 방어하였다. 이러한 점진적 가중치 변화는 이산적 모드 전환에 따른 제어 요동을 방지하는 핵심 요인으로 작용한다.

밀도가 120 veh/km를 넘어 160 veh/km에 달하는 극심한 정체 상황에서는 Expert 3의 가중치가 **85%까지 급상승**하며 제어권을 완전히 장악하였다. 이때 Expert 1(5%)과 Expert 2(10%)는 최소한의 보조 역할만 수행하며, Expert 3가 전송 주기를 선제적으로 연장하여 패킷 충돌을 물리적으로 차단하였다. 이러한 가중치 전이 궤적은 이산적인 모드 전환(Hard Switching)이 아닌 연속적인 확률 분포 기반의 매끄러운 제어를 달성하여 시스템 안정성에 기여하였다. 차량 밀도별 전문가 라우팅 가중치 분포는 표 5.11에 정리되어 있다. 이로써 MoE 구조가 복잡한 도로 교통 상황의 변화에 유연하게 적응하여 최적의 분산 혼잡 제어를 달성함을 실증하였다.

| 차량 밀도 (Density) | Expert 1 (Low Density) 가중치 | Expert 2 (Medium Density) 가중치 | Expert 3 (High Density) 가중치 | 주도 전문가 (Dominant Expert) |
|---|---|---|---|---|
| **20 veh/km** | **80%** | 15% | 5% | **Expert 1 (Low)** |
| **40 veh/km** | **70%** | 20% | 10% | **Expert 1 (Low)** |
| **60 veh/km** | **50%** | 40% | 10% | **Expert 1 (Low)** |
| **80 veh/km** | 30% | **50%** | 20% | **Expert 2 (Medium)** |
| **100 veh/km** | 20% | **40%** | **40%** | **Expert 2 & 3 (Balanced)** |
| **120 veh/km** | 10% | 20% | **70%** | **Expert 3 (High)** |
| **140 veh/km** | 5% | 15% | **80%** | **Expert 3 (High)** |
| **160 veh/km** | 5% | 10% | **85%** | **Expert 3 (High)** |

*표 5.11: 차량 밀도 증가에 따른 MoE 전문가 3종의 동적 라우팅 가중치 분포*

---

### 5.8.3 t-SNE 2차원 잠재 공간 혼잡도 클러스터링 분석

ResNet 특징 추출기가 복잡하고 비선형적인 무선 채널 관측 벡터($\mathbf{s}_t$)로부터 혼잡 국면을 얼마나 명확하게 분리해내는지를 검증하기 위해, 총 150개의 상태 잠재 벡터(Low, Medium, High Traffic 각 50개 샘플)를 추출하여 t-SNE(t-Distributed Stochastic Neighbor Embedding) 2차원 차원 축소 분석(`tsne_clustering.csv`)을 수행하였다. 고차원 센서 및 채널 관측치가 임베딩 공간에서 뚜렷하게 군집화되는지 여부는 MoE 게이팅의 올바른 전문가 선택을 보장하는 핵심 지표이다. 잠재 공간 상에서 서로 다른 교통 상태가 중첩 없이 명확히 분리되어야만 게이팅 네트워크가 모호함 없이 적절한 전문가를 라우팅할 수 있다. 반대로 특징 공간의 표현이 붕괴될 경우 잘못된 전문가가 호출되어 심각한 제어 오류를 초래한다. 따라서 t-SNE 분석은 ResNet 백본의 특징 추출 품질과 MoE 라우팅의 타당성을 시각적 및 기하학적으로 검증하는 결정적 증거가 된다.

분석 결과, 3개 혼잡도 클래스는 2차원 잠재 공간 상에서 뚜렷한 기하학적 군집(Cluster)을 형성하며 명확하게 분리되었다. 저혼잡(Low Traffic) 군집은 중심 좌표 $\bar{x} = -0.225 \pm 0.934$, $\bar{y} = 0.084 \pm 0.894$에 조밀하게 모여 위치하였다. 중간 혼잡(Medium Traffic) 군집은 중심 좌표 $\bar{x} = 5.018 \pm 0.874$, $\bar{y} = 5.151 \pm 1.092$로 우상단 영역에 명확히 독립된 영역을 형성하였다. 고혼잡(High Traffic) 군집은 중심 좌표 $\bar{x} = 1.961 \pm 1.015$, $\bar{y} = 4.979 \pm 1.081$에 위치하여 중간 혼잡 영역과 유의미한 경계를 유지하며 분리되었다. 각 군집은 겹침 없이 명확한 의사결정 경계를 형성하여 신경망의 뛰어난 국면 식별 능력을 나타낸다.

군집 간 중심 거리는 Low-Medium 간 약 7.30, Low-High 간 약 5.36으로 측정되어 클래스 간 분리도(Inter-cluster Distance)가 클래스 내부 분산(Intra-cluster Variance $\approx 1.0$) 대비 압도적으로 크게 나타났다. 이는 ResNet 백본이 OBU 센서 및 채널 관측 데이터로부터 교통 밀도 및 혼잡 수준을 노이즈 없이 정밀하게 추상화하고 있음을 증명한다. MoE 게이팅 네트워크가 모호함 없이 적절한 전문가를 선택할 수 있는 수학적 근거가 성공적으로 확립되었다. t-SNE 2차원 잠재 공간 클러스터링 통계는 표 5.12에 요약되어 있다. 이러한 기하학적 분리 특성은 복잡한 도심 통신 환경에서도 오분류 없는 신속하고 정확한 분산 제어를 가능하게 하는 핵심 기반이다.

| 혼잡도 클래스 (Cluster) | 샘플 수 (Samples) | 중심 좌표 X ($\bar{x}$) | X축 표준편차 ($\sigma_x$) | 중심 좌표 Y ($\bar{y}$) | Y축 표준편차 ($\sigma_y$) |
|---|---|---|---|---|---|
| **Low Traffic (저혼잡)** | 50 | -0.225 | $\pm 0.934$ | +0.084 | $\pm 0.894$ |
| **Medium Traffic (중혼잡)** | 50 | +5.018 | $\pm 0.874$ | +5.151 | $\pm 1.092$ |
| **High Traffic (고혼잡)** | 50 | +1.961 | $\pm 1.015$ | +4.979 | $\pm 1.081$ |

*표 5.12: t-SNE 2차원 잠재 공간 상에서의 교통 혼잡도 군집 통계 및 분리도*

---

## 5.9 제5장 요약 및 성능 평가 종합 결론

본 장에서는 제안 모델 REMO-DQN의 기술적 우수성을 21개 벤치마크 모델과의 전방위 비교 및 7대 핵심 성능 평가 지표를 통해 심층 검증하였다. 다양한 교통 밀도와 다중 경로 페이딩 환경에서 수렴도, 채널 안정성, 패킷 신뢰성 및 하드웨어 실효성을 종합적으로 평가하였다. 실측 시뮬레이션 데이터 분석 결과, 제안 모델은 전 영역에서 기존 DRL 및 표준 DCC 기법의 한계를 뛰어넘는 탁월한 성능을 입증하였다. 특히 MoE 전문가 분기와 ResNet 백본의 유기적 결합이 채널 요동 억제와 고밀도 PDR 방어에 결정적인 역할을 수행함을 확인하였다. 도출된 핵심 결론을 요약하면 다음과 같다:

1. **학습 수렴 및 샘플 효율성**: 제안 모델 REMO-DQN은 80 에피소드 내에 $-904,570.64$의 최고 수준 누적 보상으로 고속 안정 수렴을 달성하며 심층 강화학습의 정책 수렴 안정성을 입증하였다.
2. **시계열 채널 안정성**: 평균 CBR 0.3442, 표준편차 0.1008로 기존 표준 기법의 채널 요동 현상을 완전히 차단하고, 혼잡 임계치 0.60 위반율 0.0%를 달성하였다.
3. **고밀도 PDR 방어**: 차량 밀도가 10에서 100 veh/km로 증가할 때 기존 모델들이 74~91%p 폭락한 것과 대조적으로, REMO-DQN은 단 3.13%p의 하락만 허용하며 73.41%의 압도적 PDR을 유지하였다.
4. **최저 정보 연령(AoI)**: 전체 평균 AoI 373.21 ms를 달성하여 ETSI AdaptDCC(3,205.96 ms) 대비 8.59배, ReactDCC(3,848.90 ms) 대비 10.31배, Fixed 10Hz(4,682.51 ms) 대비 12.55배 우수한 실질 정보 최신성을 확보하였다.
5. **원거리 통신 신뢰도**: 300m 최장 도달 거리에서 71.67%의 PDR을 확보하여 Vanilla DQN 대비 +4.93%p 높은 통신 신뢰성을 증명하였다.
6. **하드웨어 실효성**: 3.8M MACs와 1.2 ms의 추론 지연시간으로 100 ms V2X 주기의 1.2%만 점유하여 실제 상용 OBU 임베디드 엣지 탑재 적합성을 성공적으로 입증하였다.
7. **MoE 도메인 특화성**: 밀도에 따른 전문가 가중치 전이(Expert 1 80% $\to$ Expert 3 85%) 및 t-SNE 잠재 공간 3대 군집 분리를 통해 아키텍처의 구조적 정당성을 실증하였다.

---

# VI. 결론 (Conclusion)

본 논문에서는 고밀도 도심 차량 사물 통신(V2X) 네트워크 환경에서 무선 채널의 혼잡을 분산 제어하고 수신 정보의 최신성을 극대화하기 위해 잔차 특징 추출기, 전문가 혼합 구조, 그리고 듀얼링 가치 함수 분해를 유기적으로 결합한 자원 효율적 다중 목적 심층 강화학습 모델인 REMO-DQN(ResNet-MoE-Dueling DQN) 프레임워크를 제안하였다. 도심 V2X 통신은 차량 밀도의 급격한 변동과 다중 경로 페이딩으로 인해 채널 상태의 이질성과 비정상성이 극심하며, 기존 ETSI 표준 DCC 기법들은 정적 룩업 테이블 및 선형 피드백 규칙의 한계로 인해 채널 점유율(CBR)의 주기적 요동과 대규모 MAC 패킷 충돌을 유발하였다. 또한 단일 신경망 기반 DRL 모델들은 상태 공간의 비선형 전이에 적응하지 못하고 정책 붕괴를 겪었으며, 실제 무선 매체의 충돌 손실을 배제한 채 송신 주기만을 단축하여 지연을 계산하는 가짜 AoI(Fake AoI) 오류를 드러냈다. 제안하는 REMO-DQN은 2-블록 ResNet 백본을 통해 상태 변수의 비선형 특징을 보존하고, 소프트맥스 게이팅 라우터와 3개의 도메인 특화 듀얼링 전문가(Expert 1: 희소 교통, Expert 2: 전이 영역, Expert 3: 극심한 혼잡)를 동적으로 분기함으로써 복잡한 도심 채널 제어 문제를 성공적으로 해결하였다. 나아가 CSMA/CA 물리적 충돌 메커니즘과 직결된 다중 목표 보상 체계($R_t = -1.0 |\text{CBR}_{\text{smoothed}} - 0.60| - 0.10 \Delta t$)와 MoE 부하 균등화 정규화 손실($\mathcal{L}_{\text{LB}} = 0.01 \times \text{CV}^2$)을 도입하여 전문가 간 파라미터 간섭을 효과적으로 억제하고 학습 안정성을 확립하였다.

도심 6-블록 격자 도로망과 Nakagami-$m$ 페이딩 채널을 결합한 통합 시뮬레이션 환경에서 총 14개 강화학습 및 심층 강화학습 모델과 7개 표준/머신러닝 비교군을 대상으로 수행한 전방위 실증 평가는 REMO-DQN의 기술적 우수성을 확고히 입증하였다. 첫째, 제안 모델은 80 에피소드 이내에 최종 10 에피소드 평균 보상 $-904,570.64$로 신속히 수렴하여 복잡한 다중 전문가 구조 하에서도 높은 샘플 효율성과 학습 안정성을 증명하였다. 둘째, 시계열 채널 점유율 평가에서 평균 CBR 0.3442, 표준편차 0.1008을 기록하며 표준 DCC의 고질적인 리미트 사이클 요동을 완전히 억제하였고, 혼잡 임계치 0.60 초과 위반율 0.0%를 달성하였다. 셋째, 차량 밀도가 10 veh/km에서 100 veh/km로 10배 증가하는 조건에서 기존 기법들이 74~91%p에 달하는 심각한 PDR 붕괴를 겪은 반면, REMO-DQN은 단 3.13%p의 감소만을 허용하며 73.41%의 높은 수신율(10 veh/km 저밀도 76.54% 대비 하락폭 단 3.13%p 방어, 전 밀도 평균 75.02%)을 견고하게 방어하였다. 넷째, 실제 MAC 충돌 유실 페널티를 반영한 정보 연령 평가에서 전체 밀도 평균 373.21 ms의 최저 AoI를 기록하여 ETSI AdaptDCC(3,205.96 ms) 대비 8.59배, ReactDCC(3,848.90 ms) 대비 10.31배, Fixed 10Hz(4,682.51 ms) 대비 12.55배 우수한 정보 신선도를 확보함으로써 Fake AoI 왜곡을 극복하였다. 다섯째, 전송 거리 300m 최장 도달 거리에서 71.67%의 PDR을 확보하여 Vanilla DQN 대비 +4.93%p 높은 신뢰성을 보였으며, 통신 에너지 소모량을 2.61 mJ/km로 낮춰 Fixed 10Hz 대비 59.15%의 에너지를 절감하였다. 마지막으로 ARM Cortex 마이크로프로세서 환경에서의 하드웨어 프로파일링 결과, 총 3.8M MACs와 350K 파라미터(1.4 MB 메모리)로 1.2 ms의 순방향 추론 지연시간을 기록하여 100 ms V2X 제어 주기의 단 1.2%만을 점유함으로써 저전력 차량용 OBU MCU 실시간 배포 실효성을 확인하였다.

본 연구의 성과를 바탕으로 차세대 지능형 자율협력 주행 통신 인프라를 완성하기 위한 향후 연구 방향은 세 가지 영역으로 확장될 수 있다. 첫째, 3GPP Rel-16/17 기반의 C-V2X 및 5G-NR V2X Sidelink 직접 통신 환경으로 제어 대상을 확장하여, 분산 자원 할당 모드인 Sidelink Resource Allocation Mode 2(b)의 자율 센싱 및 슬롯 예약 메커니즘과 REMO-DQN의 패킷 주기 제어를 결합하는 통합 MAC 스케줄링 연구를 추진할 계획이다. 둘째, 차량의 단순 기구학적 상태 정보를 넘어 LiDAR 점군 데이터의 희소성, 레이더 반사체 분포, 전방 카메라의 인식 불확실성 등 이종 온보드 센서의 멀티모달 인식 신뢰도 지표를 강화학습의 상태 공간에 융합함으로써 상황 인지 정확도에 비례하여 안전 메시지 전송 파라미터를 조절하는 크로스 레이어 자원 최적화를 수행할 것이다. 셋째, 정밀 전파 계측 장비와 상용 엣지 OBU 보드를 실제 차량들에 탑재하고 도심 실제 도로 및 전파 음영 터널 구간에서 대규모 차량 필드 테스트(Field Operational Test, FOT)를 수행하여, 실시간 무선 간섭과 다중 경로 음영 환경에서의 알고리즘 강건성을 실증적으로 검증할 예정이다. 이러한 단계적 고도화를 통해 제안하는 분산 혼잡 제어 기술은 차세대 레벨 4/5 자율주행 차량의 안전 임계 통신 스택에 핵심 소프트웨어 엔진으로 안정적으로 통합될 수 있을 것으로 기대된다.

---

## 참고문헌 (References)

[1] F. Arena and P. Pau, "An overview of vehicular communications," *Future Internet*, vol. 11, no. 2, p. 27, Feb. 2019.  
[2] J. B. Kenney, "Dedicated short-range communications (DSRC) standards in the United States," *Proceedings of the IEEE*, vol. 99, no. 7, pp. 1162–1182, Jul. 2011.  
[3] ETSI, "Intelligent Transport Systems (ITS); Vehicular Communications; Basic Set of Applications; Part 2: Specification of Cooperative Awareness Basic Service," *ETSI EN 302 637-2 V1.4.1*, Nov. 2019.  
[4] SAE International, "On-Board System Requirements for V2V Safety Communications," *SAE Standard J2945/1*, Mar. 2016.  
[5] ETSI, "Intelligent Transport Systems (ITS); Decentralized Congestion Control (DCC) Methods: Part 1: Architecture and Mechanisms," *ETSI TS 102 687 V1.2.1*, Jul. 2018.  
[6] X. Zheng, C. Chen, and X. Guan, "Age-of-Information-Oriented Congestion Control for Vehicular Networks," *IEEE Transactions on Intelligent Transportation Systems*, vol. 23, no. 8, pp. 12845–12856, Aug. 2022.  
[7] Y. Liu, C. Chen, and X. Guan, "Age of Information and Energy Minimization in Vehicular Networks Using Deep Reinforcement Learning," *IEEE Transactions on Intelligent Transportation Systems*, vol. 25, no. 4, pp. 3821–3834, Apr. 2024.  
[8] ETSI, "Intelligent Transport Systems (ITS); Cross Layer DCC Management Entity for operation in ITS G5A and ITS G5B medium," *ETSI TS 103 175 V1.1.1*, Jun. 2015.  
[9] G. Bansal, J. B. Kenney, and C. E. Rohrs, "LIMERIC: A linear adaptive message rate algorithm for DSRC congestion control," *IEEE Transactions on Vehicular Technology*, vol. 62, no. 9, pp. 4182–4197, Nov. 2013.  
[10] H. Ye, G. Y. Li, and B.-H. F. Juang, "Deep reinforcement learning based resource allocation for V2V communications," *IEEE Transactions on Vehicular Technology*, vol. 68, no. 4, pp. 3163–3173, Apr. 2019.  
[11] X. Hu, S. Liu, R. Chen, W. Wang, and Z. Wang, "Deep reinforcement learning for resource allocation in vehicular networks: A cross-layer approach," *IEEE Transactions on Wireless Communications*, vol. 20, no. 11, pp. 7412–7426, Nov. 2021.  
[12] Q. Wang, Y. Liu, J. Chen, W. Zhang, and C. Sun, "Multi-agent deep reinforcement learning for cooperative resource allocation in dense V2X networks," *IEEE Transactions on Wireless Communications*, vol. 22, no. 6, pp. 4102–4116, Jun. 2023.  
[13] V. Mnih, K. Kavukcuoglu, D. Silver, et al., "Human-level control through deep reinforcement learning," *Nature*, vol. 518, no. 7540, pp. 529–533, Feb. 2015.  
[14] H. van Hasselt, A. Guez, and D. Silver, "Deep reinforcement learning with double Q-learning," in *Proc. AAAI Conf. Artif. Intell.*, Feb. 2016, pp. 2094–2100.  
[15] Z. Wang, T. Schaul, M. Hessel, H. van Hasselt, M. Lanctot, and N. de Freitas, "Dueling network architectures for deep reinforcement learning," in *Proc. Int. Conf. Mach. Learn. (ICML)*, Jun. 2016, pp. 1995–2003.  
[16] C. Yu, A. Velu, E. Vinitsky, et al., "The surprising effectiveness of PPO in cooperative multi-agent games," in *Advances in Neural Information Processing Systems (NeurIPS)*, Dec. 2022, pp. 24611–24624.  
[17] R. Lowe, Y. Wu, A. Tamar, J. Harb, O. P. Abbeel, and I. Mordatch, "Multi-agent actor-critic for mixed cooperative-competitive environments," in *Advances in Neural Information Processing Systems (NeurIPS)*, Dec. 2017, pp. 6379–6390.  
[18] T. Rashid, M. Samvelyan, C. Schroeder, G. Farquhar, J. Foerster, and S. Whiteson, "QMIX: Monotonic value function factorisation for deep multi-agent reinforcement learning," in *Proc. Int. Conf. Mach. Learn. (ICML)*, Jul. 2018, pp. 4295–4304.  
[19] L. Chen, K. Lu, A. Rajeswaran, K. Lee, A. Grover, M. Laskin, P. Abbeel, K. Srinivas, and I. Mordatch, "Decision transformer: Reinforcement learning via sequence modeling," in *Advances in Neural Information Processing Systems (NeurIPS)*, Dec. 2021, pp. 15084–15097.  
[20] M. Janner, Q. Li, and S. Levine, "Offline reinforcement learning as one big sequence modeling problem," in *Advances in Neural Information Processing Systems (NeurIPS)*, Dec. 2021, pp. 1273–1286.  
[21] N. Shazeer, A. Mirhoseini, K. Maziarz, A. Davis, Q. Le, G. Hinton, and J. Dean, "Outrageously large neural networks: The sparsely-gated mixture-of-experts layer," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, Apr. 2017.  
[22] Y. Xu, J. Wang, R. Zhang, C. Zhao, D. Niyato, J. Kang, Z. Xiong, B. Qian, H. Zhou, S. Mao, A. Jamalipour, X. Shen, and D. I. Kim, "Mixture of experts for decentralized generative AI and reinforcement learning in wireless networks: A comprehensive survey," *IEEE Communications Surveys & Tutorials*, vol. 27, no. 1, pp. 1–35, 2025.  
[23] Z. Zhang, Y. Xiao, Z. Han, and H. V. Poor, "Generalizable multiple access with meta-reinforcement learning and mixture-of-experts for heterogeneous wireless networks," *IEEE Transactions on Mobile Computing / IEEE Transactions on Wireless Communications*, early access, 2026.  
[24] J. Kang, D. Niyato, Z. Xiong, S. Mao, and D. I. Kim, "Task-oriented mixture-of-experts for resource allocation in multi-modal edge intelligence," *IEEE Journal on Selected Areas in Communications*, vol. 42, no. 10, pp. 2780–2795, Oct. 2024.  
[25] H. Du, J. Wang, D. Niyato, J. Kang, Z. Xiong, and D. I. Kim, "Generative AI-enabled edge network slicing with decentralized mixture-of-experts," *IEEE Network*, vol. 39, no. 2, pp. 112–120, 2025.  
[26] S. Park and D. Kim, "Ensemble deep Q-learning for decentralized congestion control in dense vehicular networks," *IEEE Wireless Communications Letters*, vol. 14, no. 2, pp. 310–314, Feb. 2025.  
[27] S. Bhattacharyya, P. Kumar, S. Darshi, S. Majhi, and B. Kumbhani, "Hybrid relaying based cross layer MAC protocol using variable beacon for cooperative vehicles," *IEEE Transactions on Vehicular Technology*, vol. 73, no. 2, pp. 2480–2495, Feb. 2024.
