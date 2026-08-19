# Original User Request

## 2026-08-18T04:39:54Z

# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Convert the finalized Korean master draft into a publication-ready IEEE TWC LaTeX document in academic English.

Working directory: /home/imnyj/Workspace/paper4/latex

## Requirements

### R1. Translation to Academic English
Translate the entire content of `/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md` into highly professional, formal academic English suitable for IEEE Transactions on Wireless Communications (TWC). The tone must be dry, objective, and highly technical.

### R2. IEEE TWC LaTeX Formatting
Use the standard `IEEEtran` document class (`\documentclass[journal]{IEEEtran}`). Output a complete `main.tex` file that is ready to be compiled in Overleaf without structural errors. 

### R3. Tables, Equations, and Figures
- Convert all markdown tables from the draft into proper LaTeX `table` and `tabular` environments, ensuring they fit within the two-column format (or using `table*` for wide tables).
- Ensure all mathematical equations (MDP formulation, multi-objective rewards, REMO-DQN architecture) are correctly formatted using `amsmath` and standard LaTeX math modes.
- Insert `figure` environments for all graphs mentioned in the text, pointing to the correct paths in the `data/plots/` directory (or use standard placeholders).

### R4. Bibliography Extraction
Extract the 27 references listed at the end of the markdown draft and create a properly formatted BibTeX file named `references.bib`. Ensure every reference is correctly cited in the text using `\cite{}`.

## Acceptance Criteria

### Output Verification
- [ ] A `main.tex` file is generated that uses the `IEEEtran` class and includes all chapters (Abstract to Conclusion).
- [ ] A `references.bib` file is generated containing all 27 references in proper BibTeX format.
- [ ] The English translation is natural, academic, and free of AI-typical colloquialisms or hallucinated details.
- [ ] All mathematical formulas and tables from the Korean draft are strictly preserved and correctly written in LaTeX syntax.
- [ ] The working directory `/home/imnyj/Workspace/paper4/latex` is fully prepared so the user can easily zip it and upload it to Overleaf.
