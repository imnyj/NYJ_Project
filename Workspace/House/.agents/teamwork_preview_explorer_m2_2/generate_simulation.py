"""
generate_simulation.py
Generates full monthly (Year 1) and annual cashflow & payoff schedules for Milestone 2 R3.
"""

import math
import json

def calculate_cpm_monthly_payment(principal: int, annual_rate: float, term_years: int = 30) -> int:
    if principal <= 0:
        return 0
    if annual_rate <= 0:
        return int(math.ceil(principal / (term_years * 12)))
    r = annual_rate / 12.0
    n = term_years * 12
    monthly_payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return int(round(monthly_payment))

def run_simulation(price, cash_reserve=230000000, annual_rate=0.0315, term_years=30, bonus_schedule=None,
                   monthly_income=3300000, base_fixed_spending=2319708, initial_cash_balance=0):
    if bonus_schedule is None:
        # Month in calendar year: (month - 1) % 12 + 1
        # Prepayment: Jan(1)->4M, Feb(2)->1M, Jul(7)->4M, Aug(8)->1M
        # Reserved cash kept: Jan(1)->1M, Jul(7)->1M
        bonus_prepay_dict = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
        bonus_reserve_dict = {1: 1000000, 7: 1000000}
    else:
        bonus_prepay_dict = bonus_schedule
        bonus_reserve_dict = {}

    loan_principal = max(0, price - cash_reserve)
    loan_balance = float(loan_principal)
    monthly_rate = annual_rate / 12.0
    base_pmt = float(calculate_cpm_monthly_payment(loan_principal, annual_rate, term_years))
    surplus_before_loan = monthly_income - base_fixed_spending

    monthly_logs = []
    annual_logs = []
    
    total_interest_paid = 0.0
    total_regular_principal_paid = 0.0
    total_bonus_principal_paid = 0.0
    
    current_cash_balance = float(initial_cash_balance)
    month = 1
    max_months = term_years * 12 * 2

    # Annual tracking
    year_interest = 0.0
    year_reg_principal = 0.0
    year_bonus_principal = 0.0
    year_start_balance = loan_balance
    year_start_cash = current_cash_balance

    while loan_balance > 0.001 and month <= max_months:
        cal_month = ((month - 1) % 12) + 1
        year_num = ((month - 1) // 12) + 1
        
        start_bal = loan_balance
        interest_charge = start_bal * monthly_rate
        total_interest_paid += interest_charge
        year_interest += interest_charge

        # Monthly regular payment
        if month == term_years * 12 and start_bal <= base_pmt + 500:
            reg_principal = start_bal
            pmt = reg_principal + interest_charge
        else:
            pmt = min(base_pmt, start_bal + interest_charge)
            reg_principal = pmt - interest_charge
            if reg_principal > start_bal:
                reg_principal = start_bal
                pmt = reg_principal + interest_charge

        loan_balance -= reg_principal
        total_regular_principal_paid += reg_principal
        year_reg_principal += reg_principal

        # Bonus prepayment
        bonus_prepay = 0.0
        bonus_reserved = bonus_reserve_dict.get(cal_month, 0)
        if loan_balance > 0 and cal_month in bonus_prepay_dict:
            target_bonus = float(bonus_prepay_dict[cal_month])
            bonus_prepay = min(loan_balance, target_bonus)
            loan_balance -= bonus_prepay
            total_bonus_principal_paid += bonus_prepay
            year_bonus_principal += bonus_prepay

        # Net cashflow & balance updating
        net_monthly_surplus = surplus_before_loan - pmt
        current_cash_balance += net_monthly_surplus + bonus_reserved

        log_entry = {
            "month": month,
            "year": year_num,
            "cal_month": cal_month,
            "start_balance": round(start_bal),
            "interest": round(interest_charge),
            "regular_principal": round(reg_principal),
            "bonus_prepayment": round(bonus_prepay),
            "total_monthly_pmt": round(pmt),
            "net_surplus_after_pmt": round(net_monthly_surplus),
            "bonus_reserved": round(bonus_reserved),
            "end_balance": max(0, round(loan_balance)),
            "cum_cash_balance": round(current_cash_balance)
        }
        monthly_logs.append(log_entry)

        # End of Year or Paid Off Check for Annual Logging
        if cal_month == 12 or loan_balance <= 0.001:
            annual_logs.append({
                "year": year_num,
                "year_start_balance": round(year_start_balance),
                "year_interest": round(year_interest),
                "year_regular_principal": round(year_reg_principal),
                "year_bonus_principal": round(year_bonus_principal),
                "year_total_principal": round(year_reg_principal + year_bonus_principal),
                "year_end_balance": max(0, round(loan_balance)),
                "year_end_cash": round(current_cash_balance)
            })
            # Reset annual trackers
            year_interest = 0.0
            year_reg_principal = 0.0
            year_bonus_principal = 0.0
            year_start_balance = loan_balance

        if loan_balance <= 0.001:
            break

        month += 1

    return {
        "price": price,
        "loan_principal": loan_principal,
        "annual_rate": annual_rate,
        "term_years": term_years,
        "monthly_pmt": round(base_pmt),
        "payoff_month": month if loan_balance <= 0.001 else max_months,
        "payoff_years": round(month / 12.0, 2),
        "total_interest_paid": round(total_interest_paid),
        "total_regular_principal_paid": round(total_regular_principal_paid),
        "total_bonus_principal_paid": round(total_bonus_principal_paid),
        "final_cash_balance": round(current_cash_balance),
        "monthly_logs": monthly_logs,
        "annual_logs": annual_logs
    }

def main():
    scenarios = [
        {"name": "3.5억 (대출 1.2억)", "price": 350000000},
        {"name": "3.75억 (대출 1.45억)", "price": 375000000},
        {"name": "4.0억 (대출 1.7억)", "price": 400000000}
    ]

    rates = [
        {"label": "디딤돌 3.15%", "rate": 0.0315},
        {"label": "디딤돌 최저 3.00%", "rate": 0.0300},
        {"label": "시중은행 4.25%", "rate": 0.0425}
    ]

    all_results = {}

    for sc in scenarios:
        sc_name = sc["name"]
        price = sc["price"]
        all_results[sc_name] = {}
        for r in rates:
            rate_label = r["label"]
            rate_val = r["rate"]
            res = run_simulation(price, annual_rate=rate_val)
            all_results[sc_name][rate_label] = res

    with open("/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("Simulation execution complete. Exported results to simulation_results.json")

if __name__ == "__main__":
    main()
