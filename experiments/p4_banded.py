"""Payload-banded operation: bounds, detection limits and the primary-suspension stress test per band.

Bands: empty (axle load 5.5-7 t) with Dusza et al.'s empty primary values (k_p 1017 kN/m, c_p 7 kN s/m)
and laden (20-22.5 t) with the laden values (2280 kN/m, 123.3 kN s/m). Passes in a period are drawn
uniformly within the band (60-110 km/h, 3% WIM error, K = 16 roughness levels); the estimator uses the
band's fixed primary values and change detection compares the same band across periods.
  --bounds : CRB of k_B0 (k_f, k_H0 co-estimated) and the two-period MDC (one-sided 5% false alarm, 90%
             detection), N = 50/200, 20/40 dB, both bands; data and fit share the band's fixed values.
  --pseudo --band B : stress test, pseudo-true bias of k_B0 when the truth has k_p, c_p interpolated
             linearly in axle load between Dusza's empty and laden values (evaluated within the band).
  --pairs --band B --j0 --j1 : zero-change pairs of periods under the same stress truth (co-estimating
             fit per period); false alarm if D < -1.645 se_D.
Rows: results/p4/banded_runs/*.jsonl (resumable, 110-minute budget per process); --summarise ->
results/p4/banded.json.
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

import experiments.p1_fe_direct as fd  # noqa: E402
import experiments.p2_multiwheel as pm  # noqa: E402
from experiments.p1_fe_direct import TRUTH, cp_interval  # noqa: E402
from experiments.p2_common import WIM, setup  # noqa: E402
from experiments.p2_relative_change import gen  # noqa: E402
from experiments.p2_relative_coest_drift import EST, SPEEDS, families, mdc_under, phi, truth  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4" / "banded_runs"
BANDS = {"empty": ((5.5, 7.0), 1.017e6, 7.0e3), "laden": ((20.0, 22.5), 2.28e6, 1.233e5)}
T0, BUDGET = time.perf_counter(), 110 * 60
Z = 1.6448536269514722


def set_band(b):
    rng, kp, cp = BANDS[b]
    fd.W_RANGE = pm.W_RANGE = rng                 # payload draws of every dataset generator
    return kp, cp


def _done(fp, key):
    return {key(json.loads(l)) for l in fp.read_text().splitlines() if l.strip()} if fp.exists() else set()


def _append(fp, row):
    OUT.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(row, flush=True)


def _base(b):
    sm, thb, rough, _ = setup()
    mw = pm.models(sm)[0]["4"]
    kp, cp = set_band(b)
    thb_b = dict(thb, kp=kp, cp=cp)
    return sm, thb_b, rough, mw, families(mw, thb_b)


def bounds():
    fp = OUT / "bounds.jsonl"
    done = _done(fp, lambda r: (r["band"], r["N"], r["snr_db"]))
    for b in BANDS:
        sm, thb_b, rough, mw, fams = _base(b)
        for N in (50, 200):
            for snr in (20.0, 40.0):
                if (b, N, snr) in done:
                    continue
                P, Wm, Ws, g = pm.dataset(sm, thb_b, rough, mw, (48, N, int(snr)), N=N, snr=snr, speeds=SPEEDS, g_sd=0.0)
                est = MultiPassWhittle(P, Ws, WIM, rough, fams["coest"], debias=True)
                crb = est.expected_fisher(phi(EST["coest"]), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
                _append(fp, {"band": b, "N": N, "snr_db": snr, "crb_kB0_pct": 100 * crb,
                             "mdc_pct": mdc_under(0.0, 0.0, math.sqrt(2) * crb)})


def pseudo(b):
    fp = OUT / f"pseudo_{b}.jsonl"
    if fp.exists() and fp.read_text().strip():
        return
    sm, thb_b, rough, mw, fams = _base(b)
    P, Wm, Ws, g = pm.dataset(sm, thb_b, rough, mw, (31, 0), N=50, speeds=SPEEDS, g_sd=0.0)
    est = MultiPassWhittle(P, Ws, WIM, rough, fams["coest"], debias=True)
    true_all = dict(truth(thb_b, {}, TRUTH["kB0"]), primary_payload_law=True)
    r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi(EST["coest"], start=True))
    _append(fp, {"band": b, "bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100, "phi_hat": r["phi"],
                 "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]})


def pairs(b, j0, j1):
    fp = OUT / f"pairs_{b}.jsonl"
    done = _done(fp, lambda r: r["rep"])
    sm, thb_b, rough, mw, fams = _base(b)
    th = dict(truth(thb_b, {}, TRUTH["kB0"]), primary_payload_law=True)
    tmax = 30 * 60
    for j in range(j0, j1):
        if j in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        res = {}
        for per in (0, 1):
            P, Wm, Ws, g = gen(sm, th, rough, mw, (49, j, per))
            res[per] = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True).fit(phi(EST["coest"], start=True))
        d = res[1]["phi"][0] - res[0]["phi"][0]
        se = math.hypot(res[0]["se_log"][0], res[1]["se_log"][0])
        _append(fp, {"band": b, "rep": j, "D_hat": d, "se": se, "err_base": res[0]["phi"][0] - math.log(TRUTH["kB0"]),
                     "err_later": res[1]["phi"][0] - math.log(TRUTH["kB0"]),
                     "converged": res[0]["converged"] and res[1]["converged"], "wall_s": time.perf_counter() - t0})
        tmax = max(tmax, 1.3 * (time.perf_counter() - t0))


def summarise():
    out = {"bands": {b: {"W_t": BANDS[b][0], "kp": BANDS[b][1], "cp": BANDS[b][2]} for b in BANDS}}
    rows = lambda f: [json.loads(l) for l in (OUT / f).read_text().splitlines() if l.strip()] if (OUT / f).exists() else []
    out["bounds"] = rows("bounds.jsonl")
    for b in BANDS:
        ps = rows(f"pseudo_{b}.jsonl")
        if ps:
            out.setdefault("pseudo_true", {})[b] = ps[0]["bias_pct"]
        Pr = rows(f"pairs_{b}.jsonl")
        if Pr:
            D, se = np.array([r["D_hat"] for r in Pr]), np.array([r["se"] for r in Pr])
            fin = np.isfinite(se)
            se_med = float(np.median(se[fin])) if fin.any() else float("nan")
            k = int(np.sum((D < -Z * se) & fin))
            k_fb = int(np.sum(D < -Z * np.where(fin, se, se_med)))      # singular-information pairs at the median SE
            lev = [math.exp(r[x]) - 1 for r in Pr for x in ("err_base", "err_later")]
            out.setdefault("pairs", {})[b] = {
                "n": len(Pr), "n_finite_se": int(fin.sum()), "false_alarms": k, "rate_ci95": cp_interval(k, int(fin.sum())),
                "false_alarms_median_se_fallback": k_fb, "D_pct": [float(100 * x) for x in D],
                "z": [float(x) for x in D[fin] / se[fin]],
                "z_median_se_fallback": [float(x) for x in D / np.where(fin, se, se_med)], "D_mean_pct": float(np.mean(np.exp(D) - 1) * 100),
                "D_sd_pct": float(np.std(D, ddof=1) * 100) if len(D) > 1 else None, "se_median_pct": se_med * 100,
                "level_err_mean_pct": float(np.mean(lev) * 100), "level_err_sd_pct": float(np.std(lev, ddof=1) * 100),
                "all_converged": all(r["converged"] for r in Pr)}
    save_result("p4/banded", out, cfg={"speeds_kmh": SPEEDS, "estimator": "coest (kB0, cB, kf, kH0), band's fixed primary values",
                                      "stress_truth": "k_p, c_p linear in axle load between empty and laden values"}, seed=48)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bounds", action="store_true")
    ap.add_argument("--pseudo", action="store_true")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--band", choices=tuple(BANDS), default="empty")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=10)
    a = ap.parse_args()
    if a.bounds:
        bounds()
    if a.pseudo:
        pseudo(a.band)
    if a.pairs:
        pairs(a.band, a.j0, a.j1)
    if a.summarise:
        summarise()
