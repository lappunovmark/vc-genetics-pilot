"""Main figure: (A) the headline estimates grouped by question, (B) the small-sponsor gap in selection under
every specification in robust.txt. All numbers are read from results/ through headline.py.

Usage: python pilot/figure_main.py results figures/main_results.png
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headline import headline, selection_checks  # noqa: E402

RES, OUT = sys.argv[1], sys.argv[2]
INK, INK2, MUTED, GRID, SERIES, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#2a78d6", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

H = dict(headline(RES))
keys = list(H)
# panel A: (question, rows of the headline list)
GROUPS = [
    ("DOES GENETIC EVIDENCE PREDICT SUCCESS?", [keys[0], keys[1]]),
    ("WHO STARTS PROGRAMMES THAT HAVE IT?", [keys[2], keys[6], keys[5]]),
    ("WHEN MONEY GOT TIGHT (2022–25)", [keys[3], keys[4]]),
]
rows_a = []  # (kind, label, values)
for q, ks in GROUPS:
    rows_a.append(("head", q, None))
    rows_a += [("est", k, H[k]) for k in ks]
rows_b = [(kind, label, v) for label, v, kind in selection_checks(RES)]


def panel(ax, rows, xlim, ticks, xtext, value_header):
    n = len(rows)
    for i, (kind, label, v) in enumerate(rows):
        y = n - 1 - i
        if kind == "head":
            ax.text(-0.02, y - 0.12, label, transform=ax.get_yaxis_transform(), ha="right", va="center",
                    color=INK2, fontsize=8, fontweight="bold")  # fmt: skip
            continue
        est, lo, hi = v
        if kind == "range":  # range of point estimates, no interval: a bar without a marker
            ax.plot([lo, hi], [y, y], color=SERIES, lw=7, solid_capstyle="butt", zorder=2)
            txt = f"{lo:.2f} to {hi:.2f}  (range)"
        else:
            sig = lo > 1 or hi < 1
            ax.plot([lo, hi], [y, y], color=SERIES, lw=2, solid_capstyle="round", zorder=2)
            ax.scatter([est], [y], s=64, zorder=3, color=SERIES if sig else SURFACE, edgecolors=SERIES, linewidths=2)
            txt = f"{est:.2f}  ({lo:.2f}–{hi:.2f})"
        bold = "bold" if kind == "main" else "normal"
        ax.text(xtext, y, txt, va="center", ha="left", color=INK, fontsize=9.5, fontweight=bold)
        ax.text(-0.02, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center", color=INK,
                fontsize=9.5, fontweight=bold, linespacing=1.15)  # fmt: skip
    ax.axvline(1, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(*xlim)
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([f"{t:g}" for t in ticks], color=INK2)
    ax.set_yticks([])
    ax.tick_params(axis="x", colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_ylim(-0.6, n - 0.35)
    ax.text(xtext, n - 0.55, value_header, ha="left", va="bottom", color=INK2, fontsize=9, fontweight="bold")
    ax.set_facecolor(SURFACE)


fig, (ax_a, ax_b) = plt.subplots(
    2,
    1,
    figsize=(9.6, 2.4 + 0.5 * (len(rows_a) * 1.12 + len(rows_b))),
    dpi=200,
    gridspec_kw={"height_ratios": [len(rows_a) * 1.12, len(rows_b)], "hspace": 0.36},
)
fig.patch.set_facecolor(SURFACE)
panel(ax_a, rows_a, (0.3, 5.5), [0.33, 0.5, 1, 2, 4], 5.7, "Ratio (95% CI)")
panel(ax_b, rows_b, (0.42, 1.55), [0.5, 0.7, 1, 1.4], 1.575, "Odds ratio (95% CI)")
ax_a.set_xlabel("← less          Odds ratio or rate ratio, log scale          more →", color=INK2, fontsize=9)
ax_b.set_xlabel("← less often          Odds ratio, log scale          more often →", color=INK2, fontsize=9)
fig.text(0.02, 0.978, "Genetic evidence predicts success for every sponsor,\nbut small and privately financed sponsors "
         "do not start more programmes that have it", ha="left", va="top", fontsize=12.5, fontweight="bold",
         color=INK, linespacing=1.25)  # fmt: skip
fig.subplots_adjust(left=0.37, right=0.79, top=0.865, bottom=0.095)
pos_a, pos_b = ax_a.get_position(), ax_b.get_position()
fig.text(0.02, pos_a.y1 + 0.012, "A   Headline estimates of the pilot", ha="left", color=INK, fontsize=10.5,
         fontweight="bold")  # fmt: skip
fig.text(0.02, pos_b.y1 + 0.036, "B   The small-sponsor gap in selection under each specification", ha="left",
         color=INK, fontsize=10.5, fontweight="bold")  # fmt: skip
fig.text(0.02, pos_b.y1 + 0.018, "Odds that a programme has genetic support at its first trial, small industry "
         "sponsors against top-20 pharma", ha="left", color=INK2, fontsize=8.5)  # fmt: skip
fig.text(0.02, 0.012, "Filled marker: the 95% interval excludes 1. 35,887 drug × indication programmes; Open Targets "
         "26.09, ClinicalTrials.gov snapshot of 17 October 2026,\nSEC Form D 2009–2026, NIH RePORTER. Pilot on open "
         "data, not peer-reviewed.", ha="left", va="bottom", color=INK2, fontsize=8, linespacing=1.3)  # fmt: skip
fig.savefig(OUT, facecolor=SURFACE)
for kind, label, v in rows_a + rows_b:
    if v:
        print(kind, label.replace("\n", " "), v)
