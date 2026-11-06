"""Is a trial sponsor US-based? A transparent heuristic for the US-only Form D comparison.

ClinicalTrials.gov and Open Targets record no sponsor country. The rule, applied in this order to the lead-sponsor
name (dots removed, so "S.A." and "Co., Ltd." read as SA and Co Ltd):
  1. financing records with a location: an accepted NIH SBIR/STTR awardee (US only by construction), or an accepted
     Form D issuer whose STATEORCOUNTRY is a US state or territory -> "US"; a Form D issuer located abroad -> "non-US"
  2. a legal form or place name that points to another jurisdiction (GmbH, AG, SA, SAS, SE, BV, NV, AB, A/S, AS, ASA,
     Oy, SpA, Srl, SL, KK, Pty, Ltd, Limited, plc, ApS, Bhd, Pte, Co Ltd; Shanghai, Beijing, Tokyo, India, Israel,
     Canada, Australia and other place words listed below) -> "non-US"
  3. a US legal form (Inc, Incorporated, LLC, Corp, Corporation, LP, PBC, Company, Co) -> "US"
  4. otherwise -> "unknown" (left out of the US-only comparison)
"Ltd" is treated as non-US because US sponsors almost never use it. The classification is reported alongside the
models so that its limits are visible.
"""

import re

US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR "
    "PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR VI GU AS MP".split()
)
NON_US_FORMS = re.compile(
    r"\b(?:gmbh|ag|sa|sas|se|bv|nv|ab|a/s|as|asa|oy|oyj|spa|srl|sl|kk|pty|ltd|limited|plc|aps|bhd|sdn|pte|kgaa|mbh|"
    r"sarl|ltda|sae|sapi|cv)\b",
    re.I,
)
NON_US_PLACES = re.compile(
    r"\b(?:shanghai|beijing|suzhou|hangzhou|guangzhou|shenzhen|nanjing|chengdu|wuhan|tianjin|jiangsu|zhejiang|"
    r"sichuan|shandong|guangdong|hong kong|taiwan|taipei|korea|seoul|japan|tokyo|osaka|india|mumbai|hyderabad|"
    r"bangalore|bengaluru|ahmedabad|israel|canada|toronto|vancouver|montreal|quebec|australia|sydney|melbourne|"
    r"europe|european|deutschland|france|paris|italia|italy|españa|spain|nederland|netherlands|schweiz|suisse|"
    r"switzerland|danmark|denmark|sverige|sweden|norge|norway|suomi|finland|belgium|belgique|austria|österreich|"
    r"ireland|scotland|england|london|cambridge uk|pakistan|lahore|karachi|egypt|cairo|iran|tehran|turkey|türkiye|"
    r"istanbul|brasil|brazil|méxico|mexico|argentina|chile|colombia|cuba|russia|moscow|ukraine|poland|polska|"
    r"czech|hungary|romania|greece|portugal|singapore|malaysia|thailand|vietnam|indonesia|philippines|saudi|"
    r"emirates|dubai|south africa|nigeria|kenya|new zealand)\b",
    re.I,
)
US_FORMS = re.compile(r"\b(?:inc|incorporated|llc|corp|corporation|lp|pbc|company|co)\b", re.I)


def classify(name, norm=None, us_norms=(), foreign_norms=()):
    """'US', 'non-US' or 'unknown' for a lead-sponsor name.

    us_norms / foreign_norms: normalised sponsor names with a US / non-US location in the financing records.
    """
    if norm is not None:
        if norm in us_norms:
            return "US"
        if norm in foreign_norms:
            return "non-US"
    if not isinstance(name, str) or not name.strip():
        return "unknown"
    s = re.sub(r"[.,()]", lambda m: "" if m.group() == "." else " ", name)
    if NON_US_FORMS.search(s) or NON_US_PLACES.search(s):
        return "non-US"
    if US_FORMS.search(s):
        return "US"
    return "unknown"


def financing_locations(formd_review=None, sbir_sponsors=None):
    """(us_norms, foreign_norms) from formd_match_review.csv (accepted rows, formd_state) and sbir_sponsors.csv."""
    import pandas as pd

    us, foreign = set(), set()
    if formd_review is not None:
        f = pd.read_csv(formd_review)
        f = f[f.accepted.astype(bool)]
        st = f.formd_state.fillna("").astype(str).str.strip().str.upper()
        us |= set(f.norm[st.isin(US_STATES)])
        foreign |= set(f.norm[~st.isin(US_STATES) & st.ne("")])
    if sbir_sponsors is not None:
        s = pd.read_csv(sbir_sponsors)
        if "accepted" in s.columns:
            s = s[s.accepted.astype(bool)]
        us |= set(s.norm)
    return us, foreign - us
