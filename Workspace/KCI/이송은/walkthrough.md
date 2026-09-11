# V2I Precaching Decision DRL 연구 Walkthrough

이 문서는 `idea.md`의 내용을 바탕으로 KCI 논문 작업(V2I Precaching Decision DRL)을 원활하게 수행하기 위한 단계별 작업 시나리오(체크리스트)입니다. `GEMINI.md`의 규칙에 따라 모든 작업은 원자적(atomic) 서브 태스크로 분리되어 있습니다. 각 단계를 에이전트 혹은 사용자 피드백과 함께 하나씩 해결해 나갈 예정입니다.

---

## 🚀 Phase 1: 초기 환경 분석 및 사전 설정
- [ ] **1.1. SUMO 시뮬레이션 환경 확인**
  - 기존 `src/sumo` 경로 내의 네트워크, 차량 라우팅 파일, RSU 배치 상태 확인
  - 신호등 위치 및 주기 파악 (Dwell time에 결정적 영향을 미치므로 필수)
- [ ] **1.2. Baseline 차량 Dwell time 사전 측정 (Optional but Recommended)**
  - 차량들이 RSU 커버리지를 통과할 때 걸리는 대략적인 체류 시간(Dwell time) 프로파일링
  - 신호 대기 유무에 따른 Dwell time 편차 데이터 수집
- [ ] **1.3. Content Size 및 통신 속도 설정**
  - WiFi 통신 속도(Data rate) 모델링
  - 차량이 RSU 1개 또는 2개를 지나는 동안 완료될 수 있도록 적절한 Content Size 도출

## 🧠 Phase 2: RL State/Action/Reward 설계 (이론적 배경)
- [ ] **2.1. State Space 설계 (Reference: ST-MBAN)**
  - 차량 관련 Feature: 차량 위치, 속도, 주행 경로 등
  - 네트워크 관련 Feature: 남은 Content 크기, 현재 RSU의 부하 상태 등
  - **신호등 Feature:** 현재 진행 방향의 신호 상태(Green/Red 및 남은 시간) (Dwell time 예측을 위해 반드시 포함)
- [ ] **2.2. Action Space 정의**
  - Next RSU에 전체 Content를 Precaching 할 것인가? (Binary: Yes or No)
- [ ] **2.3. Reward Function 정립**
  - Action = Precache (Next RSU 활용 의도)
    - 현재 RSU에서 다운로드 완료 시 -> 패널티 (잘못된 예측에 따른 자원 낭비)
    - 다음 RSU에서 다운로드 완료 시 -> 리워드 (성공적인 Precaching)
  - Action = Not Precache (현재 RSU 내 완료 의도)
    - 현재 RSU에서 다운로드 완료 시 -> 리워드
    - 다음 RSU에서 다운로드 완료 시 -> 패널티 (다운로드 중단 및 끊김 발생)
  - *예외 상황이나 통신 끊김 등에 대한 추가 패널티 설계 필요 여부 확인*

## 💻 Phase 3: `V2I_Env` 환경 구현 (OpenAI Gym / Gymnasium 기반)
- [ ] **3.1. `init()` 및 멤버 변수 초기화**
  - SUMO TraCI 연결 설정 및 환경 변수 세팅
- [ ] **3.2. `reset()` 메서드 구현**
  - SUMO 시뮬레이션 초기화 및 시나리오 리셋 로직
  - Step을 진행하며 확률적으로 대상 차량(Target Vehicle) 및 Content 요청 발생
  - 차량이 RSU 영역 진입 시, 현 RSU 및 Next RSU 식별
  - 초기 State 생성 및 리턴
- [ ] **3.3. `step(action)` 메서드 구현**
  - Action을 받아 Next RSU Precaching 여부 결정
  - 시뮬레이션 내부 Step 루프 진행 (차량 이동 및 Content 다운로드)
  - 다운로드 완료 시나리오 체크 로직 (보상 및 패널티 부여)
  - RSU 커버리지 이탈 시나리오 (Episode 중단 / Done 처리 로직)
  - Next State 생성 및 리턴

## 🚆 Phase 4: DRL 모델 학습 및 시뮬레이션 실행
- [ ] **4.1. Stable-Baselines3 (SB3) 세팅**
  - SAC (Soft Actor-Critic) 모델 정의 및 하이퍼파라미터 튜닝
  - TD3 (Twin Delayed DDPG) 모델 정의 및 하이퍼파라미터 튜닝
- [ ] **4.2. 모델 학습 (Training Loop)**
  - 각 모델별 `env.learn()` 실행
  - 에피소드 별 Reward 추이, 성공률(Success Rate) 등 로깅 (Tensorboard 활용)
- [ ] **4.3. 학습 모델 저장 (`save()`) 및 관리**
  - `models/sac_v2i_precache.zip` 등의 형식으로 프로젝트 내부 경로에 체계적 저장

## 📊 Phase 5: 평가(Evaluation) 및 결과 시각화
- [ ] **5.1. Test 시나리오 실행 및 성능 지표 추출**
  - 학습된 모델을 불러와 Deterministic Evaluation 실행
  - 오차율, 다운로드 완료율, 네트워크 낭비량 등의 평가지표 산출
- [ ] **5.2. 그래프 플롯 및 테이블 시각화**
  - SAC vs TD3 vs Rule-based(혹은 Random) 성능 비교 시각화
  - 신호 대기 시간에 따른 결정 변화 등의 분석 그래프 도출

## 📝 Phase 6: KCI 논문 작성 (Reference: LSOM)
- [ ] **6.1. 논문 아웃라인(Outline) 작성 및 분량 배분**
  - 서론, 관련 연구, 시스템 모델 및 강화학습 설계, 성능 평가, 결론
  - LSOM 논문의 분량, 양식, 템플릿(스타일) 벤치마킹
- [ ] **6.2. 섹션별 초안 작성 (Drafting)**
  - 각 섹션을 원자적 태스크로 나누어 학술적 언어로 서술 (AI 특유의 과장된 어투 지양)
- [ ] **6.3. 교정 및 리뷰 (Review)**
  - 내용 검수, 오탈자 확인, 도표 삽입 및 캡션 작성
  - 공저자(이송은, 남영주) 피드백 반영 및 최종본 도출
