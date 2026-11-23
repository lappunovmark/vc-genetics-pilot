# Plan: an audit of the links between trial sponsors and Form D issuers by location (written before the data were fetched)

Written on 23 November 2026, before the site countries were downloaded and before any link was read for this audit.

**Why.** A trial sponsor is linked to a Form D issuer when the two names are equal after legal forms are removed,
or when a decision in `pilot/formd_decisions.csv` accepts the pair. Two different companies can carry the same
name. The validation set out in Appendix B of the working paper (two annotators, 300 pairs) has not been carried
out. This audit is a narrower check that can be made on every accepted link with evidence independent of the
financing records: where the sponsor runs its trials.

**Evidence.** For every interventional study, the countries of its listed sites (ClinicalTrials.gov API v2, field
LocationCountry), joined to the registry snapshot by NCT number; the state of the issuer in its Form D filings
(`formd_match_review.csv`).

**Flag, fixed in advance.** An accepted link is flagged when the issuer's Form D state is a US state and the
sponsor led at least three trials with listed sites, none of them with a site in the United States.

**Reading.** Every flagged link is read against the names, the issuer's state and years of filing, the sponsor's
trials and their countries and, where these do not settle it, public sources. It is classed as *same company* (for
example a US company that runs its trials abroad, or a foreign company with a US entity), *different companies*
or *undetermined*. The reading is AI-assisted and has not been repeated by the author; the sheet of flagged links
with the classes is kept for a second reading.

**Report.** The number of accepted links, of links whose sponsor has at least three trials with sites, of flags,
and of each class. If any link is classed as different companies, it is rejected in `pilot/formd_decisions.csv`
with the reason, and the Form D results are run again; the change in the selection estimate of `formd_models.txt`
(programmes of sponsors with a Form D before the first trial against other non-top-20 industry sponsors) is
reported.

**Limits.** The flag finds collisions across borders only: two US companies with the same name are not
separated, and a sponsor with fewer than three trials with sites is not screened. The audit covers Form D links;
the links to EDGAR registrants, SBIR awards, Crunchbase and Ritter's list are not screened here.
