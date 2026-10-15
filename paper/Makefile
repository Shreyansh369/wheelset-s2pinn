# Regenerates every table and number from results/ and config/, then builds the PDF.
PY ?= python3
all: main.pdf
generated/numbers.tex: FORCE
	cd .. && $(PY) experiments/make_tables.py && $(PY) experiments/make_paper_numbers.py
main.pdf: generated/numbers.tex main.tex abstract.tex authors.tex sec1_intro.tex sec2_model.tex sec3_method.tex sec4_results.tex sec5_discussion.tex sec6_conclusions.tex backmatter.tex refs.bib
	latexmk -pdf -interaction=nonstopmode main.tex
# MSSP submission folder (submission/build): sources, Figure_N.pdf in citation order, tables, highlights
# (.docx, .txt), cover letter, compiled PDF for checking, CHECKS.txt; plus a zip for Overleaf.
submission: main.pdf
	cd .. && $(PY) experiments/make_submission.py
	cd submission && rm -f wheelset_mssp_submission.zip && zip -qr wheelset_mssp_submission.zip build
clean:
	latexmk -C
FORCE:
.PHONY: all clean submission FORCE
