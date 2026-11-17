"""Dated germline genetic evidence from one Open Targets release (the release carries evidence dates since 26.x).

Usage: python pilot/extract_ot_dated.py OT_DIR OT_GENETIC_EVIDENCE_DIR OUT_CSV_GZ
OT_DIR is the directory of fetch_opentargets.py (needs target); OT_GENETIC_EVIDENCE_DIR holds the evidence_<source>
datasets of the same release. Sources and score floors are those of gs_ot_dated.py (GWAS credible sets with
L2G >= 0.5; gene burden all; ClinVar >= 0.7; Orphanet, Gene2Phenotype, Genomics England, UniProt variants and
ClinGen >= 0.5); a source that was not downloaded is skipped and named.
Writes one row per gene x disease x source: the earliest evidence year, the number of evidence rows and how many of
them carry no date.
"""

import glob
import os
import sys

import pandas as pd

FLOOR = {
    "gwas_credible_sets": 0.5,
    "gene_burden": 0.0,
    "eva": 0.7,
    "orphanet": 0.5,
    "gene2phenotype": 0.5,
    "genomics_england": 0.5,
    "uniprot_variants": 0.5,
    "clingen": 0.5,
}
COLS = ["targetId", "diseaseId", "score", "evidenceDate"]


def read(d, cols):
    files = sorted(glob.glob(os.path.join(d, "*.parquet")))
    return pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True) if files else None


def main(ot, gen, out):
    tg = read(f"{ot}/target", ["id", "approvedSymbol"]).rename(columns={"id": "targetId", "approvedSymbol": "gene"})
    parts = []
    for s, fl in FLOOR.items():
        d = read(f"{gen}/evidence_{s}", COLS)
        if d is None:
            print(f"{s}: not downloaded, skipped")
            continue
        n = len(d)
        d = d[d.score >= fl].assign(source=s, year=lambda x: pd.to_datetime(x.evidenceDate, errors="coerce").dt.year)
        print(f"{s}: rows {n}; at or above the score floor {len(d)}; dated {d.year.notna().mean():.3f}")
        parts.append(d.groupby(["targetId", "diseaseId", "source"]).agg(year=("year", "min"), n=("score", "size"), undated=("year", lambda x: int(x.isna().sum()))).reset_index())  # fmt: skip
    ev = pd.concat(parts, ignore_index=True).merge(tg, on="targetId", how="left").dropna(subset=["gene"])
    ev[["gene", "diseaseId", "source", "year", "n", "undated"]].to_csv(out, index=False)
    print(f"gene x disease x source rows written: {len(ev)}")
    print(ev.groupby("source").agg(pairs=("gene", "size"), first=("year", "min"), last=("year", "max")).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:4])
