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
| `h4_biology.txt` | Ex-ante support of trials stopped for financial or strategic reasons vs completed trials |
| `sbir_match_review.csv` | Every sponsor ↔ SBIR/STTR awardee match with both names, score and decision |
| `sbir_summary.txt`, `sbir_models.txt` | Linkage coverage and models of prior SBIR/STTR funding |

## Other

`coverage.json` (row counts at each pipeline step), `disease_mesh.csv.gz` (disease → MeSH map), `robust_*.csv`
(benchmark and novel-drug tables behind `robust.txt`).
