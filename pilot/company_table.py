"""Genetic support of the programmes of each top-20 company. Plan: docs/plan_company_table.md.

Usage: python pilot/company_table.py RESULTS_DIR
Writes company_table.txt and company_table.csv.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sponsors
from pooling import pool_sparse

TOP = "Top-20 pharma"
MOD = {"Small molecule": "small molecule", "Antibody": "antibody", "Antibody drug conjugate": "antibody", "Protein": "protein", "Enzyme": "protein", "Oligonucleotide": "nucleic acid/gene/cell", "Gene": "nucleic acid/gene/cell", "Cell": "nucleic acid/gene/cell"}  # fmt: skip


def wilson(k, n, z=1.959964):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def poisson_ci(k):
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k > 0 else 0.0
    return lo, stats.chi2.ppf(0.975, 2 * k + 2) / 2


FORMULA = "y ~ C(yb) + C(area) + C(modality)"


def table(d, f=FORMULA):
    """One row per company: programmes, supported, share with Wilson interval, observed/expected with exact interval."""
    d = pool_sparse(d, f)
    r = smf.logit(f, d).fit(disp=0, maxiter=200)
    d = d.assign(p=r.predict(d))
    rows = []
    for c, g in d.groupby("company"):
        n, k, e = len(g), int(g.y.sum()), float(g.p.sum())
        lo, hi = wilson(k, n)
        plo, phi = poisson_ci(k)
        rows.append({"company": c, "programmes": n, "supported": k, "share": k / n, "share_lo": lo, "share_hi": hi, "expected": e, "ratio": k / e, "ratio_lo": plo / e, "ratio_hi": phi / e})  # fmt: skip
    return pd.DataFrame(rows).sort_values("ratio", ascending=False), d, f


def lr_test(d, f):
    k = d.groupby("company").y.sum()
    d = d.assign(co=d.company.where(d.company.map(k) >= 3, "pooled (fewer than three supported)"))
    r0 = smf.logit(f, d).fit(disp=0, maxiter=200)
    r1 = smf.logit(f + " + C(co)", d).fit(disp=0, maxiter=200)
    lr, df = 2 * (r1.llf - r0.llf), int(r1.df_model - r0.df_model)
    return lr, df, float(stats.chi2.sf(lr, df)), int(d.co.nunique())


def drug_level(d):
    """One row per drug and company (check added after the first run, see the plan)."""
    d = d.sort_values(["company", "drug", "first_year", "area"])
    first = d[d.first_year.eq(d.groupby(["company", "drug"]).first_year.transform("min"))]
    area = first.groupby(["company", "drug"]).area.agg(lambda s: s.value_counts().sort_index().idxmax())
    g = d.groupby(["company", "drug"]).agg(y=("y", "max"), n_prog=("y", "size"), first_year=("first_year", "min"), modality=("modality", "first"))  # fmt: skip
    g = g.join(area).reset_index()
    g["yb"] = pd.cut(g.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
    g["ln_prog"] = np.log(g.n_prog)
    return g


def block(out, d, title, f=FORMULA):
    t, dd, f = table(d, f)
    lr, df, p, levels = lr_test(dd, f)
    out.extend(["=" * 100, title, f"rows={len(d)}; supported={int(d.y.sum())}; companies={d.company.nunique()}"])
    out.append(f"likelihood-ratio test of company effects ({levels} levels): chi2={lr:.2f}, df={df}, p={p:.4f}")
    out.append(t.round(4).to_string(index=False))
    return t


def main(R):
    P = pd.read_csv(f"{R}/programmes.csv.gz")
    P = P[P.insight & P.first_sponsor_tier.eq(TOP) & P.first_year.ge(2001)].copy()
    P["company"] = [sponsors.top20_parent(n, y) for n, y in zip(P.first_sponsor, P.first_year)]
    out = ["Genetic support of the programmes of each top-20 company (plan: docs/plan_company_table.md)"]
    out.append(f"top-20 programmes in indications with genetic insight, first trial 2001+: {len(P)}; without a parent under the rules: {int(P.company.isna().sum())}")  # fmt: skip
    P = P[P.company.notna()].copy()
    P["y"] = P.gs_ante_first.fillna(False).astype(int)
    P["modality"], P["area"] = P.drugType.map(MOD).fillna("other"), P.area.fillna("other")
    P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
    out.append("\n1. PRIMARY (plan)")
    t = block(out, P, "All programmes")
    t.to_csv(f"{R}/company_table.csv", index=False)
    out.append("\n2. SECONDARY (plan)")
    block(out, P[P.first_year.ge(2010)].copy(), "First trials from 2010")
    block(out, P[P.is_drug_first_indication.eq(True)].copy(), "Novel programmes only (the drug's first indication)")
    out.append("\n3. CHECK ADDED AFTER THE FIRST RUN (plan, second part): the drug as the unit")
    g = drug_level(P)
    out.append(f"drugs={P.drug.nunique()}; drug-company rows={len(g)}; drugs with programmes first sponsored by more than one company={int((g.groupby('drug').company.nunique() > 1).sum())}")  # fmt: skip
    out.append("columns: 'programmes' and 'supported' here count drugs (drug-company rows)")
    td = block(out, g, "Drugs: at least one supported programme", FORMULA + " + ln_prog")
    td.to_csv(f"{R}/company_table_drugs.csv", index=False)
    open(f"{R}/company_table.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
