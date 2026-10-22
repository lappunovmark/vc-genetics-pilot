"""Do sponsors with SEC Form D private placements pick genetically supported targets, and do they advance more often?

Usage: python formd_models.py RESULTS_DIR   (after build_panel26.py and formd_link.py)
Sample: as in sbir_models.py, programmes and phase entries in indications with genetic insight whose first (entry)
trial was led by a non-top-20 industry sponsor.
formd = the lead sponsor filed a Form D (biotech, pharma or other health care; not a pooled fund) in a calendar year
before the trial's start year. Form D data start in 2009, so the sample is restricted to trials that started in
2010 or later. In the selection models, therapeutic areas with fewer than three supported programmes are pooled
into 'other' to avoid separation.
Writes RESULTS_DIR/formd_models.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops

R = sys.argv[1]
IND = ["Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]
MOD = {
    "Small molecule": "small molecule",
    "Antibody": "antibody",
    "Antibody drug conjugate": "antibody",
    "Protein": "protein",
    "Enzyme": "protein",
    "Oligonucleotide": "nucleic acid/gene/cell",
    "Gene": "nucleic acid/gene/cell",
    "Cell": "nucleic acid/gene/cell",
}
FIRST_DATA_YEAR = 2009
fd = pd.read_csv(f"{R}/formd_sponsors.csv")
first = dict(zip(fd.norm, fd.formd_first_year))
out = []


def fit(f, d, title, keep):
    try:
        r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i in keep], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        out.extend(
            [
                "=" * 100,
                title,
                f,
                f"N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}; formd share={d.formd.mean():.4f}; "
                f"converged={r.mle_retvals['converged']}",
                t.round(4).to_string(),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def flag(names, years):
    fy = names.map(lambda s: first.get(rq2_stops.norm_sponsor(s)))
    return (pd.to_numeric(fy, errors="coerce") < years).fillna(False).astype(int)


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.gt(FIRST_DATA_YEAR)].copy()
P["formd"] = flag(P.first_sponsor, P.first_year)
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
P["modality"] = P.drugType.map(MOD).fillna("other")
P["area"] = P.area.fillna("other")
P["yb"] = pd.cut(P.first_year, [2009, 2014, 2019, 2100]).astype(str)
out.append(
    "Programmes (insight indications, first trial 2010+ by non-top-20 industry):\n"
    + P.groupby("tier", observed=True)
    .agg(n=("drug", "size"), formd=("formd", "mean"), gs_ante=("gs_ante_first", "mean"))
    .round(4)
    .to_string()
)
out.append(
    P.groupby("formd")
    .agg(n=("drug", "size"), gs_ante=("gs_ante_first", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)
P["y"] = P.gs_ante_first.fillna(False).astype(int)


def pool_sparse(d, col="area", min_events=3):
    """Areas with fewer than three supported programmes go to 'other' (otherwise the logit separates)."""
    ev = d.groupby(col).y.transform("sum")
    return d.assign(**{col: d[col].where(ev.ge(min_events), "other")})


P = pool_sparse(P)
fit(
    "y ~ formd + C(tier) + C(yb) + C(area) + C(modality)",
    P,
    "H1: ex-ante support at first trial ~ prior Form D",
    ("formd",),
)
S = pool_sparse(P[P.tier.eq("Industry, small (<=5 drugs)")])
fit(
    "y ~ formd + C(yb) + C(area) + C(modality)",
    S,
    "H1, small sponsors only: ex-ante support ~ prior Form D",
    ("formd",),
)

E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[
    E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_DATA_YEAR + 1, end_year - 6)
].copy()
E["formd"] = flag(E.lead_sponsor, E.entry_year)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
E["modality"] = E.drugType.map(MOD).fillna("other")
E["area"] = E.area.fillna("other")
E["yb"] = pd.cut(E.entry_year, [2009, 2014, 2030]).astype(str)
E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
out.append(
    "Phase entries 2010-%d (non-top-20 industry):\n" % (end_year - 6)
    + E.groupby("formd").agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string()
)
base = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ formd + gs + {base}", E, "Advancement ~ prior Form D + ex-ante support", ("formd", "gs"))
fit(f"adv ~ formd * gs + {base}", E, "Advancement ~ prior Form D x ex-ante support", ("formd", "gs", "formd:gs"))
open(f"{R}/formd_models.txt", "w").write("\n".join(out))
print("\n".join(out))
