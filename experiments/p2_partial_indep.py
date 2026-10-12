"""Main (independent-pass) estimator applied to repeated passes over one section with partial coherence.

Datasets: exactly those of experiments/p2_shared_section.py --mc (rho = 0.5, 0.7, 0.9, random lateral
offsets, 12 per rho; same seed keys). Estimator: MultiPassWhittle (bins treated as independent across
passes). Uncertainty: observed profile information (model-based) and cluster-robust sandwich
variances, clustered by DFT bin (= spatial wavenumber, where the shared roughness correlates passes)
and, for comparison, by pass. Rows: results/p2/partial_indep_runs/rho<rho>.jsonl.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import START, TRUTH, WIM, Z90, cp_interval, phi_true, setup  # noqa: E402
from experiments.p2_shared_section import RHOS, dataset  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "partial_indep_runs"


def run(rhos, n_data, seed_base=20261012):
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for rho in rhos:
        fp = RUN_DIR / f"rho{rho:.1f}.jsonl"
        done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        for j in range(n_data):
            key = (seed_base, int(round(rho * 10)), j)  # same keys as p2_shared_section --mc
            if key in done:
                continue
            ds = dataset(sm, thb, rough, key, rho)
            est = MultiPassWhittle(ds["passes"], ds["Wm"], WIM, rough, fam)
            r = est.fit(np.log([START["kB0"], START["cB"]]))
            ph, lg, lw = np.array(r["phi"]), np.array(r["logg"]), np.array(r["lw"])
            sb = est.sandwich_cov(ph, lg, lw, cluster="bin")
            sp = est.sandwich_cov(ph, lg, lw, cluster="pass")
            crb = est.expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))["crb_log"]
            row = {"rho": rho, "seed_key": list(key), "err_log": r["phi"][0] - math.log(TRUTH["kB0"]),
                   "se_obs": r["se_log"][0], "se_sandwich_bin": sb["se_log_sandwich"][0],
                   "se_sandwich_pass": sp["se_log_sandwich"][0], "crb_indep_model": crb[0],
                   "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, flush=True)


def aggregate():
    cells = []
    for fp in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        e = np.array([r["err_log"] for r in rows])
        cell = {"rho": rows[0]["rho"], "n": len(rows), "bias_rel": float(np.mean(np.exp(e) - 1)),
                "bias_rel_se": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(e))),
                "rmse_rel": float(np.sqrt(np.mean(e**2))),
                "crb_indep_model": float(np.sqrt(np.mean([r["crb_indep_model"] ** 2 for r in rows])))}
        for tag in ("se_obs", "se_sandwich_bin", "se_sandwich_pass"):
            se = np.array([r[tag] for r in rows])
            k = int(np.sum(np.abs(e) <= Z90 * se))
            cell[tag] = {"median": float(np.median(se)), "rmse_over_median_se": float(np.sqrt(np.mean(e**2)) / np.median(se)),
                         "coverage90": k / len(e), "coverage90_ci95": cp_interval(k, len(e))}
        cells.append(cell)
        print(json.dumps(cell), flush=True)
    save_result("p2/partial_indep", {"cells": cells}, cfg={"datasets": "p2_shared_section --mc keys (rho, lateral offsets)",
                "estimator": "independent-pass Whittle (MultiPassWhittle)", "sandwich": "J^-1 M J^-1, clusters by bin or by pass"},
                seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rhos", type=float, nargs="+", default=list(RHOS))
    ap.add_argument("--n-data", type=int, default=12)
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    aggregate() if a.aggregate else run(a.rhos, a.n_data)
