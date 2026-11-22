"""The stage of a sponsor in the year of a trial (pilot/vc_stage.py): the rules of docs/plan_vc_stage.md on made-up sponsors."""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import vc_stage

NAN = np.nan
S = pd.DataFrame(
    {
        # ipo_year, vc_ipo, reg_year, mark_year (round or board), owner_vc_year
        "ipo vc": [2015, True, 2014, NAN, NAN],
        "ipo no vc": [2015, False, 2014, NAN, NAN],
        "ipo no vc, round": [2015, False, 2014, 2010, NAN],
        "private, round": [NAN, False, NAN, 2010, NAN],
        "private, nothing": [NAN, False, NAN, NAN, NAN],
        "registrant": [NAN, False, 2008, NAN, NAN],
        "registrant, owner vc": [NAN, False, 2008, NAN, 2012],
        "old registrant": [NAN, False, 2001, NAN, NAN],
    },
    index=["ipo_year", "vc_ipo", "reg_year", "mark_year", "owner_vc_year"],
).T
S["vc_ipo"] = S.vc_ipo.astype(bool)
for c in ("ipo_year", "reg_year", "mark_year", "owner_vc_year"):
    S[c] = pd.to_numeric(S[c])


def g(name, year, strict=False):
    return vc_stage.stage([name], [year], S, strict=strict).iloc[0]


def test_ipo_year_counts_as_private():
    assert g("ipo vc", 2010) == "A"
    assert g("ipo vc", 2015) == "A"
    assert g("ipo vc", 2016) == "B"


def test_strict_needs_a_dated_marker():
    assert g("ipo vc", 2010, strict=True) == "D"
    assert g("ipo no vc, round", 2012, strict=True) == "A"
    assert g("ipo vc", 2016, strict=True) == "B"


def test_without_venture_marker():
    assert g("ipo no vc", 2012) == "D"
    assert g("ipo no vc", 2016) == "C"
    assert g("private, nothing", 2012) == "D"


def test_marker_must_precede_the_trial_year():
    assert g("private, round", 2010) == "D"
    assert g("private, round", 2011) == "A"
    assert g("ipo no vc, round", 2010) == "D"
    assert g("ipo no vc, round", 2016) == "B"


def test_registrant_without_ipo_year():
    assert g("registrant", 2008) == "D"
    assert g("registrant", 2009) == "C"
    assert g("registrant, owner vc", 2012) == "C"
    assert g("registrant, owner vc", 2013) == "B"
    assert g("old registrant", 2001) == "C"


def test_unknown_sponsor_is_the_rest():
    assert g("not in any source", 2012) == "D"
