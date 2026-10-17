"""P0.4: residual-induced damping bias of PINNs on SDOF and 2-DOF oscillators.

Two settings, each with a prediction that uses the *measured* unresolved residual:

Transient (free decay). Derivation in docs/derivations/eq41.md: if the trained
network is a damped sinusoid with decay rate lambda plus an unresolved part
whose residual has mean square R^2 times that of the sinusoid, the window loss
is J(lambda) = [|p(s)|^2 + R^2] g(lambda), with p(s) = s^2 + 2 zeta w s + w^2,
s = -lambda + i w_d and g = (1 - exp(-2 lambda T)) / (2 lambda). For T -> inf,
dJ/dlambda = 0 gives Eq. (41) with a dimensionally consistent lambda_0 = zeta w:
lambda*^2 = lambda_0^2 + (R / 2w)^2.

Steady state (forced). The analogous loss over complex amplitude X is
|A X - F|^2 + R^2 |X|^2, minimised by the ridge solution
X* = (A^H A + R^2 I)^{-1} A^H F, which is a different law from Eq. (41).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from scipy.optimize import least_squares

# ----------------------------------------------------------------------------
# systems
# ----------------------------------------------------------------------------


@dataclass
class LinearSystem:
    M: np.ndarray
    C: np.ndarray
    K: np.ndarray

    @property
    def n(self) -> int:
        return self.M.shape[0]

    def modes(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Natural frequencies, modal damping ratios and mass-normalised modes."""
        from scipy.linalg import eigh

        w2, Phi = eigh(self.K, self.M)
        w = np.sqrt(w2)
        zeta = np.diag(Phi.T @ self.C @ Phi) / (2 * w)
        return w, zeta, Phi


def sdof(omega: float, zeta: float) -> LinearSystem:
    return LinearSystem(np.array([[1.0]]), np.array([[2 * zeta * omega]]), np.array([[omega**2]]))


def two_dof(omega1: float, omega2: float, zeta: float) -> LinearSystem:
    """Chain m1-k1-m2-k2 (unit masses) tuned to w1, w2, with Rayleigh damping zeta on both modes."""
    # K = [[k1+k2, -k2], [-k2, k2]] with unit masses: trace = k1 + 2 k2, det = k1 k2
    tr, det = omega1**2 + omega2**2, omega1**2 * omega2**2
    # k1 + 2 k2 = tr, k1 k2 = det -> 2 k2^2 - tr k2 + det = 0
    k2 = (tr + math.sqrt(tr**2 - 8 * det)) / 4
    k1 = det / k2
    M = np.eye(2)
    K = np.array([[k1 + k2, -k2], [-k2, k2]])
    alpha = 2 * zeta * omega1 * omega2 / (omega1 + omega2)
    beta = 2 * zeta / (omega1 + omega2)
    return LinearSystem(M, alpha * M + beta * K, K)


# ----------------------------------------------------------------------------
# predictions
# ----------------------------------------------------------------------------


def window_loss(lam: float, lam0: float, wd: float, R: float, T: float) -> float:
    d = lam - lam0
    p2 = d**2 * (d**2 + 4 * wd**2)  # |p(s)|^2 for s = -lam + i wd, exact
    g = (1 - math.exp(-2 * lam * T)) / (2 * lam) if lam * T > 1e-12 else T
    return (p2 + R**2) * g


def predict_lambda_window(lam0: float, wd: float, R: float, T: float) -> float:
    """Minimiser of the finite-window loss over lambda > 0 (bounded scalar search)."""
    from scipy.optimize import minimize_scalar

    hi = lam0 + R / wd + 5.0 / T + 1.0
    res = minimize_scalar(window_loss, bounds=(1e-9, hi), args=(lam0, wd, R, T), method="bounded",
                          options={"xatol": 1e-12})
    return float(res.x)


def predict_lambda_eq41(lam0: float, omega: float, R: float) -> float:
    return math.sqrt(lam0**2 + (R / (2 * omega)) ** 2)


def ridge_amplitude(sys_: LinearSystem, Omega: float, F: np.ndarray, R: float) -> np.ndarray:
    A = sys_.K - Omega**2 * sys_.M + 1j * Omega * sys_.C
    AH = A.conj().T
    return np.linalg.solve(AH @ A + R**2 * np.eye(sys_.n), AH @ F)


# ----------------------------------------------------------------------------
# PINN
# ----------------------------------------------------------------------------


class TimeMLP(nn.Module):
    """x(t) for t in [0, T]; tanh MLP on t/T scaled to [-1, 1]."""

    def __init__(self, n_out: int, width: int, depth: int, T: float):
        super().__init__()
        layers: list[nn.Module] = [nn.Linear(1, width), nn.Tanh()]
        for _ in range(depth - 1):
            layers += [nn.Linear(width, width), nn.Tanh()]
        layers.append(nn.Linear(width, n_out))
        self.net = nn.Sequential(*layers)
        self.T = T

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        return self.net(2 * t / self.T - 1)


class FourierTimeModel(nn.Module):
    """S2-PINN's time branch as a stand-alone model: x(t) = [1, cos(w_k tau), sin(w_k tau)] @ W.

    tau = t / T, learnable w_k = exp(theta_k) initialised log-uniform in [0, log(2 pi K)]
    exactly as in third_party/s2pinn/src/spinn/models/bases.py::TimeBasis.
    """

    def __init__(self, n_out: int, n_freq: int, T: float):
        super().__init__()
        self.T = T
        self.log_omega = nn.Parameter(torch.empty(n_freq).uniform_(0.0, math.log(2 * math.pi * n_freq)))
        self.W = nn.Parameter(0.1 * torch.randn(1 + 2 * n_freq, n_out))

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        ph = (t / self.T) * torch.exp(self.log_omega)[None, :]
        feats = torch.cat([torch.ones_like(t), torch.cos(ph), torch.sin(ph)], 1)
        return feats @ self.W


def derivatives(model: nn.Module, t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    t = t.detach().requires_grad_(True)
    x = model(t)
    xs_t, xs_tt = [], []
    for j in range(x.shape[1]):
        g = torch.autograd.grad(x[:, j].sum(), t, create_graph=True)[0]
        gg = torch.autograd.grad(g.sum(), t, create_graph=True)[0]
        xs_t.append(g)
        xs_tt.append(gg)
    return x, torch.cat(xs_t, 1), torch.cat(xs_tt, 1)


def residual(sys_t: dict, x, xt, xtt, f=None):
    r = xtt @ sys_t["M"].T + xt @ sys_t["C"].T + x @ sys_t["K"].T
    return r if f is None else r - f


def _sys_tensors(sys_: LinearSystem) -> dict:
    return {k: torch.tensor(getattr(sys_, k), dtype=torch.float64) for k in ("M", "C", "K")}


@dataclass
class TrainConfig:
    width: int
    depth: int = 3
    steps: int = 5000
    lr: float = 1e-3
    n_colloc: int = 1024
    w_ic: float = 100.0


def train_transient(sys_: LinearSystem, x0: np.ndarray, v0: np.ndarray, T: float, cfg: TrainConfig, seed: int) -> TimeMLP:
    torch.manual_seed(seed)
    model = TimeMLP(sys_.n, cfg.width, cfg.depth, T).double()
    st = _sys_tensors(sys_)
    x0_t, v0_t = torch.tensor(x0)[None], torch.tensor(v0)[None]
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    gen = torch.Generator().manual_seed(seed + 10_000)
    t0 = torch.zeros(1, 1, dtype=torch.float64)
    for _ in range(cfg.steps):
        t = T * torch.rand(cfg.n_colloc, 1, generator=gen, dtype=torch.float64)
        x, xt, xtt = derivatives(model, t)
        loss_r = residual(st, x, xt, xtt).pow(2).mean()
        xi, xit, _ = derivatives(model, t0)
        loss_ic = (xi - x0_t).pow(2).sum() + (xit - v0_t).pow(2).sum()
        loss = loss_r + cfg.w_ic * loss_ic
        opt.zero_grad()
        loss.backward()
        opt.step()
    return model


def train_forced(sys_: LinearSystem, F: np.ndarray, Omega: float, n_periods: int, cfg: TrainConfig, seed: int,
                 w_per: float = 10.0, arch: str = "mlp") -> nn.Module:
    """Steady state under f(t) = F cos(Omega t) on one window with periodicity penalties.

    arch="mlp": tanh MLP of width cfg.width; arch="fourier": S2-PINN learnable-frequency
    time basis with K = cfg.width frequency pairs.
    """
    torch.manual_seed(seed)
    T = n_periods * 2 * math.pi / Omega
    if arch == "mlp":
        model = TimeMLP(sys_.n, cfg.width, cfg.depth, T).double()
    elif arch == "fourier":
        model = FourierTimeModel(sys_.n, cfg.width, T).double()
    else:
        raise ValueError(arch)
    st = _sys_tensors(sys_)
    F_t = torch.tensor(F)[None]
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    gen = torch.Generator().manual_seed(seed + 10_000)
    ends = torch.tensor([[0.0], [T]], dtype=torch.float64)
    for _ in range(cfg.steps):
        t = T * torch.rand(cfg.n_colloc, 1, generator=gen, dtype=torch.float64)
        x, xt, xtt = derivatives(model, t)
        f = torch.cos(Omega * t) * F_t
        loss_r = residual(st, x, xt, xtt, f).pow(2).mean()
        xe, xet, _ = derivatives(model, ends)
        loss_p = (xe[0] - xe[1]).pow(2).sum() + (xet[0] - xet[1]).pow(2).sum()
        loss = loss_r + w_per * loss_p
        opt.zero_grad()
        loss.backward()
        opt.step()
    return model


# ----------------------------------------------------------------------------
# measurement
# ----------------------------------------------------------------------------


def damped_sinusoid(p: np.ndarray, t: np.ndarray) -> np.ndarray:
    A, lam, wd, phi = p
    return A * np.exp(-lam * t) * np.cos(wd * t + phi)


def fit_damped_sinusoid(t: np.ndarray, y: np.ndarray, lam_init: float, wd_init: float) -> np.ndarray:
    A0 = float(np.max(np.abs(y[: max(5, len(y) // 50)])))
    best = None
    for phi0 in (0.0, math.pi / 2, math.pi, -math.pi / 2):
        res = least_squares(lambda p: damped_sinusoid(p, t) - y, x0=[A0, lam_init, wd_init, phi0],
                            bounds=([-np.inf, -10.0, 0.5 * wd_init, -10.0], [np.inf, 10.0 * max(wd_init, 1.0), 1.5 * wd_init, 10.0]),
                            x_scale="jac")
        if best is None or res.cost < best.cost:
            best = res
    return best.x


def pole_residual(p: np.ndarray, t: np.ndarray, w: float, zeta: float) -> np.ndarray:
    """L[x_fit] for x_fit = A e^{-lam t} cos(wd t + phi) under q'' + 2 zeta w q' + w^2 q."""
    A, lam, wd, phi = p
    s = -lam + 1j * wd
    ps = s**2 + 2 * zeta * w * s + w**2
    return np.real(ps * A * np.exp(1j * phi) * np.exp(s * t))


def measure_transient(model: TimeMLP, sys_: LinearSystem, T: float, n_grid: int = 4001) -> list[dict]:
    """Per mode: fitted decay rate, unresolved residual floor R, and both predictions."""
    w, zeta, Phi = sys_.modes()
    t = torch.linspace(0, T, n_grid, dtype=torch.float64)[:, None]
    x, xt, xtt = derivatives(model, t)
    r = residual(_sys_tensors(sys_), x, xt, xtt).detach().numpy()  # [N, n]
    x = x.detach().numpy()
    tt = t[:, 0].numpy()
    q = x @ (sys_.M @ Phi)  # modal coordinates (mass-normalised modes)
    rq = r @ Phi  # modal residuals: q'' + 2 zeta w q' + w^2 q
    out = []
    for k in range(sys_.n):
        lam0 = zeta[k] * w[k]
        wd = w[k] * math.sqrt(1 - zeta[k] ** 2)
        p = fit_damped_sinusoid(tt, q[:, k], lam0, wd)
        xfit = damped_sinusoid(p, tt)
        r_floor = rq[:, k] - pole_residual(p, tt, w[k], zeta[k])
        R = math.sqrt(np.mean(r_floor**2) / np.mean(xfit**2))
        R_total = math.sqrt(np.mean(rq[:, k] ** 2) / np.mean(xfit**2))
        fit_rel_err = math.sqrt(np.mean((q[:, k] - xfit) ** 2) / np.mean(xfit**2))
        out.append({
            "mode": k, "omega": float(w[k]), "zeta": float(zeta[k]), "lambda0": lam0,
            "lambda_meas": float(p[1]), "wd_meas": float(p[2]), "R_floor": R, "R_total": R_total, "fit_rel_err": fit_rel_err,
            "lambda_pred_window": predict_lambda_window(lam0, wd, R, T),
            "lambda_pred_eq41": predict_lambda_eq41(lam0, w[k], R),
        })
    return out


def harmonic_amplitude(t: np.ndarray, y: np.ndarray, Omega: float) -> tuple[complex, np.ndarray]:
    """LS fit y ~ Re[X e^{i Omega t}]; returns X and the fitted signal."""
    B = np.stack([np.cos(Omega * t), -np.sin(Omega * t)], 1)
    c, *_ = np.linalg.lstsq(B, y, rcond=None)
    return complex(c[0], c[1]), B @ c


def measure_forced(model: nn.Module, sys_: LinearSystem, F: np.ndarray, Omega: float, n_periods: int,
                   n_grid: int = 2001) -> dict:
    T = n_periods * 2 * math.pi / Omega
    t = torch.linspace(0, T, n_grid, dtype=torch.float64)[:, None]
    x, xt, xtt = derivatives(model, t)
    f = torch.cos(Omega * t) * torch.tensor(F)[None]
    r = residual(_sys_tensors(sys_), x, xt, xtt, f).detach().numpy()
    x = x.detach().numpy()
    tt = t[:, 0].numpy()
    X = np.empty(sys_.n, complex)
    xh = np.empty_like(x)
    for j in range(sys_.n):
        X[j], xh[:, j] = harmonic_amplitude(tt, x[:, j], Omega)
    A = sys_.K - Omega**2 * sys_.M + 1j * Omega * sys_.C
    r_harm = np.real(np.outer(np.exp(1j * Omega * tt), A @ X - F))  # residual of the harmonic part
    r_floor = r - r_harm
    R = math.sqrt(np.sum(np.mean(r_floor**2, 0)) / np.sum(np.mean(xh**2, 0)))
    return {"Omega": Omega, "X": X, "R_floor": R}


def fit_sdof_frf(Omegas: np.ndarray, X: np.ndarray, wn0: float, zeta0: float) -> dict:
    """Fit X(W) = g / (wn^2 - W^2 + 2 i zeta wn W) with complex g to complex data."""
    def resid(p):
        wn, z, gr, gi = p
        model = (gr + 1j * gi) / (wn**2 - Omegas**2 + 2j * z * wn * Omegas)
        e = model - X
        return np.concatenate([e.real, e.imag]) / np.max(np.abs(X))

    g0 = X[np.argmax(np.abs(X))] * 2j * zeta0 * wn0**2
    res = least_squares(resid, x0=[wn0, zeta0, g0.real, g0.imag], bounds=([0.5 * wn0, 1e-6, -np.inf, -np.inf], [1.5 * wn0, 1.0, np.inf, np.inf]))
    wn, z, gr, gi = res.x
    return {"wn": float(wn), "zeta": float(z), "decay_rate": float(z * wn), "gain": complex(gr, gi), "fit_cost": float(res.cost)}
