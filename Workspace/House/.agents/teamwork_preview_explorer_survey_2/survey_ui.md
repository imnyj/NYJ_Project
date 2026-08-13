# 🎨 웹 시뮬레이터 UI 구현 전수 조사 및 index4.html 기술 명세서

**작성일**: 2026-08-12  
**작성자**: teamwork_preview_explorer_survey_2  
**조사 대상 파일**: 
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/UI 요구서.md`
- `/home/imnyj/Workspace/House/ui/index.html`
- `/home/imnyj/Workspace/House/ui/index2.html`
- `/home/imnyj/Workspace/House/ui/index3.html`
- `/home/imnyj/Workspace/House/ui/update_ui.py`
- `/home/imnyj/Workspace/House/Budget/8. 학기 중 예상 지출 보고서.md`

---

## 1. 개요 (Executive Summary)

본 보고서는 청주 방서동 자이 아파트(30평 미만, 3.5억~4억 원대) 매입 시 발생하는 제반 비용과 대출 상환 시뮬레이션을 제공하기 위한 **인터랙티브 웹 시뮬레이터(`index4.html`) 제작용 기술 조사 보고서**입니다. 기존에 작성된 `index.html`, `index2.html`, `index3.html`의 CSS 디자인 시스템, Chart.js 그래프 구조, JavaScript 입력 바인딩 및 상환 로직을 전수 조사하여, 요구사항(R1~R5 및 UI 요구서)을 완벽히 충족하는 `index4.html` 설계 명세를 제시합니다.

---

## 2. 글래스모피즘 CSS 디자인 시스템 및 테마 분석

### 2.1 CSS Color Tokens & 디자인 변수
`index.html`과 `index3.html`은 CSS Custom Properties(`:root` 및 `[data-theme="dark"]`)를 활용한 글래스모피즘(Glassmorphism) 테마 시스템을 구축하고 있습니다.

| 디자인 토큰 (Variable) | 라이트 모드 (Light Mode) | 다크 모드 (Dark Mode) | 용도 및 시각적 특징 |
| :--- | :--- | :--- | :--- |
| `--bg` | `#f3f4f6` (Light Gray) | `#0f172a` (Slate 900) | 전체 배경색 |
| `--glass-bg` | `rgba(255, 255, 255, 0.65)` | `rgba(30, 41, 59, 0.65)` | 글래스 카드의 반투명 배경 |
| `--glass-border` | `rgba(255, 255, 255, 0.4)` | `rgba(255, 255, 255, 0.1)` | 카드의 미세한 은은한 테두리 |
| `--text-main` | `#1f2937` (Gray 800) | `#f8fafc` (Slate 50) | 주 텍스트 / 타이틀 |
| `--text-muted` | `#4b5563` (Gray 600) | `#94a3b8` (Slate 400) | 보조 설명 / 서브라벨 |
| `--accent` | `#4f46e5` (Indigo 600) | `#818cf8` (Indigo 400) | 주 브랜드 포인트 / 강조 텍스트 |
| `--danger` | `#ef4444` (Red 500) | `#ef4444` (Red 500) | 이자, 경고, 불가능 상태 |
| `--success` | `#10b981` (Emerald 500) | `#10b981` (Emerald 500) | 완납, 가능 상태, 원금 상환 |
| `--warning` | `#f59e0b` (Amber 500) | `#f59e0b` (Amber 500) | 미납 이자, 주의 상태 |
| `--card-shadow` | `0 8px 32px 0 rgba(31, 38, 135, 0.15)` | `0 8px 32px 0 rgba(0, 0, 0, 0.3)` | 입체감을 위한 부드러운 그림자 |

### 2.2 Glassmorphism 시각 효과 구현 방식
1. **Backdrop Filter**: `backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);`를 적용하여 카드 배경 뒤의 오브젝트가 블러 처리되도록 함.
2. **배경 블롭(Ambient Background Blobs)**:
   - 화면에 `position: fixed`로 3개의 원형 블롭(`.blob1`, `.blob2`, `.blob3`)을 배치.
   - `filter: blur(80px); opacity: 0.6; z-index: -1;`로 부드러운 오로라 효과 연출.
   - 다크모드 전환 시 블롭 색상 자동 변경 (`#ff9a9e` → `#312e81`, `#a18cd1` → `#831843`, `#84fab0` → `#064e3b`).
3. **카드 구조 (`.glass`)**:
   - `border-radius: 20px; padding: 30px; margin-bottom: 24px;`로 시각적 일관성 제공.

### 2.3 다크모드 토글 메커니즘
- **플로팅 버튼**: 화면 우측 상단 고정 (`position: fixed; top: 20px; right: 20px; z-index: 100`).
- **상태 전환**: `toggleTheme()` 함수 실행 시 `document.body.getAttribute('data-theme')`의 값을 체크하여 `dark` 속성을 추가/제거.
- **Chart.js 연동 동적 테마 반영**:
  - `index3.html`에서는 테마 전환 시 `calculate()`를 재호출하여 폰트 색상(`fontColor`), 축 그리드 색상(`gridColor`)을 갱신.
  - 다크모드 시 폰트는 `#94a3b8`, 그리드는 `rgba(255, 255, 255, 0.1)` 적용.

---

## 3. Chart.js 기반 이중축(Dual-Axis) 시각화 구성 분석

### 3.1 `index.html` vs `index3.html` 그래프 구현 비교
- **`index.html` / `index2.html`**: 단일 Y축 line 차트. 월 이자 부담액과 상환액 추이만 표시.
- **`index3.html`**: **이중축(Dual-Axis) 콤보 차트 (`mainChart`)** 구현.
  - **좌측 Y축 (`yLeft`)**: 월 이자/납입액/보너스 투입액 (단위: 원)
  - **우측 Y축 (`yRight`)**: 대출 잔액 (단위: 원)
  - **차트 타입 혼합**: Bar (보너스 투입) + Line (월 이자, 기준선, 대출 잔액)

### 3.2 `index3.html` 이중축 차트 세부 설정 명세
```javascript
mainChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: labels, // 예: ['1년 4월', '1년 5월', ...]
        datasets: [
            {
                label: '보너스 → 원금상환',
                data: bonusData,
                type: 'bar',
                backgroundColor: 'rgba(16, 185, 129, 0.75)',
                yAxisID: 'yLeft',
                order: 3
            },
            {
                label: '보너스 → 미납이자 청산',
                data: bonusShortfallData,
                type: 'line',
                backgroundColor: 'rgba(245, 158, 11, 0.75)',
                yAxisID: 'yLeft',
                order: 3
            },
            {
                label: '월 발생 이자 (내야 할 금액)',
                data: interestFullData,
                type: 'line',
                borderColor: '#f87171',
                yAxisID: 'yLeft',
                order: 1
            },
            {
                label: '매달 납입 가능액 (기준선)',
                data: paymentLineData,
                type: 'line',
                borderColor: '#60a5fa',
                borderDash: [8, 4],
                yAxisID: 'yLeft',
                order: 1
            },
            {
                label: '대출 잔액',
                data: balanceData,
                type: 'line',
                borderColor: '#fbbf24',
                fill: true,
                yAxisID: 'yRight',
                order: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
            x: {
                ticks: {
                    callback: function(val, index) {
                        return index % 6 === 0 ? this.getLabelForValue(val) : '';
                    }
                }
            },
            yLeft: {
                type: 'linear',
                position: 'left',
                ticks: { callback: function(v) { return formatKRW(v) + '원'; } }
            },
            yRight: {
                type: 'linear',
                position: 'right',
                ticks: { callback: function(v) { return formatKRW(v) + '원'; } },
                grid: { drawOnChartArea: false } // 우측 그리드 중첩 방지
            }
        }
    }
});
```

---

## 4. 기존 슬라이더/입력 바인딩 및 상환 계산 함수 분석

### 4.1 UI 요소와 슬라이더/입력 필드 매핑
| 요소 ID | 컨트롤 종류 | 기본값 | 범주/단위 | 연동 함수 |
| :--- | :--- | :--- | :--- | :--- |
| `apt-price` | range | 4.5억 원 | 3억~5억 (step 100만) | `calculate()` |
| `cash` | number | 2.3억 원 | 고정 보유 자금 | `calculate()` |
| `start-month` | range | 4월 | 1~12월 (step 1월) | `calculate()` |
| `max-years` | range | 30년 | 10~40년 (step 5년) | `calculate()` |
| `rate1` | range | 4.2% | 2.0%~6.0% (step 0.1%) | `calculate()` |
| `rate2` | range | 2.0% | 1.0%~4.0% (step 0.1%) | `calculate()` |
| `switch-year` | range | 3년 | 1~10년 (step 1년) | `calculate()` |
| `monthly-payment`| number | 50만 원 | 매월 상환 가능액 | `calculate()` |
| `feb-bonus` | number | 500만 원 | 2월 교연비 | `calculate()` |
| `aug-bonus` | number | 500만 원 | 8월 교연비 | `calculate()` |
| `jan-extra` | number | 0원 | 1월 추가 수당 (특강비) | `calculate()` |
| `jul-extra` | number | 0원 | 7월 추가 수당 (특강비) | `calculate()` |

### 4.2 대출 상환 시뮬레이션 알고리즘 (`index3.html` 기준)
1. **대출 원금 산출**: `loanAmount = aptPrice - cash`
2. **월별 시뮬레이션 루프 (최대 `maxYears * 12`개월)**:
   - **적용 금리 판정**: `m < switchYear * 12` 일 경우 `rate1` (보금자리론), 이후 `rate2` (신생아 특례).
   - **월 발생 이자 계산**: `monthlyInterest = currentLoan * (currentRate / 12)`
   - **월정 상환액 처리**:
     - `monthlyPayment >= monthlyInterest`: 이자 완납 후 잔여금(`monthlyPayment - monthlyInterest`)으로 원금 차감.
     - `monthlyPayment < monthlyInterest`: 납입 가능액 전액 이자 처리, 부족분은 `accumulatedShortfall`에 누적.
   - **보너스 상환 처리 (1월, 2월, 7월, 8월)**:
     - 1차: `accumulatedShortfall` 미납이자 우선 변제.
     - 2차: 미납이자 변제 후 남은 보너스로 `currentLoan` 원금 직접 차감.
   - **연말 미납이자 원금 자본화(Capitalization)**:
     - 매 12개월 경과 시점에 남아있는 미납이자(`accumulatedShortfall`)는 원금에 합산(`currentLoan += accumulatedShortfall`).
   - **종료 조건**: `currentLoan <= 0` 도달 시 완납 연월 기록 및 루프 탈출.

---

## 5. `index4.html` 완성을 위한 상세 기술 명세서

`index4.html`은 ORIGINAL_REQUEST.md의 요구사항(R1~R5), UI 요구서.md, 그리고 기존 `index3.html`의 UI 디자인 톤과 알고리즘을 종합 결합하여 제작되어야 합니다.

### 5.1 4대 실시간 핵심 지표 계산 공식 명세

#### (1) 초기 필요 자금 총액 ($C_{init}$) 및 필요 대출금 ($L_{req}$)
$$\text{일회성 부대비용 } (C_{onetime}) = \text{취득세} + \text{법무사비} + \text{중개수수료} + \text{인지세} + \text{채권할인실부담} + \text{이사비} + \text{수리비} + \text{대출부대비용(근저당/보증료)}$$
$$C_{init} = \text{아파트 매매가 } (P_{apt}) + C_{onetime}$$
$$L_{req} = C_{init} - \text{보유 현금 } (230,000,000\text{원})$$

#### (2) 월별 총 지출 ($E_{total}$)
$$E_{living} = \text{기존 13대 생활비}(2,390,708\text{원}) - \text{기존 월세}(311,000\text{원}) = 2,079,708\text{원}$$
$$E_{total} = \text{월 대출 원리금/상환액 } (P_{monthly}) + \text{아파트 관리비 } (M_{apt}) + \text{고정비 } (F_{post}) + E_{living}$$
*(※ 방서동 자이 30평 미만 관리비 기본값: 약 20만~25만 원 설정, 인터넷/주차비 고정비 포함)*

#### (3) 월 잔여 자금 ($R_{monthly}$)
$$R_{monthly} = \text{월 소득 } (3,300,000\text{원}) - E_{total}$$

#### (4) 대출 완납 예상 시점 ($T_{payoff}$)
- 월정 대출 상환액 $P_{monthly}$ + 반기별 보너스(2월/8월 교연비 각 500만 원, 1월/7월 특강비 각 100만 원) 투입 시 대출 잔액 $CurrentLoan \le 0$이 되는 총 경과 개월 수를 산출하여 `X년 Y개월`로 표시.

### 5.2 UI/UX 레이아웃 구조 설계 (`index4.html`)

```
+-----------------------------------------------------------------------+
|  🏠 방서동 자이 아파트 매입 & 종합 재무 시뮬레이터                  [☀️/🌙] |
+-----------------------------------------------------------------------+
|  [KPI 요약 카드 4종]                                                   |
|  1. 초기 필요 자금 (매매가+부대비용) | 2. 월 총 지출 (대출금+관리비+생활비) |
|  3. 월 잔여 자금 (소득-총지출)     | 4. 대출 완납 예상 시점 (X년 Y개월)    |
+-----------------------------------------------------------------------+
|  [슬라이더 & 입력 컨트롤 패널 (Glass Card)]                            |
|  - 아파트 매매가 (3.5억 / 3.75억 / 4.0억 / 사용자 지정 슬라이더)         |
|  - 대출 금리 (보금자리론 %, 신생아 특례 %, 전환 시점년)                   |
|  - 대출 상환 기간 (30년 / 35년 / 40년)                                 |
|  - 월 생활비 조정 (기존 생활비 207.97만 원 + 관리비/고정비 설정)            |
|  - 보너스 투입액 (2월/8월 교연비, 1월/7월 특강비 설정)                    |
+-----------------------------------------------------------------------+
|  [Chart.js 이중축 실시간 갱신 그래프 (Glass Card)]                     |
|  - 좌측 Y축: 월별 총 지출 & 보너스 원금 상환/미납 청산 막대             |
|  - 우측 Y축: 대출 잔액 감소 곡선                                       |
+-----------------------------------------------------------------------+
|  [상세 분석 탭 (Tabbed Views)]                                         |
|  - Tab 1: R1 매입 일회성 비용 전수 내역 (취득세, 중개비, 채권, 수리비 등) |
|  - Tab 2: R2 대출 상품 비교 (디딤돌/보금자리론 vs 일반 주담대)            |
|  - Tab 3: R3 월별 현금흐름 & 연도별 요약 스케줄 표                      |
|  - Tab 4: R4 매입 후 행정 절차 체크리스트 (기한, 담당기관, 필요서류)      |
+-----------------------------------------------------------------------+
```

---

## 6. 결론 및 개발 가이드라인

1. **디자인 톤 준수**: `index3.html`의 CSS 토큰, 글래스모피즘 효과(`backdrop-filter`, `.bg-blob`), 다크모드 전환 메커니즘을 동일하게 유지.
2. **Chart.js 이중축 완성도**: 좌측 축(월 지출 및 보너스 상환액)과 우측 축(대출 잔액)의 스케일을 독립 분리하고 `drawOnChartArea: false`로 렌더링 깔끔화.
3. **데이터 정합성 보장**: `8. 학기 중 예상 지출 보고서.md` 수치(소득 330만, 생활비 239.07만 중 월세 31.1만 제거, 보너스 교연비 1000만/특강비 200만)를 100% 반영.
4. **브라우저 싱글 파일 동작**: 별도 외부 서버 없이 `index4.html` 단일 파일로 CDN(Chart.js) 로딩하여 즉시 실행 가능하도록 구현.
