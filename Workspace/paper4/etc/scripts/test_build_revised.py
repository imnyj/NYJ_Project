import re

def build_revised_paper():
    with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
        text = f.read()

    # =========================================================================
    # 1. CRITICAL 1: Table III-1 Markdown Rendering (lines 454, 455, 462)
    # =========================================================================
    text = text.replace(r"| $|\mathcal{S}|$ |", r"| $\vert\mathcal{S}\vert$ |")
    text = text.replace(r"| $|\mathcal{A}|$ |", r"| $\vert\mathcal{A}\vert$ |")
    text = text.replace(r"| $|\mathcal{B}|$ |", r"| $\vert\mathcal{B}\vert$ |")
    text = text.replace(r"$T_{\text{GenCAM}}$", r"$T_{\text{GenCam}}$")

    # =========================================================================
    # 2. CRITICAL 2: Abstract Nakagami math typo
    # =========================================================================
    text = text.replace("Nakagami-$ 페이딩", "Nakagami-$m$ 페이딩")

    # =========================================================================
    # 3. MAJOR 1: Cross-Section Consistency (PDR & Hardware)
    # =========================================================================
    # Intro Line 65
    target_intro_pdr = r"120 veh/km의 극단적 고밀도 환경에서도 76.4% 이상의 패킷 전달률(PDR)을 유지함과 동시에 실제 MAC 충돌 페널티를 반영한 최저 정보 연령(전체 밀도 평균 AoI 373.2 ms)을 달성하여 Fake AoI 오류를 극복하였다."
    rep_intro_pdr = r"100 veh/km의 극단적 고밀도 환경에서도 73.41%의 높은 패킷 전달률(PDR)을 유지하며(10 veh/km 저밀도 76.54% 대비 하락폭 단 3.13%p 방어, 전체 평균 75.02%), 실제 MAC 충돌 페널티를 반영한 최저 정보 연령(전체 밀도 평균 AoI 373.21 ms)을 달성하여 Fake AoI 오류를 극복하였다."
    text = text.replace(target_intro_pdr, rep_intro_pdr)

    # Related Works Line 199 (Hardware numbers)
    target_rw_hw = r"최소한의 파라미터(10만 개 미만)와 마이크로초 단위의 초저지연 추론 성능을 달성하였다."
    rep_rw_hw = r"총 350K(35만 개) 파라미터와 3.8M MACs, 1.2 ms의 초저지연 온보드 추론 성능(100 ms 제어 주기의 1.2% 점유)을 달성하였다."
    text = text.replace(target_rw_hw, rep_rw_hw)

    # Related Works Line 203 (PDR numbers)
    target_rw_pdr = r"이와 같은 독보적 아키텍처 설계를 통해 제안하는 REMO-DQN은 고밀도 환경에서도 76.4% 이상의 패킷 전달률을 유지하며 차량 네트워크 혼잡 제어의 새로운 표준을 제시한다."
    rep_rw_pdr = r"이와 같은 아키텍처 설계를 통해 제안하는 REMO-DQN은 10 veh/km 저밀도 76.54%에서 100 veh/km 고밀도 73.41%를 유지(전체 평균 75.02%, 하락폭 단 3.13%p 방어)하며 차량 네트워크 분산 혼잡 제어의 우수한 신뢰성을 확보하였다."
    text = text.replace(target_rw_pdr, rep_rw_pdr)

    # Section 4 Line 501 (PDR text)
    target_s4_pdr = r"패킷 전달률(PDR)을 76.4% 이상으로 방어한다."
    rep_s4_pdr = r"패킷 전달률(PDR)을 100 veh/km 고밀도에서도 73.41%로 방어한다."
    text = text.replace(target_s4_pdr, rep_s4_pdr)

    # Hardware latency in Section 3 & System Model
    text = text.replace(
        "온보드 OBU 프로세서에서도 마이크로초 단위의 신속한 순전파 추론이 가능하도록 경량성을 유지한다.",
        "온보드 OBU 프로세서에서도 1.2 ms의 신속한 순전파 추론(100 ms 제어 주기의 1.2% 점유)이 가능하도록 경량성을 유지한다."
    )
    text = text.replace(
        "과도한 연산 부하 없이 온보드 환경에서 마이크로초 단위의 실시간 추론을 보장하도록 최적화되었다.",
        "350K 파라미터와 3.8M MACs의 경량 구조를 바탕으로 온보드 환경에서 1.2 ms의 실시간 추론(100 ms 제어 주기의 1.2% 점유)을 보장하도록 최적화되었다."
    )

    # =========================================================================
    # 4. MAJOR 2: Exaggerated adverbs and AI clichés
    # =========================================================================
    # Abstract
    text = text.replace("전파 감쇠 특성을 완벽히 포착", "전파 감쇠 특성을 정밀하게 반영")
    text = text.replace("결합하여 독보적인 분산 제어 성능을 달성하였다.", "결합하여 우수한 분산 제어 성능을 달성하였다.")

    # Section 2
    text = text.replace("독보적 차별성을 기술한다.", "차별화된 학술적 기여를 기술한다.")
    text = text.replace("치명적 망각을 MoE의 도메인 특화 라우팅이 원천 차단할 수 있음을", "치명적 망각을 MoE의 도메인 특화 라우팅이 효과적으로 방지할 수 있음을")
    text = text.replace("허위 지연시간(Fake AoI) 문제를 원천 차단하였다.", "허위 지연시간(Fake AoI) 왜곡을 효과적으로 방지하였다.")
    text = text.replace("채널 요동(Limit Cycle)을 완벽히 제거하였다.", "채널 요동(Limit Cycle)을 효과적으로 억제하였다.")

    # Section 3
    text = text.replace("전파 감쇠 특성을 완벽히 포착한다.", "전파 감쇠 특성을 정밀하게 반영한다.")
    text = text.replace("왜곡을 완벽히 방지하도록 튜닝되었다.", "왜곡을 효과적으로 방지하도록 튜닝되었다.")
    text = text.replace("백본 특징의 표현이 불안정하게 흔들리는 문제를 원천적으로 차단한다.", "백본 특징의 표현이 불안정하게 흔들리는 문제를 효과적으로 방지한다.")
    text = text.replace("전문가 사장 현상을 원천 방지하기 위해,", "전문가 사장 현상을 효과적으로 방지하기 위해,")

    # Section 5
    text = text.replace("최종 10 에피소드 평균 $-877,665.65$에 수렴하여 타 알고리즘 대비 최고의 보상 수렴 성능을 완벽히 달성하였으며,", "최종 10 에피소드 평균 $-877,665.65$에 수렴하여 타 알고리즘 대비 최고의 보상 수렴 성능을 성공적으로 달성하였으며,")
    text = text.replace("주기적 요동(Limit Cycle)을 완벽히 억제함을 실증하였다.", "주기적 요동(Limit Cycle)을 효과적으로 억제함을 실증하였다.")
    text = text.replace("초고밀도 정체 환경에서도 73.41%의 높은 PDR을 사수하여 성능 붕괴를 완벽하게 방어하였다.", "초고밀도 정체 환경에서도 73.41%의 높은 PDR을 사수하여 성능 붕괴를 안정적으로 방어하였다.")
    text = text.replace("전체 차량 밀도 구간에서 **평균 373.21 ms의 최저 AoI를 기록**하며 타의 추종을 불허하는 독보적인 우위를 입증하였다.", "전체 차량 밀도 구간에서 **평균 373.21 ms의 최저 AoI를 기록**하며 타 알고리즘 대비 탁월한 우위를 입증하였다.")
    text = text.replace("패킷 충돌을 물리적으로 원천 차단하는", "패킷 충돌을 물리적으로 효과적으로 차단하는")
    text = text.replace("실제 상용 OBU 임베디드 엣지 탑재 적합성을 완벽하게 증명하였다.", "실제 상용 OBU 임베디드 엣지 탑재 적합성을 성공적으로 입증하였다.")
    text = text.replace("필수불가결함을 수학적/실증적으로 완벽히 입증하였다.", "필수불가결함을 수학적/실증적으로 명확히 입증하였다.")
    text = text.replace("뚜렷한 기하학적 군집(Cluster)을 형성하며 완벽하게 분리되었다.", "뚜렷한 기하학적 군집(Cluster)을 형성하며 명확하게 분리되었다.")
    text = text.replace("노이즈 없이 완벽히 추상화하고 있음을 증명한다.", "노이즈 없이 정밀하게 추상화하고 있음을 증명한다.")
    text = text.replace("수학적 근거가 완벽히 확립되었다.", "수학적 근거가 성공적으로 확립되었다.")

    # Section 6 Conclusion
    text = text.replace("전문가 간 파라미터 간섭을 원천 차단하고 학습 안정성을 확립하였다.", "전문가 간 파라미터 간섭을 효과적으로 억제하고 학습 안정성을 확립하였다.")
    text = text.replace("핵심 소프트웨어 엔진으로 완벽히 통합될 수 있을 것으로 기대된다.", "핵심 소프트웨어 엔진으로 안정적으로 통합될 수 있을 것으로 기대된다.")

    # =========================================================================
    # 5. MINOR 1: Mathematical Notation Unification
    # =========================================================================
    # Romanize CBR, AoI, PDR in LaTeX math
    text = text.replace(r"$CBR$", r"$\text{CBR}$")
    text = text.replace(r"$CBR_{\text{target}} \approx 0.60$", r"$\text{CBR}_{\text{target}} \approx 0.60$")
    text = text.replace(r"$CBR_t$", r"$\text{CBR}_t$")
    text = text.replace(r"$CBR_{\text{smooth}}(k) = (1 - w) CBR_{\text{smooth}}(k-1) + w CBR(k)$", r"$\text{CBR}_{\text{smoothed}}(k) = (1 - w) \text{CBR}_{\text{smoothed}}(k-1) + w \text{CBR}(k)$")
    text = text.replace(r"$R_t = -\alpha |CBR_{\text{smooth}} - 0.60| - \beta \Delta t_{\text{CAM}}$", r"$R_t = -1.0 |\text{CBR}_{\text{smoothed}} - 0.60| - 0.10 \Delta t_{\text{CAM}} + 0.01 (N_{\text{est}}/50.0)$")
    text = text.replace(r"$CBR < 0.40$", r"$\text{CBR} < 0.40$")
    text = text.replace(r"$0.40 \le CBR \le 0.60$", r"$0.40 \le \text{CBR} \le 0.60$")
    text = text.replace(r"$CBR > 0.60$", r"$\text{CBR} > 0.60$")
    text = text.replace(r"$CBR_{\text{target}}$", r"$\text{CBR}_{\text{target}}$")
    text = text.replace(r"$CBR_{\text{target}}=0.60$", r"$\text{CBR}_{\text{target}}=0.60$")
    text = text.replace(r"$R_t = -|CBR_{\text{smoothed}} - 0.60| - 0.1 \times \Delta t$", r"$R_t = -1.0 |\text{CBR}_{\text{smoothed}} - 0.60| - 0.10 \Delta t + 0.01 (N_{\text{est}}/50.0)$")
    text = text.replace(r"$AoI$", r"$\text{AoI}$")
    text = text.replace(r"$PDR$", r"$\text{PDR}$")

    # State vector bolding
    text = text.replace(r"상태 관측 $s_t$, 행동 선택 $a_t$", r"상태 관측 $\mathbf{s}_t$, 행동 선택 $a_t$")
    text = text.replace(r"$\rho_t(\theta) = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{\text{old}}}(a_t|s_t)}$", r"$\rho_t(\theta) = \frac{\pi_\theta(a_t|\mathbf{s}_t)}{\pi_{\theta_{\text{old}}}(a_t|\mathbf{s}_t)}$")
    text = text.replace(r"상태 $s_t$, 행동 $a_t$", r"상태 $\mathbf{s}_t$, 행동 $a_t$")
    text = text.replace(r"연속 상태 벡터 $s_t = [\text{CBR}_{\text{global}}(t), N_{\text{norm}}(t), v_{\text{norm}}(t), \Delta t_{\text{CAM, norm}}(t), \text{CBR}_{\text{smoothed}}(t)]^T \in \mathbb{R}^5$", r"연속 상태 벡터 $\mathbf{s}_t = [\text{CBR}_{\text{global}}(t), N_{\text{norm}}(t), v_{\text{norm}}(t), \Delta t_{\text{CAM, norm}}(t), \text{CBR}_{\text{smoothed}}(t)]^T \in \mathbb{R}^5$")
    text = text.replace(r"$\mathcal{R}(s_t, a_t)$", r"$\mathcal{R}(\mathbf{s}_t, a_t)$")
    text = text.replace(r"$\mathcal{R}(s_t, a_t) = R_1(s_t) + R_2(s_t) + R_3(s_t)$", r"$\mathcal{R}(\mathbf{s}_t, a_t) = R_1(\mathbf{s}_t) + R_2(\mathbf{s}_t) + R_3(\mathbf{s}_t)$")
    text = text.replace(r"$R_1(s_t) = +0.01 \cdot (N_{\text{est}} / 50.0)$", r"$R_1(\mathbf{s}_t) = +0.01 \cdot (N_{\text{est}} / 50.0)$")
    text = text.replace(r"$R_2(s_t) = -1.0 \cdot |\text{CBR}_{\text{smoothed}} - 0.60|$", r"$R_2(\mathbf{s}_t) = -1.0 \cdot |\text{CBR}_{\text{smoothed}} - 0.60|$")
    text = text.replace(r"$R_3(s_t) = -0.10 \cdot (\Delta t_{\text{CAM}} / 1.0)$", r"$R_3(\mathbf{s}_t) = -0.10 \cdot (\Delta t_{\text{CAM}} / 1.0)$")
    text = text.replace(r"5차원 입력 상태 $s_t$는", r"5차원 입력 상태 $\mathbf{s}_t$는")
    text = text.replace(r"$\phi(s_t) \in \mathbb{R}^{128}$", r"$\phi(\mathbf{s}_t) \in \mathbb{R}^{128}$")
    text = text.replace(r"$\text{sg}[\phi(s_t)]$", r"$\text{sg}[\phi(\mathbf{s}_t)]$")
    text = text.replace(r"$G(s_t) = [g_1(s_t), g_2(s_t), g_3(s_t)]^T$", r"$G(\mathbf{s}_t) = [g_1(\mathbf{s}_t), g_2(\mathbf{s}_t), g_3(\mathbf{s}_t)]^T$")
    text = text.replace(r"$g_k(s_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$", r"$g_k(\mathbf{s}_t) = \exp(l_{g, k}) / \sum_{j=1}^3 \exp(l_{g, j})$")
    text = text.replace(r"$l_g = W_{g, 2} \text{ReLU}(W_{g, 1} \text{sg}[\phi(s_t)] + b_{g, 1}) + b_{g, 2}$", r"$l_g = \mathbf{W}_{g, 2} \text{ReLU}(\mathbf{W}_{g, 1} \text{sg}[\phi(\mathbf{s}_t)] + \mathbf{b}_{g, 1}) + \mathbf{b}_{g, 2}$")
    text = text.replace(r"$V_k(s_t)$", r"$V_k(\mathbf{s}_t)$")
    text = text.replace(r"$A_k(s_t, a)$", r"$A_k(\mathbf{s}_t, a)$")
    text = text.replace(r"$Q_k(s_t, a) = V_k(s_t) + (A_k(s_t, a) - \frac{1}{16}\sum_{a'=0}^{15} A_k(s_t, a'))$", r"$Q_k(\mathbf{s}_t, a) = V_k(\mathbf{s}_t) + (A_k(\mathbf{s}_t, a) - \frac{1}{16}\sum_{a'=0}^{15} A_k(\mathbf{s}_t, a'))$")
    text = text.replace(r"$Q(s_t, a)$", r"$Q(\mathbf{s}_t, a)$")
    text = text.replace(r"$g_k(s_t)$", r"$g_k(\mathbf{s}_t)$")
    text = text.replace(r"$Q(s_t, a) = \sum_{k=1}^3 g_k(s_t) \cdot Q_k(s_t, a)$", r"$Q(\mathbf{s}_t, a) = \sum_{k=1}^3 g_k(\mathbf{s}_t) \cdot Q_k(\mathbf{s}_t, a)$")
    text = text.replace(r"$a_t^* = \arg\max_{a \in \mathcal{A}} Q(s_t, a)$", r"$a_t^* = \arg\max_{a \in \mathcal{A}} Q(\mathbf{s}_t, a)$")

    return text

if __name__ == '__main__':
    res = build_revised_paper()
    print("Paper draft base revision script complete. Output length:", len(res))
