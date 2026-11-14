"""Download the EDGAR quarterly master index and keep beneficial-ownership and registration filings.

Usage: python fetch_edgar_owners.py OUT_DIR [FIRST_YEAR] [LAST_YEAR]

Source: https://www.sec.gov/Archives/edgar/full-index/YYYY/QTRn/master.gz (one line per filing and party:
CIK|Company Name|Form Type|Date Filed|Filename). A Schedule 13D or 13G is indexed under the reporting person (the
investor) and under the subject company (the issuer), with the same accession number in the file name, so the pairs
(investor, issuer) can be recovered from the index alone. Registration and annual-report forms identify operating
companies that are or became public, and when.
SEC asks automated clients to identify themselves; set SEC_USER_AGENT="Name email" in the environment.

Writes OUT_DIR/edgar_ownership.csv.gz (SC 13D, SC 13D/A, SC 13G, SC 13G/A and, from 2025, SCHEDULE 13D/13G lines), OUT_DIR/edgar_registrants.csv.gz
(S-1, S-1/A, F-1, 424B4, 10-K, 10-K405, 20-F, 40-F lines) and OUT_DIR/edgar_index_log.txt.
"""

import csv
import gzip
import os
import sys
import time

import requests

URL = "https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/master.gz"
# From 18 December 2024 the schedules are filed as structured data under new form names.
OWNERSHIP = {
    "SC 13D",
    "SC 13D/A",
    "SC 13G",
    "SC 13G/A",
    "SCHEDULE 13D",
    "SCHEDULE 13D/A",
    "SCHEDULE 13G",
    "SCHEDULE 13G/A",
}
REGISTRANT = {"S-1", "S-1/A", "F-1", "F-1/A", "424B4", "10-K", "10-K405", "20-F", "40-F"}
FIELDS = ["cik", "name", "form", "date", "filename"]


def session():
    s = requests.Session()
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        sys.exit("Set SEC_USER_AGENT, e.g. 'Jane Doe jane@example.org'")
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate", "Host": "www.sec.gov"})
    return s


def parse(raw):
    """Yield (cik, name, form, date, filename) from a master.idx; the header ends at the dashed line."""
    text = gzip.decompress(raw).decode("latin-1")
    started = False
    for line in text.splitlines():
        if not started:
            started = line.startswith("-----")
            continue
        parts = line.split("|")
        if len(parts) == 5:
            yield parts


def main(out, first_year=2001, last_year=2026):
    os.makedirs(out, exist_ok=True)
    s = session()
    log = open(os.path.join(out, "edgar_index_log.txt"), "w", encoding="utf-8")
    own = gzip.open(os.path.join(out, "edgar_ownership.csv.gz"), "wt", newline="", encoding="utf-8")
    reg = gzip.open(os.path.join(out, "edgar_registrants.csv.gz"), "wt", newline="", encoding="utf-8")
    w_own, w_reg = csv.writer(own), csv.writer(reg)
    w_own.writerow(FIELDS)
    w_reg.writerow(FIELDS)
    for y in range(int(first_year), int(last_year) + 1):
        for q in range(1, 5):
            url = URL.format(y=y, q=q)
            r = None
            for attempt in range(3):
                try:
                    r = s.get(url, timeout=120)
                    if r.status_code in (403, 429, 503):
                        time.sleep(10 * (attempt + 1))
                        continue
                    break
                except requests.RequestException as e:
                    print(f"{y}Q{q} error {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                    r = None
                    time.sleep(10)
            if r is None or r.status_code != 200:
                line = f"{y}Q{q}\tmissing\tstatus {getattr(r, 'status_code', None)}"
                log.write(line + "\n")
                log.flush()
                print(line, flush=True)
                if y >= 2026:
                    break  # future quarters
                continue
            n_all = n_own = n_reg = 0
            for cik, name, form, date, fname in parse(r.content):
                n_all += 1
                row = [cik.strip().lstrip("0"), name.strip(), form.strip(), date.strip(), fname.strip()]
                if form.strip() in OWNERSHIP:
                    w_own.writerow(row)
                    n_own += 1
                elif form.strip() in REGISTRANT:
                    w_reg.writerow(row)
                    n_reg += 1
            line = f"{y}Q{q}\tlines {n_all}\townership {n_own}\tregistrants {n_reg}\tbytes {len(r.content)}"
            log.write(line + "\n")
            log.flush()
            print(line, flush=True)
            time.sleep(0.2)  # SEC fair-access limit is 10 requests per second
    own.close()
    reg.close()
    log.close()


if __name__ == "__main__":
    main(*sys.argv[1:4])
