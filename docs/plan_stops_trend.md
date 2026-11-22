# Plan: is the rise in financial or strategic stops after 2022 a break or a trend? (written before the run)

Written on 22 November 2026, before any model of this plan was fitted.

**Why.** Table 3 of the working paper compares stop rates in 2016–21 with 2022–25 and finds that stops for
financial or strategic reasons roughly doubled in every sponsor group. Bowling, Cocucci, Koo and Harrison (2025,
*Nature Reviews Drug Discovery*, doi:10.1038/d41573-025-00208-6) report that terminations of industry Phase II and
III trials rose throughout 2013–2023, led by strategic and business reasons. A steady rise would produce the same
before/after ratio as a break in 2022, so the comparison of two periods cannot tell the two apart.

**What has already been seen.** The yearly rates by sponsor group (`results/rq2_rates.csv`) are drawn in the paper,
so this check is planned before the run but not blind to the data: the figure suggests a jump in 2022 for small
and mid-sized sponsors and a rise from 2020 for top-20 pharma and large sponsors. The plan fixes the model and the
reading rule before any trend model is fitted.

**Data.** `results/rq2_rates.csv`: for each sponsor group and calendar year, the industry Phase 1–3 drug trials at
risk and the stops for financial or strategic reasons (classifier v4). Years 2016–2025, the window of Table 3;
2026 is incomplete and is left out.

**Model.** For each sponsor group, a Poisson regression of the yearly number of stops with the logarithm of
trial-years at risk as offset:

    log(rate) = a + b · (year − 2021) + c · post,   post = 1 from 2022

The dispersion is estimated from the Pearson statistic (quasi-Poisson), because yearly counts vary more than a
Poisson model allows. A pooled model with group-specific intercepts and trends gives the ratio of the breaks of two
groups.

**Primary estimates.** exp(c) for small sponsors and for top-20 pharma: the change of level in 2022 beyond the
linear trend of the log rate; and the ratio of the two from the pooled model.

**Reading rule.** A group shows a break in 2022 if the 95% interval of exp(c) excludes 1. If neither interval
excludes 1, the doubling in Table 3 cannot be separated from a trend with these data, and the paper will say so. If
the interval for small sponsors excludes 1 and the interval of the ratio to top-20 pharma excludes 1, the break is
specific to small sponsors.

**Secondary, all descriptive.** (a) The same for mid-sized and large sponsors. (b) Years 2012–2025. (c) The trend
fitted on 2016–2021 alone and carried forward: stops observed in 2022–25 over stops expected. (d) All stops, and
for small sponsors the stops that cite lack of funding. (e) A break in 2020 instead of 2022, which the figure
suggests for top-20 pharma and large sponsors; this one is exploratory because the date comes from the data.

**Limits known in advance.** Ten yearly points per group, of which four after the break, so the trend and the break
are estimated together from little information and the intervals will be wide. A linear trend in the log rate is an
assumption. Stops are counted in the year the trial stopped, and the reason is the one the sponsor stated.
