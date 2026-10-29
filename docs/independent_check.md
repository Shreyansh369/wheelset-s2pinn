# Independent check by the second author

Checker: ______________________ (name)     Date: ______________     Commit checked: ______________

Do the three items below on your own machine, not in the authors' working copy. Record every finding under
the item and give each item a pass/fail. Send this file back with the results filled in.

## 1. Reproduction from a clean clone of `main`

```
git clone https://github.com/Shreyansh369/wheelset-s2pinn.git && cd wheelset-s2pinn
pip install -r requirements.txt
make test
make reproduce
```

- [ ] `make test` passes (note the number of tests and any failure).
- [ ] `make reproduce` finishes without error and ends with "provenance: PASS".
- [ ] The regenerated tables match the PDF, number for number:
  - `results/tables/table1_parameters.tex` (Table __ of the PDF)
  - `results/tables/table8_mdc.tex` (Table __ of the PDF)
  - `results/tables/table11_drift.tex` (Table __ of the PDF)
  
  The PDF table numbers are filled in at the final regeneration (`docs/STATUS.md`).

Findings:

Result: PASS / FAIL

## 2. Bibliography

For every entry of `paper/refs.bib`, check it against its DOI (https://doi.org/...) or its URL: title,
authors (all names and their order), year, journal or venue, volume, issue and pages. Mark entries with no
DOI or URL. `docs/reference_check.md` lists what the authors already checked; check independently of it.

| Key | DOI/URL resolves | Title | Authors | Year | Journal/venue, volume, pages | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |

Result: PASS / FAIL

## 3. Reading of the full PDF

Read `paper/main.pdf` from start to end. Record errors (wrong numbers, inconsistent statements between
sections, wrong cross-references, typos) and unclear wording, with the page and line.

| Page | Line or location | Finding | Suggested change |
|---|---|---|---|
| | | | |

Result: PASS / FAIL

## Sign-off

All three items pass: YES / NO          Signature: ______________________
