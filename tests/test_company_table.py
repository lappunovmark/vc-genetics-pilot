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
