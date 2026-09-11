## 이송은 KCI

* 주제: Outage zone V2V Precaching Decision DRL

* Main Idea: 강화학습을 통해 Outage zone에서 Precaching을 하는지 옳았는지, 현재 RSU에서 끝내는 것이 옳았는지를 판단하는 결정을 최적화 한다.

* 근거: 기존 내 연구에서 Precaching 량을 최적화해왔지만 기본적으로 Precaching 판단에 대한 결정의 예측을 한 적이 없었다. 이것이 먼저 선행되었어야 했는데, 기초적이지만 지금와서라도 해보려고 한다.

* 저자: 나준상, 남영주 (교신저자: 남영주)

* 시뮬레이션 설계
src/sumo의 시뮬레이션 환경을 그대로 사용하여 시뮬레이션 구현.
V2V_Env에서 구현
    init(): 환경 초기화

    reset():
        for step
            sumo의 next step을 통해 차량 이동
            요청 차량 1대의 content을 확률적으로 발생
            if RSU에 진입해 있는지 확인
                현 RSU와 next RSU 파악
                현 RSU 내에서 요청 차량과 같은 next RSU를 가지는 차량들을 후보로 하여 state와 전역 변수로 반영함.
                state 생성 및 return
        예외 처리 및 init으로 시나리오 초기화
    
    step():
        action 다듬기
        action에 따라 모든 후보 차량들에게 content precaching 결정.
        N_rem = 0  # 낭비된/여유 잔여 step 측정용
        is_download_complete = false

        for step:
            if 요청 차량이 RSU 범위에 있으면:
                if not is_download_complete:
                    요청 차량 content download
                    후보 차량이 RSU 범위에 있으면 content precaching (content size만큼 precaching 했으면 더 이상 pass)

                    if download 완료 check:
                        is_download_complete = true
                else:
                    # 다운로드는 이미 완료되었으나, RSU를 완전히 벗어날 때까지 낭비된/여유 체류 시간을 실측
                    N_rem += 1

            else: # 요청 차량이 RSU 범위 밖에 있으면 (Outage Zone 진입 시점)
                if is_download_complete:
                    # 1. 이미 현 RSU에서 다운로드를 끝내고 Outage Zone에 진입한 경우 (에피소드 종료)
                    if precache 하도록 decision 된 경우:
                        현 RSU에서 다운 완료 = 패널티 (N_rem 기반 가중치 반영)
                    else:
                        현 RSU에서 다운 완료 = 리워드 (N_rem 기반 가중치 반영)
                    content의 남은 량과 현재 상태를 반영하여 next state 생성
                    done = true
                    리워드 반영하여 return
                
                else:
                    # 2. 다운로드를 못 끝내서 V2V로 이어서 받아야 하는 경우
                    if 후보 차량이 한 대라도 요청 차량의 범위에 있으면:
                        요청 차량 content download
                        요청 차량과 현재 연결 가능한 모든 후보 차량은 그 만큼 precached에서 차감
                    
                    if download 완료 check (V2V 다운로드 완료 시):
                        V2V 활용에 따른 리워드/패널티 반영
                        done = true
                        return

            sumo의 next step을 통해 차량 이동

* 추가 설정
 - Content size는 WiFi를 사용하여 RSU 하나 혹은 두 개를 지나도록 설정.
 - 필요한 경우, 대략적인 차량의 dwell time 측정을 먼저해도 좋음.
 - 신호가 걸리고 안 걸리고가 가장 큰 dwell time 결정 사안이므로 state에 반영해야 함.
 - step당 다운로드 량은 step을 1초로 하여 1초당 받을 수 있는 량을 constant로 활용한다.
 - 통신속도는 가장 안정적인 6Mbps로 한다.

* 시뮬 설명
 - 비교 방안 SB3의 SAC, TD3
 - 모델들을 하나씩 불러와 환경을 learn(), save()

* 참고할 것들
 - KCI 글의 길이, 양식, 스타일 등은 LSOM을 따를 것.
 - State 설계는 ST-MBAN을 참고할 것.

---

### 🧠 에이전트(AI)가 제안하는 State 및 Reward 상세 설계안 (Outage Zone V2V)

이송은 연구원의 V2I 상황과 달리, 나준상 연구원의 모델은 **'Outage Zone(RSU 음영지역)'**에서의 **V2V(차량 간 통신) Precaching 효율성**에 초점이 맞춰져 있습니다. 따라서 주변 후보 차량들의 존재 여부(밀도)와 위치가 State에 추가되어야 합니다.

#### 1. State Space (상태 공간, $S_t$)
*   **타겟 차량(Target Vehicle) 상태**
    *   `dist_to_current_rsu` (m): 현재 RSU 중심으로부터 타겟 차량까지의 거리.
    *   `velocity` (m/s): 타겟 차량의 현재 속도.
*   **V2V 후보 차량(Candidate Vehicles) 상태 [통계적 압축 방식 적용]**
    *   `num_candidates` (int): 동일한 Next RSU를 향해 주행 중인 후보 차량의 총 수 (V2V 통신 가능 풀의 크기).
    *   `avg_relative_dist` (m): 타겟 차량과 후보 차량들 간의 평균 상대 거리.
    *   `std_relative_dist` (m): 타겟 차량과 후보 차량들 간 거리의 표준편차 (차량들이 얼마나 오밀조밀하게 군집(Platoon)을 이루고 있는지 판단).
    *   `avg_relative_velocity` (m/s): 타겟 차량과 후보 차량들 간의 평균 상대 속도 (후보 차량 무리가 멀어지고 있는지, 가까워지고 있는지를 판단하여 Outage Zone 내 연결 유지 시간 예측).
*   **네트워크(Network) 상태**
    *   `remained_content_size` (MB): 타겟 차량이 아직 받지 못한 남은 컨텐츠 크기.
*   **신호등(Traffic Light) 상태 (Dwell time 예측용)**
    *   `tl_phase` (Binary) & `tl_remaining_time` (s): 차량 진행 방향의 교차로 신호 상태 및 남은 시간.

#### 2. Action Space (행동 공간, $A_t$)
*   $A_t \in \{0, 1\}$
    *   `0 (No V2V Precache)`: 후보 차량들에게 미리 컨텐츠를 뿌리지 않음 (현재 RSU 내에서 완료될 것이라 확신).
    *   `1 (V2V Precache)`: 현재 RSU가 타겟 차량뿐만 아니라 모든 후보 차량에게도 동일한 컨텐츠를 미리 Broadcasting 해둠 (Outage Zone에 진입할 것이라 판단).

#### 3. Reward Function (보상 함수, $R_t$) [Optuna 튜닝 및 통신속도 반영]
Step=1초, 통신속도 6Mbps($C_{step}=0.75$MB) 고정 조건을 활용하여, 자원 낭비량과 V2V 활용량을 MB 단위의 Continuous Scale로 계산합니다. 가중치는 Optuna로 튜닝합니다.

*   **상수 및 지표 정의**
    *   $N_{rem}$: 다운로드 완료 후 현재 RSU를 벗어날 때까지의 잔여 Step 수.
    *   $W_{curr} = N_{rem} \times 0.75$: 현재 RSU에서 추가로 받을 수 있었으나 버려진(여유) 데이터 용량(MB).
    *   $C_{v2v}$: Outage Zone 진입 후 후보 차량들로부터 V2V를 통해 성공적으로 다운로드 한(또는 해야 했던) 데이터 량(MB).

*   **Case 1: 에이전트가 V2V Precache ($A=1$)를 결정한 경우**
    *   **Outage Zone 진입 후 V2V 다운로드 시 (성공):** 
        *   $R = +R_{base} + \alpha \left( \frac{C_{v2v}}{C_{total}} \right)$
        *   (음영지역에서 V2V로 커버한 데이터 량에 비례하여 보너스)
    *   **현재 RSU 영역에서 다운로드 완료 시 (실패/자원 낭비):** 
        *   $R = -P_{base} - \beta \left( \frac{W_{curr} \times num\_candidates}{C_{total}} \right)$
        *   (여유 시간이 많았음에도, 굳이 다수의 후보 차량에게 브로드캐스팅하느라 낭비된 백홀 트래픽에 비례하여 강한 패널티)

*   **Case 2: 에이전트가 No V2V Precache ($A=0$)를 결정한 경우**
    *   **현재 RSU 영역에서 완료 시 (성공):** 
        *   $R = +R_{base} + \gamma \left( \frac{W_{curr}}{C_{total}} \right)$
        *   (후보 차량 트래픽 낭비 없이 완벽히 끝낸 여유 시간에 비례하여 보너스)
    *   **Outage Zone 진입 후 다운로드 중단 시 (실패/지연 발생):** 
        *   $R = -P_{base} - \delta \left( \frac{C_{v2v\_missed}}{C_{total}} \right)$
        *   (V2V Precache를 안 해서 음영지역에서 받지 못하고 딜레이된 데이터 량에 비례하여 패널티)
### 🔄 서비스 보장을 위한 교차 모델(Dual-Model) 아키텍처 도입
단일 에이전트 모델로 RSU를 운용할 경우, 모델이 새로운 데이터(배치)를 쌓고 가중치를 업데이트(학습)하는 동안 인퍼런스(추론)에 지연이 발생하거나 서비스가 중단될 우려가 있습니다. 이를 방지하여 **100% 서비스 가용성(Zero Downtime)**을 보장하기 위해 다음과 같은 아키텍처를 제안 방안에 포함합니다.

*   **구조:** RSU 내에 동일한 구조의 두 모델(Model A, Model B)을 적재합니다.
*   **운용 방식 (Ping-Pong 방식):**
    *   **Phase 1:** Model A는 인퍼런스(실시간 서비스 제공)를 담당하고, Model B는 백그라운드에서 수집된 배치를 통해 학습(가중치 업데이트)을 진행합니다.
    *   **Phase 2:** Model B의 학습이 완료되면, 즉각적으로 역할을 교대(Swap)하여 Model B가 인퍼런스를 담당하고 Model A가 새로운 배치를 모아 다음 학습을 준비합니다.
*   **기대 효과:** 모델 훈련 중에도 추론 지연 시간이 전혀 발생하지 않으며, NVIDIA Jetson과 같은 엣지 컴퓨팅 디바이스에서도 CPU/GPU 자원을 시분할로 효율적으로 사용하여 서비스 연속성을 확보할 수 있습니다.
