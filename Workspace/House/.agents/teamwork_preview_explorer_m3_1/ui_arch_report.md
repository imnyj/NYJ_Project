# 🎨 `ui/index4.html` UI/UX 아키텍처 및 기술 설계 보고서 (UI Architecture Report)

**작성일시**: 2026-08-12  
**작성자**: `teamwork_preview_explorer_m3_1`  
**대상 파일**: `/home/imnyj/Workspace/House/ui/index4.html`  
**관련 입출력 참조**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `SCOPE.md`, `survey_ui.md`, `index3.html`

---

## 1. 개요 및 아키텍처 목표 (Executive Summary & Architectural Goals)

본 보고서는 청주 방서동 자이 아파트(30평 미만, 3.5억/3.75억/4.0억 원) 매입 시 발생하는 일회성 부대비용 조사(R1), 대출 상품 비교(R2), 월별 현금흐름 시뮬레이션(R3), 행정/법률 체크리스트(R4)를 결합하여 실시간으로 계산 및 시각화를 수행하는 **인터랙티브 웹 시뮬레이터 (`index4.html`)의 최종 UI/UX 아키텍처 및 기술 명세서**입니다.

### 핵심 아키텍처 목표
1. **글래스모피즘 & 다크모드 시스템 완성**: `index3.html`에서 정립된 고급 글래스모피즘(Glassmorphism) CSS 토큰 및 다크모드 전환(`toggleTheme()`), 앰비언트 배경 블롭(Ambient Background Blobs)을 완벽하게 계승하고 확장합니다.
2. **실시간 4대 KPI 지표 계산 엔진**: 사용자의 슬라이더/입력 조절에 즉각 반응하여 (1) 초기 필요 자금 총액, (2) 월별 총 지출, (3) 월 잔여 자금, (4) 대출 완납 예상 시점을 렌더링합니다.
3. **Chart.js 이중축(Dual-Axis) 콤보 시각화**: 좌측 Y축(월 지출 및 보너스 상환액)과 우측 Y축(대출 잔액 곡선)을 독립 스케일링하여 `drawOnChartArea: false` 옵션과 함께 투명하고 깔끔한 그래프를 제공합니다.
4. **4대 상세 분석 탭 (Tabbed Views)**: R1(부대비용), R2(대출 비교), R3(월별/연별 현금흐름), R4(행정 절차) 내용을 단일 페이지 탭 구조로 제공하여 뛰어난 사용성을 제공합니다.
5. **독립 실행형 웹 애플리케이션**: 외부 빌드 도구 없이 CDN(Chart.js) 기반의 단일 HTML 파일로 즉시 렌더링되며 콘솔 에러 0건을 보장합니다.

---

## 2. 글래스모피즘 CSS 디자인 시스템 및 테마 스펙 (Glassmorphism & Theme Specs)

### 2.1 CSS Color Tokens & 디자인 변수 명세
`:root` 및 `[data-theme="dark"]` 선택자를 기반으로 라이트 모드와 다크 모드의 대비감 및 투명도를 정밀하게 제어합니다.

```css
:root {
    --bg: #f3f4f6;
    --glass-bg: rgba(255, 255, 255, 0.70);
    --glass-border: rgba(255, 255, 255, 0.45);
    --text-main: #1f2937;
    --text-muted: #4b5563;
    --accent: #4f46e5;
    --accent-hover: #4338ca;
    --danger: #ef4444;
    --success: #10b981;
    --warning: #f59e0b;
    --card-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.12);
    --input-bg: rgba(255, 255, 255, 0.35);
    --tab-active-bg: #4f46e5;
    --tab-active-text: #ffffff;
}

[data-theme="dark"] {
    --bg: #0f172a;
    --glass-bg: rgba(30, 41, 59, 0.70);
    --glass-border: rgba(255, 255, 255, 0.12);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #818cf8;
    --accent-hover: #6366f1;
    --danger: #ef4444;
    --success: #10b981;
    --warning: #f59e0b;
    --card-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
    --input-bg: rgba(0, 0, 0, 0.25);
    --tab-active-bg: #818cf8;
    --tab-active-text: #0f172a;
}
```

### 2.2 Ambient Background Blobs (배경 블롭 효과)
화면 뒤편에 배치되어 영롱한 은하수/오로라 느낌을 연출하는 3개의 원형 블롭 명세입니다.

```css
.bg-blob {
    position: fixed;
    border-radius: 50%;
    filter: blur(90px);
    z-index: -1;
    opacity: 0.65;
    transition: background 0.5s ease;
}
.blob1 { width: 450px; height: 450px; background: #ff9a9e; top: -120px; left: -100px; }
.blob2 { width: 550px; height: 550px; background: #a18cd1; bottom: -120px; right: -100px; }
.blob3 { width: 350px; height: 350px; background: #84fab0; top: 45%; left: 50%; transform: translate(-50%, -50%); }

[data-theme="dark"] .blob1 { background: #312e81; }
[data-theme="dark"] .blob2 { background: #831843; }
[data-theme="dark"] .blob3 { background: #064e3b; }
```

### 2.3 Glassmorphism 카드 스타일 (`.glass`)
```css
.glass {
    background: var(--glass-bg);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    box-shadow: var(--card-shadow);
    padding: 28px;
    margin-bottom: 24px;
    transition: background 0.3s ease, border-color 0.3s ease;
}
```

### 2.4 반응형 레이아웃 Breakpoints
- **Desktop (1024px 이상)**: 4열 KPI 카드, 3열 컨트롤 패널, 이중축 차트 550px 높이.
- **Tablet (768px ~ 1023px)**: 2열 KPI 카드, 2열 컨트롤 패널.
- **Mobile (767px 이하)**: 1열 KPI 카드, 1열 컨트롤 패널, 모바일 전용 수평 스크롤 표 및 차트 높이 400px.

---

## 3. `index4.html` HTML 레이아웃 구조 (DOM Structure & Component Breakdown)

```
+-----------------------------------------------------------------------------------+
|  Header Container                                                                 |
|  - Title: 🏠 청주 방서동 자이 아파트 종합 재무 시뮬레이터                         |
|  - Subtitle: 매입 제반비용 + 대출 상환 시뮬레이션 + 실시간 현금흐름 분석          |
|  - Floating Theme Switcher Button (#themeBtn)                                     |
+-----------------------------------------------------------------------------------+
|  KPI Summary Cards Grid (.stats-grid)                                             |
|  1. 초기 필요 자금 총액 (#total-initial-cost) — [매매가 + 부대비용]               |
|  2. 월별 총 지출 (#monthly-spending) — [대출 원리금 + 관리비 + 생활비]           |
|  3. 월 잔여 자금 (#remaining-income) — [월 소득 330만 원 - 월 총지출]              |
|  4. 대출 완납 예상 시점 (#payoff-timeline) — [X년 Y개월 (완납 연월)]              |
+-----------------------------------------------------------------------------------+
|  Control Panel (.glass)                                                           |
|  - Price Preset Buttons (3.5억 / 3.75억 / 4.0억) & Continuous Slider (#apt-price)  |
|  - Cash Available Slider (#cash) (기본값: 2.3억 원)                               |
|  - Loan Type & Interest Rate Sliders:                                             |
|    * 디딤돌/보금자리론 금리 (#didimdol-rate) (기본값: 3.0~3.3%)                  |
|    * 일반 시중은행 금리 (#commercial-rate) (기본값: 4.2%)                         |
|    * 대출 선택 탭/라디오 (#loan-type-select)                                      |
|  - Loan Term Slider (#loan-term) (10년~30년, 기본값: 30년)                        |
|  - Fixed Expenses Input:                                                          |
|    * 기존 생활비 (월세 31.1만 제거 반영 기본값 2,079,708원 고정/조정)            |
|    * 아파트 관리비 (#apt-maint) (기본 20만 원), 주차/인터넷 (#apt-etc) (기본 4만) |
|  - Bonus Prepayment Inputs:                                                       |
|    * 1월/7월 특강비 각 100만 원 (#jan-extra, #jul-extra)                           |
|    * 2월/8월 교연비 각 400만 원 (#feb-bonus, #aug-bonus) (연 1,000만 원 반영)      |
+-----------------------------------------------------------------------------------+
|  Chart.js Dual-Axis Graph Container (.glass)                                      |
|  - Legend & Axis Indicator Header                                                 |
|  - <canvas id="mainChart"></canvas>                                               |
+-----------------------------------------------------------------------------------+
|  4-Tab Detail Breakdown Section (.glass)                                          |
|  - Nav Tabs: [Tab 1: 부대비용 내역] [Tab 2: 대출상품 비교] [Tab 3: 현금흐름/표] [Tab 4: 행정절차] |
|  - Tab Content Panels (#tab-content-1 ~ #tab-content-4)                           |
+-----------------------------------------------------------------------------------+
```

---

## 4. JavaScript 계산 엔진 및 알고리즘 명세 (JS Calculation Engine & Formulas)

### 4.1 4대 실시간 KPI 지표 산출 공식

#### 1) 초기 필요 자금 총액 ($C_{init}$) 및 필요 대출금 ($L_{req}$)
- **매매가 ($P_{apt}$)**: 슬라이더 선택값 (3.5억 / 3.75억 / 4.0억 등)
- **일회성 부대비용 ($C_{onetime}$)**:
  $$\text{취득세}(T_{acq}) = P_{apt} \times 1.1\% - 2,000,000\text{원 (생애최초 감면)}$$
  $$\text{중개수수료}(F_{broker}) = P_{apt} \times 0.4\% \times 1.1 (\text{VAT 포함})$$
  $$\text{법무사비}(F_{legal}) = 550,000\text{원}, \quad \text{인지세}(T_{stamp}) = 150,000\text{원}$$
  $$\text{채권할인실부담}(F_{bond}) = P_{apt} \times 0.7 \times 2.1\% \times 10\%$$
  $$\text{이사비}(F_{move}) = 1,500,000\text{원}, \quad \text{수리/청소비}(F_{repair}) = 2,000,000\text{원}$$
  $$\text{대출 인지세}(F_{loan\_stamp}) = 75,000\text{원 (차주 부담 50\%)}$$
  $$C_{onetime} = T_{acq} + F_{broker} + F_{legal} + T_{stamp} + F_{bond} + F_{move} + F_{repair} + F_{loan\_stamp}$$
- **초기 필요 자금 총액 ($C_{init}$)**:
  $$C_{init} = P_{apt} + C_{onetime}$$
- **실제 필요 대출금 ($L_{req}$)**:
  $$L_{req} = C_{init} - \text{보유 현금 }(230,000,000\text{원})$$

#### 2) 월별 총 지출 ($E_{total}$)
- **월 대출 상환액 ($P_{monthly}$)**: 사용자가 지정한 월 상환 여력 기본값 **500,000원** (또는 원리금 균등 상환액 선택 가능)
- **기존 생활비 ($E_{living}$)**: 2,390,708원 - 월세 311,000원 = **2,079,708원**
- **신규 아파트 고정비 ($E_{apt\_fixed}$)**: 관리비(200,000원) + 주차비/인터넷(40,000원) = **240,000원**
- **월 총 지출 ($E_{total}$)**:
  $$E_{total} = P_{monthly} + E_{living} + E_{apt\_fixed} = 500,000 + 2,079,708 + 240,000 = 2,819,708\text{원}$$

#### 3) 월 잔여 자금 ($R_{monthly}$)
- **월 소득 ($I_{monthly}$)**: **3,300,000원** (세후)
- **월 잔여 자금 ($R_{monthly}$)**:
  $$R_{monthly} = I_{monthly} - E_{total} = 3,300,000 - 2,819,708 = 480,292\text{원}$$

#### 4) 대출 완납 예상 시점 ($T_{payoff}$)
- 매월 월 상환금 50만 원 투입 + 1월/7월 특강비(각 100만), 2월/8월 교연비(각 400만) 등 **연 1,000만 원 원금 보너스 상환** 반영 시 대출 잔액 $CurrentLoan \le 0$이 되는 총 개월 수 계산.

---

### 4.2 대출 상환 시뮬레이션 핵심 루프 (JS Implementation Spec)

```javascript
function runAmortizationSimulation(params) {
    let currentLoan = params.loanAmount;
    let accumulatedShortfall = 0;
    let totalInterestPaid = 0;
    let totalPrincipalPaid = 0;
    
    const monthlyPayment = params.monthlyPayment; // 기본 50만 원
    const annualRate = params.interestRate;       // 예: 0.033 (3.3%)
    const monthlyRate = annualRate / 12;
    
    const chartLabels = [];
    const interestData = [];
    const bonusPrincipalData = [];
    const bonusShortfallData = [];
    const balanceData = [];
    const tableRows = [];

    const maxMonths = params.maxYears * 12;
    let finishMonth = -1;

    for (let m = 0; m < maxMonths; m++) {
        if (currentLoan <= 0) {
            if (finishMonth === -1) finishMonth = m;
            break;
        }

        const calMonth = ((params.startMonth - 1 + m) % 12) + 1;
        const yearNum = Math.floor((params.startMonth - 1 + m) / 12) + 1;

        // 1. 월 발생 이자
        const monthlyInterest = currentLoan * monthlyRate;
        let interestPaid = 0;
        let principalPaid = 0;
        let shortfall = 0;

        // 2. 월정 납입 처리
        if (monthlyPayment >= monthlyInterest) {
            interestPaid = monthlyInterest;
            principalPaid = monthlyPayment - monthlyInterest;
            currentLoan -= principalPaid;
        } else {
            interestPaid = monthlyPayment;
            shortfall = monthlyInterest - monthlyPayment;
            accumulatedShortfall += shortfall;
        }

        totalInterestPaid += interestPaid;
        totalPrincipalPaid += principalPaid;

        // 3. 정기 보너스 투입 (Follow-up 요구조건 100% 반영)
        // 1월/7월: 특강비 100만 원 / 2월/8월: 교연비 400만 원 (연 총 1,000만 원)
        let bonusAmount = 0;
        if (calMonth === 1 || calMonth === 7) bonusAmount = params.bonusJanJul; // 1,000,000
        if (calMonth === 2 || calMonth === 8) bonusAmount = params.bonusFebAug; // 4,000,000

        let bonusPrincipalPaid = 0;
        let bonusShortfallCleared = 0;

        if (bonusAmount > 0) {
            // 3-1. 미납이자 우선 변제
            if (accumulatedShortfall > 0) {
                if (bonusAmount >= accumulatedShortfall) {
                    bonusShortfallCleared = accumulatedShortfall;
                    totalInterestPaid += accumulatedShortfall;
                    bonusAmount -= accumulatedShortfall;
                    accumulatedShortfall = 0;
                } else {
                    bonusShortfallCleared = bonusAmount;
                    totalInterestPaid += bonusAmount;
                    accumulatedShortfall -= bonusAmount;
                    bonusAmount = 0;
                }
            }
            // 3-2. 잔여분 원금 직접 상환
            if (bonusAmount > 0) {
                if (bonusAmount > currentLoan) bonusAmount = currentLoan;
                currentLoan -= bonusAmount;
                totalPrincipalPaid += bonusAmount;
                bonusPrincipalPaid = bonusAmount;
            }
        }

        // 4. 연말 미납이자 자본화 (매 12개월 차)
        if ((m + 1) % 12 === 0 && accumulatedShortfall > 0) {
            currentLoan += accumulatedShortfall;
            accumulatedShortfall = 0;
        }

        if (currentLoan < 0) currentLoan = 0;

        // 차트 데이터 기록
        const labelStr = `${yearNum}년 ${calMonth}월`;
        chartLabels.push(labelStr);
        interestData.push(Math.round(monthlyInterest));
        bonusPrincipalData.push(Math.round(bonusPrincipalPaid));
        bonusShortfallData.push(Math.round(bonusShortfallCleared));
        balanceData.push(Math.round(currentLoan));

        // 표 데이터 기록
        tableRows.push({
            label: labelStr,
            payment: monthlyPayment,
            interest: monthlyInterest,
            principal: principalPaid,
            bonusPaid: bonusPrincipalPaid + bonusShortfallCleared,
            shortfall: accumulatedShortfall,
            balance: currentLoan
        });
    }

    return {
        finishMonth: finishMonth,
        totalInterestPaid: totalInterestPaid,
        totalPrincipalPaid: totalPrincipalPaid,
        chartLabels: chartLabels,
        interestData: interestData,
        bonusPrincipalData: bonusPrincipalData,
        bonusShortfallData: bonusShortfallData,
        balanceData: balanceData,
        tableRows: tableRows
    };
}
```

---

### 4.3 Chart.js 이중축(Dual-Axis) 명세

```javascript
let mainChart = null;

function renderChart(data) {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    const fontColor = isDark ? '#94a3b8' : '#4b5563';

    if (mainChart) mainChart.destroy();
    const ctx = document.getElementById('mainChart').getContext('2d');

    mainChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.chartLabels,
            datasets: [
                {
                    label: '보너스 원금상환',
                    data: data.bonusPrincipalData,
                    type: 'bar',
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1,
                    yAxisID: 'yLeft',
                    order: 3
                },
                {
                    label: '보너스 미납이자 청산',
                    data: data.bonusShortfallData,
                    type: 'bar',
                    backgroundColor: 'rgba(245, 158, 11, 0.75)',
                    borderColor: 'rgba(245, 158, 11, 1)',
                    borderWidth: 1,
                    yAxisID: 'yLeft',
                    order: 3
                },
                {
                    label: '월 발생 이자',
                    data: data.interestData,
                    type: 'line',
                    borderColor: isDark ? '#f87171' : '#dc2626',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.3,
                    yAxisID: 'yLeft',
                    order: 1
                },
                {
                    label: '대출 잔액',
                    data: data.balanceData,
                    type: 'line',
                    borderColor: isDark ? '#fbbf24' : '#d97706',
                    backgroundColor: isDark ? 'rgba(251, 191, 36, 0.08)' : 'rgba(217, 119, 6, 0.08)',
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 0,
                    tension: 0.3,
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
                        color: fontColor,
                        callback: function(val, index) {
                            return index % 6 === 0 ? this.getLabelForValue(val) : '';
                        }
                    },
                    grid: { color: gridColor }
                },
                yLeft: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: '월 이자 / 보너스 (원)', color: fontColor },
                    ticks: { color: fontColor, callback: v => formatKRW(v) + '원' },
                    grid: { color: gridColor }
                },
                yRight: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: '대출 잔액 (원)', color: isDark ? '#fbbf24' : '#d97706' },
                    ticks: { color: isDark ? '#fbbf24' : '#d97706', callback: v => formatKRW(v) + '원' },
                    grid: { drawOnChartArea: false } // 이중축 중첩 그리드 방지
                }
            }
        }
    });
}
```

---

## 5. 상세 분석 탭 (Tabbed Views) 세부 구조 설계

### Tab 1: R1 매입 일회성 비용 전수조사 탭
3.5억 / 3.75억 / 4.0억 3개 시나리오별 일회성 부대비용을 비교표 형태로 제공합니다.

| 비용 항목 | 3.5억 원 시나리오 | 3.75억 원 시나리오 | 4.0억 원 시나리오 | 산출 근거 및 규정 |
| :--- | :--- | :--- | :--- | :--- |
| **취득세 (본세+지방교육세)** | 185만 원 | 212.5만 원 | 240만 원 | 1.1% 적용 (-생애최초 200만 원 감면) |
| **중개수수료 (VAT 포함)** | 154만 원 | 165만 원 | 176만 원 | 법정 상한요율 0.4% + VAT 10% |
| **법무사 등기대행료** | 55만 원 | 55만 원 | 55만 원 | 소유권 이전 등기 표준 수수료 |
| **인지세 (매매/대출)** | 22.5만 원 | 22.5만 원 | 22.5만 원 | 매매 인지세 15만 + 대출 인지세 7.5만 |
| **국민주택채권 할인액** | 약 51.5만 원 | 약 57.4만 원 | 약 64.4만 원 | 시가표준액(70%) × 2.1% × 할인율 10% |
| **이사비** | 150만 원 | 150만 원 | 150만 원 | 포장이사 기준 평균 비용 |
| **기본 수리/청소비** | 200만 원 | 200만 원 | 200만 원 | 입주 청소 및 기본 도배/보수 |
| **총 부대비용** | **785.5만 원** | **834.9만 원** | **880.4만 원** | **매매가 외 초기 추가 필요 자금** |

### Tab 2: R2 대출 상품 비교 탭
디딤돌/보금자리론과 일반 시중은행 주택담보대출을 상세 비교하고, 규제 완화 시나리오와 소득 요건 제약을 명시합니다.

- **디딤돌대출 (신혼부부 특례)**:
  - **금리**: 연 3.0% ~ 3.3%
  - **한도**: 최대 4억 원 (LTV 70% 이내)
  - **자격 요건 분석**: 부부합산 추정 연소득 약 1.3억~1.5억 원으로 현행 소득요건(8,500만 원 이하) 초과 가능성 높음. 단, 정부 디딤돌 규제 완화 및 정책 변경 시 적용 가능성을 시뮬레이터 슬라이더로 조절 가능.
- **일반 시중은행 주택담보대출**:
  - **금리**: 연 3.8% ~ 4.5% (주요 시중은행 5년 고정 혼합형 기준)
  - **대출 부대비용**: 근저당 설정비(은행 부담), 인지세(7.5만 원 차주 부담), HF/HUG 보증료(연 0.05%~0.1%).

### Tab 3: R3 월별 현금흐름 & 연도별 상환 표 탭
- 초기 1년간의 월별 현금흐름(소득 330만, 대출 상환액 50만, 고정 생활비 207.97만, 관리비 24만, 잔여 48만)을 표로 출력.
- 이후 연도별 대출 잔액 감소 및 완납 예상 시점 표 출력.

### Tab 4: R4 매입 후 행정/법률 절차 체크리스트 탭
시간 순서에 따른 체크리스트와 담당 기관, 기한, 필요 서류를 카드형 체크리스트 UI로 배치.

1. **잔금 납부 & 영수증 수령**: 잔금 당일 / 부동산 중개업소 / 매매계약서, 잔금 이체확인서
2. **소유권 이전 등기**: 잔금일 당일 / 관할 등기소(법무사 대행) / 매매계약서, 주민등록초본, 인감증명서
3. **취득세 신고 및 납부**: 잔금일로부터 60일 이내 / 관할 구청 세무과 / 취득세 신고서, 매매계약서 사본
4. **전입신고 & 확정일자**: 입주 당일 / 주민센터 또는 정부24 / 신분증, 임대차/매매계약서
5. **재산세 안내 확인**: 매년 6월 1일 기준 소유자 부과 / 구청 세무과 / 과세물건 확인

---

## 6. 검증 및 수용 기준 (Verification Criteria & Acceptance Standard)

| 검증 항목 | 검증 방법 및 기준 | 결과 목표 |
| :--- | :--- | :--- |
| **HTML/CSS 구조 검증** | Chromium 브라우저 렌더링 및 CSS 변수 다크모드 적용 확인 | 0 Error, Perfect Glassmorphism |
| **계산 로직 정확성** | 3.5억/3.75억/4.0억 슬라이더 변경 시 부대비용 및 완납 시점 실시간 반영 | 100% 정합성 |
| **이중축 그래프 동작** | Left Y-axis(월지출/보너스) & Right Y-axis(잔액) 독립 스케일링 | `drawOnChartArea: false` 적용 |
| **보너스 상환 로직** | 연 1,000만 원 보너스 투입 시 미납이자 우선 변제 후 원금 차감 | 알고리즘 100% 일치 |

---
*본 명세서는 `index4.html` 구현 담당 에이전트가 완벽히 준수할 수 있도록 설계되었습니다.*
