# Plan: did the response to new genetic evidence change after 2015? (exploratory; written before the run)

Written on 24 November 2026, before any model with a before/after term was fitted.

**Why.** In 2015 Nelson et al. showed that drug mechanisms with human genetic support are approved about twice as
often. A natural question is whether sponsors then began to react more strongly to new genetic evidence. The paper
has the design to ask it (programme starts on a target–indication pair before and after genetic evidence on the
pair is published) but had not asked it.

**What had been seen: this is why the analysis is exploratory.** The cohort-by-cohort models of
`evidence_arrival_ot_gwas_cohorts.txt`. For top-20 pharma the response was 1.42 (0.75–2.71) for evidence years to
2015, 2.35 (1.55–3.58) for 2016–2019 and 0.66 (0.28–1.59) from 2020; the ratio of other industry to top-20 pharma
was 0.50, 0.47 and 2.21. The direction of a before/after comparison could therefore be guessed. What had not been
computed is the comparison itself with its interval, for all industry sponsors together or by group. No reading
rule can make this confirmatory; the result is reported as exploratory whatever it shows.

**Design.** The stacked design of `docs/plan_evidence_arrival_cohorts.md`, unchanged: Open Targets GWAS evidence,
one stack per evidence year with the pairs of that year and the pairs never supported, years *e* − 5 to *e* + 5,
pair × group × stack and year × group × stack fixed effects, errors clustered by indication. Added: the
interaction of `post` (and of the evidence year itself) with `late`, an indicator of evidence years from 2016.

**Primary estimate.** The coefficient of `post` × `late` in the model with both industry groups and a common
response: the ratio of the response of programme starts to evidence published from 2016 over the response to
evidence published to 2015. All evidence years are used, so the cohorts from 2020, which looked weaker, count
against a rise.

**Secondary.** The same ratio for top-20 pharma and for other industry sponsors (model with group interactions);
evidence years to 2020 only (the last cohort with five full years after the evidence); the cut at 2017 instead of
2016 (trials planned in 2015 start later); a window of 8 years.

**Descriptive table (not a test).** The share of new programmes with ex-ante genetic support by period of the
first trial, for top-20 pharma and for other industry sponsors. The stock of genetic evidence grows every year, so
this share rises for mechanical reasons and cannot show learning by itself; it is reported for context only. The
selection models by period had been seen (`top20_2010.txt`).

**Reading.** If the interval of the primary estimate excludes 1, the data are consistent with a change in the
response after 2015, as an exploratory finding to be confirmed on other data. If it includes 1, the data do not
show a change, and the width of the interval says how large a change they could have missed.

**Limits.** Few pairs gained evidence before 2016 (174 of 1,393), so the comparison is imprecise; the window covers
the first five years after the evidence, and for cohorts from 2021 fewer; a stronger response after 2015 could
also come from better evidence (larger studies, better gene assignment) and not from sponsors learning; the
limits of the evidence-arrival design listed in the earlier plans apply.
