"""Gate reports: read results/ JSON only and print pass/fail against the brief's thresholds.

Usage: python experiments/gate_report.py G0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

PAPER_DIFFUSION_MEAN = 3.71e-3


def _load(name: str):
    p = RESULTS_DIR / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def g0() -> dict:
    items: dict = {}

    # (a) S2-PINN diffusion reproduction within 2x of the paper's mean error
    rep = _load("p0/s2pinn_repro_seed42")
    if rep is None:
        timing = _load("p0/s2pinn_cpu_timing")
        items["a_s2pinn_reproduction"] = {
            "status": "PENDING",
            "why": "needs a GPU run (experiments/colab_p0_reproduce.ipynb); CPU estimate "
                   + (f"{timing['payload']['projected_hours_20k_steps']:.1f} h" if timing else "n/a"),
            "threshold": 2 * PAPER_DIFFUSION_MEAN,
        }
    else:
        p = rep["payload"]
        items["a_s2pinn_reproduction"] = {
            "status": "PASS" if p["g0_pass"] else "FAIL",
            "mean_rel_l2": p["final_metrics"]["uq/mean_rel_l2"], "threshold": 2 * PAPER_DIFFUSION_MEAN,
            "ratio_to_paper": p["ratio_to_paper"], "device": p["device"], "full_budget": p["full_paper_budget"],
            "wall_minutes": rep["provenance"]["wall_seconds"] / 60, "peak_gpu_mb": rep["provenance"]["peak_gpu_memory_mb"],
        }

    # (b) SDOF H1 trend
    h1 = _load("p0/h1_sdof")
    h1s = _load("p0/h1_sdof_summary")
    if h1:
        f = h1["payload"]["fits_log_p_vs_log_Pi"]
        leg, her = f["legendre/p_req_at_mean/p>=3"], f["hermite/p_req_at_mean/p>=3"]
        clear = leg["r2"] >= 0.95 and her["r2"] >= 0.95 and leg["slope"] > 0 and her["slope"] > 0
        items["b_h1_sdof_trend"] = {
            "status": "PASS (trend clear)" if clear else "FAIL",
            "criterion": "monotone log-log trend of required degree in Pi with R^2 >= 0.95 for both families",
            "legendre_slope_vs_logPi": [leg["slope"], leg["slope_se"]], "legendre_r2": leg["r2"],
            "hermite_slope_vs_logPi": [her["slope"], her["slope_se"]], "hermite_r2": her["r2"],
            "hermite_local_slopes": h1s["payload"]["hermite"]["local_slope_by_Pi_bin"] if h1s else None,
            "legendre_p_over_Pi": h1s["payload"]["legendre"]["p_over_Pi_by_Pi_bin"] if h1s else None,
            "hypothesis_Pi2_holds": "only asymptotically for Hermite; Legendre scales like Pi",
        }
    else:
        items["b_h1_sdof_trend"] = {"status": "PENDING"}

    # (c) Eq. (41) within 10% or measured relation reported
    e41 = _load("p0/eq41")
    if e41:
        pay = e41["payload"]
        rows = {}
        for k in ("transient/sdof", "transient/2dof", "forced/sdof", "forced/2dof"):
            v = pay.get(k, {})
            rows[k] = {kk: v.get(kk) for kk in ("n", "median_rel_err_eq41", "frac_within_10pct_eq41", "n_informative",
                                                 "median_rel_err_eq41_informative", "median_measured_bias_over_lambda0",
                                                 "pass_eq41_10pct_median", "measured_relation",
                                                 "median_rel_err_lambda_pred_window", "median_rel_err_lambda_pred_ridge",
                                                 "pointwise_ridge_amplitude")}
        all_pass = all(r["pass_eq41_10pct_median"] for r in rows.values() if r["n"])
        items["c_eq41"] = {
            "status": "PASS (Eq. 41 within 10%)" if all_pass else "Eq. 41 FAILS; measured relation reported",
            "settings": rows, "mlp_forced_trap": pay.get("forced/sdof_mlp_at_resonance"),
        }
    else:
        items["c_eq41"] = {"status": "PENDING"}

    # (d) literature stop rule
    lit = Path(__file__).resolve().parents[1] / "docs" / "lit_review.md"
    items["d_literature_stop_rule"] = {
        "status": "NOT TRIGGERED" if lit.exists() and "stop rule is not triggered" in " ".join(lit.read_text().replace("*", "").split()).lower() else "PENDING",
        "source": "docs/lit_review.md",
    }
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate", choices=["G0"])
    args = ap.parse_args()
    items = g0()
    save_result("gates/G0", items)
    for k, v in items.items():
        print(f"{k:28s} {v['status']}")
        for kk, vv in v.items():
            if kk != "status":
                print(f"    {kk}: {json.dumps(vv, default=str)[:300]}")


if __name__ == "__main__":
    main()
