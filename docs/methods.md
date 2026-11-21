# Methods

Short reference for the definitions used in the pilot. The code is the final word; each section names the script.

## Units of analysis

**Programme** (`build_panel26.py`). A parent drug × MeSH indication pair in the Open Targets Platform 26.09
clinical data, which ships trial-level records from AACT (lead sponsor, phase, start date, status, `why_stopped`)
linked to drug, target and disease. Disease IDs are mapped to MeSH by Open Targets cross-reference or exact name,
otherwise to the nearest mapped ancestor (breadth-first, at most six levels). 35,887 programmes;
29,199 are in indications with *genetic insight* (at least one human genetic association for a similar trait, as in
Minikel et al.).

**Phase entry.** The first trial of a programme in phase 1, 2 or 3 (phase 1/2 counts as 2, phase 2/3 as 3). Entry
year = start year of that trial. The entry trial's lead sponsor defines the sponsor tier.

**Advancement.** A later trial of the same programme in a higher phase that started on or after the entry date, or
an approval of the drug for that indication. Entries with a higher-phase trial that started *before* the entry are
dropped. Entries from 2000 to six years before the last entry year are modelled, so each has follow-up time.
A stricter variant uses trials only (`advanced_trial_only`); a looser one counts higher-phase trials in a similar
indication (`advanced_sim`).

**Approval dates** (`approval_dates.py`). Most Open Targets approval records carry no date, so an approval granted
before a phase entry can count as advancement (1,205 of 26,542 model entries advance through an approval alone).
Two dates are looked up for them: the earliest EMA or PMDA approval report of the same drug × indication (the only
dated approval sources in Open Targets 26.09) and the drug's year of first approval from ChEMBL 37. `advanced_dated`
drops an approval whose indication-level date, or failing that the drug-level date, precedes the entry year (619
entries); `advanced_dated_known` additionally drops undated approvals. The drug-level date is conservative: a later
indication can be approved after the drug's first approval, so some genuine advancements are removed.

## Genetic support (`gensup.py`, validated against Minikel et al. 2024)

`support(T, I)` is true if the drug's target gene T has an association with a trait A whose MeSH similarity to the
indication I is at least 0.8. Sources: OMIM, GWAS (Open Targets Genetics with L2G share ≥ 0.5, 2005–2022), PICCOLO
and Genebass. The re-implementation reproduces all 1,258 supported target–indication pairs in their data.

**Ex ante.** Only associations dated before the phase-entry year count. OMIM rows are undated and are treated as
ex ante; every model is also run without OMIM. `gs_ot_dated.py` adds an independent measure from Open Targets
evidence dated by Falaguera et al. (Zenodo 15922783), where undated evidence never counts as ex ante; H1, H3 and the
KHB decomposition are run with it there, and `h4_biology.py`, `sbir_models.py` and `formd_models.py` repeat their
headline models with it when the dated evidence (or `gs_ot_programmes.csv.gz`) is available.

## Sponsor groups

| Where | Groups | Rule |
|---|---|---|
| Programme panel (`build_panel26.py`, `sponsors.py`) | Top-20 pharma; industry small (≤ 5 drugs), mid (6–30), large (> 30); academic/other; government | Top-20 = a fixed list of 20 large research-based companies: the 17 with the largest prescription-drug sales in 2023 (Pharm Exec 50, June 2024) plus Astellas, Merck KGaA and Daiichi Sankyo (21st, 24th and 25th in that ranking; Viatris, CSL, Teva, Vertex and Sandoz rank above one or more of them and are not in the list), matched by regular expression on industry sponsors' names; an acquired company counts as the parent only for trials that started in or after the acquisition year, and a spun-off unit (Organon, Sandoz, Alcon, Abbott before AbbVie) stops counting from the year of the spin-off. The registry shows each sponsor under its current name, which after an acquisition often carries the parent ("X, Inc., a subsidiary of Merck & Co., Inc."); the sponsor's own name comes first in these forms, so the entry that matches earliest in the name decides, and renamed subsidiaries have entries with their acquisition years (`factcheck/sponsor_names_audit.py` lists every name whose match is not the leading name). Other industry sponsors are sized by the number of distinct parent drugs their normalised name leads across all Open Targets trial records. |
| Trial stops (`rq2_stops.py`) | Top-20 pharma; industry small (≤ 20 trials), mid (21–200), large (> 200) | Size = number of interventional drug trials the normalised lead-sponsor name has ever led on ClinicalTrials.gov. |

Sponsor size is the main grouping. SEC Form D private placements add a direct, dated signal of private financing
(see below).

## Models

Logistic regressions with standard errors clustered by drug (`robust26.py`), on programmes and phase entries in
indications with genetic insight.

* **Selection (H1).** Programme level: ex-ante genetic support at the first trial ~ sponsor tier + first-trial
  period + therapeutic area + modality. `robust26.py` repeats the model with standard errors clustered by sponsor
  instead of drug, with each top-20 company left out in turn, with the top-20 group cut to the 17 companies
  with the largest 2023 sales, within one disease (indication fixed effects on the indications where support
  varies; a conditional logit gives the same comparison without estimating the indication effects), and without a
  model, within cells of period × area × modality (Mantel–Haenszel). `gs_ot_dated.py` repeats it with support on
  either or on both of the two evidence measures as the outcome.
* **Advancement (H3).** Phase-entry level: advanced ~ ex-ante support + sponsor tier + phase + entry period + area +
  modality, then with a support × tier interaction.
* **Mediation (H2).** Karlson–Holm–Breen decomposition of the tier gap in advancement through ex-ante support
  (`khb26.py`).

**Convergence.** A control category with no or almost no events makes a logit quasi-separated: its coefficient drifts
towards minus infinity and the optimiser never reports convergence, although the coefficients of interest are stable
to three or four decimals. Every logit in the pipeline is checked with `factcheck/convergence_audit.py`; where a
sample has such categories (the novel-drug, trial-level H4, SBIR and stop-rate models), nominal controls with fewer
than three events are pooled into "other" and sparse start-period bins are merged into the next bin
(`pilot/pooling.py`), and any fit that still fails to converge is flagged in the output.

## Trial stops around the 2022 funding downturn (`rq2_stops.py`, `rq2_rr.py`, `stopreasons.py`)

`why_stopped` texts of terminated, withdrawn and suspended industry drug trials are classified by a keyword
classifier (v4). One label per text, first match in this order: no funding; safety / benefit-risk; efficacy /
futility; COVID-19; enrolment; M&A / licensing; business / strategic; sponsor decision, unspecified. A stated lack of
funding therefore comes first, and a scientific or operational reason stated alongside a business one wins. Negated or
neutral mentions ("not due to safety", "no safety concerns", "safety committee") are removed before matching.
*Financial or strategic* = no funding, M&A / licensing or business / strategic. v4 (7 Nov 2026) adds patterns for
business stops that v3 left unclassified (management or company decisions, programmes discontinued, withdrawn
support, wind-downs, expired grants), found by cross-checking v3 against the Open Targets StopReasons predictions,
and narrows two v3 patterns that fired on regulatory stops and on stops explained by other studies' results.
Every pattern must match at least one text outside the 200 held-out texts (in the 400 tuning texts or in the
StopReasons file with its 97 held-out trials removed), so that the held-out score is not tuned to the held-out set;
`factcheck/stopreasons_support.py`
checks this for every alternative of every pattern (validation in [results](results.md)).

Rates are stops per 1,000 active trial-years (each trial at risk adds one trial-year per calendar year). Rate ratios
compare 2022–25 with 2016–21, with Poisson confidence intervals: log RR ± 1.96 √(1/a + 1/b).

## NIH SBIR/STTR linkage (`sbir_link.py`, `sbir_models.py`)

Industry lead sponsors are matched to NIH RePORTER SBIR/STTR awardees: exact match of normalised names, then
fuzzy match (RapidFuzz `token_sort_ratio` ≥ 92) within blocks that share the first token. Every match is written
out for review; matches that differ by more than a legal form need an explicit decision in `pilot/sbir_decisions.csv`.
A sponsor counts as SBIR/STTR-funded before a trial if its first award year precedes the trial's start year.

## SEC Form D private placements (`fetch_formd.py`, `formd_link.py`, `formd_models.py`)

Form D is the notice a company files with the SEC after selling securities in a private placement. The quarterly
Form D data sets (2009 Q1 onwards) are filtered to offerings whose industry group is Biotechnology, Pharmaceuticals
or Other Health Care and that are not pooled investment funds, then joined to the filing date and the primary issuer.
Candidate names are the issuer's name at filing time and up to six previous names (on the filing and in EDGAR);
CIKs are normalised because the source pads them inconsistently, and EDGAR state markers such as "/DE/" are removed.
Sponsors are matched to names with the same rules as the SBIR/STTR linkage. A name counts as the sponsor's own if it
equals the sponsor's name after removing legal forms, or is accepted in `pilot/formd_decisions.csv` (each decision
carries a reason); several own names are pooled.

**Dating.** The sponsor's first private placement is the earliest Form D filed by its legal entity (CIK) under any
name, because most name changes in EDGAR are renames. When the sponsor's name appears under more than one CIK, the CIK
that first filed under that name is the original company and keeps its whole history; any other CIK with the name
(usually a listed shell adopted by reverse merger) contributes only filings under the sponsor's own or later names.
Two bounds are reported as sensitivity: own and later names only (`formd_first_year_own`) and every filing of every
own CIK (`formd_first_year_cik`). The selection is deterministic (ties broken by filings, first year and CIK).

**US-only comparison.** Only issuers raising money in the US file Form D, so sponsors are classified as US,
non-US or unknown (`sponsor_region.py`): US or foreign location in the financing records (Form D state, SBIR), else a
legal form or place name pointing abroad (GmbH, AG, SA, Ltd, Co. Ltd., Shanghai, India, …), else a US legal form
(Inc, LLC, Corp, Company); the rest are unknown and left out. `formd_models.py` repeats the selection and advancement
models for US sponsors only.

`formd` = the lead sponsor's first Form D is dated in a calendar year before the trial's start year. Because the data
start in 2009, the Form D models use programmes and phase entries from 2010 onwards. In the selection models,
therapeutic areas with fewer than three supported programmes are pooled into "other" to avoid separation.

**Amount raised.** Filings are folded into offerings: an amendment (Form D/A) restates the offering it amends, so
each chain of filings linked by `PREVIOUSACCESSIONNUMBER` is one offering, dated by its first filing, with the amount
sold taken from the latest filing (amendments report the cumulative amount). Every offering in a sponsor's history
under the main dating rule is listed in `results/formd_sponsor_offerings.csv.gz`. For each programme or phase entry
the amounts sold in the sponsor's offerings dated before the trial year are summed (nominal US dollars, no deflation)
and banded: no prior Form D, under $10M, $10–50M, $50M or more. `formd_models.py` fits the selection and advancement
models with the bands (reference: no prior Form D) and, among filers, with log10(1 + millions raised); two
sensitivities repeat the band models with equity offerings only (no debt-only offerings, no business combinations)
and with amounts in 2024 dollars (CPI-U, `results/cpi_u_annual.csv`).

The extract used for the published results is on the `formd-data` branch (`data_formd/`), with the fetch log.

## Owners of the sponsor (Schedules 13D and 13G)
Form D says that a sponsor raised private money, not from whom. A holder of more than 5% of a public company's
shares must file a Schedule 13D or 13G, and the EDGAR quarterly index lists every such filing under the company and
under each filer with the same accession number, so company–owner pairs can be read from the index alone
(`fetch_edgar_owners.py`, 2001–2026; from December 2024 the forms are indexed as SCHEDULE 13D/13G). A sponsor's
legal entities are the CIKs of its accepted Form D issuers and the EDGAR registrants (filers of S-1, F-1, 424B4,
10-K, 20-F or 40-F) with the same name once legal forms are removed, or accepted in `pilot/owners_decisions.csv`
after hand review (holding companies and earlier names accepted, namesakes rejected). The other parties of every
accession that names a sponsor entity are taken as its owners (`owners_link.py`). The index does not say which
party is the company and which the holder, so a sponsor that itself reports a stake in another company picks up
that company as an "owner"; no party classified as a venture fund is an operating registrant, so the venture
marker is not affected. Filer names are classified with the regular expressions in `pilot/investor_classes.tsv`
(first match wins), written after reading the names by frequency: venture capital; life-science crossover (funds
that hold public stock, including the public funds of venture firms and firms such as OrbiMed, RA Capital and
Deerfield that file for their venture and public funds under one name); hedge fund or PIPE investor; asset manager;
private equity or holding; corporate; credit and secondaries. A private fund vehicle with a series number
("Partners VII, L.P.") that no named rule covers is taken as a venture or growth fund. Individuals and companies
not named in the file stay unclassified.

`owners_models.py` repeats the selection and advancement models among non-top-20 industry sponsors (first trial in
2001 or later) with the marker "a venture-capital fund among the owners", alone, among public sponsors only, and in
three stricter or wider forms: the venture fund's first filing is dated no later than the year after the sponsor's
first registration (an owner at the time of going public, not a later purchase); a venture filing dated by the year
of the programme's first trial; a venture or crossover owner. Ownership is observed only for sponsors that became
public, only above 5%, and only at or after the filing.

## Exploratory checks behind the selection gap (`h1_mechanisms.py`)
These checks test alternative explanations of the small-sponsor gap in selection. None was pre-specified: the splits
were chosen after the result was known, so their p-values are descriptive. The models are the H1 logit with sparse
control categories pooled (`pooling.py`), because the split outcomes are rarer than the H1 outcome.

**Type of evidence.** Ex-ante support is split into support from dated population genetics (OTG, PICCOLO, Genebass:
an association dated before the year of the first trial) and support from OMIM only. OMIM carries no dates in this
pipeline and always counts as ex ante, so "OMIM only" is not a dated measure. The split is read from the programme's
first phase entry; 12 supported programmes whose type at the first trial is unknown are left out.

**Novel and follow-on.** A programme is novel when it is the drug's first indication, follow-on when the drug was
already in trials for another indication (first trial in 2000 or later).

**Partnerships.** Registry proxies only: a top-20 or any industry collaborator on the programme's first trial.
Licensing and co-development deals are not in the registry.

**Typical Phase 3 size.** For each indication, the median enrolment of the industry-led Phase 3 entry trials of other
drugs: at least three distinct trials, none of them of the programme's own drug, trials stopped early excluded.
Enrolment is the registry field (`fetch_ctgov_enrollment.py`: actual for completed trials, anticipated for ongoing
ones), downloaded on 12 November 2026 and joined to the 17 October snapshot by trial number.

**Capital against the cost of a Phase 3.** Form D capital raised before the year of the first trial (nominal USD)
against the typical Phase 3 size times USD 41,117 per patient, the median over 138 pivotal trials of 59 drugs
approved by the FDA in 2015–2016 (Moore et al., *JAMA Intern Med* 2018;178(11):1451–1457). A crude yardstick: it
ignores Phase 1–2 costs, later rounds and public financing.

**Acquisitions.** `sponsors.py` types a renamed subsidiary by its own name, but the registry moved some old records
to the acquirer's name outright. They are found through research codes (`extract_molecule_synonyms.py`): a programme
typed top-20 whose drug carries the code of a company that the same parent acquired only after the programme's first
trial. This is a lower bound: only the acquisitions listed in `sponsors.py`, only drugs with a research code in
ChEMBL.

## Venture rounds from Crunchbase (`cb_models.py`, exploratory)
Form D does not name investors and Schedules 13D/13G cover only public companies. The Crunchbase data export of
4 December 2015 (CSV copy at github.com/notpeter/crunchbase-data; Crunchbase data under CC BY-NC, not redistributed
here) lists funding rounds by type with dates and investors. Sponsor names are matched to Crunchbase company names
on the normalised name; a candidate is accepted when the names are also equal once only legal forms are removed or
when the company is in a life-science or health category, and the candidates were then read by hand
(`pilot/cb_decisions.csv`; every candidate with its decision in `results/cb_link_review.csv`). A sponsor has a
venture round when a round of type "venture" is dated before the year of the programme's first trial; "named fund"
requires an investor that is an organisation classified as venture capital or life-science crossover by
`pilot/investor_classes.tsv`. Rounds are observed to December 2015, so the sample is first trials in 2001–2016.
Coverage is incomplete: a sponsor that is not found is not known to be without venture money, which is why the
comparison among sponsors found in Crunchbase is reported next to the comparison with all other sponsors.

## Venture backing at the IPO (`ritter_models.py`, exploratory)
Jay R. Ritter's file "Founding dates for IPOs from 1975–2025" (University of Florida, version of 19 January 2026)
lists US IPOs with a flag for venture-capital backing (1; 2 for the subset he calls growth capital), compiled from
prospectuses and commercial sources. Sponsor names are matched to IPO names on the normalised name; a candidate is
accepted when the names are also equal once legal forms are removed or when the IPO name has a life-science word,
of several IPOs under one name the one closest in time to the sponsor's first trial is kept, and the candidates were
read by hand (`pilot/ritter_decisions.csv`; every candidate in `results/ritter_link_review.csv`). The flag exists
only for sponsors that went public in the US. It is used to check the pilot's own venture markers (share of
Ritter's venture-backed IPOs that a marker finds; share of a marker's sponsors that Ritter confirms) and, combined
with them, as a sponsor-level flag "venture-backed by any source". That flag is not dated to the trial.

## Investors named in IPO prospectuses (`fetch_ipo_prospectus.py`, `ipo_holders.py`, `ipo_models.py`)
The plan (`docs/plan_ipo_prospectus.md`) was committed before any prospectus was downloaded; its two amendments
(the rule for an IPO; what was read, the check by eye and the definitions) were committed before any model was
fitted. *Sample.* For each EDGAR registrant of a non-top-20 industry sponsor (`owners_link.py`), the IPO prospectus
is its first form 424B4 filed on or after its first S-1 or F-1, if it filed no annual report before the prospectus
and its first registration in the index is dated 1 April 2001 or later. The primary sample is the prospectuses
filed under the sponsor's own name (same first word of the normalised name); a registrant's other sponsor names
are companies that merged into it later and are not given its prospectus.
*Reading.* `ipo_holders.py` turns the prospectus into lines, a table row becoming one line, finds the section on
principal stockholders by its heading (or by the heading row "Name of beneficial owner") and reads every row with
a name and at least two numbers. The percentage before the offering is the first column of the table that holds
percentages (no value above 100 or with a thousands comma, and a percent sign, a star or a decimal fraction
somewhere in the column). Addresses printed under a name, footnote marks and the row for all directors and
officers as a group are removed; early filings that put the name on a row of its own above the address are read
with the name of that row. Only tables whose heading names owners or holders are read, which keeps financial
tables out. Plain-text filings (two in the sample) are not read. Twenty prospectuses drawn at random were compared
by eye with an independent rendering of each table: 95 holders, all with the right percentage. Because the reader
was still being corrected while that sample was read, ten more prospectuses were drawn after it was final: 46
holders, all read correctly, none missed and none added (`factcheck/ipo_holders_check.csv`, checked against the
reader by `factcheck/ipo_holders_check.py`).
*Classes and measures.* A holder counts if it holds 5.0% or more and is not a natural person. Classes come from
`pilot/ipo_holder_classes.tsv` (rules written after reading every name the existing rules left unclassified, and
the footnotes where the name did not say what the holder is), then `pilot/investor_classes.tsv`; the kind of a
corporate investor from the first file where given, otherwise from `pilot/corporate_investors.tsv`. The venture
share of a sponsor is the sum of the percentages held by venture-capital funds, capped at 100; a corporate holder
is a drug, drug-services or medical-technology company or its venture arm. An unclassified holder counts as
neither.
*Models.* The selection model of the pilot (first-trial period, therapeutic area, modality, sponsor size) on the
programmes of the sponsors with a prospectus read. The primary estimate is the odds ratio of ex-ante support per
10 percentage points of venture share on programmes first tried no later than the IPO year, with errors clustered
by drug; because the venture share is the same for every programme of a sponsor, each model is also reported with
errors clustered by sponsor. Rows of a sponsor-size band without any supported programme are predicted perfectly
and are dropped from that model (this changes no estimate and lets the fit converge).

## Venture investors on the board (`fetch_formd_people.py`, `formd_directors.py`, exploratory)
Form D names the issuer's executive officers, directors and promoters. Venture-capital funds file Form D as pooled
investment funds of type venture capital and name the people who manage them. A sponsor's filing has a venture
investor on the board when a director who is not an executive officer carries the name (first word of the first
name and last name) of a person named in a venture fund's filing, or when a related person's address is "care of"
an investor classified as venture capital or life-science crossover by `pilot/investor_classes.tsv`. A sponsor's
filings are those of its Form D issuers (`formd_link.py`). Two people can share a name: the share of executive
officers who are not directors and still match (2.7%, against 11.5% of outside directors) is a rough bound on chance
matches, and the marker is checked against Ritter's flag and Crunchbase. The marker is dated: a programme counts
when such a filing precedes the year of its first trial (first trials after 2009, as for the other Form D models).

## One venture flag from four sources (`vc_combined.py`, exploratory)
A sponsor is venture-backed if at least one of the four markers says so (owners in Schedules 13D/13G, Ritter's
IPO flag, a Crunchbase venture round, a venture investor on the board in Form D) and is "seen" if at least one
source could have shown it. The flag is a property of the sponsor, not dated to the trial. Sponsors that are not
seen are not known to be without venture money, so the comparison among seen sponsors is reported next to the
comparison with all other sponsors.

## Corporate and independent venture investors (`cvc_models.py`, exploratory)
Corporate investors are named by `pilot/corporate_investors.tsv` (regular expressions written after reading the
investor names by frequency; first match wins): venture arms and direct investments of large drug and
medical-technology companies, other drug companies, corporations outside drug development, and the investment arms
of foundations that own drug companies (Novo Holdings, Lundbeckfonden, Wellcome Trust), which are kept apart and
counted as corporate only in a sensitivity run. Independent funds are investors classified as venture capital or
life-science crossover by `pilot/investor_classes.tsv` that no corporate rule names. In private rounds a programme
has a corporate investor when a Crunchbase venture round dated before the year of its first trial names one, and
independent funds only when such a round names an independent fund and no corporate investor. For public sponsors
the corporate owner is a large drug company or its venture arm named with the sponsor in a Schedule 13D/13G; only
large companies count, because the index does not say which party of a filing is the owner. A large company also
files when it buys the sponsor, so the undated marker mixes minority stakes with later acquisitions, and a dated
variant keeps owners whose first filing is no later than the year of the programme's first trial, for sponsors
public by then. Models are the selection and advancement logits of `cb_models.py` and `owners_models.py`.

## Venture backing and trial stops (`vc_stops.py`, exploratory)
The trial-year panel of `formd_stops.py` (industry Phase 1–3 drug trials of non-top-20 sponsors at risk in
2016–2025) with the sponsor marked as venture-backed by any of the four sources. The programme panel covers about
three fifths of these trials, so every trial sponsor is matched again by name to Crunchbase, Ritter's list and the
Form D issuers: a match needs the same name once legal forms are removed; the links and hand rejections of the
programme panel are kept, and the new links are listed in `vc_stops_link_review.csv` with hand rejections in
`pilot/vc_stops_decisions.csv`. Owners in Schedules 13D/13G are known for sponsors of the programme panel only. The
flag is a property of the sponsor and is not dated to the trial. Models: logit on trial-years of venture group ×
post-2022 with sponsor size band, phase and start period, errors clustered by sponsor; reference group: sponsors
seen in a source without a venture marker.

## Selection by type of drug (`h1_by_modality.py`, exploratory)
The selection logit of `h1_mechanisms.py` (first-trial period and therapeutic area as controls, errors clustered by
drug, sparse categories pooled) fitted within each type of drug: small molecule; antibody, with antibody-drug
conjugates; protein, with enzymes; nucleic acid, gene and cell therapies. One model with all types tests whether
the gap differs between small molecules and biologics (sponsor tier × biologic), and one with small molecules and
antibodies only (sponsor tier × antibody). The split was chosen after the H1 result was known.

## Direction of effect (`extract_ot_direction.py`, `direction_models.py`, exploratory)
Open Targets gives evidence a direction on the target (loss or gain of function) and on the trait (risk or
protective). It does so for gene burden (taken as loss of function; trait direction from the sign of the effect),
ClinVar (loss-of-function variants only), Orphanet and Gene2Phenotype (taken as risk), and for drugs in the clinic
(inhibitors loss of function, activators gain of function); GWAS evidence has no assessment. Evidence is taken
from release 26.09 with the score floors of `gs_ot_dated.py` and mapped to MeSH with the panel's disease map. The
genetics asks for a drug that lowers the target's function when loss of function protects or gain of function is
a risk, and for one that raises it otherwise. A programme is concordant when, for a target and an indication with
MeSH similarity ≥ 0.8, the drug's direction is the one asked for; ex ante uses the Open Targets evidence date
(for ClinVar the date of the record), so ex-ante counts are conservative. "Discordant" is printed but not
interpreted: a disease caused by gain of function is invisible to an assessment of loss-of-function variants.
Models are the selection logit with concordant support as the outcome, with and without gene burden evidence.

## Programme starts around the publication of genetic evidence (`evidence_arrival.py`, exploratory)
Unit: a target × indication pair (the gene a drug acts on × the MeSH indication) with at least one programme started
in 2000–2025 in an indication with genetic insight. Evidence year: the earliest year of a supporting association
from a dated source (Open Targets Genetics with L2G share ≥ 0.5, PICCOLO, Genebass), support defined as in
`gensup.py`; pairs with OMIM support are left out because OMIM carries no dates here; pairs never supported are the
comparison group. Outcome: programmes whose first trial started in the year, by the tier of the first sponsor (a
drug with several targets counts once per pair). Model: Poisson with pair and year fixed effects, errors clustered
by indication; `post` = year after the evidence year. Because starts on a pair decline over its life, the
before-after change of one group is not an effect of the evidence (placebo with the evidence year moved five years
earlier). The contrast between sponsor groups uses two outcomes per pair-year with pair × group and year × group
effects, so it is measured against each group's own calendar trend; it rests on the groups following the same path
without the evidence (checked by the leads and by the placebo of the contrast). None of this first run was pre-specified.
Run under Python 3.13 with pyfixest; the library does not run under the Python 3.9 of the author's Mac.
A second run uses the evidence of Open Targets 26.09 instead of the Minikel associations (`extract_ot_dated.py`:
gene × disease × source with the earliest evidence date, the score floors of `gs_ot_dated.py`). Its plan
(`docs/plan_evidence_arrival_ot.md`) was committed before the run and fixes the primary evidence (GWAS credible sets),
the primary estimate (the contrast of other industry against top-20 pharma) and the rule for reading it.
An Open Targets disease or trait counts as evidence for a pair when the panel's disease map gives it a MeSH term
equal or similar (≥ 0.8) to the indication; traits without a MeSH term (many measurement traits) are not counted.
The plan spoke of leaving out pairs whose only evidence is undated; the run on all sources left out every pair with
a source whose evidence carries no date, and `EA_UNDATED=only` gives the variant with the wording of the plan.
Section F splits non-top-20 industry sponsors by the combined venture flag of `vc_combined.py`
(`docs/plan_evidence_arrival_venture.md`, written before any model with these groups); the flag describes the
sponsor and is not dated. Two checks were added after the results were known and are labelled so in the output:
`EA_LAST_EVIDENCE_YEAR=2022` leaves out pairs that gained their evidence after 2022 and have little follow-up, and
section G counts the genes behind the post-evidence starts of top-20 pharma, repeats the contrast without the
three leading genes, classes each start as a drug's first indication or a further indication (of a drug first
tried before or after the evidence year), lists the starts (`evidence_arrival_ot_<set>_top20_starts.csv`) and
repeats the models with gene × year effects, where the comparison is the other indications of the same target in
the same year. It also counts the starts by top-20 company, repeats the contrast with each company left out in
turn and without the three leading companies, and compares large and mid-sized sponsors outside the top 20 with
top-20 pharma separately. Section H repeats the design with the target as the unit: programme starts on a gene in all its
indications, the evidence year being the first year in which one of its pairs gained evidence, with gene and year
effects and errors clustered by gene. For the check planned in `docs/plan_top20_2010.md`, `EA_TOP20=2010` defines
the top-20 group by the first twenty of the Pharm Exec 50 of May 2011 (prescription-drug sales in 2010;
`sponsors.TOP20_2010`, with entries for Teva, Eisai and the companies they acquired), a sponsor that leaves the
group being typed by the size of its portfolio, and `EA_FIRST_EVIDENCE_YEAR=2010` keeps only pairs whose evidence
year is 2010 or later; `top20_2010.py` fits the selection model with that group. `figure_evidence_arrival.py` draws the event study and the contrast under
each specification from these files (`figures/evidence_arrival.png`).

## Cash runway and trial stops (`fetch_sec_frames.py`, `cash_runway.py`)
The plan (`docs/plan_cash_runway.md`) was committed before the SEC data were downloaded. `fetch_sec_frames.py` reads
the SEC's XBRL frames: for each concept and period, the value every filer reported (year-end balances as
`CY<year>Q4I`, the annual operating cash flow as `CY<year>`). A frame holds the latest filing that reports the fact,
and it also takes fiscal years that do not end in December (the nearest year-end balance and twelve-month flow).
Liquid assets are the reported total of cash, cash equivalents and short-term investments if the filer tags it,
otherwise cash and cash equivalents plus the first available of short-term investments, current marketable
securities and current available-for-sale debt securities. Runway = liquid assets / cash used in operations, in
years; below 1.5 years is short; sponsors with positive operating cash flow form a group of their own. Sponsors are
linked through the EDGAR registrant numbers of `owners_link.py`; a sponsor with several registrants takes the one
with the most liquid assets. Cohort 2022: industry Phase 1–3 drug trials of non-top-20 sponsors active on 1 January
2022, runway at the end of 2021, outcome = a financial or strategic stop (classifier v4) in 2022–2023; cohort 2018
is the same four years earlier. Logits with phase, the trial's age at the cohort date (1–2, 3–5, 6+ years) and the
sponsor's size band; errors clustered by sponsor.
Limits found after the first run and checked in models 12–15: several sponsor names can share one registrant; the
frames do not leave out non-December fiscal years, so for some sponsors the figures refer to another date than
31 December; and a registrant number says nothing about when the sponsor came to hold it, so a company that merged
into a listed company after 2021 is given that company's figures for 2021. The last group is found by comparing the
first word of the sponsor's normalised name with that of the registrant's present name on EDGAR, which also sets
aside sponsors that were merely renamed.

## Reference date

Trials count as started if their start date is on or before 17 October 2026, the date of the Open Targets download
and ClinicalTrials.gov snapshot (`PILOT_ASOF` in `build_panel26.py` and `rq2_stops.py`). Without a fixed date the
panel changed with the day the script was run, because trials registered with a future start date enter as the
calendar advances (91 reports between 17 October and 6 November 2026).

## Known limitations

* Form D marks private placements, not venture capital as such: some venture rounds are never filed, some filers are
  not venture-backed, and only issuers raising money in the US file. "No prior Form D" therefore mixes non-US
  sponsors with US sponsors that raised no private money; the US-only comparison above (`sponsor_region.py`, a
  name-based heuristic that leaves 20% of programmes unclassified) gives the same answer for selection and
  advancement and no support × Form D interaction.
* Most approval records carry no date, so an approval that preceded a phase entry can count as advancement; the
  dated variants above bound the effect (genetic premium 2.48 → 2.53 when such approvals are removed, 2.25 with trials
  only).
* Registry programmes include investigator-initiated trials of marketed drugs; levels of relative success are therefore
  not comparable with Pharmaprojects-based estimates (pilot RS 4.0–4.2 vs 2.16).
* Ex-ante support uses association years; OMIM rows (undated) are treated as ex ante, with a no-OMIM sensitivity and
  a parallel measure from Open Targets evidence dated by Falaguera et al. (2026), reported for every model. Where the
  two measures disagree (H4), the paper reports both.
* The stop-reason reference labels are an LLM-assisted first pass, not yet blind double-coded by the author.
* Sponsor names are those in the registry on the snapshot date. A renamed subsidiary is typed by its own name and
  acquisition year, but when the record of an old trial was moved to the acquirer's name outright the trial counts
  as the acquirer's; the list of acquired companies covers those met in the data, not every deal (a longer,
  unverified list of 187 deals in `factcheck/sponsor_missing_acquisitions.py` would move 204 registry trials, 0.6%
  of those typed top-20, and 29 phase entries of the panel); and a trial
  without a start date (109 industry trials typed through an entry with a year window) is typed without the window.
  Licensing and co-development between a small sponsor and a large company are not observed at all: a programme is
  typed by the lead sponsor of its first trial. This matters for reading the top-20 group: of the 138 new drugs
  that the 20 largest companies brought to FDA approval in 2015–2021, 65% came from acquisitions or in-licensing
  and 28% were invented in-house (Schuhmacher et al., Nat Rev Drug Discov 2023;22:781–782).
* The eight headline estimates (the rows of panel A of `figures/main_results.png`) are reported without adjustment
  for multiple testing. The genetic premium and the rise in funding-related stops would pass any correction; the
  small-sponsor gap in selection (p = 0.017) would not pass a Holm correction across the eight, although with
  support counted on either evidence measure it would (p = 0.0008). It should be read as suggestive.
* A sponsor that went public through a reverse merger and never filed a Form D under its own name inherits the listed
  shell's earlier placements; the own-names-only bound shows how much this can matter.
