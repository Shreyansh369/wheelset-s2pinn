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
def _nominal():
    """Nominal foundation and contact from config/track.yaml (the representative freight case)."""
    from src.reference.track import load_track_config
    c = load_track_config()
    t = c[c["nominal"]["track"]]
    return {"kf": float(t["kf"]), "eta_f": float(t["eta_f"]), "kH0": float(c["contact_freight"]["kH0"]),
            "unsprung_scale": 1.0, "axle_damp_scale": 1.0}


NOM = _nominal()
RUN_LABEL = "_freight"   # run-file suffix for the sourced-nominal round (2026-10-15)
T_START, DEADLINE_S, FIT_MAX = __import__("time").perf_counter(), 110 * 60, [45 * 60]
ESTIMATORS = {"nominal": ("kB0", "cB"), "coest": ("kB0", "cB", "kf", "kH0"), "coest_eta": ("kB0", "cB", "kf", "kH0", "eta_f")}
# realistic 1-sigma uncertainty (log scale) and where it comes from
# 1-sigma uncertainty (log scale): the sourced range is taken as about +-2 sigma (sigma = ln(hi/lo)/4);
# sources in config/params.yaml, config/track.yaml and docs/parameter_sources.md
RANGES = {
    "kf": (math.log(1333.0 / 123.0) / 4, "rail pad swept 80-800 MN/m per pad (published 105-800: Knuth et al. 2025; Thompson et al., Southampton eprint 436918) at 0.60-0.65 m spacing (Sanudo et al. 2022; Thompson et al.) -> 123-1333 MN/m^2"),
    "eta_f": (math.log(0.25 / 0.10) / 4, "rail pad loss factor 0.1-0.25 (Jones & Edwards 1996: 0.1-0.3; Knuth et al. 2025: 0.15; Thompson et al., eprint 436918: 0.2/0.25)"),
    "kH0": (math.log(2.3 / 1.388) / 4, "linearised contact stiffness 1.388 GN/m (Hertz, S1002 transverse radius +0.5 m) to 2.3 GN/m (upper end kept from an earlier, unverified literature range)"),
    "unsprung_scale": (0.04, "about 20 kg per axlebox, around 4% of the wheelset unsprung weight, between axlebox designs (SKF Evolution, New axlebox concept for heavy loads, 8 Dec 2005)"),
    "axle_damp_scale": (math.log(0.02 / 0.001) / 4, "wheelset modal damping 0.1-2% (Chaar 2007: measured less than 2%; Jin 2016 via Ahmedov & Mirsaidov 2023: 0.1-1%)"),
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
    out = RESULTS_DIR / "p2" / f"model_form_mw_runs{RUN_LABEL}"
    out.mkdir(parents=True, exist_ok=True)
    import time
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
                facs = args.factors or ((0.9, 1.1, math.exp(-sig), math.exp(sig)) if ename == "nominal" else (math.exp(-sig), math.exp(sig)))
                for f in facs:
                    if round(f, 6) in {round(x, 6) for x in done}:
                        continue
                    if time.perf_counter() - T_START + FIT_MAX[0] > DEADLINE_S:
                        print("deadline", flush=True)
                        return
                    true_all = dict(thb, **TRUTH, **NOM)
                    true_all[pname] = NOM[pname] * f
                    r = est.pseudo_true(MultiWheelFamily(mw, true_all, names=()), {}, np.zeros(est.S), np.log(Ws), phi0)
                    row = {"estimator": ename, "param": pname, "factor": f, "bias_pct": (math.exp(r["phi"][0] - math.log(TRUTH["kB0"])) - 1) * 100,
                           "phi_hat": r["phi"], "converged": r["converged"], "wall_fit_s": r["wall_fit_s"]}
                    with fp.open("a") as fh:
                        fh.write(json.dumps(row) + "\n")
                    print(row, flush=True)
                    FIT_MAX[0] = max(FIT_MAX[0], 1.3 * r["wall_fit_s"])
    summarise_sensitivity(tm.seconds)


def summarise_sensitivity(wall=None):
    out = RESULTS_DIR / "p2" / f"model_form_mw_runs{RUN_LABEL}"
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
        "model": "4 wheels (freight wagon layout), nominal track of config/track.yaml (60E1, ballasted)", "N": FIT_N,
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
    ap.add_argument("--factors", type=float, nargs="+", default=None, help="override the perturbation factors")
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
