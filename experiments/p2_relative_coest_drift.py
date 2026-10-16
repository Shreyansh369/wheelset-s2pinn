"""Relative change: per-period co-estimation, foundation-stiffness drift, and a fresh check of the gain interval.

Rail-coupled model (4 wheels, CT23 subset), debiased Whittle, N = 50 passes per period, 60-110 km/h,
SNR 40 dB. Same designs as experiments/p2_relative_change.py (baseline (41, 0), later (41, 1)).
Estimators: "nominal" (kB0, cB) and "coest" (kB0, cB, kf, kH0), each period fitted separately, so
the co-estimated kf and kH0 may differ between periods.

--coest-rel  pseudo-true relative change (x = 5%) with the coest estimator for the misspecification cases
             of p2_relative_change (same misspecification in both periods) -> gain per log error, kappa_coest.
--drift      foundation stiffness differs between periods (later kf x0.8, x0.9, x1.1, x1.2; seasonal pad
             stiffness), true change 0 and -5%; both estimators. False-alarm rate (one-sided test for a
             decrease at 5%, statistical SE only) and minimum detectable change (90% detection) under drift,
             from pseudo-true biases and CRBs.
--drift-mc   Monte Carlo check of the false-alarm rate for kf x1.2 and no true change (6 replicates).
--kappa-mc   fresh Monte Carlo for the kappa = 0.26 interval of the nominal estimator: every replicate draws
             all five misspecifications from the stated 1-sigma ranges (lognormal; the same in both periods)
             and a true reduction uniform in 2-10%; coverage of D_hat +- 1.645 sqrt(se^2 + (0.26 D_hat)^2).
--summarise  writes results/p2/relative_coest_drift.json.
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
from scipy.optimize import brentq  # noqa: E402
from scipy.stats import norm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import START, TRUTH, WIM, cp_interval, setup  # noqa: E402
from experiments.p2_model_form_mw import NOM, RANGES  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from experiments.p2_relative_change import CASES, N, SPEEDS, gen, truth  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "relative_change_runs"
EST = {"nominal": ("kB0", "cB"), "coest": ("kB0", "cB", "kf", "kH0")}
COEST_CASES = ("control", "unsprung_x0.95", "unsprung_x1.05", "axle_damp_x0.5", "axle_damp_x2",
               "eta_f_x0.82", "eta_f_x1.22", "kf_x1.2", "kH0_x1.15")
DRIFT_F = (0.8, 0.9, 1.1, 1.2)
KAPPA = 0.26


def families(mw, thb):
    out = {}
    for e, names in EST.items():
        out[e] = MultiWheelFamily(mw, dict(thb, **{k: v for k, v in NOM.items() if k not in names}), names=names)
    return out


def phi(names, kB0=None, start=False):
    v = {**(START if start else TRUTH), **NOM}
    if kB0 is not None:
        v["kB0"] = kB0
    return np.log([v[n] for n in names])


def setup_all():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fams = families(mw, thb)
    designs = {"base": mw_dataset(sm, thb, rough, mw, (41, 0), N=N, speeds=SPEEDS, g_sd=0.0),
               "later": mw_dataset(sm, thb, rough, mw, (41, 1), N=N, speeds=SPEEDS, g_sd=0.0)}
    return sm, thb, rough, mw, fams, designs


def pt(est, mw, th_true, names):
    r = est.pseudo_true(MultiWheelFamily(mw, th_true, names=()), {}, np.zeros(est.S), est.lw_meas.copy(), phi(names, start=True))
    return r["phi"][0], r["converged"]


def coest_rel(cases):
    sm, thb, rough, mw, fams, designs = setup_all()
    fp = RUN_DIR / "coest_pseudo.jsonl"
    done = {(json.loads(l)["case"], json.loads(l)["set"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    for cname in cases:
        for setname, x in (("base", 0.0), ("later", 0.05)):
            if (cname, setname) in done:
                continue
            P, Wm, Ws, g = designs[setname]
            est = MultiPassWhittle(P, Ws, WIM, rough, fams["coest"], debias=True)
            kt = TRUTH["kB0"] * (1 - x)
            lk, ok = pt(est, mw, truth(thb, CASES[cname], kt), EST["coest"])
            crb = est.expected_fisher(phi(EST["coest"], kB0=kt), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
            row = {"case": cname, "set": setname, "x": x, "log_k_hat": lk, "crb_log": crb, "converged": ok}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, flush=True)


DRIFT_FILE = "drift_pseudo_freight.jsonl"   # sourced-nominal round (2026-10-15); earlier placeholder round: drift_pseudo.jsonl


def drift(estimators):
    import time
    t_start, fit_max = time.perf_counter(), [45 * 60]
    sm, thb, rough, mw, fams, designs = setup_all()
    fp = RUN_DIR / DRIFT_FILE
    done = {(json.loads(l)["estimator"], json.loads(l)["f"], json.loads(l)["x"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    for e in estimators:
        for f in (1.0,) + DRIFT_F:
            for x in ((0.0,) if f == 1.0 else (0.0, 0.05)):
                if (e, f, x) in done:
                    continue
                if time.perf_counter() - t_start + fit_max[0] > 110 * 60:
                    print("deadline", flush=True)
                    return
                t0 = time.perf_counter()
                setname = "base" if f == 1.0 else "later"
                P, Wm, Ws, g = designs[setname]
                est = MultiPassWhittle(P, Ws, WIM, rough, fams[e], debias=True)
                kt = TRUTH["kB0"] * (1 - x)
                th = truth(thb, {"kf": f} if f != 1.0 else {}, kt)
                lk, ok = pt(est, mw, th, EST[e])
                crb = est.expected_fisher(phi(EST[e], kB0=kt), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
                row = {"estimator": e, "f": f, "x": x, "set": setname, "log_k_hat": lk, "crb_log": crb, "converged": ok,
                       "wall_s": time.perf_counter() - t0}
                with fp.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(row, flush=True)
                fit_max[0] = max(fit_max[0], 1.3 * row["wall_s"])


def drift_mc(n_rep, estimators, f=1.2, rep_start=0):
    sm, thb, rough, mw, fams, designs = setup_all()
    fp = RUN_DIR / f"drift_mc_kf{f}.jsonl"
    done = {(json.loads(l)["estimator"], json.loads(l)["rep"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    for j in range(rep_start, n_rep):
        data = None
        for e in estimators:
            if (e, j) in done:
                continue
            if data is None:
                data = {"base": gen(sm, truth(thb, {}, TRUTH["kB0"]), rough, mw, (43, j, 0)),
                        "later": gen(sm, truth(thb, {"kf": f}, TRUTH["kB0"]), rough, mw, (43, j, 1))}
            res = {}
            for s in ("base", "later"):
                P, Wm, Ws, g = data[s]
                est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams[e], debias=True)
                r = est.fit(phi(EST[e], start=True))
                res[s] = (r["phi"][0], r["se_log"][0], r["converged"])
            d = res["later"][0] - res["base"][0]
            se = math.hypot(res["base"][1], res["later"][1])
            row = {"estimator": e, "rep": j, "f": f, "D_hat": d, "se": se, "alarm": bool(d < -1.645 * se),
                   "converged": res["base"][2] and res["later"][2]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, flush=True)


def kappa_mc(n_rep, rep_start=0):
    sm, thb, rough, mw, fams, designs = setup_all()
    fp = RUN_DIR / "kappa_mc.jsonl"
    done = {json.loads(l)["rep"] for l in fp.read_text().splitlines()} if fp.exists() else set()
    for j in range(rep_start, n_rep):
        if j in done:
            continue
        rng = np.random.default_rng(np.random.SeedSequence([44, j]))
        mis = {p: float(math.exp(RANGES[p][0] * rng.standard_normal())) for p in RANGES}
        x = float(rng.uniform(0.02, 0.10))
        res = {}
        for s, kt in (("base", TRUTH["kB0"]), ("later", TRUTH["kB0"] * (1 - x))):
            P, Wm, Ws, g = gen(sm, truth(thb, mis, kt), rough, mw, (44, j, 0 if s == "base" else 1))
            est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["nominal"], debias=True)
            r = est.fit(phi(EST["nominal"], start=True))
            res[s] = (r["phi"][0], r["se_log"][0], r["converged"])
        d = res["later"][0] - res["base"][0]
        dt = math.log(1 - x)
        se = math.hypot(res["base"][1], res["later"][1])
        row = {"rep": j, "misspec": mis, "x": x, "D_hat": d, "D_true": dt, "se": se,
               "abs_err_base": res["base"][0] - math.log(TRUTH["kB0"]),
               "covered_stat": bool(abs(d - dt) <= 1.645 * se),
               "covered_kappa": bool(abs(d - dt) <= 1.645 * math.sqrt(se**2 + (KAPPA * d) ** 2)),
               "converged": res["base"][2] and res["later"][2]}
        with fp.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)


def _rows(name):
    fp = RUN_DIR / name
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def mdc_under(b0, b5, s0, alpha=0.05, power=0.90):
    """Smallest reduction m detected with prob >= power; b(m) linear between the pseudo-true biases at 0 and 5%."""
    z = norm.ppf(1 - alpha)

    def pdet(m):
        b = b0 + (b5 - b0) * m / 0.05
        return norm.cdf((-z * s0 - (math.log(1 - m) + b)) / s0)
    if pdet(1e-9) >= power:
        return 0.0
    if pdet(0.5) < power:
        return float("inf")
    return float(brentq(lambda m: pdet(m) - power, 1e-9, 0.5) * 100)


def drift_table(fname):
    """Pseudo-true drift table (apparent change, bias at a 5% drop, false-alarm rate, MDC) from a run file."""
    dr = {(r["estimator"], r["f"], r["x"]): r for r in _rows(fname)}
    drift_tab = []
    for e in EST:
        if (e, 1.0, 0.0) not in dr:
            continue
        base = dr[(e, 1.0, 0.0)]
        for f in DRIFT_F:
            if (e, f, 0.0) not in dr or (e, f, 0.05) not in dr:
                continue
            l0, l5 = dr[(e, f, 0.0)], dr[(e, f, 0.05)]
            b0 = l0["log_k_hat"] - base["log_k_hat"]
            b5 = (l5["log_k_hat"] - base["log_k_hat"]) - math.log(0.95)
            s0 = math.hypot(base["crb_log"], l0["crb_log"])
            drift_tab.append({"estimator": e, "kf_factor_later": f, "apparent_change_no_true_change_pct": (math.exp(b0) - 1) * 100,
                              "bias_at_5pct_drop_pp": ((math.exp(math.log(0.95) + b5) - 1) + 0.05) * 100,
                              "sd_change_pct": s0 * 100, "false_alarm_rate": float(norm.cdf(-1.645 - b0 / s0)),
                              # MDC is only meaningful when the test still holds its 5% false-alarm rate
                              "mdc_pct": mdc_under(b0, b5, s0) if norm.cdf(-1.645 - b0 / s0) <= 0.06 else None})
    nodrift = {}
    for e in EST:
        if (e, 1.0, 0.0) in dr:
            s0 = math.sqrt(2) * dr[(e, 1.0, 0.0)]["crb_log"]
            nodrift[e] = {"sd_change_pct": s0 * 100, "mdc_pct": mdc_under(0.0, 0.0, s0)}
    return {"table": drift_tab, "no_drift_reference": nodrift}


def summarise_freight():
    """Drift pseudo-true at the current (sourced) configuration -> results/p2/drift_freight.json."""
    out = drift_table(DRIFT_FILE)
    print(json.dumps(out, indent=1))
    save_result("p2/drift_freight", out, cfg={"model": "4-wheel rail-coupled (config nominal: Y25/Eanos layout, 60E1 ballasted)",
                                             "N_per_period": N, "speeds_kmh": SPEEDS, "snr_db": 40, "estimators": EST,
                                             "drift_kf_factors": DRIFT_F, "test": "one-sided decrease, alpha 0.05; detection 90%"}, seed=41)


def summarise():
    out = {}
    # (1) coest relative change gains
    cr = {(r["case"], r["set"]): r for r in _rows("coest_pseudo.jsonl")}
    pairs = {"unsprung_scale": ("unsprung_x0.95", "unsprung_x1.05", 0.95, 1.05), "axle_damp_scale": ("axle_damp_x0.5", "axle_damp_x2", 0.5, 2.0),
             "eta_f": ("eta_f_x0.82", "eta_f_x1.22", 0.82, 1.22)}
    dt = math.log(0.95)
    gains = {}
    for p, (cm, cp, fm, fp_) in pairs.items():
        try:
            g = [((cr[(c, "later")]["log_k_hat"] - cr[(c, "base")]["log_k_hat"]) - dt) / abs(dt) for c in (cm, cp)]
            gains[p] = (g[1] - g[0]) / (math.log(fp_) - math.log(fm))
        except KeyError:
            pass
    single = {}
    for c in ("control", "kf_x1.2", "kH0_x1.15"):
        if (c, "later") in cr and (c, "base") in cr:
            single[c] = (((cr[(c, "later")]["log_k_hat"] - cr[(c, "base")]["log_k_hat"]) - dt) / abs(dt))
    terms = {p: abs(g) * (0.03 if p == "unsprung_scale" else RANGES[p][0]) for p, g in gains.items()}
    out["coest_relative"] = {"gain_per_log": gains, "gain_ratio_single_cases": single, "kappa_terms": terms,
                             "kappa_coest": float(math.sqrt(sum(t**2 for t in terms.values()))) if terms else None,
                             "note": "kf and kH0 are co-estimated, so their gain terms are taken as the single-case ratios (kf x1.2, kH0 x1.15)"}
    # (2) drift
    out["drift"] = drift_table("drift_pseudo.jsonl")
    # (3) drift MC check
    dm = []
    for fp in sorted(RUN_DIR.glob("drift_mc_*.jsonl")):
        R = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        for e in EST:
            Re = [r for r in R if r["estimator"] == e]
            if Re:
                k = sum(r["alarm"] for r in Re)
                dm.append({"file": fp.name, "estimator": e, "n": len(Re), "false_alarms": k, "rate": k / len(Re),
                           "rate_ci95": cp_interval(k, len(Re)), "D_hat_mean_pct": float(np.mean([math.exp(r["D_hat"]) - 1 for r in Re]) * 100)})
    out["drift_mc"] = dm
    # (4) kappa check
    km = _rows("kappa_mc.jsonl")
    if km:
        ks, kk = sum(r["covered_stat"] for r in km), sum(r["covered_kappa"] for r in km)
        out["kappa_mc"] = {"n": len(km), "coverage_statistical": ks / len(km), "coverage_statistical_ci95": cp_interval(ks, len(km)),
                           "coverage_kappa": kk / len(km), "coverage_kappa_ci95": cp_interval(kk, len(km)),
                           "abs_bias_base_pct_rms": float(math.sqrt(np.mean([(math.exp(r["abs_err_base"]) - 1) ** 2 for r in km])) * 100),
                           "rel_gain_error_rms": float(math.sqrt(np.mean([((r["D_hat"] - r["D_true"]) / abs(r["D_true"])) ** 2 for r in km]))),
                           "all_converged": all(r["converged"] for r in km)}
    print(json.dumps(out, indent=1))
    save_result("p2/relative_coest_drift", out, cfg={"model": "4-wheel rail-coupled, debiased Whittle", "N_per_period": N,
                                                     "speeds_kmh": SPEEDS, "snr_db": 40, "estimators": EST, "kappa_nominal": KAPPA,
                                                     "ranges": RANGES, "drift_kf_factors": DRIFT_F,
                                                     "test": "one-sided decrease, alpha 0.05; detection 90%"}, seed=41)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--coest-rel", action="store_true")
    ap.add_argument("--drift", action="store_true")
    ap.add_argument("--drift-mc", action="store_true")
    ap.add_argument("--kappa-mc", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--summarise-freight", action="store_true")
    ap.add_argument("--cases", nargs="+", default=list(COEST_CASES))
    ap.add_argument("--estimators", nargs="+", default=list(EST))
    ap.add_argument("--n-rep", type=int, default=6)
    ap.add_argument("--rep-start", type=int, default=0, help="first replicate (to split replicates across processes)")
    a = ap.parse_args()
    if a.coest_rel:
        coest_rel(a.cases)
    if a.drift:
        drift(a.estimators)
    if a.drift_mc:
        drift_mc(a.n_rep, a.estimators, rep_start=a.rep_start)
    if a.kappa_mc:
        kappa_mc(a.n_rep, rep_start=a.rep_start)
    if a.summarise:
        summarise()
    if a.summarise_freight:
        summarise_freight()
