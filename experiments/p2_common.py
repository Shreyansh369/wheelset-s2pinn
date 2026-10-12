"""Shared data generation and fitting for the Phase 2 experiments (single FE wheelset, scenario a/iv).

Reference model: the FE wheelset with linearised Hertz contact and rail oscillator
(src/analysis/bound_scan.ScenarioModel), direct solves on a 0.25 Hz grid. Estimator family: the
exact complex-modal version of the same model (src/inverse/multipass.SingleWheelsetFamily).
Truth kB0 = 0.85e9, cB = 6e3; start (1e9, 5e3); payload uniform 5.5-22.5 t, 3% WIM;
roughness ISO 3095 shape with K = 16 sub-band levels drawn with 3 dB deviations.
"""

from __future__ import annotations

import math

import numpy as np

from experiments.p1_fe_direct import G_SD_DB, START, TRUTH, WIM, W_RANGE, Z90, cp_interval, setup  # noqa: F401
from src.inverse.multipass import generate_pass, shared_section

KMH = 1 / 3.6
FG = np.arange(44.0, 701.0, 0.25)
SEEDS = (42, 123, 456, 789, 1024)


def H_single(sm, th: dict):
    Hg = sm.axlebox_accel_per_unit_input(th, 2 * np.pi * FG)
    return lambda f: np.interp(f, FG, Hg.real) + 1j * np.interp(f, FG, Hg.imag)


def wheel_roughness(rough, r0: float, delta_db: float, rng, n_max: int = 400) -> dict:
    """Periodic wheel roughness: ISO 3095 limit shape + delta_db (assumption, not a sourced level).

    Order n has wavenumber n / r0; a periodic profile with one-sided wavenumber PSD G has
    E|w_n|^2 = 2 G(n / r0) (1 / r0) (order spacing 1 / r0 in rad/m). One draw per wheel (dataset),
    the same on every pass.
    """
    n = np.arange(1, n_max + 1)
    Om = n / r0
    G = np.zeros(n.size)
    ok = (Om >= rough.om_lo) & (Om < rough.om_hi)
    G[ok] = rough.density(Om[ok])
    var = 2 * G / r0 * 10 ** (delta_db / 10)
    return {"orders": n, "w": np.sqrt(var / 2) * (rng.standard_normal(n.size) + 1j * rng.standard_normal(n.size))}


def make_dataset(sm, thb, rough, seed_key, N=50, snr=40.0, speeds=(60.0, 110.0), shared=False,
                 wheel_delta_db=None, g_sd=G_SD_DB):
    rng = np.random.default_rng(np.random.SeedSequence(list(seed_key)))
    g = 10 ** (rng.normal(0, g_sd, rough.n_sub) / 10)
    Vs = rng.uniform(*speeds, N) * KMH
    Ws = rng.uniform(*W_RANGE, N)
    th = dict(thb, **TRUTH)
    Zs = shared_section(rng) if shared else None
    wl = wheel_roughness(rough, thb["r0"], wheel_delta_db, rng) if wheel_delta_db is not None else None
    passes = [generate_pass(H_single(sm, dict(th, W=float(W))), rough, g, V, thb["r0"], snr, rng,
                            Z_shared=Zs, wheel_lines=wl) for V, W in zip(Vs, Ws)]
    Wm = Ws * np.exp(WIM * rng.standard_normal(N))
    return {"passes": passes, "Wm": Wm, "Ws": Ws, "g": g, "Vs": Vs, "wheel": wl}


def phi_start():
    return np.log([START["kB0"], START["cB"]])


def phi_true():
    return np.log([TRUTH["kB0"], TRUTH["cB"]])


def summarise(errs, ses, crbs, profile=None) -> dict:
    e, se, crb = np.asarray(errs), np.asarray(ses), np.asarray(crbs)
    rel = np.exp(e) - 1
    k = int(np.sum(np.abs(e) <= Z90 * se))
    out = {"n": int(e.size), "bias_rel": float(rel.mean()),
           "bias_rel_se": float(rel.std(ddof=1) / math.sqrt(e.size)) if e.size > 1 else None,
           "rmse_rel": float(np.sqrt(np.mean(e**2))), "crb_rel": float(np.sqrt(np.mean(crb**2))),
           "rmse_over_crb": float(np.sqrt(np.mean(e**2)) / np.sqrt(np.mean(crb**2))),
           "coverage90_wald": k / e.size, "coverage90_wald_ci95": cp_interval(k, e.size)}
    if profile is not None:
        lo, hi = np.asarray(profile[0]), np.asarray(profile[1])
        kp = int(np.sum((lo <= e) & (hi >= e)))
        out.update({"coverage90_profile": kp / e.size, "coverage90_profile_ci95": cp_interval(kp, e.size)})
    return out
