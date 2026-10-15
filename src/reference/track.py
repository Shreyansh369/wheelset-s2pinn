"""Infinite rail on a continuous viscoelastic foundation, and multi-wheel coupling through the rail.

Rail receptance (displacement at distance x per unit harmonic point force, exp(i w t) convention):

* ``receptance_timoshenko``: derived here. Timoshenko beam (EI, kappa G A, rho A, rho I) on a
  Winkler foundation of complex stiffness per unit length beta = k_f (1 + i eta_f):
      kGA (w'' - psi') - beta w + rho A w^2 w = -F delta(x),   EI psi'' + kGA (w' - psi) + rho I w^2 psi = 0.
  In wavenumber k, W(k) = N(s) / P(s) with s = k^2, N(s) = EI s + kGA - rho I w^2 and
  P(s) = EI kGA s^2 - [kGA rho I w^2 + EI (rho A w^2 - beta)] s + (beta - rho A w^2)(kGA - rho I w^2).
  Partial fractions in s and (1/2pi) int exp(ikx) / (k^2 - s_m) dk = i exp(i q_m |x|) / (2 q_m)
  (Im q_m > 0) give the closed form. Verified against numerical inverse transforms (tests).
* ``receptance_ct_eq11``: transcription of Carrigan & Talbot (2023, MSSP 192, 110232) Eq. (11).
* ``receptance_euler``: Euler-Bernoulli beam on the same foundation, C&T Eq. (10).

Multi-wheel coupling (C&T 2023, Eqs. 5 and 8): N wheels on one rail at positions d_k, each a
wheel receptance A^w_kk, contact receptance 1/k_H, rail receptance matrix A^r_jk = R(|d_j - d_k|).
Contact forces F = (A^c + A^r + A^w)^-1 Z with Z_k = Z exp(i w d_k / V) (roughness under wheel k is
the profile shifted by d_k; wheels ordered along the direction of travel). Unlike C&T Eq. (6), the
cross terms are kept: at 20-revolution records the bin width (about 0.5 Hz) resolves the
V / (d_k - d_j) ripples.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RailTrack:
    E: float          # Pa
    G: float          # Pa
    kappa: float      # Timoshenko shear coefficient
    rho: float        # kg/m^3
    A: float          # m^2
    I: float          # m^4
    kf: float         # foundation stiffness per unit length, N/m^2
    eta_f: float      # foundation hysteretic loss factor
    source: str = ""

    def beta(self, omega=None):
        return self.kf * (1 + 1j * self.eta_f)


def receptance_timoshenko(omega: np.ndarray, x: np.ndarray, t: RailTrack) -> np.ndarray:
    """R[omega, x]; omega (rad/s) shape (nw,), x (m) shape (nx,) >= 0."""
    w = np.asarray(omega, float)[:, None]
    x = np.abs(np.asarray(x, float))[None, :]
    kGA, EI, rA, rI = t.kappa * t.G * t.A, t.E * t.I, t.rho * t.A, t.rho * t.I
    beta = t.beta(omega)
    beta = beta[:, None] if np.ndim(beta) else beta
    a2 = EI * kGA
    a1 = -(kGA * rI * w**2 + EI * (rA * w**2 - beta))
    a0 = (beta - rA * w**2) * (kGA - rI * w**2)
    disc = np.sqrt(a1**2 - 4 * a2 * a0 + 0j)
    s1, s2 = (-a1 + disc) / (2 * a2), (-a1 - disc) / (2 * a2)
    out = 0
    for sm, so in ((s1, s2), (s2, s1)):
        c = (EI * sm + kGA - rI * w**2) / (a2 * (sm - so))
        q = np.sqrt(sm + 0j)
        q = np.where(q.imag < 0, -q, q)
        out = out + c * 1j * np.exp(1j * q * x) / (2 * q)
    return out


def receptance_euler(omega: np.ndarray, x: np.ndarray, t: RailTrack) -> np.ndarray:
    """C&T Eq. (10): -(exp(-Gamma|x|) + i exp(-i Gamma|x|)) / (4 EI Gamma^3), Gamma in the 4th quadrant."""
    w = np.asarray(omega, float)[:, None]
    x = np.abs(np.asarray(x, float))[None, :]
    beta = t.beta(omega)
    beta = beta[:, None] if np.ndim(beta) else beta
    g4 = (t.rho * t.A * w**2 - beta) / (t.E * t.I)
    roots = (g4 ** 0.25)[..., None] * np.exp(1j * np.pi / 2 * np.arange(4))
    # choose the root with positive real and negative imaginary part ("fourth quadrant")
    ok = (roots.real > 0) & (roots.imag <= 0)
    G = np.where(ok.any(-1), (roots * ok).sum(-1), roots[..., 0])
    return -(np.exp(-G * x) + 1j * np.exp(-1j * G * x)) / (4 * t.E * t.I * G**3)


def receptance_ct_eq11(omega: np.ndarray, x: np.ndarray, t: RailTrack) -> np.ndarray:
    """Transcription of C&T Eq. (11) (Timoshenko beam on elastic foundation)."""
    w = np.asarray(omega, float)[:, None]
    x = np.abs(np.asarray(x, float))[None, :]
    E, G, k, rho, A, I = t.E, t.G, t.kappa, t.rho, t.A, t.I
    beta = t.beta(omega)
    beta = beta[:, None] if np.ndim(beta) else beta
    Om2 = w**2 * rho * A / beta
    R = 4 * E * A**2 * (Om2 - 1) / (I * beta) + (E * (1 - Om2) / (k * G) + Om2) ** 2
    sq = np.sqrt(R + 0j)
    l1 = beta / (2 * k * G * A) * (1 - Om2 + k * G * (-Om2 + sq) / E)
    l2 = beta / (2 * k * G * A) * (1 - Om2 + k * G * (-Om2 - sq) / E)
    r1, r2 = np.sqrt(l1 + 0j), np.sqrt(l2 + 0j)
    r1 = np.where(r1.real < 0, -r1, r1)
    r2 = np.where(r2.real < 0, -r2, r2)
    q = (k * G * A - w**2 * rho * I) / (E * I)
    return (np.exp(-x * r1) / r1 * (l1 - q) - np.exp(-x * r2) / r2 * (l2 - q)) / (2 * k * G * A * (l1 - l2))


def receptance_numeric(omega: float, x: float, t: RailTrack, kmax: float = 400.0, nk: int = 400001) -> complex:
    """Brute-force inverse Fourier transform of the Timoshenko-on-foundation dynamic stiffness (tests)."""
    k = np.linspace(-kmax, kmax, nk)
    kGA, EI, rA, rI = t.kappa * t.G * t.A, t.E * t.I, t.rho * t.A, t.rho * t.I
    beta = t.beta(omega)
    D = kGA * k**2 - (kGA * k) ** 2 / (EI * k**2 + kGA - rI * omega**2) - rA * omega**2 + beta
    return complex(np.trapezoid(np.exp(1j * k * x) / D, k) / (2 * np.pi))


# --------------------------------------------------------------------------- multi-wheel coupling
def coupled_rows(Aw: np.ndarray, kH: np.ndarray | float, R: np.ndarray, layout: np.ndarray, j: int) -> np.ndarray:
    """Row j of M = (A^c + A^r + A^w)^-1 for every frequency.

    Aw: (nw, N) wheel receptances; kH: contact stiffness (scalar or (nw,)); R: callable-free
    precomputed rail receptance matrix (nw, N, N). Returns (nw, N) complex.
    """
    nw, N = Aw.shape
    Ac = (1.0 / np.broadcast_to(np.asarray(kH, complex), (nw,)))[:, None, None] * np.eye(N)[None]
    Mtot = Ac + R + Aw[:, :, None] * np.eye(N)[None]
    e = np.zeros((nw, N), complex)
    e[:, j] = 1.0
    # row j of the inverse = solve(Mtot^T, e_j)
    return np.linalg.solve(np.transpose(Mtot, (0, 2, 1)), e[:, :, None])[:, :, 0]


def rail_matrix(omega: np.ndarray, layout: np.ndarray, track: RailTrack, receptance=receptance_timoshenko) -> np.ndarray:
    """A^r[omega, j, k] = R(|d_j - d_k|)."""
    d = np.asarray(layout, float)
    dist = np.abs(d[:, None] - d[None, :])
    u, inv = np.unique(np.round(dist, 9), return_inverse=True)
    Ru = receptance(omega, u, track)
    return Ru[:, inv.reshape(dist.shape)]


# --------------------------------------------------------------------------- config
def load_track_config(path=None) -> dict:
    """config/track.yaml with numeric strings (YAML 1.1 '207.0e9') converted to floats."""
    from pathlib import Path

    import yaml

    from src.reference.params import CONFIG_DIR, _num
    path = CONFIG_DIR / "track.yaml" if path is None else Path(path)
    raw = yaml.safe_load(path.read_text())

    def conv(node):
        if isinstance(node, dict):
            return {k: (_num(v["value"]) if isinstance(v, dict) and "value" in v else conv(v)) for k, v in node.items()}
        return node
    return conv(raw)


def make_track(rail: str = "BS113A", kf: float | None = None, eta_f: float | None = None, cfg: dict | None = None) -> RailTrack:
    """RailTrack from config: rail 'BS113A' (CT23 Table 1) or '60E1' (E, G, rho from BS113A entry)."""
    cfg = load_track_config() if cfg is None else cfg
    b = cfg["rail_BS113A"]
    r = dict(b)
    if rail == "60E1":
        r.update({k: v for k, v in cfg["rail_60E1"].items()})
    f = cfg["foundation"]
    return RailTrack(E=r["E"], G=r["G"], kappa=r["kappa"], rho=r["rho"], A=r["A"], I=r["I"],
                     kf=f["standard_kf_lab"] if kf is None else kf, eta_f=f["eta_f"] if eta_f is None else eta_f,
                     source=f"config/track.yaml rail_{rail}")
