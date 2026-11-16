"""Why do small sponsors start fewer genetically supported programmes? Exploratory checks.

Usage: python pilot/h1_mechanisms.py RESULTS_DIR CTGOV_ALL.csv CTGOV_ENROLLMENT.csv [MOLECULE_SYNONYMS.csv.gz]
These checks test alternative explanations of the small-sponsor gap in selection (H1, adjusted OR 0.68). Nothing
here was pre-specified: the splits were chosen after the H1 result was known, so p-values are descriptive.
  A. Type of evidence. Ex-ante support is split into support from dated population genetics (OTG, PICCOLO,
     Genebass: an association dated before the year of the first trial) and support from OMIM only
     (Mendelian; OMIM carries no dates in this pipeline and always counts as ex ante, so "OMIM only" is not a dated
     measure). The split is read from the programme's first phase entry; when that entry is in a later year than the
     first trial and shows dated evidence, the type at the first trial is unknown and the programme is left out.
     A4 shows where the adjusted gap comes from (the raw gap is small; the first-trial period is the control that
     opens it, because small sponsors' programmes are more recent and dated support grows over time), A5 repeats the
     split with ex-post support (no dates on either type), A6 splits novel drugs from follow-on indications.
  B. Partnerships. A small sponsor that develops a drug with a large company borrows its money and its selection.
     Registry proxies: a top-20 or any industry collaborator on the programme's first trial; the same drug led by a
     top-20 company in a phase-entry trial (any indication) in or before the year of the programme's first trial, or
     only later. "Already led by top-20" mixes in-licensed drugs with old drugs that a small company repurposes; it is
     not a measure of partnership. Licensing and co-development deals are not in the registry.
  C. Cost. Supported programmes may sit in indications whose Phase 3 trials are large, which a small sponsor cannot
     pay for. Typical Phase 3 size of an indication = median enrolment of the industry-led Phase 3 entry trials
     (each drug's first Phase 3 trial in the indication) of OTHER drugs: distinct trials, at least three, none of
     them an entry trial of the programme's own drug, trials stopped early excluded because their enrolment is
     truncated. Enrolment is the registry field (actual for completed trials, anticipated for ongoing ones).
  D. Capital. Form D capital raised before the year of the first trial (nominal USD) against the cost of one typical
     Phase 3 at USD 41,117 per patient: the median over 138 pivotal trials of 59 drugs approved by the FDA in
     2015-2016 (Moore, Zhang, Anderson, Alexander, JAMA Intern Med 2018;178(11):1451-1457; their median trial cost
     USD 19.0M, IQR 12.2-33.1M). A crude yardstick: it ignores Phase 1-2 costs, later rounds and public financing.
  E. Acquisitions (needs the synonyms file of extract_molecule_synonyms.py). sponsors.py types a renamed
     subsidiary by its own name, but the registry moved some old records to the acquirer's name outright. E1 finds
     them through research codes: a programme typed top-20 whose drug carries the code of a company the same parent
     acquired only after the programme's first trial (ACQUIRED_CODES; the loose prefixes are held in check by the
     parent and the year). It is a lower bound: only the acquisitions listed in sponsors.py, only drugs with a
     research code in ChEMBL. E2 asks the converse: did sponsors that a top-20 company later acquired start
     better-supported programmes than other non-top-20 sponsors?
Selection models are the H1 logit of robust26.py (first-trial period, therapeutic area, modality; standard errors
clustered by drug). Sparse control categories are pooled here (pooling.py), because the split outcomes are rarer
than the H1 outcome; robust26.py does not pool in its main H1 model, so A0 can differ from the published OR in the
third decimal. A sponsor group without a single event is left out of a fit and named.
Writes RESULTS_DIR/h1_mechanisms.txt.
"""

import os
import re
import sys
import warnings

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact, norm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headline  # noqa: E402
import rq2_stops  # noqa: E402
import sponsors  # noqa: E402
from pooling import pool_sparse  # noqa: E402

TIERS = [
    "Top-20 pharma",
    "Industry, large (>30)",
    "Industry, mid (6-30)",
    "Industry, small (<=5 drugs)",
    "Academic/other",
    "Government",
]
IND = TIERS[1:4]
SMALL = "Industry, small (<=5 drugs)"
KEY = ["drug", "indication_mesh_id"]
CTRL = "C(yb) + C(area) + C(modality)"
STOPPED = {"TERMINATED", "WITHDRAWN", "SUSPENDED", "NO_LONGER_AVAILABLE"}
COST_PER_PATIENT = 0.041117  # USD million, Moore et al. 2018
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
# research-code prefixes of companies in the acquisition list of sponsors.py: (prefixes, company, parent, year)
ACQUIRED_CODES = [
    ("WAY|WY|CCI|HKI|SKI|PRA|GAR|CMA|TSE|DVS|ERA", "Wyeth", "Pfizer", 2009),
    ("MDV", "Medivation", "Pfizer", 2016),
    ("AN", "Anacor", "Pfizer", 2016),
    ("ARRY", "Array", "Pfizer", 2019),
    ("APD", "Arena", "Pfizer", 2022),
    ("GBT", "Global Blood", "Pfizer", 2022),
    ("BHV", "Biohaven", "Pfizer", 2022),
    ("SGN|SEA", "Seagen", "Pfizer", 2023),
    ("CNTO", "Centocor", "Johnson & Johnson", 1999),
    ("ALS|AL", "Alios", "Johnson & Johnson", 2014),
    ("ACT", "Actelion", "Johnson & Johnson", 2017),
    ("ITMN", "InterMune", "Roche", 2014),
    ("SPK", "Spark", "Roche", 2019),
    ("SCH", "Schering-Plough", "Merck & Co", 2009),
    ("ORG", "Organon", "Merck & Co", 2009),
    ("IDX", "Idenix", "Merck & Co", 2014),
    ("CB|CXA", "Cubist", "Merck & Co", 2015),
    ("TR", "Trius", "Merck & Co", 2015),
    ("OPT|PAR", "Optimer", "Merck & Co", 2015),
    ("OTX", "Oncoethix", "Merck & Co", 2014),
    ("AF", "Afferent", "Merck & Co", 2016),
    ("PT", "Peloton", "Merck & Co", 2019),
    ("ARQ", "ArQule", "Merck & Co", 2020),
    ("VLS", "VelosBio", "Merck & Co", 2020),
    ("ACE", "Acceleron", "Merck & Co", 2021),
    ("IMG", "Imago", "Merck & Co", 2023),
    ("HPN", "Harpoon", "Merck & Co", 2024),
    ("RPL", "Verona", "Merck & Co", 2025),
    ("PCI|PC", "Pharmacyclics", "AbbVie", 2015),
    ("AGN", "Allergan", "AbbVie", 2020),
    ("CVL", "Cerevel", "AbbVie", 2024),
    ("IMGN", "ImmunoGen", "AbbVie", 2024),
    ("CHIR", "Chiron", "Novartis", 2006),
    ("AVXS", "AveXis", "Novartis", 2018),
    ("EC", "Endocyte", "Novartis", 2018),
    ("MDCO", "The Medicines Company", "Novartis", 2020),
    ("RLX", "Corthera", "Novartis", 2010),
    ("CC", "Celgene", "Bristol Myers Squibb", 2019),
    ("RPC", "Receptos", "Bristol Myers Squibb", 2019),
    ("JCAR", "Juno", "Bristol Myers Squibb", 2019),
    ("MYK", "MyoKardia", "Bristol Myers Squibb", 2020),
    ("TPX", "Turning Point", "Bristol Myers Squibb", 2022),
    ("MRTX|MGCD", "Mirati", "Bristol Myers Squibb", 2024),
    ("RYZ", "RayzeBio", "Bristol Myers Squibb", 2024),
    ("MEDI", "MedImmune", "AstraZeneca", 2007),
    ("RDEA", "Ardea", "AstraZeneca", 2012),
    ("ACP", "Acerta", "AstraZeneca", 2016),
    ("ALXN", "Alexion", "AstraZeneca", 2021),
    ("GZ|GC", "Genzyme", "Sanofi", 2011),
    ("BIVV", "Bioverativ", "Sanofi", 2018),
    ("ALX", "Ablynx", "Sanofi", 2018),
    ("PRN", "Principia", "Sanofi", 2020),
    ("THOR", "Synthorx", "Sanofi", 2020),
    ("KD", "Kadmon", "Sanofi", 2021),
    ("MRT", "Translate Bio", "Sanofi", 2021),
    ("PRV", "Provention", "Sanofi", 2023),
    ("SRT", "Sirtris", "GSK", 2008),
    ("HGS", "Human Genome Sciences", "GSK", 2012),
    ("TSR", "Tesaro", "GSK", 2019),
    ("SRA", "Sierra", "GSK", 2022),
    ("BLU", "Bellus", "GSK", 2023),
    ("IMC", "ImClone", "Eli Lilly", 2008),
    ("LOXO", "Loxo", "Eli Lilly", 2019),
    ("DRM", "Dermira", "Eli Lilly", 2020),
    ("PNT", "POINT", "Eli Lilly", 2023),
    ("MORF", "Morphic", "Eli Lilly", 2024),
    ("ONX|PR", "Onyx", "Amgen", 2013),
    ("FPA", "Five Prime", "Amgen", 2021),
    ("CCX", "ChemoCentryx", "Amgen", 2022),
    ("HZN", "Horizon", "Amgen", 2023),
    ("DCR", "Dicerna", "Novo Nordisk", 2021),
    ("MLN", "Millennium", "Takeda", 2008),
    ("AP", "Ariad", "Takeda", 2017),
    ("SHP|SPD", "Shire", "Takeda", 2019),
    ("PSI", "Pharmasset", "Gilead Sciences", 2012),
    ("KTE|KITE", "Kite", "Gilead Sciences", 2017),
    ("IMMU", "Immunomedics", "Gilead Sciences", 2020),
    ("FSI", "Forty Seven", "Gilead Sciences", 2020),
    ("PLX", "Plexxikon", "Daiichi Sankyo", 2011),
    ("AC", "Ambit", "Daiichi Sankyo", 2014),
]
CODE = re.compile(r"^([A-Za-z]{1,6})[- ]?(\d{2,}[A-Za-z0-9\-]*)$")  # a research code: letters, then digits
out = []


def say(*lines):
    out.extend(str(x) for x in lines)


def fit(f, d, keep):
    """Clustered logit after pooling sparse controls; rows of the coefficient table whose name passes `keep`."""
    y = f.split("~")[0].strip()
    d = d.dropna(subset=[y])
    dropped = ""
    for col in ("tier", "tier2", "funds"):
        # a sponsor group without a single event is predicted perfectly: its coefficient runs to minus infinity and
        # its rows add nothing to the likelihood of the other coefficients, so the group is left out and named
        if f"C({col})" in f:
            ev = d.groupby(col, observed=True)[y].sum()
            empty = [c for c in ev.index if ev[c] == 0]
            if empty:
                d = d[~d[col].isin(empty)].copy()
                d[col] = d[col].cat.remove_unused_categories()
                dropped = "; groups without events left out: " + ", ".join(map(str, empty))
    d = pool_sparse(d, f)
    r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.drug)[0]})
    t = r.summary2().tables[1]
    t = t.loc[[i for i in t.index if keep(i)], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
    t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
    note = f"N={int(r.nobs)}; events={int(d[y].sum())}; clusters (drugs)={d.drug.nunique()}"
    return t, note + dropped + ("" if r.mle_retvals["converged"] else "; NOT CONVERGED")


def show(title, f, d, keep=lambda i: "tier" in i):
    t, note = fit(f, d, keep)
    say("=" * 100, title, f, note, t[["OR", "OR_lo", "OR_hi", "P>|z|"]].round(4).to_string())
    return t


def cell(t, name):
    x = t.loc[name]
    return f"{x.OR:.2f} ({x.OR_lo:.2f}-{x.OR_hi:.2f}), p={x['P>|z|']:.3f}"


def load(R):
    P = pd.read_csv(f"{R}/programmes.csv.gz")
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    for D in (P, E):
        D["modality"] = D.drugType.map(MOD).fillna("other")
        D["area"] = D.area.fillna("other")
    # interval strings sort chronologically, which pooling.py relies on when it merges sparse period bins
    P["yb"] = pd.cut(P.first_year, [0, 2004, 2009, 2014, 2019, 2100]).astype(str)
    E["entry_start"] = pd.to_datetime(E.entry_start, errors="coerce")
    # the programme's first phase entry (drop_duplicates keeps the whole row; groupby.first would skip missing values)
    first = E.sort_values(["entry_start", "phase"]).drop_duplicates(KEY)
    first = first[KEY + ["gs_ante_noomim", "entry_year"]].rename(columns={"entry_year": "first_entry_year"})
    P = P.merge(first, on=KEY, how="left")
    P["gs_ante_first"] = P.gs_ante_first.fillna(False).astype(bool)
    for c in ("gs_post", "gs_post_noomim"):
        P[c] = P[c].fillna(False).astype(bool)
    noomim = P.gs_ante_noomim.fillna(False).astype(bool)
    # Evidence is dated by year and only accumulates. Dated evidence seen at an entry in a later year than the first
    # trial may be newer than the first trial, so the type at the first trial is unknown; no dated evidence at a later
    # entry means none at the first trial either. Supported programmes without any phase entry are unknown too.
    later = P.first_entry_year.gt(P.first_year)
    unknown = P.gs_ante_first & (P.gs_ante_noomim.isna() | (later & noomim))
    dated = P.gs_ante_first & noomim
    P["ante_dated"] = np.where(unknown, np.nan, dated)
    P["ante_omim_only"] = np.where(unknown, np.nan, P.gs_ante_first & ~dated)
    P["post_dated_type"] = P.gs_post_noomim.astype(float)
    P["post_omim_only"] = (P.gs_post & ~P.gs_post_noomim).astype(float)
    P["start_year"] = P.first_year
    H = P[P.insight & P.first_sponsor_tier.isin(TIERS)].copy()
    H["tier"] = pd.Categorical(H.first_sponsor_tier, categories=TIERS)
    return E, H


def part_a(H):
    say("", "#" * 100, "A. TYPE OF EVIDENCE", "#" * 100)
    t = H.groupby("tier", observed=True).agg(
        programmes=("drug", "size"),
        any_support=("gs_ante_first", "mean"),
        dated_population=("ante_dated", "mean"),
        omim_only=("ante_omim_only", "mean"),
    )
    t[["any_support", "dated_population", "omim_only"]] *= 100
    say(
        "Ex-ante support at the first trial, % of programmes (dated population evidence = OTG (GWAS), PICCOLO or "
        "Genebass association dated before the year of the first trial; OMIM only = Mendelian evidence alone, undated):",
        t.round(2).to_string(),
        f"split unknown for {int(H.ante_dated.isna().sum())} supported programmes (no phase entry, or dated evidence "
        "first seen at a phase entry in a later year than the first trial); they are left out of A1-A3",
    )
    f = "y ~ C(tier) + " + CTRL
    res = {}
    for y, lab in (
        ("gs_ante_first", "A0. any ex-ante support (the H1 model, sparse controls pooled)"),
        ("ante_dated", "A1. ex-ante support from dated population evidence"),
        ("ante_omim_only", "A2. ex-ante support from OMIM only"),
    ):
        res[y] = show(lab, f, H.assign(y=H[y].astype(float)))
    # one multinomial model for the two types, to test whether the small-sponsor coefficients differ
    D = H[H.ante_dated.notna()].copy()
    ev = D.groupby("area")[["ante_dated", "ante_omim_only"]].sum()
    sparse = ev[(ev.ante_dated < 3) | (ev.ante_omim_only < 3)].index
    D["area"] = D.area.where(~D.area.isin(sparse), "other")
    D["yb"] = D.yb.replace({"(0, 2004]": "(2004, 2009]"})  # no dated evidence before 2005: merge the first bin forward
    D["k"] = np.where(D.ante_dated == 1, 2, np.where(D.ante_omim_only == 1, 1, 0))
    y, X = patsy.dmatrices("k ~ C(tier) + " + CTRL, D, return_type="dataframe")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = sm.MNLogit(y, X).fit(
            disp=0, method="bfgs", maxiter=5000, cov_type="cluster", cov_kwds={"groups": pd.factorize(D.drug)[0]}
        )
    name = f"C(tier)[T.{SMALL}]"
    k = list(X.columns).index(name)
    K = X.shape[1]
    b = np.asarray(m.params)  # (K, 2): column 0 = OMIM only vs none, column 1 = dated vs none
    V = np.asarray(m.cov_params())  # equation-major order: all coefficients of equation 0, then equation 1
    d = b[k, 1] - b[k, 0]
    se = np.sqrt(V[K + k, K + k] + V[k, k] - 2 * V[k, K + k])
    say(
        "=" * 100,
        "A3. multinomial logit (none / OMIM only / dated), small sponsors vs top-20 pharma, same controls",
        f"N={len(D)}; converged={m.mle_retvals['converged']}",
        f"  OMIM only vs none: RRR {np.exp(b[k, 0]):.3f} ({np.exp(b[k, 0] - 1.96 * np.sqrt(V[k, k])):.3f}-"
        f"{np.exp(b[k, 0] + 1.96 * np.sqrt(V[k, k])):.3f})",
        f"  dated vs none:     RRR {np.exp(b[k, 1]):.3f} ({np.exp(b[k, 1] - 1.96 * np.sqrt(V[K + k, K + k])):.3f}-"
        f"{np.exp(b[k, 1] + 1.96 * np.sqrt(V[K + k, K + k])):.3f})",
        f"  difference of the two log ratios: {d:.3f} (SE {se:.3f}), ratio {np.exp(d):.3f}, "
        f"Wald p={2 * (1 - norm.cdf(abs(d / se))):.4f}",
    )
    part_a_gap(H)
    return res


def small_or(f, d, name=None):
    t, note = fit(f, d, lambda i: "tier" in i)
    extra = [x for x in note.split("; ") if x.startswith("groups without events") or x == "NOT CONVERGED"]
    return cell(t, name or f"C(tier)[T.{SMALL}]") + "".join("; " + x for x in extra)


def part_a_gap(H):
    two = H[H.tier.isin(["Top-20 pharma", SMALL])]
    outcomes = (("gs_ante_first", "any"), ("ante_dated", "dated population"), ("ante_omim_only", "OMIM only"))
    say("=" * 100, "A4. where the adjusted gap comes from (small sponsors vs top-20 pharma)")
    n = two.groupby(["tier", "yb"], observed=True).agg(
        programmes=("drug", "size"),
        any_support=("gs_ante_first", "mean"),
        dated_population=("ante_dated", "mean"),
        n_dated=("ante_dated", "sum"),
        omim_only=("ante_omim_only", "mean"),
    )
    n.insert(1, "share_of_tier", n.programmes / n.groupby(level=0, observed=True).programmes.transform("sum"))
    for c in ("share_of_tier", "any_support", "dated_population", "omim_only"):
        n[c] *= 100
    say(
        "programmes by period of the first trial; ex-ante support, % of the tier's programmes of that period:",
        n.round(1).to_string(),
        "",
        "small-sponsor OR as controls are added (all six tiers in the model):",
    )
    specs = (
        ("sponsor tier only", "y ~ C(tier)"),
        ("+ period", "y ~ C(tier) + C(yb)"),
        ("+ period, area", "y ~ C(tier) + C(yb) + C(area)"),
        ("+ period, area, modality (H1)", "y ~ C(tier) + " + CTRL),
        ("area and modality, no period", "y ~ C(tier) + C(area) + C(modality)"),
        ("start year instead of period", "y ~ C(tier) + C(start_year) + C(area) + C(modality)"),
    )
    for y, lab in outcomes:
        say(f"  {lab}:")
        for name, f in specs:
            say(f"      {name:32s} {small_or(f, H.assign(y=H[y].astype(float)))}")
    say(
        "=" * 100,
        "A5. the same split with ex-post support (every source without its date; H1 controls)",
        f"  any ex-post support:               {small_or('y ~ C(tier) + ' + CTRL, H.assign(y=H.gs_post.astype(float)))}",
        f"  OTG, PICCOLO or Genebass, ex post: {small_or('y ~ C(tier) + ' + CTRL, H.assign(y=H.post_dated_type))}",
        f"  OMIM only, ex post:                {small_or('y ~ C(tier) + ' + CTRL, H.assign(y=H.post_omim_only))}",
    )
    say(
        "=" * 100,
        "A6. novel drugs (the drug's first indication) and follow-on indications, first trial 2000 or later",
        "    (follow-on = a new indication for a drug already in trials; H1 controls)",
    )
    R = H[H.first_year.ge(2000)]
    for lab, d in (("novel", R[R.is_drug_first_indication]), ("follow-on", R[~R.is_drug_first_indication])):
        a, b = d[d.tier.eq(SMALL)], d[d.tier.eq("Top-20 pharma")]
        say(f"  {lab}: {len(d)} programmes, {d.drug.nunique()} drugs")
        for y, yl in outcomes:
            say(
                f"      {yl:16s} small {a[y].mean():.1%} ({int(a[y].sum())}/{int(a[y].notna().sum())}) vs top-20 "
                f"{b[y].mean():.1%} ({int(b[y].sum())}/{int(b[y].notna().sum())}) | OR "
                f"{small_or('y ~ C(tier) + ' + CTRL, d.assign(y=d[y].astype(float)))}"
            )


def part_b(H, E, ct):
    say("", "#" * 100, "B. PARTNERSHIPS WITH LARGE COMPANIES", "#" * 100)
    H = H.merge(ct[["nct", "collaborators", "collab_classes"]], left_on="first_trial", right_on="nct", how="left")

    def partner(r):
        if not isinstance(r.collaborators, str):
            return False, False
        top = any(sponsors.top20_parent(n, r.first_year) for n in r.collaborators.split("|"))
        ind = isinstance(r.collab_classes, str) and "INDUSTRY" in r.collab_classes.split("|")
        return top, ind

    pr = [partner(r) for r in H.itertuples()]
    H["collab_top20"] = [x[0] for x in pr]
    H["collab_industry"] = [x[1] for x in pr]
    t20 = E[E.sponsor_tier.eq("Top-20 pharma")].groupby("drug").entry_year.min().rename("top20_first_year")
    H = H.merge(t20, on="drug", how="left")
    H["pharma_before"] = H.top20_first_year.le(H.first_year)
    H["pharma_later"] = H.top20_first_year.gt(H.first_year)
    t = H.groupby("tier", observed=True).agg(
        programmes=("drug", "size"),
        any_collaborator=("collaborators", lambda s: s.notna().mean()),
        industry_collaborator=("collab_industry", "mean"),
        top20_collaborator=("collab_top20", "mean"),
        n_top20_collaborator=("collab_top20", "sum"),
        drug_led_by_top20_before=("pharma_before", "mean"),
        drug_led_by_top20_only_later=("pharma_later", "mean"),
    )
    for c in t.columns:
        if c not in ("programmes", "n_top20_collaborator"):
            t[c] *= 100
    say("First trial of the programme: collaborators in the registry, and the drug's history, % of programmes:")
    say(t.round(1).to_string())
    f = "y ~ C(tier) + " + CTRL
    nontop = H.tier.isin(IND)
    for lab, mask in (
        ("B1. without non-top-20 industry programmes that have a top-20 collaborator", ~(nontop & H.collab_top20)),
        (
            "B2. without non-top-20 industry programmes that have any industry collaborator",
            ~(nontop & H.collab_industry),
        ),
    ):
        for y in ("gs_ante_first", "ante_dated"):
            show(f"{lab}: {y}", f, H[mask].assign(y=lambda d: d[y].astype(float)))
    # small sponsors by the drug's link to top-20 pharma
    H["tier2"] = H.tier.astype(str)
    s = H.tier.eq(SMALL)
    H.loc[s & H.pharma_before, "tier2"] = "Small, drug already led by top-20"
    H.loc[s & H.pharma_later, "tier2"] = "Small, drug led by top-20 only later"
    H.loc[s & ~H.pharma_before & ~H.pharma_later, "tier2"] = "Small, drug never led by top-20"
    cats = [c for c in TIERS if c != SMALL] + [
        "Small, drug never led by top-20",
        "Small, drug already led by top-20",
        "Small, drug led by top-20 only later",
    ]
    H["tier2"] = pd.Categorical(H.tier2, categories=cats)
    t = (
        H[s]
        .groupby("tier2", observed=True)
        .agg(programmes=("drug", "size"), drugs=("drug", "nunique"), supported=("gs_ante_first", "sum"))
    )
    say("", "Small-sponsor programmes by the drug's link to top-20 pharma:", t.to_string())
    for y in ("gs_ante_first", "ante_dated"):
        show(
            f"B3. small sponsors split by the drug's link to top-20 pharma: {y}",
            "y ~ C(tier2) + " + CTRL,
            H.assign(y=H[y].astype(float)),
            keep=lambda i: "Small" in i,
        )
    return H


def part_c(H, E, en, ct):
    say("", "#" * 100, "C. SIZE OF PHASE 3 TRIALS IN THE INDICATION", "#" * 100)
    E = E.merge(en[["nct", "enrollment"]], left_on="entry_trial", right_on="nct", how="left")
    E = E.merge(ct[["nct", "status"]], on="nct", how="left")
    p3 = E[E.phase.eq(3) & E.enrollment.gt(0) & ~E.status.isin(STOPPED) & E.lead_class.eq("INDUSTRY")]
    # one row per trial and indication: a combination trial is the entry trial of several drugs
    p3 = (
        p3.groupby(["indication_mesh_id", "entry_trial"])
        .agg(
            enrollment=("enrollment", "first"),
            entry_year=("entry_year", "min"),
            area=("area", "first"),
            drugs=("drug", frozenset),
        )
        .reset_index()
    )
    say(
        f"industry-led Phase 3 entry trials with enrolment, not stopped early: {p3.entry_trial.nunique()} trials, "
        f"{len(p3)} trial-indication pairs in {p3.indication_mesh_id.nunique()} indications; median enrolment "
        f"{p3.enrollment.median():.0f}",
        "median enrolment by therapeutic area (trial-indication pairs):",
        p3.groupby("area").enrollment.agg(["size", "median"]).sort_values("median").to_string(),
    )
    by = {k: g for k, g in p3.groupby("indication_mesh_id")}

    def size(r, ante):
        g = by.get(r.indication_mesh_id)
        if g is None:
            return np.nan
        g = g[[r.drug not in s for s in g.drugs]]
        if ante:
            g = g[g.entry_year < r.first_year]
        return g.enrollment.median() if len(g) >= 3 else np.nan

    H["p3_size"] = [size(r, False) for r in H.itertuples()]
    H["p3_size_ante"] = [size(r, True) for r in H.itertuples()]
    H["lsize"] = np.log10(H.p3_size)
    H["lsize_ante"] = np.log10(H.p3_size_ante)
    say(
        f"programmes with a typical Phase 3 size (at least 3 trials of other drugs): {int(H.p3_size.notna().sum())} "
        f"of {len(H)} ({H.p3_size.notna().mean():.1%}); using only trials that started before the programme: "
        f"{int(H.p3_size_ante.notna().sum())} ({H.p3_size_ante.notna().mean():.1%})"
    )
    S = H[H.p3_size.notna()].copy()
    S["support"] = np.select(
        [S.ante_dated == 1, S.ante_omim_only == 1], ["dated population evidence", "OMIM only"], "none"
    )
    q = [0.25, 0.5, 0.75]
    say(
        "",
        "C1. typical Phase 3 enrolment of the indication, by ex-ante support of the programme:",
        S.groupby("support").p3_size.describe(percentiles=q)[["count", "25%", "50%", "75%"]].round(0).to_string(),
        "",
        "C2. typical Phase 3 enrolment of the indication, by sponsor tier of the first trial:",
        S.groupby("tier", observed=True)
        .p3_size.describe(percentiles=q)[["count", "25%", "50%", "75%"]]
        .round(0)
        .to_string(),
    )
    f = "y ~ C(tier) + " + CTRL
    name = f"C(tier)[T.{SMALL}]"
    say("", "C3. small sponsors vs top-20 pharma, without and with log10(typical Phase 3 size) as a control:")
    for y in ("gs_ante_first", "ante_dated", "ante_omim_only"):
        d = S.assign(y=S[y].astype(float))
        t0, n0 = fit(f, d, lambda i: "tier" in i)
        t1, _ = fit(f + " + lsize", d, lambda i: "tier" in i or i == "lsize")
        say(
            f"  {y:15s} {n0}",
            f"      without: {cell(t0, name)} | with: {cell(t1, name)} | size, per tenfold: {cell(t1, 'lsize')}",
        )
    A = H[H.p3_size_ante.notna()]
    for y in ("gs_ante_first", "ante_dated"):
        d = A.assign(y=A[y].astype(float))
        t0, n0 = fit(f, d, lambda i: "tier" in i)
        t1, _ = fit(f + " + lsize_ante", d, lambda i: "tier" in i or i == "lsize_ante")
        say(
            f"  {y:15s} size from earlier trials only; {n0}",
            f"      without: {cell(t0, name)} | with: {cell(t1, name)}",
        )
    S["tertile"] = pd.qcut(S.p3_size, 3, labels=["small trials", "medium trials", "large trials"])
    cut = S.groupby("tertile", observed=True).p3_size.agg(["min", "max"])
    say("", "C4. the gap by tertile of the indication's typical Phase 3 size:", cut.to_string())
    for y in ("gs_ante_first", "ante_dated"):
        for name_t, d in S.groupby("tertile", observed=True):
            d = d.assign(y=d[y].astype(float))
            t, note = fit(f, d, lambda i: "tier" in i)
            a, b = d[d.tier.eq(SMALL)], d[d.tier.eq("Top-20 pharma")]
            say(
                f"  {y:14s} {name_t:14s} small {a.y.mean():.1%} ({int(a.y.sum())}/{len(a)}) vs top-20 "
                f"{b.y.mean():.1%} ({int(b.y.sum())}/{len(b)}) | OR {cell(t, name)} | {note}"
            )
    two = S[S.tier.isin(["Top-20 pharma", SMALL])].copy()
    two["small"] = two.tier.eq(SMALL).astype(int)
    two["lsize_c"] = two.lsize - two.lsize.mean()
    for y in ("gs_ante_first", "ante_dated"):
        show(
            f"C5. small sponsor x log10(typical Phase 3 size), small and top-20 only: {y}",
            "y ~ small * lsize_c + " + CTRL,
            two.assign(y=two[y].astype(float)),
            keep=lambda i: i in ("small", "lsize_c", "small:lsize_c"),
        )
    return H


def part_d(H, R):
    say("", "#" * 100, "D. CAPITAL RAISED BEFORE THE FIRST TRIAL VS THE COST OF ONE TYPICAL PHASE 3", "#" * 100)
    O = pd.read_csv(f"{R}/formd_sponsor_offerings.csv.gz")
    fd = pd.read_csv(f"{R}/formd_sponsors.csv")
    hist = {n: (g.year.to_numpy(), g.sold.fillna(0).to_numpy()) for n, g in O.groupby("norm")}
    first = dict(zip(fd.norm, fd.formd_first_year))
    D = H[H.tier.isin(IND) & H.first_year.gt(2009)].copy()
    D["norm"] = D.first_sponsor.map(rq2_stops.norm_sponsor)
    D["formd"] = (pd.to_numeric(D.norm.map(first), errors="coerce") < D.first_year).fillna(False).astype(int)
    D["raised"] = [
        float(hist[n][1][hist[n][0] < y].sum()) / 1e6 if n in hist else 0.0 for n, y in zip(D.norm, D.first_year)
    ]
    D["tier"] = pd.Categorical(D.tier.astype(str), categories=IND)
    D["yb"] = pd.cut(D.first_year, [2009, 2014, 2019, 2100]).astype(str)
    D["y"] = D.gs_ante_first.astype(float)
    t, note = fit("y ~ formd + C(tier) + " + CTRL, D, lambda i: i == "formd")
    pub = headline.from_txt(R, "formd_models.txt", "H1: ex-ante support at first trial ~ prior Form D", "formd ")
    say(
        f"check against formd_models.txt ({pub[0]:.2f}, {pub[1]:.2f}-{pub[2]:.2f}): prior Form D OR "
        f"{cell(t, 'formd')}; {note}"
    )
    S = D[D.p3_size.notna()].copy()
    S["p3_cost"] = S.p3_size * COST_PER_PATIENT
    lab = ["no prior Form D", "raised less than one typical Phase 3", "raised at least one typical Phase 3"]
    S["funds"] = pd.Categorical(np.select([S.formd.eq(0), S.raised < S.p3_cost], lab[:2], lab[2]), categories=lab)
    say(
        f"programmes of non-top-20 industry sponsors, first trial 2010+, with a typical Phase 3 size: {len(S)}",
        f"cost of one typical Phase 3 at USD {COST_PER_PATIENT * 1e6:,.0f} per patient: median USD "
        f"{S.p3_cost.median():.0f}M (IQR {S.p3_cost.quantile(0.25):.0f}-{S.p3_cost.quantile(0.75):.0f}M)",
        S.groupby("funds", observed=True)
        .agg(
            programmes=("drug", "size"),
            raised_median_musd=("raised", "median"),
            p3_cost_median_musd=("p3_cost", "median"),
            supported=("y", "sum"),
            supported_share=("y", "mean"),
            dated_share=("ante_dated", "mean"),
        )
        .round(3)
        .to_string(),
    )
    for y in ("gs_ante_first", "ante_dated"):
        show(
            f"D1. ex-ante support ~ funds relative to one typical Phase 3: {y}",
            "y ~ C(funds) + C(tier) + " + CTRL,
            S.assign(y=S[y].astype(float)),
            keep=lambda i: "funds" in i,
        )
    F = S[S.formd.eq(1)].copy()
    F["enough"] = (F.raised >= F.p3_cost).astype(int)
    G = F[F.raised.gt(0)].copy()
    G["lratio"] = np.log10(G.raised / G.p3_cost)
    say(
        "",
        f"D2. sponsors with a prior Form D only ({len(F)} programmes; {len(G)} with a positive amount sold, used for "
        "the continuous ratio):",
    )
    for y in ("gs_ante_first", "ante_dated"):
        t, note = fit("y ~ enough + C(tier) + " + CTRL, F.assign(y=F[y].astype(float)), lambda i: i == "enough")
        t2, note2 = fit("y ~ lratio + C(tier) + " + CTRL, G.assign(y=G[y].astype(float)), lambda i: i == "lratio")
        say(
            f"  {y:14s} raised at least one typical Phase 3 vs less: OR {cell(t, 'enough')} | {note}",
            f"  {'':14s} per tenfold of raised/cost: OR {cell(t2, 'lratio')} | {note2}",
        )
    sm_ = S[S.tier.eq(SMALL)]
    say(
        "",
        "small sponsors only (counts too small for a model):",
        sm_.groupby("funds", observed=True)
        .agg(programmes=("drug", "size"), supported=("y", "sum"), share=("y", "mean"))
        .round(3)
        .to_string(),
    )
    lo, hi = (sm_[sm_.funds.eq(x)] for x in lab[1:])
    tab = [[int(hi.y.sum()), int(len(hi) - hi.y.sum())], [int(lo.y.sum()), int(len(lo) - lo.y.sum())]]
    say(
        f"small sponsors, raised at least one typical Phase 3 vs less: {tab[0][0]}/{len(hi)} vs {tab[1][0]}/{len(lo)}, "
        f"Fisher exact p={fisher_exact(tab)[1]:.3f} (unadjusted)"
    )


def part_e(H, syn_path):
    say("", "#" * 100, "E. ACQUISITIONS: RECORDS MOVED TO THE ACQUIRER, AND SPONSORS ACQUIRED LATER", "#" * 100)
    M = pd.read_csv(syn_path).fillna("")
    M["root"] = M.parentId.where(M.parentId.ne(""), M.id)
    syn = M.groupby("root").syn_chembl.agg(lambda s: "|".join(x for x in s if x))
    drug_name = M.set_index("id").name

    def prefixes(d):
        labs = syn.get(d, "").split("|")
        return {m.group(1).upper() for m in (CODE.match(x.strip()) for x in labs) if m}

    rx = [(re.compile(f"^(?:{p})$"), c, par, y) for p, c, par, y in ACQUIRED_CODES]
    H = H.copy()
    H["parent"] = [
        sponsors.top20_parent(n, y) if c == "INDUSTRY" else None
        for n, y, c in zip(H.first_sponsor, H.first_year, H.first_class)
    ]
    pf = {d: prefixes(d) for d in set(H.drug[H.tier.eq("Top-20 pharma")])}
    coded = sum(bool(v) for v in pf.values())
    company = []
    for r in H.itertuples():
        hit = None
        if r.tier == "Top-20 pharma":
            for q, c, par, y in rx:
                if par == r.parent and r.first_year < y and any(q.match(x) for x in pf[r.drug]):
                    hit = c
                    break
        company.append(hit)
    H["moved_from"] = company
    X = H[H.moved_from.notna()]
    t = (
        X.groupby("moved_from")
        .agg(
            programmes=("drug", "size"),
            drugs=("drug", "nunique"),
            supported=("gs_ante_first", "sum"),
            first=("first_year", "min"),
            last=("first_year", "max"),
            examples=("drug", lambda s: ", ".join(sorted({str(drug_name.get(d, d)) for d in s})[:4])),
        )
        .sort_values("programmes", ascending=False, kind="stable")  # ties stay in alphabetical order
    )
    top = H[H.tier.eq("Top-20 pharma")]
    say(
        f"E1. top-20 programmes: {len(top)} ({len(pf)} drugs, {coded} with a research code in ChEMBL); with the code "
        f"of a company the same parent acquired after the programme's first trial: {len(X)} programmes of "
        f"{X.drug.nunique()} drugs, {int(X.gs_ante_first.sum())} with ex-ante support ({X.gs_ante_first.mean():.1%}; "
        f"other top-20 programmes {top[top.moved_from.isna()].gs_ante_first.mean():.1%})",
        t.to_string(),
        "",
        "small-sponsor OR (H1 model) when these programmes are taken out of the top-20 group:",
    )
    f = "y ~ C(tier) + " + CTRL
    y = H.gs_ante_first.astype(float)
    say(f"      as typed                                {small_or(f, H.assign(y=y))}")
    say(f"      dropped                                 {small_or(f, H[H.moved_from.isna()].assign(y=y))}")
    for tier in (SMALL, "Industry, mid (6-30)", "Industry, large (>30)"):
        D = H.assign(y=y)
        D["tier"] = pd.Categorical(np.where(D.moved_from.notna(), tier, D.tier.astype(str)), categories=TIERS)
        say(f"      counted as {tier:29s}{small_or(f, D)}")
    # E2: sponsors later acquired by a top-20 company
    ind = H[H.tier.isin(IND)].copy()
    ent = [sponsors.leading_entry(n) if isinstance(n, str) else None for n in ind.first_sponsor]
    ind["later"] = [int(e is not None and yr < e[2]) for e, yr in zip(ent, ind.first_year)]
    ind["tier"] = pd.Categorical(ind.tier.astype(str), categories=IND)
    g = ind.groupby("later").agg(
        programmes=("drug", "size"),
        sponsors=("first_sponsor", "nunique"),
        any_support=("gs_ante_first", "mean"),
        dated_population=("ante_dated", "mean"),
        ex_post=("gs_post", "mean"),
    )
    say(
        "",
        "E2. programmes of non-top-20 industry sponsors, by whether a top-20 company acquired the sponsor later "
        "(sponsor names in the acquisition list of sponsors.py, first trial before the acquisition year):",
        g.round(4).to_string(),
    )
    for yv, lab in (("gs_ante_first", "any ex-ante"), ("ante_dated", "dated population"), ("gs_post", "ex post")):
        t, note = fit("y ~ later + C(tier) + " + CTRL, ind.assign(y=ind[yv].astype(float)), lambda i: i == "later")
        say(f"  {lab:18s} acquired later vs not: OR {cell(t, 'later')} | {note}")


def main(R, ctgov, enrol, syn=None):
    E, H = load(R)
    ct = pd.read_csv(ctgov, usecols=["nct_id", "collaborators", "collab_classes", "status"], dtype=str)
    ct["nct"] = ct.nct_id.str.lower()
    en = pd.read_csv(enrol)
    en["nct"] = en.nct_id.str.lower()
    say(
        "Mechanisms behind the small-sponsor gap in selection (exploratory; see the module docstring)",
        f"programmes in indications with genetic insight, six sponsor tiers: {len(H)}; with ex-ante support: "
        f"{int(H.gs_ante_first.sum())}",
        f"registry snapshot: {len(ct)} studies; enrolment file: {len(en)} studies, "
        f"{ct.nct_id.isin(en.nct_id).mean():.2%} of the snapshot covered",
    )
    part_a(H)
    H = part_b(H, E, ct)
    H = part_c(H, E, en, ct)
    part_d(H, R)
    if syn:
        part_e(H, syn)
    text = "\n".join(out)
    with open(f"{R}/h1_mechanisms.txt", "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:5])
