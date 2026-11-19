"""Investors named in IPO prospectuses and genetic support (plan: docs/plan_ipo_prospectus.md).

Usage: python pilot/ipo_models.py RESULTS_DIR IPO_DIR
(RESULTS_DIR holds programmes.csv.gz, phase_entries.csv.gz and ipo_holders.csv of ipo_holders.py, and, if present,
gs_ot_programmes.csv.gz, ritter_sponsors.csv and owners_sponsors.csv; IPO_DIR holds ipo_prospectus_index.csv)

Sample: IPO prospectuses (form 424B4) filed under the sponsor's own name whose table of principal stockholders was
read. A holder counts if it holds 5% or more before the offering and is not a natural person. Holders are classed
by pilot/ipo_holder_classes.tsv, then pilot/investor_classes.tsv; the kind of a corporate investor comes from the
first file where it gives one, otherwise from pilot/corporate_investors.tsv.
  venture share     sum of the percentages held by venture-capital funds before the offering (capped at 100)
  venture holder    venture share above zero
  specialist share  the same with life-science crossover funds added
  corporate holder  a drug, drug-services or medical-technology company or its venture arm among the holders
A prospectus belongs to the sponsor names linked to its registrant whose first word is the first word of the
filer's name; of several prospectuses of one name the earliest is taken. Programmes and phase entries as in
owners_models.py: indications with genetic insight, non-top-20 industry sponsors, 2001 or later.

Primary estimate (fixed in the plan): odds ratio of ex-ante support per 10 percentage points of venture share, on
programmes first tried no later than the IPO year, errors clustered by drug. The exposure is the same for every
programme of a sponsor, so each model is also given with errors clustered by sponsor (added when this script was
written, before any model was fitted).
Writes ipo_holders_classified.csv, ipo_sponsors.csv and ipo_models.txt to RESULTS_DIR.
"""

import os
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from pooling import pool_sparse

R, IPO = sys.argv[1], sys.argv[2]
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
FIRST_YEAR = 2001
VENTURE, CROSSOVER = "venture capital", "life-science crossover"
out = []


def rules():
    ext = pd.read_csv(os.path.join(HERE, "ipo_holder_classes.tsv"), sep="\t", keep_default_na=False)
    base = pd.read_csv(os.path.join(HERE, "investor_classes.tsv"), sep="\t")
    corp = pd.read_csv(os.path.join(HERE, "corporate_investors.tsv"), sep="\t")
    return (
        [(re.compile(p, re.I), c, k) for p, c, k in zip(ext.pattern, ext["class"], ext.kind)],
        [(re.compile(p, re.I), c) for p, c in zip(base.pattern, base["class"])],
        [(re.compile(p, re.I), k) for p, k in zip(corp.pattern, corp.kind)],
    )


def classify(name, ext, base, corp):
    """(class, kind of corporate investor, which file gave the class)."""
    kind = next((k for rx, k in corp if rx.search(name)), "")
    for rx, c, k in ext:
        if rx.search(name):
            return c, k or kind, "prospectus rules"
    return next((c for rx, c in base if rx.search(name)), "unclassified"), kind, "general rules"


def first_word(name):
    return (rq2_stops.norm_sponsor(name) or " ").split(" ")[0]


def sponsors():
    """One row per sponsor name: its IPO prospectus and the measures read from it."""
    idx = pd.read_csv(os.path.join(IPO, "ipo_prospectus_index.csv"), dtype=str)
    log = pd.read_csv(f"{R}/ipo_holders_log.csv", dtype=str)
    idx = idx.merge(log[["accession", "status"]], on="accession", how="left")
    n_ipo = int(idx.ipo.eq("1").sum())
    idx = idx[idx.ipo.eq("1") & idx.own_name.eq("1")].copy()
    out.append(
        f"IPO prospectuses of sponsors' registrants: {n_ipo}; filed under the sponsor's own name: {len(idx)}; "
        f"table read: {int(idx.status.eq('read').sum())} ({idx.status.value_counts().to_dict()})"
    )
    h = pd.read_csv(f"{R}/ipo_holders.csv", dtype={"cik": str})
    h = h[h.accession.isin(idx.accession[idx.status.eq("read")]) & (h.pct_before >= 5) & (h.person == 0)].copy()
    ext, base, corp = rules()
    h[["holder_class", "kind", "classed_by"]] = [classify(n, ext, base, corp) for n in h.holder]
    h.to_csv(f"{R}/ipo_holders_classified.csv", index=False)
    out.append(
        f"holdings of 5% or more by holders that are not natural persons: {len(h)} in {h.accession.nunique()} "
        f"prospectuses; by class: {h.holder_class.value_counts().to_dict()}"
    )
    out.append(
        f"classed by the rules written for the prospectuses: {int(h.classed_by.eq('prospectus rules').sum())}; "
        f"kind of corporate investor: {h.kind[h.kind.ne('')].value_counts().to_dict()}"
    )
    pharma = h.kind.str.startswith("pharma corporate")
    m = pd.DataFrame(
        {
            "holders": h.groupby("accession").size(),
            "venture_share": h[h.holder_class.eq(VENTURE)].groupby("accession").pct_before.sum(),
            "specialist_share": h[h.holder_class.isin([VENTURE, CROSSOVER])].groupby("accession").pct_before.sum(),
            "corporate": h[pharma].groupby("accession").size().gt(0),
            "corporate_large": h[h.kind.eq("pharma corporate, large")].groupby("accession").size().gt(0),
            "unclassified_share": h[h.holder_class.eq("unclassified")].groupby("accession").pct_before.sum(),
        }
    )
    s = idx[idx.status.eq("read")].merge(m, left_on="accession", right_index=True, how="left")
    for c in ("holders", "venture_share", "specialist_share", "unclassified_share"):
        s[c] = s[c].fillna(0.0)
    for c in ("corporate", "corporate_large"):
        s[c] = s[c].fillna(False).astype(bool)
    over = int((s.venture_share > 100).sum())
    s["venture_share"], s["specialist_share"] = s.venture_share.clip(upper=100), s.specialist_share.clip(upper=100)
    s["venture"] = s.venture_share.gt(0)
    s["ipo_year"] = s.date.str[:4].astype(int)
    s["norm"] = s.sponsors.str.split(";")
    s = s.explode("norm")
    s["norm"] = s.norm.str.strip()
    s = s[s.norm.str.split(" ").str[0] == s.name.map(first_word)]  # the names that merged into the filer later go
    s = s.sort_values(["norm", "date"]).drop_duplicates("norm")
    out.append(
        f"sponsor names with a prospectus read: {len(s)}; with a venture holder: {int(s.venture.sum())}; with a "
        f"corporate holder: {int(s.corporate.sum())} (large company {int(s.corporate_large.sum())}); venture funds "
        f"only: {int((s.venture & ~s.corporate).sum())}; neither: {int((~s.venture & ~s.corporate).sum())}; venture "
        f"shares above 100 before the cap: {over}"
    )
    q = s.venture_share.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(1).tolist()
    out.append(
        f"venture share, all sponsors: mean {s.venture_share.mean():.1f}, percentiles 10/25/50/75/90: {q}; IPO years "
        f"{s.ipo_year.min()}-{s.ipo_year.max()} ({int(s.ipo_year.ge(2016).sum())} in 2016 or later)"
    )
    cols = ["norm", "cik", "accession", "date", "ipo_year", "holders", "venture_share", "specialist_share", "venture", "corporate", "corporate_large", "unclassified_share"]  # fmt: skip
    s[cols].round(2).to_csv(f"{R}/ipo_sponsors.csv", index=False)
    return s[cols]


def fit(f, d, title, keep, both=True):
    """Logit with errors clustered by drug (the pilot's rule) and, for a sponsor-level exposure, by sponsor."""
    try:
        d = pool_sparse(d, f)
        ev = int(d[f.split("~")[0].strip()].sum())
        head = [
            "=" * 100,
            title,
            f,
            f"N={len(d)}; events={ev}; drugs={d.drug.nunique()}; sponsors={d.norm.nunique()}",
        ]
        for label, col in (("drug", "drug"), ("sponsor", "norm"))[: 2 if both else 1]:
            r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d[col])[0]})  # fmt: skip
            t = r.summary2().tables[1]
            t = t.loc[[i for i in t.index if i in keep], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
            t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
            head.append(f"errors clustered by {label}; converged={r.mle_retvals['converged']}")
            head.append(t.round(4).to_string())
        out.extend(head)
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def compare(name, ours, other):
    ours, other = np.asarray(ours, bool), np.asarray(other, bool)
    tp, fp = int((ours & other).sum()), int((ours & ~other).sum())
    fn, tn = int((~ours & other).sum()), int((~ours & ~other).sum())
    out.append(
        f"  {name}: n={len(ours)}; both {tp}, prospectus only {fp}, other only {fn}, neither {tn}; "
        f"agreement {(tp + tn) / max(len(ours), 1):.3f}, kappa {kappa(ours, other):.3f}"
    )


out.append("Investors named in IPO prospectuses (holders of 5% or more before the offering) and genetic support")
S = sponsors()
M = S.set_index("norm")

P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.ge(FIRST_YEAR)].copy()
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_YEAR, end_year - 6)].copy()
for T, name_col, year_col in ((P, "first_sponsor", "first_year"), (E, "lead_sponsor", "entry_year")):
    T["norm"] = T[name_col].map(rq2_stops.norm_sponsor)
    for c in ("venture_share", "specialist_share", "venture", "corporate", "ipo_year"):
        T[c] = T.norm.map(M[c])
    T["modality"] = T.drugType.map(MOD).fillna("other")
    T["area"] = T.area.fillna("other")
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
E["yb"] = pd.cut(E.entry_year, [2000, 2005, 2010, 2015, 2030]).astype(str)
P["y"] = P.gs_ante_first.fillna(False).astype(int)
n_all = len(P)
P, E = P[P.ipo_year.notna()].copy(), E[E.ipo_year.notna()].copy()
for T, year_col in ((P, "first_year"), (E, "entry_year")):
    T["v10"], T["s10"] = T.venture_share / 10, T.specialist_share / 10
    T["vc"], T["corp"] = T.venture.astype(int), T.corporate.astype(int)
    T["before"] = (T[year_col] <= T.ipo_year).astype(int)
B = P[P.before.eq(1)].copy()
out.append(
    f"\nProgrammes (insight indications, first trial {FIRST_YEAR}+, non-top-20 industry): {n_all}; of sponsors with a "
    f"prospectus read: {len(P)} ({P.norm.nunique()} sponsors); first tried no later than the IPO year: {len(B)} "
    f"({B.norm.nunique()} sponsors, {int(B.y.sum())} with ex-ante support)"
)
B["third"] = pd.qcut(B.venture_share, 3, duplicates="drop")
out.append("programmes first tried no later than the IPO year, by third of venture share:")
out.append(
    B.groupby("third", observed=True)
    .agg(n=("drug", "size"), sponsors=("norm", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean"))
    .round(4)
    .to_string()
)
out.append("the same by venture holder x corporate holder:")
out.append(
    B.groupby(["vc", "corp"])
    .agg(n=("drug", "size"), sponsors=("norm", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean"))
    .round(4)
    .to_string()
)

base_p = "C(tier) + C(yb) + C(area) + C(modality)"
out.append("\n1. PRIMARY (plan): ex-ante support per 10 percentage points of venture share, programmes first tried no later than the IPO year")  # fmt: skip
fit(f"y ~ v10 + {base_p}", B, "H1 PRIMARY: ex-ante support ~ venture share (per 10 points)", ("v10",))

out.append("\n2. Secondary (plan)")
fit(f"y ~ vc + {base_p}", B, "H1: ~ venture holder (yes against no), no later than the IPO year", ("vc",))
VO = B[(B.vc.eq(1)) | (B.corp.eq(1))].copy()
fit(f"y ~ corp + {base_p}", VO, "H1: ~ corporate holder against venture funds only, no later than the IPO year", ("corp",))  # fmt: skip
fit(f"y ~ v10 + {base_p}", P, "H1: ~ venture share, all programmes of these sponsors", ("v10",))
fit(f"y ~ vc + {base_p}", P, "H1: ~ venture holder, all programmes of these sponsors", ("vc",))
VOA = P[(P.vc.eq(1)) | (P.corp.eq(1))].copy()
fit(f"y ~ corp + {base_p}", VOA, "H1: ~ corporate holder against venture funds only, all programmes", ("corp",))
fit(f"y ~ v10 + {base_p}", P[P.before.eq(0)].copy(), "H1: ~ venture share, programmes first tried after the IPO year", ("v10",))  # fmt: skip
fit(f"y ~ v10 + {base_p}", B[B.ipo_year.ge(2016)].copy(), "H1: ~ venture share, IPOs of 2016-2026, no later than the IPO year", ("v10",))  # fmt: skip
fit(f"y ~ v10 + {base_p}", B[B.ipo_year.le(2015)].copy(), "H1: ~ venture share, IPOs of 2001-2015, no later than the IPO year", ("v10",))  # fmt: skip
fit(f"y ~ s10 + {base_p}", B, "H1 (variant declared in the plan): ~ specialist share (venture and crossover funds)", ("s10",))  # fmt: skip
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    B2 = B.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    B2["y"] = B2.gs_ot_ante_first.fillna(False).astype(int)
    fit(f"y ~ v10 + {base_p}", B2, "H1 [dated Open Targets evidence]: ~ venture share, no later than the IPO year", ("v10",))  # fmt: skip
    fit(f"y ~ vc + {base_p}", B2, "H1 [dated Open Targets evidence]: ~ venture holder, no later than the IPO year", ("vc",))  # fmt: skip
else:
    out.append("(gs_ot_programmes.csv.gz not in RESULTS_DIR: the models with dated Open Targets evidence are not run)")

E["gs"], E["adv"] = E.gs_ante.fillna(False).astype(int), E.advanced.astype(int)
EB = E[E.before.eq(1)].copy()
out.append("=" * 100)
out.append(
    f"Phase entries {FIRST_YEAR}-{end_year - 6} of these sponsors: {len(E)}; no later than the IPO year: {len(EB)} "
    f"({EB.norm.nunique()} sponsors, {int(EB.adv.sum())} advanced)"
)
base_e = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ v10 + gs + {base_e}", EB, "Advancement ~ venture share + ex-ante support, entries no later than the IPO year", ("v10", "gs"))  # fmt: skip
fit(f"adv ~ v10 + gs + {base_e}", E, "Advancement ~ venture share + ex-ante support, all entries of these sponsors", ("v10", "gs"))  # fmt: skip

out.append("\n3. The venture holder of the prospectus against other markers (a check of the measure, not a result)")
if os.path.exists(f"{R}/ritter_sponsors.csv"):
    rt = pd.read_csv(f"{R}/ritter_sponsors.csv")
    rt["norm"] = rt.first_sponsor.map(rq2_stops.norm_sponsor)
    x = S.merge(rt.drop_duplicates("norm")[["norm", "ipo_year", "ritter_vc"]], on="norm", suffixes=("", "_ritter"))
    out.append(f"  sponsors with a prospectus read that are in Jay Ritter's IPO list: {len(x)}")
    compare("venture holder against Ritter's venture flag", x.venture, x.ritter_vc)
    same = x[(x.ipo_year - x.ipo_year_ritter).abs() <= 1]
    compare("the same, IPO year of the two sources within one year", same.venture, same.ritter_vc)
if os.path.exists(f"{R}/owners_sponsors.csv"):
    ow = pd.read_csv(f"{R}/owners_sponsors.csv", dtype={"norm": str})
    x = S.merge(ow[["norm", "vc_backed", "first_vc_year"]], on="norm")
    compare("venture holder against a venture owner in Schedules 13D/13G, any time", x.venture, x.vc_backed.astype(bool))  # fmt: skip
    at_ipo = x.vc_backed.astype(bool) & (pd.to_numeric(x.first_vc_year, errors="coerce") <= x.ipo_year + 1)
    compare("the same, the owner's first filing by the year after the IPO", x.venture, at_ipo)

open(f"{R}/ipo_models.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
