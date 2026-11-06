"""Run a pilot script with statsmodels' Logit.fit wrapped, and list every fit that did not converge.

Usage: python factcheck/convergence_audit.py SCRIPT ARG...   (e.g. pilot/robust26.py /tmp/results_copy)
The script runs as __main__ on a COPY of the results directory you pass (it rewrites its outputs there). For each
logit the formula, the number of observations, the convergence flag and the number of iterations are printed; a
non-converged fit usually means quasi-separation (a control category without events), whose nuisance coefficient
drifts while the reported coefficients stay put. Check the estimates against a pooled-category refit before trusting
them.
"""

import runpy
import sys
import warnings

import statsmodels.discrete.discrete_model as dm

RECORDS = []
_fit = dm.Logit.fit


def fit(self, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = _fit(self, *args, **kwargs)
    RECORDS.append(
        (
            getattr(self, "formula", "?"),
            int(res.nobs),
            bool(res.mle_retvals.get("converged", True)),
            res.mle_retvals.get("iterations"),
        )
    )
    return res


dm.Logit.fit = fit


def main(script, *args):
    sys.argv = [script, *args]
    sys.path.insert(0, "pilot")
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit:
        pass
    bad = [r for r in RECORDS if not r[2]]
    print(f"\n[convergence audit] {script}: {len(RECORDS)} logits, {len(bad)} not converged")
    for f, n, c, it in RECORDS:
        print(f"  {'OK ' if c else 'NOT'} N={n:6d} it={it!s:>4} {f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
