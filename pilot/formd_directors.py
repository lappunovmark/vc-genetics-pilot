"""Venture investors on the board: directors named in Form D filings who also manage venture-capital funds. Exploratory.

Usage: python pilot/formd_directors.py RESULTS_DIR FORMD_DIR [RITTER_RESULTS_DIR]
FORMD_DIR holds the three files of fetch_formd_people.py; RESULTS_DIR the pilot results (after formd_link.py).

Why: Form D does not name investors, but it names the issuer's directors, and a venture investor usually takes a
board seat. Venture-capital funds file Form D too (pooled investment fund, type venture capital) and name the people
who manage them. A director of a sponsor who is also named as a manager of a venture fund marks venture backing at
the date of the sponsor's filing, for private sponsors, from SEC data only.

Person key: first word of the first name + last name, lower case, without suffixes. Rows that name an entity (a
general partner LLC, a fund administrator) are dropped from the fund side.
Markers of a sponsor's filing:
  vc_director   a director who is not an executive officer of the issuer and whose key is among the venture-fund
                managers
  vc_address    a related person whose address is care of an investor classified as venture capital or life-science
                crossover by pilot/investor_classes.tsv ("c/o Atlas Venture ...")
  vc_board      either of the two
A sponsor's filings are those of its Form D issuers (CIKs of results/formd_sponsor_offerings.csv.gz).
Two people can share a name: the share of executive officers who are not directors and still match a fund manager is
printed as a rough bound on chance matches, and the marker is checked against Jay Ritter's venture flag (sponsors
with a US IPO) and against Crunchbase venture rounds.
Sample of the models: as formd_models.py (first trial after 2009). Writes formd_directors.txt,
formd_directors_sponsors.csv.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import formd_directors_lib as fdl
import rq2_stops
from pooling import pool_sparse

R, FD = sys.argv[1], sys.argv[2]
XR = sys.argv[3] if len(sys.argv) > 3 else R
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
out = []


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


def compare(name, ours, ref):
    ours, ref = np.asarray(ours, bool), np.asarray(ref, bool)
    tp, fp, fn, tn = (
        int((ours & ref).sum()),
        int((ours & ~ref).sum()),
        int((~ours & ref).sum()),
        int((~ours & ~ref).sum()),
    )
    out.append(
        f"  {name}: sponsors {len(ours)}; both {tp}, marker only {fp}, reference only {fn}, neither {tn}; of the "
        f"reference's venture-backed sponsors the marker finds {tp / (tp + fn) if tp + fn else float('nan'):.3f}; of the "
        f"marker's sponsors the reference confirms {tp / (tp + fp) if tp + fp else float('nan'):.3f}"
    )


pb, pv = fdl.people(FD)
mg = pv[pv.key.notna()]
MANAGERS = set(mg.key)
n_funds = mg.groupby("key").CIK.nunique()

out.append(
    "Venture investors on the board, from the people named in Form D filings (exploratory; see the module docstring)"
)
out.append(
    f"venture-fund filings name {len(pv)} related persons, {int(pv.key.notna().sum())} of them natural persons: "
    f"{len(MANAGERS)} distinct names, managing funds of a median of {int(n_funds.median())} issuers each"
)
people = pb[pb.key.notna()]
only_exec = people[people.is_exec & ~people.is_dir].drop_duplicates(["CIK", "key"])
outside = people[people.is_dir & ~people.is_exec].drop_duplicates(["CIK", "key"])
out.append(
    f"biopharma filings: {pb.ACCESSIONNUMBER.nunique()} of {pb.CIK.nunique()} issuers, {len(pb)} person rows; directors who "
    f"are not executive officers: {len(outside)} issuer-person pairs, {outside.match.mean():.3f} of them match a "
    f"venture-fund manager; executive officers who are not directors: {len(only_exec)} pairs, {only_exec.match.mean():.3f} match"
)
f = fdl.filings(FD, pb).set_index("ACCESSIONNUMBER")
out.append(
    f"filings with a venture director: {f.vc_director.mean():.3f}; with a venture address: {f.vc_address.mean():.3f}; "
    f"with either: {f.vc_board.mean():.3f}"
)

# sponsors
so = pd.read_csv(f"{R}/formd_sponsor_offerings.csv.gz", dtype=str)
so["CIK"] = so.CIK.str.lstrip("0")
sc = so[["norm", "CIK"]].drop_duplicates()
sf = sc.merge(f.reset_index(), on="CIK")
S = sf.groupby("norm").agg(n_filings=("ACCESSIONNUMBER", "nunique"), first_filing_year=("year", "min")).reset_index()
for k in ("vc_director", "vc_address", "vc_board"):
    S[f"first_{k}_year"] = S.norm.map(sf[sf[k]].groupby("norm").year.min())
names = sf.merge(pb[pb.vc_director][["ACCESSIONNUMBER", "FIRSTNAME", "LASTNAME"]], on="ACCESSIONNUMBER")
names["person"] = names.FIRSTNAME.str.strip() + " " + names.LASTNAME.str.strip()
S["vc_directors"] = S.norm.map(names.groupby("norm").person.agg(lambda x: "; ".join(sorted(set(x)))))
S.to_csv(f"{R}/formd_directors_sponsors.csv", index=False)
out.append(
    f"sponsors with Form D filings that name people: {len(S)}; with a venture director: "
    f"{int(S.first_vc_director_year.notna().sum())}; with a venture address: {int(S.first_vc_address_year.notna().sum())}; "
    f"with either: {int(S.first_vc_board_year.notna().sum())}"
)
BOARD = dict(zip(S.norm, S.first_vc_board_year))
DIRY = dict(zip(S.norm, S.first_vc_director_year))
FILED = dict(zip(S.norm, S.first_filing_year))

# 1. the marker against outside flags
out.append("\n1. The board marker against outside venture flags (sponsors with Form D filings that name people)")
if os.path.exists(f"{XR}/ritter_sponsors.csv"):
    rt = pd.read_csv(f"{XR}/ritter_sponsors.csv")
    rt["norm"] = rt.first_sponsor.map(rq2_stops.norm_sponsor)
    x = rt.drop_duplicates("norm").merge(S, on="norm")
    x = x[x.first_filing_year.le(x.ipo_year)]  # the sponsor filed a Form D before going public
    compare(
        "venture director or address by the IPO year, against Ritter's flag",
        x.first_vc_board_year.le(x.ipo_year),
        x.ritter_vc,
    )
    compare("venture director only, against Ritter's flag", x.first_vc_director_year.le(x.ipo_year), x.ritter_vc)
if os.path.exists(f"{XR}/cb_sponsors.csv"):
    cb = pd.read_csv(f"{XR}/cb_sponsors.csv")
    cb["norm"] = cb.first_sponsor.map(rq2_stops.norm_sponsor)
    x = cb.drop_duplicates("norm").merge(S, on="norm")
    x = x[x.first_filing_year.le(2015)]
    compare("venture director or address by 2015, against a Crunchbase venture round by 2015", x.first_vc_board_year.le(2015), x.first_vc_round_year.le(2015))  # fmt: skip

# 2. models
P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.gt(FIRST_DATA_YEAR)].copy()
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[
    E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_DATA_YEAR + 1, end_year - 6)
].copy()
for T, name_col, year_col in ((P, "first_sponsor", "first_year"), (E, "lead_sponsor", "entry_year")):
    n = T[name_col].map(rq2_stops.norm_sponsor)
    T["filer"] = (n.map(FILED) < T[year_col]).fillna(False).astype(int)
    T["board"] = (n.map(BOARD) < T[year_col]).fillna(False).astype(int)
    T["vcdir"] = (n.map(DIRY) < T[year_col]).fillna(False).astype(int)
    T["modality"] = T.drugType.map(MOD).fillna("other")
    T["area"] = T.area.fillna("other")
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
P["yb"] = pd.cut(P.first_year, [2009, 2013, 2017, 2021, 2100]).astype(str)
E["yb"] = pd.cut(E.entry_year, [2009, 2013, 2017, 2030]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)
out.append(f"\n2. Programmes (insight indications, first trial after {FIRST_DATA_YEAR}, non-top-20 industry): {len(P)}")
out.append("ex-ante support by prior Form D with named people x venture investor on the board before the first trial:")
out.append(
    P.groupby(["filer", "board"])
    .agg(n=("drug", "size"), sponsors=("first_sponsor", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)  # fmt: skip
base_p = "C(tier) + C(yb) + C(area) + C(modality)"
fit(
    f"y ~ board + {base_p}",
    P,
    "H1: ex-ante support ~ venture investor on the board before the first trial (all)",
    ("board",),
)
PF = P[P.filer.eq(1)].copy()
fit(f"y ~ board + {base_p}", PF, "H1, sponsors with a prior Form D only: ~ venture investor on the board", ("board",))
fit(
    f"y ~ vcdir + {base_p}",
    PF,
    "H1, sponsors with a prior Form D only: ~ venture director (name match alone)",
    ("vcdir",),
)
fit("y ~ board + C(yb) + C(area) + C(modality)", P[P.first_sponsor_tier.eq(IND[2])].copy(), "H1, small sponsors only: ~ venture investor on the board", ("board",))  # fmt: skip
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ board + {base_p}", P2, "H1 [dated OT evidence]: ~ venture investor on the board (all)", ("board",))
    fit(
        f"y ~ board + {base_p}",
        P2[P2.filer.eq(1)].copy(),
        "H1 [dated OT evidence], sponsors with a prior Form D only",
        ("board",),
    )
E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
out.append("=" * 100 + f"\nPhase entries {FIRST_DATA_YEAR + 1}-{end_year - 6} (non-top-20 industry): {len(E)}")
out.append(
    E.groupby(["filer", "board"]).agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string()
)
base_e = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(
    f"adv ~ board + gs + {base_e}",
    E,
    "Advancement ~ venture investor on the board + ex-ante support (all)",
    ("board", "gs"),
)
fit(
    f"adv ~ board + gs + {base_e}",
    E[E.filer.eq(1)].copy(),
    "Advancement, sponsors with a prior Form D only",
    ("board", "gs"),
)
open(f"{R}/formd_directors.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
