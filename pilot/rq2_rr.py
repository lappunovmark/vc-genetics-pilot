"""Stop rates per 1,000 active trial-years before and after the 2022 downturn, with Poisson rate-ratio CIs.

Usage: python rq2_rr.py RESULTS_DIR [PRE_FIRST PRE_LAST POST_FIRST POST_LAST]   (default 2016 2021 2022 2025)
Input: RESULTS_DIR/rq2_rates.csv from rq2_stops.py (one row per calendar year x sponsor group: trials at risk in that
year and stops in that year). Each trial at risk contributes one trial-year per calendar year, so pooled
rate = sum(stops) / sum(at_risk). RR CI: log RR +/- 1.96 * sqrt(1/a + 1/b) (a, b = pooled stop counts).
Writes RESULTS_DIR/rq2_rr.csv.
"""
import sys
import numpy as np, pandas as pd

R = sys.argv[1]
p0, p1, q0, q1 = (int(x) for x in (sys.argv[2:6] if len(sys.argv) >= 6 else (2016, 2021, 2022, 2025)))
r = pd.read_csv(f'{R}/rq2_rates.csv')
rows = []
for g, d in r.groupby('group'):
    pre, post = d[d.year.between(p0, p1)], d[d.year.between(q0, q1)]
    for k in ('all', 'fin', 'nofund'):
        a, b = pre[f'stops_{k}'].sum(), post[f'stops_{k}'].sum()
        ta, tb = pre.at_risk.sum(), post.at_risk.sum()
        ra, rb = 1000 * a / ta, 1000 * b / tb
        rr = rb / ra if a else np.nan
        se = np.sqrt(1 / a + 1 / b) if a and b else np.nan
        rows.append({'group': g, 'stops': k, 'pre_stops': int(a), 'pre_trial_years': int(ta), 'pre_rate': ra,
                     'post_stops': int(b), 'post_trial_years': int(tb), 'post_rate': rb, 'rr': rr,
                     'rr_lo': rr * np.exp(-1.96 * se), 'rr_hi': rr * np.exp(1.96 * se)})
out = pd.DataFrame(rows)
out.to_csv(f'{R}/rq2_rr.csv', index=False)
print(f'pre {p0}-{p1}, post {q0}-{q1}')
print(out.round(3).to_string(index=False))
