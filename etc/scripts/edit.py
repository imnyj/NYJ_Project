import os
import sys

# Import lock manager and audit logger
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

lm = LockManager()
logger = AuditLogger()

target_file = "/home/imnyj/Workspace/House/ui/index.html"
agent_id = "agent_123"

if not lm.acquire(target_file, agent_id):
    print("Failed to acquire lock")
    sys.exit(1)

try:
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Replacements for Tab 2 HTML
    old_tab2_inputs = """                    <div class="form-group">
                        <label>월 원금 상환액 (원)</label>
                        <input type="number" id="t2-principal" value="500000" step="10000" oninput="updateTab2()">
                    </div>"""
    new_tab2_inputs = """                    <div class="form-group">
                        <label>월 원금 상환액 (원)</label>
                        <input type="number" id="t2-principal" value="500000" step="10000" oninput="updateTab2()">
                    </div>
                    <div class="form-group">
                        <label>연간 교연비 투입액 (원)</label>
                        <input type="number" id="t2-annual-bonus" value="10000000" step="1000000" oninput="updateTab2()">
                    </div>
                    <div class="form-group">
                        <label>연간 부가 수익 투입액 (원)</label>
                        <input type="number" id="t2-annual-extra" value="2000000" step="1000000" oninput="updateTab2()">
                    </div>"""
    content = content.replace(old_tab2_inputs, new_tab2_inputs)

    # Replacements for Tab 3 HTML
    old_tab3_inputs = """                    <div class="form-group">
                        <label>월 최대 상환 가능액 (원) <span style="font-weight:normal; font-size:0.8em;">(이자+원금)</span></label>
                        <input type="number" id="t3-payment" value="1500000" step="100000" oninput="updateTab3()">
                    </div>"""
    new_tab3_inputs = """                    <div class="form-group">
                        <label>월 최대 상환 가능액 (원) <span style="font-weight:normal; font-size:0.8em;">(이자+원금)</span></label>
                        <input type="number" id="t3-payment" value="1500000" step="100000" oninput="updateTab3()">
                    </div>
                    <div class="form-group">
                        <label>연간 교연비 투입액 (원)</label>
                        <input type="number" id="t3-annual-bonus" value="10000000" step="1000000" oninput="updateTab3()">
                    </div>
                    <div class="form-group">
                        <label>연간 부가 수익 투입액 (원)</label>
                        <input type="number" id="t3-annual-extra" value="2000000" step="1000000" oninput="updateTab3()">
                    </div>"""
    content = content.replace(old_tab3_inputs, new_tab3_inputs)

    # Tab 2 Logic changes
    old_tab2_js1 = """            const period = parseInt(document.getElementById('t2-period').value);
            const monthlyPrincipal = parseInt(document.getElementById('t2-principal').value);"""
    new_tab2_js1 = """            const period = parseInt(document.getElementById('t2-period').value);
            const monthlyPrincipal = parseInt(document.getElementById('t2-principal').value);
            const annualBonus = parseInt(document.getElementById('t2-annual-bonus').value) || 0;
            const annualExtra = parseInt(document.getElementById('t2-annual-extra').value) || 0;
            const extraAnnualRepayment = annualBonus + annualExtra;"""
    content = content.replace(old_tab2_js1, new_tab2_js1)

    old_tab2_js2 = """                totalInterestPaid += (monthlyInterest * 12);
                let actualP = Math.min(currentLoan, monthlyPrincipal * 12);
                principalPaid += actualP;
                currentLoan -= actualP;
            }"""
    new_tab2_js2 = """                totalInterestPaid += (monthlyInterest * 12);
                let actualP = Math.min(currentLoan, monthlyPrincipal * 12);
                principalPaid += actualP;
                currentLoan -= actualP;
                
                if (currentLoan > 0) {
                    let actualExtraP = Math.min(currentLoan, extraAnnualRepayment);
                    principalPaid += actualExtraP;
                    currentLoan -= actualExtraP;
                }
            }"""
    content = content.replace(old_tab2_js2, new_tab2_js2)

    # Tab 3 Logic changes
    old_tab3_js1 = """            const switchYear = parseInt(document.getElementById('t3-switch').value);
            const monthlyPayment = parseInt(document.getElementById('t3-payment').value);"""
    new_tab3_js1 = """            const switchYear = parseInt(document.getElementById('t3-switch').value);
            const monthlyPayment = parseInt(document.getElementById('t3-payment').value);
            const annualBonus = parseInt(document.getElementById('t3-annual-bonus').value) || 0;
            const annualExtra = parseInt(document.getElementById('t3-annual-extra').value) || 0;
            const extraAnnualRepayment = annualBonus + annualExtra;"""
    content = content.replace(old_tab3_js1, new_tab3_js1)

    old_tab3_js2 = """                const principalPaid = monthlyPayment - monthlyInterest;
                let actualP = Math.min(principalPaid, currentLoan);
                totalPrincipalPaid += actualP;
                totalInterestPaid += monthlyInterest;
                currentLoan -= actualP;
                month++;
                
                // 매년 첫 달 혹은 마지막 달의 데이터를 그래프에 표시"""
    new_tab3_js2 = """                const principalPaid = monthlyPayment - monthlyInterest;
                let actualP = Math.min(principalPaid, currentLoan);
                totalPrincipalPaid += actualP;
                totalInterestPaid += monthlyInterest;
                currentLoan -= actualP;
                month++;
                
                if (month % 12 === 0 && currentLoan > 0) {
                    let actualExtraP = Math.min(currentLoan, extraAnnualRepayment);
                    totalPrincipalPaid += actualExtraP;
                    currentLoan -= actualExtraP;
                }
                
                // 매년 첫 달 혹은 마지막 달의 데이터를 그래프에 표시"""
    content = content.replace(old_tab3_js2, new_tab3_js2)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.log_action(agent_id, "MODIFY", target_file, "Added annual extra repayment inputs to Tab 2 and Tab 3")
    print("Successfully updated the file.")

finally:
    lm.release(target_file, agent_id)
