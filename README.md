# Do investors pick better biology?

An independent research project by Mark Lapunov, built only from public data.

[![checks](https://github.com/lappunovmark/vc-genetics-pilot/actions/workflows/checks.yml/badge.svg)](https://github.com/lappunovmark/vc-genetics-pilot/actions/workflows/checks.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
![Status: pilot](https://img.shields.io/badge/status-pilot%2C%20not%20peer--reviewed-orange)

## The idea

Most new drugs fail in clinical trials. One of the best early clues that a drug will work is **human genetic
evidence**: studies of human DNA that link the gene the drug acts on to the disease it is meant to treat. Drugs with
this evidence succeed much more often (Minikel et al., *Nature*, 2024), and the evidence is often public and free
before a drug project even starts.

**So do biotech companies, and the investors who fund them, actually choose drugs with this evidence?** And when
biotech funding dried up in 2022, did companies drop their best projects for lack of money?

## What I found

1. **Genetic evidence works for everyone.** Drug projects with it had about 2.5 times higher odds of moving on to
   the next trial phase, and this was true for small biotechs as much as for big pharma.
2. **Small biotechs use it less.** They start fewer projects with genetic evidence than the 20 largest drug
   companies.
3. **Investor money did not lead to better choices.** Companies that had raised private investment did not pick
   drugs with more genetic evidence, and neither did companies with US government small-business grants.
4. **After 2022, small biotechs stopped more trials because they ran out of money**, about 2.5 times as often as in
   2016–21. Trials stopped for financial or business reasons did not have stronger genetic evidence than
   trials that were completed.

![Pilot results at a glance](figures/results_glance.png)

<details>
<summary>The numbers behind each finding</summary>

| Finding | Estimate (95% CI) |
|---|---|
| 1. Genetic evidence → moving to the next phase | odds ratio 2.48 (2.10–2.93) |
| 1. Difference between small biotechs and top-20 pharma in that effect | odds ratio 1.26 (0.75–2.12), not significant |
| 2. Small biotechs starting projects with genetic evidence, vs top-20 pharma | odds ratio 0.64 (0.46–0.88) |
| 3. Private investment (SEC Form D filing) → projects with genetic evidence | odds ratio 0.66 (0.41–1.05) |
| 3. Government small-business grant (NIH SBIR/STTR) → projects with genetic evidence | odds ratio 0.72 (0.38–1.39) |
| 4. Small biotechs' trials stopped for lack of funding, 2022–25 vs 2016–21 | rate ratio 2.45 (1.57–3.82) |
| 4. Genetic evidence of trials stopped for financial or business reasons, vs completed trials | odds ratio 0.75 (0.53–1.04) |

Above 1 means more likely, below 1 less likely; if the range includes 1, the difference is not statistically
significant. Small biotechs are companies with at most 5 drugs (or at most 20 trials for finding 4).

</details>

## Data

35,887 drug–disease projects (29,199 of them in diseases where human genetic data exist) from Open Targets Platform
26.09 and ClinicalTrials.gov, US government grant records (NIH RePORTER) and SEC Form D filings on private
fundraising. Everything can be rebuilt with `make all`.

**Limits.** This is a pilot and has not been peer-reviewed. Company size and Form D filings stand in for venture
capital, which is not measured directly yet.

## More

* [Detailed results](docs/results.md) · [Methods and limitations](docs/methods.md) ·
  [Pipeline and how to run it](docs/pipeline.md) · [Data dictionary](docs/data_dictionary.md)
* [Open issues and next steps](https://github.com/lappunovmark/vc-genetics-pilot/issues)

## Author

**Mark Lapunov**, MSc Bioscience Innovation and Enterprise, University College London. Previously a research intern
at Skoltech, the Russian Academy of Sciences and Westlake University.
[LinkedIn](https://www.linkedin.com/in/mark-lapunov-085909240) · [GitHub](https://github.com/lappunovmark)

To cite, use **Cite this repository** (from `CITATION.cff`). Code is MIT-licensed; data keep their sources' licences,
including CC BY 4.0 for the genetic-support data of Minikel et al. (2024), doi:10.1038/s41586-024-07316-0.
