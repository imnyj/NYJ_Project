# 심층 강화학습 기반의 차량 네트워크 내 끊김 없는 서비스를 위한 V2I 프리캐싱 의사결정 기법

## 요약 (Abstract)
차량 네트워크(Internet of Vehicles, IoV) 환경에서 멀티미디어 및 대용량 데이터 서비스에 대한 수요가 급증함에 따라, 노변 기지국(Roadside Unit, RSU)을 활용한 엣지 캐싱(Edge Caching) 및 프리캐싱(Precaching) 기술이 필수적으로 요구되고 있다. 하지만 기존의 휴리스틱(Heuristic) 기반 프리캐싱 기법은 신호등 대기 시간이나 돌발적인 교통 정체 등 도심 환경의 확률적이고 동적인 차량 이동성을 반영하지 못해 백홀(Backhaul) 대역폭의 심각한 낭비나 캐시 미스(Cache Miss)를 유발한다. 본 논문에서는 이러한 한계를 극복하기 위해 심층 강화학습(Deep Reinforcement Learning, DRL) 기반의 **V2I 프리캐싱 의사결정 기법(V2I Precaching Decision Scheme)**을 제안한다. 제안하는 기법은 RSU를 통과하는 차량들의 통계적 체류 시간(Dwell Time)과 통신 잔여 용량을 상태(State)로 받아들여, 다음 RSU(Next RSU)로 데이터를 미리 전송할지 여부를 스스로 판단한다. 특히, 단순히 이분법적인 보상을 주는 기존 연구들과 달리 낭비된 체류 시간($W_{curr}$)과 지연량 기반의 연속형(Continuous) 보상 함수를 설계하고 Optuna를 통해 가중치를 최적화하여 편향 없는 학습을 달성하였다. 또한 엣지 환경에서 모델 훈련 중 발생할 수 있는 서비스 지연(Downtime)을 원천 차단하기 위해 **교차 모델(Dual-Model) 아키텍처**를 도입하였다.

---

## 1. 서론 (Introduction)
최근 자율주행 기술의 발전과 함께 차량 내 인포테인먼트(In-Vehicle Infotainment) 시스템이 고도화되면서 차량 네트워크(IoV)의 데이터 트래픽이 폭발적으로 증가하고 있다. 이러한 대용량 콘텐츠를 중앙 클라우드 서버에서 직접 제공할 경우 백홀 링크의 혼잡과 높은 지연(Latency)이 발생한다. 이를 해결하기 위해 콘텐츠 중심 차량 네트워크(Content-centric Internet of Vehicles, CIoV) 패러다임이 등장하였으며, 도로변에 설치된 RSU(Roadside Unit)가 엣지 캐싱 노드 역할을 수행하여 차량과 가까운 곳에서 데이터를 제공한다 [1, 2].

차량은 지속적으로 이동하므로, 현재 RSU의 통신 범위를 벗어나 다음 RSU(Next RSU) 영역으로 진입하는 핸드오버(Handover) 과정이 필연적으로 발생한다. 끊김 없는(Seamless) 서비스를 보장하기 위해 차량이 도착하기 전 다음 RSU에 콘텐츠를 미리 전송해두는 프리캐싱(Precaching) 기술이 활발히 연구되어 왔다 [3]. 그러나 기존의 프리캐싱 기법들은 결정론적인(Deterministic) 이동성 예측에 의존하거나 단순한 휴리스틱 규칙에 기반하고 있어, 도심 교차로의 신호등 위상 변화나 예기치 못한 정체로 인해 발생하는 체류 시간(Dwell Time)의 변동성을 제대로 처리하지 못한다. 그 결과, 너무 일찍 프리캐싱을 수행하여 RSU의 저장 공간 및 백홀 자원을 낭비하거나, 반대로 늦게 수행하여 치명적인 통신 단절(Outage) 및 지연을 초래한다.

본 논문에서는 도심 교통의 불확실성에 유연하게 대응하고 엣지 디바이스의 제한된 자원을 극대화하기 위해, 심층 강화학습(Deep Reinforcement Learning, DRL) 기반의 지능형 V2I 프리캐싱 의사결정 기법을 제안한다. 
본 논문의 주요 기여도는 다음과 같다.
1. **DRL 기반 연속적 보상 함수 설계:** 낭비된 통신 기회($W_{curr}$)와 데이터 수신 지연량을 계산하여 정교한 연속형 보상을 부여하고, Optuna를 이용한 HPO(Hyperparameter Optimization)를 통해 수작업 편향(Bias)을 배제한 최적의 의사결정 모델(PPO, SAC 등)을 구축하였다.
2. **신호등 지연을 고려한 통계적 상태(State) 표현:** 개별 차량의 순간 속도가 0으로 수렴하는 신호 대기 상황의 한계를 극복하고자, RSU를 통과하는 전체 차량 군집의 체류 시간 기반 역산 평균 속도를 State로 활용하였다.
3. **무중단(Zero Downtime) 교차 모델 아키텍처:** 엣지 환경(NVIDIA Jetson 등)에서 강화학습 모델이 배치(Batch) 데이터를 수집하고 가중치를 업데이트하는 동안 인퍼런스가 지연되는 문제를 해결하기 위해, 두 개의 모델이 실시간으로 교대(Ping-Pong)하는 아키텍처를 적용하여 100% 서비스 가용성을 보장한다.

---

## 2. 관련 연구 (Related Work)
차량 네트워크에서의 캐싱 및 프리캐싱 전략은 초기에 콘텐츠의 인기도(Popularity)나 단순한 물리적 거리 기반의 임계값 모델로 접근되었다. [4]와 [5]는 마르코프 체인(Markov Chain) 및 최단 경로(Shortest-path) 기반으로 차량의 다음 위치를 예측하여 프리캐싱을 수행하였다. 그러나 이러한 방식은 도심의 복잡한 신호 체계나 실시간 트래픽 변화를 반영하지 못해 캐시 적중률(Hit Ratio)이 현저히 떨어지는 한계가 있었다.

최근에는 기계학습(Machine Learning) 및 강화학습을 도입하여 동적 환경에 적응하려는 시도가 주를 이루고 있다. Wang et al. [6]은 Contextual Multi-Armed Bandit 알고리즘을 사용하여 RSU의 하이브리드 캐싱을 최적화하였으며, Elsayed et al. [7]은 LSTM을 활용해 통행 시간을 예측하는 능동형 캐싱 프레임워크를 제안하였다. 또한 Jiang et al. [8]은 연합 학습(Federated Learning)과 DRL을 결합하여 차량의 프라이버시를 보호하면서도 RSU의 캐싱 효율을 높이는 방안을 제시하였다. 
하지만 기존의 ML 기반 프리캐싱 기법들은 에이전트의 훈련(Training) 단계에서 발생하는 컴퓨팅 자원 병목현상으로 인해 실시간 인퍼런스(Inference)가 차단될 수 있는 치명적인 운영상의 결함을 간과하고 있다. 또한, 프리캐싱 여부를 판단하는 강화학습 보상(Reward)이 0과 1 같은 이산적이고 편향된 휴리스틱으로 설정된 경우가 많아, 자원 낭비의 정량적 최적화가 이루어지지 못했다.

---

## 3. 제안하는 시스템 모델 및 방법론 (Proposed Scheme)
본 장에서는 도심 V2I 환경에서 엣지 자원 낭비와 서비스 지연을 최소화하기 위한 DRL 기반 프리캐싱 의사결정 시스템의 구조와 핵심 알고리즘을 상세히 설명한다.

### 3.1. 시스템 아키텍처 및 교차 모델(Dual-Model) 설계
제안하는 시스템은 교차로마다 설치된 RSU와 통신 반경 내를 주행하는 커넥티드 차량들로 구성된다. RSU는 차량의 콘텐츠 다운로드 요청을 처리하며, 차량이 현재 RSU 범위를 벗어나 Outage Zone을 거쳐 Next RSU로 이동할 것으로 예상될 때, 선제적으로 백홀망을 통해 Next RSU로 콘텐츠를 넘겨주는(Precache) 결정을 내린다.

강화학습 모델이 지속적으로 최신 교통 패턴을 학습(Online Learning)하려면 일정 주기의 배치 훈련이 필수적이다. 단일 모델을 사용할 경우 훈련 연산이 진행되는 수 초~수 분 동안 새로운 차량의 프리캐싱 요청을 처리하지 못하는 서비스 중단(Downtime)이 발생한다. 이를 극복하기 위해 본 논문은 RSU 내에 동일한 아키텍처의 **교차 모델(Model A, Model B)**을 적재하는 Ping-Pong 방식을 제안한다.
*   **인퍼런스와 학습의 분리:** Model A가 차량들에게 실시간으로 프리캐싱 여부를 판단(Inference)하며 리워드 배치를 수집하는 동안, Model B는 이전 주기에 수집된 데이터를 바탕으로 백그라운드에서 가중치를 업데이트(Training)한다.
*   **Hot-Swap 교대:** Model B의 훈련이 완료되는 즉시, 두 모델의 역할을 스위칭(Swap)한다. 이를 통해 NVIDIA Jetson과 같은 저전력 엣지 디바이스 환경에서도 CPU/GPU 자원을 시분할로 완벽히 격리하며 100%의 서비스 가용성(Zero Downtime)을 보장한다.

### 3.2. 심층 강화학습(DRL) 기반 환경 설계
프리캐싱 결정을 최적화하기 위해, RSU 에이전트는 차량의 통계적 이동성과 콘텐츠 상태를 마르코프 결정 과정(MDP)으로 모델링한다. 최신 최적화 알고리즘인 PPO(Proximal Policy Optimization) 및 SAC(Soft Actor-Critic)를 적용할 수 있도록 Continuous Action Space 구조를 채택하였다.

*   **상태 공간 (State Space):** 개별 차량의 순간 속도는 신호등 적색등 점등 시 $0$으로 수렴하여 에이전트에게 잘못된 무한 체류(Infinite Dwell) 편향을 줄 수 있다. 이를 방지하기 위해 RSU를 통과한 이전 차량들의 **체류 시간(Dwell Time) 기반 역산 평균 속도**를 통계적으로 도출하여 State로 사용한다. (State: `거리`, `역산 평균 속도`, `잔여 콘텐츠 크기`, `통신 속도`, `신호등 위상`, `신호 잔여 시간` 등 6차원)
*   **행동 공간 (Action Space):** 차량이 RSU에 진입한 시점에 프리캐싱을 수행할 것인지(Precache, $A=1$) 아니면 현재 RSU 내에서 다운로드가 끝날 것으로 믿고 대기할 것인지(No Precache, $A=0$)를 결정한다.
*   **연속형 보상 함수 (Continuous Reward Function):** 보상 함수는 단순히 맞추고 틀림을 떠나, 얼마나 자원을 낭비했는지를 메가바이트(MB) 단위로 정량화($W_{curr}$)하여 부여된다.
    *   Precache를 하지 않고 성공적으로 현재 RSU에서 다운로드를 완료한 경우, 낭비되지 않은 잉여 체류 시간에 비례하여 $+R_{base} + \gamma(W_{curr} / C_{total})$의 보상을 지급한다.
    *   Precache를 강행했으나 결국 현재 RSU에서 완료되어 백홀을 낭비한 경우, 낭비된 기회 비용에 비례하여 패널티 $-P_{base} - \beta(W_{curr} / C_{total})$를 부여한다.
    *   Precache 없이 다음 RSU로 넘어가 통신이 단절된(Missed) 경우 가장 치명적인 패널티인 $-P_{base} - \delta(C_{missed} / C_{total})$를 부과한다.

### 3.3. 하이퍼파라미터 최적화 (HPO)
보상 함수의 각 가중치 파라미터($\alpha, \beta, \gamma, \delta$) 및 모델의 학습률(Learning Rate)은 연구자의 주관적 판단이 개입될 경우 편향된 지역 최적해(Local Minima)에 빠질 위험이 크다. 본 연구는 Optuna 기반의 HPO 프레임워크를 연동하여, 단순히 보상 합계를 최대화하는 것이 아니라 시스템 측면의 비즈니스 지표(통신 낭비량 + 2배 가중된 지연 패널티)를 직접적으로 최소화하는 방향으로 최적 파라미터를 탐색하였다.

---

*(이하 4장 성능 평가 및 5장 결론은 생략)*

## 참고문헌 (References)
[1] Li, X., et al. "Proactive caching for content-centric vehicular networks." *IEEE Internet of Things Journal*, 2017.
[2] Hichri, H., et al. "Edge caching in vehicular networks: A comprehensive survey." *IEEE Communications Surveys & Tutorials*, 2021.
[3] Ding, Y., et al. "Machine learning based proactive caching in vehicular networks." *IEEE Transactions on Vehicular Technology*, 2022.
[4] Ostrovskaya, A., et al. "Mobility-aware caching in vehicular networks." *IEEE Wireless Communications*, 2018.
[5] Amadeo, M., et al. "Information-centric networking for connected vehicles." *IEEE Communications Magazine*, 2021.
[6] Wang, J., and Grace, D. "Contextual Multi-Armed Bandit for Proactive Caching at RSUs." *IEEE Transactions on Communications*, 2023.
[7] Elsayed, M., et al. "LSTM-based Predictive Proactive Caching Framework in VANETs." *IEEE Transactions on Intelligent Transportation Systems*, 2022.
[8] Jiang, Y., et al. "Asynchronous Federated Learning and DRL for Mobility-aware Edge Caching." *IEEE Journal on Selected Areas in Communications*, 2024.
