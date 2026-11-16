# Roadmap

## Next steps
1. **Blind double-coding of the stop-reason labels.** The 200 held-out `why_stopped` texts that validate the
   stop-reason classifier were first labelled with LLM assistance. The author will code the same texts blind (without
   the first-pass labels or the classifier output) and report the agreement between the two sets of labels and the
   classifier's accuracy, Cohen's κ, and the precision and recall of the financial-or-strategic class against the
   blind labels. The coding sheet, codebook and scoring script are in
   [`factcheck/double_coding/`](../factcheck/double_coding/codebook.md); the validation figures in
   [results](results.md) will then refer to the author's labels.
2. **Investor-level data on private rounds.** Venture backing is seen directly only for sponsors that later became
   public (owners in SEC Schedules 13D and 13G); for private sponsors the pilot relies on Form D placements and
   sponsor size. Round-level data with named investors would test the same question for private sponsors.
3. **Working paper.** Write up the pilot: question, data, definitions ([methods](methods.md)), results for H1–H4,
   robustness and limitations.

## Done since the first release
* **SEC Form D private placements linked to trial sponsors** (`pilot/fetch_formd.py`, `pilot/formd_link.py`,
  `pilot/formd_models.py`, `pilot/formd_stops.py`), with every match written out for review.
* **Dated Open Targets evidence** (Falaguera et al.) reported next to the main support measure in every model
  (`pilot/gs_ot_dated.py`). The main measure is unchanged; which of the two should be the headline measure is open.
* **Approval dates**, so that an approval that preceded a phase entry does not count as advancement
  (`pilot/fetch_chembl_approval.py`, `pilot/approval_dates.py`).
* **Owners of public sponsors** from SEC Schedules 13D and 13G, with hand-reviewed name matches and investor classes
  (`pilot/fetch_edgar_owners.py`, `pilot/owners_link.py`, `pilot/owners_models.py`).
* **Exploratory checks behind the small-sponsor gap in selection** (`pilot/h1_mechanisms.py`): type of evidence,
  novel and follow-on indications, partnerships, trial size, capital and acquisitions.

Corrections to earlier results are listed at the end of [results](results.md).
