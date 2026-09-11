
V2I 환경에서 최적 운송 기반 고속 Rectified Flow 체류 시간 예측 기법
강명호*,남영주**
Optimal Transport-based Fast Rectified Flow Dwell Time Prediction Scheme in V2I Environments
MyungHo Kang*, Youngju Nam**



요  약

기존의 결정론적 회귀 모델은 다봉성 분포를 학습할 때 평균 회귀 문제로 인해 예측치가 중간값에 머무르는 한계를 지니며, 기존 확산 모델은 역과정에서 반복 연산이 많아 실시간 V2I 서비스에 적용하기 어렵다. 본 논문은 데이터 분포와 노이즈 분포 사이의 확률 흐름 경로를 직선화해 약 10회의 오릴러 적분만으로 체류 시간을 예측하고, 시뮬레이션에서 교차로 내부 연결 차선을 통과할 때 발생하는 위치 추적 오류를 절대 좌표 기반 수집 방식으로 보정함으로써 데이터 신뢰성을 확보한 기법을 제안한다. 

Abstract
Deterministic regression models trained on multimodal distributions tend to collapse toward the median value, a mean-regression effect, and conventional diffusion models need hundreds of reverse-process steps that make them impractical for real-time V2I use. The proposed model instead straightens the probability-flow trajectory between the data and noise distributions, so dwell-time prediction is completed with roughly 10 Euler integration steps.
 
Keywords
optimal transport rectified flow, generative model, V2I precaching, dwell time prediction, multimodal distribution















































































































































 * 강명호(Myungho Kang)
** 남영주(Youngju Nam)
국립군산대학교 소프트웨어학과 조교수(교신저자)
   ORCID: 0000-0003-3971-0715
 Received: 00 17, 2026, Revised: 00 20, 2026, Accepted: 00 15, 2026
 Corresponding Author: Youngju Nam
  Dept. of Software
  South Korea 
  Tel.: +82-063-469-8919, Email: imnyj@kunsan.ac.kr









I. 서  론

차량-인프라 통신(Vehicle-to-Infrastructure, 이하 V2I) 기술이 자율주행·커넥티드카 서비스로 확장되면서, 차량의 역할은 이동 수단을 넘어 고화질 인포테인먼트를 제공하는 플랫폼으로 바뀌고 있다[1, 2]. 4K·8K 비디오 스트리밍, 실시간 3D 정밀 지도 증강 현실 내비게이션과 같은 대용량 서비스 수요가 늘어나면서 차량 통신 데이터 소비량은 연평균 25% 이상씩 증가하는 추세이며, 이는 한정된 무선 대역폭과 백홀 네트워크에 상당한 부하로 이어지고 있다[3]

이러한 대규모 대역폭 요구 조건을 충족하기 위해 도로변 기지국(Roadside Unit, 이하 RSU)와 차량 간의 직접적인 V2I 통신 인프라가 주목받고 있다. RSU는 차량과 가까운 거리에서 5.9 GHz WAVE 혹은 C-V2X 표준을 통해 고속 통신을 지원하며, 콘텐츠 중심 네트워킹(Content-Centric Networking, 이하 CCN) 기술과 결합하여 자주 요청되는 인기 콘텐츠를 로컬 저장소에 선제적으로 캐싱함으로써 백홀 대역폭 절약과 전송 지연 단축을 지원한다[4, 5].

이처럼 급증하는 대역폭 수요에 대응하기 위한 방안으로, 차량과 직접 통신하는 RSU 기반 V2I 인프라가 부상하고 있다. RSU는 5.9 GHz WAVE 또는 C-V2X 표준으로 차량과 근거리 고속 통신을 맺으며, CCN 구조를 결합해 인기 콘텐츠를 로컬 저장소에 미리 캐싱함으로써 백홀 대역폭을 절약하고 전송 지연을 줄인다[4, 5].

다만, 도심 환경에서는 차량이 RSU 커버리지를 지나가며 핸드오버를 반복적으로 겪는다. 핸드오버 경계 구간이나 채널 페이딩이 심한 구간에서 대역폭이 떨어지면 비디오가 끊기거나 정밀 지도가 유실되는 등 서비스 품질이 저하된다. 이 문제를 완화하려면 차량이 다음 RSU 영역에 진입하기 전, 필요한 데이터를 백홀 링크로 미리 옮겨두는 프리캐싱 기술이 뒷받침되어야 한다.

Long Short-Term Memory(이하 LSTM), Gated Recurrent Unit(이하 GRU), LightGBM과 같이 선행 연구에서 널리 쓰인 결정론적 회귀 모델은 평균제곱오차를 최소화하도록 학습되기 때문에, 실제 도로에서는 나타나기 어려운 두 봉우리의 중간값인 20~25초 부근으로 예측치가 수렴하는 평균 회귀 문제를 안고 있다. 이렇게 왜곡된 예측값을 근거로 전송을 결정하면 프리캐싱 오류로 직결된다. 최근에서는 이를 보완하고자 Denoising Diffusion Probabilistic Model(이하 DDPM) 등 확산 모델이 시도되고 있지만, 역방향 노이즈 제거 과정에서 수백 회의 수치 적분이 필요해 실시간 연산이 요구되는 엣지 RSU 환경에는 적합하지 않다.

이에 본 논문은 V2I 도심 교차로에서 나타나는 다봉성 불확실성을 모델링하면서도 엣지 노드의 실시간 연산 제약을 만족시키기 위해, 최적 운송 이론과 흐름 매칭 기법을 결합한 고속 Rectified Flow 체류 시간 예측 기법을 제시한다. 제안 기법은 초기 노이즈 분포와 실제 차량의 2D 트래킹 체류 데이터 분포 사이의 확률 흐름 경로를 직선에 가깝게 학습함으로써 10스텝 안팎의 오일러 적분만으로 3 ms 이하의 추론 속도를 확보하며, 레일리 페이딩 채널 환경에서도 프리캐싱 적중률과 전송 성능을 유지한다.

II. 관련 연구

2.1 V2I 이동성 예측과 불확실성

차량 이동성 예측 기법은 인프라 캐싱 성능을 좌우하는 핵심 요소로 다뤄져 왔다. 초창기에는 등가속도 물리 모델을 전제로 한 칼만 필터와 확률 기하학 모델이 쓰였지만, 신호등 점멸이나 도심 주행 중 급감속처럼 변동성이 큰 상황을 고정된 규칙으로는 반영하기 힘들었다. 이후 데이터 기반 접근이 발전하면서 LSTM, GRU 같은 시계열 순환 신경망과 시공간 인포머가 V2I 주행 모델링에 도입되었다[6, 7, 10]. 다만 도심 도로는 신호 주기에 따라 주행 패턴 자체가 달라지는 다봉성 분포를 보이는데, MSE 기반 오차 역전파는 이런 분포에서도 각 모드의 중간값으로 예측을 수렴시키는 평균 회귀 문제를 낳고, 결과적으로 프리캐싱 타이밍이 어긋나며 성능이 떨어진다.

2.2 생성형 인공지능 기반 시계열 예측

회귀 모델의 평균 회귀 한계를 넘어 다봉성 분포까지 예측하려는 시도로, 심층 생성 모델을 시계열 도메인에 적용하는 연구가 늘고 있다. DDPM과 스코어 기반 확률 미분 방정식은 점진적 노이즈 주입과 복원 과정을 통해 데이터 분포를 근사하는 데 쓰여 왔다[8, 9]. 다만 확산 모델 계열은 확률 경로가 곡선을 그리기 때문에 누적 오차를 줄이려면 역방향 디노이징을 수백 회 이상 반복해야 하고, 연산 자원이 제한된 RSU 엣지 노드에서는 이 지연이 실시간 서비스의 걸림돌이 된다. 이에 대한 대안으로 두 분포 사이를 최단 경로로 잇는 Flow Matching[11]과 Rectified Flow[12]가 제안된 바 있다. 본 논문은 최적 운송 정규화를 내장한 Rectified Flow 구조를 V2I 시계열 예측에 적용해 생성 경로의 곡률을 최소화하고, 이를 통해 예측 정확도와 실시간 연산 성능을 동시에 확보한다.

III. 네트워크 및 채널 모델

3.1 차량 통신 환경 및 통신 구조

본 연구가 가정하는 네트워크 아키텍처는 5 km × 5 km 규모의 맨해튼 그리드 도로망을 기반으로 한다. 각 교차로 중앙에는 컴퓨팅 코어와 콘텐츠 저장 장치(Content Store, 이하 CS)를 갖춘 RSU가 분산 배치되며, RSU 간에는 1 Gbps 유선 백홀망으로 연결되어 제어 정보를 주고받는다. 차량-인프라 통신은 5.9 GHz WAVE 표준을 따르고, 전송 오버헤드를 줄이기 위해 정보 중심 네트워킹 구조를 적용한다.

차량 탑재 장치가 콘텐츠 요청 패킷을 보내면, RSU는 CS와 대기 요청 테이블, 전달 정보 베이스를 순차 조회해 캐시 상태를 확인하고, 적중 시 곧바로 데이터 패킷을 전달한다. 차량이 RSU 셀 경계를 지날 때 생기는 핸드오버 지연을 줄이기 위해 본 논문에서는 RSU가 주도적으로 인접 노드에 데이터를 선제 캐싱하는 전략을 적용해 통신 연속성을 확보한다.

3.2 체류 시간의 다봉성 및 예측 불확실성

분산 프리캐싱의 성패를 가르는 핵심 지표는 차량의 RSU 영역 내 체류 시간이다. 대상 교차로에는 실시간 교통량에 반응해 43~60초 주기로 바뀌는 신호 체계가 설치되어 있어 통행 흐름을 제한한다. 그 결과 수집된 체류 데이터는 정차 없이 통과하는 10초대와 적색 신호로 대기하는 40초 이상 구간에서 각각 피크를 이루는 이중 피크 가우시안 혼합 분포(Gaussian Mixture Model, 이하 GMM) 형태를 띤다. MSE 기반 최적화 모델은 통상 이 두 피크의 중간값인 25초 부근으로 수렴해 프리캐싱 타이밍 오차를 만들어내는데, 제안 모델은 이러한 다봉성 구조를 그대로 반영해 분포 자체를 예측하도록 설계했다.

3.3 무선 채널 모델 및 대역폭 불일치

V2I 통신 채널의 전파 감쇄와 멀티패스 산란을 함께 반영하기 위해 경로 손실 모델에 레일리 페이딩 확률 분포를 결합한다. 거리에 따른 무선신호 감쇄 계수를 반영한 거시 경로 손실 프로파일에 레일리 페이딩을 적용한 순간 무선 처리량은 식 1과 같이 표현된다.

(1)

WAVE 표준 대역폭 6 Mbps 환경에서 시뮬레이션을 수행한 결과, 채널 감쇄와 페이딩으로 인해 평균 처리량 대비 약 15.4%의 전송량 손실이 발생하였고, 특히 RSU 통신 영역 경계 부근에서는 수신 성능이 떨어지며 순간 전송 속도가 낮아지는 현상이 관측되었다. 이러한 페이딩 변동성 때문에 단순 결정론적 시간 예측만으로는 프리캐싱을 안정적으로 수행하기 어려워, 채널 평균 처리량을 포함한 문맥 정보를 반영한 안전 마진 설정이 필요하다.

IV. Rectified Flow 기반 예측 모델

4.1 시스템 입력 특징 설계 및 전처리

제안하는 Rectified Flow 모델은 차량이 RSU 안테나 커버리지에 진입하는 시점에 수집된 다차원 문맥 벡터를 입력받아, 차량의 미래 진출 시각 분포를 예측하도록 식 2와 같이 설계되었다.

(2)

위 구조를 구축하는 과정에서 교차로 구간 내 차량 위치 측정 오류를 별도로 해결해야 했다. 시뮬레이션 환경에서 교차로 노드의 물리적 중앙 구간은 일반 도로와 식별자·기하 구조가 달라 콜론 기호로 시작하는 특수 연결 차선으로 생성되는데, 기존 좌표 추출 방식은 이 구간을 통과할 때 파싱 오류로 위치 데이터를 놓치는 경우가 있었다. 그 결과 차량이 RSU 영역을 일시적으로 벗어난 것으로 잘못 인식되는 이중 진입 현상이 발생해 체류 시간 계산에 오차가 누적되었다. 이 문제는 TraCI의 절대 좌표 조회 기능을 활용해 교차로 통과 구간에서도 위치 데이터가 끊기지 않도록 수집함으로써 해결하였다.

한편 다단계 적분 추론에서는 시간이 거꾸로 흐르지 않도록 순서를 지켜야 하므로, 예측 대상을 절대 시각 벡터가 아니라 항상 양수 값을 갖는 차분 공간으로 바꾸어 학습하도록 구성했다. 차분 변환은 식 3으로 나타난다.

(3)

추론 네트워크는 이 간격 차분 벡터를 출력하도록 하고, 네트워크 말단에 Softplus 활성화 함수와 누적 합산 모듈을 적용해 예측된 시각 정보끼리 선후 관계가 뒤바뀌지 않도록 방지하였다.

4.2 Velocity Network 아키텍처

제안 모델의 핵심인 속도 네트워크는 복원 매핑 시간, 복원 상태 텐서, 조건 벡터를 입력받아 최적 이동 속도 필드를 산출한다. 연속적인 시간 변수의 해상도를 살리기 위해 시간 정보를 고차원 임베딩 벡터로 바꾸어 사용하며, 레이어 정규화와 비선형 활성화 함수를 결합한 잔차 블록을 다층으로 쌓아 네트워크를 구성했다. 조건 벡터는 층간 임베딩 공간에서 결합되어 조건부 생성을 제어하고, 잔차 연결 덕분에 학습 과정에서 발생할 수 있는 기울기 소실·폭발 문제도 완화되었다.

4.3 최적 운송을 적용한 직선 궤적 학습

제안 모델은 최적 운송 이론과 흐름 매칭 기법을 결합해, 가우시안 노이즈 분포와 실제 차량 데이터 분포 사이를 최단 거리인 직선 경로로 정렬한다. 임의학습 단계에서의 직선 보간 상태는 식 4로 설정된다.

(4)

상태 공간상의 순간 방향 필드가 항상 상수 방향 벡터와 일치하도록 수학적으로 구성한다. 상태 시간에 따른 미분 방정식은 식 5와 같이 선형성을 유지하게 된다.

 
(5)

이렇게 직선으로 구성된 경로는 수치 적분 과정에서 오차가 쌓이는 것을 막아준다. 속도 네트워크의 학습 목표인 손실 함수는 속도 필드 차이에 대한 평균 제곱 오차로 정의하며, 식 6과 같다.

(6)




4.4 오일러 기하 적분 기반 실시간 엣지 추론

직선화된 벡터 필드를 바탕으로 엣지 노드가 실시간 추론을 수행할 때는 10회의 적산 단계를 갖는 1차 오일러 적분만 수행하면 된다. 적산 단계의 이산화 시간은 0.1 단위의 균일한 간격으로 나누어 설정했으며, 순차 계산식은 식 7과 같다.

 (7)

예측 경로가 직선에 가깝게 구성되므로 단계별 적분 근사 오차가 거의 쌓이지 않으며, 저성능 프로세서 기반 엣지 환경에서도 3 ms 이하의 속도로 체류 시간 예측을 마쳐 제어 지연 시간을 줄일 수 있다.        
V. 성능 평가

5.1 시뮬레이션 환경 구축

 제안 기법을 검증하기 위해 차량 교통 환경 시뮬레이터 SUMO와 이산 패킷 통신 시뮬레이터 NS-3를 로컬 소켓으로 연동한 통합 시뮬레이션 환경을 구축했다. 평가 대상 도로는 가로·세로 각 5 km 면적의 맨해튼 그리드 도로망이며, 교차로 간격은 500~800 m 범위로 배치했다. 각 도로는 왕복 4차로에 좌·우회전 전용 차로를 포함하고, 교차로별로 신호 주기가 43~60초 범위에서 바뀌는 감응식 신호 제어 체계(Traffic Signal Control, 이하 TSC)를 운영해 황색 신호 및 적색 전 정지 시간까지 반영한 가감속·혼잡 상황을 재현했다.

기지국 노드는 교차로 중심에 총 9개를 분산 배치하고, 인접 노드 간 통신 중첩 영역이 생기도록 설계했다. RSU의 기본 통신 반경은 800 m로 설정했지만, 도심 빌딩의 차폐 효과를 반영해 실질 수신 거리는 300~500 m 수준으로 제한했다. 차량-기지국 통신은 IEEE 802.11p WAVE 표준의 6 Mbps 대역폭을 기준으로 하며, 레일리 페이딩과 빌딩 차폐 회절 손실 모델을 함께 적용해 교차로 모퉁이를 지날 때 순간 수신 신호 세기가 20 dB까지 급감하는 통신 환경을 구현했다.

차량 유입 시나리오는 혼잡·비혼잡 시간대를 결합해 5~10초 간격으로 무작위 진입하도록 설정했고, 동시에 최대 500대까지 기동하도록 했다. 교차로에 진입한 차량은 직진 60%, 좌회전 20%, 우회전 20%의 확률로 경로를 선택해 다음 목적지 RSU에 대한 불확실성을 부여했으며, RSU 영역 진입 시점에는 30%의 확률로 10~80 MB 크기의 대용량 콘텐츠 전송을 요청하도록 구성했다. 시뮬레이션은 총 3,600초간 진행했고, 수집된 로그 데이터를 바탕으로 각 지표를 평가했다.

5.2 성능 평가 결과 및 데이터 분석

교차로 구간에서 수집한 체류 시간 데이터는 차량의 주행 패턴에 따라 두 개의 뚜렷한 피크를 이루는 이중 피크 분포로 나타났다. 정차 없이 통과하는 차량은 5~20초의 짧은 체류 시간을, 적색 신호로 대기하는 차량은 40초 이상의 체류 시간을 기록했다. 체류 시간의 구간별 빈도 분포는 표 1과 같다.

표 1. 체류 시간 구간별 빈도 분포표
Table 1. Frequency Distribution Table by Duration of Stay Section


0~20초 구간(52.5%)과 41~60초 구간(23.2%)에 관측값이 몰려 있고 21~40초 구간은 16.2%에 그쳐, 이중 피크 가우시안 혼합 분포(GMM) 특성이 뚜렷하게 드러난다. 기존 순환 신경망 계열 회귀 모델은 MSE 손실 함수의 특성상 두 피크의 평균값인 25.4초 부근으로 예측치가 수렴하는 문제를 보였고, 이 평균 회귀 문제는 교차로 환경에서 프리캐싱 오작동으로 이어졌다. 비교 모델별 예측값 분포와 실제 데이터 분포의 비교는 표 2와 같다.

표 2. 비교 모델의 예측값 분포와 실제 데이터 분포 비교표
Table 2. Comparison table of the distribution of predicted values of comparison models and the distribution of actual data


이에 비해 제안하는 최적 운송 기반 Rectified Flow 기법은 가우시안 노이즈에서 출발해 이중 모드 경계를 구분해 냈고, 실제 데이터의 다봉성 분포를 비교 모델보다 정확하게 재현했다.

5.3 체류 시간 예측 정확도 비교

교차로 주행 데이터를 대상으로 비교 모델들의 체류 시간 예측 정확도를 평균절대오차(MAE)로 분석했다. 제안 기법은 직진 통과 차량 오차 1.8초, 적색 신호 대기 차량 오차 2.3초를 포함해 종합 MAE 2.09초를 기록했다. 기존 시계열 회귀 모델은 종합 오차 12.38초, 머신러닝 회귀 모델은 10.45초로, 제안 기법이 오차를 80% 이상 줄인 셈이다. 이는 교차로 통과 시 위치 측정 오류를 보정하고 최적 운송 기반 직선 경로 학습을 결합한 결과다. 비교 모델 전체의 MAE 결과는 표 3과 같다.

기존의 확산 확률 모델(DDPM)은 종합 MAE 2.12초로 제안 기법과 비슷한 정확도를 보였지만, 추론 지연 때문에 실시간 엣지 적용에는 한계가 있었다. 하지만 제안 기법의 MAE 개선율은 LSTM 대비 83.1%에 달해, 다봉성 분포에서 회귀 모델 계열이 겪던 구조적 한계를 생성 모델 기반 접근으로 해소했음을 확인했다.

표 3. 비교 모델별 교차로 체류 시간 예측 MAE 비교
Table 3. MAE comparison of intersection dwell time predictions by comparison models


5.4 실시간 추론 지연 및 V2I 프리캐싱 성능

저성능 프로세서 기반 엣지 장치에서 추론 지연을 측정하고, 레일리 페이딩 채널 환경에서의 프리캐싱 성능을 함께 평가했다. 수백 회의 역과정 연산이 필요한 기존 확산 모델과 스코어 기반 모델은 각각 480 ms, 2,400 ms 수준의 지연을 보였으나, 제안 기법은 궤적을 직선화한 덕분에 10회의 복원 단계만으로 3 ms 이하의 추론 속도를 달성했다. 모델별 추론 지연 성능은 표 4와 같다..

표 4. 비교 모델별 엣지 장비 추론 지연 시간 비교(로그 스케일
Table 4. Comparison of inference latency for edge devices by model (log scale)


프리캐싱 적중률 85.5%는 도심 교차로의 회전 경로 불확실성과 레일리 페이딩 채널 변동성을 함께 고려한 조건에서 얻은 결과다. 세션 완료율 90.8%는 신호 정지 구간의 전송 기회를 체류 시간 예측에 반영한 결과로, 제안 기법이 실시간 엣지 서비스 환경에 적용 가능함을 뒷받침한다. 도심 복잡 격자 도로망과 레일리 페이딩 채널을 포함한 통합 시뮬레이션의 최종 프리캐싱 성능은 표 5와 같다.

표 5. 통합 시뮬레이션 프리캐싱 성능 비교
Table 5. Comparison of Integrated Simulation Prefacening Performance


VI. 결론

본 논문은 신호등 구간에서 나타나는 차량 체류 시간의 다봉성과 불확실성이 V2I 프리캐싱 인프라의 효율적 자원 배치를 가로막는다는 문제의식에서, 최적 운송 기반 고속 Rectified Flow 체류 시간 예측 기법을 제안했다. 제안 기법은 두 분포 사이의 경로를 직선 형태의 벡터 필드로 학습해 10회 이내의 오일러 적분과 3 ms 이하의 연산 속도로 예측을 수행함으로써 RSU의 실시간 프리캐싱 요구를 충족시켰다. 시뮬레이션 내 교차로 위치 추적 결함은 절대 좌표 수집 방식으로 해결했고, 레일리 페이딩 채널 변동성 및 단순 프리캐싱 의사결정의 한계도 분석해 대응 방안을 제시했다. 최종적으로 2.1초 미만의 MAE, 85.5%의 프리캐시 적중률, 90.8%의 세션 완료율을 확보해 지능형 프리캐싱 시스템에서의 실효성을 확인했다. 향후에는 다중 교차로 경로 예측 모델과의 통합을 통해 플래툰 주행 차량군의 공동 프리캐싱 자원 관리로 연구 범위를 넓힐 계획이다.







References

[1] Q. Yuan, H. Zhou, J. Li, Z. Liu, F. Yang and X. S. Shen, “Toward Efficient Content Delivery for Automated Driving Services: An Edge Computing Solution,” IEEE Network, Vol.32, No.1, pp.80-86, 2018.
[2] V. Kumar, S. Mishra and N. Chand, “Applications of VANETs: Present & Future,” Communications and Network, Vol.5, No.1B, pp.12-15, 2013.
[3] Ericsson Mobility Report [Internet], https://www.ericsson.com/en/reports-and-papers/mobility-report/dataforecasts/mobile-traffic-forecas.
[4] V. Jacobson, D.K. Smetters, J.D. Thornton, M.F. Plass, N.H. Briggs and R.L. Braynard, “Networking Named Content,” in Proceedings of the 5th international conference on Emerging networking experiments and technologies, Rome, Italy, 2009, pp.1-12.
[5] Z. Su, Y. Hui and Q. Yang, “The Next Generation Vehicular Networks: A Content-Centric Framework,” IEEE Wireless Communications, Vol.24, No.1, pp.60-66, 2017.
[6] H. Elsayed et al., “Predictive Proactive Caching in VANETs for Social Networking,” IEEE Transactions on Vehicular Technology, Vol.71, No.5, pp.5298-5313, 2022.
[7] S. Wang and D. Grace, “A Hybrid Proactive Caching System in Vehicular Networks Based on Contextual Multi-Armed Bandit Learning,” IEEE Access, Vol.11, pp.29074-29090, 2023.
[8] J. Ho, A. Jain and P. Abbeel, “Denoising Diffusion Probabilistic Models,” in Proceedings of the Advances in Neural Information Processing Systems, 2020, pp. 6840-6851.
[9] Y. Song, J. Sohl-Dickstein, D. P. Kingma, A. Kumar, S. Ermon and B. Poole, “Score-Based Generative Modeling through Stochastic Differential Equations,” in Proceedings of the International Conference on Learning Representations, 2021.
[10] C. Wang et al., “Mobility and Context-Aware Precaching Strategy Using Spatial-Temporal Informer for Vehicular Service,” IEEE Internet of Things Journal, Vol.12, No.11, pp.16053-16066, 2025.
[11] Y. Lipman, R. T. Q. Chen, H. Ben-Hamu, M. Nickel and M. Le, “Flow Matching for Generative Modeling,” in Proceedings of the International Conference on Learning Representations, Kigali, Rwanda, 2023.
[12] X. Liu, C. Gong and Q. Liu, “Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow,” in Proceedings of the International Conference on Learning Representations, Kigali, Rwanda, 2023.

























저자소개


강 명 호 (Kang-Myung HO)

   사진
 2020년 3월 ~ 현재 : 국립군산대학교 소프트웨어학과(학사)

 관심분야 : IOT,네트워크, AI, Content-Centric Networks


남 영 주 (Nam-Young ju)

   사진
2017년 : 충북대학교 정보통신공학부 (학사)
2019년 : 충북대학교 전파통신공학과 (석사)
2023년 : 충북대학교 전파통신공학과 (박사)
2023년~2024년 : 충북대학교 		컴퓨터정보통신연구소 박사후연구원
2024년～현  재 : 국립군산대학교 소프트웨어학과 조교수

관심분야 : IoT, Vehicular Network, Content-Centric Networks, Precaching, Optimization, NS3, SUMO.

