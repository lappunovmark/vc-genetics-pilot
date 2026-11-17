"""People named in Form D filings: person keys, venture-fund managers and the board marker of each filing.

Shared by formd_directors.py and vc_stops.py; see formd_directors.py for the definitions.
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owners_link

ENTITY = re.compile(
    r"\b(llc|l\.?l\.?c|lp|l\.?p|ltd|limited|inc|corp|gp|fund|funds|partners|capital|management|ventures?|holdings?|"
    r"group|trust|advisors?|company|co|gmbh|sarl|associates|services|n/?a|none)\b",
    re.I,
)
SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|md|m d|phd|ph d|esq|mba|cfa)\b")


def key(first, last):
    """'kevin|starr' for a natural person, None for an entity or an unusable name."""
    if not isinstance(first, str) or not isinstance(last, str) or ENTITY.search(first) or ENTITY.search(last):
        return None
    f = re.sub(r"[^a-z ]", " ", first.lower()).split()
    la = SUFFIX.sub(" ", re.sub(r"[^a-z ]", " ", last.lower()))
    la = "".join(la.split())
    if not f or len(f[0]) < 2 or len(la) < 2:
        return None
    return f"{f[0]}|{la}"


def roles(d):
    r = d[["RELATIONSHIP_1", "RELATIONSHIP_2", "RELATIONSHIP_3"]].fillna("")
    return r.eq("Director").any(axis=1), r.eq("Executive Officer").any(axis=1)


def people(fd):
    """Related persons of biopharma issuers with the marker columns, and the related persons of venture funds."""
    pv = pd.read_csv(f"{fd}/formd_people_vc_funds.csv.gz", dtype=str)
    pv["key"] = [key(a, b) for a, b in zip(pv.FIRSTNAME, pv.LASTNAME)]
    managers = set(pv[pv.key.notna()].key)
    pb = pd.read_csv(f"{fd}/formd_people_biopharma.csv.gz", dtype=str)
    pb["key"] = [key(a, b) for a, b in zip(pb.FIRSTNAME, pb.LASTNAME)]
    pb["is_dir"], pb["is_exec"] = roles(pb)
    pb["match"] = pb.key.isin(managers)
    pb["vc_director"] = pb.is_dir & ~pb.is_exec & pb.match
    rules = owners_link.owner_classes()
    addr = (pb.STREET1.fillna("") + " " + pb.STREET2.fillna("")).str.lower()
    co = addr.str.extract(r"c/o\s+(.+)$", expand=False)
    uniq = {a: owners_link.classify(a, rules) for a in co.dropna().unique()}
    pb["vc_address"] = co.map(uniq).isin(["venture capital", "life-science crossover"])
    pb["year"] = pd.to_datetime(pb.FILING_DATE, errors="coerce").dt.year
    pb["CIK"] = pb.CIK.str.lstrip("0")
    return pb, pv


def filings(fd, pb=None):
    """One row per biopharma filing: CIK, issuer name, year and the three markers."""
    if pb is None:
        pb, _ = people(fd)
    f = pb.groupby("ACCESSIONNUMBER").agg(
        CIK=("CIK", "first"),
        ENTITYNAME=("ENTITYNAME", "first"),
        year=("year", "first"),
        vc_director=("vc_director", "any"),
        vc_address=("vc_address", "any"),
    )
    f["vc_board"] = f.vc_director | f.vc_address
    return f.reset_index()
