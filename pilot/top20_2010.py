"""The selection model with the top-20 group defined by 2010 sales (plan: docs/plan_top20_2010.md).

Usage: python pilot/top20_2010.py RESULTS_DIR   (after build_panel26.py; gs_ot_models.py for the dated measure)

The pilot's top-20 group is fixed by prescription-drug sales in 2023. Here the group is the first twenty of the
Pharm Exec 50 of May 2011 (sales in 2010; sponsors.TOP20_2010): Teva and Eisai come in, Gilead and Merck KGaA go
out, and a sponsor that leaves the group is typed by the size of its portfolio. The script lists the programmes
that move and fits the selection model of robust26.py (ex-ante support at the first trial on sponsor tier,
first-trial period, therapeutic area and modality; errors clustered by drug) with the pilot's group, the 2010
group, and the 2010 group without Teva. The evidence-arrival contrast with this group is run by
evidence_arrival.py (EA_TOP20=2010). Writes RESULTS_DIR/top20_2010.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sponsors

R = sys.argv[1]
TOP = "Top-20 pharma"
TIERS = [TOP, "Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)", "Academic/other", "Government"]  # fmt: skip
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
out = []


def fit(d, col, title):
    d = d[d[col].isin(TIERS)].copy()
    d["tier"] = pd.Categorical(d[col], categories=TIERS)
    f = "y ~ C(tier) + C(yb) + C(area) + C(modality)"
    r = smf.logit(f, d).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
    t = r.summary2().tables[1]
    t = t.loc[[i for i in t.index if "tier" in i], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
    t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
    n = d.groupby("tier", observed=True).y.agg(["size", "sum"])
    out.extend(
        [
            "=" * 100,
            title,
            f,
            f"N={int(r.nobs)}; drugs={d.drug.nunique()}; converged={r.mle_retvals['converged']}; top-20 programmes "
            f"{int(n.loc[TOP, 'size'])} ({int(n.loc[TOP, 'sum'])} supported)",
            t.round(4).to_string(),
        ]
    )


P = pd.read_csv(f"{R}/programmes.csv.gz")
S = pd.read_csv(f"{R}/sponsors.csv.gz", usecols=["lead_sponsor", "sponsor_n_drugs"]).drop_duplicates("lead_sponsor")
size = P.first_sponsor.map(S.set_index("lead_sponsor").sponsor_n_drugs)
args = list(zip(P.first_sponsor, P.first_year, P.first_class, P.first_sponsor_tier, size))
P["tier_2010"] = [sponsors.tier_2010(*a) for a in args]
P["tier_2010x"] = [sponsors.tier_2010(*a, without=("Teva",)) for a in args]
P["parent"] = [sponsors.top20_parent(n, y) if c == "INDUSTRY" else None for n, y, c, *_ in args]
P["parent_2010"] = [sponsors.top20_parent_2010(n, y) if c == "INDUSTRY" else None for n, y, c, *_ in args]
P["modality"] = P.drugType.map(MOD).fillna("other")
P["area"] = P.area.fillna("other")
P["yb"] = pd.cut(P.first_year, [0, 2004, 2009, 2014, 2019, 2100], labels=["<=2004", "2005-09", "2010-14", "2015-19", "2020+"]).astype(str)  # fmt: skip
was, now = P.first_sponsor_tier.eq(TOP), P.tier_2010.eq(TOP)
out.append("The top-20 group defined by 2010 sales (Pharm Exec 50 of May 2011): " + ", ".join(sponsors.TOP20_2010))
out.append(
    f"programmes with a dated trial: {len(P)}; in the pilot's top-20 group: {int(was.sum())}; in the 2010 group: "
    f"{int(now.sum())}; leave the group: {int((was & ~now).sum())}; enter it: {int((~was & now).sum())}"
)
out.append("programmes that leave, by company and the tier they are given: " + "; ".join(f"{k[0]} -> {k[1]} {v}" for k, v in P[was & ~now].groupby(["parent", "tier_2010"]).size().items()))  # fmt: skip
out.append("programmes that enter, by company and the tier they had: " + "; ".join(f"{k[0]} <- {k[1]} {v}" for k, v in P[~was & now].groupby(["parent_2010", "first_sponsor_tier"]).size().items()))  # fmt: skip

H = P[P.insight].copy()
H["y"] = H.gs_ante_first.fillna(False).astype(int)
fit(H, "first_sponsor_tier", "H1 gs_ante_first, the pilot's top-20 group (as robust.txt)")
fit(H, "tier_2010", "H1 gs_ante_first, top-20 group defined by 2010 sales")
fit(H, "tier_2010x", "H1 gs_ante_first, top-20 group defined by 2010 sales, without Teva")
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    H2 = H.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    H2["y"] = H2.gs_ot_ante_first.fillna(False).astype(int)
    fit(H2, "first_sponsor_tier", "H1 [dated Open Targets evidence], the pilot's top-20 group")
    fit(H2, "tier_2010", "H1 [dated Open Targets evidence], top-20 group defined by 2010 sales")
else:
    out.append("(gs_ot_programmes.csv.gz not in RESULTS_DIR: the models with dated Open Targets evidence are not run)")
open(f"{R}/top20_2010.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
