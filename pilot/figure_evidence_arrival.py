"""Figure: programme starts around the publication of GWAS evidence for a target-indication pair.
(A) the event study of top-20 pharma and of other industry sponsors, (B) the ratio of the two responses under the
planned specifications and under the checks added after the result was known. All numbers are read from the result
files of evidence_arrival.py.

Usage: python pilot/figure_evidence_arrival.py results figures/evidence_arrival.png
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from headline import from_txt  # noqa: E402

RES, OUT = sys.argv[1], sys.argv[2]
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#ffffff"
TOP, OTHER = "#2a78d6", "#eb6834"  # categorical slots 1 and 2 (checked with the colour-blindness validator)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
GWAS, ALL, TO22 = "evidence_arrival_ot_gwas.txt", "evidence_arrival_ot_all.txt", "evidence_arrival_ot_gwas_to2022.txt"

# ---- panel A: event study --------------------------------------------------------------------------------------------
BINS = [
    ("m6plus", "6 or more\nyears before"),
    ("m5_3", "3–5 years\nbefore"),
    (None, "1–2 years\nbefore\n(reference)"),
    ("e0", "year of\npublication"),
    ("p1_2", "1–2 years\nafter"),
    ("p3_5", "3–5 years\nafter"),
    ("p6plus", "6 or more\nyears after"),
]
SERIES = [
    ("Top-20 pharma", TOP, "C. top-20 pharma: event study, reference = the two years before the evidence year", -0.11),
    ("Other industry sponsors", OTHER, "C. other industry: event study, reference = the two years before the evidence year", 0.11),
]  # fmt: skip
ev = {
    name: [(1.0, 1.0, 1.0) if k is None else from_txt(RES, GWAS, sec, k + " ") for k, _ in BINS]
    for name, _, sec, _ in SERIES
}

# ---- panel B: the contrast (other industry against top-20 pharma) ---------------------------------------------------
D1 = "D1. other industry against top-20 pharma (post_other = ratio of the two responses)"
ROWS = [
    ("head", "PLANNED BEFORE THE RUN", None),
    ("main", "Primary: GWAS evidence, target–indication pairs", from_txt(RES, GWAS, D1, "post_other")),
    ("est", "With therapeutic area × year effects", from_txt(RES, GWAS, "D2. the same with therapeutic area x year x group fixed effects", "post_other")),
    ("est", "All germline sources of evidence", from_txt(RES, ALL, D1, "post_other")),
    ("head", "ADDED AFTER THE RESULT WAS KNOWN", None),
    ("est", "Without pairs that gained evidence after 2022", from_txt(RES, TO22, D1, "post_other")),
    ("est", "Without the three leading genes (TYK2, IL12B, JAK2)", from_txt(RES, GWAS, "G. D1 without the pairs of these three genes", "post_other")),
    ("est", "Against other indications of the same target\n(gene × year effects)", from_txt(RES, GWAS, "G. D1 with gene x year x group fixed effects", "post_other")),
    ("est", "The target as the unit, all its indications together", from_txt(RES, GWAS, "H3. other industry against top-20 pharma, target level", "post_other")),
    ("est", "The target as the unit, without the three leading genes", from_txt(RES, GWAS, "H4. H3 without the three leading genes", "post_other")),
]  # fmt: skip

fig, (ax, bx) = plt.subplots(
    2, 1, figsize=(9.6, 9.6), dpi=200, gridspec_kw={"height_ratios": [1.0, 1.02], "hspace": 0.5}
)
fig.patch.set_facecolor(SURFACE)

x = range(len(BINS))
for name, col, _, dx in SERIES:
    v = ev[name]
    ax.plot([i + dx for i in x], [e for e, _, _ in v], color=col, lw=2, zorder=2, solid_capstyle="round")
    for i, ((est, lo, hi), (k, _)) in enumerate(zip(v, BINS)):
        if k is None:
            continue
        ax.plot([i + dx, i + dx], [lo, hi], color=col, lw=2, zorder=2, solid_capstyle="round")
        sig = lo > 1 or hi < 1
        ax.scatter([i + dx], [est], s=64, zorder=3, color=col if sig else SURFACE, edgecolors=col, linewidths=2)
    ax.plot([], [], color=col, lw=2, marker="o", ms=7, mfc=col, mec=col, label=name)
ax.scatter([2], [1], s=64, zorder=3, color=SURFACE, edgecolors=MUTED, linewidths=2)
ax.axhline(1, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
ax.axvspan(2.5, 3.5, color="#f3f2ee", zorder=0, lw=0)
ax.set_yscale("log")
ax.set_ylim(0.45, 5.0)
ax.yaxis.set_major_locator(FixedLocator([0.5, 0.7, 1, 1.5, 2, 3, 4]))
ax.yaxis.set_minor_locator(NullLocator())
ax.set_yticklabels(["0.5", "0.7", "1", "1.5", "2", "3", "4"], color=INK2)
ax.set_xticks(list(x))
ax.set_xticklabels([lab for _, lab in BINS], color=INK, fontsize=9, linespacing=1.2)
ax.set_xlim(-0.5, len(BINS) - 0.5 + 0.9)
ax.tick_params(axis="both", length=0)
ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.set_ylabel("Rate ratio of programme starts, log scale", color=INK2, fontsize=9)
ax.set_facecolor(SURFACE)
for name, _, _, dx in SERIES:  # direct labels at the last point, in ink
    est = ev[name][-1][0]
    ax.text(len(BINS) - 1 + 0.28, est, name.replace(" sponsors", "\nsponsors"), va="center", ha="left", color=INK, fontsize=9, linespacing=1.15)  # fmt: skip
ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK, handlelength=2.2, borderaxespad=0.2)

n = len(ROWS)
XT = 2.08
for i, (kind, label, v) in enumerate(ROWS):
    y = n - 1 - i
    if kind == "head":
        bx.text(-0.02, y - 0.12, label, transform=bx.get_yaxis_transform(), ha="right", va="center", color=INK2, fontsize=8, fontweight="bold")  # fmt: skip
        continue
    est, lo, hi = v
    sig = lo > 1 or hi < 1
    bx.plot([lo, hi], [y, y], color=TOP, lw=2, solid_capstyle="round", zorder=2)
    bx.scatter([est], [y], s=64, zorder=3, color=TOP if sig else SURFACE, edgecolors=TOP, linewidths=2)
    bold = "bold" if kind == "main" else "normal"
    bx.text(XT, y, f"{est:.2f}  ({lo:.2f}–{hi:.2f})", va="center", ha="left", color=INK, fontsize=9.5, fontweight=bold)
    bx.text(-0.02, y, label, transform=bx.get_yaxis_transform(), ha="right", va="center", color=INK, fontsize=9.5, fontweight=bold, linespacing=1.15)  # fmt: skip
bx.axvline(1, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
bx.set_xscale("log")
bx.set_xlim(0.28, 2.0)
bx.xaxis.set_major_locator(FixedLocator([0.3, 0.5, 0.7, 1, 1.5]))
bx.xaxis.set_minor_locator(NullLocator())
bx.set_xticklabels(["0.3", "0.5", "0.7", "1", "1.5"], color=INK2)
bx.set_yticks([])
bx.tick_params(axis="x", colors=INK2, length=0)
bx.grid(axis="x", color=GRID, lw=0.8, zorder=0)
for s in ("top", "right", "left"):
    bx.spines[s].set_visible(False)
bx.spines["bottom"].set_color(GRID)
bx.set_ylim(-0.6, n - 0.35)
bx.text(XT, n - 0.55, "Ratio (95% CI)", ha="left", va="bottom", color=INK2, fontsize=9, fontweight="bold")
bx.set_xlabel("← other industry respond less        log scale        more →", color=INK2, fontsize=9)  # fmt: skip
bx.set_facecolor(SURFACE)

fig.subplots_adjust(left=0.085, right=0.86, top=0.845, bottom=0.115)
pb = bx.get_position()
bx.set_position([0.44, pb.y0, 0.80 - 0.44, pb.height])
pa, pb = ax.get_position(), bx.get_position()
fig.text(0.02, 0.982, "After GWAS evidence for a target and indication is published, top-20 pharma start\nmore "
         "programmes on the pair than other industry sponsors do, but the difference\nis not specific to that indication",
         ha="left", va="top", fontsize=12.5, fontweight="bold", color=INK, linespacing=1.25)  # fmt: skip
fig.text(0.02, pa.y1 + 0.03, "A   Programme starts on the pair, by years since the evidence was published", ha="left", color=INK, fontsize=10.5, fontweight="bold")  # fmt: skip
fig.text(0.02, pa.y1 + 0.012, "Relative to the two years before publication and to pairs without such evidence in the same calendar years", ha="left", color=INK2, fontsize=8.5)  # fmt: skip
fig.text(0.02, pb.y1 + 0.034, "B   Other industry sponsors against top-20 pharma after publication, under each specification", ha="left", color=INK, fontsize=10.5, fontweight="bold")  # fmt: skip
fig.text(0.02, pb.y1 + 0.016, "Ratio of the two responses; below 1 means that other industry sponsors respond less than top-20 pharma", ha="left", color=INK2, fontsize=8.5)  # fmt: skip
fig.text(0.02, 0.012, "Filled marker: the 95% interval excludes 1. Poisson models with pair (or target) and year effects; errors "
         "clustered by indication (or gene).\n53,064 target–indication pairs with a programme started in 2000–2025, 1,393 "
         "of which gained GWAS evidence (Open Targets 26.09, L2G ≥ 0.5).\nPilot on open data, not peer-reviewed.",
         ha="left", va="bottom", color=INK2, fontsize=8, linespacing=1.3)  # fmt: skip
fig.savefig(OUT, facecolor=SURFACE)
for name in ev:
    print(name, ev[name])
for kind, label, v in ROWS:
    if v:
        print(label.replace("\n", " "), v)
