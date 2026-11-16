# factcheck

Scripts used to re-check the numbers and citations of the working paper against their sources. They are not part of
the pipeline and expect to be run from this folder, with downloaded texts and data kept out of version control.

| Script | What it checks |
|---|---|
| `verify_pilot.py` | Recomputes every number quoted from the pilot outputs in `../results/` |
| `check_minikel_repo.py`, `check_omim_only.py` | Source composition of Minikel et al.'s genetic-support data (OMIM, OTG, intOGen); saved output in `check_omim_only.out` |
| `fetch_meta.py`, `show_meta.py`, `dois.json`, `meta.json` | Crossref metadata of every cited DOI (titles, journals, volumes, pages) |
| `fetch_texts.py`, `fetch_grey.py`, `links.py`, `ctx.py` | Retrieve open-access texts of cited sources locally and print the passages behind each claim |
| `sbir_review.py` | Sorts NIH SBIR/STTR-to-sponsor matches into confidence buckets for hand review |
| `convergence_audit.py` | Runs a pipeline script with `Logit.fit` wrapped and lists every fit that did not converge (quasi-separation) |
| `stopreasons_crosscheck.py` | Agreement of the stop-reason classifier with the Open Targets StopReasons predictions (Razuvayevskaya et al., 2024), by class; output in `../results/stopreasons_crosscheck.txt` |
| `sponsor_missing_acquisitions.py` | Sponsor typing: counts the trials that a longer list of top-20 acquisitions (deal years as remembered, not verified one by one) would move to top-20; a bound, not used for typing; output in `../results/sponsor_missing_acquisitions.txt` |
| `sponsor_names_audit.py` | Sponsor typing: lists every industry sponsor name whose top-20 match is not the leading name (a renamed subsidiary needs its own entry with an acquisition year); fails on a name that has not been reviewed; output in `../results/sponsor_names_audit.txt` |
| `stopreasons_support.py` | Every pattern of the stop-reason classifier must match a text outside the held-out set (tuning texts or the StopReasons file); output in `../results/stopreasons_support.txt` |
| `double_coding/` | Blind double-coding of the 200 held-out stop-reason texts ([roadmap](../docs/roadmap.md)): `codebook.md`, `make_sheet.py` (builds `coding_sheet.xlsx` and `key.csv`), `double_coding_eval.py` (agreement, κ, financial-class precision and recall, disagreements) |

Full texts are fetched for personal checking only and are not redistributed here.
