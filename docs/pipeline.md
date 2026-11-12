# Pipeline, checks and licences

## Steps
| Step | Script | Source (licence) |
|---|---|---|
| Open Targets clinical reports, evidence, targets, diseases, molecules | `pilot/fetch_opentargets.py` | Open Targets Platform ≥ 26.03 (CC0) |
| All interventional studies (sponsor, phase, dates, status, why_stopped) | `pilot/fetch_ctgov.py all` | ClinicalTrials.gov API v2 (public domain) |
| Genetic-support labels (Minikel et al. 2024 definition) | `pilot/gensup.py` | `ericminikel/genetic_support` @ b84cf05 (CC BY 4.0) |
| Programme panel, H1 selection, phase transitions, logits | `pilot/build_panel26.py` | — |
| Robustness: adjusted H1, strict / similar-indication advancement, no-OMIM, benchmark | `pilot/robust26.py` | — |
| Ex-ante support from Open Targets evidence dated by Falaguera et al. | `pilot/gs_ot_dated.py` | Zenodo 15922783 (OT 25.03) |
| Trial stop reasons and rates around the 2022 funding downturn | `pilot/rq2_stops.py`, `pilot/rq2_rr.py`, `pilot/stopreasons.py` | — |
| Genetic support of trials stopped for money vs completed (H4), with the dated Open Targets measure when its directory is given | `pilot/h4_biology.py` | — |
| NIH SBIR/STTR awards, sponsor linkage (hand-review decisions in `pilot/sbir_decisions.csv`), models | `pilot/fetch_reporter_sbir.py`, `pilot/sbir_link.py`, `pilot/sbir_models.py` | NIH RePORTER API v2 (public) |
| Sponsor typing (acquisition- and spin-off-dated top-20) | `pilot/sponsors.py` | — |
| SEC Form D private placements (biotech, pharma, other health care; no pooled funds), sponsor linkage (hand-review decisions in `pilot/formd_decisions.csv`) with offerings and amounts, models incl. the amount raised before the trial and the US-only comparison (`pilot/sponsor_region.py`) | `pilot/fetch_formd.py`, `pilot/formd_link.py`, `pilot/formd_models.py`, `pilot/formd_stops.py` | SEC Form D data sets 2009 Q1–2026 Q3 (public domain) |
| Approval dates: EMA/PMDA report years and ChEMBL first-approval years, advancement variants that drop approvals preceding the phase entry | `pilot/fetch_chembl_approval.py`, `pilot/approval_dates.py` | ChEMBL web service, release 37 (CC BY-SA 3.0) |
| Beneficial owners of public sponsors from the EDGAR master index (Schedule 13D/13G filers; registrants S-1/F-1/424B4/10-K/20-F/40-F); owner classes in `pilot/investor_classes.tsv`, hand-review decisions in `pilot/owners_decisions.csv` — *in preparation, not yet run* | `pilot/fetch_edgar_owners.py`, `pilot/owners_link.py`, `pilot/owners_models.py` | EDGAR full index (public domain) |
| Results-at-a-glance figure | `pilot/figure_glance.py` | — |

## Running it
`make all` downloads the core sources, rebuilds the core tables, redraws the figure and runs the checks; the dated
Open Targets evidence, the approval dates and the Form D steps are the separate targets `make dated`, `make approvals`
and `make formd` (the last needs `SEC_USER_AGENT`). Step by step:
```
python pilot/fetch_opentargets.py data/ot
python pilot/fetch_ctgov.py all data/ctgov_all.csv
git clone https://github.com/ericminikel/genetic_support /tmp/genetic_support   # then checkout b84cf05
python pilot/build_panel26.py data/ot /tmp/genetic_support/data results
python pilot/robust26.py results
python pilot/gs_ot_dated.py results data/ot data/falaguera/evidence_dated /tmp/genetic_support/data
python pilot/khb26.py results > results/khb.txt
python pilot/khb26.py results gs_ot_ante gs_ot_entries.csv.gz >> results/khb.txt
python pilot/rq2_stops.py data/ctgov_all.csv results
python pilot/rq2_rr.py results
python factcheck/sponsor_names_audit.py data/ctgov_all.csv results    # fails on an unreviewed renamed subsidiary
python pilot/h4_biology.py data/ot results data/ctgov_all.csv /tmp/genetic_support/data data/falaguera/evidence_dated
python pilot/fetch_reporter_sbir.py data/nih_sbir_sttr.csv 2000 2025
python pilot/sbir_link.py data/nih_sbir_sttr.csv data/ctgov_all.csv results
python pilot/sbir_models.py results
SEC_USER_AGENT="Your Name you@example.org" python pilot/fetch_formd.py data/formd
python pilot/formd_link.py data/formd/formd_biopharma.csv.gz results
python pilot/formd_models.py results
python pilot/formd_stops.py data/ctgov_all.csv results
python pilot/fetch_chembl_approval.py data/chembl_first_approval.csv
python pilot/approval_dates.py data/ot results data/chembl_first_approval.csv
SEC_USER_AGENT="Your Name you@example.org" python pilot/fetch_edgar_owners.py data/edgar 2001 2026   # in preparation
python pilot/owners_link.py data/edgar results                                                         # in preparation
python pilot/owners_models.py results                                                                  # in preparation
python pilot/figure_glance.py results figures/results_glance.png
```
On GitHub, **Actions → pilot → Run workflow** downloads the sources and rebuilds the core tables.

## Repository layout
```
pilot/       pipeline: data download, programme panel, models, stop-reason classifier, README figure
docs/        methods, detailed results, this page and the data dictionary for results/
results/     model output and derived tables (small, versioned; provenance in results/PROVENANCE.txt)
figures/     README figure, rebuilt from results/ by pilot/figure_glance.py
tests/       unit tests and README-vs-results consistency checks
factcheck/   scripts that re-check the working paper's numbers and citations against their sources
.github/     CI checks on every push; manual end-to-end pipeline workflow
```

## Checks
`make check` runs ruff and the tests. `pytest -q` runs unit tests of the stop-reason classifier, including its
negation handling, and verifies that every headline number in the README matches the model output in `results/`.
GitHub Actions runs the same checks, lint and formatting checks, a byte-compile of all scripts and a rebuild of the
figure on every push, on Python 3.13 with `requirements.txt`. CI checks the stored results; it does not re-run the
data downloads and models. The tables in `results/` were built locally with Python 3.9.6 and pandas 2.2.3
(`results/PROVENANCE.txt`).

## Licences
Code: MIT (see `LICENSE`). Derived tables in `results/` keep the licences of their sources: Open Targets Platform
(CC0), ClinicalTrials.gov and SEC Form D data sets (public domain), NIH RePORTER (public), ChEMBL (CC BY-SA 3.0; the
first-approval extract in `results/chembl_first_approval.csv`), and Minikel et al. (2024)
`genetic_support` data (CC BY 4.0; Minikel EV, Painter JL, Dong CC, Nelson MR. *Refining the impact of genetic
evidence on clinical success.* Nature 629, 624–629 (2024), doi:10.1038/s41586-024-07316-0).
