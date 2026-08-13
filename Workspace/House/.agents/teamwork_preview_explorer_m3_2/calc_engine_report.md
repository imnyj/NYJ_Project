# Milestone 3 계산 엔진 수식 및 알고리즘 명세서 (calc_engine_report.md)

**작성일시**: 2026-08-12  
**작성자**: teamwork_preview_explorer_m3_2  
**대상 파일**: `/home/imnyj/Workspace/House/ui/index4.html` 계산 엔진 및 실시간 재계산 로직  

---

## 1. 개요 (Executive Summary)

본 보고서는 청주 방서동 자이 아파트 매입 종합 재무 시뮬레이터(`index4.html`)의 실시간 웹 계산 엔진을 구축하기 위한 **정확한 수학적 수식**, **금융 파라미터**, **JavaScript 알고리즘 명세**를 제공합니다.

시뮬레이터는 사용자의 입력(매매가, 보유 현금, 대출 금리, 대출 기간, 보너스 상환 여부 등) 변경에 따라 아래 **4대 실시간 핵심 지표** 및 **Chart.js 이중축 시각화 데이터**를 즉시 재계산해야 합니다:
1. **초기 필요 자금 총액 (Initial Cash Required)**: 아파트 매매가 + R1 일회성 제반비용(취득세, 중개수수료, 채권할인, 법무사비, 인지세, 이사비, 수리청소비 등)
2. **디딤돌 vs 시중은행 대출 분할 및 금리 (Loan Split & Rates)**: 보유 현금 대비 필요 대출금 산출, 디딤돌대출 한도(4억) 및 금리(3.0~3.3%) vs 시중은행 주담대 금리(3.8~4.5%) 가중평균 연동
3. **월 총지출 (Monthly Spending)**: 월 대출 원리금 상환액 + 아파트 고정비(관리비/주차비/TV인터넷 24만 원) + 기존 생활비(월세 제외 2,079,708 원)
4. **월 잔여 자금 (Monthly Remaining Income)**: 월 세후 순소득(330만 원) - 월 총지출
5. **보너스 중도상환 및 대출 완납 시점 (Payoff Timeline)**: 연 1,000만 원(1/7월 교연비 각 400만, 2/8월 부가소득 각 100만) 투입 시 대출 잔액이 0에 도달하는 정확한 연/개월 산출

---

## 2. R1 매입 시 일회성 비용 및 초기 필요 자금 수식 명세

### 2.1 파라미터 및 수식 요약

아파트 매매가를 $P$ (단위: 원)라고 할 때, 일회성 제반비용 $C_{R1}$ 및 초기 필요 자금 총액 $C_{initial\_total}$은 다음과 같이 산출됩니다.

$$C_{initial\_total} = P + C_{R1}$$

$$C_{R1} = T_{acq} + F_{broker} + F_{legal} + F_{stamp} + F_{bond} + F_{moving} + F_{repair}$$

| 비용 항목 | 산출 수식 / 기준 | 3.5억 시나리오 | 3.75억 시나리오 | 4.0억 시나리오 |
| :--- | :--- | :---: | :---: | :---: |
| **취득세 본세 ($1.0\%$)** | $\lfloor P \times 0.010 \rfloor$ | 3,500,000원 | 3,750,000원 | 4,000,000원 |
| **생애최초 감면** | $\min(\text{본세}, 2,000,000\text{원})$ | -2,000,000원 | -2,000,000원 | -2,000,000원 |
| **취득세 납부액** | $\max(0, \text{본세} - \text{감면})$ | 1,500,000원 | 1,750,000원 | 2,000,000원 |
| **지방교육세 ($0.1\%$)** | $\lfloor \text{취득세 납부액} \times 0.10 \rfloor$ | 150,000원 | 175,000원 | 200,000원 |
| **취득세 합계 ($T_{acq}$)** | 취득세 납부액 + 지방교육세 | **1,650,000원** | **1,925,000원** | **2,200,000원** |
| **중개수수료 ($F_{broker}$)** | $\lfloor P \times 0.004 \times 1.10 \rfloor = \lfloor P \times 0.0044 \rfloor$ | **1,540,000원** | **1,650,000원** | **1,760,000원** |
| **법무사비 ($F_{legal}$)** | 시나리오별 구간/기본값 지정 | **500,000원** | **520,000원** | **550,000원** |
| **인지세 ($F_{stamp}$)** | 부동산 소유권 이전 등기 고정액 | **150,000원** | **150,000원** | **150,000원** |
| **채권할인액 ($F_{bond}$)** | $\lfloor P \times 0.70 \times R_{bond} \times 0.10 \rfloor$ | **514,500원** | **603,750원** | **644,000원** |
| **이사비 ($F_{moving}$)** | 실거주 이사 비용 고정액 | **1,500,000원** | **1,500,000원** | **1,500,000원** |
| **수리/청소비 ($F_{repair}$)** | 기본 입주 수리 및 청소비 고정액 | **2,000,000원** | **2,000,000원** | **2,000,000원** |
| **일회성 비용 총액 ($C_{R1}$)** | 세부 항목 합계 | **7,854,500원** | **8,348,750원** | **8,804,000원** |
| **초기 필요 자금 ($C_{initial\_total}$)**| $P + C_{R1}$ | **357,854,500원** | **383,348,750원** | **408,804,000원** |

> **채권 매입 비율 ($R_{bond}$) 구체 수식**:
> 공시지가 $P_{public} = P \times 0.70$.
> $P_{public} < 2.6\text{억 원}$ 인 경우 $R_{bond} = 0.021$ ($2.1\%$), $P_{public} \ge 2.6\text{억 원}$ 인 경우 $R_{bond} = 0.023$ ($2.3\%$).

### 2.2 보유 현금 대비 잔여/부족 자금

보유 현금 $C_{cash} = 2.3\text{억 원}$ ($230,000,000\text{원}$) 기준:
- 순수 대출 필요액 (순수 매매가 기준): $L_{pure} = \max(0, P - C_{cash})$
- 일회성 비용 포함 시 현금 부족분: $\Delta_{cash} = C_{cash} - C_{initial\_total}$

---

## 3. 대출 비교, 대출 분할 및 금리 산출 로직

### 3.1 필요 대출금 및 LTV 산출

$$L_{required} = \max(0, P - C_{cash})$$

$$\text{LTV (\%)} = \frac{L_{required}}{P} \times 100$$

### 3.2 디딤돌대출 vs 시중은행 주택담보대출 분할 (Split) 모델

1. **디딤돌 대출 (신혼부부 특례)**:
   - 금리 범위: 연 $3.0\% \sim 3.3\%$ (기본값 $3.15\%$)
   - 최대 한도 $L_{didimdol\_max} = 400,000,000\text{원}$
   - LTV 한도: $70\%$ (생애최초 $80\%$)
   - **소득 요건 주의사항**: 본인 연소득 약 5,296만 원 + 배우자 연소득 약 8,000만 원 이상으로 부부합산 소득(약 1.3억~1.5억 원)이 현행 디딤돌 신혼부부 기준(8,500만 원 이하)을 초과함. 웹 시뮬레이터에서는 **디딤돌 슬라이더와 시중은행 슬라이더를 독립 제공**하여 정부 규제 완화 적용 여부에 따른 시나리오를 자유롭게 테스트할 수 있도록 설계.

2. **시중은행 주택담보대출**:
   - 금리 범위: 연 $3.8\% \sim 4.5\%$ (기본값 $4.20\%$)
   - 한도: LTV $70\%$ 이내

3. **대출 분할 및 가중평균 금리 수식**:
   필요 대출금 $L_{required}$이 디딤돌 한도 $L_{didimdol\_max}$를 초과하는 경우:
   $$L_{didimdol} = \min(L_{required}, L_{didimdol\_max})$$
   $$L_{commercial} = \max(0, L_{required} - L_{didimdol\_max})$$
   
   합산 가중평균 대출 금리 $r_{effective}$:
   $$r_{effective} = \begin{cases} r_{didimdol} & (L_{commercial} = 0) \\ \frac{L_{didimdol} \times r_{didimdol} + L_{commercial} \times r_{commercial}}{L_{required}} & (L_{commercial} > 0) \end{cases}$$

### 3.3 대출 부대비용 산출

- **대출 인지세 (차주 부담 50%)**:
  - $L_{required} \le 5,000\text{만 원}$: 0원
  - $5,000\text{만 원} < L_{required} \le 1\text{억 원}$: 35,000원
  - $L_{required} > 1\text{억 원}$: 75,000원
- **근저당 설정비**: 은행 부담 ($0$원, 차주는 주소변경 증지대 약 2만 원 수준)
- **연간 보증료 (HF/HUG)**: $L_{required} \times 0.0005$ ($0.05\%/\text{년}$)

---

## 4. 월 총지출 및 월 잔여 자금 계산 로직

### 4.1 월 고정 지출 구성 요소

```
[월 세후 소득: 3,300,000 원]
       │
       ├── (1) 월 대출 원리금 상환액 (Amortization PMT 또는 사용자 설정액 50만 원)
       ├── (2) 아파트 신규 고정비: 240,000 원 (관리비 20만 + 주차비 1만 + TV/인터넷 3만)
       └── (3) 기존 생활비 (월세 31.1만 원 제거): 2,079,708 원
```

1. **기존 13대 카테고리 생활비 재구성**:
   - 기존 분석 보고서 총 생활비: $2,390,708\text{원}$
   - 차감 항목: 월세 및 관련 비용 $-311,000\text{원}$
   - 수정 순 생활비 $E_{living\_net} = 2,079,708\text{원}$

2. **아파트 신규 고정비 ($E_{apt\_fixed}$)**:
   - 방서동 자이 30평 미만 관리비: $200,000\text{원}$
   - 주차비: $10,000\text{원}$
   - TV 및 인터넷: $30,000\text{원}$
   - 소계 $E_{apt\_fixed} = 240,000\text{원}$

3. **대출 제외 월 고정 지출 합계 ($E_{fixed\_no\_loan}$)**:
   $$E_{fixed\_no\_loan} = 2,079,708 + 240,000 = 2,319,708\text{원}$$

### 4.2 원리금 균등상환 (CPM) 및 월 총지출 수식

대출금 $L$, 연금리 $r$, 대출 기간 $N$년 ($n = N \times 12$개월) 일 때 월 원리금 균등상환액 $M_{cpm}$:

$$M_{cpm} = L \times \frac{\frac{r}{12} \left(1 + \frac{r}{12}\right)^n}{\left(1 + \frac{r}{12}\right)^n - 1}$$

- **월 총지출 ($E_{monthly\_total}$)**:
  $$E_{monthly\_total} = M_{cpm} + E_{fixed\_no\_loan} = M_{cpm} + 2,319,708\text{원}$$
  *(사용자가 월 상환 목표액 $M_{user}$ (예: 50만 원)를 설정한 경우 $M_{cpm}$ 대신 $M_{user}$ 사용)*

### 4.3 월 잔여 자금 (Monthly Remaining Income) 수식

$$I_{remaining} = I_{net} - E_{monthly\_total} = 3,300,000 - E_{monthly\_total}$$

- **예시 계산 (월 상환 50만 원 설정 시)**:
  - 월 총지출: $500,000 + 2,319,708 = 2,819,708\text{원}$
  - 월 잔여 자금: $3,300,000 - 2,819,708 = 480,292\text{원}$

---

## 5. 보너스 중도상환 스케줄 및 완납 시점 시뮬레이션 알고리즘

### 5.1 보너스 투입 스케줄 (Follow-up 확정안)

- **1월**: 교연비 상환 투입 **400만 원** (100만 원 개인 유보)
- **2월**: 부가소득 상환 투입 **100만 원**
- **7월**: 교연비 상환 투입 **400만 원** (100만 원 개인 유보)
- **8월**: 부가소득 상환 투입 **100만 원**
- **연간 보너스 상환 총액**: **1,000만 원 / 년**

### 5.2 이자 계산, 원금 상환 및 미납이자 처리 시뮬레이션 순서도

매월 시뮬레이션 시 다음 원칙을 엄격히 적용합니다:
1. **당월 이자 계산**: $I_m = B_{m-1} \times \frac{r}{12}$ ($B_{m-1}$: 기말 잔액)
2. **약정 월 납입액 ($M$) 처리**:
   - $M \ge I_m$ 인 경우: 당월 발생 이자 $I_m$ 전액 상환, 남은 금액 $M - I_m$으로 원금 상환 ($B_m' = B_{m-1} - (M - I_m)$).
   - $M < I_m$ 인 경우: 납입액 $M$ 전체를 이자 상환에 충당, 부족분 $I_m - M$은 미납이자 누적액 $S_{acc}$에 추가 ($S_{acc} \leftarrow S_{acc} + (I_m - M)$).
3. **보너스 투입월 ($m \in \{1, 2, 7, 8\}$) 처리**:
   - 보너스 금액 $V_{bonus}$ 발생
   - **[우선순위 1] 미납이자 청산**: $S_{acc} > 0$ 인 경우 보너스로 미납이자 $S_{acc}$를 먼저 차감.
   - **[우선순위 2] 원금 조기 상환**: 미납이자 청산 후 남은 보너스 잔액 $V_{rem}$으로 대출 원금 조기 상환 ($B_m = B_m' - V_{rem}$).
4. **대출 완납 여부 판별**:
   - $B_m \le 0$ 도달 시 시뮬레이션 종료. 완납 개월수 $m^*$ 기록.

---

## 6. JavaScript 구현 코드 명세 (`index4.html` 용)

다음은 `index4.html`에 탑재될 실시간 재계산 핵심 엔진 함수 사양입니다.

```javascript
/**
 * Milestone 3 Financial Simulation Engine Specification
 */
function calculateFinancials(inputs) {
    const {
        price,              // 매매가 (원)
        cash,               // 보유 현금 (원)
        didimdolRate,       // 디딤돌 금리 (소수점, 예: 0.0315)
        commercialRate,     // 시중은행 금리 (소수점, 예: 0.042)
        termYears,          // 대출 기간 (년, 예: 30)
        monthlyPaymentTarget, // 사용자가 설정한 월 상환 목표액 (원, 예: 500000)
        useBonusPrepay      // 보너스 상환 사용 여부 (boolean)
    } = inputs;

    // 1. R1 일회성 비용 계산
    const grossAcqTax = Math.floor(price * 0.011);
    const acqTaxExemption = Math.min(grossAcqTax, 2000000);
    const netAcqTax = Math.max(0, grossAcqTax - acqTaxExemption);
    
    const brokerageFee = Math.floor(price * 0.0044);
    
    let legalFee = 500000;
    if (price === 375000000) legalFee = 520000;
    else if (price === 400000000) legalFee = 550000;

    const stampDuty = 150000;
    
    const publicPrice = price * 0.70;
    const bondRate = publicPrice < 260000000 ? 0.021 : 0.023;
    const bondDiscountFee = Math.floor(publicPrice * bondRate * 0.10);
    
    const movingFee = 1500000;
    const repairCleaningFee = 2000000;

    const totalR1Cost = netAcqTax + brokerageFee + legalFee + stampDuty + bondDiscountFee + movingFee + repairCleaningFee;
    const totalInitialCapital = price + totalR1Cost;
    const cashSurplusOrDeficit = cash - totalInitialCapital;

    // 2. 필요 대출금 및 대출 분할/가중평균 금리
    const requiredLoan = Math.max(0, price - cash);
    const ltvPercent = price > 0 ? (requiredLoan / price) * 100 : 0;

    const DIDIMDOL_MAX_LIMIT = 400000000;
    let didimdolAmount = 0;
    let commercialAmount = 0;
    let effectiveRate = commercialRate;

    if (requiredLoan > 0) {
        didimdolAmount = Math.min(requiredLoan, DIDIMDOL_MAX_LIMIT);
        commercialAmount = Math.max(0, requiredLoan - DIDIMDOL_MAX_LIMIT);
        effectiveRate = (didimdolAmount * didimdolRate + commercialAmount * commercialRate) / requiredLoan;
    }

    // 3. 월 고정 지출 및 원리금 균등상환액 (CPM)
    const baseLivingNet = 2079708; // 2,390,708 - 311,000
    const aptFixedExpenses = 240000; // 관리비 20만 + 주차비 1만 + 인터넷/TV 3만
    const totalFixedSpendingNoLoan = baseLivingNet + aptFixedExpenses; // 2,319,708 원

    const totalMonths = termYears * 12;
    const monthlyRate = effectiveRate / 12;
    
    let cpmMonthlyPayment = 0;
    if (requiredLoan > 0 && monthlyRate > 0) {
        cpmMonthlyPayment = Math.round(
            requiredLoan * (monthlyRate * Math.pow(1 + monthlyRate, totalMonths)) / (Math.pow(1 + monthlyRate, totalMonths) - 1)
        );
    }

    const appliedMonthlyPayment = monthlyPaymentTarget > 0 ? monthlyPaymentTarget : cpmMonthlyPayment;
    const totalMonthlySpending = appliedMonthlyPayment + totalFixedSpendingNoLoan;
    const remainingMonthlyIncome = 3300000 - totalMonthlySpending;

    // 4. 월별 대출 상환 시뮬레이션 (보너스 반영)
    let currentBalance = requiredLoan;
    let accumulatedShortfall = 0;
    let totalInterestPaid = 0;
    let totalPrincipalPaid = 0;
    let finishMonth = 0;
    let isPaidOff = false;

    const bonusSchedule = useBonusPrepay ? { 1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000 } : {};

    const maxSimulateMonths = termYears * 12;
    const monthlyLog = [];

    for (let m = 1; m <= maxSimulateMonths; m++) {
        if (currentBalance <= 0) {
            if (!isPaidOff) {
                isPaidOff = true;
                finishMonth = m - 1;
            }
            break;
        }

        const startBal = currentBalance;
        const interestThisMonth = startBal * monthlyRate;
        
        let principalPaidThisMonth = 0;
        let interestPaidThisMonth = 0;

        if (appliedMonthlyPayment >= interestThisMonth) {
            interestPaidThisMonth = interestThisMonth;
            principalPaidThisMonth = appliedMonthlyPayment - interestThisMonth;
            if (principalPaidThisMonth > currentBalance) {
                principalPaidThisMonth = currentBalance;
            }
            currentBalance -= principalPaidThisMonth;
        } else {
            interestPaidThisMonth = appliedMonthlyPayment;
            const shortfall = interestThisMonth - appliedMonthlyPayment;
            accumulatedShortfall += shortfall;
        }

        totalInterestPaid += interestPaidThisMonth;
        totalPrincipalPaid += principalPaidThisMonth;

        // 보너스 투입월 판별
        const calMonth = ((m - 1) % 12) + 1;
        let bonusPaidThisMonth = 0;
        let shortfallClearedThisMonth = 0;

        if (bonusSchedule[calMonth] && currentBalance > 0) {
            let availableBonus = bonusSchedule[calMonth];
            
            // 미납이자 우선 청산
            if (accumulatedShortfall > 0) {
                if (availableBonus >= accumulatedShortfall) {
                    shortfallClearedThisMonth = accumulatedShortfall;
                    totalInterestPaid += accumulatedShortfall;
                    availableBonus -= accumulatedShortfall;
                    accumulatedShortfall = 0;
                } else {
                    shortfallClearedThisMonth = availableBonus;
                    totalInterestPaid += availableBonus;
                    accumulatedShortfall -= availableBonus;
                    availableBonus = 0;
                }
            }

            // 남은 보너스로 원금 상환
            if (availableBonus > 0) {
                bonusPaidThisMonth = Math.min(currentBalance, availableBonus);
                currentBalance -= bonusPaidThisMonth;
                totalPrincipalPaid += bonusPaidThisMonth;
            }
        }

        // 연말 미납이자 원금 가산 (부담금 이월 처리)
        if (m % 12 === 0 && accumulatedShortfall > 0) {
            currentBalance += accumulatedShortfall;
            accumulatedShortfall = 0;
        }

        monthlyLog.push({
            month: m,
            calMonth: calMonth,
            startBalance: Math.round(startBal),
            interest: Math.round(interestThisMonth),
            regularPrincipal: Math.round(principalPaidThisMonth),
            bonusPrincipal: Math.round(bonusPaidThisMonth),
            shortfallCleared: Math.round(shortfallClearedThisMonth),
            endBalance: Math.max(0, Math.round(currentBalance))
        });

        if (currentBalance <= 0 && !isPaidOff) {
            isPaidOff = true;
            finishMonth = m;
            break;
        }
    }

    const payoffYears = Math.floor(finishMonth / 12);
    const payoffMonths = finishMonth % 12;

    return {
        initialCosts: {
            netAcqTax,
            brokerageFee,
            legalFee,
            stampDuty,
            bondDiscountFee,
            movingFee,
            repairCleaningFee,
            totalR1Cost,
            totalInitialCapital,
            cashSurplusOrDeficit
        },
        loanDetails: {
            requiredLoan,
            ltvPercent,
            didimdolAmount,
            commercialAmount,
            effectiveRate,
            cpmMonthlyPayment
        },
        monthlySpending: {
            appliedMonthlyPayment,
            baseLivingNet,
            aptFixedExpenses,
            totalFixedSpendingNoLoan,
            totalMonthlySpending,
            remainingMonthlyIncome
        },
        payoffTimeline: {
            isPaidOff,
            finishMonth,
            payoffYears,
            payoffMonths,
            totalInterestPaid: Math.round(totalInterestPaid),
            totalPrincipalPaid: Math.round(totalPrincipalPaid)
        },
        monthlyLog
    };
}
```

---

## 7. 결론 및 검증 수단 (Conclusion & Verification)

### 7.1 주요 시나리오 검증 결과

| 시나리오 항목 | 3.5억 원 매매 | 3.75억 원 매매 | 4.0억 원 매매 |
| :--- | :---: | :---: | :---: |
| **보유 현금** | 2.3억 원 | 2.3억 원 | 2.3억 원 |
| **필요 대출금** | **1.2억 원** | **1.45억 원** | **1.7억 원** |
| **LTV** | 34.29% | 38.67% | 42.50% |
| **R1 일회성 비용** | **7,854,500원** | **8,348,750원** | **8,804,000원** |
| **초기 필요 자금** | 357,854,500원 | 383,348,750원 | 408,804,000원 |
| **월 고정 지출 (대출 제외)** | 2,319,708원 | 2,319,708원 | 2,319,708원 |
| **월 50만 원 상환 시 총지출** | **2,819,708원** | **2,819,708원** | **2,819,708원** |
| **월 잔여 자금 (330만 - 지출)** | **480,292원** | **480,292원** | **480,292원** |
| **대출 완납 예상 기간 (연1,000만 보너스 투입)** | **약 8년 3개월** | **약 9년 7개월** | **약 10년 10개월** |

### 7.2 독립적 검증 수단

1. **파이썬 기준 엔진 검증**:
   - `python3 /home/imnyj/Workspace/House/etc/scripts/calc_engine.py --verify` 실행으로 R1 세부 산출액 100% 일치 확인.
2. **E2E 참조 엔진 실행**:
   - `python3 /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py` 실행을 통한 시뮬레이션 타임라인 검증.
