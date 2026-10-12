"""Phase 2 (1) on the rail-coupled model: model-form sensitivity and bias budget for kB0.

Model: instrumented FE wheelset + 3 neighbour wheelsets (CT23 4-wheel subset) on an infinite
Timoshenko BS113A rail with a hysteretic foundation (kf = 154 MN/m^2, eta_f = 0.2; CT23), Hertz
contact kH0 = 1.4e9 N/m at W0; debiased Whittle likelihood. Rail rho A and EI are fixed by the rail
type and are not perturbed. Perturbed (the estimator does not know): foundation stiffness kf and loss
factor eta_f, contact stiffness kH0, unsprung mass (whole wheelset mass matrix, all wheelsets) and
axle damping (all wheelsets).

Method: first-order misspecified-ML bias b = J^-1 E[score at the truth] (MultiPassWhittle.misspec_bias),
nuisances free, averaged over 3 random designs (N = 50, 60-110 km/h, payload 5.5-22.5 t, SNR 40 dB).
Sensitivity = (b(+10%) - b(-10%)) / 2, reported as % kB0 bias per 10% parameter error; +-30% checks
linearity. Estimators: "nominal" (kB0, cB), "coest" (kB0, cB, kf, kH0), "coest_eta" (+ eta_f).
Validation: (i) the same formula on the scenario-(a) rail-oscillator model against the Monte Carlo
biases of experiments/p2_model_form.py; (ii) Monte Carlo fits on the rail-coupled model for two cases.
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

from experiments.p1_fe_direct import START, TRUTH, WIM, setup  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from experiments.p2_model_form import NOMINAL as OSC_NOMINAL, dataset as osc_dataset  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

PARAMS = ("kf", "eta_f", "kH0", "unsprung_scale", "axle_damp_scale")
NOM = {"kf": 154e6, "eta_f": 0.2, "kH0": 1.4e9, "unsprung_scale": 1.0, "axle_damp_scale": 1.0}
ESTIMATORS = {"nominal": ("kB0", "cB"), "coest": ("kB0", "cB", "kf", "kH0"), "coest_eta": ("kB0", "cB", "kf", "kH0", "eta_f")}
# realistic 1-sigma uncertainty (log scale) and where it comes from
RANGES = {
    "kf": (0.35, "CT23: in-situ ABA-derived kf 1.2-2.6x the lab value (Tables 2, 5 vs Sec. 5.1.1); section-to-section spread"),
    "eta_f": (0.20, "CT23 Sec. 5.1.1: literature loss factor 0.2-0.3"),
    "kH0": (0.15, "assumption: Hertz constant C_H for freight wheel/60E1 profiles not sourced (CT23 value is metro); wheel load from WIM"),
    "unsprung_scale": (0.03, "assumption: design mass known; wear and fittings"),
    "axle_damp_scale": (0.50, "assumption: axle damping is a placeholder (1% at 80 Hz); factor ~1.65 either way"),
}
FIT_N, SPEEDS = 50, (60.0, 110.0)


def designs(sm, thb, rough, mw, n=3):
    """Random designs (speeds, payloads, bins, floors); W_meas = true W so that lw at the truth is exact."""
    return [mw_dataset(sm, thb, rough, mw, (31, k), N=FIT_N, speeds=SPEEDS, g_sd=0.0) for k in range(n)]


def lin_bias(est, fam_fit, names, fam_true):
    tv = {**TRUTH, **NOM}
    phi = np.log([tv[n] for n in names])
    return est.misspec_bias(phi, np.zeros(est.S), est.lw_meas.copy(), fam_true, {})


def sensitivity(args):
    sm, thb, rough, _ = setup()
    mws, track = models(sm)
    mw = mws["4"]
    rows = []
    with Timer() as tm:
        dss = designs(sm, thb, rough, mw)
        for ename, names in ESTIMATORS.items():
            fam_fit = MultiWheelFamily(mw, dict(thb, **{k: v for k, v in NOM.items() if k not in names}), names=names)
            ests = [MultiPassWhittle(P, Ws, WIM, rough, fam_fit, debias=True) for P, Wm, Ws, g in dss]
            for pname in PARAMS:
                res = {}
                for f in (0.7, 0.9, 1.1, 1.3):
                    true_all = dict(thb, **TRUTH, **NOM)
                    true_all[pname] = NOM[pname] * f
                    fam_true = MultiWheelFamily(mw, true_all, names=())
                    b = [lin_bias(e, fam_fit, names, fam_true)["bias_log"][0] for e in ests]
                    res[f] = float(np.mean(b))
                crb = float(np.mean([lin_bias(e, fam_fit, names, MultiWheelFamily(mw, dict(thb, **TRUTH, **NOM), names=()))["crb_log"][0]
                                     for e in ests]))
                sens10 = (res[1.1] - res[0.9]) / 2 * 100
                sens30 = (res[1.3] - res[0.7]) / 6 * 100
                rows.append({"estimator": ename, "param": pname, "bias_pct": {str(k): v * 100 for k, v in res.items()},
                             "sens_pct_per_10pct": sens10, "sens_pct_per_10pct_from_30": sens30, "crb_pct": crb * 100})
                print(ename, pname, round(sens10, 3), round(sens30, 3), {k: round(v * 100, 3) for k, v in res.items()}, flush=True)
    budget = {}
    for ename in ESTIMATORS:
        terms = {}
        for r in rows:
            if r["estimator"] != ename:
                continue
            sig = RANGES[r["param"]][0]
            terms[r["param"]] = r["sens_pct_per_10pct"] * sig / 0.10
        budget[ename] = {"terms_pct_1sigma": terms, "rss_pct": float(math.sqrt(sum(t**2 for t in terms.values()))),
                         "sum_abs_pct": float(sum(abs(t) for t in terms.values())),
                         "crb_pct": float(np.mean([r["crb_pct"] for r in rows if r["estimator"] == ename]))}
        print(ename, budget[ename], flush=True)
    save_result("p2/model_form_mw_sensitivity", {"rows": rows, "budget": budget, "ranges": RANGES}, cfg={
        "model": "4 wheels (CT23 subset), BS113A Timoshenko rail, kf 154e6, eta_f 0.2, kH0 1.4e9", "N": FIT_N,
        "speeds_kmh": SPEEDS, "snr_db": 40, "designs": 3, "method": "first-order misspecified-ML bias (J^-1 E[score])",
        "likelihood": "debiased Whittle", "nominal": NOM, "truth": TRUTH}, seed=31, wall_seconds=tm.seconds)


def validate_osc(args):
    """Linearised bias on the rail-oscillator model, for comparison with the p2_model_form.py Monte Carlo."""
    from experiments.p2_model_form import CASES, ESTIMATORS as OSC_EST
    sm, thb, rough, _ = setup()
    rows = []
    with Timer() as tm:
        dss = [osc_dataset(sm, thb, rough, {}, (31, k)) for k in range(3)]
        for ename, names in OSC_EST.items():
            fam_fit = SingleWheelsetFamily(sm, dict(thb, **OSC_NOMINAL), names=names)
            tv = {**TRUTH, **OSC_NOMINAL}
            phi = np.log([tv[n] for n in names])
            ests = [MultiPassWhittle(P, Ws, WIM, rough, fam_fit) for P, Wm, Ws, g in dss]
            for cname, case in CASES.items():
                if "per_pass" in case:
                    continue
                true_all = dict(thb, **TRUTH, **OSC_NOMINAL)
                for k, s in case.items():
                    true_all[k] = s if k == "axle_damp_scale" else true_all[k] * s
                fam_true = SingleWheelsetFamily(sm, true_all, names=())
                b = [e.misspec_bias(phi, np.zeros(e.S), e.lw_meas.copy(), fam_true, {})["bias_log"][0] for e in ests]
                rows.append({"case": cname, "estimator": ename, "lin_bias_pct": float(np.mean(b) * 100)})
                print(rows[-1], flush=True)
    save_result("p2/model_form_linear_check", {"rows": rows}, cfg={"model": "scenario (a) rail oscillator", "designs": 3,
                "compare_with": "results/p2/model_form.json (Monte Carlo)"}, seed=31, wall_seconds=tm.seconds)


def mc_check(args):
    """A few full fits on the rail-coupled model to check the linearised biases."""
    sm, thb, rough, _ = setup()
    mws, _ = models(sm)
    mw = mws["4"]
    rows = []
    out = RESULTS_DIR / "p2" / "model_form_mw_mc.jsonl"
    for pname, f in (("kf", 1.3), ("axle_damp_scale", 2.0)):
        for j in range(args.n_data):
            true_all = dict(thb, **TRUTH, **NOM)
            true_all[pname] = NOM[pname] * f
            # the generator reads every model-form key from th (dataset uses dict(thb, **TRUTH))
            passes, Wm, Ws, g = mw_dataset(sm, true_all, rough, mw, (32, j), N=FIT_N, speeds=SPEEDS)
            for ename in ("nominal", "coest"):
                names = ESTIMATORS[ename]
                fam_fit = MultiWheelFamily(mw, dict(thb, **{k: v for k, v in NOM.items() if k not in names}), names=names)
                est = MultiPassWhittle([dict(q) for q in passes], Wm, WIM, rough, fam_fit, debias=True)
                start = {**START, **NOM}
                r = est.fit(np.log([start[n] for n in names]))
                row = {"param": pname, "factor": f, "estimator": ename, "j": j,
                       "err_log_kB0": r["phi"][0] - math.log(TRUTH["kB0"]), "se_log": r["se_log"][0], "converged": r["converged"]}
                rows.append(row)
                with out.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(row, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensitivity", action="store_true")
    ap.add_argument("--validate-osc", action="store_true")
    ap.add_argument("--mc-check", action="store_true")
    ap.add_argument("--n-data", type=int, default=4)
    a = ap.parse_args()
    if a.validate_osc:
        validate_osc(a)
    if a.sensitivity:
        sensitivity(a)
    if a.mc_check:
        mc_check(a)
