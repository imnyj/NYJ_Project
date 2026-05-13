# Idea Memory

## [2026-05-08] Phase 2 — 1차 브레인스토밍 (Brainstorm Round 1)

**세션 컨텍스트**:
- 타겟 저널: IEEE Internet of Things Journal (IoT-J)
- 도메인: 차량 네트워크 Layer-2 (MAC/링크 계층) + 경량 AI
- 시뮬레이터: libsumo + SumoNetSim
- 제약: 경량 모델, 3개월 이내 시뮬레이션 완료
- 기반 레퍼런스: 47편 (AI-MAC 직접 경쟁 10편 포함)

---

# Idea Brainstorm Report (1차)

## 0. 컨텍스트 요약

- **타겟 저널**: IEEE Internet of Things Journal (IoT-J) — IoT 응용성·확장성·시스템 통합·실측/시뮬레이션 검증을 핵심 심사 기준으로 삼음.
- **도메인**: 차량 네트워크 Layer-2(MAC/링크 계층) + 경량 AI; 사용자는 프로토콜 연구자로서 MAC 메커니즘 자체를 재설계하는 방향이 강점.
- **자원 제약**: libsumo + SumoNetSim 시뮬레이션, 경량 모델(tinyML·표 형 RL·경량 GNN 등), 3개월 이내 완료 목표; 47편 검증 레퍼런스(AI-MAC 직접 경쟁 10편 포함) 활용.

---

## 1. 후보 아이디어 5개

---

### 후보 #1: AI-Adaptive EDCA — Q-Table 기반 동적 AIFS/CW 조정으로 V2X 우선순위 보장

- **핵심 가설(Hypothesis)**: 차량 밀도와 메시지 긴급도(Safety/Non-Safety)를 입력으로 하는 표 형(tabular) Q-learning이 EDCA의 AIFS와 Contention Window(CW) 파라미터를 실시간으로 조정하면, 고정 파라미터 EDCA 대비 Safety 메시지 PDR과 지연을 동시에 개선할 수 있다.
- **MAC 메커니즘 변경점**: IEEE 802.11p/802.11bd EDCA의 AC_VO·AC_VI 접근 카테고리에서 AIFS[AC]와 CWmin[AC]/CWmax[AC]를 에피소드별로 동적 갱신. 기존 고정 테이블 값 대신 Q-테이블 출력으로 대체.
- **AI 구성 요소**:
  - 모델: 표 형 Q-learning (상태 수 ≤ 256 → 메모리 수 KB 수준)
  - 입력: (채널 부하 레벨[0-3], 큐 점유율[0-3], 메시지 타입[Safety/Non-Safety]) = 32개 상태
  - 출력: (AIFS 오프셋 Δ ∈ {0,1,2,3}, CW 스케일 ∈ {small, mid, large}) = 12개 액션
  - 경량화 전략: ε-greedy, 에피소드 당 단일 룩업 → 추론 비용 O(1), 학습 수렴 < 500 스텝
- **시뮬레이션 구현**:
  - libsumo로 시내 격자 시나리오(500m×500m) 생성 → 차량 밀도/속도 추출
  - SumoNetSim 네트워크 계층에 EDCA 파라미터 갱신 API 추가 (파이썬 hook)
  - 에이전트 1개/차량, 중앙화 없이 분산 실행
  - 추가 시뮬레이터 불필요
- **베이스라인 (3+)**:
  1. **IEEE 802.11p 고정 EDCA** (표준 파라미터) — SumoNetSim 기본 구현
  2. **Wu2025** (RL 기반 긴급 메시지 브로드캐스트) — 동일 SumoNetSim에서 백오프 추정 모듈 재현
  3. **Iqbal2025** (Lightweight RL 스펙트럼 관리) — 동일 Q-learning 구조, 주파수 선택 대신 EDCA 파라미터만 변경하여 비교
  4. **IEEE 802.11bd 고정 EDCA** — 표준 파라미터 (차세대 기준선)
- **평가 메트릭**: PDR (Safety / Non-Safety 분리), E2E 지연(ms), 채널 점유율(CBR), 공정성 지수(Jain), 처리량(Mbps)
- **예상 핵심 기여 (Contribution)**:
  - EDCA 파라미터 공간을 상태-액션 테이블로 정형화하여 표 형 RL로 풀 수 있음을 최초 증명
  - 차량 밀도 변화에 실시간 적응하는 경량(< 1 KB 모델) EDCA 파라미터 제어기 설계
  - IoT-J 대상 V2X Safety 메시지 보장 시나리오에서 공정 비교 프레임워크 제시
- **IoT-J 적합성 점수**: ★★★★☆ (4/5) — EDCA는 표준 V2X MAC 핵심이고 IoT 서비스 품질 보장과 직결; 표 형 RL의 경량성은 IoT 엣지 배포 적합성을 높임.
- **노벨티 위험**: Wu2025(RL + 긴급 브로드캐스트), Iqbal2025(경량 RL 스펙트럼 관리) — AIFS/CW 동적 조정 자체는 기존 논문들이 주로 고정 Q-값 기반이거나 DQN 사용; 표 형 Q + EDCA 4파라미터 동시 조정은 차별화 가능하나 세심한 noveltyx-check 필요.

---

### 후보 #2: Context-Aware Beacon Rate Control — TinyMLP 기반 동적 비콘 주파수·전력 공동 제어

- **핵심 가설(Hypothesis)**: 차량의 이동 컨텍스트(속도, 가속도, 인접 차량 수)를 입력으로 하는 초경량 MLP(≤ 2 hidden layers, ≤ 64 뉴런)가 비콘 전송 주파수(1–10 Hz)와 전력(-10 ~ +20 dBm)을 공동 최적화하면, ETSI ITS-G5 표준 대비 채널 부하를 줄이면서도 인식 품질(AoI 기반)을 유지할 수 있다.
- **MAC 메커니즘 변경점**: ETSI EN 302 637-2(CAM) 비콘 생성 트리거 조건 재설계 — 기존 고정 1/10Hz DCC(Decentralized Congestion Control) 대신 TinyMLP 출력으로 전송 간격·전력 설정.
- **AI 구성 요소**:
  - 모델: TinyMLP (Input: 5 features, 2×32 ReLU, Output: 2 — freq index, power level)
  - 입력: (속도, 가속도, 이웃 차량 수 추정치, 현재 CBR, AoI 누적 값)
  - 출력: (비콘 주기 인덱스 ∈ {1,2,5,10Hz}, 전력 레벨 ∈ {low, mid, high})
  - 경량화: 오프라인 지도학습(behavior cloning from optimal DCC table) → 추론 비용 ~1ms, 파라미터 수 < 2000
- **시뮬레이션 구현**:
  - libsumo: 교차로 시나리오(10-way intersection) + 고속도로 시나리오 생성
  - SumoNetSim: ETSI DCC 모듈 수정 → TinyMLP 추론 훅 삽입
  - 오프라인 학습 데이터: libsumo 시뮬레이션 결과로 최적 DCC 테이블 생성 → behavior cloning
- **베이스라인 (3+)**:
  1. **ETSI DCC 고정 알고리즘** (Reactive/Adaptive) — SumoNetSim 기본
  2. **Bhattacharyya2024** (Variable Beacon MAC) — 동일 시뮬레이터에서 비콘 간격만 조정하는 비교
  3. **Zila2026** (TinyML MAC for IIoT) — 동일 경량화 접근, 차량 도메인으로 전환 비교
  4. **고정 10Hz 비콘** (최대 CBR) — 채널 포화 기준선
- **평가 메트릭**: CBR(%), AoI(ms), PDR(%), 에너지 소비(Joules/km), 인식 범위(m)
- **예상 핵심 기여 (Contribution)**:
  - TinyMLP를 V2X 비콘 전송 제어기에 직접 내장하는 첫 번째 경량 AI-DCC 설계
  - AoI와 CBR 간 트레이드오프를 동시에 최적화하는 통합 제어 프레임워크
  - IoT 엣지 MCU(ARM Cortex-M)에 배포 가능한 모델 크기·추론 속도 실증
- **IoT-J 적합성 점수**: ★★★★★ (5/5) — AoI, IoT 배포 가능성, V2X 표준 연동 모두 IoT-J 핵심 키워드와 정확히 일치.
- **노벨티 위험**: Bhattacharyya2024(Variable Beacon MAC), Zila2026(TinyML MAC) — AoI 기반 비콘 제어 + TinyMLP 조합은 직접 선행 연구 없음; DCC 대체 AI 논문들은 DRL 위주로 경량 MLP 접근 차별화 가능. Ni2024(Hyperdimensional Learning MAC)는 간접 경쟁.

---

### 후보 #3: Federated Lightweight Q-Learning for Distributed TDMA Slot Negotiation in V2X Platoons

- **핵심 가설(Hypothesis)**: 플래툰(군집 차량) 내 각 차량이 표 형 Q-learning으로 TDMA 슬롯을 독립 협상하고, 리더 차량에서 경량 연합(federated) Q-테이블 평균화를 수행하면, 중앙 스케줄링 없이도 슬롯 충돌률을 최소화할 수 있다.
- **MAC 메커니즘 변경점**: 기존 TDMA 고정 슬롯 배정 → 분산 Q-learning 기반 슬롯 선택 + 플래툰 리더에서 연합 평균화(FedAvg 변형, 테이블 크기 ≤ 64×8). 슬롯 충돌 감지 시 벌점 보상.
- **AI 구성 요소**:
  - 모델: 분산 표 형 Q-learning (슬롯 인덱스 × 우선순위 레벨 = 64 × 8 테이블/차량)
  - 입력: (현재 슬롯 상태, 이웃 비콘 수신 이력, 우선순위 레벨)
  - 출력: 다음 전송 슬롯 선택
  - 연합 집계: FedAvg per-platoon, 100 에피소드마다 리더 전파 → 통신 오버헤드 < 512 bytes/update
  - 경량화: 테이블 사이즈 고정, no neural network
- **시뮬레이션 구현**:
  - libsumo: 고속도로 플래툰 시나리오 (5-10대 차량/플래툰, 2-5개 플래툰)
  - SumoNetSim: TDMA 슬롯 프레임 구현 + 연합 집계 모듈 추가 (별도 시뮬레이터 불필요)
  - 필요 시 platoon_mac_sim.py 경량 확장 모듈 libsumo 위에서 작성
- **베이스라인 (3+)**:
  1. **고정 TDMA** (라운드로빈) — SumoNetSim 직접 구현
  2. **CSMA/CA (IEEE 802.11p)** — 기존 SumoNetSim 지원
  3. **Liu2024** (Federated Multi-Agent DRL for NR-V2X 자원 할당) — DRL vs Q-table 비교
  4. **Narayanasamy2024** (Cascaded MARL resource allocation) — 플래툰 전용 DRL 비교
- **평가 메트릭**: 슬롯 충돌률(%), PDR(%), 슬롯 수렴 속도(에피소드), E2E 지연(ms), 확장성(차량 수 vs. 성능)
- **예상 핵심 기여 (Contribution)**:
  - TDMA 슬롯 협상에 연합 Q-테이블 집계를 적용한 첫 경량 분산 MAC 설계
  - 플래툰 내 확장성(Scalability) 실증: 차량 수 증가 시 충돌률 변화 분석
  - 중앙 스케줄러 없는 self-organizing TDMA 프레임워크
- **IoT-J 적합성 점수**: ★★★★☆ (4/5) — 플래툰 IoT 노드 자율 조직화, 경량 연합학습 IoT-J 주요 트렌드 부합; 단, TDMA는 802.11p 표준 외 커스텀 프레임이라 실용성 논거 보강 필요.
- **노벨티 위험**: Liu2024(Federated MARL for NR-V2X), Narayanasamy2024(Cascaded MARL platoon) — 이들은 DRL 기반이고 NR-V2X 자원 블록 중심; 표 형 Q + TDMA 슬롯 + FedAvg 조합은 별도 공간. Alagumani2024(Q-learning V2X clustering)와의 차별화 명확히 필요.

---

### 후보 #4: Online Lightweight GNN-MAC — 실시간 그래프 추론으로 CSMA 채널 예측·사전 예약

- **핵심 가설(Hypothesis)**: 차량 간 통신 토폴로지를 경량 Graph Neural Network(GNN, ≤ 2 레이어, ≤ 32 채널)으로 모델링하여 CSMA 충돌 확률을 예측하고, 예측 충돌이 높은 차량에 선제적 채널 예약(mini-slot reservation)을 적용하면 Dense VANET에서 PDR과 지연이 향상된다.
- **MAC 메커니즘 변경점**: CSMA/CA 백오프 전 단계에 GNN 추론 기반 "충돌 위험 스코어" 계산 추가 → 스코어가 임계값 초과 시 mini-slot 예약 요청 프레임 전송. 기존 DCF/EDCA 파이프라인은 그대로 유지하되 예약 경로만 병렬 추가.
- **AI 구성 요소**:
  - 모델: 2-layer GraphSAGE (mean aggregation), 32-dim 히든, 파라미터 수 < 5000
  - 입력: 노드 피처 (차량 속도, 큐 길이, 이웃 수), 엣지 피처 (수신 신호 강도, 거리)
  - 출력: 노드별 충돌 위험 스코어 [0,1]
  - 경량화: NeighborSampling(k=5), 추론 주기 50ms, TorchScript 직렬화 후 C 바인딩 불필요(Python OK)
- **시뮬레이션 구현**:
  - libsumo: 위치·속도·이웃 정보 추출 → 그래프 생성 (networkx 기반)
  - SumoNetSim: 충돌 위험 스코어 → 전송 큐 우선순위 반영 훅
  - 별도 gnn_predictor.py 모듈 libsumo 루프 안에서 실행 (추가 시뮬레이터로 분류)
  - 학습 데이터: libsumo 시뮬레이션 충돌 이력 레이블 → 오프라인 학습 (< 1시간)
- **베이스라인 (3+)**:
  1. **표준 CSMA/CA (802.11p DCF)** — SumoNetSim 기본
  2. **Li2024a** (GCN-Enhanced Multi-Agent MAC) — 동일 GNN 접근이지만 MARL 기반; 단순 GraphSAGE 비교
  3. **Ni2024** (Hyperdimensional MAC) — 비신경망 경량 MAC과 비교
  4. **Wu2025** (RL 기반 충돌 추정 MAC) — 유사 문제 접근 다른 방법론
- **평가 메트릭**: PDR(%), E2E 지연(ms), 충돌률(%), 처리량(Mbps), GNN 추론 지연(ms)
- **예상 핵심 기여 (Contribution)**:
  - CSMA 충돌 예측을 그래프 구조로 접근한 경량 GNN-MAC 최초 제안
  - mini-slot 예약 메커니즘과 GNN 스코어의 결합으로 DCF 개선 신규 경로 제시
  - Dense VANET(차량 100대 이상) 시나리오에서 GNN 추론 비용 vs. PDR 개선 트레이드오프 정량화
- **IoT-J 적합성 점수**: ★★★☆☆ (3/5) — GNN 아이디어는 신선하지만 IoT-J보다는 IEEE TWC/TVT 성향; IoT-J 채택하려면 에너지 효율·IoT 배포 가능성 논거 강화 필요. 구현 복잡도 대비 novelty 리스크 높음.
- **노벨티 위험**: Li2024a(GCN-Enhanced Multi-Agent MAC — **직접 경쟁**), Zhou2025(GNN Continual Learning 자원 할당), Ni2024 — Li2024a와의 명확한 차별화(mini-slot 예약, 경량화)가 핵심. noveltyx-check 필수.

---

### 후보 #5: Mobility-Predictive MAC Scheduler — LSTM-Free, Linear Predictor 기반 채널 접근 사전 스케줄링

- **핵심 가설(Hypothesis)**: 차량 이동 예측을 LSTM 없이 선형 예측기(Kalman Filter 또는 Linear Regression)로 수행하고, 예측된 이웃 집합 변화를 기반으로 TDMA/OFDMA 슬롯을 사전 스케줄링하면, 반응형(Reactive) MAC 대비 핸드오버 경계에서의 패킷 손실을 줄이고 IoT 센서 데이터 연속성을 높일 수 있다.
- **MAC 메커니즘 변경점**: 기존 반응형 채널 접근(충돌 후 백오프) → 선형 예측 기반 사전 슬롯 예약. 예측 수평선(prediction horizon) = 500ms. 슬롯 충돌 시 fallback CSMA/CA.
- **AI 구성 요소**:
  - 모델: 차량별 Kalman Filter (상태: 위치 x,y, 속도 vx,vy) + Linear Regression 이웃 수 예측
  - 입력: libsumo에서 추출한 위치·속도 시계열 (과거 1초 = 10 샘플)
  - 출력: 500ms 후 이웃 집합 변화 확률 → 슬롯 예약 여부 결정
  - 경량화: KF는 4×4 행렬 연산 → 추론 O(1), 전혀 GPU 불필요
- **시뮬레이션 구현**:
  - libsumo: 실제 도로망(OpenStreetMap 기반) 로드 → 이동 궤적 추출
  - SumoNetSim: 슬롯 예약 프레임 추가 + Fallback CSMA 통합
  - mobility_predictor.py 모듈: Kalman Filter (scipy.linalg) → libsumo 루프에 삽입
  - 3개월 이내 완료 용이 (수치 모델 only)
- **베이스라인 (3+)**:
  1. **반응형 CSMA/CA** — SumoNetSim 기본
  2. **Bhattacharyya2024** (Variable Beacon 크로스 레이어 MAC) — 이동성 예측 없는 크로스 레이어 비교
  3. **PV2025** (RIS-Assisted Full Duplex MAC with ML-QoS prediction) — 예측 기반 QoS MAC과 비교
  4. **고정 TDMA** (라운드로빈) — 슬롯 예약 기준선
- **평가 메트릭**: 핸드오버 경계 PDR(%), E2E 지연(ms), 슬롯 예약 정확도(%), IoT 데이터 연속성(메시지 갭 ms), 채널 효율(%)
- **예상 핵심 기여 (Contribution)**:
  - 무거운 LSTM 없이 Kalman Filter만으로 MAC 사전 스케줄링을 구현한 경량 접근 제안
  - 이동성 예측 정확도와 MAC 성능 연계를 최초로 IoT-J 맥락에서 정량 분석
  - IoT 센서 데이터 연속성 메트릭 도입으로 V2X-IoT 통합 시나리오 기여
- **IoT-J 적합성 점수**: ★★★★☆ (4/5) — IoT 센서 연속성, 경량 배포, 이동성 연구는 IoT-J 핵심 토픽; V2X 맥락에서 IoT 통합 서사 잘 맞음.
- **노벨티 위험**: PV2025(ML-driven QoS prediction MAC), Bhattacharyya2024(Cross-layer MAC Variable Beacon), Chen2025(RL Flexible Numerology V2V) — 예측 기반 MAC은 선행 연구 존재하지만 Kalman Filter + MAC 스케줄링 조합은 직접 경쟁 논문 없음; noveltyx-check 권장.

---

## 2. 후보 비교 표

| # | 제목 | 노벨티 강도 | 구현 난이도 | IoT-J 적합성 | 추천 순위 |
|---|------|------------|------------|-------------|---------|
| 1 | AI-Adaptive EDCA (Q-Table AIFS/CW) | ★★★★☆ 중상 | ★★☆☆☆ 낮음 | ★★★★☆ | 2위 |
| 2 | Context-Aware Beacon Rate Control (TinyMLP-DCC) | ★★★★★ 높음 | ★★★☆☆ 중간 | ★★★★★ | **1위** |
| 3 | Federated Q-Table TDMA Slot Negotiation | ★★★★☆ 중상 | ★★★☆☆ 중간 | ★★★★☆ | 3위 |
| 4 | Online GNN-MAC (충돌 예측 + mini-slot 예약) | ★★★☆☆ 중간 | ★★★★☆ 높음 | ★★★☆☆ | 5위 |
| 5 | Mobility-Predictive MAC (Kalman Filter 슬롯 예약) | ★★★★☆ 중상 | ★★☆☆☆ 낮음 | ★★★★☆ | 4위 |

---

## 3. 1순위 추천 + 근거

**추천: 후보 #2 — Context-Aware Beacon Rate Control (TinyMLP 기반 동적 비콘 주파수·전력 공동 제어)**

이 아이디어는 IEEE IoT-J의 핵심 평가 기준인 IoT 배포 가능성(TinyMLP < 2000 파라미터, MCU 실행 가능), AoI 기반 서비스 품질 보장, 표준(ETSI DCC) 대체 메커니즘 재설계를 모두 충족한다.
비콘 전송 제어는 MAC 메커니즘의 핵심 파라미터(전송 주기, 전력)를 직접 재설계하므로 프로토콜 연구자의 강점과 일치하며, behavior cloning 기반 오프라인 학습으로 시뮬레이션 기간을 1개월 이내로 단축할 수 있다.
AoI + CBR 동시 최적화라는 평가 축은 기존 단일 메트릭(PDR 또는 지연만) 논문들과 차별화되며, Zila2026·Bhattacharyya2024 등과의 직접 충돌도 TinyMLP + V2X + AoI 삼중 조합으로 회피 가능하다.

---

## 4. Librarian에 검증 의뢰할 키워드 묶음 (1순위 후보 #2 기준)

1. `"TinyMLP beacon rate control V2X" OR "tiny MLP V2X MAC beacon"`
2. `"AoI-aware DCC vehicular" OR "Age of Information decentralized congestion control V2X"`
3. `"lightweight neural network ETSI DCC 802.11p" OR "neural DCC V2I beacon"`
4. `"beacon power joint control V2X deep learning" OR "joint beacon frequency power optimization VANET"`
5. `"TinyML MAC protocol vehicular" OR "on-device inference MAC V2X IoT"`
6. `"ETSI EN 302 637 machine learning replacement" OR "CAM generation rate AI control"`
7. `"context-aware beacon adaptation vehicular IoT" OR "mobility-context beacon optimization"`


---

**다음 단계**:
- Librarian에게 후보 #2 (TinyMLP-DCC) 키워드 noveltyx-check 검색 의뢰
- 검색 결과 수령 후 2차 회의에서 1~2개 후보로 좁히기
- idea_spec.md 작성은 2차 회의 이후



---

## [2026-05-08] Phase 2 — 2차 회의: Feasibility & Contribution Review (Round 2)

**세션 컨텍스트**:
- 대상 후보: 후보 #2 (TinyMLP-based Beacon Rate & Power Joint Control)
- Librarian novelty 판정: NOVEL (신뢰도 90%)
- 직접 충돌 논문: 0건 / 부분 중첩 4편 (Bhattacharyya2024, Zila2026, Ni2024, Wu2025)
- 수행 작업: Feasibility & Contribution Review (4개 차원)
- 최종 판정: ✅ GO — idea_spec.md 작성 완료

---

### Phase 2 검토 요약

#### 검토 차원 1 — Contribution 명확성
1차 3개 기여를 IoT-J 기준으로 2+1 구조로 재정렬:
- **C1 [Protocol Design]**: ETSI CAM 호환 AI-DCC 프로토콜 설계 (Novel + Verifiable)
  → ETSI EN 302 637-2 CAM 생성 레이어에 TinyMLP를 내장하여 T_GenCam + p_tx 2D 공동 제어하는 프로토콜 구조 최초 정형화
- **C2 [AI/System]**: AoI-CBR 공동 최적화 Behavior Cloning 프레임워크 (Novel + Impactful)
  → Oracle = AoI+CBR 가중 합 최소화 16-action grid-search. RL 대비 결정론적 학습.
- **C3 [Deployment]**: MCU 배포 가능성 실증 (Verifiable + Impactful)
  → 파라미터 <2,000, FLASH <16 KB, 추론 <1 ms @ Cortex-M4 수치 제시

C1이 "프로토콜 설계 측면" 기여로 사용자 강점 반영.

#### 검토 차원 2 — Feasibility (Q1~Q5)
- **Q1 (ETSI DCC 모듈)**: SumoNetSim에 ETSI DCC 내장 불확실 → 보수적 판단: etsi_cam_layer.py 직접 구현 필요 (2-3주). ETSI EN 302 571에 사양 명확히 정의되어 있어 구현 가능.
- **Q2 (Oracle 생성)**: 16개 이산 행동 조합 전수 grid-search → myopically optimal (200 ms horizon). 전역 최적성 보장, 장기 최적성은 한계로 명시.
- **Q3 (AoI 측정)**: CAM 패킷에 t_gen 타임스탬프 삽입 → 수신 시 AoI_ij = t_rx - t_gen. SumoNetSim 콜백 노출 여부 미확인 시 로그 후처리로 대체 가능.
- **Q4 (Wall-clock 추정)**: 모듈 구현(4주) + Oracle 생성(1주) + 학습(1주) + 실험(2주) + 분석+작성(4주) = 12주 이내 ✅
- **Q5 (베이스라인 위험)**: 최대 위험: ETSI DCC Adaptive (LIMERIC) 재현 복잡도. 완화: Simplified Adaptive (PID 기반) 대체 + 논문에 "simplified" 명시.

#### 검토 차원 3 — Baseline 보강
- BL-A: ETSI DCC Reactive (직접 구현)
- BL-B: ETSI DCC Adaptive/LIMERIC (직접 구현, 위험 높음 → simplified 대체 고려)
- BL-C: Bhattacharyya2024 Variable Beacon (알고리즘 재현)
- BL-D: Fixed 10 Hz (1줄)
- ABL-1: Rate-Only (전력 제어 제거) → 전력 공동 제어 기여도 격리
- ABL-2: No-AoI (AoI 입력 제거) → AoI 피드백 중요성 격리
- Zila2026: IIoT 도메인이라 직접 재현 불가 → Related Work 수치 인용으로 처리

#### 검토 차원 4 — IoT-J 차별화
예상 리뷰어 질문 3개 + 답변 초안 작성:
1. "왜 IoT-J인가?" → 차량=IoT 엣지 노드, AoI=IoT 정보신선도, MCU 배포 = IoT 시스템 통합
2. "실측 MCU 데이터 없이 배포 가능성 주장 가능한가?" → CMSIS-NN 공개 벤치마크, MLPerf Tiny 근거 + 한계 명시
3. "Oracle 합리성 보장?" → 16-action 전수탐색 = 상태별 전역 최적, myopic 한계 투명 공개 + Oracle upper bound 베이스라인 추가

---

### Phase 2 산출물
- `/home/imnyj/papers/paper4/paper/idea/idea_spec.md` ✅ 작성 완료
- `/home/imnyj/papers/paper4/.pipeline/brain/idea_memory.md` ✅ 업데이트 (이 항목)

---

### 다음 단계 권고
1. **Experimenter 호출**: idea_spec.md §5 실험 계획에 따라 모듈 구현 시작 (etsi_cam_layer.py 최우선)
2. **Writer 예고**: §7 Storyline을 Introduction 초안으로 확장 의뢰
3. **리스크 모니터링**: ETSI DCC Adaptive (LIMERIC) 구현 난이도 실측 후 BL-B 대체 여부 결정
4. **아카이브 감시**: 2026년 arXiv에 "TinyML + vehicular beacon" 조합 등장 시 Librarian 재호출

**세션 종료 시각**: 2026-05-08
**Idea Agent 상태**: ✅ Phase 2 완료, GO 판정, idea_spec.md 확정
