"""Phase 2 (1) on the rail-coupled model: model-form sensitivity and bias budget for kB0.

Model: instrumented FE wheelset + 3 neighbour wheelsets (CT23 4-wheel subset) on an infinite
Timoshenko BS113A rail with a hysteretic foundation (kf = 154 MN/m^2, eta_f = 0.2; CT23), Hertz
contact kH0 = 1.4e9 N/m at W0; debiased Whittle likelihood. Rail rho A and EI are fixed by the rail
type and are not perturbed. Perturbed (the estimator does not know): foundation stiffness kf and loss
factor eta_f, contact stiffness kH0, unsprung mass (whole wheelset mass matrix, all wheelsets) and
axle damping (all wheelsets).

Method: pseudo-true fits (MultiPassWhittle.pseudo_true): every periodogram value is replaced by its
expectation under the perturbed truth and the profile likelihood is maximised, giving the
large-sample bias without linearisation (the first-order formula J^-1 E[score] was checked first and
fails for the large effects; see results/p2/model_form_linear_check.json). One design: N = 50,
60-110 km/h, payload 5.5-22.5 t, SNR 40 dB. Per parameter: +-10% (sensitivity, % kB0 bias per 10%
error) and +-1 sigma of a realistic range (bias budget). Estimators: "nominal" (kB0, cB) and
"coest" (kB0, cB, kf, kH0). Validation of the pseudo-true approach: rail-oscillator cases vs the
Monte Carlo biases of experiments/p2_model_form.py.
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
    """Pseudo-true (expected-data) fits: exact large-sample bias, no linearisation."""
    sm, thb, rough, _ = setup()
    mws, track = models(sm)
    mw = mws["4"]
    rows = []
    out = RESULTS_DIR / "p2" / "model_form_mw_runs"
    out.mkdir(parents=True, exist_ok=True)
    with Timer() as tm:
        P, Wm, Ws, g = designs(sm, thb, rough, mw, n=1)[0]
        for ename in args.estimators:
            names = ESTIMATORS[ename]
            fam_fit = MultiWheelFamily(mw, dict(thb, **{k: v for k, v in NOM.items() if k not in names}), names=names)
            est = MultiPassWhittle(P, Ws, WIM, rough, fam_fit, debias=True)
            start = {**START, **NOM}
            phi0 = np.log([start[n] for n in names])
            for pname in args.params:
                sig = RANGES[pname][0]
                fp = out / f"{ename}__{pname}.jsonl"
                done = {json.loads(l)["factor"] for l in fp.read_text().splitlines()} if fp.exists() else set()
                for f in (0.9, 1.1, math.exp(-sig), math.exp(sig)):
                    if round(f, 6) in {round(x, 6) for x in done}:
                        continue
                    true_all = dict(thb, **TRUTH, **NOM)
                    true_all[pname] = NOM[pname] * f
                    r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi0)
                    row = {"estimator": ename, "param": pname, "factor": f, "bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100,
                           "phi_hat": r["phi"], "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]}
                    with fp.open("a") as fh:
                        fh.write(json.dumps(row) + "\n")
                    print(row, flush=True)
    summarise_sensitivity(tm.seconds)


def summarise_sensitivity(wall=None):
    out = RESULTS_DIR / "p2" / "model_form_mw_runs"
    rows = [json.loads(l) for fp in sorted(out.glob("*.jsonl")) for l in fp.read_text().splitlines() if l.strip()]
    table, budget = [], {}
    for ename in ESTIMATORS:
        terms = {}
        for pname in PARAMS:
            R = {round(r["factor"], 6): r["bias_pct"] for r in rows if r["estimator"] == ename and r["param"] == pname}
            if not R:
                continue
            sig = RANGES[pname][0]
            b_lo, b_hi = R.get(round(math.exp(-sig), 6)), R.get(round(math.exp(sig), 6))
            sens = (R[round(1.1, 6)] - R[round(0.9, 6)]) / 2 if round(1.1, 6) in R and round(0.9, 6) in R else None
            table.append({"estimator": ename, "param": pname, "sens_pct_per_10pct": sens,
                          "bias_at_minus_1sigma_pct": b_lo, "bias_at_plus_1sigma_pct": b_hi, "sigma_log": sig,
                          "range_source": RANGES[pname][1]})
            if b_lo is not None and b_hi is not None:
                terms[pname] = max(abs(b_lo), abs(b_hi))
        if terms:
            budget[ename] = {"terms_pct_1sigma_worst_side": terms, "rss_pct": float(math.sqrt(sum(t**2 for t in terms.values()))),
                             "sum_abs_pct": float(sum(terms.values()))}
    for t in table:
        print(t, flush=True)
    print(budget, flush=True)
    save_result("p2/model_form_mw_sensitivity", {"table": table, "budget": budget, "ranges": RANGES}, cfg={
        "model": "4 wheels (CT23 subset), BS113A Timoshenko rail, kf 154e6, eta_f 0.2, kH0 1.4e9", "N": FIT_N,
        "speeds_kmh": SPEEDS, "snr_db": 40, "method": "pseudo-true fit to expected periodograms (large-sample bias)",
        "likelihood": "debiased Whittle", "nominal": NOM, "truth": TRUTH}, seed=31, wall_seconds=wall)


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


def validate_pseudo(args):
    """Pseudo-true biases on the rail-oscillator model vs the Monte Carlo of experiments/p2_model_form.py."""
    from experiments.p2_model_form import CASES, ESTIMATORS as OSC_EST
    sm, thb, rough, _ = setup()
    P, Wm, Ws, g = osc_dataset(sm, thb, rough, {}, (31, 0))
    mc = {(c["case"], c["estimator"]): c for c in json.loads((RESULTS_DIR / "p2" / "model_form.json").read_text())["payload"]["cells"]}
    rows = []
    with Timer() as tm:
        for cname in ("kH0_x0.7", "m_r_x1.3", "axle_damp_x2", "k_r_x0.7", "k_r_x1.3"):
            for ename, names in OSC_EST.items():
                fam = SingleWheelsetFamily(sm, dict(thb, **OSC_NOMINAL), names=names)
                est = MultiPassWhittle(P, Ws, WIM, rough, fam)
                ta = dict(thb, **TRUTH, **OSC_NOMINAL)
                for k, sc in CASES[cname].items():
                    ta[k] = sc if k == "axle_damp_scale" else ta[k] * sc
                st = {**START, **OSC_NOMINAL}
                r = est.pseudo_true(SingleWheelsetFamily(sm, ta, names=()), {}, np.zeros(est.S), np.log(Ws), np.log([st[n] for n in names]))
                m = mc.get((cname, ename), {})
                rows.append({"case": cname, "estimator": ename,
                             "pseudo_true_bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100,
                             "mc_bias_pct": m.get("bias_rel_kB0", float("nan")) * 100,
                             "mc_bias_se_pct": (m.get("bias_rel_kB0_se") or float("nan")) * 100, "mc_n": m.get("n")})
                print(rows[-1], flush=True)
    save_result("p2/pseudo_true_check", {"rows": rows}, cfg={"model": "scenario (a) rail oscillator", "design": "(31, 0), N=50"},
                seed=31, wall_seconds=tm.seconds)


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
    ap.add_argument("--estimators", nargs="+", default=["nominal", "coest"])
    ap.add_argument("--params", nargs="+", default=list(PARAMS))
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--validate-pseudo", action="store_true")
    a = ap.parse_args()
    if a.validate_osc:
        validate_osc(a)
    if a.sensitivity:
        sensitivity(a)
    if a.mc_check:
        mc_check(a)
    if a.summarise:
        summarise_sensitivity()
    if a.validate_pseudo:
        validate_pseudo(a)
