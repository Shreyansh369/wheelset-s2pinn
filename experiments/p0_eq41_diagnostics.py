"""Exploratory breakdown of results/p0/eq41.json (not part of the pre-registered gate).

Bins transient records by how well the PINN output is described by one damped
sinusoid (fit_rel_err), since Eq. (41)'s derivation assumes it is. Also fits the
measured relation per bin. Writes results/p0/eq41_diagnostics.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.results import load_result, save_result  # noqa: E402

BINS = [(0.0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 10.0)]


def fit_relation(recs):
    y = np.array([r["lambda_meas"] ** 2 - r["lambda0"] ** 2 for r in recs])
    x = np.array([r["R_floor"] / (2 * r["omega"]) for r in recs])
    ok = (y > 0) & (x > 0)
    if ok.sum() < 3:
        return None
    A = np.stack([np.ones(ok.sum()), np.log(x[ok])], 1)
    coef, *_ = np.linalg.lstsq(A, np.log(y[ok]), rcond=None)
    # coefficient with beta fixed at 2 (Eq. 41's form)
    c2 = float(np.exp(np.median(np.log(y[ok]) - 2 * np.log(x[ok]))))
    return {"c": float(np.exp(coef[0])), "beta": float(coef[1]), "c_if_beta_2_median": c2, "n": int(ok.sum())}


def main() -> None:
    pay = load_result("p0/eq41")["payload"]
    out = {}
    for key in ("transient/sdof", "transient/2dof"):
        recs = pay[key]["records"]
        rows = {}
        for lo, hi in BINS:
            sel = [r for r in recs if lo <= r["fit_rel_err"] < hi]
            if not sel:
                continue
            e = np.array([abs(r["lambda_meas"] - r["lambda_pred_eq41"]) / r["lambda_meas"] for r in sel])
            bias = np.array([(r["lambda_meas"] - r["lambda0"]) / r["lambda0"] for r in sel])
            dl_meas = np.array([r["lambda_meas"] - r["lambda0"] for r in sel])
            dl_pred = np.array([r["lambda_pred_eq41"] - r["lambda0"] for r in sel])
            rows[f"fit_rel_err in [{lo},{hi})"] = {
                "n": len(sel), "median_rel_err_eq41": float(np.median(e)), "frac_within_10pct": float(np.mean(e <= 0.1)),
                "median_bias_over_lambda0": float(np.median(bias)),
                "median_ratio_excess_meas_over_pred": float(np.median(dl_meas / np.where(dl_pred > 0, dl_pred, np.nan)))
                if np.any(dl_pred > 0) else None,
                "relation": fit_relation(sel),
            }
        out[key] = rows
        # by capacity
        caps = sorted({(r["width"], r["steps"]) for r in recs})
        out[key + "/by_capacity"] = {
            f"w{w}_s{s}": {
                "n": len([r for r in recs if (r["width"], r["steps"]) == (w, s)]),
                "median_rel_err_eq41": float(np.median([abs(r["lambda_meas"] - r["lambda_pred_eq41"]) / r["lambda_meas"]
                                                        for r in recs if (r["width"], r["steps"]) == (w, s)])),
                "median_fit_rel_err": float(np.median([r["fit_rel_err"] for r in recs if (r["width"], r["steps"]) == (w, s)])),
                "median_bias_over_lambda0": float(np.median([(r["lambda_meas"] - r["lambda0"]) / r["lambda0"]
                                                             for r in recs if (r["width"], r["steps"]) == (w, s)])),
            }
            for (w, s) in caps
        }
    save_result("p0/eq41_diagnostics", out)
    import json

    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
