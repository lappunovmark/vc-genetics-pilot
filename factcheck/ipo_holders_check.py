"""Compare the reader of IPO prospectus tables with holders read by eye.

Usage: python ipo_holders_check.py RESULTS_DIR   (RESULTS_DIR holds ipo_holders.csv of pilot/ipo_holders.py)

ipo_holders_check.csv lists, for 20 prospectuses drawn at random from the primary sample, every holder of 5% or
more that is not a natural person, as read by eye from an independent rendering of the table (BeautifulSoup with
lxml, not the reader's own parser): 95 holders. The script reports holders the reader misses, adds or gives a
different percentage for, and exits with an error if there is any.
"""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
eye = pd.read_csv(os.path.join(HERE, "ipo_holders_check.csv"))
got = pd.read_csv(os.path.join(sys.argv[1], "ipo_holders.csv"))
got = got[got.accession.isin(eye.accession) & (got.person == 0) & (got.pct_before >= 5)]
m = eye.merge(got[["accession", "holder", "pct_before"]], on=["accession", "holder"], how="outer", suffixes=("_eye", ""), indicator=True)  # fmt: skip
missed = m[m._merge == "left_only"]
added = m[m._merge == "right_only"]
differ = m[(m._merge == "both") & ((m.pct_before_eye - m.pct_before).abs() > 1e-9)]
print(f"prospectuses: {eye.accession.nunique()}; holders read by eye: {len(eye)}; agree: {len(m) - len(missed) - len(added) - len(differ)}")  # fmt: skip
for label, d in (("missed by the reader", missed), ("added by the reader", added), ("different percentage", differ)):
    print(f"{label}: {len(d)}")
    if len(d):
        print(d[["accession", "holder", "pct_before_eye", "pct_before"]].to_string(index=False))
sys.exit(1 if len(missed) + len(added) + len(differ) else 0)
