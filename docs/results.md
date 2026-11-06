# Pilot results in detail

Open Targets Platform 26.09 and ClinicalTrials.gov snapshot of 17 October 2026. Pilot results, not peer-reviewed.
Model output is in `results/` ([data dictionary](data_dictionary.md)); definitions are in [methods](methods.md).

## Estimates
* 35,887 drug × MeSH-indication programmes; 29,199 in indications with genetic insight.
* Ex-ante genetic support at phase entry: OR 2.48 (2.10–2.93) for advancing a phase; no difference between small
  industry sponsors and top-20 pharma (interaction OR 1.26, 0.75–2.12).
* Small industry sponsors start fewer programmes with ex-ante support (adjusted OR 0.64, 0.46–0.88), not significant
  for novel drugs (0.79, 0.49–1.29).
* Financial or strategic trial stops per 1,000 active trial-years rose 2.1–2.6-fold from 2016–21 to 2022–25 in every
  industry group. Among small sponsors, stops citing lack of funding rose 2.45-fold (1.57–3.82); in the other groups
  such stops are rare.
* Trials stopped for financial or strategic reasons carried no more, and probably less, ex-ante genetic support than
  completed trials (9.0% vs 10.4%; adjusted OR 0.75, 0.53–1.04), most clearly in trials that ended in 2022 or later.
  Without undated OMIM evidence the overall gap is not significant (OR 0.86, 0.61–1.22).
* Prior NIH SBIR/STTR funding of the sponsor is not linked to ex-ante support (OR 0.72, 0.38–1.39).
* SEC Form D: 40,995 private offerings by biotech, pharma and other health care issuers (2009 Q1–2026 Q3); 784 of
  2,964 non-top-20 industry sponsor names matched to an issuer (66 of them after hand review, 27 candidate matches
  rejected). Among programmes first trialled in 2010 or later, sponsors with a prior Form D started genetically
  supported programmes no more often (3.4% vs 5.9%; adjusted OR 0.66, 0.41–1.05) and advanced no more often
  (adjusted OR 0.88, 0.71–1.09); genetic support predicted advancement in both groups (interaction OR 1.58,
  0.75–3.30).

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
  ([#2](https://github.com/lappunovmark/vc-genetics-pilot/issues/2)), so these figures may change.

## Corrections
* 19 Oct 2026: ClinicalTrials.gov mixes `YYYY-MM` and `YYYY-MM-DD` dates; pandas 2 without `format='mixed'` dropped
  38% of start dates and 41% of completion dates in `rq2_stops.py`. Fixed; the trial-stop and H4 results were re-run
  (numbers above are corrected). The Open Targets panel (H1–H3) was not affected: its dates are typed.
