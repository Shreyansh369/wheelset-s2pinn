"""Robust (sandwich) standard errors for stored fits, without refitting.

Each dataset is regenerated from its seed key (deterministic), the nuisances are re-profiled at the stored
estimate, and the covariance of the globals is computed from the expected Fisher J (exact kernel-mixed
sub-band columns) and per-cluster score sums:
  model    : J^-1 (expected information at the estimate)
  bin      : clusters = same DFT bin across passes (existing estimator, for repeated sections)
  block8   : clusters = 8 adjacent bins within a pass (about the main lobe and first sidelobes)
  block61  : clusters = 61 adjacent bins within a pass (the debiasing kernel support, +-30 bins)
--headline : the 4-wheel headline fits (results/p2/headline_mw_runs, 20 and 40 dB, 5 seeds x 10).
--kappa    : the 20 kappa-revalidation replicates (results/p3/kappa_coest_runs, co-estimating fit),
             both periods.
Chunks by --j0/--j1 over the list of fits; rows to results/p3/robust_se_runs/*.jsonl; --summarise ->
results/p3/robust_se.json (Wald 90% coverage of k_B0 with each SE; for kappa, coverage of the change with
and without kappa = 0.044 and the slope correction of results/p3/calibration.json).
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

from experiments.p1_fe_direct import TRUTH, WIM, cp_interval  # noqa: E402
from experiments.p2_common import SEEDS  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

OUT = RESULTS_DIR / "p3" / "robust_se_runs"
CL = [("bin", "bin", 0), ("block8", "block", 8), ("block61", "block", 61)]
Z90 = 1.6448536269514722
T_START, DEADLINE_S = time.perf_counter(), 110 * 60


def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def _append(fp, row):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print({k: v for k, v in row.items() if k not in ("se",)}, flush=True)


def robust(est, phi):
    _, st = est.profile_nll(np.asarray(phi, float), return_state=True)
    r = est.sandwich_cov(phi, st["logg"], st["lw"], exact_sub=True, clusters_list=CL)
    se = {"model": r["bin"]["se_log_model"]}
    se.update({name: r[name]["se_log_sandwich"] for name, _, _ in CL})
    return se


def headline_list():
    out = []
    for snr in (20, 40):
        for seed in SEEDS:
            for r in _rows(RESULTS_DIR / "p2" / "headline_mw_runs" / f"snr{snr}_seed{seed}.jsonl"):
                out.append(r)
    return sorted(out, key=lambda r: tuple(r["seed_key"]))


def headline(j0, j1):
    from experiments.p2_common import setup
    from experiments.p2_multiwheel import dataset, models
    from src.analysis.multiwheel import MultiWheelFamily
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb)
    fp = OUT / "headline.jsonl"
    done = {tuple(r["seed_key"]) for r in _rows(fp)}
    for r in headline_list()[j0:j1]:
        key = tuple(r["seed_key"])
        if key in done:
            continue
        if time.perf_counter() - T_START > DEADLINE_S - 300:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, key, N=50, snr=float(key[1]))
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True)
        se = robust(est, r["phi_hat"])
        _append(fp, {"seed_key": list(key), "snr_db": key[1], "err_log": r["err_log"][0], "se_obs": r["se_log"][0],
                     "se": se, "wall_s": time.perf_counter() - t0})


def kappa(j0, j1):
    from experiments.p2_relative_change import gen, truth
    from experiments.p2_relative_coest_drift import EST, setup_all
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "kappa.jsonl"
    done = {(r["rep"], r["set"]) for r in _rows(fp)}
    reps = sorted((r for r in _rows(RESULTS_DIR / "p3" / "kappa_coest_runs" / "rows.jsonl") if r["rep"] < 20), key=lambda r: r["rep"])
    for r in reps[j0:j1]:
        for s, kt in (("base", TRUTH["kB0"]), ("later", TRUTH["kB0"] * (1 - r["x"]))):
            if (r["rep"], s) in done:
                continue
            if time.perf_counter() - T_START > DEADLINE_S - 600:
                print("deadline", flush=True)
                return
            t0 = time.perf_counter()
            P, Wm, Ws, g = gen(sm, truth(thb, r["misspec"], kt), rough, mw, (45, r["rep"], 0 if s == "base" else 1))
            est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fams["coest"], debias=True)
            se = robust(est, r["phi_" + s])
            _append(fp, {"rep": r["rep"], "set": s, "se": se, "wall_s": time.perf_counter() - t0})


def summarise():
    out = {}
    H = _rows(OUT / "headline.jsonl")
    hl = []
    for snr in (20, 40):
        R = [r for r in H if r["snr_db"] == snr]
        if not R:
            continue
        cell = {"snr_db": snr, "n": len(R)}
        for name in ["obs", "model"] + [c[0] for c in CL]:
            se = np.array([r["se_obs"] if name == "obs" else r["se"][name][0] for r in R])
            e = np.array([r["err_log"] for r in R])
            k = int(np.sum(np.abs(e) <= Z90 * se))
            cell[name] = {"coverage90": k / len(R), "ci95": cp_interval(k, len(R)), "se_median_pct": float(np.median(se) * 100),
                          "rmse_over_median_se": float(np.sqrt(np.mean(e**2)) / np.median(se))}
        hl.append(cell)
    out["headline"] = hl
    K = _rows(OUT / "kappa.jsonl")
    reps = {r["rep"]: r for r in _rows(RESULTS_DIR / "p3" / "kappa_coest_runs" / "rows.jsonl") if r["rep"] < 20}
    cal = RESULTS_DIR / "p3" / "calibration.json"
    slope = json.loads(cal.read_text())["payload"]["coest"]["slope"] if cal.exists() else 1.0
    by = {}
    for r in K:
        by.setdefault(r["rep"], {})[r["set"]] = r["se"]
    full = [j for j in sorted(by) if len(by[j]) == 2 and j in reps]
    kc = {"n": len(full), "slope_correction": slope, "kappa": 0.044,
          "note": "slope from pseudo-true correct-model fits and sandwich SE are not tuned on these replicates"}
    for name in ["stored", "model"] + [c[0] for c in CL]:
        for corr in (False, True):
            for kap in (0.0, 0.044):
                c = 0
                for j in full:
                    r = reps[j]
                    se = r["se"] if name == "stored" else math.hypot(by[j]["base"][name][0], by[j]["later"][name][0])
                    d = r["D_hat"] / slope if corr else r["D_hat"]
                    c += abs(d - r["D_true"]) <= Z90 * math.sqrt(se**2 + (kap * d) ** 2)
                key = f"{name}{'_slopecorr' if corr else ''}_kappa{kap}"
                kc[key] = {"covered": int(c), "coverage": c / len(full) if full else None, "ci95": cp_interval(int(c), len(full)) if full else None}
        if name != "stored":
            kc[f"{name}_se_D_median_pct"] = float(np.median([math.hypot(by[j]["base"][name][0], by[j]["later"][name][0]) for j in full]) * 100) if full else None
    kc["stored_se_D_median_pct"] = float(np.median([reps[j]["se"] for j in full]) * 100) if full else None
    out["kappa"] = kc
    save_result("p3/robust_se", out, cfg={"clusters": CL, "fisher": "expected, exact kernel-mixed sub-band columns",
                                         "wald_level": 0.90}, seed=0)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--headline", action="store_true")
    ap.add_argument("--kappa", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=1000)
    a = ap.parse_args()
    if a.headline:
        headline(a.j0, a.j1)
    if a.kappa:
        kappa(a.j0, a.j1)
    if a.summarise:
        summarise()
