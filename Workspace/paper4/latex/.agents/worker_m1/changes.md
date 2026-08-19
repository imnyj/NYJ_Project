# Changes Report — Milestone 1 (worker_m1)

**Date**: 2026-08-18T17:30:45+09:00  
**Agent**: worker_m1 (Milestone 1 Academic Worker)  
**Target File**: `/home/imnyj/Workspace/paper4/latex/main.tex`  
**Backup File**: `/home/imnyj/Workspace/paper4/latex/backup/main.tex.bak_m1`  

---

## 1. Summary of Changes

### A. Requirement R2: Introduction Contributions Formatting (Lines 72–78)
- **Itemize Structure Preservation & Refinement**: Reorganized the 4 core contribution items within the `\begin{itemize} ... \end{itemize}` environment.
- **Academic Writing Style Enforcement (R1 Alignment)**:
  - Replaced prohibited exaggerated word `Comprehensive` with `Multi-Model`.
  - Replaced cliché `first systematic empirical comparison` with `empirical evaluation`.
  - Converted parenthetical data dumps into natural academic prose:
    - `($\sigma=0.1008$)` $\rightarrow$ `with standard deviation 0.1008`
    - `(a modest 3.13\%p drop from 76.54\% at 10~veh/km)` $\rightarrow$ `, representing a 3.13\%p decrease from 76.54\% at 10~veh/km,`
    - `(3,205.96~ms)` and `(4,682.51~ms)` $\rightarrow$ `with 3,205.96~ms and Fixed 10~Hz with 4,682.51~ms`
    - `(1.4~MB memory)` $\rightarrow$ `, 1.4~MB memory,`
  - Replaced dramatic word `collapse` with `degrade`, and removed subjective modifier `merely`.

### B. Requirement R3: Related Works Table I Restructuring (Lines 138–163)
- **Year Column Deletion**: Removed the 2nd column (`Year`) from the table header and all 13 table rows, reducing column count from 6 to 5.
- **Author Names Elimination**: Replaced all author names, et al. phrases, and journal names in the Reference column with pure `\cite{...}` citation keys:
  - `ETSI TS 102 687 \cite{ETSI_TS_102_687, ETSI_TS_103_175}` $\rightarrow$ `\cite{ETSI_TS_102_687, ETSI_TS_103_175}`
  - `Ye \textit{et al.} (IEEE TVT) \cite{Ye2019Deep}` $\rightarrow$ `\cite{Ye2019Deep}`
  - `Hu \textit{et al.} (IEEE TWC) \cite{Hu2021Deep}` $\rightarrow$ `\cite{Hu2021Deep}`
  - `Zheng \textit{et al.} (IEEE T-ITS) \cite{Zheng2022Age}` $\rightarrow$ `\cite{Zheng2022Age}`
  - `Wang \textit{et al.} (IEEE TWC) \cite{Wang2023Multi}` $\rightarrow$ `\cite{Wang2023Multi}`
  - `Bhattacharyya \textit{et al.} (IEEE TVT) \cite{Bhattacharyya2024Hybrid}` $\rightarrow$ `\cite{Bhattacharyya2024Hybrid}`
  - `Liu \textit{et al.} (IEEE T-ITS) \cite{Liu2024Age}` $\rightarrow$ `\cite{Liu2024Age}`
  - `Kang \textit{et al.} (IEEE JSAC) \cite{Kang2024Task}` $\rightarrow$ `\cite{Kang2024Task}`
  - `Xu \textit{et al.} (IEEE COMST) \cite{Xu2025Mixture}` $\rightarrow$ `\cite{Xu2025Mixture}`
  - `Du \textit{et al.} (IEEE Network) \cite{Du2025Generative}` $\rightarrow$ `\cite{Du2025Generative}`
  - `Park \& Kim (IEEE WCL) \cite{Park2025Ensemble}` $\rightarrow$ `\cite{Park2025Ensemble}`
  - `Zhang \textit{et al.} (IEEE TMC/TWC) \cite{Zhang2026Generalizable}` $\rightarrow$ `\cite{Zhang2026Generalizable}`
  - Proposed model explicitly labeled as `\textbf{Proposed REMO-DQN}`.
- **Fixed Width & Auto-wrapping (`p{...}` & `L`)**:
  - Replaced unconstrained `l c l l c c` with `\begin{tabularx}{\textwidth}{>{\centering\arraybackslash}p{2.2cm} L L >{\centering\arraybackslash}p{2.0cm} >{\centering\arraybackslash}p{2.8cm}}`.
  - Column 1: `>{\centering\arraybackslash}p{2.2cm}` (Citation keys)
  - Column 2: `L` (`>{\raggedright\arraybackslash}X`) (Optimization Target)
  - Column 3: `L` (`>{\raggedright\arraybackslash}X`) (RL Algorithm Used)
  - Column 4: `>{\centering\arraybackslash}p{2.0cm}` (Baselines count)
  - Column 5: `>{\centering\arraybackslash}p{2.8cm}` (MoE / Ensemble status)
  - Prevents horizontal table overflow on standard two-column IEEEtran page format (`table*` spans full textwidth).
- **Caption Refinement**:
  - Replaced `\caption{Comprehensive Literature Comparison of V2X Congestion Control and RL Frameworks}` with `\caption{Comparison of Related Studies on V2X Congestion Control and RL Frameworks}`.

---

## 2. Concurrency & Safety Compliance

1. **Backup**: Created pre-modification backup `/home/imnyj/Workspace/paper4/latex/backup/main.tex.bak_m1`.
2. **File Lock Acquisition**: Acquired lock on `main.tex` via `LockManager` before modification.
3. **File Lock Release**: Released lock on `main.tex` via `LockManager` immediately after modification.
4. **Audit Logging**: Recorded change entry in `/tmp/agent_audit.log` via `AuditLogger`.

---

## 3. Verification Commands & Results

- **Validation Tool**: `python3 /home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py`
  - **Tier 1 (Base Assets & Figures)**: PASSED (9 figures, IEEEtran.cls, references.bib verified)
  - **Tier 2 (BibTeX 27 Keys)**: PASSED (27 unique keys verified)
  - **Tier 3 (LaTeX Environments & Delimiters)**: PASSED (All 14 tabularx, 5 table*, 2 itemize, 25 equation environments balanced, 302 math spans balanced)
  - **Tier 4 (In-Text Citations & Labels)**: PASSED (27 unique citation keys, 63 labels, 26 cross-references verified)
  - **Result**: `[SUCCESS] ALL INTEGRITY & VALIDATION CHECKS PASSED (0 ERRORS)`
- **Build Suite**: `make validate` $\rightarrow$ PASSED with exit code 0.
