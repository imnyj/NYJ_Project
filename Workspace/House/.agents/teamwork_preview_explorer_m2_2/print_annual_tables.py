import json

with open("simulation_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for sc_name, sc_data in data.items():
    print(f"==========================================================")
    print(f"  Annual Payoff Schedule: {sc_name} (Didimdol 3.15%)")
    print(f"==========================================================")
    res = sc_data["디딤돌 3.15%"]
    annual_logs = res["annual_logs"]
    print(f"연차 | 기초잔액 | 연간이자 | 정기원금 | 보너스원금 | 총원금상환 | 기말잔액 | 기말현금잔고")
    print("-" * 105)
    for row in annual_logs:
        y = row["year"]
        sb = row["year_start_balance"]
        intr = row["year_interest"]
        rp = row["year_regular_principal"]
        bp = row["year_bonus_principal"]
        tp = row["year_total_principal"]
        eb = row["year_end_balance"]
        ec = row["year_end_cash"]
        print(f"{y:2d}년 | {sb:11,d} | {intr:9,d} | {rp:9,d} | {bp:10,d} | {tp:10,d} | {eb:11,d} | {ec:11,d}")
    print()
