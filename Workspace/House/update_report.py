import sys
import os

sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

def calculate_monthly(p, annual_rate, years):
    r = annual_rate / 12 / 100
    n = years * 12
    if r == 0:
        return p / n
    return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

targets = [300_000_000, 400_000_000, 450_000_000]
cash = 230_000_000

report = "# Real Estate Financial Strategy Report\n\n"
report += "## 1. Financial Overview\n"
report += "- **My Asset:** 30M KRW\n"
report += "- **My Parents' Support:** 100M KRW\n"
report += "- **Eunbi's Parents' Support:** 100M KRW (Matched to my parents' support)\n"
report += "- **Total Available Cash:** 230M KRW\n\n"

report += "## 2. Income & Loan Eligibility Analysis\n"
report += "- **Combined Income:** > 150M KRW (My income: ~70M, Eunbi's net: >80M)\n"
report += "### Loan Options\n"
report += "- **Newlywed Didimdol:** Impossible (Income limit is 85M KRW).\n"
report += "- **Bogeumjari:** Possible if done as a single person before marriage.\n"
report += "- **Newborn Special:** Possible in 2 years (Income limit is up to 200M KRW).\n"
report += "- **Regular Bank Loan:** Possible.\n\n"

report += "## 3. Required Loan & Monthly Payment Estimates\n"
report += "Assumed interest rates: Regular Bank (4.0%), Government/Newborn (2.5%).\n\n"
report += "| Target Price | Required Loan | Regular (4.0%, 30y) | Regular (4.0%, 40y) | Govt (2.5%, 30y) | Govt (2.5%, 40y) |\n"
report += "|---|---|---|---|---|---|\n"

for target in targets:
    loan = target - cash
    if loan <= 0:
        report += f"| {target//10000}M | 0M | 0 | 0 | 0 | 0 |\n"
        continue
    
    reg_30 = calculate_monthly(loan, 4.0, 30)
    reg_40 = calculate_monthly(loan, 4.0, 40)
    gov_30 = calculate_monthly(loan, 2.5, 30)
    gov_40 = calculate_monthly(loan, 2.5, 40)
    
    report += f"| {target//10000}M | {loan//10000}M | {int(reg_30):,} KRW | {int(reg_40):,} KRW | {int(gov_30):,} KRW | {int(gov_40):,} KRW |\n"

report += "\n## 4. Proposed Strategies\n\n"
report += "### Strategy 1: Use Bogeumjari as single before marriage -> Refinance to Newborn Special later\n"
report += "- **Pros:** Can secure a lower interest rate immediately without waiting 2 years. Smooth transition to Newborn Special.\n"
report += "- **Cons:** Must buy the property under a single name before officially registering the marriage. May have limits on maximum loan amounts.\n\n"

report += "### Strategy 2: Use Regular loans now -> Refinance to Newborn Special later\n"
report += "- **Pros:** Flexible, no restrictions on marriage registration. Can buy jointly.\n"
report += "- **Cons:** Higher initial interest rates (~4.0%) meaning higher monthly payments for the first 2 years.\n\n"

report += "### Strategy 3: Persuade parents to sell their Officetel to secure more cash\n"
report += "- **Pros:** Increases available cash upfront, drastically reducing loan burden and monthly payments. Allows targeting a higher-priced apartment.\n"
report += "- **Cons:** Parents may be reluctant or lose rental income. Could take time to sell the Officetel.\n\n"

report += "### Strategy 4: Live temporarily in Eunbi's parent's annex\n"
report += "- **Pros:** No housing costs for the first few years. Allows saving aggressively until the Newborn Special loan is available.\n"
report += "- **Cons:** Less independence. Commute or lifestyle adjustments may be required.\n"

file_path = "/home/imnyj/Workspace/House/docs/strategy_report.md"

lm = LockManager()
logger = AuditLogger()

lock_acquired = lm.acquire(file_path, "real_estate_analyst")
if not lock_acquired:
    print(f"Failed to acquire lock for {file_path}")
    sys.exit(1)

try:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write(report)
    logger.log_action("real_estate_analyst", "MODIFY", file_path, "Updated strategy report with new financial constraints and 4 strategies.")
    print("Successfully updated report.")
finally:
    lm.release(file_path, "real_estate_analyst")
