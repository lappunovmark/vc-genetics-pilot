"""Corporate and independent venture investors, and genetic support. Exploratory.

Usage: python pilot/cvc_models.py RESULTS_DIR CRUNCHBASE_DIR
(after cb_models.py and owners_link.py: uses cb_link_review.csv and owners_pairs.csv.gz)

Why: the venture markers of the pilot do not separate venture arms of pharmaceutical companies from independent
venture funds. A corporate investor chooses with the parent's scientific knowledge and for the parent's pipeline, so
sponsors it backs may select targets differently (Alvarez-Garrido and Dushnitsky compare the two kinds of backing).

Corporate investors are named by pilot/corporate_investors.tsv (tab-separated regular expressions, first match
wins): venture arms and direct investments of large drug and medical-technology companies, other drug companies,
corporations outside drug development, and investment arms of foundations that own drug companies (Novo Holdings,
Lundbeckfonden, Wellcome Trust), which are kept apart. Independent funds are investors classified as venture capital
or life-science crossover by pilot/investor_classes.tsv that no corporate rule names.

A. Private rounds (Crunchbase export of December 2015; programmes first tried in 2001-2016, as cb_models.py):
   a programme has a corporate investor when a venture round dated before the year of its first trial names one,
   and independent funds only when such a round names an independent fund and no corporate investor.
B. Owners of public sponsors (Schedules 13D/13G, as owners_models.py): the sponsor has a corporate owner when a
   large drug company or its venture arm is named with it in a filing, and venture funds only when a venture fund is
   and no corporate owner. Sponsor-level, not dated to the trial; only large companies count, because the index does
   not say which party of a filing is the owner and a small sponsor cannot own 5% of a large company. A large company
   also files when it buys the sponsor, so the undated marker mixes minority stakes with later acquisitions; the
   dated variant keeps owners whose first filing is no later than the year of the programme's first trial, for
   sponsors that were public by then.
Models are the H1 logit and the advancement logit of cb_models.py and owners_models.py with these groups.
Writes cvc_models.txt and cvc_sponsors.csv.
"""

import os
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owners_link
import rq2_stops
from pooling import pool_sparse

R, CB = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
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
CORP = ["pharma corporate, large", "pharma corporate, other", "other corporate"]
A_GROUPS = [
    "no venture round",
    "venture round, investors not classified",
    "independent funds only",
    "corporate investor",
]
B_GROUPS = ["no venture or corporate owner", "venture funds only", "corporate owner"]
out = []


def corporate_rules():
    d = pd.read_csv(os.path.join(HERE, "corporate_investors.tsv"), sep="\t")
    return [(re.compile(p, re.I), k) for p, k in zip(d.pattern, d.kind)]


def kind(name, rules):
    for rx, k in rules:
        if rx.search(name):
            return k
    return ""


def fit(f, d, title, keep):
    try:
        y = f.split("~")[0].strip()
        for col in ("fin", "own"):
            if f"C({col})" in f:  # a group without a single event is left out and named (see h1_mechanisms.py)
                ev = d.groupby(col, observed=True)[y].sum()
                empty = [c for c in ev.index if ev[c] == 0]
                if empty:
                    d = d[~d[col].isin(empty)].copy()
                    d[col] = d[col].cat.remove_unused_categories()
                    title += "; groups without events left out: " + ", ".join(empty)
        d = pool_sparse(d, f)
        r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if keep(i)], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
        note = f"N={int(r.nobs)}; events={int(d[y].sum())}; clusters (drugs)={d.drug.nunique()}; converged={r.mle_retvals['converged']}"
        out.extend(["=" * 100, title, f, note, t.round(4).to_string()])
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def prep(D, tier_col, year_col, bins):
    D["tier"] = pd.Categorical(D[tier_col], categories=IND)
    D["modality"] = D.drugType.map(MOD).fillna("other")
    D["area"] = D.area.fillna("other")
    D["yb"] = pd.cut(D[year_col], bins).astype(str)
    return D


def groups(D, cols):
    t = D.groupby(cols[0], observed=True).agg(
        programmes=("drug", "size"), sponsors=(cols[1], "nunique"), supported=("y", "sum"), share=("y", "mean")
    )
    t["share"] = (100 * t["share"]).round(2)
    return t.to_string()


crules, orules = corporate_rules(), owners_link.owner_classes()
P0 = pd.read_csv(f"{R}/programmes.csv.gz")
E0 = pd.read_csv(f"{R}/phase_entries.csv.gz")
P0["y"] = P0.gs_ante_first.fillna(False).astype(int)
E0["gs"] = E0.gs_ante.fillna(False).astype(int)
E0["adv"] = E0.advanced.astype(int)
out.append("Corporate and independent venture investors (exploratory; see the module docstring)")

# ---- A. private rounds -------------------------------------------------------------------------------------------
M = pd.read_csv(f"{R}/cb_link_review.csv")
A = M[M.decision.eq("accept")][["first_sponsor", "permalink"]].drop_duplicates()
inv = pd.read_csv(f"{CB}/investments.csv", dtype=str, encoding_errors="replace")
inv = inv[inv.funding_round_type.eq("venture") & inv.investor_permalink.fillna("").str.startswith("/organization/")]
inv = A.merge(inv, left_on="permalink", right_on="company_permalink")
inv["year"] = pd.to_datetime(inv.funded_at, errors="coerce").dt.year
inv["kind"] = [kind(str(n), crules) for n in inv.investor_name]
inv["cls"] = [owners_link.classify(str(n), orules) for n in inv.investor_name]
inv["corp"] = inv.kind.isin(CORP)
inv["pharma"] = inv.kind.isin(CORP[:2])
inv["found"] = inv.kind.eq("foundation-owned")
inv["indep"] = inv.cls.isin(["venture capital", "life-science crossover"]) & inv.kind.eq("")
rd = pd.read_csv(f"{CB}/rounds.csv", dtype=str, encoding_errors="replace")
rd = A.merge(rd[rd.funding_round_type.eq("venture")], left_on="permalink", right_on="company_permalink")
rd["year"] = pd.to_datetime(rd.funded_at, errors="coerce").dt.year
YEAR = {"round": rd.groupby("first_sponsor").year.min().to_dict()}
for k in ("corp", "pharma", "found", "indep"):
    YEAR[k] = inv[inv[k]].groupby("first_sponsor").year.min().to_dict()
names = inv[inv.corp | inv.found].groupby(["kind", "investor_name"]).first_sponsor.nunique().rename("sponsors")
out.append(
    f"\nA. PRIVATE ROUNDS. Sponsors with a venture round: {len(YEAR['round'])}; with a corporate investor: "
    f"{len(YEAR['corp'])} (a drug or medical-technology company: {len(YEAR['pharma'])}); with an independent fund: "
    f"{len(YEAR['indep'])}; with a foundation-owned investor: {len(YEAR['found'])}"
)
out.append("corporate and foundation-owned investors named in the venture rounds (sponsors backed):")
out.append(names.reset_index().sort_values(["kind", "sponsors"], ascending=[True, False]).to_string(index=False))

P = P0[P0.insight & P0.first_sponsor_tier.isin(IND) & P0.first_year.between(2001, 2016)].copy()
end_year = int(E0.entry_year.max())
E = E0[E0.insight & ~E0.prior_higher & E0.sponsor_tier.isin(IND) & E0.entry_year.between(2001, min(2016, end_year - 6))].copy()  # fmt: skip
for D, name_col, year_col, tier_col in ((P, "first_sponsor", "first_year", "first_sponsor_tier"), (E, "lead_sponsor", "entry_year", "sponsor_tier")):  # fmt: skip
    prep(D, tier_col, year_col, [2000, 2005, 2010, 2016])
    for k, tab in YEAR.items():
        D[k] = (D[name_col].map(tab) < D[year_col]).fillna(False).astype(int)
    D["fin"] = pd.Categorical(
        np.select(
            [D.corp.eq(1), D.indep.eq(1), D["round"].eq(1)], [A_GROUPS[3], A_GROUPS[2], A_GROUPS[1]], A_GROUPS[0]
        ),
        categories=A_GROUPS,
    )
    D["fin_f"] = pd.Categorical(  # sensitivity: foundation-owned investors counted as corporate
        np.select(
            [(D.corp | D.found).eq(1), D.indep.eq(1), D["round"].eq(1)],
            [A_GROUPS[3], A_GROUPS[2], A_GROUPS[1]],
            A_GROUPS[0],
        ),
        categories=A_GROUPS,
    )
out.append(f"\nprogrammes (insight indications, first trial 2001-2016, non-top-20 industry): {len(P)}")
out.append(groups(P, ("fin", "first_sponsor")))
base_p = "C(tier) + C(yb) + C(area) + C(modality)"
base_e = "C(phase) + " + base_p
is_fin = lambda i: i.startswith("C(fin)")  # noqa: E731
fit(f"y ~ C(fin) + {base_p}", P, "A1. H1: ex-ante support ~ investors before the first trial (reference: no venture round)", is_fin)  # fmt: skip
N = P[P.fin.isin(A_GROUPS[2:])].copy()
N["corp_inv"] = N.fin.eq(A_GROUPS[3]).astype(int)
fit(f"y ~ corp_inv + {base_p}", N, "A2. H1, programmes with a named investor: corporate investor against independent funds only", lambda i: i == "corp_inv")  # fmt: skip
N["pharma_inv"] = N.pharma
fit(f"y ~ pharma_inv + {base_p}", N, "A3. as A2, drug and medical-technology companies only", lambda i: i == "pharma_inv")  # fmt: skip
F = P.assign(fin=P.fin_f)
fit(f"y ~ C(fin) + {base_p}", F, "A4. as A1, foundation-owned investors counted as corporate", is_fin)
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ C(fin) + {base_p}", P2, "A5. as A1 [dated OT evidence]", is_fin)
out.append("=" * 100 + f"\nphase entries 2001-{int(E.entry_year.max())} (non-top-20 industry): {len(E)}")
out.append(E.groupby("fin", observed=True).agg(entries=("drug", "size"), advanced=("adv", "mean"), gs=("gs", "mean")).round(4).to_string())  # fmt: skip
fit(f"adv ~ C(fin) + gs + {base_e}", E, "A6. advancement ~ investors before the entry + ex-ante support", lambda i: is_fin(i) or i == "gs")  # fmt: skip
NE = E[E.fin.isin(A_GROUPS[2:])].copy()
NE["corp_inv"] = NE.fin.eq(A_GROUPS[3]).astype(int)
fit(f"adv ~ corp_inv + gs + {base_e}", NE, "A7. advancement, entries with a named investor: corporate investor against independent funds only", lambda i: i in ("corp_inv", "gs"))  # fmt: skip

# ---- B. owners of public sponsors ---------------------------------------------------------------------------------
o = pd.read_csv(f"{R}/owners_pairs.csv.gz")
ow = pd.read_csv(f"{R}/owners_sponsors.csv", dtype={"norm": str})
o["kind"] = [kind(str(n), crules) for n in o.owner_name]
o["corp"] = o.kind.eq(CORP[0])
o["found"] = o.kind.eq("foundation-owned")
o["vcf"] = o.owner_class.eq("venture capital") & o.kind.eq("")
CORP_O, VC_O, FOUND_O = set(o[o.corp].norm), set(o[o.vcf].norm), set(o[o.found].norm)
PUBLIC = set(ow[ow.is_registrant.astype(bool)].norm)
PUBLIC_YEAR = dict(zip(ow.norm, pd.to_numeric(ow.registrant_first_year, errors="coerce")))
o["year"] = pd.to_datetime(o.first_date, errors="coerce").dt.year
CORP_Y, VC_Y = o[o.corp].groupby("norm").year.min().to_dict(), o[o.vcf].groupby("norm").year.min().to_dict()
onames = o[o.corp].groupby("owner_name").norm.nunique().rename("n").reset_index().sort_values(["n", "owner_name"], ascending=[False, True]).set_index("owner_name").n  # fmt: skip
out.append(
    f"\nB. OWNERS OF PUBLIC SPONSORS. Registrants: {len(PUBLIC)}; with a large drug company or its venture arm among "
    f"the owners: {len(CORP_O)}; with a venture fund: {len(VC_O)}; with both: {len(CORP_O & VC_O)}; with a "
    f"foundation-owned investor: {len(FOUND_O)}"
)
out.append(
    "corporate owners named with the most sponsors: " + "; ".join(f"{n} ({c})" for n, c in onames.head(15).items())
)
P = P0[P0.insight & P0.first_sponsor_tier.isin(IND) & P0.first_year.ge(2001)].copy()
E = E0[E0.insight & ~E0.prior_higher & E0.sponsor_tier.isin(IND) & E0.entry_year.between(2001, end_year - 6)].copy()
for D, name_col, year_col, tier_col in ((P, "first_sponsor", "first_year", "first_sponsor_tier"), (E, "lead_sponsor", "entry_year", "sponsor_tier")):  # fmt: skip
    prep(D, tier_col, year_col, [2000, 2005, 2010, 2015, 2020, 2100])
    n = D[name_col].map(rq2_stops.norm_sponsor)
    D["public"] = n.isin(PUBLIC).astype(int)
    D["own"] = pd.Categorical(np.select([n.isin(CORP_O), n.isin(VC_O)], [B_GROUPS[2], B_GROUPS[1]], B_GROUPS[0]), categories=B_GROUPS)  # fmt: skip
    D["sp"] = n
    D["public_at"] = (n.map(PUBLIC_YEAR) <= D[year_col]).fillna(False).astype(int)
    D["own_d"] = pd.Categorical(
        np.select(
            [(n.map(CORP_Y) <= D[year_col]).fillna(False), (n.map(VC_Y) <= D[year_col]).fillna(False)],
            [B_GROUPS[2], B_GROUPS[1]],
            B_GROUPS[0],
        ),
        categories=B_GROUPS,
    )
out.append(f"\nprogrammes (insight indications, first trial 2001+, non-top-20 industry): {len(P)}; of public sponsors: {int(P.public.sum())}")  # fmt: skip
PP, EP = P[P.public.eq(1)].copy(), E[E.public.eq(1)].copy()
out.append("programmes of public sponsors:")
out.append(groups(PP, ("own", "sp")))
is_own = lambda i: i.startswith("C(own)")  # noqa: E731
fit(f"y ~ C(own) + {base_p}", PP, "B1. H1, public sponsors: ex-ante support ~ owners (reference: no venture or corporate owner)", is_own)  # fmt: skip
V = PP[PP.own.isin(B_GROUPS[1:])].copy()
V["corp_owner"] = V.own.eq(B_GROUPS[2]).astype(int)
fit(f"y ~ corp_owner + {base_p}", V, "B2. H1, sponsors with a venture or corporate owner: corporate owner against venture funds only", lambda i: i == "corp_owner")  # fmt: skip
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    V2 = V.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    V2["y"] = V2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ corp_owner + {base_p}", V2, "B3. as B2 [dated OT evidence]", lambda i: i == "corp_owner")
out.append("=" * 100 + f"\nphase entries of public sponsors: {len(EP)}")
out.append(EP.groupby("own", observed=True).agg(entries=("drug", "size"), advanced=("adv", "mean"), gs=("gs", "mean")).round(4).to_string())  # fmt: skip
fit(f"adv ~ C(own) + gs + {base_e}", EP, "B4. advancement, public sponsors ~ owners + ex-ante support", lambda i: is_own(i) or i == "gs")  # fmt: skip
VE = EP[EP.own.isin(B_GROUPS[1:])].copy()
VE["corp_owner"] = VE.own.eq(B_GROUPS[2]).astype(int)
fit(f"adv ~ corp_owner + gs + {base_e}", VE, "B5. advancement, sponsors with a venture or corporate owner: corporate owner against venture funds only", lambda i: i in ("corp_owner", "gs"))  # fmt: skip

PD, ED = P[P.public_at.eq(1)].assign(own=lambda d: d.own_d), E[E.public_at.eq(1)].assign(own=lambda d: d.own_d)
out.append(
    "=" * 100 + f"\nprogrammes of sponsors public by the year of the first trial, owners dated by that year: {len(PD)}"
)
out.append(groups(PD, ("own", "sp")))
fit(
    f"y ~ C(own) + {base_p}",
    PD,
    "B6. H1, sponsors public by the first trial: ex-ante support ~ owners by that year",
    is_own,
)
VD = PD[PD.own.isin(B_GROUPS[1:])].copy()
VD["corp_owner"] = VD.own.eq(B_GROUPS[2]).astype(int)
fit(
    f"y ~ corp_owner + {base_p}",
    VD,
    "B7. as B6, corporate owner against venture funds only",
    lambda i: i == "corp_owner",
)
fit(f"adv ~ C(own) + gs + {base_e}", ED, "B8. advancement, sponsors public by the entry ~ owners by that year + ex-ante support", lambda i: is_own(i) or i == "gs")  # fmt: skip

S = pd.DataFrame({"first_sponsor": sorted(YEAR["round"])})
for k in ("round", "indep", "corp", "pharma", "found"):
    S[f"first_{k}_year"] = S.first_sponsor.map(YEAR[k])
S["corporate_investors"] = S.first_sponsor.map(
    inv[inv.corp].groupby("first_sponsor").investor_name.agg(lambda x: "; ".join(sorted(set(x))))
)
S.to_csv(f"{R}/cvc_sponsors.csv", index=False)
open(f"{R}/cvc_models.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
