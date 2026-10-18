#!/usr/bin/env bash
# Final regeneration of every summary, table, figure and number from the stored result rows.
# Runs only on a fully clean tree (no modified or untracked files anywhere, results/ included), so that the
# git commit recorded in every summary identifies both the code and the rows it was computed from; each
# summary also records the SHA-256 of every rows file it read (provenance.input_hashes). No Monte Carlo is
# run here: the rows come from scripts/regenerate_all.sh (or the stored results).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}
if [ -n "$(git status --porcelain)" ]; then
  echo "final_regenerate: the tree is not clean (results/ included); commit or remove these first:" >&2
  git status --porcelain >&2
  exit 1
fi
echo "final_regenerate: clean tree at $(git rev-parse HEAD)"

# rewritten so that they record the values-v2 config hash (no Monte Carlo, minutes): FE verification and
# gate G1, and the Fig. 1 transfer functions (make_figures.py recomputes them when the file is absent)
$PY experiments/p1_verify.py && $PY experiments/gate_report.py G1
rm -f results/p2/fig1_transfer.json

# summaries, in the dependency order of scripts/regenerate_all.sh
$PY experiments/p4_sweep.py --summarise
$PY experiments/p2_model_form_mw.py --summarise
$PY experiments/p2_relative_coest_drift.py --summarise-freight
$PY experiments/p3_headline_v2.py --kb 120 --attributed --label _frozen10 --ten --aggregate
$PY experiments/p4_ignore_coupling.py --summarise
$PY experiments/p4_gain_y25.py --summarise
$PY experiments/p3_validation_mc.py --summarise
$PY experiments/p3_calibrated.py
$PY experiments/p4_inverse_crime.py --summarise
$PY experiments/p4_primary_damping.py --summarise
$PY experiments/p4_banded.py --summarise
$PY experiments/p4_bias_diag_y25.py --summarise
$PY experiments/p2_multiwheel.py --aggregate --tag _y25

# tables, figures, numbers, PDF and checks
make reproduce
echo "final_regenerate: done; review 'git diff --stat' and commit the regenerated files"
