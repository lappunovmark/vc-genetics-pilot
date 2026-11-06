"""Date the approvals that count as advancement, so that an approval granted before a phase entry does not count.

Usage: python approval_dates.py OT_DIR RESULTS_DIR CHEMBL_CSV
Inputs: Open Targets clinical reports and evidence (approval reports from EMA and PMDA carry a year), the panel from
build_panel26.py (phase_entries.csv.gz, disease_mesh.csv.gz) and the ChEMBL first-approval years from
fetch_chembl_approval.py (drug level).

For each phase entry that advanced only through an approval (no later higher-phase trial), two dates are looked up:
  indication_approval_year  earliest year of an EMA or PMDA approval report of the same drug x MeSH indication
  drug_first_approval       ChEMBL year of first approval of the drug (any indication)
Advancement variants:
  advanced_dated        approval counts unless a known indication-level year precedes the entry year, or, when no
                        indication-level year is known, unless the drug's first approval precedes the entry year
                        (the drug-level date is a conservative proxy: a later indication can be approved after a
                        drug's first approval, so this variant removes some genuine advancements)
  advanced_dated_known  approval counts only when a known date (indication level, else drug level) is not earlier
                        than the entry year; undated approvals do not count
  advanced_trial_only   a later higher-phase trial only (already in the panel; the strictest bound)
Re-estimates the main advancement models of robust26.py under each variant. Writes RESULTS_DIR/approval_dates.txt
and RESULTS_DIR/approval_dated_entries.csv.gz.
"""

import glob
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

TIERS = [
    "Top-20 pharma",
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]
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


def read(d, cols):
    files = sorted(glob.glob(os.path.join(d, "*.parquet")))
    return pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True)


def indication_approval_years(ot, R):
    """Earliest dated approval year per (parent drug, MeSH indication) from EMA and PMDA approval reports."""
    cr = read(f"{ot}/clinical_report", ["id", "clinicalStage", "source", "year"])
    cr = cr[cr.clinicalStage.eq("APPROVAL") & cr.year.notna()]
    ev = read(f"{ot}/evidence_clinical_precedence", ["drugId", "diseaseId", "clinicalReportId", "clinicalStage"])
    ev = ev[ev.clinicalStage.eq("APPROVAL")].merge(
        cr[["id", "source", "year"]], left_on="clinicalReportId", right_on="id"
    )
    mol = read(f"{ot}/drug_molecule", ["id", "parentId"])
    parent = dict(zip(mol.id, mol.parentId.where(mol.parentId.notna(), mol.id)))
    ev["drug"] = ev.drugId.map(parent).fillna(ev.drugId)
    dm = pd.read_csv(f"{R}/disease_mesh.csv.gz")[["diseaseId", "indication_mesh_id"]]
    ev = ev.merge(dm, on="diseaseId")
    ev["year"] = pd.to_numeric(ev.year, errors="coerce")
    g = ev.groupby(["drug", "indication_mesh_id"]).agg(
        indication_approval_year=("year", "min"), approval_year_sources=("source", lambda x: ";".join(sorted(set(x))))
    )
    return g.reset_index(), cr.source.value_counts().to_dict()


def logit(f, d, title, out, keep=("gs",)):
    try:
        r = smf.logit(f, d).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[
            [i for i in t.index if i in keep or i.startswith("gs:")], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]
        ]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        out.extend(
            [
                "=" * 100,
                title,
                f,
                f"N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}; advanced share={d.adv.mean():.4f}",
                t.round(4).to_string(),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def main(ot, R, chembl_csv):
    out = []
    ind, src_counts = indication_approval_years(ot, R)
    ch = pd.read_csv(chembl_csv)
    ch["first_approval"] = pd.to_numeric(ch.first_approval, errors="coerce")
    drug_first = dict(zip(ch.molecule_chembl_id, ch.first_approval))
    out.append(
        f"dated approval reports by source: {src_counts}; drug x indication pairs with a dated approval: {len(ind)}; "
        f"ChEMBL approved molecules: {len(ch)} ({ch.chembl_release.iloc[0] if len(ch) else '?'}), with a first-approval "
        f"year: {int(ch.first_approval.notna().sum())}"
    )
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    E = E.merge(ind, on=["drug", "indication_mesh_id"], how="left")
    E["drug_first_approval"] = E.drug.map(drug_first)
    appr_only = E.advanced & ~E.advanced_trial_only
    ind_before = E.indication_approval_year.notna() & (E.indication_approval_year < E.entry_year)
    ind_known_ok = E.indication_approval_year.notna() & (E.indication_approval_year >= E.entry_year)
    drug_before = (
        E.indication_approval_year.isna() & E.drug_first_approval.notna() & (E.drug_first_approval < E.entry_year)
    )
    drug_known_ok = (
        E.indication_approval_year.isna() & E.drug_first_approval.notna() & (E.drug_first_approval >= E.entry_year)
    )
    E["approval_before_entry"] = appr_only & (ind_before | drug_before)
    E["advanced_dated"] = E.advanced_trial_only | (appr_only & ~(ind_before | drug_before))
    E["advanced_dated_known"] = E.advanced_trial_only | (appr_only & (ind_known_ok | drug_known_ok))

    end_year = int(E.entry_year.max())
    T = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
    a = T[T.advanced & ~T.advanced_trial_only]
    out.append(
        f"\nPhase entries in the model window: {len(T)}; advanced {int(T.advanced.sum())}, of which by approval only "
        f"{len(a)} ({len(a) / len(T):.4f} of entries)"
    )
    out.append(
        f"  approval-only entries with an indication-level approval year: {int(a.indication_approval_year.notna().sum())}; "
        f"with a drug-level first-approval year: {int(a.drug_first_approval.notna().sum())}; with neither: "
        f"{int((a.indication_approval_year.isna() & a.drug_first_approval.isna()).sum())}"
    )
    out.append(
        f"  approval precedes the entry year: indication level {int((a.indication_approval_year < a.entry_year).sum())}, "
        f"drug level (no indication date) {int(((a.indication_approval_year.isna()) & (a.drug_first_approval < a.entry_year)).sum())}; "
        f"total removed from advancement: {int(a.approval_before_entry.sum())}"
    )
    T["approval_only"] = T.advanced & ~T.advanced_trial_only
    cols = [
        "approval_only",
        "approval_before_entry",
        "advanced",
        "advanced_dated",
        "advanced_dated_known",
        "advanced_trial_only",
    ]
    by_phase = T.groupby("phase")[cols].mean().assign(entries=T.groupby("phase").size())
    out.append(
        "  by phase (share of entries advanced by approval only, with an approval dated before entry, and advanced under "
        "each definition):\n" + by_phase[["entries"] + cols].round(4).to_string()
    )
    by_tier = T.groupby("sponsor_tier")[cols[1:4]].mean().assign(entries=T.groupby("sponsor_tier").size())
    out.append("  by sponsor tier:\n" + by_tier[["entries"] + cols[1:4]].round(4).to_string())

    T["tier"] = pd.Categorical(T.sponsor_tier, categories=TIERS)
    T["gs"] = T.gs_ante.fillna(False).astype(int)
    T["modality"] = T.drugType.map(MOD).fillna("other")
    T["area"] = T.area.fillna("other")
    T["yb"] = pd.cut(T.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
    base = "C(phase) + C(yb) + C(area) + C(modality)"
    for col, lab in (
        ("advanced", "main (approval counts, undated)"),
        ("advanced_dated", "dated: approvals known to precede the entry removed"),
        ("advanced_dated_known", "dated, known only: undated approvals do not count"),
        ("advanced_trial_only", "trial only"),
    ):
        T["adv"] = T[col].astype(int)
        logit(f"adv ~ gs + C(tier) + {base}", T, f"Advance [{lab}]: main effects", out)
        I = T[T.tier.isin(TIERS[:4])].copy()
        I["tier"] = I.tier.cat.remove_unused_categories()
        logit(f"adv ~ gs * C(tier) + {base}", I, f"Advance [{lab}], industry only: support x tier", out, keep=())
    E[
        ["drug", "indication_mesh_id", "phase", "entry_trial", "entry_year", "indication_approval_year",
         "approval_year_sources", "drug_first_approval", "approval_before_entry", "advanced", "advanced_dated",
         "advanced_dated_known", "advanced_trial_only"]
    ].to_csv(f"{R}/approval_dated_entries.csv.gz", index=False)  # fmt: skip
    open(f"{R}/approval_dates.txt", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
