# Pilot results in detail

Open Targets Platform 26.09 and ClinicalTrials.gov snapshot of 17 October 2026. Pilot results, not peer-reviewed.
Model output is in `results/` ([data dictionary](data_dictionary.md)); definitions are in [methods](methods.md).

## Estimates
* 35,887 drug × MeSH-indication programmes; 29,199 in indications with genetic insight.
* Ex-ante genetic support at phase entry: OR 2.48 (2.10–2.93) for advancing a phase; no difference between small
  industry sponsors and top-20 pharma (interaction OR 1.26, 0.75–2.12).
* Small industry sponsors start fewer programmes with ex-ante support (adjusted OR 0.64, 0.46–0.88), not significant
  for novel drugs (0.79, 0.49–1.29).
* Approval dates: 1,205 of 26,542 phase entries advance through an approval alone; 619 of these approvals can be dated
  (EMA or PMDA report, else ChEMBL first approval) before the entry year and are probably approvals that preceded the
  trial. Removing them leaves the genetic premium at OR 2.53 (2.12–3.01); counting only dated approvals gives 2.50
  (2.10–2.98); trials only, 2.25 (1.87–2.69). The small-sponsor interaction stays non-significant (1.50, 0.89–2.54).
* Financial or strategic trial stops per 1,000 active trial-years rose 2.1–2.6-fold from 2016–21 to 2022–25 in every
  industry group. Among small sponsors, stops citing lack of funding rose 2.45-fold (1.57–3.82); in the other groups
  such stops are rare.
* Trials stopped for financial or strategic reasons carried no more ex-ante genetic support than completed trials
  (9.0% vs 10.4%; adjusted OR 0.75, 0.53–1.04, most clearly in trials that ended in 2022 or later). Whether they
  carried less depends on the measure: without undated OMIM evidence the overall gap is not significant (OR 0.87,
  0.61–1.23), and with the independent measure built from Open Targets germline evidence dated by Falaguera et al.
  there is no gap at all (11.0% vs 11.5%; OR 0.88, 0.64–1.22; trials ending 2022 or later OR 1.02, 0.70–1.49).
* Prior NIH SBIR/STTR funding of the sponsor is not linked to ex-ante support (OR 0.72, 0.38–1.39; with the dated
  Open Targets measure 0.83, 0.49–1.41).
* SEC Form D: 40,995 private offerings by biotech, pharma and other health care issuers (2009 Q1–2026 Q3); 801 of
  2,964 non-top-20 industry sponsor names matched to an issuer (751 on identical names up to legal form, 50 accepted
  after hand review; 15 candidate matches not used). Among programmes first trialled in 2010 or later, sponsors with
  a prior Form D started genetically supported programmes no more often (4.0% vs 5.7%; adjusted OR 0.74, 0.48–1.14)
  and advanced no more often (adjusted OR 0.88, 0.72–1.09). Genetic support predicted advancement in both groups and,
  in this version of the linkage, more strongly among Form D filers (interaction OR 2.12, 1.10–4.10); the interaction
  was 1.58 (0.75–3.30) before the linkage fixes of 6 November 2026, so it should be read as fragile. Dating the first
  Form D by own names only gives OR 0.77 (0.50–1.20) for selection and 0.91 (0.73–1.14) for advancement; the
  whole-CIK dating changes no flag in the analysis window. With the dated Open Targets measure the selection OR is
  0.73 (0.46–1.17). Restricting both groups to sponsors classified as US-based (`pilot/sponsor_region.py`: US
  financing records, else legal form and place names; 1,990 programmes, 47% with a prior Form D) gives OR 0.89
  (0.51–1.56) for selection, 0.89 (0.69–1.17) for advancement and an interaction of 0.89 (0.37–2.12), so the
  significant interaction in the full sample reflects the mix of US and non-US sponsors among non-filers.
* Amount raised: summing the amounts sold in the sponsor's Form D offerings before the first trial (3,060 offerings of
  the 801 linked sponsors, median $6.0M) shows no dose–response. Programmes of sponsors that had raised under $10M,
  $10–50M and $50M or more had ex-ante support in 4.2%, 4.8% and 3.2% of cases against 5.7% without a prior Form D
  (adjusted OR 0.75, 0.39–1.44; 1.11, 0.59–2.08; 0.51, 0.23–1.11); among filers, each tenfold increase in the amount
  raised changes the odds of support by 0.85 (0.56–1.30). Advancement does not rise with the amount either (0.92,
  0.72, 1.02 for the three bands; log-linear 1.12, 0.85–1.48 among filers).

## Validation
* `gensup.py` reproduces all 1,258 genetically supported target–indication pairs in Minikel et al.'s data exactly
  (OMIM, OTG, PICCOLO and Genebass evidence; commit b84cf05; no pairs missing or added).
* Genetic insight for indications outside their set: the approximation agrees with their label for 96.6% of their
  1,013 indications with a MeSH ID.
* Replication note: in their data, the Phase I→launch RS computed as the product of phase-wise RS, as described in
  their Methods (1.076 × 1.571 × 1.275), is 2.16, while the ratio of launch shares among programmes entering phase I
  is 2.63, close to the headline 2.6. Both are reported in `results/robust.txt` for comparison.
* Stop-reason classifier v3 (provisional): 83.0% agreement with reference labels on 200 held-out texts (Cohen's
  κ 0.79); financial or strategic class precision 0.91, recall 0.86. The reference labels in
  `results/rq2_hand_labels.csv` are an LLM-assisted first pass that has not yet been blind double-coded by the author
  ([#2](https://github.com/lappunovmark/vc-genetics-pilot/issues/2); the coding sheet, codebook and scoring script
  are in `factcheck/double_coding/`), so these figures may change.

## Corrections
* 6 Nov 2026: results depended on the run date. `build_panel26.py` counted a trial as started if its start date was
  not later than *today*, so trials registered with a future start date entered the panel as the calendar advanced
  (35,896 programmes on 6 November instead of 35,887). The reference date is now fixed at 17 October 2026 (the data
  snapshot), which reproduces the published panel exactly. `rq2_stops.py` uses the same date for its year range.
* 6 Nov 2026: Form D linkage. When several issuers shared a normalised name, the one kept was decided by an unstable
  sort, so results differed between runs (5 sponsors); CIK zero-padding split some issuers in two; and a namesake with
  more filings could displace the issuer with the sponsor's exact name (12 sponsors wrongly left unmatched, e.g.
  Prevail Therapeutics matched to Prevail Holdings). The linkage is now deterministic, prefers exact names, pools
  same-company issuers and dates placements as described in `docs/methods.md`. Accepted matches 784 → 801; selection
  OR 0.66 (0.41–1.05) → 0.74 (0.48–1.14); advancement OR 0.88 (0.71–1.09) → 0.88 (0.72–1.09); the support × Form D
  interaction 1.58 (0.75–3.30) → 2.12 (1.10–4.10). Conclusions unchanged.
* 19 Oct 2026: ClinicalTrials.gov mixes `YYYY-MM` and `YYYY-MM-DD` dates; pandas 2 without `format='mixed'` dropped
  38% of start dates and 41% of completion dates in `rq2_stops.py`. Fixed; the trial-stop and H4 results were re-run
  (numbers above are corrected). The Open Targets panel (H1–H3) was not affected: its dates are typed.
