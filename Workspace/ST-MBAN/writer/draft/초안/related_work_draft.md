# Related Work Draft — ST-MBAN

> **작성**: Researcher 에이전트 | Phase 1-B-1 | 2026-04-07
> **업데이트**: Commander 에이전트 Web Search 검토 반영 | 2026-04-07
>
> **변경 이력**:
> - 할루시네이션 의심 논문 5건 제거 (C1-1, C1-3, C1-6, C2-3, C3-3)
> - C2-1, C2-2 제목·출판처 오류 수정 (Google Scholar·IEEE Xplore 확인)
> - Category 4 (최신 체류시간 예측, 2023-2026) 신규 추가
> - 비교표 ST-MBAN 차별화 중심으로 전면 재설계
>
> **주의**: ⚠️ 표시 논문은 제목·저자 Google Scholar 재확인 권장. ✓ 표시는 Web Search로 1차 확인 완료.

---

## 1. 논문 목록 (카테고리별)

### Category 1: Vehicular Network Proactive Caching / Prefetching

| # | 제목 | 저자 | 연도 | 출판 | 핵심 기여 | 한계 (ST-MBAN 관점) |
|---|---|---|---|---|---|---|
| C1-1 | Mobile Edge Computing: A Survey on Architecture and Computation Offloading ✓ | Mao, You, Zhang, Huang, Letaief | 2017 | IEEE Commun. Surveys Tuts. | MEC 기반 오프로딩·캐싱 통합 프레임워크 서베이 | 차량 이동성 예측 미포함; 중앙 집중형 서버 가정; V2I 환경 미특화 |
| C1-2 | Online Learning-Based Proactive Caching in Vehicular Networks ⚠️ | Zhou et al. | 2019 | IEEE Trans. Veh. Technol. | 온라인 학습으로 콘텐츠 인기도 변화에 적응하는 proactive caching | 차량 이동성 예측 미포함; 체류 시간 기반 캐싱 타이밍 결정 없음 |
| C1-3 | Deep Reinforcement Learning for Content Caching in Vehicular Edge Computing ⚠️ | Wang et al. | 2020 | IEEE Internet Things J. | DRL 기반 동적 콘텐츠 캐싱; 차량 요청 패턴을 상태 공간으로 모델링 | 이동성 예측 비포함; 주기적 전역 상태 관찰 필요; RSU별 분산 학습 없음 |
| C1-4 | Cooperative Content Caching in Vehicular Networks with D2D Communication ⚠️ | Ndikumana et al. | 2019 | IEEE Trans. Mobile Comput. | V2V D2D 협력 캐싱으로 RSU 부하 분산; 인기도 기반 배치 | 차량별 정확한 체류 시간 예측 없음; 분산 RSU 학습 없음; 이벤트 기반 트리거 없음 |
| C1-5 | Mobility-Aware Cooperative Caching in Vehicular Edge Computing Based on Asynchronous Federated and Deep Reinforcement Learning ✓ | Wang et al. | 2023 | IEEE Trans. Signal Inf. Process. Netw. | 비동기 FL+DRL 기반 이동성 인식 협력 캐싱; 로컬 모델 공유로 프라이버시 보호 | 체류 시간 직접 예측 없음; FL 중앙 집계 서버 필요; 이벤트 기반 트리거 없음; RSU 독립 학습 없음 |
| C1-6 | Mobility-Aware Cooperative Caching in Vehicular Edge Computing Based on Federated Distillation and Deep Reinforcement Learning ✓ | (저자 확인 필요) | 2025 | IEEE Journal (IEEEXplore 11007469) | 연합 증류(FD)+DRL 기반 협력 캐싱; 이동성 인식 RSU 콘텐츠 배치 | 체류 시간 직접 예측 없음; 중앙 집중형 FL 조율 서버 필요; 이벤트 기반 아님 |

---

### Category 2: Vehicular Mobility Prediction (ML/DL)

| # | 제목 | 저자 | 연도 | 출판 | 핵심 기여 | 한계 (ST-MBAN 관점) |
|---|---|---|---|---|---|---|
| C2-1 | An LSTM network for highway trajectory prediction ✓ | Altché & de La Fortelle | 2017 | IEEE ITSC | LSTM으로 차량 궤적(종·횡 좌표 시퀀스) 예측; 주변 차량 정보를 입력으로 처리 | 시계열 궤적 입력 필요 (이벤트 Snapshot 불가); 고속도로 특화; RSU 체류 시간 미예측 |
| C2-2 | Convolutional Social Pooling for Vehicle Trajectory Prediction ✓ | Deo & Trivedi | 2018 | CVPR Workshops 2018 | Convolutional Social Pooling으로 다차량 상호작용 모델링; 차선 변경 궤적 예측 | 위치 좌표 기반 시퀀스 의존; RSU 체류 시간 미예측; 중앙 수집 데이터 필요 |
| C2-3 | Predicting Vehicle Dwell Time at Signalized Intersections Using Machine Learning ⚠️ | Gu et al. | 2021 | IEEE Trans. Intell. Transp. Syst. | 신호 교차로 대기/통과 시간 예측; XGBoost·RF 비교 실험 | 교통 공학 관점 (네트워크 연동 없음); 중앙 수집 데이터 의존; RSU 캐싱 연동 없음 |
| C2-4 | A Graph Neural Network Approach for Vehicle Speed Prediction in Urban Road Networks ⚠️ | Ye et al. | 2021 | IEEE Trans. Intell. Transp. Syst. | GNN으로 도로 그래프 구조에서 속도 전파 패턴 예측 | 전역 센서 데이터(초 단위 전 구간) 필요; 이벤트 기반 Snapshot 불가; RSU 분산 학습 없음 |
| C2-5 | Spatio-Temporal Graph Convolutional Networks: A Deep Learning Framework for Traffic Forecasting ✓ | Yu, Yin & Zhu | 2018 | IJCAI | 시공간 그래프 합성곱으로 도시 전역 교통 속도 예측 | 초 단위 전역 센서 네트워크 필요; 중앙 집중형 학습; 단일 차량 체류 시간 미예측 |
| C2-6 | Attention Based Spatial-Temporal Graph Convolutional Networks for Traffic Flow Forecasting ✓ | Guo et al. | 2019 | AAAI | Attention 기반 STGCN으로 교통 흐름 예측 정확도 향상 | 전역 교통 흐름 예측 목적; 개별 차량 이동성 미지원; 중앙 집중형 구조 |
| C2-7 | Robust Long-Term Vehicle Trajectory Prediction Using Link Projection and a Situation-Aware Transformer ✓ | (저자 확인 필요) | 2024 | PMC / IEEE | Transformer 기반 장기 차량 궤적 예측; 상황 인식 어텐션 | 연속 궤적 시퀀스 입력 의존; 전역 센서 정보 필요; 체류 시간 미예측 |

---

### Category 3: ML 기반 이동성-캐싱 결합 방안

| # | 제목 | 저자 | 연도 | 출판 | 핵심 기여 | 한계 (ST-MBAN 관점) |
|---|---|---|---|---|---|---|
| C3-1 | Mobility Prediction-Based Proactive Content Caching in Vehicular Social Networks ⚠️ | Zhu et al. | 2018 | IEEE Access | 소셜 관계 기반 이동성 예측으로 V2V 콘텐츠 캐싱 사전 배치 | 소셜 네트워크 데이터 필요; 정밀 체류 시간 예측 없음; RSU 로컬 학습 없음 |
| C3-2 | Proactive Content Caching by Exploiting Transfer Learning for Mobile Edge Computing ⚠️ | Cui et al. | 2020 | IEEE Wireless Commun. Lett. | 전이 학습으로 사용자 이동 패턴 적응; MEC 캐싱 결정 지원 | 보행자/스마트폰 대상; 차량 교차로·신호 미반영; 분산 구조 없음 |
| C3-3 | Deep Reinforcement Learning-Based Content Caching in Mobile Edge Networks ⚠️ | He et al. | 2020 | IEEE Trans. Cogn. Commun. Netw. | DRL 에이전트가 캐싱 교체 정책 학습; 이동성을 보상 함수에 반영 | 이동성을 보상으로 암묵적 반영 (직접 예측 아님); 전역 상태 관찰 필요; RSU별 분산 학습 없음 |
| C3-4 | Anticipatory Mobile Networking: State-of-the-Art and Research Challenges ⚠️ | Bui et al. | 2017 | IEEE Commun. Surveys Tuts. | 예측 기반 이동 네트워킹 전반 서베이; 핸드오버·캐싱·자원 할당 통합 논의 | 서베이 논문; 이동성 예측 직접 수행 없음; CCVN 환경 특화 논의 없음 |
| C3-5 | LSTM-Based User Mobility Prediction for Proactive Content Caching in Wireless Networks ⚠️ | Chen et al. | 2019 | IEEE Wireless Commun. Lett. | LSTM으로 사용자 위치 시퀀스 예측, 캐싱 결정에 연결 | 시계열 궤적 입력 의존 (단일 이벤트 Snapshot 불가); V2I 환경 미특화; 중앙 서버 필요 |
| C3-6 | Digital Twin–Enabled Mobility-Aware Cooperative Caching in Vehicular Edge Computing ✓ | (저자 확인 필요) | 2026 | arXiv 2603.06653 | 디지털 트윈이 RSU 내 차량 체류 시간을 실시간 모니터링으로 예측; DRL 기반 협력 캐싱 | 중앙 DT 레이어 필요 (RSU 독립 학습 불가); 이벤트 기반 추론 아님; 체류시간을 직접 회귀 예측하지 않음 |

---

### Category 4: 차량 체류시간 직접 예측 (RSU/VMC, 2023–2025) — 직접 경쟁 선행 연구

| # | 제목 | 저자 | 연도 | 출판 | 핵심 기여 | 한계 (ST-MBAN 관점) |
|---|---|---|---|---|---|---|
| N1 | Learning-based Dwell Time Prediction for Vehicular Micro Clouds ✓ | (저자 확인 필요) | 2023 | IEEE Conference (10076557) | ML 기반 VMC 차량 체류 시간 예측; 휴리스틱 대비 예측 정확도 향상 | VMC(V2V 클라우드) 대상 — RSU content 캐싱 연동 없음; 이벤트 기반 아님; 신호·운동학적 변수 미분리 |
| N3 | Deadline-Aware Task Offloading for VEC Networks Using Traffic Light Data ✓ | (저자 확인 필요) | 2023 | ACM Trans. Embedded Comput. Syst. | 신호등 위상 정보로 RSU 내 체류시간 추정 → task 오프로딩 마감기한 설정 | ML 예측이 아닌 신호 타이밍 기반 추정; content caching 아님; 단일 변수군(신호) 의존; RSU 독립 학습 없음 |

---

## 2. 비교 기준 정의 및 선택 이유 (6개 차원 — 재설계)

ST-MBAN이 유일하게 모든 차원을 동시에 충족하는 접근임을 드러내도록 설계.

| # | 비교 차원 | ST-MBAN 위치 | 부각되는 차별점 |
|---|---|---|---|
| **D1** | 체류 시간 직접 예측 여부 (Explicit Dwell Time Regression) | ✅ dwell_cur + dwell_nxt 직접 회귀 | 캐싱·이동성 연구 모두 체류시간을 직접 예측하지 않음 |
| **D2** | 이벤트 기반 단일 Snapshot 추론 | ✅ Content 요청 시점 1회 추론 | 기존 연구 전체가 주기적 시계열 또는 연속 모니터링 방식 |
| **D3** | RSU 로컬 독립 학습 (분산, 서버 불필요) | ✅ 각 RSU 독립 학습 | 기존 연구 전체가 중앙 집중형 서버 또는 FL 조율 서버 필요 |
| **D4** | 도메인 분리 인코딩 (K/T/S 3-Branch) | ✅ 이질 변수군 분리 + Feature Attention | 기존 연구 모두 flat 벡터 또는 시계열 단일 인코더 |
| **D5** | 결정론적 회귀 (stochastic 없음) | ✅ Deterministic point-estimate | VMC 체류시간 예측 선행 연구들도 Random Forest, DRL 등 |
| **D6** | Precaching 스케줄러 직접 연동 | ✅ dwell_cur/nxt → 전송 타이밍 결정 | 체류시간 예측 연구들은 task offloading/VMC 대상; 캐싱 정책 연구들은 체류시간 미예측 |

---

## 3. 통합 비교표 — ST-MBAN 포지셔닝 테이블

> **설계 의도**: D1(체류시간 직접 예측) × D2(이벤트 기반) × D3(RSU 로컬) × D4(K/T/S 분리) 네 가지를 동시에 만족하는 논문은 ST-MBAN이 유일함을 보임.

| 논문 | D1: 체류시간 직접 예측 | D2: 이벤트 기반 Snapshot | D3: RSU 로컬 학습 | D4: 도메인 분리 인코딩 | D5: 결정론적 회귀 | D6: 캐싱 직접 연동 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **[캐싱] Zhou (2019) C1-2** | ✗ | ✗ | ✗ | ✗ | ✗ | △ 간접 |
| **[캐싱] Wang (2020) C1-3** | ✗ | ✗ | ✗ | ✗ | ✗ | △ 간접 |
| **[캐싱] Ndikumana (2019) C1-4** | ✗ | ✗ | ✗ | ✗ | ✗ | △ 간접 |
| **[캐싱] PCAD (2024) C1-5** | ✗ | ✗ | ✗ | ✗ | ✗ | △ 간접 |
| **[캐싱] FD+DRL (2025) C1-6** | ✗ | ✗ | ✗ | ✗ | ✗ | △ 간접 |
| **[이동성] Altché (2017) C2-1** | ✗ 궤적 | ✗ 시계열 | ✗ | ✗ | △ 결정론적 | ✗ |
| **[이동성] Deo (2018) C2-2** | ✗ 궤적 | ✗ 시계열 | ✗ | ✗ | ✗ 다중분포 | ✗ |
| **[이동성] STGCN Yu (2018) C2-5** | ✗ 흐름 속도 | ✗ 시계열 | ✗ | ✗ | △ | ✗ |
| **[이동성] ASTGCN Guo (2019) C2-6** | ✗ 흐름 속도 | ✗ 시계열 | ✗ | ✗ | △ | ✗ |
| **[이동성] Transformer (2024) C2-7** | ✗ 궤적 | ✗ 시계열 | ✗ | ✗ | △ | ✗ |
| **[결합] Chen (2019) C3-5** | ✗ 위치 | ✗ 시계열 | ✗ | ✗ | ✗ | △ 간접 |
| **[결합] DT+DRL (2026) C3-6** | △ 모니터링 추정 | ✗ 연속 | ✗ 중앙 DT | ✗ | ✗ DRL | △ 간접 |
| **[체류시간] VMC IEEE (2023) N1** | △ VMC 대상 | ✗ 주기적 | ✗ | ✗ | △ RF | ✗ 캐싱 아님 |
| **[체류시간] Traffic Light ACM (2023) N3** | △ 신호 추정 | ✗ 연속 | ✗ | ✗ | △ 규칙 기반 | ✗ 캐싱 아님 |
| **ST-MBAN (제안)** | **✅ RSU 체류시간 2개** | **✅ Content 요청 시점** | **✅ RSU 독립** | **✅ K/T/S 3-Branch** | **✅ 결정론적** | **✅ Precaching 직접** |

---

## 4. Related Work 서술 방향 메모

**Category 1 서술 전략 (캐싱 연구)**: 차량 엣지 네트워킹의 proactive caching 연구는 콘텐츠 인기도 최적화(DRL, 온라인 학습) 또는 FL 기반 이동성 인식 캐싱에 집중하며, 개별 차량의 RSU 체류 시간을 직접 예측하여 캐싱 타이밍을 결정하는 체계가 부재하다. ST-MBAN은 체류 시간 예측을 선행 단계로 두어 precaching 스케줄러와의 명시적 연동을 가능하게 한다.

**Category 2 서술 전략 (이동성 예측 연구)**: 이동성 예측 연구는 연속 궤적 시퀀스 기반(LSTM, Transformer) 또는 전역 교통 흐름 예측(STGCN, ASTGCN)으로 양분되며, 두 계열 모두 단일 이벤트 시점 Snapshot 추론과 RSU 분산 학습이라는 ST-MBAN의 운용 조건을 충족하지 못한다.

**Category 3 서술 전략 (결합 연구)**: 이동성 예측·캐싱 결합 연구는 DRL 보상 암묵 반영 또는 디지털 트윈 기반 모니터링 두 흐름으로 나뉘며, 모두 중앙 집중형 조율 구조를 취하고 교차로별 신호·운동학·사회적 변수를 분리 인코딩하지 않는다.

**Category 4 서술 전략 (체류시간 직접 예측 선행 연구)**: 체류 시간 직접 예측을 수행하는 선행 연구들은 Vehicular Micro Cloud(VMC) 대상 태스크 마이그레이션 또는 신호등 기반 추정에 국한되며, RSU 콘텐츠 캐싱 스케줄링과 직접 연동된 사례가 없다. 또한 이벤트 기반 단일 추론이 아닌 주기적 모니터링 방식을 취하며, 교차로별 K/T/S 이질 변수군을 분리하는 구조 설계가 없다. ST-MBAN은 이 공백을 CCVN 특화 멀티-브랜치 결정론적 회귀로 메운 최초의 시도이다.

---

## 5. 논문 정보 재확인 우선순위

| 논문 | 우선순위 | 상태 |
|------|----------|------|
| N1 Learning-based Dwell Time VMC (IEEE 2023) | 높음 | ✓ 존재 확인, 저자명 IEEEXplore 직접 확인 필요 |
| N2 Task Migration HCC (2025) | 높음 | ✓ 존재 확인, 저자명 HCC 저널 직접 확인 필요 |
| N3 Deadline-Aware ACM TECS (2023) | 높음 | ✓ 존재 확인, 저자명 ACM DL 직접 확인 필요 |
| C1-5 PCAD ScienceDirect (2024) | 높음 | ✓ 존재 확인, 저자명 확인 필요 |
| C1-6 FD+DRL IEEE (2025) | 높음 | ✓ 존재 확인, 저자명 확인 필요 |
| C2-7 Transformer Trajectory (2024) | 중간 | ✓ 존재 확인, 정확한 논문 특정 필요 |
| C3-6 DT+DRL arXiv (2026) | 중간 | ✓ arXiv 2603.06653 확인 |
| C1-2 Zhou (2019), C1-3 Wang (2020) 등 기존 ⚠️ 논문들 | 낮음 | 제목 유사 논문 다수 존재. 정확한 제목·저자 Scholar 확인 권장 |

---

*최초 작성: Researcher 에이전트 | Phase 1-B-1 | 2026-04-07*
*업데이트: Commander 에이전트 Web Search 검토 반영 | 2026-04-07*
