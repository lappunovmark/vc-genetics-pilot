# Roadmap

## Next steps
1. **Blind double-coding of the stop-reason labels.** The 200 held-out `why_stopped` texts that validate the
   stop-reason classifier were first labelled with LLM assistance. The author will code the same texts blind (without
   the first-pass labels or the classifier output) and report the agreement between the two sets of labels and the
   classifier's accuracy, Cohen's κ, and the precision and recall of the financial-or-strategic class against the
   blind labels. The coding sheet, codebook and scoring script are in
   [`factcheck/double_coding/`](../factcheck/double_coding/codebook.md); the validation figures in
   [results](results.md) will then refer to the author's labels.
2. **Investor-level data on private rounds after 2015.** Investors are named for venture rounds up to 2015 (a
   Crunchbase export) and, for sponsors that went public, above 5% (Schedules 13D and 13G; the holders listed in
   IPO prospectuses, read for 344 sponsors of 2003–2026). For sponsors that stayed private after 2015 the pilot has
   only Form D placements, directors named in Form D filings and sponsor size. Round-level data with named
   investors from a licensed deal database would test the same questions for them and give the comparison of
   corporate and independent investors enough cases.
3. **A top-20 list fixed year by year.** The top-20 group is defined by 2023 sales, after the programmes studied.
   With the group fixed by 2010 sales the result on programme starts after the publication of genetic evidence
   holds (0.56, 0.38–0.82; `docs/plan_top20_2010.md`), but eighteen of the twenty companies are the same and
   acquisitions after 2010 still move programmes into the group. A list fixed before each period, with licensing
   and acquisitions followed programme by programme, is still needed before the result is read as behaviour of
   large companies.
4. **Working paper.** The pilot is being written up: question, data, definitions ([methods](methods.md)), results
   for H1–H4, robustness and limitations.

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

* **Further venture markers** (`pilot/cb_models.py`, `pilot/ritter_models.py`, `pilot/formd_directors.py`,
  `pilot/vc_combined.py`): venture rounds in a 2015 Crunchbase export, venture-backed IPOs, venture investors on
  the board in Form D filings and a flag that combines the four sources; corporate against independent investors
  (`pilot/cvc_models.py`); trial stops by venture backing (`pilot/vc_stops.py`).
* **The selection gap by type of drug and by direction of effect** (`pilot/h1_by_modality.py`,
  `pilot/direction_models.py`).
* **Programme starts around the publication of genetic evidence** (`pilot/evidence_arrival.py`), repeated on Open
  Targets 26.09 evidence and split by venture backing under plans committed before the runs, with the checks added
  afterwards (concentration by gene and company, comparison within a target, the target as the unit).
* **Cash runway of public sponsors and trial stops** (`pilot/fetch_sec_frames.py`, `pilot/cash_runway.py`), planned
  before the data were downloaded.
* **Investors named in IPO prospectuses** (`pilot/fetch_ipo_prospectus.py`, `pilot/ipo_holders.py`,
  `pilot/ipo_models.py`): the holders of more than 5% before the offering, read from 344 prospectuses of 2003–2026
  and classed by hand-written rules, under a plan written before the download.
* **The sponsor's financing stage in the year of the trial** (`pilot/vc_stage.py`): private and venture-backed,
  public after venture backing, public without a venture marker, dated from the IPO year, Crunchbase rounds and
  Form D boards, under a plan written before the run. Still open: the date of the first sale of preferred stock,
  which a rule could not read reliably from the prospectuses and would have to be read by hand.
* **Sponsor names as they stood in April 2015** (`pilot/extract_ictrp_2015.py`, `pilot/sponsor_2015.py`): the
  selection and advancement results do not depend on records moved between sponsors after April 2015; planned
  before the download.

Corrections to earlier results are listed at the end of [results](results.md).
