import sys
import os

sys.path.append('/home/imnyj/Command')

from core.lock_manager import LockManager
from core.audit_logger import AuditLogger

def main():
    file_path = '/home/imnyj/Workspace/House/ui/index.html'
    agent_id = 'parent'
    
    lock = LockManager()
    logger = AuditLogger()
    
    if not lock.acquire(file_path, agent_id):
        print("Failed to acquire lock")
        sys.exit(1)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        old_tab3_html = '''        <!-- 탭 3: 역산 계산기 -->
        <div id="tab3" class="tab-content glass">
            <h2 style="margin-bottom: 20px;">역산 계산기 <span style="font-size:0.6em; color:var(--text-muted);">(월 이자로 아파트 가격 산출)</span></h2>
            
            <div class="grid" style="grid-template-columns: 1fr;">
                <div style="margin-bottom: 10px;">
                    <canvas id="chartTab3" style="max-height: 200px;"></canvas>
                </div>
                
                <div class="grid">
                    <div>
                        <div class="form-group">
                            <label>감당 가능한 월 이자 (원)</label>
                            <input type="number" id="t3-interest" value="400000" step="10000" oninput="updateTab3()">
                        </div>
                        <div class="form-group">
                            <label>예상 대출 금리 (%)</label>
                            <input type="number" id="t3-rate" value="4.2" step="0.1" oninput="updateTab3()">
                        </div>
                    </div>
                    <div class="result-box">
                        <p>기본 자금: <strong>2억 3,000만원</strong></p>
                        <p>역산 대출 가능액: <strong id="t3-max-loan" style="color:var(--accent);">1억 1,428만원</strong></p>
                        <hr style="border: 0; border-top: 1px dashed var(--glass-border); margin: 15px 0;">
                        <h3 style="margin: 0; font-size: 1.4em;">최대 구매 가능 아파트:<br><span id="t3-apt-price" style="color:var(--success); font-size: 1.2em;">3억 4,428만원</span></h3>
                    </div>
                </div>
            </div>
        </div>'''
        
        new_tab3_html = '''        <!-- 탭 3: 역산 계산기 -->
        <div id="tab3" class="tab-content glass">
            <h2 style="margin-bottom: 20px;">역산 계산기 <span style="font-size:0.6em; color:var(--text-muted);">(목표 상환액으로 상환 기간 산출)</span></h2>
            <div class="result-box" style="margin-bottom: 25px;">
                <strong>기본 자금 Fix: <span style="color:var(--accent); font-size:1.2em;">2억 3,000만원</span></strong>
                <p style="margin: 5px 0 0 0; font-size:0.9em; color:var(--text-muted);">내 부모님 1억 + 나 3천만원 + 은비네 부모님 1억</p>
            </div>
            
            <div class="grid">
                <div>
                    <div class="form-group">
                        <label>아파트 가격 <span class="value-display" id="t3-apt-val">3억 5,000만원</span></label>
                        <input type="range" id="t3-apt" min="300000000" max="450000000" step="1000000" value="350000000" oninput="updateTab3()">
                    </div>
                    <div class="form-group">
                        <label>신생아 대출 전환 시점 <span class="value-display" id="t3-switch-val">3년 뒤</span></label>
                        <input type="range" id="t3-switch" min="1" max="10" step="1" value="3" oninput="updateTab3()">
                    </div>
                    <div class="form-group">
                        <label>월 최대 상환 가능액 (원) <span style="font-weight:normal; font-size:0.8em;">(이자+원금)</span></label>
                        <input type="number" id="t3-payment" value="1500000" step="100000" oninput="updateTab3()">
                    </div>
                    
                    <div class="result-box" style="margin-top: 20px;">
                        <p style="margin:0;">예상 상환 완료: <strong id="t3-result-time" style="color:var(--success); font-size:1.2em;">-</strong></p>
                        <p style="margin: 10px 0 0 0; font-size:0.9em; color:var(--danger);" id="t3-error-msg"></p>
                    </div>
                </div>
                <div>
                    <canvas id="chartTab3" style="max-height: 350px;"></canvas>
                </div>
            </div>
        </div>'''
        
        old_init_charts = '''        function initCharts() {
            const ctx2 = document.getElementById('chartTab2').getContext('2d');
            chart2 = new Chart(ctx2, {
                type: 'line',
                data: { labels: [], datasets: [{ 
                    label: '월 이자 부담액 (원)', 
                    data: [], 
                    borderColor: '#4f46e5', 
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#4f46e5',
                    pointRadius: 4
                }] },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                    plugins: { 
                        tooltip: { callbacks: { label: function(context) { return Math.round(context.raw).toLocaleString() + '원'; } } },
                        legend: { labels: { font: { family: 'inherit', weight: 'bold' } } } 
                    }
                }
            });

            const ctx3 = document.getElementById('chartTab3').getContext('2d');
            chart3 = new Chart(ctx3, {
                type: 'bar',
                data: { labels: ['감당 가능한 월 이자'], datasets: [{ 
                    label: '월 이자액 (원)', 
                    data: [], 
                    backgroundColor: '#10b981',
                    borderRadius: 8
                }] },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    scales: { x: { beginAtZero: true } },
                    plugins: { 
                        tooltip: { callbacks: { label: function(context) { return Math.round(context.raw).toLocaleString() + '원'; } } }
                    }
                }
            });
            updateChartTheme();
        }'''
        
        new_init_charts = '''        function initCharts() {
            const ctx2 = document.getElementById('chartTab2').getContext('2d');
            chart2 = new Chart(ctx2, {
                type: 'line',
                data: { labels: [], datasets: [
                    { 
                        label: '이자 + 원금상환액 (원)', 
                        data: [], 
                        borderColor: '#10b981', 
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: false,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#10b981',
                        pointRadius: 4
                    },
                    { 
                        label: '월 이자 부담액 (원)', 
                        data: [], 
                        borderColor: '#4f46e5', 
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#4f46e5',
                        pointRadius: 4
                    }
                ] },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                    plugins: { 
                        tooltip: { callbacks: { label: function(context) { return Math.round(context.raw).toLocaleString() + '원'; } } },
                        legend: { labels: { font: { family: 'inherit', weight: 'bold' } } } 
                    }
                }
            });

            const ctx3 = document.getElementById('chartTab3').getContext('2d');
            chart3 = new Chart(ctx3, {
                type: 'line',
                data: { labels: [], datasets: [
                    { 
                        label: '월 최대 상환액 (이자+원금)', 
                        data: [], 
                        borderColor: '#10b981', 
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: false,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#10b981',
                        pointRadius: 4
                    },
                    { 
                        label: '월 이자액 (원)', 
                        data: [], 
                        borderColor: '#ef4444', 
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: true,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#ef4444',
                        pointRadius: 4
                    }
                ] },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                    plugins: { 
                        tooltip: { callbacks: { label: function(context) { return Math.round(context.raw).toLocaleString() + '원'; } } },
                        legend: { labels: { font: { family: 'inherit', weight: 'bold' } } } 
                    }
                }
            });
            updateChartTheme();
        }'''
        
        old_update_funcs = '''        function updateTab2() {
            const aptPrice = parseInt(document.getElementById('t2-apt').value);
            const switchYear = parseInt(document.getElementById('t2-switch').value);
            const period = parseInt(document.getElementById('t2-period').value);
            const monthlyPrincipal = parseInt(document.getElementById('t2-principal').value);

            document.getElementById('t2-apt-val').innerText = formatKRW(aptPrice);
            document.getElementById('t2-switch-val').innerText = switchYear + '년 뒤';
            document.getElementById('t2-period-val').innerText = period + '년';

            const loanAmount = aptPrice - BASE_CASH;
            document.getElementById('t2-loan-amount').innerText = formatKRW(loanAmount);

            const labels = [];
            const data = [];
            let currentLoan = loanAmount;
            
            // 보금자리론 평균 4.2%, 신생아 대출 평균 2.0% 가정
            const rate1 = 0.042; 
            const rate2 = 0.020;

            if (loanAmount <= 0) {
                chart2.data.labels = [];
                chart2.data.datasets[0].data = [];
                chart2.update();
                return;
            }
            
            for(let year = 1; year <= period; year++) {
                if(currentLoan <= 0) break;
                
                const currentRate = year <= switchYear ? rate1 : rate2;
                const monthlyInterest = currentLoan * (currentRate / 12);
                
                labels.push(`${year}년차`);
                data.push(Math.round(monthlyInterest));

                currentLoan -= (monthlyPrincipal * 12);
            }

            chart2.data.labels = labels;
            chart2.data.datasets[0].data = data;
            chart2.update();
        }

        function updateTab3() {
            const monthlyInterest = parseInt(document.getElementById('t3-interest').value) || 0;
            const rate = parseFloat(document.getElementById('t3-rate').value) / 100 || 0.042;
            
            let maxLoan = 0;
            if (rate > 0) {
                maxLoan = monthlyInterest / (rate / 12);
            }
            const aptPrice = maxLoan + BASE_CASH;

            document.getElementById('t3-max-loan').innerText = formatKRW(maxLoan);
            document.getElementById('t3-apt-price').innerText = formatKRW(aptPrice);

            chart3.data.datasets[0].data = [monthlyInterest];
            chart3.update();
        }'''

        new_update_funcs = '''        function updateTab2() {
            const aptPrice = parseInt(document.getElementById('t2-apt').value);
            const switchYear = parseInt(document.getElementById('t2-switch').value);
            const period = parseInt(document.getElementById('t2-period').value);
            const monthlyPrincipal = parseInt(document.getElementById('t2-principal').value);

            document.getElementById('t2-apt-val').innerText = formatKRW(aptPrice);
            document.getElementById('t2-switch-val').innerText = switchYear + '년 뒤';
            document.getElementById('t2-period-val').innerText = period + '년';

            const loanAmount = aptPrice - BASE_CASH;
            document.getElementById('t2-loan-amount').innerText = formatKRW(loanAmount);

            const labels = [];
            const interestData = [];
            const totalData = [];
            let currentLoan = loanAmount;
            
            // 보금자리론 평균 4.2%, 신생아 대출 평균 2.0% 가정
            const rate1 = 0.042; 
            const rate2 = 0.020;

            if (loanAmount <= 0) {
                chart2.data.labels = [];
                chart2.data.datasets[0].data = [];
                chart2.data.datasets[1].data = [];
                chart2.update();
                return;
            }
            
            for(let year = 1; year <= period; year++) {
                if(currentLoan <= 0) break;
                
                const currentRate = year <= switchYear ? rate1 : rate2;
                const monthlyInterest = currentLoan * (currentRate / 12);
                
                labels.push(`${year}년차`);
                interestData.push(Math.round(monthlyInterest));
                totalData.push(Math.round(monthlyInterest + monthlyPrincipal));

                currentLoan -= (monthlyPrincipal * 12);
            }

            chart2.data.labels = labels;
            chart2.data.datasets[0].data = totalData;
            chart2.data.datasets[1].data = interestData;
            chart2.update();
        }

        function updateTab3() {
            const aptPrice = parseInt(document.getElementById('t3-apt').value);
            const switchYear = parseInt(document.getElementById('t3-switch').value);
            const monthlyPayment = parseInt(document.getElementById('t3-payment').value);

            document.getElementById('t3-apt-val').innerText = formatKRW(aptPrice);
            document.getElementById('t3-switch-val').innerText = switchYear + '년 뒤';
            
            let loanAmount = aptPrice - BASE_CASH;
            const errorMsgEl = document.getElementById('t3-error-msg');
            const resultTimeEl = document.getElementById('t3-result-time');
            
            errorMsgEl.innerText = "";
            resultTimeEl.innerText = "-";

            const rate1 = 0.042; 
            const rate2 = 0.020;

            if (loanAmount <= 0) {
                resultTimeEl.innerText = "대출 불필요 (보유 자금으로 구매 가능)";
                chart3.data.labels = [];
                chart3.data.datasets[0].data = [];
                chart3.data.datasets[1].data = [];
                chart3.update();
                return;
            }

            let currentLoan = loanAmount;
            let month = 0;
            const labels = [];
            const interestData = [];
            const paymentData = [];
            
            const MAX_MONTHS = 1200; // 최대 100년 방지용
            
            while (currentLoan > 0 && month < MAX_MONTHS) {
                const currentYear = Math.floor(month / 12) + 1;
                const currentRate = currentYear <= switchYear ? rate1 : rate2;
                const monthlyInterest = currentLoan * (currentRate / 12);
                
                if (monthlyInterest >= monthlyPayment) {
                    errorMsgEl.innerText = "월 상환액이 이자보다 적거나 같아 상환이 불가능합니다.";
                    break;
                }
                
                const principalPaid = monthlyPayment - monthlyInterest;
                currentLoan -= principalPaid;
                month++;
                
                // 매년 첫 달 혹은 마지막 달의 데이터를 그래프에 표시
                if (month % 12 === 1 || currentLoan <= 0) {
                    labels.push(`${Math.ceil(month/12)}년차`);
                    interestData.push(Math.round(monthlyInterest));
                    paymentData.push(monthlyPayment);
                }
            }
            
            if (currentLoan <= 0) {
                const years = Math.floor(month / 12);
                const months = month % 12;
                let resultText = "";
                if (years > 0) resultText += `${years}년 `;
                if (months > 0 || years === 0) resultText += `${months}개월 `;
                resultText += "소요";
                resultTimeEl.innerText = resultText;
            }
            
            chart3.data.labels = labels;
            chart3.data.datasets[0].data = paymentData;
            chart3.data.datasets[1].data = interestData;
            chart3.update();
        }'''

        content = content.replace(old_tab3_html, new_tab3_html)
        content = content.replace(old_init_charts, new_init_charts)
        content = content.replace(old_update_funcs, new_update_funcs)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.log_action(agent_id, "MODIFY", file_path, "Updated for loan calculator enhancements")
        print("Successfully updated UI")
    finally:
        lock.release(file_path, agent_id)

if __name__ == '__main__':
    main()
