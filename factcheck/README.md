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
| `double_coding/` | Blind double-coding of the 200 held-out stop-reason texts ([#2](https://github.com/lappunovmark/vc-genetics-pilot/issues/2)): `codebook.md`, `make_sheet.py` (builds `coding_sheet.xlsx` and `key.csv`), `double_coding_eval.py` (agreement, κ, financial-class precision and recall, disagreements) |

Full texts are fetched for personal checking only and are not redistributed here.
