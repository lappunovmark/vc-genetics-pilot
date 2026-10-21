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
