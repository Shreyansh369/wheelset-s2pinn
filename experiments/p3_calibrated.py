"""Simulation-calibrated intervals (stopping rule of 2026-10-13).

From the frozen-estimator headline Monte Carlo (results/p3/headline_v2_runs/kb120_attr.jsonl; 4-wheel
rail-coupled data, 5 seeds x 10 per SNR) we measure, per SNR,
  b = mean error of log k_B0 (bias),  r = sd(error) / median(Wald SE) (SE inflation).
Calibrated interval for log k_B0:  (log k_hat - b) +- 1.645 r SE.
Its coverage on the same 50 fits is in-sample by construction; a leave-one-seed-out version (b and r
from the other four seeds) is reported as the honest check.
Relative change: the level bias cancels in D = log k_later - log k_base, so only the inflation applies:
  D +- 1.645 sqrt((r se_D)^2 + (kappa D)^2), kappa = 0.044. Applied to the 20 kappa-revalidation replicates
(results/p3/kappa_coest_runs, fitted with the earlier +-30-bin estimator and the co-estimating family,
so r from the 40 dB headline is transferred, not measured on them).
MDC under calibration: MDC_cal = r x MDC (one-sided 5% / 90%), from the coest no-drift MDC
(results/p2/relative_coest_drift.json, N = 50, 40 dB) and the CRB-based N = 200 MDC
(results/p2/relative_intervals.json). Writes results/p3/calibrated.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import cp_interval  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

Z = 1.6448536269514722
KAPPA = 0.044


def load_rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]


def calib(R):
    e = np.array([r["err_log"][0] for r in R])
    se = np.array([r["se_log"][0] for r in R])
    b = float(e.mean())
    r = float(np.std(e, ddof=1) / np.median(se))
    return b, r


def coverage(R, b, r):
    k = sum(abs(x["err_log"][0] - b) <= Z * r * x["se_log"][0] for x in R)
    return int(k), len(R)


def main():
    H = load_rows(RESULTS_DIR / "p3" / "headline_v2_runs" / "kb120_attr.jsonl")
    out = {"headline": []}
    cal = {}
    for snr in (20, 40):
        R = [x for x in H if x["snr_db"] == snr]
        b, r = calib(R)
        cal[snr] = (b, r)
        k0, n = coverage(R, 0.0, 1.0)
        k1, _ = coverage(R, b, r)
        loso = 0
        for s in sorted({x["seed"] for x in R}):
            bs, rs = calib([x for x in R if x["seed"] != s])
            loso += coverage([x for x in R if x["seed"] == s], bs, rs)[0]
        out["headline"].append({"snr_db": snr, "n": n, "bias_pct": 100 * (math.exp(b) - 1), "se_inflation": r,
                                "coverage_uncalibrated": k0 / n, "coverage_uncalibrated_ci95": cp_interval(k0, n),
                                "coverage_calibrated_in_sample": k1 / n,
                                "coverage_calibrated_leave_one_seed_out": loso / n, "coverage_loso_ci95": cp_interval(loso, n)})
    b40, r40 = cal[40]
    K = [x for x in load_rows(RESULTS_DIR / "p3" / "kappa_coest_runs" / "rows.jsonl") if x["rep"] < 20]
    kk = {name: sum(abs(x["D_hat"] - x["D_true"]) <= Z * math.sqrt((f * x["se"]) ** 2 + (kap * x["D_hat"]) ** 2) for x in K)
          for name, f, kap in (("raw_kappa0", 1.0, 0.0), ("raw_kappa", 1.0, KAPPA), ("calibrated_kappa0", r40, 0.0), ("calibrated_kappa", r40, KAPPA))}
    out["kappa_replicates"] = {"n": len(K), "se_inflation_used": r40, "kappa": KAPPA,
                               **{k: {"covered": int(v), "coverage": v / len(K), "ci95": cp_interval(int(v), len(K))} for k, v in kk.items()},
                               "note": "inflation transferred from the 40 dB headline (frozen estimator); the replicates were fitted with the "
                                       "earlier +-30-bin kernel and the co-estimating family; nothing tuned on them"}
    rc = json.loads((RESULTS_DIR / "p2" / "relative_coest_drift.json").read_text())["payload"]["drift"]["no_drift_reference"]["coest"]
    ri = json.loads((RESULTS_DIR / "p2" / "relative_intervals.json").read_text())["payload"]["mdc"]
    n200 = {m["snr_db"]: m["mdc_pct_crb"] for m in ri if m["N"] == 200 and m["kappa"] == "no_model_form"}
    out["mdc"] = [{"N": 50, "snr_db": 40, "mdc_pct": rc["mdc_pct"], "se_inflation": r40, "mdc_calibrated_pct": rc["mdc_pct"] * r40,
                   "source": "relative_coest_drift.json coest, no drift"}]
    for snr, v in sorted(n200.items()):
        out["mdc"].append({"N": 200, "snr_db": snr, "mdc_pct": v, "se_inflation": cal[snr][1], "mdc_calibrated_pct": v * cal[snr][1],
                           "source": "relative_intervals.json, CRB-based, no model-form term"})
    save_result("p3/calibrated", out, cfg={"headline": "results/p3/headline_v2_runs/kb120_attr.jsonl", "kappa": KAPPA,
                                           "rule": "subtract mean bias, inflate SE by sd(error)/median(SE), per SNR"}, seed=0)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
