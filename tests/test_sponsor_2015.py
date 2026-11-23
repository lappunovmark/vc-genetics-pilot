"""Moves between sponsor names of April 2015 and of the snapshot (pilot/sponsor_2015.py), on made-up trials."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import sponsor_2015

CT = pd.DataFrame(
    [
        ("NCT00000001", "Bristol-Myers Squibb", "INDUSTRY", "2012-05-01"),  # record moved to the acquirer
        ("NCT00000002", "Pfizer", "INDUSTRY", "2010-01-01"),  # same name then and now
        ("NCT00000003", "Some Biotech, Inc.", "INDUSTRY", "2010-01-01"),  # was a top-20 trial in 2015
        ("NCT00000004", "Some University", "OTHER", "2010-01-01"),  # not industry today: never a move
        ("NCT00000005", "Pfizer Inc.", "INDUSTRY", "2011-01-01"),  # only the legal form differs
        ("NCT00000006", "Pfizer", "INDUSTRY", "2011-01-01"),  # not in the 2015 copy
    ],
    columns=["nct_id", "lead_sponsor", "lead_class", "start_date"],
)
IC = pd.DataFrame(
    [
        ("NCT00000001", "Celgene Corporation"),
        ("NCT00000002", "Pfizer"),
        ("NCT00000003", "Pfizer"),
        ("NCT00000004", "Pfizer"),
        ("NCT00000005", "Pfizer"),
    ],
    columns=["nct_id", "sponsor_2015"],
)


def test_moves():
    t = sponsor_2015.compare(CT, IC).set_index("nct_id")
    assert len(t) == 5
    assert t.at["NCT00000001", "moved_in"] and not t.at["NCT00000001", "moved_out"]
    assert not t.at["NCT00000002", "moved_in"] and not t.at["NCT00000002", "moved_out"]
    assert t.at["NCT00000003", "moved_out"] and not t.at["NCT00000003", "moved_in"]
    assert not t.at["NCT00000004", "moved_in"] and not t.at["NCT00000004", "moved_out"]
    assert not t.at["NCT00000005", "changed"] and t.at["NCT00000001", "changed"]


def test_retype():
    t = sponsor_2015.compare(CT, IC).set_index("nct_id")
    bands = {"celgene": "Industry, large (>30)"}
    got = sponsor_2015.retype(
        ["Top-20 pharma", "Top-20 pharma", "Industry, small (<=5 drugs)", "Top-20 pharma"],
        ["NCT00000001", "NCT00000002", "NCT00000003", "NCT00000006"],
        t,
        bands,
    )
    assert got == ["Industry, large (>30)", "Top-20 pharma", "Top-20 pharma", "Top-20 pharma"]
    assert sponsor_2015.retype(["Top-20 pharma"], ["NCT00000001"], t, {}) == [None]
