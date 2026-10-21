"""Sort SBIR-sponsor matches into confidence buckets for hand review."""

import re
import sys

import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 48)
pd.set_option("display.max_rows", 2000)
LEGAL = re.compile(
    r"\b(incorporated|inc|ltd|limited|llc|corp|corporation|co|company|gmbh|ag|sa|plc|bv|nv|spa|kk|pty|srl|ab|as|oy|kg|lp|the)\b"
)
GEN = {
    "pharmaceuticals": "pharma",
    "pharmaceutical": "pharma",
    "pharma": "pharma",
    "biopharma": "biopharma",
    "biopharmaceuticals": "biopharma",
    "biopharmaceutical": "biopharma",
    "therapeutics": "therapeutics",
    "biosciences": "biosciences",
    "bioscience": "biosciences",
    "biotech": "biotech",
    "biotechnology": "biotech",
    "biotechnologies": "biotech",
    "research": "research",
    "development": "development",
    "holdings": "holdings",
    "holding": "holdings",
    "group": "group",
    "international": "international",
    "usa": "usa",
    "us": "usa",
}


def strict(s):
    s = re.sub(r"[^a-z0-9]+", " ", str(s).lower())
    return re.sub(r"\s+", " ", LEGAL.sub(" ", s)).strip()


def generic(s):
    return {GEN[w] for w in strict(s).split() if w in GEN} - {"usa", "international", "group", "holdings"}


m = pd.read_csv(sys.argv[1])
m["strict_eq"] = [strict(a) == strict(b) for a, b in zip(m.lead_sponsor, m.sbir_org)]
ga = [generic(a) for a in m.lead_sponsor]
gb = [generic(b) for b in m.sbir_org]
m["gen_conflict"] = [bool(a) and bool(b) and not (a & b) for a, b in zip(ga, gb)]
m["bucket"] = "review"
m.loc[m.strict_eq, "bucket"] = "accept_strict"
m.loc[~m.strict_eq & m.gen_conflict, "bucket"] = "reject_generic_conflict"
m.loc[m.match.eq("fuzzy"), "bucket"] = "reject_fuzzy_checked"
print(m.bucket.value_counts().to_string())
for b in ("reject_generic_conflict", "review"):
    d = m[m.bucket.eq(b)].sort_values("n_trials", ascending=False)
    print(f"\n## {b} ({len(d)})")
    print(d[["lead_sponsor", "sbir_org", "sbir_state", "n_trials", "sbir_first_fy"]].to_string())
m.to_csv(sys.argv[2], index=False)
