"""Did trials of sponsors with less private money behind them stop for financial reasons more often after 2022?

Usage: python formd_stops.py CTGOV_ALL_CSV RESULTS_DIR   (after rq2_stops.py and formd_link.py)
Sample: industry Phase 1-3 drug trials of non-top-20 sponsors (groups as in rq2_stops.py), at risk in 2016-2025.
Capital behind the sponsor = amount sold in its Form D offerings dated before the trial's start year
(results/formd_sponsor_offerings.csv.gz, main dating rule), banded as in formd_models.py: no prior Form D,
under $10M, $10-50M, $50M or more.
Rates are financial or strategic stops (and stops citing lack of funding) per 1,000 active trial-years, 2016-21 vs
2022-25, by band, with Poisson rate ratios; logits on trial-years with standard errors clustered by sponsor.
Writes RESULTS_DIR/formd_stops.txt and formd_stops_rates.csv.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops

BANDS = ["none", "<$10M", "$10-50M", ">=$50M"]
PRE, POST = (2016, 2021), (2022, 2025)


def raised_before(names, years, hist):
    out = []
    for s, y in zip(names, years):
        h = hist.get(rq2_stops.norm_sponsor(s))
        out.append(float(h[1][h[0] < y].sum()) / 1e6 if h is not None and pd.notna(y) else np.nan)
    return np.array(out)


def band(names, years, hist):
    r = raised_before(names, years, hist)
    has = np.array(
        [
            (rq2_stops.norm_sponsor(s) in hist) and pd.notna(y) and bool((hist[rq2_stops.norm_sponsor(s)][0] < y).any())
            for s, y in zip(names, years)
        ]
    )
    return pd.Categorical(np.select([~has, r < 10, r < 50], BANDS[:3], default=BANDS[3]), categories=BANDS), r


def rr(a, ta, b, tb):
    """Rate ratio post/pre with a Poisson 95% CI; (nan, nan, nan) when either count is zero."""
    if a == 0 or b == 0:
        return np.nan, np.nan, np.nan
    r = (b / tb) / (a / ta)
    se = np.sqrt(1 / a + 1 / b)
    return r, r * np.exp(-1.96 * se), r * np.exp(1.96 * se)


def main(ctgov, R):
    today = pd.Timestamp(os.environ.get("PILOT_ASOF", "2026-10-17"))
    ct = rq2_stops.load(ctgov)
    ct = ct[ct.group.ne(rq2_stops.GROUPS[0])].copy()  # non-top-20 industry
    O = pd.read_csv(f"{R}/formd_sponsor_offerings.csv.gz")
    hist = {n: (g.year.to_numpy(), g.sold.fillna(0).to_numpy()) for n, g in O.groupby("norm")}
    ct["band"], ct["raised"] = band(ct.lead_sponsor, ct.start_year, hist)
    out = [
        "Non-top-20 industry Phase 1-3 drug trials by amount the sponsor had raised in Form D offerings before the start year:"
    ]
    out.append(
        ct[ct.start_year.between(2010, today.year)]
        .groupby("band", observed=False)
        .agg(trials=("nct_id", "size"), sponsors=("sponsor_norm", "nunique"), raised_median=("raised", "median"))
        .round(2)
        .to_string()
    )
    # trial-year panel
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
            )[
                [
                    "nct_id",
                    "sponsor_norm",
                    "group",
                    "band",
                    "raised",
                    "phases",
                    "start_year",
                    "year",
                    "fin_t",
                    "nofund_t",
                    "any_t",
                ]
            ]
        )
    ty = pd.concat(rows, ignore_index=True)
    ty["post"] = (ty.year >= POST[0]).astype(int)
    rates = []
    for bnd, d in ty.groupby("band", observed=False):
        pre, post = d[d.post.eq(0)], d[d.post.eq(1)]
        row = {"band": bnd, "pre_trial_years": len(pre), "post_trial_years": len(post)}
        for y in ("fin_t", "nofund_t", "any_t"):
            a, bb = int(pre[y].sum()), int(post[y].sum())
            r, lo, hi = rr(a, len(pre), bb, len(post))
            row.update(
                {
                    f"{y}_pre": a,
                    f"{y}_post": bb,
                    f"{y}_rate_pre": 1000 * a / len(pre) if len(pre) else np.nan,
                    f"{y}_rate_post": 1000 * bb / len(post) if len(post) else np.nan,
                    f"{y}_rr": r,
                    f"{y}_rr_lo": lo,
                    f"{y}_rr_hi": hi,
                }
            )
        rates.append(row)
    rates = pd.DataFrame(rates)
    rates.to_csv(f"{R}/formd_stops_rates.csv", index=False)
    out.append(f"\nStops per 1,000 active trial-years, {PRE[0]}-{PRE[1]} vs {POST[0]}-{POST[1]}, by band:")
    show = rates[
        ["band", "pre_trial_years", "post_trial_years"]
        + [c for c in rates.columns if c.startswith(("fin_t", "nofund_t"))]
    ]
    out.append(show.round(3).to_string(index=False))
    ty["phase"] = ty.phases.fillna("").str.extract(r"(PHASE[123])", expand=False).fillna("other")
    ty["yb"] = pd.cut(ty.start_year, [0, 2009, 2014, 2019, 2100]).astype(str)
    for y, lab in (("fin_t", "financial or strategic stop"), ("nofund_t", "stop citing lack of funding")):
        ty["y"] = ty[y]
        for f, title in (
            (
                "y ~ C(band) * post + C(group) + C(phase) + C(yb)",
                f"{lab} per trial-year ~ band x post-2022 (reference: no prior Form D, pre-2022)",
            ),
            ("y ~ C(band) + post + C(group) + C(phase) + C(yb)", f"{lab} per trial-year ~ band + post-2022"),
        ):
            try:
                r = smf.logit(f, ty).fit(
                    disp=0,
                    maxiter=300,
                    cov_type="cluster",
                    cov_kwds={"groups": pd.factorize(ty.sponsor_norm.fillna("?"))[0]},
                )
                t = r.summary2().tables[1]
                t = t.loc[
                    [i for i in t.index if i.startswith("C(band)") or i == "post"],
                    ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"],
                ]
                t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
                out.extend(
                    [
                        "=" * 100,
                        title,
                        f,
                        f"N={int(r.nobs)} trial-years; clusters (sponsors)={ty.sponsor_norm.nunique()}; events={int(ty.y.sum())}",
                        t.round(4).to_string(),
                    ]
                )
            except Exception as e:
                out.extend(["=" * 100, title, f, f"failed: {e!r}"])
    open(f"{R}/formd_stops.txt", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:3])
