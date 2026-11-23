"""The evidence-arrival contrast of evidence_arrival.py (D1) with clean controls, cohort by cohort.

Usage: python pilot/evidence_arrival_cohorts.py RESULTS_DIR MINIKEL_DATA_DIR OT_DATED_CSV gwas|all
(the arguments of evidence_arrival.py, which is run first to build the pair-year panel and rewrites its own output
files in RESULTS_DIR; needs pyfixest and Python >= 3.10; plan written before the run:
docs/plan_evidence_arrival_cohorts.md)

For each evidence year e, a stack holds the pairs whose evidence year is e and the pairs never supported, in the
years e-K to e+K. The model of D1 is fitted on the stacks together, with pair x group x stack and year x group x
stack fixed effects, so that a cohort is compared only with pairs that never gained evidence (Cengiz et al. 2019).
Writes RESULTS_DIR/evidence_arrival_<...>_cohorts.txt.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COLS = ["pid", "year", "indication_mesh_id", "post", "e0", "E"]


def stacks(grid, c0, c1, k, cohorts=None):
    """Long frame: one row per stack x pair x year x group (0 = top-20 pharma, 1 = other industry)."""
    never = grid[grid.E.isna()]
    parts, n_treated = [], 0
    for e in sorted(grid.E.dropna().unique()):
        if cohorts is not None and not (cohorts[0] <= e <= cohorts[1]):
            continue
        tr = grid[grid.E.eq(e) & grid.year.between(e - k, e + k)]
        co = never[never.year.between(e - k, e + k)]
        n_treated += tr.pid.nunique()
        for grp, col in ((0, c0), (1, c1)):
            for d in (tr, co):
                d = d[d.groupby("pid")[col].transform("sum") > 0]
                parts.append(d[COLS].assign(y=d[col].to_numpy(), grp=grp, cohort=int(e)))
    s = pd.concat(parts, ignore_index=True)
    s["pg"] = pd.factorize(s.cohort.astype(str) + "_" + s.pid.astype(str) + "_" + s.grp.astype(str))[0]
    s["yg"] = pd.factorize(s.cohort.astype(str) + "_" + s.year.astype(str) + "_" + s.grp.astype(str))[0]
    for t in ("post", "e0"):
        s[f"{t}_other"] = s[t] * s.grp
    return s, n_treated


def fit(ea, out, grid, c0, c1, k, title, cohorts=None):
    try:
        s, n_treated = stacks(grid, c0, c1, k, cohorts)
        m = ea.pf.fepois("y ~ post + e0 + post_other + e0_other | pg + yg", data=s, vcov={"CRV1": ea.CL})
        tp = s[s.E.notna()]
        head = (
            f"stacks={s.cohort.nunique()}; pairs with evidence in them={n_treated}; pair-groups with a start in the window: "
            f"with evidence {tp.pg.nunique()}, never supported {s[s.E.isna()].pg.nunique()}; rows={len(s)}; programme "
            f"starts on pairs with evidence: top-20 pharma {int(tp[tp.grp.eq(0)].y.sum())}, other industry "
            f"{int(tp[tp.grp.eq(1)].y.sum())}"
        )
        out.extend(["=" * 100, title, "y ~ post + e0 + post_other + e0_other | pair x group x stack + year x group x stack", head, ea.tidy(m, ["post", "post_other"])])  # fmt: skip
        names, b, v = list(m._coefnames), m.coef(), np.asarray(m._vcov)
        i, j = names.index("post"), names.index("post_other")
        est, se = b["post"] + b["post_other"], float(np.sqrt(v[i, i] + v[j, j] + 2 * v[i, j]))
        out.append(f"response of other industry (post + post_other, normal interval): RR {np.exp(est):.4f} ({np.exp(est - 1.96 * se):.4f} to {np.exp(est + 1.96 * se):.4f})")  # fmt: skip
    except Exception as e:
        out.extend(["=" * 100, title, f"failed: {e!r}"])


def main():
    import evidence_arrival as ea  # runs the planned analysis and leaves the pair-year panel in ea.grid

    out = ["The evidence-arrival contrast with clean controls, cohort by cohort (plan: docs/plan_evidence_arrival_cohorts.md)"]  # fmt: skip
    g = ea.grid
    c0, c1 = ea.YC["top-20 pharma"], ea.YC["other industry"]
    out.append(f"pair-year panel of evidence_arrival.py: {g.pid.nunique()} pairs, {int(g[g.E.notna()].pid.nunique())} with dated evidence")  # fmt: skip
    out.append("\n1. PRIMARY (plan): window of 5 years; post_other = ratio of the response of other industry to that of top-20 pharma")  # fmt: skip
    fit(ea, out, g, c0, c1, 5, "Stacked D1, years e-5 to e+5")
    out.append("\n2. SECONDARY (plan)")
    fit(ea, out, g, c0, c1, 3, "Stacked D1, years e-3 to e+3")
    fit(ea, out, g, c0, c1, 8, "Stacked D1, years e-8 to e+8")
    for lo, hi, label in ((0, 2015, "evidence years to 2015"), (2016, 2019, "evidence years 2016-2019"), (2020, 9999, "evidence years from 2020")):  # fmt: skip
        fit(ea, out, g, c0, c1, 5, f"Stacked D1, years e-5 to e+5, {label}", cohorts=(lo, hi))
    name = f"evidence_arrival{'_ot_' + ea.OT_SET if ea.OT_SET else ''}{ea.SUF}_cohorts.txt"
    open(f"{ea.R}/{name}", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
