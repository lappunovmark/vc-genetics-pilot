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
            "Stops citing lack of funding, small sponsors\n(up to 20 trials), 2022–25 vs 2016–21",
            from_rr(res, "Industry, small (<=20)", "nofund"),
        ),
        (
            "Genetic support: trials stopped for financial/\nstrategic reasons vs completed (all years)",
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


def selection_checks(res="results"):
    """The small-sponsor odds ratio of the selection model (H1) under each specification reported in robust.txt:
    list of (label, (estimate, lo, hi), kind); kind is "step", "main", "check", "range" (lo, hi = the range of the
    point estimate when each top-20 company is left out in turn; no confidence interval) or "head" (a heading)."""
    tier_small = "C(tier)[T.Industry, small (<=5 drugs)]"
    base = "H1 gs_ante_first: + first-trial period, area, modality"

    def h1(section, fname="robust.txt"):
        return from_txt(res, fname, section, tier_small)

    with open(os.path.join(res, "robust.txt"), encoding="utf-8") as fh:
        txt = fh.read()
    m = re.search(r"range of the small-sponsor OR: (\d\.\d+) to (\d\.\d+)", txt)
    lo, hi = float(m.group(1)), float(m.group(2))
    mh = re.search(r"Mantel-Haenszel.*\n.*?OR (\d\.\d+) \((\d\.\d+)-(\d\.\d+)\)", txt)
    mantel_haenszel = tuple(float(x) for x in mh.groups())
    both = "(Minikel-based, dated OT): ex-ante support at first trial"
    return [
        ("No controls", h1("H1 gs_ante_first: unadjusted"), "step"),
        ("+ period of the first trial", h1("H1 gs_ante_first: + first-trial period only"), "step"),
        ("+ therapeutic area", h1("H1 gs_ante_first: + first-trial period, area"), "step"),
        ("+ type of drug  (main model)", h1(base), "main"),
        ("Errors clustered by sponsor", h1(base + "; clustered by sponsor"), "check"),
        (
            "Top-20 group cut to 17 companies",
            h1(base + "; top-20 group cut to the 17 largest companies"),
            "check",
        ),
        ("Each top-20 company left out in turn", ((lo + hi) / 2, lo, hi), "range"),
        (
            "Within the same disease (indication fixed effects)",
            h1("H1 gs_ante_first: + first-trial period, modality, indication fixed effects"),
            "check",
        ),
        ("Like with like: period × area × drug type cells", mantel_haenszel, "check"),
        (
            "Independent, dated genetic evidence",
            h1("H1 with dated OT evidence: ex-ante support at first trial", "gs_ot_models.txt"),
            "check",
        ),
        (
            "Support on either evidence measure",
            h1(f"H1 with support on either measure {both}", "gs_ot_models.txt"),
            "check",
        ),
        (
            "Support on both evidence measures",
            h1(f"H1 with support on both measures {both}", "gs_ot_models.txt"),
            "check",
        ),
        ("New drugs only (first indication)", h1("H1 gs_ante_first, novel-drug programmes only"), "check"),
    ] + period_split(res)


def period_split(res="results"):
    """The small-sponsor gap before and from 2016 (post hoc model of evidence_arrival_2015.py: top-20 pharma and
    small industry sponsors only), as rows for the figure; empty when that result file is absent."""
    path = os.path.join(res, "evidence_arrival_ot_gwas_2015.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.strip() == "Top-20 pharma against: Industry, small (<=5 drugs)"
    )
    row = next(line for line in lines[start:] if line.startswith("inverse, other sponsors against top-20 pharma"))
    before, after = (tuple(float(x) for x in m) for m in re.findall(r"OR (\d+\.\d+) \((\d+\.\d+) to (\d+\.\d+)\)", row))
    return [
        ("SPLIT BY PERIOD, MADE AFTER THE DATA WERE SEEN", None, "head"),
        ("First trials before 2016", before, "check"),
        ("First trials from 2016", after, "check"),
    ]
