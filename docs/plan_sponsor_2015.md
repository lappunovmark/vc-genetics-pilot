# Plan: sponsor names as they stood in April 2015 (written before the file was downloaded)

Written on 23 November 2026, before the 2015 copy of the registry was downloaded or opened.

**Why.** Sponsor groups rest on the names in ClinicalTrials.gov on the snapshot date (17 October 2026). When a
company is acquired, the record of an old trial may be moved to the acquirer's name, and the trial then counts
as the acquirer's. The rules in `pilot/sponsors.py` handle renamed subsidiaries with their acquisition years, but
not records moved outright, and the list of acquisitions covers the deals met in the data. The registry's own
history of record versions would settle this, but its endpoint refuses requests from scripts (HTTP 403 on 23
November 2026), and the monthly archives of AACT need an account. An open copy of the WHO International Clinical
Trials Registry Platform retrieved in the first week of April 2015 (van Valkenhoef, Zenodo,
doi:10.5281/zenodo.46392, CC0) holds the ClinicalTrials.gov records of that date with their primary sponsor.

**What it can show.** Only trials registered by April 2015, and only changes of the sponsor name between April
2015 and October 2026. A record moved before April 2015 looks the same in both.

**Measures.** For every trial of the registry snapshot found in the 2015 copy, the primary sponsor of 2015 and the
lead sponsor of 2026 are normalised with the function used throughout (`rq2_stops.norm_sponsor`) and typed as
top-20 pharma or not with `sponsors.top20_parent` for the trial's start year.
1. The share of trials whose normalised name changed.
2. Among industry trials typed top-20 pharma today, the share not typed top-20 under the 2015 name ("moved in"),
   and the reverse ("moved out"); the same for the first trials of programmes and for phase-entry trials.
3. The names behind the moves, listed by frequency, so that each can be read.

**Re-estimation.** The headline selection model (`robust.txt`, "H1 gs_ante_first: + first-trial period, area,
modality": the coefficient of small sponsors against top-20 pharma) is fitted again (a) without the programmes
whose first trial moved in or out, and (b) with those programmes given the group of the 2015 name where that name
is typed in the current data, and left out where it is not. The advancement model with the support × tier
interaction is fitted again in the same two ways on phase entries.

**Reading rule, fixed in advance.** The counts are descriptive. If under (a) or (b) the interval of the
small-sponsor coefficient changes from excluding 1 to including it, or the reverse, the selection result depends
on records moved between sponsors after April 2015, and the paper says so; otherwise it does not depend on them.
Either way the estimates are reported.

**Not covered.** Trials registered after April 2015; moves before April 2015; the evidence-arrival result for
top-20 pharma, which is left for a separate run.
