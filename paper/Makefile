# Regenerates every table and number from results/ and config/, then builds the PDF.
PY ?= python3
all: main.pdf
generated/numbers.tex: FORCE
	cd .. && $(PY) experiments/make_tables.py && $(PY) experiments/make_paper_numbers.py
main.pdf: generated/numbers.tex main.tex abstract.tex authors.tex sec1_intro.tex sec2_model.tex sec3_method.tex sec4_results.tex sec5_discussion.tex sec6_conclusions.tex declarations.tex refs.bib
	latexmk -pdf -interaction=nonstopmode main.tex
# Self-contained Overleaf project: sources, generated numbers, tables and figures in one flat tree.
overleaf: main.pdf
	rm -rf build/overleaf && mkdir -p build/overleaf/tables build/overleaf/figures build/overleaf/generated
	cp main.tex abstract.tex authors.tex sec*.tex declarations.tex refs.bib build/overleaf/
	cp generated/numbers.tex build/overleaf/generated/
	cp ../results/tables/*.tex build/overleaf/tables/
	cp ../figures/*.pdf build/overleaf/figures/
	cp main.bbl build/overleaf/
	cd build/overleaf && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null && latexmk -c >/dev/null && rm -f main.pdf
	cd build && rm -f wheelset_paper_overleaf.zip && zip -qr wheelset_paper_overleaf.zip overleaf
clean:
	latexmk -C
FORCE:
.PHONY: all clean overleaf FORCE
