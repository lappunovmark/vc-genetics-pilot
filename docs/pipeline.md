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
| Genetic support of trials stopped for money vs completed (H4) | `pilot/h4_biology.py` | — |
| NIH SBIR/STTR awards, sponsor linkage (hand-review decisions in `pilot/sbir_decisions.csv`), models | `pilot/fetch_reporter_sbir.py`, `pilot/sbir_link.py`, `pilot/sbir_models.py` | NIH RePORTER API v2 (public) |
| Sponsor typing (acquisition- and spin-off-dated top-20) | `pilot/sponsors.py` | — |
| SEC Form D private placements (biotech, pharma, other health care; no pooled funds), sponsor linkage (hand-review decisions in `pilot/formd_decisions.csv`), models | `pilot/fetch_formd.py`, `pilot/formd_link.py`, `pilot/formd_models.py` | SEC Form D data sets 2009 Q1–2026 Q3 (public domain) |
| Results-at-a-glance figure | `pilot/figure_glance.py` | — |

## Running it
`make all` downloads the sources, rebuilds `results/`, redraws the figure and runs the checks. Step by step:
```
python pilot/fetch_opentargets.py data/ot
python pilot/fetch_ctgov.py all data/ctgov_all.csv
git clone https://github.com/ericminikel/genetic_support /tmp/genetic_support   # then checkout b84cf05
python pilot/build_panel26.py data/ot /tmp/genetic_support/data results
python pilot/robust26.py results
python pilot/gs_ot_dated.py results data/ot data/falaguera/evidence_dated /tmp/genetic_support/data
python pilot/rq2_stops.py data/ctgov_all.csv results
python pilot/rq2_rr.py results
python pilot/h4_biology.py data/ot results data/ctgov_all.csv /tmp/genetic_support/data
python pilot/fetch_reporter_sbir.py data/nih_sbir_sttr.csv 2000 2025
python pilot/sbir_link.py data/nih_sbir_sttr.csv data/ctgov_all.csv results
python pilot/sbir_models.py results
SEC_USER_AGENT="Your Name you@example.org" python pilot/fetch_formd.py data/formd
python pilot/formd_link.py data/formd/formd_biopharma.csv.gz results
python pilot/formd_models.py results
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
(CC0), ClinicalTrials.gov and SEC Form D data sets (public domain), NIH RePORTER (public), and Minikel et al. (2024)
`genetic_support` data (CC BY 4.0; Minikel EV, Painter JL, Dong CC, Nelson MR. *Refining the impact of genetic
evidence on clinical success.* Nature 629, 624–629 (2024), doi:10.1038/s41586-024-07316-0).
