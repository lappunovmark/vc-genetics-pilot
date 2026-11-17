"""Did trials of venture-backed sponsors stop for financial reasons more often after 2022? Exploratory.

Usage: python pilot/vc_stops.py CTGOV_ALL_CSV RESULTS_DIR CRUNCHBASE_DIR IPO-age.xlsx FORMD_DIR
(after rq2_stops.py, owners_link.py, cb_models.py, ritter_models.py and formd_directors.py)

Why: the second question of the pilot is whether the 2022 funding downturn hit capital-dependent sponsors harder.
rq2_stops.py and formd_stops.py use the number of trials and the capital raised as stand-ins for that dependence;
here the sponsor is marked as venture-backed directly.

Sample: industry Phase 1-3 drug trials of non-top-20 sponsors at risk in 2016-2025 (as formd_stops.py).
Venture flag of the sponsor (a property of the sponsor, not dated to the trial), from any of:
  a venture-capital owner in Schedules 13D/13G (owners_sponsors.csv; sponsors of the programme panel only),
  a venture-backed US IPO in Jay Ritter's list, a round of type "venture" in the Crunchbase export of December 2015,
  a venture investor on the board in a Form D filing.
The programme panel covers about three fifths of these trials, so for the last three sources every trial sponsor is
matched again by name: a match needs the same name once legal forms are removed (sbir_link.strict); pairs rejected
by hand for the panel stay rejected and the panel's accepted links are added.
Groups: venture-backed; seen in a source without a venture marker; not seen in any source.
Rates are stops per 1,000 active trial-years, 2016-21 against 2022-25, with Poisson rate ratios; logits on
trial-years with standard errors clustered by sponsor. Writes vc_stops.txt, vc_stops_rates.csv and
vc_stops_link_review.csv (every name link made here; hand rejections are in vc_stops_decisions.csv).
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import formd_directors_lib as fdl
import rq2_stops
import sbir_link
from formd_stops import rr
from pooling import pool_sparse

PRE, POST = (2016, 2021), (2022, 2025)
GROUPS = ["seen, no venture marker", "venture-backed", "not seen"]
HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = []  # every name link made here, for checking by eye


def rejected(path, cols, source):
    """Pairs rejected by hand: for the programme panel (path) and for the other trial sponsors (vc_stops_decisions)."""
    bad = set()
    if os.path.exists(path):
        d = pd.read_csv(path, dtype=str)
        bad |= set(map(tuple, d[d.decision.eq("reject")][cols].to_numpy()))
    d = pd.read_csv(os.path.join(HERE, "vc_stops_decisions.csv"), dtype=str)
    d = d[d.decision.eq("reject") & d.source.eq(source)]
    return bad, set(zip(d.lead_sponsor, d.name))


def crunchbase(names, cb_dir, R):
    """norm -> True if a venture round is known; keys = sponsors found in Crunchbase."""
    c = pd.read_csv(f"{cb_dir}/companies.csv", dtype=str, encoding_errors="replace")
    c = c[c.name.notna()].assign(strict=lambda d: d.name.map(sbir_link.strict))
    m = names.merge(c[["name", "strict", "permalink", "category_list"]], on="strict")
    bad, bad2 = rejected(os.path.join(HERE, "cb_decisions.csv"), ["first_sponsor", "name"], "round")
    m = m.assign(reject=[(a, b) in bad or (a, b) in bad2 for a, b in zip(m.lead_sponsor, m.name)])
    REVIEW.append(
        m.assign(source="round", detail=m.category_list)[["source", "lead_sponsor", "name", "detail", "reject"]]
    )
    m = m[~m.reject]
    r = pd.read_csv(f"{cb_dir}/rounds.csv", dtype=str, encoding_errors="replace")
    ven = set(r[r.funding_round_type.eq("venture")].company_permalink)
    found = m.assign(vc=m.permalink.isin(ven)).groupby("norm").vc.any().to_dict()
    if os.path.exists(f"{R}/cb_sponsors.csv"):  # the hand-reviewed links of the programme panel
        p = pd.read_csv(f"{R}/cb_sponsors.csv")
        for n, v in zip(p.first_sponsor.map(rq2_stops.norm_sponsor), p.first_vc_round_year.notna()):
            found[n] = bool(found.get(n, False) or v)
    return found


def ritter(names, xlsx, R):
    d = pd.read_excel(xlsx, dtype=str).iloc[:, :12]
    d.columns = [
        "date",
        "name",
        "ticker",
        "cusip",
        "adr",
        "vc",
        "dual",
        "shares",
        "internet",
        "perm",
        "founding",
        "rollup",
    ]
    d = d[d.name.notna() & d.date.str.fullmatch(r"\d{8}")].copy()
    d["vc"] = pd.to_numeric(d.vc, errors="coerce")
    d = d[d.vc.isin([0, 1, 2])].assign(
        strict=lambda x: x.name.map(sbir_link.strict), ipo_year=lambda x: x.date.str[:4].astype(int)
    )
    m = names.merge(d[["name", "date", "strict", "vc", "ipo_year"]], on="strict")
    bad, bad2 = rejected(os.path.join(HERE, "ritter_decisions.csv"), ["first_sponsor", "name", "date"], "ipo")
    m = m.assign(reject=[(a, b, c) in bad or (a, b) in bad2 for a, b, c in zip(m.lead_sponsor, m.name, m.date)])
    REVIEW.append(m.assign(source="ipo", detail=m.date)[["source", "lead_sponsor", "name", "detail", "reject"]])
    m = m[~m.reject]
    m["gap"] = (m.ipo_year - m["first"]).abs()
    m = m.sort_values(["norm", "gap", "date"]).drop_duplicates("norm")
    found = dict(zip(m.norm, m.vc.isin([1, 2])))
    if os.path.exists(f"{R}/ritter_sponsors.csv"):
        p = pd.read_csv(f"{R}/ritter_sponsors.csv")
        for n, v in zip(p.first_sponsor.map(rq2_stops.norm_sponsor), p.ritter_vc.astype(bool)):
            found[n] = bool(v)
    return found


def boards(names, fd_dir, R):
    f = fdl.filings(fd_dir)  # one row per biopharma filing: CIK, issuer name, vc_board
    iss = f.drop_duplicates(["CIK", "ENTITYNAME"]).assign(strict=lambda d: d.ENTITYNAME.map(sbir_link.strict))
    m = names.merge(iss[["CIK", "ENTITYNAME", "strict"]], on="strict")
    REVIEW.append(
        m.assign(source="board", name=m.ENTITYNAME, detail=m.CIK, reject=False)[
            ["source", "lead_sponsor", "name", "detail", "reject"]
        ]
    )
    m = m[["norm", "CIK"]]
    if os.path.exists(f"{R}/formd_sponsor_offerings.csv.gz"):
        so = pd.read_csv(f"{R}/formd_sponsor_offerings.csv.gz", dtype=str)
        m = pd.concat([m, so.assign(CIK=so.CIK.str.lstrip("0"))[["norm", "CIK"]]]).drop_duplicates()
    by_cik = f.groupby("CIK").vc_board.any()
    m = m[m.CIK.isin(by_cik.index)]
    return m.assign(vc=m.CIK.map(by_cik)).groupby("norm").vc.any().to_dict()


def main(ctgov, R, cb_dir, xlsx, fd_dir):
    today = pd.Timestamp(os.environ.get("PILOT_ASOF", "2026-10-17"))
    ct = rq2_stops.load(ctgov)
    ct = ct[ct.group.ne(rq2_stops.GROUPS[0])].copy()
    names = ct.groupby("lead_sponsor").start_year.min().rename("first").reset_index()
    names["norm"] = names.lead_sponsor.map(rq2_stops.norm_sponsor)
    names["strict"] = names.lead_sponsor.map(sbir_link.strict)
    names = names[names.norm.notna()]
    src = {"round": crunchbase(names, cb_dir, R), "ipo": ritter(names, xlsx, R), "board": boards(names, fd_dir, R)}
    if os.path.exists(f"{R}/owners_sponsors.csv"):
        ow = pd.read_csv(f"{R}/owners_sponsors.csv", dtype={"norm": str})
        src["owners"] = dict(
            zip(ow[ow.is_registrant.astype(bool)].norm, ow[ow.is_registrant.astype(bool)].vc_backed.astype(bool))
        )
    pd.concat(REVIEW).sort_values(["source", "lead_sponsor", "name"]).to_csv(
        f"{R}/vc_stops_link_review.csv", index=False
    )
    sp = pd.DataFrame({"norm": sorted(set(names.norm))})
    for k, tab in src.items():
        sp[f"seen_{k}"] = sp.norm.isin(tab)
        sp[f"vc_{k}"] = sp.norm.map(tab).fillna(False).astype(bool)
    sp["seen"] = sp[[f"seen_{k}" for k in src]].any(axis=1)
    sp["vc"] = sp[[f"vc_{k}" for k in src]].any(axis=1)
    sp["vcg"] = np.select([sp.vc, sp.seen], [GROUPS[1], GROUPS[0]], GROUPS[2])
    ct["vcg"] = pd.Categorical(ct.sponsor_norm.map(dict(zip(sp.norm, sp.vcg))).fillna(GROUPS[2]), categories=GROUPS)
    out = ["Trial stops of venture-backed sponsors around 2022 (exploratory; see the module docstring)"]
    out.append(
        f"non-top-20 industry sponsors: {len(sp)}; seen in at least one source: {int(sp.seen.sum())}; venture-backed: "
        f"{int(sp.vc.sum())} ("
        + "; ".join(f"{k} {int(sp[f'seen_{k}'].sum())} / {int(sp[f'vc_{k}'].sum())}" for k in src)
        + ")"
    )
    out.append(
        ct[ct.start_year.between(2010, today.year)]
        .groupby(["vcg", "group"], observed=True)
        .agg(trials=("nct_id", "size"), sponsors=("sponsor_norm", "nunique"))
        .to_string()
    )
    ended = ct.stop_date.fillna(ct.completion_date).fillna(ct.primary_completion_date)
    rows = []
    for t in range(PRE[0], POST[1] + 1):
        a, b = pd.Timestamp(t, 1, 1), pd.Timestamp(t, 12, 31)
        d = ct[(ct.start_date <= b) & (ended.isna() | (ended >= a))]
        rows.append(
            d.assign(
                year=t,
                fin_t=(d.stopped & d.fin & (d.stop_year == t)).astype(int),
                nofund_t=(d.stopped & d.nofund & (d.stop_year == t)).astype(int),
                any_t=(d.stopped & (d.stop_year == t)).astype(int),
            )[["nct_id", "sponsor_norm", "group", "vcg", "phases", "start_year", "year", "fin_t", "nofund_t", "any_t"]]
        )
    ty = pd.concat(rows, ignore_index=True)
    ty["post"] = (ty.year >= POST[0]).astype(int)
    rates = []
    for g, d in ty.groupby("vcg", observed=False):
        pre, post = d[d.post.eq(0)], d[d.post.eq(1)]
        row = {"group": g, "pre_trial_years": len(pre), "post_trial_years": len(post)}
        for y in ("fin_t", "nofund_t", "any_t"):
            a, bb = int(pre[y].sum()), int(post[y].sum())
            r, lo, hi = rr(a, len(pre), bb, len(post))
            row.update({f"{y}_pre": a, f"{y}_post": bb, f"{y}_rate_pre": 1000 * a / len(pre), f"{y}_rate_post": 1000 * bb / len(post), f"{y}_rr": r, f"{y}_rr_lo": lo, f"{y}_rr_hi": hi})  # fmt: skip
        rates.append(row)
    rates = pd.DataFrame(rates)
    rates.to_csv(f"{R}/vc_stops_rates.csv", index=False)
    out.append(f"\nStops per 1,000 active trial-years, {PRE[0]}-{PRE[1]} vs {POST[0]}-{POST[1]}:")
    out.append(rates.round(3).to_string(index=False))
    ty["phase"] = ty.phases.fillna("").str.extract(r"(PHASE[123])", expand=False).fillna("other")
    ty["yb"] = pd.cut(ty.start_year, [0, 2009, 2014, 2019, 2100]).astype(str)

    def fit(d, f, title):
        try:
            d = pool_sparse(d, f)
            r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.sponsor_norm.fillna("?"))[0]})  # fmt: skip
            t = r.summary2().tables[1]
            t = t.loc[
                [i for i in t.index if i.startswith("C(vcg)") or i == "post"],
                ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"],
            ]
            t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
            head = (
                f"N={int(r.nobs)} trial-years; clusters (sponsors)={d.sponsor_norm.nunique()}; events={int(d.y.sum())}"
            )
            out.extend(
                [
                    "=" * 100,
                    title,
                    f,
                    head + ("" if r.mle_retvals["converged"] else "; NOT CONVERGED"),
                    t.round(4).to_string(),
                ]
            )
        except Exception as e:
            out.extend(["=" * 100, title, f, f"failed: {e!r}"])

    for y, lab in (
        ("fin_t", "financial or strategic stop"),
        ("nofund_t", "stop citing lack of funding"),
        ("any_t", "any stop"),
    ):
        ty["y"] = ty[y]
        fit(ty, "y ~ C(vcg) * post + C(group) + C(phase) + C(yb)", f"{lab} per trial-year ~ venture group x post-2022 (reference: seen, no venture marker; pre-2022)")  # fmt: skip
        fit(ty[ty.vcg.ne(GROUPS[2])].assign(vcg=lambda d: d.vcg.cat.remove_unused_categories()), "y ~ C(vcg) * post + C(group) + C(phase) + C(yb)", f"{lab}, sponsors seen in a source only")  # fmt: skip
        sm = ty[ty.group.eq(rq2_stops.GROUPS[3])]
        fit(sm, "y ~ C(vcg) * post + C(phase) + C(yb)", f"{lab}, small sponsors (up to 20 trials) only")
    open(f"{R}/vc_stops.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:6])
