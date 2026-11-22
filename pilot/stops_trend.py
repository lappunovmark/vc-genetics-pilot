"""Is the rise in financial or strategic trial stops after 2022 a break or a trend? (docs/plan_stops_trend.md)

Usage: python pilot/stops_trend.py RESULTS_DIR
Input: RESULTS_DIR/rq2_rates.csv from rq2_stops.py (one row per calendar year x sponsor group: trials at risk and
stops in that year). For each group a Poisson regression of the yearly stops with log(at risk) as offset,
log(rate) = a + b * (year - 2021) + c * post, post = 1 from the break year; the dispersion is estimated from the
Pearson statistic (quasi-Poisson). exp(c) is the change of level at the break beyond the linear trend.
Writes RESULTS_DIR/stops_trend.txt.
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

R = sys.argv[1]
D = pd.read_csv(f"{R}/rq2_rates.csv")
GROUPS = ["Top-20 pharma", "Industry, large (>200 trials)", "Industry, mid (21-200)", "Industry, small (<=20)"]
OUT = []


def say(*a):
    OUT.append(" ".join(str(x) for x in a))


def design(d, brk):
    X = pd.DataFrame({"const": 1.0, "trend": d.year - 2021.0, "post": (d.year >= brk).astype(float)}, index=d.index)
    return X


def fit(d, col, brk):
    """exp(c), its 95% interval, the yearly trend exp(b), the dispersion and the number of stops."""
    X = design(d, brk)
    m = sm.GLM(d[col], X, family=sm.families.Poisson(), offset=np.log(d.at_risk)).fit(scale="X2")
    b, se = m.params["post"], m.bse["post"]
    return {
        "break": np.exp(b),
        "lo": np.exp(b - 1.96 * se),
        "hi": np.exp(b + 1.96 * se),
        "p": m.pvalues["post"],
        "trend": np.exp(m.params["trend"]),
        "trend_lo": np.exp(m.params["trend"] - 1.96 * m.bse["trend"]),
        "trend_hi": np.exp(m.params["trend"] + 1.96 * m.bse["trend"]),
        "scale": m.scale,
        "stops": int(d[col].sum()),
    }


def table(title, col, y0, y1, brk, groups=GROUPS):
    say("=" * 100)
    say(title)
    say(f"stops = {col}; years {y0}-{y1}; break from {brk}; quasi-Poisson (Pearson scale), offset log(at risk)")
    say(
        f"{'group':32s} {'stops':>6s} {'break':>7s} {'lo':>7s} {'hi':>7s} {'p':>7s}   {'trend/yr':>8s} {'lo':>6s} {'hi':>6s} {'scale':>6s}"
    )
    for g in groups:
        d = D[D.group.eq(g) & D.year.between(y0, y1)].sort_values("year")
        r = fit(d, col, brk)
        say(
            f"{g:32s} {r['stops']:6d} {r['break']:7.4f} {r['lo']:7.4f} {r['hi']:7.4f} {r['p']:7.4f}   "
            f"{r['trend']:8.4f} {r['trend_lo']:6.4f} {r['trend_hi']:6.4f} {r['scale']:6.2f}"
        )


def ratio(title, col, y0, y1, brk, ga, gb):
    """Pooled model for two groups with group-specific intercepts and trends: break of ga over break of gb."""
    d = D[D.group.isin([ga, gb]) & D.year.between(y0, y1)].copy()
    a = d.group.eq(ga).astype(float)
    X = pd.DataFrame(
        {
            "const": 1.0,
            "a": a,
            "trend": d.year - 2021.0,
            "trend_a": (d.year - 2021.0) * a,
            "post": (d.year >= brk).astype(float),
            "post_a": (d.year >= brk).astype(float) * a,
        },
        index=d.index,
    )
    m = sm.GLM(d[col], X, family=sm.families.Poisson(), offset=np.log(d.at_risk)).fit(scale="X2")
    b, se = m.params["post_a"], m.bse["post_a"]
    say("-" * 100)
    say(title)
    say(
        f"ratio of the breaks ({ga} over {gb}): {np.exp(b):.4f} ({np.exp(b - 1.96 * se):.4f}-{np.exp(b + 1.96 * se):.4f}), "
        f"p={m.pvalues['post_a']:.4f}; scale={m.scale:.2f}; years {y0}-{y1}; break from {brk}"
    )


def carried_forward(col, groups=GROUPS):
    say("=" * 100)
    say("C. Trend fitted on 2016-2021 alone and carried forward: stops observed in 2022-25 over stops expected")
    say(f"stops = {col}; descriptive (six yearly points for the trend)")
    for g in groups:
        d = D[D.group.eq(g)].sort_values("year")
        pre, post = d[d.year.between(2016, 2021)], d[d.year.between(2022, 2025)]
        X = pd.DataFrame({"const": 1.0, "trend": pre.year - 2021.0}, index=pre.index)
        m = sm.GLM(pre[col], X, family=sm.families.Poisson(), offset=np.log(pre.at_risk)).fit(scale="X2")
        Xp = pd.DataFrame({"const": 1.0, "trend": post.year - 2021.0}, index=post.index)
        exp = float(m.predict(Xp, offset=np.log(post.at_risk)).sum())
        obs = int(post[col].sum())
        say(
            f"{g:32s} trend/yr {np.exp(m.params['trend']):.4f}; observed {obs}; expected {exp:.1f}; "
            f"observed/expected {obs / exp:.4f}"
        )


SMALL, TOP = "Industry, small (<=20)", "Top-20 pharma"
say("Trend or break? Financial or strategic stops of industry Phase 1-3 drug trials (docs/plan_stops_trend.md)")
say("exp(c) of log(rate) = a + b*(year-2021) + c*post: the change of level at the break beyond the linear trend")
table("A (primary). Break in 2022, years 2016-2025, financial or strategic stops", "stops_fin", 2016, 2025, 2022)
ratio("A. Pooled model, small sponsors against top-20 pharma", "stops_fin", 2016, 2025, 2022, SMALL, TOP)
table("B. Break in 2022, years 2012-2025, financial or strategic stops", "stops_fin", 2012, 2025, 2022)
ratio("B. Pooled model, small sponsors against top-20 pharma", "stops_fin", 2012, 2025, 2022, SMALL, TOP)
carried_forward("stops_fin")
table("D1. Break in 2022, years 2016-2025, all stops", "stops_all", 2016, 2025, 2022)
table("D2. Break in 2022, years 2016-2025, stops citing lack of funding", "stops_nofund", 2016, 2025, 2022, [SMALL])
table(
    "E (exploratory: the date comes from the figure). Break in 2020, years 2012-2025, financial or strategic stops",
    "stops_fin",
    2012,
    2025,
    2020,
)
open(f"{R}/stops_trend.txt", "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("\n".join(OUT))
