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
  --cb-fixed F : with --pairs or --pseudo, c_B fixed at F x nominal in the fit (k_B0, k_f, k_H0 estimated);
             rows to *_cbfix.jsonl (laden band, where c_B is not identified).
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
from experiments.p2_relative_coest_drift import EST, NOM, SPEEDS, families, mdc_under, phi, truth  # noqa: E402
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


CBFIX = ("kB0", "kf", "kH0")


def fam_cbfix(mw, thb_b, F):
    """Co-estimating family with c_B fixed at F x nominal."""
    return MultiWheelFamily(mw, dict(thb_b, **{k: v for k, v in NOM.items() if k not in CBFIX}, cB=TRUTH["cB"] * F), names=CBFIX)


def pseudo(b, cbf=None):
    fp = OUT / (f"pseudo_{b}.jsonl" if cbf is None else f"pseudo_{b}_cbfix.jsonl")
    if cbf is None and fp.exists() and fp.read_text().strip():
        return
    if cbf is not None and cbf in _done(fp, lambda r: r["cB_factor"]):
        return
    sm, thb_b, rough, mw, fams = _base(b)
    P, Wm, Ws, g = pm.dataset(sm, thb_b, rough, mw, (31, 0), N=50, speeds=SPEEDS, g_sd=0.0)
    fam, names = (fams["coest"], EST["coest"]) if cbf is None else (fam_cbfix(mw, thb_b, cbf), CBFIX)
    est = MultiPassWhittle(P, Ws, WIM, rough, fam, debias=True)
    true_all = dict(truth(thb_b, {}, TRUTH["kB0"]), primary_payload_law=True)
    r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi(names, start=True))
    row = {"band": b, "bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100, "phi_hat": r["phi"],
           "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]}
    if cbf is not None:
        row["cB_factor"] = cbf
    _append(fp, row)


def pairs(b, j0, j1, cbf=None):
    fp = OUT / (f"pairs_{b}.jsonl" if cbf is None else f"pairs_{b}_cbfix.jsonl")
    done = _done(fp, lambda r: r["rep"])
    sm, thb_b, rough, mw, fams = _base(b)
    fam, names = (fams["coest"], EST["coest"]) if cbf is None else (fam_cbfix(mw, thb_b, cbf), CBFIX)
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
            res[per] = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True).fit(phi(names, start=True))
        d = res[1]["phi"][0] - res[0]["phi"][0]
        se = math.hypot(res[0]["se_log"][0], res[1]["se_log"][0])
        _append(fp, {"band": b, "rep": j, "cB_factor": cbf, "D_hat": d, "se": se, "err_base": res[0]["phi"][0] - math.log(TRUTH["kB0"]),
                     "err_later": res[1]["phi"][0] - math.log(TRUTH["kB0"]),
                     "converged": res[0]["converged"] and res[1]["converged"], "wall_s": time.perf_counter() - t0})
        tmax = max(tmax, 1.3 * (time.perf_counter() - t0))


def _design(b, key):
    """Speeds and true payloads of a period, replaying the first draws of experiments.p2_relative_change.gen."""
    from experiments.p1_fe_direct import G_SD_DB
    from experiments.p2_relative_change import N as NP, SPEEDS as SP
    rng = np.random.default_rng(np.random.SeedSequence(key))
    g = 10 ** (rng.normal(0, G_SD_DB, _design.nsub) / 10)
    Vs = rng.uniform(*SP, NP)
    Ws = rng.uniform(*BANDS[b][0], NP)
    return Vs, Ws, g


def _lean(b, Pr):
    """Within-band calibration and design check over the zero-change pairs: apparent change D, its SE,
    z, the ratio of the empirical SD of D to the mean reported SE, and whether D follows the difference of
    the periods' mean payload, mean speed or mean roughness level (both periods are drawn identically,
    keys (49, j, 0) and (49, j, 1))."""
    if len(Pr) < 3:
        return None
    _design.nsub = setup()[2].n_sub
    D, se = np.array([r["D_hat"] for r in Pr]), np.array([r["se"] for r in Pr])
    dW, dV, dg = [], [], []
    for r in Pr:
        a, c = _design(b, (49, r["rep"], 0)), _design(b, (49, r["rep"], 1))
        dW.append(c[1].mean() - a[1].mean())
        dV.append(c[0].mean() - a[0].mean())
        dg.append(10 * np.log10(c[2]).mean() - 10 * np.log10(a[2]).mean())
    z = D / se
    corr = lambda x: float(np.corrcoef(x, D)[0, 1])
    slope_W = float(np.polyfit(dW, D, 1)[0] * 100)
    return {"n": len(Pr), "D_mean_pct": float(D.mean() * 100), "D_mean_se_pct": float(D.std(ddof=1) / math.sqrt(len(D)) * 100),
            "D_sd_pct": float(D.std(ddof=1) * 100), "se_mean_pct": float(se.mean() * 100),
            "sd_over_mean_se": float(D.std(ddof=1) / se.mean()), "z_mean": float(z.mean()), "z_sd": float(z.std(ddof=1)),
            "n_positive": int((D > 0).sum()), "level_err_base_mean_pct": float(np.mean([r["err_base"] for r in Pr]) * 100),
            "level_err_later_mean_pct": float(np.mean([r["err_later"] for r in Pr]) * 100),
            "dW_mean_t": float(np.mean(dW)), "dW_sd_t": float(np.std(dW, ddof=1)), "dV_mean_kmh": float(np.mean(dV)),
            "dg_mean_db": float(np.mean(dg)), "corr_D_dW": corr(dW), "corr_D_dV": corr(dV), "corr_D_dg": corr(dg),
            "slope_D_per_t_pct": slope_W}


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
    lean = _lean("empty", rows("pairs_empty.jsonl"))
    if lean:
        out["lean_empty"] = lean
    Pc = rows("pairs_laden_cbfix.jsonl")
    if Pc:
        D, se = np.array([r["D_hat"] for r in Pc]), np.array([r["se"] for r in Pc])
        k = int(np.sum(D < -Z * se))
        out["pairs_laden_cbfix"] = {"n": len(Pc), "false_alarms": k, "rate_ci95": cp_interval(k, len(Pc)),
                                    "D_pct": [float(100 * x) for x in D], "z": [float(x) for x in D / se],
                                    "D_mean_pct": float(np.mean(np.exp(D) - 1) * 100), "se_median_pct": float(np.median(se) * 100),
                                    "level_err_pct": [float(100 * (math.exp(r[x]) - 1)) for r in Pc for x in ("err_base", "err_later")],
                                    "all_converged": all(r["converged"] for r in Pc)}
    Ps = rows("pseudo_laden_cbfix.jsonl")
    if Ps:
        out["pseudo_laden_cbfix"] = {str(r["cB_factor"]): r["bias_pct"] for r in Ps}
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
    ap.add_argument("--cb-fixed", type=float, default=None)
    a = ap.parse_args()
    if a.bounds:
        bounds()
    if a.pseudo:
        pseudo(a.band, a.cb_fixed)
    if a.pairs:
        pairs(a.band, a.j0, a.j1, a.cb_fixed)
    if a.summarise:
        summarise()
