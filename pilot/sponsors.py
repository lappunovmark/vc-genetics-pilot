"""Pilot sponsor typing.

Top-20 pharma = the 20 largest companies by 2023 pharmaceutical revenue (fixed list). Acquired companies count
as the parent only for trials that started in or after the acquisition (completion) year; before that they are
typed like any other industry sponsor. Year 0 = long-standing subsidiary or legacy name.
PILOT ASSUMPTIONS: the top-20 list itself is fixed over time; names matched by regular expression.
"""
import re

# (regex, parent, first year counted as parent[, first year no longer counted (spin-off)])
ENTRIES = [
    (r'pfizer|pharmacia|upjohn', 'Pfizer', 0), (r'wyeth', 'Pfizer', 2009), (r'hospira', 'Pfizer', 2015),
    (r'medivation', 'Pfizer', 2016), (r'anacor', 'Pfizer', 2016), (r'array biopharma', 'Pfizer', 2019),
    (r'arena pharm', 'Pfizer', 2022), (r'global blood', 'Pfizer', 2022), (r'biohaven', 'Pfizer', 2022),
    (r'seagen|seattle genetics', 'Pfizer', 2023),
    (r'johnson\s*&\s*johnson|janssen|ortho[- ]mcneil|mcneil|tibotec', 'Johnson & Johnson', 0),
    (r'centocor', 'Johnson & Johnson', 1999), (r'crucell', 'Johnson & Johnson', 2011), (r'alios', 'Johnson & Johnson', 2014),
    (r'actelion', 'Johnson & Johnson', 2017), (r'momenta', 'Johnson & Johnson', 2020),
    (r'hoffmann-la roche|\broche\b', 'Roche', 0), (r'genentech', 'Roche', 1990), (r'chugai', 'Roche', 2002),
    (r'intermune', 'Roche', 2014), (r'spark therapeutics', 'Roche', 2019),
    (r'merck sharp|\bmsd\b|merck & co', 'Merck & Co', 0), (r'schering-plough', 'Merck & Co', 2009),
    (r'organon', 'Merck & Co', 2009, 2021), (r'idenix', 'Merck & Co', 2014), (r'cubist', 'Merck & Co', 2015),
    (r'acceleron', 'Merck & Co', 2021), (r'prometheus bio', 'Merck & Co', 2023),
    (r'abbvie', 'AbbVie', 2013), (r'\babbott\b', 'AbbVie', 0, 2013), (r'pharmacyclics', 'AbbVie', 2015),
    (r'stemcentrx', 'AbbVie', 2016), (r'allergan', 'AbbVie', 2020), (r'cerevel', 'AbbVie', 2024), (r'immunogen', 'AbbVie', 2024),
    (r'novartis', 'Novartis', 0), (r'sandoz', 'Novartis', 0, 2024), (r'chiron', 'Novartis', 2006), (r'alcon', 'Novartis', 2011, 2019),
    (r'avexis', 'Novartis', 2018), (r'endocyte', 'Novartis', 2018), (r'advanced accelerator', 'Novartis', 2018),
    (r'the medicines company', 'Novartis', 2020),
    (r'bristol[- ]?myers', 'Bristol Myers Squibb', 0), (r'celgene|receptos|juno therapeutics', 'Bristol Myers Squibb', 2019),
    (r'myokardia', 'Bristol Myers Squibb', 2020), (r'turning point', 'Bristol Myers Squibb', 2022),
    (r'karuna|mirati|rayzebio', 'Bristol Myers Squibb', 2024),
    (r'astrazeneca|\bzeneca\b|\bastra\b', 'AstraZeneca', 0), (r'medimmune', 'AstraZeneca', 2007), (r'ardea', 'AstraZeneca', 2012),
    (r'pearl therapeutics', 'AstraZeneca', 2013), (r'acerta', 'AstraZeneca', 2016), (r'alexion', 'AstraZeneca', 2021),
    (r'sanofi|aventis', 'Sanofi', 0), (r'genzyme', 'Sanofi', 2011), (r'bioverativ|ablynx', 'Sanofi', 2018),
    (r'principia', 'Sanofi', 2020), (r'kadmon|translate bio', 'Sanofi', 2021), (r'provention', 'Sanofi', 2023),
    (r'glaxo|\bgsk\b|smithkline', 'GSK', 0), (r'viiv|stiefel', 'GSK', 2009), (r'human genome sciences', 'GSK', 2012),
    (r'tesaro', 'GSK', 2019), (r'sierra oncology|affinivax', 'GSK', 2022), (r'bellus', 'GSK', 2023),
    (r'eli lilly|\blilly\b', 'Eli Lilly', 0), (r'imclone', 'Eli Lilly', 2008), (r'loxo', 'Eli Lilly', 2019),
    (r'dermira', 'Eli Lilly', 2020), (r'prevail therapeutics', 'Eli Lilly', 2021), (r'akouos', 'Eli Lilly', 2022),
    (r'\bamgen\b', 'Amgen', 0), (r'immunex', 'Amgen', 2002), (r'onyx pharm', 'Amgen', 2013), (r'five prime', 'Amgen', 2021),
    (r'chemocentryx', 'Amgen', 2022), (r'horizon therap|horizon pharma', 'Amgen', 2023),
    (r'novo nordisk', 'Novo Nordisk', 0),
    (r'\bbayer\b', 'Bayer', 0),
    (r'takeda', 'Takeda', 0), (r'millennium pharm', 'Takeda', 2008), (r'ariad', 'Takeda', 2017), (r'tigenix', 'Takeda', 2018),
    (r'shire|baxalta', 'Takeda', 2019),
    (r'boehringer', 'Boehringer Ingelheim', 0),
    (r'gilead', 'Gilead Sciences', 0), (r'pharmasset', 'Gilead Sciences', 2012), (r'kite pharma', 'Gilead Sciences', 2017),
    (r'immunomedics|forty seven', 'Gilead Sciences', 2020),
    (r'merck kgaa|emd serono', 'Merck KGaA', 0), (r'serono', 'Merck KGaA', 2007),
    (r'astellas', 'Astellas', 0), (r'ocata', 'Astellas', 2016), (r'audentes', 'Astellas', 2020), (r'iveric', 'Astellas', 2023),
    (r'daiichi', 'Daiichi Sankyo', 0), (r'plexxikon', 'Daiichi Sankyo', 2011), (r'ambit bio', 'Daiichi Sankyo', 2014),
]
_RX = [(re.compile(e[0], re.I), e[1], e[2], e[3] if len(e) > 3 else 9999) for e in ENTRIES]


def top20_parent(name, year=None):
    """Top-20 parent of a sponsor name, or None. With `year` (trial start year), an acquired company maps to the
    parent only from its acquisition year onwards, and a spun-off unit (Organon 2021, Sandoz 2024, Alcon 2019, Abbott's
    pharma business split off as AbbVie in 2013) stops counting from the spin-off year."""
    if not isinstance(name, str):
        return None
    for rx, parent, since, until in _RX:
        if rx.search(name):
            if year is not None and year == year and not (since <= year < until):
                continue
            return parent
    return None


def sponsor_type(name, cls, year=None):
    """cls = ClinicalTrials.gov LeadSponsorClass (INDUSTRY, NIH, FED, OTHER_GOV, OTHER, NETWORK, INDIV, UNKNOWN)."""
    if cls == 'INDUSTRY':
        return 'Top-20 pharma' if top20_parent(name, year) else 'Other industry'
    if cls in ('NIH', 'FED', 'OTHER_GOV'):
        return 'Government'
    if cls == 'OTHER':
        return 'Academic/other'
    return 'Other'
