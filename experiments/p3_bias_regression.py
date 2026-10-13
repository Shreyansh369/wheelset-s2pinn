"""Does the k_B0 error of the 4-wheel headline datasets (40 dB, 5 seeds x 10) depend on the pass design?

Each dataset's speeds and payloads are regenerated from its seed key exactly as in
experiments/p2_multiwheel.dataset (roughness levels, then speeds, then payloads; no passes are simulated).
Features per dataset: speed spread (sd of V), payload spread (sd of W), minimum speed, and the number of
DFT bins within +-30 Hz of the support resonance summed over passes. The resonance frequency f_s(W) is the
|H| peak of the rail-coupled single-wheel model that moves with k_B0 (peaks at 5.5/14/22.5 t,
interpolated in log W). Bins per pass: k with |k/T_i - f_s(W_i)| <= 30 Hz inside the 50-700 Hz band,
T_i = 20 revolutions / V_i.
Regression: OLS of the error (%) on the standardised features, plus each feature alone. Also the paired
seed-123 check (same datasets at 60 dB, and the refined estimator at 40 dB). Writes
results/p3/bias_regression.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import G_SD_DB, TRUTH, W_RANGE  # noqa: E402
from experiments.p2_common import SEEDS  # noqa: E402
from experiments.p2_common import setup  # noqa: E402
from experiments.p2_multiwheel import KMH, models  # noqa: E402
from src.inverse.whittle import F_HI, F_LO, N_REVS  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

HALF = 30.0


def resonance(sm, thb, mw1):
    f = np.arange(400.0, 700.1, 0.25)
    w = 2 * np.pi * f
    Wn = np.array([5.5, 14.0, 22.5])
    fs = []
    for W in Wn:
        th = dict(thb, **TRUTH, W=float(W))
        a0 = np.abs(mw1.components(th, w)[:, 0])
        a1 = np.abs(mw1.components(dict(th, kB0=TRUTH["kB0"] * 1.05), w)[:, 0])
        pk = [i for i in range(1, f.size - 1) if a0[i] > a0[i - 1] and a0[i] > a0[i + 1]]
        shift = [np.argmax(a1[max(i - 80, 0):i + 80]) + max(i - 80, 0) - i for i in pk]   # peak moved by +5% k_B0
        i = max((p for p, s in zip(pk, shift) if s > 0), key=lambda p: a0[p])
        fs.append(f[i])
    return Wn, np.array(fs)


def main():
    sm, thb, rough, _ = setup()
    mw1 = models(sm)[0]["1"]
    Wn, fsn = resonance(sm, thb, mw1)
    r0 = thb["r0"]
    L = N_REVS * 2 * math.pi * r0
    rows = []
    for seed in SEEDS:
        fp = RESULTS_DIR / "p2" / "headline_mw_runs" / f"snr40_seed{seed}.jsonl"
        for l in fp.read_text().splitlines():
            r = json.loads(l)
            rng = np.random.default_rng(np.random.SeedSequence(r["seed_key"]))
            rng.normal(0, G_SD_DB, rough.n_sub)
            V = rng.uniform(60.0, 110.0, 50) * KMH
            W = rng.uniform(*W_RANGE, 50)
            fs = np.interp(np.log(W), np.log(Wn), fsn)
            T = L / V
            lo, hi = np.maximum(fs - HALF, F_LO), np.minimum(fs + HALF, F_HI)
            nb = np.floor(hi * T) - np.ceil(lo * T) + 1
            rows.append({"seed": seed, "j": r["seed_key"][2], "err_pct": 100 * (math.exp(r["err_log"][0]) - 1),
                         "se_pct": 100 * r["se_log"][0], "speed_sd_kmh": float(np.std(V / KMH, ddof=1)),
                         "payload_sd_t": float(np.std(W, ddof=1)), "speed_min_kmh": float(V.min() / KMH),
                         "bins_near_resonance": float(nb.sum())})
    feats = ["speed_sd_kmh", "payload_sd_t", "speed_min_kmh", "bins_near_resonance"]
    y = np.array([r["err_pct"] for r in rows])
    X = np.array([[r[k] for k in feats] for r in rows])
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    A = np.column_stack([np.ones(len(y)), Z])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    dof = len(y) - A.shape[1]
    s2 = res @ res / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    tval = beta / np.sqrt(np.diag(cov))
    r2 = 1 - res @ res / np.sum((y - y.mean()) ** 2)
    fstat = (r2 / len(feats)) / ((1 - r2) / dof)
    joint = {"r2": float(r2), "F": float(fstat), "p_F": float(1 - stats.f.cdf(fstat, len(feats), dof)),
             "coef_pct_per_sd": {k: float(b) for k, b in zip(feats, beta[1:])},
             "t": {k: float(t) for k, t in zip(feats, tval[1:])},
             "p": {k: float(2 * (1 - stats.t.cdf(abs(t), dof))) for k, t in zip(feats, tval[1:])},
             "intercept_pct": float(beta[0])}
    single = {k: {"r": float(stats.pearsonr(X[:, i], y)[0]), "p": float(stats.pearsonr(X[:, i], y)[1])} for i, k in enumerate(feats)}
    corr_feats = np.corrcoef(X.T).tolist()
    seed_means = {s: float(np.mean([r["err_pct"] for r in rows if r["seed"] == s])) for s in SEEDS}
    an = stats.f_oneway(*[[r["err_pct"] for r in rows if r["seed"] == s] for s in SEEDS])

    def paired(tag):
        fp = RESULTS_DIR / "p3" / "bias_diag_runs" / tag
        return {json.loads(l)["j"]: 100 * (math.exp(json.loads(l)["err_log"][0]) - 1) for l in fp.read_text().splitlines()} if fp.exists() else {}
    base40 = {r["j"]: r["err_pct"] for r in rows if r["seed"] == 123}
    p60, pref = paired("base_snr60_seed123.jsonl"), paired("refined_snr40_seed123.jsonl")
    js = sorted(base40)
    pair = {"datasets": js, "base_40db_pct": [base40[j] for j in js], "base_60db_pct": [p60.get(j) for j in js],
            "refined_40db_pct": [pref.get(j) for j in js],
            "mean_base_40": float(np.mean([base40[j] for j in js])),
            "mean_base_60": float(np.mean([p60[j] for j in js if j in p60])) if p60 else None,
            "mean_refined_40": float(np.mean([pref[j] for j in js if j in pref])) if pref else None,
            "max_abs_diff_60_vs_40": float(max(abs(p60[j] - base40[j]) for j in js if j in p60)) if p60 else None,
            "max_abs_diff_refined_vs_base": float(max(abs(pref[j] - base40[j]) for j in js if j in pref)) if pref else None}
    out = {"resonance_hz_at_W": dict(zip([float(w) for w in Wn], [float(x) for x in fsn])), "n": len(rows),
           "error_mean_pct": float(y.mean()), "error_sd_pct": float(y.std(ddof=1)), "joint_ols": joint, "single_feature": single,
           "feature_correlation": {"order": feats, "matrix": corr_feats}, "seed_means_pct": seed_means,
           "seed_anova": {"F": float(an.statistic), "p": float(an.pvalue)}, "seed123_paired": pair, "rows": rows}
    save_result("p3/bias_regression", out, cfg={"datasets": "headline_mw 40 dB, 5 seeds x 10", "half_window_hz": HALF,
                                                "features": feats}, seed=0)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
