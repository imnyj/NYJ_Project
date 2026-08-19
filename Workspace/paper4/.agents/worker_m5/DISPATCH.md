## 2026-08-18T03:37:23Z
당신은 Paper4 IEEE TWC 논문 작성의 제5장 성능 평가(Performance Evaluation) 집필 전담 Worker입니다.

### Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 작업 지침:
1. 다음 파일들을 반드시 읽으십시오:
   - `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
   - `/home/imnyj/GEMINI.md`
   - `/home/imnyj/.agents/skills/academic-writing-style/SKILL.md`
   - `/home/imnyj/.agents/skills/anti-hallucination/SKILL.md`
   - `/home/imnyj/Workspace/paper4/.agents/explorer_survey_1/handoff.md`
   - `/home/imnyj/Workspace/paper4/.agents/explorer_survey_1/analysis.md`
   - `/home/imnyj/Workspace/paper4/walkthrough.md`

2. 당신의 전담 출력 파일은 `/home/imnyj/Workspace/paper4/paper/05_performance_evaluation.md` 입니다. (이 파일만 작성하십시오)
3. 요구사항 (R5): 14개 이상의 벤치마크 알고리즘과 7대 핵심 평가 지표의 실측 수치 통계를 총망라하여 최고 권위 저널 TWC 수준으로 서술하십시오:
   - **5.1 시뮬레이션 환경 및 벤치마크 알고리즘 (Simulation Setup & Baselines)**:
     - SUMO 도심 격자망(Urban Grid), Nakagami-m ($m=3$) 페이딩, $R_{\text{comm}}=300\text{m}$, 밀도 10~100 veh/km, 속도 20~100 km/h.
     - 14개 RL/DRL 모델 (QLearning, SARSA, ActorCritic, VanillaDQN, DoubleDQN, DuelingDQN, DDPG, PPO, SAC, TD3, DecisionTransformer, MAPPO, MoEDQN, 제안 모델 REMO-DQN) + 7개 비-RL 모델 (Fixed 10Hz, ReactDCC, AdaptDCC, Heuristic, DecTree, StdMLP, TinyMLP). Optuna 하이퍼파라미터 최적화 세팅.
   - **5.2 (Metric 1) 학습 수렴도 및 샘플 효율성 (Reward Convergence & Sample Efficiency)**:
     - 14개 모델의 수렴 곡선 비교: REMO-DQN의 80 에피소드 내 고속 안정 수렴 (-904,570.64), DQN 기반 모델의 샘플 효율성 우위 증명.
   - **5.3 (Metric 2) 시계열 채널 안정성 (Time-Series CBR Trace & Stability)**:
     - 표준 AdaptDCC/ReactDCC의 극심한 CBR 요동(Oscillation, 표준편차 > 0.25) vs REMO-DQN의 일직선 안정성(평균 0.3442, 표준편차 0.1008), 혼잡 임계치(0.60) 위반율 0.0% 달성.
   - **5.4 (Metric 3 & 4) 패킷 전달률 (PDR) 및 통신 에너지 효율 (PDR vs Density & Energy Efficiency)**:
     - 밀도 10에서 100 veh/km 증가 시: 타 모델들 PDR 74~91%p 폭락 vs REMO-DQN 76.54%에서 73.41%로 단 3.13%p 하락에 그치는 압도적 방어력.
     - 송신 파워 적응에 따른 에너지 소모 절감 효과.
   - **5.5 (Metric 5) 정보 연령 (AoI vs Density) 및 가짜 AoI 한계 극복**:
     - 전체 평균 AoI: REMO-DQN 373.21 ms vs AdaptDCC 3,205.96 ms, ReactDCC 3,848.90 ms, Fixed 10Hz 4,682.51 ms.
     - 충돌 유실 페널티를 고려한 '진짜 AoI' vs 단순 송신 지연 '가짜 AoI' 투명한 학술적 분석.
   - **5.6 (Metric 6) 거리별 PDR (PDR vs Distance)**:
     - 0~300m 구간에서 300m 최장거리 도달 시 71.67% PDR 유지 (Vanilla DQN 66.74% 대비 +4.93%p 우위).
   - **5.7 (Metric 7) 하드웨어 실효성 및 OBU 복잡도 프로파일링 (Hardware Latency & Complexity)**:
     - 3.8M MACs, 350K 파라미터, 추론 지연시간 1.2 ms (ARM Cortex-M4 MCU 기준), 100ms V2X 주기의 1.2%만 점유하여 실시간 엣지 탑재 완벽 증명.
   - **5.8 절제 연구 및 MoE 도메인 특화성 (Ablation Study & MoE Domain Specialization)**:
     - Vanilla DQN vs DQN+MoE vs REMO-DQN 비교.
     - 차량 밀도에 따른 Expert 1(80%) $\to$ Expert 3(85%) 동적 가중치 전이 및 t-SNE 3대 군집화 시각화 분석.
4. 모든 수치와 비교 데이터는 표(Table)와 함께 마크다운 형식으로 상세히 기술하십시오.
5. 작성 완료 후 `/home/imnyj/Workspace/paper4/.agents/worker_m5/handoff.md`에 결과 요약을 남기고 orchestrator_1에게 완료 보고 메시지를 보내십시오.
