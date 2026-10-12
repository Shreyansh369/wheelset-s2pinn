"""Exact natural frequencies of a uniform free-free Timoshenko beam (verification target, G1a).

Harmonic solutions W(x) e^{i w t}, Psi(x) e^{i w t} of
    kGA (W'' - Psi') + rho A w^2 W = 0,
    EI Psi'' + kGA (W' - Psi) + rho I w^2 Psi = 0
with W ~ e^{lam x} give the characteristic polynomial
    kGA EI lam^4 + w^2 (kGA rho I + rho A EI) lam^2 + rho A w^2 (rho I w^2 - kGA) = 0.
Below the cut-off frequency sqrt(kGA / (rho I)) the roots are lam^2 = alpha^2 > 0 and
lam^2 = -beta^2 < 0. In the real basis {cosh ax, sinh ax, cos bx, sin bx} the
rotation follows as Psi = {r_a sinh, r_a cosh, q_b sin, -q_b cos} with
r_a = (kGA a^2 + rho A w^2)/(kGA a) and q_b = (rho A w^2 - kGA b^2)/(kGA b).
Free ends: bending moment EI Psi' = 0 and shear kGA (W' - Psi) = 0 at x = 0, L.
The frequencies are the roots of the 4x4 determinant (the Timoshenko frequency equation).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


def _det(w: float, E: float, Gs: float, kappa: float, rho: float, A: float, I: float, L: float) -> float:
    kGA, EI = kappa * Gs * A, E * I
    a4 = kGA * EI
    a2 = w**2 * (kGA * rho * I + rho * A * EI)
    a0 = rho * A * w**2 * (rho * I * w**2 - kGA)
    disc = math.sqrt(a2**2 - 4 * a4 * a0)
    s1 = (-a2 + disc) / (2 * a4)  # > 0 below cut-off
    s2 = (-a2 - disc) / (2 * a4)  # < 0
    if s1 <= 0:
        raise ValueError("above cut-off frequency")
    al, be = math.sqrt(s1), math.sqrt(-s2)
    ra = (kGA * al**2 + rho * A * w**2) / (kGA * al)
    qb = (rho * A * w**2 - kGA * be**2) / (kGA * be)

    def rows(x: float) -> np.ndarray:
        ch, sh, c, s = math.cosh(al * x), math.sinh(al * x), math.cos(be * x), math.sin(be * x)
        # W and W' for the four basis functions
        W1 = np.array([al * sh, al * ch, -be * s, be * c])
        Psi = np.array([ra * sh, ra * ch, qb * s, -qb * c])
        dPsi = np.array([ra * al * ch, ra * al * sh, qb * be * c, qb * be * s])
        return np.vstack([dPsi, W1 - Psi])

    Mx = np.vstack([rows(0.0), rows(L)])
    # scale columns so cosh/sinh growth does not swamp the determinant's sign changes
    Mx = Mx / np.maximum(np.abs(Mx).max(axis=0), 1e-300)
    return float(np.linalg.det(Mx))


def timoshenko_freefree_freqs(E: float, Gs: float, kappa: float, rho: float, A: float, I: float, L: float,
                              n_modes: int = 4, w_max: float | None = None, n_scan: int = 20000) -> np.ndarray:
    """First ``n_modes`` non-zero natural frequencies (rad/s) by sign-change scan + Brent."""
    w_cut = math.sqrt(kappa * Gs * A / (rho * I))
    w_hi = min(w_max or 0.999 * w_cut, 0.999 * w_cut)
    grid = np.linspace(w_hi * 1e-4, w_hi, n_scan)
    vals = np.array([_det(w, E, Gs, kappa, rho, A, I, L) for w in grid])
    roots = []
    for i in range(len(grid) - 1):
        if np.sign(vals[i]) != np.sign(vals[i + 1]) and np.isfinite(vals[i]) and np.isfinite(vals[i + 1]):
            r = brentq(_det, grid[i], grid[i + 1], args=(E, Gs, kappa, rho, A, I, L), xtol=1e-12, rtol=1e-14)
            # reject poles of the scaled determinant: |det| must be small at a true root
            if abs(_det(r, E, Gs, kappa, rho, A, I, L)) < 1e-6:
                roots.append(r)
        if len(roots) >= n_modes:
            break
    return np.array(roots)


def euler_bernoulli_freefree(E: float, rho: float, A: float, I: float, L: float, n_modes: int = 4) -> np.ndarray:
    """Euler-Bernoulli limit: cos(bL) cosh(bL) = 1."""
    f = lambda x: math.cos(x) * math.cosh(x) - 1
    roots, x = [], 1.0
    while len(roots) < n_modes:
        if f(x) * f(x + 0.01) < 0:
            roots.append(brentq(f, x, x + 0.01))
        x += 0.01
    bL = np.array(roots)
    return (bL / L) ** 2 * math.sqrt(E * I / (rho * A))
