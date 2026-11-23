"""The location flag of factcheck/link_audit.py on made-up sponsors."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "factcheck"))
import link_audit


def test_flags():
    rows, cc = [], []
    for sponsor, sites in (
        ("Alpha Bio Inc.", ["China", "China", "China|Australia"]),  # three trials, none in the US
        ("Beta Bio Inc.", ["China", "China", "United States|China"]),  # one trial with a US site
        ("Gamma Bio Inc.", ["China", "China", ""]),  # only two trials with sites
        ("Delta Bio Inc.", ["Israel", "Israel", "Israel"]),  # issuer not in a US state
    ):
        for i, s in enumerate(sites):
            nct = f"NCT{len(rows):08d}"
            rows.append((nct, sponsor, f"201{i}-01-01" if i else None))  # a trial without a start date
            cc.append((nct, s))
    ct = pd.DataFrame(rows, columns=["nct_id", "lead_sponsor", "start_date"])
    countries = pd.DataFrame(cc, columns=["nct_id", "countries"])
    links = pd.DataFrame(
        {
            "norm": ["alpha bio", "beta bio", "gamma bio", "delta bio"],
            "accepted": [True, True, True, True],
            "formd_state": ["CA", "CA", "MA", "L3"],
        }
    )
    sites = link_audit.sponsor_sites(ct, countries)
    assert sites.at["alpha bio", "with_sites"] == 3 and sites.at["beta bio", "us_trials"] == 1
    m = link_audit.flags(links, sites).set_index("norm")
    assert m.flag.to_dict() == {"alpha bio": True, "beta bio": False, "gamma bio": False, "delta bio": False}
    assert sites.at["alpha bio", "top_countries"].startswith("China 3")
    assert sites.at["alpha bio", "first_start"] == 2011 and sites.at["alpha bio", "last_start"] == 2012
