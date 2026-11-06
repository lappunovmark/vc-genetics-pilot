"""Link industry trial sponsors to SEC Form D issuers (private placements in biotech, pharma and health care).

Usage: python formd_link.py FORMD_CSV RESULTS_DIR
Inputs: FORMD_CSV from fetch_formd.py; RESULTS_DIR/sponsors.csv.gz from build_panel26.py (one row per trial record).

Names. Every filing carries the issuer's name at filing time (ENTITYNAME) and up to six previous names (reported on the
filing and in EDGAR). Candidate names for matching are all of these; CIKs are normalised (zero-padding is
inconsistent in the source) and may legitimately appear under several names (renamed companies, reverse-merger
shells).

Matching follows sbir_link.py (precision first): exact match of normalised names, then RapidFuzz token_sort_ratio >= 92
within blocks sharing the first normalised token. A candidate name counts as the sponsor's own ("same company") if it
equals the sponsor's name after removing legal forms alone and is not rejected in formd_decisions.csv, or if it is
accepted there after hand review. Several own names are pooled.

Dating rule (formd_first_year). The sponsor's first private placement is the earliest Form D filed by its legal entity
(CIK) under any name, because most name changes in EDGAR are renames of the same company. When the sponsor's name
appears under more than one CIK, the CIK that first filed under that name is taken as the original company and keeps
its whole history; the other CIKs (typically a listed shell that adopted the name after a reverse merger) contribute
only filings made under the sponsor's own names or later names, not under their former businesses' names. Two bounds
are kept for sensitivity: formd_first_year_own counts only filings under the sponsor's own names and later names of
the same CIK (a successor name is one whose filing lists an own name as a previous name); formd_first_year_cik counts
every filing of every own CIK. EDGAR state suffixes such as "/DE/" are removed before names are compared.

Offerings. An amendment (Form D/A) restates the offering it amends, so filings are folded into offerings by following
PREVIOUSACCESSIONNUMBER to the first filing of the chain; an offering is dated by its first filing and its amount sold
is the figure on the latest filing of the chain (amendments report the cumulative amount). Offerings whose chain
starts outside the extract (filed before 2009 or under another industry group) start at the first filing seen.

Writes RESULTS_DIR/formd_match_review.csv (every candidate sponsor name with the chosen issuer record), formd_sponsors.csv
(accepted sponsors: first filing year under the three definitions, filings, largest amount sold, CIKs),
formd_sponsor_offerings.csv.gz (every offering in an accepted sponsor's history under the main rule: year, amount sold,
security type, number of investors) and formd_summary.txt.
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from sbir_link import match, strict

DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formd_decisions.csv")
PREV_COLS = [
    "ISSUER_PREVIOUSNAME_1",
    "ISSUER_PREVIOUSNAME_2",
    "ISSUER_PREVIOUSNAME_3",
    "EDGAR_PREVIOUSNAME_1",
    "EDGAR_PREVIOUSNAME_2",
    "EDGAR_PREVIOUSNAME_3",
]
IND = ["Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]


EDGAR_SUFFIX = re.compile(r"\s*/\s*(?:[A-Z]{2}|NEW|DELAWARE|CANADA|ADR)\s*/?\s*$", re.I)


def clean_name(s):
    """Issuer name without EDGAR's trailing state or status marker ("GTX INC /DE/", "KINETA, INC./DE")."""
    return EDGAR_SUFFIX.sub("", str(s)).strip()


def filings(path):
    """Form D filings with normalised CIK, filing year, amount sold and the strict form of the name at filing time."""
    f = pd.read_csv(path, dtype=str)
    for c in ["ENTITYNAME"] + PREV_COLS:
        if c in f.columns:
            f[c] = f[c].where(f[c].isna(), f[c].map(clean_name))
    # CIKs come with inconsistent zero-padding ("000744218" and "0000744218" are the same issuer).
    f["CIK"] = f.CIK.str.strip().str.lstrip("0")
    f["filing_year"] = pd.to_datetime(f.FILING_DATE, errors="coerce", format="mixed").dt.year
    f["sold"] = pd.to_numeric(f.TOTALAMOUNTSOLD, errors="coerce")
    f = f[f.CIK.notna() & f.CIK.ne("") & f.filing_year.notna() & f.ENTITYNAME.notna()].copy()
    f["fname"] = f.ENTITYNAME.map(strict)
    return f


def offerings(f):
    """One row per offering, amendments folded into the filing they amend (see the module docstring)."""
    prev = dict(zip(f.ACCESSIONNUMBER, f.PREVIOUSACCESSIONNUMBER))
    known = set(f.ACCESSIONNUMBER)

    def root(a):
        seen = set()
        while True:
            p = prev.get(a)
            if not isinstance(p, str) or p not in known or p in seen:
                return a
            seen.add(a)
            a = p

    f = f.assign(
        offering=f.ACCESSIONNUMBER.map(root), investors=pd.to_numeric(f.TOTALNUMBERALREADYINVESTED, errors="coerce")
    )
    f = f.sort_values(["offering", "FILING_DATE", "ACCESSIONNUMBER"], kind="mergesort")
    flag = lambda c: (c.astype(str).str.lower().eq("true")).any()  # noqa: E731
    o = f.groupby("offering").agg(
        CIK=("CIK", "first"),
        fname=("fname", "first"),
        issuer_name=("ENTITYNAME", "first"),
        year=("filing_year", "min"),
        sale_date=("SALE_DATE", "first"),
        sold=("sold", "last"),
        sold_max=("sold", "max"),
        equity=("ISEQUITYTYPE", flag),
        debt=("ISDEBTTYPE", flag),
        business_combination=("ISBUSINESSCOMBINATIONTRANS", flag),
        investors=("investors", "last"),
        n_filings=("ACCESSIONNUMBER", "size"),
    )
    o["sold"] = o.sold.fillna(o.sold_max)
    o["year"] = o.year.astype(int)
    # every (CIK, name at filing time) that appears in the chain, so that an offering amended under a later name is
    # still found from the earlier name's history
    k = f[["offering", "CIK", "fname"]].drop_duplicates()
    keys = {off: list(zip(g.CIK, g.fname)) for off, g in k.groupby("offering", sort=False)}
    return o.drop(columns="sold_max"), keys


def name_history(f):
    """Filing history per (CIK, name at filing time)."""
    return f.groupby(["CIK", "fname"]).agg(
        first_year=("filing_year", "min"),
        last_year=("filing_year", "max"),
        n_filings=("ACCESSIONNUMBER", "nunique"),
        max_sold=("sold", "max"),
        industry=("INDUSTRYGROUPTYPE", lambda x: x.mode().iat[0] if len(x.mode()) else None),
        state=("STATEORCOUNTRY", "first"),
        entity=("ENTITYNAME", "last"),
    )


def successors(f):
    """(CIK, earlier name) -> set of later names under which the same CIK filed, from the previous-name fields."""
    cols = [c for c in PREV_COLS if c in f.columns]
    p = f.melt(id_vars=["CIK", "fname"], value_vars=cols, value_name="prev").dropna(subset=["prev"])
    p["prev"] = p.prev.map(strict)
    p = p[p.prev.ne("") & (p.prev != p.fname)]
    out = {}
    for cik, prev, fname in p[["CIK", "prev", "fname"]].drop_duplicates().itertuples(index=False):
        out.setdefault((cik, prev), set()).add(fname)
    return out


def candidates(f):
    """One row per (normalised name, CIK, strict name) over names at filing time and previous names."""
    cols = ["ENTITYNAME"] + [c for c in PREV_COLS if c in f.columns]
    n = f.melt(id_vars=["CIK"], value_vars=cols, value_name="issuer_name").dropna(subset=["issuer_name"])
    n = n[n.issuer_name.str.strip().ne("")].drop(columns="variable")
    n["fname"] = n.issuer_name.map(strict)
    n["norm"] = n.issuer_name.map(rq2_stops.norm_sponsor)
    n = n[n.norm.notna() & n.norm.str.len().ge(3) & n.fname.ne("")]
    n = n.sort_values(["CIK", "fname", "issuer_name"]).drop_duplicates(["norm", "CIK", "fname"])
    return n


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


def decisions(path=DECISIONS):
    if not os.path.exists(path):
        return {}
    d = pd.read_csv(path)
    return {(strict(a), strict(b)): v for a, b, v in zip(d.lead_sponsor, d.issuer_name, d.decision)}


def own_and_successor_names(own, succ):
    """Closure of (CIK, name) pairs reachable from the sponsor's own names through successor links."""
    seen, stack = set(), list(own)
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        stack.extend((key[0], nxt) for nxt in succ.get(key, ()))
    return seen


def resolve(m, hist, succ, dec):
    """One record per sponsor name: pooled history of its own and successor names, or the top candidate for review.

    Also returns, per accepted sponsor, the (CIK, name) pairs of its history under the main dating rule."""
    m = m.copy()
    m["strict_eq"] = [strict(a) == strict(b) for a, b in zip(m.lead_sponsor, m.issuer_name)]
    m["decision"] = [dec.get((strict(a), b)) for a, b in zip(m.lead_sponsor, m.fname)]
    m["same_company"] = (m.strict_eq & m.decision.ne("reject")) | m.decision.eq("accept")
    m = m.merge(hist, left_on=["CIK", "fname"], right_index=True, how="left")
    m["n_filings"] = m.n_filings.fillna(0).astype(int)
    m = m.sort_values(
        ["norm", "same_company", "strict_eq", "decision", "n_filings", "first_year", "CIK"],
        ascending=[True, False, False, True, False, True, True],
        kind="mergesort",
        na_position="last",
    )
    rows, history = [], {}
    for norm, g in m.groupby("norm", sort=False):
        top = g.iloc[0]
        own = g[g.same_company]
        keys = own_and_successor_names(set(zip(own.CIK, own.fname)), succ)
        h_own = hist[hist.index.isin(list(keys))] if keys else hist.iloc[0:0]
        ciks = sorted(set(own.CIK), key=int)
        h_cik = hist[hist.index.get_level_values("CIK").isin(ciks)] if ciks else hist.iloc[0:0]
        # main definition: the CIK that first filed under the sponsor's own name is the original company and keeps
        # its whole history (renames); any other CIK sharing the name (usually a listed shell adopted by reverse
        # merger) contributes own and successor names only
        if len(ciks) > 1:
            own_start = hist.loc[hist.index.isin(list(zip(own.CIK, own.fname)))].groupby(level="CIK").first_year.min()
            original = own_start.sort_index(key=lambda i: i.astype(int)).idxmin()
            h = hist[(hist.index.get_level_values("CIK") == original) | hist.index.isin(list(keys))]
        else:
            h = h_cik
        if len(own) and len(h):
            history[norm] = set(h.index)
        rows.append(
            {
                "match": top.match,
                "score": top.score,
                "lead_sponsor": top.lead_sponsor,
                "norm": norm,
                "tier": top.tier,
                "n_trials": top.n_trials,
                "issuer_name": top.issuer_name,
                "issuer_norm": top.issuer_norm,
                "CIK": ";".join(ciks) if len(own) else top.CIK,
                "strict_eq": bool(top.strict_eq),
                "decision": top.decision,
                "accepted": bool(len(own)) and len(h) > 0,
                "n_candidate_names": len(g),
                "n_own_ciks": len(ciks),
                "n_own_names": int(len(own)),
                "n_history_names": int(len(h)),
                "formd_first_year": h.first_year.min() if len(h) else pd.NA,
                "formd_last_year": h.last_year.max() if len(h) else pd.NA,
                "formd_filings": int(h.n_filings.sum()) if len(h) else 0,
                "formd_max_sold": h.max_sold.max() if len(h) else pd.NA,
                "formd_first_year_own": h_own.first_year.min() if len(h_own) else pd.NA,
                "formd_first_year_cik": h_cik.first_year.min() if len(h_cik) else pd.NA,
                "formd_industry": top.industry,
                "formd_state": top.state,
                "candidate_first_year": top.first_year,
                "candidate_filings": int(top.n_filings),
            }
        )
    return pd.DataFrame(rows), history


def sponsor_offerings(o, keys, history):
    """Offerings in each accepted sponsor's history: an offering belongs to a sponsor when any filing of its chain was
    made under a (CIK, name) pair of that sponsor's history under the main dating rule."""
    owner = {}
    for norm, hk in history.items():
        for key in hk:
            owner.setdefault(key, set()).add(norm)
    rows = []
    for off, ks in keys.items():
        norms = set().union(*(owner.get(k, set()) for k in ks))
        rows.extend({"norm": n, "offering": off} for n in sorted(norms))
    so = pd.DataFrame(rows).merge(o, left_on="offering", right_index=True)
    return so.sort_values(["norm", "year", "offering"], kind="mergesort").reset_index(drop=True)


def main(formd_csv, R):
    f = filings(formd_csv)
    hist = name_history(f)
    succ = successors(f)
    cand = candidates(f)
    sp = sponsors(R)
    m = match(sp, cand).rename(columns={"sbir_norm": "issuer_norm"})
    m, history = resolve(m, hist, succ, decisions())
    m.sort_values(["accepted", "match", "score", "norm"]).to_csv(f"{R}/formd_match_review.csv", index=False)
    acc = m[m.accepted]
    o, keys = offerings(f)
    so = sponsor_offerings(o, keys, history)
    so.to_csv(f"{R}/formd_sponsor_offerings.csv.gz", index=False)
    # the earliest offering of every sponsor must be the first filing year of the main dating rule
    first_off = so.groupby("norm").year.min()
    mismatch = acc[acc.norm.map(first_off).ne(pd.to_numeric(acc.formd_first_year))]
    assert len(mismatch) == 0, mismatch[["norm", "formd_first_year"]].head()
    acc[
        [
            "norm",
            "lead_sponsor",
            "issuer_name",
            "CIK",
            "tier",
            "formd_first_year",
            "formd_first_year_own",
            "formd_first_year_cik",
            "formd_filings",
            "formd_max_sold",
        ]
    ].to_csv(f"{R}/formd_sponsors.csv", index=False)
    out = [
        f"Form D filings kept (biotech, pharma, other health care; no pooled funds): {len(f)}; issuer CIKs: "
        f"{f.CIK.nunique()}; distinct names at filing time: {hist.index.get_level_values('fname').nunique()}; "
        f"candidate names incl. previous names: {len(cand)}",
        f"non-top-20 industry sponsor names in the panel: {len(sp)}",
        f"candidate matches: {len(m)} (exact {int(m.match.eq('exact').sum())}, fuzzy {int(m.match.eq('fuzzy').sum())}); "
        f"accepted {len(acc)} (strict name agreement {int((m.strict_eq & m.accepted).sum())}, accepted after hand "
        f"review {int((~m.strict_eq & m.accepted).sum())}, not used {int((~m.accepted).sum())})",
        f"accepted sponsors with several own names pooled: {int((acc.n_own_names > 1).sum())}; with several own CIKs: "
        f"{int((acc.n_own_ciks > 1).sum())}; first year under the main rule differs from the own-names-only bound for "
        f"{int((acc.formd_first_year != acc.formd_first_year_own).sum())} sponsors and from the whole-CIK bound for "
        f"{int((acc.formd_first_year != acc.formd_first_year_cik).sum())}",
        f"offerings: {len(o)} from {len(f)} filings ({int((o.n_filings > 1).sum())} amended at least once; "
        f"{int(f.ISAMENDMENT.astype(str).str.lower().eq('true').sum())} amendments, of which "
        f"{int((f.ISAMENDMENT.astype(str).str.lower().eq('true') & ~f.PREVIOUSACCESSIONNUMBER.isin(set(f.ACCESSIONNUMBER))).sum())} "
        f"amend a filing outside the extract); offerings of accepted sponsors: {len(so)} "
        f"({int(so.equity.sum())} with equity, {int(so.debt.sum())} with debt; amount sold known for "
        f"{int(so.sold.notna().sum())}, median ${so.sold.median():,.0f})",
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
