# Paper4: ResNet-MoE-Dueling DQL-DCC Overall Plan

본 문서는 Paper4 (V2X DCC 혼잡 제어) 논문 작성을 위한 핵심 기여도, 지표, 서론 디자인, 필수 그래프 및 비교군(Baselines)을 총망라한 기획안입니다.

## 1. Core Contributions (핵심 기여도)
1. **V2X DCC를 위한 하이브리드 DRL 아키텍처 제안**: 복잡한 차량 상태(State)의 비선형적 특징을 추출하는 `ResNet` 모듈, 채널 혼잡도 수준에 따라 전문화된 판단을 내리는 `MoE(Mixture of Experts)` 라우터, 그리고 상태 가치와 행동 이점을 분리해 학습 안정성을 높인 `Dueling DQN`을 최초로 융합한 혼잡 제어 아키텍처를 제시함.
2. **엄격한 채널 안정성(Stability) 확보 및 요동(Oscillation) 현상 제거**: 기존 휴리스틱 기반 기법(AdaptDCC 등)이 유발하는 불법적인 전송 폭주(Burst)와 CBR 요동 현상을 원천 차단하여, 네트워크 규격을 엄격히 준수하는 평온한 채널 환경을 구축함.
3. **고밀도 환경에서의 PDR 극대화 및 가짜 AoI(Fake AoI) 한계 돌파**: 순간적인 전송 폭주로 인해 발생하는 MAC 계층의 대규모 패킷 충돌(Collision)을 방지함으로써, 극한의 차량 밀도에서도 76.4% 이상의 독보적인 패킷 수신율(PDR)을 달성하고 신뢰성 있는 정보 최신성(AoI)을 보장함.

## 2. Evaluation Metrics (기여도를 입증하기 위한 지표)
* **CBR (Channel Busy Ratio)**: 채널 점유율의 절대적 수치 및 시간에 따른 분산(Variance)/표준편차. (안정성과 요동 방지를 증명)
* **PDR (Packet Delivery Ratio)**: 전송된 패킷 대비 실제 수신 성공률. (충돌 방지 및 신뢰성 증명)
* **AoI (Age of Information)**: 패킷이 도달하기까지 걸린 시간과 정보의 최신성. (단순 지연시간이 아닌, 충돌로 인한 패킷 드랍 페널티를 포함한 진짜 정보 도달성 증명)
* **Reward Convergence**: DRL 에이전트의 에피소드별 누적 보상. (복잡한 하이브리드 모델의 학습 타당성 증명)

## 3. Introduction Design (서론 구조)
1. **Background**: 자율주행 및 V2X 안전 어플리케이션의 발전으로 인해 극도로 신뢰성 있는(High PDR, Low AoI) 통신 환경의 필요성 대두.
2. **Problem Statement**: 고밀도 환경에서 노드들이 동시에 메시지를 뿜어내면 MAC 충돌이 발생함. 이를 막기 위해 ETSI 표준 규격(ReactDCC, AdaptDCC)이 도입되었으나, 이들은 특정 상황에서 전송을 일시적으로 폭주(Burst)시켜 CBR이 심하게 요동(Oscillation)치고 MAC 충돌을 유발하는 치명적인 결함이 존재.
3. **Limitations of Simple ML**: 이를 해결하기 위해 지도학습(TinyMLP)이나 단순 DQN을 적용한 연구들이 있었으나, 시시각각 변하는 비선형적 교통 밀도와 채널 상태를 단순 모델 하나로 커버하기엔 적응력과 학습 안정성이 부족함.
4. **Proposed Solution**: 본 논문은 상태 추출(ResNet) -> 혼잡도별 분기(MoE) -> 가치 판단(Dueling)으로 이어지는 3단계 하이브리드 강화학습 구조를 제안하여, 복잡한 환경 변수를 완벽히 통제하고 안정적인 메시지 전송 주기를 산출함.
5. **Results Summary**: 시뮬레이션 결과, 제안 모델은 CBR을 안정적으로 통제하면서도 76% 이상의 압도적인 PDR을 달성하여 혼잡 제어의 딜레마를 완벽히 해결함.

## 4. Required Graphs (모델 정당성 입증용 그래프 목록)
1. **DQN Reward Convergence Curve**: (X축: Episodes, Y축: Total Reward) 복잡한 하이브리드 모델이 발산하지 않고 안정적으로 수렴함을 증명.
2. **Time-Series CBR Trace 궤적 차트**: (X축: Time, Y축: 순간 CBR) AdaptDCC의 톱니바퀴 같은 요동(Oscillation)과 본 모델의 일직선(Stability)을 직접적으로 대조하는 핵심 시각화 그래프.
3. **PDR vs. Vehicle Density**: (X축: 차량 밀도 10~100, Y축: PDR) 밀도가 높아질수록 타 모델들은 PDR이 추락하지만, 제안 모델은 방어해 내는 형태의 라인/바 그래프.
4. **AoI vs. Vehicle Density**: (X축: 차량 밀도, Y축: Mean AoI) 충돌로 인해 유실된 패킷까지 고려한 '진짜' 정보 최신성 우위 입증.
5. **CBR Cumulative Distribution Function (CDF)**: 전체 시뮬레이션 시간 중 채널이 혼잡 임계치를 넘지 않고 안전 영역에 머문 비율 증명.
6. **Ablation Study (구조 절제 실험)**: [Vanilla DQN] vs [DQN+MoE] vs [ResNet+MoE+Dueling] 의 성능(PDR)을 비교하여, 굳이 이렇게 복잡한 3단 구조를 붙인 이유(정당성)를 수학적으로 증명.

## 5. Comparison Baselines (비교 방안 목록)
1. **Fixed 10Hz (No DCC)**: 아무런 제어 없이 10Hz로 쏘는 기법 (충돌의 한계선, 최하위 벤치마크).
2. **ReactDCC**: 가장 기초적인 ETSI 반응형 표준 혼잡 제어.
3. **AdaptDCC**: 적응형 표준 혼잡 제어 (CBR 요동 및 전송 폭주 결함을 보여줄 핵심 '동네북' 비교군).
4. **TinyMLP (Supervised Learning)**: 이전 버전의 지도학습 모델 (휴리스틱의 결함을 그대로 답습하는 모방 학습의 한계 입증).
5. **Vanilla DQN**: 아키텍처 혁신이 없는 순정 강화학습 (본 논문의 하이브리드 아키텍처 대비 성능이 떨어짐을 보여줄 비교군).
6. **Proposed Model (H-DQL-DCC)**: 본 논문이 최종 제안하는 ResNet-MoE-Dueling DQL 구조.
