"""Link industry trial sponsors to NIH SBIR/STTR awardees (public-validation signal and control for the full study).

Usage: python sbir_link.py SBIR_CSV CTGOV_ALL_CSV RESULTS_DIR
Matching (precision first):
  1. exact match of normalised names (legal suffixes and generic words removed, as in rq2_stops.norm_sponsor);
  2. fuzzy match within blocks sharing the first normalised token: rapidfuzz token_sort_ratio >= 92 and the shorter
     name at least 6 characters.
Every match, exact or fuzzy, is written out with both original names for hand validation (normalisation strips generic
words such as 'pharmaceuticals', so two different firms can share a core name). A match is used only if the two names
agree after removing legal forms alone (inc, ltd, llc, ...) and it is not rejected in sbir_decisions.csv, or if it is
accepted there after hand review (renamed firms, predecessors, subsidiaries). A sponsor counts as SBIR/STTR-funded
before a trial if its earliest award fiscal year is earlier than the trial's start year.
Writes RESULTS_DIR/sbir_sponsors.csv (one row per matched sponsor), sbir_match_review.csv (every match),
sbir_trials.csv.gz and sbir_summary.txt.
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = process = None


LEGAL = re.compile(
    r"\b(incorporated|inc|ltd|limited|llc|corp|corporation|co|company|gmbh|ag|sa|plc|bv|nv|spa|kk|pty|"
    r"srl|ab|as|oy|kg|lp|the)\b"
)
DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sbir_decisions.csv")


def strict(s):
    s = re.sub(r"[^a-z0-9]+", " ", str(s).lower())
    return re.sub(r"\s+", " ", LEGAL.sub(" ", s)).strip()


def apply_decisions(m, path=DECISIONS):
    d = pd.read_csv(path)
    dec = {(strict(a), strict(b)): v for a, b, v in zip(d.lead_sponsor, d.sbir_org, d.decision)}
    m = m.copy()
    m["strict_eq"] = [strict(a) == strict(b) for a, b in zip(m.lead_sponsor, m.sbir_org)]
    m["decision"] = [dec.get((strict(a), strict(b))) for a, b in zip(m.lead_sponsor, m.sbir_org)]
    m["accepted"] = (m.strict_eq & m.decision.ne("reject")) | m.decision.eq("accept")
    return m


def awardees(path):
    s = pd.read_csv(path, dtype=str)
    s["fiscal_year"] = pd.to_numeric(s.fiscal_year, errors="coerce")
    s["award_amount"] = pd.to_numeric(s.award_amount, errors="coerce")
    s["norm"] = s.org_name.map(rq2_stops.norm_sponsor)
    s = s[s.norm.notna() & s.norm.str.len().ge(3)]
    g = s.groupby("norm").agg(
        sbir_first_fy=("fiscal_year", "min"),
        sbir_last_fy=("fiscal_year", "max"),
        sbir_awards=("appl_id", "nunique"),
        sbir_projects=("core_project_num", "nunique"),
        sbir_amount=("award_amount", "sum"),
        sbir_org=("org_name", "first"),
        sbir_state=("org_state", "first"),
        sbir_country=("org_country", "first"),
        sbir_phase2=("activity_code", lambda x: x.isin(["R42", "R44", "U44"]).any()),
    )
    return g.reset_index()


def sponsors_from_ctgov(path):
    ct = rq2_stops.load(path)
    g = ct.groupby("sponsor_norm").agg(
        lead_sponsor=("lead_sponsor", "first"),
        n_trials=("nct_id", "nunique"),
        group=("group", "first"),
        first_trial_year=("start_year", "min"),
    )
    return g.reset_index().rename(columns={"sponsor_norm": "norm"}), ct


def match(sp, aw, threshold=92, min_len=6):
    exact = sp.merge(aw, on="norm")
    exact["match"] = "exact"
    exact["score"] = 100.0
    exact["sbir_norm"] = exact.norm
    rest = sp[~sp.norm.isin(exact.norm)].copy()
    rows = []
    if process is not None and len(rest):
        aw = aw.assign(tok=aw.norm.str.split().str[0])
        blocks = {t: d for t, d in aw.groupby("tok")}
        for r in rest.itertuples(index=False):
            if not isinstance(r.norm, str):
                continue
            cand = blocks.get(r.norm.split()[0])
            if cand is None:
                continue
            best = process.extractOne(r.norm, cand.norm.tolist(), scorer=fuzz.token_sort_ratio)
            if best and best[1] >= threshold and min(len(r.norm), len(best[0])) >= min_len:
                rows.append({"norm": r.norm, "sbir_norm": best[0], "score": best[1]})
    fz = pd.DataFrame(rows, columns=["norm", "sbir_norm", "score"])
    if len(fz):
        fz = fz.merge(sp, on="norm").merge(aw.drop(columns="tok").rename(columns={"norm": "sbir_norm"}), on="sbir_norm")
        fz["match"] = "fuzzy"
    return pd.concat([exact, fz], ignore_index=True)


def main(sbir_csv, ctg, R):
    aw = awardees(sbir_csv)
    sp, ct = sponsors_from_ctgov(ctg)
    m = apply_decisions(match(sp, aw))
    m.to_csv(f"{R}/sbir_sponsors.csv", index=False)
    m[
        [
            "match",
            "accepted",
            "decision",
            "lead_sponsor",
            "norm",
            "sbir_org",
            "sbir_norm",
            "score",
            "sbir_state",
            "n_trials",
            "first_trial_year",
            "sbir_first_fy",
        ]
    ].sort_values(["match", "score"]).to_csv(f"{R}/sbir_match_review.csv", index=False)
    acc = m[m.accepted]
    ct = ct.merge(
        acc[["norm", "sbir_first_fy"]].rename(columns={"norm": "sponsor_norm"}), on="sponsor_norm", how="left"
    )
    ct["sbir_before"] = ct.sbir_first_fy.lt(ct.start_year)
    out = [
        f"awardee organisations (normalised): {len(aw)}; industry sponsors on ClinicalTrials.gov: {len(sp)}",
        f"candidate matches: {len(m)} (exact {int(m.match.eq('exact').sum())}, fuzzy {int(m.match.eq('fuzzy').sum())}); "
        f"accepted {len(acc)} (strict name agreement {int((m.strict_eq & m.accepted).sum())}, "
        f"accepted after hand review {int((~m.strict_eq & m.accepted).sum())}, rejected {int((~m.accepted).sum())})",
        "",
        "Share of industry Phase 1-3 drug trials whose sponsor had an NIH SBIR/STTR award before the trial started:",
        ct.groupby("group").sbir_before.agg(["mean", "sum", "size"]).round(4).to_string(),
        "",
        "Share of sponsors ever matched, by group:",
        sp.assign(matched=sp.norm.isin(acc.norm))
        .groupby("group")
        .matched.agg(["mean", "sum", "size"])
        .round(4)
        .to_string(),
    ]
    open(f"{R}/sbir_summary.txt", "w").write("\n".join(out))
    ct[["nct_id", "sponsor_norm", "group", "start_year", "sbir_first_fy", "sbir_before"]].to_csv(
        f"{R}/sbir_trials.csv.gz", index=False
    )
    print("\n".join(out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
