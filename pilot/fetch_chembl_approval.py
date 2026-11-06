"""Download the year of first approval of every approved molecule from the ChEMBL web service.

Usage: python fetch_chembl_approval.py OUT.csv
Source: https://www.ebi.ac.uk/chembl/api/data/molecule (max_phase = 4, i.e. approved), paged. The ChEMBL id is the
drug id used by Open Targets, so the file joins directly to the programme panel. Writes molecule_chembl_id,
pref_name, first_approval, max_phase, and the ChEMBL release reported by the service.
"""

import csv
import sys
import time

import requests

BASE = "https://www.ebi.ac.uk/chembl/api/data"
FIELDS = ["molecule_chembl_id", "pref_name", "first_approval", "max_phase"]


def main(out):
    s = requests.Session()
    s.headers["User-Agent"] = "vc-genetics-pilot (independent research project; contact via repository)"
    status = s.get(f"{BASE}/status.json", timeout=60).json()
    release = status.get("chembl_db_version") or status.get("chembl_release")
    rows, url = [], f"{BASE}/molecule.json?max_phase=4&limit=1000&only={','.join(FIELDS)}"
    while url:
        r = s.get(url, timeout=120)
        r.raise_for_status()
        j = r.json()
        rows.extend({k: m.get(k) for k in FIELDS} for m in j["molecules"])
        nxt = j["page_meta"].get("next")
        url = "https://www.ebi.ac.uk" + nxt if nxt else None
        print(f"{len(rows)} of {j['page_meta']['total_count']}", file=sys.stderr)
        time.sleep(0.5)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS + ["chembl_release"])
        w.writeheader()
        for row in rows:
            w.writerow({**row, "chembl_release": release})
    print(f"wrote {len(rows)} approved molecules ({release}) to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
