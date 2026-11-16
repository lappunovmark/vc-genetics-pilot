"""Research codes and other synonyms of every Open Targets molecule, for h1_mechanisms.py (part E).

Usage: python pilot/extract_molecule_synonyms.py OT_DIR OUT.csv.gz
Writes id, name, parentId, drugType, syn_chembl and syn_aact ('|'-separated labels by source) from
OT_DIR/drug_molecule. Only the ChEMBL labels are used downstream: the AACT labels are free text from trial records.
"""

import glob
import sys

import pandas as pd


def main(ot, out):
    d = pd.concat(
        pd.read_parquet(f, columns=["id", "name", "parentId", "synonyms", "drugType"])
        for f in sorted(glob.glob(f"{ot}/drug_molecule/*.parquet"))
    )

    def labels(x, src):
        if x is None:
            return ""
        return "|".join(str(s["label"]).replace("|", "/") for s in x if isinstance(s, dict) and s.get("source") == src)

    d["syn_chembl"] = d.synonyms.map(lambda x: labels(x, "ChEMBL"))
    d["syn_aact"] = d.synonyms.map(lambda x: labels(x, "AACT"))
    d.drop(columns=["synonyms"]).to_csv(out, index=False)
    print(f"{len(d)} molecules; with a ChEMBL synonym: {d.syn_chembl.ne('').mean():.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
