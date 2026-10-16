"""Primary-suspension misspecification: payload-dependent k_p and c_p in the data, fixed values in the fit.

Data: the 4-wheel rail-coupled model at the current config with the primary stiffness and damping of each
pass interpolated linearly in axle load between Dusza et al.'s empty (1017 kN/m, 7 kN s/m) and laden
(2280 kN/m, 123.3 kN s/m) values (config primary.kp/cp ranges; th["primary_payload_law"]). Fit: the
frozen estimator with the fixed nominal (empty) values.
  --pseudo : pseudo-true (expected-data) fits, estimators "nominal" (k_B0, c_B) and "coest" (+ k_f, k_H0):
             large-sample bias of k_B0. Design as the model-form study (N = 50, 60-110 km/h, 40 dB).
  --pairs  : 10 zero-change pairs of periods (keys (47, j, 0/1)), co-estimating fit per period; false
             alarm if D < -1.645 se_D (uncalibrated) and with the 40 dB SE inflation (results/p3/calibrated.json).
Rows: results/p4/primary_damping_runs/{pseudo,pairs}.jsonl (resumable, 110-minute budget per process);
--summarise -> results/p4/primary_damping.json.
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

from experiments.p1_fe_direct import TRUTH, cp_interval  # noqa: E402
from experiments.p2_common import WIM, setup  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from experiments.p2_relative_change import gen  # noqa: E402
from experiments.p2_relative_coest_drift import EST, NOM, SPEEDS, families, phi, truth  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4" / "primary_damping_runs"
T0, BUDGET = time.perf_counter(), 110 * 60
Z = 1.6448536269514722
N_PAIRS = 10


def _done(fp, key):
    return {key(json.loads(l)) for l in fp.read_text().splitlines() if l.strip()} if fp.exists() else set()


def _append(fp, row):
    OUT.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(row, flush=True)


def pseudo():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fams = families(mw, thb)
    P, Wm, Ws, g = mw_dataset(sm, thb, rough, mw, (31, 0), N=50, speeds=SPEEDS, g_sd=0.0)
    fp = OUT / "pseudo.jsonl"
    done = _done(fp, lambda r: r["estimator"])
    true_all = dict(thb, **TRUTH, **NOM, primary_payload_law=True)
    for e in ("nominal", "coest"):
        if e in done:
            continue
        est = MultiPassWhittle(P, Ws, WIM, rough, fams[e], debias=True)
        r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi(EST[e], start=True))
        _append(fp, {"estimator": e, "bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100,
                     "phi_hat": r["phi"], "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]})


def pairs():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fams = families(mw, thb)
    fp = OUT / "pairs.jsonl"
    done = _done(fp, lambda r: r["rep"])
    th = dict(truth(thb, {}, TRUTH["kB0"]), primary_payload_law=True)
    tmax = 30 * 60
    for j in range(N_PAIRS):
        if j in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        res = {}
        for per in (0, 1):
            Pp, Wmp, Wsp, gp = gen(sm, th, rough, mw, (47, j, per))
            r = MultiPassWhittle([dict(q) for q in Pp], Wmp, WIM, rough, fams["coest"], debias=True).fit(phi(EST["coest"], start=True))
            res[per] = r
        d = res[1]["phi"][0] - res[0]["phi"][0]
        se = math.hypot(res[0]["se_log"][0], res[1]["se_log"][0])
        _append(fp, {"rep": j, "D_hat": d, "se": se, "err_base": res[0]["phi"][0] - math.log(TRUTH["kB0"]),
                     "err_later": res[1]["phi"][0] - math.log(TRUTH["kB0"]),
                     "converged": res[0]["converged"] and res[1]["converged"], "wall_s": time.perf_counter() - t0})
        tmax = max(tmax, 1.3 * (time.perf_counter() - t0))


def summarise():
    out = {}
    R = [json.loads(l) for l in (OUT / "pseudo.jsonl").read_text().splitlines() if l.strip()] if (OUT / "pseudo.jsonl").exists() else []
    out["pseudo_true"] = {r["estimator"]: {"bias_pct": r["bias_pct"], "converged": r["converged"]} for r in R}
    cal = json.loads((RESULTS_DIR / "p3/calibrated.json").read_text())["payload"]
    r40 = next(h for h in cal["headline"] if h["snr_db"] == 40)["all_seeds"]["inflation_rmse_over_se"]
    Pr = [json.loads(l) for l in (OUT / "pairs.jsonl").read_text().splitlines() if l.strip()] if (OUT / "pairs.jsonl").exists() else []
    if Pr:
        D = np.array([r["D_hat"] for r in Pr])
        se = np.array([r["se"] for r in Pr])
        k_raw, k_cal = int(np.sum(D < -Z * se)), int(np.sum(D < -Z * r40 * se))
        out["pairs"] = {"n": len(Pr), "false_alarms_raw": k_raw, "rate_raw_ci95": cp_interval(k_raw, len(Pr)),
                        "false_alarms_calibrated": k_cal, "rate_calibrated_ci95": cp_interval(k_cal, len(Pr)),
                        "D_mean_pct": float(np.mean(np.exp(D) - 1) * 100), "D_sd_pct": float(np.std(D, ddof=1) * 100) if len(D) > 1 else None,
                        "level_bias_mean_pct": float(np.mean([math.exp(r["err_base"]) - 1 for r in Pr] + [math.exp(r["err_later"]) - 1 for r in Pr]) * 100),
                        "se_inflation_used": r40, "all_converged": all(r["converged"] for r in Pr)}
    save_result("p4/primary_damping", out, cfg={"data": "k_p, c_p linear in axle load between empty and laden (Dusza et al. 2024)",
                                               "fit": "fixed empty values", "N": 50, "snr_db": 40, "speeds_kmh": SPEEDS}, seed=47)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pseudo", action="store_true")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()
    if a.pseudo:
        pseudo()
    if a.pairs:
        pairs()
    if a.summarise:
        summarise()
