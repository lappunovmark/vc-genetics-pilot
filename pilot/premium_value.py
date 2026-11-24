"""What the genetic premium is worth in clinical cost: an illustration. Plan: docs/plan_premium_value.md.

Usage: python pilot/premium_value.py RESULTS_DIR [N_BOOTSTRAP]
Reads phase_entries.csv.gz; writes premium_value.txt.
"""

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pooling import pool_sparse

# DiMasi, Grabowski and Hansen (2016), J Health Econ 47:20-33, Table 2: mean out-of-pocket clinical cost per
# investigational compound entering the phase, millions of 2013 dollars
COST = {1: 25.3, 2: 58.6, 3: 255.4}
IND = ["Top-20 pharma", "Industry, large (>30)", "Industry, mid (6-30)", "Industry, small (<=5 drugs)"]
MOD = {"Small molecule": "small molecule", "Antibody": "antibody", "Antibody drug conjugate": "antibody", "Protein": "protein", "Enzyme": "protein", "Oligonucleotide": "nucleic acid/gene/cell", "Gene": "nucleic acid/gene/cell", "Cell": "nucleic acid/gene/cell"}  # fmt: skip
F = "adv ~ gs + C(tier) + C(yb) + C(area) + C(modality)"


def money(s, cost=COST):
    """From the three advancement rates: probability of approval from phase 1, phase 1 programmes per approval,
    expected clinical cost per programme entering phase 1, and clinical cost per approval."""
    s1, s2, s3 = s
    p = s1 * s2 * s3
    e = cost[1] + s1 * cost[2] + s1 * s2 * cost[3]
    return {"s1": s1, "s2": s2, "s3": s3, "p_approval": p, "per_approval": 1 / p, "cost_entrant": e, "cost_approval": e / p}  # fmt: skip


def rates(d, adjusted=True):
    """Advancement rates by phase with support switched on and off (adjusted), or the raw rates by support."""
    on, off = [], []
    for k in (1, 2, 3):
        x = d[d.phase.eq(k)]
        if not adjusted:
            on.append(x[x.gs.eq(1)].adv.mean())
            off.append(x[x.gs.eq(0)].adv.mean())
            continue
        x = pool_sparse(x, F)
        r = smf.logit(F, x).fit(disp=0, maxiter=200)
        on.append(float(r.predict(x.assign(gs=1)).mean()))
        off.append(float(r.predict(x.assign(gs=0)).mean()))
    return on, off


def summary(d, adjusted=True):
    on, off = rates(d, adjusted)
    a, b = money(on), money(off)
    out = {f"{k}_gs": v for k, v in a.items()} | {f"{k}_no": v for k, v in b.items()}
    out["ratio_p_approval"] = a["p_approval"] / b["p_approval"]
    out["ratio_cost_approval"] = a["cost_approval"] / b["cost_approval"]
    out["saving_per_approval"] = b["cost_approval"] - a["cost_approval"]
    return out


def bootstrap(d, n, adjusted=True, seed=20261124):
    rng = np.random.default_rng(seed)
    groups = {k: v for k, v in d.groupby("drug").indices.items()}
    keys = np.array(list(groups))
    rows, failed = [], 0
    for _ in range(n):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys))])
        try:
            rows.append(summary(d.iloc[idx], adjusted))
        except Exception:
            failed += 1
    return pd.DataFrame(rows), failed


def block(out, d, title, n, adjusted=True):
    est = summary(d, adjusted)
    cnt = d.groupby(["phase", "gs"]).adv.agg(["size", "sum"])
    out.extend(["=" * 100, title, f"entries={len(d)}; drugs={d.drug.nunique()}; rates {'adjusted (support switched on and off for the same entries)' if adjusted else 'unadjusted'}"])  # fmt: skip
    out.append("entries and advanced by phase and support: " + "; ".join(f"phase {int(k)} {'supported' if g else 'not'} {int(r['size'])}/{int(r['sum'])}" for (k, g), r in cnt.iterrows()))  # fmt: skip
    t = pd.DataFrame({"estimate": est})
    if n:
        b, failed = bootstrap(d, n, adjusted)
        t["lo"], t["hi"] = b.quantile(0.025), b.quantile(0.975)
        out.append(f"bootstrap by drug: {len(b)} resamples used, {failed} failed")
    out.append(t.round(4).to_string())
    return est


def sample(E, sim=False, first=False):
    prior, adv = ("prior_higher_sim", "advanced_sim") if sim else ("prior_higher", "advanced")
    end = int(E.entry_year.max())
    d = E[E.insight & ~E[prior] & E.sponsor_tier.isin(IND) & E.entry_year.between(2000, end - 6)].copy()
    if first:
        d = d[d.is_drug_first_indication.eq(True)]
    d["adv"], d["gs"] = d[adv].astype(int), d.gs_ante.fillna(False).astype(int)
    d["tier"], d["modality"], d["area"] = d.sponsor_tier, d.drugType.map(MOD).fillna("other"), d.area.fillna("other")
    d["yb"] = pd.cut(d.entry_year, [1999, 2005, 2010, 2015, 2030]).astype(str)
    return d.reset_index(drop=True)


def main(R, n=1000):
    E = pd.read_csv(f"{R}/phase_entries.csv.gz")
    out = ["What the genetic premium is worth in clinical cost: AN ILLUSTRATION (plan: docs/plan_premium_value.md)"]
    out.append(f"costs per compound entering the phase, millions of 2013 dollars (DiMasi et al. 2016, Table 2): {COST}")
    out.append("s1..s3 = advancement rates from phases 1..3; p_approval = their product; per_approval = phase 1 programmes per approval;")  # fmt: skip
    out.append("cost_entrant = expected clinical cost per programme entering phase 1; cost_approval = cost_entrant / p_approval;")  # fmt: skip
    out.append("_gs = with ex-ante genetic support, _no = without; saving_per_approval = cost_approval_no - cost_approval_gs")  # fmt: skip
    out.append("\n1. PRIMARY (plan): industry sponsors, adjusted rates")
    block(out, sample(E), "Industry sponsors, exact indication", n)
    out.append("\n2. SENSITIVITY (plan)")
    block(out, sample(E), "Unadjusted rates", n, adjusted=False)
    block(out, sample(E, sim=True), "Advancement and earlier trials counted in similar indications", n)
    block(out, sample(E, sim=True, first=True), "The drug's first indication only, similar-indication definition", n)
    open(f"{R}/premium_value.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1000)
