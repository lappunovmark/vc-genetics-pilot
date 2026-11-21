# Data dictionary: `results/`

Every file is written by a script in `pilot/`; provenance (release, snapshot date, code commit) is in
`results/PROVENANCE.txt`. Compressed tables (`.csv.gz`) open directly with `pandas.read_csv`.

## Programme panel (`build_panel26.py`)

**`programmes.csv.gz`**: one row per drug × MeSH indication.

| Column | Meaning |
|---|---|
| `drug`, `indication_mesh_id` | ChEMBL parent drug ID and MeSH descriptor ID |
| `first_trial`, `first_year`, `first_phase` | Earliest trial of the programme, its start year and phase |
| `first_sponsor_tier`, `first_sponsor`, `first_class` | Sponsor group, lead sponsor name and ClinicalTrials.gov sponsor class of that trial |
| `max_trial_phase`, `approved` | Highest phase reached in a trial; approval for this indication in Open Targets |
| `drug_first_year`, `drug_first_tier`, `is_drug_first_indication` | Start year and sponsor group of the drug's first trial in any indication; whether this programme is that first one |
| `drugType`, `area`, `mesh_map` | Modality, therapeutic area, and how the disease was mapped to MeSH (`direct` or `ancestor`) |
| `insight`, `insight_source`, `in_sim` | Genetic insight for the indication and where the label comes from (`minikel` = their set, `approx` = approximation for other indications) |
| `gs_post`, `gs_ante_first`, `gs_post_noomim` | Genetic support at any time; ex ante at the first trial; any time without OMIM |
| `n_targets` | Number of distinct target genes linked to the programme |

**`phase_entries.csv.gz`**: one row per programme × phase entry (phases 1–3). Adds `entry_trial`, `entry_start`,
`entry_year`, `sponsor_tier`, `lead_sponsor`, `sponsor_n_drugs`, `prior_higher` (a higher-phase trial started
before entry), `next_start` (first later higher-phase trial), `advanced`, `advanced_trial_only`,
`prior_higher_sim`, `advanced_sim`, and `gs_post`, `gs_ante`, `gs_ante_noomim`.

**`sponsors.csv.gz`**: one row per trial record: lead sponsor, normalised name, sponsor class, top-20 parent (if
any), portfolio size and sponsor group.

**`h1_selection.csv`**, **`h1_by_period.csv`**: share of programmes with genetic support by sponsor group (overall
and by period), with Wilson 95% intervals.

**`transitions.csv`**: phase-transition counts and probabilities with and without genetic support by phase and
sponsor group; `rs` is relative success (P(advance | support) / P(advance | no support)).

**`models.txt`**, **`robust.txt`**, **`khb.txt`**, **`gs_ot_models.txt`**: model output (coefficients, odds ratios,
95% intervals, N and number of drug clusters).

## Trial stops (`rq2_stops.py`, `rq2_rr.py`)

| File | Content |
|---|---|
| `rq2_stops_by_year.csv` | Stopped trials by stop year × sponsor group × reason class |
| `rq2_rates.csv` | Per year and group: trials at risk, stops (all, financial or strategic, no funding) and rates per 1,000 |
| `rq2_rr.csv` | Pooled rates 2016–21 vs 2022–25 and rate ratios with 95% intervals; `stops` = `all`, `fin` or `nofund` |
| `rq2_shares.csv` | Share of stops with a stated reason that are financial or no-funding, by year × group |
| `rq2_did.txt` | Difference-in-differences and event-study logits (the no-funding fits separate, a group-by-period cell having no events, and are flagged as not estimable) |
| `sponsor_missing_acquisitions.txt` | How many registry trials and panel phase entries a longer, unverified list of top-20 acquisitions would move to top-20 (a bound on the omission; not used for typing) |
| `sponsor_names_audit.txt` | Industry sponsor names whose top-20 match is not the leading name (each reviewed in `pilot/sponsors.py`), and trials without a start date typed through an entry with a year window |
| `rq2_label_sample.csv` | Stratified sample of `why_stopped` texts drawn for hand coding |
| `rq2_hand_labels.csv` | Hand labels for the tuning and held-out sets, with classifier v1, v3 and v4 output |
| `stopreasons_crosscheck.txt`, `stopreasons_support.txt` | Agreement of the classifier with the Open Targets StopReasons predictions, and the number of texts each classifier pattern matches in the StopReasons file, the tuning texts and the held-out texts (`factcheck/`) |

## H4 and SBIR/STTR

| File | Content |
|---|---|
| `h4_biology.txt` | Ex-ante support of trials stopped for financial or strategic reasons vs completed trials (Minikel measure, no-OMIM variant and the dated Open Targets measure) |
| `sbir_match_review.csv` | Every sponsor ↔ SBIR/STTR awardee match with both names, score and decision |
| `sbir_summary.txt`, `sbir_models.txt` | Linkage coverage and models of prior SBIR/STTR funding |

## Approval dates (`approval_dates.py`)

| File | Content |
|---|---|
| `approval_dates.txt` | Counts of approval-only advancements with and without a date, by phase and sponsor tier, and the advancement models under four definitions (main, dated, dated-known-only, trial only) |
| `chembl_first_approval.csv` | ChEMBL 37 extract: approved molecules with their year of first approval (input snapshot, fetched 6 Nov 2026) |
| `approval_dated_entries.csv.gz` | Per phase entry: indication-level approval year and sources, drug-level first approval, and the advancement flags (produced locally, not versioned) |

## SEC Form D (`formd_link.py`, `formd_models.py`)

| File | Content |
|---|---|
| `formd_match_review.csv` | One row per matched sponsor name: match type and score, the issuer name shown for review, strict-name flag and hand-review decision, `accepted`, own CIKs (`;`-separated when pooled), numbers of candidate names, own CIKs and own names, first and last filing year, filings and largest amount sold under the main dating rule, the two sensitivity datings (`formd_first_year_own`, `formd_first_year_cik`), and the reviewed candidate's own first year and filings |
| `formd_sponsors.csv` | Accepted matches: one row per normalised sponsor name with the three first-year datings |
| `cpi_u_annual.csv` | CPI-U annual averages 2000–2026 (FRED series CPIAUCSL, monthly values averaged by year; 2026 = January–September; fetched 7 Nov 2026), used to express Form D amounts in 2024 dollars |
| `formd_sponsor_offerings.csv.gz` | Every offering in an accepted sponsor's history under the main dating rule: `offering` (accession number of the first filing of the chain), CIK and issuer name at that filing, `year` (first filing), `sale_date`, `sold` (amount sold on the latest filing of the chain, USD), `equity` / `debt` / `business_combination` flags, `investors` (number already invested, latest filing), `n_filings` in the chain |
| `owners_summary.txt`, `owners_models.txt` | Owners of the sponsor from Schedules 13D/13G: linkage coverage and owner classes; selection and advancement models with the marker "a venture-capital fund among the owners" and its variants (owner at the time of going public, filing dated by the trial year, venture or crossover owner, dated Open Targets measure) |
| `owners_sponsors.csv` | One row per sponsor with a legal entity on EDGAR: CIKs, `is_registrant`, `registrant_first_year`, number of owners by class, `vc_backed`, `first_vc_year`, `vc_names` |
| `owners_pairs.csv.gz` | Sponsor × owner pairs: owner CIK, name and class, first and last filing date, number of filings, `ambiguous` (two sponsor entities in one filing) |
| `owners_review.csv`, `owners_registrant_review.csv` | Owner names by the number of sponsors they hold, with their class (the list read to write `pilot/investor_classes.tsv`); sponsor–registrant name matches with the hand decision |
| `formd_stops.txt`, `formd_stops_rates.csv` | Trial stops by the capital the sponsor had raised in Form D offerings before the trial: stops per 1,000 active trial-years 2016–21 vs 2022–25 by band with Poisson rate ratios, and trial-year logits (`formd_stops.py`) |
| `h1_mechanisms.txt` | Exploratory checks behind the small-sponsor gap in selection: support by type of evidence, novel and follow-on indications, partnerships, typical Phase 3 size of the indication, capital raised against the cost of one Phase 3, acquisitions |
| `cb_models.txt`, `cb_link_review.csv`, `cb_sponsors.csv` | Exploratory: venture rounds from the Crunchbase export of December 2015: every candidate name match with its decision, the sponsors found with the year of their first venture round and the venture funds named, selection and advancement models |
| `ritter_models.txt`, `ritter_link_review.csv`, `ritter_sponsors.csv` | Exploratory: sponsors matched to Jay Ritter's list of US IPOs (every candidate with its decision; the IPO date and venture flag of the accepted ones), agreement of the pilot's venture markers with that flag, selection and advancement models, combined venture flag |
| `formd_directors.txt`, `formd_directors_sponsors.csv` | Exploratory: venture investors on the board from the people named in Form D filings (per sponsor: years of the first filing with a venture director or a venture address, the directors matched), checks against Ritter's flag and Crunchbase, selection and advancement models |
| `vc_combined.txt` | Exploratory: one venture flag from four sources (13D/13G owners, Ritter's IPO flag, Crunchbase venture rounds, Form D boards) and the selection model with it |
| `cvc_models.txt`, `cvc_sponsors.csv` | Exploratory: selection and advancement models that separate corporate investors from independent venture funds, in Crunchbase venture rounds and among the owners of public sponsors; per sponsor: years of the first venture round with an independent fund, a corporate investor, a drug-company investor and a foundation-owned investor, and the corporate investors named |
| `vc_stops.txt`, `vc_stops_rates.csv`, `vc_stops_link_review.csv` | Exploratory: trial stops per 1,000 active trial-years in 2016–21 and 2022–25 by venture backing of the sponsor, with rate ratios and trial-year logits; every name link made for it, with hand rejections marked |
| `h1_by_modality.txt` | Exploratory: the selection model within each type of drug and the test of whether the small-sponsor gap differs between small molecules and biologics |
| `direction_models.txt`, `direction_programmes.csv.gz` | Exploratory: programmes whose drug acts in the direction the genetic evidence asks for (Open Targets direction of effect), by sponsor tier, with selection models; per programme: directional evidence, concordant, discordant, ever and before the first trial |
| `evidence_arrival_ot_gwas.txt`, `evidence_arrival_ot_all.txt` | The evidence-arrival models repeated on Open Targets 26.09 evidence (GWAS credible sets; all germline sources), under the plan in `docs/plan_evidence_arrival_ot.md` |
| `evidence_arrival_ot_gwas_venture.txt`, `evidence_arrival_ot_all_venture.txt` | The evidence-arrival contrasts with non-top-20 industry sponsors split by the combined venture flag, under the plan in `docs/plan_evidence_arrival_venture.md` |
| `evidence_arrival_ot_gwas_top2010_from2010.txt` and the files with `_top2010`, `_top2010x` or `_from2010` in their names; `top20_2010.txt` | The evidence-arrival contrast and the selection model with the top-20 group defined by 2010 sales, under the plan in `docs/plan_top20_2010.md` (primary: GWAS evidence, 2010 group, evidence years from 2010; `x` = without Teva; `_from2010` alone = the pilot's group on those pairs) |
| `ipo_models.txt`, `ipo_sponsors.csv`, `ipo_holders_log.csv` | Investors named in IPO prospectuses, under the plan in `docs/plan_ipo_prospectus.md`: the models; one row per sponsor (registrant, prospectus, IPO year, number of holders of 5% or more that are not natural persons, venture share, share of venture and crossover funds, venture holder, corporate holder, unclassified share); one row per prospectus with what the reader made of it |
| `cash_runway.txt`, `cash_runway_sponsors.csv` | Trial stops in 2022–2023 (and 2018–2019) by the sponsor's cash runway at the end of the year before, from SEC XBRL frames, under the plan in `docs/plan_cash_runway.md`; per sponsor: liquid assets, operating cash flow, runway and group at the end of 2021, the registrant used, the dates its figures refer to, its present name on EDGAR, and whether the fiscal year ends in December and the name is the sponsor's own (checks added after the first run) |
| `evidence_arrival_ot_gwas_to2022.txt`, `evidence_arrival_ot_gwas_to2022_venture.txt` | Robustness run of the two files above without the pairs whose evidence year is after 2022 |
| `evidence_arrival_ot_all_planrule.txt`, `evidence_arrival_ot_all_planrule_venture.txt` | The run on all germline sources with the wording of the plan for undated evidence (`EA_UNDATED=only`): a pair is left out only when none of its evidence carries a date |
| `evidence_arrival_ot_<set>_top20_starts.csv` | Every programme start of top-20 pharma after the evidence year of its pair (gene, indication, area, drug, type of drug, sponsor, year of the start, evidence year, year of the drug's first trial, whether it is the drug's first indication); one file per run of `evidence_arrival.py` on Open Targets evidence |
| `evidence_arrival.txt` | Exploratory: programme starts on target × indication pairs before and after the first dated genetic association, by sponsor group (fixed-effects Poisson, event study, contrast between groups, placebo) |
| `formd_summary.txt`, `formd_models.txt` | Linkage coverage by sponsor tier; selection and advancement models with the Form D flag, the amount raised before the trial (bands and log-linear among filers), the dating sensitivities, the dated Open Targets measure and the US-only comparison |

## Other

`coverage.json` (row counts at each pipeline step and the reference date `asof`), `disease_mesh.csv.gz` (disease → MeSH map),
`programme_targets.csv.gz` (the target genes of each programme: drug, MeSH indication, gene), `robust_*.csv`
(benchmark and novel-drug tables behind `robust.txt`).

The sponsor-level and link-review tables of the exploratory venture markers (`cb_link_review.csv`, `cb_sponsors.csv`,
`ritter_link_review.csv`, `ritter_sponsors.csv`, `formd_directors_sponsors.csv`, `cvc_sponsors.csv`,
`vc_stops_link_review.csv`) are not in the repository: they derive from data that is not redistributed (the
Crunchbase export, Jay Ritter's IPO list) or name individual people (directors in Form D filings). The scripts
write them next to the model output. The same holds for `ipo_holders.csv` and `ipo_holders_classified.csv` (every
row read from the tables of principal stockholders, which list directors and officers by name; the holders of 5%
or more with their class): `pilot/ipo_holders.py` and `pilot/ipo_models.py` write them from the prospectuses.
