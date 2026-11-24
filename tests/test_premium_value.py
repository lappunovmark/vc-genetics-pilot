"""Cost arithmetic of pilot/premium_value.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import premium_value as pv


def test_expected_cost_reproduces_the_cost_study():
    # DiMasi et al. (2016), Table 2: 59.52% of compounds enter phase 2 and 21.14% phase 3; expected cost 114.2
    m = pv.money((0.5952, 0.2114 / 0.5952, 0.5))
    assert abs(m["cost_entrant"] - 114.2) < 0.05
    assert abs(m["p_approval"] - 0.1057) < 1e-4 and abs(m["cost_approval"] - m["cost_entrant"] / 0.1057) < 1e-6


def test_money_by_hand():
    m = pv.money((0.5, 0.5, 0.5), cost={1: 10, 2: 20, 3: 40})
    assert m["p_approval"] == 0.125 and m["per_approval"] == 8
    assert m["cost_entrant"] == 10 + 10 + 10 and m["cost_approval"] == 240
