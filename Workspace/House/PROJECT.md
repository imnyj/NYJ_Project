# Project: House Financial Simulation Project (청주 방서동 자이 아파트)

## Architecture
본 프로젝트는 청주 방서동 자이 아파트(<30평, 3.5억/3.75억/4.0억 원) 매입 시 발생하는 일회성 제반비용 조사, 대출 비교 분석, 월별/연별 수지 시뮬레이션, 행정/법률 절차 체크리스트를 포함한 종합 재무 시뮬레이션 보고서(MD)와 인터랙티브 웹 시뮬레이터(HTML) 개발 프로젝트이다.

### 데이터 및 계산 시스템 구조
1. **입력 파라미터**:
   - 보유 현금: 2.3억 원 (본인 3,000만 + 본인 부모님 1억 + 여자친구 부모님 1억)
   - 아파트 매매가 시나리오: 3.5억 원 / 3.75억 원 / 4.0억 원
   - 소득: 월 330만 원 (연 3,960만 원)
   - 정기 보너스 투입 계획: 1월/7월 교연비 400만 원 (100만 유보), 2월/8월 부가소득 100만 원 -> 연 총 1,000만 원 원금 보너스 상환
   - 월 주거 비용 부담 가능액: 50만 원 (대출 원리금 상환용)
   - 생활비: 기존 13대 카테고리 2,390,708 원 중 월세 항목(31.1만 원) 제거 -> 생활비 기본 2,079,708 원
   - 신규 고정비: 아파트 관리비(20만 원), 주차비(1만 원), TV/인터넷(3만 원) -> 총 24만 원
   - 변경 후 월 고정 지출: 2,319,708 원 (대출 원리금 제외)
2. **일회성 비용 (3.5억 / 3.75억 / 4.0억 시나리오)**:
   - 취득세: 본세 1.0% + 지방교육세 0.1% = 1.1% (생애최초 취득세 감면 200만 원 적용)
     - 3.5억: 385만 - 200만 = 185만 원
     - 3.75억: 412.5만 - 200만 = 212.5만 원
     - 4.0억: 440만 - 200만 = 240만 원
   - 법무사 등기대행료: 약 50만~55만 원
   - 중개수수료: 법정 상한 요율 0.4% + VAT 10% = 0.44% (3.5억: 154만 원 / 3.75억: 165만 원 / 4.0억: 176만 원)
   - 인지세: 15만 원
   - 국민주택채권 매입비(할인 실부담액): 시가표준액(공시가 약 70%) × 매입률 2.1~2.3% × 할인율 10% (3.5억: 약 51.5만 원 / 3.75억: 약 57.4만 원 / 4.0억: 약 64.4만 원)
   - 이사비: 150만 원
   - 기본 수리/청소: 200만 원
   - 일회성 비용 총액: 3.5억 시나리오 785.5만 원 / 3.75억 시나리오 834.9만 원 / 4.0억 시나리오 880.4만 원
3. **대출 비교 시나리오**:
   - 디딤돌대출 (신혼부부 특례): 금리 연 3.0~3.3%, 한도 4억, LTV 70%
   - 보금자리론 / 일반 시중은행 주택담보대출 비교
   - 대출 부대비용: 근저당 설정비 (은행 부담), 인지세 (차주 실부담 7.5만 원), 보증료 (연 0.05~0.1%)
4. **산출물**:
   - `House_Financial_Simulation_Report.md`: 종합 마크다운 보고서
   - `ui/index4.html`: 글래스모피즘 & Chart.js 이중축 웹 시뮬레이터

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1. 일회성 비용 전수조사 | 3개 가격 시나리오별 취득세(감면 포함), 법무사비, 중개수수료, 인지세, 채권할인액, 이사비, 수리청소비 산출 근거 명시 | M1 | ORIGINAL_REQUEST §R1 |
| 2 | R2. 대출 시나리오 비교 | 디딤돌/보금자리론 vs 시중은행 금리, 한도, 소득요건 및 근저당설정비, 인지세, 보증료 비교 | M1 | ORIGINAL_REQUEST §R2 |
| 3 | R3. 월별/연별 재무 시뮬레이션 | 초기 1년 월별 현금흐름, 이후 연별 요약, 관리비/주차비/인터넷 추가, 월세 제거, 보너스 투입 원금상환 로직 반영 | M2 | ORIGINAL_REQUEST §R3 |
| 4 | R4. 행정/법률 절차 체크리스트 | 잔금~전입신고/등기/취득세/재산세 시간순 체크리스트 (기한, 담당기관, 필요서류) | M2 | ORIGINAL_REQUEST §R4 |
| 5 | R5. 웹 시뮬레이터 (ui/index4.html) | Glassmorphism UI, 다크모드, 입력 슬라이더, Chart.js 이중축 그래프, 4대 실시간 지표 계산 | M3 | ORIGINAL_REQUEST §R5 |
| 6 | E2E 테스트 수트 구축 | Tier 1~4 요구사항 기반 E2E 검증 수트 작성 및 TEST_READY.md 발행 | E2E | Dual Track E2E |
| 7 | 최종 통합 & 적대적 검증 | 전체 산출물 통합 검증, Tier 5 적대적 챌린저 검증 및 승리 감사 | M4 | Dual Track Final |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Suite | E2E 테스트 하네스, 스크립트 작성 및 TEST_READY.md 게시 | Survey | IN_PROGRESS |
| M1 | Financial Data Engine & Analysis | R1 일회성 비용 전수조사 & R2 대출 상품/부대비용 비교 데이터 검증 스크립트 | Survey | DONE |
| M2 | Comprehensive Financial Report | R3 월별/연별 재무 시뮬레이션 및 R4 행정/법률 체크리스트 마크다운 보고서 작성 | M1 | PLANNED |
| M3 | Interactive Web Simulator | R5 ui/index4.html 제작 (Glassmorphism, Chart.js, 실시간 계산) | M1 | PLANNED |
| M4 | Final E2E Integration & Verification | 100% E2E 테스트 통과 및 Tier 5 적대적 챌린저 검증, 종합 보고서 최종 확정 | E2E, M2, M3 | PLANNED |

## Code Layout
```
/home/imnyj/Workspace/House/
├── ORIGINAL_REQUEST.md                          # 원본 사용자 요구서
├── PROJECT.md                                   # 프로젝트 메인 오케스트레이션 설계서
├── House_Financial_Simulation_Report.md         # 최종 종합 재무 시뮬레이션 보고서 (R1~R4)
├── ui/
│   ├── index.html, index2.html, index3.html     # 레거시 UI 파일
│   └── index4.html                              # 신규 인터랙티브 웹 시뮬레이터 (R5)
├── Budget/
│   └── 8. 학기 중 예상 지출 보고서.md             # 기존 예산 참고 데이터
├── etc/                                         # 보조 스크립트, 데이터 JSON, 로그 (GEMINI.md Rule 10)
│   ├── scripts/                                 # 계산 엔진 및 검증 스크립트
│   ├── data/                                    # 시뮬레이션 파라미터 JSON
│   └── tests/                                   # E2E 테스트 수트 스크립트
└── .agents/                                     # 에이전트 메타데이터
```

## Interface Contracts
### Data Contract: `etc/data/financial_params.json`
- `scenarios`: `[350000000, 375000000, 400000000]`
- `cash_reserve`: `230000000`
- `monthly_income`: `3300000`
- `bonuses`: `[ {month: 1, amount: 1000000}, {month: 2, amount: 5000000}, {month: 7, amount: 1000000}, {month: 8, amount: 5000000} ]`
- `expenses`: base living expense without rent (2,079,708) + apartment fixed (240,000) = 2,319,708

### Web Simulator Contract: `ui/index4.html`
- Inputs: `#price-slider`, `#cash-slider`, `#rate-slider`, `#term-slider`
- Key Output Elements: `#total-initial-cost`, `#monthly-spending`, `#remaining-income`, `#payoff-timeline`
- Dual-axis Chart: `Chart.js` instance with `y` (monthly payments/interest/bonus bar) and `y1` (loan balance line).
