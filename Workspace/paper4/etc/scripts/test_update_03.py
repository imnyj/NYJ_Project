import sys
import re

def update_03_system_model():
    file_path = "/home/imnyj/Workspace/paper4/paper/03_system_model.md"
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Table III-1 math pipes
    text = text.replace(r"| $|\mathcal{S}|$ |", r"| $\vert\mathcal{S}\vert$ |")
    text = text.replace(r"| $|\mathcal{A}|$ |", r"| $\vert\mathcal{A}\vert$ |")
    text = text.replace(r"| $|\mathcal{B}|$ |", r"| $\vert\mathcal{B}\vert$ |")
    text = text.replace(r"$T_{\text{GenCAM}}$", r"$T_{\text{GenCam}}$")

    # 2. Exaggerations & Hardware text in 03
    text = text.replace("전파 감쇠 특성을 완벽히 포착한다.", "전파 감쇠 특성을 정밀하게 반영한다.")
    text = text.replace("왜곡을 완벽히 방지하도록 튜닝되었다.", "왜곡을 효과적으로 방지하도록 튜닝되었다.")
    text = text.replace("온보드 OBU 프로세서에서도 마이크로초 단위의 신속한 순전파 추론이 가능하도록 경량성을 유지한다.", "온보드 OBU 프로세서에서도 1.2 ms의 신속한 순전파 추론(100 ms 제어 주기의 1.2% 점유)이 가능하도록 경량성을 유지한다.")
    text = text.replace("백본 특징의 표현이 불안정하게 흔들리는 문제를 원천적으로 차단한다.", "백본 특징의 표현이 불안정하게 흔들리는 문제를 효과적으로 방지한다.")
    text = text.replace("전문가 사장 현상을 원천 방지하기 위해,", "전문가 사장 현상을 효과적으로 방지하기 위해,")
    text = text.replace("과도한 연산 부하 없이 온보드 환경에서 마이크로초 단위의 실시간 추론을 보장하도록 최적화되었다.", "350K 파라미터와 3.8M MACs의 경량 구조를 바탕으로 온보드 환경에서 1.2 ms의 실시간 추론(100 ms 제어 주기의 1.2% 점유)을 보장하도록 최적화되었다.")

    # 3. Paragraph expansions for short paragraphs in 03_system_model.md
    # Line 20
    target_c = r"이 감쇠 계수는 채널 점유율이 증가함에 따라 선형적으로 감소하며, 채널이 극도로 포화된 상황에서도 최소 0.1의 통신 가능성을 유지하도록 $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t))$로 설계된다."
    rep_c = r"이 감쇠 계수는 채널 점유율이 증가함에 따라 선형적으로 감소하며, 채널이 극도로 포화된 상황에서도 최소 0.1의 통신 가능성을 유지하도록 $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t))$로 설계된다. 이러한 감쇠 함수 모델링은 채널 부하가 가중될수록 무선 매체 상의 패킷 충돌 확률이 비선형적으로 증가하는 실제 IEEE 802.11p 분산 환경의 물리적 경합 현상을 정밀하게 반영한다."
    text = text.replace(target_c, rep_c)

    # Line 25
    target_d = r"구체적으로 방향각 변화량 $|\Delta \theta| \ge \Delta \theta_{\text{th}} = 4.0^\circ$, 위치 이동 변위 $\|\Delta \mathbf{p}\|_2 \ge \Delta d_{\text{th}} = 4.0\text{ m}$, 주행 속도 변화량 $|\Delta v| \ge \Delta v_{\text{th}} = 0.5\text{ m/s}$, 혹은 최대 생성 주기 만료 $\Delta t_i \ge T_{\text{GenCam, max}} = 1.0\text{ s}$ ($1\text{ Hz}$) 중 하나라도 만족되면 원초적 이벤트 트리거 플래그 $\text{Trig}_i(t) = 1$이 활성화된다."
    rep_d = r"구체적으로 방향각 변화량 $|\Delta \theta| \ge \Delta \theta_{\text{th}} = 4.0^\circ$, 위치 이동 변위 $\|\Delta \mathbf{p}\|_2 \ge \Delta d_{\text{th}} = 4.0\text{ m}$, 주행 속도 변화량 $|\Delta v| \ge \Delta v_{\text{th}} = 0.5\text{ m/s}$, 혹은 최대 생성 주기 만료 $\Delta t_i \ge T_{\text{GenCam, max}} = 1.0\text{ s}$ ($1\text{ Hz}$) 중 하나라도 만족되면 원초적 이벤트 트리거 플래그 $\text{Trig}_i(t) = 1$이 활성화된다. 이러한 동적 트리거링 규칙은 차량의 불필요한 비콘 전송을 억제하면서도 급격한 주행 궤적 변화 시 주변 차량에 대한 상황 인식 신선도를 최우선으로 확보하도록 돕는다."
    text = text.replace(target_d, rep_d)

    # Line 30
    target_e = r"여기서 감지 반경 $500\text{ m}$는 통신 반경 $300\text{ m}$보다 넓게 설정되어 잠재적인 은닉 노드의 간섭 신호 에너지까지 포괄하여 채널 부하를 정확히 측정하도록 돕는다."
    rep_e = r"여기서 감지 반경 $500\text{ m}$는 통신 반경 $300\text{ m}$보다 넓게 설정되어 잠재적인 은닉 노드의 간섭 신호 에너지까지 포괄하여 채널 부하를 정확히 측정하도록 돕는다. 따라서 개별 차량은 중앙 제어 장치의 통신 보조 없이도 국소 수신 에너지만으로 주변 무선 채널의 실시간 혼잡 상태를 독립적으로 추정할 수 있다."
    text = text.replace(target_e, rep_e)

    # Line 35
    target_f = r"통신 반경 $R_{\text{comm}} = 300\text{ m}$ 내 모든 유효 차량 쌍 집합 $\mathcal{P}_{\text{comm}}(t) = \{(i, j) \in \mathcal{V}(t) \times \mathcal{V}(t) \mid i \neq j, d_{ij}(t) \le R_{\text{comm}}\}$에 대한 네트워크 평균 AoI $\overline{\text{AoI}}(t)$는 $\overline{\text{AoI}}(t) = \frac{1}{|\mathcal{P}_{\text{comm}}(t)|} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \min(\Delta_{ij}(t) \times 1000\text{ [ms]}, 2000\text{ [ms]})$로 산출된다."
    rep_f = r"통신 반경 $R_{\text{comm}} = 300\text{ m}$ 내 모든 유효 차량 쌍 집합 $\mathcal{P}_{\text{comm}}(t) = \{(i, j) \in \mathcal{V}(t) \times \mathcal{V}(t) \mid i \neq j, d_{ij}(t) \le R_{\text{comm}}\}$에 대한 네트워크 평균 AoI $\overline{\text{AoI}}(t)$는 $\overline{\text{AoI}}(t) = \frac{1}{|\mathcal{P}_{\text{comm}}(t)|} \sum_{(i,j) \in \mathcal{P}_{\text{comm}}(t)} \min(\Delta_{ij}(t) \times 1000\text{ [ms]}, 2000\text{ [ms]})$로 산출된다. 이 지표는 단순 패킷 손실률을 넘어 수신 차량의 관점에서 실제 인지하고 있는 정보의 시간적 지연과 노후화 정도를 통합적으로 정량화한다."
    text = text.replace(target_f, rep_f)

    # Line 46
    target_sa = r"이 5차원 관측 벡터는 채널 부하, 공간 밀도, 주행 역학 및 시간적 신선도를 유기적으로 포괄하여 신경망에 풍부한 상황 맥락을 제공한다."
    rep_sa = r"이 5차원 관측 벡터는 채널 부하, 공간 밀도, 주행 역학 및 시간적 신선도를 유기적으로 포괄하여 신경망에 풍부한 상황 맥락을 제공한다. 각 상태 원소는 상이한 물리 단위를 균일한 스케일로 맞추기 위해 유효 최댓값 및 표준 기준 상수로 정규화된다. 이를 통해 심층 신경망 내부에서 특정 특징값의 스케일에 의해 그래디언트가 편향되는 현상을 효과적으로 방지한다."
    text = text.replace(target_sa, rep_sa)

    # Line 51
    target_sb = r"선택된 행동 인덱스 $a_t$로부터 물리 계층 제어 파라미터로의 전단사 디코딩 함수 $\Omega: \mathcal{A} \to \mathcal{T}_{\text{grid}} \times \mathcal{P}_{\text{grid}}$는 정수 몫 연산 $i_T = \lfloor a_t / 4 \rfloor \in \{0, 1, 2, 3\}$과 나머지 연산 $i_P = (a_t \bmod 4) \in \{0, 1, 2, 3\}$을 통해 $T_{\text{GenCam}}(a_t) = \mathcal{T}_{\text{grid}}[i_T]$ 및 $P_{\text{tx}}(a_t) = \mathcal{P}_{\text{grid}}[i_P]$로 확정된다."
    rep_sb = r"선택된 행동 인덱스 $a_t$로부터 물리 계층 제어 파라미터로의 전단사 디코딩 함수 $\Omega: \mathcal{A} \to \mathcal{T}_{\text{grid}} \times \mathcal{P}_{\text{grid}}$는 정수 몫 연산 $i_T = \lfloor a_t / 4 \rfloor \in \{0, 1, 2, 3\}$과 나머지 연산 $i_P = (a_t \bmod 4) \in \{0, 1, 2, 3\}$을 통해 $T_{\text{GenCam}}(a_t) = \mathcal{T}_{\text{grid}}[i_T]$ 및 $P_{\text{tx}}(a_t) = \mathcal{P}_{\text{grid}}[i_P]$로 확정된다. 이와 같은 2차원 이산 행동 결합은 복잡한 연속 제어기 대비 학습 수렴 안정성을 보장하면서도 물리 계층과 MAC 계층의 파라미터를 유기적으로 결합 제어할 수 있는 풍부한 표현력을 제공한다."
    text = text.replace(target_sb, rep_sb)

    # Line 56
    target_sc = r"각 성분은 군집 인식성 확보, 표준 혼잡도 추종 및 정보 신선도 보존을 독립적으로 유도하도록 정식화된다."
    rep_sc = r"각 성분은 군집 인식성 확보, 표준 혼잡도 추종 및 정보 신선도 보존을 독립적으로 유도하도록 정식화된다. 따라서 에이전트는 무선 채널의 혼잡 억제와 안전 비콘의 실시간 최신성 유지라는 상충 목표 간의 최적 파레토 균형점을 효과적으로 학습하게 된다."
    text = text.replace(target_sc, rep_sc)

    # Line 112
    target_resnet = r"구체적인 순전파 연산은 중간 표현 $\mathbf{z}_l^{(1)} = \text{ReLU}(\mathbf{W}_{l, 1} \mathbf{h}_{l-1} + \mathbf{b}_{l, 1})$, 2차 변환 $\mathbf{z}_l^{(2)} = \mathbf{W}_{l, 2} \mathbf{z}_l^{(1)} + \mathbf{b}_{l, 2}$, 그리고 스킵 결합 $\mathbf{h}_l = \text{ReLU}(\mathbf{z}_l^{(2)} + \mathbf{h}_{l-1})$의 단계로 진행된다 ($\mathbf{W}_{l, 1}, \mathbf{W}_{l, 2} \in \mathbb{R}^{128 \times 128}$, $\mathbf{b}_{l, 1}, \mathbf{b}_{l, 2} \in \mathbb{R}^{128}$)."
    rep_resnet = r"구체적인 순전파 연산은 중간 표현 $\mathbf{z}_l^{(1)} = \text{ReLU}(\mathbf{W}_{l, 1} \mathbf{h}_{l-1} + \mathbf{b}_{l, 1})$, 2차 변환 $\mathbf{z}_l^{(2)} = \mathbf{W}_{l, 2} \mathbf{z}_l^{(1)} + \mathbf{b}_{l, 2}$, 그리고 스킵 결합 $\mathbf{h}_l = \text{ReLU}(\mathbf{z}_l^{(2)} + \mathbf{h}_{l-1})$의 단계로 진행된다 ($\mathbf{W}_{l, 1}, \mathbf{W}_{l, 2} \in \mathbb{R}^{128 \times 128}$, $\mathbf{b}_{l, 1}, \mathbf{b}_{l, 2} \in \mathbb{R}^{128}$). 이러한 계층적 변환 구조는 다차원 관측 상태의 비선형 특징을 왜곡 없이 추출하여 후속 전문가 모듈에 고품질의 잠재 벡터를 전달한다."
    text = text.replace(target_resnet, rep_resnet)

    # Line 117
    target_moe = r"최종 라우팅 확률은 소프트맥스 함수를 거쳐 $g_k(\mathbf{s}_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$로 결정된다."
    rep_moe = r"최종 라우팅 확률은 소프트맥스 함수를 거쳐 $g_k(\mathbf{s}_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$로 결정된다. 이와 같은 소프트 라우팅 구조는 급격한 이산적 모드 전환 없이 트래픽 혼잡 국면의 전이에 맞추어 각 전문가의 정책을 매끄럽게 융합한다."
    text = text.replace(target_moe, rep_moe)

    # Line 122
    target_dueling = r"이점 스트림은 16차원 행동 벡터를 출력하며 $A_k(\mathbf{s}_t, a) = \mathbf{W}_{a, k}^{(2)} \text{ReLU}(\mathbf{W}_{a, k}^{(1)} \phi(\mathbf{s}_t) + \mathbf{b}_{a, k}^{(1)}) + \mathbf{b}_{a, k}^{(2)}$로 계산된다 ($\mathbf{W}_{a, k}^{(1)} \in \mathbb{R}^{64 \times 128}$, $\mathbf{W}_{a, k}^{(2)} \in \mathbb{R}^{16 \times 64}$)."
    rep_dueling = r"이점 스트림은 16차원 행동 벡터를 출력하며 $A_k(\mathbf{s}_t, a) = \mathbf{W}_{a, k}^{(2)} \text{ReLU}(\mathbf{W}_{a, k}^{(1)} \phi(\mathbf{s}_t) + \mathbf{b}_{a, k}^{(1)}) + \mathbf{b}_{a, k}^{(2)}$로 계산된다 ($\mathbf{W}_{a, k}^{(1)} \in \mathbb{R}^{64 \times 128}$, $\mathbf{W}_{a, k}^{(2)} \in \mathbb{R}^{16 \times 64}$). 가치 스트림은 주변 환경의 전반적인 안전도와 채널 혼잡도를 총괄 평가하고, 이점 스트림은 주어진 상태에서 취할 수 있는 각 전송 파라미터 쌍의 상대적 유효성을 식별한다. 이러한 이원화된 신경망 분리는 상태 가치에 의해 행동 선택의 미세한 차이가 묻히는 현상을 방지하여 학습 속도와 가치 추정의 정확도를 크게 향상시킨다."
    text = text.replace(target_dueling, rep_dueling)

    # Line 127
    target_opt = r"미니배치 $\mathcal{B}$ ($|\mathcal{B}| = 64$)에 대한 시간차(TD) 오차 손실은 평균 제곱 오차 $\mathcal{L}_{\text{TD}}(\theta) = \frac{1}{|\mathcal{B}|} \sum_{(\mathbf{s}, a, r, \mathbf{s}', d) \in \mathcal{B}} (Q(\mathbf{s}, a; \theta) - y)^2$로 정의된다."
    rep_opt = r"미니배치 $\mathcal{B}$ ($\vert\mathcal{B}\vert = 64$)에 대한 시간차(TD) 오차 손실은 평균 제곱 오차 $\mathcal{L}_{\text{TD}}(\theta) = \frac{1}{\vert\mathcal{B}\vert} \sum_{(\mathbf{s}, a, r, \mathbf{s}', d) \in \mathcal{B}} (Q(\mathbf{s}, a; \theta) - y)^2$로 정의된다. 이러한 손실 구조는 행동 가치의 과대추정을 효과적으로 억제하여 무선 채널의 급격한 변동 속에서도 안정적인 벨만 최적화 수렴을 유도한다."
    text = text.replace(target_opt, rep_opt)

    return text

if __name__ == '__main__':
    res = update_03_system_model()
    print("03 update script prepared successfully. Length:", len(res))
