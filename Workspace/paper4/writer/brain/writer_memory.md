# Writer Memory — Stage 2 of 3

**Agent:** Writer
**Task:** Stage 2 of 3 — Network Model + Proposed Scheme
**Timestamp:** 2026-05-08 (Stage 2 completion)
**Target File:** /home/imnyj/papers/paper4/paper/draft/main.tex

---

## Stage 2 Completion Summary

### Sections Written
1. **§III — Network Model and Scheme Overview** (`\section{Network Model and Scheme Overview}`, `\label{sec.net}`)
   - 3 subsections written
2. **§IV — Proposed Scheme** (`\section{Proposed Scheme}`, `\label{sec.prop}`)
   - 4 subsections written

### Subsection Inventory

#### §III Subsections
| Label | Title |
|-------|-------|
| `\label{subsec:net_env}` | Vehicular Network Environment |
| `\label{subsec:cam_dcc}` | ETSI CAM Service and Baseline DCC |
| `\label{subsec:overview}` | Scheme Overview |

#### §IV Subsections
| Label | Title |
|-------|-------|
| `\label{subsec:1}` | State, Action, and Joint Cost Formulation |
| `\label{subsec:2}` | Oracle Generation via Exhaustive Grid Search |
| `\label{subsec:3}` | TinyMLP Architecture and Behavior Cloning |
| `\label{subsec:4}` | ETSI Compliance and MCU Deployment |

### Equations Written (11 total)
| Label | Description |
|-------|-------------|
| `eq:tgencam_bounds` | T_GenCam ∈ [100ms, 1000ms] ETSI bounds |
| `eq:state` | 5D vehicle state vector definition |
| `eq:aoi_def` | AoI_ij = t_rx - t_gen |
| `eq:aoi_avg` | Network-wide average AoI |
| `eq:action_space` | Joint action (T, p) ∈ T × P |
| `eq:cost` | Joint cost J(T, p | s) = α·AoI + β·CBR + γ·M |
| `eq:oracle` | argmin oracle action selection |
| `eq:param_count` | Total params = 192 + 1056 + 264 = 1,448 |
| `eq:bc_loss` | BC loss = CE(T_logits, T*) + CE(p_logits, p*) |
| `eq:clamp` | ETSI compliance clamp for T_GenCam |
| `eq:memory` | MCU memory ≈ 1.4 KB + 0.5 KB ≈ 2 KB |

### Algorithms Written (1 total)
| Label | Title |
|-------|-------|
| `alg:oracle` | Algorithm 1: Oracle Label Generation via Exhaustive Grid Search |

### Tables Written (1 new in §IV)
| Label | Title |
|-------|-------|
| `tab:arch` | TinyMLP Layer-by-Layer Architecture |

### Citations Used in New Sections (6 instances, 4 unique keys)
- `Bhattacharyya2024` (×3): ETSI CAM triggers, Reactive DCC, ETSI compliance gate
- `Mianji2025` (×1): AI override layer compatibility
- `Iliopoulos2025` (×1): ETSI event trigger priority
- `Zila2026` (×1): MCU deployment / CMSIS-NN reference

**All keys verified within the 47-key approved list. No new keys invented.**

### Preamble Modification
- Added `\usepackage{algorithm}` (was missing; `\usepackage{algorithmic}` was already present)

### Preserved Sections (unchanged)
- Abstract ✓
- Keywords ✓
- Introduction ✓
- Related Work ✓
- §V Performance Evaluation (TODO stub) ✓
- §VI Conclusion (TODO stub) ✓
- thebibliography (TODO stub) ✓

### File Stats
- Total characters: 39,714
- Total lines: 857

---

## Key Design Decisions

1. **No \includegraphics used** — all block diagrams described textually per constraint.
2. **No placeholder figure text** — structural descriptions are prose-only.
3. **ETSI override architecture** — DCC state machine preserved, AI layer overlaid.
4. **Proposition 1 (Myopic Optimality)** — explicitly scoped to 200ms horizon.
5. **Definition 1 (Vehicle State)** — uses `\textbf{Definition 1}` bold format (no theorem env).
6. **Algorithm 1** uses `algorithm` + `algorithmic` package with `[1]` line numbering.
7. **Table tab:arch** presents layer-by-layer TinyMLP structure with param counts.
8. **Equation eq:param_count** explicitly shows: 192 + 1056 + 264 = 1,448.
9. **INT8 quantization** and STM32F407 deployment profile described in §IV.D.
10. **C header `tinymlp_aidcc.h`** deployment artifact named (matches idea_spec §4.4).

---

## Stage 3 Remaining Work
- §V Performance Evaluation: simulation setup, baselines, metrics, result tables
- §VI Conclusion: summary, limitations, future work
- Bibliography: paste bibitem.tex contents
