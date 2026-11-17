"""Venture rounds with named investors (Crunchbase export of December 2015) and genetic support. Exploratory.

Usage: python pilot/cb_models.py RESULTS_DIR CRUNCHBASE_DIR
CRUNCHBASE_DIR holds companies.csv, rounds.csv and investments.csv of the Crunchbase data export of 4 December 2015
(CSV copy at github.com/notpeter/crunchbase-data; Crunchbase data, CC BY-NC 4.0, not redistributed here).

Why: Form D shows that a sponsor raised private money, not from whom, and Schedules 13D/13G name owners only after
the sponsor became public. Crunchbase lists funding rounds by type (venture, seed, angel, ...) with their dates and
investors, so it marks a venture round before the trial for private sponsors too. Its coverage is incomplete and
stops in 2015, so the sample is programmes whose first trial started in 2001-2016.

Linkage. Sponsor names (first sponsor of a programme, non-top-20 industry) are matched to Crunchbase company names
on the normalised name of rq2_stops.norm_sponsor. A candidate is accepted when the two names are also equal once
only legal forms are removed (sbir_link.strict), or when the Crunchbase company is in a life-science or health
category; other candidates (namesakes in other industries) are rejected. The candidates were then read by hand and
the corrections are in pilot/cb_decisions.csv. Every candidate is written out with its decision.

Markers (sponsor x year of the programme's first trial):
  cb            the sponsor is found in Crunchbase
  vc_round      a round of type "venture" dated before the year of the first trial
  vc_named      such a round with at least one investor that is an organisation classified as venture capital or
                life-science crossover by pilot/investor_classes.tsv
  any_round     any equity round (venture, seed, angel, private equity, undisclosed, convertible note) before that year
Models: the H1 logit of owners_models.py (tier, first-trial period, therapeutic area, modality; errors clustered by
drug; sparse controls pooled) and the advancement logit. Writes cb_link_review.csv, cb_sponsors.csv, cb_models.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owners_link
import rq2_stops
import sbir_link
from pooling import pool_sparse

R, CB = sys.argv[1], sys.argv[2]
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
FIRST_YEAR, LAST_YEAR = 2001, 2016  # rounds are observed to December 2015
LIFE = (
    r"bio|pharma|health|medic|therapeut|life science|diagnos|clinical|drug|oncolog|genetic|neurosc|vaccin|"
    r"nanotech|chemic"
)
EQUITY = {"venture", "seed", "angel", "private_equity", "undisclosed", "convertible_note"}
DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_decisions.csv")
out = []


def read(name):
    return pd.read_csv(f"{CB}/{name}.csv", dtype=str, encoding_errors="replace")


def link(names):
    """Sponsor names -> accepted Crunchbase companies; every candidate with its decision."""
    c = read("companies")
    c = c[c.name.notna()].copy()
    c["norm"] = c.name.map(rq2_stops.norm_sponsor)
    c["strict"] = c.name.map(sbir_link.strict)
    s = pd.DataFrame({"first_sponsor": sorted(set(names))})
    s["norm"] = s.first_sponsor.map(rq2_stops.norm_sponsor)
    s["strict_sponsor"] = s.first_sponsor.map(sbir_link.strict)
    m = s[s.norm.notna()].merge(c[c.norm.notna()], on="norm")
    same = m.strict_sponsor.eq(m.strict)
    life = m.category_list.fillna("").str.contains(LIFE, case=False)
    m["decision"] = np.where(same | life, "accept", "reject")
    m["reason"] = np.select([same, life], ["same name", "life-science category"], "other industry, name differs")
    if os.path.exists(DECISIONS):  # hand review of the candidates; overrides the rule
        d = pd.read_csv(DECISIONS).set_index(["first_sponsor", "name"])
        key = list(zip(m.first_sponsor, m.name))
        hit = [k in d.index for k in key]
        m.loc[hit, "decision"] = [d.loc[k, "decision"] for k, h in zip(key, hit) if h]
        m.loc[hit, "reason"] = ["hand review: " + d.loc[k, "reason"] for k, h in zip(key, hit) if h]
    cols = ["first_sponsor", "name", "category_list", "country_code", "founded_at", "permalink", "decision", "reason"]
    return m[cols].sort_values(["first_sponsor", "name"]).reset_index(drop=True)


def rounds_of(m):
    """Rounds of the accepted companies, one row per sponsor x round, with the classes of the investors."""
    r = read("rounds")
    r["date"] = pd.to_datetime(r.funded_at, errors="coerce")
    inv = read("investments")
    rules = owners_link.owner_classes()
    inv["org"] = inv.investor_permalink.fillna("").str.startswith("/organization/")
    inv["cls"] = [owners_link.classify(str(n), rules) for n in inv.investor_name]
    inv["vc"] = inv.org & inv.cls.isin(["venture capital", "life-science crossover"])
    g = inv.groupby("funding_round_permalink").agg(
        n_investors=("investor_name", "nunique"),
        n_org=("org", "sum"),
        n_vc=("vc", "sum"),
        vc_names=("investor_name", lambda x: "; ".join(sorted(set(x[inv.loc[x.index, "vc"]].astype(str))))),
    )
    r = r.merge(g, left_on="funding_round_permalink", right_index=True, how="left")
    for col in ("n_investors", "n_org", "n_vc"):
        r[col] = r[col].fillna(0).astype(int)
    a = m[m.decision.eq("accept")][["first_sponsor", "permalink"]].drop_duplicates()
    return a.merge(r, left_on="permalink", right_on="company_permalink", how="left")


def first_year(sr, mask):
    y = sr[mask & sr.date.notna()].groupby("first_sponsor").date.min().dt.year
    return y.to_dict()


def fit(f, d, title, keep):
    try:
        d = pool_sparse(d, f)
        r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i in keep], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        ev = int(d[f.split("~")[0].strip()].sum())
        out.extend(
            [
                "=" * 100,
                title,
                f,
                f"N={int(r.nobs)}; events={ev}; clusters (drugs)={d.drug.nunique()}; "
                f"converged={r.mle_retvals['converged']}",
                t.round(4).to_string(),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def before(names, years, table):
    y = names.map(table)
    return (y < years).fillna(False).astype(int)


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.between(FIRST_YEAR, LAST_YEAR)].copy()
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[
    E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_YEAR, min(LAST_YEAR, end_year - 6))
].copy()  # fmt: skip

M = link(pd.concat([P.first_sponsor, E.lead_sponsor]).dropna())
M.to_csv(f"{R}/cb_link_review.csv", index=False)
SR = rounds_of(M)
venture = SR.funding_round_type.eq("venture")
T = {
    "vc_round": first_year(SR, venture),
    "vc_named": first_year(SR, venture & SR.n_vc.gt(0)),
    "any_round": first_year(SR, SR.funding_round_type.isin(EQUITY)),
}
INCB = set(M[M.decision.eq("accept")].first_sponsor)
S = pd.DataFrame({"first_sponsor": sorted(INCB)})
for k, tab in T.items():
    S[f"first_{k}_year"] = S.first_sponsor.map(tab)
S["n_venture_rounds"] = S.first_sponsor.map(SR[venture].groupby("first_sponsor").size()).fillna(0).astype(int)
S["vc_investors"] = S.first_sponsor.map(
    SR[venture & SR.vc_names.fillna("").ne("")]
    .groupby("first_sponsor")
    .vc_names.agg(lambda x: "; ".join(sorted(set("; ".join(x).split("; ")))))
)
S.to_csv(f"{R}/cb_sponsors.csv", index=False)

n_sp = pd.concat([P.first_sponsor, E.lead_sponsor]).dropna().nunique()
out.append(
    "Crunchbase export of 4 December 2015: venture rounds of trial sponsors (exploratory; see the module docstring)"
)
out.append(
    f"sponsor names (non-top-20 industry, first trial or phase entry {FIRST_YEAR}-{LAST_YEAR}): {n_sp}; "
    f"candidate name matches: {len(M)}; accepted: {int(M.decision.eq('accept').sum())} "
    f"(same name {int((M.decision.eq('accept') & M.reason.eq('same name')).sum())}, life-science category "
    f"{int((M.decision.eq('accept') & M.reason.eq('life-science category')).sum())}); rejected: "
    f"{int(M.decision.eq('reject').sum())} (by hand {int(M.reason.str.startswith('hand review').sum())})"
)
out.append(
    f"sponsors found in Crunchbase: {len(INCB)}; with a venture round: {int(S.first_vc_round_year.notna().sum())}; "
    f"with a venture round that names a venture or crossover fund: {int(S.first_vc_named_year.notna().sum())}; "
    f"with any equity round: {int(S.first_any_round_year.notna().sum())}"
)

for D, name_col, year_col in ((P, "first_sponsor", "first_year"), (E, "lead_sponsor", "entry_year")):
    D["cb"] = D[name_col].isin(INCB).astype(int)
    for k, tab in T.items():
        D[k] = before(D[name_col], D[year_col], tab)
    D["modality"] = D.drugType.map(MOD).fillna("other")
    D["area"] = D.area.fillna("other")
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2016]).astype(str)
E["yb"] = pd.cut(E.entry_year, [2000, 2005, 2010, 2016]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)

out.append(f"\nProgrammes (insight indications, first trial {FIRST_YEAR}-{LAST_YEAR}, non-top-20 industry): {len(P)}")
out.append(
    P.groupby("tier", observed=True)
    .agg(n=("drug", "size"), in_crunchbase=("cb", "mean"), vc_round=("vc_round", "mean"), vc_named=("vc_named", "mean"), any_round=("any_round", "mean"), gs_ante=("y", "mean"))
    .round(4)
    .to_string()
)  # fmt: skip
out.append("ex-ante support by Crunchbase x venture round before the first trial:")
out.append(
    P.groupby(["cb", "vc_round"])
    .agg(n=("drug", "size"), supported=("y", "sum"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)
base_p = "C(tier) + C(yb) + C(area) + C(modality)"
fit(f"y ~ vc_round + {base_p}", P, "H1: ex-ante support at first trial ~ venture round before the first trial", ("vc_round",))  # fmt: skip
fit(f"y ~ vc_round + cb + {base_p}", P, "H1: ~ venture round + found in Crunchbase", ("vc_round", "cb"))
PC = P[P.cb.eq(1)].copy()
fit(f"y ~ vc_round + {base_p}", PC, "H1, sponsors found in Crunchbase only: ~ venture round", ("vc_round",))
fit(f"y ~ vc_named + {base_p}", P, "H1: ~ venture round that names a venture or crossover fund", ("vc_named",))
fit(f"y ~ vc_named + {base_p}", PC, "H1, sponsors found in Crunchbase only: ~ venture round with a named fund", ("vc_named",))  # fmt: skip
fit(f"y ~ any_round + {base_p}", P, "H1: ~ any equity round before the first trial", ("any_round",))
PS = P[P.first_sponsor_tier.eq(IND[2])].copy()
fit("y ~ vc_round + C(yb) + C(area) + C(modality)", PS, "H1, small sponsors only: ~ venture round", ("vc_round",))
P10 = P[P.first_year.ge(2006)].copy()
fit(f"y ~ vc_round + {base_p}", P10, "H1, first trial 2006-2016 (better Crunchbase coverage): ~ venture round", ("vc_round",))  # fmt: skip
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ vc_round + {base_p}", P2, "H1 [dated OT evidence]: ~ venture round before the first trial", ("vc_round",))
    fit(f"y ~ vc_round + {base_p}", P2[P2.cb.eq(1)].copy(), "H1 [dated OT evidence], sponsors found in Crunchbase only", ("vc_round",))  # fmt: skip

E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
out.append("=" * 100 + f"\nPhase entries {FIRST_YEAR}-{int(E.entry_year.max())} (non-top-20 industry): {len(E)}")
out.append(
    E.groupby(["cb", "vc_round"]).agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string()
)
base_e = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ vc_round + gs + {base_e}", E, "Advancement ~ venture round before the entry + ex-ante support", ("vc_round", "gs"))  # fmt: skip
fit(f"adv ~ vc_round * gs + {base_e}", E, "Advancement ~ venture round x ex-ante support", ("vc_round", "gs", "vc_round:gs"))  # fmt: skip
EC = E[E.cb.eq(1)].copy()
fit(f"adv ~ vc_round + gs + {base_e}", EC, "Advancement, sponsors found in Crunchbase only", ("vc_round", "gs"))
open(f"{R}/cb_models.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
