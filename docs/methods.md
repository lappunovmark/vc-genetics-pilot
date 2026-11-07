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

**Approval dates** (`approval_dates.py`). Most Open Targets approval records carry no date, so an approval granted
before a phase entry can count as advancement (1,205 of 26,542 model entries advance through an approval alone).
Two dates are looked up for them: the earliest EMA or PMDA approval report of the same drug × indication (the only
dated approval sources in Open Targets 26.09) and the drug's year of first approval from ChEMBL 37. `advanced_dated`
drops an approval whose indication-level date, or failing that the drug-level date, precedes the entry year (619
entries); `advanced_dated_known` additionally drops undated approvals. The drug-level date is conservative: a later
indication can be approved after the drug's first approval, so some genuine advancements are removed.

## Genetic support (`gensup.py`, validated against Minikel et al. 2024)

`support(T, I)` is true if the drug's target gene T has an association with a trait A whose MeSH similarity to the
indication I is at least 0.8. Sources: OMIM, GWAS (Open Targets Genetics with L2G share ≥ 0.5, 2005–2022), PICCOLO
and Genebass. The re-implementation reproduces all 1,258 supported target–indication pairs in their data.

**Ex ante.** Only associations dated before the phase-entry year count. OMIM rows are undated and are treated as
ex ante; every model is also run without OMIM. `gs_ot_dated.py` adds an independent measure from Open Targets
evidence dated by Falaguera et al. (Zenodo 15922783), where undated evidence never counts as ex ante; H1, H3 and the
KHB decomposition are run with it there, and `h4_biology.py`, `sbir_models.py` and `formd_models.py` repeat their
headline models with it when the dated evidence (or `gs_ot_programmes.csv.gz`) is available.

## Sponsor groups

| Where | Groups | Rule |
|---|---|---|
| Programme panel (`build_panel26.py`, `sponsors.py`) | Top-20 pharma; industry small (≤ 5 drugs), mid (6–30), large (> 30); academic/other; government | Top-20 = largest companies by 2023 pharmaceutical revenue, matched by regular expression; an acquired company counts as the parent only for trials that started in or after the acquisition year. Other industry sponsors are sized by the number of distinct parent drugs their normalised name leads across all Open Targets trial records. |
| Trial stops (`rq2_stops.py`) | Top-20 pharma; industry small (≤ 20 trials), mid (21–200), large (> 200) | Size = number of interventional drug trials the normalised lead-sponsor name has ever led on ClinicalTrials.gov. |

Sponsor size is the main grouping. SEC Form D private placements add a direct, dated signal of private financing
(see below).

## Models

Logistic regressions with standard errors clustered by drug (`robust26.py`), on programmes and phase entries in
indications with genetic insight.

* **Selection (H1).** Programme level: ex-ante genetic support at the first trial ~ sponsor tier + first-trial
  period + therapeutic area + modality.
* **Advancement (H3).** Phase-entry level: advanced ~ ex-ante support + sponsor tier + phase + entry period + area +
  modality, then with a support × tier interaction.
* **Mediation (H2).** Karlson–Holm–Breen decomposition of the tier gap in advancement through ex-ante support
  (`khb26.py`).

**Convergence.** A control category with no or almost no events makes a logit quasi-separated: its coefficient drifts
towards minus infinity and the optimiser never reports convergence, although the coefficients of interest are stable
to three or four decimals. Every logit in the pipeline is checked with `factcheck/convergence_audit.py`; where a
sample has such categories (the novel-drug, trial-level H4, SBIR and stop-rate models), nominal controls with fewer
than three events are pooled into "other" and sparse start-period bins are merged into the next bin
(`pilot/pooling.py`), and any fit that still fails to converge is flagged in the output.

## Trial stops around the 2022 funding downturn (`rq2_stops.py`, `rq2_rr.py`, `stopreasons.py`)

`why_stopped` texts of terminated, withdrawn and suspended industry drug trials are classified by a keyword
classifier (v4). One label per text, first match in this order: no funding; safety / benefit-risk; efficacy /
futility; COVID-19; enrolment; M&A / licensing; business / strategic; sponsor decision, unspecified. Negated or
neutral mentions ("not due to safety", "no safety concerns", "safety committee") are removed before matching.
*Financial or strategic* = no funding, M&A / licensing or business / strategic. v4 (7 Nov 2026) adds patterns for
business stops that v3 left unclassified (management or company decisions, programmes discontinued, withdrawn
support, wind-downs, expired grants), found by cross-checking v3 against the Open Targets StopReasons predictions.
Every pattern must match at least one text outside the 200 held-out texts (in the 400 tuning texts or in the
StopReasons file), so that the held-out score is not tuned to the held-out set; `factcheck/stopreasons_support.py`
checks this for every alternative of every pattern (validation in [results](results.md)).

Rates are stops per 1,000 active trial-years (each trial at risk adds one trial-year per calendar year). Rate ratios
compare 2022–25 with 2016–21, with Poisson confidence intervals: log RR ± 1.96 √(1/a + 1/b).

## NIH SBIR/STTR linkage (`sbir_link.py`, `sbir_models.py`)

Industry lead sponsors are matched to NIH RePORTER SBIR/STTR awardees: exact match of normalised names, then
fuzzy match (RapidFuzz `token_sort_ratio` ≥ 92) within blocks that share the first token. Every match is written
out for review; matches that differ by more than a legal form need an explicit decision in `pilot/sbir_decisions.csv`.
A sponsor counts as SBIR/STTR-funded before a trial if its first award year precedes the trial's start year.

## SEC Form D private placements (`fetch_formd.py`, `formd_link.py`, `formd_models.py`)

Form D is the notice a company files with the SEC after selling securities in a private placement. The quarterly
Form D data sets (2009 Q1 onwards) are filtered to offerings whose industry group is Biotechnology, Pharmaceuticals
or Other Health Care and that are not pooled investment funds, then joined to the filing date and the primary issuer.
Candidate names are the issuer's name at filing time and up to six previous names (on the filing and in EDGAR);
CIKs are normalised because the source pads them inconsistently, and EDGAR state markers such as "/DE/" are removed.
Sponsors are matched to names with the same rules as the SBIR/STTR linkage. A name counts as the sponsor's own if it
equals the sponsor's name after removing legal forms, or is accepted in `pilot/formd_decisions.csv` (each decision
carries a reason); several own names are pooled.

**Dating.** The sponsor's first private placement is the earliest Form D filed by its legal entity (CIK) under any
name, because most name changes in EDGAR are renames. When the sponsor's name appears under more than one CIK, the CIK
that first filed under that name is the original company and keeps its whole history; any other CIK with the name
(usually a listed shell adopted by reverse merger) contributes only filings under the sponsor's own or later names.
Two bounds are reported as sensitivity: own and later names only (`formd_first_year_own`) and every filing of every
own CIK (`formd_first_year_cik`). The selection is deterministic (ties broken by filings, first year and CIK).

**US-only comparison.** Only issuers raising money in the US file Form D, so sponsors are classified as US,
non-US or unknown (`sponsor_region.py`): US or foreign location in the financing records (Form D state, SBIR), else a
legal form or place name pointing abroad (GmbH, AG, SA, Ltd, Co. Ltd., Shanghai, India, …), else a US legal form
(Inc, LLC, Corp, Company); the rest are unknown and left out. `formd_models.py` repeats the selection and advancement
models for US sponsors only.

`formd` = the lead sponsor's first Form D is dated in a calendar year before the trial's start year. Because the data
start in 2009, the Form D models use programmes and phase entries from 2010 onwards. In the selection models,
therapeutic areas with fewer than three supported programmes are pooled into "other" to avoid separation.

**Amount raised.** Filings are folded into offerings: an amendment (Form D/A) restates the offering it amends, so
each chain of filings linked by `PREVIOUSACCESSIONNUMBER` is one offering, dated by its first filing, with the amount
sold taken from the latest filing (amendments report the cumulative amount). Every offering in a sponsor's history
under the main dating rule is listed in `results/formd_sponsor_offerings.csv.gz`. For each programme or phase entry
the amounts sold in the sponsor's offerings dated before the trial year are summed (nominal US dollars, no deflation)
and banded: no prior Form D, under $10M, $10–50M, $50M or more. `formd_models.py` fits the selection and advancement
models with the bands (reference: no prior Form D) and, among filers, with log10(1 + millions raised); two
sensitivities repeat the band models with equity offerings only (no debt-only offerings, no business combinations)
and with amounts in 2024 dollars (CPI-U, `results/cpi_u_annual.csv`).

The extract used for the published results is on the `formd-data` branch (`data_formd/`), with the fetch log.

## Reference date

Trials count as started if their start date is on or before 17 October 2026, the date of the Open Targets download
and ClinicalTrials.gov snapshot (`PILOT_ASOF` in `build_panel26.py` and `rq2_stops.py`). Without a fixed date the
panel changed with the day the script was run, because trials registered with a future start date enter as the
calendar advances (91 reports between 17 October and 6 November 2026).

## Known limitations

* Form D marks private placements, not venture capital as such: some venture rounds are never filed, some filers are
  not venture-backed, and only issuers raising money in the US file. "No prior Form D" therefore mixes non-US
  sponsors with US sponsors that raised no private money; the US-only comparison above (`sponsor_region.py`, a
  name-based heuristic that leaves 20% of programmes unclassified) gives the same answer for selection and
  advancement and no support × Form D interaction.
* Most approval records carry no date, so an approval that preceded a phase entry can count as advancement; the
  dated variants above bound the effect (genetic premium 2.48 → 2.53 when such approvals are removed, 2.25 with trials
  only).
* Registry programmes include investigator-initiated trials of marketed drugs; levels of relative success are therefore
  not comparable with Pharmaprojects-based estimates (pilot RS 4.0–4.2 vs 2.16).
* Ex-ante support uses association years; OMIM rows (undated) are treated as ex ante, with a no-OMIM sensitivity and
  a parallel measure from Open Targets evidence dated by Falaguera et al. (2026), reported for every model. Where the
  two measures disagree (H4), the paper reports both.
* The stop-reason reference labels are an LLM-assisted first pass, not yet blind double-coded by the author.
* A sponsor that went public through a reverse merger and never filed a Form D under its own name inherits the listed
  shell's earlier placements; the own-names-only bound shows how much this can matter.
