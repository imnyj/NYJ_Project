
LSOM-based Snapshot Edge Precaching Framework for CIoV
 Youngju Nam†, Jeong-Hun Kim††
ABSTRACT
This paper proposes a snapshot edge precaching framework based on the Linear Space Optimization Model (LSOM) for efficient data transmission in a Content-Centric Internet of Vehicles environment. To overcome the latency issues of existing centralized approaches and the multi-modal prediction limitations of machine learning regression models, we propose the LSOM model to perform independent dwell time inference at the edge using only single-point-in-time data. The proposed method combines linear differential space optimization, which ensures temporal constraints, with conditional pre-network-based flow matching to guarantee robust predictions even in uncertain urban traffic environments. In a simulation environment modeling urban traffic, the proposed framework achieved prediction accuracy surpassing state-of-the-art machine learning and deep learning baselines, confirming that it achieves stable mobility service continuity while decreasing user latency by 22.9% and mitigating the traffic waste problem by 20.5%.
Keywords:CIoV, Precaching, Edge Intelligence, Snapshot Inference.
CIoV에서 LSOM 기반의 스냅샷 엣지 프리캐싱 프레임워크
 남 영 주†, 김 정 훈††
요     약
본 논문은 CIoV(Content-Centric Internet of Vehicles) 환경의 효율적인 데이터 전송을 위해 LSOM(선형 공간 최적화 모델) 기반의 스냅샷 엣지 프리캐싱 프레임워크를 제안한다. 기존 중앙 집중형 방식의 지연 문제와 기계학습 회귀 모델의 다봉성 예측 한계를 극복하기 위해, LSOM 모델을 제안하여 단일 시점 데이터만으로 엣지에서 독립적인 체류 시간 추론을 수행한다. 제안 기법은 시간적 제약을 보장하는 선형 차분 공간 최적화와 조건부 사전망 기반 흐름 매칭을 결합하여 불확실한 도심 교통 환경에서도 강건한 예측을 보장한다. 도심 교통을 모사한 시뮬레이션 환경에서 제안 프레임워크는 최첨단 기계학습 및 딥러닝 베이스라인들을 상회하는 예측 정확도를 달성하였으며, 이를 통해 사용자 지연 시간을 22.9% 낮추고 트래픽 낭비 문제를 20.5% 개선하여 안정적인 모빌리티 서비스 연속성을 달성함을 확인하였다.
키워드:콘텐츠 중심 차량 네트워크, 프리캐싱, 엣지 인텔리전스, 스냅샷 추론, 이동성 예측.
1. 서  론※이 논문은 2025학년도 국립군산대학교 신임교수 연구비 지원에 의하여 연구되었음.
†비 회 원:국립군산대학교 소프트웨어학과 조교수
†비 회 원:국립군산대학교 컴퓨터정보공학과 조교수
논문접수:2026년 0월 0일
수 정 일:1차 2026년 0월 0일
심사완료:2026년 0월 0일
  * Corresponding Author : Jeong-Hun Kim (kimjh@kunsan.ac.kr)
  

4차 산업혁명의 확산과 함께 자율주행 및 커넥티드 카 기술이 비약적으로 발전함에 따라, 자동차는 단순한 기계적 운송 수단을 넘어 운전자와 탑승자에게 다양한 정보를 제공하는 스마트 모빌리티 플랫폼으로 진화하고 있다[1]. 이러한 변화 속에서 차량 내 인포테인먼트 서비스의 중요성은 날로 증대되고 있으며, 대용량 데이터 전송을 요구하는 애플리케이션들이 폭발적으로 증가하는 추세이다. Ericsson Mobility Report에 따르면, 전 세계 모바일 데이터 트래픽은 연평균 25% 이상의 가파른 성장세를 보이고 있으며[2], 이에 따라 제한된 무선 대역폭과 네트워크 자원을 효율적으로 관리하는 것이 미래 모빌리티 산업의 핵심 과제로 부상하였다.
특히 도심 환경은 고층 빌딩으로 인한 신호 감쇠, 통신 혼잡, 그리고 신호등에 의한 불규칙한 이동 정지 등이 빈번하게 발생하는 복잡한 환경이다. 차량이 RSU(Road Side Unit) 사이를 이동할 때 발생하는 핸드오버는 필연적으로 서비스 품질 저하를 야기하며, 이를 해결하기 위해 콘텐츠 중심 네트워킹(CCN) 기술이 도입되었다[3, 4]. CCN 기반 CIoV 환경에서는 RSU가 캐시 기능을 수행하여 백홀 부하를 줄일 수 있으나, 제한된 커버리지로 인해 차량 이동 경로를 미리 예측하고 컨텐츠를 선제적으로 전송하는 프리캐싱 기술이 필수적이다[5, 6]. 그러나 기존 연구들은 대부분 중앙 클라우드 서버에 의존하는 중앙 집중형 방식을 채택하고 있어, 실시간성이 떨어지고 막대한 네트워크 오버헤드를 유발한다는 구조적 한계를 안고 있다.
무엇보다 도심 도로의 불확실한 교통 흐름은 정확한 체류 시간 예측을 어렵게 만드는 가장 큰 요인이다. 교차로의 신호등, 돌발적인 정체, 보행자 이동 등 다양한 변수로 인해 차량의 체류 시간은 단순한 정규 분포가 아닌 복잡하고 꼬리가 긴 다봉성 분포를 띠게 된다. 기존의 단순 선형 회귀나 고전적 딥러닝 모델들은 이러한 복합적인 상황에서 단순히 평균값으로 수렴하는 경향이 있어, 실제 데이터의 분포적 특성을 전혀 반영하지 못한다. 즉, 단순한 결정론적 모델로는 딜레마 존에 놓인 차량의 "멈춤"과 "통과"라는 이원적 상황을 제대로 구분하지 못하며, 이는 필연적으로 예측 실패와 프리캐싱 성능 저하로 귀결된다.
본 논문에서는 이러한 한계들을 극복하고 엣지 레벨에서의 완전한 자율성을 확보하기 위해, LSOM 기반의 스냅샷 엣지 인텔리전스 프리캐싱 프레임워크를 제안한다. 제안하는 프레임워크는 지속적인 궤적 추적 없이 차량 진입 순간의 단일 시점 문맥 정보만을 활용한다. LSOM은 복잡한 도심 트래픽을 처리하기 위해 실제 체류 시간을 선형 차분 공간으로 매핑하여 다봉성을 포착하고, 조건부 사전 분포 기반 흐름 매칭 기술을 융합하여 불확실성 하에서도 높은 예측 정밀도를 달성한다. 모든 연산 과정은 중앙 서버 없이 엣지에서의 실시간 추론 최적화를 거쳐 각 RSU에서 독립적으로 수행되므로 시스템의 실시간성과 확장성을 보장한다.

2. 관련 연구
2.1 CIoV와 프리캐싱
차량 네트워크와 CCN의 결합인 CIoV 환경에서 캐싱 전략은 크게 사후 캐싱(Reactive Caching)과 사전 캐싱(Proactive Caching/Precaching)으로 구분된다. 사후 캐싱은 사용자가 요청한 데이터가 지나갈 때 RSU에 복사본을 남기는 수동적인 방식인 반면, 프리캐싱은 사용자 요청이 발생하기 전에 미래의 수요를 예측하여 데이터를 미리 가져다 놓는 능동적인 방식이다. 초기 연구들은 단순히 콘텐츠의 인기도에 의존하여, Zipf 분포 등을 따르는 인기 콘텐츠를 인접 RSU들에 무작위로 혹은 확률적으로 뿌려두는 방식을 사용하였다. 그러나 이는 차량 개개인의 이동 경로와 무관하게 데이터를 저장하므로 캐시 적중률이 낮고 스토리지 자원을 낭비하는 단점이 있었다. 이후 연구들은 차량의 속도, 방향, 목적지와 같은 이동성 정보를 결합하여 선별적 캐싱을 시도했으나, 단순한 선형 이동 모델이나 고정된 확률 모델에 의존하여 신호등이나 교통 체증과 같은 도심지의 동적 변수들을 유연하게 반영하지 못하는 한계가 있었다. 이에 본 논문은 고정된 규칙 대신 데이터 기반의 유연한 추론을 수행하는 LSOM을 제안하여 이러한 한계를 극복하고자 한다.

2.2 머신러닝 기반 이동성 예측의 한계
최근 딥러닝 기술의 발전과 함께, 차량의 이동성을 보다 정교하게 모델링하기 위한 머신러닝 기반 연구들이 활발히 진행되고 있다[7-13]. Wang et al.[7]은 Contextual Multi-Armed Bandit 알고리즘을, Elsayed et al.[8]은 LSTM 네트워크를 활용하여 예측 정확도를 높이고자 하였다. 또한, Jiang et al.[9]은 연합 학습을 통해 개인 정보 보호 문제를 다루었다.
하지만 이러한 연구들은 여전히 두 가지 치명적인 한계를 지닌다. 첫째, 대부분의 모델이 평균 제곱 오차(MSE) 최소화에 집중하여, 도심 교통의 본질인 다봉성을 간과하고 평균 회귀 문제에 빠진다. 둘째, 높은 연산 복잡도와 긴 시계열 데이터를 요구하여, 실시간성이 필수적인 엣지 노드에서의 운영이 불가능하다. 따라서 복잡한 시계열 데이터 없이도 단일 시점의 문맥 정보만으로 다봉성 분포를 정확히 학습할 수 있는 새로운 접근법이 절실하다. 본 논문이 제안하는 LSOM은 이러한 요구에 부응하여, 선형 공간 최적화를 통해 경량화된 연산만으로도 불확실성 하에서의 정밀 예측을 가능케 하는 최적의 솔루션을 제공한다.

3. 네트워크 모델
3.1 V2I 기반의 CIoV 네트워크 및 CCN 전송 모델
본 논문에서 고려하는 CIoV 네트워크는 현대적인 도심부 교차로(Manhattan Grid) 환경을 기반으로 모델링되었다. 도심의 주요 교차로마다 컴퓨팅 유닛과 대용량 스토리지를 갖춘 RSU가 배치되어 있으며, 모든 RSU는 고속 유선 백홀(Fiber)을 통해 상호 연결됨과 동시에 중앙의 콘텐츠 서버와 통신한다. 차량은 IEEE 802.11p WAVE 또는 C-V2X와 같은 차량 통신 표준을 준수하는 On-Board Unit(OBU)을 탑재하고 있으며, RSU의 통신 반경 내에 진입했을 때 V2I(Vehicle-to-Infrastructure) 통신을 수행한다.
콘텐츠 전송 프로토콜로는 CCN 아키텍처를 채택한다. CCN에서 통신은 데이터 소비자인 차량의 요청에 의해 주도된다. 차량이 특정 비디오 스트리밍이나 지도 데이터 등의 콘텐츠를 필요로 할 때, 해당 콘텐츠의 고유한 계층적 이름(Hierarchical Name, 예: /kci/video/seg1)을 포함한 Interest 패킷을 네트워크에 브로드캐스트한다. RSU는 이 Interest 패킷을 수신하여 자신의 Content Store (CS)를 검색한다. 만약 요청된 콘텐츠가 CS에 캐싱되어 있다면, RSU는 즉시 해당 데이터를 담은 Data 패킷을 차량에게 전송한다. 반면 콘텐츠가 없다면, RSU는 Pending Interest Table (PIT)에 요청 기록을 남기고, Forwarding Information Base (FIB)를 참조하여 인접한 RSU나 중앙 서버로 Interest 패킷을 포워딩한다. 이러한 구조는 데이터가 물리적으로 어디에 위치해 있는지보다 무엇인가를 중시하므로, 인기 있는 콘텐츠가 사용자와 인접한 RSU 캐시에 자연스럽게 분산 저장되어 전체 네트워크의 트래픽 부하를 효과적으로 분산시키는 장점이 있다.

3.2 RSU 주도의 실시간 로컬 상태 모니터링
성공적이고 효율적인 프리캐싱을 위해서는 RSU가 자신의 서비스 영역 내 상황을 정확하게 인지하고 있어야 한다. 이를 위해 각 RSU는 자신의 커버리지 내 트래픽 및 통신 상태를 실시간으로 모니터링하고, LSOM의 입력 변수로 활용될 두 가지 핵심 지표를 주기적으로 갱신하며 관리한다.
첫째, 평균 차량 속도 이다. RSU는 자신의 통신 영역에 진입하고 이탈하는 모든 차량의 타임스탬프를 로그로 기록한다. 이 데이터를 바탕으로 지난 1시간 동안 통신 영역을 통과한 차량들의 평균적인 주행 속도를 산출한다. 는 현재 도로의 소통 원활 정도를 나타내는 거시적인 지표로, 개별 차량의 체류 시간을 예측하는 데 있어 기준점 역할을 수행한다.
둘째, 평균 통신 처리량 이다. 무선 통신 채널은 시변성이 강하고, 특히 다수의 차량이 동시에 접속할 경우 대역폭 경쟁으로 인해 실제 전송 속도가 급격히 저하될 수 있다. RSU는 현재 접속 중인 차량들에게 제공되는 실제 데이터 전송 속도를 실시간으로 측정하고 평균화하여 를 관리한다. 이 값은 RSU가 차량이 떠나기 전까지 물리적으로 전송 가능한 데이터의 총량을 계산하는 데 결정적인 변수로 작용하며, 과도한 프리캐싱으로 인한 자원 낭비를 방지하는 상한선을 설정하는 데 기여한다. 이 두 지표는 1분 단위로 갱신되어 스냅샷 추론 모델의 핵심 입력 변수로 활용된다.

4. 스냅샷 기반 엣지 프리캐싱 프레임워크
제안하는 프레임워크는 중앙 클라우드 서버나 컨트롤러의 개입 없이, 각 RSU가 독립적인 엣지 인텔리전스 에이전트로서 동작하는 분산형 구조를 갖는다. 전체 동작 과정은 크게 3단계의 워크플로우(요청 처리 및 스냅샷 특징 추출, 엣지 기반 체류 시간 추론, 프리캐싱 의사결정 및 실행)로 구성되며, 각 단계는 밀리초 단위의 실시간성을 보장하도록 설계되었다.

4.1 요청 처리 및 스냅샷 특징 추출
차량이 RSU 영역에 진입하여 컨텐츠를 요청하는 Interest 패킷을 전송하는 순간, RSU는 즉시 서비스 제공을 위한 CCN 프로토콜을 수행함과 동시에 내부적으로 프리캐싱 예측 모듈을 가동한다. 이때 가장 중요한 과정은 체류 시간 예측에 필요한 정보를 수집하는 것인데, 제안하는 프레임워크는 LSOM의 추론 정확도를 극대화하기 위해 중앙 서버를 경유하지 않고 RSU 간의 직접 통신을 통해 현장의 생생한 정보를 수집한다. 우선 현재 RSU는 자신의 로컬 환경 정보(접속 차량 수, 평균 속도, 평균 처리량, 현재 신호 상태 및 잔여 시간)와 차량이 보낸 패킷 헤더에서 추출한 이동성 정보(현재 위치, 진입 속도 등)를 수집한다. 하지만 차량이 향후 지나갈 다음 RSU의 상황을 알지 못하면 정확한 예측이 불가능하다. 이를 해결하기 위해 현재 RSU는 백홀 네트워크를 활용하여여 다음 RSU에게 Info Request 패킷을 통해 즉시 자신의 인접 RSU들에게 질의하여, 현재 자신의 영역으로 진입하고 있는 차량의 수를 파악한다. 이와 더불어 자신의 현재 혼잡도, 신호등 상태, 평균 처리량 등의 정보를 모두 취합한 후, 이를 하나의 Info 패킷으로 패키징하여 현재 RSU에게 회신한다. 해당 RSU는 수신된 다음 RSU의 정보와 자신의 로컬 정보를 결합하여 최종적인 스냅샷 특징 벡터를 완성한다.
결과적으로 완성된 특징 벡터는 로컬 및 다음 RSU의 동적 상태, 차량 이동성 데이터, 그리고 교통 흐름 정보라는 세 가지 핵심 요소로 구성된다. 첫째, 로컬 및 다음 RSU의 동적 상태 정보에는 각 RSU의 평균 차량 속도, 평균 통신 처리량, 신호등 상태(Green/Yellow/Red) 및 잔여 시간이 포함된다. 둘째, 차량 이동성 데이터로는 차량이 현재 RSU를 벗어나기까지의 거리, 다음 RSU에 진입하기까지의 거리, 그리고 다음 RSU를 통과하는 거리 등이 수집된다. 마지막으로 교통 흐름 정보에는 로 유입되는 인접 도로의 트래픽 양 및 대기 차량 수가 포함되어 RSU 주변의 혼잡도를 LSOM이 입체적으로 해석할 수 있도록 돕는다. 이 모든 데이터 수집 및 특징 벡터 생성 과정은 수 밀리초 이내에 완료되며, 완성된 벡터는 엣지 모델 내부의 전처리 모듈인 표준 스케일링과 원-핫 인코딩을 거쳐 최종적인 입력 특징()으로 변환되어 LSOM 추론 엔진의 입력으로 사용된다.

4.2 엣지 기반 체류 시간 추론
제안하는 프레임워크의 핵심 추론 엔진인 LSOM은 Fig. 1과 같이 전처리된 스냅샷 특징 를 입력받아 현 RSU 체류 시간(), 다음 RSU 진입시간(), 다음 RSU 이탈시간()으로 구성된 실제 타겟 를 동시에 예측한다. 여기서 타겟 로 정의된다. LSOM은 기존 딥러닝 모델들이 공통적으로 겪는 평균 수렴 현상과 예측의 비물리적 모순을 극복하기 위해, 선형 차분 공간 기하 변환과 조건부 사전망 기반 흐름 매칭(Conditional prior-based flow matching, CP-FM) 구조를 결합하였다. 제안하는 LSOM의 전체적인 신경망 구조는 그림 1과 같다.

Fig. . LSOM architecture

1) 선형 기하 변환 및 목표 공간 정의
다중 체류 시간 예측에서 중요한 물리적 제약은 시간의 절대적 순차성()과 양수성()의 보장이다. 기존 예측 모델들은 이러한 성질을 제어하기 위해 대수 변환을 주로 활용했으나, 이는 모델의 역변환 단계에서 지수 함수적 팽창을 야기하여 역전파 시 기울기 불안정을 빈번하게 유발한다. 이러한 문제를 해결하기 위해 LSOM은 실제 타겟 를 직접 추론하지 않고, 수식 (1)과 같이 시간차를 나타내는 선형 차분 변수 로 분해한다.


(1)
이후 산출된 차분 벡터 를 학습 데이터의 평균 와 표준편차 를 활용하여 수식 (2)와 같이 정규화함으로써, 모델 학습의 실제 목표 상태가 되는 선형 차분 타겟 텐서 를 생성한다.


(2)

역으로, 모델 추론 후 예측된 텐서를 물리적 시간 공간으로 복원할 때에는 지수 함수 대신 부드러운 선형 특성을 지닌 Softplus 활성화 함수를 통과시켜 모든 구간의 양수성을 확정짓고, 누적 합 연산을 통해 시간의 순차성을 완벽하게 재구성한다.

2) LSOM 신경망 구조
도심 교통 데이터의 복잡한 다봉성을 모델링하고 실험의 완벽한 재현성을 보장하기 위해, LSOM은 내부적으로 파라미터 로 구성된 조건부 사전망 CP-FM과 파라미터 로 구성된 흐름망을 결합한 구조로 설계되었다.
조건부 사전망은 입력 스냅샷 의 복잡한 비선형적 교통 문맥을 추출하여 결정론적인 앵커를 제공한다. 내부 구조는 다계층 퍼셉트론을 백본으로 한다. 입력 는 지정된 은닉 차원으로 매핑된 후, 선형 변환, 기울기 소실 방지 및 정규화를 위한 계층 정규화, 부드러운 비선형성을 제공하는 SiLU 활성화 함수, 그리고 과적합 방지를 위한 드롭아웃이 순차적으로 결합된 블록들을 통과한다. 마지막 출력층은 타겟 차원인 3차원으로 투영되어 스칼라 분산 추정 없이 순수한 사전 평균 앵커 를 직접 출력한다. 이러한 구조는 순수한 무작위 노이즈에서 탐색을 시작하는 기존 생성형 모델의 학습 불안정성을 원천 제거하며, 주어진 문맥 에 가장 부합하는 타겟 공간의 기댓값 좌표를 속도장의 출발점 앵커로 제공하여 모델의 탐색 공간을 축소하고 수렴 속도를 극대화한다.
흐름망은  기반의 초기 상태에서 목표 상태 까지의 연속적인 궤적을 잇는 속도장 를 예측하는 심층 신경망이다. 입력으로 조건 문맥 , 현재 상미분 방정식의 궤적 상태 , 그리고 스칼라 시간 스텝 를 동시에 받는다. 연속적인 시간 흐름을 모델이 인지할 수 있도록 스칼라 는 트랜스포머 아키텍처 기반의 정현파 시간 임베딩 모듈을 거쳐 고차원 벡터로 변환된다. 이후 선형 투영된 조건 의 임베딩과 상태 가 결합되어 다수의 잔차 블록을 통과한다. 각 잔차 블록은 계층 정규화, 시간 임베딩 가산, 선형 변환, SiLU, 드롭아웃, 계층 정규화, 선형 변환의 구조를 가지며, 블록의 입력과 출력 간에는 스킵 커넥션이 적용되어 깊은 망에서도 기울기 소실 없이 역전파가 안정적으로 이루어지도록 돕는다. 최종적으로 계층 정규화와 선형 계층을 거쳐 예측된 속도 벡터 가 출력되며, 이는 시간 변화에 따른 궤적의 곡률과 비선형적인 데이터 분포 이동을 잔차 학습을 통해 안정적으로 매핑하는 이점을 가진다.

3) 모델 최적화
제안하는 LSOM의 구조를 바탕으로 파라미터 의 조건부 사전망과 파라미터 의 흐름망은 두 가지 오차를 결합하여 최적화된다.
먼저, 사전망은 수식 (3)과 같이 를 입력받아 앵커 를 도출한다.


(3)

이때 모델은 생성된 앵커 가 실제 정답 상태인 에 공간적으로 근접하도록, 수식 (4)의 사전망 오차 를 최소화하는 방향으로 학습된다.


(4)

다음으로, 흐름망의 적분 시작점인 초기 상태 는 조건부 사전망이 추정한 앵커 에 표준 정규분포를 따르는 노이즈 를 주입하여 으로 설정된다. 시간 변수 에 대하여, 에서 로 향하는 최단 선형 보간 궤적 는 수식 (5)와 같이 정의된다.


(5)

이 궤적을 시간 에 대해 미분하면, 모델이 모사해야 할 이상적인 타겟 속도는 가 된다. 흐름망은 현재 궤적 상태 , 시간 , 그리고 조건 가 주어졌을 때 이 타겟 속도를 완벽히 근사하도록 수식 (6)의 속도장 오차 를 최적화한다.


(6)

최종적으로 LSOM 모델은 두 오차가 결합된 하이브리드 형태의 최종 목적 함수 을 최소화함으로써, 앵커 추정의 안정성과 확률적 분포 매핑 능력을 동시에 달성한다.


(7)


4) 점 예측 및 구간 예측
학습이 완료된 모델을 RSU 엣지 디바이스 환경에서 추론할 때, 연산 지연의 방지는 프리캐싱에서 중요하다. 따라서 목적에 맞추어 두 가지 추론 궤적을 지원한다. 단일 대푯값이 필요한 점 예측 시에는 상미분방정식 적분 연산을 완전히 생략한다. 조건부 사전망의 출력 를 점 예측 텐서 로 채택하여 단 1회의 전파만으로 연산을 완료한다.
반면, 불확실성을 포함하여 전송량의 보수적 마진을 산출해야 하는 구간 예측 시에는 노이즈 을 포함하여 흐름망을 통과시켜 다중 샘플 분포 를 생성한다. 이때 엣지 환경의 분포 편향 문제를 교정하기 위해, 사전 캘리브레이션 데이터셋에서 도출된 차원()의 CQR(Conformal Quantile Regression) [14] 오차 보정 벡터 를 산출한다. 도출된 에 이 CQR 벡터를 텐서 결합함으로써, 마진이 보증된 최종 구간 범위를 확정짓는다.
최종적으로 획득한 텐서는 Softplus와 누적 합 연산을 거쳐 물리적으로 오류가 없는 최종 예측 타겟 의 형태로 출력된다.

4.3 프리캐싱 의사결정 및 실행
프리캐싱 의사결정 및 실행 단계는 앞선 단계에서 LSOM을 통해 도출된 정밀한 체류 시간 예측값을 실제 네트워크 운용 전략으로 변환하는 과정이다. 이 단계의 핵심 목표는 차량이 다음 RSU 영역으로 진입하는 순간 데이터 끊김이 발생하지 않도록, 최적의 타이밍에 적절한 양의 콘텐츠를 미리 배치하는 것이다.
우선 RSU는 현재의 무선 채널 상태를 반영하는 평균 통신 처리량과 예측된 체류 시간을 결합하여, 차량이 현재 서비스 영역을 벗어나기 전까지 물리적으로 전송 가능한 데이터의 총량을 산출한다. 구체적으로 전송 가능한 청크의 개수는 평균 통신 속도와 체류 시간의 곱을 단일 콘텐츠 청크의 크기로 나눈 값의 정수부로 결정된다. 여기서 LSOM이 제공하는 정확한 체류 시간은 이 전송 가능량을 과대평가하여 불필요한 데이터를 전송하거나, 과소평가하여 가용 대역폭을 낭비하는 문제를 방지하는 결정적인 역할을 수행한다.
계산된 청크 개수는 현재 RSU와 다음 RSU가 담당해야 할 서비스 범위를 명확하게 구분 짓는 경계점이 된다. 현재 RSU는 해당 순번의 청크까지를 차량에게 직접 전송하여 소진시키고, 그 이후의 데이터는 다음 RSU가 책임지도록 이양한다. 이를 위해 현재 RSU는 백홀 네트워크를 통해 다음 RSU에게 구체적인 프리캐싱 지시 메시지를 전달한다. 이 메시지는 단순한 데이터 요청이 아니라, 차량이 언제 도착할지, 어떤 콘텐츠의 몇 번째 청크부터 서비스해야 하는지를 명시하는 확정적인 제어 명령이다. 지시를 수신한 다음 RSU는 해당 콘텐츠가 자신의 로컬 캐시에 이미 존재하는지 확인하고, 부재할 경우에만 인접 노드나 중앙 서버로부터 데이터를 사전에 인출하여 저장한다. 이러한 선제적인 준비 과정 덕분에 차량은 핸드오버 직후 딜레이 없이 고화질 스트리밍 서비스를 이어서 제공받을 수 있게 된다.

5. 성능 평가
5.1 시뮬레이션 환경 구축
본 연구에서 제안하는 LSOM 기반 엣지 프리캐싱 프레임워크의 성능을 객관적이고 정량적으로 검증하기 위해, 네트워크 동작을 모사하는 NS-3 시뮬레이터와 차량의 미시적 움직임을 구현하는 SUMO 트래픽 시뮬레이터를 실시간으로 상호 연동한 통합 테스트베드를 구축하였다. 실험 배경이 되는 도심 환경은 고층 빌딩과 복잡한 교차로가 밀집한 서울 강남 혹은 뉴욕 맨해튼의 도로망을 반영하여 15km  15km 크기의 규격화된 Manhattan Grid 모델로 설정하였다. 도로망 내 각 교차로 간격은 2400m이며 왕복 4차선 도로를 가정하여, 차량들이 빈번하게 가감속하고 차선을 변경하는 현실적인 주행 환경을 조성하였다.
특히 본 연구가 해결하고자 하는 도심 교통의 불확실성을 시뮬레이션 상에 구현하기 위해, 모든 교차로의 신호등은 43초라는 짧은 주기로 점멸하도록 설정하였다. 이는 차량들의 흐름을 주기적으로 단절시켜 체류 시간 데이터에 인위적인 다봉성 분포를 형성하고, 예측 모델에게 딜레마 존과 같은 고난이도 상황을 부여하기 위함이다. 차량 이동성은 현실성을 높이기 위해 100대의 차량이 무작위로 생성되어 Dijkstra 최단 경로 알고리즘에 따라 목적지로 이동하는 시나리오를 채택하였으며, 각 차량은 실제 운전자와 유사하게 주변 상황에 반응하며 주행한다.
통신 인프라 측면에서는 차량과 인프라 간의 통신을 위해 IEEE 802.11p WAVE 표준을 적용하였으며, 5.9GHz 대역에서 6Mbps의 전송 속도를 갖도록 설정하여 전형적인 DSRC 환경을 모사하였다. 데이터 처리를 담당하는 RSU는 각 교차로 중앙에 배치되어 반경 800m를 커버하며, RSU 간에는 1Gbps급 광섬유 백홀 링크가 연결되어 있어 지연 없는 고속 데이터 교환이 가능하도록 설계하였다. 마지막으로 제안하는 LSOM 모델은 Python의 PyTorch 라이브러리를 활용하여 구현되었으며, NS-3 시뮬레이터와 TCP 소켓 인터페이스를 통해 실시간으로 데이터를 주고받으며 추론을 수행하는 Hardware-in-the-Loop 형태의 검증 환경을 갖추었다.

5.2 실험 설정
시뮬레이션 환경으로부터 총 302,850건의 RSU 프리캐싱 요청 스냅샷 데이터를 수집하였다. 데이터 누수를 방지하고 모델의 예측 성능과 일반화 능력을 검증하기 위해, 층화 추출 기법을 적용하여 10-Fold 교차 검증 실험을 수행하였다. 해당 실험의 예측 목표는 프리캐싱 의사결정을 위한 타겟에 해당하는 현 RSU 체류 시간(), 다음 RSU 진입시간(), 다음 RSU 이탈시간()을 동시에 예측하도록 구성하였다.
제안하는 LSOM 모델의 예측 정확도를 공정하게 평가하기 위해 최첨단 기계학습 및 딥러닝 베이스라인들인 랜덤 포레스트(RF) [15], XGBoost(XGB) [16], CatBoost(CatB) [17], MLP [18], FT-Transformer(FTT) [18], TabR [19]과 비교하였다. 이러한 베이스라인들은 공식 파이썬 라이브러리 또는 공개된 구현 소스코드를 활용하였다. 이 중 딥러닝 베이스라인들과 LSOM은 AdamW 최적화기를 사용하였으며 배치 사이즈는 512, 에포크는 200, 가중치 감쇠율은 로 설정했고, 모두 CQR 기법을 적용하여 구간 범위를 보정하였다. 평가하는 모든 모델의 하이퍼파라미터는 편향된 평가를 방지하기 위해 훈련 데이터 내에서 50,000개의 샘플을 무작위 추출하여 별도의 검증 집합을 구성한 뒤, Optuna 프레임워크 [20]를 활용하여 30회의 시행 동안 최적화하였다.

Model
Target
RMSE
MAE

RF
[15]

149.400±1.760
76.155±0.619
0.619±0.008

155.757±1.649
84.011±0.667
0.616±0.007

228.852±1.683
141.029±0.708
0.576±0.005
XGB
[16]

137.678±1.996
68.243±0.606
0.676±0.009

143.029±1.915
74.818±0.647
0.676±0.008

217.008±1.847
130.096±0.803
0.619±0.006
CatB
[17]

122.432±2.076
63.884±0.687
0.744±0.007

128.108±1.946
69.540±0.691
0.740±0.007

207.829±1.811
125.173±1.006
0.650±0.006
MLP [18]

166.214±2.152
71.706±0.930
0.528±0.008

171.974±1.757
79.384±0.879
0.532±0.005

267.734±3.031
142.751±1.380
0.420±0.007
FTT
[18]

188.171±4.723
100.935±4.902
0.395±0.029

194.549±4.856
111.877±3.897
0.401±0.028

290.331±6.867
190.639±5.070
0.317±0.034
TabR [19]

160.838±5.577
79.902±5.159
0.558±0.031

166.249±4.571
87.752±4.504
0.562±0.023

252.392±6.341
157.985±5.325
0.484±0.026
LSOM
(ours)

111.854±1.837
56.050±0.837
0.786±0.006

118.164±1.688
61.657±0.825
0.779±0.006

200.741±1.600
114.644±1.421
0.684±0.005
Table 1. Comparison of evaluation results for dwell time

Fig. . Residual analysis of LSOM, CatBoost, and TabR models for dwell time and next dwell time

Fig. . Quantitative comparison of distribution modeling performance via WD and CCC for dwell time and next dwell time

5.3 성능 평가 결과
LSOM을 포함한 모든 경쟁 모델이 추론한 타겟 별 성능 지표는 모델의 설명력을 나타내는 결정계수(), 평균 제곱근 오차(RMSE), 평균 절대 오차(MAE)를 활용하였으며, 10-Fold 교차 검증을 통해 산출된 각 지표의 평균과 표준편차는 Table 1과 같다. 실험 결과에 따르면 제안하는 LSOM 모델은 타겟 , ,  모든 시점에 대해 다른 비교 모델 전체를 능가하는 예측 정확도를 달성하였다. 프리캐싱 전송 한계량을 산출하는 핵심 척도인 현 RSU 체류 시간()에 대해 베이스라인 중 가장 예측 정확도가 뛰어난 경쟁 모델인 CatBoost가 평균 122.432의 RMSE를 기록한 데 반해, LSOM은 RMSE를 평균 111.854로 낮추고 는 평균 0.786을 달성하였다. 반면 어텐션 기반의 최신 딥러닝 모델인 FTT나 TabR의 는 각각 0.395와 0.558 수준에 머물며 전통적인 트리 기반 모델보다도 낮은 예측 정확도를 보였다. 이는 기존 딥러닝 모델들이 도심 트래픽 데이터의 비선형성을 정교하게 모델링할 수 없음을 시사한다.
한편으로 모든 경쟁 모델에서 공통적으로 다음 RSU 이탈시간()의 예측 정확도가 하락하는 양상이 확인된다. 이는 에 대한 예측이 단순히 차량의 단순 도로 이동 시간에 더해, 다음 교차로 영역 내부로 진입한 후 발생하는 신호등 대기와 정체와 같은 동적인 교통 변수들로 인한 추가 체류 시간의 불확실성이 지속적으로 누적 반영되기 때문이다. 즉, 와 같이 예측의 시공간적 범위가 증가함에 따라 누적되는 불확실성으로 인해 타겟의 분포가 복잡해지고 예측 난이도가 비약적으로 상승하게 된다. LSOM은 순차적 시간 제약을 보장하며 의 예측에 대해서도 성능 저하를 완화하여 다른 경쟁 모델보다 강건한 예측 정확도를 달성하였다.
이러한 성능적 우수성을 분석하기 위해 제안하는 LSOM과 기계학습 앙상블 모델 중 가장 우수한 CatBoost, 딥러닝 기반 모델 중 가장 우수한 TabR에 대한 잔차 분석 결과를 Fig. 2에서 제시한다. 또한 각 경쟁 모델이 실제 데이터의 다봉성 분포를 얼마나 효과적으로 모델링하는지 정량적으로 평가하기 위해, 타겟의 실제 분포와 예측 분포 간의 거리를 평가하는 Wasserstein 거리(WD) 지표와 실제값과 예측값에 대한 항등함수를 나타내는  대각 점선과 모델의 최적 적합선 간의 일치 상관 계수(CCC) 지표를 측정하여 Fig. 3과 같이 제시하였다. Fig 2.의 현 RSU 체류 시간에 대한 잔차 분석 결과에서 LSOM의 최적 적합선(빨간색 실선)은 로 형성되어 대각 점선에 완벽히 정렬되어 있음을 확인할 수 있다. 반면 CatBoost와 TabR은 다소 틀어진 최적 적합선이 형성됨을 확인할 수 있다. 특히 TabR은 데이터가 특정 구간에서 수직으로 길게 늘어지는 전형적인 모드 붕괴 양상을 보였다. 예측 난이도가 비약적으로 상승하는 다음 RSU 체류 시간()의 분포에서는 극명한 차이가 나타난다. TabR은 방향성을 잃고 발산하였으며(), LSOM과 CatBoost는 불확실성이 커짐에 따라 예측 정확도가 모두 저하되었다. 하지만 LSOM은 TabR과 달리 모드 붕괴 양상이 나타나지 않으며, 다음 RSU 체류 시간의 실제 분포와 가장 유사한 예측 분포를 학습하고 있음을 확인할 수 있다.
이러한 모델 간 예측 분포의 차이는 Fig. 3에서 명확하게 나타난다. WD가 작을수록 실제 분포와 예측 분포가 구조적으로 유사하며, CCC가 높을수록 분포가 수치적으로 일치함을 의미한다. 기존 딥러닝 기반 베이스라인들은 전반적으로 높은 WD와 낮은 CCC를 보였으며, 이는 타겟의 실제 분포가 가진 특징인 꼬리가 긴(long-tailed) 다봉성을 정확히 포착하지 못한다는 것을 의미한다. 따라서 딥러닝 기반 베이스라인들은 평균 회귀에 빠져 모드 붕괴 문제를 겪게 된다. 이와 대조적으로 LSOM은 현 RSU 체류 시간 및 다음 RSU 체류 시간 모두에 대해서 가장 낮은 WD와 가장 높은 CCC를 달성하여 앙상블 기반 기계학습 베이스라인들보다 실제 분포에 더 가까운 예측 분포를 학습함을 입증하였다.
결론적으로 이러한 실험 결과는 LSOM이 중앙 집중형 궤적 추적의 도움 없이 단일 스냅샷 정보와 엣지 노드의 가벼운 추론만으로도 모빌리티 환경의 불확실성을 통제할 수 있음을 입증한다. 이는 프리캐싱 단계에서 과대 추정으로 인한 백홀 대역폭의 심각한 낭비나, 과소 추정으로 인한 서비스 단절 현상을 방지할 수 있는 핵심 기술 기반이 된다. 
Fig.  Access Delay per Model
Fig. 4에서 확인할 수 있듯이, 기존 모델들의 경우 다봉성을 띄는 도심 궤적의 딜레마를 정확히 포착해 내지 못하여 평균 90ms 수준의 지연을 발생시켰습니다. 그러나 제안하는 LSOM 기법은 최적운송 기반의 정밀한 선형 공간 매핑을 통해 예측 오차를 크게 줄여 69.4ms의 가장 낮은 지연 시간을 달성하였습니다. 또한, Fig. 4에서 확인할 수 있듯이, 도심 환경의 신호 대기 등으로 차량이 멈췄음에도 모델이 주행 중일 것이라 오판하는 경우 엄청난 양의 선제적 캐싱 트래픽 낭비가 발생합니다. 다른 예측 기법들은 평균 약 67MB의 자원을 낭비했으나, LSOM 기법은 이동성 불확실성을 강건하게 잡아내어 53.07MB만을 기록하며 가장 높은 엣지 캐시 적중 효율을 뽐냈습니다.
Fig.  Wasted traffic per Model


6. 결  론
본 논문에서는 4차 산업혁명 시대의 자율주행 및 커넥티드 카 환경에서 폭증하는 대용량 데이터 트래픽 문제를 해결하기 위해, 엣지 컴퓨팅 기반의 지능형 프리캐싱 프레임워크를 제안하였다. 특히 기존 연구들이 간과해왔던 도심 교통의 복잡한 다봉성 분포와 불확실성 문제를 해결하기 위해, 선형 공간 최적화와 조건부 사전 분포 기반의 흐름 매칭 기법을 결합한 LSOM 모델을 핵심 추론 엔진으로 도입하였다. 제안하는 프레임워크는 차량의 지속적인 위치 추적에 의존하던 기존의 중앙 집중형 방식에서 탈피하여, 차량 진입 시점의 단일 스냅샷 데이터만으로 엣지 노드 스스로 판단하고 행동하는 분산형 자율 제어 구조를 실현하였다.
시뮬레이션을 통한 성능 검증 결과, 제안 기법은 기존 방식들에 비하여 사용자 지연 시간이 22.9% 감소하였고, 낭비되는 트래픽 문제를 20.5% 개선하였으며, 신호등이나 돌발 정체와 같은 가변적인 도로 상황에서도 높은 예측 정확도를 유지함을 확인하였다. 이는 고가의 GPU 서버나 복잡한 통신 인프라 증설 없이도, 현재 구축된 RSU 인프라와 경량화된 AI 모델을 결합하여 차세대 모빌리티 서비스를 즉시 수용할 수 있는 실용적인 해법임을 시사한다. 본 연구는 향후 LSOM 모델을 실제 도심 도로에 설치된 RSU 테스트베드에 이식하여 실증적인 성능을 검증하고, 다양한 기상 조건이나 사고 상황과 같은 비정형 데이터까지 학습할 수 있도록 모델을 고도화하는 방향으로 연구를 확장할 계획이다.

References
[1] Z. Zhang, C. -H. Lung, M. St-Hilaire and I. Lambadaris, “Smart Proactive Caching: Empower the Video Delivery for Autonomous Vehicles in ICN-Based Networks,” IEEE Transactions on Vehicular Technology, Vol 69, No.7, pp.7955-7965, 2020.
[2] Ericsson Mobility Report [Internet], https://www.ericsson.com/en/reports-and-papers/mobility-report/dataforecasts/mobile-traffic-forecas.
[3] V. Jacobson, D.K. Smetters, J.D. Thornton, M.F. Plass, N.H. Briggs and R.L. Braynard, “Networking Named Content,” in Proceedings of the 5th international conference on Emerging networking experiments and technologies, Rome, Italy, 2009, pp.1-12.
[4] Z. Li, Y. Chen, D. Liu and X. Li, “Performance analysis for an enhanced architecture of IoV via Content-Centric Networking,”  EURASIP Journal on Wireless Communications and Networking, Vol.2017, No.1, pp.1-7, 2017.
[5] H. Ding et al., “Probabilistic Data Prefetching for Data Transportation in Smart Cities,” IEEE Internet of Things Journal, Vol.9, No.3, pp.1655-1666, 2022.
[6] Y. Wu, X. Fang, C. Luo and G. Min, “Intelligent Content Precaching Scheme for Platoon-Based Edge Vehicular Networks,” IEEE Internet of Things Journal, Vol.9, No.20, pp.20503-20518, 2022.
[7] S. Wang and D. Grace, “A Hybrid Proactive Caching System in Vehicular Networks Based on Contextual Multi-Armed Bandit Learning,” IEEE Access, Vol.11, pp.29074-29090, 2023.
[8] H. Elsayed, M. Ibrahim, H. Khedr and M. El-Shafie, “Predictive Proactive Caching in VANETs for Social Networking,” IEEE Transactions on  Vehicular Technology, Vol.71, No.5, pp.5298-5313, 2022.
[9] K. Jiang, Y. Cao, Y. Song, H. Zhou, S. Wan and X. Zhang, “Asynchronous Federated and Reinforcement Learning for Mobility-Aware Edge Caching in IoV,” IEEE Internet of Things Journal, Vol.11, No.9, pp.15334-15347, 2024.
[10] G. T. Maale et al., “DeepFESL: Deep Federated Echo State Learning-Based Proactive Content Caching in UAV-Assisted Networks,” IEEE Transactions on  Vehicular Technology, Vol.72, No.9, pp.12208-12220, 2023.
[11] S. Khanal, K. Thar and E. Huh, “Route-Based Proactive Content Caching Using Self-Attention in Hierarchical Federated Learning,” IEEE Access, Vol.10, pp.2169-3536, 2022.
[12] C. Wang et al., “Mobility and Context-Aware Precaching Strategy Using Spatial-Temporal Informer for Vehicular Service,” IEEE Internet of Things Journal, Vol.12, No.11, pp.16053-16066, 2025.
[13] Y. Zhang, R. Wang, Y. Wang, M. Chen and M. Guizani, “Diversity-Driven Proactive Caching for Mobile Networks,” IEEE Transactions on Mobile Computing, Vol.23, No.7, pp.7878-7894, 2023.
[14] Y. Romano, E. Patterson and E. Candes, “Conformalized quantile regression,” Advances in neural information processing systems, Vol.32, pp.1-11, 2019.
[15] L. Breiman, “Random forests,” Machine learning, Vol.45, No.1, pp.5-32, 2001.
[16] T. Chen and C. Guestrin, “Xgboost: A scalable tree boosting system,” in Proceedings of the 22nd acm sigkdd international conference on knowledge discovery and data mining, San Francisco, CA, USA, 2016, pp.785-794.
[17] L. Prokhorenkova, G. Gusev, A. Vorobev, A.V. Dorogush and A. Gulin, “CatBoost: unbiased boosting with categorical features,” Advances in neural information processing systems, Vol.31, pp.1-11, 2018.
[18] Y. Gorishniy, I. Rubachev, V. Khrulkov and A. Babenko, “Revisiting deep learning models for tabular data,” Advances in neural information processing systems, Vol.34, pp.18932-18943, 2021.
[19] Y. Gorishniy, I. Rubachev, N. Kartashev, D. Shlenskii, A. Kotelnikov and A. Babenko, “Tabr: Tabular deep learning meets nearest neighbors in 2023,” in Proceedings of the Twelfth International Conference on Learning Representations, Vienna, Austria, 2024, pp.1-39.
[20] T. Akiba, S. Sano, T. Yanase, T. Ohta and M. Koyama, “Optuna: A next-generation hyperparameter optimization framework,” in Proceedings of the 25th ACM SIGKDD international conference on knowledge discovery & data mining, Anchorage, AK, USA, 2019, pp.2623-2631.



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



김 정 훈
http://orcid.org/0000-0001-8209-5944
e-mail: kimjh@kunsan.ac.kr
2017년 충북대학교 소프트웨어학과
       (학사)
2019년 충북대학교 소프트웨어학과
       (석사)
2023년 충북대학교 소프트웨어학과 (박사)
2025년～현  재 국립군산대학교 컴퓨터정보공학과 조교수
관심분야:Data mining and analysis, Machine learning, Artificial intelligence, Pattern recognition, Computer vision, Databases, Big data systems.
