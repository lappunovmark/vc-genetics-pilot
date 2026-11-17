"""Does the drug act in the direction the genetics points to, and does that differ by sponsor? Exploratory.

Usage: python pilot/direction_models.py RESULTS_DIR MINIKEL_DATA_DIR OT_DIRECTION_DIR
(after extract_ot_direction.py; MINIKEL_DATA_DIR holds sim.tsv.gz)

Why: the pilot's support flag says that human genetics links the drug's target to the indication. It does not say
whether the drug pushes the target the way the genetics suggests: when losing the gene's function causes the
disease, an inhibitor of that gene is "supported" by the flag but acts in the opposite direction.
Genetic side: Open Targets 26.09 evidence with a direction of effect (gene burden, ClinVar, Orphanet,
Gene2Phenotype; no GWAS). The drug should reduce the target's function (LoF) when loss of function protects or
gain of function is a risk, and raise it (GoF) when loss of function is a risk or gain of function protects.
Drug side: the direction Open Targets assigns to the drug's action on the gene (inhibitors LoF, activators GoF).
A programme has directional evidence when one of its targets has such evidence for an indication with MeSH
similarity >= 0.8 (the rule of gensup.py, with the panel's disease map). It is concordant when for at least one
target and piece of evidence the drug's direction is the one the genetics asks for, and discordant when directions
are known and none agrees. Ex ante: evidence dated before the year of the first trial (Open Targets evidence date;
for ClinVar this is the date of the record, so ex-ante counts are small and conservative).
Caveats: Open Targets assesses ClinVar for loss-of-function variants only, so a disease caused by gain of function
in the same gene is invisible here and "discordant" is not proof of a wrong direction: the genes that most often
come out discordant are oncogenes and ion channels whose diseases are caused by gain of function (EGFR, FGFR3,
ERBB2, KIT, RET, SCN5A), for which an inhibitor is the right direction. The discordant counts are therefore
printed but not interpreted; the concordant label is the usable one. Gene burden evidence is taken as loss of
function and for a quantitative trait "risk" only means a higher value, so the models are repeated without it.
Nothing here was pre-specified.
Sample, controls and clustering are those of h1_mechanisms.py. Writes RESULTS_DIR/direction_models.txt and
direction_programmes.csv.gz.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup
import h1_mechanisms as hm

KEY = ["drug", "indication_mesh_id"]
SMALL, TOP = hm.SMALL, hm.TIERS[0]
F = "C(tier) + " + hm.CTRL


def flags(m, suffix):
    g = m.groupby(KEY).agg(conc=("conc", "any"), disc=("disc", "any")).reset_index()
    g[f"has{suffix}"] = True
    g[f"conc{suffix}"] = g.conc
    g[f"disc{suffix}"] = g.disc & ~g.conc
    return g[KEY + [f"has{suffix}", f"conc{suffix}", f"disc{suffix}"]]


def build(H, pt, a, dd, sp):
    ti = H[KEY + ["first_year"]].merge(pt, on=KEY)
    u = ti.indication_mesh_id.unique()
    sp = pd.concat([sp, pd.DataFrame({"meshcode_a": u, "meshcode_b": u})]).drop_duplicates()
    m = ti.merge(sp, left_on="indication_mesh_id", right_on="meshcode_a").merge(
        a, left_on=["gene", "meshcode_b"], right_on=["gene", "mesh_id"]
    )
    m = m.merge(dd, on=["drug", "gene"], how="left")
    m["conc"] = m.does.eq(m.need)
    m["disc"] = m.does.notna() & m.does.ne(m.need)
    out = H.merge(flags(m, "_post"), on=KEY, how="left").merge(
        flags(m[m.year < m.first_year], "_ante"), on=KEY, how="left"
    )
    cols = ["has_post", "conc_post", "disc_post", "has_ante", "conc_ante", "disc_ante"]
    out[cols] = out[cols].fillna(False).astype(bool)
    return m, out


def table(H):
    t = H.groupby("tier", observed=True).agg(
        programmes=("drug", "size"),
        directional=("has_post", "sum"),
        concordant=("conc_post", "sum"),
        discordant=("disc_post", "sum"),
        directional_ante=("has_ante", "sum"),
        concordant_ante=("conc_ante", "sum"),
        discordant_ante=("disc_ante", "sum"),
    )
    t["concordant_%"] = (100 * t.concordant / t.programmes).round(2)
    t["discordant_%"] = (100 * t.discordant / t.programmes).round(2)
    t["concordant_of_known_%"] = (100 * t.concordant / (t.concordant + t.discordant)).round(1)
    return t


def flag():
    """hm.show has just written the model's note as the last but one line."""
    return " (the model did not converge)" if "NOT CONVERGED" in hm.out[-2] else ""


def models(H, label):
    rows = []
    for y, name in (
        ("conc_post", "concordant support, evidence of any date"),
        ("disc_post", "discordant evidence only, any date"),
        ("conc_ante", "concordant support before the first trial"),
    ):
        d = H.assign(y=H[y].astype(int))
        try:
            t = hm.show(f"{label}{name}", "y ~ " + F, d)
            rows.append(f"  {name}: small sponsors vs top-20 pharma " + hm.cell(t, f"C(tier)[T.{SMALL}]") + flag())
        except Exception as e:
            hm.say("=" * 100, f"{label}{name}", f"failed: {e!r}")
    k = H[H.conc_post | H.disc_post].assign(y=lambda d: d.conc_post.astype(int))
    try:
        t = hm.show(f"{label}concordant rather than discordant, programmes with a known direction", "y ~ " + F, k)
        rows.append(
            "  concordant rather than discordant (known direction): small vs top-20 "
            + hm.cell(t, f"C(tier)[T.{SMALL}]")
            + flag()
        )
    except Exception as e:
        hm.say("=" * 100, f"{label}concordant rather than discordant", f"failed: {e!r}")
    return rows


def main(R, mdir, ddir):
    _, H = hm.load(R)
    pt = pd.read_csv(f"{R}/programme_targets.csv.gz")
    dm = pd.read_csv(f"{R}/disease_mesh.csv.gz")[["diseaseId", "indication_mesh_id"]]
    sp = gensup.similar_pairs(pd.read_csv(f"{mdir}/sim.tsv.gz", sep="\t"))
    ev = pd.read_csv(f"{ddir}/ot_direction_evidence.csv.gz")
    lof = (ev.directionOnTarget.eq("LoF") & ev.directionOnTrait.eq("protect")) | (
        ev.directionOnTarget.eq("GoF") & ev.directionOnTrait.eq("risk")
    )
    ev["need"] = np.where(lof, "LoF", "GoF")
    a = ev.merge(dm.rename(columns={"indication_mesh_id": "mesh_id"}), on="diseaseId")
    a = a.groupby(["gene", "mesh_id", "source", "need"]).year.min().reset_index()
    dd = pd.read_csv(f"{ddir}/ot_drug_direction.csv.gz").dropna(subset=["directionOnTarget"])
    assert not dd.duplicated(["drugId", "gene"]).any()  # one direction per drug and gene
    dd = dd.rename(columns={"drugId": "drug", "directionOnTarget": "does"})[["drug", "gene", "does"]]
    m, H2 = build(H, pt, a, dd, sp)
    say = hm.say
    say(
        "Direction of effect: does the drug act the way the genetics points? (exploratory; see the module docstring)",
        f"evidence rows with a direction and a MeSH indication: {len(a)} "
        f"(of {len(ev)} gene x disease x source x direction rows; {ev.diseaseId.isin(dm.diseaseId).mean():.1%} mapped)",
        f"programmes with insight: {len(H2)}; with directional evidence on a target: {int(H2.has_post.sum())}; "
        f"concordant {int(H2.conc_post.sum())}; discordant {int(H2.disc_post.sum())}; "
        f"drug direction unknown {int((H2.has_post & ~H2.conc_post & ~H2.disc_post).sum())}",
        "",
        "programme x target x evidence rows: what the genetics asks for (need) against what the drug does:",
        pd.crosstab([m.source, m.need], m.does.fillna("unknown")).to_string(),
        "",
        "overlap with the pilot's support flag (ever supported, gs_post):",
        pd.crosstab(H2.gs_post, [H2.conc_post, H2.disc_post]).to_string(),
        "",
        "by sponsor tier:",
        table(H2).to_string(),
    )
    rows = models(H2, "")
    # without gene burden: Mendelian sources only (no quantitative traits, no assumed loss of function)
    m2, H3 = build(H, pt, a[a.source.ne("gene_burden")], dd, sp)
    say("", "#" * 100, "WITHOUT GENE BURDEN EVIDENCE (ClinVar, Orphanet, Gene2Phenotype only)", "#" * 100)
    say(table(H3).to_string())
    rows2 = models(H3, "no gene burden: ")
    say("", "small sponsors vs top-20 pharma (adjusted odds ratios):", *rows, "without gene burden evidence:", *rows2)
    cols = KEY + ["first_sponsor_tier", "first_year", "gs_post", "gs_ante_first"]
    cols += ["has_post", "conc_post", "disc_post", "has_ante", "conc_ante", "disc_ante"]
    H2[cols].to_csv(f"{R}/direction_programmes.csv.gz", index=False)
    open(f"{R}/direction_models.txt", "w").write("\n".join(hm.out) + "\n")
    print("\n".join(hm.out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
