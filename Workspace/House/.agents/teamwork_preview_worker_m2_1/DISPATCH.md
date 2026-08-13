## 2026-08-12T08:12:07Z
You are teamwork_preview_worker_m2_1.
Your working directory is `/home/imnyj/Workspace/House/.agents/teamwork_preview_worker_m2_1`.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task is to write the complete, publication-ready Markdown report saved at `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`.

Read the following files carefully for complete data and structural specs:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m2/SCOPE.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_1/analysis_r1_r2.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/analysis_r3.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_3/analysis_r4_outline.md`

Requirements for `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`:
1. **Executive Summary & Overview**: Concise summary of findings, key recommendations, and decision matrix.
2. **R1. 일회성 비용 전수조사 (One-off Transaction Costs)**:
   - Scenarios: 3.5억, 3.75억, 4.0억 원.
   - Items: 취득세(2025-2026 이원화 세율 & 생애첫주택 200만 원 감면), 법무사 수수료(~50만~55만 원), 중개보수 요율 상한(0.4%+VAT 10%=0.44%), 인지세(15만 원), 국민주택채권 할인 매입비(공시가 70% x 2.1~2.3% x 10%), 이사비(150만 원), 수리/입주청소비(200만 원).
   - Clear breakdown table for each scenario + total initial cash needed (매매가 + 일회성비용 - 대출금).
3. **R2. 대출 시나리오 비교 분석 및 핵심 소득 분석 (Mortgage Scenarios & Income Analysis)**:
   - 보유 현금 2.3억 원 기준 필요 대출금 (1.2억 / 1.45억 / 1.7억 원).
   - 디딤돌/보금자리론 vs 시중은행(KB국민/신한 등 연 4.25%) 비교.
   - **Crucial Income Analysis**: Document joint couple income (~1.33억~1.5억+ KRW with husband 5,296만 + wife 8,000만+) exceeding current Didimdol limit (8,500만 원), AND present government deregulation scenario (소득요건 완화/철폐 시 연 3.15% 디딤돌 적용으로 월 7.46만~10.57만 원, 30년 총 2,687만~3,807만 원 이자 절감 효과).
   - Secondary loan fees: 근저당권 설정비(은행 부담), 대출 인지세(7.5만 원 차주 부담), HF/HUG 보증료(연 0.05~0.1%).
4. **R3. 월별/연별 종합 재무 시뮬레이션 (Monthly & Annual Financial Simulation)**:
   - Monthly income (330만 원), 13 expense categories (월세 31.1만 원 삭제, 관리비 20만 원 + 주차비 1만 원 + 인터넷/TV 3만 원 추가 -> 순 고정지출 2,319,708원/월, 잉여 980,292원).
   - Bonus prepayment schedule: Jan/Jul 400만 원, Feb/Aug 100만 원 (Total 1,000만 원/년 중도상환).
   - Initial 1-year monthly schedule + annual summary table until 100% payoff for all 3 scenarios (3.5억, 3.75억, 4.0억).
   - Interest rate sensitivity analysis & payoff timeframe summary.
5. **R4. 행정 및 법률 신고 체크리스트 (Administrative Checklist)**:
   - Timeline: 부동산 거래신고 -> 잔금 및 열쇠 인수 -> 취득세 신고/납부 (생애첫주택 감면 신청, 3개월 내 전입 및 3년 실거주 조건) -> 소유권 이전 등기 및 채권/인지세 처리 -> 전입신고 및 은행 우대금리 등록 -> 재산세/종부세 관리.
   - Structured 6-column Markdown table (단계, 절차명, 법정 기한, 담당 기관, 필요 서류, 핵심 유의사항).
6. **Action Plan & Strategic Recommendations**: Practical step-by-step roadmap for contract execution, loan application, and financial risk management.

Language: Korean.
Quality: Publication-ready, comprehensive Markdown report with clean formatting, headers, tables, callout notes.

When finished, deliver `handoff.md` in your working directory `/home/imnyj/Workspace/House/.agents/teamwork_preview_worker_m2_1/` detailing your work and verification. Notify parent when completed.
