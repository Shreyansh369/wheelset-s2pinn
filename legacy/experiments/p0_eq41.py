"""P0.4: test Eq. (41) (residual-induced damping bias) on SDOF and 2-DOF systems.

Pre-registered before running (stored in the result config):

* Transient: tanh-MLP PINNs on free decay, windows of 2 and 4 cycles of mode 1,
  capacities (width, Adam steps) in {(16, 3000), (32, 6000), (64, 10000)},
  zeta in {2, 5}%, seeds {42, 123, 456, 789, 1024}. Per mode: fitted decay rate
  lambda_meas, residual floor R (residual not explained by the fitted pole),
  Eq. (41) prediction sqrt(lambda0^2 + (R/2w)^2) and its finite-window form.
* Steady state: forced response over 2 forcing periods with periodicity
  penalties, at 9 frequencies spanning +-3 half-power half-widths around mode 1,
  zeta = 2%, same seeds. Model: S2-PINN's learnable-frequency Fourier time
  branch with K in {2, 4, 8} frequency pairs (3000 Adam steps, lr 1e-3, the
  S2-PINN default). The effective damping is a modal FRF fit to the complex
  amplitudes. Predictions: Eq. (41) with R at resonance, and the ridge law with
  R(Omega), the latter also checked point by point on amplitude.
  (A tanh-MLP time model was piloted first and stayed at the trivial solution
  x = 0 at every capacity tried; a small MLP arm at resonance documents this.)
* Gate criterion (user's G0): Eq. (41) within 10% of measured effective damping.
  Evaluated as the median over runs of |lambda_meas - lambda_pred| / lambda_meas,
  per setting. Also reported: fraction of runs within 10%, the same on the
  "informative" subset (measured bias >= 10% of lambda0), and a fitted measured
  relation lambda^2 - lambda0^2 = c (R/2w)^beta.

Usage: python experiments/p0_eq41.py [--workers 4] [--quick]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

SEEDS = [42, 123, 456, 789, 1024]
W1 = 2 * math.pi
W2 = 2 * math.pi * 2.7
TRANSIENT_CAPS = [(16, 3000), (32, 6000), (64, 10000)]
FORCED_CAPS = [(2, 3000), (4, 3000), (8, 3000)]  # (K frequency pairs, steps), Fourier time model
MLP_FORCED_CAPS = [(32, 6000), (64, 10000)]
ZETAS_T = [0.02, 0.05]
ZETA_F = 0.02
CYCLES_T = [2, 4]
SWEEP_HALFWIDTHS = [-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3]
N_PERIODS_F = 2


def _system(kind: str, zeta: float):
    from src.analysis.damping_bias import sdof, two_dof

    return sdof(W1, zeta) if kind == "sdof" else two_dof(W1, W2, zeta)


def run_transient(job: dict) -> dict:
    import torch

    torch.set_num_threads(1)
    from src.analysis.damping_bias import TrainConfig, measure_transient, train_transient

    s = _system(job["system"], job["zeta"])
    w, _, Phi = s.modes()
    T = job["cycles"] * 2 * math.pi / W1
    x0 = Phi.sum(1) / np.abs(Phi.sum(1)).max() if s.n > 1 else np.array([1.0])  # excite every mode
    t0 = time.perf_counter()
    model = train_transient(s, x0, np.zeros(s.n), T, TrainConfig(width=job["width"], steps=job["steps"]), job["seed"])
    modes = measure_transient(model, s, T)
    return {**job, "T": T, "modes": modes, "wall_s": time.perf_counter() - t0}


def run_forced(job: dict) -> dict:
    import torch

    torch.set_num_threads(1)
    from src.analysis.damping_bias import TrainConfig, measure_forced, train_forced

    s = _system(job["system"], job["zeta"])
    F = np.zeros(s.n)
    F[0] = 1.0
    t0 = time.perf_counter()
    model = train_forced(s, F, job["Omega"], N_PERIODS_F, TrainConfig(width=job["width"], steps=job["steps"]), job["seed"],
                         arch=job["arch"])
    m = measure_forced(model, s, F, job["Omega"], N_PERIODS_F)
    return {**job, "X_re": m["X"].real.tolist(), "X_im": m["X"].imag.tolist(), "R_floor": m["R_floor"],
            "wall_s": time.perf_counter() - t0}


def build_jobs(quick: bool) -> tuple[list[dict], list[dict]]:
    seeds = SEEDS[:1] if quick else SEEDS
    tj = [{"system": sy, "zeta": z, "cycles": c, "width": wd, "steps": st, "seed": sd}
          for sy in ("sdof", "2dof") for z in ZETAS_T for c in CYCLES_T for (wd, st) in TRANSIENT_CAPS for sd in seeds]
    fj = [{"system": sy, "zeta": ZETA_F, "Omega": W1 * (1 + ZETA_F * h), "halfwidths": h, "width": wd, "steps": st,
           "seed": sd, "arch": "fourier"}
          for sy in ("sdof", "2dof") for (wd, st) in FORCED_CAPS for sd in seeds for h in SWEEP_HALFWIDTHS]
    fj += [{"system": "sdof", "zeta": ZETA_F, "Omega": W1, "halfwidths": 0, "width": wd, "steps": st, "seed": sd, "arch": "mlp"}
           for (wd, st) in MLP_FORCED_CAPS for sd in seeds]
    if quick:
        tj = [j for j in tj if j["width"] == 16]
        fj = [j for j in fj if j["width"] == 4 and j["arch"] == "fourier"]
    return tj, fj


def rel(a: float, b: float) -> float:
    return abs(a - b) / abs(a)


def summarise(transient: list[dict], forced: list[dict]) -> dict:
    from src.analysis.damping_bias import fit_sdof_frf, predict_lambda_eq41, ridge_amplitude

    summary: dict = {}
    # ---------------- transient
    for sy in ("sdof", "2dof"):
        recs = [dict(m, **{k: r[k] for k in ("zeta", "cycles", "width", "steps", "seed", "T")})
                for r in transient if r["system"] == sy for m in r["modes"]]
        summary[f"transient/{sy}"] = _gate_stats(recs, "lambda_meas", "lambda_pred_eq41", extra_pred="lambda_pred_window")
        summary[f"transient/{sy}"]["records"] = recs

    # ---------------- forced: per (system, capacity, seed) sweep -> FRF fit
    for sy in ("sdof", "2dof"):
        s = _system(sy, ZETA_F)
        w, zeta, Phi = s.modes()
        recs = []
        for (wd, st) in FORCED_CAPS:
            for sd in SEEDS:
                rows = sorted([r for r in forced if r["system"] == sy and r["width"] == wd and r["seed"] == sd
                               and r["arch"] == "fourier"], key=lambda r: r["Omega"])
                if len(rows) < 5:
                    continue
                Om = np.array([r["Omega"] for r in rows])
                X = np.array([np.array(r["X_re"]) + 1j * np.array(r["X_im"]) for r in rows])  # [n_om, n]
                Rf = np.array([r["R_floor"] for r in rows])
                q1 = X @ (s.M @ Phi[:, 0])  # mode-1 modal amplitude
                F = np.zeros(s.n)
                F[0] = 1.0
                X_true = np.array([ridge_amplitude(s, o, F, 0.0) for o in Om]) @ (s.M @ Phi[:, 0])
                X_ridge = np.array([ridge_amplitude(s, o, F, r) for o, r in zip(Om, Rf)]) @ (s.M @ Phi[:, 0])
                fm = fit_sdof_frf(Om, q1, w[0], zeta[0])
                ft = fit_sdof_frf(Om, X_true, w[0], zeta[0])
                fr = fit_sdof_frf(Om, X_ridge, w[0], zeta[0])
                R_res = float(Rf[np.argmin(np.abs(Om - w[0]))])
                amp_meas = np.abs(q1) / np.abs(X_true)
                amp_ridge = np.abs(X_ridge) / np.abs(X_true)
                recs.append({
                    "K_freq_pairs": wd, "width": wd, "steps": st, "seed": sd, "lambda0": float(zeta[0] * w[0]),
                    "amp_ratio_meas_all": amp_meas.tolist(), "amp_ratio_ridge_all": amp_ridge.tolist(),
                    "non_collapsed": bool(np.all((amp_meas > 0.05) & (amp_meas < 2.0))),
                    "lambda0_frf_fit_to_exact": ft["decay_rate"],
                    "lambda_meas": fm["decay_rate"], "wn_meas": fm["wn"], "frf_fit_cost": fm["fit_cost"],
                    "R_floor_at_resonance": R_res, "R_floor_all": Rf.tolist(),
                    "lambda_pred_eq41": predict_lambda_eq41(float(zeta[0] * w[0]), float(w[0]), R_res),
                    "lambda_pred_ridge": fr["decay_rate"],
                    "amp_ratio_at_resonance_meas": float(abs(q1[np.argmin(np.abs(Om - w[0]))]) / abs(X_true[np.argmin(np.abs(Om - w[0]))])),
                })
        summary[f"forced/{sy}"] = _gate_stats(recs, "lambda_meas", "lambda_pred_eq41", extra_pred="lambda_pred_ridge")
        nc = [r for r in recs if r["non_collapsed"]]
        summary[f"forced/{sy}"]["non_collapsed_subset"] = _gate_stats(nc, "lambda_meas", "lambda_pred_eq41",
                                                                      extra_pred="lambda_pred_ridge") if nc else {"n": 0}
        am = np.concatenate([r["amp_ratio_meas_all"] for r in recs]) if recs else np.array([])
        ar = np.concatenate([r["amp_ratio_ridge_all"] for r in recs]) if recs else np.array([])
        ok = am > 0.05
        summary[f"forced/{sy}"]["pointwise_ridge_amplitude"] = {
            "n_points": int(am.size), "n_non_collapsed": int(ok.sum()),
            "median_rel_err_non_collapsed": float(np.median(np.abs(am[ok] - ar[ok]) / am[ok])) if ok.any() else None,
            "frac_within_10pct_non_collapsed": float(np.mean(np.abs(am[ok] - ar[ok]) / am[ok] <= 0.10)) if ok.any() else None,
        }
        summary[f"forced/{sy}"]["records"] = recs
    mlp = [r for r in forced if r.get("arch") == "mlp"]
    if mlp:
        s = _system("sdof", ZETA_F)
        Xt = abs(ridge_amplitude(s, W1, np.array([1.0]), 0.0)[0])
        summary["forced/sdof_mlp_at_resonance"] = {
            "n": len(mlp),
            "amp_ratio": [abs(complex(r["X_re"][0], r["X_im"][0])) / Xt for r in mlp],
            "caps": [(r["width"], r["steps"]) for r in mlp], "seeds": [r["seed"] for r in mlp],
            "R_floor": [r["R_floor"] for r in mlp],
        }
    return summary


def _gate_stats(recs: list[dict], meas: str, pred: str, extra_pred: str | None = None) -> dict:
    if not recs:
        return {"n": 0}
    e = np.array([rel(r[meas], r[pred]) for r in recs])
    bias = np.array([(r[meas] - r["lambda0"]) / r["lambda0"] for r in recs])
    info = bias >= 0.10
    out = {
        "n": len(recs),
        "median_rel_err_eq41": float(np.median(e)),
        "frac_within_10pct_eq41": float(np.mean(e <= 0.10)),
        "n_informative": int(info.sum()),
        "median_rel_err_eq41_informative": float(np.median(e[info])) if info.any() else None,
        "frac_within_10pct_eq41_informative": float(np.mean(e[info] <= 0.10)) if info.any() else None,
        "median_measured_bias_over_lambda0": float(np.median(bias)),
        "pass_eq41_10pct_median": bool(np.median(e) <= 0.10),
    }
    if extra_pred:
        e2 = np.array([rel(r[meas], r[extra_pred]) for r in recs])
        out[f"median_rel_err_{extra_pred}"] = float(np.median(e2))
        out[f"frac_within_10pct_{extra_pred}"] = float(np.mean(e2 <= 0.10))
    # measured relation: lambda^2 - lambda0^2 = c (R / 2w)^beta, on runs with positive excess
    Rkey = "R_floor" if "R_floor" in recs[0] else "R_floor_at_resonance"
    om = np.array([r.get("omega", 2 * math.pi) for r in recs])
    y = np.array([r[meas] ** 2 - r["lambda0"] ** 2 for r in recs])
    x = np.array([r[Rkey] for r in recs]) / (2 * om)
    ok = (y > 0) & (x > 0)
    if ok.sum() >= 3:
        A = np.stack([np.ones(ok.sum()), np.log(x[ok])], 1)
        coef, *_ = np.linalg.lstsq(A, np.log(y[ok]), rcond=None)
        resid = np.log(y[ok]) - A @ coef
        se = np.sqrt(resid @ resid / max(ok.sum() - 2, 1) / np.sum((np.log(x[ok]) - np.log(x[ok]).mean()) ** 2))
        out["measured_relation"] = {"c": float(np.exp(coef[0])), "beta": float(coef[1]), "beta_se": float(se),
                                    "n": int(ok.sum()), "eq41_means": "c=1, beta=2"}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    tj, fj = build_jobs(args.quick)
    raw_path = RESULTS_DIR / "p0" / ("eq41_raw_quick.jsonl" if args.quick else "eq41_raw.jsonl")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if raw_path.exists():  # resume
        for line in raw_path.read_text().splitlines():
            r = json.loads(line)
            done[json.dumps(r["job"], sort_keys=True)] = r
    todo = [("transient", j) for j in tj] + [("forced", j) for j in fj]
    todo = [(k, j) for k, j in todo if json.dumps(j, sort_keys=True) not in done]
    print(f"{len(done)} done, {len(todo)} to run")
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as ex, raw_path.open("a") as fh:
        futs = {ex.submit(run_transient if k == "transient" else run_forced, j): (k, j) for k, j in todo}
        for i, f in enumerate(as_completed(futs)):
            k, j = futs[f]
            res = f.result()
            rec = {"kind": k, "job": j, "result": res}
            fh.write(json.dumps(rec, default=float) + "\n")
            fh.flush()
            done[json.dumps(j, sort_keys=True)] = rec
            print(f"[{i + 1}/{len(todo)}] {k} {j} {res['wall_s']:.0f}s", flush=True)
    wall = time.perf_counter() - t0
    transient = [r["result"] for r in done.values() if r["kind"] == "transient" and r["job"] in tj]
    forced = [r["result"] for r in done.values() if r["kind"] == "forced" and r["job"] in fj]
    summary = summarise(transient, forced)
    cfg = {"seeds": SEEDS, "w1": W1, "w2": W2, "transient_caps": TRANSIENT_CAPS, "forced_caps": FORCED_CAPS,
           "mlp_forced_caps": MLP_FORCED_CAPS, "zetas_transient": ZETAS_T, "zeta_forced": ZETA_F, "cycles_transient": CYCLES_T,
           "sweep_halfwidths": SWEEP_HALFWIDTHS, "n_periods_forced": N_PERIODS_F, "quick": args.quick,
           "gate": "median |lambda_meas - lambda_eq41| / lambda_meas <= 0.10 per setting",
           "R_definition": "sqrt(mean(r_floor^2)/mean(x_fit^2)), r_floor = PINN residual minus residual of the fitted pole/harmonic"}
    name = "p0/eq41_quick" if args.quick else "p0/eq41"
    save_result(name, summary, cfg=cfg, wall_seconds=wall)
    for k, v in summary.items():
        print(k, {kk: vv for kk, vv in v.items() if kk != "records"})


if __name__ == "__main__":
    main()
