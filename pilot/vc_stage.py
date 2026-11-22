"""The sponsor's financing stage in the year of the trial, and the selection model with it.

Usage: python pilot/vc_stage.py RESULTS_DIR
(after owners_link.py, cb_models.py, ritter_models.py, formd_directors.py and ipo_models.py; plan written before the
run: docs/plan_vc_stage.md)

Each programme of a non-top-20 industry sponsor is placed by what the sponsor was in the year t of the programme's
first trial:
  A  private and venture-backed: not public at t, and venture-backed at an IPO still ahead, or a dated venture
     marker (Crunchbase venture round, venture investor on the board in a Form D filing) in a year before t
  B  public, venture-backed before: public at t, and venture-backed at the IPO, or a dated venture marker before t,
     or a venture-capital fund among its owners in a Schedule 13D/13G first filed before t
  C  public, no venture marker
  D  the rest: not known to be public at t, no venture marker before t
Public at t: t is later than the IPO year (the earlier of the prospectus and Jay Ritter's list); without an IPO year,
t is later than the first year as an EDGAR registrant, and a first year of 2001 (where the index begins) means public
throughout. Top-20 pharma is the reference group. Writes vc_stage.txt.
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.discrete.conditional_models import ConditionalLogit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops
from pooling import pool_sparse

TOP = "Top-20 pharma"
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
FIRST_YEAR = 2001
INDEX_START = 2001
GROUPS = {"A": "private, venture-backed", "B": "public, venture-backed before", "C": "public, no venture marker", "D": "the rest"}  # fmt: skip


def sponsor_dates(R):
    """One row per normalised sponsor name with the dated markers of every source that is present."""

    def table(name, key=None):
        path = f"{R}/{name}"
        if not os.path.exists(path):
            return None
        t = pd.read_csv(path, dtype={"norm": str})
        if key:
            t["norm"] = t[key].map(rq2_stops.norm_sponsor)
        return t[t.norm.notna()]

    cols = {}
    ipo, rt, ow, cb, bd = (
        table("ipo_sponsors.csv"),
        table("ritter_sponsors.csv", "first_sponsor"),
        table("owners_sponsors.csv"),
        table("cb_sponsors.csv", "first_sponsor"),
        table("formd_directors_sponsors.csv"),
    )
    if ipo is not None:
        cols["ipo_year_prospectus"] = ipo.groupby("norm").ipo_year.min()
        cols["vc_prospectus"] = ipo.groupby("norm").venture.max().astype(bool)
    if rt is not None:
        cols["ipo_year_ritter"] = rt.groupby("norm").ipo_year.min()
        cols["vc_ritter"] = rt.groupby("norm").ritter_vc.max().astype(bool)
    if ow is not None:
        cols["reg_year"] = ow.groupby("norm").registrant_first_year.min()
        cols["owner_vc_year"] = ow.groupby("norm").first_vc_year.min()
    if cb is not None:
        cols["round_year"] = cb.groupby("norm").first_vc_round_year.min()
    if bd is not None:
        cols["board_year"] = bd.groupby("norm").first_vc_board_year.min()
    S = pd.DataFrame(cols)
    for c in ("ipo_year_prospectus", "ipo_year_ritter", "reg_year", "owner_vc_year", "round_year", "board_year"):
        S[c] = pd.to_numeric(S[c], errors="coerce") if c in S else np.nan
    for c in ("vc_prospectus", "vc_ritter"):
        S[c] = S[c].fillna(False).astype(bool) if c in S else False
    S["ipo_year"] = S[["ipo_year_prospectus", "ipo_year_ritter"]].min(axis=1)
    S["vc_ipo"] = (S.vc_prospectus | S.vc_ritter) & S.ipo_year.notna()
    S["mark_year"] = S[["round_year", "board_year"]].min(axis=1)
    return S


def stage(norm, year, S, strict=False):
    """Group A-D of the plan for each (sponsor name, year); `strict` keeps only dated markers in group A."""
    norm, t = pd.Series(norm).reset_index(drop=True), pd.Series(year).reset_index(drop=True).astype(float)
    ipo, reg = norm.map(S.ipo_year), norm.map(S.reg_year)
    vc_ipo = norm.map(S.vc_ipo).fillna(False).astype(bool)
    mark, own = norm.map(S.mark_year), norm.map(S.owner_vc_year)
    public = np.where(ipo.notna(), t > ipo, reg.notna() & ((t > reg) | (reg <= INDEX_START)))
    dated = (mark < t).to_numpy()
    owner = (own < t).to_numpy()
    ahead = (vc_ipo & (t <= ipo)).to_numpy()
    a = ~public & (dated if strict else (ahead | dated))
    b = public & (vc_ipo.to_numpy() | dated | owner)
    g = np.where(a, "A", np.where(b, "B", np.where(public, "C", "D")))
    return pd.Series(g)


def or_table(r, names):
    t = r.summary2().tables[1]
    t = t.loc[[i for i in t.index if i in names], ["Coef.", "Std.Err.", "P>|z|", "[0.025", "0.975]"]]
    t["OR"], t["OR_lo"], t["OR_hi"] = np.exp(t["Coef."]), np.exp(t["[0.025"]), np.exp(t["0.975]"])
    return t.round(4).to_string()


def contrast(r, expr):
    c = r.t_test(expr)
    b, (lo, hi) = float(np.ravel(c.effect)[0]), np.ravel(c.conf_int())
    return f"  {expr}: OR {np.exp(b):.4f} ({np.exp(lo):.4f}-{np.exp(hi):.4f}), p={float(np.ravel(c.pvalue)[0]):.4f}"


def fit(out, f, d, title, keep, contrasts=()):
    """Logit with errors clustered by drug (the pilot's rule) and by sponsor."""
    try:
        d = pool_sparse(d, f)
        y = f.split("~")[0].strip()
        out.extend(["=" * 100, title, f])
        out.append(f"N={len(d)}; events={int(d[y].sum())}; drugs={d.drug.nunique()}; sponsors={d.norm.nunique()}")
        for label, col in (("drug", "drug"), ("sponsor", "norm")):
            r = smf.logit(f, d).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": pd.factorize(d[col])[0]})  # fmt: skip
            out.append(f"errors clustered by {label}; converged={r.mle_retvals['converged']}")
            out.append(or_table(r, keep))
            out.extend(contrast(r, c) for c in contrasts)
    except Exception as e:
        out.extend(["=" * 100, title, f, f"failed: {e!r}"])


def dummies(T):
    for g in GROUPS:
        T[f"g{g}"] = T.group.eq(g).astype(int)


def within(out, P, S):
    """Secondary (e): after the IPO year against no later than it, within sponsors venture-backed at their IPO."""
    W = P[P.first_sponsor_tier.isin(IND) & P.norm.map(S.vc_ipo).fillna(False).astype(bool)].copy()
    W["after"] = (W.first_year > W.norm.map(S.ipo_year)).astype(int)
    both = W.groupby("norm").after.transform("nunique").eq(2)
    W = W[both].copy()
    varies = W.groupby("norm").y.transform("nunique").eq(2)
    out.extend(["=" * 100, "(e) Within sponsor: programmes first tried after the IPO year against no later than it"])
    out.append(
        f"sponsors venture-backed at their IPO with programmes on both sides: {W.norm.nunique()} ({len(W)} programmes, "
        f"{int(W.y.sum())} supported); sponsors whose programmes differ in support (the ones that inform the "
        f"estimate): {W[varies].norm.nunique()} ({int(varies.sum())} programmes)"
    )
    out.append(W.groupby("after").agg(n=("y", "size"), supported=("y", "sum"), gs_ante=("y", "mean")).round(4).to_string())  # fmt: skip
    for label, X in (
        ("with first-trial period (plan)", pd.concat([W[["after"]], pd.get_dummies(W.yb, drop_first=True)], axis=1)),
        ("without the period control (not in the plan; shown because period and stage move together)", W[["after"]]),
    ):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = ConditionalLogit(W.y.to_numpy(), X.astype(float), groups=W.norm.to_numpy()).fit(disp=0)
            b, (lo, hi) = float(r.params["after"]), r.conf_int().loc["after"]
            out.append(f"conditional logit, {label}: OR after {np.exp(b):.4f} ({np.exp(lo):.4f}-{np.exp(hi):.4f}), p={float(r.pvalues['after']):.4f}")  # fmt: skip
        except Exception as e:
            out.append(f"conditional logit, {label}: failed: {e!r}")


def main(R):
    out = ["The sponsor's financing stage in the year of the trial (plan: docs/plan_vc_stage.md)"]
    S = sponsor_dates(R)
    P = pd.read_csv(f"{R}/programmes.csv.gz")
    P = P[P.insight & P.first_sponsor_tier.isin(IND + [TOP]) & P.first_year.ge(FIRST_YEAR)].copy()
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    end_year = int(E.entry_year.max())
    E = E[E.insight & ~E.prior_higher & E.sponsor_tier.isin(IND + [TOP]) & E.entry_year.between(FIRST_YEAR, end_year - 6)].copy()  # fmt: skip
    for T, name_col, year_col, tier_col in (
        (P, "first_sponsor", "first_year", "first_sponsor_tier"),
        (E, "lead_sponsor", "entry_year", "sponsor_tier"),
    ):
        T["norm"] = T[name_col].map(rq2_stops.norm_sponsor).fillna("")
        top = T[tier_col].eq(TOP).to_numpy()
        T["group"] = np.where(top, "top20", stage(T.norm, T[year_col], S).to_numpy())
        T["group_strict"] = np.where(top, "top20", stage(T.norm, T[year_col], S, strict=True).to_numpy())
        T["modality"] = T.drugType.map(MOD).fillna("other")
        T["area"] = T.area.fillna("other")
        dummies(T)
    P["tier"] = P.first_sponsor_tier
    P["yb"] = pd.cut(P.first_year, [2000, 2005, 2010, 2015, 2020, 2100]).astype(str)
    E["yb"] = pd.cut(E.entry_year, [2000, 2005, 2010, 2015, 2030]).astype(str)
    P["y"] = P.gs_ante_first.fillna(False).astype(int)

    sp = P[P.group.ne("top20")].drop_duplicates("norm")
    out.append(
        f"non-top-20 industry sponsors with a programme: {len(sp)}; with an IPO year: {int(sp.norm.map(S.ipo_year).notna().sum())} "
        f"(venture-backed at the IPO: {int(sp.norm.map(S.vc_ipo).fillna(False).sum())}); with a first year as registrant "
        f"and no IPO year: {int((sp.norm.map(S.reg_year).notna() & sp.norm.map(S.ipo_year).isna()).sum())}; with a dated "
        f"venture marker: {int(sp.norm.map(S.mark_year).notna().sum())}"
    )
    out.append(f"\nProgrammes (insight indications, first trial {FIRST_YEAR}+, industry sponsors): {len(P)}")
    for col, label in (
        ("group", "groups of the plan"),
        ("group_strict", "strict variant of group A (dated marker only)"),
    ):
        out.append(f"by stage in the year of the first trial, {label}:")
        t = P.groupby(col).agg(n=("drug", "size"), sponsors=("norm", "nunique"), supported=("y", "sum"), gs_ante=("y", "mean")).round(4)  # fmt: skip
        t.index = [f"{i} {GROUPS.get(i, 'top-20 pharma')}" for i in t.index]
        out.append(t.to_string())
    a = P[P.group.eq("A")]
    ahead = a.first_year <= a.norm.map(S.ipo_year)
    dated = a.norm.map(S.mark_year) < a.first_year
    out.append(
        f"group A by rule: IPO still ahead and venture-backed at it {int((ahead & a.norm.map(S.vc_ipo).fillna(False)).sum())}; "
        f"dated marker before the trial {int(dated.sum())}; both {int((ahead & a.norm.map(S.vc_ipo).fillna(False) & dated).sum())}"
    )

    base = "C(yb) + C(area) + C(modality)"
    G = "gA + gB + gC + gD"
    keep = ("gA", "gB", "gC", "gD")
    out.append(
        "\n1. PRIMARY (plan): ex-ante support, group A against top-20 pharma (coefficient gA); secondary (a) as contrasts"
    )
    fit(out, f"y ~ {G} + {base}", P, "H1: ex-ante support ~ stage in the year of the first trial (reference: top-20 pharma)", keep, ("gA - gB = 0", "gA - gD = 0"))  # fmt: skip
    out.append("\n2. SECONDARY (plan)")
    N = P[P.group.ne("top20")].copy()
    N["tier"] = pd.Categorical(N.tier, categories=IND)
    fit(out, f"y ~ gA + C(tier) + {base}", N, "(b) non-top-20 sponsors only: group A against all others, with the size band", ("gA",))  # fmt: skip
    Q = P.copy()
    Q["group"] = Q.group_strict
    dummies(Q)
    fit(out, f"y ~ {G} + {base}", Q, "(c) strict variant: group A needs a dated venture marker before the trial", keep, ("gA - gB = 0", "gA - gD = 0"))  # fmt: skip
    fit(out, f"y ~ {G} + {base}", P[P.first_year.ge(2010)].copy(), "(d) first trials from 2010", keep, ("gA - gB = 0", "gA - gD = 0"))  # fmt: skip
    within(out, P, S)
    if os.path.exists(f"{R}/gs_ot_programmes.csv.gz"):
        O = pd.read_csv(f"{R}/gs_ot_programmes.csv.gz", usecols=["drug", "indication_mesh_id", "gs_ot_ante_first"])
        P2 = P.drop(columns="y").merge(O, on=["drug", "indication_mesh_id"], how="left")
        P2["y"] = P2.gs_ot_ante_first.fillna(False).astype(int)
        fit(out, f"y ~ {G} + {base}", P2, "(f) [dated Open Targets evidence] ex-ante support ~ stage", keep, ("gA - gB = 0", "gA - gD = 0"))  # fmt: skip
    else:
        out.append("=" * 100)
        out.append(
            "(f) gs_ot_programmes.csv.gz not in RESULTS_DIR: the model with dated Open Targets evidence is not run"
        )

    E["gs"], E["adv"] = E.gs_ante.fillna(False).astype(int), E.advanced.astype(int)
    out.append("=" * 100)
    out.append(f"(g) Phase entries {FIRST_YEAR}-{end_year - 6}, industry sponsors, no earlier higher phase: {len(E)} ({int(E.adv.sum())} advanced)")  # fmt: skip
    t = E.groupby(["group", "gs"]).agg(n=("adv", "size"), advanced=("adv", "sum"), rate=("adv", "mean")).round(4)
    out.append(t.to_string())
    inter = " + ".join(f"gs:g{g}" for g in GROUPS)
    fit(
        out,
        f"adv ~ gs + {G} + {inter} + C(phase) + {base}",
        E,
        "Advancement ~ ex-ante support x stage in the year of the entry trial (reference: top-20 pharma)",
        ("gs", *keep, *(f"gs:g{g}" for g in GROUPS)),
        ("gs:gA - gs:gB = 0",),
    )
    open(f"{R}/vc_stage.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
