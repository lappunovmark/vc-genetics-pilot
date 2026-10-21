"""Robustness checks on the OT 26.x pilot panel (outputs of build_panel26.py).

Usage: python robust26.py RESULTS_DIR
Writes RESULTS_DIR/robust.txt and RESULTS_DIR/robust_*.csv
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

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
        out.extend(["=" * 100, title, f, f"N={int(r.nobs)} clusters={groups.nunique()}", t.round(4).to_string()])
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
# novel-drug programmes: the drug's first indication(s), first trial 2000+, sponsor of the drug's first trial
N = H[H.is_drug_first_indication & H.first_year.ge(2000)].copy()
out.append(f"\nNovel-drug programmes (drug first indication, first trial >= 2000): {len(N)}")
N["y"] = N.gs_post.fillna(False).astype(int)
logit("y ~ C(tier) + C(yb) + C(area) + C(modality)", N, N.drug, "H1 gs_post, novel-drug programmes only")
N["y"] = N.gs_ante_first.fillna(False).astype(int)
logit("y ~ C(tier) + C(yb) + C(area) + C(modality)", N, N.drug, "H1 gs_ante_first, novel-drug programmes only")
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
