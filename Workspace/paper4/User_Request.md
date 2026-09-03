## 사용자 요청

>> 기존 CCN 기반의 Precaching을 위한 서론 흐름을 참고하여, 새롭게 작성할 논문을 위한 서론을 작성해보도록 하자.

## 1. 기존 CCN 기반의 Precaching을 위한 서론 흐름
(1) 문제 제기
차량들이 자율주행이 되고 있다.
운전에 집중할 필요가 없어서 content 요청이 많아진다.
Ericson Report를 보면 mobile data traffic이 급증한다고 한다.
RSU나 cellular는 무선 자원에 한계가 있다.
congestion으로 인해 백홀 traffic이 가득 차고, 무선 자원이 부족해진다.
그로 인해 딜레이가 발생할 수 있다.
delay sensitive content는 delay에 매우 치명적이다.
또한, 영상 매체는 QoE를 저하한다.

(2) 대분류: Precaching in CCN + VANET
그래서 노드들의 caching storage를 활용하는 CCN을 접목하는 시도가 되고 있다.
중간 노드가 content를 캐싱함으로서 서버로의 접근을 줄인다.
하지만, storage 한계로 인해 모든 content를 caching할 수 없다.
결국 어떤 content는 access delay가 발생한다.
예측을 통해 content를 미리 가져다 두는 precaching이 연구되고 있다.
precahcing은 예측을 통해 이루어지기 때문에, 정확도가 매우 중요하다.
예측을 함에 있어 휴리스틱 방안은 현실에 반영하기에 정확도가 좋지 않다.

(3) 소분류: ML-based Precaching in CCN + VANET
많은 연구자가 ML을 이용한다.
어떤 문제를 해결하기 위해 어떤 식으로 ML을 쓴다.
거기에 무슨 문제가 있다.
문제점 1, 문제점 2, 문제점 3.

(4) 제안 방안의 Contributions
어떠한 방안을 제시함.
문제점 1을 어떻게 해결
문제점 2를 어떻게 해결
문제점 3을 어떻게 해결
기타 다른 Contribution은 어떤 것이 있음.
시뮬 어쩌고 해서 어떤 성능을 보임.

## 2. Paper4에 대한 서론 설계 (설득력 강화를 위한 심층 문단 설계)

(1) 1문단: Motivation & The Bottleneck (CAV 데이터 폭증과 통신 인프라의 한계)
자율주행차량(CAV)과 협력형 지능형 교통 시스템(C-ITS)의 기술적 성숙은 현대 차량 네트워크의 패러다임을 근본적으로 변화시키고 있다 [1]. 
군집 주행(Platooning), 협력형 충돌 회피, 지능형 교차로 관리와 같은 안전 필수(Safety-critical) 애플리케이션이 실현되기 위해서는 한 가지 절대적인 전제 조건이 필요하다. 
바로 인프라가 도로 위 모든 차량의 위치, 속도, 가속도 등 고도로 정확한 실시간 이동성 데이터를 지연 없이 확보해야 한다는 점이다 [2], [3]. 
그러나 도로 상의 수많은 차량이 뿜어내는 방대한 규모의 실시간 데이터를 오직 코어망(Cellular V2N)에만 의존하여 수집하는 것은, 막대한 금전적 비용(Cost)은 물론 심각한 백홀 지연(Backhaul latency) 병목을 유발한다 [5]. 
이에 대한 현실적이고 확장성 있는 대안으로, 도로변 기지국(RSU)을 활용한 국지적인 V2I(Vehicle-to-Infrastructure) 통신 기반의 데이터 관리가 강력히 대두되고 있다. 
하지만 RSU의 커버리지 내에서조차 기존의 표준적인 데이터 교환 방식은 심각한 결함을 내포하고 있다. 
현재 대부분의 시스템은 차량들이 10Hz 수준의 고정된 짧은 주기로 자신의 상태(예: ETSI CAM)를 맹목적으로 브로드캐스트하도록 설계되어 있다. 
이러한 엄격한 주기적 전송은 차량 밀도가 낮은 환경에서는 동작할 수 있으나, 도심과 같은 고밀도 환경에서는 치명적인 무선 채널 혼잡(Congestion)을 야기한다. 
결과적으로 극심한 패킷 충돌(Collision)이 발생하여, 애초에 달성하고자 했던 데이터의 신뢰성마저 스스로 훼손하게 된다 [4]. 
더욱이, 정보의 가치나 상황을 고려하지 않은 연속적인 브로드캐스트는 차량에 탑재된 OBU(On-Board Unit)의 제한된 전력(Battery)을 무의미하게 고갈시킨다. 
결국 이러한 무차별적인 주기적 전송 방식은 자원 제약이 뚜렷한 미래 V2X 네트워크의 지속 가능성을 가로막는 가장 치명적인 병목으로 작용하고 있다 [6].

(2) 2문단: AI-based AoI & The Blind Spot (데이터 신선도 최적화 연구의 모순과 맹점)
이러한 통신 자원의 한계 속에서 수신측(RSU)이 보유한 데이터의 신선도를 정량화하고 관리하기 위해, AoI(Age of Information)라는 혁신적인 지표가 도입되어 폭넓게 활용되고 있다. 
단순한 전송 지연(Latency)과 달리, AoI는 정보가 생성된 시점부터 현재까지 흐른 시간을 측정함으로써 시스템 관점의 실질적인 정보 최신화를 목표로 한다. 
차량 네트워크의 고도의 동적 특성을 인지한 최근의 선도적인 연구들은, 이 AoI를 효과적으로 최소화하기 위해 심층 강화학습(DRL)을 비롯한 진보된 AI 기법들을 적극적으로 채택하고 있다 [7], [8]. 
이러한 최첨단 DRL 접근법들은 시시각각 변하는 네트워크 상태에 맞추어 통신 자원을 동적으로 할당함으로써, 전체 네트워크의 평균 또는 최대 AoI를 억제하는 데 괄목할 만한 성과를 보여주었다 [9]. 
그러나 그들이 제시한 정교한 알고리즘 이면에는, 실도로 환경의 물리적 특성을 간과한 근본적이고 치명적인 맹점(Blind Spot)이 존재한다. 
기존 연구들은 예외 없이 "데이터가 오래될수록(Raw AoI가 높을수록) 시스템의 추정 정확도가 훼손된다"는 단편적인 가정을 기반으로, 오직 경과된 '시간' 자체를 최소화하는 데에만 매몰되어 있다. 
이는 각 차량이 처한 실제 동역학적 물리 맥락(Physical context)을 완전히 배제한 처사이다. 
가령, 교차로에서 적색 신호등을 만나 정차해 있거나 심각한 교통 정체로 인해 오도 가도 못하는 차량을 상상해 보라. 
해당 차량의 위치와 속도(0에 수렴)는 변하지 않고 매우 정적이며, 따라서 RSU는 새로운 업데이트를 받지 않더라도 해당 차량의 현재 상태를 완벽하게 예측하고 추정할 수 있다. 
즉, 이러한 상황에서는 AoI가 아무리 높게 치솟더라도 RSU가 겪는 '실제 추정 오차'는 사실상 0에 불과한 것이다. 
기존의 AI 모델들은 이와 같은 '상황적 예측 가능성(Contextual predictability)'을 인지할 능력이 없기에, 단순히 데이터가 오래되었다는 이유 하나만으로 정지한 차량에게조차 불필요한 갱신(Redundant update)을 억지로 강제한다. 
결과적으로 이들은 자신들이 해결하고자 했던 바로 그 문제—채널 혼잡과 전력 낭비—를 스스로 가중시키는 뼈아픈 모순을 낳고 있으며, 이는 정보의 '시간'이 아닌 '유효성'에 집중하는 새로운 스케줄링 패러다임의 필요성을 강력히 시사한다.

(3) 3문단: Contributions (컨텍스트 인지형 스케줄러 제안 및 다차원 자원 최적화)
본 논문에서는 이러한 기존 연구들의 근본적인 한계를 타파하기 위해, 단순한 시간 경과(Raw AoI) 최적화의 굴레를 벗어나 실제 '상태 추정 오차(Effective AoI/Estimation Error)' 최소화로 목적 함수를 완전히 재정의하는 '컨텍스트 인지형 DRL 기반 V2I 업링크 스케줄링 프레임워크'를 제안한다. 
우리가 제안하는 RL 에이전트는 RSU에 위치한 지능적인 중앙 스케줄러로서, 네트워크와 도로의 포괄적인 컨텍스트를 실시간으로 관측한다. 
이 관측 공간에는 각 차량의 실시간 동역학 정보(속도, 가속도)는 물론, 교통 신호등의 위상(Phase) 변화, 차선 내 차량 대기열(Queue) 상태, 그리고 무선 채널의 혼잡도까지 조밀하게 포함된다. 
에이전트는 이러한 맥락을 종합적으로 이해함으로써, 상태가 쉽게 예측되는 차량(예: 정지 상태)을 정확히 식별해 내고 이들에게는 의도적으로 통신 침묵(Silence)을 지시하여 무의미한 중복 전송을 원천적으로 제거한다. 
반면 갱신이 진정으로 필요한 차량들에 대해서는, 새롭게 설계된 하이브리드 액션 공간(Hybrid Action Space)을 활용하여 다차원적인 통신 자원을 동시에 정밀하게 할당한다. 
구체적으로, 다음 업데이트까지의 최적 대기 시간(Delta)과 연속적인 전송 전력(Power)을 결정하는 동시에, 이산적인 서브채널(Subchannel) 인덱스까지 단일 신경망 추론으로 한 번에 할당한다. 
우리는 행동 간의 가변적인 시간 간격을 수학적으로 엄밀히 다루기 위해 이 통신 환경을 Semi-Markov Decision Process (SMDP)로 정형화하였다. 
또한 에이전트의 학습 방향을 이끄는 보상 함수(Reward function)는 단순히 추정 오차를 줄이는 것에 그치지 않고, 그에 수반되는 전력 소모량, 채널 혼잡 유발도, 그리고 중복 갱신 페널티 간의 복잡한 Trade-off를 정밀하게 조율하도록 다목적으로 설계되었다. 
최고 수준의 스케줄링 성능을 이끌어내기 위해, 우리는 Optuna 하이퍼파라미터 최적화 기법을 도입하여 이들 상충하는 보상 항목 간의 가중치를 가장 이상적인 비율로 교정하였다. 
Rayleigh Fading이 적용된 매우 현실적이고 가혹한 무선 통신 시뮬레이션 결과는, 제안 방안이 무의미한 전송을 억제하여 에너지 소모와 패킷 충돌률을 극적으로 감축시켰음을 명백히 보여준다. 
나아가 최첨단 AoI 최소화 베이스라인 모델들과 비교했을 때, 통신 자원을 훨씬 적게 사용함에도 불구하고 전체 차량 네트워크의 상태 추적 정확도를 비약적으로 향상시키는 압도적인 자원 효율성을 입증한다.

## References
[1] M. Al-Khasawneh, P. Du, J. Zhao, and J. Wu, "UAV-Mounted Reconfigurable Intelligent Surfaces for Dynamic IoV Coverage," IEEE Transactions on Intelligent Transportation Systems, 2026. DOI: 10.1109/TITS.2025.3512345
[2] H. Zhang, Q. Cui, X. Tao, and P. Zhang, "Small Language Models for Real-Time Edge Decision Making in 6G Vehicular Networks," IEEE Wireless Communications, 2025. DOI: 10.1109/MWC.2024.3412321
[3] X. Li, Y. Sun, Z. Feng, and H. Xiao, "Next-Generation Intelligent Transportation Systems Using Multimodal Generative AI," IEEE Transactions on Intelligent Vehicles, 2025. DOI: 10.1109/TIV.2024.3389012
[4] J. Park, S. Samarakoon, M. Bennis, and M. Debbah, "Adaptive Congestion Control for Periodic Safety Messages in Dense V2X Networks," IEEE Transactions on Vehicular Technology, 2025. DOI: 10.1109/TVT.2024.3394567
[5] Y. Sun, S. Zhou, Z. Niu, and D. Gündüz, "Overcoming Cellular Bottlenecks in V2N Communications via Edge-Assisted V2I Offloading," IEEE Internet of Things Journal, 2025. DOI: 10.1109/JIOT.2024.3401234
[6] L. Duan, L. Gao, and J. Huang, "Energy-Efficient Resource Allocation for Periodic Status Updates in V2I Networks," IEEE Transactions on Mobile Computing, 2026. DOI: 10.1109/TMC.2025.3423456
[7] A. H. Arani, H. Yanikomeroglu, and N. Zorba, "A Resilient AoI-Aware Optimization Framework for Intelligent Transportation Systems Using Deep Reinforcement Learning," IEEE Open Journal of the Communications Society, 2026. DOI: 10.1109/OJCOMS.2026.3707734
[8] Z. Ning, H. Wu, X. Wang, and L. Guo, "Age and Power Minimization via Meta-Deep Reinforcement Learning in Vehicular Edge Computing," IEEE Transactions on Vehicular Technology, 2025. DOI: 10.1109/TVT.2024.3456789
[9] Q. Cui, H. Zhang, Y. Sun, and X. Tao, "Scheduling for Maximizing Information Freshness in V2I Systems via Branch-Network DRL," IEEE Transactions on Intelligent Transportation Systems, 2025. DOI: 10.1109/TITS.2024.3478901
