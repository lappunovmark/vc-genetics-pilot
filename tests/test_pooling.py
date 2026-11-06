"""pooling.pool_sparse: sparse control categories are pooled, exposures and dense categories are left alone."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pilot"))
from pooling import pool_sparse  # noqa: E402


def frame():
    return pd.DataFrame(
        {
            "y": [1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1],
            "area": ["onc"] * 5 + ["imm"] * 2 + ["neu"] * 10,
            "yb": ["a", "a", "a", "a", "a", "b", "b", "c", "c", "c", "c", "c", "d", "d", "d", "d", "e"],
            "fin": [1, 0] * 8 + [1],
        }
    )


def test_nominal_sparse_merged_into_largest_dense_level():
    d = pool_sparse(frame(), "y ~ fin + C(area) + C(yb)")
    assert set(d.area) == {"onc", "neu"}  # imm has 1 event -> merged into neu (largest level with events)
    assert (d.area.eq("neu").sum()) == 12


def test_nominal_sparse_merged_into_other_when_other_has_events():
    f = frame()
    f["area"] = ["onc"] * 5 + ["imm"] * 2 + ["other"] * 10
    d = pool_sparse(f, "y ~ fin + C(area)")
    assert set(d.area) == {"onc", "other"} and (d.area.eq("other").sum()) == 12


def test_ordered_sparse_merged_forward_and_top_end_backward():
    d = pool_sparse(frame(), "y ~ fin + C(area) + C(yb)")
    # events by yb: a=3, b=1, c=3, d=3, e=1 -> b merges into c; e (top end) merges into d
    assert set(d.yb) == {"a", "c", "d"}
    assert (d.yb.eq("c").sum()) == 7 and (d.yb.eq("d").sum()) == 5


def test_exposure_and_absent_controls_untouched():
    f = frame()
    d = pool_sparse(f, "y ~ fin + C(yb)")
    assert d.fin.equals(f.fin) and d.area.equals(f.area)  # area not in the formula
    assert len(d) == len(f)


def test_response_taken_from_formula():
    f = frame().rename(columns={"y": "adv"})
    d = pool_sparse(f, "adv ~ fin + C(area)")
    assert set(d.area) == {"onc", "neu"}
