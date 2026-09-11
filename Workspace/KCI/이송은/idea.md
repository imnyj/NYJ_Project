## 이송은 KCI

* 주제: V2I Precaching Decision DRL

* Main Idea: 강화학습을 통해 Next RSU에 Precaching을 하는지 옳았는지, 현재 RSU에서 끝내는 것이 옳았는지를 판단하는 결정을 최적화 한다.

* 근거: 기존 내 연구에서 Precaching 량을 최적화해왔지만 기본적으로 Precaching 판단에 대한 결정의 예측을 한 적이 없었다. 이것이 먼저 선행되었어야 했는데, 기초적이지만 지금와서라도 해보려고 한다.

* 저자: 이송은, 남영주 (교신저자: 남영주)

* 시뮬레이션 설계
src/sumo의 시뮬레이션 환경을 그대로 사용하여 시뮬레이션 구현.
V2I_Env에서 구현
    init(): 환경 초기화

    reset():
        for step
            sumo의 next step을 통해 차량 이동
            요청 차량 1대의 content을 확률적으로 발생
            if RSU에 진입해 있는지 확인
                현 RSU와 next RSU 파악
                state 생성 및 return
        예외 처리 및 init으로 시나리오 초기화
    
    step():
        action 다듬기
        action에 따라 next RSU에게 precaching 결정 (량에 대한 예측이 아니기 때문에 content가 모두 precached되었다고 가정)

        for step:
            if 요청 차량이 현 RSU 또는 Next RSU 범위 내에 있으면:
                요청 차량 content download
                
                if download 완료 check:
                    if precache 하도록 decision 된 경우:
                        현 RSU에서 다운 완료 = 패널티
                        Next RSU에서 다운 완료 = 리워드
                    else:
                        현 RSU에서 다운 완료 = 리워드
                        Next RSU에서 다운 완료 = 패널티
                    
                    # (Note: 잔여 step 수 N_rem은 현 시점의 '남은 거리 / 속도'로 추정하거나, 
                    # 에피소드 종료 전 현 RSU를 벗어날 때까지 시뮬레이션을 step만 진행시켜 정확히 잰 뒤 계산)
                    content의 남은 량과 현재 상태를 반영하여 next state 생성
                    done = true
                    리워드 반영하여 return

            else: # 요청 차량이 RSU 범위 밖(Outage Zone)에 있으면:
                # V2I 환경이므로 다운로드 불가, 이동만 진행 (Next RSU 진입 대기)
                pass
            
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

### 🧠 에이전트(AI)가 제안하는 State 및 Reward 상세 설계안

ST-MBAN의 공간적/네트워크 특징과 V2I Dwell Time의 핵심인 신호등 정보를 종합하여 다음과 같이 구체적인 State와 Reward를 제안합니다.

#### 1. State Space (상태 공간, $S_t$)
차량이 RSU 영역을 지나는 동안의 동적인 물리적/통신적 상태를 벡터화합니다.
*   **차량(Vehicle) 상태**
    *   `dist_to_current_rsu` (m): 현재 연결된 RSU 중심으로부터 차량까지의 거리 (커버리지 이탈 시점을 예측).
    *   `velocity` (m/s): 차량의 현재 속도.
*   **네트워크(Network) 상태**
    *   `remained_content_size` (MB): 타겟 차량이 아직 다운로드 받지 못한 남은 컨텐츠의 크기.
    *   `current_rsu_data_rate` (Mbps): 현재 RSU의 가용 통신 속도 (채널 상태나 트래픽 부하 반영).
*   **신호등(Traffic Light) 상태 (Dwell time의 핵심 변수)**
    *   `tl_phase` (Binary): 차량 진행 방향의 교차로 신호 상태 (Green = 1, Red = 0).
    *   `tl_remaining_time` (s): 현재 신호가 유지되는 남은 시간 (신호 대기로 인해 체류 시간이 길어질지 여부를 에이전트가 파악하도록 도움).

#### 2. Action Space (행동 공간, $A_t$)
Discrete 행동 공간으로 정의하며, 량(Quantity) 예측이 아니므로 이진 결정(Binary Decision)을 수행합니다.
*   $A_t \in \{0, 1\}$
    *   `0 (No Precache)`: Next RSU에 미리 컨텐츠를 넘겨두지 않음 (현재 RSU 내에서 완료될 것이라 확신).
    *   `1 (Precache)`: Next RSU로 컨텐츠 전체를 미리 넘겨둠 (Next RSU까지 이동해야 다운로드가 완료될 것이라 판단).

#### 3. Reward Function (보상 함수, $R_t$) [Optuna 튜닝 및 통신속도 반영]
사용자 설정(Step=1초, 통신속도 6Mbps 고정)에 따라, '거리($D_{rem}$)' 대신 **'잔여 체류 시간 동안 받을 수 있었던 데이터 량(MB)'**을 산출하여 스케일 불균형과 비선형성 문제를 완벽히 해결합니다.
또한, 수식의 가중치($\alpha, \beta, \gamma, \delta$)에 의한 작위적 편향을 막기 위해 **Optuna**를 활용하여 하이퍼파라미터 최적화를 수행합니다.

*   **상수 및 지표 정의**
    *   $C_{step} = 0.75$ MB (6Mbps 속도로 1초(1 Step) 동안 다운로드 가능한 량)
    *   $N_{rem}$: 다운로드 완료 후 현재 RSU 커버리지를 벗어날 때까지의 잔여 Step 수(초)
    *   $W_{curr} = N_{rem} \times C_{step}$: 현재 RSU에서 추가로 받을 수 있었으나 버려진(여유) 데이터 용량(MB)
    *   $C_{next}$: Next RSU로 이관된(또는 이관되었어야 할) 실제 남은 컨텐츠 량(MB)

*   **Case 1: 에이전트가 Precache ($A=1$)를 결정한 경우**
    *   **실제로 Next RSU 영역에서 다운로드 완료 시 (성공):** 
        *   보상: $R = +R_{base} + \alpha \left( \frac{C_{next}}{C_{total}} \right)$
        *   설명: Next RSU에서 실제로 활용된 데이터 량($C_{next}$) 비율에 비례하는 보너스.
    *   **현재 RSU 영역에서 다운로드 완료 시 (실패/자원 낭비):** 
        *   보상: $R = -P_{base} - \beta \left( \frac{W_{curr}}{C_{total}} \right)$
        *   설명: 낭비된 체류 시간 동안 받을 수 있었던 가상의 데이터 량($W_{curr}$) 비율에 비례하는 패널티.

*   **Case 2: 에이전트가 No Precache ($A=0$)를 결정한 경우**
    *   **실제로 현재 RSU 영역에서 완료 시 (성공):** 
        *   보상: $R = +R_{base} + \gamma \left( \frac{W_{curr}}{C_{total}} \right)$
        *   설명: 안전하게 완료하고 남은 여유 체류 시간의 데이터 량($W_{curr}$) 비율에 비례하는 보너스.
    *   **Next RSU 영역까지 넘어간 후 완료 시 (실패/지연 발생):** 
        *   보상: $R = -P_{base} - \delta \left( \frac{C_{next}}{C_{total}} \right)$
        *   설명: Precache 없이 Next RSU에서 새로 받아야 하는 지연 데이터 량($C_{next}$) 비율에 비례하는 패널티.
### 🔄 서비스 보장을 위한 교차 모델(Dual-Model) 아키텍처 도입
단일 에이전트 모델로 RSU를 운용할 경우, 모델이 새로운 데이터(배치)를 쌓고 가중치를 업데이트(학습)하는 동안 인퍼런스(추론)에 지연이 발생하거나 서비스가 중단될 우려가 있습니다. 이를 방지하여 **100% 서비스 가용성(Zero Downtime)**을 보장하기 위해 다음과 같은 아키텍처를 제안 방안에 포함합니다.

*   **구조:** RSU 내에 동일한 구조의 두 모델(Model A, Model B)을 적재합니다.
*   **운용 방식 (Ping-Pong 방식):**
    *   **Phase 1:** Model A는 인퍼런스(실시간 서비스 제공)를 담당하고, Model B는 백그라운드에서 수집된 배치를 통해 학습(가중치 업데이트)을 진행합니다.
    *   **Phase 2:** Model B의 학습이 완료되면, 즉각적으로 역할을 교대(Swap)하여 Model B가 인퍼런스를 담당하고 Model A가 새로운 배치를 모아 다음 학습을 준비합니다.
*   **기대 효과:** 모델 훈련 중에도 추론 지연 시간이 전혀 발생하지 않으며, NVIDIA Jetson과 같은 엣지 컴퓨팅 디바이스에서도 CPU/GPU 자원을 시분할로 효율적으로 사용하여 서비스 연속성을 확보할 수 있습니다.
