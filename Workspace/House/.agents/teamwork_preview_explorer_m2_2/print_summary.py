import json

with open("simulation_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for sc_name, sc_data in data.items():
    print(f"=== {sc_name} ===")
    for rate_label, res in sc_data.items():
        lp = res['loan_principal']
        pmt = res['monthly_pmt']
        pm = res['payoff_month']
        py = res['payoff_years']
        ti = res['total_interest_paid']
        fc = res['final_cash_balance']
        print(f"  [{rate_label}]")
        print(f"    Loan Principal: {lp:,} KRW")
        print(f"    Monthly PMT: {pmt:,} KRW")
        print(f"    Payoff Time: {pm} months ({py} years)")
        print(f"    Total Interest Paid: {ti:,} KRW")
        print(f"    Final Cash Balance at Payoff: {fc:,} KRW")
