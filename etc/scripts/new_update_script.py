import sys
import os

sys.path.append('/home/imnyj/Command/core')
from lock_manager import LockManager
from audit_logger import AuditLogger

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real Estate Loan Calculator</title>
    <style>
        :root {
            --bg-gradient-start: #f0f4f8;
            --bg-gradient-end: #e0eaf5;
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: rgba(255, 255, 255, 0.4);
            --glass-shadow: rgba(0, 0, 0, 0.1);
            --text-main: #2c3e50;
            --text-muted: #596a7b;
            --accent-primary: #3b82f6;
            --accent-secondary: #8b5cf6;
            --input-bg: rgba(255, 255, 255, 0.8);
            --input-focus-border: #3b82f6;
            --success: #10b981;
            --danger: #ef4444;
        }

        [data-theme="dark"] {
            --bg-gradient-start: #111827;
            --bg-gradient-end: #1f2937;
            --glass-bg: rgba(31, 41, 55, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: rgba(0, 0, 0, 0.5);
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --accent-primary: #60a5fa;
            --accent-secondary: #a78bfa;
            --input-bg: rgba(17, 24, 39, 0.8);
            --input-focus-border: #60a5fa;
            --success: #34d399;
            --danger: #f87171;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg-gradient-start), var(--bg-gradient-end));
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            transition: all 0.4s ease;
            padding-top: 40px;
            padding-bottom: 40px;
        }

        /* Abstract Background Shapes */
        .shape {
            position: fixed;
            filter: blur(80px);
            z-index: -1;
            opacity: 0.6;
            border-radius: 50%;
            animation: float 10s infinite ease-in-out alternate;
        }

        .shape-1 {
            top: -10%; left: -10%; width: 50vw; height: 50vw; background: var(--accent-primary);
        }
        
        .shape-2 {
            bottom: -10%; right: -10%; width: 40vw; height: 40vw; background: var(--accent-secondary); animation-delay: -5s;
        }

        @keyframes float {
            from { transform: translate(0, 0) scale(1); }
            to { transform: translate(20px, 30px) scale(1.05); }
        }

        .container {
            width: 90%;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 30px;
            border: 1px solid var(--glass-border);
            box-shadow: 0 25px 50px -12px var(--glass-shadow);
        }

        h1 {
            text-align: center;
            margin-bottom: 20px;
            font-size: 2.8em;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }

        .global-cash-section {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(139, 92, 246, 0.05));
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 25px;
            margin-bottom: 30px;
        }

        .global-cash-section h2 {
            font-size: 1.2em;
            margin-top: 0;
            margin-bottom: 20px;
            color: var(--text-muted);
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .total-cash-display {
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px dashed var(--glass-border);
        }

        .total-cash-display .label {
            font-size: 0.9em;
            color: var(--text-muted);
            margin-bottom: 5px;
        }

        .total-cash-display .value {
            font-size: 2.2em;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .tabs {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
        }

        .tab {
            padding: 12px 28px;
            border-radius: 40px;
            font-weight: 600;
            cursor: pointer;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            color: var(--text-muted);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .tab:hover {
            transform: translateY(-2px);
            color: var(--text-main);
            border-color: var(--accent-primary);
        }

        .tab.active {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border-color: transparent;
            box-shadow: 0 10px 20px -10px var(--accent-primary);
        }

        .tab-content {
            display: none;
            animation: slideUp 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
            opacity: 0;
            transform: translateY(20px);
        }

        .tab-content.active {
            display: block;
        }

        @keyframes slideUp {
            to { opacity: 1; transform: translateY(0); }
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .form-group label {
            font-size: 0.95em;
            font-weight: 600;
            color: var(--text-main);
            margin-left: 4px;
        }

        .form-group input {
            width: 100%;
            padding: 16px 20px;
            border-radius: 16px;
            border: 1px solid var(--glass-border);
            background: var(--input-bg);
            color: var(--text-main);
            font-size: 1.1em;
            font-weight: 500;
            box-sizing: border-box;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: var(--input-focus-border);
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
            transform: translateY(-1px);
        }

        .result-card {
            margin-top: 30px;
            padding: 30px;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
            border: 1px solid rgba(139, 92, 246, 0.2);
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .result-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
        }

        .result-card h3 {
            margin: 0;
            font-size: 1.1em;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .main-result {
            font-size: 3em;
            font-weight: 800;
            margin: 15px 0;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .details-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px solid var(--glass-border);
        }

        .detail-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .detail-label {
            font-size: 0.9em;
            color: var(--text-muted);
        }

        .detail-value {
            font-size: 1.3em;
            font-weight: 700;
            color: var(--text-main);
        }

        .theme-toggle {
            position: fixed;
            top: 24px;
            right: 24px;
            padding: 12px 20px;
            border-radius: 30px;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            font-weight: 600;
            cursor: pointer;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 6px -1px var(--glass-shadow);
            transition: all 0.3s ease;
            z-index: 100;
        }

        .theme-toggle:hover {
            transform: scale(1.05);
            background: var(--input-bg);
        }

        /* Strategies Tab Styles */
        .strategies-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }

        .strategy-card {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 10px 30px -10px var(--glass-shadow);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
            text-align: left;
        }

        .strategy-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px -15px var(--glass-shadow);
            border-color: var(--accent-primary);
        }

        .strategy-card h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--text-main);
            font-size: 1.25em;
            line-height: 1.4;
        }

        .strategy-number {
            display: inline-block;
            padding: 4px 10px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .pros-cons {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .pro-con-section h4 {
            margin: 0 0 8px 0;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pro-con-section.pro h4 {
            color: var(--success);
        }

        .pro-con-section.con h4 {
            color: var(--danger);
        }

        .pro-con-section p {
            margin: 0;
            font-size: 0.95em;
            color: var(--text-muted);
            line-height: 1.5;
        }

        @media (max-width: 768px) {
            .details-grid { grid-template-columns: 1fr; gap: 15px; }
            .container { padding: 25px; width: 95%; margin: 20px auto; }
            .main-result { font-size: 2.2em; }
            h1 { font-size: 2em; }
            .tabs { flex-direction: column; }
            .tab { text-align: center; }
        }
    </style>
</head>
<body>
    <div class="shape shape-1"></div>
    <div class="shape shape-2"></div>

    <button class="theme-toggle" id="themeToggle" aria-label="Toggle Theme">
        <span id="themeIcon">🌙</span> <span id="themeText">Dark Mode</span>
    </button>

    <div class="container">
        <h1>Real Estate Insights</h1>

        <!-- Global Cash Breakdown Section -->
        <div class="global-cash-section">
            <h2>Available Cash Breakdown</h2>
            <div class="form-grid">
                <div class="form-group">
                    <label>My Asset (KRW)</label>
                    <input type="text" id="g-asset" value="100,000,000" inputmode="numeric">
                </div>
                <div class="form-group">
                    <label>My Parents' Support (KRW)</label>
                    <input type="text" id="g-parents" value="100,000,000" inputmode="numeric">
                </div>
                <div class="form-group">
                    <label>Eunbi's Parents' Support (KRW)</label>
                    <input type="text" id="g-eunbi" value="40,000,000" inputmode="numeric">
                </div>
            </div>
            <div class="total-cash-display">
                <div class="label">Total Available Cash</div>
                <div class="value" id="g-total-cash">240,000,000 KRW</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" data-target="calc-payment">Payment Calculator</div>
            <div class="tab" data-target="calc-budget">Budget Explorer</div>
            <div class="tab" data-target="strategies">Purchase Strategies</div>
        </div>

        <!-- Tab 1: Calculate Payment -->
        <div id="calc-payment" class="tab-content active">
            <div class="form-grid">
                <div class="form-group">
                    <label>Apartment Price (KRW)</label>
                    <input type="text" id="p-price" value="500,000,000" inputmode="numeric">
                </div>
                <div class="form-group">
                    <label>Annual Interest Rate (%)</label>
                    <input type="number" id="p-rate" value="4.0" step="0.1" inputmode="decimal">
                </div>
                <div class="form-group">
                    <label>Loan Period (Years)</label>
                    <input type="number" id="p-years" value="30" inputmode="numeric">
                </div>
            </div>

            <div class="result-card">
                <h3>Estimated Monthly Payment</h3>
                <div class="main-result" id="p-monthly">0 KRW</div>
                <div class="details-grid">
                    <div class="detail-item">
                        <span class="detail-label">Total Loan Amount</span>
                        <span class="detail-value" id="p-loan">0 KRW</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Total Payment (Principal + Interest)</span>
                        <span class="detail-value" id="p-total">0 KRW</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 2: Inverse Calculator (Budget Explorer) -->
        <div id="calc-budget" class="tab-content">
            <div class="form-grid">
                <div class="form-group">
                    <label>Target Monthly Payment (KRW)</label>
                    <input type="text" id="b-monthly" value="1,500,000" inputmode="numeric">
                </div>
                <div class="form-group">
                    <label>Annual Interest Rate (%)</label>
                    <input type="number" id="b-rate" value="4.0" step="0.1" inputmode="decimal">
                </div>
                <div class="form-group">
                    <label>Loan Period (Years)</label>
                    <input type="number" id="b-years" value="30" inputmode="numeric">
                </div>
            </div>

            <div class="result-card">
                <h3>Max Affordable Apartment</h3>
                <div class="main-result" id="b-max-price">0 KRW</div>
                <div class="details-grid">
                    <div class="detail-item">
                        <span class="detail-label">Max Loan Amount</span>
                        <span class="detail-value" id="b-loan">0 KRW</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Total Payment (Principal + Interest)</span>
                        <span class="detail-value" id="b-total">0 KRW</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 3: Strategies -->
        <div id="strategies" class="tab-content">
            <div class="strategies-grid">
                <!-- Strategy 1 -->
                <div class="strategy-card">
                    <span class="strategy-number">Strategy 1</span>
                    <h3>Buy with Bogeumjari as single before marriage &rarr; Refinance to Newborn Special later</h3>
                    <div class="pros-cons">
                        <div class="pro-con-section pro">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg> Pros</h4>
                            <p>Can secure a house now with relatively good rates. Lower threshold for single household. Smooth transition to Newborn Special later.</p>
                        </div>
                        <div class="pro-con-section con">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg> Cons</h4>
                            <p>Bogeumjari limits property value (e.g., under 600M KRW) and income. Requires being single on paper initially.</p>
                        </div>
                    </div>
                </div>

                <!-- Strategy 2 -->
                <div class="strategy-card">
                    <span class="strategy-number">Strategy 2</span>
                    <h3>Buy with Regular loans &rarr; Refinance to Newborn Special later</h3>
                    <div class="pros-cons">
                        <div class="pro-con-section pro">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg> Pros</h4>
                            <p>No property value or income limits for the initial purchase. Can buy a better or more expensive apartment right now.</p>
                        </div>
                        <div class="pro-con-section con">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg> Cons</h4>
                            <p>Higher initial interest rates and monthly burden. Refinancing depends heavily on Newborn Special policies at that time.</p>
                        </div>
                    </div>
                </div>

                <!-- Strategy 3 -->
                <div class="strategy-card">
                    <span class="strategy-number">Strategy 3</span>
                    <h3>Persuade parents to sell Officetel</h3>
                    <div class="pros-cons">
                        <div class="pro-con-section pro">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg> Pros</h4>
                            <p>Significant increase in Available Cash. Reduces or completely eliminates the need for high-interest loans. Lower monthly burden.</p>
                        </div>
                        <div class="pro-con-section con">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg> Cons</h4>
                            <p>Difficult to persuade parents. Loss of regular rental income from the Officetel. Potential tax implications on the sale.</p>
                        </div>
                    </div>
                </div>

                <!-- Strategy 4 -->
                <div class="strategy-card">
                    <span class="strategy-number">Strategy 4</span>
                    <h3>Live in Eunbi's parent's annex temporarily</h3>
                    <div class="pros-cons">
                        <div class="pro-con-section pro">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg> Pros</h4>
                            <p>Save massive amounts of money on rent and interest. Can build up assets over time. Flexibility to buy a much better place later.</p>
                        </div>
                        <div class="pro-con-section con">
                            <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg> Cons</h4>
                            <p>Lack of complete independence. Potential friction or discomfort. Delays building equity in own real estate.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
        // Formatting numbers with commas on input
        function setupNumberInput(id) {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', function(e) {
                // Allow only digits
                let val = this.value.replace(/[^0-9]/g, '');
                if (val === '') {
                    this.value = '';
                } else {
                    this.value = parseInt(val, 10).toLocaleString('en-US');
                }
                updateCalculations();
            });
        }

        function getNumber(id) {
            const el = document.getElementById(id);
            if (!el) return 0;
            return parseFloat(el.value.replace(/,/g, '')) || 0;
        }

        function setFormatted(id, value) {
            const el = document.getElementById(id);
            if (!el) return;
            el.textContent = Math.round(value).toLocaleString('en-US') + ' KRW';
        }

        // Calculations
        function updateCalculations() {
            // Calculate Total Cash
            const asset = getNumber('g-asset');
            const parents = getNumber('g-parents');
            const eunbi = getNumber('g-eunbi');
            const totalCash = asset + parents + eunbi;
            
            setFormatted('g-total-cash', totalCash);

            // Payment Calculation (Tab 1)
            const price = getNumber('p-price');
            const pRate = getNumber('p-rate');
            const pYears = getNumber('p-years');

            let pLoanAmount = Math.max(0, price - totalCash);
            setFormatted('p-loan', pLoanAmount);

            if (pLoanAmount === 0 || pYears === 0) {
                setFormatted('p-monthly', 0);
                setFormatted('p-total', 0);
            } else {
                const r = (pRate / 100) / 12;
                const n = pYears * 12;
                let monthlyPayment = 0;
                
                if (r === 0) {
                    monthlyPayment = pLoanAmount / n;
                } else {
                    monthlyPayment = pLoanAmount * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
                }
                
                setFormatted('p-monthly', monthlyPayment);
                setFormatted('p-total', monthlyPayment * n);
            }

            // Budget Calculation (Tab 2)
            const bMonthly = getNumber('b-monthly');
            const bRate = getNumber('b-rate');
            const bYears = getNumber('b-years');
            
            if (bYears > 0) {
                const r = (bRate / 100) / 12;
                const n = bYears * 12;
                let bMaxLoan = 0;
                
                if (r === 0) {
                    bMaxLoan = bMonthly * n;
                } else {
                    bMaxLoan = bMonthly * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n));
                }
                
                setFormatted('b-loan', bMaxLoan);
                setFormatted('b-max-price', bMaxLoan + totalCash);
                setFormatted('b-total', bMonthly * n);
            } else {
                setFormatted('b-loan', 0);
                setFormatted('b-max-price', totalCash);
                setFormatted('b-total', 0);
            }
        }

        // Setup Event Listeners
        ['g-asset', 'g-parents', 'g-eunbi', 'p-price', 'b-monthly'].forEach(setupNumberInput);
        
        document.querySelectorAll('input[type="number"]').forEach(el => {
            el.addEventListener('input', updateCalculations);
        });

        // Tab Switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab, .tab-content').forEach(el => {
                    el.classList.remove('active');
                });
                tab.classList.add('active');
                document.getElementById(tab.dataset.target).classList.add('active');
            });
        });

        // Theme Toggle
        const themeToggle = document.getElementById('themeToggle');
        themeToggle.addEventListener('click', () => {
            const isDark = document.body.getAttribute('data-theme') === 'dark';
            if (isDark) {
                document.body.removeAttribute('data-theme');
                document.getElementById('themeIcon').textContent = '🌙';
                document.getElementById('themeText').textContent = 'Dark Mode';
            } else {
                document.body.setAttribute('data-theme', 'dark');
                document.getElementById('themeIcon').textContent = '☀️';
                document.getElementById('themeText').textContent = 'Light Mode';
            }
        });

        // Initial Calc
        updateCalculations();
    </script>
</body>
</html>"""

file_path = '/home/imnyj/Workspace/House/ui/index.html'
file_path = '/home/imnyj/Workspace/House/ui/index.html'

lock = LockManager()
logger = AuditLogger()

if lock.acquire(file_path, "UI_Updater"):
    try:
        with open(file_path, 'w') as f:
            f.write(html_content)
        logger.log_action("UI_Updater", "MODIFY", file_path, "Updated UI to include Total Cash dynamic calculation and 4 Purchase Strategies.")
        print("Successfully updated UI.")
    finally:
        lock.release(file_path, "UI_Updater")
else:
    print("Could not acquire lock.")
