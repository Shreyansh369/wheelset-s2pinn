"""Option (iv): speed diversity + narrowband roughness forcing. kB0 Cramer-Rao bound (exploratory).

Model (scenario a): kB0 = 1e9 N/m, linearised Hertz contact (k_H0 = 1.4e9 N/m at W0, ~W^(1/3)) +
rail oscillator, observation = left-axlebox acceleration, band 50-700 Hz, fs = 2 kHz.

Roughness is defined in the wavelength domain: a one-sided wavenumber PSD G(Omega) that is smooth
within each one-third-octave band (log-log interpolation of the ISO 3095:2013 Fig. 2 limit between
band centres) times a free level g_b per band (with optional Gaussian prior of 2 or 4 dB, 1 sigma).
Each pass at speed V_i maps wavenumber to frequency f = V Omega / (2 pi). The record is
20 wheel revolutions, T_i = 20 * 2 pi r0 / V_i, and the forcing is resolved into DFT bins of width
1/T_i; each bin is an independent complex Gaussian amplitude c ~ CN(0, v) with
v = |H(w; theta, W_i)|^2 * 2 G(Omega) dOmega (+ LS noise), dOmega = 2 pi df / V_i.
Speed is known per pass; payload is measured per pass with 3% (1 sigma) WIM error, and each pass's
true log W is a nuisance removed by a Schur complement. Unknowns: log kB0 (target), log cB, log g_b.

Also computed: the old discrete case (one line per band, at band centres) at fixed speed, to
separate discretisation from speed diversity. Writes results/p1/bound_speed.json. Single-threaded.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_bound_robustness import ISO3095_FIG2_DB, ISO_SOURCE  # noqa: E402
from src.analysis.bound_scan import Scenario, ScenarioModel  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

F_LO, F_HI, FS, N_REVS, WIM = 50.0, 700.0, 2000.0, 20, 0.03
KMH = 1 / 3.6
W_GRID = np.linspace(5.5, 22.5, 6)
BANDS = np.array(sorted(ISO3095_FIG2_DB))  # band-centre wavelengths (m), ascending
LEVEL_DB = np.array([ISO3095_FIG2_DB[l] for l in BANDS])
OM_C = 2 * np.pi / BANDS  # band-centre wavenumbers (descending with BANDS ascending)
EDGE = 2 ** (1 / 6)


def band_index(Om: np.ndarray) -> np.ndarray:
    """Index into BANDS of the one-third-octave band containing wavenumber Om (-1 if none)."""
    idx = np.full(Om.shape, -1)
    for b, oc in enumerate(OM_C):
        idx[(Om >= oc / EDGE) & (Om < oc * EDGE)] = b
    return idx


def iso_density(Om: np.ndarray) -> np.ndarray:
    """Smooth wavenumber PSD (m^2 per rad/m) whose band integrals match the ISO band levels."""
    rms2 = 1e-12 * 10 ** (LEVEL_DB / 10)
    dens_c = rms2 / (OM_C * (EDGE - 1 / EDGE))
    o = np.argsort(OM_C)
    return np.exp(np.interp(np.log(Om), np.log(OM_C[o]), np.log(dens_c[o])))


def transfer_grid(sm: ScenarioModel, th: dict, f: np.ndarray, h: float = 1e-4) -> dict:
    out = {"f": f}
    for Wv in W_GRID:
        t = dict(th, W=float(Wv))
        w = 2 * np.pi * f
        H = sm.axlebox_accel_per_unit_input(t, w)
        d = {}
        for nm in ("kB0", "cB", "W"):
            u = dict(t); u[nm] *= math.exp(h)
            dd = dict(t); dd[nm] *= math.exp(-h)
            d[nm] = (sm.axlebox_accel_per_unit_input(u, w) - sm.axlebox_accel_per_unit_input(dd, w)) / (2 * h)
        out[float(Wv)] = {"H": H, "d": d}
    return out


def interp_c(fq: np.ndarray, f: np.ndarray, z: np.ndarray) -> np.ndarray:
    return np.interp(fq, f, z.real) + 1j * np.interp(fq, f, z.imag)


def pass_fisher(TG: dict, V: float, W: float, r0: float, snr_db: float, mode: str) -> tuple[np.ndarray, np.ndarray]:
    """Per-pass Fisher over [log kB0, log cB, log g_1..g_B, log W]; mode 'narrowband' or 'discrete'."""
    T = N_REVS * 2 * np.pi * r0 / V
    df = 1 / T
    if mode == "narrowband":
        fk = np.arange(math.ceil(F_LO / df), math.floor(F_HI / df) + 1) * df
        Om = 2 * np.pi * fk / V
        b = band_index(Om)
        keep = b >= 0
        fk, Om, b = fk[keep], Om[keep], b[keep]
        zvar = 2 * iso_density(Om) * (2 * np.pi * df / V)  # E|Z|^2 per bin
    else:  # one line per band at the band centre (old scan)
        fk = V * OM_C / (2 * np.pi)
        keep = (fk >= F_LO) & (fk <= F_HI)
        fk, b = fk[keep], np.where(keep)[0]
        zvar = 2 * 1e-12 * 10 ** (LEVEL_DB[keep] / 10)
    G = TG[W]
    H = interp_c(fk, TG["f"], G["H"])
    dH = {k: interp_c(fk, TG["f"], v) for k, v in G["d"].items()}
    sig = np.abs(H) ** 2 * zvar
    n_samp = int(T * FS)
    e = 4 * (0.5 * sig.sum()) / 10 ** (snr_db / 10) / n_samp
    v = sig + e
    nb = len(BANDS)
    P = 2 + nb + 1
    D = np.zeros((fk.size, P))
    D[:, 0] = 2 * np.real(np.conj(H) * dH["kB0"]) * zvar / v
    D[:, 1] = 2 * np.real(np.conj(H) * dH["cB"]) * zvar / v
    D[np.arange(fk.size), 2 + b] = sig / v
    D[:, -1] = 2 * np.real(np.conj(H) * dH["W"]) * zvar / v
    return D.T @ D, np.unique(b)


def speed_samples(dist: tuple, n: int) -> np.ndarray:
    lo, hi = dist
    q = (np.arange(n) + 0.5) / n  # stratified quantiles of a uniform distribution
    return (lo + (hi - lo) * q) * KMH


def bound(TG, r0, dist, n_passes, snr_db, prior_db, mode) -> dict:
    Vs = speed_samples(dist, n_passes)
    Ws = W_GRID[(np.arange(n_passes) * 5) % len(W_GRID)]  # spread payload evenly, decorrelated from V
    nb = len(BANDS)
    Jg = np.zeros((2 + nb, 2 + nb))
    seen = set()
    for V, W in zip(Vs, Ws):
        J, bs = pass_fisher(TG, V, float(W), r0, snr_db, mode)
        seen.update(bs.tolist())
        g = J.shape[0] - 1
        Jg += J[:g, :g] - np.outer(J[:g, g], J[:g, g]) / (J[g, g] + 1 / WIM**2)
    idx = [0, 1] + [2 + b for b in sorted(seen)]
    Jr = Jg[np.ix_(idx, idx)]
    if prior_db is not None:
        s = prior_db * math.log(10) / 10
        Jr[2:, 2:] += np.eye(len(idx) - 2) / s**2
    d = 1 / np.sqrt(np.maximum(np.diag(Jr), 1e-300))
    lam, Vv = np.linalg.eigh(Jr * np.outer(d, d))
    good = lam > 1e-10
    bad = (Vv[:, ~good] ** 2).sum(1)[0] if (~good).any() else 0.0
    crb = float("inf") if bad > 1e-6 else float(d[0] * np.sqrt((Vv[0, good] ** 2 / lam[good]).sum()))
    return {"crb_rel_kB0": crb, "n_bands_seen": len(seen), "speed_std_kmh": float(np.std(Vs) / KMH)}


def main() -> None:
    p = load_params()
    th = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": p.r0}
    sc = Scenario(name="a_iv", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=F_HI, fs=FS, forcing_spec={},
                  targets=["log_kB0"], kH0=1.4e9)
    sm = ScenarioModel(p, sc)
    f = np.arange(F_LO - 1, F_HI + 1.25, 0.25)
    with Timer() as tm:
        TG = transfer_grid(sm, th, f)
        rows = []
        dists = {"fixed_100": (100.0, 100.0), "uniform_95_105": (95.0, 105.0), "uniform_80_110": (80.0, 110.0),
                 "uniform_60_110": (60.0, 110.0)}
        for mode in ("discrete", "narrowband"):
            for dname, dist in dists.items():
                if mode == "discrete" and dname != "fixed_100":
                    continue
                for n in (50, 200):
                    for snr in (20.0, 40.0):
                        for prior in (None, 4.0, 2.0):
                            r = bound(TG, p.r0, dist, n, snr, prior, mode)
                            rows.append({"mode": mode, "speed_dist": dname, "N": n, "snr_db": snr,
                                         "band_prior_db": prior, **r})
                            print(rows[-1], flush=True)
    save_result("p1/bound_speed", {"rows": rows}, cfg={
        "band_hz": [F_LO, F_HI], "fs": FS, "n_revs": N_REVS, "wim_sigma": WIM, "W_grid_t": W_GRID.tolist(),
        "roughness_source": ISO_SOURCE, "kH0": 1.4e9, "kB0": 1e9, "cB": 5e3,
        "freq_grid_step_hz": 0.25, "speed_sampling": "stratified quantiles of uniform distribution"},
        wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
