"""Replication of the power figure of the working paper (Figure 2: sponsor x genetic-support interaction).

Usage: python factcheck/power_replication.py RESULTS_DIR [REPLICATIONS]

The figure was drawn from a simulation made before the data were assembled (400 replications per scenario); the
script that produced it is not in this repository. This script repeats the simulation from the assumptions stated
in the paper: a baseline phase transition of 28% without genetic support, a share of supported spells of 7% or 15%,
25% of spells from VC-backed sponsors, a relative success (risk ratio) of genetic support that differs between the
two sponsor groups, a logistic model with the interaction, and a two-sided Wald test at 0.05. With two binary
regressors the logit is saturated, so the interaction and its standard error come from the eight cell counts.
Writes power_replication.txt: the power shown in the figure and the replicated power for each scenario.
"""

import sys

import numpy as np

BASE, VC_SHARE = 0.28, 0.25
# (relative success for other sponsors, for VC-backed sponsors) -> powers shown in the figure for
# N = 3,000 and 7% supported, 3,000 and 15%, 6,000 and 7%, 6,000 and 15%
FIGURE = {
    (1.6, 1.0): (0.53, 0.80, 0.83, 0.99),
    (1.4, 1.0): (0.30, 0.48, 0.48, 0.80),
    (1.6, 1.2): (0.29, 0.48, 0.46, 0.78),
}
CELLS = ((3000, 0.07), (3000, 0.15), (6000, 0.07), (6000, 0.15))


def power(n, share, rs_other, rs_vc, reps, rng):
    hits = used = 0
    for _ in range(reps):
        vc, gs = rng.random(n) < VC_SHARE, rng.random(n) < share
        y = rng.random(n) < np.where(gs, BASE * np.where(vc, rs_vc, rs_other), BASE)
        c = np.array([[(y & (vc == v) & (gs == g)).sum(), (~y & (vc == v) & (gs == g)).sum()] for v in (0, 1) for g in (0, 1)], float)  # fmt: skip
        if (c == 0).any():
            continue
        used += 1
        lo = np.log(
            c[:, 0] / c[:, 1]
        )  # log odds in the cells: other/unsupported, other/supported, VC/unsupported, VC/supported
        z = ((lo[3] - lo[2]) - (lo[1] - lo[0])) / np.sqrt((1 / c).sum())
        hits += abs(z) > 1.959964
    return hits / used


def main(res, reps=4000):
    rng = np.random.default_rng(20261124)
    out = [f"Replication of the power figure: {reps} replications per scenario, seed 20261124 (the figure used 400)"]
    out.append("rs_other  rs_vc      n  share  figure  replication  difference")
    worst = 0.0
    for (rs_other, rs_vc), shown in FIGURE.items():
        for (n, share), f in zip(CELLS, shown):
            p = power(n, share, rs_other, rs_vc, reps, rng)
            worst = max(worst, abs(p - f))
            out.append(f"{rs_other:8.1f}  {rs_vc:5.1f}  {n:5d}  {share:5.2f}  {f:6.2f}  {p:11.3f}  {p - f:+10.3f}")
    out.append(
        f"largest absolute difference: {worst:.3f} (the standard error of a power near 0.5 from 400 replications is 0.025)"
    )
    open(f"{res}/power_replication.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4000)
