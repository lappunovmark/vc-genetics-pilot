"""Do sponsors with SEC Form D private placements pick genetically supported targets, and do they advance more often?

Usage: python formd_models.py RESULTS_DIR   (after build_panel26.py and formd_link.py)
Sample: as in sbir_models.py, programmes and phase entries in indications with genetic insight whose first (entry)
trial was led by a non-top-20 industry sponsor.
formd = the lead sponsor filed a Form D (biotech, pharma or other health care; not a pooled fund) in a calendar year
before the trial's start year. Form D data start in 2009, so the sample is restricted to trials that started in
2010 or later. In the selection models, therapeutic areas with fewer than three supported programmes are pooled
into 'other' to avoid separation.
Writes RESULTS_DIR/formd_models.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops

R = sys.argv[1]
IND = ["Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]
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
FIRST_DATA_YEAR = 2009
fd = pd.read_csv(f"{R}/formd_sponsors.csv")
# three datings of the sponsor's first Form D (see formd_link.py): main rule, own names only, whole CIK history
FIRST = {
    "main": dict(zip(fd.norm, fd.formd_first_year)),
    "own": dict(zip(fd.norm, fd.formd_first_year_own)),
    "cik": dict(zip(fd.norm, fd.formd_first_year_cik)),
}
first = FIRST["main"]
out = []


def fit(f, d, title, keep):
    try:
        r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
        t = r.summary2().tables[1]
        t = t.loc[[i for i in t.index if i in keep], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
        t["OR"] = np.exp(t["Coef."])
        t["OR_lo"] = np.exp(t["[0.025"])
        t["OR_hi"] = np.exp(t["0.975]"])
        out.extend(
            [
                "=" * 100,
                title,
                f,
                f"N={int(r.nobs)}; clusters (drugs)={d.drug.nunique()}; formd share={d.formd.mean():.4f}; "
                f"converged={r.mle_retvals['converged']}",
                t.round(4).to_string(),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def flag(names, years, first=first):
    fy = names.map(lambda s: first.get(rq2_stops.norm_sponsor(s)))
    return (pd.to_numeric(fy, errors="coerce") < years).fillna(False).astype(int)


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_sponsor_tier.isin(IND) & P.first_year.gt(FIRST_DATA_YEAR)].copy()
P["formd"] = flag(P.first_sponsor, P.first_year)
P["tier"] = pd.Categorical(P.first_sponsor_tier, categories=IND)
P["modality"] = P.drugType.map(MOD).fillna("other")
P["area"] = P.area.fillna("other")
P["yb"] = pd.cut(P.first_year, [2009, 2014, 2019, 2100]).astype(str)
out.append(
    "Programmes (insight indications, first trial 2010+ by non-top-20 industry):\n"
    + P.groupby("tier", observed=True)
    .agg(n=("drug", "size"), formd=("formd", "mean"), gs_ante=("gs_ante_first", "mean"))
    .round(4)
    .to_string()
)
out.append(
    P.groupby("formd")
    .agg(n=("drug", "size"), gs_ante=("gs_ante_first", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)
P["y"] = P.gs_ante_first.fillna(False).astype(int)


def pool_sparse(d, col="area", min_events=3):
    """Areas with fewer than three supported programmes go to 'other' (otherwise the logit separates)."""
    ev = d.groupby(col).y.transform("sum")
    return d.assign(**{col: d[col].where(ev.ge(min_events), "other")})


P = pool_sparse(P)
fit(
    "y ~ formd + C(tier) + C(yb) + C(area) + C(modality)",
    P,
    "H1: ex-ante support at first trial ~ prior Form D",
    ("formd",),
)
if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
    # independent measure: dated Open Targets germline evidence (gs_ot_dated.py)
    G = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
    P2 = P.drop(columns="y").merge(G, on=["drug", "indication_mesh_id"], how="left")
    P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
    P2 = pool_sparse(P2)
    fit(
        "y ~ formd + C(tier) + C(yb) + C(area) + C(modality)",
        P2,
        "H1 [dated OT evidence]: ex-ante support ~ prior Form D",
        ("formd",),
    )
S = pool_sparse(P[P.tier.eq("Industry, small (<=5 drugs)")])
fit(
    "y ~ formd + C(yb) + C(area) + C(modality)",
    S,
    "H1, small sponsors only: ex-ante support ~ prior Form D",
    ("formd",),
)

E = pd.read_csv(f"{R}/phase_entries.csv.gz")
end_year = int(E.entry_year.max())
E = E[
    E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND) & E.entry_year.between(FIRST_DATA_YEAR + 1, end_year - 6)
].copy()
E["formd"] = flag(E.lead_sponsor, E.entry_year)
E["tier"] = pd.Categorical(E.sponsor_tier, categories=IND)
E["modality"] = E.drugType.map(MOD).fillna("other")
E["area"] = E.area.fillna("other")
E["yb"] = pd.cut(E.entry_year, [2009, 2014, 2030]).astype(str)
E["gs"] = E.gs_ante.fillna(False).astype(int)
E["adv"] = E.advanced.astype(int)
out.append(
    "Phase entries 2010-%d (non-top-20 industry):\n" % (end_year - 6)
    + E.groupby("formd").agg(n=("drug", "size"), adv=("adv", "mean"), gs=("gs", "mean")).round(4).to_string()
)
base = "C(phase) + C(tier) + C(yb) + C(area) + C(modality)"
fit(f"adv ~ formd + gs + {base}", E, "Advancement ~ prior Form D + ex-ante support", ("formd", "gs"))
fit(f"adv ~ formd * gs + {base}", E, "Advancement ~ prior Form D x ex-ante support", ("formd", "gs", "formd:gs"))

# Intensity: how much the sponsor had raised in Form D offerings before the trial year (nominal USD, amount sold on
# the latest filing of each offering; formd_link.py). Bands: none (no prior Form D), under $10M, $10-50M, $50M or more.
O = pd.read_csv(f"{R}/formd_sponsor_offerings.csv.gz")
HIST = {n: (g.year.to_numpy(), g.sold.fillna(0).to_numpy()) for n, g in O.groupby("norm")}
# equity-only sensitivity: offerings that include equity and are not business combinations (reverse-merger PIPEs)
OE = O[O.equity.astype(bool) & ~O.business_combination.astype(bool)]
HIST_EQ = {n: (g.year.to_numpy(), g.sold.fillna(0).to_numpy()) for n, g in OE.groupby("norm")}
BANDS = ["none", "<$10M", "$10-50M", ">=$50M"]


def raised_before(names, years, hist=HIST):
    """Cumulative USD millions sold in the sponsor's offerings dated before the trial year (0 when none)."""
    out = []
    for s, y in zip(names, years):
        h = hist.get(rq2_stops.norm_sponsor(s))
        out.append(float(h[1][h[0] < y].sum()) / 1e6 if h is not None else 0.0)
    return pd.Series(out, index=names.index)


def band(d, col="raised"):
    r = d[col]
    b = np.select([d.formd.eq(0), r < 10, r < 50], BANDS[:3], default=BANDS[3])
    return pd.Categorical(b, categories=BANDS)


P["raised"] = raised_before(P.first_sponsor, P.first_year)
E["raised"] = raised_before(E.lead_sponsor, E.entry_year)


def has_prior_offering(names, years):
    return pd.Series(
        [(n in HIST) and bool((HIST[n][0] < y).any()) for n, y in zip(names.map(rq2_stops.norm_sponsor), years)],
        index=names.index,
    )


# the offerings table and the first-year flag must agree: a prior Form D means at least one prior offering
assert (has_prior_offering(P.first_sponsor, P.first_year) == P.formd.eq(1)).all()
assert (has_prior_offering(E.lead_sponsor, E.entry_year) == E.formd.eq(1)).all()
P["band"] = band(P)
E["band"] = band(E)
out.append(
    "=" * 100 + "\nAmount raised in Form D offerings before the first trial (USD millions, nominal), programmes:"
)
out.append(
    P.groupby("band", observed=False)
    .agg(n=("drug", "size"), raised_median=("raised", "median"), gs_ante=("y", "mean"), gs_post=("gs_post", "mean"))
    .round(4)
    .to_string()
)
out.append("phase entries:")
out.append(
    E.groupby("band", observed=False)
    .agg(n=("drug", "size"), raised_median=("raised", "median"), adv=("adv", "mean"), gs=("gs", "mean"))
    .round(4)
    .to_string()
)
keep_bands = tuple(f"C(band)[T.{b}]" for b in BANDS[1:])
fit("y ~ C(band) + C(tier) + C(yb) + C(area) + C(modality)", P, "H1: ex-ante support ~ amount raised before the first trial (bands, reference: no prior Form D)", keep_bands)  # fmt: skip
fit(f"adv ~ C(band) + gs + {base}", E, "Advancement ~ amount raised before the entry (bands) + ex-ante support", keep_bands + ("gs",))  # fmt: skip
PF = pool_sparse(P[P.formd.eq(1)].assign(log_raised=lambda d: np.log10(1 + d.raised)))
EF = E[E.formd.eq(1)].assign(log_raised=lambda d: np.log10(1 + d.raised))
fit("y ~ log_raised + C(tier) + C(yb) + C(area) + C(modality)", PF, "H1, Form D filers only: ex-ante support ~ log10(1 + USD millions raised before the first trial)", ("log_raised",))  # fmt: skip
fit(f"adv ~ log_raised + gs + {base}", EF, "Advancement, Form D filers only ~ log10(1 + USD millions raised before the entry) + ex-ante support", ("log_raised", "gs"))  # fmt: skip
fit(f"adv ~ log_raised * gs + {base}", EF, "Advancement, Form D filers only ~ log10(1 + raised) x ex-ante support", ("log_raised", "gs", "log_raised:gs"))  # fmt: skip
# equity-only amounts (debt-only offerings and business-combination placements excluded)
P["raised_eq"] = raised_before(P.first_sponsor, P.first_year, HIST_EQ)
E["raised_eq"] = raised_before(E.lead_sponsor, E.entry_year, HIST_EQ)
PQ = P.assign(band=band(P, "raised_eq"))
EQ = E.assign(band=band(E, "raised_eq"))
out.append(
    "=" * 100
    + "\nSensitivity, equity-only amounts (no debt-only offerings, no business combinations): programmes by band"
)
out.append(PQ.groupby("band", observed=False).agg(n=("drug", "size"), raised_median=("raised_eq", "median"), gs_ante=("y", "mean")).round(4).to_string())  # fmt: skip
fit("y ~ C(band) + C(tier) + C(yb) + C(area) + C(modality)", PQ, "H1 [equity only]: ex-ante support ~ amount raised before the first trial (bands)", keep_bands)  # fmt: skip
fit(f"adv ~ C(band) + gs + {base}", EQ, "Advancement [equity only] ~ amount raised before the entry (bands) + ex-ante support", keep_bands + ("gs",))  # fmt: skip
PFQ = pool_sparse(P[P.formd.eq(1)].assign(log_raised=lambda d: np.log10(1 + d.raised_eq)))
fit("y ~ log_raised + C(tier) + C(yb) + C(area) + C(modality)", PFQ, "H1 [equity only], Form D filers only: ex-ante support ~ log10(1 + USD millions of equity raised)", ("log_raised",))  # fmt: skip

# Sensitivity: the two bounds on the dating of the first Form D
for lab, name in (("own names only (lower bound on history)", "own"), ("whole CIK history (upper bound)", "cik")):
    P2 = P.assign(formd=flag(P.first_sponsor, P.first_year, FIRST[name]))
    E2 = E.assign(formd=flag(E.lead_sponsor, E.entry_year, FIRST[name]))
    out.append("=" * 100 + f"\nSensitivity, first Form D dated by {lab}: formd share programmes={P2.formd.mean():.4f}, "
               f"entries={E2.formd.mean():.4f}")  # fmt: skip
    fit(
        "y ~ formd + C(tier) + C(yb) + C(area) + C(modality)",
        P2,
        f"H1 [{name}]: ex-ante support ~ prior Form D",
        ("formd",),
    )
    fit(f"adv ~ formd + gs + {base}", E2, f"Advancement [{name}] ~ prior Form D + ex-ante support", ("formd", "gs"))
# US-only comparison: only issuers raising money in the US file Form D, so "no prior Form D" mixes non-US sponsors with
# US sponsors that raised no private money. Restrict both groups to sponsors classified as US (sponsor_region.py).
import sponsor_region  # noqa: E402

us_norms, foreign_norms = sponsor_region.financing_locations(f"{R}/formd_match_review.csv")


def region(names):
    return pd.Series(
        [sponsor_region.classify(n, rq2_stops.norm_sponsor(n), us_norms, foreign_norms) for n in names],
        index=names.index,
    )


P["region"] = region(P.first_sponsor)
E["region"] = region(E.lead_sponsor)
out.append("=" * 100 + "\nSponsor region (heuristic, see sponsor_region.py): programmes by region x prior Form D")
out.append(pd.crosstab(P.region, P.formd, margins=True).to_string())
out.append("phase entries by region x prior Form D")
out.append(pd.crosstab(E.region, E.formd, margins=True).to_string())
PU = pool_sparse(P[P.region.eq("US")].copy())
EU = E[E.region.eq("US")].copy()
fit(
    "y ~ formd + C(tier) + C(yb) + C(area) + C(modality)",
    PU,
    "H1, US sponsors only: ex-ante support ~ prior Form D",
    ("formd",),
)
fit(f"adv ~ formd + gs + {base}", EU, "Advancement, US sponsors only ~ prior Form D + ex-ante support", ("formd", "gs"))
fit(
    f"adv ~ formd * gs + {base}",
    EU,
    "Advancement, US sponsors only ~ prior Form D x ex-ante support",
    ("formd", "gs", "formd:gs"),
)
open(f"{R}/formd_models.txt", "w").write("\n".join(out))
print("\n".join(out))
