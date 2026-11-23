"""Primary sponsor of every ClinicalTrials.gov record in the WHO ICTRP copy of April 2015.

Usage: python -I pilot/extract_ictrp_2015.py data-20150402.zip OUT.csv.gz
(the zip is the file of van Valkenhoef, Zenodo, doi:10.5281/zenodo.46392, CC0: one XML file per record of sixteen
registries, retrieved in the first week of April 2015; plan: docs/plan_sponsor_2015.md)

Only members named NCT<digits>.xml are read. The fields are taken with regular expressions from the text of the
record (the file is outside data, so it is not handed to an XML parser), and character entities are unescaped.
Writes nct_id, sponsor_2015, registered, last_updated.
"""

import csv
import gzip
import html
import re
import sys
import zipfile

MEMBER = re.compile(r"(?:^|/)(NCT\d{8})\.xml$")
FIELDS = {
    "sponsor_2015": re.compile(r"<Primary_sponsor>(.*?)</Primary_sponsor>", re.S),
    "registered": re.compile(r"<Date_registration2>(.*?)</Date_registration2>", re.S),
    "last_updated": re.compile(r"<last_updated>(.*?)</last_updated>", re.S),
    "trial_id": re.compile(r"<TrialID>(.*?)</TrialID>", re.S),
}


def field(rx, text):
    m = rx.search(text)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else ""


def main(src, dst):
    n = bad = empty = 0
    with zipfile.ZipFile(src) as z, gzip.open(dst, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nct_id", "sponsor_2015", "registered", "last_updated"])
        for info in z.infolist():
            m = MEMBER.search(info.filename)
            if not m:
                continue
            text = z.read(info).decode("utf-8", "replace")
            row = {k: field(rx, text) for k, rx in FIELDS.items()}
            if row["trial_id"].upper() != m.group(1):
                bad += 1  # the record inside is not the one the file is named after
                continue
            empty += row["sponsor_2015"] == ""
            w.writerow([m.group(1), row["sponsor_2015"], row["registered"], row["last_updated"]])
            n += 1
    print(
        f"ClinicalTrials.gov records written: {n}; without a primary sponsor: {empty}; file name and TrialID differ: {bad}"
    )


if __name__ == "__main__":
    main(*sys.argv[1:3])
