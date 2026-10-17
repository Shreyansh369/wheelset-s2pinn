# Top-level targets. `make reproduce` rebuilds every table, figure and number of the paper from the stored
# results/ (minutes), checks provenance and builds paper/main.pdf. `make montecarlo` regenerates the
# stored results themselves (days of single-core time; see docs/compute_cost.md and scripts/regenerate_all.sh).
PY ?= python3

reproduce:
	$(PY) experiments/make_tables.py
	$(PY) experiments/make_figures.py
	$(PY) experiments/make_paper_numbers.py
	$(MAKE) -C paper main.pdf
	$(PY) experiments/make_freeze_check.py
	$(PY) experiments/make_provenance_check.py || echo "provenance check FAILED: see docs/provenance.md"

check:
	$(PY) experiments/make_provenance_check.py
	$(PY) experiments/make_freeze_check.py
	$(PY) experiments/make_reference_check.py
	$(MAKE) -C paper submission

test:
	$(PY) -m pytest -q tests

montecarlo:
	scripts/regenerate_all.sh

.PHONY: reproduce check test montecarlo
