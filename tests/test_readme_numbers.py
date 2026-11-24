"""The headline numbers quoted in README.md must match the model output in results/."""

import json
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
from headline import headline  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
    README = fh.read()


@pytest.mark.parametrize("label, values", headline(RESULTS), ids=lambda x: x if isinstance(x, str) else "")
def test_headline_estimate_quoted_in_readme(label, values):
    est, lo, hi = values
    for v in (est, lo, hi):
        assert f"{v:.2f}" in README, f"{label!r}: {v:.2f} not found in README"


def test_programme_counts():
    with open(os.path.join(RESULTS, "coverage.json"), encoding="utf-8") as fh:
        cov = json.load(fh)
    assert f"{cov['programmes_with_trials']:,}" in README
    assert f"{cov['programmes_with_insight']:,}" in README
    assert cov["ot_release"] in README


# Estimates quoted in the README beyond the headline list: (result file, block title, row).
D1 = "D1. other industry against top-20 pharma (post_other = ratio of the two responses)"
QUOTED = [
    ("evidence_arrival_ot_gwas.txt", "A. top-20 pharma: programme starts after the evidence year (pair and year fixed effects)", "post "),
    ("evidence_arrival_ot_gwas.txt", "A. other industry: programme starts after the evidence year (pair and year fixed effects)", "post "),
    ("evidence_arrival_ot_gwas.txt", D1, "post_other"),
    ("evidence_arrival_ot_gwas.txt", "G. D1 with gene x year x group fixed effects", "post_other"),
    ("cash_runway.txt", "1 (primary). Cohort 2022, sponsors with a runway: financial or strategic stop ~ short runway", "short "),
    ("cvc_models.txt", "A2. H1, programmes with a named investor: corporate investor against independent funds only", "corp_inv"),
    ("ipo_models.txt", "H1 PRIMARY: ex-ante support ~ venture share (per 10 points)", "v10 "),
    ("evidence_arrival_ot_gwas_top2010_from2010.txt", D1, "post_other"),
]  # fmt: skip


@pytest.mark.parametrize(
    "fname, section, key", QUOTED, ids=[f"{f}:{k.strip()}:{i}" for i, (f, _, k) in enumerate(QUOTED)]
)
def test_further_estimates_quoted_in_readme(fname, section, key):
    from headline import from_txt

    est, lo, hi = from_txt(RESULTS, fname, section, key)
    assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README, (
        f"{fname} / {section!r}: {est:.2f} ({lo:.2f}–{hi:.2f}) not in README"
    )


def test_trend_break_quoted_in_readme():
    """The jump of 2022 beyond the trend (stops_trend.txt, block A) for small sponsors and top-20 pharma."""
    with open(os.path.join(RESULTS, "stops_trend.txt"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("A (primary)"))
    block = lines[start : start + 8]
    for group in ("Industry, small (<=20)", "Top-20 pharma"):
        row = next(line for line in block if line.startswith(group))
        est, lo, hi = (float(x) for x in row[len(group) :].split()[1:4])
        assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README, f"{group}: {est:.2f} ({lo:.2f}–{hi:.2f}) not in README"


def test_placebo_quoted_in_readme():
    """The placebo band against none and supported against placebo (placebo_similarity.txt, primary model)."""
    with open(os.path.join(RESULTS, "placebo_similarity.txt"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("1. PRIMARY"))
    block = lines[start : start + 12]
    row = next(line for line in block if line.startswith("b_placebo"))
    est, lo, hi = (float(x) for x in row.split()[-3:])
    assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README
    row = next(line for line in block if line.startswith("supported against placebo"))
    est, lo, hi = (
        float(row.split("OR ")[1].split()[0]),
        float(row.split("(")[1].split()[0]),
        float(row.split(" to ")[1].split(")")[0]),
    )
    assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README


def test_cohort_contrast_quoted_in_readme():
    """The stacked contrast with the five-year window (evidence_arrival_ot_gwas_cohorts.txt, primary model)."""
    with open(os.path.join(RESULTS, "evidence_arrival_ot_gwas_cohorts.txt"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("1. PRIMARY"))
    row = next(line for line in lines[start : start + 12] if line.startswith("post_other"))
    est, lo, hi = (float(x) for x in row.split()[-3:])
    assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README


def test_before_and_after_2015_quoted_in_readme():
    """The response to later evidence and the selection gap by period (evidence_arrival_ot_gwas_2015.txt)."""
    import re

    with open(os.path.join(RESULTS, "evidence_arrival_ot_gwas_2015.txt"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("1. PRIMARY"))
    row = next(line for line in lines[start:] if line.startswith("post_late"))
    est, lo, hi = (float(x) for x in row.split()[-3:])
    assert f"{est:.2f} ({lo:.2f}–{hi:.2f})" in README
    start = next(i for i, line in enumerate(lines) if line.startswith("4. POST HOC"))
    row = next(line for line in lines[start:] if line.startswith("inverse, other sponsors against top-20 pharma"))
    found = re.findall(r"OR (\d+\.\d+) \((\d+\.\d+) to (\d+\.\d+)\)", row)
    assert len(found) == 2
    for est, lo, hi in found:
        assert f"{float(est):.2f} ({float(lo):.2f}–{float(hi):.2f})" in README
