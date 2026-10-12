"""Task (c): repeated passes over the same section with partially coherent roughness (random lateral offsets).

Records are aligned in position (20 revolutions from the same start point), so bin k of every pass
samples the same spatial wavenumber. Each pass runs at a random lateral wheel position y_i ~ N(0, sy^2)
on a railhead whose roughness decorrelates laterally with a Gaussian correlation exp(-dy^2 / (2 l^2))
(wavelength-independent; an assumption, no source). Pairwise coherence C_ij = exp(-(y_i - y_j)^2 / (2 l^2));
sy / l is set so that the mean pairwise coherence is rho = E[C_ij] = (1 + 2 sy^2 / l^2)^(-1/2),
rho in {0.5, 0.7, 0.9}. Roughness coefficients: Z = W L^T with L = chol(C), so Corr(Z_i, Z_j) = C_ij.

Estimator: ExchangeableSectionWhittle (src/inverse/variants.py), which assumes exchangeable coherence
rho (estimated with kB0 and cB) -> misspecified with respect to the offset-dependent C.
--bound: per rho, CRB of kB0 for (i) the oracle model (true C known; dense Fisher), (ii) the exchangeable
         model with rho estimated (dense Fisher at C = exchangeable(rho)), and (iii) independent sections.
--mc:    12 datasets per rho (N = 50, 60-110 km/h, SNR 40 dB): bias, RMSE vs CRB, Wald 90% coverage.
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

from experiments.p2_common import (G_SD_DB, KMH, START, TRUTH, WIM, W_RANGE, H_single, phi_true, setup,  # noqa: E402
                                   summarise)
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily, generate_pass  # noqa: E402
from src.inverse.variants import ExchangeableSectionWhittle, SharedSectionWhittle, dense_fisher  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "partial_coherence_runs"
RHOS = (0.5, 0.7, 0.9)
N_FINE = 40000


def lateral_coherence(rng, N, rho):
    r = math.sqrt((rho**-2 - 1) / 2)  # sy / l
    y = r * rng.standard_normal(N)
    return np.exp(-((y[:, None] - y[None, :]) ** 2) / 2), y


def dataset(sm, thb, rough, seed_key, rho, N=50, snr=40.0, speeds=(60.0, 110.0), g_sd=G_SD_DB):
    rng = np.random.default_rng(np.random.SeedSequence(list(seed_key)))
    g = 10 ** (rng.normal(0, g_sd, rough.n_sub) / 10)
    Vs = rng.uniform(*speeds, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    C, y = lateral_coherence(rng, N, rho)
    L = np.linalg.cholesky(C + 1e-10 * np.eye(N))
    Wn = rng.standard_normal((N_FINE, N)) + 1j * rng.standard_normal((N_FINE, N))
    Z = Wn @ L.T
    th = dict(thb, **TRUTH)
    passes = [generate_pass(H_single(sm, dict(th, W=float(W))), rough, g, V, thb["r0"], snr, rng, Z_shared={"Z": Z[:, i]})
              for i, (V, W) in enumerate(zip(Vs, Ws))]
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    return {"passes": passes, "Wm": Wm, "Ws": Ws, "g": g, "C": C, "y": y}


def bound():
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    rows = []
    with Timer() as tm:
        for rho in RHOS:
            ds = dataset(sm, thb, rough, (89, int(rho * 10)), rho, g_sd=0.0)
            sh = SharedSectionWhittle(ds["passes"], ds["Ws"], WIM, rough, fam)
            lg, lw = np.zeros(rough.n_sub), np.log(ds["Ws"])
            oracle = dense_fisher(sh, phi_true(), lg, lw, ds["C"])
            N = len(ds["passes"])
            Cx = (1 - rho) * np.eye(N) + rho * np.ones((N, N))
            exch = dense_fisher(sh, phi_true(), lg, lw, Cx, rho_param=True)
            ind = MultiPassWhittle(ds["passes"], ds["Ws"], WIM, rough, fam).expected_fisher(phi_true(), lg, lw)["crb_log"]
            off = ds["C"][~np.eye(N, dtype=bool)]
            rows.append({"rho": rho, "C_offdiag_mean": float(off.mean()), "C_offdiag_min": float(off.min()),
                         "oracle_crb": oracle, "exchangeable_rho_estimated_crb": exch, "independent_crb": ind})
            print(rows[-1], flush=True)
    save_result("p2/partial_coherence_bound", {"rows": rows}, cfg={
        "N": 50, "speeds_kmh": [60, 110], "snr_db": 40, "wim_sigma": WIM, "truth": TRUTH,
        "coherence": "Gaussian lateral correlation, random lateral offsets; rho = mean pairwise coherence (assumption)"},
        seed=89, wall_seconds=tm.seconds)


def mc(n_data, rhos, seed_base=20261012):
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for rho in rhos:
        fp = RUN_DIR / f"rho{rho:.1f}.jsonl"
        done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        for j in range(n_data):
            key = (seed_base, int(round(rho * 10)), j)
            if key in done:
                continue
            ds = dataset(sm, thb, rough, key, rho)
            est = ExchangeableSectionWhittle(ds["passes"], ds["Wm"], WIM, rough, fam)
            r = est.fit(np.r_[np.log([START["kB0"], START["cB"]]), 0.0])
            rho_hat = 1 / (1 + math.exp(-r["phi"][2]))
            N = len(ds["passes"])
            oracle = dense_fisher(est, phi_true(), np.log(ds["g"]), np.log(ds["Ws"]), ds["C"])
            row = {"rho": rho, "seed_key": list(key), "err_log": [r["phi"][0] - math.log(TRUTH["kB0"]), r["phi"][1] - math.log(TRUTH["cB"])],
                   "se_log": r["se_log"][:2], "rho_hat": rho_hat, "C_offdiag_mean": float(ds["C"][~np.eye(N, dtype=bool)].mean()),
                   "crb_log_oracle": oracle, "converged": r["converged"], "wall_fit_s": r["wall_fit_s"], "s_per_eval": r["s_per_eval"]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"rho={rho} j={j} err={row['err_log'][0]:+.5f} se={row['se_log'][0]:.5f} oracle={oracle[0]:.5f} "
                  f"rho_hat={rho_hat:.3f} fit={r['wall_fit_s']:.0f}s", flush=True)


def aggregate():
    cells = []
    for fp in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        s = summarise([r["err_log"][0] for r in rows], [r["se_log"][0] for r in rows], [r["crb_log_oracle"][0] for r in rows])
        cells.append({"rho": rows[0]["rho"], "kB0": s, "rho_hat_median": float(np.median([r["rho_hat"] for r in rows])),
                      "C_offdiag_mean_median": float(np.median([r["C_offdiag_mean"] for r in rows])),
                      "all_converged": all(r["converged"] for r in rows),
                      "fit_s_median": float(np.median([r["wall_fit_s"] for r in rows]))})
        print(json.dumps(cells[-1]), flush=True)
    save_result("p2/partial_coherence_mc", {"cells": cells}, cfg={"N": 50, "speeds_kmh": [60, 110], "snr_db": 40,
                "estimator": "exchangeable coherence, rho estimated; CRB reference = oracle (true C)"}, seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", action="store_true")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--n-data", type=int, default=12)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(RHOS))
    a = ap.parse_args()
    if a.bound:
        bound()
    if a.mc:
        mc(a.n_data, a.rhos)
    if a.aggregate:
        aggregate()
