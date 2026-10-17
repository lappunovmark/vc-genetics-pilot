# Genetic support × sponsor financing × clinical success — MSc BIE dissertation (UCL)

Pilot code for the working paper on ex-ante human genetic support, sponsor type and clinical development
outcomes (draft in Claude Docs, Section 5.1 reports the pilot).

## Pipeline
| Step | Script | Source (licence) |
|---|---|---|
| Open Targets clinical reports, evidence, targets, diseases, molecules | `pilot/fetch_opentargets.py` | Open Targets Platform ≥ 26.03 (CC0) |
| All interventional studies (sponsor, phase, dates, status, why_stopped) | `pilot/fetch_ctgov.py all` | ClinicalTrials.gov API v2 (public domain) |
| Genetic-support labels (Minikel et al. 2024 definition) | `pilot/gensup.py` | `ericminikel/genetic_support` @ b84cf05 (CC BY 4.0) |
| Programme panel, H1 selection, phase transitions, logits | `pilot/build_panel26.py` | — |
| Robustness: adjusted H1, strict / similar-indication advancement, no-OMIM, benchmark | `pilot/robust26.py` | — |
| Ex-ante support from Open Targets evidence dated by Falaguera et al. | `pilot/gs_ot_dated.py` | Zenodo 15922783 (OT 25.03) |
| RQ2: stop reasons and rates around the 2022 funding downturn | `pilot/rq2_stops.py`, `pilot/stopreasons.py` | — |
| Sponsor typing (acquisition- and spin-off-dated top-20) | `pilot/sponsors.py` | — |

Run locally:
```
python pilot/fetch_opentargets.py data/ot
python pilot/fetch_ctgov.py all data/ctgov_all.csv
git clone https://github.com/ericminikel/genetic_support /tmp/genetic_support   # then checkout b84cf05
python pilot/build_panel26.py data/ot /tmp/genetic_support/data results
python pilot/robust26.py results
python pilot/gs_ot_dated.py results data/ot data/falaguera/evidence_dated /tmp/genetic_support/data
python pilot/rq2_stops.py data/ctgov_all.csv results
```
or run **Actions → pilot → Run workflow** once the repository is on GitHub.

## Validation done
* `gensup.py` reproduces Minikel et al.'s 1,255 genetically supported target–indication pairs exactly.
* Genetic insight for indications outside their set: approximation agrees with their label for 96.6% of 1,014 indications.
* Replication note: their headline Phase I→launch RS (2.6) is a crude ratio of launch shares; the product of
  phase-wise RS (1.076 × 1.571 × 1.275), as their Methods define it, gives 2.16.
* Stop-reason classifier v3: 83.0% agreement with hand labels on 200 held-out texts (Cohen's κ 0.79); financial or
  strategic class precision 0.91, recall 0.86. Hand labels: `results/rq2_hand_labels.csv` (first pass by an AI
  assistant; to be double-coded by the author).

## Pilot results (Open Targets 26.09, ClinicalTrials.gov snapshot 17 Oct 2026)
* 35,887 drug × MeSH-indication programmes; 29,199 in indications with genetic insight.
* Ex-ante genetic support at phase entry: OR 2.48 (2.10–2.93) for advancing a phase; no difference between small
  industry sponsors and top-20 pharma (interaction OR 1.26, 0.75–2.12).
* Small industry sponsors start fewer programmes with ex-ante support (adjusted OR 0.64, 0.46–0.88), not significant
  for novel drugs (0.79, 0.49–1.29).
* Financial or strategic trial stops per 1,000 active trial-years rose 2.3–2.65-fold from 2016–21 to 2022–25 in every
  industry group; stops citing lack of funding rose 2.75-fold (1.59–4.78), almost only among small sponsors.

## Known pilot simplifications
* Sponsor tiers (top-20; other industry by portfolio size) stand in for VC backing until EDGAR / PitchBook data are linked.
* Most approval records carry no date, so an approval that preceded a phase entry can count as advancement.
* Registry programmes include investigator-initiated trials of marketed drugs; levels of relative success are therefore
  not comparable with Pharmaprojects-based estimates (pilot RS 4.0–4.2 vs 2.16).
* Ex-ante support uses association years; OMIM rows (undated) are treated as ex ante, with a no-OMIM sensitivity.
  Falaguera et al. (2026) evidence timestamps will replace this.
