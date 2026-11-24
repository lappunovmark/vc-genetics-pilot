"""Intervals used in pilot/company_table.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import company_table as ct


def test_wilson_and_poisson():
    lo, hi = ct.wilson(10, 100)
    assert abs(lo - 0.0552) < 1e-3 and abs(hi - 0.1744) < 1e-3
    lo, hi = ct.poisson_ci(10)
    assert abs(lo - 4.795) < 1e-2 and abs(hi - 18.39) < 1e-2
    assert ct.poisson_ci(0)[0] == 0.0 and abs(ct.poisson_ci(0)[1] - 3.689) < 1e-2


def test_drug_level_collapses_programmes():
    import pandas as pd

    d = pd.DataFrame(
        {
            "company": ["A", "A", "A", "B"],
            "drug": ["x", "x", "y", "x"],
            "y": [0, 1, 0, 0],
            "first_year": [2004, 2011, 2012, 2016],
            "area": ["oncology", "neurology", "oncology", "oncology"],
            "modality": ["antibody"] * 4,
        }
    )
    g = ct.drug_level(d).set_index(["company", "drug"])
    assert len(g) == 3
    assert g.loc[("A", "x"), "y"] == 1 and g.loc[("A", "x"), "n_prog"] == 2
    assert g.loc[("A", "x"), "area"] == "oncology" and g.loc[("A", "x"), "first_year"] == 2004
    assert g.loc[("B", "x"), "y"] == 0
