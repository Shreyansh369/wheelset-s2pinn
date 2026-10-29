"""Preregistration v2 §4: statistics of the simultaneous-error and zero-change studies, with their uncertainty.

Reads results/p5/runs/simerr<tag>.jsonl and zero<tag>.jsonl (rows of experiments/p5_v2.py) and the nominal
banded MDC (results/p4/banded.json, or --banded for a re-frozen configuration). For each estimator (xpr-1, the
primary; the frozen estimator on the same data, secondary):
  coverage of the Wald 90% interval (Clopper-Pearson 95%; also with singular replicates counted as misses),
  F90 = 90th percentile of |D - D_true| / (1.645 se), false-alarm rate (D < -1.645 se, Clopper-Pearson),
  s0 = max(1, sd z_zero), g90 = 90th percentile of (D_true - D)/D_true, MDC_cons = MDC_nom s0 / (1 - g90)
  for N = 50, 200 in each band at 40 dB, and P_det = mean Phi(2.927 (1 - e_j)/(1 - g90) - 1.645).
Uncertainty: B = 2000 bootstrap resamples (zero-change and simultaneous-error replicates drawn independently,
seed 4747), 95% percentile intervals; Clopper-Pearson for proportions. Writes results/p5/v2_summary<tag>.json.

    python3 experiments/p5_summary.py --tag _massd
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import cp_interval  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

Z = 1.6448536269514722
B, SEED = 2000, 4747


def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def _q90(v):
    return float(np.percentile(v, 90)) if len(v) else float("nan")


def stats(S, Zr, mdc_nom, est):
    """All §4 statistics for one estimator: est = "xpr" (D_hat, se) or "frozen" (D_hat_frozen, se_frozen)."""
    dk, sk = ("D_hat", "se") if est == "xpr" else ("D_hat_frozen", "se_frozen")
    d, se, dt = (np.array([r[k] for r in S], float) for k in (dk, sk, "D_true"))
    sing = np.array([any(p["singular"] if est == "xpr" else p["se_std_source"] == "cb_fixed" for p in r["periods"].values())
                     for r in S], bool)
    cov = np.abs(d - dt) <= Z * se
    ratio = np.abs(d - dt) / (Z * se)
    e = (dt - d) / dt                      # positive when the change is underestimated (dt < 0 for a loss)
    dz, sz = (np.array([r[k] for r in Zr], float) for k in (dk, sk))
    z = dz / sz
    fa = dz < -Z * sz
    s0 = max(1.0, float(np.std(z, ddof=1))) if len(z) > 1 else float("nan")
    g90 = _q90(e)
    fac = s0 / (1 - g90)
    pdet = float(np.mean(norm.cdf(2.927 * (1 - e) / (1 - g90) - Z)))
    out = {"n_simerr": len(S), "n_zero": len(Zr), "n_singular_simerr": int(sing.sum()),
           "n_singular_zero": int(sum(any(p["singular"] if est == "xpr" else p["se_std_source"] == "cb_fixed"
                                          for p in r["periods"].values()) for r in Zr)),
           "coverage": float(cov.mean()), "coverage_cp95": cp_interval(int(cov.sum()), len(S)),
           "coverage_singular_as_miss": float((cov & ~sing).mean()),
           "coverage_singular_as_miss_cp95": cp_interval(int((cov & ~sing).sum()), len(S)),
           "F90": _q90(ratio), "false_alarms": int(fa.sum()), "false_alarm_rate": float(fa.mean()) if len(fa) else None,
           "false_alarm_cp95": cp_interval(int(fa.sum()), len(fa)) if len(fa) else None,
           "z_sd": float(np.std(z, ddof=1)) if len(z) > 1 else None, "z_mean": float(np.mean(z)) if len(z) else None,
           "s0": s0, "g90": g90, "mdc_factor": fac, "P_det": pdet,
           "mdc_cons_pct": {k: v * fac for k, v in mdc_nom.items()}}
    # bootstrap over replicates (independent resamples of the two studies)
    rng = np.random.default_rng(SEED)
    bt = {k: [] for k in ("coverage", "F90", "s0", "g90", "mdc_factor", "P_det", "false_alarm_rate")}
    for _ in range(B):
        i = rng.integers(0, len(S), len(S))
        k = rng.integers(0, len(Zr), len(Zr)) if len(Zr) else np.array([], int)
        g = _q90(e[i])
        s = max(1.0, float(np.std(z[k], ddof=1))) if len(k) > 1 else float("nan")
        bt["coverage"].append(cov[i].mean())
        bt["F90"].append(_q90(ratio[i]))
        bt["s0"].append(s)
        bt["g90"].append(g)
        bt["mdc_factor"].append(s / (1 - g))
        bt["P_det"].append(float(np.mean(norm.cdf(2.927 * (1 - e[i]) / (1 - g) - Z))))
        bt["false_alarm_rate"].append(fa[k].mean() if len(k) else float("nan"))
    ci = {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in bt.items()}
    out["bootstrap95"] = ci
    out["mdc_cons_pct_bootstrap95"] = {k: [v * ci["mdc_factor"][0], v * ci["mdc_factor"][1]] for k, v in mdc_nom.items()}
    out["validated_90pct_detection"] = bool(ci["P_det"][0] >= 0.90)
    out["coverage_below_90"] = bool(out["coverage_cp95"][1] < 0.90)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--banded", default="p4/banded.json", help="nominal MDC source (results/<path>)")
    a = ap.parse_args()
    S = sorted(_rows(RESULTS_DIR / "p5" / "runs" / f"simerr{a.tag}.jsonl"), key=lambda r: r["rep"])
    Zr = sorted(_rows(RESULTS_DIR / "p5" / "runs" / f"zero{a.tag}.jsonl"), key=lambda r: r["rep"])
    bd = json.loads((RESULTS_DIR / a.banded).read_text())["payload"]["bounds"]
    mdc_nom = {f"{b['band']}_N{b['N']}": b["mdc_pct"] for b in bd if b["snr_db"] == 40.0}
    failed = _rows(RESULTS_DIR / "p5" / "failed_fits.jsonl")
    payload = {"preregistration": "docs/preregistration_v2.md", "tag": a.tag, "mdc_nominal_pct_40dB": mdc_nom,
               "mdc_nominal_source": f"results/{a.banded}",
               "contiguous_simerr": [r["rep"] for r in S] == list(range(len(S))),
               "contiguous_zero": [r["rep"] for r in Zr] == list(range(len(Zr))),
               "n_failed_fits": sum(1 for f in failed if f["study"] in (f"simerr{a.tag}", f"zero{a.tag}")),
               "failed_fit_log": "results/p5/failed_fits.jsonl",
               "n_restart_kept": {k: sum(p["kept"] == "xpr" for r in R for p in r["periods"].values())
                                  for k, R in (("simerr", S), ("zero", Zr))},
               "xpr": stats(S, Zr, mdc_nom, "xpr"), "frozen": stats(S, Zr, mdc_nom, "frozen")}
    save_result(f"p5/v2_summary{a.tag}", payload, cfg={"bootstrap": {"B": B, "seed": SEED}, "z": Z}, seed=SEED)
    print(json.dumps({k: payload["xpr"][k] for k in ("n_simerr", "n_zero", "coverage", "F90", "s0", "g90", "mdc_factor", "P_det")}, indent=1))


if __name__ == "__main__":
    main()
