# Reproduce the pilot end to end. Downloads need network access and roughly 10 GB of disk.
# Usage: make data && make results    (or: make all)
PY        ?= python
DATA      ?= data
RES       ?= results
MINIKEL   ?= /tmp/genetic_support
MINIKEL_COMMIT = b84cf0580b7df1af14b2c72068ed42b5aa0c52a4

.PHONY: all data results dated approvals formd owners mechanisms venture biology runway figure check lint test clean-data

all: data results figure check

data: $(DATA)/ot/RELEASE $(DATA)/ctgov_all.csv $(MINIKEL)/data $(DATA)/nih_sbir_sttr.csv

$(DATA)/ot/RELEASE:
	$(PY) pilot/fetch_opentargets.py $(DATA)/ot

$(DATA)/ctgov_all.csv:
	$(PY) pilot/fetch_ctgov.py all $@

$(MINIKEL)/data:
	git clone https://github.com/ericminikel/genetic_support $(MINIKEL)
	git -C $(MINIKEL) checkout $(MINIKEL_COMMIT)

$(DATA)/nih_sbir_sttr.csv:
	$(PY) pilot/fetch_reporter_sbir.py $@ 2000 2025

results:
	$(PY) pilot/build_panel26.py $(DATA)/ot $(MINIKEL)/data $(RES)
	$(PY) pilot/robust26.py $(RES)
	$(PY) pilot/khb26.py $(RES) > $(RES)/khb.txt
	$(PY) pilot/rq2_stops.py $(DATA)/ctgov_all.csv $(RES)
	$(PY) pilot/rq2_rr.py $(RES)
	$(PY) factcheck/sponsor_names_audit.py $(DATA)/ctgov_all.csv $(RES)
	$(PY) factcheck/sponsor_missing_acquisitions.py $(DATA)/ctgov_all.csv $(RES)
	$(PY) pilot/h4_biology.py $(DATA)/ot $(RES) $(DATA)/ctgov_all.csv $(MINIKEL)/data
	$(PY) pilot/sbir_link.py $(DATA)/nih_sbir_sttr.csv $(DATA)/ctgov_all.csv $(RES)
	$(PY) pilot/sbir_models.py $(RES)

dated:  # needs Falaguera et al. evidence (Zenodo 15922783) in $(DATA)/falaguera/evidence_dated
	$(PY) pilot/gs_ot_dated.py $(RES) $(DATA)/ot $(DATA)/falaguera/evidence_dated $(MINIKEL)/data
	$(PY) pilot/khb26.py $(RES) > $(RES)/khb.txt
	$(PY) pilot/khb26.py $(RES) gs_ot_ante gs_ot_entries.csv.gz >> $(RES)/khb.txt
	$(PY) pilot/sbir_models.py $(RES)  # again: adds the block with the dated measure
	$(PY) pilot/h4_biology.py $(DATA)/ot $(RES) $(DATA)/ctgov_all.csv $(MINIKEL)/data $(DATA)/falaguera/evidence_dated

approvals:  # approval dates from EMA/PMDA reports and ChEMBL; the ChEMBL extract used is kept in results/
	$(PY) pilot/fetch_chembl_approval.py $(DATA)/chembl_first_approval.csv
	$(PY) pilot/approval_dates.py $(DATA)/ot $(RES) $(DATA)/chembl_first_approval.csv

formd:  # SEC asks for a contact: SEC_USER_AGENT="Your Name you@example.org" make formd
	$(PY) pilot/fetch_formd.py $(DATA)/formd
	$(PY) pilot/formd_link.py $(DATA)/formd/formd_biopharma.csv.gz $(RES)
	$(PY) pilot/formd_models.py $(RES)
	$(PY) pilot/formd_stops.py $(DATA)/ctgov_all.csv $(RES)

owners:  # SEC asks for a contact: SEC_USER_AGENT="Your Name you@example.org" make owners
	$(PY) pilot/fetch_edgar_owners.py $(DATA)/edgar 2001 2026
	$(PY) pilot/owners_link.py $(DATA)/edgar $(RES)
	$(PY) pilot/owners_models.py $(RES)

mechanisms:  # exploratory checks behind the selection gap; needs the Form D results (make formd)
	$(PY) pilot/fetch_ctgov_enrollment.py $(DATA)/ctgov_enrollment.csv
	$(PY) pilot/extract_molecule_synonyms.py $(DATA)/ot $(DATA)/ot_molecule_synonyms.csv.gz
	$(PY) pilot/h1_mechanisms.py $(RES) $(DATA)/ctgov_all.csv $(DATA)/ctgov_enrollment.csv $(DATA)/ot_molecule_synonyms.csv.gz

venture:  # exploratory venture markers (SEC_USER_AGENT="Your Name you@example.org" make venture); needs make formd and make owners, the Crunchbase export of December 2015 in $(DATA)/crunchbase/cb2015 and Jay Ritter's IPO-age.xlsx in $(DATA)/ritter (neither is redistributed here)
	$(PY) pilot/cb_models.py $(RES) $(DATA)/crunchbase/cb2015
	$(PY) pilot/ritter_models.py $(RES) $(DATA)/ritter/IPO-age.xlsx $(RES)
	$(PY) pilot/fetch_formd_people.py $(DATA)/formd
	$(PY) pilot/formd_directors.py $(RES) $(DATA)/formd $(RES)
	$(PY) pilot/vc_combined.py $(RES)
	$(PY) pilot/cvc_models.py $(RES) $(DATA)/crunchbase/cb2015
	$(PY) pilot/vc_stops.py $(DATA)/ctgov_all.csv $(RES) $(DATA)/crunchbase/cb2015 $(DATA)/ritter/IPO-age.xlsx $(DATA)/formd

biology:  # exploratory: the gap by type of drug, direction of effect, arrival of genetic evidence (the last needs pyfixest and Python >= 3.10)
	$(PY) pilot/h1_by_modality.py $(RES)
	OT_DATASETS=evidence_gene_burden,evidence_eva,evidence_orphanet,evidence_gene2phenotype $(PY) pilot/fetch_opentargets.py $(DATA)/ot_gen
	$(PY) pilot/extract_ot_direction.py $(DATA)/ot $(DATA)/ot_gen $(DATA)/ot_direction
	$(PY) pilot/direction_models.py $(RES) $(MINIKEL)/data $(DATA)/ot_direction
	$(PY) pilot/evidence_arrival.py $(RES) $(MINIKEL)/data
	OT_DATASETS=evidence_gwas_credible_sets,evidence_clingen,evidence_genomics_england,evidence_uniprot_variants $(PY) pilot/fetch_opentargets.py $(DATA)/ot_gen
	$(PY) pilot/extract_ot_dated.py $(DATA)/ot $(DATA)/ot_gen $(DATA)/ot_direction/ot_dated_evidence.csv.gz
	$(PY) pilot/evidence_arrival.py $(RES) $(MINIKEL)/data $(DATA)/ot_direction/ot_dated_evidence.csv.gz gwas
	$(PY) pilot/evidence_arrival.py $(RES) $(MINIKEL)/data $(DATA)/ot_direction/ot_dated_evidence.csv.gz all
	EA_LAST_EVIDENCE_YEAR=2022 $(PY) pilot/evidence_arrival.py $(RES) $(MINIKEL)/data $(DATA)/ot_direction/ot_dated_evidence.csv.gz gwas
	EA_UNDATED=only $(PY) pilot/evidence_arrival.py $(RES) $(MINIKEL)/data $(DATA)/ot_direction/ot_dated_evidence.csv.gz all

runway:  # cash runway and trial stops (SEC_USER_AGENT="Your Name you@example.org" make runway); needs make owners and the trial table of h4_biology.py
	$(PY) pilot/fetch_sec_frames.py $(DATA)/sec_frames
	$(PY) pilot/cash_runway.py $(DATA)/ctgov_all.csv $(RES) $(DATA)/sec_frames/sec_frames.csv.gz $(RES)/h4_trials.csv.gz

figure:
	$(PY) pilot/figure_glance.py $(RES) figures/results_glance.png
	$(PY) pilot/figure_main.py $(RES) figures/main_results.png
	$(PY) pilot/figure_evidence_arrival.py $(RES) figures/evidence_arrival.png

check: lint test

lint:
	ruff check pilot tests factcheck

test:
	pytest -q

clean-data:
	rm -rf $(DATA)
