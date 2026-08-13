# E2E 테스트 수트 구성을 위한 조사 및 설계 보고서 (Handoff Report)

## 1. Observation (관찰 내용)

본 조사는 청주 방서동 자이 아파트 매입 프로젝트의 종합 재무 시뮬레이션 시스템 및 웹 시뮬레이터에 대한 E2E (End-to-End) 테스트 수트 구축 방안을 정의하기 위해 수행되었습니다.

### 1.1 환경 및 도구 탐색 결과
- **Python 실행 환경**:
  - 기본 실행 경로: `/usr/bin/python3` (Python 3.12.3)
  - 가상환경 실행 경로: `/home/imnyj/venv/bin/python` (Python 3.12.3)
  - 표준 라이브러리: `unittest`, `json`, `math`, `re`, `html.parser`, `urllib` 모두 정상 탑재.
- **테스트 프레임워크 및 파싱 도구**:
  - `/home/imnyj/venv/bin/pytest`: `pytest 9.0.3` 정상 설치 및 즉시 사용 가능 확인.
  - HTML 파싱: `/home/imnyj/venv/bin/python` 상에서 `bs4` (BeautifulSoup4) 파싱 라이브러리 탑재 확인 (`python -c "import bs4"` OK).
  - 브라우저 자동화 툴: `selenium` 및 `playwright`는 기본 및 venv 환경에 미설치됨.
- **JavaScript 파싱/실행 엔진**:
  - `/usr/bin/node` (Node.js v18.19.1) 설치 확인 (`node --version` 실행 결과: `v18.19.1`).
  - Node.js CLI를 통한 헤드리스 JS 수식/로직 독립 검증 실행 지원 가능.

### 1.2 프로젝트 요구사항 및 데이터 구조 관찰
1. **`ORIGINAL_REQUEST.md` 요구사항**:
   - **R1 (일회성 비용)**: 3.5억, 3.75억, 4.0억 원 3개 매매가 시나리오. 취득세(1.1% - 생애최초 200만 원 감면), 법무사비(약 50~55만 원), 중개수수료(0.4% + VAT 10% = 0.44%), 인지세(15만 원), 국민주택채권 할인 실부담금, 이사비(150만 원), 기본 수리/청소비(200만 원).
   - **R2 (대출 시나리오)**: 보유 현금 2.3억 원 (본인 3천만 + 양가 각 1억). 디딤돌/보금자리론 vs 시중은행 대출 비교. 대출 부대비용(인지세 7.5만 원 차주 부담, 근저당 설정비 은행 부담, 보증료 연 0.05~0.1%).
   - **R3 (월별 수지 시뮬레이션)**: 기존 생활비 2,390,708원 중 월세(31.1만 원) 제거 → 기본 2,079,708원. 신규 고정비(관리비 20만 원 + 주차비 1만 원 + 인터넷/TV 3만 원 = 총 24만 원) 추가 → 월 변동/고정 지출 기본합 2,319,708원. 보너스 투입(2월/8월 교연비 각 500만 원, 1월/7월 특강비 각 100만 원, 총 연 1,200만 원) 시 미납 이자 우선 청산 후 원금 상환.
   - **R4 (행정 절차 체크리스트)**: 잔금 납부 → 소유권 이전 등기 → 취득세 신고(60일 이내) → 전입신고 → 확정일자 → 재산세/종부세 안내.
   - **R5 (인터랙티브 웹 시뮬레이터)**: `/home/imnyj/Workspace/House/ui/index4.html` 단일 파일. 슬라이더 `#price-slider`, `#cash-slider`, `#rate-slider`, `#term-slider`, 지표 카드 `#total-initial-cost`, `#monthly-spending`, `#remaining-income`, `#payoff-timeline`, Chart.js 이중축 그래프 (월지출/잔액), 글래스모피즘 다크모드.

2. **`PROJECT.md` 구조 및 인터페이스 계약**:
   - 데이터 계약: `etc/data/financial_params.json`
   - 디렉토리 규칙: GEMINI.md Rule 10에 따라 보조 테스트 및 스크립트는 `etc/tests/` 및 `etc/scripts/`에 배치.

---

## 2. Logic Chain (논리 체인)

1. **테스트 환경 선정**:
   - 관찰 결과, 시스템 상에 `pytest 9.0.3`, `bs4`, `node v18.19.1`이 가용 가능함.
   - 무거운 selenium/playwright 설치 없이 Python의 `unittest`/`pytest`와 `BeautifulSoup4`, Node.js CLI를 조합하면 E2E 검증(데이터 엔진 계산 검증, 마크다운 보고서 정합성, HTML DOM 구조 검증, JS 수식 엔진 검증)을 100% 가볍고 안정적으로 수행할 수 있음.

2. **계층형 (4-Tier) E2E 수트 구성 논리**:
   - **Tier 1 (데이터 엔진 및 세금/부대비용 수식 검증)**: `etc/data/financial_params.json` 및 `etc/scripts/` 계산 엔진의 R1 일회성 비용과 R2 대출 부대비용 및 한도 수식이 정확한지 검증.
   - **Tier 2 (재무 시뮬레이션 보고서 & 행정 체크리스트 검증)**: `House_Financial_Simulation_Report.md` 파일 내 13대 카테고리 수치 정합성, 월세 제거 확인, 보너스 투입 원금상환 로직, R4 시간순 체크리스트 필수 요소 정규식 분석.
   - **Tier 3 (웹 시뮬레이터 HTML & JS 로직 검증)**: `ui/index4.html` 내 핵심 DOM ID 선언 유무(`BeautifulSoup` 활용), Chart.js 이중축 스크립트 연결 유무, 및 JS 상환 산식 계산 결과의 정합성 검증.
   - **Tier 4 (통합 및 Acceptance Criteria 전수 검증)**: 3개 시나리오(3.5억/3.75억/4.0억) 간 데이터 일치성 종합 검증 및 `ORIGINAL_REQUEST.md` Acceptance Criteria의 전 항목 자동 체크.

3. **자동화 실행 및 Exit Code 0 보장 체계**:
   - `etc/tests/run_e2e_tests.py` 마스터 러너를 작성하여 `pytest` 혹은 `unittest.TextTestRunner` 모듈로 Tier 1~4를 순차 실행.
   - 모든 테스트 통과 시 성공 요약 리포트를 `etc/logs/e2e_results.json`에 저장하고 **Exit Code 0**으로 종료. 단 하나라도 실패 시 에러 트레이스 출력과 함께 **Exit Code 1** 반환.

---

## 3. Caveats (제약 및 고려사항)

- **헤드리스 브라우저 미존재**: Playwright나 Selenium 브라우저 바이너리가 설치되어 있지 않으므로, 웹 UI 테스트는 `bs4` 기반 정적 DOM 파싱과 Node.js 기반 JS 계산식 격리 테스트로 대체하여 안정성을 확보함.
- **읽기 전용 조사 범위**: 본 에이전트는 explorer 역할로 탐색 및 구조 설계를 담당함. 프로젝트 메인 코드 작성은 담당 구획(M1~M3 개발 에이전트)에서 수행하며, E2E 수트는 `etc/tests/` 디렉토리에 구축됨.
- **GEMINI.md 배치 규정**: 모든 테스트 관련 보조 파일은 GEMINI.md Rule 10에 따라 `etc/tests/` 하위에 위치해야 함.

---

## 4. Conclusion & Recommendations (결론 및 세부 권장사항)

### 4.1 E2E 테스트 디렉토리 구조 제안
```
/home/imnyj/Workspace/House/
└── etc/
    ├── tests/
    │   ├── run_e2e_tests.py             # 마스터 E2E 러너 & 리포터
    │   ├── test_tier1.py                # Tier 1: 일회성 비용 & 대출 파라미터 엔진 검증
    │   ├── test_tier2.py                # Tier 2: 종합 보고서(MD) & 행정 체크리스트 검증
    │   ├── test_tier3.py                # Tier 3: 웹 시뮬레이터(index4.html) DOM & JS 로직 검증
    │   ├── test_tier4.py                # Tier 4: 시나리오 간 데이터 통합 & 수용 기준 전수 검증
    │   └── helpers/
    │       ├── js_runner.js             # HTML 내 JS 수식 검증용 Node.js 헬퍼
    │       └── report_parser.py         # Markdown 테이블 및 텍스트 파싱 헬퍼
    └── logs/
        └── e2e_results.json             # E2E 테스트 실행 결과 로그
```

### 4.2 각 Tier별 상세 검증 명세 및 수식 검증안

#### Tier 1: `etc/tests/test_tier1.py` (파라미터 및 일회성 비용 엔진)
- **검증 항목**:
  1. `financial_params.json` 및 계산 엔진의 3개 시나리오별 일회성 비용 합계 검증:
     - 3.5억: 취득세 185만 원 (385만 - 감면 200만) + 중개수수료 154만 원 (0.44%) + 법무사비 50만 원 + 인지세 15만 원 + 채권할인 51.5만 원 + 이사비 150만 원 + 수리청소비 200만 원 = 총 **7,855,000 원**.
     - 3.75억: 취득세 212.5만 원 (412.5만 - 200만) + 중개수수료 165만 원 + 법무사비 50만 원 + 인지세 15만 원 + 채권할인 57.4만 원 + 이사비 150만 원 + 수리청소비 200만 원 = 총 **8,349,000 원**.
     - 4.0억: 취득세 240만 원 (440만 - 200만) + 중개수수료 176만 원 + 법무사비 50만 원 + 인지세 15만 원 + 채권할인 64.4만 원 + 이사비 150만 원 + 수리청소비 200만 원 = 총 **8,804,000 원**.
  2. 대출 부대비용 검증: 차주 인지세 75,000원, 근저당 설정비 0원 (은행 부담), 보증료율 반영 여부.
  3. 필요 대출금 검증: `매매가 - 2.3억 원(보유현금)`.

#### Tier 2: `etc/tests/test_tier2.py` (마크다운 보고서 정합성)
- **검증 항목**:
  1. `House_Financial_Simulation_Report.md` 내 13대 생활비 반영 여부 (`Budget/8. 학기 중 예상 지출 보고서.md` 2,390,708원 데이터와의 일치성 확인).
  2. 월세(311,000원) 제거 및 2,079,708원 순수 생활비 전환 검증.
  3. 신규 고정비(관리비 20만, 주차비 1만, TV/인터넷 3만 = 24만 원) 포함하여 대출 제외 고정지출 2,319,708원 정확히 명시되었는지 검증.
  4. 보너스 수입 Schedule (1월/7월 특강비 각 100만 원, 2월/8월 교연비 각 500만 원) 및 원금 상환 차감 로직 검증.
  5. R4 행정절차 필수 단계 6종 (잔금, 등기, 취득세 60일, 전입신고, 확정일자, 재산세/종부세) 및 필요 서류/기관 존재 검증.

#### Tier 3: `etc/tests/test_tier3.py` (웹 시뮬레이터 DOM 및 JS 로직)
- **검증 항목**:
  1. `ui/index4.html` 파일 정적 파싱 (`bs4` 사용):
     - 핵심 요소 ID 검증: `#price-slider`, `#cash-slider`, `#rate-slider`, `#term-slider`, `#total-initial-cost`, `#monthly-spending`, `#remaining-income`, `#payoff-timeline`.
     - 외부 라이브러리 검증: Chart.js CDN 스크립트 태그 포함 여부.
     - 디자인 클래스 검증: 글래스모피즘 CSS 스타일 및 다크모드 토글 버튼/이벤트 존재.
  2. JS 계산 로직 파싱 및 Node.js 실행 검증:
     - `ui/index4.html` 내 원리금 상환 및 보너스 반영 원금 상환 함수를 추출하여 Node.js에서 실행하여 계산 수치 검증.

#### Tier 4: `etc/tests/test_tier4.py` (통합 수용 기준 및 시나리오 교차 검증)
- **검증 항목**:
  1. `financial_params.json`, `House_Financial_Simulation_Report.md`, `ui/index4.html` 3자 간 기본 파라미터(보유 현금 2.3억, 기본 지출 2,319,708원 등)의 100% 일치성 검증.
  2. `ORIGINAL_REQUEST.md` Acceptance Criteria Checklist 전 항목 자동 검증.

#### 마스터 러너: `etc/tests/run_e2e_tests.py`
- **구현 방식**:
  - Python `unittest.TestLoader()` 또는 `pytest.main()` 호출.
  - 전체 실행결과(성공/실패 수, 실패 테스트 이름, 상세 에러 메세지)를 `etc/logs/e2e_results.json`에 저장.
  - 성공시 `sys.exit(0)`, 실패시 `sys.exit(1)`.

---

## 5. Verification Method (검증 방법)

### 5.1 E2E 수트 독립 검증 명령어
수트 작성 완료 후 다음 명령어로 독립 검증을 수행합니다:

```bash
# 1. pytest를 이용한 전체 E2E 테스트 실행
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/ -v

# 2. 마스터 러너 스크립트를 이용한 E2E 종합 테스트 실행
/home/imnyj/venv/bin/python /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py
```

### 5.2 성공 및 무효화 조건
- **성공 조건 (Exit Code 0)**:
  - 모든 Tier 1~4 테스트 케이스가 통과(Pass)함.
  - `etc/logs/e2e_results.json`에 `"status": "SUCCESS"`, `"failed": 0`으로 기록됨.
- **무효화 / 실패 조건 (Exit Code 1)**:
  - 세금 감면액(생애최초 200만 원) 누락 또는 중개수수료율 오산.
  - 13대 카테고리 생활비 중 월세 제외 미반영 또는 신규 고정비(24만 원) 미반영.
  - `index4.html` 내 필수 슬라이더/카드의 DOM ID 누락.
  - 3.5억/3.75억/4.0억 시나리오 간 데이터 불일치 발생.
