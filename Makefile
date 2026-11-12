# Reproduce the pilot end to end. Downloads need network access and roughly 10 GB of disk.
# Usage: make data && make results    (or: make all)
PY        ?= python
DATA      ?= data
RES       ?= results
MINIKEL   ?= /tmp/genetic_support
MINIKEL_COMMIT = b84cf0580b7df1af14b2c72068ed42b5aa0c52a4

.PHONY: all data results dated approvals formd figure check lint test clean-data

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

figure:
	$(PY) pilot/figure_glance.py $(RES) figures/results_glance.png

check: lint test

lint:
	ruff check pilot tests factcheck

test:
	pytest -q

clean-data:
	rm -rf $(DATA)
