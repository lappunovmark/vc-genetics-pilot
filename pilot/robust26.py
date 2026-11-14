"""Robustness checks on the OT 26.x pilot panel (outputs of build_panel26.py).

Usage: python robust26.py RESULTS_DIR
Writes RESULTS_DIR/robust.txt and RESULTS_DIR/robust_*.csv
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.discrete.conditional_models import ConditionalLogit
from statsmodels.stats.contingency_tables import StratifiedTable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops  # noqa: E402
import sponsors  # noqa: E402

R = sys.argv[1]
P = pd.read_csv(f"{R}/programmes.csv.gz")
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
out = []
TIERS = [
    "Top-20 pharma",
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]


def mod(dt):
    if dt == "Small molecule":
        return "small molecule"
    if dt in ("Antibody", "Antibody drug conjugate"):
        return "antibody"
    if dt in ("Protein", "Enzyme"):
        return "protein"
    if dt in ("Oligonucleotide", "Gene", "Cell"):
        return "nucleic acid/gene/cell"
    return "other"


for D in (P, E):
    D["modality"] = D.drugType.map(mod)
    D["area"] = D.area.fillna("other")
P["yb"] = pd.cut(
    P.first_year, [0, 2004, 2009, 2014, 2019, 2100], labels=["<=2004", "2005-09", "2010-14", "2015-19", "2020+"]
).astype(str)


def logit(f, d, groups, title):
    try:
        r = smf.logit(f, d).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})
        t = r.summary2().tables[1]
        keep = [i for i in t.index if "tier" in i or i in ("gs",) or i.startswith("gs:")]
        t = t.loc[keep, ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        conv = r.mle_retvals["converged"]
        out.extend(
            [
                "=" * 100,
                title,
                f,
                f"N={int(r.nobs)} clusters={groups.nunique()}" + ("" if conv else " NOT CONVERGED"),
                t.round(4).to_string(),
            ]
        )
        if not conv:
            print("WARNING: not converged:", title, file=sys.stderr)
        return t
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


# ---------- H1: who picks genetically supported targets? ----------
H = P[P.insight & P.first_sponsor_tier.isin(TIERS)].copy()
H["tier"] = pd.Categorical(H.first_sponsor_tier, categories=TIERS)
for y in ("gs_post", "gs_ante_first", "gs_post_noomim"):
    H["y"] = H[y].fillna(False).astype(int)
    logit("y ~ C(tier)", H, H.drug, f"H1 {y}: unadjusted")
    logit("y ~ C(tier) + C(yb) + C(area) + C(modality)", H, H.drug, f"H1 {y}: + first-trial period, area, modality")
# Where the adjusted gap in ex-ante support comes from: the controls added one at a time, and the composition of each
# tier's programmes. The unadjusted shares of small sponsors and top-20 pharma barely differ; the gap opens within
# periods and areas because small sponsors' programmes are more recent and less often in oncology.
H["y"] = H.gs_ante_first.fillna(False).astype(int)
logit("y ~ C(tier) + C(yb)", H, H.drug, "H1 gs_ante_first: + first-trial period only")
logit("y ~ C(tier) + C(yb) + C(area)", H, H.drug, "H1 gs_ante_first: + first-trial period, area")
mix = H.groupby("tier", observed=True).agg(
    programmes=("drug", "size"),
    first_trial_2015_or_later=("first_year", lambda s: s.ge(2015).mean()),
    oncology=("area", lambda s: s.eq("oncology").mean()),
    gs_ante=("y", "mean"),
)
out.extend(["=" * 100, "Composition of programmes by sponsor tier (shares):", mix.round(4).to_string()])
# How much the small-sponsor gap leans on the way errors are clustered and on single companies. Selection is a
# sponsor's decision, so errors are clustered by sponsor (the parent for top-20 pharma, else the normalised name);
# each top-20 company is left out in turn; and the top-20 group is cut to the 17 companies that lead the 2023
# prescription-sales ranking (sponsors.TOP20_BEYOND_17 names the other three).
H1F = "y ~ C(tier) + C(yb) + C(area) + C(modality)"
H["parent"] = [
    sponsors.top20_parent(n, y) if c == "INDUSTRY" else None
    for n, y, c in zip(H.first_sponsor, H.first_year, H.first_class)
]
H["sponsor_cluster"] = np.where(H.parent.notna(), H.parent, H.first_sponsor.map(rq2_stops.norm_sponsor).fillna("?"))
out.append(
    f"\nSponsor clusters: {H.sponsor_cluster.nunique()} "
    f"({H[H.tier.eq('Top-20 pharma')].sponsor_cluster.nunique()} top-20 parents)"
)
logit(H1F, H, H.sponsor_cluster, "H1 gs_ante_first: + first-trial period, area, modality; clustered by sponsor")
logit(
    H1F,
    H[~H.parent.isin(sponsors.TOP20_BEYOND_17)],
    H[~H.parent.isin(sponsors.TOP20_BEYOND_17)].drug,
    "H1 gs_ante_first: + first-trial period, area, modality; top-20 group cut to the 17 largest companies",
)
SMALL = "C(tier)[T.Industry, small (<=5 drugs)]"
loo = []
for parent in sorted(H.parent.dropna().unique()):
    D = H[H.parent.ne(parent)]
    r = smf.logit(H1F, D).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(D.drug)[0]})
    lo, hi = np.exp(r.conf_int().loc[SMALL])
    own = H[H.parent.eq(parent)]
    loo.append(
        {
            "left_out": parent,
            "programmes": len(own),
            "gs_ante": own.y.mean(),
            "OR_small": np.exp(r.params[SMALL]),
            "OR_lo": lo,
            "OR_hi": hi,
            "p": r.pvalues[SMALL],
            "converged": r.mle_retvals["converged"],
        }
    )
loo = pd.DataFrame(loo)
out.extend(
    [
        "=" * 100,
        "H1 gs_ante_first, small sponsors vs top-20 pharma with one top-20 company left out at a time:",
        loo.round(4).to_string(index=False),
        f"range of the small-sponsor OR: {loo.OR_small.min():.4f} to {loo.OR_small.max():.4f}; "
        f"largest p: {loo.p.max():.4f}; all converged: {bool(loo.converged.all())}",
    ]
)
# The same comparison within one disease: indication fixed effects instead of the therapeutic area, on the
# indications where support varies (the others carry no information on the tier coefficients); the conditional
# logit gives the same estimate without estimating the indication effects (model-based errors, not clustered).
V = H[H.groupby("indication_mesh_id").y.transform(lambda s: 0 < s.sum() < len(s)).astype(bool)]
out.append(
    f"\nIndications where ex-ante support varies: {V.indication_mesh_id.nunique()}; programmes: {len(V)}; "
    f"supported: {int(V.y.sum())} of {int(H.y.sum())}"
)
logit(
    "y ~ C(tier) + C(yb) + C(modality) + C(indication_mesh_id)",
    V,
    V.drug,
    "H1 gs_ante_first: + first-trial period, modality, indication fixed effects",
)
XV = pd.get_dummies(V[["tier", "yb", "modality"]].astype(str)).astype(float)
XV = XV.drop(
    columns=["tier_Top-20 pharma", f"yb_{sorted(V.yb.unique())[0]}", f"modality_{sorted(V.modality.unique())[0]}"]
)
cl = ConditionalLogit(V.y.values, XV.values, groups=pd.factorize(V.indication_mesh_id)[0]).fit(
    disp=0, method="newton", maxiter=200
)  # the default BFGS stops short of the maximum here
i = list(XV.columns).index("tier_Industry, small (<=5 drugs)")
out.extend(
    [
        "=" * 100,
        "H1 gs_ante_first: conditional logit within indication (period, modality; model-based errors)",
        f"small sponsors vs top-20 pharma: OR {np.exp(cl.params[i]):.4f} "
        f"({np.exp(cl.params[i] - 1.96 * cl.bse[i]):.4f}-{np.exp(cl.params[i] + 1.96 * cl.bse[i]):.4f}), "
        f"p={cl.pvalues[i]:.4f}",
    ]
)
# Without a model: small sponsors against top-20 pharma within cells of period x area x modality (Mantel-Haenszel).
S2 = H[H.first_sponsor_tier.isin(["Top-20 pharma", "Industry, small (<=5 drugs)"])]
tabs = []
for _, d in S2.groupby(["yb", "area", "modality"]):
    t = (
        pd.crosstab(d.first_sponsor_tier.ne("Top-20 pharma").astype(int), d.y)
        .reindex(index=[1, 0], columns=[1, 0], fill_value=0)
        .values
    )
    if t.sum(1).min() > 0:
        tabs.append(t)
mh = StratifiedTable(tabs)
lo, hi = mh.oddsratio_pooled_confint()
out.extend(
    [
        "=" * 100,
        "H1 gs_ante_first: Mantel-Haenszel, small sponsors vs top-20 pharma within period x area x modality cells",
        f"small sponsors vs top-20 pharma: OR {mh.oddsratio_pooled:.4f} ({lo:.4f}-{hi:.4f}), "
        f"p={mh.test_null_odds().pvalue:.4f}; cells with both groups: {len(tabs)}; "
        f"programmes: {int(sum(t.sum() for t in tabs))}",
    ]
)
# novel-drug programmes: the drug's first indication(s), first trial 2000+, sponsor of the drug's first trial
N = H[H.is_drug_first_indication & H.first_year.ge(2000)].copy()
out.append(f"\nNovel-drug programmes (drug first indication, first trial >= 2000): {len(N)}")


def pool_sparse(d, col="area", min_events=3):
    """Categories with fewer than three supported programmes go to 'other' (otherwise the logit separates: in the
    novel-drug sample no infection programme has ex-ante support)."""
    ev = d.groupby(col).y.transform("sum")
    return d.assign(**{col: d[col].where(ev.ge(min_events), "other")})


N["y"] = N.gs_post.fillna(False).astype(int)
logit("y ~ C(tier) + C(yb) + C(area) + C(modality)", pool_sparse(N), N.drug, "H1 gs_post, novel-drug programmes only")
N["y"] = N.gs_ante_first.fillna(False).astype(int)
logit(
    "y ~ C(tier) + C(yb) + C(area) + C(modality)",
    pool_sparse(N),
    N.drug,
    "H1 gs_ante_first, novel-drug programmes only",
)
tab = N.groupby("first_sponsor_tier").agg(
    n=("drug", "size"), gs_post=("gs_post", "mean"), gs_ante=("gs_ante_first", "mean")
)
tab.to_csv(f"{R}/robust_h1_novel.csv")
out.append(tab.round(4).to_string())

# ---------- Transitions ----------
end_year = int(E.entry_year.max())
T = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
T["tier"] = pd.Categorical(T.sponsor_tier, categories=TIERS)
T["gs"] = T.gs_ante.fillna(False).astype(int)
T["adv"] = T.advanced.astype(int)
T["yb"] = pd.cut(T.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
base = "C(phase) + C(yb) + C(area) + C(modality)"
logit(f"adv ~ gs + C(tier) + {base}", T, T.drug, "Advance: main effects (ex-ante support at entry)")
logit(f"adv ~ gs * C(tier) + {base}", T, T.drug, "Advance: support x sponsor tier")
T2 = T.copy()
T2["adv"] = T2.advanced_trial_only.astype(int)
logit(
    f"adv ~ gs + C(tier) + {base}",
    T2,
    T2.drug,
    "Advance (strict: a later higher-phase trial, approval alone not counted)",
)
T3 = T[T.mesh_map.eq("direct")]
logit(f"adv ~ gs + C(tier) + {base}", T3, T3.drug, "Advance: indications mapped directly to MeSH only")
T4 = T.copy()
T4["gs"] = T4.gs_ante_noomim.fillna(False).astype(int)
logit(f"adv ~ gs + C(tier) + {base}", T4, T4.drug, "Advance: support without OMIM")
T5 = T.copy()
T5["gs"] = T5.gs_post.fillna(False).astype(int)
logit(f"adv ~ gs + C(tier) + {base}", T5, T5.drug, "Advance: ex-post support (any year)")
I = T[T.tier.isin(TIERS[:4])].copy()
I["tier"] = I.tier.cat.remove_unused_categories()
logit(f"adv ~ gs * C(tier) + {base}", I, I.drug, "Advance, industry sponsors only: support x tier")
for k in (1, 2, 3):
    Ik = I[I.phase.eq(k)]
    logit(
        "adv ~ gs * C(tier) + C(yb) + C(area) + C(modality)",
        Ik,
        Ik.drug,
        f"Advance from phase {k}, industry only: support x tier",
    )

# ---------- Minikel-style benchmark: phase-wise P(S) product, ex-post support ----------
rows = []
B = E[E.insight & ~E.prior_higher & E.entry_year.between(2000, end_year - 6)]
for lab, col in (("ex-post", "gs_post"), ("ex-ante", "gs_ante")):
    ps = {}
    for g in (True, False):
        prod = 1.0
        for k in (1, 2, 3):
            d = B[(B.phase == k) & (B[col].fillna(False) == g)]
            p = d.advanced.mean()
            prod *= p
            rows.append({"support": lab, "gs": g, "phase": k, "n": len(d), "p_advance": p})
        ps[g] = prod
    rows.append(
        {"support": lab, "gs": "RS product I->launch", "phase": "I-L", "n": np.nan, "p_advance": ps[True] / ps[False]}
    )
bm = pd.DataFrame(rows)
bm.to_csv(f"{R}/robust_benchmark.csv", index=False)
out.extend(["=" * 100, "Benchmark vs Minikel et al. (2.16 product / 2.63 crude):", bm.round(4).to_string()])

# ---------- benchmark variants: similarity-aware advancement, industry sponsors, novel-drug programmes ----------
IND = TIERS[:4]
rows = []
variants = {
    "exact indication, all sponsors": (E.insight & ~E.prior_higher, "advanced"),
    "similar indication, all sponsors": (E.insight & ~E.prior_higher_sim, "advanced_sim"),
    "exact indication, industry": (E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND), "advanced"),
    "similar indication, industry": (E.insight & ~E.prior_higher_sim & E.sponsor_tier.isin(IND), "advanced_sim"),
    "similar indication, industry, drug first indication": (
        E.insight & ~E.prior_higher_sim & E.sponsor_tier.isin(IND) & E.is_drug_first_indication,
        "advanced_sim",
    ),
}
for name, (mask, ycol) in variants.items():
    B2 = E[mask & E.entry_year.between(2000, end_year - 6)]
    for col in ("gs_post", "gs_ante"):
        ps, rec = {}, {"variant": name, "support": col}
        for g in (True, False):
            prod = 1.0
            for k in (1, 2, 3):
                d = B2[(B2.phase == k) & (B2[col].fillna(False) == g)]
                p = d[ycol].mean()
                prod *= p
                rec[f"p{k}_{'gs' if g else 'no'}"] = round(p, 4)
                rec[f"n{k}_{'gs' if g else 'no'}"] = len(d)
            ps[g] = prod
        rec["pIL_gs"] = round(ps[True], 4)
        rec["pIL_no"] = round(ps[False], 4)
        rec["RS_product"] = round(ps[True] / ps[False], 3)
        rows.append(rec)
bv = pd.DataFrame(rows)
bv.to_csv(f"{R}/robust_benchmark_variants.csv", index=False)
out.extend(["=" * 100, "Benchmark variants (phase-wise product):", bv.to_string()])
S = E[E.insight & ~E.prior_higher_sim & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
S["tier"] = pd.Categorical(S.sponsor_tier, categories=TIERS)
S["gs"] = S.gs_ante.fillna(False).astype(int)
S["adv"] = S.advanced_sim.astype(int)
S["yb"] = pd.cut(S.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
logit(f"adv ~ gs + C(tier) + {base}", S, S.drug, "Advance (similar-indication definition): main effects")
logit(f"adv ~ gs * C(tier) + {base}", S, S.drug, "Advance (similar-indication definition): support x tier")
SI = S[S.tier.isin(IND)].copy()
SI["tier"] = SI.tier.cat.remove_unused_categories()
for k in (1, 2, 3):
    Sk = SI[SI.phase.eq(k)]
    logit(
        "adv ~ gs * C(tier) + C(yb) + C(area) + C(modality)",
        Sk,
        Sk.drug,
        f"Advance (similar) from phase {k}, industry: support x tier",
    )
open(f"{R}/robust.txt", "w").write("\n".join(out))
print("\n".join(out))
