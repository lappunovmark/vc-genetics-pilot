# Plan: what the genetic premium is worth in clinical cost (an illustration; written before the calculation)

Written on 24 November 2026, before any cost was computed.

**Why.** The paper reports the premium for genetic support as an odds ratio of advancing to the next phase. Readers
outside the field ask what it means in programmes and in money: how many phase 1 programmes it takes to get one
approval with and without genetic support, and what the clinical trials for one approval cost.

**What had been seen.** The phase-by-phase advancement rates by support, unadjusted (`robust_benchmark.csv`,
`robust_benchmark_variants.csv`); for industry sponsors, 0.75, 0.48 and 0.53 with ex-ante support against 0.39,
0.26 and 0.34 without. The direction and rough size of the result are therefore known. This is arithmetic on rates
of that kind and on published costs, not a test, and it is reported as an illustration.

**Sample.** Phase entries of industry sponsors in indications with genetic insight, entry years 2000 to six years
before the end of the data, without an earlier trial of the programme in a higher phase: the sample of the
advancement model, industry sponsors only, because the cost figures are industry costs.

**Rates.** For each phase, a logit of advancement on ex-ante support, sponsor class, entry period, therapeutic area
and modality. The rate with support is the mean predicted probability over all entries of the phase with support
switched on, the rate without is the same with support switched off. Both rates therefore refer to the same mix of
programmes. Advancement from phase 3 is approval (or a phase 4 trial).

**Costs.** DiMasi, Grabowski and Hansen (2016), Table 2: mean out-of-pocket cost per investigational compound that
enters the phase, 25.3, 58.6 and 255.4 million 2013 dollars for phases 1, 2 and 3. The same costs are assumed with
and without genetic support.

**Quantities, with and without support.** The probability that a programme entering phase 1 is approved (the
product of the three rates); the number of phase 1 programmes per approval; the expected clinical cost per
programme entering phase 1 (cost of phase 1, plus the cost of phase 2 times the chance of reaching it, plus the
cost of phase 3 times the chance of reaching it); the clinical cost per approval (the expected cost divided by the
probability of approval); the ratio and the difference between the two. Intervals: percentile intervals from
1,000 bootstrap resamples of drugs (the rates are re-estimated in each; the costs are held fixed).

**Sensitivity.** Unadjusted rates; advancement and earlier trials counted in similar indications
(`advanced_sim`); the drug's first indication only, which is closest to the unit of the cost study (a new
compound).

**How it is reported.** As an illustration. The ratio between supported and unsupported programmes is the figure
to quote; dollar amounts are given as "under the costs of DiMasi et al." and scale one to one with the cost
figures, which other studies put lower (Sertkaya et al. 2024).

**Limits.** The premium is an association, not the effect of choosing a supported target. Advancement is read from
the registry for a drug–indication pair and is lower than the phase success that companies report for a compound,
so the cost per approval comes out too high for both groups; the ratio is less affected. Costs come from
self-originated compounds of ten large firms and exclude preclinical work and the cost of capital. Few supported
programmes enter the sample in phase 1 (95), so intervals are wide. Most approval records carry no date.
