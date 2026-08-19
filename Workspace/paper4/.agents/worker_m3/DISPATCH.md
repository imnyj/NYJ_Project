## 2026-08-18T03:37:23Z

당신은 Paper4 IEEE TWC 논문 작성의 제3장 시스템 모델 및 REMO-DQN 아키텍처(System Model & Proposed Architecture) 집필 전담 Worker입니다.

### Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 작업 지침:
1. 다음 파일들을 반드시 읽으십시오:
   - `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
   - `/home/imnyj/GEMINI.md`
   - `/home/imnyj/.agents/skills/academic-writing-style/SKILL.md`
   - `/home/imnyj/.agents/skills/anti-hallucination/SKILL.md`
   - `/home/imnyj/Workspace/paper4/.agents/explorer_survey_2/handoff.md`

2. 당신의 전담 출력 파일은 `/home/imnyj/Workspace/paper4/paper/03_system_model.md` 입니다. (이 파일만 작성하십시오)
3. 요구사항 (R3): IEEE Transactions on Wireless Communications (TWC) 최고 권위 저널 수준으로 완벽한 수학 공식과 함께 작성하십시오:
   - **3.1 네트워크 및 통신 시스템 모델 (Network & Communication System Model)**:
     - 시간 슬롯 모델 ($\Delta T_{\text{step}} = 100\text{ms}$), 통신 반경 ($R_{\text{comm}} = 300\text{m}$), 감지 반경 ($R_{\text{sense}} = 500\text{m}$).
     - 경로 손실 모델 ($d_0=1\text{m}, \text{PL}_0=47.86\text{dB}, \alpha=2.0$), 나카가미-$m$ 페이딩 ($m=3.0$), 잡음 전력 $N_0 = -94\text{dBm}$, SNR 임계치 $\gamma_{\text{th}} = 5.0\text{dB}$.
     - Nakagami-$m$ 수신 성공 확률 공식 $P_{\text{succ}}(d, P_{\text{tx}}) = \exp(-x)(1 + x + x^2/2)$ ($x = \frac{m \gamma_{\text{th, lin}}}{\gamma_{\text{lin}}}$).
     - CSMA/CA MAC 채널 경합 및 충돌 감쇠 계수 $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j)$, 최종 도달 확률 $P_{\text{rx}, ij} = P_{\text{succ}} \cdot f_{\text{collision}}$.
     - ETSI EN 302 637-2 CAM 이벤트 기반 패킷 생성 규칙 ($|\Delta \theta| \ge 4^\circ$, $\Delta d \ge 4\text{m}$, $|\Delta v| \ge 0.5\text{m/s}$, $\Delta t \ge 1.0\text{s}$).
   - **3.2 MDP 정식화 (Markov Decision Process Formulation)**:
     - 상태 공간 $s_t \in \mathbb{R}^5$: $[\text{CBR}_{\text{global}}, N_{\text{est}}/50, v/25, \Delta t_{\text{CAM}}/1.0, \text{CBR}_{\text{smoothed}}]$.
     - 행동 공간 $a_t \in \{0, \dots, 15\}$: $T_{\text{GenCAM}} \in \{0.1, 0.2, 0.5, 1.0\}\text{s} \times P_{\text{tx}} \in \{0, 10, 20, 30\}\text{dBm}$.
     - 다중 목표 보상 함수: $R_t = R_1 + R_2 + R_3 = +0.01 \cdot (N_{\text{est}}/50) - 1.0 \cdot |\text{CBR}_{\text{smoothed}} - 0.60| - 0.1 \cdot (\Delta t_{\text{CAM}}/1.0)$ (인식성 보상, 0.60 혼잡도 유지 및 요동 페널티, AoI 신선도 페널티).
   - **3.3 REMO-DQN 신경망 아키텍처 (REMO-DQN Architecture)**:
     - ResNet 특징 추출기: Linear(5, 128) + 2개의 Residual Blocks (각 블록 skip connection $h_{\text{out}} = \text{ReLU}(\text{Linear}(\text{ReLU}(\text{Linear}(x))) + x)$), 출력 $\phi(s_t) \in \mathbb{R}^{128}$.
     - MoE Gating Router: Linear(128, 64) $\to$ ReLU $\to$ Linear(64, 3) $\to$ Softmax, 게이팅 가중치 $g(s_t) = [g_1, g_2, g_3]^T$.
     - 3개의 Dueling Experts: 각 전문가 $k$마다 $V_k(s_t) \in \mathbb{R}^1$과 $A_k(s_t, a) \in \mathbb{R}^{16}$ 스트림 분리, $Q_k(s_t, a) = V_k(s_t) + (A_k(s_t, a) - \frac{1}{16}\sum A_k(s_t, a'))$.
     - 가중합 Q-값: $Q(s_t, a) = \sum_{k=1}^3 g_k(s_t) Q_k(s_t, a)$.
     - 부하 균등화 손실 (Load Balancing Loss): $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{TD}} + 0.01 \cdot \text{CV}^2(\bar{g})$.
4. 모든 수식은 LaTeX math 문법으로 작성하고 논리적 설명을 빠짐없이 기술하십시오.
5. 작성 완료 후 `/home/imnyj/Workspace/paper4/.agents/worker_m3/handoff.md`에 결과 요약을 남기고 orchestrator_1에게 완료 보고 메시지를 보내십시오.
