"""Task (c): repeated passes over the same section (shared roughness, different speeds) vs independent sections.

Shared section: records aligned in position (20 revolutions from the same start point), so bin k of
every pass samples the same rail-roughness Fourier coefficient. Independent sections: a fresh
roughness realisation per pass (the model used so far). Partial coherence: the roughness seen on
pass i is rho R_k + sqrt(1 - rho^2) eps_ik (e.g. different lateral wheel paths across the railhead).

--bound: kB0/cB CRB at N = 50, SNR 40 dB, for speeds fixed 100 / 95-105 / 60-110: shared (rank-one
         Fisher) vs independent; and an exact dense Fisher for rho in {1, 0.99, 0.9, 0.5, 0} at 60-110
         (checked against the rank-one form at rho = 1 and the independent form at rho = 0).
--mc:    20 datasets per speed case for shared sections (fitted with the shared likelihood) and for
         paired independent sections (independent likelihood); plus rho = 0.9 data fitted with the
         rho = 1 shared likelihood (misspecification check).
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import (G_SD_DB, KMH, TRUTH, WIM, W_RANGE, H_single, make_dataset, phi_start,  # noqa: E402
                                   phi_true, setup, summarise)
from src.inverse.multipass import MultiPassWhittle, SingleWheelsetFamily, generate_pass, shared_section  # noqa: E402
from src.inverse.variants import SharedSectionWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p2" / "shared_section_runs"
SPEEDS = {"fixed_100": (100.0, 100.0), "uniform_95_105": (95.0, 105.0), "uniform_60_110": (60.0, 110.0)}


def partial_dataset(sm, thb, rough, seed_key, rho, N=50, snr=40.0, speeds=(60.0, 110.0)):
    """Shared section with pass-to-pass coherence rho of the roughness Fourier coefficients."""
    rng = np.random.default_rng(np.random.SeedSequence(list(seed_key)))
    g = 10 ** (rng.normal(0, G_SD_DB, rough.n_sub) / 10)
    Vs = rng.uniform(*speeds, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    th = dict(thb, **TRUTH)
    Zc = shared_section(rng)["Z"]
    passes = []
    for V, W in zip(Vs, Ws):
        Zi = {"Z": rho * Zc + math.sqrt(1 - rho**2) * shared_section(rng)["Z"]}
        passes.append(generate_pass(H_single(sm, dict(th, W=float(W))), rough, g, V, thb["r0"], snr, rng, Z_shared=Zi))
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    return {"passes": passes, "Wm": Wm, "Ws": Ws, "g": g}


def dense_fisher(est: SharedSectionWhittle, phi, logg, lw, rho, h=1e-4) -> list[float]:
    """Exact Gaussian Fisher, Sigma_k = s (rho^2 h h^H + (1 - rho^2) diag|h|^2) + E, per spatial bin."""
    phi = np.asarray(phi, float)
    d, N = phi.size, len(est.P)
    tab0 = est.fam.table(est.theta(phi))
    Hm, dHw = est._Hmat(tab0, lw, deriv=True)
    dHt = []
    for a in range(d):
        e = np.eye(d)[a] * h
        Hp, _ = est._Hmat(est.fam.table(est.theta(phi + e)), lw)
        Hn, _ = est._Hmat(est.fam.table(est.theta(phi - e)), lw)
        dHt.append((Hp - Hn) / (2 * h))
    s = est.base_k * np.exp(logg[est.sub_k])
    used = np.unique(est.sub_k)
    smap = -np.ones(est.S, int)
    smap[used] = np.arange(used.size)
    n = d + used.size + N
    J = np.zeros((n, n))
    r2 = rho**2
    for kk in range(est.ks.size):
        pr = np.nonzero(est.present[kk])[0]
        hk = Hm[kk, pr]
        e = 1.0 / est.Einv[kk, pr]
        sk = s[kk]
        Sig = sk * (r2 * np.outer(hk, hk.conj()) + (1 - r2) * np.diag(np.abs(hk) ** 2)) + np.diag(e)
        Wi = np.linalg.inv(Sig)
        cols, mats = [], []

        def dsig(x):
            return sk * (r2 * (np.outer(x, hk.conj()) + np.outer(hk, x.conj())) + (1 - r2) * np.diag(2 * np.real(np.conj(hk) * x)))
        for a in range(d):
            cols.append(a)
            mats.append(dsig(dHt[a][kk, pr]))
        cols.append(d + smap[est.sub_k[kk]])
        mats.append(sk * (r2 * np.outer(hk, hk.conj()) + (1 - r2) * np.diag(np.abs(hk) ** 2)))
        for m, i in enumerate(pr):
            x = np.zeros(pr.size, complex)
            x[m] = dHw[kk, i]
            cols.append(d + used.size + i)
            mats.append(dsig(x))
        WD = np.einsum("ij,ajk->aik", Wi, np.array(mats))
        Ib = np.real(np.einsum("aij,bji->ab", WD, WD))
        J[np.ix_(cols, cols)] += Ib
    J[d + used.size:, d + used.size:] += np.eye(N) / est.sW**2
    sc = 1 / np.sqrt(np.diag(J))
    Ci = np.linalg.inv(J * np.outer(sc, sc)) * np.outer(sc, sc)
    return [float(math.sqrt(Ci[a, a])) for a in range(d)]


def bound():
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    rows = []
    with Timer() as tm:
        for sname, spd in SPEEDS.items():
            ds_i = make_dataset(sm, thb, rough, (88, 0), speeds=spd)
            ds_s = make_dataset(sm, thb, rough, (88, 0), speeds=spd, shared=True)
            ci = MultiPassWhittle(ds_i["passes"], ds_i["Ws"], WIM, rough, fam).expected_fisher(phi_true(), np.log(ds_i["g"]), np.log(ds_i["Ws"]))
            cs = SharedSectionWhittle(ds_s["passes"], ds_s["Ws"], WIM, rough, fam).expected_fisher(phi_true(), np.log(ds_s["g"]), np.log(ds_s["Ws"]))
            rows.append({"speeds": sname, "independent_crb": ci["crb_log"], "shared_crb": cs["crb_log"]})
            print(rows[-1], flush=True)
        ds = make_dataset(sm, thb, rough, (88, 0), speeds=SPEEDS["uniform_60_110"], shared=True)
        est = SharedSectionWhittle(ds["passes"], ds["Ws"], WIM, rough, fam)
        coh = [{"check": "rank-one form at rho=1", "crb": est.expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))["crb_log"]},
               {"check": "independent form at rho=0 (same bins)",
                "crb": MultiPassWhittle(ds["passes"], ds["Ws"], WIM, rough, fam).expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))["crb_log"]}]
        print(coh, flush=True)
        for rho in (1.0, 0.99, 0.9, 0.5, 0.0):
            c = dense_fisher(est, phi_true(), np.log(ds["g"]), np.log(ds["Ws"]), rho)
            coh.append({"rho": rho, "crb": c})
            print(coh[-1], flush=True)
    save_result("p2/shared_section_bound", {"speed_rows": rows, "coherence_rows_60_110": coh},
                cfg={"N": 50, "snr_db": 40, "wim_sigma": WIM, "truth": TRUTH,
                     "coherence_model": "Sigma = s (rho^2 h h^H + (1 - rho^2) diag|h|^2) + E"}, seed=88, wall_seconds=tm.seconds)


def mc(n_data, speeds, seed_base=20261012):
    sm, thb, rough, _ = setup()
    fam = SingleWheelsetFamily(sm, thb)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(f"shared_{s}", s, "shared") for s in speeds] + [(f"independent_{s}", s, "independent") for s in speeds] \
        + [("rho0.9_uniform_60_110", "uniform_60_110", "rho0.9")]
    for name, sname, kind in jobs:
        fp = RUN_DIR / f"{name}.jsonl"
        done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
        nd = n_data if kind != "rho0.9" else max(n_data // 2, 1)
        for j in range(nd):
            key = (seed_base, list(SPEEDS).index(sname), j)  # paired across shared / independent
            if tuple(key) in done:
                continue
            if kind == "rho0.9":
                ds = partial_dataset(sm, thb, rough, key, 0.9, speeds=SPEEDS[sname])
            else:
                ds = make_dataset(sm, thb, rough, key, speeds=SPEEDS[sname], shared=(kind == "shared"))
            cls = MultiPassWhittle if kind == "independent" else SharedSectionWhittle
            est = cls(ds["passes"], ds["Wm"], WIM, rough, fam)
            r = est.fit(phi_start())
            pi = est.profile_interval(0)
            crb = est.expected_fisher(phi_true(), np.log(ds["g"]), np.log(ds["Ws"]))
            lt = math.log(TRUTH["kB0"])
            row = {"job": name, "seed_key": list(key), "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])],
                   "se_log": r["se_log"], "crb_log": crb["crb_log"], "profile90_err": [pi["lo"] - lt, pi["hi"] - lt],
                   "converged": r["converged"], "wall_fit_s": r["wall_fit_s"], "s_per_eval": r["s_per_eval"]}
            with fp.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"{name} j={j} err={row['err_log'][0]:+.6f} se={r['se_log'][0]:.6f} crb={crb['crb_log'][0]:.6f} "
                  f"fit={r['wall_fit_s']:.0f}s", flush=True)


def aggregate():
    cells = []
    for fp in sorted(RUN_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
        s = summarise([r["err_log"][0] for r in rows], [r["se_log"][0] for r in rows], [r["crb_log"][0] for r in rows],
                      profile=([r["profile90_err"][0] for r in rows], [r["profile90_err"][1] for r in rows]))
        cB = summarise([r["err_log"][1] for r in rows], [r["se_log"][1] for r in rows], [r["crb_log"][1] for r in rows])
        cells.append({"job": fp.stem, "kB0": s, "cB": cB, "all_converged": all(r["converged"] for r in rows),
                      "fit_s_median": float(np.median([r["wall_fit_s"] for r in rows]))})
        print(json.dumps(cells[-1]), flush=True)
    save_result("p2/shared_section_mc", {"cells": cells}, cfg={"N": 50, "snr_db": 40, "truth": TRUTH, "wim_sigma": WIM},
                seed=20261012)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", action="store_true")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--n-data", type=int, default=20)
    ap.add_argument("--speeds", nargs="+", default=["fixed_100", "uniform_60_110"])
    a = ap.parse_args()
    if a.bound:
        bound()
    if a.mc:
        mc(a.n_data, a.speeds)
    if a.aggregate:
        aggregate()
