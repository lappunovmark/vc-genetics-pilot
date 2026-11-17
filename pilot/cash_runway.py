"""Cash runway before a downturn and trial stops (plan written before the data were downloaded:
docs/plan_cash_runway.md).

Usage: python pilot/cash_runway.py CTGOV_ALL_CSV RESULTS_DIR SEC_FRAMES_CSV_GZ [H4_TRIALS_CSV_GZ]
(after rq2_stops.py and owners_link.py; SEC_FRAMES_CSV_GZ is the file of fetch_sec_frames.py)

Runway = liquid assets at the end of a year / cash used in operations during that year, in years. Liquid assets:
the reported total of cash, cash equivalents and short-term investments if the filer reports it, otherwise cash and
cash equivalents plus the first available of short-term investments, current marketable securities and current
available-for-sale debt securities. Short runway: less than 1.5 years. Sponsors with positive operating cash flow
have no runway and are a group of their own.
Cohort 2022: industry Phase 1-3 drug trials of non-top-20 sponsors with a runway at the end of 2021, active on
1 January 2022; outcome = stopped for a financial or strategic reason in 2022-2023. Cohort 2018 (ordinary years):
runway at the end of 2017, trials active on 1 January 2018, stops in 2018-2019.
Logits with phase, start period and the sponsor's size band; errors clustered by sponsor.
Writes cash_runway.txt and cash_runway_sponsors.csv.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from pooling import pool_sparse

SHORT = 1.5
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
TOTAL = "CashCashEquivalentsAndShortTermInvestments"
INVEST = ["ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]
OCF = "NetCashProvidedByUsedInOperatingActivities"
out = []


def first(w, cols):
    v = pd.Series(np.nan, index=w.index)
    for c in cols:
        if c in w:
            v = v.fillna(w[c])
    return v


def runway(fr, year):
    """One row per CIK: liquid assets at the end of `year`, operating cash flow of `year`, runway in years."""
    d = fr[fr.period.isin([f"CY{year}Q4I", f"CY{year}"])]
    w = d.pivot_table(index="cik", columns="concept", values="val", aggfunc="max")
    liquid = w[TOTAL] if TOTAL in w else pd.Series(np.nan, index=w.index)
    liquid = liquid.fillna(first(w, CASH) + first(w, INVEST).fillna(0))
    r = pd.DataFrame({"liquid": liquid, "ocf": w[OCF] if OCF in w else np.nan})
    r = r[r.liquid.notna() & r.ocf.notna()]
    r["runway"] = np.where(r.ocf < 0, r.liquid / -r.ocf, np.nan)
    return r


def cohort(ct, rw, year, ciks):
    """Trials active on 1 January `year` of sponsors with cash figures for `year - 1`."""
    a = pd.Timestamp(year, 1, 1)
    ended = ct.stop_date.fillna(ct.completion_date).fillna(ct.primary_completion_date)
    d = ct[(ct.start_date < a) & (ended.isna() | (ended >= a))].copy()
    best = {}
    for norm, cs in ciks.items():  # a sponsor with several registrants: the one with the most liquid assets
        hit = rw.loc[rw.index.intersection(cs)]
        if len(hit):
            best[norm] = hit.sort_values("liquid", ascending=False).iloc[0]
    b = pd.DataFrame(best).T
    d = d[d.sponsor_norm.isin(b.index)].copy()
    for c in ("liquid", "ocf", "runway"):
        d[c] = d.sponsor_norm.map(b[c]).astype(float)
    win = d.stop_year.between(year, year + 1)
    d["fin_y"] = (d.stopped & d.fin & win).astype(int)
    d["any_y"] = (d.stopped & win).astype(int)
    d["nofund_y"] = (d.stopped & d.nofund & win).astype(int)
    d["positive"] = (d.ocf >= 0).astype(int)
    d["short"] = (d.runway < SHORT).astype(int)
    d["cash"] = np.select([d.positive.eq(1), d.short.eq(1)], ["positive cash flow", "short runway"], "longer runway")
    d["cohort"] = year
    d["phase"] = d.phases.fillna("").str.extract(r"(PHASE[123])", expand=False).fillna("other")
    # start period relative to the cohort year, with the same labels in both cohorts (labels by calendar year would
    # identify the cohort and make the downturn term of the pooled model collinear with the period controls)
    d["yb"] = pd.cut(year - d.start_year, [0, 2, 5, 200], labels=["1-2 years", "3-5 years", "6+ years"]).astype(str)
    return d


def fit(f, d, title, keep):
    y = f.split("~")[0].strip()
    if d[y].sum() < 5:
        out.extend(["=" * 100, title, f, f"not estimated: {int(d[y].sum())} events"])
        return
    try:
        d = pool_sparse(d, f)
        r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.sponsor_norm)[0]})  # fmt: skip
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if keep(i)], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
        note = f"N={int(r.nobs)} trials; sponsors={d.sponsor_norm.nunique()}; events={int(d[y].sum())}; converged={r.mle_retvals['converged']}"
        out.extend(["=" * 100, title, f, note, t.round(4).to_string()])
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def describe(d, label):
    t = d.groupby("cash").agg(
        sponsors=("sponsor_norm", "nunique"),
        trials=("nct_id", "size"),
        financial_stops=("fin_y", "sum"),
        any_stop=("any_y", "sum"),
        lack_of_funding=("nofund_y", "sum"),
        median_runway=("runway", "median"),
    )
    t["financial_per_100"] = (100 * t.financial_stops / t.trials).round(2)
    t["any_per_100"] = (100 * t.any_stop / t.trials).round(2)
    out.extend(["", label, t.round(2).to_string()])


def main(ctgov, R, frames, h4=None):
    ct = rq2_stops.load(ctgov)
    ct = ct[ct.group.ne(rq2_stops.GROUPS[0])].copy()
    ow = pd.read_csv(f"{R}/owners_sponsors.csv", dtype=str)
    ciks = {n: [int(x) for x in str(c).replace(",", ";").split(";") if x.strip().isdigit()] for n, c in zip(ow.norm, ow.ciks) if pd.notna(c)}  # fmt: skip
    fr = pd.read_csv(frames)
    c22, c18 = cohort(ct, runway(fr, 2021), 2022, ciks), cohort(ct, runway(fr, 2017), 2018, ciks)
    out.append("Cash runway and trial stops (plan: docs/plan_cash_runway.md)")
    out.append(
        f"non-top-20 industry sponsors with an EDGAR registrant: {len(ciks)}; with cash figures for 2021 and a trial "
        f"active on 1 January 2022: {c22.sponsor_norm.nunique()} ({len(c22)} trials); for 2017 and 1 January 2018: "
        f"{c18.sponsor_norm.nunique()} ({len(c18)} trials)"
    )
    describe(c22, "Cohort 2022 (runway at the end of 2021; stops in 2022-2023):")
    describe(c18, "Cohort 2018 (runway at the end of 2017; stops in 2018-2019):")
    ctrl = "C(phase) + C(yb) + C(group)"
    neg22, neg18 = c22[c22.positive.eq(0)].copy(), c18[c18.positive.eq(0)].copy()
    is_short = lambda i: i == "short"  # noqa: E731
    fit(f"fin_y ~ short + {ctrl}", neg22, "1 (primary). Cohort 2022, sponsors with a runway: financial or strategic stop ~ short runway", is_short)  # fmt: skip
    fit(f"fin_y ~ short + {ctrl}", neg18, "2. Cohort 2018, the same model in ordinary years", is_short)
    both = pd.concat([neg22, neg18], ignore_index=True)
    both["downturn"] = both.cohort.eq(2022).astype(int)
    fit(f"fin_y ~ short * downturn + {ctrl}", both, "3 (second estimate). Both cohorts: short runway x downturn", lambda i: i in ("short", "downturn", "short:downturn"))  # fmt: skip
    fit(f"any_y ~ short + {ctrl}", neg22, "4. Cohort 2022: any stop ~ short runway", is_short)
    fit(f"any_y ~ short * downturn + {ctrl}", both, "5. Both cohorts: any stop ~ short runway x downturn", lambda i: i in ("short", "downturn", "short:downturn"))  # fmt: skip
    fit(f"nofund_y ~ short + {ctrl}", neg22, "6. Cohort 2022: stop citing lack of funding ~ short runway", is_short)
    neg22["lrun"] = np.log(neg22.runway.clip(lower=0.05))
    fit(f"fin_y ~ lrun + {ctrl}", neg22, "7. Cohort 2022: financial or strategic stop ~ log runway (years)", lambda i: i == "lrun")  # fmt: skip
    q = neg22.drop_duplicates("sponsor_norm").runway.quantile([1 / 3, 2 / 3]).tolist()
    neg22["third"] = pd.Categorical(np.select([neg22.runway <= q[0], neg22.runway <= q[1]], ["shortest", "middle"], "longest"), categories=["longest", "middle", "shortest"])  # fmt: skip
    out.append(
        f"\nthirds of sponsors by runway at the end of 2021: up to {q[0]:.2f} years, up to {q[1]:.2f} years, longer"
    )
    fit(f"fin_y ~ C(third) + {ctrl}", neg22, "8. Cohort 2022: financial or strategic stop ~ thirds of runway (reference: longest)", lambda i: i.startswith("C(third)"))  # fmt: skip
    c22["cash"] = pd.Categorical(c22.cash, categories=["longer runway", "short runway", "positive cash flow"])
    fit(f"fin_y ~ C(cash) + {ctrl}", c22, "9. Cohort 2022, all sponsors with cash figures: three groups (reference: longer runway)", lambda i: i.startswith("C(cash)"))  # fmt: skip
    small = neg22[neg22.group.eq(rq2_stops.GROUPS[3])]
    fit("fin_y ~ short + C(phase) + C(yb)", small, "10. Cohort 2022, small sponsors (up to 20 trials) only", is_short)
    if h4 and os.path.exists(h4):
        h = pd.read_csv(h4, usecols=["nct_id", "gs_ante", "gs_ot_ante"]).groupby("nct_id").max().reset_index()
        b = neg22[neg22.short.eq(1)].merge(h, on="nct_id")
        b["state"] = np.where(b.fin_y.eq(1), "stopped for financial reasons", "not stopped for financial reasons")
        t = b.groupby("state").agg(
            trials=("nct_id", "size"), gs_ante=("gs_ante", "mean"), gs_ot_ante=("gs_ot_ante", "mean")
        )
        out.extend(["", "11. Trials of short-runway sponsors with a genetic-support label (h4_biology.py), cohort 2022:", t.round(4).to_string()])  # fmt: skip
    s = c22.drop_duplicates("sponsor_norm")[["sponsor_norm", "liquid", "ocf", "runway", "cash"]]
    s.to_csv(f"{R}/cash_runway_sponsors.csv", index=False)
    open(f"{R}/cash_runway.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:5])
