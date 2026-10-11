"""FE-direct Whittle estimator: Monte Carlo over random datasets (scenario a, option iv).

For each (N passes, speed distribution) cell, 20 random datasets are generated from the reference FE
model (src/inverse/whittle.generate_pass, direct solves on 0.25 Hz). Each dataset draws a new roughness
realisation, new per-sub-band level deviations (3 dB 1-sigma, K = 16 per one-third octave), pass
speeds, payloads (uniform 5.5-22.5 t), WIM errors (3%) and sensor noise. The estimator
(src/inverse/whittle.WhittleFit, modal H on 0.5 Hz, 25 payload nodes) fits log kB0 and log cB by
maximum likelihood with all sub-band levels and per-pass log W profiled out, from the nominal start
(kB0, cB) = (1e9 N/m, 5e3 N s/m). Truth: kB0 = 0.85e9 (15% stiffness loss), cB = 6e3.

Recorded per dataset: estimate, observed profile-information SE, expected-Fisher CRB at the truth
(same bins, floors, speeds, payloads), wall time per likelihood evaluation and per fit.
Rows are appended to results/p1/fe_direct_runs/<cell>.jsonl (resumable); --aggregate writes
results/p1/fe_direct.json. Single-threaded.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.stats import beta  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_bound_robustness import ISO3095_FIG2_DB, ISO_SOURCE  # noqa: E402
from src.analysis.bound_scan import Scenario, ScenarioModel  # noqa: E402
from src.inverse.whittle import ModalH, Roughness, WhittleFit, generate_pass  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

KMH = 1 / 3.6
SPEEDS = {"fixed_100": (100.0, 100.0), "uniform_95_105": (95.0, 105.0), "uniform_60_110": (60.0, 110.0)}
TRUTH = {"kB0": 0.85e9, "cB": 6e3}
START = {"kB0": 1e9, "cB": 5e3}
K_SUB, G_SD_DB, WIM, W_RANGE = 16, 3.0, 0.03, (5.5, 22.5)
W_NODES = np.exp(np.linspace(math.log(5.0), math.log(24.0), 25))
F_GRID = np.arange(45.0, 702.0, 0.5)
Z90 = 1.6448536269514722
RUN_DIR = RESULTS_DIR / "p1" / "fe_direct_runs"


def setup():
    p = load_params()
    sm = ScenarioModel(p, Scenario(name="a_iv", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=700, fs=2000,
                                   forcing_spec={}, targets=["log_kB0"], kH0=1.4e9))
    thb = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": p.r0}
    bands = np.array(sorted(ISO3095_FIG2_DB))
    rough = Roughness(bands, np.array([ISO3095_FIG2_DB[b] for b in bands]), K=K_SUB)
    return sm, thb, rough, ModalH(sm, W_NODES, F_GRID)


def one_dataset(sm, thb, rough, mh, N, speed, snr_db, seed_key) -> dict:
    rng = np.random.default_rng(np.random.SeedSequence(seed_key))
    g_true = 10 ** (rng.normal(0, G_SD_DB, rough.n_sub) / 10)
    lo, hi = SPEEDS[speed]
    Vs = rng.uniform(lo, hi, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    th_true = dict(thb, **TRUTH)
    t0 = time.perf_counter()
    passes = [generate_pass(sm, th_true, rough, g_true, V, W, snr_db, rng) for V, W in zip(Vs, Ws)]
    t_gen = time.perf_counter() - t0
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    floor_ratio = float(np.mean([q["e_noise"] / q["e_noise_true"] for q in passes]))
    fit = WhittleFit(passes, Wm, WIM, rough, mh, thb)
    r = fit.fit(np.log([START["kB0"], START["cB"]]))
    crb = fit.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g_true), np.log(Ws))
    err = [r["phi"][0] - math.log(TRUTH["kB0"]), r["phi"][1] - math.log(TRUTH["cB"])]
    return {"N": N, "speed": speed, "snr_db": snr_db, "seed_key": list(seed_key), "phi_hat": r["phi"],
            "err_log": err, "se_log_obs": r["se_log"], "crb_log_truth": crb["crb_log"],
            "corr_kB0_cB_crb": crb["corr_kB0_cB"], "n_params": crb["n_params"],
            "converged": r["converged"], "n_iter": r["n_iter"], "n_eval": r["n_eval"],
            "s_per_eval": r["s_per_eval"], "wall_fit_s": r["wall_fit_s"], "wall_generate_s": t_gen,
            "bins_total": int(sum(len(c2) for c2 in fit.c2)), "n_subbands_seen": int(fit.used.size),
            "floor_meas_over_noise": floor_ratio, "speed_std_kmh": float(np.std(Vs) / KMH)}


def cp_interval(k: int, n: int, a: float = 0.05) -> list[float]:
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 1, n - k))
    return [lo, hi]


def summarise(rows: list[dict]) -> dict:
    out = {"n_datasets": len(rows)}
    for j, nm in enumerate(("kB0", "cB")):
        e = np.array([r["err_log"][j] for r in rows])
        se = np.array([r["se_log_obs"][j] for r in rows])
        crb = np.array([r["crb_log_truth"][j] for r in rows])
        rel = np.exp(e) - 1
        rmse = float(np.sqrt(np.mean(e**2)))
        cov_obs = int(np.sum(np.abs(e) <= Z90 * se))
        cov_crb = int(np.sum(np.abs(e) <= Z90 * crb))
        out[nm] = {"bias_rel": float(np.mean(rel)), "bias_rel_se": float(np.std(rel, ddof=1) / math.sqrt(len(e))),
                   "rmse_rel": rmse, "crb_rel_mean": float(np.mean(crb)), "rmse_over_crb": rmse / float(np.sqrt(np.mean(crb**2))),
                   "max_abs_rel_err": float(np.max(np.abs(rel))),
                   "se_obs_over_crb_median": float(np.median(se / crb)),
                   "coverage90_wald_observed": cov_obs / len(e), "coverage90_wald_observed_ci95": cp_interval(cov_obs, len(e)),
                   "coverage90_wald_crb": cov_crb / len(e), "coverage90_wald_crb_ci95": cp_interval(cov_crb, len(e))}
    out["timing"] = {"s_per_eval_median": float(np.median([r["s_per_eval"] for r in rows])),
                     "wall_fit_s_median": float(np.median([r["wall_fit_s"] for r in rows])),
                     "wall_fit_s_max": float(np.max([r["wall_fit_s"] for r in rows])),
                     "n_eval_median": float(np.median([r["n_eval"] for r in rows])),
                     "wall_generate_s_median": float(np.median([r["wall_generate_s"] for r in rows]))}
    out["all_converged"] = bool(all(r["converged"] for r in rows))
    out["floor_meas_over_noise_median"] = float(np.median([r["floor_meas_over_noise"] for r in rows]))
    return out


def aggregate() -> None:
    cells = []
    for fpath in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(line) for line in fpath.read_text().splitlines() if line.strip()]
        if rows:
            cells.append({"cell": fpath.stem, "N": rows[0]["N"], "speed": rows[0]["speed"],
                          "snr_db": rows[0]["snr_db"], **summarise(rows)})
    wall = sum(json.loads(l)["wall_fit_s"] + json.loads(l)["wall_generate_s"]
               for fpath in RUN_DIR.glob("*.jsonl") for l in fpath.read_text().splitlines() if l.strip())
    save_result("p1/fe_direct", {"cells": cells}, cfg={
        "truth": TRUTH, "start": START, "K_per_third_octave": K_SUB, "subband_level_sd_db": G_SD_DB,
        "wim_sigma": WIM, "W_range_t": W_RANGE, "speeds_kmh": SPEEDS, "roughness_source": ISO_SOURCE,
        "estimator_H": "complex-modal, 25 log-W nodes (cubic), 0.5 Hz grid (linear)",
        "generator_H": "direct FE solves, 0.25 Hz grid, 4x-fine roughness realisation, rectangular 20-rev record",
        "coverage": "Wald 90% from observed profile information (and from the expected-Fisher CRB at the truth); "
                    "Clopper-Pearson 95% intervals on the coverage fraction",
        "rows_dir": str(RUN_DIR.relative_to(RESULTS_DIR))}, seed=20261011, wall_seconds=wall)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, nargs="+", default=[50])
    ap.add_argument("--speeds", nargs="+", default=list(SPEEDS))
    ap.add_argument("--snr", type=float, default=40.0)
    ap.add_argument("--n-data", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=20261011)
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    if a.aggregate:
        aggregate()
        return
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    sm, thb, rough, mh = setup()
    for N in a.N:
        for si, speed in enumerate(SPEEDS):
            if speed not in a.speeds:
                continue
            fpath = RUN_DIR / f"N{N}_{speed}_snr{int(a.snr)}.jsonl"
            done = {tuple(json.loads(l)["seed_key"]) for l in fpath.read_text().splitlines() if l.strip()} \
                if fpath.exists() else set()
            for j in range(a.n_data):
                key = (a.seed_base, N, si, int(a.snr), j)
                if key in done:
                    continue
                row = one_dataset(sm, thb, rough, mh, N, speed, a.snr, key)
                with fpath.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"N={N} {speed} j={j} err_kB0={row['err_log'][0]:+.4f} se={row['se_log_obs'][0]:.4f} "
                      f"crb={row['crb_log_truth'][0]:.4f} err_cB={row['err_log'][1]:+.3f} fit={row['wall_fit_s']:.1f}s",
                      flush=True)


if __name__ == "__main__":
    main()
