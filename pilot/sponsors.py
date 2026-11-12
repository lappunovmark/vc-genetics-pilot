"""Pilot sponsor typing.

Top-20 pharma = a fixed list of 20 large research-based pharmaceutical companies: the 17 companies with the largest
prescription-drug sales in 2023 (Pharm Exec 50, June 2024, Evaluate data: Johnson & Johnson, AbbVie, Novartis,
Merck & Co, Roche, Pfizer, Bristol Myers Squibb, AstraZeneca, Sanofi, GSK, Novo Nordisk, Eli Lilly, Takeda, Amgen,
Gilead, Boehringer Ingelheim, Bayer) and three further originator companies with broad pipelines, Astellas (21st),
Merck KGaA (24th) and Daiichi Sankyo (25th). It is NOT the top 20 of that ranking: Viatris, CSL and Teva (18th to
20th; generics and plasma products), Vertex (22nd) and Sandoz (23rd; part of Novartis until 2023) are not in the
list. robust26.py repeats the selection model with the group cut to the first 17. Acquired companies count as the
parent only for trials that started in or after the acquisition (completion) year; before that they are typed like
any other industry sponsor. A spun-off unit stops counting from the year of the spin-off. Year 0 = long-standing
subsidiary or legacy name.

The registry shows a sponsor under its current name, and after an acquisition that name often carries the parent
("Karuna Therapeutics, Inc., a Bristol Myers Squibb company", "Wyeth is now a wholly owned subsidiary of Pfizer").
The sponsor's own name comes first in every such form, so the entry that matches EARLIEST in the name decides, with
its own year window; a parent named later in the string is ignored. (Until 12 Nov 2026 the first entry of the list
that matched decided, so the parent's name typed all trials of a renamed subsidiary as top-20, including those it
started as an independent company.) A renamed subsidiary needs an entry of its own with its acquisition year:
factcheck/sponsor_names_audit.py lists the names where the top-20 match is not the leading name, for review.
Every pattern must start at a word boundary ("shire" must not match "Warwickshire", "alios" not "Healios").

Limit that names cannot fix: when the registry record of an old trial was moved to the acquirer's name outright
("Pfizer" for a trial that Medivation started), the trial counts as the acquirer's.
PILOT ASSUMPTIONS: the top-20 list itself is fixed over time; names matched by regular expression; the list of
acquired companies covers the ones met in the data, not every deal (factcheck/sponsor_missing_acquisitions.py
counts the trials that further deals would move).
"""

import re

# (regex, parent, first year counted as parent[, first year no longer counted (spin-off)])
ENTRIES = [
    (r"pfizer|pharmacia|upjohn", "Pfizer", 0),
    (r"wyeth", "Pfizer", 2009),
    (r"hospira", "Pfizer", 2015),
    (r"medivation", "Pfizer", 2016),
    (r"anacor", "Pfizer", 2016),
    (r"array biopharma", "Pfizer", 2019),
    (r"metsera", "Pfizer", 2025),
    (r"arena pharm", "Pfizer", 2022),
    (r"global blood", "Pfizer", 2022),
    (r"biohaven", "Pfizer", 2022),
    (r"seagen|seattle genetics", "Pfizer", 2023),
    (r"johnson\s*&\s*johnson|janssen|ortho[- ]mcneil|mcneil|tibotec", "Johnson & Johnson", 0),
    (r"centocor", "Johnson & Johnson", 1999),
    (r"crucell", "Johnson & Johnson", 2011),
    (r"alios\b", "Johnson & Johnson", 2014),
    (r"actelion", "Johnson & Johnson", 2017),
    (r"momenta", "Johnson & Johnson", 2020),
    (r"hoffmann-la roche|\broche\b", "Roche", 0),
    (r"genentech", "Roche", 1990),
    (r"chugai", "Roche", 2002),
    (r"intermune", "Roche", 2014),
    (r"spark therapeutics", "Roche", 2019),
    (r"merck sharp|\bmsd\b|merck & co", "Merck & Co", 0),
    (r"schering-plough", "Merck & Co", 2009),
    (r"organon", "Merck & Co", 2009, 2021),
    (r"idenix", "Merck & Co", 2014),
    (r"cubist", "Merck & Co", 2015),
    (r"trius therap|optimer pharm", "Merck & Co", 2015),  # Cubist bought both in 2013
    (r"novacardia", "Merck & Co", 2007),
    (r"oncoethix", "Merck & Co", 2014),
    (r"afferent pharm", "Merck & Co", 2016),
    (r"immune design|peloton therap", "Merck & Co", 2019),
    (r"arqule|velosbio|oncoimmune", "Merck & Co", 2020),
    (r"acceleron", "Merck & Co", 2021),
    (r"imago bio", "Merck & Co", 2023),
    (r"harpoon therap", "Merck & Co", 2024),
    (r"verona pharma", "Merck & Co", 2025),
    (r"cidara|terns\b", "Merck & Co", 2026),
    (r"prometheus bio", "Merck & Co", 2023),
    (r"abbvie", "AbbVie", 0),  # the registry renamed Abbott's pre-2013 pharma trials to AbbVie
    (r"\babbott\b", "AbbVie", 0, 2013),
    (r"pharmacyclics", "AbbVie", 2015),
    (r"stemcentrx", "AbbVie", 2016),
    (r"allergan", "AbbVie", 2020),
    (r"cerevel", "AbbVie", 2024),
    (r"immunogen\b", "AbbVie", 2024),
    (r"novartis", "Novartis", 0),
    (r"sandoz", "Novartis", 0, 2023),  # spun off on 4 October 2023
    (r"chiron", "Novartis", 2006),
    (r"alcon\b", "Novartis", 2011, 2019),
    (r"corthera", "Novartis", 2010),
    (r"avexis", "Novartis", 2018),
    (r"endocyte", "Novartis", 2018),
    (r"advanced accelerator", "Novartis", 2018),
    (r"the medicines company", "Novartis", 2020),
    (r"tourmaline bio", "Novartis", 2025),
    (r"bristol[- ]?myers", "Bristol Myers Squibb", 0),
    (r"adnexus", "Bristol Myers Squibb", 2007),
    (r"celgene|receptos|juno therapeutics", "Bristol Myers Squibb", 2019),
    (r"myokardia", "Bristol Myers Squibb", 2020),
    (r"turning point therap", "Bristol Myers Squibb", 2022),
    (r"karuna\b|mirati\b|rayzebio", "Bristol Myers Squibb", 2024),
    (r"astrazeneca|\bzeneca\b|\bastra\b", "AstraZeneca", 0),
    (r"medimmune", "AstraZeneca", 2007),
    (r"ardea bio", "AstraZeneca", 2012),
    (r"pearl therapeutics", "AstraZeneca", 2013),
    (r"acerta", "AstraZeneca", 2016),
    (r"alexion", "AstraZeneca", 2021),
    (r"sanofi|aventis", "Sanofi", 0),
    (r"genzyme", "Sanofi", 2011),
    (r"bioverativ|ablynx", "Sanofi", 2018),
    (r"principia|synthorx", "Sanofi", 2020),
    (r"kadmon|translate bio", "Sanofi", 2021),
    (r"provention", "Sanofi", 2023),
    (r"glaxo|\bgsk\b|smithkline", "GSK", 0),
    (r"sirtris", "GSK", 2008),
    (r"viiv|stiefel", "GSK", 2009),
    (r"human genome sciences", "GSK", 2012),
    (r"tesaro", "GSK", 2019),
    (r"sierra oncology|affinivax", "GSK", 2022),
    (r"bellus health", "GSK", 2023),
    (r"idrx", "GSK", 2025),
    (r"rapt therap", "GSK", 2026),
    (r"eli lilly|\blilly\b", "Eli Lilly", 0),
    (r"imclone", "Eli Lilly", 2008),
    (r"loxo\b", "Eli Lilly", 2019),
    (r"dermira", "Eli Lilly", 2020),
    (r"prevail therapeutics", "Eli Lilly", 2021),
    (r"akouos", "Eli Lilly", 2022),
    (r"dice therap|point biopharma", "Eli Lilly", 2023),
    (r"morphic", "Eli Lilly", 2024),
    (r"scorpion therap", "Eli Lilly", 2025),
    (r"ajax therap|vaccine company, inc", "Eli Lilly", 2026),
    (r"\bamgen\b", "Amgen", 0),
    (r"immunex", "Amgen", 2002),
    (r"onyx pharm", "Amgen", 2013),
    (r"five prime", "Amgen", 2021),
    (r"chemocentryx", "Amgen", 2022),
    (r"horizon therap|horizon pharma", "Amgen", 2023),
    (r"novo nordisk", "Novo Nordisk", 0),
    (r"dicerna", "Novo Nordisk", 2021),
    (r"\bbayer\b", "Bayer", 0),
    (r"takeda", "Takeda", 0),
    (r"millennium pharm", "Takeda", 2008),
    (r"ariad", "Takeda", 2017),
    (r"tigenix", "Takeda", 2018),
    (r"shire\b|baxalta", "Takeda", 2019),
    (r"boehringer", "Boehringer Ingelheim", 0),
    (r"gilead", "Gilead Sciences", 0),
    (r"pharmasset", "Gilead Sciences", 2012),
    (r"kite pharma|kite, a gilead", "Gilead Sciences", 2017),
    (r"immunomedics|forty seven", "Gilead Sciences", 2020),
    (r"merck kgaa|merck healthcare kgaa|emd serono", "Merck KGaA", 0),
    (r"serono", "Merck KGaA", 2007),
    (r"springworks", "Merck KGaA", 2025),
    (r"astellas", "Astellas", 0),
    (r"ocata", "Astellas", 2016),
    (r"audentes", "Astellas", 2020),
    (r"iveric", "Astellas", 2023),
    (r"daiichi", "Daiichi Sankyo", 0),
    (r"plexxikon", "Daiichi Sankyo", 2011),
    (r"ambit bio", "Daiichi Sankyo", 2014),
]
# the three companies of the list that are not among the 17 largest by 2023 prescription sales
TOP20_BEYOND_17 = ("Astellas", "Merck KGaA", "Daiichi Sankyo")

# Names in which the top-20 match is not the leading name, read one by one (factcheck/sponsor_names_audit.py fails on
# any other): start of the sponsor name -> why the typing is right.
REVIEWED_NONLEADING = {
    "Xian-Janssen": "Johnson & Johnson's joint venture in China, long-standing",
    "PriCara, Unit of Ortho-McNeil": "a Johnson & Johnson unit",
    "Opella Healthcare Group SAS, a Sanofi Company": "Sanofi's consumer unit; its trials here start in 2023-2024",
    "Naurex, Inc, an affiliate of Allergan": "Allergan counts as AbbVie from 2020; Naurex's trials are earlier",
    "Durata Therapeutics Inc., an affiliate of Allergan": "as Naurex",
    "Chase Pharmaceuticals Corporation, an affiliate of Allergan": "as Naurex",
    "Vitae Pharmaceuticals Inc., an Allergan affiliate": "as Naurex",
    "Rempex Pharmaceuticals (a wholly owned subsidiary of The Medicines Company)": "sold to Melinta in 2018, before "
    "Novartis bought The Medicines Company (2020); no trial from 2020 on",
}

# every pattern starts at a word boundary
_RX = [(re.compile(r"\b(?:" + e[0] + ")", re.I), e[1], e[2], e[3] if len(e) > 3 else 9999) for e in ENTRIES]


def leading_entry(name):
    """(position, parent, first year, end year) of the entry that matches earliest in the name, or None. The earliest
    match is the sponsor's own name; a parent named later in the string ("X, a subsidiary of Y") does not decide."""
    best = None
    for rx, parent, since, until in _RX:
        m = rx.search(name)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), parent, since, until)
    return best


def top20_parent(name, year=None):
    """Top-20 parent of a sponsor name, or None. With `year` (trial start year), an acquired company maps to the
    parent only from its acquisition year onwards, and a spun-off unit (Organon 2021, Sandoz 2023, Alcon 2019, Abbott's
    pharma business split off as AbbVie in 2013) stops counting from the spin-off year. Without a year (trial with
    no start date) the window is not applied."""
    if not isinstance(name, str):
        return None
    best = leading_entry(name)
    if best is None:
        return None
    _, parent, since, until = best
    if year is not None and year == year and not (since <= year < until):
        return None
    return parent


def sponsor_type(name, cls, year=None):
    """cls = ClinicalTrials.gov LeadSponsorClass (INDUSTRY, NIH, FED, OTHER_GOV, OTHER, NETWORK, INDIV, UNKNOWN)."""
    if cls == "INDUSTRY":
        return "Top-20 pharma" if top20_parent(name, year) else "Other industry"
    if cls in ("NIH", "FED", "OTHER_GOV"):
        return "Government"
    if cls == "OTHER":
        return "Academic/other"
    return "Other"
