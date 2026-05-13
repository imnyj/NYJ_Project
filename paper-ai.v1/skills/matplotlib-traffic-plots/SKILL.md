---
name: matplotlib-traffic-plots
description: Use when producing publication-quality matplotlib/seaborn figures for traffic/V2X papers. Provides a journal-ready rcParams, a color-blind-safe palette, canonical plot types (fundamental diagram, CDF, PDR vs distance), and DPI/font rules. Load this before writing any figure-generation code.
---

# Publication-Ready Matplotlib Skill

## When to load
When Writer invokes the Visualization Tool, or when Experimenter post-processes
results into figures for the paper.

## One-time journal rcParams

Paste at the TOP of every plotting module:

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

def set_journal_style():
    """IEEE single-column ≈ 3.5" wide; Elsevier 1-col ≈ 3.54". We use 3.5"."""
    mpl.rcParams.update({
        "font.family":       "serif",
        "font.serif":        ["Times New Roman", "DejaVu Serif"],
        "font.size":         9,
        "axes.titlesize":    9,
        "axes.labelsize":    9,
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        "legend.fontsize":   8,
        "figure.figsize":    (3.5, 2.5),     # inches
        "figure.dpi":        150,
        "savefig.dpi":       300,             # submission-ready
        "savefig.bbox":      "tight",
        "savefig.format":    "pdf",           # vector
        "axes.linewidth":    0.8,
        "lines.linewidth":   1.2,
        "lines.markersize":  4,
        "grid.linewidth":    0.4,
        "grid.alpha":        0.5,
        "axes.grid":         True,
        "pdf.fonttype":      42,              # embed TrueType, no Type 3
        "ps.fonttype":       42,
    })
```

## Color-blind-safe palette

Use **Okabe-Ito** (widely recommended for color-vision deficiency):

```python
OKABE_ITO = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#CC79A7",  # purple/pink
    "#56B4E9",  # sky
    "#D55E00",  # vermillion
    "#F0E442",  # yellow
    "#000000",  # black
]

LINESTYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS    = ["o", "s", "^", "D", "v", "P", "X"]
```

**Redundant encoding** is mandatory: every series gets a distinct color AND
a distinct linestyle AND a distinct marker. A grayscale print of your PDF
should still be readable.

## Canonical plot types

### Fundamental diagram (speed vs density)
```python
fig, ax = plt.subplots()
for i, scheme in enumerate(schemes):
    ax.plot(density[scheme], speed[scheme],
            color=OKABE_ITO[i], linestyle=LINESTYLES[i],
            marker=MARKERS[i], label=scheme)
ax.set_xlabel("Density (veh/km)")
ax.set_ylabel("Mean speed (km/h)")
ax.legend(loc="best", framealpha=0.9)
fig.savefig("output/figures/fundamental_diagram.pdf")
```

### CDF (for latency, waiting time, etc.)
```python
import numpy as np
def plot_cdf(ax, values, label, idx):
    x = np.sort(values)
    y = np.arange(1, len(x) + 1) / len(x)
    ax.plot(x, y, color=OKABE_ITO[idx], linestyle=LINESTYLES[idx], label=label)
    ax.set_ylabel("CDF")
    ax.set_ylim(0, 1.02)
```

### Bar chart with error bars (mean ± 95 % CI)
```python
fig, ax = plt.subplots()
x = np.arange(len(schemes))
means = [summary[s]["mean"] for s in schemes]
ci95  = [1.96 * summary[s]["std"] / np.sqrt(summary[s]["n"]) for s in schemes]
ax.bar(x, means, yerr=ci95, capsize=3, color=OKABE_ITO[:len(schemes)],
       edgecolor="black", linewidth=0.6)
ax.set_xticks(x)
ax.set_xticklabels(schemes, rotation=20, ha="right")
```

### Heatmap (e.g., PDR vs distance × density)
```python
import seaborn as sns
sns.heatmap(
    pdr_matrix, annot=True, fmt=".2f",
    cmap="viridis",                # perceptually uniform; CB-safe
    xticklabels=distances, yticklabels=densities,
    cbar_kws={"label": "PDR"},
    ax=ax,
)
```

## Data integrity rules (NEVER violate)

1. **Do not truncate the y-axis** to exaggerate differences. If necessary,
   draw a broken-axis marker explicitly.
2. **Never smooth data silently.** If you smooth, caption it explicitly.
3. **Error bars are mandatory** for any aggregated metric.
4. **Do not drop outliers** without reporting in the caption.
5. **Axis units** must always be stated (`km/h`, `veh/km`, not bare numbers).

## Caption rules

- Figures stand alone: a reader should understand the figure + caption without reading the surrounding text.
- State: what is plotted, what each series is, what the error bars represent, how many seeds.

## Output hygiene

- Save as PDF (vector); also save a PNG copy for VLM critique in Phase 5.
- Filename pattern: `figures/<metric>_<context>.pdf` — e.g. `figures/pdr_vs_distance.pdf`.
- No spaces in filenames; LaTeX is picky.
