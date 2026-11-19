"""Read the principal stockholders table of each IPO prospectus (plan: docs/plan_ipo_prospectus.md).

Usage: python pilot/ipo_holders.py IPO_DIR RESULTS_DIR
(IPO_DIR is the directory of fetch_ipo_prospectus.py; writes RESULTS_DIR/ipo_holders.csv and ipo_holders_log.csv)

A prospectus is turned into lines of text, a table row becoming one line with its cells joined by tabs. The section
headed "Principal stockholders" (or shareholders, security ownership, and the like) is cut out, and every row of
its ownership tables that has a name and at least two numbers is read:
  holder        the name, without footnote marks and without the address printed under it
  pct_before    the percentage of shares owned before the offering: the first column of the table that holds
                percentages (a dash or a star for "less than 1%" is read as 0)
  block         the part of the table the row stands in: holders (of more than 5%), insiders (directors and
                officers) or unknown where the table has no such sub-headings
  organisation  1 if the name has a word that marks an organisation (L.P., LLC, Fund, Ventures, Ltd ...)
  person        1 if the name is that of a natural person: no such word, and a title or degree, or a first name
                borne by a director or officer in some prospectus, in a name of two to five words
  read_by       how the percentage was found (column; shifted by one cell; row, where the table has no clear
                percentage column) and "+above" where the name stood on a row of its own above the numbers
Nothing is classified here; ipo_models.py does that. The log has one row per prospectus: read, plain-text filing
(not read), no section found or no table rows read, the number of rows and the number of holders of 5% or more
that are not natural persons.
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
    r"(?i)^\W*(our\s+)?((principal|major)(\s+and\s+(selling|registered))?|selling\s+and\s+principal)\s+(stock|share)holders"
    r"(\s+and\s+management)?\W*$"
    r"|^\W*(security\s+|stock\s+|share\s+|beneficial\s+)?ownership\s+of\s+[\w\s,]{0,80}$"
)
NEXT = re.compile(
    r"(?i)^\W*(description\s+of\s+(our\s+)?(capital\s+stock|share\s+capital|securities|american\s+depositary|common\s+stock"
    r"|ordinary\s+shares|shares)|certain\s+relationships|related[\s-]+party\s+transactions|certain\s+transactions"
    r"|shares\s+eligible\s+for\s+future\s+sale|underwriting|material\s+(u\.?s\.?|united\s+states)|taxation"
    r"|selling\s+(stock|share)holders)\b.{0,60}$"
)
OWNER = re.compile(r"(?i)\b(name(\s+and\s+address)?\s+of\s+)?beneficial\s+owners?\b")
NUM = re.compile(r"^\(?\$?\d[\d,]*(\.\d+)?\)?%?$")
ROW = "\x1f"  # marks a line that was a table row
TABLE = "\x1e"  # a line of its own where a table starts
INNER = "\x1d"  # a line break inside a table cell
MARK = "\x1c"  # around a superscript inside a table cell (a footnote mark)
SUP = re.compile(MARK + "[^" + MARK + INNER + "\t]{0,12}" + MARK + "?")
DASH = {"—", "–", "-", "--", "―", "‑", "−", "_", "__"}
STAR = re.compile(r"(?i)^(\*+|†|<\s*1(\.0)?|less\s+than\s+(1|one)(\.0)?(\s*percent)?)$")
FOOT = re.compile(r"^[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]]$")
NOTE = re.compile(r"(\s*[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]],?)+\s*$|\s*[†‡*]+\s*$")
PLACE = re.compile(r",\s*[A-Z]{2}\.?\s+\d{5}\b|\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b")  # a US or UK postcode
ADDRESS = re.compile(r"(?i)^\W*(c/o\b|\d|p\.?\s?o\.?\s*box|one\s|two\s|suite\b|attn|attention|address)")
STREET = re.compile(
    r"(?i)\b(avenue|ave|street|road|rd|floor|building|bldg|plaza|drive|boulevard|blvd|lane|suite|parkway|strasse|rue"
    r"|postfach|p\.?\s?o\.?\s*box)\b\.?"
)
SOFT = re.compile(r"(?i)\b(house|tower|square|centre|center|way|court|place)\b")  # only on a second line of a cell
INSIDER = re.compile(r"(?i)director|officer|executive|management|board|employee|insider")
HOLDER = re.compile(
    r"(?i)\b5(\.0)?\s*%|five\s+percent|5\s+percent|greater\s+than|more\s+than|principal|other\s+(stock|share)holders|selling"
    r"|major\s+(stock|share)holders"
)
TABLEHEAD = re.compile(
    r"(?i)beneficial|\bowners?\b|\bname\b|(stock|share)holders?\b|\bholders?\b|\bowned\b|\boffering\b|\bpercentage\b"
)
LABEL = re.compile(r"(?i)holders|owners|directors?|officers")
LABEL2 = re.compile(r"(?i)management|board|members")
FUND = re.compile(r"(?i)\b(l\.?p|l\.?l\.?c|inc|ltd|limited|funds?|capital|partners|ventures?|advisors|company|corp)\b")
GROUP = re.compile(
    r"(?i)\ball\b.*\b(as\s+a\s+group|\d+\s+(persons?|individuals?|people))|\bas\s+a?\s*group\b"
    r"|\bgroup\s*\(\s*\d+\s+(persons?|individuals?|people)|^\W*total\b|\(\s*\d+\s+(persons?|individuals?|people)\s*\)"
)
TITLE = re.compile(
    r"(?i)\b(ph\.?\s?d|m\.?d|j\.?d|m\.?b\.?a|d\.?v\.?m|pharm\.?d|d\.?phil|chief|officer|president|director|chairman"
    r"|dr|mr|mrs|ms|esq|representing)\b|,\s*(jr|sr)\b|\b(jr|sr)\.?$"
)
VEHICLE = re.compile(r"(?i)^\W*(entities|entity|funds?|affiliates|trusts?|persons|individuals)\b")
ORG = re.compile(
    r"(?i)\b(l\.?\s?p\.?|l\.?l\.?c\.?|l\.?l\.?p\.?|inc|ltd|limited|plc|corp|corporation|company|co|fund|funds|ventures?|"
    r"capital|partners|partnership|holdings?|holding|investments?|investors?|investment|management|advisors?|advisers?|"
    r"associates|trust|trustees?|foundation|university|group|gmbh|ag|s\.?a\.?|n\.?v\.?|b\.?v\.?|sarl|s\.?à\.?r\.?l\.?|pte|kg|"
    r"entities|affiliated|affiliates|bank|institute|college|pharma\w*|therapeutics|biotech\w*|sciences?|health\w*|"
    r"medical|laboratories|labs|asset|equity|global|international|opportunit\w+|master|growth|bioventures|biocapital|"
    r"lifesciences|technolog\w+|research|kk|k\.k\.|oy|ab|a/s|aps|as|spa|s\.?p\.?a\.?|llp|lllp|sicar|sicav|scsp|fcpr|fcpi|"
    r"regents|school|hospital|clinic|society|association|council|ministry|government|state|estate|family)\b"
)


class _Lines(HTMLParser):
    """HTML -> lines of text. A table row becomes one line, its cells joined by tabs (a cell that spans n columns is
    followed by n-1 empty cells, so that a column keeps its position from row to row); a line break inside a cell is
    kept as INNER, and a superscript inside a cell (a footnote mark) is put between MARK characters."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.row, self.cell, self.span = [], [], None, None, 1

    def _flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if t:
            self.lines.append(t)

    def _close_cell(self):
        if self.cell is not None:
            self.row.append("".join(self.cell))
            self.row.extend([""] * (self.span - 1))
        self.cell, self.span = None, 1

    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.row is None:
            self._flush()
            self.lines.append(TABLE)
        elif tag == "tr":
            self._flush()
            self.row, self.cell, self.span = [], None, 1
        elif tag in ("td", "th"):
            if self.row is not None:
                self._close_cell()
                self.cell = []
                span = dict(attrs).get("colspan") or "1"
                self.span = min(int(span), 30) if span.isdigit() else 1
        elif tag == "sup" and self.cell is not None:
            self.cell.append(MARK)
        elif tag in BLOCK:
            if self.row is None:
                self._flush()
            elif self.cell is not None:
                self.cell.append(INNER)

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self._close_cell()
            cells = [re.sub(r"[ \t\r\n\f\v]+", " ", c).strip() for c in self.row]
            if any(c.strip(INNER + " ") for c in cells):
                self.lines.append(ROW + "\t".join(cells))
            self.row, self.cell = None, None
        elif tag == "sup" and self.cell is not None:
            self.cell.append(MARK)
        elif tag in BLOCK:
            if self.row is None:
                self._flush()
            elif self.cell is not None:
                self.cell.append(INNER)

    def handle_data(self, data):
        if self.row is not None:
            if self.cell is None:
                self.cell = []
            self.cell.append(data.replace("\t", " "))
        else:
            self.buf.append(data)


def clean(s):
    return re.sub(r"[​‌‍﻿\xa0]", " ", s)


def flat(line):
    """A line as plain text (for headings)."""
    return re.sub(r"\s+", " ", SUP.sub(" ", line.lstrip(ROW)).replace("\t", " ").replace(INNER, " ")).strip()


def to_lines(doc):
    """(lines, kind): kind is 'html' or 'text'. The plain-text filings of the early 2000s set their tables with
    spaces and wrap names over lines; they are few and are not read."""
    if not re.search(r"(?i)<(td|div|font|p)\b", doc[:300000]):
        return [clean(html.unescape(re.sub(r"<[^>]{0,80}>", " ", x).rstrip())) for x in doc.splitlines()], "text"
    p = _Lines()
    p.feed(doc)
    p._flush()
    return [clean(x) for x in p.lines], "html"


def _end(lines, i):
    stop = min(i + 500, len(lines))
    return next((j for j in range(i + 8, stop) if len(lines[j]) < 90 and NEXT.match(flat(lines[j]))), stop)


def sections(lines):
    """Candidate sections, best first. The table of contents names the section too, so a heading counts only if
    the word 'beneficial' follows it closely; the last such heading comes first (the first of a run of headings
    that repeat within 150 lines). A prospectus whose section has
    another title is found by the heading row of the table itself ('Name of beneficial owner')."""
    out = []
    starts = [i for i, x in enumerate(lines) if x != TABLE and len(x) < 110 and HEAD.match(flat(x))]
    good = [i for i in starts if any("beneficial" in x.lower() for x in lines[i + 1 : i + 60])]
    while good:
        i = good.pop()
        while good and i - good[-1] < 150:  # the heading is repeated where the table runs over a page
            i = good.pop()
        out.append(lines[i : _end(lines, i)])
    for i, x in enumerate(lines):
        if x.startswith(ROW) and len(x) < 400 and OWNER.search(flat(x)):
            out.append(lines[max(i - 1, 0) : _end(lines, i)])
    return out


def token(c):
    """A cell of a table as (value, has a percent sign, kind): kind is 'num', 'dash', 'star', 'skip' or 'text'."""
    c = SUP.sub(" ", c).replace(INNER, " ").strip()
    c = re.sub(r"\s*%", "%", c)
    c = re.sub(r"(\s*[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]])+$", "", c).strip() if not FOOT.match(c) else c
    if c in ("", "%", "$", ")", "(", "%)") or FOOT.match(c):
        return (None, False, "skip")
    pct = c.endswith("%")
    core = c.rstrip("%").strip()
    if core in DASH or core == "":
        return (0.0, pct, "dash")
    if STAR.match(core):
        return (0.0, pct, "star")
    if NUM.match(core):
        return (float(re.sub(r"[^\d.]", "", core)), pct, "num" if "," not in core else "big")
    return (None, False, "text")


def is_address(x):
    x = re.sub(r"[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]]", " ", x)  # footnote marks
    return bool(ADDRESS.match(x) or STREET.search(x) or PLACE.search(x) or (re.search(r"\d", x) and not ORG.search(x)))


def name_of(cell):
    """The holder's name: the lines of the cell before the address, without footnote marks."""
    parts = [NOTE.sub("", x.strip()).strip() for x in SUP.sub(" ", cell).split(INNER)]
    parts = [x for x in parts if x]
    keep = []
    for x in parts:
        if keep and (is_address(x) or SOFT.search(x)):
            break
        keep.append(x)
        if len(keep) == 3:
            break
    name = re.sub(r"\s+", " ", " ".join(keep))
    name = re.sub(r"(\s*[\(\[]\s*\d{1,2}[a-z]?\s*[\)\]],?)+", " ", name)
    return re.sub(r"\s+", " ", name).strip(" .:,;*†‡")


def grid(sec):
    """Rows of the tables of a section: ('data', table number, name, {column: token}, column of the name),
    ('label', table, text, line, column) or ('head', table, text) for a row above the first data row of a table."""
    out, t, started = [], 0, False
    for line in sec[1:]:
        if line == TABLE:
            t, started = t + 1, False
            continue
        if not line.startswith(ROW):
            continue
        cells = [SUP.sub(" ", c) for c in line[1:].split("\t")]
        filled = [(i, c) for i, c in enumerate(cells) if c.replace(INNER, " ").strip()]
        if not filled:
            continue
        i0, first = filled[0]
        if not started:
            out.append(("head", t, flat(line)))
        if not re.search(r"[A-Za-z]{2}", first) or NUM.match(first.strip()):
            continue
        toks, last = {}, None
        for i, c in filled[1:]:
            v = token(c)
            if v[2] == "skip":
                if c.replace(INNER, " ").strip().startswith("%") and last is not None:  # the sign in a cell of its own
                    toks[last] = (toks[last][0], True, toks[last][2])
                continue
            toks[i], last = v, i
        if not toks:
            out.append(("label", t, first, line, i0))
        elif all(v[2] != "text" for v in toks.values()) and len(toks) >= 2:
            out.append(("data", t, first, toks, i0))
            started = True
    return out


def percent_columns(rows):
    """Columns of a table that hold percentages: no value above 100 or with a thousands comma, and a percent
    sign, a star for 'less than 1%' or a decimal fraction somewhere in the column."""
    stat = {}
    for r in rows:
        for i, (v, pct, k) in r[3].items():
            s = stat.setdefault(i, {"big": 0, "mark": 0, "n": 0})
            s["n"] += k in ("num", "big")
            s["big"] += k == "big" or (v is not None and v > 100)
            s["mark"] += pct or k == "star" or (k == "num" and v != int(v))
    return sorted(i for i, s in stat.items() if not s["big"] and s["mark"])


def read_rows(sec):
    """Holders of a section: (name, percent before the offering, block, is an organisation, how the percent was
    found). The percentage before the offering is the first percentage column of the table."""
    g = grid(sec)
    # a table is read if the rows above its first data row name owners or holders; a table without any heading
    # row is read if the table before it was (a table that runs over a page). This keeps out the financial
    # tables of a prospectus whose next section has a title the reader does not know.
    heads, ok, before = {}, {}, False
    for r in g:
        if r[0] == "head":
            heads[r[1]] = heads.get(r[1], "") + " " + r[2]
    for t in sorted({r[1] for r in g if r[0] == "data"}):
        text = heads.get(t, "")
        first = next(r for r in g if r[0] == "data" and r[1] == t)
        text = text.replace(flat(ROW + first[2]), "", 1)
        bare = not re.search(r"[A-Za-z]{3}", LABEL.sub("", text))
        ok[t] = before = bool(TABLEHEAD.search(text)) or (bare and before)
    g = [r for r in g if r[0] != "head" and ok.get(r[1], r[0] == "label")]
    data = [r for r in g if r[0] == "data"]
    by_table = {}
    for r in data:
        by_table.setdefault(r[1], []).append(r)
    whole = percent_columns(data)
    cols = {t: (percent_columns(rs) if len(rs) >= 3 else []) or whole for t, rs in by_table.items()}
    rows, block, seen, pending = [], "unknown", set(), None
    for r in g:
        if r[0] == "label":
            label = re.sub(r"\s+", " ", r[2].replace(INNER, " ")).strip(" :")
            short = len(label) < 110
            sub = LABEL.search(label) or (LABEL2.search(label) and not FUND.search(label))
            if short and sub and not re.match(r"(?i)\W*(c/o|attn)\b", label) and not label.endswith("."):
                insider, holder = bool(INSIDER.search(label)), bool(HOLDER.search(label))
                block = "holders" if holder and not insider else "insiders" if insider and not holder else block
                pending = None
            elif is_address(label):
                pass  # a line of an address, under the name it belongs to or under a row already read
            elif r[2].rstrip().endswith((":", ".")) or len(label) > 110:
                pending = None
            elif pending and r[4] > pending[1]:
                pass  # an indented line under the name: the address
            else:
                pending = (r[2], r[4])
            continue
        # early filings put the name on a row of its own, the address under it and the numbers on its last line
        own = name_of(r[2])
        joined = ""
        if pending and (r[4] > pending[1] or is_address(own)):
            name, joined = name_of(pending[0]), "+above"
        else:
            name = own
        pending, toks = None, r[3]
        if GROUP.search(name) or len(name) > 160 or len(name) < 3:
            continue
        pc, how = cols.get(r[1], []), "column"
        cand = next((toks[c] for c in pc[:1] if c in toks), None)
        if cand is None and pc:  # a percent sign or a bracket can shift a number by one cell
            cand, how = (
                next((toks[c] for c in (pc[0] + 1, pc[0] - 1) if c in toks and toks[c][2] != "big"), None),
                "shifted",
            )
        if cand is None:
            order = [toks[i] for i in sorted(toks)]
            marked = [x for x in order[1:] if x[1] or x[2] == "star" or (x[2] == "num" and x[0] != int(x[0]))]
            cand, how = (marked[0] if marked else None), "row"
            if cand is None and all(x[2] == "dash" for x in order):
                cand = order[0]
        if cand is None or cand[0] is None or cand[0] > 100:
            continue
        key = re.sub(r"\W+", "", name.lower())
        if key in seen:
            continue
        seen.add(key)
        person = bool(TITLE.search(name)) and not re.search(r"(?i)represented\s+by", name) and not VEHICLE.match(name)
        rows.append((name, cand[0], block, bool(ORG.search(name)) and not person, how + joined))
    return rows


def best(lines):
    """The section with a readable table, and its rows."""
    secs = sections(lines)
    for sec in secs:
        rows = read_rows(sec)
        if len(rows) >= 3 and any(p > 0 for _, p, *_ in rows):
            return sec, rows
    return (secs[0] if secs else None), []


def first_word(name):
    """The first word of a name that is not a title or an initial."""
    w = [x.strip(".,").lower() for x in re.sub(r"(?i)^(dr|mr|mrs|ms|prof|sir)\.?\s+", "", name).split()]
    return next((x for x in w if len(x) > 2 or (len(x) == 2 and "." not in x and x.isalpha())), "")


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
        if kind == "text":
            log.append((r.cik, r.accession, r.name, "plain-text filing, not read", 0, 0))
            continue
        sec, rows = best(lines)
        if sec is None:
            log.append((r.cik, r.accession, r.name, "no principal stockholders section", 0, 0))
            continue
        log.append((r.cik, r.accession, r.name, "read" if rows else "no table rows read", len(rows), 0))
        out.extend([r.cik, r.accession, r.date, n, p, b, int(o), h] for n, p, b, o, h in rows)
    cols = ["cik", "accession", "date", "holder", "pct_before", "block", "organisation", "read_by"]
    d = pd.DataFrame(out, columns=cols)
    # a natural person: a title or degree in the name, or a first name borne by a director or officer of any
    # prospectus, in a name of two to five words without a word that marks an organisation
    given = {first_word(n) for n in d.holder[(d.block == "insiders") & (d.organisation == 0)]}
    given = {g for g in given if len(g) > 2 and g.isalpha()}
    words = d.holder.str.split().str.len()
    named = d.holder.map(first_word).isin(given) & words.between(2, 5) & ~d.holder.str.contains(r"\d")
    titled = d.holder.map(lambda n: bool(TITLE.search(n))) & ~d.holder.str.contains(r"(?i)represented\s+by")
    vehicle = d.holder.map(lambda n: bool(VEHICLE.match(n)))
    d["person"] = ((d.organisation == 0) & (named | titled) & ~vehicle).astype(int)
    d.to_csv(os.path.join(res, "ipo_holders.csv"), index=False)
    lg = pd.DataFrame(log, columns=["cik", "accession", "name", "status", "rows", "holders_5pct"])
    n5 = d[(d.person == 0) & (d.pct_before >= 5)].groupby("accession").size()
    lg["holders_5pct"] = lg.accession.map(n5).fillna(0).astype(int)
    lg.to_csv(os.path.join(res, "ipo_holders_log.csv"), index=False)
    print(lg.status.value_counts().to_string())
    print(
        f"prospectuses with a holder of 5% or more that is not a natural person: {int((lg.holders_5pct > 0).sum())} of {len(lg)}"
    )


if __name__ == "__main__":
    main(*sys.argv[1:3])
