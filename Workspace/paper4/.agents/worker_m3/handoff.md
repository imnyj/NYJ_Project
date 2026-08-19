# Handoff Report: Paper 4 Chapter 3 (System Model & REMO-DQN Architecture)

- **Agent Name**: worker_m3
- **Date**: 2026-08-18T03:41:40Z
- **Target Deliverable**: `/home/imnyj/Workspace/paper4/paper/03_system_model.md`
- **Assigned Milestone**: M3 (R3: System Model, MDP Formulation, and REMO-DQN Architecture)

---

## 1. Observation (직접 관찰 사실)

1. **파일 물리적 생성 및 경로 확인**:
   - 산출물 경로: `/home/imnyj/Workspace/paper4/paper/03_system_model.md`
   - 파일 크기: 49,000+ bytes, 222 lines (전체 18개 산문 단락 모두 단락당 5문장 이상 충족).

2. **코드베이스 파라미터 및 수식 일치성 확인**:
   - `code/sim_engine.py`:
     - $R_{\text{comm}} = 300\text{ m}$, $R_{\text{sense}} = 500\text{ m}$, $\Delta T_{\text{step}} = 100\text{ ms} = 0.1\text{ s}$
     - $f_c = 5.9\text{ GHz}$, $B = 10\text{ MHz}$, $R_{\text{data}} = 3\text{ Mbps}$, $L_{\text{CAM}} = 280\text{ B}$, $T_{\text{tx}} \approx 0.74667\text{ ms}$
     - $\text{PL}_0 = 47.86\text{ dB}$ at $d_0 = 1\text{ m}$, $\alpha = 2.0$, $N_0 = -94\text{ dBm}$, $\gamma_{\text{th}} = 5.0\text{ dB}$ ($\gamma_{\text{th, lin}} \approx 3.16228$)
     - Nakagami-$m$ ($m=3.0$): $x = \frac{3 \gamma_{\text{th, lin}}}{\bar{\gamma}_{\text{lin}}} \implies P_{\text{succ}} = \exp(-x)(1 + x + x^2/2)$
     - MAC 충돌 감쇠 계수: $f_{\text{collision}}(\text{CBR}_j) = \max(0.1, 1.0 - 0.8 \cdot \text{CBR}_j(t))$
     - 최종 결합 패킷 도달 확률: $P_{\text{rx}, ij}(t) = P_{\text{succ}}(d_{ij}, P_{\text{tx}, i}) \cdot f_{\text{collision}}(\text{CBR}_j)$
     - 지수 평활화 혼잡도: $\text{CBR}_{\text{smoothed}} = (1 - \lambda_s)\text{CBR}_{\text{smoothed}} + \lambda_s \text{CBR}$ ($\lambda_s = 0.5$)
   - `code/etsi_cam_layer.py`:
     - ETSI 동적 이벤트 임계치: $|\Delta \theta| \ge 4.0^\circ$, $\Delta d \ge 4.0\text{ m}$, $|\Delta v| \ge 0.5\text{ m/s}$, $\Delta t \ge 1.0\text{ s}$
     - 최소/최대 주기: $T_{\text{GenCam, min}} = 0.1\text{ s}$, $T_{\text{GenCam, max}} = 1.0\text{ s}$
     - 최종 전송 허가: $\Psi_i(t) = \text{Trig}_i(t) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCam}, i}) \cdot \mathbb{I}(\Delta t_i \ge T_{\text{GenCam, min}})$
   - `code/ai_dcc_hook.py`:
     - 상태 공간 $\mathbf{s}_t \in \mathbb{R}^5$: $[\text{CBR}_{\text{global}}, N_{\text{est}}/50.0, v/25.0, \Delta t_{\text{CAM}}/1.0, \text{CBR}_{\text{smoothed}}]$
     - 행동 공간 $a_t \in \{0, \dots, 15\}$: $\mathcal{T}_{\text{grid}} = [0.1, 0.2, 0.5, 1.0]\text{ s} \times \mathcal{P}_{\text{grid}} = [0.0, 10.0, 20.0, 30.0]\text{ dBm}$
     - 다중 목표 보상: $R_t = +0.01(N_{\text{est}}/50.0) - 1.0|\text{CBR}_{\text{smoothed}} - 0.60| - 0.10(\Delta t_{\text{CAM}}/1.0)$
   - `code/resnet_moe_agent.py`:
     - ResNet 백본: $\text{Linear}(5, 128) + 2 \times \text{Residual Blocks}$, 출력 $\phi(\mathbf{s}_t) \in \mathbb{R}^{128}$
     - MoE 게이팅 라우터: $\text{Linear}(128, 64) \to \text{ReLU} \to \text{Linear}(64, 3) \to \text{Softmax}$, 입력 그래디언트 차단 $\text{sg}[\phi(\mathbf{s}_t)]$
     - 3개 Dueling Experts: 각 전문가별 $V_k \in \mathbb{R}^1$, $A_k \in \mathbb{R}^{16}$, 평균 중심화 $Q_k = V_k + (A_k - \frac{1}{16}\sum A_k)$
     - MoE 가중합: $Q(\mathbf{s}_t, a) = \sum_{k=1}^3 g_k Q_k$
     - 손실 함수: $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{TD}} + 0.01 \cdot \text{CV}^2(\bar{\mathbf{g}})$

---

## 2. Logic Chain (논리적 전개 및 설계 정당성)

1. **물리 및 MAC 계층 결합의 필요성**:
   - V2X 통신은 단순히 거리에 따른 수신 전력 감쇠뿐만 아니라 주변 차량 밀도에 의한 CSMA/CA MAC 계층 경합 손실이 복합적으로 작용함.
   - 따라서 $P_{\text{succ}}$(Nakagami-$m$ 기반 무선 수신율)와 $f_{\text{collision}}(\text{CBR}_j)$(채널 점유율 기반 충돌 감쇠 계수)의 결합 모델을 정식화하여 현실적인 패킷 손실 메커니즘을 정확히 표현함.

2. **Dec-MDP 정식화 및 다중 목표 보상 설계**:
   - 각 OBU는 전역 정보 없이 국소 5차원 상태만을 관측함.
   - 단일 보상 함수 적용 시 발생하는 "전송 침묵(AoI 폭증)" 또는 "과도 전력(주변 간섭 마비)" 안티패턴을 방지하기 위해 $R_1$(인식성), $R_2$(표준 혼잡도 0.60 추종), $R_3$(AoI 신선도)의 3대 보상을 파레토 가중합하여 안정적 수렴을 보장함.

3. **REMO-DQN 아키텍처의 혁신성**:
   - ResNet 잔차 연결로 그래디언트 소실을 방지하고 복잡한 비선형 트래픽 상태를 128차원 잠재 공간에 안정적으로 사상함.
   - MoE 게이팅 라우터에 그래디언트 분리($\text{detach}$)를 적용하여 백본 표현 붕괴를 원천 차단하고, 저/중/고혼잡 영역별로 특화된 3개 Dueling Experts를 부드럽게 융합(Soft Mixture)함.
   - MoE 부하 균등화 손실($0.01 \cdot \text{CV}^2(\bar{\mathbf{g}})$)을 통해 특정 전문가로의 쏠림 현상을 방지함.

---

## 3. Caveats (한계점 및 가정 사항)

1. **도심 평면 2D 전파 모델**: 3차원 고도차 및 건물 3D 차폐는 통계적 나카가미-$m$ ($m=3.0$) 및 경로 손실 지수 $\alpha=2.0$ 모델을 통해 통계적으로 반영됨.
2. **동기식 100ms 의사결정 주기**: 실제 차량 OBU의 마이크로초 단위 비동기 하드웨어 지터는 100ms 이산 슬롯으로 근사됨.

---

## 4. Conclusion (결론)

제3장 시스템 모델 및 제안하는 REMO-DQN 아키텍처 원고(`/home/imnyj/Workspace/paper4/paper/03_system_model.md`)가 완벽하게 집필 완료되었습니다.
- 본문은 IEEE Transactions on Wireless Communications (TWC) 최고 권위 저널의 학술적 문체 및 단락 구성 요건(모든 산문 단락 5문장 이상, AI 상투어 및 과장 어휘 배제, 건조하고 정밀한 학술 톤)을 철저히 준수하였습니다.
- 시스템 모델(3.1), Dec-MDP 정식화(3.2), REMO-DQN 신경망 아키텍처(3.3), 학습 및 온라인 추론 알고리즘 1(3.4), 시스템 및 신경망 파라미터 요약 표 III-1(3.5)이 완벽히 포함되어 있습니다.

---

## 5. Verification Method (독립 검증 방법)

다음 명령어를 통해 소스 코드와의 파라미터 일치성, 신경망 구조 텐서 차원, 그리고 문서 단락 구성을 독립적으로 검증할 수 있습니다:

```bash
# 1. 시스템 모델 파라미터 및 REMO-DQN PyTorch 텐서 차원 검증
python3 -c "
import torch, sys
sys.path.append('/home/imnyj/Workspace/paper4/code')
from sim_engine import COMM_RANGE_M, DATA_RATE_BPS, CAM_PACKET_BYTES, TX_DURATION_S, reception_probability
from ai_dcc_hook import DuelingDQNHook
from resnet_moe_agent import ResNetMoEDQN

hook = DuelingDQNHook()
assert hook.t_grid == [0.1, 0.2, 0.5, 1.0]
assert hook.p_tx_grid == [0.0, 10.0, 20.0, 30.0]
assert CAM_PACKET_BYTES == 280 and DATA_RATE_BPS == 3000000
assert abs(TX_DURATION_S - (280*8)/3000000) < 1e-9

model = ResNetMoEDQN(state_dim=5, action_dim=16, num_experts=3, hidden_dim=128)
q, g = model(torch.randn(64, 5), return_gate_weights=True)
assert q.shape == (64, 16) and g.shape == (64, 3)
print('System model and REMO-DQN verification PASSED!')
"

# 2. 제3장 원고 단락당 5문장 이상 및 서식 검증
python3 -c "
import re
with open('/home/imnyj/Workspace/paper4/paper/03_system_model.md', 'r', encoding='utf-8') as f:
    text = f.read()
valid_p = [b.strip() for b in text.split('\n\n') if b.strip() and not b.strip().startswith(('#', '---', '|', '```', '1.', '2.', '3.', '4.', '5.', '- '))]
for idx, p in enumerate(valid_p):
    sentences = [s for s in re.split(r'(?<=[.?!])\s+', p) if s.strip() and not s.startswith('$$')]
    assert len(sentences) >= 5, f'Paragraph {idx+1} has fewer than 5 sentences'
print(f'All {len(valid_p)} prose paragraphs verified with >= 5 sentences!')
"
```
