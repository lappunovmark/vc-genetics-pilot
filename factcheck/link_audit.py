"""Location audit of the accepted links between trial sponsors and Form D issuers.

Usage: python factcheck/link_audit.py CTGOV_ALL_CSV CTGOV_COUNTRIES_CSV RESULTS_DIR
(CTGOV_COUNTRIES_CSV of pilot/fetch_ctgov_countries.py; RESULTS_DIR holds formd_match_review.csv; plan written before
the data were fetched: docs/plan_link_audit.md)

An accepted link is flagged when the issuer's Form D state is a US state and the sponsor led at least three trials
with listed sites, none of them with a site in the United States. Writes link_audit.txt and link_audit_flags.csv
(the flagged links, to be read; the column `class` is filled by hand).
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))
import rq2_stops

US = set(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR "
    "PA PR RI SC SD TN TX UT VT VA WA WV WI WY".split()
)
MIN_TRIALS = 3


def sponsor_sites(ct, countries):
    """Per normalised sponsor name: trials led, trials with listed sites, trials with a US site, countries by count."""
    t = ct.merge(countries, on="nct_id", how="left")
    t["norm"] = t.lead_sponsor.map(rq2_stops.norm_sponsor)
    t["countries"] = t.countries.fillna("")
    t["has_sites"] = t.countries.ne("")
    t["us"] = t.countries.map(lambda s: "United States" in s.split("|"))
    g = t.groupby("norm")
    out = g.agg(trials=("nct_id", "size"), with_sites=("has_sites", "sum"), us_trials=("us", "sum"))
    top = (
        t[t.has_sites]
        .assign(c=lambda d: d.countries.str.split("|"))
        .explode("c")
        .groupby(["norm", "c"])
        .size()
        .rename("n")
        .reset_index()
        .sort_values(["norm", "n", "c"], ascending=[True, False, True])
    )
    out["top_countries"] = top.groupby("norm").apply(lambda d: "; ".join(f"{c} {n}" for c, n in zip(d.c[:4], d.n[:4])))
    t["start_year"] = pd.to_numeric(t.start_date.astype(str).str[:4], errors="coerce")
    out["first_start"] = t.groupby("norm").start_year.min()
    out["last_start"] = t.groupby("norm").start_year.max()
    return out


def flags(links, sites):
    m = links[links.accepted.astype(bool)].merge(sites, left_on="norm", right_index=True, how="left")
    m["us_issuer"] = m.formd_state.isin(US)
    m["screened"] = m.with_sites.fillna(0) >= MIN_TRIALS
    m["flag"] = m.us_issuer & m.screened & m.us_trials.fillna(0).eq(0)
    return m


def main(ctgov, ccsv, R):
    ct = pd.read_csv(ctgov, usecols=["nct_id", "lead_sponsor", "start_date"], dtype=str)
    countries = pd.read_csv(ccsv, dtype=str)
    links = pd.read_csv(f"{R}/formd_match_review.csv", low_memory=False)
    m = flags(links, sponsor_sites(ct, countries))
    out = ["Location audit of the accepted sponsor-issuer links (plan: docs/plan_link_audit.md)"]
    out.append(f"studies in the snapshot: {len(ct)}; with site countries downloaded: {int(ct.nct_id.isin(countries.nct_id).sum())}")  # fmt: skip
    out.append(
        f"accepted links: {len(m)}; issuer in a US state: {int(m.us_issuer.sum())}; sponsor with at least {MIN_TRIALS} "
        f"trials with listed sites: {int(m.screened.sum())}; both: {int((m.us_issuer & m.screened).sum())}; flagged (no "
        f"trial with a US site): {int(m.flag.sum())}"
    )
    cols = ["lead_sponsor", "issuer_name", "CIK", "strict_eq", "formd_state", "formd_first_year", "formd_last_year", "trials", "with_sites", "us_trials", "top_countries", "first_start", "last_start"]  # fmt: skip
    f = m[m.flag][cols].sort_values("lead_sponsor").assign(**{"class": "", "note": ""})
    path = f"{R}/link_audit_flags.csv"
    if os.path.exists(path):  # keep the classes already filled in by hand
        old = pd.read_csv(path, dtype=str).set_index("CIK")
        for c in ("class", "note"):
            f[c] = f.CIK.astype(str).map(old[c]).fillna("")
    f.to_csv(path, index=False)
    if f["class"].ne("").any():
        out.append(f"classes of the flagged links: {f['class'].value_counts().to_dict()}")
    open(f"{R}/link_audit.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
