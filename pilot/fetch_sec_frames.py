"""Cash and operating cash flow of all SEC filers for given years, from the XBRL "frames" API (public domain).

Usage: SEC_USER_AGENT="Name email" python pilot/fetch_sec_frames.py OUT_DIR [FIRST_YEAR LAST_YEAR]
One request per concept and period returns the value every filer reported for it. Year-end balances (CY<year>Q4I)
of cash, restricted cash and short-term investments, and the annual operating cash flow (CY<year>), 2017-2022 by
default. The SEC asks for a contact in the User-Agent header and for at most ten requests a second.
Writes OUT_DIR/sec_frames.csv.gz (concept, period, cik, entity, value, end date, accession) and a log.
"""

import os
import sys
import time

import pandas as pd
import requests

BASE = "https://data.sec.gov/api/xbrl/frames/us-gaap"
INSTANT = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "CashCashEquivalentsAndShortTermInvestments",
    "ShortTermInvestments",
    "MarketableSecuritiesCurrent",
    "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
]
DURATION = ["NetCashProvidedByUsedInOperatingActivities"]


def main(out, y0=2017, y1=2022):
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        raise SystemExit('set SEC_USER_AGENT="Your Name you@example.org"')
    os.makedirs(out, exist_ok=True)
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    rows, log = [], []
    for year in range(int(y0), int(y1) + 1):
        for concept, period in [(c, f"CY{year}Q4I") for c in INSTANT] + [(c, f"CY{year}") for c in DURATION]:
            url = f"{BASE}/{concept}/USD/{period}.json"
            for attempt in range(4):
                r = s.get(url, timeout=60)
                if r.status_code == 200 or r.status_code == 404:
                    break
                time.sleep(2 * (attempt + 1))
            if r.status_code != 200:
                log.append(f"{concept} {period}: HTTP {r.status_code}")
                continue
            d = pd.DataFrame(r.json().get("data", []))
            log.append(f"{concept} {period}: {len(d)} filers")
            if len(d):
                rows.append(d.assign(concept=concept, period=period)[["concept", "period", "cik", "entityName", "val", "end", "accn"]])  # fmt: skip
            time.sleep(0.3)
    pd.concat(rows, ignore_index=True).to_csv(f"{out}/sec_frames.csv.gz", index=False)
    open(f"{out}/sec_frames_log.txt", "w").write("\n".join(log) + "\n")  # no contact details in the log
    print("\n".join(log))


if __name__ == "__main__":
    main(*sys.argv[1:4])
