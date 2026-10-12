"""Tapered vs untapered Whittle estimator on the same datasets (N = 50, three speed cases, 20 each; --snr 40 or 20).

Reads results/p1/fe_direct_runs/N50_<speed>_snr40.jsonl (rectangular window, all bins, floor measured
from the record: noise + leakage) and N50_<speed>_snr40_hann.jsonl (Hann taper in both the floor
estimate and the likelihood, every second bin). Rows are paired by seed key, so both estimators see
identical records. Common reference: the CRB with the true sensor-noise floor, untapered, all bins
(field crb_log_truth_truefloor_rect, computed in the Hann run for the same datasets).

Writes results/p1/fe_direct_taper_compare.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import RUN_DIR, SPEEDS, Z90, cp_interval  # noqa: E402
from src.utils.results import save_result  # noqa: E402


def load(fpath: Path) -> dict:
    return {tuple(r["seed_key"]): r for r in map(json.loads, fpath.read_text().splitlines()) if r}


def stats(rows: list[dict], ref: list[float], j: int) -> dict:
    e = np.array([r["err_log"][j] for r in rows])
    se = np.array([r["se_log_obs"][j] for r in rows])
    own = np.array([r["crb_log_truth"][j] for r in rows])
    ref = np.asarray(ref)
    rel = np.exp(e) - 1
    rmse = float(np.sqrt(np.mean(e**2)))
    k_obs = int(np.sum(np.abs(e) <= Z90 * se))
    k_ref = int(np.sum(np.abs(e) <= Z90 * ref))
    return {"bias_rel": float(rel.mean()), "bias_rel_se": float(rel.std(ddof=1) / math.sqrt(len(e))),
            "rmse_rel": rmse, "rmse_over_crb_ref": rmse / float(np.sqrt(np.mean(ref**2))),
            "rmse_over_own_nominal_crb": rmse / float(np.sqrt(np.mean(own**2))),
            "own_nominal_crb_over_ref_median": float(np.median(own / ref)),
            "se_obs_over_crb_ref_median": float(np.median(se / ref)),
            "coverage90_observed_se": k_obs / len(e), "coverage90_observed_se_ci95": cp_interval(k_obs, len(e)),
            "coverage90_crb_ref": k_ref / len(e), "coverage90_crb_ref_ci95": cp_interval(k_ref, len(e))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snr", type=int, default=40)
    snr = ap.parse_args().snr
    cells = []
    for speed in SPEEDS:
        a = load(RUN_DIR / f"N50_{speed}_snr{snr}.jsonl")
        b = load(RUN_DIR / f"N50_{speed}_snr{snr}_hann.jsonl")
        keys = sorted(set(a) & set(b))
        if not keys:
            continue
        ra, rb = [a[k] for k in keys], [b[k] for k in keys]
        cell = {"speed": speed, "n_paired": len(keys)}
        for j, nm in enumerate(("kB0", "cB")):
            ref = [r["crb_log_truth_truefloor_rect"][j] for r in rb]
            cell[nm] = {"rect_all_bins": stats(ra, ref, j), "hann_every_2nd_bin": stats(rb, ref, j),
                        "crb_ref_mean": float(np.mean(ref)),
                        "paired_rms_diff_estimates": float(np.sqrt(np.mean(
                            [(x["phi_hat"][j] - y["phi_hat"][j]) ** 2 for x, y in zip(ra, rb)])))}
        cell["floor_over_true_noise_median"] = {"rect": float(np.median([r["floor_meas_over_noise"] for r in ra])),
                                                "hann": float(np.median([r["floor_meas_over_noise"] for r in rb]))}
        cell["timing_fit_s_median"] = {"rect": float(np.median([r["wall_fit_s"] for r in ra])),
                                       "hann": float(np.median([r["wall_fit_s"] for r in rb]))}
        cells.append(cell)
        print(json.dumps(cell, indent=1), flush=True)
    save_result("p1/fe_direct_taper_compare" + ("" if snr == 40 else f"_snr{snr}"), {"cells": cells}, cfg={
        "N": 50, "snr_db": snr, "reference_crb": "true noise floor, rectangular window, all bins",
        "hann": "periodic Hann taper, power-normalised; every second DFT bin; floor from 750-950 Hz of the tapered DFT",
        "rect": "rectangular window, all bins; floor from 750-950 Hz (noise + leakage)"}, seed=20261011)


if __name__ == "__main__":
    main()
