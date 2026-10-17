"""Model-form gain of relative changes at the frozen configuration, empty payload band (gain study).

Pseudo-true (expected-data) fits on two fixed designs of N = 50 passes in the empty band (5.5-7 t, the
band's primary values; keys (41, 0) baseline and (41, 1) later, 60-110 km/h, roughness levels at the
reference): the truth has k_B0 reduced by x = 0, 2, 5, 10 % in the later design and one model parameter
wrong by a fixed factor (cases below, or none for the control); the fit uses the nominal model, either
with k_f, k_H0 fixed ("nominal") or re-estimated in each period ("coest"). For each case the error of the
estimated change D = log k_later - log k_base relative to the true change gives the gain per unit log
error, gamma_p = mean over x of [(b(+) - b(-)) / |D_true|] / (log f+ - log f-), and
kappa = sqrt(sum_p (gamma_p sigma_p)^2) with the 1-sigma log ranges of experiments/p2_model_form_mw.RANGES.
Rows: results/p4/gain_y25_runs/pseudo.jsonl (resumable, 110-minute budget per process; --cases to split);
--summarise -> results/p4/gain_y25.json.
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

from experiments.p1_fe_direct import TRUTH, WIM  # noqa: E402
from experiments.p2_model_form_mw import RANGES  # noqa: E402
from experiments.p2_relative_coest_drift import EST, NOM, pt, setup_all, truth  # noqa: E402
from experiments.p4_banded import set_band  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p4" / "gain_y25_runs"
CASES = {"control": {}, "kf_x0.8": {"kf": 0.8}, "kf_x1.2": {"kf": 1.2}, "eta_f_x0.82": {"eta_f": 0.82}, "eta_f_x1.22": {"eta_f": 1.22},
         "kH0_x0.85": {"kH0": 0.85}, "kH0_x1.15": {"kH0": 1.15}, "unsprung_x0.95": {"unsprung_scale": 0.95},
         "unsprung_x1.05": {"unsprung_scale": 1.05}, "axle_damp_x0.5": {"axle_damp_scale": 0.5}, "axle_damp_x2": {"axle_damp_scale": 2.0}}
PAIRS = {"kf": ("kf_x0.8", "kf_x1.2"), "eta_f": ("eta_f_x0.82", "eta_f_x1.22"), "kH0": ("kH0_x0.85", "kH0_x1.15"),
         "unsprung_scale": ("unsprung_x0.95", "unsprung_x1.05"), "axle_damp_scale": ("axle_damp_x0.5", "axle_damp_x2")}
XS = (0.0, 0.02, 0.05, 0.10)
T0, BUDGET = time.perf_counter(), 110 * 60


def run(cases, estimators):
    set_band("empty")
    sm, thb, rough, mw, fams, designs = setup_all()
    fp = OUT / "pseudo.jsonl"
    done = {(json.loads(l)["case"], json.loads(l)["estimator"], json.loads(l)["x"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    tmax = 20 * 60
    for e in estimators:
        ests = {k: MultiPassWhittle(P, Ws, WIM, rough, fams[e], debias=True) for k, (P, Wm, Ws, g) in designs.items()}
        for c in cases:
            for x in XS:
                if (c, e, x) in done:
                    continue
                if time.perf_counter() - T0 + tmax > BUDGET:
                    print("deadline", flush=True)
                    return
                t0 = time.perf_counter()
                kt = TRUTH["kB0"] * (1 - x)
                lk, ok = pt(ests["base" if x == 0 else "later"], mw, truth(thb, CASES[c], kt), EST[e])
                OUT.mkdir(parents=True, exist_ok=True)
                row = {"case": c, "estimator": e, "x": x, "log_k_hat": lk, "converged": ok, "wall_s": time.perf_counter() - t0}
                with fp.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(row, flush=True)
                tmax = max(tmax, 1.3 * row["wall_s"])


def summarise():
    R = {(r["case"], r["estimator"], r["x"]): r for r in (json.loads(l) for l in (OUT / "pseudo.jsonl").read_text().splitlines() if l.strip())}
    out = {"design": "empty band 5.5-7 t, N = 50, 60-110 km/h, keys (41, 0)/(41, 1), pseudo-true", "estimators": {}}
    for e in EST:
        tab, bias = [], {}
        for c in CASES:
            if (c, e, 0.0) not in R:
                continue
            lb = R[(c, e, 0.0)]["log_k_hat"]
            for x in XS[1:]:
                if (c, e, x) not in R:
                    continue
                d, dt = R[(c, e, x)]["log_k_hat"] - lb, math.log(1 - x)
                bias[(c, x)] = (d - dt) / abs(dt)
                tab.append({"case": c, "x": x, "rel_change_true_pct": -100 * x, "rel_change_hat_pct": 100 * (math.exp(d) - 1),
                            "rel_change_bias_pp": 100 * (math.exp(d) - 1) + 100 * x,
                            "abs_bias_base_pct": 100 * (math.exp(lb - math.log(TRUTH["kB0"])) - 1)})
        gam, terms = {}, {}
        for p, (lo, hi) in PAIRS.items():
            fl, fh = CASES[lo][p], CASES[hi][p]
            g = [(bias[(hi, x)] - bias[(lo, x)]) / (math.log(fh) - math.log(fl)) for x in XS[1:] if (hi, x) in bias and (lo, x) in bias]
            if g:
                gam[p] = {"gamma_per_log": float(np.mean(g)), "gamma_by_x": [float(v) for v in g]}
                terms[p] = abs(gam[p]["gamma_per_log"]) * RANGES[p][0]
        out["estimators"][e] = {"pseudo_true": tab, "gains": gam, "kappa_terms": terms,
                                "kappa": float(math.sqrt(sum(v**2 for v in terms.values()))) if len(terms) == len(PAIRS) else None,
                                "control_rel_error": [bias[("control", x)] for x in XS[1:] if ("control", x) in bias]}
    save_result("p4/gain_y25", out, cfg={"cases": CASES, "ranges_sigma_log": {p: RANGES[p][0] for p in RANGES}, "x": XS, "nominal": NOM}, seed=41)
    print(json.dumps({e: {"kappa": v["kappa"], "terms": v["kappa_terms"]} for e, v in out["estimators"].items()}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--cases", nargs="+", default=list(CASES))
    ap.add_argument("--estimators", nargs="+", default=list(EST))
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()
    if a.run:
        run(a.cases, a.estimators)
    if a.summarise:
        summarise()
