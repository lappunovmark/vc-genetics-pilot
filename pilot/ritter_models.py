"""Venture backing at the IPO (Jay Ritter's list of US IPOs, 1975-2025) and genetic support. Exploratory.

Usage: python pilot/ritter_models.py RESULTS_DIR IPO-age.xlsx [CRUNCHBASE_RESULTS_DIR]
IPO-age.xlsx: "Founding dates for IPOs from 1975-2025" of Jay R. Ritter (University of Florida), version of
19 January 2026, https://site.warrington.ufl.edu/ritter/ipo-data/ . One row per US IPO with the offer date, the
company name and VC = 1 for a venture-capital-backed IPO, 2 for the subset he calls growth-capital-backed, 0 otherwise.

Why: the pilot's own venture markers are built from filings (Schedules 13D/13G) or from a crowd-sourced database
(Crunchbase). Ritter's flag is compiled by hand from prospectuses and commercial sources and is the standard one in
the IPO literature, so it serves two purposes: to check the pilot's markers and to repeat the selection model with
an outside definition of venture backing.

Linkage: sponsor names (non-top-20 industry) are matched to IPO names on the normalised name
(rq2_stops.norm_sponsor). A candidate is accepted when the names are also equal once only legal forms are removed
(sbir_link.strict) or when the IPO name has a life-science word; of several IPOs under one name the one closest in
time to the sponsor's first trial is kept. Hand corrections, if any, are read from pilot/ritter_decisions.csv.
The flag is known only for sponsors that went public in the US, so every comparison is among those sponsors. The flag is combined
with the pilot's other venture markers in vc_combined.py.
Writes ritter_link_review.csv, ritter_sponsors.csv, ritter_models.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
import sbir_link
from pooling import pool_sparse

R, XLSX = sys.argv[1], sys.argv[2]
CBR = sys.argv[3] if len(sys.argv) > 3 else R
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
LIFE = r"bio|pharm|therap|gene|genom|onc|medic|scienc|immun|neuro|vaccin|cell|health|diagnos|labs?\b|rx\b"
DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ritter_decisions.csv")
out = []


def ipos(path):
    d = pd.read_excel(path, dtype=str).iloc[:, :12]
    d.columns = [
        "date",
        "name",
        "ticker",
        "cusip",
        "adr",
        "vc",
        "dual",
        "shares",
        "internet",
        "perm",
        "founding",
        "rollup",
    ]
    d = d[d.name.notna() & d.date.str.fullmatch(r"\d{8}")].copy()
    d["ipo_year"] = d.date.str[:4].astype(int)
    d["vc"] = pd.to_numeric(d.vc, errors="coerce")
    d = d[d.vc.isin([0, 1, 2])]  # 9 and "." are missing values in the file
    d["norm"] = d.name.map(rq2_stops.norm_sponsor)
    d["strict"] = d.name.map(sbir_link.strict)
    return d[d.norm.notna()]


def link(sp, d):
    """sp: first_sponsor, first (year of the sponsor's first trial). Returns every candidate with its decision."""
    s = sp.copy()
    s["norm"] = s.first_sponsor.map(rq2_stops.norm_sponsor)
    s["strict_sponsor"] = s.first_sponsor.map(sbir_link.strict)
    m = s[s.norm.notna()].merge(d, on="norm")
    same = m.strict_sponsor.eq(m.strict)
    life = m.name.str.contains(LIFE, case=False)
    m["decision"] = np.where(same | life, "accept", "reject")
    m["reason"] = np.select([same, life], ["same name", "life-science word"], "name differs, no life-science word")
    if os.path.exists(DECISIONS):
        dec = pd.read_csv(DECISIONS, dtype=str).set_index(["first_sponsor", "name", "date"])
        key = list(zip(m.first_sponsor, m.name, m.date))
        hit = [k in dec.index for k in key]
        m.loc[hit, "decision"] = [dec.loc[k, "decision"] for k, h in zip(key, hit) if h]
        m.loc[hit, "reason"] = ["hand review: " + dec.loc[k, "reason"] for k, h in zip(key, hit) if h]
    # several accepted IPOs under one name: keep the one closest in time to the sponsor's first trial
    m["gap"] = (m.ipo_year - m["first"]).abs()
    acc = m[m.decision.eq("accept")].sort_values(["first_sponsor", "gap", "date"])
    extra = acc[acc.duplicated("first_sponsor")].index
    m.loc[extra, "decision"] = "reject"
    m.loc[extra, "reason"] = "another IPO under the same name is closer in time"
    cols = ["first_sponsor", "first", "name", "date", "ticker", "vc", "founding", "decision", "reason"]
    return m[cols].sort_values(["first_sponsor", "date"]).reset_index(drop=True)


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def compare(name, ours, ritter):
    """Agreement of one of the pilot's markers with Ritter's flag on the sponsors where both are defined."""
    ours, ritter = np.asarray(ours, bool), np.asarray(ritter, bool)
    tp, fp = int((ours & ritter).sum()), int((ours & ~ritter).sum())
    fn, tn = int((~ours & ritter).sum()), int((~ours & ~ritter).sum())
    n = len(ours)
    out.append(
        f"  {name}: sponsors {n}; both {tp}, marker only {fp}, Ritter only {fn}, neither {tn}; agreement "
        f"{(tp + tn) / n:.3f}, kappa {kappa(ours, ritter):.3f}; of Ritter's venture-backed IPOs the marker finds "
        f"{tp / (tp + fn):.3f}; of the marker's sponsors Ritter confirms {tp / (tp + fp) if tp + fp else float('nan'):.3f}"
    )


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


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.ge(FIRST_YEAR)].copy()
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_YEAR, end_year - 6)].copy()
names = pd.concat(
    [P[["first_sponsor", "first_year"]], E[["lead_sponsor", "entry_year"]].set_axis(["first_sponsor", "first_year"], axis=1)]
)  # fmt: skip
SP = names.groupby("first_sponsor").first_year.min().rename("first").reset_index()
D = ipos(XLSX)
M = link(SP, D)
M.to_csv(f"{R}/ritter_link_review.csv", index=False)
A = M[M.decision.eq("accept")].copy()
A["ritter_vc"] = A.vc.isin([1, 2])
A["ipo_year"] = A.date.str[:4].astype(int)
A["norm"] = A.first_sponsor.map(rq2_stops.norm_sponsor)
A[["first_sponsor", "name", "date", "ipo_year", "vc", "ritter_vc", "founding"]].to_csv(
    f"{R}/ritter_sponsors.csv", index=False
)
IPO_YEAR, RVC, RVC1 = dict(zip(A.first_sponsor, A.ipo_year)), dict(zip(A.first_sponsor, A.ritter_vc)), dict(zip(A.first_sponsor, A.vc.eq(1)))  # fmt: skip

out.append(
    "Venture backing at the IPO from Jay Ritter's list of US IPOs 1975-2025 (exploratory; see the module docstring)"
)
out.append(
    f"IPOs in the file with a venture flag: {len(D)} (venture-backed {int(D.vc.eq(1).sum())}, growth capital "
    f"{int(D.vc.eq(2).sum())}); sponsor names (non-top-20 industry, first trial {FIRST_YEAR}+): {len(SP)}; candidate "
    f"name matches: {len(M)}; accepted: {len(A)} (same name {int(A.reason.eq('same name').sum())}, life-science word "
    f"{int(A.reason.eq('life-science word').sum())}, by hand {int(A.reason.str.startswith('hand review').sum())}); "
    f"rejected: {int(M.decision.eq('reject').sum())}"
)
out.append(
    f"sponsors with a US IPO in the list: {len(A)}; venture-backed at the IPO: {int(A.ritter_vc.sum())} "
    f"(of them growth capital {int(A.vc.eq(2).sum())}); IPO years {A.ipo_year.min()}-{A.ipo_year.max()}"
)

# 1. the pilot's markers against Ritter's flag
out.append("\n1. The pilot's venture markers against Ritter's flag (sponsors where both are defined)")
if os.path.exists(f"{R}/owners_sponsors.csv"):
    ow = pd.read_csv(f"{R}/owners_sponsors.csv", dtype={"norm": str})
    ow = ow[ow.is_registrant.astype(bool)]
    x = A.merge(ow[["norm", "vc_backed", "first_vc_year", "registrant_first_year"]], on="norm")
    x = x.drop_duplicates("first_sponsor")
    at_ipo = x.vc_backed.astype(bool) & (pd.to_numeric(x.first_vc_year, errors="coerce") <= x.ipo_year + 1)
    out.append(f"  sponsors with a Ritter IPO that are also EDGAR registrants: {len(x)}")
    compare("venture owner in Schedules 13D/13G, any time", x.vc_backed.astype(bool), x.ritter_vc)
    compare("venture owner in Schedules 13D/13G by the year after the IPO", at_ipo, x.ritter_vc)
    y = x[x.ipo_year.ge(2001)]
    at_ipo_y = y.vc_backed.astype(bool) & (pd.to_numeric(y.first_vc_year, errors="coerce") <= y.ipo_year + 1)
    compare("the same, IPOs of 2001 or later (the window of the EDGAR index)", at_ipo_y, y.ritter_vc)
if os.path.exists(f"{CBR}/cb_sponsors.csv"):
    cb = pd.read_csv(f"{CBR}/cb_sponsors.csv")
    x = A.merge(cb[["first_sponsor", "first_vc_round_year"]], on="first_sponsor")
    x = x[x.ipo_year.between(2001, 2015)]  # Crunchbase rounds are observed to December 2015
    out.append(f"  sponsors with a Ritter IPO in 2001-2015 that are also found in Crunchbase: {len(x)}")
    compare(
        "Crunchbase venture round dated no later than the IPO year", x.first_vc_round_year.le(x.ipo_year), x.ritter_vc
    )

# 2. selection and advancement among sponsors that went public in the US
for T, name_col, year_col in ((P, "first_sponsor", "first_year"), (E, "lead_sponsor", "entry_year")):
    T["ipo"] = T[name_col].isin(IPO_YEAR).astype(int)
    T["rvc"] = T[name_col].map(RVC).fillna(False).astype(int)
    T["rvc1"] = T[name_col].map(RVC1).fillna(False).astype(int)
    T["before_ipo"] = (T[year_col] <= T[name_col].map(IPO_YEAR)).fillna(False).astype(int)
    T["modality"] = T.drugType.map(MOD).fillna("other")
    T["area"] = T.area.fillna("other")
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
E["yb"] = pd.cut(E.entry_year, [2000, 2005, 2010, 2015, 2030]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)
out.append(f"\n2. Programmes (insight indications, first trial {FIRST_YEAR}+, non-top-20 industry): {len(P)}")
out.append("ex-ante support by US IPO x venture-backed at the IPO:")
out.append(
    P.groupby(["ipo", "rvc"])
    .agg(n=("drug", "size"), sponsors=("first_sponsor", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)  # fmt: skip
base_p = "C(tier) + C(yb) + C(area) + C(modality)"
PI = P[P.ipo.eq(1)].copy()
fit(f"y ~ rvc + {base_p}", PI, "H1, sponsors with a US IPO: ex-ante support ~ venture-backed at the IPO", ("rvc",))
fit(f"y ~ rvc1 + {base_p}", PI, "H1, sponsors with a US IPO: ~ venture-backed, growth capital not counted", ("rvc1",))
fit(
    f"y ~ rvc + {base_p}", PI[PI.before_ipo.eq(1)].copy(), "H1, programmes started no later than the IPO year", ("rvc",)
)
fit(f"y ~ rvc + {base_p}", PI[PI.before_ipo.eq(0)].copy(), "H1, programmes started after the IPO year", ("rvc",))
fit(f"y ~ rvc + ipo + {base_p}", P, "H1, all non-top-20 industry: ~ venture-backed at the IPO + US IPO", ("rvc", "ipo"))
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = PI.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(
        f"y ~ rvc + {base_p}",
        P2,
        "H1 [dated OT evidence], sponsors with a US IPO: ~ venture-backed at the IPO",
        ("rvc",),
    )

E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
EI = E[E.ipo.eq(1)].copy()
out.append("=" * 100 + f"\nPhase entries {FIRST_YEAR}-{end_year - 6} of sponsors with a US IPO: {len(EI)}")
out.append(EI.groupby("rvc").agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string())
base_e = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ rvc + gs + {base_e}", EI, "Advancement, sponsors with a US IPO ~ venture-backed at the IPO + ex-ante support", ("rvc", "gs"))  # fmt: skip
fit(
    f"adv ~ rvc * gs + {base_e}",
    EI,
    "Advancement ~ venture-backed at the IPO x ex-ante support",
    ("rvc", "gs", "rvc:gs"),
)
open(f"{R}/ritter_models.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
