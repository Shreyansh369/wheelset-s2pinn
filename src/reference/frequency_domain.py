"""Exact steady-state response of L1-lin by frequency-domain solve.

All forcing sits at discrete frequencies (wheel orders n f_r, track wavenumbers
times V) and the model is linear, so the steady state is a finite harmonic sum:

    q(t) = sum_w Re[ Q(w) e^{i w t} ],   Q(w) = Z(w) Xhat(w),

with Z(w) = sum_{j at w} zeta_j scale_j phase_j the complex contact-displacement
amplitude (the same at both wheels) and Xhat(w) the response to unit contact
amplitude, from (K - w^2 M + i w C)_ff X_f = -(K - w^2 M + i w C)_fp X_p.
The response is exactly linear in zeta_2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.reference.params import Params
from src.reference.timoshenko_fe import L1LinModel, Matrices


def dynamic_stiffness(m: Matrices, w: float) -> np.ndarray:
    return m.K - w**2 * m.M + 1j * w * m.C


def unit_response(model: L1LinModel, m: Matrices, w: float) -> np.ndarray:
    """Full complex DOF vector for unit contact amplitude at both wheels."""
    D = dynamic_stiffness(m, w)
    X = np.zeros(model.n, complex)
    if model.rail:
        r = model.p.v["rail_sdof"]
        F = np.zeros(model.n, complex)
        for j in model.wheel_w_dofs():
            F[j] = r["k_r"] + 1j * w * r["c_r"] - w**2 * r["m_r"]
        return np.linalg.solve(D, F)
    f, pz = m.free, m.presc
    X[pz] = 1.0
    X[f] = np.linalg.solve(D[np.ix_(f, f)], -D[np.ix_(f, pz)] @ X[pz])
    return X


class ForcingMap:
    """Maps the ordered forcing variables zeta_2 onto the unique forcing frequencies."""

    def __init__(self, p: Params):
        self.vars = p.forcing_variables()
        om = np.array([v["omega"] for v in self.vars])
        self.omegas, self.index = np.unique(np.round(om, 10), return_inverse=True)
        self.coef = np.array([v["scale"] * v["phase"] for v in self.vars])  # complex
        self.names = [v["name"] for v in self.vars]

    @property
    def n_vars(self) -> int:
        return len(self.vars)

    def amplitudes(self, zeta: np.ndarray) -> np.ndarray:
        """Complex contact amplitude Z(w) per unique frequency; zeta: [..., n_vars] -> [..., n_w]."""
        zeta = np.asarray(zeta, float)
        out = np.zeros(zeta.shape[:-1] + (self.omegas.size,), complex)
        for j in range(self.n_vars):
            out[..., self.index[j]] += zeta[..., j] * self.coef[j]
        return out


def unit_responses(model: L1LinModel, fmap: ForcingMap, kB0: float, cB: float, W: float) -> np.ndarray:
    """Xhat[w, dof] for each unique forcing frequency."""
    m = model.matrices(kB0, cB, W)
    return np.stack([unit_response(model, m, w) for w in fmap.omegas])


@dataclass
class HarmonicSolution:
    omegas: np.ndarray       # [n_w]
    Q: np.ndarray            # [n_w, n_dof] complex DOF amplitudes
    Z: np.ndarray            # [n_w] complex contact amplitudes
    mats: Matrices

    def _eval(self, t: np.ndarray, order: int) -> np.ndarray:
        t = np.atleast_1d(t)
        ph = np.exp(1j * np.outer(t, self.omegas)) * (1j * self.omegas) ** order  # [T, n_w]
        return np.real(ph @ self.Q)  # [T, n_dof]

    def q(self, t):
        return self._eval(t, 0)

    def qd(self, t):
        return self._eval(t, 1)

    def qdd(self, t):
        return self._eval(t, 2)

    def z(self, t, order: int = 0) -> np.ndarray:
        t = np.atleast_1d(t)
        return np.real(np.exp(1j * np.outer(t, self.omegas)) * (1j * self.omegas) ** order @ self.Z)


def harmonic_solution(model: L1LinModel, fmap: ForcingMap, kB0: float, cB: float, W: float,
                      zeta: np.ndarray) -> HarmonicSolution:
    Xh = unit_responses(model, fmap, kB0, cB, W)
    Z = fmap.amplitudes(zeta)
    return HarmonicSolution(fmap.omegas, Z[:, None] * Xh, Z, model.matrices(kB0, cB, W))
