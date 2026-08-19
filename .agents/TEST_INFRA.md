# E2E Test Infra: IEEE TWC LaTeX Publication Conversion

## Test Philosophy
- Requirement-driven verification based on `/home/imnyj/.agents/ORIGINAL_REQUEST.md`.
- Comprehensive multi-tier validation: File Integrity, Document Class & Preamble, Section Completeness, Mathematical Rigor, Quantitative Numerical Fidelity, BibTeX/Citation Integrity, Figure Integration, and Overleaf Package Self-Containment.

## Feature Inventory & Verification Matrix
| # | Feature | Target File | Verification Metric |
|---|---------|-------------|---------------------|
| F1 | BibTeX Database | `latex/references.bib` | 27 valid BibTeX entries, no syntax errors, all fields present |
| F2 | LaTeX Class & Environment | `latex/IEEEtran.cls`, `main.tex` | IEEEtran document class, standard compliant packages |
| F3 | Section Completeness | `latex/main.tex` | Title, Abstract, Keywords, Sec I (Intro), Sec II (Related), Sec III (Model & REMO-DQN), Sec IV (Scenarios), Sec V (Evaluation), Sec VI (Conclusion) |
| F4 | Mathematical Formulations | `latex/main.tex` | All 22 equation groups / 34 equations with amsmath environments, proper indexing, zero broken math tags |
| F5 | Tables Integration | `latex/main.tex` | 13/14 tables formatted in booktabs with IEEE two-column / table* layout, exact numerical values matching draft |
| F6 | Algorithm Pseudocode | `latex/main.tex` | Algorithm 1 formatted using algorithm + algpseudocode |
| F7 | Figure Assets & References | `latex/figures/`, `main.tex` | All 9 visualizer PNG figures copied to figures/ directory, properly referenced with \includegraphics and \ref |
| F8 | In-Text Citation Resolution | `latex/main.tex` | All 27 references cited via \cite{}, zero broken / undefined citation keys |
| F9 | Overleaf Package Readiness | `latex/paper4_latex_overleaf.zip` | Standalone archive with IEEEtran.cls, main.tex, references.bib, figures/ directory |

## Test Execution Tiers
- **Tier 1 (Structural & Syntax Validation)**: Python AST / regex syntax validator verifying balanced LaTeX environments (\begin{} / \end{}), math delimiters ($$, \begin{equation}), balanced braces, and file existence.
- **Tier 2 (Citation & Cross-Reference Validation)**: Verification script ensuring every \cite{} matches a key in references.bib, and all 27 references are cited; every \ref{} matches a declared \label{}.
- **Tier 3 (Numerical & Equation Fidelity)**: Verification comparing all table values (PDR 73.41%, AoI 373.21 ms, CBR 0.3442, MACs 3.8M, etc.) and equation constants ($w_1=0.01, w_2=1.0, w_3=0.10$, $m=3.0$, $\lambda_{LB}=0.01$) against the master draft.
- **Tier 4 (Packaging & Overleaf Self-Containment)**: Verification of zip archive integrity, relative figure paths, and presence of IEEEtran.cls.
