---
name: scie-latex-template
description: Use when producing final LaTeX draft for SCIE-grade journals (IEEE, Elsevier, Springer Nature, ACM, MDPI, Wiley). Provides the template preamble, section scaffold, cross-reference conventions, math labeling rules, and journal-specific class options. Load this before writing any .tex file.
---

# SCIE LaTeX Template Skill

## When to load
When Writer is about to produce `drafts/main.tex`, a section `.tex` file, or
when Reviewer (PROOFREADER mode) checks LaTeX-specific style issues.

## Class selection per venue

| Publisher | Document class | Example option |
|---|---|---|
| IEEE | `IEEEtran` | `\documentclass[journal,twocolumn]{IEEEtran}` |
| Elsevier | `elsarticle` | `\documentclass[review,3p,times]{elsarticle}` |
| Springer Nature | `sn-jnl` | `\documentclass[sn-basic]{sn-jnl}` |
| ACM | `acmart` | `\documentclass[acmsmall]{acmart}` |
| MDPI | `mdpi` | `\documentclass[article,final]{mdpi}` |
| Wiley | `WileyNJD-v2` | per-journal variant |

## Canonical preamble (IEEEtran example)

```latex
\documentclass[journal,twocolumn]{IEEEtran}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}            % professional tables
\usepackage{siunitx}             % consistent SI units
\usepackage{cleveref}            % smart \cref{} references
\usepackage[colorlinks=true,allcolors=blue]{hyperref}

\begin{document}
\title{TITLE HERE}
\author{Author~Name,~\IEEEmembership{Member,~IEEE}}
\maketitle

\begin{abstract}
(150–250 words, one paragraph.)
\end{abstract}

\begin{IEEEkeywords}
5–6 keywords, sorted alphabetically.
\end{IEEEkeywords}

% Sections here

\bibliographystyle{IEEEtran}
\bibliography{refs}
\end{document}
```

## Section scaffold (standard SCIE paper)

```
1. Introduction         (1–1.5 pages: motivation, gap, contribution list)
2. Related Work         (1 page: prior approaches, positioned via refs.json)
3. System Model / Problem Formulation   (math-heavy, labels every equation)
4. Proposed Method      (the core contribution; sub-sectioned)
5. Experimental Setup   (pulled from experiment_spec.yaml)
6. Results              (each figure from Visualization Tool)
7. Discussion           (Opus turf — analysis, limits, future work)
8. Conclusion           (3–4 sentences, no new content)
```

## Labeling conventions (STRICT)

| Element | Label prefix | Example |
|---|---|---|
| Equation | `eq:` | `\label{eq:throughput_def}` |
| Figure | `fig:` | `\label{fig:fundamental_diagram}` |
| Table | `tab:` | `\label{tab:baseline_params}` |
| Section | `sec:` | `\label{sec:method}` |
| Algorithm | `alg:` | `\label{alg:scheduling}` |

Reference with `\cref{...}` (via `cleveref`), never `Fig.~\ref{...}` hand-coded.

## Citation rule (ENFORCED by Librarian)

NEVER write `\cite{smith2020}` or inline BibTeX entries. Use the corpus-ID
convention:

```latex
...has been shown \cite{corpusID:12345678}.
```

The post-processor (Phase 5) fetches authoritative BibTeX from Crossref /
Semantic Scholar keyed on these IDs and writes `refs.bib` automatically.
This prevents the 14–95 % BibTeX hallucination documented in the GhostCite
literature.

## Figure inclusion (from Visualization Tool)

```latex
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fundamental_diagram.pdf}
  \caption{Fundamental diagram of the proposed scheme vs baselines.}
  \label{fig:fundamental_diagram}
\end{figure}
```

Always include `.pdf` (vector), never `.png` in camera-ready.

## Math style

- Use `\operatorname{}` for multi-letter operators (`\operatorname{tr}`, not `tr`).
- Align multi-line equations with `align` environment + `&`.
- Vectors: `\mathbf{x}`. Matrices: `\mathbf{A}`. Sets: `\mathcal{S}`.
- No inline `$$...$$` — use `\[ ... \]` or `equation` env.

## Reviewer common complaints (pre-submit checklist)

1. ☐ Every equation has `\label` and is referenced at least once.
2. ☐ Every figure has units on both axes.
3. ☐ Every table has `\toprule` / `\midrule` / `\bottomrule` (booktabs), never `\hline`.
4. ☐ All acronyms are defined on first use and used consistently.
5. ☐ No "In this paper, we propose..." clichés — be specific.
6. ☐ Conclusion does not introduce new material.
7. ☐ All references use corpus IDs (no hand-written BibTeX).
