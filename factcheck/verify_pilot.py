"""Recompute every number quoted in Section 5.1 / abstract of the working paper from the pilot outputs."""

import json

import pandas as pd

R = "../results"
pd.set_option("display.width", 220)
cov = json.load(open(f"{R}/coverage.json"))
print(
    "coverage:",
    {
        k: cov[k]
        for k in ["ot_release", "evidence_rows", "programmes_with_trials", "programmes_with_insight", "phase_entries"]
    },
)
mm = cov["evidence_rows_by_mesh_method"]
tot = sum(mm.values())
anc = sum(v for k, v in mm.items() if k.startswith("ancestor"))
print(
    "mesh mapping shares: xref %.3f name %.3f ancestor %.3f unmapped %.4f"
    % (mm["xref"] / tot, mm["name"] / tot, anc / tot, mm.get("unmapped", 0) / tot)
)
ev = pd.read_parquet("../data/ot/evidence_clinical_precedence", columns=["drugId", "targetId"])
print("evidence drugs (raw drugId)", ev.drugId.nunique(), "targets", ev.targetId.nunique())
ct = pd.read_csv("../data/ctgov_all.csv", usecols=["nct_id", "lead_sponsor", "lead_class"], dtype=str)
print("ctgov rows", len(ct), "unique nct", ct.nct_id.nunique())
# OT trialSponsor == ClinicalTrials.gov lead sponsor?
cr = pd.read_parquet("../data/ot/clinical_report", columns=["id", "origin", "trialSponsor"])
cr = cr[cr.origin.eq("CLINICAL_TRIAL")].copy()
cr["nct_id"] = cr.id.str.upper()
cr["ot_name"] = cr.trialSponsor.map(lambda x: x.get("name") if isinstance(x, dict) else None)
cr["ot_class"] = cr.trialSponsor.map(lambda x: x.get("agencyClass") if isinstance(x, dict) else None)
m = cr.merge(ct, on="nct_id")
print(
    "OT trial reports matched to CT.gov:",
    len(m),
    "of",
    len(cr),
    "| same lead sponsor name: %.4f | same class: %.4f"
    % ((m.ot_name == m.lead_sponsor).mean(), (m.ot_class == m.lead_class).mean()),
)
print(m[m.ot_name != m.lead_sponsor][["nct_id", "ot_name", "lead_sponsor"]].head(8).to_string())
h = pd.read_csv(f"{R}/h1_selection.csv")
print(h[["sponsor_tier", "n_programmes", "gs_ante_first_share", "gs_post_share"]].round(4).to_string())
E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end = int(E.entry_year.max())
T = E[E.insight & ~E.prior_higher & E.entry_year.between(2000, end - 6)]
T6 = T[
    T.sponsor_tier.isin(
        [
            "Top-20 pharma",
            "Industry, large (>30)",
            "Industry, mid (6-30)",
            "Industry, small (<=5 drugs)",
            "Academic/other",
            "Government",
        ]
    )
]
print("entries in main model (6 tiers):", len(T6), "| years", T6.entry_year.min(), T6.entry_year.max())
print("ex-ante support share by tier:")
print(T6.groupby("sponsor_tier").gs_ante.mean().round(4).to_string())
P = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz")
I = P[P.insight]
both = (I.gs_post.fillna(False) & I.gs_ot_post).sum()
print(
    "label agreement: Minikel-supported",
    int(I.gs_post.fillna(False).sum()),
    "OT-supported",
    int(I.gs_ot_post.sum()),
    "both",
    int(both),
)
r = pd.read_csv(f"{R}/rq2_rates.csv")
print(
    r[r.year.between(2018, 2025)].pivot(index="year", columns="group", values="rate_fin_per_1000").round(2).to_string()
)
