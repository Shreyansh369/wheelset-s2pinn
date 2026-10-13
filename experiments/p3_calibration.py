"""Calibration slope of the relative change with the correct model (no misspecification).

Pseudo-true (large-sample) fits of the co-estimating estimator (k_B0, c_B, k_f, k_H0 per period) on the
relative-change designs of experiments/p2_relative_coest_drift.py: baseline k_B0 = truth, later
k_B0 x (1 - x) for x = 2, 5, 10%. The baseline and x = 5% fits are the "control" rows of
results/p2/relative_change_runs/coest_pseudo.jsonl (same design, same estimator); x = 2% and 10% are new.
Slope = least-squares slope of D_hat on D_true through the origin. Writes results/p3/calibration.json.
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

from experiments.p1_fe_direct import TRUTH, WIM  # noqa: E402
from experiments.p2_relative_change import truth  # noqa: E402
from experiments.p2_relative_coest_drift import EST, pt, setup_all  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

FP = RESULTS_DIR / "p3" / "calibration_runs.jsonl"
XS = (0.02, 0.05, 0.10)


def rows():
    out = [json.loads(l) for l in FP.read_text().splitlines()] if FP.exists() else []
    for l in (RESULTS_DIR / "p2" / "relative_change_runs" / "coest_pseudo.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r["case"] == "control":
            out.append({"x": r["x"], "log_k_hat": r["log_k_hat"], "converged": r["converged"], "source": "coest_pseudo.jsonl control"})
    return out


def run(xs):
    sm, thb, rough, mw, fams, designs = setup_all()
    have = {round(r["x"], 6) for r in rows()}
    for x in xs:
        if round(x, 6) in have:
            continue
        P, Wm, Ws, g = designs["later"]
        est = MultiPassWhittle(P, Ws, WIM, rough, fams["coest"], debias=True)
        lk, ok = pt(est, mw, truth(thb, {}, TRUTH["kB0"] * (1 - x)), EST["coest"])
        FP.parent.mkdir(parents=True, exist_ok=True)
        with FP.open("a") as fh:
            fh.write(json.dumps({"x": x, "log_k_hat": lk, "converged": ok, "source": "p3_calibration"}) + "\n")
        print(x, lk, ok, flush=True)


def summarise():
    R = {round(r["x"], 6): r for r in rows()}
    base = R[0.0]["log_k_hat"]
    pts = [{"x": x, "D_true": math.log(1 - x), "D_hat": R[round(x, 6)]["log_k_hat"] - base,
            "true_change_pct": -100 * x, "est_change_pct": 100 * (math.exp(R[round(x, 6)]["log_k_hat"] - base) - 1)}
           for x in XS if round(x, 6) in R]
    dt, dh = np.array([p["D_true"] for p in pts]), np.array([p["D_hat"] for p in pts])
    slope = float(dh @ dt / (dt @ dt))
    out = {"coest": {"points": pts, "slope": slope, "base_abs_err_log": base - math.log(TRUTH["kB0"]),
                     "all_converged": all(r["converged"] for r in R.values())}}
    save_result("p3/calibration", out, cfg={"estimator": "coest (kB0, cB, kf, kH0)", "fit": "pseudo-true, correct model",
                                           "design": "p2_relative_coest_drift designs (41, 0)/(41, 1), N = 50"}, seed=41)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()
    if a.run:
        run(XS)
    if a.summarise:
        summarise()
