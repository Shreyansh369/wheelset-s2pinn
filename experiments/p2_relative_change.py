"""Trend monitoring: is the relative change of kB0 robust to model-form error that biases absolute kB0?

Rail-coupled model (instrumented FE wheelset + 3 neighbours, CT23 4-wheel subset, BS113A Timoshenko rail,
kf 154 MN/m^2, eta_f 0.2), debiased Whittle likelihood, nominal estimator (kB0, cB) with nominal
values of every other parameter. The truth differs from the fitted model by one misspecification
(the same for the baseline and the later set): unsprung mass x0.95 / x1.05, contact stiffness
x0.85 / x1.15, axle damping x0.5 / x2, foundation stiffness x0.8 / x1.2 (plus a control).
Baseline: true kB0 = 0.85e9. Later set: true kB0 reduced by 2%, 5%, 10% (bearing degradation).
Baseline and later sets are different designs (passes at other speeds and payloads, other roughness).

--pseudo: large-sample limits by pseudo-true fits (expected periodograms, no noise); relative-change
          estimate D_hat = log k_later - log k_base vs the truth log(1 - x); analytic Wald coverage
          Phi(1.645 - b / s) - Phi(-1.645 - b / s), s = sqrt(CRB_base^2 + CRB_later^2).
--mc:     Monte Carlo check (6 replicates) for control, unsprung x1.05 and kf x1.2 at x = 5%.
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
from scipy.stats import norm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import START, TRUTH, WIM, Z90, cp_interval, setup  # noqa: E402
from experiments.p2_model_form_mw import NOM  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

CASES = {"control": {}, "unsprung_x0.95": {"unsprung_scale": 0.95}, "unsprung_x1.05": {"unsprung_scale": 1.05},
         "kH0_x0.85": {"kH0": 0.85}, "kH0_x1.15": {"kH0": 1.15}, "axle_damp_x0.5": {"axle_damp_scale": 0.5},
         "axle_damp_x2": {"axle_damp_scale": 2.0}, "kf_x0.8": {"kf": 0.8}, "kf_x1.2": {"kf": 1.2},
         "eta_f_x0.82": {"eta_f": 0.82}, "eta_f_x1.22": {"eta_f": 1.22}}
REDUCTIONS = (0.02, 0.05, 0.10)
RUN_DIR = RESULTS_DIR / "p2" / "relative_change_runs"
N, SPEEDS = 50, (60.0, 110.0)


def gen(sm, th_true, rough, mw, seed_key, g_sd=None):
    """As experiments/p2_multiwheel.dataset but with the full truth (incl. kB0) taken from th_true."""
    from experiments.p1_fe_direct import G_SD_DB, W_RANGE
    from experiments.p2_multiwheel import FG, KMH
    from src.inverse.multipass import generate_pass
    rng = np.random.default_rng(np.random.SeedSequence(seed_key))
    g = 10 ** (rng.normal(0, G_SD_DB if g_sd is None else g_sd, rough.n_sub) / 10)
    Vs = rng.uniform(*SPEEDS, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    passes = [generate_pass(mw.reference_H(dict(th_true, W=float(W)), V, FG), rough, g, V, th_true["r0"], 40.0, rng)
              for V, W in zip(Vs, Ws)]
    return passes, Ws * np.exp(WIM * rng.standard_normal(N)), Ws, g


def truth(thb, case, kB0):
    t = dict(thb, **TRUTH, **NOM)
    for k, f in case.items():
        t[k] = NOM[k] * f
    t["kB0"] = kB0
    return t


def fam_fit(mw, thb):
    return MultiWheelFamily(mw, dict(thb, **NOM), names=("kB0", "cB"))


def pseudo(case_names):
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    ff = fam_fit(mw, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    designs = {"base": mw_dataset(sm, thb, rough, mw, (41, 0), N=N, speeds=SPEEDS, g_sd=0.0),
               "later": mw_dataset(sm, thb, rough, mw, (41, 1), N=N, speeds=SPEEDS, g_sd=0.0)}
    ests = {k: MultiPassWhittle(P, Ws, WIM, rough, ff, debias=True) for k, (P, Wm, Ws, g) in designs.items()}
    phi0 = np.log([START["kB0"], START["cB"]])
    for cname in case_names:
        fp = RUN_DIR / f"pseudo_{cname}.jsonl"
        done = {(json.loads(l)["set"], json.loads(l)["x"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        for setname, x in [("base", 0.0)] + [("later", x) for x in REDUCTIONS]:
            if (setname, x) in done:
                continue
            est = ests[setname]
            kt = TRUTH["kB0"] * (1 - x)
            ft = MultiWheelFamily(mw, truth(thb, CASES[cname], kt), names=())
            r = est.pseudo_true(ft, {}, np.zeros(est.S), est.lw_meas.copy(), phi0)
            crb = est.expected_fisher(np.log([kt, TRUTH["cB"]]), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
            row = {"case": cname, "set": setname, "x": x, "kB0_true": kt, "log_k_hat": r["phi"][0],
                   "abs_bias_pct": (math.exp(r["phi"][0] - math.log(kt)) - 1) * 100, "crb_log": crb, "converged": r["converged"]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, flush=True)


def mc(n_rep, case_names, x=0.05):
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    ff = fam_fit(mw, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    phi0 = np.log([START["kB0"], START["cB"]])
    for cname in case_names:
        fp = RUN_DIR / f"mc_{cname}_x{x}.jsonl"
        done = {json.loads(l)["rep"] for l in fp.read_text().splitlines()} if fp.exists() else set()
        for j in range(n_rep):
            if j in done:
                continue
            out = {}
            for setname, kt, sk in (("base", TRUTH["kB0"], (42, j, 0)), ("later", TRUTH["kB0"] * (1 - x), (42, j, 1))):
                P, Wm, Ws, g = gen(sm, truth(thb, CASES[cname], kt), rough, mw, sk)
                est = MultiPassWhittle(P, Wm, WIM, rough, ff, debias=True)
                r = est.fit(phi0)
                out[setname] = (r["phi"][0], r["se_log"][0], kt, r["converged"])
            d_hat = out["later"][0] - out["base"][0]
            se = math.hypot(out["base"][1], out["later"][1])
            row = {"case": cname, "x": x, "rep": j, "D_hat": d_hat, "D_true": math.log(1 - x), "se": se,
                   "abs_err_base": out["base"][0] - math.log(TRUTH["kB0"]), "converged": out["base"][3] and out["later"][3]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(row, flush=True)


def summarise():
    rows = [json.loads(l) for fp in sorted(RUN_DIR.glob("pseudo_*.jsonl")) for l in fp.read_text().splitlines() if l.strip()]
    table = []
    for cname in CASES:
        R = [r for r in rows if r["case"] == cname]
        base = [r for r in R if r["set"] == "base"]
        if not base:
            continue
        b = base[0]
        for x in REDUCTIONS:
            L = [r for r in R if r["set"] == "later" and r["x"] == x]
            if not L:
                continue
            l_ = L[0]
            d_hat = l_["log_k_hat"] - b["log_k_hat"]
            d_true = math.log(1 - x)
            s = math.hypot(b["crb_log"], l_["crb_log"])
            bias = d_hat - d_true
            cov = float(norm.cdf(1.645 - bias / s) - norm.cdf(-1.645 - bias / s))
            table.append({"case": cname, "x": x, "abs_bias_base_pct": b["abs_bias_pct"], "abs_bias_later_pct": l_["abs_bias_pct"],
                          "rel_change_true_pct": -x * 100, "rel_change_hat_pct": (math.exp(d_hat) - 1) * 100,
                          "rel_change_bias_pp": ((math.exp(d_hat) - 1) - (-x)) * 100, "sd_rel_change_pp": s * 100,
                          "bias_over_sd": bias / s, "predicted_coverage90": cov})
    mcrows = [json.loads(l) for fp in sorted(RUN_DIR.glob("mc_*.jsonl")) for l in fp.read_text().splitlines() if l.strip()]
    mcs = []
    for cname in CASES:
        R = [r for r in mcrows if r["case"] == cname]
        if not R:
            continue
        e = np.array([r["D_hat"] - r["D_true"] for r in R])
        se = np.array([r["se"] for r in R])
        k = int(np.sum(np.abs(e) <= Z90 * se))
        mcs.append({"case": cname, "x": R[0]["x"], "n": len(R), "rel_change_bias_pp": float(np.mean(e) * 100),
                    "rel_change_bias_se_pp": float(np.std(e, ddof=1) / math.sqrt(len(e)) * 100) if len(e) > 1 else None,
                    "abs_bias_base_pct": float(np.mean([math.exp(r["abs_err_base"]) - 1 for r in R]) * 100),
                    "coverage90": k / len(R), "coverage90_ci95": cp_interval(k, len(R))})
    for t in table:
        print(t)
    for m in mcs:
        print(m)
    save_result("p2/relative_change", {"pseudo_true": table, "mc_check": mcs}, cfg={
        "model": "4-wheel rail-coupled (CT23 subset), debiased Whittle, nominal estimator (kB0, cB)", "N": N,
        "speeds_kmh": SPEEDS, "snr_db": 40, "cases": CASES, "reductions": REDUCTIONS,
        "coverage": "predicted from pseudo-true bias and CRB (Wald, asymptotically normal); Monte Carlo check for 3 cases"},
        seed=41)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pseudo", action="store_true")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--cases", nargs="+", default=list(CASES))
    ap.add_argument("--n-rep", type=int, default=6)
    a = ap.parse_args()
    if a.pseudo:
        pseudo(a.cases)
    if a.mc:
        mc(a.n_rep, a.cases)
    if a.summarise:
        summarise()
