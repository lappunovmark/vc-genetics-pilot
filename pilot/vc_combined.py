"""One venture flag from four sources, and the selection model with it. Exploratory.

Usage: python pilot/vc_combined.py RESULTS_DIR
(after owners_link.py, cb_models.py, ritter_models.py and formd_directors.py; a source whose file is missing is skipped)
A sponsor (non-top-20 industry) is venture-backed if at least one source says so:
  owners     a venture-capital fund among its owners in Schedules 13D/13G (owners_sponsors.csv)
  ipo        venture-backed at its US IPO in Jay Ritter's list (ritter_sponsors.csv)
  round      a round of type "venture" in the Crunchbase export of December 2015 (cb_sponsors.csv)
  board      a venture investor on its board in a Form D filing (formd_directors_sponsors.csv)
and it is "seen" if at least one source could have shown it: an EDGAR registrant, a US IPO in the list, a company
found in Crunchbase, or a Form D issuer whose filings name people. The flag is a property of the sponsor and is not
dated to the trial. Sponsors that are not seen are not known to be without venture money, so the comparison among
seen sponsors is printed next to the comparison with all other sponsors. Writes vc_combined.txt.
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


def table(name):
    path = f"{R}/{name}"
    return pd.read_csv(path, dtype={"norm": str}) if os.path.exists(path) else None


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
        head = (
            f"N={int(r.nobs)}; events={ev}; clusters (drugs)={d.drug.nunique()}; converged={r.mle_retvals['converged']}"
        )
        out.extend(["=" * 100, title, f, head, t.round(5).to_string()])
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.ge(FIRST_YEAR)].copy()
P["norm"] = P.first_sponsor.map(rq2_stops.norm_sponsor)
VC, SEEN = {}, {}
ow, rt, cb, bd = (
    table(n) for n in ("owners_sponsors.csv", "ritter_sponsors.csv", "cb_sponsors.csv", "formd_directors_sponsors.csv")
)
if ow is not None:
    VC["owners"], SEEN["owners"] = set(ow[ow.vc_backed.astype(bool)].norm), set(ow[ow.is_registrant.astype(bool)].norm)
if rt is not None:
    n = rt.first_sponsor.map(rq2_stops.norm_sponsor)
    VC["ipo"], SEEN["ipo"] = set(n[rt.ritter_vc.astype(bool)]), set(n)
if cb is not None:
    n = cb.first_sponsor.map(rq2_stops.norm_sponsor)
    VC["round"], SEEN["round"] = set(n[cb.first_vc_round_year.notna()]), set(n)
if bd is not None:
    VC["board"], SEEN["board"] = set(bd[bd.first_vc_board_year.notna()].norm), set(bd.norm)
for k in VC:
    P[f"vc_{k}"] = P.norm.isin(VC[k]).astype(int)
    P[f"seen_{k}"] = P.norm.isin(SEEN[k]).astype(int)
P["vc_any"] = P[[f"vc_{k}" for k in VC]].max(axis=1)
P["n_sources"] = P[[f"vc_{k}" for k in VC]].sum(axis=1)
P["vc_two"] = P.n_sources.ge(2).astype(int)
P["seen"] = P[[f"seen_{k}" for k in VC]].max(axis=1)
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
P["modality"] = P.drugType.map(MOD).fillna("other")
P["area"] = P.area.fillna("other")
P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)
sp = P.drop_duplicates("norm")
out.append("One venture flag from four sources (exploratory; see the module docstring)")
out.append(
    f"sponsors (non-top-20 industry, first trial {FIRST_YEAR}+): {len(sp)}; seen in at least one source: {int(sp.seen.sum())}; "
    f"venture-backed by at least one: {int(sp.vc_any.sum())}; by at least two: {int(sp.vc_two.sum())}"
)
out.append(
    "by source (sponsors seen / venture-backed): "
    + "; ".join(f"{k} {int(sp[f'seen_{k}'].sum())} / {int(sp[f'vc_{k}'].sum())}" for k in VC)
)
out.append(f"\nProgrammes (insight indications, first trial {FIRST_YEAR}+): {len(P)}")
out.append(
    P.groupby(["seen", "vc_any"]).agg(n=("drug", "size"), sponsors=("norm", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean")).round(4).to_string()
)  # fmt: skip
base = "C(tier) + C(yb) + C(area) + C(modality)"
PS = P[P.seen.eq(1)].copy()
fit(
    f"y ~ vc_any + {base}",
    P,
    "H1: ex-ante support ~ venture-backed by any source (all non-top-20 industry)",
    ("vc_any",),
)
fit(f"y ~ vc_any + {base}", PS, "H1, sponsors seen in at least one source: ~ venture-backed by any source", ("vc_any",))
fit(
    f"y ~ vc_two + {base}",
    PS,
    "H1, sponsors seen in at least one source: ~ venture-backed by at least two sources",
    ("vc_two",),
)
fit("y ~ vc_any + C(yb) + C(area) + C(modality)", P[P.first_sponsor_tier.eq(IND[2])].copy(), "H1, small sponsors only: ~ venture-backed by any source", ("vc_any",))  # fmt: skip
fit("y ~ vc_any + C(yb) + C(area) + C(modality)", PS[PS.first_sponsor_tier.eq(IND[2])].copy(), "H1, small sponsors seen in at least one source", ("vc_any",))  # fmt: skip
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    fit(
        f"y ~ vc_any + {base}",
        P2,
        "H1 [dated OT evidence]: ~ venture-backed by any source (all non-top-20 industry)",
        ("vc_any",),
    )
    fit(
        f"y ~ vc_any + {base}",
        P2[P2.seen.eq(1)].copy(),
        "H1 [dated OT evidence], sponsors seen in at least one source",
        ("vc_any",),
    )
open(f"{R}/vc_combined.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
