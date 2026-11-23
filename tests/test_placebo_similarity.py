"""Bands of the highest similarity between a target's ex-ante genetic evidence and the indication."""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import placebo_similarity as ps

ENTRIES = pd.DataFrame(
    [
        ("d1", "I1", 2010),
        ("d2", "I1", 2010),
        ("d3", "I1", 2010),
        ("d4", "I1", 2010),
        ("d5", "I1", 2010),
        ("d6", "I1", 2010),
    ],
    columns=["drug", "indication_mesh_id", "yr"],
)
TARGETS = pd.DataFrame(
    [
        ("d1", "I1", "G1"),
        ("d2", "I1", "G2"),
        ("d3", "I1", "G3"),
        ("d3", "I1", "G2"),
        ("d4", "I1", "G4"),
        ("d5", "I1", "G5"),
        ("d6", "I1", "G6"),
    ],
    columns=["drug", "indication_mesh_id", "gene"],
)
ASSOC = pd.DataFrame(
    [
        ("G1", "I1", "OTG", 2005),  # the indication itself, before the entry
        ("G2", "T_far", "OTG", 2008),  # unrelated trait
        ("G3", "T_mid", "OMIM", np.nan),  # OMIM counts as ex ante
        ("G4", "I1", "OTG", 2012),  # after the entry: does not count
        ("G5", "T_unknown", "OTG", 2001),  # trait without a score
        ("G6", "T_near", "OTG", 2009),
        ("G6", "T_far", "OTG", 2003),
    ],
    columns=["gene", "mesh_id", "source", "year"],
)
SIM = pd.DataFrame(
    [("I1", "T_far", 0.05), ("I1", "T_mid", 0.6), ("I1", "T_near", 0.85)],
    columns=["meshcode_a", "meshcode_b", "comb_norm"],
)


def test_bands():
    s = ps.max_similarity(ENTRIES, TARGETS, ASSOC, SIM).set_index("drug")
    got = {d: ps.band(s.at[d, "max_sim"], s.at[d, "n_assoc"]) for d in s.index}
    assert got == {
        "d1": "supported",
        "d2": "placebo",
        "d3": "0.5-0.8",
        "d4": "none",
        "d5": "unscored",
        "d6": "supported",
    }
    assert ps.band(0.15, 2, cut=0.1) == "0.1-0.5" and ps.band(0.05, 2, cut=0.1) == "placebo"
    assert s.at["d5", "n_unscored"] == 1 and s.at["d6", "n_assoc"] == 2
