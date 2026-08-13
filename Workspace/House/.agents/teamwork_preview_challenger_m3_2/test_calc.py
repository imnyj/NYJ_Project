import re
import json

def calc_js_logic(price, cash=230000000, monthly_payment_input=500000, didimdol_rate=0.0315, commercial_rate=0.042, term_years=30, use_bonus=True, bonus_jan=1000000, bonus_feb=4000000, bonus_jul=1000000, bonus_aug=4000000):
    # 1. R1 Costs
    grossAcqTax = int(price * 0.011)
    acqTaxExemption = min(grossAcqTax, 2000000)
    netAcqTaxTotal = max(0, grossAcqTax - acqTaxExemption)

    brokerageFee = int(price * 0.0044)

    if price >= 375000000 and price < 400000000:
        legalFee = 520000
    elif price >= 400000000:
        legalFee = 550000
    else:
        legalFee = 500000

    stampDuty = 150000
    publicPrice = price * 0.70
    bondRate = 0.021 if publicPrice < 260000000 else 0.023
    bondDiscountFee = int(publicPrice * bondRate * 0.10)
    movingFee = 1500000
    repairCleaningFee = 2000000

    requiredLoan = max(0, price - cash)
    if requiredLoan > 100000000:
        loanStampDuty = 75000
    elif requiredLoan > 50000000:
        loanStampDuty = 35000
    else:
        loanStampDuty = 0

    totalR1Cost = netAcqTaxTotal + brokerageFee + legalFee + stampDuty + bondDiscountFee + movingFee + repairCleaningFee + loanStampDuty
    totalInitialCapital = price + totalR1Cost

    # 2. Loan Split & Effective Rate
    DIDIMDOL_MAX = 400000000
    if requiredLoan > 0:
        didimdolAmount = min(requiredLoan, DIDIMDOL_MAX)
        commercialAmount = max(0, requiredLoan - DIDIMDOL_MAX)
        effectiveRate = (didimdolAmount * didimdol_rate + commercialAmount * commercial_rate) / requiredLoan
    else:
        didimdolAmount = 0
        commercialAmount = 0
        effectiveRate = commercial_rate

    # 3. Monthly Spending
    baseLivingNet = 2079708
    aptFixedExpenses = 240000
    totalFixedSpendingNoLoan = baseLivingNet + aptFixedExpenses # 2319708
    totalMonthlySpending = monthly_payment_input + totalFixedSpendingNoLoan
    monthlyNetIncome = 3300000
    remainingMonthlyIncome = monthlyNetIncome - totalMonthlySpending

    # 4. Amortization
    monthlyRate = effectiveRate / 12
    currentBalance = requiredLoan
    accumulatedShortfall = 0
    totalInterestPaid = 0
    totalPrincipalPaid = 0
    finishMonth = 0
    isPaidOff = False
    maxMonths = term_years * 12

    monthlyLog = []

    for m in range(1, maxMonths + 1):
        if currentBalance <= 0:
            if not isPaidOff:
                isPaidOff = True
                finishMonth = m - 1
            break

        startBal = currentBalance
        interestThisMonth = startBal * monthlyRate

        principalPaidThisMonth = 0
        interestPaidThisMonth = 0

        if monthly_payment_input >= interestThisMonth:
            interestPaidThisMonth = interestThisMonth
            principalPaidThisMonth = monthly_payment_input - interestThisMonth
            if principalPaidThisMonth > currentBalance:
                principalPaidThisMonth = currentBalance
            currentBalance -= principalPaidThisMonth
        else:
            interestPaidThisMonth = monthly_payment_input
            shortfall = interestThisMonth - monthly_payment_input
            accumulatedShortfall += shortfall

        totalInterestPaid += interestPaidThisMonth
        totalPrincipalPaid += principalPaidThisMonth

        calMonth = ((m - 1) % 12) + 1
        bonusAmount = 0
        if use_bonus:
            if calMonth == 1: bonusAmount = bonus_jan
            elif calMonth == 2: bonusAmount = bonus_feb
            elif calMonth == 7: bonusAmount = bonus_jul
            elif calMonth == 8: bonusAmount = bonus_aug

        bonusPaidThisMonth = 0
        shortfallClearedThisMonth = 0

        if bonusAmount > 0 and currentBalance > 0:
            if accumulatedShortfall > 0:
                if bonusAmount >= accumulatedShortfall:
                    shortfallClearedThisMonth = accumulatedShortfall
                    totalInterestPaid += accumulatedShortfall
                    bonusAmount -= accumulatedShortfall
                    accumulatedShortfall = 0
                else:
                    shortfallClearedThisMonth = bonusAmount
                    totalInterestPaid += bonusAmount
                    accumulatedShortfall -= bonusAmount
                    bonusAmount = 0

            if bonusAmount > 0:
                bonusPaidThisMonth = min(currentBalance, bonusAmount)
                currentBalance -= bonusPaidThisMonth
                totalPrincipalPaid += bonusPaidThisMonth

        if m % 12 == 0 and accumulatedShortfall > 0:
            currentBalance += accumulatedShortfall
            accumulatedShortfall = 0

        if currentBalance < 0:
            currentBalance = 0

        monthlyLog.append({
            'month': m,
            'interest': interestThisMonth,
            'principalPaid': principalPaidThisMonth,
            'bonusPaid': bonusPaidThisMonth,
            'balance': currentBalance,
            'shortfall': accumulatedShortfall
        })

        if currentBalance <= 0 and not isPaidOff:
            isPaidOff = True
            finishMonth = m
            break

    if not isPaidOff:
        finishMonth = maxMonths

    return {
        'price': price,
        'grossAcqTax': grossAcqTax,
        'acqTaxExemption': acqTaxExemption,
        'netAcqTaxTotal': netAcqTaxTotal,
        'brokerageFee': brokerageFee,
        'legalFee': legalFee,
        'stampDuty': stampDuty,
        'bondDiscountFee': bondDiscountFee,
        'movingFee': movingFee,
        'repairCleaningFee': repairCleaningFee,
        'loanStampDuty': loanStampDuty,
        'totalR1Cost': totalR1Cost,
        'totalInitialCapital': totalInitialCapital,
        'requiredLoan': requiredLoan,
        'effectiveRate': effectiveRate,
        'totalMonthlySpending': totalMonthlySpending,
        'remainingMonthlyIncome': remainingMonthlyIncome,
        'isPaidOff': isPaidOff,
        'finishMonth': finishMonth,
        'payoffYears': finishMonth // 12,
        'payoffMonths': finishMonth % 12,
        'totalInterestPaid': round(totalInterestPaid),
        'monthlyLogLength': len(monthlyLog)
    }

for p in [350000000, 375000000, 400000000]:
    res = calc_js_logic(p)
    print(f"=== Scenario Price: {p/1e8}억 ===")
    print(f"  R1 Total Cost: {res['totalR1Cost']:,} KRW ({res['totalR1Cost']/1e4:.1f}만)")
    print(f"  Total Initial Capital: {res['totalInitialCapital']:,} KRW ({res['totalInitialCapital']/1e8:.4f}억)")
    print(f"  Required Loan: {res['requiredLoan']:,} KRW ({res['requiredLoan']/1e8:.2f}억)")
    print(f"  Effective Rate: {res['effectiveRate']*100:.3f}%")
    print(f"  Total Monthly Spending: {res['totalMonthlySpending']:,} KRW")
    print(f"  Remaining Monthly Income: {res['remainingMonthlyIncome']:,} KRW")
    print(f"  Paid Off: {res['isPaidOff']}, Timeline: {res['finishMonth']} months ({res['payoffYears']}y {res['payoffMonths']}m)")
    print(f"  Total Interest Paid: {res['totalInterestPaid']:,} KRW\n")
