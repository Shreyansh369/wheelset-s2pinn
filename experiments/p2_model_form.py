"""Phase 2 (1): robustness of the FE-direct estimator to model-form error (scenario a, option iv).

Data come from the reference FE model with perturbed inputs the estimator does not know:
contact stiffness kH0 (x0.7, x1.3), rail-oscillator stiffness k_r (x0.7, x1.3) and mass m_r (x1.3),
axle damping (x0.5, x2), and pass-to-pass track variation (k_r lognormal 15%, kH0 lognormal 10%,
drawn per pass). Two estimators fit every dataset:
  "nominal": (kB0, cB) free, everything else at its nominal value;
  "coest":   (kB0, cB, kH0, k_r) free (one global value each).
Datasets are paired across cases (the seed key does not include the case), so differences between
cases come from the model perturbation alone. N = 50, speeds uniform 60-110 km/h, payload uniform
5.5-22.5 t with 3% WIM error, SNR 40 dB, K = 16 sub-bands with 3 dB level deviations.
Truth: kB0 = 0.85e9, cB = 6e3. Rows: results/p2/model_form_runs/<case>__<estimator>.jsonl.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import G_SD_DB, START, TRUTH, WIM, W_RANGE, Z90, cp_interval, setup  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily, generate_pass  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

KMH = 1 / 3.6
NOMINAL = {"kH0": 1.4e9, "k_r": 1.0e8, "m_r": 150.0}
CASES = {
    "control": {},
    "kH0_x0.7": {"kH0": 0.7}, "kH0_x1.3": {"kH0": 1.3},
    "k_r_x0.7": {"k_r": 0.7}, "k_r_x1.3": {"k_r": 1.3},
    "m_r_x1.3": {"m_r": 1.3},
    "axle_damp_x0.5": {"axle_damp_scale": 0.5}, "axle_damp_x2": {"axle_damp_scale": 2.0},
    "pass_to_pass_track": {"per_pass": {"k_r": 0.15, "kH0": 0.10}},
}
ESTIMATORS = {"nominal": ("kB0", "cB"), "coest": ("kB0", "cB", "kH0", "k_r")}
RUN_DIR = RESULTS_DIR / "p2" / "model_form_runs"
FG = np.arange(44.0, 701.0, 0.25)


def true_theta(case: dict, thb: dict, rng: np.random.Generator) -> dict:
    th = dict(thb, **TRUTH, **NOMINAL)
    for k, s in case.items():
        if k == "per_pass":
            for kk, sd in s.items():
                th[kk] = th[kk] * math.exp(sd * rng.standard_normal())
        elif k == "axle_damp_scale":
            th[k] = s
        else:
            th[k] = th[k] * s
    return th


def dataset(sm, thb, rough, case: dict, seed_key, N=50, snr=40.0, speeds=(60.0, 110.0)):
    rng = np.random.default_rng(np.random.SeedSequence(seed_key))
    g = 10 ** (rng.normal(0, G_SD_DB, rough.n_sub) / 10)
    Vs = rng.uniform(*speeds, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    rng_case = np.random.default_rng(np.random.SeedSequence(list(seed_key) + [7]))  # per-pass perturbations
    passes = []
    for V, W in zip(Vs, Ws):
        th = true_theta(case, thb, rng_case)
        Hg = sm.axlebox_accel_per_unit_input(dict(th, W=float(W)), 2 * np.pi * FG)
        passes.append(generate_pass(lambda f: np.interp(f, FG, Hg.real) + 1j * np.interp(f, FG, Hg.imag),
                                    rough, g, V, thb["r0"], snr, rng))
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    return passes, Wm, Ws, g


def run(case_names, n_data, seed_base):
    sm, thb, rough, _ = setup()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for cname in case_names:
        for j in range(n_data):
            key = (seed_base, j)
            todo = []
            for ename in ESTIMATORS:
                fp = RUN_DIR / f"{cname}__{ename}.jsonl"
                done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
                if key not in done:
                    todo.append(ename)
            if not todo:
                continue
            t0 = time.perf_counter()
            passes, Wm, Ws, g = dataset(sm, thb, rough, CASES[cname], key)
            t_gen = time.perf_counter() - t0
            for ename in todo:
                names = ESTIMATORS[ename]
                fam = SingleWheelsetFamily(sm, dict(thb, **NOMINAL), names=names)
                est = MultiPassWhittle([dict(q) for q in passes], Wm, WIM, rough, fam)
                start = {**START, **NOMINAL}
                r = est.fit(np.log([start[n] for n in names]))
                tv = {**TRUTH, **NOMINAL}
                crb = est.expected_fisher(np.log([tv[n] for n in names]), np.log(g), np.log(Ws))
                row = {"case": cname, "estimator": ename, "names": list(names), "seed_key": list(key),
                       "phi_hat": r["phi"], "se_log": r["se_log"], "crb_log_nominal_truth": crb["crb_log"],
                       "err_log_kB0": r["phi"][0] - math.log(TRUTH["kB0"]),
                       "converged": r["converged"], "n_eval": r["n_eval"], "wall_fit_s": r["wall_fit_s"],
                       "wall_generate_s": t_gen}
                with (RUN_DIR / f"{cname}__{ename}.jsonl").open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"{cname:20s} {ename:8s} j={j} err={row['err_log_kB0']:+.4f} se={r['se_log'][0]:.4f} "
                      f"fit={r['wall_fit_s']:.0f}s", flush=True)


def aggregate():
    out = []
    for cname in CASES:
        for ename in ESTIMATORS:
            fp = RUN_DIR / f"{cname}__{ename}.jsonl"
            if not fp.exists():
                continue
            rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
            e = np.array([r["err_log_kB0"] for r in rows])
            se = np.array([r["se_log"][0] for r in rows])
            crb_ctrl = np.array([r["crb_log_nominal_truth"][0] for r in rows])
            k = int(np.sum(np.abs(e) <= Z90 * se))
            extra = {}
            if ename == "coest":
                for idx, nm in ((2, "kH0"), (3, "k_r")):
                    extra[f"{nm}_hat_over_nominal_median"] = float(np.median([math.exp(r["phi_hat"][idx]) / {**NOMINAL}[nm]
                                                                              for r in rows]))
            out.append({"case": cname, "estimator": ename, "n": len(rows),
                        "bias_rel_kB0": float(np.mean(np.exp(e) - 1)),
                        "bias_rel_kB0_se": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(e))) if len(e) > 1 else None,
                        "crb_rel_kB0": float(np.sqrt(np.mean(crb_ctrl**2))),
                        "bias_over_crb": float(np.mean(e) / np.sqrt(np.mean(crb_ctrl**2))),
                        "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / np.sqrt(np.mean(crb_ctrl**2))),
                        "coverage90_wald": k / len(e), "coverage90_wald_ci95": cp_interval(k, len(e)),
                        "all_converged": all(r["converged"] for r in rows),
                        "fit_s_median": float(np.median([r["wall_fit_s"] for r in rows])), **extra})
            print(out[-1], flush=True)
    save_result("p2/model_form", {"cells": out}, cfg={
        "cases": CASES, "estimators": {k: list(v) for k, v in ESTIMATORS.items()}, "nominal": NOMINAL,
        "truth": TRUTH, "N": 50, "speeds_kmh": [60, 110], "snr_db": 40, "wim_sigma": WIM,
        "note": "paired datasets across cases; CRB = expected Fisher of the fitted model at the nominal truth"},
        seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=list(CASES))
    ap.add_argument("--n-data", type=int, default=10)
    ap.add_argument("--seed-base", type=int, default=20261012)
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    aggregate() if a.aggregate else run(a.cases, a.n_data, a.seed_base)
