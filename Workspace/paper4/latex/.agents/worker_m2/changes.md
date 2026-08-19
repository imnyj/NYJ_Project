# Milestone 2 Modification Log (changes.md)

- **Agent**: worker_m2 (Academic Worker)
- **Target File**: `/home/imnyj/Workspace/paper4/latex/main.tex`
- **Scope**: Milestone 2 — R1 Academic Writing Style Enforcement
- **Date**: 2026-08-18

---

## 1. Summary of Changes

Milestone 2 addressed all requirements of R1 (Academic Writing Style Enforcement) in `/home/imnyj/Workspace/paper4/latex/main.tex`, specifically:
1. **R1.1 Forbidden & Exaggerated Words Removal**:
   - Replaced all 4 remaining occurrences of `comprehensive` in text (Abstract, Intro, Section V-A, Section VI) with `extensive`, `broad`, or `detailed`.
   - Replaced `utilize` in Section II-C with `use`.
   - Confirmed 0 occurrences of prohibited marketing/AI words (`elucidate`, `seamless`, `vital`, `fosters`, `significantly`, `substantially`, `leveraging`, `subsequently`, `effectively`, `encapsulates`).
   - Retained standardized domain proper nouns (`Connected and Autonomous Vehicles`, `autonomous sensing`).
2. **R1.2 Codebase / CSV Filename Removal**:
   - Eliminated all 8 internal `.csv` filenames from Section V (`cbr_trace.csv`, `pdr_vs_density.csv`, `aoi_vs_density.csv`, `pdr_vs_distance.csv`, `hardware_feasibility.csv`, `ablation_study.csv`, `moe_routing.csv`, `tsne_clustering.csv`).
   - Replaced with natural academic phrasing describing experimental configurations and conditions.
3. **R1.3 Parentheses Reduction & Redundant Acronym Elimination**:
   - Removed duplicate acronym expansions for `FSM` in Section II-A, `SAC` in Section II-B, and `REMO-DQN` in Section I.
   - Converted data-dump parenthetical listings (in Abstract, Intro, Section II, Section IV, Section V, Section VI) into natural academic prose.
4. **R1.4 Paragraph Cohesion & Completeness ($\ge 5$ Sentences)**:
   - Merged and enriched short fragmented paragraphs across Abstract, Section I, Section II, Section III-D, Section IV, Section V, and Section VI to ensure all narrative paragraphs contain at least 5 complete, logical, and academically sound sentences.

---

## 2. Detailed Line-by-Line Changes

| Section | Line / Area | Before (Original Text Snippet) | After (Revised Academic Text Snippet) | Rationale |
|---|---|---|---|---|
| Abstract | L51 | `Comprehensive empirical evaluations...` | `Extensive empirical evaluations...` | R1.1 Exaggerated word removal |
| Abstract | L52 | 4 sentences in Abstract Para 1 & 2 | Added concluding academic sentences to both paragraphs (5 sentences each) | R1.4 Paragraph completeness |
| Section I | L66 | `(ETSI TS 102 687), notably reactive control (ReactDCC) and adaptive linear control (AdaptDCC)...` | `Standard ETSI DCC protocols \cite{ETSI_TS_102_687, ETSI_TS_103_175}, namely reactive control (ReactDCC) and adaptive linear control (AdaptDCC)...` | R1.3 Parentheses reduction |
| Section I | L68 | `...lacks comprehensive, standardized empirical benchmarks...` | `...lacks extensive, standardized empirical benchmarks...` | R1.1 Exaggerated word removal |
| Section I | L70 | `...introduce REMO-DQN (Resource-Efficient Multi-Objective Deep Q-Network)...` | `...introduce REMO-DQN, an integrated modular framework...` | R1.3 Redundant acronym expansion removal |
| Section II-A | L89-109 | Fragmented rule-based discussion | Expanded context on ETSI DCC, FSM parameter switching, and linear feedback | R1.4 Paragraph completeness |
| Section II-A | L91 | `ReactDCC (ETSI TS 102 687 Annex B) adopts a Finite State Machine (FSM)...` | `ReactDCC \cite{ETSI_TS_103_175} adopts an FSM...` | R1.3 Redundant acronym definition removal |
| Section II-B | L126 | `Soft Actor-Critic (SAC) maximizes...` | `SAC maximizes expected return...` | R1.3 Redundant acronym definition removal |
| Section II-B | L133 | Single 1-sentence paragraph listing 4 limitations | Expanded to 5 full analytical sentences discussing vehicular DRL bottlenecks | R1.4 Paragraph completeness |
| Section II-C | L166 | `...utilize centralized critics...` | `...use centralized critics...` | R1.1 Cliché verb replacement |
| Section II-C | L173 | 2-sentence paragraph on MADRL bottlenecks | Expanded to 5 full sentences explaining wireless signaling and MCU constraints | R1.4 Paragraph completeness |
| Section II-D | L183 | 4-sentence paragraph with parentheses specs | Expanded to 5 full sentences with natural prose specs | R1.3 & R1.4 Paragraph completeness & parentheses reduction |
| Section III-D | L444 | 1-sentence paragraph | Expanded to 5 full sentences describing physical, MAC, and Dec-MDP parameters | R1.4 Paragraph completeness |
| Section IV-A--D | L453-478 | Fragmented sub-paragraphs | Expanded each subsection paragraph to 5 full sentences with cross-layer discussion | R1.4 Paragraph completeness & parentheses reduction |
| Section V-A | L520, L522 | `comprehensive comparison`, short intro | Replaced `comprehensive` with `broad`, added radio propagation and tuning sentences | R1.1 & R1.4 Paragraph completeness |
| Section V-B | L594, L596 | `(PPO, Actor-Critic, SAC, TD3)`, `(final reward ...)` | Converted to prose, expanded convergence discussion to 5 sentences per paragraph | R1.3 & R1.4 Parentheses reduction & paragraph completeness |
| Section V-C | L632 | `(`cbr_trace.csv`)` | Removed filename, expanded CBR stabilization discussion to 5 sentences | R1.2 & R1.4 Filename removal & paragraph completeness |
| Section V-D | L636, L638 | `(`pdr_vs_density.csv`)`, 3-fold data-dump parens | Removed filename, converted parenthetical lists to prose, merged into 6-sentence paragraph | R1.2, R1.3, R1.4 Filename, parentheses & paragraph completeness |
| Section V-E | L706-721 | `(`aoi_vs_density.csv`)`, parentheses data dump | Removed filename, expanded theoretical AoI and true AoI evaluation to 5+ sentences | R1.2, R1.3, R1.4 Filename, parentheses & paragraph completeness |
| Section V-F | L793 | `(`pdr_vs_distance.csv`)` | Removed filename, converted parenthetical comparisons to prose (6 sentences) | R1.2, R1.3, R1.4 Filename, parentheses & paragraph completeness |
| Section V-G | L822 | `(`hardware_feasibility.csv`)` | Removed filename, expanded MCU real-time headroom discussion to 5 sentences | R1.2 & R1.4 Filename removal & paragraph completeness |
| Section V-H | L826 | `(`ablation_study.csv`)` | Removed filename, converted component metrics to prose (5 sentences) | R1.2, R1.3, R1.4 Filename, parentheses & paragraph completeness |
| Section V-H | L912 | `(`moe_routing.csv`)` | Removed filename, expanded routing weight dynamics discussion to 5 sentences | R1.2 & R1.4 Filename removal & paragraph completeness |
| Section V-H | L915 | `(`tsne_clustering.csv`)` | Removed filename, expanded geometric cluster separation discussion to 5 sentences | R1.2 & R1.4 Filename removal & paragraph completeness |
| Section VI | L933 | `Comprehensive evaluations...` | `Extensive evaluations...` | R1.1 Exaggerated word removal |
| Section VI | L935 | Single 1-sentence future work paragraph | Expanded to 5 full sentences covering 5G-NR Mode 2(b), multimodal sensing, FL, and FOTs | R1.4 Paragraph completeness & parentheses reduction |

---

## 3. Verification Commands & Outputs

1. **LaTeX Integrity & Syntax Validator (`etc/scripts/validate_latex.py`)**:
   - Result: `[SUCCESS] ALL INTEGRITY & VALIDATION CHECKS PASSED (0 ERRORS)`
2. **Forbidden / Exaggerated Words Scan**:
   - `elucidate`, `seamless`, `vital`, `fosters`, `comprehensive`, `significantly`, `substantially`, `leveraging`, `utilizing`, `utilize`, `subsequently`, `systematically`, `encapsulates`: **0 found**.
   - Allowed proper nouns: `Connected and Autonomous Vehicles` (L64), `autonomous sensing` (L931) — verified.
3. **Exposed Filename Scan**:
   - `.csv`, `.py`, `.sh`, `.json`: **0 found** in manuscript text.
4. **Parentheses Data-Dump Scan**:
   - Raw data-dump parenthetical patterns: **0 found**.
5. **Paragraph Sentence Count Verification**:
   - All prose paragraphs in Abstract, Intro, Related Works, Dynamic Operational Workflow, Performance Evaluation, and Conclusion: **$\ge 5$ sentences per paragraph** verified.
