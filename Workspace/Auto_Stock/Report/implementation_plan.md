# 주식 자동 매매 프로그램 구현 계획 (Auto Stock ML/RL Trader)

## 📌 Goal Description
키움증권 REST API 및 다중 데이터 소스(OpenDART, 네이버 금융 등)를 활용하여 국내 주식을 거래하는 **하이브리드 머신러닝(지도학습+강화학습) 자동 매매 프로그램**을 구축합니다. 
이 시스템은 완전한 로컬 환경에서 구동되며, 데이터 환각 방지 및 자본 손실 위험을 최소화하기 위해 **가상 모의투자 환경을 선제적으로 구축하고 철저한 단계별 검증(Phase 1~5)** 을 거친 후 실거래에 투입되도록 고도로 안정성을 추구합니다.

## ⚠️ User Review Required
> [!WARNING]
> **OpenDART API Key 발급:** 정확한 재무제표 크로스체크를 위해 금융감독원 OpenDART API 키 발급이 추가로 필요합니다. (무료 발급 가능)
> **이메일 알림 설정:** `imnyj19922@gmail.com`으로 중요 알림을 발송하기 위해 발신용 이메일 계정의 SMTP 설정(예: Gmail 앱 비밀번호)이 필요합니다.

## ❓ Open Questions
- 8단계(ML 실거래)에 도달하기 전까지 단계별로 긴 시간이 소요될 수 있습니다. 각 Phase가 완료될 때마다 이메일 알림을 통해 작업 현황 보고를 받으시겠습니까, 아니면 로컬 시스템 로그로만 남기는 것이 좋으시겠습니까?

## 🛠 Proposed Changes (Architecture & Modules)

프로젝트 기본 디렉토리: `/home/imnyj/Workspace/Auto_Stock`

### 1. Data Pipeline (데이터 수집 및 크로스체크)
- `modules/data/collector_fundamental.py`: 키움, DART, 네이버 금융에서 재무/지표 데이터를 각각 수집하고 교차 검증하여 결측치 및 이상치를 보정하는 모듈.
- `modules/data/collector_price.py`: 특정 종목의 과거 시계열 데이터(분봉/일봉) 수집 및 저장.
- `modules/data/streamer.py`: 장중 실시간 주가 데이터를 수집 및 로컬 캐싱.

### 2. Trading Engine (매매 및 가상 환경)
- `modules/engine/mock_environment.py`: 가상 잔액(Virtual Balance) 관리, 가상 체결(Slippage 반영), 모의 자동 매수/매도 처리를 담당하는 모의 투자 코어 엔진.
- `modules/engine/manual_trader.py`: CLI 명령어 또는 단순 스크립트를 통해 실계좌에 주문(Buy/Sell)을 직접 넣고 제어할 수 있는 수동 매매 검증 모듈.
- `modules/engine/live_trader.py`: 최종 실거래를 담당할 자동화 모듈.

### 3. ML Models (학습 및 예측)
- `modules/ml/supervised_trainer.py`: 교차 검증된 데이터를 바탕으로 현재가 및 단기 미래 주가를 예측하는 지도학습 모델 훈련.
- `modules/ml/rl_trainer.py`: 가상 환경(Mock Environment)을 활용하여 최적의 Action(Buy/Sell/Hold)을 학습하는 강화학습 에이전트.

## 🔍 Step-by-step Verification Plan (신뢰성 확보를 위한 단계별 실행 계획)

### Phase 1: 데이터 신뢰성 및 파이프라인 검증
- **Step 1:** 재무제표 및 지표 다중 소스 수집 및 교차 검증 로직 구현.
- **Step 2:** 특정 관심 종목의 과거 시계열 주가 데이터 수집 및 DB(Parquet/SQLite) 적재.
- **Step 3:** 실시간 주가 정보 수집 및 지연시간(Latency) 테스트.

### Phase 2: 가상 체결 엔진(모의 투자) 구축
- **Step 4:** `mock_environment.py`를 구현하여 초기 가상 자본금을 설정하고, 임의의 룰 기반 로직으로 가상 매수/매도/잔액 갱신이 1원 단위까지 정확히 맞는지 회계적 무결성 검증.

### Phase 3: 실거래 제어 안전성 검증
- **Step 5:** `manual_trader.py`를 작성하여 버튼 혹은 커맨드라인으로 소액(예: 1주) 실거래 매수/매도 주문을 넣고 실제 계좌 잔고가 제대로 변동되는지 1차 수동 검증.

### Phase 4: ML 모델 학습 및 모의 평가 (Paper Trading)
- **Step 6:** 검증된 신뢰성 높은 데이터를 통해 지도학습 및 강화학습 모델 훈련(학습 시 실거래 데이터 구조 사용).
- **Step 7:** 훈련된 모델을 Phase 2의 가상 엔진에 결합하여 장중 실시간 데이터를 받으며 모의 투자를 진행. 예측 수익률 추적 및 모델 안정성 평가.

### Phase 5: Live Trading (실거래 자동 매매)
- **Step 8:** 모의 평가에서 승률 및 안정성이 입증된 ML 모델을 Phase 3에서 검증해둔 실거래 모듈과 최종 결합하여 완전 자동 매매 시작.
