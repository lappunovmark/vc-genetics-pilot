"""When genetic evidence about a target-indication pair is published, who starts programmes on it? Exploratory.

Usage: python pilot/evidence_arrival.py RESULTS_DIR MINIKEL_DATA_DIR [OT_DATED_CSV gwas|all]
(RESULTS_DIR after build_panel26.py; MINIKEL_DATA_DIR = data/ of ericminikel/genetic_support @ b84cf05.)
With OT_DATED_CSV (the file of extract_ot_dated.py) the evidence years come from that Open Targets release instead of
the Minikel associations ("gwas": GWAS credible sets only; "all": every germline source), pairs whose supporting
evidence carries no date are left out in place of the OMIM pairs, and the output is evidence_arrival_ot_<set>.txt
(plan written before the run: docs/plan_evidence_arrival_ot.md) with the venture split of section F in
evidence_arrival_ot_<set>_venture.txt (plan: docs/plan_evidence_arrival_venture.md).
Environment, for checks added after the planned runs: EA_LAST_EVIDENCE_YEAR=2022 leaves out pairs whose evidence
year is later (output suffix _to2022); EA_UNDATED=only leaves out a pair only when none of its supporting evidence
carries a date, which is the wording of the plan (output suffix _planrule; the first run left out every pair with
a source whose evidence is undated, also when another source dates it).
For the check planned in docs/plan_top20_2010.md: EA_TOP20=2010 defines the top-20 group by 2010 sales
(sponsors.TOP20_2010; EA_TOP20=2010x the same without Teva; output suffix _top2010 or _top2010x), a sponsor that
leaves the group being typed by the size of its portfolio; EA_FIRST_EVIDENCE_YEAR=2010 leaves out pairs whose
evidence year is earlier (output suffix _from2010).

Why: the selection models compare sponsors at one point in time and are descriptive. This script uses the timing of
the evidence instead. For a target-indication pair (the gene a drug acts on x the MeSH indication), the year in which
the first dated genetic association supporting the pair was published is taken as an information shock, and the
number of new programmes on the pair is followed before and after it.

Unit: gene x indication pair with at least one programme in an indication with genetic insight, years 2000-2025.
Evidence year E: the earliest year of a supporting association from a dated source (Open Targets Genetics with L2G
share >= 0.5, PICCOLO, Genebass), support defined as in gensup.py (MeSH similarity >= 0.8). Pairs with OMIM support
are left out because OMIM carries no dates here. Pairs never supported are the comparison group.
Outcome: programmes (drug x indication) whose first trial started in the year, by the tier of the first sponsor; a
drug with several targets counts once for each pair.
Model: Poisson with pair and year fixed effects (pyfixest.fepois), standard errors clustered by indication.
  post = year > E (the ex-ante rule of the pilot: an association counts from the year after its publication);
  the year E itself has its own indicator.
The event study replaces post by bins of years since E, the two years before E being the reference.
Starts on a pair decline over its life whether or not evidence arrives (placebo E), so the before-after change of
one group is not an effect of the evidence. The contrast between sponsor groups on the same pairs (D) removes that
common decline; it rests on the groups following the same path without the evidence, which the placebo of the
contrast and the leads of D6 check. The contrast is measured against each group's own calendar trend on the other
pairs (year x group effects): the raw rates on pairs with evidence fall by a similar proportion in both groups, and
the groups differ because other industry sponsors started more programmes over time elsewhere and top-20 pharma
fewer. Nothing in the first run (Minikel associations) was pre-specified; the runs on Open Targets evidence and
section F follow plans written before them, and section G was added after their results were known.
Writes RESULTS_DIR/evidence_arrival.txt (or evidence_arrival_ot_<set>.txt).
"""

import os
import sys

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gensup
import sponsors

R, MIN = sys.argv[1], sys.argv[2]
OT_CSV, OT_SET = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else (None, None)
SUF = f"_to{os.environ['EA_LAST_EVIDENCE_YEAR']}" if os.environ.get("EA_LAST_EVIDENCE_YEAR") else ""
ONLY_UNDATED = os.environ.get("EA_UNDATED") == "only"
SUF += "_planrule" if ONLY_UNDATED else ""
TOP20_SET = os.environ.get("EA_TOP20")  # None (the pilot's group), "2010" or "2010x"
FIRST_E = os.environ.get("EA_FIRST_EVIDENCE_YEAR")
SUF += (f"_top{TOP20_SET}" if TOP20_SET else "") + (f"_from{FIRST_E}" if FIRST_E else "")
Y0, Y1 = 2000, 2025
TOP, SMALL = "Top-20 pharma", "Industry, small (<=5 drugs)"
MIDLARGE = ["Industry, large (>30)", "Industry, mid (6-30)"]
PUBLIC = ["Academic/other", "Government"]
GROUPS = {
    "all sponsors": None,
    "top-20 pharma": [TOP],
    "other industry": [SMALL] + MIDLARGE,
    "industry, small": [SMALL],
    "industry, mid and large": MIDLARGE,
    "academic and government": PUBLIC,
}
DATED = ("OTG", "PICCOLO", "Genebass")
BINS = [(-99, -6, "m6+"), (-5, -3, "m5_3"), (0, 0, "e0"), (1, 2, "p1_2"), (3, 5, "p3_5"), (6, 99, "p6+")]
out, NOTE = [], []
CL = "indication_mesh_id"


def evidence_years(pairs):
    """First dated supporting association per pair, and whether OMIM supports the pair."""
    assoc = pd.read_csv(f"{MIN}/assoc.tsv.gz", sep="\t", low_memory=False)
    sim = pd.read_csv(f"{MIN}/sim.tsv.gz", sep="\t")
    a = gensup.filter_assoc(assoc)
    dated = DATED
    if OT_CSV:  # evidence of one Open Targets release, mapped to MeSH with the panel's disease map
        dm = pd.read_csv(f"{R}/disease_mesh.csv.gz")[["diseaseId", "indication_mesh_id"]]
        a = pd.read_csv(OT_CSV).merge(dm.rename(columns={"indication_mesh_id": "mesh_id"}), on="diseaseId")
        if OT_SET == "gwas":
            a = a[a.source.eq("gwas_credible_sets")]
        a = a.groupby(["gene", "mesh_id", "source"]).year.min().reset_index()
        dated = tuple(a.source.unique())
        a.loc[a.year.isna(), "source"] = "OMIM"  # undated evidence is handled as OMIM is: the pair is left out
    sp = gensup.similar_pairs(sim)
    u = pairs.indication_mesh_id.unique()
    sp = pd.concat([sp, pd.DataFrame({"meshcode_a": u, "meshcode_b": u})]).drop_duplicates()
    m = pairs.merge(sp, left_on="indication_mesh_id", right_on="meshcode_a").merge(
        a, left_on=["gene", "meshcode_b"], right_on=["gene", "mesh_id"]
    )
    key = ["gene", "indication_mesh_id"]
    e = m[m.source.isin(dated)].groupby(key).year.min().rename("E").reset_index()
    o = m[m.source.eq("OMIM")][key].drop_duplicates().assign(omim=True)
    r = pairs.merge(e, on=key, how="left").merge(o, on=key, how="left")
    r["omim"] = r.omim.eq(True)
    if ONLY_UNDATED:  # the wording of the plan: left out only when no supporting evidence carries a date
        NOTE.append(
            f"EA_UNDATED=only: {int((r.omim & r.E.notna()).sum())} pairs with undated evidence from one source and "
            "dated evidence from another are kept with the dated year"
        )
        r["omim"] = r.omim & r.E.isna()
    return r


def tidy(m, keep):
    t = m.tidy().loc[keep, ["Estimate", "Std. Error", "Pr(>|t|)", "2.5%", "97.5%"]]
    t["RR"] = np.exp(t["Estimate"])
    t["RR_lo"] = np.exp(t["2.5%"])
    t["RR_hi"] = np.exp(t["97.5%"])
    return t.round(4).to_string()


def fit(d, ycol, title, fe="pid + year", terms=("post", "e0"), cl=CL):
    d = d[d.groupby("pid")[ycol].transform("sum") > 0]  # pairs without a start add nothing to a fixed-effects Poisson
    try:
        m = pf.fepois(f"{ycol} ~ {' + '.join(terms)} | {fe}", data=d, vcov={"CRV1": cl})
        tr = d[d.E.notna()]
        out.extend(
            [
                "=" * 100,
                title,
                f"{ycol} ~ {' + '.join(terms)} | {fe}; pairs={d.pid.nunique()} (with dated evidence {tr.pid.nunique()}); "
                f"programme starts={int(d[ycol].sum())} (on pairs with evidence {int(tr[ycol].sum())}, after it "
                f"{int(tr[tr.post.eq(1)][ycol].sum())})",
                tidy(m, list(terms)),
            ]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f"failed: {e!r}"])


P = pd.read_csv(f"{R}/programmes.csv.gz")
P = P[P.insight & P.first_year.between(Y0, Y1)]
PARENT = sponsors.top20_parent
if TOP20_SET:  # the top-20 group defined by 2010 sales (docs/plan_top20_2010.md)
    WITHOUT = ("Teva",) if TOP20_SET == "2010x" else ()
    keep = set(sponsors.TOP20_2010) - set(WITHOUT)

    def PARENT(name, year):  # noqa: N802
        p = sponsors.top20_parent_2010(name, year)
        return p if p in keep else None

    S = pd.read_csv(f"{R}/sponsors.csv.gz", usecols=["lead_sponsor", "sponsor_n_drugs"]).drop_duplicates("lead_sponsor")
    size = P.first_sponsor.map(S.set_index("lead_sponsor").sponsor_n_drugs)
    was = P.first_sponsor_tier.eq(TOP)
    P = P.assign(
        first_sponsor_tier=[
            sponsors.tier_2010(n, y, c, t, k, WITHOUT)
            for n, y, c, t, k in zip(P.first_sponsor, P.first_year, P.first_class, P.first_sponsor_tier, size)
        ]
    )
    now = P.first_sponsor_tier.eq(TOP)
    NOTE.append(
        f"EA_TOP20={TOP20_SET}: top-20 group defined by 2010 sales ({len(keep)} companies); {int((was & ~now).sum())} "
        f"programmes leave the group and {int((~was & now).sum())} enter (of {int(was.sum())} in the pilot's group)"
    )
T = pd.read_csv(f"{R}/programme_targets.csv.gz")
D = P.merge(T, on=["drug", "indication_mesh_id"])
pairs = evidence_years(D[["gene", "indication_mesh_id"]].drop_duplicates())
out.append("Programme starts around the publication of genetic evidence (exploratory; see the module docstring)")
out.append(
    f"pairs with a programme started {Y0}-{Y1} in an indication with genetic insight: {len(pairs)}; with OMIM support "
    f"(left out): {int(pairs.omim.sum())}; with dated evidence and no OMIM: {int((pairs.E.notna() & ~pairs.omim).sum())}; "
    f"never supported: {int((pairs.E.isna() & ~pairs.omim).sum())}"
)
out.extend(NOTE)
pairs = pairs[~pairs.omim].copy()
if FIRST_E:
    n0 = len(pairs)
    pairs = pairs[pairs.E.isna() | (pairs.E >= int(FIRST_E))].copy()
    out.append(f"{n0 - len(pairs)} pairs with an evidence year before {FIRST_E} left out (docs/plan_top20_2010.md)")
LAST_E = os.environ.get("EA_LAST_EVIDENCE_YEAR")  # robustness: leave out pairs whose evidence year is later
if LAST_E:
    n0 = len(pairs)
    pairs = pairs[pairs.E.isna() | (pairs.E <= int(LAST_E))].copy()
    out.append(
        f"robustness run: {n0 - len(pairs)} pairs with an evidence year after {LAST_E} left out (too little follow-up)"
    )
pairs["pid"] = np.arange(len(pairs))
area = P.groupby("indication_mesh_id").area.agg(lambda x: x.fillna("other").mode().iat[0])
pairs["area"] = pairs.indication_mesh_id.map(area).fillna("other")
ev = pairs[pairs.E.notna()]
out.append(
    "evidence year of the pairs with dated evidence: "
    + ev.E.astype(int).value_counts().sort_index().to_dict().__repr__()
)

D = D.merge(pairs[["gene", "indication_mesh_id", "pid"]], on=["gene", "indication_mesh_id"])
grid = pairs[["pid", "gene", "indication_mesh_id", "area", "E"]].merge(
    pd.DataFrame({"year": range(Y0, Y1 + 1)}), how="cross"
)
for g, tiers in GROUPS.items():
    d = D if tiers is None else D[D.first_sponsor_tier.isin(tiers)]
    n = d.groupby(["pid", "first_year"]).size().rename(g).reset_index().rename(columns={"first_year": "year"})
    grid = grid.merge(n, on=["pid", "year"], how="left")
    grid[g] = grid[g].fillna(0).astype(int)
grid = grid.rename(columns={g: f"y{i}" for i, g in enumerate(GROUPS)})
for col, tiers in (("n_top", [TOP]), ("n_other", [SMALL] + MIDLARGE)):  # novel programmes: the drug's first indication
    d = D[D.first_sponsor_tier.isin(tiers) & D.is_drug_first_indication.eq(True)]
    n = d.groupby(["pid", "first_year"]).size().rename(col).reset_index().rename(columns={"first_year": "year"})
    grid = grid.merge(n, on=["pid", "year"], how="left")
    grid[col] = grid[col].fillna(0).astype(int)
YC = {g: f"y{i}" for i, g in enumerate(GROUPS)}
rel = grid.year - grid.E
grid["post"] = (rel > 0).astype(int)
grid["e0"] = (rel == 0).astype(int)
for lo, hi, name in BINS:
    grid[name.replace("+", "plus")] = rel.between(lo, hi).astype(int)
ES = [n.replace("+", "plus") for _, _, n in BINS]
grid["ay"] = pd.factorize(grid.area + "_" + grid.year.astype(str))[0]
grid["gy"] = pd.factorize(grid.gene + "_" + grid.year.astype(str))[0]

tr = grid[grid.E.notna()]
out.append(
    "\nprogramme starts on pairs with dated evidence, by years since the evidence year (all sponsors / top-20 / other industry / academic and government):"
)
tab = tr.assign(
    k=pd.cut(
        tr.year - tr.E, [-99, -6, -3, -1, 0, 2, 5, 99], labels=["<=-6", "-5..-3", "-2..-1", "0", "1..2", "3..5", ">=6"]
    )
)
tab = tab.groupby("k", observed=True).agg(pair_years=("pid", "size"), all=(YC["all sponsors"], "sum"), top20=(YC["top-20 pharma"], "sum"), other_industry=(YC["other industry"], "sum"), public=(YC["academic and government"], "sum"))  # fmt: skip
for c in ("all", "top20", "other_industry", "public"):
    tab[f"{c}_per_1000"] = (1000 * tab[c] / tab.pair_years).round(2)
out.append(tab.to_string())

for g, y in YC.items():
    fit(grid, y, f"A. {g}: programme starts after the evidence year (pair and year fixed effects)")
for g in ("all sponsors", "top-20 pharma", "other industry"):
    fit(grid, YC[g], f"B. {g}: with therapeutic area x year fixed effects", fe="pid + ay")
for g in ("all sponsors", "top-20 pharma", "other industry", "academic and government"):
    fit(grid, YC[g], f"C. {g}: event study, reference = the two years before the evidence year", terms=tuple(ES))


# D. do other sponsors respond differently from top-20 pharma? Stacked: two outcomes per pair-year, with pair x group
# and year x group fixed effects, so the coefficient on post_other is the ratio of the two responses. The decline of
# starts over a pair's life (the placebo in E) is common to the groups and drops out of this contrast.
def stacked(
    d,
    other,
    title,
    by_area=False,
    terms=("post", "e0"),
    show=("post", "post_other"),
    top=None,
    both=False,
    cl=CL,
    tfe=None,
):
    c0, c1 = top or YC["top-20 pharma"], YC.get(other, other)
    if both:  # only pairs on which each of the two groups started at least one programme
        ok = (d.groupby("pid")[c0].transform("sum") > 0) & (d.groupby("pid")[c1].transform("sum") > 0)
        d = d[ok]
    s2 = pd.concat([d.assign(y=d[c0], grp=0), d.assign(y=d[c1], grp=1)])
    s2["pg"] = s2.pid * 2 + s2.grp
    tcol = tfe or ("ay" if by_area else "year")  # the time effect: year, area x year or gene x year
    s2["yg"] = s2[tcol] * 2 + s2.grp
    rhs = list(terms)
    for t in terms:
        s2[f"{t}_other"] = s2[t] * s2.grp
        rhs.append(f"{t}_other")
    s2 = s2[s2.groupby("pg").y.transform("sum") > 0]
    try:
        m = pf.fepois(f"y ~ {' + '.join(rhs)} | pg + yg", data=s2, vcov={"CRV1": cl})
        fe = (
            "pair x group + " + {"year": "year x group", "ay": "area x year x group", "gy": "gene x year x group"}[tcol]
        )
        out.extend(
            ["=" * 100, title, f"y ~ {' + '.join(rhs)} | {fe}; pair-groups={s2.pg.nunique()}", tidy(m, list(show))]
        )
    except Exception as e:
        out.extend(["=" * 100, title, f"failed: {e!r}"])


stacked(grid, "other industry", "D1. other industry against top-20 pharma (post_other = ratio of the two responses)")
stacked(grid, "other industry", "D2. the same with therapeutic area x year x group fixed effects", by_area=True)
stacked(grid, "industry, small", "D3. small industry sponsors against top-20 pharma")
stacked(grid, "industry, mid and large", "D4. mid-sized and large industry sponsors against top-20 pharma")
stacked(grid, "academic and government", "D5. academic and government sponsors against top-20 pharma")
stacked(grid, "other industry", "D9. D1 with standard errors clustered by gene", cl="gene")
stacked(grid, "other industry", "D7. D1 on pairs where both groups started at least one programme", both=True)
stacked(grid, "n_other", "D8. D1 for novel programmes only (the drug's first indication)", top="n_top")
stacked(
    grid,
    "other industry",
    "D6. event study of the contrast (reference = the two years before the evidence year; *_other = ratio to top-20)",
    terms=tuple(ES),
    show=tuple(f"{t}_other" for t in ES),
)

# E. placebo: shift the evidence year five years earlier and use only years before the true evidence year
pl = grid[grid.E.isna() | (grid.year < grid.E)].copy()
pl["post"] = ((pl.year - (pl.E - 5)) > 0).astype(int)
pl["e0"] = ((pl.year - (pl.E - 5)) == 0).astype(int)
for g in ("all sponsors", "top-20 pharma", "other industry"):
    fit(pl, YC[g], f"E. placebo, {g}: evidence year moved five years earlier, years before the true evidence year only")
stacked(pl, "other industry", "E. placebo of the contrast D1: other industry against top-20 pharma")


# F. venture-backed sponsors (plan written before the run: docs/plan_evidence_arrival_venture.md). Needs the sponsor
# tables of owners_link.py, ritter_models.py, cb_models.py and formd_directors.py; written to a file of its own.
def venture_norms():
    import rq2_stops

    vc = set()
    for name, col, flag in (
        ("owners_sponsors.csv", "norm", lambda d: d.vc_backed.astype(bool)),
        ("ritter_sponsors.csv", "first_sponsor", lambda d: d.ritter_vc.astype(bool)),
        ("cb_sponsors.csv", "first_sponsor", lambda d: d.first_vc_round_year.notna()),
        ("formd_directors_sponsors.csv", "norm", lambda d: d.first_vc_board_year.notna()),
    ):
        path = f"{R}/{name}"
        if not os.path.exists(path):
            return None
        d = pd.read_csv(path, dtype={"norm": str})
        n = d[col] if col == "norm" else d[col].map(rq2_stops.norm_sponsor)
        vc |= set(n[flag(d)].dropna())
    return vc


VC = venture_norms() if OT_CSV else None
if VC is not None:
    import rq2_stops

    main_out, out = out, []
    ind = D[D.first_sponsor_tier.isin([SMALL] + MIDLARGE)].copy()
    ind["vc"] = ind.first_sponsor.map(rq2_stops.norm_sponsor).isin(VC)
    for col, d in (("v_yes", ind[ind.vc]), ("v_no", ind[~ind.vc])):
        n = d.groupby(["pid", "first_year"]).size().rename(col).reset_index().rename(columns={"first_year": "year"})
        grid = grid.merge(n, on=["pid", "year"], how="left")
        grid[col] = grid[col].fillna(0).astype(int)
    pl = grid[grid.E.isna() | (grid.year < grid.E)].copy()
    pl["post"] = ((pl.year - (pl.E - 5)) > 0).astype(int)
    pl["e0"] = ((pl.year - (pl.E - 5)) == 0).astype(int)
    ind["norm"] = ind.first_sponsor.map(rq2_stops.norm_sponsor)
    sp = ind.drop_duplicates("norm")  # sponsors, not spellings of their names in the registry
    out.append(
        "Venture-backed sponsors and the publication of genetic evidence (plan: docs/plan_evidence_arrival_venture.md)"
    )
    out.append(
        f"evidence set: {OT_SET}; non-top-20 industry sponsors with a programme on these pairs: {len(sp)}; venture-backed "
        f"by at least one source: {int(sp.vc.sum())}; programme starts: venture-backed {int(grid.v_yes.sum())}, "
        f"no venture marker {int(grid.v_no.sum())}, top-20 pharma {int(grid[YC['top-20 pharma']].sum())}"
    )
    fit(grid, "v_yes", "F1. venture-backed industry sponsors: programme starts after the evidence year")
    fit(grid, "v_no", "F2. industry sponsors without a venture marker: programme starts after the evidence year")
    stacked(grid, "v_yes", "F3 (primary). venture-backed industry sponsors against top-20 pharma")
    stacked(grid, "v_no", "F4. industry sponsors without a venture marker against top-20 pharma")
    stacked(grid, "v_yes", "F5. venture-backed against industry sponsors without a venture marker", top="v_no")
    stacked(grid, "v_yes", "F6. F3 with therapeutic area x year x group fixed effects", by_area=True)
    stacked(grid, "v_yes", "F7. F3 with standard errors clustered by gene", cl="gene")
    stacked(
        pl,
        "v_yes",
        "F8. placebo of F3: evidence year moved five years earlier, years before the true evidence year only",
    )
    stacked(pl, "v_yes", "F9. placebo of F5", top="v_no")
    open(f"{R}/evidence_arrival_ot_{OT_SET}{SUF}_venture.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    out = main_out

# G. how concentrated is the response? Added after the results of D were known (not in the plan).
if OT_CSV:
    tp = D[D.first_sponsor_tier.eq(TOP)].merge(pairs[["pid", "E"]], on="pid")
    tp = tp[tp.first_year > tp.E]
    by_gene = tp.groupby("gene").size().sort_values(ascending=False)
    out.extend(
        [
            "=" * 100,
            "G. concentration of the top-20 response (added after the results above were known)",
            f"top-20 programme starts after the evidence year: {len(tp)} on {tp.pid.nunique()} pairs; genes "
            f"{tp.gene.nunique()}; indications {tp.indication_mesh_id.nunique()}; drugs {tp.drug.nunique()}; programmes "
            f"{len(tp.drop_duplicates(['drug', 'indication_mesh_id']))}",
            "genes with the most such starts: " + "; ".join(f"{g} {n}" for g, n in by_gene.head(5).items()),
        ]
    )
    lead = list(by_gene.index[:3])
    for g in lead:
        stacked(grid[grid.gene.ne(g)], "other industry", f"G. D1 without the pairs of {g}")
    stacked(grid[~grid.gene.isin(lead)], "other industry", "G. D1 without the pairs of these three genes")
    fit(grid[~grid.gene.isin(lead)], YC["top-20 pharma"], "G. top-20 pharma without the pairs of these three genes")

    # what the starts are: new drugs or new indications of drugs already in trials
    def kind(t, label):
        first = int(t.is_drug_first_indication.eq(True).sum())
        before = int((t.drug_first_year <= t.E).sum())
        return (
            f"{label}: {len(t)} starts; the drug's first indication {first}; a further indication of a drug first tried "
            f"after the evidence year {len(t) - first - int((~t.is_drug_first_indication.eq(True) & (t.drug_first_year <= t.E)).sum())}; "
            f"a further indication of a drug already in trials by the evidence year "
            f"{int((~t.is_drug_first_indication.eq(True) & (t.drug_first_year <= t.E)).sum())} "
            f"(drug in trials by the evidence year, either kind: {before})"
        )

    ot = D[D.first_sponsor_tier.isin([SMALL] + MIDLARGE)].merge(pairs[["pid", "E"]], on="pid")
    ot = ot[ot.first_year > ot.E]
    out.extend(
        [
            "",
            "what the programme starts after the evidence year are (added after the results were known):",
            kind(tp, "top-20 pharma, all genes"),
            kind(tp[tp.gene.isin(lead)], "top-20 pharma, the three leading genes"),
            kind(tp[~tp.gene.isin(lead)], "top-20 pharma, other genes"),
            kind(ot, "other industry, all genes"),
        ]
    )
    cols = ["gene", "indication_mesh_id", "area", "drug", "drugType", "first_sponsor", "first_year", "E", "drug_first_year", "is_drug_first_indication"]  # fmt: skip
    tp.assign(E=tp.E.astype(int))[cols].sort_values(["gene", "drug", "first_year", "indication_mesh_id"]).rename(
        columns={"E": "evidence_year"}
    ).to_csv(f"{R}/evidence_arrival_ot_{OT_SET}{SUF}_top20_starts.csv", index=False)
    # within one target and year: pairs with evidence against the other indications of the same gene
    fit(grid, YC["top-20 pharma"], "G. top-20 pharma with gene x year fixed effects (other indications of the same target as the comparison)", fe="pid + gy")  # fmt: skip
    fit(grid, YC["other industry"], "G. other industry with gene x year fixed effects", fe="pid + gy")
    stacked(grid, "other industry", "G. D1 with gene x year x group fixed effects", tfe="gy")

    # which companies carry the response, and does the size of a sponsor outside the top 20 matter?
    def add_count(g, d, col):
        n = d.groupby(["pid", "first_year"]).size().rename(col).reset_index().rename(columns={"first_year": "year"})
        g = g.merge(n, on=["pid", "year"], how="left")
        g[col] = g[col].fillna(0).astype(int)
        return g

    dt = D[D.first_sponsor_tier.eq(TOP)].copy()
    dt["parent"] = [PARENT(n, y) or "?" for n, y in zip(dt.first_sponsor, dt.first_year)]
    by_parent = tp.assign(parent=[PARENT(n, y) or "?" for n, y in zip(tp.first_sponsor, tp.first_year)])
    by_parent = by_parent.groupby("parent").size().sort_values(ascending=False)
    out.extend(
        [
            "=" * 100,
            "G. companies behind the top-20 response (added after the results were known)",
            "top-20 programme starts after the evidence year by company: "
            + "; ".join(f"{k} {v}" for k, v in by_parent.items()),
        ]
    )
    loo = []
    for par in sorted(dt.parent.unique()):
        g2 = add_count(grid, dt[dt.parent.ne(par)], "y_loo")
        n0 = len(out)
        stacked(g2, "other industry", f"loo {par}", top="y_loo")
        row = [x for x in out[n0:] if x.startswith("post_other") or "\npost_other" in x]
        del out[n0:]
        if row:
            v = [ln for ln in row[0].splitlines() if ln.startswith("post_other")][0].split()
            loo.append((par, float(v[-3]), float(v[-2]), float(v[-1])))
    out.append("D1 with each top-20 company left out in turn (ratio, 95% CI):")
    out.extend(f"  without {par:24s} {e:.4f}  {lo:.4f}  {hi:.4f}" for par, e, lo, hi in loo)
    out.append(
        f"range of the contrast: {min(x[1] for x in loo):.4f} to {max(x[1] for x in loo):.4f}; largest upper bound "
        f"{max(x[3] for x in loo):.4f}"
    )
    top3c = list(by_parent.index[:3])
    g2 = add_count(grid, dt[~dt.parent.isin(top3c)], "y_loo")
    stacked(g2, "other industry", "G. D1 without the three companies with the most such starts: " + ", ".join(top3c), top="y_loo")  # fmt: skip
    for col, tiers, lab in (("n_large", [MIDLARGE[0]], "large (>30 drugs)"), ("n_mid", [MIDLARGE[1]], "mid-sized (6-30 drugs)")):  # fmt: skip
        grid = add_count(grid, D[D.first_sponsor_tier.isin(tiers)], col)
        stacked(grid, col, f"G. {lab} industry sponsors outside the top 20 against top-20 pharma")

    # H. the same design with the target as the unit: all indications of a gene together, evidence year = the first
    # year in which one of its pairs gained evidence. Added after G showed that the response is not specific to the
    # indication.
    yc = [YC["top-20 pharma"], YC["other industry"]]
    gg = grid.groupby(["gene", "year"])[yc].sum().reset_index()
    gg["E"] = gg.gene.map(pairs.groupby("gene").E.min())
    gg["pid"] = pd.factorize(gg.gene)[0]
    gg["post"] = (gg.year > gg.E).astype(int)
    gg["e0"] = (gg.year == gg.E).astype(int)
    gp = gg[gg.E.isna() | (gg.year < gg.E)].copy()
    gp["post"] = ((gp.year - (gp.E - 5)) > 0).astype(int)
    gp["e0"] = ((gp.year - (gp.E - 5)) == 0).astype(int)
    out.extend(
        [
            "=" * 100,
            "H. the target as the unit (added after G): programme starts on a gene in all its indications, before and "
            "after the first year in which one of its pairs gained evidence; errors clustered by gene",
            f"genes: {gg.gene.nunique()}; with evidence: {gg[gg.E.notna()].gene.nunique()}",
        ]
    )
    fit(gg, yc[0], "H1. top-20 pharma, target level", cl="gene")
    fit(gg, yc[1], "H2. other industry, target level", cl="gene")
    stacked(gg, yc[1], "H3. other industry against top-20 pharma, target level", cl="gene")
    stacked(gg[~gg.gene.isin(lead)], yc[1], "H4. H3 without the three leading genes", cl="gene")
    stacked(gp, yc[1], "H5. placebo of H3: evidence year moved five years earlier", cl="gene")

open(f"{R}/evidence_arrival_ot_{OT_SET}{SUF}.txt" if OT_CSV else f"{R}/evidence_arrival.txt", "w").write(
    "\n".join(out) + "\n"
)
print("\n".join(out))
