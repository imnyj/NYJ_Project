## 2026-08-18T03:37:23Z
당신은 Paper4 IEEE TWC 논문 작성의 제4장 본문 동적 시나리오 흐름(Main Body - Dynamic Scenario Flow) 집필 전담 Worker입니다.

### Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 작업 지침:
1. 다음 파일들을 반드시 읽으십시오:
   - `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
   - `/home/imnyj/GEMINI.md`
   - `/home/imnyj/.agents/skills/academic-writing-style/SKILL.md`
   - `/home/imnyj/.agents/skills/anti-hallucination/SKILL.md`
   - `/home/imnyj/Workspace/paper4/.agents/explorer_survey_2/handoff.md`
   - `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3/handoff.md`

2. 당신의 전담 출력 파일은 `/home/imnyj/Workspace/paper4/paper/04_scenario_flow.md` 입니다. (이 파일만 작성하십시오)
3. 요구사항 (R4): 독자가 V2X 시스템의 시계열적 동작 메커니즘을 완벽히 이해할 수 있도록 4단계 시나리오 파이프라인(4.1 ~ 4.4)을 상세히 기술하십시오:
   - **4.1 패킷 발생 및 이기종 트래픽 혼합 시나리오 (Packet Generation & Heterogeneous Traffic Mixture)**:
     - 3대 이기종 트래픽 모델링: 주기적 안전 비콘(ETSI CAM 280 Bytes, $1\sim10\text{Hz}$), 이벤트 기반 긴급 메시지(ETSI DENM, 최고우선순위 AC_VO), 비안전 백그라운드 인포테인먼트 트래픽(AC_BE/BK).
     - OBU MAC 계층 버퍼 유입 및 큐 적재 역학(Queue Dynamics).
   - **4.2 고밀도 환경에서의 채널 경합 및 MAC 충돌 메커니즘 (Channel Contention & MAC Collision in Dense Scenarios)**:
     - IEEE 802.11p/bd EDCA CSMA/CA의 Backoff 감쇄 및 CCA 동작.
     - 차량 밀도 증가에 따른 동시 송신 노드 급증과 충돌 확률 $P_{\text{collision}} = 1 - (1 - \tau)^{N-1}$ 폭증.
     - 은닉 노드(Hidden Terminal) 문제와 다중 경로 나카가미-$m$ 페이딩 중첩에 의한 패킷 유실, MAC 큐 지연 누적 및 버퍼 드랍, CBR 포화 메커니즘.
   - **4.3 DRL 기반 분산 혼잡 인지 및 상태/보상 정식화 (DRL-based Distributed Congestion Cognition)**:
     - 각 차량 OBU 에이전트의 주기적 관측 ($\text{CBR}_{\text{global}}, N_{\text{neighbors}}, v_{\text{norm}}, \Delta t_{\text{CAM}}, \text{CBR}_{\text{smoothed}}$).
     - 지수이동평균(EMA, $\lambda_s=0.5$)을 통한 노이즈 필터링 및 혼잡 페널티/AoI 신선도 다중 목표 보상 실시간 피드백 루프.
   - **4.4 MoE 기반 동적 라우팅 및 전송 제어 (MoE-based Dynamic Routing & Transmission Control)**:
     - ResNet 128차원 특징 추출 및 Softmax 게이팅 라우팅 $g(s_t) = [g_1, g_2, g_3]^T$.
     - 3개 전문가 서브넷의 트래픽 상황별 도메인 특화 역할:
       1. Expert 1 (Sparse Traffic, $\text{CBR} < 0.40$): 채널 여유 시 $T_{\text{GenCAM}} = 0.1\text{s}$ 극초단 주기 적용 $\to$ AoI 극소화.
       2. Expert 2 (Transitional Traffic, $0.40 \le \text{CBR} \le 0.60$): 통신량 증가 시 $T_{\text{GenCAM}} = 0.2\sim0.5\text{s}$ 미세 조절 $\to$ CBR 0.60 안정 유지.
       3. Expert 3 (Severe Congestion, $\text{CBR} > 0.60$): 극심한 정체 시 $T_{\text{GenCAM}} = 1.0\text{s}$ 및 송신 파워 절감 $\to$ MAC 충돌 차단 및 PDR 76.4% 방어.
     - Dueling Q-값 결합 및 $\arg\max Q(s, a)$ 기반 최적 제어 파라미터 ($T_{\text{GenCAM}}^*, P_{\text{tx}}^*$) OBU MAC 계층 즉시 주입.
4. 작성 완료 후 `/home/imnyj/Workspace/paper4/.agents/worker_m4/handoff.md`에 결과 요약을 남기고 orchestrator_1에게 완료 보고 메시지를 보내십시오.
