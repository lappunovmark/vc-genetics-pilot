"""Direction of effect from Open Targets: what the genetics says a drug should do, and what the drug does.

Usage: python pilot/extract_ot_direction.py OT_DIR OT_GENETIC_EVIDENCE_DIR OUT_DIR
OT_DIR is the directory of fetch_opentargets.py (needs target, evidence_clinical_precedence);
OT_GENETIC_EVIDENCE_DIR holds evidence_gene_burden, evidence_eva, evidence_orphanet and evidence_gene2phenotype of
the same release (the germline sources for which Open Targets assesses a direction of effect).

Open Targets gives each piece of evidence a direction on the target (loss or gain of function, LoF / GoF) and a
direction on the trait (risk / protect); for a drug in the clinic the direction on the target comes from its action
(inhibitors LoF, activators GoF) and the direction on the trait is "protect". Gene burden evidence is taken as LoF
with the trait direction read from the sign of the effect; ClinVar evidence is assessed for LoF variants;
Orphanet and Gene2Phenotype are taken as risk. GWAS evidence has no assessment.
Score floors are those of gs_ot_dated.py (ClinVar >= 0.7; Orphanet, Gene2Phenotype >= 0.5; gene burden all).
Writes OUT_DIR/ot_direction_evidence.csv.gz (gene x disease x source x direction, with the earliest evidence year
and the number of evidence rows) and OUT_DIR/ot_drug_direction.csv.gz (drug x gene x direction on the target).
"""

import glob
import os
import sys

import pandas as pd

FLOOR = {"gene_burden": 0.0, "eva": 0.7, "orphanet": 0.5, "gene2phenotype": 0.5}
COLS = ["targetId", "diseaseId", "score", "evidenceDate", "directionOnTarget", "directionOnTrait"]


def read(d, cols):
    files = sorted(glob.glob(os.path.join(d, "*.parquet")))
    if not files:
        raise SystemExit(f"no parquet files in {d}")
    return pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True)


def main(ot, gen, out):
    tg = read(f"{ot}/target", ["id", "approvedSymbol"]).rename(columns={"id": "targetId", "approvedSymbol": "gene"})
    parts, log = [], []
    for s, fl in FLOOR.items():
        d = read(f"{gen}/evidence_{s}", COLS)
        n = len(d)
        d = d[d.score >= fl]
        both = d.directionOnTarget.notna() & d.directionOnTrait.notna()
        log.append(f"{s}: rows {n}; at or above the score floor {len(d)}; with both directions {int(both.sum())}")
        d = d[both].assign(source=s, year=lambda x: pd.to_datetime(x.evidenceDate, errors="coerce").dt.year)
        parts.append(d)
    ev = pd.concat(parts, ignore_index=True).merge(tg, on="targetId", how="left")
    log.append(f"evidence rows without a gene symbol: {int(ev.gene.isna().sum())}")
    key = ["gene", "diseaseId", "source", "directionOnTarget", "directionOnTrait"]
    ev = ev.dropna(subset=["gene"]).groupby(key).agg(year=("year", "min"), n=("score", "size")).reset_index()
    ev.to_csv(f"{out}/ot_direction_evidence.csv.gz", index=False)
    log.append(f"gene x disease x source x direction rows written: {len(ev)}")
    log.append(pd.crosstab([ev.source, ev.directionOnTarget], ev.directionOnTrait).to_string())
    cp = read(f"{ot}/evidence_clinical_precedence", ["drugId", "targetId", "directionOnTarget"])
    cp = cp.merge(tg, on="targetId", how="left").dropna(subset=["drugId", "gene"])
    dd = cp.groupby(["drugId", "gene", "directionOnTarget"], dropna=False).size().rename("n").reset_index()
    dd.to_csv(f"{out}/ot_drug_direction.csv.gz", index=False)
    log.append(f"drug x gene x direction rows written: {len(dd)}; drugs {dd.drugId.nunique()}")
    log.append(dd.directionOnTarget.fillna("none").value_counts().to_string())
    print("\n".join(log))


if __name__ == "__main__":
    main(*sys.argv[1:4])
