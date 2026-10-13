"""Validation Monte Carlo runs, chunked so that every process finishes well inside 2 h.

--kappa  : fresh relative-change Monte Carlo for the co-estimating fit (k_B0, c_B, k_f, k_H0 per period)
           with all five misspecifications drawn at random (RANGES of p2_model_form_mw). k_f is drawn
           log-normally (sigma 0.35) by stratified sampling: replicate j uses the quantile (pi_j + 0.5)/n of
           a random permutation pi, so the n draws cover the distribution evenly and the top stratum reaches
           x2.2 (n = 40). The other four are drawn i.i.d. log-normal. True change x ~ U(2%, 10%) decrease.
           Replicates 40-43 are stress cases with k_f fixed at x2.0, 2.3, 2.6, 3.0 (other draws random);
           they are reported separately and do not enter the coverage estimate.
           Rows: results/p3/kappa_coest_runs/rows.jsonl.
--drift  : drift Monte Carlo, later-period k_f x f (default 0.8), true change 0, both estimators.
           Rows: results/p3/drift_mc_runs/kf<f>.jsonl.
--bias   : bias diagnosis on the 4-wheel headline datasets (keys (42, 40, j), j < 10): the same data
           (roughness, speeds, payloads, noise draw) at another SNR, with the base estimator (0.5 Hz table,
           sub-band-attributed scoring) or the refined one (--refined: 0.25 Hz table, exact sub-band scoring).
           Rows: results/p3/bias_diag_runs/<variant>_snr<snr>.jsonl.
Every row records its wall time. Chunks: --j0, --j1 (replicate range). --summarise writes
results/p3/validation_mc.json.
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
from scipy.stats import norm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import START, TRUTH, WIM, cp_interval  # noqa: E402
from experiments.p2_model_form_mw import RANGES  # noqa: E402
from experiments.p2_relative_change import gen, truth  # noqa: E402
from experiments.p2_relative_coest_drift import EST, phi, setup_all  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p3"
N_KAPPA = 40
KF_STRESS = (2.0, 2.3, 2.6, 3.0)  # replicates 40-43: k_f fixed beyond the stratified range, reported separately
KAPPA_COEST = 0.044      # results/p2/relative_coest_drift.json coest_relative.kappa_coest (rounded as stated)
KAPPA_NOMINAL = 0.26


def _done(fp, key):
    return {key(json.loads(l)) for l in fp.read_text().splitlines() if l.strip()} if fp.exists() else set()


def _append(fp, row):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(row, flush=True)


T_START = time.perf_counter()
DEADLINE_S = 110 * 60        # a chunk never starts a replicate it cannot finish inside this budget
REP_MAX_S = [55 * 60]        # running estimate of the slowest replicate (initial: slowest seen so far, 53 min)


def _time_left_for_rep() -> bool:
    ok = time.perf_counter() - T_START + REP_MAX_S[0] <= DEADLINE_S
    if not ok:
        print(f"deadline: stopping chunk after {time.perf_counter() - T_START:.0f} s", flush=True)
    return ok


def _fit(P, Wm, rough, fam, names, **kw):
    est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True, **kw)
    r = est.fit(phi(names, start=True))
    return r, est


# ----------------------------------------------------------------------------- (1) kappa, co-estimating fit
def kappa_draw(j):
    perm = np.random.default_rng(np.random.SeedSequence([45, 999])).permutation(N_KAPPA)
    rng = np.random.default_rng(np.random.SeedSequence([45, j]))
    mis = {p: float(math.exp(RANGES[p][0] * rng.standard_normal())) for p in RANGES}
    mis["kf"] = (float(math.exp(RANGES["kf"][0] * norm.ppf((perm[j] + 0.5) / N_KAPPA))) if j < N_KAPPA
                 else KF_STRESS[j - N_KAPPA])
    return mis, float(rng.uniform(0.02, 0.10))


def kappa(j0, j1):
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "kappa_coest_runs" / "rows.jsonl"
    done = _done(fp, lambda r: r["rep"])
    for j in range(j0, j1):
        if j in done:
            continue
        if not _time_left_for_rep():
            break
        t0 = time.perf_counter()
        mis, x = kappa_draw(j)
        res = {}
        for s, kt in (("base", TRUTH["kB0"]), ("later", TRUTH["kB0"] * (1 - x))):
            P, Wm, Ws, g = gen(sm, truth(thb, mis, kt), rough, mw, (45, j, 0 if s == "base" else 1))
            r, _ = _fit(P, Wm, rough, fams["coest"], EST["coest"])
            res[s] = r
        d = res["later"]["phi"][0] - res["base"]["phi"][0]
        dt = math.log(1 - x)
        se = math.hypot(res["base"]["se_log"][0], res["later"]["se_log"][0])
        _append(fp, {"rep": j, "misspec": mis, "x": x, "D_hat": d, "D_true": dt, "se": se,
                     "abs_err_base": res["base"]["phi"][0] - math.log(TRUTH["kB0"]),
                     "phi_base": res["base"]["phi"], "phi_later": res["later"]["phi"],
                     "converged": res["base"]["converged"] and res["later"]["converged"],
                     "wall_s": time.perf_counter() - t0})
        REP_MAX_S[0] = max(REP_MAX_S[0], time.perf_counter() - t0)


# ----------------------------------------------------------------------------- (3) drift MC
def drift(j0, j1, f):
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "drift_mc_runs" / f"kf{f}.jsonl"
    done = _done(fp, lambda r: (r["estimator"], r["rep"]))
    for j in range(j0, j1):
        if all((e, j) in done for e in EST):
            continue
        if not _time_left_for_rep():
            break
        t0 = time.perf_counter()
        data = {"base": gen(sm, truth(thb, {}, TRUTH["kB0"]), rough, mw, (46, j, 0)),
                "later": gen(sm, truth(thb, {"kf": f}, TRUTH["kB0"]), rough, mw, (46, j, 1))}
        for e in EST:
            if (e, j) in done:
                continue
            t1 = time.perf_counter()
            res = {s: _fit(data[s][0], data[s][1], rough, fams[e], EST[e])[0] for s in data}
            d = res["later"]["phi"][0] - res["base"]["phi"][0]
            se = math.hypot(res["base"]["se_log"][0], res["later"]["se_log"][0])
            _append(fp, {"estimator": e, "rep": j, "f": f, "D_hat": d, "se": se, "alarm": bool(d < -1.645 * se),
                         "converged": res["base"]["converged"] and res["later"]["converged"],
                         "wall_s": time.perf_counter() - t1 + (t1 - t0 if e == "nominal" else 0.0)})
        REP_MAX_S[0] = max(REP_MAX_S[0], time.perf_counter() - t0)


# ----------------------------------------------------------------------------- (2) bias diagnosis
def bias(j0, j1, snr, refined, seed=42, kb=None):
    from experiments.p2_common import setup
    from experiments.p2_multiwheel import dataset, models
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb, f_grid=np.arange(45.0, 702.0, 0.25) if refined else None)
    tag = "refined" if refined else ("base" if kb is None else f"kb{kb}")
    fp = OUT / "bias_diag_runs" / (f"{tag}_snr{int(snr)}.jsonl" if seed == 42 else f"{tag}_snr{int(snr)}_seed{seed}.jsonl")
    done = _done(fp, lambda r: r["j"])
    lt = math.log(TRUTH["kB0"])
    for j in range(j0, j1):
        if j in done:
            continue
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, (seed, 40, j), N=50, snr=snr)
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True, exact_subband=refined,
                               **({} if kb is None else {"Kb": kb}))
        r = est.fit(np.log([START["kB0"], START["cB"]]))
        crb = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g), np.log(Ws))["crb_log"]
        _append(fp, {"j": j, "seed": seed, "snr_db": snr, "variant": tag, "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])],
                     "se_log": r["se_log"], "crb_log": crb, "converged": r["converged"], "wall_s": time.perf_counter() - t0})


# ----------------------------------------------------------------------------- summary
def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def summarise():
    out = {}
    Rall = _rows(OUT / "kappa_coest_runs" / "rows.jsonl")
    R = [r for r in Rall if r["rep"] < N_KAPPA]
    if Rall:
        out["kappa_coest_stress"] = [{"rep": r["rep"], "kf": r["misspec"]["kf"], "true_change_pct": -100 * r["x"],
                                      "est_change_pct": 100 * (math.exp(r["D_hat"]) - 1),
                                      "error_frac": (r["D_hat"] - r["D_true"]) / abs(r["D_true"]),
                                      "covered": abs(r["D_hat"] - r["D_true"]) <= 1.645 * math.sqrt(r["se"] ** 2 + (KAPPA_COEST * r["D_hat"]) ** 2)}
                                     for r in sorted(Rall, key=lambda r: r["rep"]) if r["rep"] >= N_KAPPA]
    if R:
        def cov(k):
            c = [abs(r["D_hat"] - r["D_true"]) <= 1.645 * math.sqrt(r["se"] ** 2 + (k * r["D_hat"]) ** 2) for r in R]
            return sum(c), len(c)
        ks, n = cov(KAPPA_COEST)
        k0, _ = cov(0.0)
        ge = [(r["D_hat"] - r["D_true"]) / abs(r["D_true"]) for r in R]
        worst = sorted(R, key=lambda r: -abs((r["D_hat"] - r["D_true"]) / r["D_true"]))[:5]
        out["kappa_coest"] = {
            "n": n, "kappa": KAPPA_COEST, "coverage": ks / n, "coverage_ci95": cp_interval(ks, n),
            "coverage_statistical_only": k0 / n, "coverage_statistical_only_ci95": cp_interval(k0, n),
            "rms_change_error_frac": float(np.sqrt(np.mean(np.square(ge)))),
            "mean_change_error_frac": float(np.mean(ge)),
            "kappa_empirical_rms": float(np.sqrt(max(np.mean(np.square(ge)) - np.mean([(r["se"] / r["D_true"]) ** 2 for r in R]), 0.0))),
            "kf_draw_range": [min(r["misspec"]["kf"] for r in R), max(r["misspec"]["kf"] for r in R)],
            "n_kf_ge_2": sum(r["misspec"]["kf"] >= 2 for r in R),
            "abs_bias_base_pct_rms": float(np.sqrt(np.mean([(math.exp(r["abs_err_base"]) - 1) ** 2 for r in R])) * 100),
            "worst": [{"rep": r["rep"], "misspec": r["misspec"], "true_change_pct": -100 * r["x"],
                       "est_change_pct": 100 * (math.exp(r["D_hat"]) - 1),
                       "error_frac": (r["D_hat"] - r["D_true"]) / abs(r["D_true"]),
                       "covered": abs(r["D_hat"] - r["D_true"]) <= 1.645 * math.sqrt(r["se"] ** 2 + (KAPPA_COEST * r["D_hat"]) ** 2)}
                      for r in worst],
            "all_converged": all(r["converged"] for r in R),
            "wall_s_median": float(np.median([r["wall_s"] for r in R]))}
    for fp in sorted((OUT / "drift_mc_runs").glob("kf*.jsonl")):
        R = _rows(fp)
        for e in EST:
            Re = [r for r in R if r["estimator"] == e]
            if Re:
                k = sum(r["alarm"] for r in Re)
                out.setdefault("drift_mc", []).append({
                    "kf_factor": Re[0]["f"], "estimator": e, "n": len(Re), "false_alarms": k, "rate": k / len(Re),
                    "rate_ci95": cp_interval(k, len(Re)), "D_hat_mean_pct": float(np.mean([math.exp(r["D_hat"]) - 1 for r in Re]) * 100),
                    "D_hat_sd_pct": float(np.std([r["D_hat"] for r in Re], ddof=1) * 100) if len(Re) > 1 else None,
                    "se_median_pct": float(np.median([r["se"] for r in Re]) * 100),
                    "all_converged": all(r["converged"] for r in Re)})
    diag = []
    sets = {}
    for sd in (42, 123):
        hl = _rows(RESULTS_DIR / "p2" / "headline_mw_runs" / f"snr40_seed{sd}.jsonl")
        sets[("base", 40.0, sd)] = [dict(r, j=r["seed_key"][2]) for r in hl if r["seed_key"][2] < 10]
    for fp in sorted((OUT / "bias_diag_runs").glob("*.jsonl")):
        R = _rows(fp)
        if R:
            sets[(R[0]["variant"], float(R[0]["snr_db"]), R[0].get("seed", 42))] = R
    for (v, snr, sd), R in sorted(sets.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        e = np.array([r["err_log"][0] for r in R])
        c = np.array([r["crb_log"][0] for r in R])
        se = np.array([r["se_log"][0] for r in R])
        k = int(np.sum(np.abs(e) <= 1.645 * se))
        diag.append({"seed": sd, "variant": v, "snr_db": snr, "n": len(R), "bias_pct": float(np.mean(np.exp(e) - 1) * 100),
                     "bias_se_pct": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(R)) * 100),
                     "rmse_pct": float(np.sqrt(np.mean(e**2)) * 100), "crb_pct": float(np.sqrt(np.mean(c**2)) * 100),
                     "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / np.sqrt(np.mean(c**2))),
                     "coverage90_wald": k / len(R), "cB_bias_pct": float(np.mean([math.exp(r["err_log"][1]) - 1 for r in R]) * 100),
                     "datasets": sorted(r["j"] for r in R)})
    out["bias_diag"] = diag
    save_result("p3/validation_mc", out, cfg={
        "kappa": {"N_per_period": 50, "estimator": "coest (kB0, cB, kf, kH0)", "kappa": KAPPA_COEST, "ranges": RANGES,
                  "kf_sampling": "stratified log-normal sigma 0.35", "x": "U(2%, 10%) decrease"},
        "drift": {"true_change": 0, "N_per_period": 50, "snr_db": 40},
        "bias": {"datasets": "keys (42, 40, j), 4-wheel headline; same data at each SNR", "refined": "0.25 Hz table, exact sub-band scoring"}},
        seed=45)
    print(json.dumps(out, indent=1, default=str)[:4000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kappa", action="store_true")
    ap.add_argument("--drift", action="store_true")
    ap.add_argument("--bias", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=1)
    ap.add_argument("--f", type=float, default=0.8)
    ap.add_argument("--snr", type=float, default=60.0)
    ap.add_argument("--refined", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--kb", type=int, default=None, help="debiasing kernel half-width in bins (default 30)")
    a = ap.parse_args()
    if a.kappa:
        kappa(a.j0, a.j1)
    if a.drift:
        drift(a.j0, a.j1, a.f)
    if a.bias:
        bias(a.j0, a.j1, a.snr, a.refined, a.seed, a.kb)
    if a.summarise:
        summarise()
