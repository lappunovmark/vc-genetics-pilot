"""Results-at-a-glance figure for the README: headline ratios with 95% CIs, read from results/.

Usage: python pilot/figure_glance.py results figures/results_glance.png
"""
import csv
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

RES, OUT = sys.argv[1], sys.argv[2]
NUM = re.compile(r'-?\d+\.\d+')


def from_txt(fname, section, key):
    """Last three numbers (OR, lo, hi) of the row starting with `key` inside the block headed `section`."""
    lines = open(f'{RES}/{fname}', encoding='utf-8').read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == section)
    for l in lines[start + 1:]:
        if l.startswith('====='):
            break
        if l.startswith(key):
            return tuple(float(x) for x in NUM.findall(l[len(key):])[-3:])
    raise KeyError((fname, section, key))


def from_rr(group, stops):
    with open(f'{RES}/rq2_rr.csv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['group'] == group and r['stops'] == stops:
                return float(r['rr']), float(r['rr_lo']), float(r['rr_hi'])
    raise KeyError((group, stops))


rows = [
    ('Genetic support at phase entry\n→ advancing to the next phase',
     from_txt('robust.txt', 'Advance: main effects (ex-ante support at entry)', 'gs ')),
    ('…difference for small sponsors\nvs top-20 pharma (interaction)',
     from_txt('robust.txt', 'Advance: support x sponsor tier', 'gs:C(tier)[T.Industry, small (<=5 drugs)]')),
    ('Small sponsors starting programmes\nwith genetic support (vs top-20)',
     from_txt('robust.txt', 'H1 gs_ante_first: + first-trial period, area, modality', 'C(tier)[T.Industry, small (<=5 drugs)]')),
    ('Stops citing lack of funding,\nsmall sponsors, 2022–25 vs 2016–21',
     from_rr('Industry, small (<=20)', 'nofund')),
    ('Genetic support: trials stopped for\nfinancial/strategic reasons vs completed',
     from_txt('h4_biology.txt', 'gs_ante ~ outcome (reference: completed) + phase, start period, area, modality, sponsor group',
              "C(outcome, Treatment(reference='Completed'))[T.Stopped: financial or strategic]")),
    ('Prior NIH SBIR/STTR funding\n→ genetic support of programmes',
     from_txt('sbir_models.txt', 'H1: ex-ante support at first trial ~ prior SBIR/STTR', 'sbir ')),
]

INK, INK2, MUTED, GRID, SERIES, SURFACE = '#0b0b0b', '#52514e', '#8a8984', '#e6e5e1', '#2a78d6', '#ffffff'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
n = len(rows)
for i, (label, (est, lo, hi)) in enumerate(rows):
    y = n - 1 - i
    sig = lo > 1 or hi < 1
    ax.plot([lo, hi], [y, y], color=SERIES, lw=2, solid_capstyle='round', zorder=2)
    ax.scatter([est], [y], s=64, zorder=3, color=SERIES if sig else SURFACE, edgecolors=SERIES, linewidths=2)
    ax.text(5.6, y, f'{est:.2f}  ({lo:.2f}–{hi:.2f})', va='center', ha='left', color=INK, fontsize=9.5)
ax.axvline(1, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
ax.set_xscale('log')
ax.set_xlim(0.3, 5.5)
ax.xaxis.set_major_locator(FixedLocator([0.33, 0.5, 1, 2, 4]))
ax.xaxis.set_minor_locator(NullLocator())
ax.set_xticklabels(['0.33', '0.5', '1', '2', '4'], color=INK2)
ax.set_yticks(range(n))
ax.set_yticklabels([r[0] for r in rows][::-1], color=INK, fontsize=9.5)
ax.tick_params(axis='y', length=0, pad=8)
ax.tick_params(axis='x', colors=INK2, length=0)
ax.grid(axis='x', color=GRID, lw=0.8, zorder=0)
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
ax.spines['bottom'].set_color(GRID)
ax.set_xlabel('Odds ratio or rate ratio, 95% CI (log scale)   ·   filled = CI excludes 1', color=INK2, fontsize=9)
ax.text(5.6, n - 0.35, 'Estimate (95% CI)', ha='left', va='bottom', color=INK2, fontsize=9, fontweight='bold')
ax.text(0.3, n - 0.35, '← lower', ha='left', va='bottom', color=MUTED, fontsize=8.5)
ax.text(1.04, n - 0.35, 'higher →', ha='left', va='bottom', color=MUTED, fontsize=8.5)
ax.set_ylim(-0.6, n - 0.1)
fig.suptitle('Do investors pick better biology? Pilot results at a glance', x=0.02, ha='left', y=0.985,
             fontsize=12.5, fontweight='bold', color=INK)
fig.text(0.02, 0.905, '35,887 drug × indication programmes · Open Targets 26.09 · ClinicalTrials.gov snapshot 17 Oct 2026 · '
         'not peer-reviewed', ha='left', color=INK2, fontsize=8.5)
fig.subplots_adjust(left=0.34, right=0.80, top=0.84, bottom=0.14)
fig.savefig(OUT, facecolor=SURFACE)
for label, v in rows:
    print(label.replace('\n', ' '), v)
