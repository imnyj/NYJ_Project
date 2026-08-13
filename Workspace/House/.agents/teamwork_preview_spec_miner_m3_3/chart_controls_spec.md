# Chart.js 이중축 그래프 및 인터랙티브 컨트롤 사양서 (Milestone 3: `index4.html`)

본 문서는 청주 방서동 자이 아파트 매입 종합 재무 시뮬레이터의 HTML 웹 애플리케이션(`ui/index4.html`) 제작을 위한 **Chart.js 이중축 그래프 및 인터랙티브 컨트롤 사양서**이다.

---

## 1. 개요 및 목적 (Overview)

- **대상 파일**: `/home/imnyj/Workspace/House/ui/index4.html`
- **디자인 스타일**: Glassmorphism (글래스모피즘), Dark/Light 테마 토글, 반응형 웹 레이아웃 (기존 `index3.html` 디자인 톤 및 기술 스택 승계)
- **주요 기능**:
  1. 아파트 가격, 보유 현금, 금리, 상환 기간, 보너스 상환 여부 조절용 인터랙티브 컨트롤
  2. 실시간 대출 상환 및 재무 현금흐름 재계산 엔진 (Client-side JavaScript Calculation Engine)
  3. 4대 주요 재무 KPI 지표 카드 (초기 필요 자금, 월 총 지출, 월 잔여 자금, 완납 예상 시점) 실시간 표출
  4. Chart.js 이중축(Dual-axis) 통합 그래프 (좌측 Stacked Bar: 월 지출/원금/이자/보너스, 우측 Line: 대출 잔액)
  5. Canvas 재사용 오류 및 메모리 누수 방지 차트 라이프사이클 관리

---

## 2. Features Discovered (기능 명세)

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| F1 | Preset Control | 프리셋 버튼 (3.5억/3.75억/4.0억) | 3개 아파트 가격 시나리오 빠른 선택 버튼 | 클릭 이벤트 (Button Click) | 프리셋 가격 설정, 슬라이더 동기화, UI 재계산 | 연속 클릭 시 이벤트 데바운싱 처리 | `ORIGINAL_REQUEST.md` §R5 |
| F2 | Slider Control | 매매가 연속 슬라이더 (3.0억~5.0억) | 1,000만 원 단위 미세 매매가 조절 슬라이더 | `input` 이벤트 (`value`: 300M~500M) | `#apt-price-val` 텍스트 갱신, 실시간 재계산 | 범위 초과 시 min/max 자동 보정 | `ORIGINAL_REQUEST.md` §R5 |
| F3 | Slider Control | 보유 현금 슬라이더 | 보유 자산 조절 슬라이더 (기본 2.3억 원, range: 1.0억~4.0억) | `input` 이벤트 (`value`: 100M~400M) | `#cash-val` 텍스트 갱신, 대출 필요금액 변경 | 현금 ≥ 매매가 시 대출금=0 처리 | `ORIGINAL_REQUEST.md` §R5 & Follow-up |
| F4 | Slider Control | 디딤돌대출 금리 슬라이더 | 신혼부부 디딤돌 금리 조절 (3.0% ~ 3.3%, step 0.05%) | `input` 이벤트 (`value`: 3.0~3.3) | `#rate-didimdol-val` 텍스트 갱신 | 소득 조건 초과 경고 문구 표시 | `ORIGINAL_REQUEST.md` §R2 & Follow-up |
| F5 | Slider Control | 시중은행 금리 슬라이더 | 시중은행/보금자리론 금리 조절 (3.8% ~ 4.5%, step 0.05%) | `input` 이벤트 (`value`: 3.8~4.5) | `#rate-commercial-val` 텍스트 갱신 | 금리 0% 이하 입력 불가 | `ORIGINAL_REQUEST.md` §R2 & Follow-up |
| F6 | Slider Control | 대출 상환 기간 슬라이더 | 대출 만기 조절 슬라이더 (10년 ~ 30년, step 1년) | `input` 이벤트 (`value`: 10~30) | `#term-val` 텍스트 갱신 | 30년 초과 제한 | `SCOPE.md` §M3-2 |
| F7 | Prepayment Structure | 보너스 조기상환 토글 및 월별 입력 | 연 1,000만 원 보너스(1월/7월 400만, 2월/8월 100만) 원금상환 적용/해제 | 토글 스위치 (`checked`), 월별 `number` 입력 | 보너스 상환 반영 및 완납기간 대폭 단축 | 토글 OFF 시 입력 폼 비활성화(disabled) | `ORIGINAL_REQUEST.md` §Follow-up |
| F8 | Chart Rendering | Chart.js 이중축 차트 (yLeft/yRight) | 좌측 축: 월지출 Stacked Bar, 우측 축: 대출잔액 Line (`drawOnChartArea: false`) | 시뮬레이션 배열 데이터 | Canvas 그래프 실시간 visual 렌더링 | 재초기화 시 이전 Chart 객체 `.destroy()` | `ORIGINAL_REQUEST.md` §R5 |
| F9 | Dynamic KPI | 4대 핵심 지표 카드 실시간 갱신 | 초기 필요 자금, 월 총 지출, 월 잔여 소득, 완납 시점 카드 | 시뮬레이션 결과 수치 | HTML 텍스트/색상 갱신 | 자금 부족 시 danger 스타일 바인딩 | `PROJECT.md` §Interface Contracts |
| F10 | Theme System | 글래스모피즘 다크/라이트 테마 | 배경 블롭 애니메이션 및 테마별 차트 컬러 동적 변경 | `#themeBtn` 클릭 | CSS 변수 변경, 차트 grid/font 색상 재적용 | 테마 변경 시 차트 텍스트 가독성 유지 | `index3.html` §Line 259-270 |

---

## 3. 인터랙티브 컨트롤 상세 사양 (Interactive Controls Spec)

### 3.1 아파트 매매가 선택 컨트롤 (Price Selector)
- **프리셋 버튼 3종**:
  - `3.5억 원` (`value="350000000"`)
  - `3.75억 원` (`value="375000000"`)
  - `4.0억 원` (`value="400000000"`)
  - UI 구성: `.price-preset-btn` 클래스, 선택된 버튼에는 `.active` (강조 배경 및 보더) 적용.
- **연속 슬라이더 (Price Slider)**:
  - ID: `#apt-price`
  - Attributes: `min="300000000"`, `max="500000000"`, `step="5000000"`, `value="375000000"` (또는 기본 3.5억)
  - Display ID: `#apt-price-val` (형식: `3억 7,500만 원` / `3.75억 원`)
- **동기화 로직 (Sync Logic)**:
  - 프리셋 버튼 클릭 시 슬라이더 `value` 변경 -> `calculate()` 함수 호출 -> 클릭된 프리셋 버튼에 `.active` 클래스 토글.
  - 슬라이더 직접 조작 시 슬라이더 값과 매칭되는 프리셋 버튼이 있으면 활성화, 없으면 프리셋 버튼의 `.active` 모두 해제.

### 3.2 보유 현금 슬라이더 (Cash Available Slider)
- **ID**: `#cash-reserve`
- **Attributes**: `min="100000000"`, `max="400000000"`, `step="5000000"`, `value="230000000"` (기본값 **2.3억 원**)
- **Display ID**: `#cash-reserve-val` (형식: `2억 3,000만 원`)
- **설명 데이터 표출**: `(본인 3천만 + 본인 부모님 1억 + 은비 부모님 1억)` 안내 서브 텍스트 명시.

### 3.3 대출 금리 슬라이더 (Interest Rate Sliders)
1. **디딤돌대출 금리 슬라이더 (Didimdol Rate)**:
   - ID: `#rate-didimdol`
   - Attributes: `min="3.0"`, `max="3.3"`, `step="0.05"`, `value="3.15"`
   - Display ID: `#rate-didimdol-val` (형식: `3.15%`)
   - 툴팁/안내: *"신혼부부 특례 디딤돌 금리 (소득 조건 준수 시 적용)"*
2. **시중은행/보금자리론 금리 슬라이더 (Commercial Rate)**:
   - ID: `#rate-commercial`
   - Attributes: `min="3.8"`, `max="4.5"`, `step="0.05"`, `value="4.00"`
   - Display ID: `#rate-commercial-val` (형식: `4.00%`)
   - 툴팁/안내: *"디딤돌 소득 초과 시 적용되는 일반 시중은행 금리"*

### 3.4 대출 상환 기간 슬라이더 (Loan Duration Slider)
- **ID**: `#loan-term`
- **Attributes**: `min="10"`, `max="30"`, `step="1"`, `value="30"` (기본값 **30년**)
- **Display ID**: `#loan-term-val` (형식: `30년`)

### 3.5 보너스 조기상환 토글 및 월별 입력 구조 (Bonus Prepayment Structure)
- **스위치 토글 (Toggle Switch)**:
  - ID: `#bonus-toggle`
  - Type: `<input type="checkbox" id="bonus-toggle" checked>`
  - Label: *"연간 보너스 원금 조기상환 적용 (연 1,000만 원)"*
- **월별 상환 입력 필드 (4개 월 분할 구조)**:
  - `1월 교연비/특강비 상환액`: ID `#bonus-jan`, default `4000000` (400만 원)
  - `2월 부가소득 상환액`: ID `#bonus-feb`, default `1000000` (100만 원)
  - `7월 교연비 상환액`: ID `#bonus-jul`, default `4000000` (400만 원)
  - `8월 부가소득 상환액`: ID `#bonus-aug`, default `1000000` (100만 원)
- **토글 동작**: `#bonus-toggle`이 `false` 일 경우, 4개 월별 입력 폼을 `disabled = true`로 변경하고 시뮬레이션 계산 시 보너스 상환액을 `0`으로 처리.

---

## 4. Chart.js 이중축 그래프 명세 (Dual-axis Chart Configuration)

### 4.1 차트 Canvas 구조 및 옵션

```html
<div class="chart-container" style="position: relative; height: 450px; width: 100%;">
    <canvas id="financialChart"></canvas>
</div>
```

### 4.2 데이터셋 구조 (Datasets Specifications)

Chart.js 설정 객체 구조는 다음과 같다:

```javascript
const chartConfig = {
    type: 'bar', // 기본 타입은 bar (스택형 막대)
    data: {
        labels: labelsArray, // 예: ['1년 1월', '1년 2월', ..., '15년 4월']
        datasets: [
            // [Dataset 0] 월 이자 지출 (Left Y-Axis - Stacked Bar)
            {
                label: '월 납입 이자',
                data: interestDataArray,
                type: 'bar',
                stack: 'monthlyExpense',
                backgroundColor: isDark ? 'rgba(239, 68, 68, 0.75)' : 'rgba(239, 68, 68, 0.65)',
                borderColor: '#ef4444',
                borderWidth: 1,
                yAxisID: 'yLeft',
                order: 3
            },
            // [Dataset 1] 월 정기 원금 상환 (Left Y-Axis - Stacked Bar)
            {
                label: '정기 원금 상환',
                data: principalDataArray,
                type: 'bar',
                stack: 'monthlyExpense',
                backgroundColor: isDark ? 'rgba(59, 130, 246, 0.75)' : 'rgba(59, 130, 246, 0.65)',
                borderColor: '#3b82f6',
                borderWidth: 1,
                yAxisID: 'yLeft',
                order: 2
            },
            // [Dataset 2] 보너스 조기 상환 (Left Y-Axis - Stacked Bar)
            {
                label: '보너스 원금 조기상환',
                data: bonusDataArray,
                type: 'bar',
                stack: 'monthlyExpense',
                backgroundColor: isDark ? 'rgba(16, 185, 129, 0.85)' : 'rgba(16, 185, 129, 0.75)',
                borderColor: '#10b981',
                borderWidth: 1,
                yAxisID: 'yLeft',
                order: 1
            },
            // [Dataset 3] 대출 잔액 곡선 (Right Y-Axis - Line Chart)
            {
                label: '대출 잔액 추세',
                data: balanceDataArray,
                type: 'line',
                borderColor: isDark ? '#fbbf24' : '#d97706',
                backgroundColor: isDark ? 'rgba(251, 191, 36, 0.1)' : 'rgba(217, 119, 6, 0.1)',
                fill: true,
                borderWidth: 3,
                pointRadius: 0,
                pointHoverRadius: 6,
                tension: 0.2,
                yAxisID: 'yRight',
                order: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false
        },
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: fontColor,
                    font: { family: 'Pretendard, -apple-system, sans-serif', weight: '600', size: 12 },
                    usePointStyle: true,
                    padding: 16
                }
            },
            tooltip: {
                backgroundColor: isDark ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)',
                titleColor: isDark ? '#f8fafc' : '#1f2937',
                bodyColor: isDark ? '#cbd5e1' : '#4b5563',
                borderColor: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: function(context) {
                        const label = context.dataset.label || '';
                        const val = context.raw || 0;
                        if (val === 0 && context.datasetIndex === 2) return null; // 보너스 0원인 달 숨김
                        return `${label}: ${formatFullKRW(val)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                stacked: true,
                grid: { color: gridColor },
                ticks: {
                    color: fontColor,
                    font: { size: 10 },
                    maxRotation: 0,
                    callback: function(val, index) {
                        // 30년(360개월) 장기 시뮬레이션 시 X축 라벨 1년 단위 표출
                        return index % 12 === 0 ? this.getLabelForValue(val) : '';
                    }
                }
            },
            yLeft: {
                type: 'linear',
                position: 'left',
                stacked: true, // 원금 + 이자 + 보너스 스택형 쌓기
                title: {
                    display: true,
                    text: '월 지출액 (원금+이자+보너스)',
                    color: fontColor,
                    font: { weight: 'bold', size: 11 }
                },
                ticks: {
                    color: fontColor,
                    callback: function(value) { return formatShortKRW(value); }
                },
                grid: { color: gridColor }
            },
            yRight: {
                type: 'linear',
                position: 'right',
                stacked: false,
                title: {
                    display: true,
                    text: '대출 잔액 (원)',
                    color: isDark ? '#fbbf24' : '#d97706',
                    font: { weight: 'bold', size: 11 }
                },
                ticks: {
                    color: isDark ? '#fbbf24' : '#d97706',
                    callback: function(value) { return formatShortKRW(value); }
                },
                // [필수] 우측 Y축 grid 가좌측 Y축 grid와 겹치지 않도록 깔끔하게 지움
                grid: { drawOnChartArea: false }
            }
        }
    }
};
```

---

### 4.3 동적 실시간 갱신 및 메모리 누수 / Canvas 재사용 오류 방지 로직

Chart.js에서 슬라이더 조작 시 `Canvas is already in use. Chart with ID 'X' must be destroyed before the canvas can be reused.` 에러가 발생하는 것을 방지하기 위해 다음 패턴을 준수해야 한다.

#### 방안 A: Chart 인스턴스 전역 관리 및 `.destroy()` 패턴 (추천)

```javascript
let chartInstance = null;

function renderChart(labels, interestData, principalData, bonusData, balanceData) {
    const canvas = document.getElementById('financialChart');
    if (!canvas) return;

    // 1. 기존 차트 인스턴스가 존재할 경우 안전하게 파괴 (Memory Leak 방지)
    if (chartInstance !== null) {
        chartInstance.destroy();
        chartInstance = null;
    }

    const ctx = canvas.getContext('2d');
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    
    // 2. 신규 차트 생성
    chartInstance = new Chart(ctx, getChartConfig(isDark, labels, interestData, principalData, bonusData, balanceData));
}
```

#### 방안 B: Data In-Place Update 패턴 (성능 극대화)

```javascript
function updateChartInPlace(labels, interestData, principalData, bonusData, balanceData) {
    if (!chartInstance) {
        renderChart(labels, interestData, principalData, bonusData, balanceData);
        return;
    }

    // 배열 참조 교체
    chartInstance.data.labels = labels;
    chartInstance.data.datasets[0].data = interestData;
    chartInstance.data.datasets[1].data = principalData;
    chartInstance.data.datasets[2].data = bonusData;
    chartInstance.data.datasets[3].data = balanceData;

    // 애니메이션 없이 즉시 갱신 (슬라이더 드래그 시 매끄러운 60fps 보장)
    chartInstance.update('none');
}
```

---

## 5. 실시간 KPI 지표 카드 연동 명세 (KPI Cards Specification)

시뮬레이션 계산 완료 시 상단 4개 지표 카드의 HTML 텍스트 및 스타일을 동적으로 업데이트한다:

| KPI 카드 | HTML Element ID | 산출 수식 / 로직 | 표시 형식 예시 |
|---|---|---|---|
| **1. 초기 필요 자금** | `#kpi-initial-cash` | `아파트 매매가 + R1 일회성 제반비용` | `3억 5,785만 원` |
| *(서브 텍스트)* | `#kpi-initial-diff` | `보유 현금(2.3억) - (초기 필요자금 - 대출금)` | `(보유현금 대비 +154만 원 여유)` |
| **2. 월 총 지출** | `#kpi-monthly-expenditure` | `월 대출 원리금 + 아파트 고정비(24만) + 생활비(207.97만)` | `2,845,210 원/월` |
| **3. 월 잔여 자금** | `#kpi-monthly-surplus` | `월 세후 소득(330만) - 월 총 지출` | `+454,790 원/월` |
| **4. 완납 예상 시점** | `#kpi-payoff-timeline` | `대출 잔액 ≤ 0 이 되는 월 수 (년, 개월 환산)` | `14년 8개월 (30년 대비 15년 4개월 단축)` |

### 수식 상세 요약:
1. **R1 일회성 비용 합계 ($C_{one\_time}$)**:
   - 취득세: $\text{Price} \times 1.1\% - 2,000,000\text{원 (생애최초 감면)}$
   - 중개수수료: $\text{Price} \times 0.44\%$
   - 법무사비: 50만 원 (3.5억) / 52만 원 (3.75억) / 55만 원 (4.0억)
   - 인지세: 15만 원
   - 국민주택채권 할인액: $\text{Price} \times 70\% \times 2.1\% \times 10\%$
   - 이사비: 150만 원
   - 수리/청소비: 200만 원
2. **월 고정 비대출 지출 ($E_{fixed}$)**:
   - 기존 13대 카테고리 생활비 (월세 31.1만 제외): $2,079,708$ 원
   - 아파트 고정비 (관리비 20만 + 주차비 1만 + TV/인터넷 3만): $240,000$ 원
   - 합계: $2,319,708$ 원
3. **월 대출 원리금 ($P_{monthly}$)**:
   - 디딤돌 / 시중은행 금리 기반 원리금 균등상환액 (CPM) 계산

---

## 6. Edge Cases & Error Handling (예외 처리 명세)

| # | Feature / Scenario | Specific Input Case | Observed & Specified Behavior |
|---|-------------------|---------------------|-------------------------------|
| E1 | 대출 불필요 케이스 | 보유 현금 $\ge$ 아파트 매매가 (예: 현금 3.5억, 매매가 3.5억) | 대출 필요금액 = 0원. KPI에 "대출 불필요" 표출. 그래프는 잔액 0선 표출, 이자/원금 0 처리. 경고 박스에 초록색 완료 메시지 표시. |
| E2 | 월 적자 (Negative Cash Flow) | 대출 원리금 + 고정 지출 > 월 소득 (330만 원) | 월 잔여 자금 카드가 붉은색(`var(--danger)`)으로 변경되며 `-XX만 원 (적자 발생)` 경고문 표출. |
| E3 | 금리 0% 입력 | Slider `rate = 0.0%` 입력 시 | 원리금 균등 상환 수식 분모 0 에러(`NaN`) 방지. `P / (years * 12)`로 단순 분할 상환 처리. |
| E4 | 보너스 원금 상환 시 잔액 초과 | 잔여 대출 잔액 < 보너스 투입액 (예: 잔액 200만 원, 보너스 400만 원) | 보너스 투입액을 잔여 대출 잔액으로 자동 자름 (`min(bonus, balance)`). 상환 완료 처리 후 시뮬레이션 종료. |
| E5 | 슬라이더 드래그 시 고빈도 재계산 | 슬라이더 조작 시 1초에 60회 이상 `input` 이벤트 발생 | `requestAnimationFrame` 또는 30ms 데바운싱(Debounce)을 적용하여 DOM 및 Chart.js 갱신 병목 현상 방지. |
| E6 | 다크모드 / 라이트모드 전환 | 사용자가 `#themeBtn` 클릭 시 | `toggleTheme()` 실행 시 body attribute 변경 후 차트 gridColor 및 fontColor를 다크모드에 맞춰 갱신 후 `chartInstance.update()` 실행. |
| E7 | 모바일/소형 화면 가로 스크롤 | 브라우저 너비 < 768px | 슬라이더 입력 폼 1열 배치, KPI 카드 2x2 배치, 차트 height 350px 조정으로 깨짐 방지. |

---

## 7. DOM 이벤트 바인딩 및 계산엔진 통합 구조

```javascript
// 이벤트 리스너 바인딩 통합 함수
function initEventListeners() {
    // 1. 매매가 프리셋 버튼
    document.querySelectorAll('.price-preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const price = parseInt(e.target.dataset.price);
            document.getElementById('apt-price').value = price;
            updatePresetActiveState(price);
            debouncedCalculate();
        });
    });

    // 2. 슬라이더 이벤트 (input)
    const sliders = ['apt-price', 'cash-reserve', 'rate-didimdol', 'rate-commercial', 'loan-term'];
    sliders.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', debouncedCalculate);
    });

    // 3. 보너스 상환 토글 및 월별 입력
    const bonusToggle = document.getElementById('bonus-toggle');
    if (bonusToggle) {
        bonusToggle.addEventListener('change', (e) => {
            const isEnabled = e.target.checked;
            ['bonus-jan', 'bonus-feb', 'bonus-jul', 'bonus-aug'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.disabled = !isEnabled;
            });
            debouncedCalculate();
        });
    }

    const bonusInputs = ['bonus-jan', 'bonus-feb', 'bonus-jul', 'bonus-aug'];
    bonusInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', debouncedCalculate);
    });
}
```

---

## 8. 결론 및 검증 요약 (Summary)

본 명세서는 `ORIGINAL_REQUEST.md`, `PROJECT.md`, `SCOPE.md` 및 기존 `index3.html`을 정밀 분석하여 작성되었으며, `index4.html` 구현 개발자 및 E2E 검증 시스템에서 참조할 수 있는 완벽한 사양을 제공한다.
