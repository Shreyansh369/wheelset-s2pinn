"""Simulation-calibrated intervals with a split-sample check (stopping rule, 2026-10-13).

Frozen estimator: wide kernel (+-120 bins), default (own-sub-band) scoring, K = 16, no smoothness prior,
fixed load exponent. Headline Monte Carlo: results/p3/headline_v2_runs/kb120_attr.jsonl (4-wheel
rail-coupled data, seeds 42/123/456/789/1024 x 10 datasets per SNR).

Per SNR:
  * need for calibration: the uncalibrated Wald 90% coverage on all 50 fits; an SNR whose coverage is
    >= 0.85 gets no calibration at all (no bias subtraction, no inflation).
  * otherwise: bias b = mean error of log k_B0, inflation r = RMSE / median Wald SE (RMSE about the truth,
    as specified), calibrated interval (log k_hat - b) +- 1.645 r SE.
  * honest check: b and r from seeds {42, 123, 456}, coverage on {789, 1024}; and the reverse split.
  * reported calibration constants for use: b and r from all five seeds.
Relative change (bias cancels in D): D +- 1.645 sqrt((r se_D)^2 + (kappa D)^2), kappa = 0.044, r of the
SNR of the replicates (40 dB). The 20 kappa-revalidation replicates (results/p3/kappa_coest_runs) were
not used for calibration; they were fitted with the earlier +-30-bin kernel and the co-estimating family.
MDC under calibration = r x MDC. Writes results/p3/calibrated.json.
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

# freight rerun (sourced nominals) when complete, else the earlier headline
HEADLINE_RUNS = "kb120_attr_freight.jsonl" if (RESULTS_DIR / "p3/headline_v2_runs/kb120_attr_freight.jsonl").exists() else "kb120_attr.jsonl"

Z = 1.6448536269514722
KAPPA = 0.044
SPLITS = {"A": ((42, 123, 456), (789, 1024)), "B": ((789, 1024), (42, 123, 456))}
THRESH = 0.85


def rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]


def calib(R):
    e = np.array([r["err_log"][0] for r in R])
    se = np.array([r["se_log"][0] for r in R])
    return float(e.mean()), float(np.sqrt(np.mean(e**2)) / np.median(se))


def cover(R, b, r):
    k = int(sum(abs(x["err_log"][0] - b) <= Z * r * x["se_log"][0] for x in R))
    return {"covered": k, "n": len(R), "coverage": k / len(R), "ci95": cp_interval(k, len(R))}


def main():
    H = rows(RESULTS_DIR / "p3" / "headline_v2_runs" / HEADLINE_RUNS)
    out, use = {"headline": []}, {}
    for snr in (20, 40):
        R = [x for x in H if x["snr_db"] == snr]
        raw = cover(R, 0.0, 1.0)
        needed = raw["coverage"] < THRESH
        cell = {"snr_db": snr, "n": len(R), "uncalibrated": raw, "calibration_applied": needed}
        b_all, r_all = calib(R)
        cell["all_seeds"] = {"bias_pct": 100 * (math.exp(b_all) - 1), "inflation_rmse_over_se": r_all}
        for name, (cal, test) in SPLITS.items():
            Rc, Rt = [x for x in R if x["seed"] in cal], [x for x in R if x["seed"] in test]
            b, r = calib(Rc)
            cell[f"split_{name}"] = {"calibrate_on": list(cal), "test_on": list(test), "bias_pct": 100 * (math.exp(b) - 1),
                                     "inflation": r, "test_uncalibrated": cover(Rt, 0.0, 1.0), "test_calibrated": cover(Rt, b, r)}
        use[snr] = (b_all, r_all) if needed else (0.0, 1.0)
        cell["used"] = {"bias_log": use[snr][0], "inflation": use[snr][1]}
        out["headline"].append(cell)
    r40 = use[40][1]
    K = [x for x in rows(RESULTS_DIR / "p3" / "kappa_coest_runs" / "rows.jsonl") if x["rep"] < 20]

    def kcov(f, kap):
        k = int(sum(abs(x["D_hat"] - x["D_true"]) <= Z * math.sqrt((f * x["se"]) ** 2 + (kap * x["D_hat"]) ** 2) for x in K))
        return {"covered": k, "n": len(K), "coverage": k / len(K), "ci95": cp_interval(k, len(K))}
    out["kappa_replicates"] = {"snr_db": 40, "inflation": r40, "kappa": KAPPA, "uncalibrated_stat": kcov(1.0, 0.0),
                               "uncalibrated_kappa": kcov(1.0, KAPPA), "calibrated_stat": kcov(r40, 0.0),
                               "calibrated_kappa": kcov(r40, KAPPA),
                               "note": "replicates not used for calibration; fitted with the earlier +-30-bin kernel and the co-estimating family"}
    mb = RESULTS_DIR / "p4" / "mdc_bounds.json"
    if mb.exists():              # current configuration: co-estimating fit, bound-based
        mdc = [{"N": r["N"], "snr_db": r["snr_db"], "mdc_pct": r["mdc_pct"], "source": "p4/mdc_bounds.json (coest, CRB, current config)"}
               for r in json.loads(mb.read_text())["payload"]["rows"] if r["estimator"] == "coest"]
    else:
        rc = json.loads((RESULTS_DIR / "p2" / "relative_coest_drift.json").read_text())["payload"]["drift"]["no_drift_reference"]["coest"]
        ri = json.loads((RESULTS_DIR / "p2" / "relative_intervals.json").read_text())["payload"]["mdc"]
        mdc = [{"N": 50, "snr_db": 40, "mdc_pct": rc["mdc_pct"], "source": "relative_coest_drift.json (coest, no drift)"}]
        mdc += [{"N": m["N"], "snr_db": m["snr_db"], "mdc_pct": m["mdc_pct_crb"], "source": "relative_intervals.json (CRB, no model-form term)"}
                for m in ri if m["kappa"] == "no_model_form" and not (m["N"] == 50 and m["snr_db"] == 40)]
    for m in mdc:
        m["inflation"] = use[m["snr_db"]][1]
        m["mdc_calibrated_pct"] = m["mdc_pct"] * m["inflation"]
    out["mdc"] = sorted(mdc, key=lambda m: (m["N"], m["snr_db"]))
    save_result("p3/calibrated", out, cfg={"headline": f"results/p3/headline_v2_runs/{HEADLINE_RUNS}", "kappa": KAPPA,
                                           "threshold_for_calibration": THRESH, "splits": {k: [list(a), list(b)] for k, (a, b) in SPLITS.items()},
                                           "inflation": "RMSE about the truth / median Wald SE", "frozen_estimator":
                                           "kernel +-120 bins, own-sub-band scoring, K = 16, no prior, load exponent fixed"}, seed=0)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
