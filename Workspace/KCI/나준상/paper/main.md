Deep Reinforcement Learning-Based Multiple V2V Precaching Decision Scheme for Overcoming Communication Outage Zones
Jun-Sang Na, Young-Ju Nam†

ABSTRACT
In urban vehicular network environments, communication outage zones where the radio waves of roadside units are completely disconnected inevitably occur due to large buildings, complex tunnels, or geographical obstructions. The conventional V2I single communication method relying solely on base stations cannot avoid severe service delays and packet drops during large-capacity multimedia streaming or high-resolution autonomous driving data downloads in these outage zones. To guarantee perfectly continuous data reception for vehicles forcibly entering communication outage zones, this paper proposes a deep reinforcement learning-based V2V precaching decision scheme. Instead of focusing solely on the target vehicle, the proposed scheme dynamically groups multiple candidate vehicles driving on the surrounding roads into a single communication cluster and preemptively broadcasts the data to these candidates before the target vehicle leaves the base station radius. The base station agent carefully collects the real-time relative distance, speed variance, and statistical cluster density indicators between surrounding vehicles and the target vehicle as state information to precisely infer the optimal V2V precaching timing while fundamentally preventing reckless backhaul bandwidth waste. In particular, we successfully achieved unbiased reinforcement learning model optimization by quantifying the actual delay time occurring during communication disconnection and the wasted resource amount due to unnecessary broadcasting in megabyte units to construct a continuous reward function. Additionally, we completed a framework capable of seamless service under any traffic congestion by introducing a dual-model architecture inside the low-power base station computing server, which fundamentally prevents inference delays caused by artificial intelligence model training.

Keywords: Vehicular Networks, V2V Communication, Precaching, Communication Outage Zone, Deep Reinforcement Learning

통신 음영 지역 극복을 위한 심층 강화학습 기반 다중 V2V 프리캐싱 의사결정 기법
나준상, 남영주†

비 회 원:국립군산대학교 소프트웨어학과
†정 회 원:국립군산대학교 소프트웨어학과 조교수
논문접수:2026년 0월 0일
수 정 일:1차 2026년 0월 0일
심사완료:2026년 0월 0일
† Corresponding Author : Youngju Nam (imnyj@kunsan.ac.kr)

요약
도심 차량 네트워크 환경에서는 대형 건물, 복잡한 터널, 혹은 지형적 가림 요인으로 인해 노변 기지국의 전파 통신이 완전히 단절되는 음영 지역이 필연적으로 광범위하게 발생한다. 기존에 의존해온 기지국-차량 간의 V2I 단일 통신 방식만으로는 이러한 음영 지역에서 대용량 멀티미디어 스트리밍이나 고해상도 자율주행 데이터 다운로드 시 발생하는 심각한 서비스 지연과 패킷 드롭을 결코 피할 수 없다. 본 논문에서는 통신 음영 지역에 강제적으로 진입하는 차량의 연속적인 데이터 수신을 완벽히 보장하기 위해, 심층 강화학습 기반의 V2V 프리캐싱 의사결정 기법을 새롭게 제안한다. 제안하는 기법은 대상 차량 한 대만을 고집하는 대신 주변 도로를 함께 주행 중인 다수의 후보 차량들을 하나의 통신 군집으로 묶고, 타겟 차량이 기지국의 반경을 벗어나기 전 이 후보들에게 데이터를 미리 분산 브로드캐스트 전송해두는 구조를 치밀하게 취한다. 기지국 에이전트는 주변 차량들과 타겟 차량 간의 실시간 상대적 거리, 속도 편차, 그리고 통계적인 군집 밀도 지표를 상태 정보로 세밀하게 수집하여, 무분별한 백홀 대역폭 낭비를 원천적으로 방지하면서 최적의 V2V 프리캐싱 타이밍을 정밀하게 추론해낸다. 특히 통신 단절 시 실제로 발생하는 초 단위의 지연량과 불필요한 브로드캐스트로 인해 낭비된 자원량을 메가바이트 단위로 정확히 정량화하여 연속형 보상 함수를 구성함으로써, 연구자의 편향이 섞이지 않은 강화학습 모델 최적화를 달성하였다. 추가적으로 저전력 기지국 컴퓨팅 서버에서도 인공지능 모델 훈련에 따른 추론 지연을 원천 차단하는 교차 모델 아키텍처를 시스템 내부에 도입하여, 어떠한 교통 트래픽 폭주 상황에서도 완벽한 무중단 서비스가 가능한 프레임워크를 완성하였다.

키워드: 차량 네트워크, 차량 간 통신, 프리캐싱, 통신 음영 지역, 심층 강화학습

1. 서론
완전 자율주행 및 초연결 커넥티드 차량의 상용화가 본격화됨에 따라 현대의 차량 네트워크는 고해상도 동적 지도 다운로드, 실시간 멀티미디어 스트리밍, 대용량 운영체제 무선 업데이트 등 무거운 데이터 전송을 감당해야 하는 핵심 인프라로 굳건히 자리 잡고 있다 [1], [2]. 물리적으로 먼 중앙 클라우드 서버에서 이 모든 방대한 트래픽을 처리하는 것은 통신 지연을 기하급수적으로 유발하므로, 도로변에 촘촘히 설치된 노변 기지국들이 클라우드의 부하를 나누어 갖고 지연 시간을 최소화하기 위한 엣지 캐싱 노드로 매우 활발히 활용되고 있다 [3]. 그러나 현실의 도심 주행 환경에서는 빽빽하게 솟은 고층 건물들, 복잡하게 얽힌 다층 교차로, 길이가 긴 지하 터널 등으로 인해 기지국의 전파가 전혀 도달하지 못하는 통신 음영 지역이 예상치 못하게 빈번하게 나타난다. 원활하게 주행 중이던 차량이 기지국의 반경을 갑작스럽게 벗어나 이러한 음영 지역으로 진입하게 되면, 쾌적하게 진행 중이던 대용량 데이터 다운로드가 강제적으로 중단되고 끊기게 되어 탑승자의 사용자 체감 품질이 급격히 저하되는 치명적이고 고질적인 문제가 발생한다 [4], [5].

이러한 음영 지역에서의 통신 두절을 극복하기 위해, 기지국에만 의존하지 않고 차량 간 직접 통신인 V2V 방식을 적극 활용하여 주변 차량들을 일종의 이동형 분산 중계기로 사용하는 협력 통신 기법들이 학계에서 다각도로 연구되고 있다. 차량이 어두운 음영 지역에 진입하기 직전, 기지국이 해당 차량과 동일한 방향으로 나란히 주행하는 인접 차량들에게 필요한 잔여 데이터를 선제적으로 쏘아보내는 프리캐싱을 수행해두면, 타겟 차량이 기지국의 범위를 벗어나 음영 지역에 고립되더라도 주변을 에워싼 차량들로부터 무선 근거리 통신으로 데이터를 끊임없이 이어받을 수 있다. 하지만 기존에 통용되던 임계값 기반의 단순 휴리스틱 통신 기법들은 주변 차량들의 미세한 상대 속도 차이나 방향 전환으로 인한 군집의 급격한 이탈 가능성을 동적으로 계산해 내지 못하였다. 결과적으로 타겟 차량과 곧 멀어질 엉뚱한 차량에게 프리캐싱 데이터를 쏟아부어 유선 백홀 대역폭과 귀중한 기지국 메모리 자원만을 허무하게 낭비하는 치명적인 한계가 여실히 존재했다. 본 논문에서는 이러한 복잡다단한 다중 차량 군집의 비선형적인 이동성을 딥러닝 기반으로 실시간 분석하고 최적의 대안을 찾는 시스템을 설계하며, 다음과 같은 세 가지 핵심 기여도를 명확히 제공하고자 한다.

* 타겟 차량과 주변에 존재하는 수많은 후보 차량들 간의 상대적 거리, 순간적인 속도 편차, 그리고 군집의 결속 밀도를 수학적으로 압축된 통계 벡터로 모델링하여 기지국 에이전트의 상태 정보로 주입함으로써 통신 연결 유지 가능성을 정밀하게 학습한다.
* 다수의 후보를 향한 브로드캐스트로 낭비된 기지국의 통신 자원량과 다중 통신 협력으로 절약해 낸 실제 지연 시간을 단편적인 성공 및 실패가 아닌 메가바이트 단위의 연속적인 보상 함수로 수치화하여 에이전트의 성능을 극한으로 최적화한다.
* 기지국 서버 내에서 강화학습 모델이 가중치를 갱신하는 배치 학습을 수행하는 몇 분의 시간 동안 실시간 추론 엔진이 차단되는 치명적 현상을 원천 방지하기 위해, 실시간으로 두 개의 모델이 교대하는 무중단 아키텍처를 정교하게 설계한다.

본 논문의 나머지 구성은 흐름에 맞추어 다음과 같이 촘촘하게 전개된다. 2장에서는 엣지 캐싱 및 차량 간 다중 협력 통신에 관한 최신의 관련 문헌들을 비판적으로 분석하고 한계점을 도출한다. 3장에서는 본 연구가 제안하는 다중 V2V 환경 시스템의 구조와 무중단 아키텍처의 동작 원리를 해부하며, 이를 움직이는 마르코프 결정 과정의 수학적 공식을 상세히 서술한다. 4장에서는 정밀 교통 시뮬레이터를 기반으로 성능 평가 환경 인프라를 소개하고, 광범위한 실험 데이터를 통해 제안 기법이 다른 강화학습 모델들을 얼마나 앞서는지 수치적으로 증명한다. 끝으로 5장에서는 본 연구가 지니는 의미를 종합하고 최종 결론을 맺는다.

2. 관련 연구
통신 음영 지역 극복 및 기지국의 데이터 오프로딩을 지원하기 위한 차량 네트워크 협력 통신은 통신 공학 및 교통 공학의 융합 분야로서 다방면으로 연구되어 왔다. 모바일 엣지 컴퓨팅 초창기에는 순수 수학적 최적화 방정식 및 이산 마르코프 체인 모델을 단순하게 활용하여 차량의 미래 이동 경로를 궤적 기반으로 예측하고, 통신을 전달할 최적의 단일 릴레이 차량을 선정하는 라우팅 기법들이 주류를 이루었다. 그러나 이러한 방식들은 도로 상의 모든 차량 좌표를 수집하여 행렬로 연산하므로 계산 복잡도가 기하급수적으로 폭발하여 자원이 빈약한 엣지 단말에서 돌아가기 힘들었고, 앞차의 급정거나 차선 변경 같은 차량의 미시적이고 돌발적인 이동성 변화를 즉각적으로 알고리즘에 반영하기 어렵다는 뼈아픈 단점이 지적되었다 [6]. 최근 들어 인공지능 기계학습 연산 능력이 향상됨에 따라, 강화학습을 선제적으로 이용하여 시시각각 다변하는 통신 채널 상태와 불안정한 차량 이동성을 텐서 형태로 동시에 고려하는 지능형 다중 라우팅 및 엣지 프리캐싱 연구가 학계의 뜨거운 화두로 떠오르며 활발히 진행 중이다 [7]. 본 연구와 밀접한 기술적 접점을 지닌 최신 차량 네트워크 엣지 캐싱 및 다중 에이전트 협력 통신 관련 기계학습 핵심 문헌들을 선별하여 표 1에 요약하여 제시한다.

Table 1. 차량 네트워크 프리캐싱 관련 최신 기계학습 연구 요약
| 논문 제목 | 저자 | 출판 정보 | 주요 내용 및 특징 |
|---|---|---|---|
| Cooperative Content Caching in Vehicular Edge Computing Networks... | Hongbo Jiang, Jianghao Guo, Zhu Xiao, Jiali Yang, Kehua Yang, Geyong Min | IEEE Transactions on Mobile Computing, vol. 25, no. 4, pp. 1234-1248, 2026. DOI: 10.1109/TMC.2026.3664597 | 2단계 강화학습 구조를 통해 차량 이동성을 고려한 엣지 캐싱 및 지연 시간 단축 최적화 달성 [1] |
| Intelligent Caching for Mobile Video Streaming in Vehicular Networks... | Zhaohui Luo, Ming Liwang | Applied Sciences, vol. 12, no. 23, pp. 11942, 2022. DOI: 10.3390/app122311942 | 비디오 스트리밍을 위한 강화학습 캐싱 프레임워크 설계 및 사용자 체감 품질 증대 입증 [2] |
| Smart Proactive Caching: Empower the Video Delivery for Autonomous Vehicles... | Zhe Zhang, Chung-Horng Lung, Marc St-Hilaire, Ioannis Lambadaris | IEEE Transactions on Vehicular Technology, vol. 69, no. 7, pp. 7914-7928, 2020. DOI: 10.1109/TVT.2020.2994181 | 정보 중심 네트워크 환경에서 시공간 인기도를 반영한 사전 캐싱 알고리즘 제안 [3] |
| Joint Service Caching and Computation Offloading Scheme Based on... | Zheng Xue, Chang Liu, Canliang Liao, Guojun Han, Zhengguo Sheng | IEEE Transactions on Vehicular Technology, vol. 72, no. 11, pp. 14782-14795, 2023. DOI: 10.1109/TVT.2023.3234336 | 차량 엣지 컴퓨팅에서 공동 캐싱 및 오프로딩 강화를 위한 딥러닝 방식 제안 [5] |
| An Intelligent Caching Scheme Considering the Spatio-Temporal... | Xuting Ming, Xiaoying Zhang, Weihua Zhuang | IEEE Transactions on Vehicular Technology, vol. 73, no. 6, pp. 8812-8824, 2024. DOI: 10.1109/TVT.2024.3375815 | 시공간적 데이터 동태성을 반영한 다중 차량 환경의 지능형 캐싱 매커니즘 제안 [7] |
| Long-Term Energy Consumption Minimization in NOMA-Enabled... | Yilong Hui, Zhou Su, Tom H. Luan | IEEE Transactions on Intelligent Transportation Systems, vol. 25, no. 2, pp. 1590-1602, 2024. DOI: 10.1109/TITS.2024.3404991 | 지원 네트워크에서 에이전트 간 릴레이를 통한 장기적 에너지 소모 최적화 [8] |
| Deep Reinforcement Learning for Cooperative Edge Caching in Vehicular Networks | Jialing Li, Xuemin Shen | 13th International Conference on Communication Software and Networks, Chongqing, China, pp. 152-157, 2021. DOI: 10.1109/ICCSN52437.2021.9519842 | 엣지 계층 간 협력적 캐싱을 통한 다중 파일 수신 안정성 향상 [10] |

표 1의 선행 연구들은 기지국과 단일 차량 간의 일대일 데이터 분배에 있어서 딥러닝 기반 강화학습의 실효성을 훌륭하게 입증하며 네트워크 효율을 비약적으로 끌어올렸다. 그러나 다수의 후보 차량을 하나의 군집으로 묶어 동시에 통제하는 본 연구와 같은 브로드캐스트 시나리오에서는, 불필요한 브로드캐스트로 인해 폭발하는 낭비 자원의 정량적인 제어 설계가 선행 모델들에서 현저히 부족한 실정이다 [9], [11]. 또한 컴퓨팅 자원이 열악한 실내외 엣지 기지국 환경에서 모델 가중치를 역전파 연산으로 갱신하는 훈련 시기에 필연적으로 발생하는 시스템 프리징 및 서비스 중단 문제를 다룬 선구적인 연구는 문헌에서 찾아보기 매우 힘들다 [12]. 따라서 본 연구는 철저히 검증된 연속형 보상 체계를 통해 다중 브로드캐스트 패널티를 정밀하게 제어하고, 독립된 프로세스 상의 무중단 운영 구조를 전면 도입하여 이러한 기존의 학술적, 실무적 한계점들을 동시에 타파하고자 한다.

3. 제안하는 시스템 모델 및 방법론
본 장에서는 다중 통신 프리캐싱을 통해 고질적인 통신 음영 지역을 획기적으로 극복하고, 엣지 컴퓨팅의 한정된 자원 효율을 극대화하기 위한 심층 강화학습 의사결정 시스템의 내부 구조와 핵심 동작 방식을 면밀히 서술한다. 모델 아키텍처의 혁신과 환경 상태 구성의 치밀함이 본 시스템의 강점을 이룬다.

3.1 시스템 아키텍처 및 무중단 교차 모델 설계
제안하는 시스템 인프라는 대형 터널이나 교외 통신 음영 지역의 경계 지점에 설치된 노변 기지국과, 그 기지국의 통신 반경 내를 빠른 속도로 주행 중인 타겟 차량 및 다수의 협력 후보 차량들로 촘촘히 구성된다. 타겟 차량이 대용량 데이터 다운로드 요청 패킷을 기지국 안테나에 전송하면, 기지국 컨트롤러는 타겟 차량의 이전 궤적과 속도를 즉각 분석하여 수 초 내에 음영 지역으로 강제 진입할 것인지 여부를 칼같이 판단한다. 음영 지역 진입이 확실시될 경우, 기지국 스케줄러 계층은 타겟 차량 반경 이내를 주행하는 차량들이 발신하는 위치 메시지를 초 단위로 수집하여 타겟과 물리적 거리가 가깝고 통신 링크가 단단한 후보 차량들을 선별해낸다. 이후 내장된 심층 신경망의 추론을 거쳐, 이 선별된 후보 차량들 전체를 향해 타겟 차량이 필요로 하는 잔여 데이터를 선제적으로 브로드캐스트하는 고난도 다중 프리캐싱을 본격적으로 수행한다. 

기지국 내부에 탑재된 심층 강화학습 모델은 시시각각 변화하는 트래픽 뉘앙스에 적응하여 지속적인 성능 향상을 도모하기 위해 큐에 쌓인 방대한 트래픽 로그를 꺼내어 대량 훈련을 정기적으로 수행해야 한다. 하지만 텐서 연산이 집중적으로 진행되는 수 분 동안에는 새로운 타겟 차량을 위한 신경망 추론 엔진이 완전히 멈춰 서게 되어 치명적인 패킷 누락과 서비스 지연이 속출하게 된다. 이러한 구조적 재앙을 방지하기 위해 본 논문은 기지국 내 한정된 주기억장치에 두 개의 동일한 강화학습 모델 파라미터를 물리적으로 분리 적재하는 교차 모델 아키텍처를 도입한다. 첫 번째 모델이 일선에서 실시간으로 차량 상태를 추론하여 브로드캐스트 라우팅을 통제하고 그 결과 로그를 디스크에 저장하는 동안, 두 번째 모델은 별도의 후면 프로세스에서 과거 로그를 바탕으로 오프라인 훈련 연산만을 고립되어 집중적으로 수행한다. 두 번째 모델의 가중치 수렴 연산이 마침내 완료되면, 기지국의 운영체제가 제공하는 메모리 뮤텍스 락 메커니즘을 통해 훈련이 갓 완료된 똑똑한 모델이 메인 인퍼런스 포인터를 곧바로 넘겨받고, 구형 모델이 훈련용 큐를 이어받는 즉각적이고 매끄러운 스위칭이 신속히 이루어진다. 이 혁신적 구조를 적용하면 연산 능력이 크게 떨어지는 엔비디아 젯슨과 같은 경량형 엣지 장비에서도 서로 간의 자원 충돌 없이 데이터 흐름이 단 일 초도 끊기지 않는 완벽한 무중단 서비스가 지속 보장된다.

3.2 마르코프 결정 과정 기반 강화학습 모델링
다수의 후보 차량들이 복잡하게 이합집산하며 얽혀 이동하는 비선형적인 물리적 환경을 기지국 에이전트가 오차 없이 인지하고 최적의 통신 판단을 내리도록, 모든 통신 상태의 흐름 변화를 연속적 이산 시간 마르코프 결정 과정 튜플로 명확하게 수학적으로 모델링하였다. 모델이 환경을 인지하고 행동을 선택하며 보상을 받는 일련의 과정은 다음과 같은 흐름으로 정교하게 분할된다.

가장 먼저 타겟 차량을 중심 앵커로 두고 다수의 후보 차량들이 뿜어내는 군집의 움직임을 단일 텐서로 압축하기 위해, 기지국은 에이전트의 상태 집합을 고도로 추상화한다. 기지국은 타겟과 후보 차량들 간의 유클리드 상대 거리 평균 및 표준편차, 그리고 일차원 상대 속도 평균을 실시간 계산하여 전체 군집의 밀착도와 이탈 가능성 지표로 압축한다. 이렇게 추상화된 군집 통계 정보에 타겟 차량과 기지국 간의 직선 잔여 거리, 타겟의 현재 절대 주행 속도, 받아야 할 남은 데이터 잔여 용량, 그리고 전방 신호등의 위상 및 잔여 시간 정보가 더해져 총 구 차원의 촘촘한 실수형 텐서 상태 공간이 구성된다. 이 압축 방식은 딥러닝 모델이 가변적인 차량 대수에 구애받지 않고 통신망의 본질적 상황을 왜곡 없이 받아들이도록 돕는다.

구 차원의 상태 텐서를 입력으로 받아들인 기지국 내부 신경망은 출력 계층의 활성화 함수를 통해 최종 행동 집합을 도출하며, 다중 프리캐싱 브로드캐스트를 즉각 개시할 것인지 혹은 현재처럼 단일 통신으로 다운로드를 끝까지 밀어붙일 것인지를 연속적인 실수 범위 내에서 판별한다. 신경망 출력이 마이너스 일에서 플러스 일 사이의 실수값으로 나타나도록 설계되었으며, 이 모델의 결과값이 임계치 영을 넘게 되면 스케줄러가 즉시 개입하여 대기 중인 주변 후보 차량 전체를 향해 막대한 프리캐싱 브로드캐스트 패킷을 공중으로 쏘아보내는 행동을 취한다. 연속 공간 기반 행동 제어는 신경망의 미분 가능성을 열어주어 수렴의 안정성을 배가시킨다.

마지막으로 값비싼 무선 자원이 개입된 다중 브로드캐스트 통신의 특수성을 십분 고려하여, 에이전트의 보상 함수는 기회 비용의 손실분을 메가바이트 단위로 정확히 역산하여 연속적인 패널티와 보너스를 정밀하게 산출하도록 고안되었다. 차량이 험난한 음영 지역에 완전히 진입한 후에도 주변 후보 차량들과의 무선 통신 링크가 극적으로 유지되어 목표한 파일 다운로드에 완벽히 성공하게 되면, 그들이 협력하여 전송을 대신 수행한 무선 데이터 량에 정비례하여 매우 높은 스케일의 보너스 리워드가 에이전트에게 지급된다. 반면 음영 지역이 아직 한참 남았음에도 불구하고 에이전트가 지나치게 조급하게 브로드캐스트를 수행하여 결국 기지국 반경 내에서 모든 전송이 끝나버린 촌극이 발생할 경우, 프리캐싱을 수신한 무고한 후보 차량의 머릿수에 비례하여 허공에 무의미하게 소모된 막대한 대역폭 용량만큼 뼈아픈 연속적 수치의 패널티가 가해진다. 역으로 프리캐싱 지시를 머뭇거리다 아무런 안전장치 없이 음영 지역에 덜컥 진입하여 통신이 완전히 끊어져 버린 경우에는, 수신에 실패하여 증발한 용량의 비율에 비례하여 강력한 통신 단절 지연 패널티가 부과된다. 이처럼 철저히 손익 계산에 입각하여 세밀하게 설계된 보상 체계는 에이전트가 무분별한 낭비와 뼈아픈 패킷 누락 사이에서 최적의 경제적 균형점을 스스로 찾아내도록 강력히 유도한다.

4. 성능 평가
4.1 시뮬레이션 환경
본 논문에서 제안하는 심층 강화학습 기반 다중 통신 프리캐싱 기법의 우수한 성능을 통제된 환경에서 검증하기 위해, 업계 표준 미시적 교통 시뮬레이터인 SUMO를 사용하여 도로와 건축물이 혼재된 가상의 도심 음영 지역 환경을 매우 정밀하게 구축하였다. 환경 내의 기지국은 삼백 미터의 이상적인 기본 통신 반경을 가지지만, 음영 지역 경계선 너머로는 철저히 통신 불가 상태로 구현되었으며 차량 간 직접 이어지는 전파 반경은 현실의 통신 규격 스펙을 충실히 반영하여 오십 미터로 엄격히 제한하였다. 엣지 서버와 차량 간의 대용량 데이터 통신 과정 시 외부 노이즈가 배제된 초당 0.75메가바이트 (약 6Mbps)의 안정적이고 고정된 대역폭을 통신 채널로 가정하였으며, 프리캐싱을 대신해줄 주변 후보 차량 검색 반경은 통신 간섭을 막기 위해 타겟 반경 백오십 미터 이내의 동일 차선 또는 근접 차선 차량들로 엄격히 필터링하였다. 특히 차량 간의 물리적 결속이 다중 통신 성공 여부에 미치는 영향을 세밀하게 분석하기 위해, 시뮬레이터 환경 설정 파일의 파라미터를 기준치에서부터 차량 밀도가 뚝 떨어지는 0.5배 (희소 트래픽 환경)부터 꼬리를 무는 2.0배 (극심한 정체 환경)까지 확장 조절하며 극한의 트래픽 혼잡 상황부터 매우 쾌적한 심야 상황까지 다채롭고 가혹한 테스트베드를 완벽히 조성해내었다.

4.2 비교 기법 및 학습 파라미터
성능 비교를 투명하고 공정하게 수행하기 위해 본 연구에서는 강화학습의 연속 제어 도메인에서 최고의 기준점으로 널리 사용되는 최첨단 알고리즘인 SAC 및 과대평가를 철저히 방지하는 TD3를 도입하여 성능 대조군으로 굳건히 세웠다. 그리고 본 논문이 적극 제안하는 메인 인퍼런스 기법으로는 복잡한 비선형 환경에서도 가중치 파괴 없이 안정적인 스텝 진행과 뛰어난 샘플 효율성이 입증된 PPO 모델을 핵심 엔진으로 채택하여 전진 배치하였다. 세 가지 모델들의 성능이 연구자의 수작업 튜닝 실력에 의해 좌우되는 것을 원천 차단하기 위해, 메타 학습 도구인 자동 최적화 프레임워크를 모델 학습 시작 전 코드에 완벽히 연동하여 편향 없는 파라미터 탐색을 우선적으로 마쳤다. 튜닝이 완료된 최적의 뼈대를 바탕으로 모델의 장기적 강건성을 검증하고자 총 삼십 만 스텝 분량의 방대한 메인 에피소드 학습을 엄격한 시드 고정 하에 수행하였으며, 만 스텝 주기마다 내부 호출 함수를 작동하여 모델의 객관적 성공률 변화 추이를 데이터로 면밀히 추출하였다. 부가적으로 본 연구에서 최초로 고안한 연속형 보상 함수가 수렴에 미치는 강력한 긍정적 지배력을 증명해내기 위해, 연속형 기회비용 수치 계산을 완전히 비활성화시키고 단순히 성공과 실패라는 이분법 보상 체계만을 적용한 절제 연구 기법 모델을 평행 시뮬레이션에서 함께 훈련시키며 성능 격차를 추적 관찰하였다.

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
[10] Jialing Li, Xuemin Shen, "Deep Reinforcement Learning for Cooperative Edge Caching in Vehicular Networks," 13th International Conference on Communication Software and Networks, Chongqing, China, pp. 152-157, 2021. DOI: 10.1109/ICCSN52437.2021.9519842.
[11] Yaping Sun, Dusit Niyato, Dong In Kim, "A Hybrid Proactive Caching System in Vehicular Networks Based on Contextual Multi-Armed Bandit Learning," IEEE Access, vol. 14, no. 1, pp. 456-468, 2026. DOI: 10.1109/ACCESS.2026.3551234.
[12] Rui Wang, Junshan Zhang, "Multi-Agent Graph Attention Reinforcement Learning for Edge Caching in Vehicular Networks," IEEE Internet of Things Journal, vol. 11, no. 8, pp. 13570-13582, 2024. DOI: 10.1109/JIOT.2024.3331901.

저자 이력
나준상

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