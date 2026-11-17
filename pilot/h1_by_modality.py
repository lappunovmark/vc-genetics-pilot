"""Is the small-sponsor gap in selection (H1) the same for every type of drug? Exploratory.

Usage: python pilot/h1_by_modality.py RESULTS_DIR
The H1 model holds the type of drug fixed (C(modality)) but gives one gap for all types. Here the same logit is
fitted within each type (small molecule; antibody, with antibody-drug conjugates; protein, with enzymes; nucleic
acid, gene and cell therapies), and one model with all programmes tests whether the gap differs between small
molecules and the other types (sponsor tier x biologic). Sample, outcome, controls and clustering are those of
h1_mechanisms.py (programmes in indications with genetic insight; ex-ante support at the first trial; first-trial
period and therapeutic area; errors clustered by drug; sparse control categories pooled). The split was chosen after
the H1 result was known, so p-values are descriptive. Writes RESULTS_DIR/h1_by_modality.txt.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h1_mechanisms as hm

SMALL, TOP = hm.SMALL, hm.TIERS[0]
TYPES = ["small molecule", "antibody", "protein", "nucleic acid/gene/cell"]


def main(R):
    _, H = hm.load(R)
    H["y"] = H.gs_ante_first.astype(int)
    out = hm.out
    out.append("Selection gap by type of drug (exploratory; see the module docstring)")
    tab = H.groupby(["modality", "tier"], observed=True).y.agg(["sum", "size"])
    tab["share"] = tab["sum"] / tab["size"]
    out.append("\nsupported / programmes (share) by type of drug and sponsor tier:")
    out.append(
        tab.apply(lambda r: f"{int(r['sum'])}/{int(r['size'])} ({r['share']:.1%})", axis=1).unstack("tier").to_string()
    )
    rows = []
    for m in TYPES:
        d = H[H.modality.eq(m)].copy()
        try:
            t = hm.show(f"H1 within type: {m}", "y ~ C(tier) + C(yb) + C(area)", d)
            x = t.loc[f"C(tier)[T.{SMALL}]"] if f"C(tier)[T.{SMALL}]" in t.index else None
            bad = "NOT CONVERGED" in out[-2]
        except Exception as e:  # too few events for a model
            out.extend(["=" * 100, f"H1 within type: {m}", f"failed: {e!r}"])
            x, bad = None, False
        a, b = d[d.tier.eq(SMALL)], d[d.tier.eq(TOP)]
        rows.append(
            f"  {m:24s} small {int(a.y.sum())}/{len(a)} ({a.y.mean():.1%}) vs top-20 {int(b.y.sum())}/{len(b)} "
            f"({b.y.mean():.1%}); adjusted OR "
            + (f"{x.OR:.2f} ({x.OR_lo:.2f}-{x.OR_hi:.2f}), p={x['P>|z|']:.3f}" if x is not None else "not estimated")
            + (" (the model did not converge)" if bad else "")
        )
    H["biologic"] = (~H.modality.isin(["small molecule", "other"])).astype(int)
    d = H[H.modality.ne("other")].copy()
    t = hm.show(
        "all types except 'other': sponsor tier x biologic (reference: small molecule, top-20 pharma)",
        "y ~ C(tier) * biologic + C(yb) + C(area)",
        d,
        keep=lambda i: "tier" in i or i == "biologic",
    )
    k = f"C(tier)[T.{SMALL}]:biologic"
    out.append("")
    out.append("small sponsors vs top-20 pharma, by type of drug:")
    out.extend(rows)
    out.append(
        f"  small sponsor x biologic (ratio of the two gaps): {t.loc[k].OR:.2f} "
        f"({t.loc[k].OR_lo:.2f}-{t.loc[k].OR_hi:.2f}), p={t.loc[k]['P>|z|']:.3f}"
    )
    d2 = H[H.modality.isin(["small molecule", "antibody"])].copy()
    d2["biologic"] = d2.modality.eq("antibody").astype(int)
    t2 = hm.show(
        "small molecules and antibodies only: sponsor tier x antibody",
        "y ~ C(tier) * biologic + C(yb) + C(area)",
        d2,
        keep=lambda i: "tier" in i or i == "biologic",
    )
    out.append(
        f"  small sponsor x antibody (antibodies against small molecules): {t2.loc[k].OR:.2f} "
        f"({t2.loc[k].OR_lo:.2f}-{t2.loc[k].OR_hi:.2f}), p={t2.loc[k]['P>|z|']:.3f}"
    )
    assert np.isfinite(t.loc[k].OR)
    open(f"{R}/h1_by_modality.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
