# Plan: do venture-backed sponsors respond to published genetic evidence? (written before the analysis was run)

Written on 18 November 2026, after the run described in `plan_evidence_arrival_ot.md` and before any model with
the venture groups was fitted.

**Question.** After GWAS evidence for a target × indication pair is published, top-20 pharma start more programmes
on the pair and other industry sponsors do not (`results/evidence_arrival_ot_gwas.txt`). Is that also true of the
industry sponsors that are venture-backed, and do they respond more than the industry sponsors that are not?

**Groups.** Non-top-20 industry sponsors are split by the combined venture flag of `vc_combined.py` (a venture owner
in Schedules 13D/13G, a venture-backed IPO in Ritter's list, a Crunchbase venture round, or a venture investor on
the board in Form D): *venture-backed* (at least one source) and *no venture marker* (all others, which mixes
sponsors without venture money with sponsors about whose financing nothing is known). The flag describes the
sponsor and is not dated; the markers miss between 9% and 23% of venture-backed sponsors where an outside flag
exists.

**Everything else** is as in the run on Open Targets 26.09 evidence: same pairs, evidence (GWAS credible sets with
L2G ≥ 0.5 as the primary set; all germline sources as the secondary set), outcome, models and clustering.

**Primary estimate.** The contrast of venture-backed sponsors against top-20 pharma after the evidence year.

**Secondary.** The contrast of venture-backed sponsors against industry sponsors without a venture marker; the
response of each group on its own; the contrast of sponsors without a marker against top-20 pharma; the placebo of
the primary contrast; the same on all germline sources.

**Reading rule, fixed in advance.** If the primary contrast is below 1 with an interval that excludes 1,
venture-backed sponsors respond less than top-20 pharma. If the interval includes 1, the data do not separate the
two. The comparison with sponsors without a marker is read the same way and answers whether venture backing goes
with a stronger response than that of other industry sponsors. All estimates are reported whatever they show.
