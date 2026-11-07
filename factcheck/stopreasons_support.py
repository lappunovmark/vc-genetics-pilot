"""Check that every pattern of the stop-reason classifier has support outside the held-out texts.

Usage (from the repository root): python factcheck/stopreasons_support.py STOPREASONS_REPO [RESULTS_DIR]
STOPREASONS_REPO: a clone of https://github.com/opentargets/StopReasons (file
data/stopped_predictions_formatted_30_09_22.csv, 28,561 stopped trials with their why_stopped text).

The classifier (pilot/stopreasons.py) is scored on 200 held-out hand-labelled texts. That score means nothing for a
pattern that was written with a held-out text in view, so the rule is: every top-level alternative of every class
pattern must match at least one text outside the held-out set, in the 400 tuning texts of results/rq2_hand_labels.csv
or in the StopReasons file with the held-out trials removed from it (negation handling applied first, as in the
classifier). Alternatives that match nothing
anywhere are reported too (dead patterns). Exit status 1 if any alternative is supported only by held-out texts.
Writes RESULTS_DIR/stopreasons_support.txt with the counts for every alternative.
"""

import os
import re
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import stopreasons  # noqa: E402


def alternatives(rx):
    """Split a regex on '|' at nesting depth 0."""
    out, depth, cur = [], 0, ""
    for ch in rx:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "|" and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def main(repo, R=os.path.join(ROOT, "results")):
    sr = pd.read_csv(os.path.join(repo, "data", "stopped_predictions_formatted_30_09_22.csv")).drop_duplicates("nctid")
    h = pd.read_csv(os.path.join(R, "rq2_hand_labels.csv"))
    held_ids = set(h[h.set.str.startswith("held-out")].nct_id)
    n_overlap = int(sr.nctid.isin(held_ids).sum())  # held-out trials registered by 2021 are in the StopReasons file too
    sr = sr[~sr.nctid.isin(held_ids)].why_stopped.astype(str).map(stopreasons.clean)
    tune = h[h.set.eq("tuning")].why_stopped.map(stopreasons.clean)
    held = h[h.set.str.startswith("held-out")].why_stopped.map(stopreasons.clean)
    rows = []
    for cls, rx in stopreasons.CLASSES:
        for alt in alternatives(rx):
            c = re.compile(alt, re.I)
            n = [int(s.map(lambda t: bool(c.search(t))).sum()) for s in (sr, tune, held)]
            rows.append((cls, alt, *n))
    t = pd.DataFrame(rows, columns=["class", "pattern", "stopreasons", "tuning", "heldout"])
    bad = t[(t.stopreasons + t.tuning).eq(0) & t.heldout.gt(0)]
    dead = t[(t.stopreasons + t.tuning + t.heldout).eq(0)]
    out = [
        f"StopReasons texts: {len(sr)} (after removing {n_overlap} held-out trials); tuning texts: {len(tune)}; "
        f"held-out texts: {len(held)}",
        f"alternatives checked: {len(t)}",
        "=" * 100,
        "Supported only by held-out texts (must be empty):",
        bad.to_string(index=False) if len(bad) else "  none",
        "=" * 100,
        f"Matching no text in any of the three sets (dead patterns, harmless): {len(dead)}",
        dead.to_string(index=False) if len(dead) else "  none",
        "=" * 100,
        "All alternatives:",
        t.to_string(index=False),
    ]
    text = "\n".join(out)
    open(os.path.join(R, "stopreasons_support.txt"), "w").write(text)
    print(text)
    return 1 if len(bad) else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
