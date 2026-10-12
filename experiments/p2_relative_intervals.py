"""Relative change as the headline output: intervals with a model-form term, their coverage, the minimum
detectable change, and the absolute budget with the unsprung mass known to +-1%.

1. Model-form gain. From the pseudo-true relative-change fits (experiments/p2_relative_change.py), the
   bias of D = log(k_later / k_base) is close to proportional to |D|: b = g |D|. For each parameter p the
   gain per unit log error is gamma_p = (g(+) - g(-)) / (log f+ - log f-), averaged over the 2/5/10%
   reductions; kappa = sqrt(sum_p (gamma_p sigma_p)^2) with the realistic 1-sigma ranges of
   experiments/p2_model_form_mw.RANGES (unsprung mass 3%, or 1% from drawings).
2. Interval: D_hat +- 1.645 sqrt(se^2 + (kappa D_hat)^2); coverage checked on the relative-change Monte
   Carlo (control, unsprung x1.05, kf x1.2 at a 5% reduction) against the statistical-only interval.
3. Minimum detectable change (one-sided test for a decrease, 5% false-alarm rate, 90% detection):
   smallest m with Phi((m - 1.645 s0) / sqrt(s0^2 + kappa^2 m^2)) = 0.9, s0 = sqrt(2) x CRB(N, SNR) of the
   rail-coupled model (baseline and later sets of N passes each), also with s0 inflated by the
   empirical RMSE/CRB of the headline Monte Carlo at that SNR.
4. Absolute bias budget (rail-coupled, pseudo-true) with sigma_mass = 3% vs 1%.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.optimize import brentq  # noqa: E402
from scipy.stats import norm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import TRUTH, WIM, cp_interval, setup  # noqa: E402
from experiments.p2_model_form_mw import NOM, RANGES  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

RC = RESULTS_DIR / "p2" / "relative_change_runs"
MF = RESULTS_DIR / "p2" / "model_form_mw_runs"
PAIRS = {"unsprung_scale": ("unsprung_x0.95", "unsprung_x1.05", 0.95, 1.05), "kH0": ("kH0_x0.85", "kH0_x1.15", 0.85, 1.15),
         "axle_damp_scale": ("axle_damp_x0.5", "axle_damp_x2", 0.5, 2.0), "kf": ("kf_x0.8", "kf_x1.2", 0.8, 1.2),
         "eta_f": ("eta_f_x0.82", "eta_f_x1.22", 0.82, 1.22)}


def gains():
    rows = [json.loads(l) for fp in RC.glob("pseudo_*.jsonl") for l in fp.read_text().splitlines() if l.strip()]
    lk = {(r["case"], r["set"], r["x"]): r["log_k_hat"] for r in rows}
    out = {}
    for p, (cm, cp, fm, fp_) in PAIRS.items():
        gs = []
        for x in (0.02, 0.05, 0.10):
            try:
                dt = math.log(1 - x)
                g = []
                for c in (cm, cp):
                    dh = lk[(c, "later", x)] - lk[(c, "base", 0.0)]
                    g.append((dh - dt) / abs(dt))
                gs.append((g[1] - g[0]) / (math.log(fp_) - math.log(fm)))
            except KeyError:
                pass
        if gs:
            out[p] = {"gamma_per_log": float(np.mean(gs)), "gamma_by_x": gs}
    return out


def kappa(gam, sig_mass):
    terms = {}
    for p, g in gam.items():
        sig = sig_mass if p == "unsprung_scale" else RANGES[p][0]
        terms[p] = abs(g["gamma_per_log"]) * sig
    return float(math.sqrt(sum(t**2 for t in terms.values()))), terms


def coverage(kap):
    rows = [json.loads(l) for fp in RC.glob("mc_*.jsonl") for l in fp.read_text().splitlines() if l.strip()]
    out = {}
    for case in sorted({r["case"] for r in rows}):
        R = [r for r in rows if r["case"] == case]
        e = np.array([r["D_hat"] - r["D_true"] for r in R])
        se = np.array([r["se"] for r in R])
        dh = np.array([r["D_hat"] for r in R])
        k_stat = int(np.sum(np.abs(e) <= 1.645 * se))
        k_comb = int(np.sum(np.abs(e) <= 1.645 * np.sqrt(se**2 + (kap * dh) ** 2)))
        out[case] = {"n": len(R), "x": R[0]["x"], "bias_pp": float(np.mean((np.exp(dh) - 1) - (np.exp([r["D_true"] for r in R]) - 1)) * 100),
                     "coverage_statistical": k_stat / len(R), "coverage_statistical_ci95": cp_interval(k_stat, len(R)),
                     "coverage_combined": k_comb / len(R), "coverage_combined_ci95": cp_interval(k_comb, len(R)),
                     "half_width_combined_pp_median": float(np.median(1.645 * np.sqrt(se**2 + (kap * dh) ** 2)) * 100)}
    return out


def crb_table():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, dict(thb, **NOM), names=("kB0", "cB"))
    out = {}
    for N in (50, 200):
        for snr in (20.0, 40.0):
            P, Wm, Ws, g = mw_dataset(sm, thb, rough, mw, (51, N, int(snr)), N=N, snr=snr, g_sd=0.0)
            est = MultiPassWhittle(P, Ws, WIM, rough, fam, debias=True)
            out[f"N{N}_snr{int(snr)}"] = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.zeros(est.S), np.log(Ws))["crb_log"][0]
            print(N, snr, out[f"N{N}_snr{int(snr)}"], flush=True)
    return out


def mdc(s0, kap, alpha=0.05, power=0.90):
    z = norm.ppf(1 - alpha)
    if kap * norm.ppf(power) >= 1:
        return float("inf")
    f = lambda m: norm.cdf((m - z * s0) / math.sqrt(s0**2 + (kap * m) ** 2)) - power  # noqa: E731
    m = brentq(f, z * s0, 5.0)
    return float((1 - math.exp(-m)) * 100)


def mass_budget():
    rows = [json.loads(l) for fp in MF.glob("*.jsonl") for l in fp.read_text().splitlines() if l.strip()]
    out = {}
    for ename in ("nominal", "coest"):
        for sm_ in (0.03, 0.01):
            terms = {}
            for p in RANGES:
                sig = sm_ if p == "unsprung_scale" else RANGES[p][0]
                R = {round(r["factor"], 6): r["bias_pct"] for r in rows if r["estimator"] == ename and r["param"] == p}
                lo, hi = R.get(round(math.exp(-sig), 6)), R.get(round(math.exp(sig), 6))
                if lo is not None and hi is not None:
                    terms[p] = max(abs(lo), abs(hi))
            out[f"{ename}_mass{int(sm_ * 100)}pct"] = {"terms_pct": terms, "rss_pct": float(math.sqrt(sum(t**2 for t in terms.values()))),
                                                      "complete": len(terms) == len(RANGES)}
    return out


def main():
    with Timer() as tm:
        gam = gains()
        k3, t3 = kappa(gam, 0.03)
        k1, t1 = kappa(gam, 0.01)
        cov3, cov1 = coverage(k3), coverage(k1)
        crb = crb_table()
        head = {}
        for nm in ("headline", "headline_noisefit", "headline_debias"):
            fp = RESULTS_DIR / "p2" / f"{nm}.json"
            if fp.exists():
                for c in json.loads(fp.read_text())["payload"]["cells"]:
                    head[(nm, int(c["snr_db"]))] = c["kB0_pooled"]["rmse_over_crb"]
        infl = {20: max(1.0, head.get(("headline", 20), 1.0)), 40: max(1.0, head.get(("headline", 40), 1.0))}
        md = []
        for key, c in crb.items():
            N, snr = int(key.split("_")[0][1:]), int(key.split("snr")[1])
            s0 = math.sqrt(2) * c
            for lab, kap in (("mass3pct", k3), ("mass1pct", k1), ("no_model_form", 0.0)):
                md.append({"N": N, "snr_db": snr, "kappa": lab, "sd_D0_pct": s0 * 100,
                           "mdc_pct_crb": mdc(s0, kap), "mdc_pct_inflated": mdc(s0 * infl[snr], kap), "inflation": infl[snr]})
        mb = mass_budget()
    for r in md:
        print(r)
    print("kappa", k3, t3, k1, t1)
    print("coverage", cov3)
    print("mass budget", mb)
    save_result("p2/relative_intervals", {"gains": gam, "kappa_mass3": {"kappa": k3, "terms": t3}, "kappa_mass1": {"kappa": k1, "terms": t1},
                                          "coverage_mass3": cov3, "coverage_mass1": cov1, "crb_rail_coupled": crb, "mdc": md,
                                          "abs_budget_mass": mb, "headline_rmse_over_crb": {f"{k[0]}_{k[1]}": v for k, v in head.items()}},
                cfg={"alpha": 0.05, "power": 0.90, "test": "one-sided, decrease", "ranges": RANGES,
                     "unsprung_mass_sigma": {"0.03": "assumption (see docs/paper1_outline.md)", "0.01": "drawings / weighed wheelsets"}},
                seed=51, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
