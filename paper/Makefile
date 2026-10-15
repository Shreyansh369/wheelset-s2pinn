# Regenerates every table and number from results/ and config/, then builds the PDF.
PY ?= python3
all: main.pdf
generated/numbers.tex: FORCE
	cd .. && $(PY) experiments/make_tables.py && $(PY) experiments/make_paper_numbers.py
main.pdf: generated/numbers.tex main.tex sec1_intro.tex sec2_model.tex sec3_method.tex sec4_results.tex sec5_discussion.tex refs.bib
	latexmk -pdf -interaction=nonstopmode main.tex
clean:
	latexmk -C
FORCE:
.PHONY: all clean FORCE
