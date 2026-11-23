"""Sponsor names as they stood in April 2015 against the names in the registry snapshot.

Usage: python pilot/sponsor_2015.py CTGOV_ALL_CSV ICTRP_2015_CSV_GZ RESULTS_DIR
(CTGOV_ALL_CSV of fetch_ctgov.py; ICTRP_2015_CSV_GZ of extract_ictrp_2015.py; RESULTS_DIR holds programmes.csv.gz,
phase_entries.csv.gz and sponsors.csv.gz; plan written before the 2015 copy was downloaded: docs/plan_sponsor_2015.md)

A trial "moved in" when it is typed top-20 pharma under the lead sponsor of the snapshot and not under the primary
sponsor of April 2015 (sponsors.top20_parent with the trial's start year in both cases); it "moved out" in the
reverse case. The headline selection and advancement models of robust26.py are fitted again (a) without the
programmes or entries whose first trial moved, and (b) with those rows given the group of the 2015 name: top-20
pharma when the 2015 name is typed so, otherwise the size band that name has in sponsors.csv.gz, and left out when
the name is not there. Writes sponsor_2015.txt and sponsor_2015_moves.csv.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_panel26
import rq2_stops
import sponsors

TOP = "Top-20 pharma"
TIERS = [
    TOP,
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]
SMALL = "C(tier)[T.Industry, small (<=5 drugs)]"


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


def compare(ct, ic):
    """One row per trial of the snapshot found in the 2015 copy, with both names typed for the start year."""
    t = ct.merge(ic, on="nct_id", how="inner")
    t = t[t.sponsor_2015.fillna("").ne("")].copy()
    t["year"] = pd.to_numeric(t.start_date.astype(str).str[:4], errors="coerce")
    t["norm_now"] = t.lead_sponsor.map(rq2_stops.norm_sponsor)
    t["norm_2015"] = t.sponsor_2015.map(rq2_stops.norm_sponsor)
    t["changed"] = t.norm_now.fillna("") != t.norm_2015.fillna("")
    yr = [None if y != y else int(y) for y in t.year]
    industry = t.lead_class.eq("INDUSTRY").to_numpy()
    now = [sponsors.top20_parent(n, y) if i else None for n, y, i in zip(t.lead_sponsor, yr, industry)]
    old = [sponsors.top20_parent(n, y) for n, y in zip(t.sponsor_2015, yr)]
    t["top_now"] = [p is not None for p in now]
    t["top_2015"] = [p is not None for p in old]
    t["moved_in"] = t.top_now & ~t.top_2015
    t["moved_out"] = ~t.top_now & t.top_2015 & industry
    return t


def band_of(name, bands):
    """Size band of a non-top-20 industry name in sponsors.csv.gz, or None."""
    return bands.get(build_panel26.norm_sponsor(name))


def retype(tier, nct, T, bands):
    """Tier under the 2015 name for the rows whose trial moved; None where the 2015 name has no band."""
    out = []
    for tr, n in zip(tier, nct):
        if n not in T.index or not (T.at[n, "moved_in"] or T.at[n, "moved_out"]):
            out.append(tr)
        elif T.at[n, "moved_out"]:
            out.append(TOP)
        else:
            out.append(band_of(T.at[n, "sponsor_2015"], bands))
    return out


def fit(out, f, d, title, keep):
    try:
        r = smf.logit(f, d).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i in keep], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
        out.extend([title, f"N={int(r.nobs)}; events={int(d[f.split('~')[0].strip()].sum())}; converged={r.mle_retvals['converged']}", t.round(4).to_string()])  # fmt: skip
    except Exception as e:
        out.extend([title, f"failed: {e!r}"])


def main(ctgov, ictrp, R):
    out = ["Sponsor names as they stood in April 2015 (plan: docs/plan_sponsor_2015.md)"]
    ct = pd.read_csv(ctgov, usecols=["nct_id", "lead_sponsor", "lead_class", "start_date"], dtype=str)
    ct["nct_id"] = ct.nct_id.str.upper()
    ic = pd.read_csv(ictrp, dtype=str).drop_duplicates("nct_id")
    t = compare(ct, ic)
    out.append(
        f"trials in the registry snapshot: {len(ct)}; ClinicalTrials.gov records in the 2015 copy: {len(ic)}; in both, "
        f"with a 2015 sponsor: {len(t)}"
    )
    ind = t[t.lead_class.eq("INDUSTRY")]
    out.append(
        f"1. normalised sponsor name changed: {int(t.changed.sum())} of {len(t)} ({t.changed.mean():.4f}); among trials "
        f"with an industry lead sponsor today: {int(ind.changed.sum())} of {len(ind)} ({ind.changed.mean():.4f})"
    )
    top = ind[ind.top_now]
    out.append(
        f"2. industry trials typed top-20 pharma today: {len(top)}; not typed top-20 under the 2015 name (moved in): "
        f"{int(top.moved_in.sum())} ({top.moved_in.mean():.4f}); industry trials not typed top-20 today: "
        f"{int((~ind.top_now).sum())}; typed top-20 under the 2015 name (moved out): {int(ind.moved_out.sum())} "
        f"({ind.moved_out.sum() / max(1, int((~ind.top_now).sum())):.4f})"
    )
    mv = t[t.moved_in | t.moved_out]
    moves = (
        mv.assign(direction=np.where(mv.moved_in, "in", "out"))
        .groupby(["direction", "sponsor_2015", "lead_sponsor"])
        .size()
        .rename("trials")
        .reset_index()
        .sort_values(["direction", "trials"], ascending=[True, False])
    )
    moves.to_csv(f"{R}/sponsor_2015_moves.csv", index=False)
    out.append(f"3. pairs of names behind the moves: {len(moves)} (sponsor_2015_moves.csv); the most frequent:")
    out.append(moves.groupby("direction").head(15).to_string(index=False))

    T = t.set_index("nct_id")
    S = pd.read_csv(f"{R}/sponsors.csv.gz", usecols=["sponsor_norm", "sponsor_tier"])
    S = S[S.sponsor_tier.isin(TIERS[1:4])].drop_duplicates("sponsor_norm")
    bands = dict(zip(S.sponsor_norm, S.sponsor_tier))
    P = pd.read_csv(f"{R}/programmes.csv.gz")
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    for D, trial, tier, label in ((P, "first_trial", "first_sponsor_tier", "first trials of programmes"), (E, "entry_trial", "sponsor_tier", "phase-entry trials")):  # fmt: skip
        D["nct"] = D[trial].astype(str).str.upper()
        D["in_2015"] = D.nct.isin(T.index)
        D["moved_in"] = D.nct.map(T.moved_in).fillna(False).astype(bool)
        D["moved_out"] = D.nct.map(T.moved_out).fillna(False).astype(bool)
        D["tier_2015"] = retype(D[tier], D.nct, T, bands)
        D["modality"] = D.drugType.map(mod)
        D["area"] = D.area.fillna("other")
        topd = D[D[tier].eq(TOP)]
        out.append(
            f"{label}: {len(D)}; found in the 2015 copy: {int(D.in_2015.sum())}; typed top-20 today: {len(topd)} "
            f"(in the 2015 copy: {int(topd.in_2015.sum())}); moved in: {int(D.moved_in.sum())}; moved out: "
            f"{int(D.moved_out.sum())}; moved and without a band for the 2015 name: {int(D.tier_2015.isna().sum())}"
        )

    P["yb"] = pd.cut(P.first_year, [0, 2004, 2009, 2014, 2019, 2100], labels=["<=2004", "2005-09", "2010-14", "2015-19", "2020+"]).astype(str)  # fmt: skip
    H = P[P.insight & P.first_sponsor_tier.isin(TIERS)].copy()
    H["y"] = H.gs_ante_first.fillna(False).astype(int)
    f = "y ~ C(tier) + C(yb) + C(area) + C(modality)"
    out.append("=" * 100)
    out.append("Selection (robust.txt, 'H1 gs_ante_first: + first-trial period, area, modality'): small sponsors against top-20 pharma")  # fmt: skip
    for title, d in (
        ("as in robust.txt", H.assign(tier=pd.Categorical(H.first_sponsor_tier, categories=TIERS))),
        (
            "(a) without the programmes whose first trial moved",
            H[~(H.moved_in | H.moved_out)].assign(
                tier=lambda x: pd.Categorical(x.first_sponsor_tier, categories=TIERS)
            ),
        ),  # fmt: skip
        (
            "(b) moved programmes under the group of the 2015 name",
            H[H.tier_2015.notna()].assign(tier=lambda x: pd.Categorical(x.tier_2015, categories=TIERS)),
        ),  # fmt: skip
    ):
        fit(out, f, d, title, (SMALL,))

    end_year = int(E.entry_year.max())
    A = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(TIERS) & E.entry_year.between(2000, end_year - 6)].copy()
    A["gs"], A["adv"] = A.gs_ante.fillna(False).astype(int), A.advanced.astype(int)
    A["yb"] = pd.cut(A.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
    f = "adv ~ gs * C(tier) + C(phase) + C(yb) + C(area) + C(modality)"
    out.append("=" * 100)
    out.append("Advancement (robust.txt, 'Advance: support x sponsor tier'): support, and its interaction with small sponsors")  # fmt: skip
    for title, d in (
        ("as in robust.txt", A.assign(tier=pd.Categorical(A.sponsor_tier, categories=TIERS))),
        (
            "(a) without the entries whose trial moved",
            A[~(A.moved_in | A.moved_out)].assign(tier=lambda x: pd.Categorical(x.sponsor_tier, categories=TIERS)),
        ),  # fmt: skip
        (
            "(b) moved entries under the group of the 2015 name",
            A[A.tier_2015.notna()].assign(tier=lambda x: pd.Categorical(x.tier_2015, categories=TIERS)),
        ),  # fmt: skip
    ):
        fit(out, f, d, title, ("gs", "gs:" + SMALL))
    open(f"{R}/sponsor_2015.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
