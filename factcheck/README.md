# factcheck

Scripts used to re-check the numbers and citations of the working paper against their sources. They are not part of
the pipeline and expect to be run from this folder, with downloaded texts and data kept out of version control.

| Script | What it checks |
|---|---|
| `verify_pilot.py` | Recomputes every number quoted from the pilot outputs in `../results/` |
| `check_minikel_repo.py`, `check_omim_only.py` | Source composition of Minikel et al.'s genetic-support data (OMIM, OTG, intOGen) |
| `fetch_meta.py`, `show_meta.py`, `dois.json`, `meta.json` | Crossref metadata of every cited DOI (titles, journals, volumes, pages) |
| `fetch_texts.py`, `fetch_grey.py`, `links.py`, `ctx.py` | Retrieve open-access texts of cited sources locally and print the passages behind each claim |
| `sbir_review.py` | Sorts NIH SBIR/STTR-to-sponsor matches into confidence buckets for hand review |

Full texts are fetched for personal checking only and are not redistributed here.
