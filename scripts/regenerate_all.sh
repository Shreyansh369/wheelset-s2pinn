#!/usr/bin/env bash
# Full regeneration of every result at the frozen (or pinned headline) configuration, from scratch.
# Long: see docs/compute_cost.md for the recorded cost of each study. Every Monte Carlo script is
# resumable (rows are appended to a .jsonl file and skipped if present) and stops itself after about
# 110 minutes, so each command below can be re-run until its rows are complete and run in parallel
# with the others on separate cores. Results from an earlier configuration (listed in
# docs/provenance.md) are not regenerated here: they are stored, and reproducible by checking out the
# commit recorded in their provenance.git_commit field.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}
rep() { for _ in 1 2 3 4 5 6; do "$@"; done; }       # repeat a resumable command until it has caught up

# reference model, verification, transfer functions, bounds
$PY experiments/p1_verify.py && $PY experiments/gate_report.py G1
rm -f results/p2/fig1_transfer.json                    # make_figures.py recomputes it at the frozen config
$PY experiments/p2_multiwheel.py --bound
$PY experiments/p3_exponent_bound.py
$PY experiments/p3_bearing_clearance.py
$PY experiments/p4_contact_hertz.py
$PY experiments/p4_mdc_bounds.py
rep $PY experiments/p4_sweep.py --run && $PY experiments/p4_sweep.py --summarise

# model-form sensitivity and foundation drift (pseudo-true fits)
rep $PY experiments/p2_model_form_mw.py --sensitivity && $PY experiments/p2_model_form_mw.py --summarise
rep $PY experiments/p2_relative_coest_drift.py --drift && $PY experiments/p2_relative_coest_drift.py --summarise-freight

# headline Monte Carlo (pinned headline configuration) and its simulation calibration
for j in 0 10 20 30 40 50 60 70 80 90; do
  WHEELSET_CONFIG_DIR=config/snapshots/headline_freight_v1 rep $PY experiments/p3_headline_v2.py --kb 120 --attributed --label _freight --j0 $j --j1 $((j + 10))
done
WHEELSET_CONFIG_DIR=config/snapshots/headline_freight_v1 $PY experiments/p3_headline_v2.py --kb 120 --attributed --label _freight --aggregate
$PY experiments/p3_calibrated.py
rep $PY experiments/p4_ignore_coupling.py && $PY experiments/p4_ignore_coupling.py --summarise

# drift Monte Carlo, 20 pairs per estimator
for j in $(seq 0 19); do rep $PY experiments/p3_validation_mc.py --drift --tag _freight --j0 $j --j1 $((j + 1)); done
$PY experiments/p3_validation_mc.py --summarise

# nonlinear contact and generator check
for m in nl lin; do rep $PY experiments/p4_inverse_crime.py --mode $m --j0 0 --j1 20; done
rep $PY experiments/p4_inverse_crime.py --mode pairs --j0 0 --j1 20
rep $PY experiments/p4_inverse_crime.py --mode fd --j0 0 --j1 10
rep $PY experiments/p4_inverse_crime.py --mode lin --pad 1.6 --tag _pad1.6 --j0 0 --j1 10
$PY experiments/p4_generator_check.py && $PY experiments/p4_generator_expper.py
$PY experiments/p4_inverse_crime.py --summarise

# payload-dependent primary suspension and payload bands
$PY experiments/p4_primary_damping.py --pseudo && rep $PY experiments/p4_primary_damping.py --pairs --j0 0 --j1 3
$PY experiments/p4_primary_damping.py --summarise
$PY experiments/p4_banded.py --bounds
for b in empty laden; do $PY experiments/p4_banded.py --pseudo --band $b; done
for f in 1.0 0.5 2.0; do $PY experiments/p4_banded.py --pseudo --band laden --cb-fixed $f; done
for j in $(seq 0 19); do rep $PY experiments/p4_banded.py --pairs --band empty --j0 $j --j1 $((j + 1)); done
for j in $(seq 0 4); do rep $PY experiments/p4_banded.py --pairs --band laden --j0 $j --j1 $((j + 1)); done
for j in $(seq 0 4); do rep $PY experiments/p4_banded.py --pairs --band laden --cb-fixed 1.0 --j0 $j --j1 $((j + 1)); done
$PY experiments/p4_banded.py --summarise

# bias diagnosis on the headline datasets and the multi-wheel Monte Carlo
for v in kb30 snr60 exact K4 K1; do rep $PY experiments/p4_bias_diag_y25.py --variant $v --j0 0 --j1 10; done
rep $PY experiments/p4_bias_diag_y25.py --robust --j0 0 --j1 50 && $PY experiments/p4_bias_diag_y25.py --summarise
for w in 2 4 8; do rep timeout 6900 $PY experiments/p2_multiwheel.py --mc --n-data 10 --tag _y25 --wheels $w; done
$PY experiments/p2_multiwheel.py --aggregate --tag _y25

# tables, figures, numbers, checks, PDF
make reproduce
