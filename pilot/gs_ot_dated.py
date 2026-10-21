"""Ex-ante genetic support from Open Targets evidence dated by Falaguera et al. (Zenodo 15922783, OT 25.03).

Usage: python gs_ot_dated.py RESULTS_DIR OT_DIR FALAGUERA_EVIDENCE_DIR MINIKEL_DATA_DIR

Germline genetic sources and score floors (excludes uncertain/benign ClinVar, limited/disputed curations):
  gwas_credible_sets L2G >= 0.5 | gene_burden all | eva (ClinVar) >= 0.7 | orphanet, gene2phenotype,
  genomics_england, uniprot_literature, uniprot_variants, clingen >= 0.5. intOGen (somatic, undated) excluded.
Evidence diseases are mapped to MeSH with the panel's own map (disease_mesh.csv.gz) and labelled with the
Minikel similarity rule (>= 0.8). Ex ante = evidence year < phase-entry year; undated evidence never counts as ex ante.
Writes RESULTS_DIR/gs_ot_entries.csv.gz, gs_ot_programmes.csv.gz and gs_ot_models.txt.
"""

import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup

FLOOR = {
    "gwas_credible_sets": 0.5,
    "gene_burden": 0.0,
    "eva": 0.7,
    "orphanet": 0.5,
    "gene2phenotype": 0.5,
    "genomics_england": 0.5,
    "uniprot_literature": 0.5,
    "uniprot_variants": 0.5,
    "clingen": 0.5,
}
TIERS = [
    "Top-20 pharma",
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]


def load_evidence(fal, ot, dm):
    parts = []
    for s, fl in FLOOR.items():
        files = glob.glob(os.path.join(fal, f"sourceId={s}", "*.parquet"))
        d = pd.concat([pd.read_parquet(f, columns=["targetId", "diseaseId", "score", "year"]) for f in files])
        d = d[d.score >= fl].assign(source=s)
        parts.append(d)
    ev = pd.concat(parts, ignore_index=True)
    tg = pd.concat([pd.read_parquet(f, columns=["id", "approvedSymbol"]) for f in glob.glob(f"{ot}/target/*.parquet")])
    ev = ev.merge(tg.rename(columns={"id": "targetId", "approvedSymbol": "gene"}), on="targetId", how="left")
    ev = ev.merge(
        dm[["diseaseId", "indication_mesh_id"]].rename(columns={"indication_mesh_id": "mesh_id"}),
        on="diseaseId",
        how="left",
    )
    cov = {
        "rows": len(ev),
        "with_gene": float(ev.gene.notna().mean()),
        "with_mesh": float(ev.mesh_id.notna().mean()),
        "dated": float(ev.year.notna().mean()),
        "by_source": ev.source.value_counts().to_dict(),
    }
    a = ev.dropna(subset=["gene", "mesh_id"])
    # earliest year per gene x MeSH x source keeps the join small and is all the ex-ante rule needs
    a = a.groupby(["gene", "mesh_id", "source"], dropna=False).year.min().reset_index()
    return a, cov


def logit(f, d, groups, title, out):
    import statsmodels.formula.api as smf

    try:
        r = smf.logit(f, d).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})
        t = r.summary2().tables[1]
        t = t.loc[
            [i for i in t.index if "tier" in i or i == "gs" or i.startswith("gs:")],
            ["Coef.", "P>|z|", "[0.025", "0.975]"],
        ]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        out.extend(["=" * 90, title, f, f"N={int(r.nobs)}", t.round(4).to_string()])
    except Exception as e:
        out.extend(["=" * 90, title, f, f"failed: {e!r}"])


def main(R, ot, fal, mdir):
    dm = pd.read_csv(f"{R}/disease_mesh.csv.gz")
    targets = pd.read_csv(f"{R}/programme_targets.csv.gz")
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    P = pd.read_csv(f"{R}/programmes.csv.gz")
    a, cov = load_evidence(fal, ot, dm)
    _, sim, _ = gensup.load(mdir)
    simp = gensup.similar_pairs(sim)
    key = ["drug", "indication_mesh_id"]
    idx = key + ["phase"]
    ti = E[idx + ["entry_year"]].merge(targets, on=key).rename(columns={"entry_year": "yr"})
    lab = gensup.label(ti, a, simp, year_col="yr", omim_mode="none")
    E = E.merge(
        lab.groupby(idx).agg(gs_ot_post=("gs_post", "any"), gs_ot_ante=("gs_ante", "any")).reset_index(),
        on=idx,
        how="left",
    )
    pt = P[key + ["first_year"]].merge(targets, on=key)
    pl = gensup.label(pt, a, simp, year_col="first_year", omim_mode="none")
    P = P.merge(
        pl.groupby(key).agg(gs_ot_post=("gs_post", "any"), gs_ot_ante_first=("gs_ante", "any")).reset_index(),
        on=key,
        how="left",
    )
    for D, cols in ((E, ["gs_ot_post", "gs_ot_ante"]), (P, ["gs_ot_post", "gs_ot_ante_first"])):
        for c in cols:
            D[c] = D[c].fillna(False).astype(bool)
    E.to_csv(f"{R}/gs_ot_entries.csv.gz", index=False)
    P.to_csv(f"{R}/gs_ot_programmes.csv.gz", index=False)

    out = [f"coverage: {cov}"]
    I = P[P.insight]
    out.append("Agreement with Minikel-based labels (programmes with insight):")
    out.append(pd.crosstab(I.gs_post.fillna(False), I.gs_ot_post, margins=True).to_string())
    out.append(pd.crosstab(I.gs_ante_first.fillna(False), I.gs_ot_ante_first, margins=True).to_string())
    tab = I.groupby("first_sponsor_tier").agg(
        n=("drug", "size"), gs_ot_post=("gs_ot_post", "mean"), gs_ot_ante=("gs_ot_ante_first", "mean")
    )
    out.append(tab.round(4).to_string())

    def mod(dt):
        return {
            "Small molecule": "small molecule",
            "Antibody": "antibody",
            "Antibody drug conjugate": "antibody",
            "Protein": "protein",
            "Enzyme": "protein",
            "Oligonucleotide": "nucleic acid/gene/cell",
            "Gene": "nucleic acid/gene/cell",
            "Cell": "nucleic acid/gene/cell",
        }.get(dt, "other")

    H = I[I.first_sponsor_tier.isin(TIERS)].copy()
    H["tier"] = pd.Categorical(H.first_sponsor_tier, categories=TIERS)
    H["modality"] = H.drugType.map(mod)
    H["area"] = H.area.fillna("other")
    H["yb"] = pd.cut(H.first_year, [0, 2004, 2009, 2014, 2019, 2100]).astype(str)
    H["y"] = H.gs_ot_ante_first.astype(int)
    logit(
        "y ~ C(tier) + C(yb) + C(area) + C(modality)",
        H,
        H.drug,
        "H1 with dated OT evidence: ex-ante support at first trial",
        out,
    )
    end_year = int(E.entry_year.max())
    T = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
    T["tier"] = pd.Categorical(T.sponsor_tier, categories=TIERS)
    T["modality"] = T.drugType.map(mod)
    T["area"] = T.area.fillna("other")
    T["yb"] = pd.cut(T.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
    T["adv"] = T.advanced.astype(int)
    base = "C(phase) + C(yb) + C(area) + C(modality)"
    for col, nm in (("gs_ot_ante", "dated OT evidence, ex ante"), ("gs_ot_post", "OT evidence, any year")):
        T["gs"] = T[col].astype(int)
        out.append(f"{nm}: share of entries supported {T.gs.mean():.4f}")
        logit(f"adv ~ gs + C(tier) + {base}", T, T.drug, f"Advance ~ support ({nm})", out)
        logit(f"adv ~ gs * C(tier) + {base}", T, T.drug, f"Advance ~ support x tier ({nm})", out)
    open(f"{R}/gs_ot_models.txt", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:5])
