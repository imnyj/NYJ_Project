## 2026-08-12T08:10:27Z
You are teamwork_preview_orchestrator_m3, Sub-Orchestrator for Milestone 3 (Interactive Web Simulator).
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m3`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_2/survey_ui.md`
- Existing template `/home/imnyj/Workspace/House/ui/index3.html`

Your Scope (Milestone 3):
Develop the interactive web simulator HTML file saved at `/home/imnyj/Workspace/House/ui/index4.html`.
Requirements:
1. **Design System**: Maintain Glassmorphism UI style, dark mode toggle (`toggleTheme()`), ambient background blobs, responsive layout matching `index3.html`.
2. **Interactive Controls**:
   - Price selector/slider (3.5억, 3.75억, 4.0억 presets & continuous slider 3.0억~5.0억)
   - Cash available slider (default 2.3억 원)
   - Didimdol interest rate slider (~3.0~3.3%) and Commercial bank interest rate slider (~3.8~4.5%) for flexible deregulation comparative analysis
   - Loan duration slider (10~30 years)
   - Bonus prepayment toggle/inputs (default 1,000만/yr: Jan/Jul 400만, Feb/Aug 100만)
3. **Real-time Recalculations & Indicators**:
   - Initial cash required total (price + R1 one-time costs)
   - Monthly total spending (loan P+I + maintenance + living expenses)
   - Monthly remaining income (330만 - total spending)
   - Loan payoff timeline (exact year & month)
4. **Chart.js Dual-axis Graph**:
   - Left Y-axis: Monthly expenditure (interest, principal, bonus bar chart)
   - Right Y-axis: Loan balance curve (`drawOnChartArea: false`)
   - Real-time chart update on input change
5. **No External Runtime Errors**: Must run seamlessly in browser without console errors.

Execute via Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate loop. Record dead ends in DEAD_ENDS.md and gate status in GATE_STATUS.md in your working directory.
Follow GEMINI.md rules, Korean language output, and save to `/home/imnyj/Workspace/House/ui/index4.html`. When complete, set M3 status to DONE in PROJECT.md and deliver your handoff.md.
