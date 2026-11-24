"""The before/after terms of pilot/evidence_arrival_2015.py."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))


def test_add_late_marks_stacks_from_the_cut():
    import evidence_arrival_2015 as m

    s = pd.DataFrame(
        {"cohort": [2015, 2015, 2016, 2019], "post": [1, 0, 1, 1], "e0": [0, 1, 0, 0], "grp": [0, 1, 0, 1]}
    )
    t = m.add_late(s, 2016)
    assert t.late.tolist() == [0, 0, 1, 1]
    assert t.post_late.tolist() == [0, 0, 1, 1] and t.e0_late.tolist() == [0, 0, 0, 0]
    assert t.post_late_other.tolist() == [0, 0, 0, 1]
    assert m.add_late(s, 2017).late.tolist() == [0, 0, 0, 1]
