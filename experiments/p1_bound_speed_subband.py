"""Option (iv), fair version: roughness free at sub-band resolution; does speed diversity separate it?

Same physics and narrowband observation model as experiments/p1_bound_speed.py, but the roughness
wavenumber PSD has an unknown level in each of K sub-bands per one-third octave (K = 1 ... 256;
K = 256 is about one DFT bin per sub-band at 100 km/h). Within a sub-band the PSD follows the smooth
ISO 3095 shape. At a single speed, a roughness feature at wavenumber Omega always lands at the same
frequency, so as K grows its level becomes inseparable from |H(f)|^2. Across speeds the same
Omega lands at f = V Omega / 2 pi, while the support resonance stays put.

Parameters: log kB0 (target), log cB, one log level per sub-band seen (optional independent prior,
dB 1-sigma), and each pass's log W (measured, 3% WIM prior). The full Fisher matrix is assembled
with its block structure (sub-band block diagonal) and solved directly. Writes
results/p1/bound_speed_subband.json. Single-threaded.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.linalg import LinAlgError, cho_factor, cho_solve  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_bound_speed import (  # noqa: E402
    EDGE, F_HI, F_LO, FS, KMH, N_REVS, OM_C, W_GRID, WIM, interp_c, iso_density, speed_samples, transfer_grid,
)
from experiments.p1_bound_robustness import ISO_SOURCE  # noqa: E402
from src.analysis.bound_scan import Scenario, ScenarioModel  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

OM_LO = OM_C.min() / EDGE  # lower edge of the longest-wavelength band
OM_HI = OM_C.max() * EDGE


def subband(Om: np.ndarray, K: int) -> np.ndarray:
    width = math.log(EDGE**2) / K  # log-width of a sub-band
    s = np.floor(np.log(Om / OM_LO) / width).astype(int)
    s[(Om < OM_LO) | (Om >= OM_HI)] = -1
    return s


def crb(TG, r0, dist, n_passes, snr_db, K, prior_db, payload: str = "spread") -> dict:
    Vs = speed_samples(dist, n_passes)
    if payload == "spread":
        Ws = W_GRID[(np.arange(n_passes) * 5) % len(W_GRID)]
    else:  # every pass at the same (loaded) payload: removes payload diversity
        Ws = np.full(n_passes, W_GRID[-1])
    per = []
    for V, W in zip(Vs, Ws):
        T = N_REVS * 2 * np.pi * r0 / V
        df = 1 / T
        fk = np.arange(math.ceil(F_LO / df), math.floor(F_HI / df) + 1) * df
        Om = 2 * np.pi * fk / V
        s = subband(Om, K)
        keep = s >= 0
        fk, Om, s = fk[keep], Om[keep], s[keep]
        zvar = 2 * iso_density(Om) * (2 * np.pi * df / V)
        G = TG[float(W)]
        H = interp_c(fk, TG["f"], G["H"])
        dH = {k: interp_c(fk, TG["f"], v) for k, v in G["d"].items()}
        sig = np.abs(H) ** 2 * zvar
        e = 4 * (0.5 * sig.sum()) / 10 ** (snr_db / 10) / int(T * FS)
        v = sig + e
        dg = np.stack([2 * np.real(np.conj(H) * dH["kB0"]) * zvar / v,
                       2 * np.real(np.conj(H) * dH["cB"]) * zvar / v], 1)
        ds = sig / v
        dw = 2 * np.real(np.conj(H) * dH["W"]) * zvar / v
        per.append((dg, s, ds, dw))
    used = np.unique(np.concatenate([p[1] for p in per]))
    smap = {int(x): i for i, x in enumerate(used)}
    S, N = used.size, n_passes
    n = 2 + S + N
    J = np.zeros((n, n))
    for i, (dg, s, ds, dw) in enumerate(per):
        si = 2 + np.array([smap[int(x)] for x in s])
        wi = 2 + S + i
        J[:2, :2] += dg.T @ dg
        np.add.at(J, (np.zeros_like(si), si), dg[:, 0] * ds)
        np.add.at(J, (np.ones_like(si), si), dg[:, 1] * ds)
        np.add.at(J, (si, si), ds * ds)
        J[:2, wi] += dg.T @ dw
        np.add.at(J, (si, np.full_like(si, wi)), ds * dw)
        J[wi, wi] += dw @ dw + 1 / WIM**2
    iu = np.triu_indices(n, 1)
    J[(iu[1], iu[0])] = J[iu]  # symmetrise from the upper triangle
    if prior_db is not None:
        sl = prior_db * math.log(10) / 10
        J[2:2 + S, 2:2 + S] += np.eye(S) / sl**2
    d = 1 / np.sqrt(np.maximum(np.diag(J), 1e-300))
    Js = J * np.outer(d, d)
    try:
        c = cho_factor(Js + 1e-12 * np.eye(n), lower=True)
        x = cho_solve(c, np.eye(n)[:, 0])
        val = float(d[0] * math.sqrt(max(x[0], 0)))
        if not np.isfinite(val) or val > 1e3:
            val = float("inf")
    except LinAlgError:
        val = float("inf")
    return {"crb_rel_kB0": val, "n_subbands": int(S), "speed_std_kmh": float(np.std(Vs) / KMH)}


def main() -> None:
    p = load_params()
    th = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": p.r0}
    sm = ScenarioModel(p, Scenario(name="a_iv", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=F_HI, fs=FS,
                                   forcing_spec={}, targets=["log_kB0"], kH0=1.4e9))
    f = np.arange(F_LO - 1, F_HI + 1.25, 0.25)
    dists = {"fixed_100": (100.0, 100.0), "uniform_95_105": (95.0, 105.0), "uniform_80_110": (80.0, 110.0),
             "uniform_60_110": (60.0, 110.0)}
    rows = []
    with Timer() as tm:
        TG = transfer_grid(sm, th, f)
        for K in (16, 256):  # attribution: payload diversity removed
            for dname, dist in dists.items():
                for prior in (None, 2.0):
                    r = crb(TG, p.r0, dist, 50, 20.0, K, prior, payload="constant")
                    rows.append({"K_per_third_octave": K, "speed_dist": dname, "N": 50, "snr_db": 20.0,
                                 "subband_prior_db": prior, "payload": "constant_22.5t", **r})
                    print(rows[-1], flush=True)
        for K in (1, 4, 16, 64, 256):
            for dname, dist in dists.items():
                for N in (50, 200):
                    for snr in (20.0, 40.0):
                        for prior in (None, 4.0, 2.0):
                            r = crb(TG, p.r0, dist, N, snr, K, prior)
                            rows.append({"K_per_third_octave": K, "speed_dist": dname, "N": N, "snr_db": snr,
                                         "subband_prior_db": prior, "payload": "spread_5.5-22.5t", **r})
                            print(rows[-1], flush=True)
    save_result("p1/bound_speed_subband", {"rows": rows}, cfg={
        "band_hz": [F_LO, F_HI], "fs": FS, "n_revs": N_REVS, "wim_sigma": WIM, "roughness_source": ISO_SOURCE,
        "K_values": [1, 4, 16, 64, 256], "note": "roughness level free per sub-band; within a sub-band ISO shape"},
        wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
