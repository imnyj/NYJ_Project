# Original User Request

## Initial Request — 2026-08-18T03:32:56Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

본 프로젝트는 V2X 혼잡 제어(DCC)를 위해 제안된 하이브리드 강화학습 모델(REMO-DQN)의 우수성을 14개 최신 알고리즘들과 비교 분석하는 논문(Paper4) 작성입니다. 타겟 저널은 **IEEE Transactions on Wireless Communications (TWC)** 입니다.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. 서론 (Introduction) 작성 가이드라인
IEEE TWC 수준의 깊이 있는 서술을 위해, 각 문단은 최소 5문장 이상으로 상세하고 짜임새 있게 작성할 것.
- **문단 1 (배경):** V2X 및 VANET의 중요성, 고밀도 환경에서의 신뢰성 있는 통신 채널 확보의 어려움, DCC의 필요성, 정보 연령(AoI) 지표의 중요성.
- **문단 2 (문제점 1):** 기존 ETSI 표준 DCC 기법(ReactDCC, AdaptDCC)의 고정 규칙으로 인한 CBR 요동(Oscillation) 및 폭주(Burst) 한계. 단순 RL 도입의 한계와 PDR 추락/Fake AoI 문제.
- **문단 3 (문제점 2):** 다양한 최신 DRL(PPO, SAC, MAPPO 등)의 등장이 있었으나 V2X 환경에서의 총체적/경험적 비교 부재. 복잡한 비선형적 교통/채널 상태를 인지하고 동적으로 라우팅할 수 있는 통합 아키텍처(MoE 등) 적용의 필요성.
- **문단 4 (제안 방안 및 기여도):** 14개 RL 알고리즘 종합 비교 및 새로운 하이브리드 아키텍처(ResNet+MoE+Dueling DQN) 제안. 
  - (기여도 1) 14개 알고리즘의 최적화 및 수렴성 종합 분석. 
  - (기여도 2) 채널 안정성 확보 및 고밀도 환경에서 PDR 방어, 최저 AoI 달성. 
  - (기여도 3) 샘플 효율성 및 하드웨어 추론 지연시간(Latency) 검증으로 실효성 입증.
- **문단 5 (글 구성 안내):** 2장 관련 연구, 3장 네트워크 모델, 4장 본문(시나리오), 5장 성능 평가, 6장 결론으로 이어지는 구성 안내.

### R2. 관련 연구 (Related Works) 설계
- 기존 연구 흐름(표준 DCC, 단일 DRL, 다중 에이전트 DRL) 외에, **2025~2026년 MoE+무선망/RL 결합 관련 최신 논문(예: "Mixture of Experts for Decentralized Generative AI and Reinforcement Learning in Wireless Networks", 2025)**을 반드시 포함할 것.
- 비교 테이블 포함: [Reference, Year, Optimization Target (AoI/PDR), RL Algorithm Used, Number of Baselines, MoE/Ensemble Applied (Y/N)]

### R3. 시스템 모델 (Network Model) 구조
- System Overview, MDP Formulation (상태, 행동, 다중 보상 함수 R1, R2), Proposed Architecture (REMO-DQN) 서술.

### R4. 본문 (Main Body - 시나리오 흐름)
- 4.1 Packet Generation & Traffic Mixed Scenario: 안전 비콘, 다운로드, 메시지 등 이기종 패킷 발생 모델.
- 4.2 Channel Contention & MAC Collision: 밀도 증가 시 CSMA/CA MAC 계층의 패킷 충돌 및 큐 병목 메커니즘.
- 4.3 DRL-based Congestion Recognition: OBU 에이전트의 주기적 채널 상태 관측 및 혼잡 페널티 산출.
- 4.4 Dynamic Routing & Transmission Control: 관측된 상황(여유 vs 혼잡)에 맞춰 MoE가 전문가 네트워크를 라우팅하여 최종 전송 주기(Rate)를 최적화하는 과정.

### R5. 성능 평가 (Performance Evaluation) 병합
기존 14개 모델 시뮬레이션 결과와 7대 핵심 지표를 모두 융합하여 서술.
- 5.1 실험 세팅: SUMO 환경, 14개 벤치마크 모델 설명.
- 5.2 (Metric 1) 학습 수렴도: 14개 모델의 Reward Convergence 비교 (DQN 기반 모델의 샘플 효율성 우위 증명).
- 5.3 (Metric 2) 채널 안정성 (Time-Series CBR Trace): 표준 기법의 요동(Oscillation)과 제안 방안의 안정성 대조.
- 5.4 (Metric 3 & 4) PDR & 에너지 효율: 차량 밀도 증가 시 PDR 방어 우수성 및 통신 에너지 소모량.
- 5.5 (Metric 5) AoI vs Density: PDR 극대화에 따른 Trade-off 기회비용 투명 분석.
- 5.6 (Metric 6) 하드웨어 실효성: MCU 환경에서의 추론 지연시간/메모리(FLOPs) 프로파일링.

## Acceptance Criteria
- [ ] 서론 각 문단이 5문장 이상으로 논리적으로 충분히 서술되었는가.
- [ ] 성능 평가 지표에 14개 알고리즘 비교와 CBR, PDR, AoI, Latency 지표가 모두 포함되었는가.
- [ ] 글의 언어가 한글(Korean)이며, TWC 저널 수준의 격식과 마크다운(수식 포함) 포맷을 만족하는가.
