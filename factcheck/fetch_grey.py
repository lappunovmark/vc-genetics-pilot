"""Grey literature, preprints and publisher pages -> texts/<name>.txt (generic UA, no personal data)."""

import sys
import time

from fetch_texts import get, html_text, pdf_text, save, say

URLS = [
    ("BIO2021", "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf"),
    ("Citeline2024", "https://www.citeline.com/-/media/8f1a3eb60cde4827bb513ea6f78316e2"),
    ("Fierce_graveyard2023", "https://www.fiercebiotech.com/biotech/2023-biotech-graveyard"),
    (
        "Fierce_layoffs2023",
        "https://www.fiercebiotech.com/biotech/every-bad-signal-theres-good-sign-not-far-behind-biopharma-layoffs-rise-57-yoy-hope-2024",
    ),
    ("CTA_terminations2022", "https://www.clinicaltrialsarena.com/features/clinical-trial-terminations/"),
    ("Tranchero2026", "https://www.matteotranchero.com/pdf/Diamondsintherough_Tranchero.pdf"),
    ("Li2024_AFA_page", "https://afajof.org/management/viewp.php?n=137172"),
    ("Paterson2026_abs", "https://arxiv.org/abs/2606.14823"),
    ("Paterson2026", "https://arxiv.org/pdf/2606.14823"),
    ("Gao2024_abs", "https://arxiv.org/abs/2406.10292"),
    ("Gao2024", "https://arxiv.org/pdf/2406.10292"),
    ("Pak2015", "https://www.biorxiv.org/content/10.1101/021543v1.full.pdf"),
    ("Pak2015_html", "https://www.biorxiv.org/content/10.1101/021543v1.full"),
    ("Zhou2024", "https://www.medrxiv.org/content/10.1101/2024.02.26.24303388v1.full.pdf"),
    ("Guedj2004", "https://www.nber.org/system/files/working_papers/w10933/w10933.pdf"),
    ("Hermosilla2017", "https://www.nber.org/system/files/working_papers/w23989/w23989.pdf"),
    ("KLP_nber", "https://www.nber.org/system/files/working_papers/w24595/w24595.pdf"),
    ("Cunningham_nber", "https://www.nber.org/system/files/working_papers/w25241/w25241.pdf"),
    ("NASEM2022_catalog", "https://nap.nationalacademies.org/catalog/26376"),
    ("Hay2014_nature", "https://www.nature.com/articles/nbt.2786"),
    ("Nelson2015_nature", "https://www.nature.com/articles/ng.3314"),
    ("DowdenMunro2019_nature", "https://www.nature.com/articles/d41573-019-00074-z"),
    ("Harrison2016_nature", "https://www.nature.com/articles/nrd.2016.184"),
    ("Hurle2016_nature", "https://www.nature.com/articles/nrd.2016.164"),
    ("Ochoa2022_nature", "https://www.nature.com/articles/d41573-022-00120-3"),
    ("Rusina2023_nature", "https://www.nature.com/articles/d41573-023-00158-x"),
    ("Phares2025_nature", "https://www.nature.com/articles/d41573-025-00036-8"),
    ("Kasenda2014_jama", "https://jamanetwork.com/journals/jama/fullarticle/1838196"),
    ("Kennedy2023_sd", "https://www.sciencedirect.com/science/article/pii/S1359644622004305"),
    (
        "Kang2026_lww",
        "https://journals.lww.com/lww-medicalcare/fulltext/2026/07000/success_rates_of_venture_capital_investment_in.4.aspx",
    ),
    ("Falaguera_zenodo", "https://zenodo.org/records/15922783"),
    ("StopReasons_github", "https://github.com/opentargets/StopReasons"),
    ("CTO_github", "https://github.com/sunlabuiuc/CTO"),
    ("timeseries_github", "https://github.com/opentargets/timeseries"),
    ("DM2019_suppl", "https://media.nature.com/original/magazine-assets/d41573-019-00074-z/16690028"),
    (
        "DM2019_clarivate",
        "https://clarivate.com/life-sciences-healthcare/blog/record-new-drug-approvals-fleeting-success-or-here-to-stay/",
    ),
    ("Phares2025_suppl", "https://media.nature.com/original/magazine-assets/d41573-025-00036-8/50677254"),
    ("Phares2025_newdigs", "https://newdigs.tuftsmedicalcenter.org/?p=4912"),
    (
        "NEWDIGS2023_pdf",
        "https://newdigs.tuftsmedicalcenter.org/wp-content/uploads/2023/10/NEWDIGS-Success-Rate-Comparison-2023F210v056.pdf",
    ),
    ("NEWDIGS2023_page", "https://newdigs.tuftsmedicalcenter.org/are-cell-and-gene-therapy-programs-a-better-bet/"),
]

only = set(sys.argv[1:])
for name, url in URLS:
    if only and name not in only:
        continue
    say("##", name, url)
    r = get(url)
    if r is None:
        save(name, "(request failed)", url)
        continue
    ct = r.headers.get("content-type", "")
    say("  status", r.status_code, ct, len(r.content), r.url[:120])
    if r.content[:4] == b"%PDF":
        t = pdf_text(r.content)
    elif "html" in ct or r.content.lstrip()[:1] == b"<":
        t = html_text(r.content)
    else:
        t = r.text
    save(name, f"HTTP {r.status_code} final_url={r.url}\n\n" + t, url)
    time.sleep(1)
