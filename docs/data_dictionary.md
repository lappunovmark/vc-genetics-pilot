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
| `rq2_did.txt` | Difference-in-differences and event-study logits |
| `rq2_label_sample.csv` | Stratified sample of `why_stopped` texts drawn for hand coding |
| `rq2_hand_labels.csv` | Hand labels for the tuning and held-out sets, with classifier v1 and v3 output |

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
| `formd_sponsor_offerings.csv.gz` | Every offering in an accepted sponsor's history under the main dating rule: `offering` (accession number of the first filing of the chain), CIK and issuer name at that filing, `year` (first filing), `sale_date`, `sold` (amount sold on the latest filing of the chain, USD), `equity` / `debt` / `business_combination` flags, `investors` (number already invested, latest filing), `n_filings` in the chain |
| `formd_summary.txt`, `formd_models.txt` | Linkage coverage by sponsor tier; selection and advancement models with the Form D flag, the amount raised before the trial (bands and log-linear among filers), the dating sensitivities, the dated Open Targets measure and the US-only comparison |

## Other

`coverage.json` (row counts at each pipeline step and the reference date `asof`), `disease_mesh.csv.gz` (disease → MeSH map), `robust_*.csv`
(benchmark and novel-drug tables behind `robust.txt`).
