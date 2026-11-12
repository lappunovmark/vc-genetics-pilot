"""Sponsor typing: the sponsor's own name decides, not a parent named later in the registry string."""

import os
import sys

import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
sys.path.insert(0, os.path.join(ROOT, "factcheck"))
import sponsor_names_audit  # noqa: E402
from sponsors import top20_parent  # noqa: E402

MERCK = ", a subsidiary of Merck & Co., Inc. (Rahway, New Jersey USA)"
CASES = [
    # renamed subsidiaries: the parent only from the acquisition year on
    ("Karuna Therapeutics, Inc., a Bristol Myers Squibb company", 2019, None),
    ("Karuna Therapeutics, Inc., a Bristol Myers Squibb company", 2024, "Bristol Myers Squibb"),
    ("Wyeth is now a wholly owned subsidiary of Pfizer", 2005, None),
    ("Wyeth is now a wholly owned subsidiary of Pfizer", 2009, "Pfizer"),
    ("Genzyme, a Sanofi Company", 2008, None),
    ("Genzyme, a Sanofi Company", 2011, "Sanofi"),
    ("Seagen, a wholly owned subsidiary of Pfizer", 2021, None),
    ("Seagen, a wholly owned subsidiary of Pfizer", 2023, "Pfizer"),
    ("Sierra Oncology LLC - a GSK company", 2014, None),
    ("Acceleron Pharma, Inc., a wholly-owned subsidiary of Merck & Co., Inc., Rahway, NJ USA", 2015, None),
    (
        "ArQule, Inc., a subsidiary of Merck Sharp & Dohme LLC, a subsidiary of Merck & Co., Inc. (Rahway, NJ USA)",
        2012,
        None,
    ),
    (
        "ArQule, Inc., a subsidiary of Merck Sharp & Dohme LLC, a subsidiary of Merck & Co., Inc. (Rahway, NJ USA)",
        2020,
        "Merck & Co",
    ),
    ("Verona Pharma, Inc." + MERCK, 2017, None),
    ("Verona Pharma, Inc." + MERCK, 2025, "Merck & Co"),
    ("Peloton Therapeutics, Inc." + MERCK, 2016, None),
    ("Trius Therapeutics LLC" + MERCK, 2010, None),
    ("Terns, Inc." + MERCK, 2020, None),
    ("Kite, A Gilead Company", 2016, None),
    ("Kite, A Gilead Company", 2018, "Gilead Sciences"),
    ("Kite Pharma, Inc.", 2018, "Gilead Sciences"),
    ("Dicerna Pharmaceuticals, Inc., a Novo Nordisk company", 2019, None),
    ("Bellus Health Inc. - a GSK company", 2020, None),
    ("Sirtris, a GSK Company", 2007, None),
    ("Sirtris, a GSK Company", 2009, "GSK"),
    ("Tourmaline Bio, Inc., a Novartis Company", 2024, None),
    ("SpringWorks Therapeutics, Inc., a healthcare company of Merck KGaA, Darmstadt, Germany", 2019, None),
    ("Naurex, Inc, an affiliate of Allergan plc", 2016, None),
    ("Baxalta now part of Shire", 2017, None),
    ("Baxalta now part of Shire", 2019, "Takeda"),
    ("Juno Therapeutics, Inc., a Bristol-Myers Squibb Company", 2023, "Bristol Myers Squibb"),
    # the parent itself, legacy names, long-standing units
    ("Merck Sharp & Dohme LLC", 1995, "Merck & Co"),
    ("Pfizer", 2001, "Pfizer"),
    ("GlaxoSmithKline", 2003, "GSK"),
    ("Hoffmann-La Roche", 2010, "Roche"),
    ("Genentech, Inc.", 2005, "Roche"),
    ("Xian-Janssen Pharmaceutical Ltd.", 2010, "Johnson & Johnson"),
    ("Merck Healthcare KGaA, Darmstadt, Germany, an affiliate of Merck KGaA, Darmstadt, Germany", 2021, "Merck KGaA"),
    ("Daiichi Sankyo Europe, GmbH, a Daiichi Sankyo Company", 2010, "Daiichi Sankyo"),
    ("Opella Healthcare Group SAS, a Sanofi Company", 2023, "Sanofi"),
    ("Pfizer's Upjohn has merged with Mylan to form Viatris Inc.", 2005, "Pfizer"),
    # Abbott's pharma business became AbbVie in 2013; the registry renamed its earlier trials
    ("AbbVie", 2008, "AbbVie"),
    ("AbbVie (prior sponsor, Abbott)", 2008, "AbbVie"),
    ("Abbott", 2010, "AbbVie"),
    ("Abbott", 2015, None),
    # spin-offs
    ("Organon and Co", 2015, "Merck & Co"),
    ("Organon and Co", 2022, None),
    ("Biohaven Therapeutics Ltd.", 2024, None),  # the independent spin-off, not the business Pfizer bought
    ("Biohaven Pharmaceuticals, Inc.", 2022, None),
    ("Pfizer's Upjohn has merged with Mylan to form Viatris Inc.", 2015, "Pfizer"),
    ("Pfizer's Upjohn has merged with Mylan to form Viatris Inc.", 2021, None),
    ("Pfizer's Upjohn has merged with Mylan to form Viatris Inc.", None, "Pfizer"),
    ("Sandoz", 2022, "Novartis"),
    ("Sandoz", 2023, None),
    # a pattern inside another word is not a match
    ("University Hospitals Coventry and Warwickshire NHS Trust", 2020, None),
    ("The Hillshire Brands Company", 2020, None),
    ("Shire", 2020, "Takeda"),
    ("Healios K.K.", 2018, None),
    ("Kephalios", 2018, None),
    ("ImmunoGenesis", 2025, None),
    ("ImmunoGen, Inc.", 2025, "AbbVie"),
    ("Natural Immunogenics Corp.", 2025, None),
    ("Pocket Naloxone Corp", 2021, None),
    ("Loxo Oncology, Inc.", 2020, "Eli Lilly"),
    ("Cardeas Pharma", 2014, None),
    ("Ardea Biosciences, Inc.", 2013, "AstraZeneca"),
    ("Tatiana Falcone, MD", 2015, None),
    ("Alcon Research", 2014, "Novartis"),
    ("Enrico Ammirati", 2025, None),
    ("Mirati Therapeutics Inc.", 2024, "Bristol Myers Squibb"),
    ("Turning Point", 2023, None),
    ("Turning Point Therapeutics, Inc.", 2023, "Bristol Myers Squibb"),
    # no start year: the window cannot be applied
    ("Genentech, Inc.", None, "Roche"),
    ("Incyte Corporation", 2015, None),
    (None, 2015, None),
]


@pytest.mark.parametrize("name,year,parent", CASES)
def test_top20_parent(name, year, parent):
    assert top20_parent(name, year) == parent


def test_every_nonleading_match_in_the_panel_was_reviewed():
    """A sponsor name in the committed panel whose top-20 match is not the leading name must have been read by hand:
    an unlisted renamed subsidiary would otherwise be typed as its parent for all years."""
    R = os.path.join(ROOT, "results")
    names = set(pd.read_csv(f"{R}/phase_entries.csv.gz", usecols=["lead_sponsor"]).lead_sponsor.dropna())
    names |= set(pd.read_csv(f"{R}/programmes.csv.gz", usecols=["first_sponsor"]).first_sponsor.dropna())
    assert sponsor_names_audit.nonleading(names) == []
