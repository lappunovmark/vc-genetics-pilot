"""Did the response of programme starts to new genetic evidence change after 2015? Exploratory.

Usage: python pilot/evidence_arrival_2015.py RESULTS_DIR MINIKEL_DATA_DIR OT_DATED_CSV gwas
(the arguments of evidence_arrival.py, which is run first to build the pair-year panel and rewrites its own output
files in RESULTS_DIR; needs pyfixest and Python >= 3.10; plan: docs/plan_evidence_arrival_2015.md)

The stacked design of evidence_arrival_cohorts.py with one more term: post x late, where late marks the stacks of
evidence years from the cut (2016). exp(coefficient) is the ratio of the response to evidence published from the
cut over the response to earlier evidence. Writes RESULTS_DIR/evidence_arrival_ot_gwas_2015.txt.
"""

import gc
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_arrival_cohorts as eac

TOP = "Top-20 pharma"


def add_late(s, cut):
    """Adds the before/after terms in place (the stacked frame has millions of rows) and returns the frame."""
    s["late"] = (s.cohort >= cut).astype("int8")
    for t in ("post", "e0"):
        s[f"{t}_late"] = (s[t] * s.late).astype("int8")
        s[f"{t}_late_other"] = (s[t] * s.late * s.grp).astype("int8")
    return s


def slim(s):
    """Smaller integer types for the indicator and index columns: the models are fitted on up to four million rows."""
    for c in ("post", "e0", "post_other", "e0_other", "grp"):
        s[c] = s[c].astype("int8")
    for c in ("pg", "yg", "cohort"):
        s[c] = s[c].astype("int32")
    return s


def combo(m, names):
    """exp of the sum of coefficients, with a normal interval from the clustered covariance."""
    cn, b, v = list(m._coefnames), m.coef(), np.asarray(m._vcov)
    idx = [cn.index(n) for n in names]
    est, se = float(sum(b[n] for n in names)), float(np.sqrt(v[np.ix_(idx, idx)].sum()))
    return np.exp(est), np.exp(est - 1.96 * se), np.exp(est + 1.96 * se)


def fit(ea, out, grid, c0, c1, k, title, cut=2016, last=None):
    try:
        s, n_treated = eac.stacks(grid, c0, c1, k, cohorts=(0, last) if last else None)
        s = add_late(slim(s), cut)
        tp = s[s.E.notna()]
        cnt = tp.groupby(["late", "grp"]).agg(pair_groups=("pg", "nunique"), starts=("y", "sum"))
        out.extend(["=" * 100, title])
        out.append(f"stacks={s.cohort.nunique()} (late: {s[s.late.eq(1)].cohort.nunique()}); pairs with evidence in them={n_treated}; rows={len(s)}")  # fmt: skip
        for (late, grp), r in cnt.iterrows():
            out.append(f"  evidence {'from' if late else 'before'} {cut}, {'other industry' if grp else 'top-20 pharma'}: pair-groups with a start in the window={int(r.pair_groups)}; starts={int(r.starts)}")  # fmt: skip
        m = ea.pf.fepois("y ~ post + e0 + post_late + e0_late | pg + yg", data=s, vcov={"CRV1": ea.CL})
        out.extend(["common response: y ~ post + e0 + post_late + e0_late | pair x group x stack + year x group x stack", ea.tidy(m, ["post", "post_late"])])  # fmt: skip
        out.append("response to evidence from the cut (post + post_late): RR %.4f (%.4f to %.4f)" % combo(m, ["post", "post_late"]))  # fmt: skip
        f = "y ~ post + e0 + post_late + e0_late + post_other + e0_other + post_late_other + e0_late_other | pg + yg"
        del m
        gc.collect()
        m = ea.pf.fepois(f, data=s, vcov={"CRV1": ea.CL})
        out.extend(["by group: " + f.replace("| pg + yg", "| pair x group x stack + year x group x stack"), ea.tidy(m, ["post", "post_late", "post_other", "post_late_other"])])  # fmt: skip
        out.append("change for top-20 pharma (post_late): ratio %.4f (%.4f to %.4f)" % combo(m, ["post_late"]))
        out.append("change for other industry (post_late + post_late_other): ratio %.4f (%.4f to %.4f)" % combo(m, ["post_late", "post_late_other"]))  # fmt: skip
        del m, s
        gc.collect()
    except Exception as e:
        out.extend(["=" * 100, title, f"failed: {e!r}"])


def shares(R):
    """Share of new programmes with ex-ante genetic support by period and sponsor class (descriptive)."""
    from company_table import wilson

    P = pd.read_csv(f"{R}/programmes.csv.gz")
    P = P[P.insight & P.first_year.between(2001, 2025) & P.first_class.eq("INDUSTRY")].copy()
    P["group"] = np.where(P.first_sponsor_tier.eq(TOP), "top-20 pharma", "other industry")
    P["period"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2025], labels=["2001-2005", "2006-2010", "2011-2015", "2016-2020", "2021-2025"])  # fmt: skip
    rows = []
    for (g, p), d in P.groupby(["group", "period"], observed=True):
        n, k = len(d), int(d.gs_ante_first.fillna(False).sum())
        lo, hi = wilson(k, n)
        rows.append({"group": g, "period": p, "programmes": n, "supported": k, "share": k / n, "share_lo": lo, "share_hi": hi})  # fmt: skip
    return pd.DataFrame(rows)


def main():
    import evidence_arrival as ea  # runs the planned analysis and leaves the pair-year panel in ea.grid

    out = ["Did the response to new genetic evidence change after 2015? EXPLORATORY (plan: docs/plan_evidence_arrival_2015.md)"]  # fmt: skip
    g = ea.grid
    c0, c1 = ea.YC["top-20 pharma"], ea.YC["other industry"]
    out.append(f"pair-year panel of evidence_arrival.py: {g.pid.nunique()} pairs, {int(g[g.E.notna()].pid.nunique())} with dated evidence")  # fmt: skip
    out.append(
        "post_late = ratio of the response to evidence published from the cut over the response to earlier evidence"
    )
    out.append("\n1. PRIMARY (plan): window of 5 years, cut at 2016, all evidence years, common response of both industry groups")  # fmt: skip
    fit(ea, out, g, c0, c1, 5, "Stacked, years e-5 to e+5, late = evidence years from 2016")
    out.append("\n2. SECONDARY (plan)")
    fit(ea, out, g, c0, c1, 5, "Stacked, years e-5 to e+5, evidence years to 2020 only", last=2020)
    fit(ea, out, g, c0, c1, 5, "Stacked, years e-5 to e+5, late = evidence years from 2017", cut=2017)
    fit(ea, out, g, c0, c1, 8, "Stacked, years e-8 to e+8, late = evidence years from 2016")
    out.append("\n3. DESCRIPTIVE (plan; not a test): share of new programmes with ex-ante genetic support by period of the first trial")  # fmt: skip
    out.append("industry-sponsored programmes in indications with genetic insight; the share rises with the stock of evidence")  # fmt: skip
    out.append(shares(ea.R).round(4).to_string(index=False))
    open(f"{ea.R}/evidence_arrival_ot_gwas_2015.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
