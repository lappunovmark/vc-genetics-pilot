"""Download the IPO prospectuses (form 424B4) of trial sponsors from SEC EDGAR (public domain).

Usage: SEC_USER_AGENT="Name email" python pilot/fetch_ipo_prospectus.py EDGAR_DIR RESULTS_DIR OUT_DIR
(EDGAR_DIR holds edgar_registrants.csv.gz of fetch_edgar_owners.py; RESULTS_DIR holds owners_sponsors.csv of
owners_link.py; plan written before the download: docs/plan_ipo_prospectus.md)

The IPO prospectus of a registrant is its first 424B4 filed on or after its first S-1 or F-1, if the registrant
filed no annual report (10-K, 10-K405, 20-F, 40-F) before that registration. `own_name` marks filings whose filer
name at the time has the same first word, after normalisation, as one of the sponsor names linked to the registrant;
the others are later renamings or companies that merged into a listed company.
One request per filing (the complete submission text file named in the EDGAR index); the prospectus itself, the first
document of the submission, is kept. The SEC asks for a contact in the User-Agent header and for at most ten requests
a second. Files already downloaded are skipped, so the script can be run again after an interruption.
Writes OUT_DIR/ipo_prospectus_index.csv, OUT_DIR/docs/<cik>_<accession>.htm.gz and OUT_DIR/ipo_prospectus_log.txt.
"""

import gzip
import os
import re
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq2_stops

BASE = "https://www.sec.gov/Archives/"
ANNUAL = ["10-K", "10-K405", "20-F", "40-F"]
DOC = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
TEXT = re.compile(r"<TEXT>(.*)</TEXT>", re.S)


def first_word(name):
    return (rq2_stops.norm_sponsor(name) or " ").split(" ")[0]


def select(edgar_dir, results_dir):
    """One row per registrant of a sponsor: its IPO prospectus in the EDGAR index."""
    ow = pd.read_csv(os.path.join(results_dir, "owners_sponsors.csv"), dtype=str)
    norms = {}
    for n, c in zip(ow.norm, ow.ciks):
        if isinstance(c, str):
            for x in c.replace(",", ";").split(";"):
                if x.strip().isdigit():
                    norms.setdefault(str(int(x)), set()).add(n)
    r = pd.read_csv(os.path.join(edgar_dir, "edgar_registrants.csv.gz"), dtype=str)
    r["cik"] = r.cik.str.lstrip("0")
    r = r[r.cik.isin(norms)].copy()
    r["date"] = pd.to_datetime(r.date)
    reg = r[r.form.isin(["S-1", "F-1"])].groupby("cik").date.min().rename("first_registration")
    ann = r[r.form.isin(ANNUAL)].groupby("cik").date.min().rename("first_annual_report")
    p = r[r.form.eq("424B4")].merge(reg, on="cik").merge(ann, on="cik", how="left")
    p = p[p.date >= p.first_registration].sort_values(["cik", "date", "filename"]).drop_duplicates("cik")
    p = p[p.first_annual_report.isna() | (p.first_annual_report > p.first_registration)].copy()
    p["sponsors"] = p.cik.map(lambda c: "; ".join(sorted(norms[c])))
    p["own_name"] = [int(any(first_word(e) == n.split(" ")[0] for n in norms[c])) for c, e in zip(p.cik, p.name)]
    p["accession"] = p.filename.str.extract(r"(\d{10}-\d{2}-\d{6})", expand=False)
    cols = ["cik", "sponsors", "name", "date", "first_registration", "own_name", "accession", "filename"]
    return p.sort_values(["date", "cik"])[cols]


def prospectus(raw):
    """The first document of a complete submission text file (the prospectus), or None."""
    m = DOC.search(raw)
    if not m:
        return None
    t = TEXT.search(m.group(1))
    return t.group(1) if t else m.group(1)


def main(edgar_dir, results_dir, out):
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua or "@" not in ua:
        raise SystemExit('set SEC_USER_AGENT="Your Name you@example.org"')
    os.makedirs(os.path.join(out, "docs"), exist_ok=True)
    idx = select(edgar_dir, results_dir)
    idx.to_csv(os.path.join(out, "ipo_prospectus_index.csv"), index=False)
    print(
        f"IPO prospectuses of sponsors in the index: {len(idx)}; under the sponsor's own name: {int(idx.own_name.sum())}"
    )
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate", "Host": "www.sec.gov"})
    log, done, failed = [], 0, 0
    for i, row in enumerate(idx.itertuples(), 1):
        path = os.path.join(out, "docs", f"{row.cik}_{row.accession}.htm.gz")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            done += 1
            continue
        r = None
        for attempt in range(4):
            try:
                r = s.get(BASE + row.filename, timeout=180)
            except requests.RequestException as e:
                r = None
                err = repr(e)
            if r is not None and r.status_code == 200:
                break
            time.sleep(5 * (attempt + 1))  # the SEC answers 403 or 429 when asked too fast
        if r is None or r.status_code != 200:
            failed += 1
            log.append(f"{row.cik} {row.accession}: " + (f"HTTP {r.status_code}" if r is not None else err))
            continue
        doc = prospectus(r.content.decode("latin-1"))
        if not doc or len(doc) < 10000:
            failed += 1
            log.append(f"{row.cik} {row.accession}: no prospectus document found in the submission")
            continue
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(doc)
        done += 1
        log.append(f"{row.cik} {row.accession}: {len(doc)} characters")
        if i % 25 == 0:
            print(f"  {i} of {len(idx)}")
        time.sleep(0.25)
    summary = f"prospectuses saved: {done} of {len(idx)}; failed: {failed}"
    with open(os.path.join(out, "ipo_prospectus_log.txt"), "w", encoding="utf-8") as fh:  # no contact details here
        fh.write("\n".join([summary] + log) + "\n")
    print(summary)


if __name__ == "__main__":
    main(*sys.argv[1:4])
