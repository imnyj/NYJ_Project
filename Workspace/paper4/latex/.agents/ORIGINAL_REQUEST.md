# Original User Request

## 2026-08-18T08:25:11Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Revise the completed LaTeX document based on strict academic guidelines.

Working directory: /home/imnyj/Workspace/paper4/latex

## Requirements

### R1. Academic Writing Style Enforcement
Revise the text in `main.tex` strictly following these rules:
- **No Exaggerated Words**: Remove/replace `elucidate`, `seamless`, `vital`, `fosters`, `comprehensive`, `significantly`, `substantially`. Use dry, clear words (`explain`, `detail`, `uninterrupted`, `essential`, `reduces`).
- **No AI Clichés**: Remove/replace `leveraging/leverages`, `utilizing`, `subsequently`, `systematically`, `effectively`, `autonomously`, `encapsulates`.
- **Parentheses Reduction**: Remove unnecessary parentheses (e.g., for redundant acronym definitions or side notes). Convert them into natural prose.
- **No Filenames**: Do NOT mention any file names (e.g., `main.tex`, `sim_engine.py`) in the manuscript text. Readers cannot see the codebase.

### R2. Introduction Contributions Formatting
- The contributions section in the Introduction MUST be formatted using an `itemize` environment. (This is the only exception to any general 'no itemize' rules).

### R3. Related Works Table Restructuring
Revise the comparison table in the Related Works section:
- **Remove Authors**: Do not write author names. Represent the paper solely with the `\cite{}` command.
- **Remove Year Column**: Delete the 'Year' column entirely.
- **Width Management**: Use fixed-width column specifiers (e.g., `p{3cm}`) for text-heavy columns to allow automatic line wrapping, preventing the table from overflowing the page width.

### R4. Mathematical Expression Verification
- Thoroughly verify all mathematical expressions, equations, and inline math variables to ensure correct LaTeX syntax and notation consistency.

## Acceptance Criteria
- [ ] No prohibited AI expressions exist in the revised `main.tex`.
- [ ] The contributions in the introduction are bulleted (`itemize`).
- [ ] No file names appear in the manuscript text.
- [ ] The related works table uses `\cite{}` only, has no Year column, and uses `p{}` columns for line wrapping.
- [ ] All LaTeX equations compile correctly without syntax errors.
