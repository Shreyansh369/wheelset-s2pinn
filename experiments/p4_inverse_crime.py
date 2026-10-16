"""Inverse-crime check limited to nonlinear Hertzian contact (Milestone B).

Data: the rail-coupled 4-wheel model at the sourced nominals with nonlinear Hertz contact
(src/reference/time_domain_contact.py; everything else identical to the estimator's model). Design as the
headline: N = 50 passes, speeds uniform 60-110 km/h, payload uniform 5.5-22.5 t with 3% WIM error, K = 16
roughness levels per third octave drawn with a 3 dB spread, 40 dB.
  --nl     20 datasets (keys (60, j)), true k_B0 = TRUTH;
  --lin    the same 20 datasets with linear contact (identical roughness, speeds, payloads and noise draws):
           isolates the effect of the contact nonlinearity on each estimate;
  --pairs  20 zero-change pairs (keys (61, j, period)), nonlinear contact, true change 0, for false alarms.
Fit: the frozen linear estimator (debiased Whittle, +-120-bin kernel, own-sub-band scoring, K = 16,
(k_B0, c_B) free). Wald SE from the observed information; false alarm if D < -1.645 se_D, uncalibrated and
with the 40 dB simulation calibration (results/p3/calibrated.json, SE inflation). Rows:
results/p4/inverse_crime_runs/<mode>.jsonl (resumable, 110-minute budget per process); --summarise ->
results/p4/inverse_crime.json.
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

from experiments.p1_fe_direct import G_SD_DB, START, TRUTH, W_RANGE, WIM, cp_interval  # noqa: E402
from experiments.p2_common import setup  # noqa: E402
from experiments.p2_multiwheel import KMH, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.reference.time_domain_contact import NonlinearContactGenerator  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4" / "inverse_crime_runs"
N, SNR, SPEEDS = 50, 40.0, (60.0, 110.0)
T0, BUDGET = time.perf_counter(), 110 * 60
Z = 1.6448536269514722
TAG = [""]


def dataset(gen, rough, r0, key, contact):
    """Same draw order as experiments/p2_multiwheel.dataset; each pass has its own seeded stream so the
    linear twin sees identical roughness and noise."""
    rng = np.random.default_rng(np.random.SeedSequence(key))
    g = 10 ** (rng.normal(0, G_SD_DB, rough.n_sub) / 10)
    Vs = rng.uniform(*SPEEDS, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    passes, stats = [], []
    for i, (V, W) in enumerate(zip(Vs, Ws)):
        p = gen.simulate(rough, g, V, W, r0, SNR, np.random.default_rng(np.random.SeedSequence(list(key) + [1000 + i])), contact=contact)
        passes.append(p)
        stats.append({k: p[k] for k in ("iterations", "converged", "delta0_um", "delta_rms_um", "delta_min_ratio", "contact_loss_fraction")
                      if k in p})
    return passes, Wm, Ws, g, stats


def fit(passes, Wm, rough, fam):
    est = MultiPassWhittle([dict(q) for q in passes], Wm, WIM, rough, fam, debias=True)
    return est.fit(np.log([START["kB0"], START["cB"]]))


def run(mode, j0, j1):
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    gen = NonlinearContactGenerator(mw, dict(thb, **TRUTH))
    fam = MultiWheelFamily(mw, thb)
    OUT.mkdir(parents=True, exist_ok=True)
    fp = OUT / f"{mode}{TAG[0]}.jsonl"
    done = {tuple(json.loads(l)["key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    keys = [(61, j, per) for j in range(j0, j1) for per in (0, 1)] if mode == "pairs" else [(60, j) for j in range(j0, j1)]
    # --fd: frequency-domain generator at the current config on the same keys (generator check)
    tmax = 15 * 60
    lt = math.log(TRUTH["kB0"])
    for key in keys:
        if key in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t1 = time.perf_counter()
        if mode == "fd":   # frequency-domain generator (estimator's data model), same speeds/payloads/levels
            from experiments.p2_multiwheel import dataset as fd_dataset
            P, Wm, Ws, g = fd_dataset(sm, thb, rough, mw, key, N=N, snr=SNR, speeds=SPEEDS)
            st = [{"converged": True, "contact_loss_fraction": 0.0, "delta_min_ratio": 1.0, "delta_rms_um": 0.0, "delta0_um": 1.0}]
        else:
            P, Wm, Ws, g, st = dataset(gen, rough, thb["r0"], key, "linear" if mode == "lin" else "hertz")
        t_gen = time.perf_counter() - t1
        r = fit(P, Wm, rough, fam)
        row = {"key": list(key), "mode": mode, "err_log": r["phi"][0] - lt, "se_log": r["se_log"][0],
               "err_log_cB": r["phi"][1] - math.log(TRUTH["cB"]), "phi": r["phi"], "converged": r["converged"],
               "gen_converged_all": all(s.get("converged", True) for s in st),
               "contact_loss_max": max(s.get("contact_loss_fraction", 0.0) for s in st),
               "delta_min_ratio_min": min(s["delta_min_ratio"] for s in st),
               "delta_rms_over_delta0_max": max(s["delta_rms_um"] / s["delta0_um"] for s in st),
               "wall_gen_s": t_gen, "wall_s": time.perf_counter() - t1}
        with fp.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        tmax = max(tmax, 1.3 * row["wall_s"])


def _rows(mode):
    fp = OUT / f"{mode}.jsonl"
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def summarise():
    out = {}
    cal = RESULTS_DIR / "p3" / "calibrated.json"
    c40 = next((h for h in json.loads(cal.read_text())["payload"]["headline"] if h["snr_db"] == 40), None) if cal.exists() else None
    b40 = math.log(1 + c40["all_seeds"]["bias_pct"] / 100) if c40 and c40["calibration_applied"] else 0.0
    r40 = c40["all_seeds"]["inflation_rmse_over_se"] if c40 and c40["calibration_applied"] else 1.0
    for mode in ("nl", "lin", "fd"):
        R = _rows(mode)
        if not R:
            continue
        e = np.array([r["err_log"] for r in R])
        se = np.array([r["se_log"] for r in R])
        k_raw = int(np.sum(np.abs(e) <= Z * se))
        k_cal = int(np.sum(np.abs(e - b40) <= Z * r40 * se))
        out[mode] = {"n": len(R), "bias_pct": float(np.mean(np.exp(e) - 1) * 100), "bias_se_pct": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(R)) * 100),
                     "rmse_pct": float(np.sqrt(np.mean(e**2)) * 100), "se_median_pct": float(np.median(se) * 100),
                     "coverage_raw": k_raw / len(R), "coverage_raw_ci95": cp_interval(k_raw, len(R)),
                     "coverage_calibrated": k_cal / len(R), "coverage_calibrated_ci95": cp_interval(k_cal, len(R)),
                     "cB_bias_pct": float(np.mean([math.exp(r["err_log_cB"]) - 1 for r in R]) * 100),
                     "contact_loss_max": max(r["contact_loss_max"] for r in R), "delta_min_ratio_min": min(r["delta_min_ratio_min"] for r in R),
                     "delta_rms_over_delta0_max": max(r["delta_rms_over_delta0_max"] for r in R),
                     "all_converged": all(r["converged"] and r["gen_converged_all"] for r in R)}
    Rn, Rl = {tuple(r["key"]): r for r in _rows("nl")}, {tuple(r["key"]): r for r in _rows("lin")}
    both = sorted(set(Rn) & set(Rl))
    if both:
        d = np.array([Rn[k]["err_log"] - Rl[k]["err_log"] for k in both]) * 100
        out["nl_minus_lin"] = {"n": len(both), "mean_pp": float(d.mean()), "sd_pp": float(d.std(ddof=1)) if len(d) > 1 else None,
                               "se_pp": float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else None, "max_abs_pp": float(np.max(np.abs(d)))}
    P = {}
    for r in _rows("pairs"):
        P.setdefault(r["key"][1], {})[r["key"][2]] = r
    pairs = [v for v in P.values() if 0 in v and 1 in v]
    if pairs:
        D = np.array([v[1]["phi"][0] - v[0]["phi"][0] for v in pairs])
        sD = np.array([math.hypot(v[0]["se_log"], v[1]["se_log"]) for v in pairs])
        fa_raw = int(np.sum(D < -Z * sD))
        fa_cal = int(np.sum(D < -Z * r40 * sD))
        out["pairs"] = {"n": len(pairs), "false_alarms_raw": fa_raw, "rate_raw": fa_raw / len(pairs), "rate_raw_ci95": cp_interval(fa_raw, len(pairs)),
                        "false_alarms_calibrated": fa_cal, "rate_calibrated": fa_cal / len(pairs), "rate_calibrated_ci95": cp_interval(fa_cal, len(pairs)),
                        "D_mean_pct": float(np.mean(np.exp(D) - 1) * 100), "D_sd_pct": float(np.std(D, ddof=1) * 100) if len(D) > 1 else None,
                        "sD_median_pct": float(np.median(sD) * 100), "se_inflation_used": r40}
    save_result("p4/inverse_crime", out, cfg={"generator": "nonlinear Hertz contact, frequency-domain operators, fixed-point iteration",
                                              "estimator": "frozen linear (debiased Whittle, +-120 bins, K = 16, kB0 and cB)",
                                              "N": N, "snr_db": SNR, "speeds_kmh": SPEEDS}, seed=60)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("nl", "lin", "pairs", "fd"))
    ap.add_argument("--tag", default="", help="run-file suffix (e.g. _v2 after the roughness-grid fix)")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=20)
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()
    TAG[0] = a.tag
    if a.summarise:
        summarise()
    else:
        run(a.mode, a.j0, a.j1)
