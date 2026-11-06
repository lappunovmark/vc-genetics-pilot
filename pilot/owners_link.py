"""Who owned the sponsor? Beneficial owners (Schedule 13D/13G filers) of trial sponsors that are or became public.

Usage: python owners_link.py EDGAR_DIR RESULTS_DIR
Inputs: EDGAR_DIR/edgar_ownership.csv.gz and edgar_registrants.csv.gz from fetch_edgar_owners.py; RESULTS_DIR/
sponsors.csv.gz (build_panel26.py) and formd_sponsors.csv (formd_link.py; gives the CIKs of Form D filers).

Sponsor CIKs. A non-top-20 industry sponsor's legal entities are (a) the CIKs of its accepted Form D issuers and
(b) EDGAR registrants (filers of S-1, F-1, 424B4, 10-K, 20-F or 40-F) whose name equals the sponsor's name once legal
forms are removed, or is accepted in pilot/owners_decisions.csv after hand review (same rules as the SBIR and Form D
linkages; fuzzy candidates are written for review and not used unless accepted).

Owners. A Schedule 13D or 13G is indexed under the subject company and under each reporting person with the same
accession number, so for every accession in which a sponsor CIK appears, the other parties are its owners. Owner names
are classified with pilot/investor_classes.tsv (tab-separated regular expressions, first match wins): venture capital, crossover or
hedge fund, asset manager or index fund, corporate, bank or broker, other; unmatched names are "unclassified" and
listed in owners_review.csv by the number of sponsors they hold, for hand classification.

Writes RESULTS_DIR/owners_pairs.csv.gz (sponsor x owner x first and last filing), owners_sponsors.csv (one row per
sponsor: CIKs, first registration year, owners by class, first venture-capital filing year), owners_registrant_review.csv
(name matches to registrants), owners_review.csv (owner names by frequency and class) and owners_summary.txt.
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from sbir_link import match, strict

HERE = os.path.dirname(os.path.abspath(__file__))
DECISIONS = os.path.join(HERE, "owners_decisions.csv")
CLASSES = os.path.join(HERE, "investor_classes.tsv")
IND = ["Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]
ACC = re.compile(r"(\d{10}-\d{2}-\d{6})")
EDGAR_SUFFIX = re.compile(r"\s*/\s*(?:[A-Z]{2}|NEW|DELAWARE|CANADA|ADR|OLD)\s*/?\s*$", re.I)


def clean(s):
    return EDGAR_SUFFIX.sub("", str(s)).strip()


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


def registrants(path):
    """One row per (registrant CIK, name): first and last registration or annual-report filing."""
    r = pd.read_csv(path, dtype=str)
    r["name"] = r.name.map(clean)
    r["year"] = pd.to_datetime(r.date, errors="coerce").dt.year
    r = r[r.year.notna()]
    g = r.groupby(["cik", "name"]).agg(first_year=("year", "min"), last_year=("year", "max"), n=("form", "size"))
    g = g.reset_index()
    g["norm"] = g.name.map(rq2_stops.norm_sponsor)
    g["fname"] = g.name.map(strict)
    return g[g.norm.notna() & g.norm.str.len().ge(3)]


def decisions(path=DECISIONS):
    if not os.path.exists(path):
        return {}
    d = pd.read_csv(path)
    return {(strict(a), strict(b)): v for a, b, v in zip(d.lead_sponsor, d.registrant, d.decision)}


def sponsor_ciks(sp, reg, formd_path):
    """CIK set per sponsor: accepted Form D issuers plus registrants with the sponsor's exact (or accepted) name."""
    ciks = {}
    if os.path.exists(formd_path):
        fd = pd.read_csv(formd_path, dtype=str)
        for norm, c in zip(fd.norm, fd.CIK):
            ciks.setdefault(norm, set()).update(x.lstrip("0") for x in str(c).split(";") if x and x != "nan")
    cand = reg.rename(columns={"name": "registrant"})
    m = match(sp, cand[["norm", "cik", "registrant", "fname", "first_year", "last_year", "n"]]).rename(
        columns={"sbir_norm": "registrant_norm"}
    )
    dec = decisions()
    m["strict_eq"] = [strict(a) == b for a, b in zip(m.lead_sponsor, m.fname)]
    m["decision"] = [dec.get((strict(a), b)) for a, b in zip(m.lead_sponsor, m.fname)]
    m["accepted"] = (m.strict_eq & m.decision.ne("reject")) | m.decision.eq("accept")
    m["known_formd_cik"] = [c in ciks.get(n, set()) for n, c in zip(m.norm, m.cik)]
    for norm, c in zip(m.norm[m.accepted | m.known_formd_cik], m.cik[m.accepted | m.known_formd_cik]):
        ciks.setdefault(norm, set()).add(c)
    return ciks, m.sort_values(["accepted", "match", "score", "norm"], kind="mergesort")


def owner_classes(path=CLASSES):
    if not os.path.exists(path):
        return []
    d = pd.read_csv(path, sep="\t")
    return [(re.compile(p, re.I), c) for p, c in zip(d.pattern, d["class"])]


def classify(name, rules):
    for rx, c in rules:
        if rx.search(name):
            return c
    return "unclassified"


def pairs(own_path, ciks):
    """Sponsor x owner pairs from the ownership index lines."""
    o = pd.read_csv(own_path, dtype=str)
    o["acc"] = o.filename.str.extract(ACC, expand=False)
    o = o[o.acc.notna()].copy()
    o["name"] = o.name.map(clean)
    o["cik"] = o.cik.str.lstrip("0")
    o["date"] = pd.to_datetime(o.date, errors="coerce")
    cik_to_norms = {}
    for n, cs in ciks.items():
        for c in cs:
            cik_to_norms.setdefault(c, set()).add(n)
    hit = o[o.cik.isin(cik_to_norms)]
    o = o[o.acc.isin(set(hit.acc))]
    parties = o.groupby("acc").agg(ciks=("cik", lambda x: sorted(set(x))))
    single = int((parties.ciks.str.len() == 1).sum())
    rows = []
    for acc, g in o.groupby("acc", sort=False):
        subj = [c for c in set(g.cik) if c in cik_to_norms]
        for s_cik in subj:
            for r in g[g.cik != s_cik].drop_duplicates("cik").itertuples(index=False):
                for norm in cik_to_norms[s_cik]:
                    rows.append(
                        {
                            "norm": norm,
                            "sponsor_cik": s_cik,
                            "owner_cik": r.cik,
                            "owner_name": r.name,
                            "form": r.form,
                            "date": r.date,
                            "acc": acc,
                            "ambiguous": len(subj) > 1,
                        }
                    )
    p = pd.DataFrame(rows)
    return p, {"accessions": len(parties), "accessions_with_one_party": single}


def main(edgar_dir, R):
    sp = sponsors(R)
    reg = registrants(f"{edgar_dir}/edgar_registrants.csv.gz")
    ciks, review = sponsor_ciks(sp, reg, f"{R}/formd_sponsors.csv")
    review.to_csv(f"{R}/owners_registrant_review.csv", index=False)
    p, info = pairs(f"{edgar_dir}/edgar_ownership.csv.gz", ciks)
    rules = owner_classes()
    p["owner_class"] = p.owner_name.map(lambda s: classify(s, rules))
    p = p.sort_values(["norm", "owner_cik", "date"], kind="mergesort")
    agg = (
        p.groupby(["norm", "owner_cik"])
        .agg(
            owner_name=("owner_name", "last"),
            owner_class=("owner_class", "first"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            filings=("acc", "nunique"),
            ambiguous=("ambiguous", "any"),
        )
        .reset_index()
    )
    agg.to_csv(f"{R}/owners_pairs.csv.gz", index=False)
    # first registration year per sponsor (IPO proxy; companies public before the index window show its first year)
    reg_first = {}
    for norm, cs in ciks.items():
        y = reg[reg.cik.isin(cs)].first_year
        reg_first[norm] = int(y.min()) if len(y) else pd.NA
    vc = agg[agg.owner_class.eq("venture capital")]
    out = sp.copy()
    out["ciks"] = out.norm.map(lambda n: ";".join(sorted(ciks.get(n, set()), key=int)))
    out["is_registrant"] = out.norm.map(lambda n: pd.notna(reg_first.get(n, pd.NA)))
    out["registrant_first_year"] = out.norm.map(reg_first)
    out["n_owners"] = out.norm.map(agg.groupby("norm").size()).fillna(0).astype(int)
    for c in sorted(agg.owner_class.unique()):
        out[f"n_{re.sub(r'[^a-z]+', '_', c)}"] = (
            out.norm.map(agg[agg.owner_class.eq(c)].groupby("norm").size()).fillna(0).astype(int)
        )
    out["vc_backed"] = out.norm.isin(vc.norm)
    out["first_vc_year"] = out.norm.map(vc.groupby("norm").first_date.min().dt.year)
    out["vc_names"] = out.norm.map(vc.groupby("norm").owner_name.agg(lambda x: "; ".join(sorted(set(x)))))
    out = out[out.ciks.ne("")]
    out.to_csv(f"{R}/owners_sponsors.csv", index=False)
    rev = (
        agg.groupby(["owner_name", "owner_class"])
        .agg(sponsors=("norm", "nunique"), filings=("filings", "sum"))
        .reset_index()
        .sort_values(["sponsors", "owner_name"], ascending=[False, True])
    )
    rev.to_csv(f"{R}/owners_review.csv", index=False)
    lines = [
        f"registrant names: {len(reg)}; sponsor names: {len(sp)}; sponsors with at least one CIK: {len(out)} "
        f"(from Form D: {int(out.norm.isin(pd.read_csv(f'{R}/formd_sponsors.csv').norm).sum()) if os.path.exists(f'{R}/formd_sponsors.csv') else 0}; "
        f"registrants: {int(out.is_registrant.sum())})",
        f"registrant name matches: {len(review)} (accepted {int(review.accepted.sum())}: strict {int((review.strict_eq & review.accepted).sum())}, "
        f"hand-accepted {int((~review.strict_eq & review.accepted).sum())}; not used {int((~review.accepted).sum())})",
        f"13D/13G accessions naming a sponsor CIK: {info['accessions']}; with no other party in the index: "
        f"{info['accessions_with_one_party']}",
        f"sponsor x owner pairs: {len(agg)}; owner classes: {agg.owner_class.value_counts().to_dict()}",
        f"sponsors with any owner filing: {int((out.n_owners > 0).sum())}; VC-backed (a venture-capital filer): "
        f"{int(out.vc_backed.sum())}",
        "",
        "By tier:",
        out.groupby("tier")[["is_registrant", "vc_backed"]].agg(["mean", "sum", "size"]).round(4).to_string(),
    ]
    open(f"{R}/owners_summary.txt", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:3])
