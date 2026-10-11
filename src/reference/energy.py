"""Energy-balance residual, doc Eq. (28), in windowed integral form (G1b).

With E_m = 1/2 qd^T M qd + 1/2 q^T K q over all DOFs, the equations of motion imply
    E_m(t1) - E_m(t0) = int_t0^t1 [ P_in - qd^T C qd ] dt,
where P_in is the power of the external generalised forces only: the contact
reaction at prescribed wheel DOFs (rigid track), or the rail-oscillator forcing
on the wheel DOFs (rail_sdof). The free-DOF equations do not enter P_in, so the
residual measures how well the solution satisfies them. The integral form needs
no common period, so it holds for incommensurate forcing frequencies.
"""

from __future__ import annotations

import numpy as np


def _gauss_grid(t0: float, t1: float, n_panels: int, n_nodes: int = 8) -> tuple[np.ndarray, np.ndarray]:
    g, w = np.polynomial.legendre.leggauss(n_nodes)
    e = np.linspace(t0, t1, n_panels + 1)
    h = 0.5 * np.diff(e)
    mid = 0.5 * (e[1:] + e[:-1])
    return (mid[:, None] + h[:, None] * g).ravel(), (h[:, None] * w).ravel()


def external_power(model, mats, q, qd, qdd, z, zd, zdd) -> np.ndarray:
    """P_in(t) for arrays q, qd, qdd [T, n] and contact z, zd, zdd [T]."""
    if model.rail:
        r = model.p.v["rail_sdof"]
        F = r["k_r"] * z + r["c_r"] * zd + r["m_r"] * zdd  # [T], same at both wheels
        return F * qd[:, model.wheel_w_dofs()].sum(1)
    res = qdd @ mats.M.T + qd @ mats.C.T + q @ mats.K.T  # full residual, [T, n]
    pz = mats.presc
    return np.sum(qd[:, pz] * res[:, pz], axis=1)


def energy(mats, q, qd) -> np.ndarray:
    return 0.5 * np.einsum("ti,ij,tj->t", qd, mats.M, qd) + 0.5 * np.einsum("ti,ij,tj->t", q, mats.K, q)


def energy_residual_window(model, sol, t0: float, t1: float, n_panels: int = 400) -> dict:
    """Relative residual of the integral energy balance for a HarmonicSolution."""
    m = sol.mats
    tg, wg = _gauss_grid(t0, t1, n_panels)
    q, qd, qdd = sol.q(tg), sol.qd(tg), sol.qdd(tg)
    z, zd, zdd = sol.z(tg, 0), sol.z(tg, 1), sol.z(tg, 2)
    p_in = external_power(model, m, q, qd, qdd, z, zd, zdd)
    p_diss = np.einsum("ti,ij,tj->t", qd, m.C, qd)
    te = np.array([t0, t1])
    E = energy(m, sol.q(te), sol.qd(te))
    E_scale = max(np.max(energy(m, q, qd)), np.max(E))
    lhs = E[1] - E[0]
    rhs = float(np.sum(wg * (p_in - p_diss)))
    return {"dE": float(lhs), "int_power": rhs, "E_max": float(E_scale), "rel_residual": abs(lhs - rhs) / E_scale,
            "int_P_in": float(np.sum(wg * p_in)), "int_P_diss": float(np.sum(wg * p_diss))}
