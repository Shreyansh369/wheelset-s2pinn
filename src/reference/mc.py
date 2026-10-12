"""Monte Carlo reference datasets on L1-lin (ground truth for Phases 2-4).

Inputs in standard coordinates: u = (u_kB, u_cB, u_W) ~ U(-1, 1)^3 and zeta_2 ~ N(0, I_14).
Health: kB0 = kB0_nom e^{h u_kB}, cB = cB_nom e^{h u_cB} (log-uniform, h = prior half-width);
payload W uniform on [W_min, W_max]. Per sample the unit-contact responses at the 7 forcing
frequencies are solved once; amplitudes then follow by linearity.
"""

from __future__ import annotations

import time

import numpy as np

from src.reference.frequency_domain import ForcingMap, unit_responses
from src.reference.params import Params
from src.reference.timoshenko_fe import L1LinModel


def sample_inputs(n: int, n_vars: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, size=(n, 3)), rng.standard_normal((n, n_vars))


def run_mc(p: Params, n: int, seed: int, model: L1LinModel | None = None) -> dict:
    mdl = model or L1LinModel(p)
    fm = ForcingMap(p)
    u, zeta = sample_inputs(n, fm.n_vars, seed)
    kB0, cB = p.theta_from_u(u[:, 0], u[:, 1])
    W = p.W_from_u(u[:, 2])
    wnodes = np.arange(0, 2 * mdl.mesh.x.size, 2)
    ib = mdl.ib[0]
    acc_unit = np.empty((n, fm.omegas.size), complex)
    w_unit = np.empty((n, fm.omegas.size, wnodes.size), np.complex64)
    t0 = time.perf_counter()
    for i in range(n):
        Xh = unit_responses(mdl, fm, kB0[i], cB[i], W[i])
        acc_unit[i] = -(fm.omegas**2) * Xh[:, ib]
        w_unit[i] = Xh[:, wnodes]
    solve_s = time.perf_counter() - t0
    Z = fm.amplitudes(zeta)  # [n, n_w]
    return {
        "u": u, "zeta": zeta, "kB0": kB0, "cB": cB, "W": W, "omegas": fm.omegas, "var_names": fm.names,
        "acc_unit": acc_unit, "acc": Z * acc_unit, "w_unit": w_unit, "x_nodes": mdl.mesh.x,
        "seconds_per_sample": solve_s / n,
    }
