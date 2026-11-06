"""Do sponsors with identified venture-capital owners pick genetically supported targets, and do they advance more?

Usage: python owners_models.py RESULTS_DIR   (after build_panel26.py, formd_link.py and owners_link.py)
Sample: as in formd_models.py, programmes and phase entries in indications with genetic insight whose first (entry)
trial was led by a non-top-20 industry sponsor, first trial in 2001 or later (the EDGAR index window).
Markers from owners_sponsors.csv (owners_link.py):
  public      the sponsor (any of its legal entities) filed a registration statement or annual report on EDGAR
  vc_backed   a Schedule 13D/13G about the sponsor was filed by an owner classified as venture capital
  crossover   ... by a life-science crossover fund
Ownership is observed only for public companies and only at or after the filing, so vc_backed is a sponsor-level
attribute (ever observed), not dated to the trial; the comparison that holds the public status fixed is the one
among public sponsors. Writes RESULTS_DIR/owners_models.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from pooling import pool_sparse

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
FIRST_YEAR = 2001
out = []
ow = pd.read_csv(f"{R}/owners_sponsors.csv")
ow["norm"] = ow.norm.astype(str)
PUBLIC = dict(zip(ow.norm, ow.is_registrant.astype(bool)))
PUBLIC_YEAR = dict(zip(ow.norm, pd.to_numeric(ow.registrant_first_year, errors="coerce")))
VC = dict(zip(ow.norm, ow.vc_backed.astype(bool)))
CROSS = dict(zip(ow.norm, ow.get("n_life_science_crossover", pd.Series(0, index=ow.index)).fillna(0).gt(0)))
ANY = dict(zip(ow.norm, ow.n_owners.fillna(0).gt(0)))


def mark(names, table, default=False):
    return names.map(rq2_stops.norm_sponsor).map(table).fillna(default).astype(int)


def fit(f, d, title, keep):
    try:
        d = pool_sparse(d, f)  # pooling.py: sparse control categories, so that the fit converges
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
                f"N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}; converged={r.mle_retvals['converged']}",
                t.round(4).to_string(),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.ge(FIRST_YEAR)].copy()
for col, table in (("public", PUBLIC), ("vc", VC), ("crossover", CROSS), ("any_owner", ANY)):
    P[col] = mark(P.first_sponsor, table)
P["public_at_trial"] = (
    (P.first_sponsor.map(rq2_stops.norm_sponsor).map(PUBLIC_YEAR) <= P.first_year).fillna(False).astype(int)
)
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
P["modality"] = P.drugType.map(MOD).fillna("other")
P["area"] = P.area.fillna("other")
P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)
out.append("Programmes (insight indications, first trial 2001+ by non-top-20 industry): sponsor markers by tier")
out.append(
    P.groupby("tier", observed=True)
    .agg(n=("drug", "size"), public=("public", "mean"), public_at_trial=("public_at_trial", "mean"), vc=("vc", "mean"), crossover=("crossover", "mean"), any_owner=("any_owner", "mean"))
    .round(4)
    .to_string()
)  # fmt: skip
out.append("ex-ante support by public x VC-backed:")
out.append(
    P.groupby(["public", "vc"])
    .agg(n=("drug", "size"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)
base_p = "C(tier) + C(yb) + C(area) + C(modality)"
fit(
    f"y ~ vc + {base_p}",
    P,
    "H1: ex-ante support at first trial ~ VC-backed (all non-top-20 industry)",
    ("vc",),
)
fit(f"y ~ vc + public + {base_p}", P, "H1: ex-ante support ~ VC-backed + public", ("vc", "public"))
PP = P[P.public.eq(1)].copy()
fit(f"y ~ vc + {base_p}", PP, "H1, public sponsors only: ex-ante support ~ VC-backed", ("vc",))
fit(
    f"y ~ vc + crossover + {base_p}",
    PP,
    "H1, public sponsors only: ~ VC-backed + crossover-backed",
    ("vc", "crossover"),
)
fit(
    f"y ~ public_at_trial + {base_p}",
    P,
    "H1: ex-ante support ~ public at the time of the first trial",
    ("public_at_trial",),
)
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ vc + {base_p}", P2, "H1 [dated OT evidence]: ex-ante support ~ VC-backed", ("vc",))
    fit(
        f"y ~ vc + {base_p}",
        P2[P2.public.eq(1)].copy(),
        "H1 [dated OT evidence], public sponsors only",
        ("vc",),
    )

E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_YEAR, end_year - 6)].copy()
for col, table in (("public", PUBLIC), ("vc", VC), ("crossover", CROSS)):
    E[col] = mark(E.lead_sponsor, table)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
E["modality"] = E.drugType.map(MOD).fillna("other")
E["area"] = E.area.fillna("other")
E["yb"] = pd.cut(E.entry_year, [2000, 2005, 2010, 2015, 2030]).astype(str)
E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
out.append(
    "=" * 100 + f"\nPhase entries {FIRST_YEAR}-{end_year - 6} (non-top-20 industry): advancement by public x VC-backed"
)
out.append(
    E.groupby(["public", "vc"]).agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string()
)
base_e = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ vc + gs + {base_e}", E, "Advancement ~ VC-backed + ex-ante support", ("vc", "gs"))
fit(f"adv ~ vc * gs + {base_e}", E, "Advancement ~ VC-backed x ex-ante support", ("vc", "gs", "vc:gs"))
EP = E[E.public.eq(1)].copy()
fit(f"adv ~ vc + gs + {base_e}", EP, "Advancement, public sponsors only ~ VC-backed + ex-ante support", ("vc", "gs"))
fit(
    f"adv ~ vc * gs + {base_e}",
    EP,
    "Advancement, public sponsors only ~ VC-backed x ex-ante support",
    ("vc", "gs", "vc:gs"),
)
open(f"{R}/owners_models.txt", "w").write("\n".join(out))
print("\n".join(out))
