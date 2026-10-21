# Methods

Short reference for the definitions used in the pilot. The code is the final word; each section names the script.

## Units of analysis

**Programme** (`build_panel26.py`). A parent drug × MeSH indication pair in the Open Targets Platform 26.09
clinical data, which ships trial-level records from AACT (lead sponsor, phase, start date, status, `why_stopped`)
linked to drug, target and disease. Disease IDs are mapped to MeSH by Open Targets cross-reference or exact name,
otherwise to the nearest mapped ancestor (breadth-first, at most six levels). 35,887 programmes;
29,199 are in indications with *genetic insight* (at least one human genetic association for a similar trait, as in
Minikel et al.).

**Phase entry.** The first trial of a programme in phase 1, 2 or 3 (phase 1/2 counts as 2, phase 2/3 as 3). Entry
year = start year of that trial. The entry trial's lead sponsor defines the sponsor tier.

**Advancement.** A later trial of the same programme in a higher phase that started on or after the entry date, or
an approval of the drug for that indication. Entries with a higher-phase trial that started *before* the entry are
dropped. Entries from 2000 to six years before the last entry year are modelled, so each has follow-up time.
A stricter variant uses trials only (`advanced_trial_only`); a looser one counts higher-phase trials in a similar
indication (`advanced_sim`).

## Genetic support (`gensup.py`, validated against Minikel et al. 2024)

`support(T, I)` is true if the drug's target gene T has an association with a trait A whose MeSH similarity to the
indication I is at least 0.8. Sources: OMIM, GWAS (Open Targets Genetics with L2G share ≥ 0.5, 2005–2022), PICCOLO
and Genebass. The re-implementation reproduces all 1,258 supported target–indication pairs in their data.

**Ex ante.** Only associations dated before the phase-entry year count. OMIM rows are undated and are treated as
ex ante; every model is also run without OMIM. `gs_ot_dated.py` adds an independent measure from Open Targets
evidence dated by Falaguera et al. (Zenodo 15922783), where undated evidence never counts as ex ante.

## Sponsor groups

| Where | Groups | Rule |
|---|---|---|
| Programme panel (`build_panel26.py`, `sponsors.py`) | Top-20 pharma; industry small (≤ 5 drugs), mid (6–30), large (> 30); academic/other; government | Top-20 = largest companies by 2023 pharmaceutical revenue, matched by regular expression; an acquired company counts as the parent only for trials that started in or after the acquisition year. Other industry sponsors are sized by the number of distinct parent drugs their normalised name leads across all Open Targets trial records. |
| Trial stops (`rq2_stops.py`) | Top-20 pharma; industry small (≤ 20 trials), mid (21–200), large (> 200) | Size = number of interventional drug trials the normalised lead-sponsor name has ever led on ClinicalTrials.gov. |

Sponsor size stands in for venture backing until SEC Form D rounds are linked (see the roadmap in the README).

## Models

Logistic regressions with standard errors clustered by drug (`robust26.py`), on programmes and phase entries in
indications with genetic insight.

* **Selection (H1).** Programme level: ex-ante genetic support at the first trial ~ sponsor tier + first-trial
  period + therapeutic area + modality.
* **Advancement (H3).** Phase-entry level: advanced ~ ex-ante support + sponsor tier + phase + entry period + area +
  modality, then with a support × tier interaction.
* **Mediation (H2).** Karlson–Holm–Breen decomposition of the tier gap in advancement through ex-ante support
  (`khb26.py`).

## Trial stops around the 2022 funding downturn (`rq2_stops.py`, `rq2_rr.py`, `stopreasons.py`)

`why_stopped` texts of terminated, withdrawn and suspended industry drug trials are classified by a keyword
classifier (v3). One label per text, first match in this order: no funding; safety / benefit-risk; efficacy /
futility; COVID-19; enrolment; M&A / licensing; business / strategic; sponsor decision, unspecified. Negated or
neutral mentions ("not due to safety", "no safety concerns", "safety committee") are removed before matching.
*Financial or strategic* = no funding, M&A / licensing or business / strategic.

Rates are stops per 1,000 active trial-years (each trial at risk adds one trial-year per calendar year). Rate ratios
compare 2022–25 with 2016–21, with Poisson confidence intervals: log RR ± 1.96 √(1/a + 1/b).

## NIH SBIR/STTR linkage (`sbir_link.py`, `sbir_models.py`)

Industry lead sponsors are matched to NIH RePORTER SBIR/STTR awardees: exact match of normalised names, then
fuzzy match (RapidFuzz `token_sort_ratio` ≥ 92) within blocks that share the first token. Every match is written
out for review; matches that differ by more than a legal form need an explicit decision in `pilot/sbir_decisions.csv`.
A sponsor counts as SBIR/STTR-funded before a trial if its first award year precedes the trial's start year.

## Known limitations

See *Known pilot simplifications* in the README. The two that matter most: most approval records carry no date,
and registry programmes include investigator-initiated trials of marketed drugs, so absolute success rates are not
comparable with Pharmaprojects-based estimates.
