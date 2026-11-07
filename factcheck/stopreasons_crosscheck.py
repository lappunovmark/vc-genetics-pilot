"""Cross-check the keyword stop-reason classifier against the Open Targets StopReasons predictions.

Usage (from the repository root): python factcheck/stopreasons_crosscheck.py STOPREASONS_REPO [RESULTS_DIR]
STOPREASONS_REPO: a clone of https://github.com/opentargets/StopReasons (Apache 2.0; file
data/stopped_predictions_formatted_30_09_22.csv, 31,867 trial x prediction rows for 28,561 stopped trials registered
by late 2021, predictions of the BERT classifier of Razuvayevskaya et al., 2024, Nature Genetics). The file is read in
place and not redistributed.

Our classifier (pilot/stopreasons.py, current version) is applied to the same why_stopped texts. The two schemes differ: theirs has
no 'no funding' class and its 'Business_Administrative' merges funding, business and sponsor decisions, so the
comparison is made on binary classes with a stated mapping. Writes RESULTS_DIR/stopreasons_crosscheck.txt.
"""

import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import stopreasons  # noqa: E402

FIN = set(stopreasons.FINANCIAL)
MAP = {
    # ours (set of classes)                              theirs (set of predictions; any of several per trial)
    "financial or strategic": (FIN, {"Business_Administrative"}),
    "financial or strategic + sponsor decision": (FIN | {"Sponsor decision, unspecified"}, {"Business_Administrative"}),
    "efficacy / futility": ({"Efficacy / futility"}, {"Negative", "Interim_Analysis", "Insufficient_Data"}),
    "safety / benefit-risk": ({"Safety / benefit-risk"}, {"Safety_Sideeffects"}),
    "enrolment": ({"Enrolment"}, {"Insufficient_Enrollment"}),
    "COVID-19": ({"COVID-19"}, {"Covid19"}),
}


def kappa(a, b):
    a, b = a.astype(bool), b.astype(bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe)


def compare(g, out, label):
    out.append("=" * 100 + f"\n{label}: {len(g)} trials")
    for name, (ours, theirs) in MAP.items():
        a = g.ours.isin(ours)
        b = g.preds.map(lambda p: any(x in theirs for x in p))
        tp = int((a & b).sum())
        out.append(
            f"  {name:44s} ours={int(a.sum()):6d} theirs={int(b.sum()):6d} both={tp:6d} "
            f"P(theirs|ours)={tp / a.sum():.3f} P(ours|theirs)={tp / b.sum():.3f} kappa={kappa(a, b):.3f}"
        )


def main(repo, R=os.path.join(ROOT, "results")):
    d = pd.read_csv(os.path.join(repo, "data", "stopped_predictions_formatted_30_09_22.csv"))
    d["ours"] = d.why_stopped.map(stopreasons.classify)
    g = d.groupby("nctid").agg(
        why=("why_stopped", "first"), ours=("ours", "first"), preds=("prediction", lambda x: sorted(set(x)))
    )
    out = [
        f"StopReasons predictions: {len(d)} rows, {len(g)} trials, {int(g.preds.str.len().gt(1).sum())} with more than one prediction",
        "Our class (rows) x their single prediction (columns; 'multi' = several predictions):",
        pd.crosstab(g.ours, g.preds.map(lambda p: p[0] if len(p) == 1 else "multi")).to_string(),
    ]
    compare(g, out, "All stopped trials in the StopReasons file")
    h4 = os.path.join(R, "h4_trials.csv.gz")
    if os.path.exists(h4):
        ids = set(pd.read_csv(h4, usecols=["nct_id"]).nct_id)
        compare(g[g.index.isin(ids)], out, "Industry Phase 1-3 drug trials of the H4 sample")
    # texts we call 'Other' that they call business/administrative: the main source of disagreement, for review
    o = g[g.ours.eq("Other") & g.preds.map(lambda p: "Business_Administrative" in p)]
    out.append("=" * 100 + f"\nOur 'Other' that they call Business_Administrative: {len(o)} trials; 25 examples:")
    out.extend("  - " + str(t)[:140] for t in o.why.head(25))
    b = g[g.ours.isin(FIN) & ~g.preds.map(lambda p: "Business_Administrative" in p)]
    out.append(
        "=" * 100
        + f"\nOur financial/strategic that they do not call Business_Administrative: {len(b)} trials; 25 examples:"
    )
    out.extend(f"  - [{p}] {str(t)[:120]}" for t, p in zip(b.why.head(25), b.preds.head(25)))
    text = "\n".join(out)
    open(os.path.join(R, "stopreasons_crosscheck.txt"), "w").write(text)
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:3])
