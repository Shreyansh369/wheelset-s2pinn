"""L1-lin structural model: stepped Timoshenko axle + rigid wheels + bearing supports + axleboxes.

Vertical plane only. Gyroscopic and rotating-damping terms of doc Eqs. (2)-(3)
are dropped (Omega / omega_1 << 1, checked in P1.6). Element: two-node
Timoshenko beam with interdependent interpolation (Friedman & Kosmatka 1993),
exact for static deflection and free of shear locking; consistent mass with
translational and rotary inertia. DOFs per node: (w, psi), psi = section rotation.

Global DOF layout: [w_0, psi_0, ..., w_{N-1}, psi_{N-1}, z_bL, z_bR].
Wheel nodes carry rigid wheels (translational mass on w, diametral inertia on psi);
their w is prescribed by quasi-static rigid contact (doc §15.2): w = z_c(t).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from src.reference.params import Params


def timoshenko_element(E: float, Gs: float, kappa: float, rho: float, A: float, I: float, L: float):
    """Stiffness and consistent mass of a 2-node Timoshenko element (DOFs w1, psi1, w2, psi2)."""
    phi = 12 * E * I / (kappa * Gs * A * L**2)
    c = E * I / ((1 + phi) * L**3)
    K = c * np.array([
        [12, 6 * L, -12, 6 * L],
        [6 * L, (4 + phi) * L**2, -6 * L, (2 - phi) * L**2],
        [-12, -6 * L, 12, -6 * L],
        [6 * L, (2 - phi) * L**2, -6 * L, (4 + phi) * L**2],
    ])
    p2 = phi**2
    m = rho * A * L / (1 + phi) ** 2
    a = 13 / 35 + 7 * phi / 10 + p2 / 3
    b = (11 / 210 + 11 * phi / 120 + p2 / 24) * L
    cc = 9 / 70 + 3 * phi / 10 + p2 / 6
    d = (13 / 420 + 3 * phi / 40 + p2 / 24) * L
    e = (1 / 105 + phi / 60 + p2 / 120) * L**2
    f = (1 / 140 + phi / 60 + p2 / 120) * L**2
    Mt = m * np.array([[a, b, cc, -d], [b, e, d, -f], [cc, d, a, -b], [-d, -f, -b, e]])
    r = rho * I / ((1 + phi) ** 2 * L)
    g = (1 / 10 - phi / 2) * L
    h = (2 / 15 + phi / 6 + p2 / 3) * L**2
    k = (1 / 30 + phi / 6 - p2 / 6) * L**2
    Mr = r * np.array([[6 / 5, g, -6 / 5, g], [g, h, -g, -k], [-6 / 5, -g, 6 / 5, -g], [g, -k, -g, h]])
    return K, Mt + Mr


def section_props(d: float) -> tuple[float, float]:
    return math.pi * d**2 / 4, math.pi * d**4 / 64


@dataclass
class Mesh:
    x: np.ndarray            # node coordinates
    d: np.ndarray            # element diameters
    wheel_nodes: tuple[int, int]
    journal_nodes: tuple[int, int]


def build_mesh(p: Params, n_elements: int | None = None) -> Mesh:
    a = p.v["axle"]
    n_el = int(n_elements or a["n_elements"])
    half = a["length"] / 2
    bounds = [0.0] + [s[0] for s in a["sections"]]
    if abs(bounds[-1] - half) > 1e-9:
        raise ValueError("last section must end at the axle end")
    key = sorted(set(bounds + [a["wheel_xi"], a["journal_xi"]]))
    # distribute elements over the half axle proportional to segment length (>= 1 each)
    seg = np.diff(key)
    n_half = max(len(seg), n_el // 2)
    counts = np.maximum(1, np.round(seg / seg.sum() * n_half).astype(int))
    while counts.sum() > n_half:
        counts[np.argmax(counts)] -= 1
    while counts.sum() < n_half:
        counts[np.argmax(seg / counts)] += 1
    xs = [0.0]
    for x0, x1, c in zip(key[:-1], key[1:], counts):
        xs += list(np.linspace(x0, x1, c + 1)[1:])
    xr = np.array(xs)
    x = np.concatenate([-xr[::-1], xr[1:]])
    mid = 0.5 * (x[1:] + x[:-1])
    d = np.empty(mid.size)
    for i, xm in enumerate(np.abs(mid)):
        for outer, dia in a["sections"]:
            if xm <= outer + 1e-12:
                d[i] = dia
                break
    find = lambda xv: int(np.argmin(np.abs(x - xv)))
    return Mesh(x=x, d=d, wheel_nodes=(find(-a["wheel_xi"]), find(a["wheel_xi"])),
                journal_nodes=(find(-a["journal_xi"]), find(a["journal_xi"])))


def assemble_beam(mesh: Mesh, p: Params, uniform_d: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    m = p.v["material"]
    n = 2 * mesh.x.size
    K = np.zeros((n, n))
    M = np.zeros((n, n))
    for e in range(mesh.x.size - 1):
        A, I = section_props(uniform_d if uniform_d is not None else mesh.d[e])
        ke, me = timoshenko_element(m["E"], m["Gs"], m["kappa"], m["rho"], A, I, mesh.x[e + 1] - mesh.x[e])
        idx = slice(2 * e, 2 * e + 4)
        K[idx, idx] += ke
        M[idx, idx] += me
    return K, M


@dataclass
class Matrices:
    M: np.ndarray
    C: np.ndarray
    K: np.ndarray
    free: np.ndarray        # indices of free DOFs
    presc: np.ndarray       # indices of prescribed DOFs (wheel w), order (left, right)
    axlebox: tuple[int, int]
    mesh: Mesh


class L1LinModel:
    """Assembles M, C, K for given health parameters (kB0, cB) and axle load W."""

    def __init__(self, p: Params, n_elements: int | None = None):
        self.p = p
        self.mesh = build_mesh(p, n_elements)
        Kb, Mb = assemble_beam(self.mesh, p)
        a = p.v["axle"]
        beta = 2 * a["damping_zeta"] / (2 * math.pi * a["damping_fref"])
        nb = Kb.shape[0]
        self.n = nb + 2
        self.ib = (nb, nb + 1)
        self.K0 = np.zeros((self.n, self.n))
        self.M0 = np.zeros((self.n, self.n))
        self.C0 = np.zeros((self.n, self.n))
        self.K0[:nb, :nb] = Kb
        self.M0[:nb, :nb] = Mb
        self.C0[:nb, :nb] = beta * Kb
        w = p.v["wheel"]
        for j in self.mesh.wheel_nodes:
            self.M0[2 * j, 2 * j] += w["mass"]
            self.M0[2 * j + 1, 2 * j + 1] += w["diametral_inertia"]
        mb = p.v["axlebox"]["mass"]
        kp, cp = p.v["primary"]["kp"], p.v["primary"]["cp"]
        for ib in self.ib:
            self.M0[ib, ib] += mb
            self.K0[ib, ib] += kp
            self.C0[ib, ib] += cp
        self.rail = p.v["rail_sdof"]["enabled"]
        if self.rail:
            r = p.v["rail_sdof"]
            for j in self.mesh.wheel_nodes:  # rail moves with the wheel minus the prescribed offset
                self.M0[2 * j, 2 * j] += r["m_r"]
                self.K0[2 * j, 2 * j] += r["k_r"]
                self.C0[2 * j, 2 * j] += r["c_r"]
        if p.v["bearing"]["support_law"] != "linear":
            raise NotImplementedError("non-smooth support laws are time-domain only and not implemented yet")
        presc = [] if self.rail else [2 * j for j in self.mesh.wheel_nodes]
        self.presc = np.array(presc, int)
        self.free = np.array([i for i in range(self.n) if i not in set(presc)], int)

    def matrices(self, kB0: float, cB: float, W: float, load_exp: float | None = None,
                 clearance_growth_um: float = 0.0) -> Matrices:
        kB = self.p.kB(kB0, W, load_exp=load_exp, clearance_growth_um=clearance_growth_um)
        K, C = self.K0.copy(), self.C0.copy()
        for jn, ib in zip(self.mesh.journal_nodes, self.ib):
            iw = 2 * jn
            for (r, c), s in (((iw, iw), 1), ((ib, ib), 1), ((iw, ib), -1), ((ib, iw), -1)):
                K[r, c] += s * kB
                C[r, c] += s * cB
        return Matrices(self.M0, C, K, self.free, self.presc, self.ib, self.mesh)

    def wheel_w_dofs(self) -> np.ndarray:
        return np.array([2 * j for j in self.mesh.wheel_nodes], int)
