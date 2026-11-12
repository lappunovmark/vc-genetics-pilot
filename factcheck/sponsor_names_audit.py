"""Audit of the top-20 sponsor name rules (pilot/sponsors.py) against the registry snapshot.

Usage (from the repository root): python factcheck/sponsor_names_audit.py CTGOV_ALL.csv [RESULTS_DIR]

The registry shows a sponsor under its current name. After an acquisition that name often carries the parent
("X, Inc., a subsidiary of Merck & Co., Inc."), and the trials X started as an independent company must not be typed
as the parent's. sponsors.py lets the entry that matches earliest in the name decide, so a renamed subsidiary needs
an entry of its own with its acquisition year. This script lists every industry sponsor name whose top-20 match is
NOT the leading name: each must be in sponsors.REVIEWED_NONLEADING (read by hand), otherwise the exit status is 1 and
the name needs either an entry with a year or a line in that list. It also prints the trials typed as top-20 through
an entry with a year window although they have no start date (the window cannot be applied to them).
Writes RESULTS_DIR/sponsor_names_audit.txt.
"""

import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import sponsors  # noqa: E402


def nonleading(names):
    """Sponsor names whose earliest top-20 match does not start the name and that are not in the reviewed list."""
    bad = []
    for n in names:
        e = sponsors.leading_entry(n) if isinstance(n, str) else None
        if e and e[0] > 0 and not any(n.startswith(k) for k in sponsors.REVIEWED_NONLEADING):
            bad.append(n)
    return sorted(set(bad))


def main(path, R=os.path.join(ROOT, "results")):
    ct = pd.read_csv(path, usecols=["nct_id", "lead_sponsor", "lead_class", "start_date"], dtype=str)
    ct = ct[ct.lead_class.eq("INDUSTRY")].copy()
    ct["year"] = pd.to_datetime(ct.start_date, errors="coerce", format="mixed").dt.year
    ct["parent"] = [sponsors.top20_parent(n, y) for n, y in zip(ct.lead_sponsor, ct.year)]
    g = ct.groupby("lead_sponsor").agg(
        trials=("nct_id", "size"), first=("year", "min"), last=("year", "max"), top20=("parent", "count")
    )
    g["entry"] = [sponsors.leading_entry(n) for n in g.index]
    a = g[g.entry.map(lambda e: e is not None and e[0] > 0)].sort_values("trials", ascending=False)
    bad = nonleading(a.index)
    w = ct[ct.year.isna() & ct.parent.notna()]
    w = w[w.lead_sponsor.map(lambda n: (lambda e: e[2] > 0 or e[3] < 9999)(sponsors.leading_entry(n)))]
    out = [
        f"industry trials: {len(ct)}; typed top-20: {int(ct.parent.notna().sum())}; sponsor names with a top-20 "
        f"entry: {int(g.entry.notna().sum())}",
        "=" * 100,
        "Names whose top-20 match is not the leading name (all must be in sponsors.REVIEWED_NONLEADING):",
        a[["trials", "first", "last", "top20", "entry"]].to_string() if len(a) else "  none",
        "=" * 100,
        "Not reviewed (must be empty):",
        "\n".join("  " + n for n in bad) if bad else "  none",
        "=" * 100,
        f"Trials without a start date typed top-20 through an entry with a year window: {len(w)}",
        w.lead_sponsor.value_counts().to_string() if len(w) else "  none",
    ]
    text = "\n".join(out)
    with open(os.path.join(R, "sponsor_names_audit.txt"), "w") as fh:
        fh.write(text + "\n")
    print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
