"""Read the principal stockholders table of each IPO prospectus (plan: docs/plan_ipo_prospectus.md).

Usage: python pilot/ipo_holders.py IPO_DIR RESULTS_DIR
(IPO_DIR is the directory of fetch_ipo_prospectus.py; writes RESULTS_DIR/ipo_holders.csv and ipo_holders_log.csv)

A prospectus is turned into lines of text, a table row becoming one line with its cells joined by tabs. The section
headed "Principal stockholders" (or shareholders, with or without "and selling") is cut out, and every row of its
table that has a name, a number of shares and a percentage is read: the holder, the percentage of shares owned
before the offering, the part of the table it stands in (holders of more than 5%, or directors and officers) and
whether the name is that of an organisation or of a natural person. Nothing is classified here; ipo_models.py does
that. A prospectus without a readable table is named in the log with the reason.
"""

import gzip
import html
import os
import re
import sys
from html.parser import HTMLParser

import pandas as pd

BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table", "center", "hr", "page", "caption"}
HEAD = re.compile(
    r"(?i)^\W*(principal(\s+and\s+selling)?|selling\s+and\s+principal)\s+(stock|share)holders\W*$"
    r"|^\W*security\s+ownership\s+of\s+certain\s+beneficial\s+owners(\s+and\s+management)?\W*$"
    r"|^\W*(beneficial\s+)?ownership\s+of\s+(our\s+)?(common\s+stock|securities|ordinary\s+shares)\W*$"
)
NEXT = re.compile(
    r"(?i)^\W*(description\s+of\s+(our\s+)?(capital\s+stock|share\s+capital|securities|american\s+depositary|common\s+stock)"
    r"|certain\s+relationships|related[\s-]+party\s+transactions|certain\s+transactions|shares\s+eligible\s+for\s+future\s+sale"
    r"|underwriting|material\s+(u\.?s\.?|united\s+states)|taxation|selling\s+(stock|share)holders)\b.{0,60}$"
)
NUM = re.compile(r"^\(?\$?\d[\d,]*(\.\d+)?\)?%?$")
ROW = "\x1f"  # marks a line that was a table row
SUBHEAD = re.compile(
    r"(?i)^\W*(5\s*%|(five|greater|more\s+than|principal|other|selling|directors?|named|executive|officers?"
    r"|non-employee|management|members|supervisory|board)\b)"
)
DASH = {"—", "–", "-", "--", "―", "‑", "*", "**", "†"}
NOTE = re.compile(r"(\s*[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]])+\s*$|\s*[†‡*]+\s*$")
INSIDER = re.compile(r"(?i)director|officer|executive|management|board|employee|insider")
HOLDER = re.compile(
    r"(?i)\b5\s*%|five\s+percent|greater\s+than|more\s+than|principal|other\s+(stock|share)holders|selling"
)
GROUP = re.compile(r"(?i)\ball\b.*\b(as\s+a\s+group|\d+\s+persons?)")
ORG = re.compile(
    r"(?i)\b(l\.?\s?p\.?|l\.?l\.?c\.?|l\.?l\.?p\.?|inc|ltd|limited|plc|corp|corporation|company|co|fund|funds|ventures?|"
    r"capital|partners|partnership|holdings?|holding|investments?|investors?|investment|management|advisors?|advisers?|"
    r"associates|trust|trustees?|foundation|university|group|gmbh|ag|s\.?a\.?|n\.?v\.?|b\.?v\.?|sarl|s\.?à\.?r\.?l\.?|pte|kg|"
    r"entities|affiliated|affiliates|bank|institute|college|pharma\w*|therapeutics|biotech\w*|sciences?|health\w*|"
    r"medical|laboratories|labs|asset|equity|global|international|opportunit\w+|master|growth|bioventures|biocapital|"
    r"lifesciences|technolog\w+|research|kk|k\.k\.|oy|ab|a/s|aps|as|spa|s\.p\.a\.|llp|lllp|sicar|sicav|scsp|fcpr|fcpi|"
    r"regents|school|hospital|clinic|society|association|council|ministry|government|state|estate|family)\b"
)


class _Lines(HTMLParser):
    """HTML -> lines of text; a table row becomes one line, cells joined by tabs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.row, self.cell = [], [], None, None

    def _flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if t:
            self.lines.append(t)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._flush()
            self.row, self.cell = [], None
        elif tag in ("td", "th"):
            if self.row is not None:
                if self.cell is not None:
                    self.row.append(self.cell)
                self.cell = []
        elif tag in BLOCK:
            if self.row is None:
                self._flush()
            elif self.cell is not None:
                self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            if self.cell is not None:
                self.row.append(self.cell)
            cells = [re.sub(r"\s+", " ", "".join(c)).strip() for c in self.row]
            if any(cells):
                self.lines.append(ROW + "\t".join(cells))
            self.row, self.cell = None, None
        elif tag in BLOCK and self.row is None:
            self._flush()

    def handle_data(self, data):
        if self.row is not None:
            if self.cell is None:
                self.cell = []
            self.cell.append(data)
        else:
            self.buf.append(data)


def clean(s):
    return re.sub(r"[​‌‍﻿\xa0]", " ", s)


def to_lines(doc):
    """(lines, kind): kind is 'html' or 'text' (the plain-text filings of the early 2000s)."""
    if not re.search(r"(?i)<(td|div|font|p)\b", doc[:300000]):
        return [clean(html.unescape(x.rstrip())) for x in doc.splitlines()], "text"
    p = _Lines()
    p.feed(doc)
    p._flush()
    return [clean(x) for x in p.lines], "html"


def section(lines):
    """Lines of the principal stockholders section, or None. The table of contents names the section too, so the
    heading that counts is the last one followed by the words 'beneficial' and a table."""
    starts = [i for i, x in enumerate(lines) if len(x) < 90 and HEAD.match(x.lstrip(ROW).replace("\t", " ").strip())]
    for i in reversed(starts):
        body = lines[i + 1 : i + 60]
        if any("beneficial" in x.lower() for x in body):
            end = next((j for j in range(i + 8, min(i + 500, len(lines))) if NEXT.match(lines[j].lstrip(ROW).replace("\t", " ").strip()) and len(lines[j]) < 90), min(i + 500, len(lines)))  # fmt: skip
            return lines[i:end]
    return None


def cells_of(line, kind):
    if kind == "html":
        return [c.strip() for c in line.lstrip(ROW).split("\t")]
    line = re.sub(r"\.{3,}", "  ", line)  # dot leaders of the plain-text tables
    return [c.strip() for c in re.split(r"\s{2,}", line.strip())]


def tokens(cells):
    """Numeric tokens of a row after its name: (value or None for a dash or star, has a percent sign)."""
    out = []
    for i, c in enumerate(cells):
        c = c.strip()
        if c in ("%", "", "$") or re.fullmatch(r"[\(\[]\d{1,2}[a-z]?[\)\]]", c):
            continue
        if c in DASH:
            out.append((None, False, c))
            continue
        if NUM.match(c):
            pct = c.endswith("%") or (i + 1 < len(cells) and cells[i + 1].strip().startswith("%"))
            out.append((float(re.sub(r"[^\d.]", "", c)), pct, c))
        else:
            return None  # text after the name: not a data row
    return out


def read_rows(sec, kind):
    """Holders of a section: (name, percent before the offering, block, is an organisation)."""
    rows, block, pending = [], "unknown", ""
    for line in sec[1:]:
        cells = [c for c in cells_of(line, kind)]
        cells = cells if kind == "text" else [c for c in cells if c.strip() != ""]
        if not cells:
            continue
        name = cells[0]
        if not re.search(r"[A-Za-z]{2}", name) or NUM.match(name):
            continue
        tk = tokens(cells[1:])
        if tk is None:
            pending = ""
            continue
        if not tk:  # a row without numbers: a sub-heading of the table, or the first line of a wrapped name
            label = name.strip(" :")
            in_table = (
                line.startswith(ROW) if kind == "html" else (len(line.strip()) < 70 and not line.rstrip().endswith("."))
            )
            if in_table and len(label) < 110 and SUBHEAD.match(label) and len(cells) == 1:
                if HOLDER.search(label) and not re.match(r"(?i)\W*(directors?|named|executive|officers?)", label):
                    block = "holders"
                elif INSIDER.search(label):
                    block = "insiders"
            pending = name if kind == "text" and len(name) < 60 and not SUBHEAD.match(label) else ""
            continue
        if len(tk) < 2:
            pending = ""
            continue
        full = (pending + " " + name).strip() if pending else name
        pending = ""
        full = NOTE.sub("", full.strip(" .:")).strip(" .:")
        if GROUP.search(full) or len(full) > 160:
            continue
        shares = tk[0][0]
        marked = [t for t in tk[1:] if t[1] or t[2] in DASH]
        cand = marked[0] if marked else tk[1]
        pct = cand[0]
        if cand[2] in DASH:
            pct = 0.0
        if pct is None or pct > 100 or (shares is not None and shares < pct and not cand[1]):
            continue
        rows.append((full, pct, block, bool(ORG.search(full))))
    return rows


def main(ipo_dir, res):
    idx = pd.read_csv(os.path.join(ipo_dir, "ipo_prospectus_index.csv"), dtype=str)
    out, log = [], []
    for r in idx.itertuples():
        path = os.path.join(ipo_dir, "docs", f"{r.cik}_{r.accession}.htm.gz")
        if not os.path.exists(path):
            log.append((r.cik, r.accession, r.name, "not downloaded", 0, 0))
            continue
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            lines, kind = to_lines(fh.read())
        sec = section(lines)
        if sec is None:
            log.append((r.cik, r.accession, r.name, "no principal stockholders section", 0, 0))
            continue
        rows = read_rows(sec, kind)
        orgs = [x for x in rows if x[3] and x[1] >= 4.95]
        log.append((r.cik, r.accession, r.name, "read" if rows else "no table rows read", len(rows), len(orgs)))
        out.extend((r.cik, r.accession, r.date, n, p, b, int(o)) for n, p, b, o in rows)
    cols = ["cik", "accession", "date", "holder", "pct_before", "block", "organisation"]
    pd.DataFrame(out, columns=cols).to_csv(os.path.join(res, "ipo_holders.csv"), index=False)
    lg = pd.DataFrame(log, columns=["cik", "accession", "name", "status", "rows", "organisations_5pct"])
    lg.to_csv(os.path.join(res, "ipo_holders_log.csv"), index=False)
    print(lg.status.value_counts().to_string())
    print(
        f"prospectuses with at least one organisation holding 5% or more: {int((lg.organisations_5pct > 0).sum())} of {len(lg)}"
    )


if __name__ == "__main__":
    main(*sys.argv[1:3])
