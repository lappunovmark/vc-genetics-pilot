# Plan: evidence arrival with Open Targets 26.09 evidence (written before the analysis was run)

Written on 18 November 2026, before `evidence_arrival.py` was run on the evidence described here.

**Why.** The first version of this analysis (`results/evidence_arrival.txt`) used the associations of Minikel et al.
(dated to 2022) and had 822 pairs that gained evidence. Its main contrast (programme starts of other industry
sponsors against top-20 pharma after the evidence year: 0.60, 0.37–0.95) was fragile. Open Targets 26.09 dates its
evidence itself and runs to 2026, so the same design can be repeated on a larger and partly newer set of evidence.

**What stays the same.** The code, the unit (target × indication pair with a programme started in 2000–2025 in an
indication with genetic insight), the outcome (programme starts per pair and year by sponsor group), the models
(Poisson with pair and year fixed effects; the contrast with pair × group and year × group effects; errors clustered
by indication), the MeSH similarity rule (≥ 0.8) and the placebo and lead checks.

**What changes.** Only the evidence table: gene × disease × source × earliest evidence year from Open Targets 26.09
(`extract_ot_dated.py`), mapped to MeSH with the panel's disease map. Pairs whose only supporting evidence carries
no date are left out, as pairs with OMIM support were.

**Primary analysis.** Evidence = GWAS credible sets with L2G ≥ 0.5 (population genetics, where the selection gap
sits). Estimate = the contrast D1: other industry sponsors against top-20 pharma after the evidence year.

**Secondary.** The same contrast with all germline sources; with area × year effects; clustered by gene; small
sponsors and mid-sized or large sponsors separately; pairs where both groups started programmes; novel programmes
only; leads; placebo.

**Reading rule, fixed in advance.** If the primary contrast is below 1 with an interval that excludes 1, the first
result is taken as repeated on the new evidence. If the interval includes 1, the first result is reported as not
repeated, whatever the point estimate. Both versions are reported in full either way.
