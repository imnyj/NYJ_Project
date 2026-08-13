# DISPATCH

## 2026-08-12T17:04:25Z
<USER_REQUEST>
You are the Project Orchestrator for the House Financial Simulation Project.

Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_1`
Please create your `BRIEFING.md` and maintain `progress.md` in your working directory.

## Project Requirements
Please read `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md` for full verbatim instructions and acceptance criteria. Key deliverables:
1. R1: Full Investigation of One-time Purchase Costs for Cheongju Bangseo-dong Xi Apartment (<30 pyeong, 3.5억, 3.75억, 4억 scenarios). Include acquisition tax (2025-2026 tax rates & exemptions), legal fee, broker fee (statutory cap), stamp duty, National Housing Bond purchase (discount rate applied), moving fee, repair/cleaning fees.
2. R2: Mortgage Scenario Comparative Analysis (Didimdol/Bogeumjari vs Commercial Bank). Include secondary loan fees (mortgage establishment fee, loan stamp tax, HF/HUG guarantee fees).
3. R3: Monthly Comprehensive Financial Simulation. Read `/home/imnyj/Workspace/House/Budget/8. 학기 중 예상 지출 보고서.md` to extract monthly income (330만 원), 13 expense categories (~239만 원), annual bonuses (Feb/Aug 교연비 500만 each, Jan/Jul 특강비 100만 each). Remove 월세 (31.1만) and replace with apartment maintenance fee, parking, internet/TV.
4. R4: Administrative & Legal Reporting Checklist (post-purchase timeline, deadlines, institutions, required documents).
5. R5: Interactive Web Simulator HTML (`/home/imnyj/Workspace/House/ui/index4.html`). Maintain glassmorphism UI style and Chart.js dual-axis graph from `ui/index3.html`. Support slider/inputs for price, cash, interest rate, duration. Real-time updates for initial cash required, monthly spending, remaining income, payoff timeline.
6. Comprehensive Markdown Financial Simulation Report saved in `/home/imnyj/Workspace/House/`.

Ensure all code/deliverables comply with GEMINI.md user rules (e.g., locking protocol if needed, Korean language output, clear atomization).

When finished, deliver your final report and notify Sentinel so victory audit can be conducted.
</USER_REQUEST>

## Follow-up — 2026-08-12T17:07:15Z
[사용자 추가 요구사항 전달 - 즉시 반영 요청]
1. 보유 현금: 총 2.3억 원 (본인 3,000만 + 본인 부모님 1억 + 은비네 부모님 1억)
2. 월 상환 능력: 월 주거 비용 부담 가능액 50만 원 (대출 원리금 상환용)
3. 보너스 투입 계획:
   - 1월 / 7월: 교연비 500만 원 중 400만 원 투입 (100만 원 개인 유보)
   - 2월 / 8월: 부가 소득 중 100만 원씩 투입
4. 연간 추가 상환 총액: (400만 × 2회) + (100만 × 2회) = 연 1,000만 원 보너스 상환
이 수치(연간 총 1,000만 원 상환, 1월/7월 400만, 2월/8월 100만)를 시뮬레이터(HTML) 및 MD 보고서 계산 로직과 기본값에 적용.

## Follow-up — 2026-08-12T17:10:19Z
[소득 관련 추가 데이터 및 대출 정책 지침 전달]
1. 소득 정보:
   - 본인 세전 월급 4,413,660원 (연 5,296만 원) / 세후 330만 원
   - 배우자(은비) 세금 900만 원 납부 고소득자 (추정 연소득 8,000만 원 이상)
   - 부부합산 추정 연소득: 약 1.3억~1.5억+ 원 (디딤돌 소득 기준 초과 가능성)
2. 지침:
   - R2 보고서: 디딤돌 소득 초과로 자격 미달 가능성 명시 + 규제 완화 시 대출 가능 시나리오 병기.
   - R5 시뮬레이터(ui/index4.html): 디딤돌 및 시중은행 금리를 슬라이더로 조절하여 규제 완화 적용 여부별 비교 가능토록 제작.


