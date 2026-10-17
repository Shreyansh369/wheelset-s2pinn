# Release checklist (paper version)

Fill in at the final freeze; the Zenodo DOI goes only into `paper/doi.tex` (macro `\ZenodoDOI`), from
where the data availability statement and the cover letter take it.

## Before tagging

- [ ] All Monte Carlo runs for the paper finished; `python3 experiments/make_compute_cost.py`.
- [ ] `make reproduce` and `make check` run clean on a fresh clone with `pip install -r requirements.txt`.
- [ ] `docs/provenance.md` says PASS, or every remaining earlier-configuration item is labelled as such
      in its caption or paragraph and none is in the abstract, highlights or conclusions.
- [ ] `docs/freeze_check.md`: every number in the abstract, highlights, conclusions and cover letter
      matches its macro.
- [ ] Abstract ≤ 250 words; highlights 3–5 bullets of ≤ 85 characters (`paper/submission/build/CHECKS.txt`).
- [ ] `docs/reference_check.md`: every reference checked by hand (initials and date in the last column).
- [ ] Author names, affiliations, ORCIDs, CRediT roles, competing interests and acknowledgements filled
      in (`paper/authors.tex`, `paper/backmatter.tex`); AI declaration wording confirmed.
- [ ] `legacy/` contains no third-party code; `git submodule status` is empty.
- [ ] No third-party PDFs tracked (`git ls-files '*.pdf'` shows only figures, the review drafts and the
      G0 report in legacy/).

## Tag

- Tag name: `mssp-v1.0` (resubmissions: `mssp-v1.1`, ...).
- Commit hash: `<fill in: git rev-parse mssp-v1.0>`.
- `git tag -a mssp-v1.0 -m "Code and results for the MSSP submission" && git push origin mssp-v1.0`

## Files to deposit at Zenodo (GitHub release archive of the tag)

- `src/`, `experiments/`, `scripts/`, `tests/`, `config/` (with `snapshots/` and `provenance.yaml`)
- `results/` (JSON summaries and JSONL run files; no large arrays)
- `figures/`, `paper/` (LaTeX source, `generated/`, `submission/`), compiled `paper/main.pdf`
- `docs/` (parameter sources, provenance, reference check, compute cost, this checklist)
- `README.md`, `Makefile`, `requirements.txt`, `pyproject.toml`
- `legacy/` may be included for the record; it contains no third-party code
- Excluded: third-party PDFs (`.gitignore`), the S²-PINN code (not in the repository)

## After deposit

- [ ] Put the DOI into `paper/doi.tex`, rebuild (`make reproduce`, `make -C paper submission`), commit.
- [ ] Check that the Zenodo record shows the tag and commit hash above.
