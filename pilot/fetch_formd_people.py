"""People named in Form D filings: directors of biopharma issuers and the managers of venture-capital funds.

Usage: SEC_USER_AGENT="Name email" python pilot/fetch_formd_people.py OUT_DIR [FIRST_YEAR]

Why: Form D does not name investors, but it names the issuer's executive officers, directors and promoters, and a
venture investor usually takes a board seat. Venture-capital funds file Form D themselves (industry group "Pooled
Investment Fund", fund type "Venture Capital Fund") and name their managers. A person who is a director of a
biopharma issuer and a manager of a venture fund links the two with SEC data only.

Reads the same quarterly Form D data sets as fetch_formd.py (FORMDSUBMISSION, ISSUERS, OFFERING, RELATEDPERSONS).
Writes to OUT_DIR:
  formd_people_biopharma.csv.gz  related persons of offerings by biotech, pharma and other health care issuers
                                 (not pooled funds), with the issuer's CIK and name and the filing date
  formd_vc_funds.csv.gz          issuers that are pooled investment funds of type venture capital
  formd_people_vc_funds.csv.gz   related persons of those funds
  formd_people_log.txt           one line per archive (rows kept, columns seen)
"""

import io
import os
import sys
import time
import zipfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_formd as F


def pick(df, *needles):
    """First column whose name contains every needle (the data sets renamed a few columns over the years)."""
    for c in df.columns:
        if all(n in c for n in needles):
            return c
    return None


def one_archive(zf):
    off, iss, sub, rel = (F.read_table(zf, s) for s in ("OFFERING", "ISSUERS", "FORMDSUBMISSION", "RELATEDPERSONS"))
    if any(t is None for t in (off, iss, sub, rel)):
        return None, None, None, "table missing"
    ind = off[pick(off, "INDUSTRYGROUPTYPE")].fillna("").str.strip().str.lower()
    pooled_col, fund_col = pick(off, "POOLEDINVESTMENTFUND"), pick(off, "INVESTMENTFUNDTYPE")
    pooled = off[pooled_col].fillna("").str.lower().isin(["true", "1", "y", "yes"]) if pooled_col else False
    bio = off[ind.isin(F.INDUSTRY) & ~pooled].ACCESSIONNUMBER
    is_fund = ind.eq("pooled investment fund")
    vc = off[is_fund & off[fund_col].fillna("").str.contains("venture", case=False)] if fund_col else off.iloc[0:0]
    primary = iss.drop_duplicates("ACCESSIONNUMBER")  # the first issuer row is the primary issuer
    head = primary[["ACCESSIONNUMBER", "CIK", "ENTITYNAME", "STATEORCOUNTRY"]].merge(
        sub[["ACCESSIONNUMBER", "FILING_DATE", "SUBMISSIONTYPE"]], on="ACCESSIONNUMBER", how="left"
    )
    people_bio = rel[rel.ACCESSIONNUMBER.isin(set(bio))].merge(head, on="ACCESSIONNUMBER", how="left")
    funds = head[head.ACCESSIONNUMBER.isin(set(vc.ACCESSIONNUMBER))]
    people_vc = rel[rel.ACCESSIONNUMBER.isin(set(vc.ACCESSIONNUMBER))].merge(head, on="ACCESSIONNUMBER", how="left")
    cols = f"fund type column: {fund_col}; related-person columns: {','.join(rel.columns)}"
    return people_bio, funds, people_vc, cols


def main(out, first_year=2009):
    os.makedirs(out, exist_ok=True)
    s = F.session()
    parts = {"bio": [], "funds": [], "vc": []}
    with open(os.path.join(out, "formd_people_log.txt"), "w", encoding="utf-8") as logf:

        def note(line):
            logf.write(line + "\n")
            logf.flush()
            print(line[:200], flush=True)

        urls = F.archive_urls(s, first_year)
        note(f"archives to fetch: {len(urls)}")
        for y, q, u in urls:
            try:
                r = s.get(u, timeout=180)
                r.raise_for_status()
                zf = zipfile.ZipFile(io.BytesIO(r.content))
                pb, fu, pv, cols = one_archive(zf)
            except Exception as e:  # a missing quarter must not stop the run; it is logged
                note(f"{y}q{q}: FAILED {e!r}")
                continue
            if pb is None:
                note(f"{y}q{q}: SKIPPED {cols}")
                continue
            for k, d in (("bio", pb), ("funds", fu), ("vc", pv)):
                parts[k].append(d.assign(archive=f"{y}q{q}"))
            note(f"{y}q{q}: biopharma people {len(pb)}; venture funds {len(fu)}; their people {len(pv)}; {cols}")
            time.sleep(0.5)
    for k, name in (("bio", "formd_people_biopharma"), ("funds", "formd_vc_funds"), ("vc", "formd_people_vc_funds")):
        d = pd.concat(parts[k], ignore_index=True) if parts[k] else pd.DataFrame()
        d.to_csv(os.path.join(out, f"{name}.csv.gz"), index=False)
        print(name, len(d), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2009)
