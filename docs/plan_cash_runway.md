# Plan: cash runway before the 2022 downturn and trial stops (written before the data were downloaded)

Written on 18 November 2026, before the SEC data described here were downloaded.

**Question.** Financial and strategic trial stops rose 2.0–2.5-fold after 2022 for every class of sponsor, and
sponsor size, capital raised and venture backing did not separate who was hit. Those are indirect measures of
dependence on new capital. A direct one is how long a sponsor could go on without raising money. Did sponsors that
entered 2022 with a short cash runway stop more trials for financial reasons in 2022–2023, and was that link
stronger than in ordinary years?

**Data.** The SEC's XBRL frames (`pilot/fetch_sec_frames.py`): year-end cash and short-term investments and annual
operating cash flow of every filer, 2017–2022. Sponsors are linked through the EDGAR registrant numbers that
`owners_link.py` already assigned. Public sponsors only.

**Runway.** Liquid assets at the end of the year divided by the cash used in operations during that year, in
years. Liquid assets: the reported total of cash, cash equivalents and short-term investments if a filer reports
it; otherwise cash and cash equivalents plus the first available of short-term investments, current marketable
securities, current available-for-sale debt securities. Sponsors with positive operating cash flow have no runway
and form a separate group. **Short runway: less than 1.5 years.**

**Sample.** Industry Phase 1–3 drug trials of non-top-20 sponsors with a runway at the end of 2021, active on
1 January 2022. Comparison cohort: the same with the runway at the end of 2017 and trials active on 1 January 2018.

**Outcome.** The trial was stopped for a financial or strategic reason (classifier v4) within the two following
calendar years (2022–2023; comparison cohort 2018–2019). Secondary: any stop; stops that cite lack of funding.

**Models.** Logit of the outcome on short runway, with phase, start period and the sponsor's size band; errors
clustered by sponsor. Primary estimate: the odds ratio of short runway in the 2022 cohort. Second estimate: the
interaction of short runway with the 2022 cohort in the pooled model of both cohorts.

**Secondary.** Runway as a continuous variable (log years) and in thirds; sponsors with positive cash flow as a
group; small sponsors only; whether the trials that short-runway sponsors stopped for financial reasons had ex-ante
genetic support as often as their trials that went on.

**Reading rule, fixed in advance.** If the primary odds ratio is above 1 with an interval that excludes 1,
sponsors short of cash stopped more trials in the downturn. If the interaction is above 1 with an interval that
excludes 1, the link was stronger in the downturn than in ordinary years. Otherwise the data do not show it. All
estimates are reported whatever they show.

**Known limits.** Public sponsors only; filers tag their balance sheets differently, so some are missed; the
calendar-year frames miss filers whose fiscal year does not end in December; the runway ignores money raised
later; a short runway may also reflect a pipeline that investors already doubted.
