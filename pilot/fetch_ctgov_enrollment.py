"""Enrolment (number of participants) for every interventional study on ClinicalTrials.gov.

Usage: python pilot/fetch_ctgov_enrollment.py OUT.csv
Writes nct_id, enrollment, enrollment_type (ACTUAL or ESTIMATED). Kept apart from fetch_ctgov.py so that the registry
snapshot of 17 October 2026 used by the pilot is not re-downloaded: this file is joined to the snapshot by nct_id, so
only the enrolment values carry the later download date.
"""

import sys

import pandas as pd
from fetch_ctgov import API, get

FIELDS = "NCTId,EnrollmentCount,EnrollmentType"


def main(out):
    rows, token, n = [], None, 0
    while True:
        q = {"filter.advanced": "AREA[StudyType]INTERVENTIONAL", "pageSize": 1000, "format": "json", "fields": FIELDS}
        if token:
            q["pageToken"] = token
        js = get(q)
        for st in js.get("studies", []):
            p = st.get("protocolSection", {})
            e = (p.get("designModule", {}) or {}).get("enrollmentInfo", {}) or {}
            rows.append(
                {
                    "nct_id": (p.get("identificationModule", {}) or {}).get("nctId"),
                    "enrollment": e.get("count"),
                    "enrollment_type": e.get("type"),
                }
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
