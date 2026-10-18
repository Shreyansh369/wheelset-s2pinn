# MDPI (Sensors) build: fallback target

The MSSP version (`paper/main.tex`, Elsevier `cas-sc`) is the primary one. This folder builds the same paper
in the MDPI LaTeX template for *Sensors*, without changing anything in `paper/`.

## Build

1. Download the MDPI LaTeX template from https://www.mdpi.com/authors/latex and unpack it. It is not on CTAN
   and is not stored here. The cloud session that wrote this script could not reach mdpi.com.
2. `make -C paper` (or `make reproduce`) so that `paper/generated/numbers.tex` and `results/tables/` are current.
3. `python3 paper/alt_mdpi/make_mdpi.py --template /path/to/unpacked/template`
   (the folder that contains `Definitions/mdpi.cls`; add `--no-pdf` for the folder and zip only).

Output (git-ignored): `paper/alt_mdpi/build/` with `main_mdpi.tex` and `main_mdpi.pdf`, plus
`paper/alt_mdpi/wheelset_mdpi_overleaf.zip`. To build on Overleaf, upload the zip, set the main document to
`main_mdpi.tex` and the compiler to pdfLaTeX.

## What the script does

- Wraps the unchanged `sec1`–`sec6`, the abstract, `generated/numbers.tex`, the tables, the figures and
  `refs.bib` in MDPI front matter (`\Title`, `\Author`, `\address`, `\abstract`, `\keyword`). Author slots
  are placeholders, as in `paper/authors.tex`.
- Maps `paper/backmatter.tex` to the MDPI back matter: CRediT → `\authorcontributions`, Funding, Data
  availability, Acknowledgements (with the generative-AI declaration appended, since MDPI asks for it there),
  competing interest → `\conflictsofinterest`.
- Uses `Definitions/mdpi.bst` when the template has it, else `unsrtnat`.

## Before an MDPI submission (not done)

- **Abstract:** MDPI asks for about 200 words in one paragraph. The current abstract is about 245–250 words
  (the count depends on how macros are counted), and the script prints the count. The Step-8 STOP applies to
  the abstract.
- Author contributions in MDPI wording (CRediT roles are accepted), and the MDPI conflict-of-interest sentence.
- No highlights. A graphical abstract is optional.
- Tested only against a stub class that defines the MDPI front-matter macros, not the real `mdpi.cls`.
  Check the first real build for clashes (MDPI loads its own packages and sets its own float and caption
  styles).
