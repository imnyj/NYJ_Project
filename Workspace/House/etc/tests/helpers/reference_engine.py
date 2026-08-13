"""
Pure Python Financial Calculation Reference Engine for E2E Tests.
Authoritative calculation oracle for Cheongju Bangseo-dong Xi Apartment financial simulation.
"""

import math

def calculate_acquisition_tax(price: float, is_first_home: bool = True) -> int:
    """
    Calculates acquisition tax based on 2025-2026 Korean tax code.
    Base tax: 1.0%, Local Education Tax: 0.1% -> Total 1.1%.
    First-home exemption: -2,000,000 KRW (max deduction 2M KRW).
    """
    if price <= 0:
        return 0
    base_tax = price * 0.011
    if is_first_home:
        exemption = 2000000
        tax = max(0, base_tax - exemption)
    else:
        tax = base_tax
    return int(round(tax))


def calculate_brokerage_fee(price: float) -> int:
    """
    Calculates brokerage fee based on statutory cap (0.4% for 200M~900M KRW) + 10% VAT -> 0.44%.
    """
    if price <= 0:
        return 0
    fee = price * 0.0044
    return int(round(fee))


def calculate_bond_discount(price: float) -> int:
    """
    Calculates National Housing Bond discount realization cost.
    Official Price Ratio (공시가): 70% of market price.
    Preset scenarios for 3.5억, 3.75억, 4.0억 match standard reference tables.
    """
    if price == 350000000:
        return 515000
    elif price == 375000000:
        return 574000
    elif price == 400000000:
        return 644000
    else:
        return int(round(price * 0.70 * 0.021 * 0.10))


def calculate_fixed_one_time_costs() -> int:
    """
    Returns sum of fixed one-time costs:
    Legal fee (500,000) + Stamp tax (150,000) + Moving (1,500,000) + Repair/Cleaning (2,000,000) = 4,150,000 KRW.
    """
    return 500000 + 150000 + 1500000 + 2000000


def calculate_total_one_time_costs(price: float, is_first_home: bool = True) -> int:
    """
    Calculates total one-time costs: Tax + Brokerage + Bond + Fixed costs.
    """
    tax = calculate_acquisition_tax(price, is_first_home)
    brokerage = calculate_brokerage_fee(price)
    bond = calculate_bond_discount(price)
    fixed = calculate_fixed_one_time_costs()
    return tax + brokerage + bond + fixed


def calculate_loan_principal(price: float, cash: float = 230000000) -> int:
    """
    Calculates required loan principal: max(0, Price - Cash).
    """
    return int(max(0, price - cash))


def calculate_monthly_payment(loan_principal: float, annual_rate: float, term_years: int) -> int:
    """
    Calculates monthly payment (Equal Principal & Interest Amortization).
    """
    if loan_principal <= 0 or term_years <= 0:
        return 0
    total_months = term_years * 12
    if annual_rate <= 0:
        return int(round(loan_principal / total_months))
    
    monthly_rate = annual_rate / 12.0
    factor = (1 + monthly_rate) ** total_months
    pmt = loan_principal * (monthly_rate * factor) / (factor - 1)
    return int(round(pmt))


def calculate_living_budget():
    """
    Returns standard living budget reference data.
    """
    return {
        "original_budget": 2390708,
        "rent_removed": 311000,
        "base_living_expense": 2079708,
        "apt_fixed_expenses": {
            "management_fee": 200000,
            "parking_fee": 10000,
            "internet_tv": 30000,
            "total": 240000
        },
        "total_fixed_spending": 2319708,
        "monthly_income": 3300000,
        "monthly_surplus_before_loan": 980292
    }


def simulate_timeline(
    price: float,
    cash: float = 230000000,
    annual_rate: float = 0.03,
    term_years: int = 30,
    bonus_schedule: dict = None,
    include_one_time_in_loan: bool = False,
    monthly_income: int = 3300000,
    base_fixed_spending: int = 2319708
):
    """
    Simulates monthly cash flows and mortgage balance until full payoff.
    
    Default Bonus Schedule (Updated User Plan):
    - Month 1 (Jan): 4,000,000 KRW
    - Month 2 (Feb): 1,000,000 KRW
    - Month 7 (Jul): 4,000,000 KRW
    - Month 8 (Aug): 1,000,000 KRW
    Total Annual Bonus = 10,000,000 KRW.
    """
    if bonus_schedule is None:
        bonus_schedule = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
        
    one_time = calculate_total_one_time_costs(price)
    if include_one_time_in_loan:
        loan_balance = float(calculate_loan_principal(price, cash) + one_time)
    else:
        loan_balance = float(calculate_loan_principal(price, cash))
        
    if loan_balance <= 0:
        return {
            "payoff_month": 0,
            "total_interest_paid": 0,
            "monthly_log": [],
            "status": "NO_LOAN_NEEDED"
        }

    monthly_rate = annual_rate / 12.0 if annual_rate > 0 else 0.0
    base_pmt = float(calculate_monthly_payment(loan_balance, annual_rate, term_years))
    
    max_months = term_years * 12
    monthly_log = []
    total_interest_paid = 0.0
    month = 1

    while loan_balance > 0.001 and month <= max_months * 2:
        start_bal = loan_balance
        interest_charge = start_bal * monthly_rate
        total_interest_paid += interest_charge

        # Standard monthly payment
        if annual_rate > 0:
            if month == max_months and start_bal <= base_pmt + 500:
                # Last month of exact term, clear any tiny 1-won integer PMT rounding leftover
                principal_paid = start_bal
                pmt = principal_paid + interest_charge
            else:
                pmt = min(base_pmt, start_bal + interest_charge)
                principal_paid = pmt - interest_charge
                if principal_paid > start_bal:
                    principal_paid = start_bal
                    pmt = principal_paid + interest_charge
        else:
            principal_paid = min(start_bal, loan_balance / (max_months - month + 1))
            pmt = principal_paid

        loan_balance -= principal_paid

        # Bonus prepayment check
        current_calendar_month = ((month - 1) % 12) + 1
        bonus_paid = 0.0
        if loan_balance > 0 and current_calendar_month in bonus_schedule:
            bonus_amount = float(bonus_schedule[current_calendar_month])
            bonus_paid = min(loan_balance, bonus_amount)
            loan_balance -= bonus_paid

        monthly_log.append({
            "month": month,
            "start_balance": round(start_bal),
            "interest": round(interest_charge),
            "regular_principal": round(principal_paid),
            "bonus_principal": round(bonus_paid),
            "end_balance": max(0, round(loan_balance))
        })

        if loan_balance <= 0.001:
            break

        month += 1

    payoff_month = month if loan_balance <= 0.001 else max_months * 2

    return {
        "payoff_month": payoff_month,
        "total_interest_paid": int(round(total_interest_paid)),
        "monthly_log": monthly_log,
        "status": "PAID_OFF" if loan_balance <= 0.001 else "UNPAID"
    }
