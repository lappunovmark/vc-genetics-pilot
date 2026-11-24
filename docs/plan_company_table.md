# Plan: genetic support of the programmes of each top-20 company (written before the run)

Written on 24 November 2026, before support was tabulated by company.

**Why.** The paper compares classes of sponsor. Readers ask the next question: which of the twenty largest
companies start programmes with genetic support most often. No open table of this kind was found.

**What had been seen.** The selection model with each top-20 company left out in turn (0.65 to 0.71). Shares by
company had not been tabulated.

**Sample.** Programmes in indications with genetic insight whose first trial started in 2001 or later and whose
first sponsor is typed top-20 pharma, attributed to the parent company by the rules of `pilot/sponsors.py` for the
year of the first trial.

**Measures, per company.** The number of programmes, the number with ex-ante genetic support, the share with a
Wilson 95% interval, and the ratio of observed to expected supported programmes. Expected is the sum of the
probabilities from a logit of support on first-trial period, therapeutic area and modality fitted on all top-20
programmes, so the ratio compares a company with what the group does for the same mix of programmes. The interval
of the ratio is the exact Poisson interval of the observed count divided by the expected count.

**Test fixed in advance.** A likelihood-ratio test of company effects in the logit with the same controls
(companies with fewer than three supported programmes pooled into one level).

**Reading rule.** If the test does not reject equality at 0.05, the table is descriptive: the data do not
distinguish the companies, and no ranking is claimed. If it rejects, the companies whose interval of the ratio
excludes 1 are named as above or below the group. Either way the full table is reported, ordered by the ratio,
with the number of programmes shown so that small numbers are visible.

**Secondary.** The same with first trials from 2010; the same for novel programmes only (the drug's first
indication).

**Limits.** A programme is attributed to the sponsor of its first trial under the name in the registry today, so
acquired and in-licensed programmes count for the company that started the trial; with few supported programmes
per company the intervals are wide; multiple comparisons across twenty companies are not adjusted for.

## Check added after the first run (24 November 2026, written before it was run)

**What had been seen.** The primary and secondary tables above. The primary test rejected equality; the ratios
ranged from about 2 to 0, and four companies had an interval excluding 1, two of them only just.

**Why a check is needed.** The programmes of one drug are not independent: 4,928 programmes belong to 1,463 drugs,
and one drug accounts for up to six supported programmes of a company. The test and the Poisson intervals above
treat programmes as independent, so they overstate what the data can distinguish. The planned block of novel
programmes does not remove this (several indications of a drug can start in the same year).

**The check.** The drug as the unit. One row per drug and company: the drug's programmes in the primary sample that
the company was first to sponsor. Outcome: at least one of them had ex-ante genetic support. Controls: period of
the earliest of these programmes, therapeutic area of the earliest programme (the most frequent area among the
earliest when there are several, then alphabetical order), modality, and the logarithm of the number of programmes
(a drug tested in more indications has more chances of a supported one). The same table (supported drugs,
expected, ratio with exact Poisson interval) and the same likelihood-ratio test, with companies with fewer than
three supported drugs pooled.

**Reading rule.** The drug-level test and intervals decide what is said in the text. A company is named as above
or below the group only if its drug-level interval excludes 1. If the drug-level test does not reject equality at
0.05, no company is named. The programme-level table stays in the output as planned, with this caveat.
