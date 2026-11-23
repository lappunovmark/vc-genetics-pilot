"""Advancement by the similarity of the target's genetic evidence to the indication; the lowest band is a placebo.

Usage: python pilot/placebo_similarity.py MINIKEL_DATA_DIR RESULTS_DIR
(MINIKEL_DATA_DIR holds assoc.tsv.gz and sim.tsv.gz of Minikel et al. 2024; RESULTS_DIR holds phase_entries.csv.gz
and programme_targets.csv.gz; plan written before the run: docs/plan_placebo_similarity.md)

For each phase entry: over the targets of the programme and the associations of each target dated before the entry
year (OMIM counted as ex ante), the highest similarity between the associated trait and the indication (identical
terms count as 1). Bands: supported (>= 0.8, which must reproduce gs_ante), 0.5-0.8, 0.2-0.5, placebo (< 0.2: the
target has genetic evidence, all of it for unrelated traits), none (no ex-ante association; the reference).
Writes placebo_similarity.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup

TIERS = [
    "Top-20 pharma",
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]
BANDS = ["none", "placebo", "0.2-0.5", "0.5-0.8", "supported"]


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


def max_similarity(entries, targets, a, sim):
    """Highest similarity of an ex-ante association of any target to the indication, per (drug, indication, year).
    Returns a frame with max_sim (NaN when no target has an ex-ante association) and n_unscored (associated
    traits without a similarity score to the indication)."""
    key = ["drug", "indication_mesh_id", "yr"]
    ti = entries[key].drop_duplicates().merge(targets, on=["drug", "indication_mesh_id"])
    m = ti.merge(a, on="gene")
    m = m[(m.year < m.yr) | (m.year.isna() & m.source.eq("OMIM"))]
    m = m[key + ["mesh_id"]].drop_duplicates()
    m = m.merge(
        sim.rename(columns={"meshcode_a": "indication_mesh_id", "meshcode_b": "mesh_id"}),
        on=["indication_mesh_id", "mesh_id"],
        how="left",
    )
    m.loc[m.indication_mesh_id.eq(m.mesh_id), "comb_norm"] = 1.0
    out = m.groupby(key).agg(max_sim=("comb_norm", "max"), n_assoc=("mesh_id", "size"), n_unscored=("comb_norm", lambda s: int(s.isna().sum()))).reset_index()  # fmt: skip
    return entries[key].drop_duplicates().merge(out, on=key, how="left")


def band(max_sim, n_assoc, cut=0.2):
    """Band of an entry; an entry whose associations all lack a score is 'unscored' and left out of the models."""
    if n_assoc != n_assoc or n_assoc == 0:
        return "none"
    if max_sim != max_sim:
        return "unscored"
    if max_sim >= 0.8:
        return "supported"
    if max_sim >= 0.5:
        return "0.5-0.8"
    if max_sim >= cut:
        return "0.2-0.5" if cut == 0.2 else f"{cut}-0.5"
    return "placebo"


def fit(out, d, title, levels):
    d = d[d.band.isin(levels)].copy()
    for lv in levels[1:]:
        d["b_" + lv.replace(".", "").replace("-", "_")] = d.band.eq(lv).astype(int)
    names = ["b_" + lv.replace(".", "").replace("-", "_") for lv in levels[1:]]
    f = "adv ~ " + " + ".join(names) + " + C(tier) + C(phase) + C(yb) + C(area) + C(modality)"
    out.extend(["=" * 100, title, f])
    try:
        r = smf.logit(f, d).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1].loc[names, ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
        out.append(f"N={int(r.nobs)}; advanced={int(d.adv.sum())}; drugs={d.drug.nunique()}; converged={r.mle_retvals['converged']}")  # fmt: skip
        out.append(t.round(4).to_string())
        c = r.t_test("b_supported - b_placebo = 0")
        b, (lo, hi) = float(np.ravel(c.effect)[0]), np.ravel(c.conf_int())
        out.append(f"supported against placebo: OR {np.exp(b):.4f} ({np.exp(lo):.4f} to {np.exp(hi):.4f}), p={float(np.ravel(c.pvalue)[0]):.4f}")  # fmt: skip
    except Exception as e:
        out.append(f"failed: {e!r}")


def main(mdir, R):
    out = ["Advancement by the similarity of the genetic evidence to the indication (plan: docs/plan_placebo_similarity.md)"]  # fmt: skip
    assoc, sim, _ = gensup.load(mdir)
    a = gensup.filter_assoc(assoc)
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    targets = pd.read_csv(f"{R}/programme_targets.csv.gz")
    end_year = int(E.entry_year.max())
    T = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
    T["yr"] = T.entry_year
    T["tier"] = pd.Categorical(T.sponsor_tier, categories=TIERS)
    T["gs"], T["adv"] = T.gs_ante.fillna(False).astype(int), T.advanced.astype(int)
    T["yb"] = pd.cut(T.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
    T["modality"], T["area"] = T.drugType.map(mod), T.area.fillna("other")
    key = ["drug", "indication_mesh_id", "yr"]
    for label, aa in (("all sources", a), ("without OMIM", a[a.source != "OMIM"])):
        s = max_similarity(T, targets, aa, sim)
        col = "" if label == "all sources" else "_noomim"
        T = T.merge(s.rename(columns={c: c + col for c in ("max_sim", "n_assoc", "n_unscored")}), on=key, how="left")
    T["band"] = [band(m, n) for m, n in zip(T.max_sim, T.n_assoc)]
    T["band_01"] = [band(m, n, cut=0.1) for m, n in zip(T.max_sim, T.n_assoc)]
    T["band_noomim"] = [band(m, n) for m, n in zip(T.max_sim_noomim, T.n_assoc_noomim)]
    out.append(f"phase entries: {len(T)} ({int(T.adv.sum())} advanced); with ex-ante support in the panel: {int(T.gs.sum())}")  # fmt: skip
    agree = pd.crosstab(T.band.eq("supported"), T.gs.astype(bool))
    out.append("check: band 'supported' (rows) against gs_ante of the panel (columns):")
    out.append(agree.to_string())
    out.append(f"entries with an association whose trait has no similarity score to the indication: {int((T.n_unscored > 0).sum())}; all associations unscored (left out): {int(T.band.eq('unscored').sum())}")  # fmt: skip
    tab = T.groupby("band").agg(n=("adv", "size"), advanced=("adv", "sum"), rate=("adv", "mean")).reindex(BANDS + ["unscored"]).round(4)  # fmt: skip
    out.append("advancement by band (unadjusted):")
    out.append(tab.to_string())

    out.append("\n1. PRIMARY (plan): the placebo band against none (coefficient b_placebo)")
    fit(out, T, "Advance ~ bands of the highest similarity (reference: none)", BANDS)
    out.append("\n2. SECONDARY (plan)")
    fit(out, T.assign(band=T.band_noomim), "without OMIM: bands from dated associations only", BANDS)
    fit(out, T[T.sponsor_tier.isin(TIERS[:4])].assign(tier=lambda x: pd.Categorical(x.sponsor_tier, categories=TIERS[:4])), "industry sponsors only", BANDS)  # fmt: skip
    fit(out, T.assign(band=T.band_01), "placebo band cut at 0.1 (the band 0.1-0.5 replaces 0.2-0.5)", ["none", "placebo", "0.1-0.5", "0.5-0.8", "supported"])  # fmt: skip
    open(f"{R}/placebo_similarity.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:3])
