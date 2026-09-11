# Outage Zone V2V Precaching Decision DRL 연구 Walkthrough

이 문서는 나준상 연구원의 `idea.md`를 바탕으로 KCI 논문 작업(Outage Zone V2V Precaching Decision DRL)을 원활하게 수행하기 위한 단계별 작업 시나리오(체크리스트)입니다. `GEMINI.md` 규칙에 따라 원자적(atomic) 서브 태스크로 분리되어 있습니다.

---

## 🚀 Phase 1: 초기 환경 분석 및 사전 설정
- [ ] **1.1. SUMO 시뮬레이션 환경 확인**
  - 기존 `src/sumo` 내 네트워크 파일 확인 (RSU 배치 및 Outage Zone(음영 지역) 거리/크기 파악)
  - 신호등 위치 및 주기 파악 (타겟 차량과 후보 차량들의 군집 형성(Platooning) 여부에 영향을 미침)
- [ ] **1.2. Baseline 차량 밀도(Density) 및 Dwell time 사전 측정**
  - Outage Zone 진입 시 타겟 차량과 동일 방향 후보 차량들(Candidate Vehicles) 간의 평균 유지 거리 프로파일링
- [ ] **1.3. 통신 속도 및 제원 설정**
  - Step당 1초, V2I 및 V2V 통신 속도 6Mbps (0.75MB/s) 고정 파라미터 환경 변수 등록
  - V2V 통신 반경(Range) 파라미터 세팅

## 🧠 Phase 2: RL State/Action/Reward 설계 (이론적 배경)
- [ ] **2.1. State Space 설계 (Reference: ST-MBAN)**
  - 타겟 차량 Feature: 위치, RSU까지의 거리, 속도
  - 후보 차량 Feature: 동일 방향 후보 차량 수(`num_candidates`), 타겟과의 평균 거리(`avg_dist_to_target`)
  - 네트워크 및 신호등 Feature: 남은 Content 크기, 신호 상태 및 남은 시간
- [ ] **2.2. Action Space 정의**
  - Outage Zone 진입에 대비해 후보 차량들에게 V2V용 컨텐츠를 Precache 할 것인가? (Binary: 0 or 1)
- [ ] **2.3. Reward Function 정립 및 Optuna 세팅**
  - Step=1초, 6Mbps 기준 남은 용량(MB) 단위로 통일된 Continuous Reward / Penalty 설계 확립
  - $\alpha, \beta, \gamma, \delta$ 가중치 튜닝을 위한 Optuna Objective 함수 구성

## 💻 Phase 3: `V2V_Env` 환경 구현 (OpenAI Gym / Gymnasium 기반)
- [ ] **3.1. `init()` 및 멤버 변수 초기화**
  - SUMO TraCI 연결 설정 및 타겟/후보 차량 추적용 리스트 초기화
- [ ] **3.2. `reset()` 메서드 구현**
  - 시나리오 리셋 로직 및 Target Vehicle 무작위 선정
  - 타겟 차량의 Next RSU를 식별하고, 현재 RSU 내에 있는 동일 목적지 차량들을 '후보 차량'으로 전역 변수(State)에 반영
- [ ] **3.3. `step(action)` 메서드 구현**
  - Action(1: V2V Precache, 0: No Precache)에 따른 브로드캐스팅 결정
  - RSU 내 거주 중: 타겟 차량 다운로드 및 후보 차량 Precaching 동시 진행
  - Outage Zone 진입 시: 타겟 차량이 V2V 범위 내의 후보 차량들로부터 남은 컨텐츠 다운로드 (Precached 량 차감 로직)
  - 에피소드 종료 조건(다운로드 완료 혹은 다음 RSU 진입 시)에 따른 Reward/Penalty 반환 로직 구현

## 🚆 Phase 4: DRL 모델 학습 및 시뮬레이션 실행
- [ ] **4.1. Stable-Baselines3 (SB3) 세팅**
  - SAC, TD3 모델 정의 및 초기 파라미터 튜닝
- [ ] **4.2. 모델 학습 (Training Loop) 및 Optuna 결합**
  - Optuna 스터디를 통해 최적의 Reward 가중치 탐색 및 모델 학습 병행
  - Tensorboard 연동을 통해 성공률, 평균 낭비 트래픽 등 로깅
- [ ] **4.3. 학습 모델 저장 (`save()`)**
  - `models/sac_v2v_outage_precache.zip` 등의 형식으로 산출물 디렉토리에 저장

## 📊 Phase 5: 평가(Evaluation) 및 결과 시각화
- [ ] **5.1. Test 시나리오 실행 및 성능 지표 추출**
  - 학습된 V2V 모델을 Deterministic 모드로 평가
  - V2V 활용률(%), 백홀 트래픽 낭비량, 다운로드 완료까지 걸린 시간 지표 추출
- [ ] **5.2. 그래프 플롯 및 테이블 시각화**
  - SAC vs TD3 vs No-Precache(Rule-based) 알고리즘 성능 비교 시각화
  - 후보 차량 수(Density) 변화에 따른 V2V Precaching 결정 비율(%) 분석 그래프 도출

## 📝 Phase 6: KCI 논문 작성 (Reference: LSOM)
- [ ] **6.1. 논문 아웃라인(Outline) 작성 및 분량 배분**
  - 서론(음영 지역 통신 단절 문제), 관련 연구, V2V 기반 시스템 모델, DRL 성능 평가, 결론
  - 나준상/남영주 저자 양식, KCI(LSOM) 템플릿 적용
- [ ] **6.2. 섹션별 초안 작성 (Drafting)**
  - 각 파트를 원자적 태스크로 나누어 학술적 언어로 서술
- [ ] **6.3. 교정 및 리뷰 (Review)**
  - 오탈자 확인 및 수식(State, Reward) 도식화/수식화 점검
  - 남영주 교수(교신저자) 피드백 반영 후 최종본 도출
