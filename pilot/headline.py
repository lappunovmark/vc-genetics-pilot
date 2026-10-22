"""Headline estimates (ratio, 95% CI low, 95% CI high) read directly from the model output in results/.

Used by figure_glance.py and by tests/test_readme_numbers.py, so the figure, the README and the model output
cannot drift apart.
"""

import csv
import os
import re

NUM = re.compile(r"-?\d+\.\d+")


def from_txt(res, fname, section, key):
    """Last three numbers (OR, lo, hi) of the row starting with `key` inside the block headed `section`."""
    with open(os.path.join(res, fname), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == section)
    for line in lines[start + 1 :]:
        if line.startswith("====="):
            break
        if line.startswith(key):
            return tuple(float(x) for x in NUM.findall(line[len(key) :])[-3:])
    raise KeyError((fname, section, key))


def from_rr(res, group, stops):
    """Rate ratio and 95% CI of trial stops, 2022-25 vs 2016-21, for one sponsor group."""
    with open(os.path.join(res, "rq2_rr.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["group"] == group and row["stops"] == stops:
                return float(row["rr"]), float(row["rr_lo"]), float(row["rr_hi"])
    raise KeyError((group, stops))


def headline(res="results"):
    """Ordered list of (label, (estimate, lo, hi)) for the README figure and checks."""
    tier_small = "C(tier)[T.Industry, small (<=5 drugs)]"
    return [
        (
            "Genetic support at phase entry\n→ advancing to the next phase",
            from_txt(res, "robust.txt", "Advance: main effects (ex-ante support at entry)", "gs "),
        ),
        (
            "…difference for small sponsors\nvs top-20 pharma (interaction)",
            from_txt(res, "robust.txt", "Advance: support x sponsor tier", "gs:" + tier_small),
        ),
        (
            "Small sponsors starting programmes\nwith genetic support (vs top-20)",
            from_txt(res, "robust.txt", "H1 gs_ante_first: + first-trial period, area, modality", tier_small),
        ),
        (
            "Stops citing lack of funding,\nsmall sponsors, 2022–25 vs 2016–21",
            from_rr(res, "Industry, small (<=20)", "nofund"),
        ),
        (
            "Genetic support: trials stopped for\nfinancial/strategic reasons vs completed",
            from_txt(
                res,
                "h4_biology.txt",
                "gs_ante ~ outcome (reference: completed) + phase, start period, area, modality, sponsor group",
                "C(outcome, Treatment(reference='Completed'))[T.Stopped: financial or strategic]",
            ),
        ),
        (
            "Prior NIH SBIR/STTR funding\n→ genetic support of programmes",
            from_txt(res, "sbir_models.txt", "H1: ex-ante support at first trial ~ prior SBIR/STTR", "sbir "),
        ),
        (
            "Prior SEC Form D private placement\n→ genetic support of programmes",
            from_txt(res, "formd_models.txt", "H1: ex-ante support at first trial ~ prior Form D", "formd "),
        ),
    ]
