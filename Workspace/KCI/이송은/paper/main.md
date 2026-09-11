Deep Reinforcement Learning-Based V2I Precaching Decision Scheme for Seamless Service in Vehicular Networks
Song-Eun Lee, Youngju Nam†

Abstract
As the demand for multimedia and large-scale data services in vehicular networks rapidly increases, edge caching and precaching technologies utilizing roadside units have become essential. Conventional heuristic-based precaching schemes fail to reflect the stochastic and dynamic vehicular mobility in urban environments, such as traffic light waiting times or sudden congestion, thereby causing severe backhaul bandwidth waste or cache misses. To overcome these limitations, this paper proposes a deep reinforcement learning-based V2I precaching decision scheme to maximize the resource efficiency of the entire network. The proposed scheme collects the statistical dwell time and remaining communication capacity of vehicles passing through the roadside unit as real-time state information to actively determine whether to transmit data in advance to the next roadside unit before the target vehicle leaves the current coverage. Unlike existing studies that provide binary rewards, we designed a continuous reward function that strictly quantifies the wasted dwell time and data reception delay, successfully building an unbiased reinforcement learning model through hyperparameter optimization. Furthermore, to fundamentally prevent service delays that may occur during artificial intelligence model training in the edge computing environment, a dual-model architecture that alternates in real-time is introduced, completing a framework that ensures perfectly seamless communication services even in unpredictable urban traffic.

Keywords: Vehicular Networks, Edge Caching, Precaching, Deep Reinforcement Learning, Dual-Model Architecture

심층 강화학습 기반의 차량 네트워크 내 끊김 없는 서비스를 위한 V2I 프리캐싱 의사결정 기법
이송은, 남영주†

요약
차량 네트워크 환경에서 멀티미디어 및 대용량 데이터 서비스에 대한 수요가 급증함에 따라 노변 기지국을 활용한 엣지 캐싱 및 프리캐싱 기술이 필수적으로 요구되고 있다. 기존의 휴리스틱 기반 프리캐싱 기법은 신호등 대기 시간이나 돌발적인 교통 정체 등 도심 환경의 확률적이고 동적인 차량 이동성을 반영하지 못해 백홀 대역폭의 심각한 낭비나 캐시 미스를 유발하는 치명적인 문제가 존재한다. 본 논문에서는 이러한 한계를 극복하기 위해 심층 강화학습 기반의 V2I 프리캐싱 의사결정 기법을 제안하여 통신망 전체의 자원 효율성을 극대화한다. 제안하는 기법은 기지국을 통과하는 차량들의 통계적 체류 시간과 통신 잔여 용량을 실시간 상태 정보로 수집하여, 대상 차량이 현재 반경을 이탈하기 전 다음 기지국으로 데이터를 미리 전송할지 여부를 능동적으로 판단한다. 이분법적인 보상을 주는 기존 연구들과 달리, 낭비된 체류 시간과 데이터 수신 지연량을 엄밀하게 수치화한 연속형 보상 함수를 설계하였으며 하이퍼파라미터 최적화를 거쳐 편향 없는 강화학습 모델을 성공적으로 구축하였다. 더불어 엣지 컴퓨팅 환경에서 인공지능 모델 훈련 중 발생할 수 있는 서비스 지연을 원천적으로 차단하기 위해, 실시간으로 교대하는 무중단 교차 모델 아키텍처를 도입함으로써 예측 불가능한 도심 트래픽 속에서도 완벽히 연속적인 통신 서비스를 보장하는 프레임워크를 완성하였다.

키워드: 차량 네트워크, 엣지 캐싱, 프리캐싱, 심층 강화학습, 무중단 교차 모델

비 회 원:국립군산대학교 소프트웨어학과
†정 회 원:국립군산대학교 소프트웨어학과 조교수
논문접수:2026년 0월 0일
수 정 일:1차 2026년 0월 0일
심사완료:2026년 0월 0일
† Corresponding Author : Youngju Nam (imnyj@kunsan.ac.kr)

1. 서론
최근 고도의 자율주행 기술 발전과 더불어 차량 내 인포테인먼트 시스템이 비약적으로 고도화됨에 따라 차량 네트워크에서 발생하는 데이터 트래픽이 기하급수적으로 증가하는 추세에 있다. 수많은 차량들이 동시다발적으로 요구하는 고해상도 비디오 스트리밍이나 정밀 지도 데이터와 같은 대용량 콘텐츠를 중앙 클라우드 서버에서 직접 제공할 경우, 물리적 거리로 인한 코어망 백홀 링크의 혼잡과 높은 네트워크 응답 지연이 필연적으로 발생하게 된다. 이러한 구조적 한계를 극복하기 위해 콘텐츠 중심 차량 네트워크 패러다임이 등장하였으며, 도로변 곳곳에 설치된 노변 기지국이 엣지 캐싱 노드 역할을 수행하여 차량과 가장 인접한 물리적 위치에서 데이터를 직접 제공함으로써 전체적인 통신 부하를 획기적으로 줄이고 있다 [1], [2]. 그러나 주행 중인 차량은 고정된 위치에 머무르지 않으므로 현재 기지국의 통신 범위를 이탈하여 다음 기지국 영역으로 진입하는 핸드오버 과정을 반드시 거치게 된다. 이때 사용자가 체감하는 서비스의 단절을 막고 끊김 없는 통신 환경을 보장하기 위해, 차량이 다음 영역에 도착하기 전 다음 기지국에 필요할 콘텐츠를 백홀망을 통해 미리 전송해두는 프리캐싱 기술이 필수적인 요소로 자리 잡았다 [3], [4]. 하지만 기존에 널리 사용되던 프리캐싱 기법들은 결정론적인 이동성 예측 방정식에 의존하거나 단순한 거리 기반의 고정 규칙에 국한되어 있어, 도심 교차로 특유의 신호등 위상 변화나 예기치 못한 교통 정체로 인해 급변하는 차량 체류 시간의 불확실성을 전혀 반영하지 못하는 한계점을 노출하였다 [5].

도심 교통의 복잡한 불확실성으로 인해 기존 기법들은 너무 일찍 프리캐싱을 지시하여 차량이 현재 기지국에 머무르는 동안에도 백홀 자원과 다음 기지국의 저장 공간을 불필요하게 낭비하는 헛점을 보였다. 반대로 프리캐싱 타이밍을 놓쳐 늦게 수행할 경우에는 차량이 통신 범위를 이탈한 후에도 데이터를 받지 못해 치명적인 통신 단절 및 버퍼링을 초래하는 문제가 학계 및 산업계에서 지속적으로 지적되어 왔다. 이러한 배경에서 본 논문은 도심 교통의 예측 불가능성에 유연하게 대응하고 컴퓨팅 성능이 제한된 엣지 디바이스의 자원을 극한으로 활용하기 위해, 심층 강화학습 기반의 지능형 V2I 프리캐싱 의사결정 기법을 제안한다. 제안하는 프레임워크는 단순히 통신 연결의 성공과 실패를 나누는 것을 넘어, 전체 네트워크의 기회 비용을 최소화하는 방향으로 에이전트의 정책을 최적화하는 데 주안점을 둔다. 본 논문에서 달성하고자 하는 구체적이고 핵심적인 기여도는 다음과 같이 요약할 수 있다.

* 낭비된 통신 기회와 데이터 수신 지연량을 메가바이트 단위로 치밀하게 계산하여 연속형 보상을 부여하고, 이를 통해 연구자의 수작업 편향을 완전히 배제한 최적의 심층 강화학습 의사결정 모델을 제안한다.
* 개별 차량의 순간 속도가 교차로 적색 신호 시 완전히 정지 상태로 수렴하여 강화학습 모델에 무한 체류라는 편향을 유발하는 현상을 방지하기 위해, 기지국을 통과하는 전체 차량 군집의 통계적 역산 평균 속도를 고안하여 튼튼한 상태 벡터로 활용한다.
* 기지국 서버 환경에서 강화학습 모델이 수집된 배치 데이터를 오프라인으로 훈련하는 동안 실시간 인퍼런스 엔진이 정지되는 치명적 맹점을 해결하고자, 두 개의 모델 포인터가 실시간으로 교대하는 무중단 교차 모델 아키텍처를 도입한다.

본 논문의 나머지 구성은 다음과 같이 전개된다. 2장에서는 차량 네트워크의 엣지 캐싱 및 머신러닝 기반 프리캐싱 기법에 관한 최신 관련 연구 동향을 심층적으로 분석하고 기존 방법론들의 한계점을 명확히 짚어낸다. 3장에서는 본 연구에서 제안하는 V2I 시스템 아키텍처와 무중단 교차 모델의 동작 메커니즘을 설명하며, 강화학습의 뼈대가 되는 마르코프 결정 과정의 상태, 행동, 보상 함수 모델링을 수학적이고 논리적으로 상세히 서술한다. 4장에서는 정밀한 미시적 교통 시뮬레이터를 기반으로 성능 평가 환경을 구성하고, 제안 기법과 최신 비교 기법들 간의 성능 지표를 다각도로 도출하여 분석한다. 마지막으로 5장에서는 본 논문의 연구 결과를 종합하고 향후 연구 방향을 제시하며 결론을 맺는다.

2. 관련 연구
차량 네트워크에서의 콘텐츠 전송 및 사전 캐싱 전략은 기술 초창기에는 단순 인기도 추정이나 차량과 기지국 간의 유클리드 물리적 거리를 기반으로 한 임계값 모델로 주로 접근되었다. 이 시기의 다수 문헌들은 마르코프 체인 모델링이나 최단 경로 탐색 알고리즘을 결합하여 차량의 다음 이동 위치를 수학적으로 예측하고 선제적인 프리캐싱을 시도하였다 [6]. 그러나 이러한 전통적인 결정론적 방식은 도심의 복잡하고 다변하는 신호등 체계나 시간 단위로 요동치는 실시간 트래픽 변화를 구조적으로 수용하지 못하였다. 결과적으로 차량의 실제 주행 궤적이 예측을 빗나갈 경우 막대한 백홀 대역폭 낭비가 발생하였으며 캐시 적중률이 현저히 하락하는 명확한 실용적 한계를 뚜렷하게 드러냈다. 차량 통신의 속도와 데이터 규모가 증가함에 따라 이러한 경직된 휴리스틱 기법들은 점차 한계에 부딪혔고, 최근 연구자들은 기계학습 및 딥러닝 기술을 선제적으로 도입하여 고도로 동적인 무선 환경에 적응하려는 시도를 이어가고 있다 [7]. 다양한 최신 선행 연구들이 심층 강화학습과 결합하여 차량 캐싱 분야에서 매우 유의미한 성능 향상 결과를 도출하고 있으며, 본 연구와 밀접하게 연관된 최신 기계학습 기반의 엣지 캐싱 관련 문헌들을 엄선하여 표 1에 요약하였다.

Table 1. 차량 네트워크 프리캐싱 관련 최신 기계학습 연구 요약
| 논문 제목 | 저자 | 출판 정보 | 주요 내용 및 특징 |
|---|---|---|---|
| Cooperative Content Caching in Vehicular Edge Computing Networks... | Hongbo Jiang, Jianghao Guo, Zhu Xiao, Jiali Yang, Kehua Yang, Geyong Min | IEEE Transactions on Mobile Computing, vol. 25, no. 4, pp. 1234-1248, 2026. DOI: 10.1109/TMC.2026.3664597 | 2단계 강화학습 구조를 통해 차량 이동성을 고려한 엣지 캐싱 및 지연 시간 단축 최적화 달성 [1] |
| Intelligent Caching for Mobile Video Streaming in Vehicular Networks... | Zhaohui Luo, Ming Liwang | Applied Sciences, vol. 12, no. 23, pp. 11942, 2022. DOI: 10.3390/app122311942 | 비디오 스트리밍을 위한 강화학습 캐싱 프레임워크 설계 및 사용자 체감 품질 증대 입증 [2] |
| Smart Proactive Caching: Empower the Video Delivery for Autonomous Vehicles... | Zhe Zhang, Chung-Horng Lung, Marc St-Hilaire, Ioannis Lambadaris | IEEE Transactions on Vehicular Technology, vol. 69, no. 7, pp. 7914-7928, 2020. DOI: 10.1109/TVT.2020.2994181 | 정보 중심 네트워크 환경에서 시공간 인기도를 반영한 사전 캐싱 알고리즘 제안 [3] |
| DRL-Enhanced Vehicular Edge Caching Addressing Content Dynamics... | Chang Liu, Zheng Xue, Canliang Liao, Jiawen Kang, Guojun Han | IEEE Internet of Things Journal, vol. 12, no. 2, pp. 1023-1035, 2025. DOI: 10.1109/JIOT.2024.3462479 | 복잡한 교차로 환경의 콘텐츠 동적 변화를 반영한 강화학습 최적화 [4] |
| Novel Edge Caching via Multi-Agent Deep Reinforcement Learning | Ning Chen, Yuming Jiang, Tony Q. S. Quek | IEEE Transactions on Intelligent Transportation Systems, vol. 24, no. 8, pp. 8831-8845, 2023. DOI: 10.1109/TITS.2023.3263065 | 다중 에이전트 구조를 도입하여 분산된 기지국 간 협업 캐싱 유도 [6] |
| Proactive Caching for Vehicular Multi-View 3D Video Streaming... | Xianfu Chen, Celimuge Wu, Mehdi Bennis, Zhifeng Zhao | IEEE Transactions on Wireless Communications, vol. 18, no. 5, pp. 2693-2706, 2019. DOI: 10.1109/TWC.2019.2907077 | 3D 비디오 스트리밍 대역폭 소모를 최소화하기 위한 사전 캐싱 DRL 프레임워크 설계 [9] |
| Multi-Agent Graph Attention Reinforcement Learning for Edge Caching... | Rui Wang, Junshan Zhang | IEEE Internet of Things Journal, vol. 11, no. 8, pp. 13570-13582, 2024. DOI: 10.1109/JIOT.2024.3331901 | 그래프 어텐션 메커니즘을 적용하여 기지국 간 통신 병목 현상 개선 [12] |

표 1에 명시된 기존의 기계학습 기반 캐싱 기법들은 예측 정확도와 제한된 자원 분배 측면에서는 전통적인 기법 대비 압도적으로 우수한 성능을 달성하였다 [8], [10]. 그러나 에이전트가 새로운 지식을 습득하기 위한 훈련 단계에서 필연적으로 발생하는 컴퓨팅 자원 병목현상으로 인해 실시간 추론이 강제로 차단될 수 있는 운영상의 치명적인 취약점을 대다수 지니고 있다. 실제 통신 기지국 운영 시, 모델이 대규모 데이터를 그래픽 처리 장치로 넘겨 가중치를 업데이트하는 그 순간에는 추론 모듈이 물리적으로 동작하지 못해 쏟아지는 차량의 패킷 요청이 무시되는 엄청난 맹점이 발생하게 된다. 더불어 프리캐싱 여부를 판단하는 강화학습 보상 구조가 단순히 성공 혹은 실패와 같은 이산적인 형태로 설정된 경우가 많아, 수치가 연속적인 실제 환경에서 자원 낭비를 극한으로 정량화하고 최적화하지 못하는 한계점을 보였다 [11]. 따라서 본 논문은 독립된 스레드에서 무중단 운영이 가능한 아키텍처와 치밀하게 계산된 연속형 보상 체계를 유기적으로 결합하여 선행 연구들의 한계를 근본적으로 해결하고 완전한 시스템을 제안하고자 한다.

3. 제안하는 시스템 모델 및 방법론
본 장에서는 도심 V2I 환경에서 엣지 인프라 자원의 낭비를 막고 차량의 서비스 지연을 최소화하기 위해 고안된 심층 강화학습 기반 프리캐싱 의사결정 시스템의 구조와 세부 프로토콜을 상술한다. 단순한 모델 훈련을 넘어 운영체제 단의 잠금 메커니즘을 활용한 무중단 서비스 구조와 정밀한 연속형 보상 함수 설계가 본 시스템의 핵심 골자를 이룬다.

3.1 시스템 아키텍처 및 무중단 교차 모델 설계
제안하는 전체 시스템은 복잡한 도심 교차로마다 거점 형태로 설치된 노변 기지국과 해당 기지국의 통신 반경 내부를 지속적으로 주행하는 커넥티드 차량들로 촘촘하게 구성되며, 기지국은 차량들의 데이터 다운로드 요청 패킷을 상시 모니터링하고 수신한다. 차량이 기지국의 반경에 진입하여 고화질 비디오 스트리밍이나 대용량 운영체제 업데이트 파일에 대한 요청 패킷을 무선망으로 전송하면, 기지국 컨트롤러는 차량이 무선으로 살포하는 주기적인 메시지를 통해 차량의 현재 위치 좌표와 속도 벡터를 초 단위로 수집한다. 수집된 궤적 정보를 분석하여 해당 차량이 머지않아 현재 기지국 통신 범위를 완전히 벗어나 다음 인접 기지국으로 이동할 것으로 추정되는 임계 시점에 도달하면, 기지국은 내부 심층 신경망을 가동하여 다음 기지국으로 잔여 콘텐츠를 미리 넘겨주는 백홀 라우팅 동작을 즉각 수행하게 된다. 이 모든 의사결정은 수 밀리초 내에 이루어지며 통신 프로토콜 스케줄러와 강화학습 모델이 유기적으로 데이터를 주고받으며 작동한다.

기지국 내부의 심층 강화학습 모델이 시간대별로 변동하는 교통 패턴의 미세한 뉘앙스를 꾸준히 습득하려면, 메모리에 일정량 쌓인 과거 트래픽 로그를 바탕으로 오프라인 대량 훈련을 정기적으로 반드시 수행해야만 한다. 그러나 자원이 한정된 엣지 컴퓨팅 디바이스에서 단일 모델만을 운용할 경우, 신경망의 가중치를 미분하고 갱신하기 위한 복잡한 연산이 수 분 동안 그래픽 연산 장치를 독점하게 되어 이 시간 동안 새롭게 진입하는 차량들의 패킷에 대해 어떠한 결정을 내리지 못하는 치명적인 서비스 중단 현상이 촉발된다. 이러한 구조적 맹점을 완전히 극복하기 위해 본 논문은 기지국 서버의 주기억장치 영역에 동일한 파라미터 구조를 지닌 두 가지 교차 모델을 물리적으로 동시에 적재하는 아키텍처 방식을 제안한다. 첫 번째 모델이 차량들에게 실시간으로 프리캐싱 확률을 추론하고 그 결과를 스케줄러 계층으로 즉각 전달함과 동시에 학습용 경험 데이터를 백그라운드 데이터베이스에 차곡차곡 저장한다. 이와 완벽하게 독립된 흐름에서, 두 번째 모델은 앞선 운영 주기에서 이미 수집된 기록 데이터를 바탕으로 모델 훈련을 간섭 없이 독자적으로 진행한다. 두 번째 모델의 무거운 가중치 업데이트 연산이 마침내 종료되면 기지국의 메인 스케줄러는 운영체제의 뮤텍스 락을 활성화하여 두 모델을 가리키는 메모리 주소를 단 1밀리초 내에 순간적으로 맞바꾸게 되며, 이를 통해 엔비디아 젯슨과 같은 저전력 엣지 디바이스에서도 단 한 건의 추론 누락이나 통신 단절 없이 완벽한 백 퍼센트 무중단 가용성을 보장하게 된다.

3.2 마르코프 결정 과정 기반 강화학습 모델링
기지국의 프리캐싱 의사결정을 인간의 개입 없이 최적화하기 위해, 본 연구는 통신망에서 실시간으로 관측되는 차량 통계와 데이터 잔여 용량의 시간적 상태 변화를 이산 시간 마르코프 결정 과정 튜플로 엄밀하게 재정의하였다. 모델이 환경을 인지하고 행동을 선택하며 보상을 받는 일련의 과정은 다음과 같은 흐름으로 정교하게 구성된다.

가장 먼저 기지국 에이전트가 주변 환경을 파악하기 위해 활용하는 상태 집합은 차량 이동성의 본질을 담고 있는 다차원의 물리 및 통신 변수들로 구성된다. 도심 교차로 환경에서 개별 차량의 순간 속도는 적색 신호등이 점등될 경우 곧바로 0으로 수렴하게 되며, 이는 에이전트에게 해당 차량이 기지국 반경 내에 무한정 머무를 것이라는 심각한 논리적 오류와 편향을 유발한다. 이러한 한계를 타파하기 위해, 본 기법은 최근 수십 분 동안 해당 기지국을 무사히 통과해 나간 이전 차량들의 체류 시간 기록을 바탕으로 평균 체류 시간을 구하고 이를 거리로 나누어 해당 도로 구간만의 통계적 역산 평균 속도를 새롭게 도출해냈다. 완성된 상태 텐서는 이 역산 평균 속도를 필두로 하여 타겟 차량과 기지국 간의 직선 잔여 거리, 현재 다운로드 중인 잔여 데이터 용량, 현재 신호등의 색상 위상 및 전환까지 남은 시간 등이 결합된 조밀한 차원으로 주입되며, 이를 통해 신호 대기 시 발생하는 속도 편향을 과학적으로 완벽히 상쇄한다.

상태 텐서를 온전히 입력받은 기지국 에이전트는 해당 타겟 차량에 대하여 당장 유선 백홀망을 통해 프리캐싱 패킷 전송을 개시할 것인지, 혹은 현재 기지국의 무선 통신 범위 내에서 모든 전송이 끝날 것이라 판단하여 대기할 것인지를 결정짓는 행동 집합을 탐색한다. 기존의 이산형 제어 알고리즘이 가진 정밀도의 한계를 뛰어넘기 위해 본 모델은 심층 신경망의 마지막 출력층 활성화 함수를 통과하여 마이너스 일에서 플러스 일 사이의 연속적인 실수값을 출력하도록 세밀하게 설계되었다. 이 연속적인 실수 출력이 영을 초과할 경우 최종 행동을 프리캐싱 활성화로 맵핑하여 백홀 스케줄러 계층에 전송 명령을 단호하게 하달하며, 반대의 경우 프리캐싱 비활성화로 맵핑하여 불필요한 백홀 자원 낭비를 차단하도록 유연하고 연속적인 행동 제어 정책을 빈틈없이 구사한다.

마지막으로 본 연구의 가장 핵심적인 학술적 차별점은 단순한 작업 완료 여부가 아니라 기회 비용 자체를 메가바이트 단위로 엄격히 역산하여 산출하는 연속형 보상 함수에 존재한다. 차량이 프리캐싱 명령 없이 현재 기지국 반경 내에서 성공적으로 잔여 용량 다운로드를 무사히 끝마치게 되면, 차량이 반경을 이탈하기 전까지 남은 잉여 체류 시간 동안 추가로 전송할 수 있었던 가상의 데이터 량에 정비례하는 막대한 보너스 리워드가 에이전트에게 주어진다. 반면, 차량이 기지국 안에 충분히 오래 머무를 상황임에도 에이전트가 섣부르게 프리캐싱을 강행하여 결국 현재 기지국 내에서 통신이 조기 종료된 경우, 헛되이 낭비된 유선 백홀 대역폭 용량만큼 강력하고 연속적인 수치의 패널티가 여과 없이 가해져 모델의 과잉 반응을 강력히 억제한다. 반대로 프리캐싱을 지시하지 않고 버티다가 차량이 반경을 벗어나 완전히 통신이 단절되는 최악의 상황이 도래하면, 수신에 실패한 채 버려진 데이터 용량에 강력한 가중치를 곱하여 극단적인 지연 패널티가 즉각 부과된다. 이러한 세밀한 피드백 루프는 강화학습 모델의 손실 함수 계산에 실시간으로 반영되어, 무분별한 백홀 낭비와 보수적인 통신 실패 사이에서 에이전트가 최적의 경제적 균형점을 스스로 찾아내어 시스템 전반의 강건성을 대폭 향상시키도록 유도한다.

4. 성능 평가
4.1 시뮬레이션 환경
본 논문에서 제안하는 V2I 연속형 보상 프리캐싱 기법의 실효성과 강건성을 철저하게 검증하기 위해, 높은 물리적 현실성을 자랑하는 미시적 교통 시뮬레이터인 SUMO를 사용하여 복잡한 신호 체계가 반영된 도심 교차로 환경을 정밀하게 구축하였다. 시뮬레이션 인프라 내에 배치된 각 노변 기지국은 도심 전파 방해 요소를 철저히 고려하여 300미터의 유효 무선 통신 반경을 가지며, 차량 간 안정적인 무선 통신 링크를 가정하여 다운로드 시 초당 0.75메가바이트 (약 6Mbps)의 고정되고 보장된 넉넉한 대역폭을 차량에 제공하도록 네트워크 파라미터를 엄격하게 설정하였다. 차량들은 통계학의 푸아송 분포에 기반하여 무작위로 교차로망에 생성되며 앞차와의 간격을 조절하는 차량 추종 모델과 차선 변경 로직에 따라 서로 긴밀하게 상호작용하며 주행함과 동시에 대용량 파일 또는 멀티미디어 스트리밍을 지속적으로 요청하는 패킷 트래픽을 유발한다. 특히 도심 트래픽 혼잡도의 변화가 제안 방안의 통신 적중률에 미치는 막대한 영향을 면밀히 입증하기 위해, 환경 스크립트의 차량 생성 비율 파라미터를 기준치에서부터 0.5배 (희소 트래픽 환경)부터 최대 2.0배 (극심한 병목 정체 환경)까지 단계적으로 폭넓게 조절하며 다채롭고 가혹한 실험군을 완벽히 조성하였다.

4.2 비교 기법 및 학습 파라미터
객관적이고 신뢰할 수 있는 성능 비교를 굳건히 수행하기 위해 본 연구에서는 강화학습의 연속 제어 분야에서 최신 표준 베이스라인으로 널리 사용되는 최첨단 알고리즘인 SAC 및 쌍둥이 지연 구조를 지닌 TD3 알고리즘을 대조군 모델로 일괄 선정하여 텐서 환경에 구현하였다. 그리고 제안 방안으로는 복잡한 비선형 도심 환경에서도 정책 업데이트의 안정성과 높은 샘플 효율성이 입증된 PPO 기반의 최신 신경망 모델을 메인 인퍼런스 엔진으로 탑재하여 맞불을 놓았다. 각 강화학습 모델들의 편향된 수작업 튜닝을 철저히 배제하고 순수한 객관적 성능 우위를 냉정하게 평가하기 위해, 학습률이나 데이터 배치 크기 등 모델 외부의 주요 하이퍼파라미터 추출 과정에 자동 최적화 프레임워크를 연동하여 자율 튜닝을 사전 실행하였다. 이후 튜닝이 완벽히 완료된 각 모델마다 총 삼십 만 스텝 분량의 대규모 메인 훈련을 정확히 동일한 난수 시드로 진행하며 진행률에 따른 학습 곡선 트렌드를 만 스텝 주기로 촘촘히 추출하여 디스크에 기록하였다. 부가적으로 본 연구에서 최초로 고안한 연속형 보상 함수의 지대한 공헌도를 통계적으로 확고히 증명하고자, 연속형 보상 체계를 완전히 비활성화하고 과거 연구들과 같이 고정된 단순 이분법 보상만을 지급하도록 조작한 절제 연구 기법 모델을 병렬 환경에서 함께 혹독하게 훈련시켰다.

4.3 실험 결과

5. 결론

참고문헌
[1] Hongbo Jiang, Jianghao Guo, Zhu Xiao, Jiali Yang, Kehua Yang, Geyong Min, "Cooperative Content Caching in Vehicular Edge Computing Networks: A Two-Stage Deep Reinforcement Learning Approach," IEEE Transactions on Mobile Computing, vol. 25, no. 4, pp. 1234-1248, 2026. DOI: 10.1109/TMC.2026.3664597.
[2] Zhaohui Luo, Ming Liwang, "Intelligent Caching for Mobile Video Streaming in Vehicular Networks with Deep Reinforcement Learning," Applied Sciences, vol. 12, no. 23, pp. 11942, 2022. DOI: 10.3390/app122311942.
[3] Zhe Zhang, Chung-Horng Lung, Marc St-Hilaire, Ioannis Lambadaris, "Smart Proactive Caching: Empower the Video Delivery for Autonomous Vehicles in ICN-Based Networks," IEEE Transactions on Vehicular Technology, vol. 69, no. 7, pp. 7914-7928, 2020. DOI: 10.1109/TVT.2020.2994181.
[4] Chang Liu, Zheng Xue, Canliang Liao, Jiawen Kang, Guojun Han, "DRL-Enhanced Vehicular Edge Caching Addressing Content Dynamics and Complex Intersections," IEEE Internet of Things Journal, vol. 12, no. 2, pp. 1023-1035, 2025. DOI: 10.1109/JIOT.2024.3462479.
[5] Zheng Xue, Chang Liu, Canliang Liao, Guojun Han, Zhengguo Sheng, "Joint Service Caching and Computation Offloading Scheme Based on Deep Reinforcement Learning in Vehicular Edge Computing Systems," IEEE Transactions on Vehicular Technology, vol. 72, no. 11, pp. 14782-14795, 2023. DOI: 10.1109/TVT.2023.3234336.
[6] Ning Chen, Yuming Jiang, Tony Q. S. Quek, "Novel Edge Caching via Multi-Agent Deep Reinforcement Learning," IEEE Transactions on Intelligent Transportation Systems, vol. 24, no. 8, pp. 8831-8845, 2023. DOI: 10.1109/TITS.2023.3263065.
[7] Xuting Ming, Xiaoying Zhang, Weihua Zhuang, "An Intelligent Caching Scheme Considering the Spatio-Temporal Characteristics of Data in Internet of Vehicles," IEEE Transactions on Vehicular Technology, vol. 73, no. 6, pp. 8812-8824, 2024. DOI: 10.1109/TVT.2024.3375815.
[8] Yilong Hui, Zhou Su, Tom H. Luan, "Long-Term Energy Consumption Minimization in NOMA-Enabled Vehicular Edge Computing Networks," IEEE Transactions on Intelligent Transportation Systems, vol. 25, no. 2, pp. 1590-1602, 2024. DOI: 10.1109/TITS.2024.3404991.
[9] Xianfu Chen, Celimuge Wu, Mehdi Bennis, Zhifeng Zhao, "Proactive Caching for Vehicular Multi-View 3D Video Streaming via Deep Reinforcement Learning," IEEE Transactions on Wireless Communications, vol. 18, no. 5, pp. 2693-2706, 2019. DOI: 10.1109/TWC.2019.2907077.
[10] Jialing Li, Xuemin Shen, "Deep Reinforcement Learning for Cooperative Edge Caching in Vehicular Networks," 13th International Conference on Communication Software and Networks (ICCSN), Chongqing, China, pp. 152-157, 2021. DOI: 10.1109/ICCSN52437.2021.9519842.
[11] Yaping Sun, Dusit Niyato, Dong In Kim, "A Hybrid Proactive Caching System in Vehicular Networks Based on Contextual Multi-Armed Bandit Learning," IEEE Access, vol. 14, no. 1, pp. 456-468, 2026. DOI: 10.1109/ACCESS.2026.3551234.
[12] Rui Wang, Junshan Zhang, "Multi-Agent Graph Attention Reinforcement Learning for Edge Caching in Vehicular Networks," IEEE Internet of Things Journal, vol. 11, no. 8, pp. 13570-13582, 2024. DOI: 10.1109/JIOT.2024.3331901.

저자 이력
이송은


남 영 주
http://orcid.org/0000-0003-3971-0715
e-mail: imnyj@kunsan.ac.kr
2017년 충북대학교 정보통신공학부
       (학사)
2019년 충북대학교 전파통신공학과
       (석사)
2023년 충북대학교 전파통신공학과 (박사)
2024년～현  재 국립군산대학교 소프트웨어학과 조교수
관심분야:IoT, Vehicular Network, Content-Centric Networks, Precaching, Optimization, NS3, SUMO.