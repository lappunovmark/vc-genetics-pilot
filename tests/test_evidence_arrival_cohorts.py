"""Stacks of the cohort-by-cohort evidence-arrival contrast (pilot/evidence_arrival_cohorts.py) on a made-up panel."""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import evidence_arrival_cohorts as eac


def panel():
    rows = []
    # pid 1: evidence 2010; pid 2: evidence 2015; pid 3 and 4: never supported
    for pid, e in ((1, 2010), (2, 2015), (3, np.nan), (4, np.nan)):
        for year in range(2000, 2026):
            top = int((pid, year) in {(1, 2012), (2, 2001), (3, 2011), (4, 2024)})
            oth = int((pid, year) in {(1, 2008), (2, 2016), (3, 2003)})
            rows.append((pid, year, "I", int(year > e) if e == e else 0, int(year == e) if e == e else 0, e, top, oth))
    return pd.DataFrame(rows, columns=["pid", "year", "indication_mesh_id", "post", "e0", "E", "top", "oth"])


def test_stacks():
    s, n = eac.stacks(panel(), "top", "oth", 5)
    assert n == 2 and set(s.cohort) == {2010, 2015}
    a = s[s.cohort.eq(2010)]
    assert a.year.min() == 2005 and a.year.max() == 2015
    # pair 2 (evidence 2015) is not a control in the 2010 stack; pair 4 has no start in the window and drops
    assert set(a[a.grp.eq(0)].pid) == {1, 3}
    # other industry in the 2010 stack: pair 1 (start in 2008); pair 3 started only in 2003, outside the window
    assert set(a[a.grp.eq(1)].pid) == {1}
    b = s[s.cohort.eq(2015)]
    assert set(b[b.grp.eq(0)].pid) == {3} and set(b[b.grp.eq(1)].pid) == {2}
    assert (s.post_other == s.post * s.grp).all()
    # the same pair-group in two stacks has two fixed effects
    assert s[s.pid.eq(3) & s.grp.eq(0)].pg.nunique() == 2
    assert int(s[s.E.notna() & s.post.eq(1)].y.sum()) == 2


def test_cohort_filter():
    s, n = eac.stacks(panel(), "top", "oth", 5, cohorts=(2011, 2019))
    assert n == 1 and set(s.cohort) == {2015}
