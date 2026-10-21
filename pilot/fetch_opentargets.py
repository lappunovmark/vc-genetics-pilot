"""Download the Open Targets Platform datasets the pilot needs (release 26.03 or later layout:
output/<dataset>/*.parquet). Usage: python fetch_opentargets.py OUT_DIR   (env OT_RELEASE, default = latest)"""

import os
import re
import sys
import time

import requests

BASE = os.environ.get("OT_BASE", "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/")
DATASETS = [
    "evidence_clinical_precedence",
    "clinical_report",
    "clinical_indication",
    "clinical_target",
    "drug_molecule",
    "drug_mechanism_of_action",
    "target",
    "disease",
]
S = requests.Session()


def ls(url):
    for i in range(5):
        try:
            r = S.get(url, timeout=60)
            r.raise_for_status()
            return re.findall(r'href="([^"?#/][^"?#]*)"', r.text)
        except Exception as e:
            print("retry", url, e, flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def main(out):
    rel = (
        os.environ.get("OT_RELEASE") or sorted(h.rstrip("/") for h in ls(BASE) if re.fullmatch(r"\d{2}\.\d{2}/", h))[-1]
    )
    root = f"{BASE}{rel}/output/"
    print("Open Targets release", rel, flush=True)
    for d in DATASETS:
        files = [f for f in ls(root + d + "/") if f.endswith(".parquet")]
        if not files:
            raise SystemExit(f"{d}: no parquet files under {root}{d}/ (layout changed?)")
        os.makedirs(os.path.join(out, d), exist_ok=True)
        for f in files:
            p = os.path.join(out, d, f)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                continue
            with S.get(root + d + "/" + f, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(p, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        print(d, len(files), "files", flush=True)
    open(os.path.join(out, "RELEASE"), "w").write(rel)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ot")
