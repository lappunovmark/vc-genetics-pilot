"""Score the author's blind coding of the 200 held-out stop-reason texts.

Usage (from the repository root): python factcheck/double_coding/double_coding_eval.py [coding_sheet.xlsx | coding_answers.csv]
Joins the filled sheet to results/rq2_hand_labels.csv through key.csv and reports, for the author's labels against
(a) the first-pass labels, (b) classifier v3 and (c) classifier v4: agreement, Cohen's kappa, the confusion table, precision and recall
of the financial-or-strategic class, and every disagreement for adjudication. Writes results/double_coding.txt and
results/double_coding_disagreements.csv.
"""

import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
from stopreasons import FINANCIAL  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def kappa(a, b):
    a, b = pd.Series(a).astype(str), pd.Series(b).astype(str)
    po = (a == b).mean()
    pa, pb = a.value_counts(normalize=True), b.value_counts(normalize=True)
    pe = sum(pa.get(c, 0) * pb.get(c, 0) for c in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fin_scores(truth, pred):
    y, p = truth.isin(FINANCIAL), pred.isin(FINANCIAL)
    tp = int((y & p).sum())
    return tp / p.sum() if p.sum() else float("nan"), tp / y.sum() if y.sum() else float("nan")


def main(sheet=os.path.join(HERE, "coding_sheet.xlsx")):
    if sheet.lower().endswith(".csv"):  # answers exported by coding_page.html
        s = pd.read_csv(sheet).rename(columns={"label": "author_label"})
    else:
        s = pd.read_excel(sheet, sheet_name="Coding").rename(columns={"label": "author_label"})
    s = s[["id", "author_label", "confidence", "note"]]
    key = pd.read_csv(os.path.join(HERE, "key.csv"))
    d = pd.read_csv(os.path.join(ROOT, "results", "rq2_hand_labels.csv"))
    m = key.merge(s, on="id").merge(d, on="nct_id")
    done = m[m.author_label.notna()]
    out = [f"texts coded: {len(done)} of {len(m)}"]
    if len(done) < len(m):
        out.append("WARNING: the sheet is not complete; results below use the coded rows only")
    for name, col in (
        ("first-pass labels (AI assistant)", "hand_label"),
        ("classifier v3", "classifier_v3"),
        ("classifier v4", "classifier_v4"),
    ):
        agree = (done.author_label == done[col]).mean()
        prec, rec = fin_scores(done.author_label, done[col])
        out.extend(
            [
                "=" * 90,
                f"author vs {name}: agreement {agree:.4f}, kappa {kappa(done.author_label, done[col]):.4f}, "
                f"financial-or-strategic precision {prec:.4f} recall {rec:.4f} (author's labels as reference)",
                pd.crosstab(done.author_label, done[col], margins=True).to_string(),
            ]
        )
    if done.confidence.notna().any():
        low = done[done.confidence.astype(str).str.lower().eq("low")]
        out.append(f"low-confidence rows: {len(low)}; agreement with first pass among them: "
                   f"{(low.author_label == low.hand_label).mean():.4f}")  # fmt: skip
    dis = done[done.author_label != done.hand_label][
        [
            "id",
            "nct_id",
            "why_stopped",
            "author_label",
            "hand_label",
            "classifier_v3",
            "classifier_v4",
            "confidence",
            "note",
        ]
    ]
    dis.to_csv(os.path.join(ROOT, "results", "double_coding_disagreements.csv"), index=False)
    out.append(f"disagreements with the first pass written to results/double_coding_disagreements.csv ({len(dis)})")
    text = "\n".join(out)
    open(os.path.join(ROOT, "results", "double_coding.txt"), "w").write(text)
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:2])
