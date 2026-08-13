import json

with open("simulation_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for sc_name, sc_data in data.items():
    print(f"==================================================")
    print(f"  Year 1 Monthly Schedule: {sc_name} (Didimdol 3.15%)")
    print(f"==================================================")
    res = sc_data["디딤돌 3.15%"]
    logs = res["monthly_logs"][:12]
    print(f"월 | 시작잔액 | 이자 | 정기원금 | 보너스상환 | 월상환총액 | 월순수익 | 유보금 | 기말잔액 | 기말현금잔고")
    print("-" * 105)
    for row in logs:
        m = row["month"]
        sb = row["start_balance"]
        intr = row["interest"]
        rp = row["regular_principal"]
        bp = row["bonus_prepayment"]
        pmt = row["total_monthly_pmt"]
        ns = row["net_surplus_after_pmt"]
        br = row["bonus_reserved"]
        eb = row["end_balance"]
        cb = row["cum_cash_balance"]
        print(f"{m:2d} | {sb:11,d} | {intr:7,d} | {rp:8,d} | {bp:10,d} | {pmt:10,d} | {ns:8,d} | {br:6,d} | {eb:11,d} | {cb:11,d}")
    print()
