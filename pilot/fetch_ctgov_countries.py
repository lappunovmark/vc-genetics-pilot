"""Countries of the trial sites of every interventional study on ClinicalTrials.gov.

Usage: python pilot/fetch_ctgov_countries.py OUT.csv
Writes nct_id, countries (the distinct countries of the study's listed sites, joined by "|"; empty when no site is
listed). Kept apart from fetch_ctgov.py so that the registry snapshot of 17 October 2026 is not re-downloaded: this
file is joined to the snapshot by nct_id, so only the site countries carry the later download date. Used by
factcheck/link_audit.py (plan: docs/plan_link_audit.md).
"""

import sys

import pandas as pd
from fetch_ctgov import API, get

FIELDS = "NCTId,LocationCountry"


def main(out):
    rows, token, n = [], None, 0
    while True:
        q = {"filter.advanced": "AREA[StudyType]INTERVENTIONAL", "pageSize": 1000, "format": "json", "fields": FIELDS}
        if token:
            q["pageToken"] = token
        js = get(q)
        for st in js.get("studies", []):
            p = st.get("protocolSection", {})
            locs = (p.get("contactsLocationsModule", {}) or {}).get("locations", []) or []
            countries = sorted({x.get("country") for x in locs if x.get("country")})
            rows.append(
                {"nct_id": (p.get("identificationModule", {}) or {}).get("nctId"), "countries": "|".join(countries)}
            )
        n += 1
        token = js.get("nextPageToken")
        if n % 20 == 0:
            print(n, "pages", len(rows), "rows", flush=True)
        if not token:
            break
    pd.DataFrame(rows).to_csv(out, index=False)
    print(len(rows), "rows ->", out, "| API:", API)


if __name__ == "__main__":
    main(sys.argv[1])
