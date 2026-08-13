# Scope: Milestone 3 (Interactive Web Simulator)

## Architecture
- Standalone HTML/CSS/JS file: `/home/imnyj/Workspace/House/ui/index4.html`
- Uses Tailwind CSS CDN / Glassmorphic CSS styles, Chart.js CDN for dual-axis charts, Lucide icons (or SVG/FontAwesome matching index3.html).
- Client-side calculation engine for loan amortization, Didimdol vs Commercial bank split, bonus prepayments, monthly spending/remaining income, and cash requirement.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| M3-1 | Design System | Glassmorphism, dark mode toggle (`toggleTheme()`), ambient background blobs, responsive layout matching index3.html | M3 | User Request |
| M3-2 | Interactive Controls | Price presets (3.5/3.75/4.0억) & continuous slider (3.0~5.0억), Cash available slider (default 2.3억), Didimdol (3.0~3.3%) & Commercial bank (3.8~4.5%) interest rate sliders, Loan duration slider (10~30 yrs), Bonus prepayment toggle/inputs (default 1000만/yr) | M3 | User Request |
| M3-3 | Real-time Recalculations | Initial cash required (price + R1 one-time costs), Monthly total spending (P+I + maintenance + living), Monthly remaining income (330만 - total spending), Loan payoff timeline (exact year & month) | M3 | User Request |
| M3-4 | Chart.js Dual-axis Graph | Left Y-axis: Monthly expenditure (interest, principal, bonus bar chart); Right Y-axis: Loan balance curve (`drawOnChartArea: false`); Real-time chart update | M3 | User Request |
| M3-5 | Error-Free Runtime | Zero console errors, responsive, clean UX | M3 | User Request |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M3 | Interactive Web Simulator | Complete index4.html implementation | M1, M2 | IN_PROGRESS |

## Interface Contracts
- Input: User selections/sliders in index4.html
- Output: Dynamic UI updates, Chart.js rendering, real-time KPI indicator cards.
