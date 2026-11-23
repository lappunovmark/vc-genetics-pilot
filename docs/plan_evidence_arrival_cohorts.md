# Plan: the evidence-arrival contrast with clean controls, cohort by cohort (written before the run)

Written on 23 November 2026, before any model of this kind was fitted.

**Why.** The contrast D1 of `evidence_arrival.py` (other industry sponsors against top-20 pharma after genetic
evidence on a target–indication pair is published: 0.54, 0.34–0.84, on Open Targets GWAS evidence) is a Poisson
model with pair × group and year × group fixed effects on all pairs and years. Evidence arrives in different
years for different pairs. In such a design a pooled two-way fixed-effects model also compares pairs that gained
evidence late with pairs that gained it earlier, and it can be biased when the response differs between cohorts
or grows with time (Goodman-Bacon 2021; Sun and Abraham 2021; Baker, Larcker and Wang 2022). A stacked design
removes these comparisons (Cengiz et al. 2019): each cohort is compared only with pairs that never gained
evidence, inside a window around its own evidence year.

**What had been seen.** Every block of `evidence_arrival_ot_gwas.txt`, including the event study of the contrast
(D6) and the checks added after the first runs. No stacked or cohort-specific model had been fitted.

**Design.** The pair-year panel of the planned run on Open Targets GWAS evidence is taken as it is. For each
evidence year *e*, a stack holds the pairs whose evidence year is *e* and the pairs never supported, in the years
*e* − 5 to *e* + 5 (within 2000–2025). The stacks are put together and the model of D1 is fitted with the fixed
effects made specific to the stack: programme starts of top-20 pharma and of other industry sponsors on
`post`, the evidence year itself, and their interactions with the group, with pair × group × stack and year ×
group × stack fixed effects; errors clustered by indication, which also covers the repeated use of the control
pairs. A pair-group without a start inside the window of its stack drops out, as in any Poisson model with
fixed effects.

**Primary estimate.** The coefficient of `post` × other industry: the ratio of the two responses.

**Secondary.** Windows of 3 and of 8 years; the response of each group in the stacked model; the primary model
separately for evidence years to 2015, 2016–2019 and from 2020.

**Reading rule, fixed in advance.** If the interval of the primary estimate lies below 1, the contrast does not
depend on comparisons between cohorts. If it includes 1, the contrast of D1 is not robust to the estimator, and
the paper says so. Either way all estimates are reported.

**Limits.** The window shortens the period after the evidence, so the estimate is about the first five years;
cohorts near the ends of the panel have shorter windows; the checks that limit the reading of D1 (concentration
in a few genes, the comparison within a target, the top-20 group being defined by later sales) are not addressed
by this run.
