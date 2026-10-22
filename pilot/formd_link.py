"""Link industry trial sponsors to SEC Form D issuers (private placements in biotech, pharma and health care).

Usage: python formd_link.py FORMD_CSV RESULTS_DIR
Inputs: FORMD_CSV from fetch_formd.py; RESULTS_DIR/sponsors.csv.gz from build_panel26.py (one row per trial record).
Issuer names include current and previous names reported on the filing and in EDGAR, all mapped to the issuer CIK.
Matching follows sbir_link.py (precision first): exact match of normalised names, then RapidFuzz token_sort_ratio >= 92
within blocks sharing the first normalised token. A match is used only if the two names agree after removing legal
forms alone, and it is not rejected in formd_decisions.csv, or if it is accepted there after hand review.
For each accepted sponsor: year of its first Form D filing (any non-fund offering in these industry groups), number of
filings and the largest amount reported sold.
Writes RESULTS_DIR/formd_match_review.csv (every candidate match), formd_sponsors.csv (accepted, one row per sponsor
name) and formd_summary.txt.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from sbir_link import match, strict

DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formd_decisions.csv")
NAME_COLS = [
    "ENTITYNAME",
    "ISSUER_PREVIOUSNAME_1",
    "ISSUER_PREVIOUSNAME_2",
    "ISSUER_PREVIOUSNAME_3",
    "EDGAR_PREVIOUSNAME_1",
    "EDGAR_PREVIOUSNAME_2",
    "EDGAR_PREVIOUSNAME_3",
]
IND = ["Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]


def issuers(path):
    """One row per (normalised issuer name, CIK) with the CIK's filing history."""
    f = pd.read_csv(path, dtype=str)
    f["filing_year"] = pd.to_datetime(f.FILING_DATE, errors="coerce", format="mixed").dt.year
    f["sold"] = pd.to_numeric(f.TOTALAMOUNTSOLD, errors="coerce")
    f = f[f.CIK.notna() & f.filing_year.notna()]
    hist = f.groupby("CIK").agg(
        formd_first_year=("filing_year", "min"),
        formd_last_year=("filing_year", "max"),
        formd_filings=("ACCESSIONNUMBER", "nunique"),
        formd_max_sold=("sold", "max"),
        formd_industry=("INDUSTRYGROUPTYPE", lambda x: x.mode().iat[0] if len(x.mode()) else None),
        formd_state=("STATEORCOUNTRY", "first"),
        formd_entity=("ENTITYNAME", "last"),
    )
    names = (
        f.melt(id_vars=["CIK"], value_vars=[c for c in NAME_COLS if c in f.columns], value_name="issuer_name")
        .dropna(subset=["issuer_name"])
        .drop(columns="variable")
        .drop_duplicates()
    )
    names = names[names.issuer_name.str.strip().ne("")]
    names["norm"] = names.issuer_name.map(rq2_stops.norm_sponsor)
    names = names[names.norm.notna() & names.norm.str.len().ge(3)]
    names = names.drop_duplicates(["norm", "CIK"]).merge(hist.reset_index(), on="CIK")
    return names, len(f)


def sponsors(R):
    s = pd.read_csv(f"{R}/sponsors.csv.gz", dtype=str)
    s = s[s.sponsor_tier.isin(IND)]
    s["norm"] = s.lead_sponsor.map(rq2_stops.norm_sponsor)
    return (
        s.dropna(subset=["norm"])
        .groupby("norm")
        .agg(
            lead_sponsor=("lead_sponsor", "first"),
            tier=("sponsor_tier", "first"),
            n_trials=("clinicalReportId", "nunique"),
        )
        .reset_index()
    )


def apply_decisions(m, path=DECISIONS):
    m = m.copy()
    m["strict_eq"] = [strict(a) == strict(b) for a, b in zip(m.lead_sponsor, m.issuer_name)]
    dec = {}
    if os.path.exists(path):
        d = pd.read_csv(path)
        dec = {(strict(a), strict(b)): v for a, b, v in zip(d.lead_sponsor, d.issuer_name, d.decision)}
    m["decision"] = [dec.get((strict(a), strict(b))) for a, b in zip(m.lead_sponsor, m.issuer_name)]
    m["accepted"] = (m.strict_eq & m.decision.ne("reject")) | m.decision.eq("accept")
    return m


def main(formd_csv, R):
    names, n_rows = issuers(formd_csv)
    sp = sponsors(R)
    # one candidate CIK per normalised name: the one with the most filings
    best = names.sort_values("formd_filings", ascending=False).drop_duplicates("norm")
    m = match(sp, best).rename(columns={"sbir_norm": "issuer_norm"})
    m = apply_decisions(m)
    cols = ["match", "accepted", "decision", "strict_eq", "lead_sponsor", "issuer_name", "norm", "issuer_norm",
            "score", "CIK", "tier", "n_trials", "formd_first_year", "formd_filings", "formd_max_sold",
            "formd_industry", "formd_state"]  # fmt: skip
    m[cols].sort_values(["accepted", "match", "score"]).to_csv(f"{R}/formd_match_review.csv", index=False)
    acc = m[m.accepted]
    acc[
        ["norm", "lead_sponsor", "issuer_name", "CIK", "tier", "formd_first_year", "formd_filings", "formd_max_sold"]
    ].to_csv(f"{R}/formd_sponsors.csv", index=False)
    out = [
        f"Form D rows kept (biotech, pharma, other health care; no pooled funds): {n_rows}; issuer CIKs: "
        f"{names.CIK.nunique()}; issuer names incl. previous names: {len(names)}",
        f"non-top-20 industry sponsor names in the panel: {len(sp)}",
        f"candidate matches: {len(m)} (exact {int(m.match.eq('exact').sum())}, fuzzy {int(m.match.eq('fuzzy').sum())}); "
        f"accepted {len(acc)} (strict name agreement {int((m.strict_eq & m.accepted).sum())}, accepted after hand "
        f"review {int((~m.strict_eq & m.accepted).sum())}, not used {int((~m.accepted).sum())})",
        "",
        "Share of sponsor names matched to a Form D issuer, by tier:",
        sp.assign(matched=sp.norm.isin(acc.norm))
        .groupby("tier")
        .matched.agg(["mean", "sum", "size"])
        .round(4)
        .to_string(),
    ]
    open(f"{R}/formd_summary.txt", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:3])
