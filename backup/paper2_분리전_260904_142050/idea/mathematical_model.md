# Mathematical Formulation (PAMDP)

본 문서는 UAV 선제적 핸드오버 스케줄링을 위한 Parametrized Action Markov Decision Process (PAMDP) 수학적 모델링을 정의합니다.

## 1. 시스템 모델 (System Model)
- **통신망 집합**: $\mathcal{N} = \{n_S, n_C, n_R\}$ (각각 Starlink, Cellular, RSU를 의미)
- **UAV 궤적**: 
  - 시간 $t$에서의 사전에 스케줄링된 위치 및 속도: $L^{sch}(t), V^{sch}(t)$
  - GPS/IMU로 측정된 실제 위치 및 속도: $L^{act}(t), V^{act}(t)$
  - **추적 오차 (Tracking Error)**: $e(t) = L^{act}(t) - L^{sch}(t)$

## 2. PAMDP 구성 요소

의사결정 시점(Decision Epoch) $k$에서의 상태, 행동, 보상은 다음과 같이 정의됩니다. $t_k$는 $k$번째 의사결정이 내려지는 시간입니다.

### 2.1. 상태 공간 (State Space, $\mathcal{S}$)
상태 $s_k \in \mathcal{S}$는 UAV가 행동을 결정하기 위해 관측하는 정보들의 집합입니다.
$$ s_k = \Big[ c_k, \; L^{sch}(t_k), \; \mathcal{H}_k, \; \mathbf{Q}_k \Big] $$
- $c_k \in \mathcal{N}$: 현재 접속 중인 통신망
- $L^{sch}(t_k)$: 현재 스케줄링된 위치
- $\mathcal{H}_k = \{e(t_k), e(t_{k-1}), \dots, e(t_{k-W+1})\}$: 윈도우 크기 $W$ 동안의 추적 오차 히스토리 (바람 등 불확실성 추론용)
- $\mathbf{Q}_k = \{ (B_n, D_n) \mid n \in \mathcal{N} \}$: 각 통신망 $n$의 예상 대역폭($B$)과 지연시간($D$) 상태

### 2.2. 행동 공간 (Action Space, $\mathcal{A}$)
하이브리드 행동(Parametrized Action) $a_k \in \mathcal{A}$는 이산 변수와 연속 변수의 쌍으로 정의됩니다.
$$ a_k = (m_k, \; \tau_k) $$
- **Discrete Action ($m_k$)**: 전환할 타겟 통신망. $m_k \in \mathcal{N}$ (만약 $m_k = c_k$라면 망 유지)
- **Continuous Action ($\tau_k$)**: 다음 의사결정(핸드오버 시도)까지 대기할 시간. $\tau_k \in (0, \tau_{max}]$

### 2.3. 보상 함수 (Reward Function, $\mathcal{R}$)
보상 $r_k$는 행동 $a_k$를 수행하는 시간 구간 $[t_k, t_k+\tau_k]$ 동안 얻는 QoE 이득과 핑퐁(Ping-pong) 패널티의 Trade-off로 정의됩니다.
$$ r_k = \alpha \int_{t_k}^{t_k+\tau_k} \text{QoE}(t) dt - \beta \cdot \mathbb{I}(m_k \neq c_k) \cdot P_{HO} $$
- $\text{QoE}(t) = w_1 \log(1 + B_{m_k}(t)) - w_2 D_{m_k}(t)$: 대역폭에 비례하고 지연시간에 반비례하는 서비스 품질 함수
- $\mathbb{I}(\cdot)$: 조건이 참이면 1, 거짓이면 0을 반환하는 지시 함수 (Indicator Function)
- $P_{HO}$: 핸드오버 발생 시 부과되는 패널티 (Signaling Overhead 및 핑퐁 방지)
- $\alpha, \beta$: QoE와 핸드오버 패널티 간의 가중치 (Trade-off 조절 파라미터)

## 3. 최적화 목표
목적 함수는 에피소드(전체 비행 시간 $T$) 동안 누적되는 할인된 보상(Discounted Return)을 극대화하는 최적의 정책 $\pi^*$를 찾는 것입니다.
$$ \max_{\pi} \mathbb{E}_{\pi} \left[ \sum_{k=0}^{K} \gamma^k r_k \right] $$
(단, $\gamma \in [0,1]$는 할인율)
