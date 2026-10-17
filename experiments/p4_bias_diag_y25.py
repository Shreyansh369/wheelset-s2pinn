"""Estimator bias diagnosis at the current (Y25/Eanos) configuration.

Uses the pinned headline configuration (config/snapshots/headline_freight_v1) so that every variant is
fitted to exactly the datasets of the headline Monte Carlo (results/p3/headline_v2_runs/
kb120_attr_freight.jsonl; keys (seed, 40, j), j < 10, N = 50, 60-110 km/h). The frozen estimator
(+-120-bin kernel, sub-band-attributed scoring, 0.5 Hz table, K = 16) is the headline itself; the
variants change one thing each, on the seed-123 datasets:
  kb30       : +-30-bin debiasing kernel (kernel truncation), 40 dB
  snr60      : the same data at 60 dB (noise)
  exact      : exact sub-band scoring with a 0.25 Hz table (scoring and table resolution), 40 dB
  K4, K1     : 4 or 1 roughness levels per third octave in the estimator (data: 16), 40 dB
  --robust   : sandwich standard errors (bin, 8- and 61-bin blocks) for the 50 headline datasets at 40 dB
  --regress  : the headline errors at 40 dB against the pass design (speed spread, payload spread,
               minimum speed, DFT bins within +-30 Hz of the support resonance)
Rows: results/p4/bias_diag_y25_runs/<variant>.jsonl (resumable, 110-minute budget per process);
--summarise -> results/p4/bias_diag_y25.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("WHEELSET_CONFIG_DIR", os.path.join(_REPO, "config", "snapshots", "headline_freight_v1"))

import argparse  # noqa: E402
import dataclasses  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, _REPO)

from experiments.p1_fe_direct import G_SD_DB, START, TRUTH, W_RANGE, WIM, cp_interval  # noqa: E402
from experiments.p2_common import SEEDS, setup  # noqa: E402
from experiments.p2_multiwheel import KMH, dataset, models  # noqa: E402
from experiments.p3_robust_se import CL, robust  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import F_HI, F_LO, N_REVS, MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4" / "bias_diag_y25_runs"
HEADLINE = RESULTS_DIR / "p3" / "headline_v2_runs" / "kb120_attr_freight.jsonl"
VARIANTS = {"kb30": dict(snr=40.0, kb=30), "snr60": dict(snr=60.0), "exact": dict(snr=40.0, exact=True),
            "K4": dict(snr=40.0, ksub=4), "K1": dict(snr=40.0, ksub=1)}
T0, BUDGET = time.perf_counter(), 110 * 60
HALF = 30.0


def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def _append(fp, row):
    OUT.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(row, flush=True)


def headline(snr=40, seed=None):
    R = [r for r in _rows(HEADLINE) if r["snr_db"] == snr and (seed is None or r["seed"] == seed)]
    return sorted(R, key=lambda r: tuple(r["seed_key"]))


def variant(name, j0, j1, seed=123):
    v = VARIANTS[name]
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb, f_grid=np.arange(45.0, 702.0, 0.25) if v.get("exact") else None)
    rough_est = dataclasses.replace(rough, K=v["ksub"]) if v.get("ksub") else rough
    fp = OUT / f"{name}.jsonl"
    done = {r["j"] for r in _rows(fp)}
    tmax, lt = 15 * 60, math.log(TRUTH["kB0"])
    for j in range(j0, j1):
        if j in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, (seed, 40, j), N=50, snr=v["snr"])
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough_est, fam, debias=True, Kb=v.get("kb", 120),
                               exact_subband=bool(v.get("exact")))
        r = est.fit(np.log([START["kB0"], START["cB"]]))
        crb = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.zeros(est.S) if v.get("ksub") else np.log(g),
                                  np.log(Ws))["crb_log"]
        _append(fp, {"j": j, "seed": seed, "variant": name, "snr_db": v["snr"],
                     "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])], "se_log": r["se_log"],
                     "crb_log": crb, "converged": r["converged"], "wall_s": time.perf_counter() - t0})
        tmax = max(tmax, 1.3 * (time.perf_counter() - t0))


def robust_run(j0, j1):
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb)
    fp = OUT / "robust.jsonl"
    done = {tuple(r["seed_key"]) for r in _rows(fp)}
    tmax, lt = 15 * 60, math.log(TRUTH["kB0"])
    for r in headline(40)[j0:j1]:
        key = tuple(r["seed_key"])
        if key in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, key, N=50, snr=float(key[1]))
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True)
        phi = [r["err_log"][0] + lt, r["err_log"][1] + math.log(TRUTH["cB"])]
        _append(fp, {"seed_key": list(key), "err_log": r["err_log"][0], "se_obs": r["se_log"][0], "se": robust(est, phi),
                     "wall_s": time.perf_counter() - t0})
        tmax = max(tmax, 1.3 * (time.perf_counter() - t0))


def regress():
    """Headline errors at 40 dB against the pass design (as experiments/p3_bias_regression.py)."""
    sm, thb, rough, _ = setup()
    mw1 = models(sm)[0]["1"]
    from experiments.p3_bias_regression import resonance
    Wn, fsn = resonance(sm, thb, mw1)
    L = N_REVS * 2 * math.pi * thb["r0"]
    rows = []
    for r in headline(40):
        rng = np.random.default_rng(np.random.SeedSequence(r["seed_key"]))
        rng.normal(0, G_SD_DB, rough.n_sub)
        V = rng.uniform(60.0, 110.0, 50) * KMH
        W = rng.uniform(*W_RANGE, 50)
        fs = np.interp(np.log(W), np.log(Wn), fsn)
        T = L / V
        lo, hi = np.maximum(fs - HALF, F_LO), np.minimum(fs + HALF, F_HI)
        nb = np.floor(hi * T) - np.ceil(lo * T) + 1
        rows.append({"seed": r["seed"], "j": r["seed_key"][2], "err_pct": 100 * (math.exp(r["err_log"][0]) - 1),
                     "speed_sd_kmh": float(np.std(V / KMH, ddof=1)), "payload_sd_t": float(np.std(W, ddof=1)),
                     "speed_min_kmh": float(V.min() / KMH), "bins_near_resonance": float(nb.sum())})
    feats = ["speed_sd_kmh", "payload_sd_t", "speed_min_kmh", "bins_near_resonance"]
    X = np.array([[r[k] for k in feats] for r in rows])
    X = (X - X.mean(0)) / X.std(0, ddof=1)
    y = np.array([r["err_pct"] for r in rows])
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    r2 = 1 - res @ res / np.sum((y - y.mean()) ** 2)
    dfm, dfr = len(feats), len(y) - len(feats) - 1
    pF = float(stats.f.sf((r2 / dfm) / ((1 - r2) / dfr), dfm, dfr))
    single = {k: {"r": float(stats.pearsonr(X[:, i], y)[0]), "p": float(stats.pearsonr(X[:, i], y)[1])} for i, k in enumerate(feats)}
    return {"n": len(rows), "r2": float(r2), "p_F": pF, "single_feature": single,
            "resonance_hz_at_W": dict(zip([float(w) for w in Wn], [float(x) for x in fsn]))}


def _stats(R):
    e = np.array([r["err_log"][0] for r in R])
    c = np.array([r["crb_log"][0] for r in R])
    se = np.array([r["se_log"][0] for r in R])
    k = int(np.sum(np.abs(e) <= 1.6448536269514722 * se))
    return {"n": len(R), "bias_pct": float(np.mean(np.exp(e) - 1) * 100),
            "bias_se_pct": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(R)) * 100),
            "rmse_pct": float(np.sqrt(np.mean(e**2)) * 100), "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / np.sqrt(np.mean(c**2))),
            "coverage90_wald": k / len(R), "cB_bias_pct": float(np.mean([math.exp(r["err_log"][1]) - 1 for r in R]) * 100),
            "all_converged": all(r["converged"] for r in R)}


def summarise():
    out = {"headline_seed123": _stats([dict(r, j=r["seed_key"][2]) for r in headline(40, 123) if r["seed_key"][2] < 10]),
           "headline_seed42": _stats([dict(r, j=r["seed_key"][2]) for r in headline(40, 42) if r["seed_key"][2] < 10])}
    base = {r["seed_key"][2]: 100 * (math.exp(r["err_log"][0]) - 1) for r in headline(40, 123)}
    base_se = {r["seed_key"][2]: r["se_log"][0] for r in headline(40, 123)}
    out["variants"] = {}
    for name in VARIANTS:
        R = list({r["j"]: r for r in _rows(OUT / f"{name}.jsonl")}.values())     # one row per dataset
        if R:
            s = _stats(R)
            d = [100 * (math.exp(r["err_log"][0]) - 1) - base[r["j"]] for r in R if r["j"] in base]
            s["max_abs_diff_vs_headline_pp"] = float(max(abs(x) for x in d)) if d else None
            s["mean_diff_vs_headline_pp"] = float(np.mean(d)) if d else None
            s["n_lower_than_headline"] = int(sum(x < 0 for x in d))
            q = [r["se_log"][0] / base_se[r["j"]] for r in R if r["j"] in base_se]
            s["se_ratio_vs_headline_mean"] = float(np.mean(q)) if q else None
            s["se_ratio_vs_headline_range"] = [float(min(q)), float(max(q))] if q else None
            out["variants"][name] = s
    Rr = list({tuple(r["seed_key"]): r for r in _rows(OUT / "robust.jsonl")}.values())
    if Rr:
        e = np.array([r["err_log"] for r in Rr])
        cov = {}
        for name in ["model"] + [c[0] for c in CL]:
            s = np.array([r["se"][name] for r in Rr])
            k = int(np.sum(np.abs(e) <= 1.6448536269514722 * s))
            cov[name] = {"se_median_pct": float(np.median(s) * 100), "coverage90": k / len(Rr), "coverage90_ci95": cp_interval(k, len(Rr))}
        out["robust_se_40db"] = {"n": len(Rr), **cov}
    out["regression"] = regress()
    save_result("p4/bias_diag_y25", out, cfg={"config": "config/snapshots/headline_freight_v1 (headline datasets)",
                                               "datasets": "keys (seed, 40, j), j < 10; variants on seed 123", "variants": VARIANTS},
                seed=123)
    print(json.dumps({k: v for k, v in out.items()}, indent=1, default=str)[:5000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=tuple(VARIANTS))
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=10)
    a = ap.parse_args()
    if a.variant:
        variant(a.variant, a.j0, a.j1)
    if a.robust:
        robust_run(a.j0, a.j1)
    if a.summarise:
        summarise()
