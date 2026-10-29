"""Preregistration v2 (docs/preregistration_v2.md): the corrected estimator and the v2 change studies.

Corrected estimator ("xpr-1"): the frozen estimator (multipass-whittle-2, co-estimating k_B0, c_B, k_f, k_H0)
fitted to each period from the standard start, then a cross-period restart: each period is refitted from the
other period's standard-start estimate (the full parameter vector, unchanged; no truth information). Per period
the solution with the lower negative log-likelihood is kept; a gain of 0.01 or less keeps the standard-start
fit. Standard error of k_B0 from the observed information at the kept solution; if that information is not
positive definite (singular, in practice c_B driven towards zero), the expected-information SE with c_B
fixed at its kept estimate and the fitted roughness levels and payloads (no truth information). Every fit
that fails (Nelder-Mead not converged, or a non-finite NLL or estimate) is logged to
results/p5/failed_fits.jsonl and kept in the statistics.

Studies (empty payload band, 50 passes per period, 60-110 km/h, 40 dB, as the v1 kappa study):
  --kind simerr : simultaneous random model errors (all five factors of experiments/p2_model_form_mw.RANGES,
                  k_f stratified over the n replicates), true change x ~ U(2%, 10%);
  --kind zero   : the same draws and data seeds with zero true change.
Seeds: draws SeedSequence([47, j]) (k_f permutation SeedSequence([47, 999, n])); data (47, j, 0/1). The v1
studies used 45. Rows per fit: results/p5/runs/<kind><tag>_fits.jsonl (resumable after a restart); one row per
replicate: results/p5/runs/<kind><tag>.jsonl. Each replicate row also carries the frozen-estimator result
(standard-start fits only) on the same data.

    WHEELSET_CONFIG_DIR=config/sensitivity/mass_dusza python3 experiments/p5_v2.py --kind simerr --n 200 \
        --j0 0 --j1 1 --tag _massd
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

from experiments.p1_fe_direct import TRUTH, WIM  # noqa: E402
from experiments.p2_model_form_mw import RANGES  # noqa: E402
from experiments.p2_relative_change import gen, truth  # noqa: E402
from experiments.p2_relative_coest_drift import EST, phi, setup_all  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, _git_commit  # noqa: E402

OUT = RESULTS_DIR / "p5"
SEED = 47
NAMES = EST["coest"]
TIE_NLL = 0.01          # a restart must lower the NLL by more than this to replace the standard-start fit
FAILED = OUT / "failed_fits.jsonl"
ESTIMATOR = "multipass-whittle-2 + cross-period restart (xpr-1)"


def draw(j, n):
    """Pre-registered draw of replicate j of n: model-error factors and true change (preregistration_v2 §3)."""
    perm = np.random.default_rng(np.random.SeedSequence([SEED, 999, n])).permutation(n)
    rng = np.random.default_rng(np.random.SeedSequence([SEED, j]))
    mis = {p: float(math.exp(RANGES[p][0] * rng.standard_normal())) for p in RANGES}
    mis["kf"] = float(math.exp(RANGES["kf"][0] * norm.ppf((perm[j] + 0.5) / n)))
    return mis, float(rng.uniform(0.02, 0.10))


def _append(fp, row):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _rows(fp):
    return [json.loads(l) for l in fp.read_text().splitlines() if l.strip()] if fp.exists() else []


def _failed(r) -> str | None:
    if not r["converged"]:
        return "nelder-mead not converged"
    if not (math.isfinite(r["nll"]) and all(math.isfinite(v) for v in r["phi"])):
        return "non-finite nll or estimate"
    return None


def se_cb_fixed(est, ph, logg, lw):
    """Expected-information SE of log k_B0 with c_B fixed at its estimate (fitted levels and payloads)."""
    J = est._fisher_parts(np.asarray(ph, float), np.asarray(logg, float), np.asarray(lw, float))[0]
    ic = NAMES.index("cB")
    keep = [i for i in range(J.shape[0]) if i != ic]
    Jk = J[np.ix_(keep, keep)]
    sc = 1 / np.sqrt(np.diag(Jk))
    return float(math.sqrt(np.linalg.inv(Jk * np.outer(sc, sc))[0, 0] * sc[0] ** 2))


def replicate(kind, j, n, tag, ctx):
    """Four fits (standard start per period, then the cross-period restarts), resumable fit by fit."""
    sm, thb, rough, mw, fams = ctx
    mis, x = draw(j, n)
    if kind == "zero":
        x = 0.0
    ff = OUT / "runs" / f"{kind}{tag}_fits.jsonl"
    have = {(r["rep"], r["period"], r["start"]): r for r in _rows(ff) if r["n"] == n}
    data, ests, fits = {}, {}, {}
    for s, kt in (("base", TRUTH["kB0"]), ("later", TRUTH["kB0"] * (1 - x))):
        data[s] = gen(sm, truth(thb, mis, kt), rough, mw, (SEED, j, 0 if s == "base" else 1))
        ests[s] = MultiPassWhittle([dict(q) for q in data[s][0]], data[s][1], WIM, rough, fams["coest"], debias=True)
    commit = _git_commit()
    for s, start in (("base", "std"), ("later", "std"), ("base", "xpr"), ("later", "xpr")):
        k = (j, s, start)
        if k in have:
            fits[(s, start)] = have[k]
            continue
        other = "later" if s == "base" else "base"
        phi0 = phi(NAMES, start=True) if start == "std" else np.asarray(fits[(other, "std")]["phi"], float)
        t0 = time.perf_counter()
        r = ests[s].fit(phi0)
        row = {"rep": j, "n": n, "kind": kind, "period": s, "start": start, "phi0": list(map(float, phi0)),
               "phi": r["phi"], "se_log": r["se_log"], "nll": r["nll"], "converged": r["converged"],
               "n_iter": r["n_iter"], "n_eval": r["n_eval"], "logg": r["logg"], "lw": r["lw"],
               "wall_s": time.perf_counter() - t0, "git_commit": commit}
        _append(ff, row)
        fits[(s, start)] = row
        why = _failed(row)
        if why:
            _append(FAILED, {"study": f"{kind}{tag}", "rep": j, "n": n, "period": s, "start": start, "reason": why,
                             "nll": r["nll"], "phi": r["phi"], "n_iter": r["n_iter"], "seed_key": [SEED, j, 0 if s == "base" else 1],
                             "git_commit": commit})
    per = {}
    for s in ("base", "later"):
        a, b = fits[(s, "std")], fits[(s, "xpr")]
        use_x = math.isfinite(b["nll"]) and b["nll"] < a["nll"] - TIE_NLL
        kept = b if use_x else a
        se = kept["se_log"][0]
        src = "observed"
        if not math.isfinite(se):
            se, src = se_cb_fixed(ests[s], kept["phi"], kept["logg"], kept["lw"]), "cb_fixed"
        se_std, src_std = a["se_log"][0], "observed"
        if not math.isfinite(se_std):
            se_std, src_std = (se, src) if not use_x else (se_cb_fixed(ests[s], a["phi"], a["logg"], a["lw"]), "cb_fixed")
        per[s] = {"kept": "xpr" if use_x else "std", "nll_gain": a["nll"] - b["nll"], "phi": kept["phi"], "se": se,
                  "se_source": src, "singular": src == "cb_fixed", "cb_at_bound": kept["phi"][1] < 0,
                  "failed": bool(_failed(kept)), "phi_std": a["phi"], "se_std": se_std, "se_std_source": src_std,
                  "converged_std": a["converged"], "converged_xpr": b["converged"]}
    dt = math.log(1 - x)
    d = per["later"]["phi"][0] - per["base"]["phi"][0]
    d_std = per["later"]["phi_std"][0] - per["base"]["phi_std"][0]
    return {"rep": j, "n": n, "kind": kind, "tag": tag, "misspec": mis, "x": x, "D_true": dt,
            "D_hat": d, "se": math.hypot(per["base"]["se"], per["later"]["se"]),
            "D_hat_frozen": d_std, "se_frozen": math.hypot(per["base"]["se_std"], per["later"]["se_std"]),
            "periods": per, "estimator": ESTIMATOR, "band": "empty",
            "config_dir": os.environ.get("WHEELSET_CONFIG_DIR", "config"), "git_commit": commit,
            "wall_s": sum(fits[k]["wall_s"] for k in fits)}


def run(kind, j0, j1, n, tag):
    from experiments.p4_banded import set_band
    set_band("empty")
    sm, thb, rough, mw, fams, _ = setup_all()
    fp = OUT / "runs" / f"{kind}{tag}.jsonl"
    done = {r["rep"] for r in _rows(fp) if r["n"] == n}
    for j in range(j0, j1):
        if j not in done:
            row = replicate(kind, j, n, tag, (sm, thb, rough, mw, fams))
            _append(fp, row)
            print(json.dumps({k: row[k] for k in ("rep", "D_hat", "D_true", "se", "D_hat_frozen", "wall_s")}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("simerr", "zero"), required=True)
    ap.add_argument("--n", type=int, required=True, help="number of replicates of the study (fixes the k_f strata)")
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=1)
    ap.add_argument("--tag", default="", help="run-file suffix naming the configuration, e.g. _massd or _frozen")
    a = ap.parse_args()
    run(a.kind, a.j0, a.j1, a.n, a.tag)
