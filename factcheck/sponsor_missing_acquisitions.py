"""How much would acquisitions that are NOT in pilot/sponsors.py change the sponsor typing?

Usage (from the repository root): python factcheck/sponsor_missing_acquisitions.py CTGOV_ALL.csv [RESULTS_DIR]

sponsors.py lists the acquired companies met in the data, not every deal of the top-20 companies. This script takes
a longer list of deals (CANDIDATES: name pattern, acquirer, completion year as remembered, NOT verified one by one)
and counts the trials that started in or after the deal year under the acquired company's own name and are typed
non-top-20. The counts bound the size of the omission; they are not used to change any typing. A pattern can also
catch an unrelated company (the names are printed), which makes the bound more generous.
Writes RESULTS_DIR/sponsor_missing_acquisitions.txt.
"""

import os
import re
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "pilot"))
import sponsors  # noqa: E402

CANDIDATES = {
    "Bristol Myers Squibb": "medarex:2009 zymogenetics:2010 amylin:2012 inhibitex:2012 cardioxyl:2015 flexus:2015 "
    "abraxis:2019 pharmion:2019 impact_biomed:2019",
    "Johnson & Johnson": "cougar_bio:2009 aragon_pharm:2013 novira:2015 scios:2003 alza_corp:2001 ambrx:2024 "
    "intra-cellular:2025 proteologix:2024 peninsula_pharm:2005 omrix:2008",
    "Astellas": "osi_pharm:2010 agensys:2007 ganymed:2016 ogeda:2017 mitobridge:2018 potenza:2018",
    "Daiichi Sankyo": "u3_pharma:2008 ranbaxy:2008",
    "Amgen": "micromet:2012 biovex:2011 kai_pharm:2012 abgenix:2006 tularik:2004 dezima:2015 teneobio:2021",
    "Gilead Sciences": "cv_therapeutics:2009 calistoga:2011 ym_bio:2013 myogen:2006 arresto:2011 cymabay:2024 "
    "mirobio:2022 myr_gmbh:2021",
    "Takeda": "nycomed:2011 intellikine:2012 ligocyte:2012 inviragen:2013 nimbus_lakshmi:2023 viropharma:2019 "
    "nps_pharm:2019 dyax:2019",
    "Roche": "ignyta:2018 anadys:2011 seragon:2014 santaris:2014 trophos:2015 promedior:2020 inflazome:2020 "
    "telavant:2023 carmot:2024 poseida:2025 89bio:2025 foundation_medicine:2018",
    "AstraZeneca": "amplimmune:2013 omthera:2013 zs_pharma:2015 novexel:2010 cambridge_antibody:2006 kudos:2006 "
    "cincor:2023 icosavax:2024 gracell:2024 amolyt:2024 fusion_pharm:2024 caelum:2021 neogene:2023 synageva:2021 "
    "achillion:2021 portola:2021",
    "Pfizer": "king_pharm:2011 coley_pharm:2007 encysive:2008 vicuron:2005 excaliard:2011 foldrx:2010 "
    "trillium_therap:2021 reviral:2022 amplyx:2021 therachon:2019 redvax:2015 bamboo_therap:2016 parke-davis:2000 "
    "warner-lambert:2000 agouron:2000 sugen:2003 searle:2003",
    "Merck & Co": "sirna_therap:2006 inspire_pharm:2011 iomet:2016 rigontec:2017 viralytics:2018 tilos:2019 "
    "themis_bio:2020 pandion:2021 eyebio:2024 caraway:2023",
    "AbbVie": "facet_biotech:2010 solvay_pharm:2010 kos_pharm:2006 landos:2024 aliada:2025 capstan_therap:2025 "
    "mitokinin:2022 syndesi:2022 forest_lab:2020 tobira:2020 kythera:2020 actavis:2020 warner_chilcott:2020",
    "Novartis": "genoptix:2011 fougera:2012 costim:2014 selexys:2016 ziarco:2017 encore_vision:2017 gyroscope:2022 "
    "chinook:2023 morphosys:2024 mariana_onc:2024 kate_therap:2024 anthos:2025 vedere:2020 arctos:2021 "
    "avidity:2026 regulus:2025",
    "Eli Lilly": "icos_corp:2007 avid_radio:2010 armo_bio:2018 colucid:2017 hypnion:2007 sgx_pharm:2008 "
    "applied_molecular_evolution:2004 disarm:2020 protomer:2021 versanis:2023 sigilon:2023 verve_therap:2025 "
    "siteone:2025 adverum:2025",
    "GSK": "reliant_pharm:2007 id_biomedical:2005 corixa:2005 praecis:2007 genelabs:2009 cellzome:2012 aiolos:2024 "
    "domantis:2007",
    "Sanofi": "bipar:2009 fovea:2009 targegen:2010 zentiva:2009 shantha:2009 protein_sciences:2017 kymab:2021 "
    "kiadis:2021 amunix:2022 inhibrx:2024 blueprint_medicines:2025 vigil_neuro:2025 tidal_therap:2021",
    "Bayer": "schering_ag:2006 berlex:2006 algeta:2014 bluerock:2019 askbio:2020 asklepios:2020 vividion:2021 "
    "conceptus:2013",
    "Novo Nordisk": "forma_therap:2022 inversago:2023 cardior_pharm:2024 emisphere:2020 corvidia:2020 akero:2025",
    "Boehringer Ingelheim": "nbe-therap:2020 abexxa:2021 amal_therap:2019 nerio:2023",
}


def main(path, R=os.path.join(ROOT, "results")):
    ct = pd.read_csv(path, usecols=["nct_id", "lead_sponsor", "lead_class", "start_date"], dtype=str)
    ct = ct[ct.lead_class.eq("INDUSTRY")].copy()
    ct["year"] = pd.to_datetime(ct.start_date, errors="coerce", format="mixed").dt.year
    ct["parent"] = [sponsors.top20_parent(n, y) for n, y in zip(ct.lead_sponsor, ct.year)]
    E = pd.read_csv(f"{R}/phase_entries.csv.gz", usecols=["lead_sponsor", "sponsor_tier", "entry_year"])
    E = E[E.sponsor_tier.fillna("").str.startswith("Industry")]
    rows = []
    for acquirer, deals in CANDIDATES.items():
        for deal in deals.split():
            pat, year = deal.rsplit(":", 1)
            rx = re.compile(r"\b" + re.escape(pat.replace("_", " ")), re.I)
            m = ct[ct.lead_sponsor.map(lambda n: bool(rx.search(n)))]
            after = m[m.year.ge(int(year)) & m.parent.isna()]
            pe = E[E.lead_sponsor.fillna("").map(lambda n: bool(rx.search(n))) & E.entry_year.ge(int(year))]
            rows.append(
                {
                    "company": pat.replace("_", " "),
                    "acquirer": acquirer,
                    "year": int(year),
                    "trials_under_own_name": len(m),
                    "of_which_from_deal_year": len(after),
                    "panel_phase_entries_from_deal_year": len(pe),
                    "names": "; ".join(sorted(set(after.lead_sponsor))[:2]),
                }
            )
    t = pd.DataFrame(rows).sort_values(["of_which_from_deal_year", "company"], ascending=[False, True], kind="stable")
    n_top = int(ct.parent.notna().sum())
    out = [
        f"deals checked: {len(t)}; industry trials typed top-20: {n_top}",
        f"trials started in or after the deal year under the acquired company's own name (typed non-top-20): "
        f"{int(t.of_which_from_deal_year.sum())} ({t.of_which_from_deal_year.sum() / n_top:.2%} of the top-20 trials); "
        f"phase entries of the panel: {int(t.panel_phase_entries_from_deal_year.sum())}",
        "=" * 100,
        t[t.of_which_from_deal_year.gt(0) | t.panel_phase_entries_from_deal_year.gt(0)].to_string(index=False),
    ]
    text = "\n".join(out)
    with open(os.path.join(R, "sponsor_missing_acquisitions.txt"), "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:3])
