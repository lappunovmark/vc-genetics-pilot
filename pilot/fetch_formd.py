"""Download SEC Form D data sets and keep private offerings by biotech, pharma and other health care issuers.

Usage: python fetch_formd.py OUT_DIR [FIRST_YEAR]

Source: SEC Form D data sets (quarterly, from 2009), https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets
Each quarterly archive has FORMDSUBMISSION, ISSUERS and OFFERING tables keyed by ACCESSIONNUMBER. Kept: offerings
whose industry group is Biotechnology, Pharmaceuticals or Other Health Care and that are not pooled investment funds,
joined to the filing date and the primary issuer (name, CIK, state, year of incorporation, previous names).
SEC asks automated clients to identify themselves; set SEC_USER_AGENT="Name email" in the environment.

Writes OUT_DIR/formd_biopharma.csv.gz and OUT_DIR/formd_fetch_log.txt (one line per archive: rows kept, columns seen).
"""

import csv
import io
import os
import re
import sys
import time
import zipfile

import pandas as pd
import requests

LIST_URL = "https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets"
PATTERN = "https://www.sec.gov/files/structureddata/data/form-d-data-sets/{y}q{q}_d.zip"
INDUSTRY = {"biotechnology", "pharmaceuticals", "other health care"}
OFFER_COLS = [
    "ACCESSIONNUMBER",
    "INDUSTRYGROUPTYPE",
    "ISAMENDMENT",
    "PREVIOUSACCESSIONNUMBER",
    "SALE_DATE",
    "YETTOOCCUR",
    "ISEQUITYTYPE",
    "ISDEBTTYPE",
    "ISOPTIONTOACQUIRETYPE",
    "ISSECURITYTOBEACQUIREDTYPE",
    "ISPOOLEDINVESTMENTFUNDTYPE",
    "ISBUSINESSCOMBINATIONTRANS",
    "TOTALOFFERINGAMOUNT",
    "TOTALAMOUNTSOLD",
    "TOTALNUMBERALREADYINVESTED",
    "REVENUERANGE",
    "FEDERALEXEMPTIONS_ITEMS_LIST",
]
ISSUER_COLS = [
    "ACCESSIONNUMBER",
    "CIK",
    "ENTITYNAME",
    "STATEORCOUNTRY",
    "JURISDICTIONOFINC",
    "ENTITYTYPE",
    "YEAROFINC_VALUE_ENTERED",
    "ISSUER_PREVIOUSNAME_1",
    "ISSUER_PREVIOUSNAME_2",
    "ISSUER_PREVIOUSNAME_3",
    "EDGAR_PREVIOUSNAME_1",
    "EDGAR_PREVIOUSNAME_2",
    "EDGAR_PREVIOUSNAME_3",
]
SUB_COLS = ["ACCESSIONNUMBER", "FILING_DATE", "SUBMISSIONTYPE", "TESTORLIVE"]


def session():
    s = requests.Session()
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        sys.exit("Set SEC_USER_AGENT, e.g. 'Jane Doe jane@example.org'")
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


def archive_urls(s, first_year):
    """Archive links from the SEC listing page; falls back to the documented file pattern."""
    urls = []
    try:
        r = s.get(LIST_URL, timeout=60)
        r.raise_for_status()
        for href in re.findall(r'href="([^"]+\.zip)"', r.text):
            if "form-d" in href.lower() or re.search(r"\d{4}q\d_d\.zip$", href.lower()):
                urls.append(href if href.startswith("http") else "https://www.sec.gov" + href)
    except requests.RequestException as e:
        print("listing page failed:", e, flush=True)
    if not urls:
        urls = [PATTERN.format(y=y, q=q) for y in range(first_year, 2027) for q in range(1, 5)]
    keep = []
    for u in dict.fromkeys(urls):
        m = re.search(r"(\d{4})q(\d)", u.lower())
        if m and int(m.group(1)) >= first_year:
            keep.append((int(m.group(1)), int(m.group(2)), u))
    return sorted(keep)


def read_table(zf, stem):
    name = next((n for n in zf.namelist() if os.path.basename(n).upper().startswith(stem)), None)
    if name is None:
        return None
    raw = zf.read(name)
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(text), sep="\t", dtype=str, quoting=csv.QUOTE_NONE, on_bad_lines="skip")
    df.columns = [c.strip().upper() for c in df.columns]
    return df


def main(out, first_year=2009):
    os.makedirs(out, exist_ok=True)
    s = session()
    frames, log = [], []
    for y, q, url in archive_urls(s, first_year):
        for attempt in range(4):
            try:
                r = s.get(url, timeout=300)
                if r.status_code == 404:
                    break
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"{y}q{q} attempt {attempt + 1}: {e}", flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            log.append(f"{y}q{q}\tFAILED\t{url}")
            continue
        if r.status_code == 404:
            log.append(f"{y}q{q}\t404\t{url}")
            continue
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        off, iss, sub = (read_table(zf, k) for k in ("OFFERING", "ISSUERS", "FORMDSUBMISSION"))
        if off is None or iss is None or sub is None:
            log.append(f"{y}q{q}\tMISSING TABLES\t{zf.namelist()}")
            continue
        o = off[off.get("INDUSTRYGROUPTYPE", pd.Series(dtype=str)).str.strip().str.lower().isin(INDUSTRY)]
        o = o[o.get("ISPOOLEDINVESTMENTFUNDTYPE", pd.Series("false", index=o.index)).str.lower().ne("true")]
        o = o[[c for c in OFFER_COLS if c in o.columns]]
        i = iss
        if "IS_PRIMARYISSUER_FLAG" in i.columns:
            i = i[i.IS_PRIMARYISSUER_FLAG.str.upper().eq("YES")]
        i = i[[c for c in ISSUER_COLS if c in i.columns]].drop_duplicates("ACCESSIONNUMBER")
        sb = sub[[c for c in SUB_COLS if c in sub.columns]].drop_duplicates("ACCESSIONNUMBER")
        m = o.merge(sb, on="ACCESSIONNUMBER", how="left").merge(i, on="ACCESSIONNUMBER", how="left")
        m.insert(0, "quarter", f"{y}q{q}")
        frames.append(m)
        log.append(f"{y}q{q}\t{len(m)}\toffering:{len(off)}\tcols:{','.join(off.columns)}")
        print(log[-1][:160], flush=True)
        time.sleep(0.5)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df.to_csv(os.path.join(out, "formd_biopharma.csv.gz"), index=False)
    with open(os.path.join(out, "formd_fetch_log.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + f"\nTOTAL\t{len(df)}\n")
    print("rows kept:", len(df))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2009)
