"""Instrumented FE wheelset coupled to other wheelsets through an infinite rail (task (a)).

Each rail carries N wheels at positions d_k (CT23 layout or config). Roughness is the same profile
under every wheel, shifted by d_k, and the same on both rails (left/right symmetric, as in the
scenario-(a) model), so each rail is solved separately with symmetric wheelset loading:

  wheel receptance A^w_kk = left-wheel displacement per unit force pair at both wheel seats of
  wheelset k (FE wheelset, no contact): the instrumented wheelset uses (kB0, cB) under test, the
  others the nominal bearing (healthy); every wheelset carries the same payload W;
  contact receptance 1/k_H(W), k_H = kH0 (W/W0)^(1/3);
  rail receptance A^r_jk = R(|d_j - d_k|) (src/reference/track.py).
  Left-axlebox acceleration of the instrumented wheelset j per unit roughness:
      H(f; V) = -w^2 Hca_j(w) sum_k M_jk(w) exp(i w (d_k - d_j) / V),  M = (A^c + A^r + A^w)^-1,
  with Hca_j the axlebox displacement per unit force pair. The cross terms are kept.

``MultiWheelFamily`` is the estimator's version (exact complex-modal wheelset receptances at payload
nodes, splined in log W); ``reference_H`` is the generator's (direct FE solves, then exact phases).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg import eig

from src.inverse.multipass import Family, Table
from src.reference.track import RailTrack, coupled_rows, rail_matrix, receptance_timoshenko

NEIGHBOUR = {"kB0": 1.0e9, "cB": 5.0e3}


class MultiWheelModel:
    def __init__(self, sm, track: RailTrack, layout, j_inst: int, kH0: float = 1.4e9, neighbour: dict | None = None,
                 receptance=receptance_timoshenko):
        self.sm, self.track = sm, track
        self.layout = np.asarray(layout, float)
        self.j = int(j_inst)
        self.d = self.layout - self.layout[self.j]
        self.kH0 = kH0
        self.W0 = sm.p.v["payload"]["W0"]
        self.neigh = dict(NEIGHBOUR if neighbour is None else neighbour)
        self.recept = receptance
        self.wdofs = list(sm.wheels)
        self._R = {}

    def kH(self, th: dict) -> float:
        return th.get("kH0", self.kH0) * (th["W"] / self.W0) ** (1 / 3)

    def force_pattern(self, n: int) -> np.ndarray:
        f = np.zeros(n)
        f[self.wdofs] = 1.0
        return f

    def wheelset_direct(self, th: dict, omegas: np.ndarray):
        """(Hw, Hca) by direct solves: wheel-seat and left-axlebox displacement per unit force pair."""
        M, C, K = self.sm.wheelset_matrices(th)
        f = self.force_pattern(M.shape[0]).astype(complex)
        Hw, Hca = np.empty(omegas.size, complex), np.empty(omegas.size, complex)
        for i, w in enumerate(omegas):
            X = np.linalg.solve(K - w**2 * M + 1j * w * C, f)
            Hw[i], Hca[i] = X[self.wdofs[0]], X[self.sm.ibL]
        return Hw, Hca

    def wheelset_modal(self, th: dict, omegas: np.ndarray):
        """Same as wheelset_direct by exact complex-modal summation (all modes)."""
        M, C, K = self.sm.wheelset_matrices(th)
        n = M.shape[0]
        Mi = np.linalg.inv(M)
        A = np.block([[np.zeros((n, n)), np.eye(n)], [-Mi @ K, -Mi @ C]])
        b = np.concatenate([np.zeros(n), Mi @ self.force_pattern(n)])
        lam, VL, VR = eig(A, left=True, right=True)
        num = (VL.conj().T @ b) / np.einsum("ij,ij->j", VL.conj(), VR)
        den = 1.0 / (1j * omegas[:, None] - lam[None, :])
        return den @ (VR[self.wdofs[0], :] * num), den @ (VR[self.sm.ibL, :] * num)

    def rail(self, omegas: np.ndarray) -> np.ndarray:
        key = (omegas.size, float(omegas[0]), float(omegas[-1]))
        if key not in self._R:
            self._R[key] = rail_matrix(omegas, self.layout, self.track, self.recept)
        return self._R[key]

    def components(self, th: dict, omegas: np.ndarray, method: str = "direct", neigh_Hw=None) -> np.ndarray:
        """G[w, k] = -w^2 Hca_j M_jk; H(f; V) = sum_k G_k exp(i w d_k / V)."""
        ws = self.wheelset_direct if method == "direct" else self.wheelset_modal
        Hw_i, Hca_i = ws(th, omegas)
        N = self.layout.size
        if N > 1 and neigh_Hw is None:
            neigh_Hw, _ = ws(dict(th, **self.neigh), omegas)
        Aw = np.empty((omegas.size, N), complex)
        for k in range(N):
            Aw[:, k] = Hw_i if k == self.j else neigh_Hw
        rows = coupled_rows(Aw, self.kH(th), self.rail(omegas), self.layout, self.j)
        return -(omegas**2)[:, None] * Hca_i[:, None] * rows

    def reference_H(self, th: dict, V: float, f_grid: np.ndarray):
        """Generator transfer function for one pass: callable f -> H, smooth part on f_grid, exact phases."""
        G = self.components(th, 2 * np.pi * f_grid, "direct")

        def H(f):
            out = np.zeros(np.size(f), complex)
            for k in range(G.shape[1]):
                g = np.interp(f, f_grid, G[:, k].real) + 1j * np.interp(f, f_grid, G[:, k].imag)
                out += g * np.exp(1j * 2 * np.pi * f * self.d[k] / V)
            return out
        return H


class MultiWheelFamily(Family):
    """Estimator family for the rail-coupled model (exact modal wheelset receptances at payload nodes)."""

    def __init__(self, mw: MultiWheelModel, fixed: dict, names=("kB0", "cB"), W_nodes=None, f_grid=None):
        self.mw, self.fixed, self.names = mw, dict(fixed), tuple(names)
        self.W_nodes = np.exp(np.linspace(math.log(5.0), math.log(24.0), 25)) if W_nodes is None else W_nodes
        self.f = np.arange(45.0, 702.0, 0.5) if f_grid is None else f_grid
        self.w = 2 * np.pi * self.f
        self._neigh = {}

    def table(self, theta: dict) -> Table:
        N = self.mw.layout.size
        G = np.empty((self.W_nodes.size, self.f.size, N), complex)
        for i, W in enumerate(self.W_nodes):
            th = dict(self.fixed, **theta, W=float(W))
            if N > 1 and i not in self._neigh:
                self._neigh[i] = self.mw.wheelset_modal(dict(th, **self.mw.neigh), self.w)[0]
            G[i] = self.mw.components(th, self.w, "modal", neigh_Hw=self._neigh.get(i))
        return Table(np.log(self.W_nodes), self.f, G, self.mw.d.copy())
