# Project: LaTeX Manuscript Academic Revision & Verification

## Architecture
The project targets the comprehensive revision and refinement of `/home/imnyj/Workspace/paper4/latex/main.tex` according to strict academic style standards, IEEEtran formatting rules, structural table/list adjustments, mathematical consistency, and build validation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R2 Intro Contributions Formatting | Format Intro contributions (L72-L78) as `itemize` bullet list with polished academic prose | M1 | Survey (Explorer 2) |
| 2 | R3 Table I Restructuring | Restructure Table I (L138-L163): remove Year column, replace author names with `\cite{}`, apply fixed-width `p{...}` / `L` wrapping, polish caption | M1 | Survey (Explorer 2) |
| 3 | R1.1 Exaggerated & Cliché Words Removal | Remove/replace all instances of `comprehensive` (6), `utilize` (1), `systematic` (1) with dry/clear words | M2 | Survey (Explorer 1) |
| 4 | R1.2 Source Filename Removal | Remove/rephrase all 8 internal `.csv` filename mentions in manuscript text (L632, L636, L719, L793, L822, L826, L912, L915) | M2 | Survey (Explorer 1) |
| 5 | R1.3 Parentheses & Acronym Reduction | Eliminate redundant acronym definitions (FSM, SAC, REMO-DQN) and convert data-dump parentheses to natural prose | M2 | Survey (Explorer 1) |
| 6 | R1.4 Paragraph Cohesion & Completeness | Merge and enrich 9 short fragmented paragraphs to ensure each paragraph has >=5 well-structured sentences | M2 | Survey (Explorer 1) |
| 7 | R4.1 Math Verification | Verify all 32 display equations and 303 inline math spans for LaTeX syntax and notation consistency | M3 | Survey (Explorer 3) |
| 8 | R4.2 Automated Validation Suite | Execute `etc/scripts/validate_latex.py` Tier 1-4 static checks and assertion scripts | M3 | Survey (Explorer 3) |
| 9 | R4.3 Overleaf Packaging & Gate | Generate and verify `paper4_latex_overleaf.zip` package via `make zip` | M3 | Survey (Explorer 3) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Structural Formatting (R2 & R3) | Intro contributions `itemize` and Table I restructuring | none | DONE |
| M2 | Academic Style & Cleansing (R1) | Forbidden words removal, filename removal, parentheses reduction, paragraph cohesion | M1 | DONE |
| M3 | Math Verification, Test & Packaging (R4) | Math validation, static checks Tier 1-4, `make zip` distribution package | M2 | DONE |

## Interface Contracts & Constraints
- **File Locking**: Any modification to `main.tex` must acquire file lock via `/home/imnyj/Command/core/lock_manager.py`.
- **Audit Logging**: Any modification to `main.tex` must be logged via `/home/imnyj/Command/core/audit_logger.py`.
- **Backup**: Before modifying `main.tex`, create a backup copy in `backup/`.
- **Auxiliary Files**: All scripts, temporary logs, and reports must be stored under `etc/` (e.g., `etc/scripts/`, `etc/logs/`) or `.agents/`.
- **No Hallucination**: Do not break LaTeX tags, environment pairings (`\begin{} ... \end{}`), equation labels (`\label{eq:...}`), figure labels (`\label{fig:...}`), table labels (`\label{tab:...}`), or BibTeX citation keys (`\cite{...}`).

## Code Layout
- Main Document: `/home/imnyj/Workspace/paper4/latex/main.tex`
- Bibliography: `/home/imnyj/Workspace/paper4/latex/references.bib`
- Class File: `/home/imnyj/Workspace/paper4/latex/IEEEtran.cls`
- Figures: `/home/imnyj/Workspace/paper4/latex/figures/`
- Build System: `/home/imnyj/Workspace/paper4/latex/Makefile`
- Validation Scripts: `/home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py`
- Backup Dir: `/home/imnyj/Workspace/paper4/latex/backup/`
- Distribution Output: `/home/imnyj/Workspace/paper4/latex/paper4_latex_overleaf.zip`
