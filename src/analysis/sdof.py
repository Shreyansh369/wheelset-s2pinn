"""H1 on an SDOF oscillator: gPC degree needed to resolve the response near resonance.

Model (unit mass, mean stiffness 1, so the mean natural frequency is 1):

    x'' + c x' + k(xi) x = e^{i w t},   H(w; xi) = 1 / (k(xi) - w^2 + i c w),

with a deterministic damper c = 2 zeta_bar (zeta_bar is the nominal damping
ratio at k = 1) and a random stiffness of coefficient of variation ``cov``:

* ``legendre``: k = 1 + sqrt(3) cov xi,          xi ~ U(-1, 1)
* ``hermite``:  k = exp(sigma_L xi - sigma_L^2/2), xi ~ N(0, 1), sigma_L^2 = ln(1 + cov^2)

The surrogate is the orthonormal gPC projection of H(w; .) truncated at degree p.
Because the basis is orthonormal, the truncated variance sum_{n=1..p} |c_n|^2
increases monotonically to Var[H], so the relative variance error is
1 - Var_p / Var and the required degree is the first p where it drops below tol.

Coefficients are computed by composite Gauss-Legendre quadrature, which is fine
enough to resolve both the resonance peak in xi and polynomials of degree p_max.
For Hermite the integral is cut at |xi| = 10; by Cauchy-Schwarz the neglected
part of every coefficient is below sup|H| * P(|xi| > 10)^{1/2} ~ 1e-11 sup|H|.

Pi = s / zeta_bar with s the coefficient of variation of the natural frequency
(computed by the same quadrature).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FAMILIES = ("legendre", "hermite")


def quadrature(family: str, n_panels: int, nodes_per_panel: int = 10, cut: float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    """Nodes and probability weights (summing to 1) for xi's distribution."""
    lo, hi = (-1.0, 1.0) if family == "legendre" else (-cut, cut)
    g, gw = np.polynomial.legendre.leggauss(nodes_per_panel)
    edges = np.linspace(lo, hi, n_panels + 1)
    half = 0.5 * np.diff(edges)
    mid = 0.5 * (edges[1:] + edges[:-1])
    x = (mid[:, None] + half[:, None] * g[None, :]).ravel()
    w = (half[:, None] * gw[None, :]).ravel()
    if family == "legendre":
        w = w / 2.0
    elif family == "hermite":
        w = w * np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)
    else:
        raise ValueError(family)
    return x, w


def orthonormal_polys(family: str, x: np.ndarray, p_max: int) -> np.ndarray:
    """[N, p_max+1] orthonormal Legendre (U(-1,1)) or probabilists' Hermite (N(0,1))."""
    P = np.empty((x.size, p_max + 1))
    P[:, 0] = 1.0
    if p_max == 0:
        return P
    if family == "legendre":
        # q_n = sqrt(2n+1) P_n; recurrence in normalised form
        P[:, 1] = np.sqrt(3.0) * x
        for n in range(1, p_max):
            a = np.sqrt((2 * n + 1) * (2 * n + 3)) / (n + 1)
            b = n / (n + 1) * np.sqrt((2 * n + 3) / (2 * n - 1))
            P[:, n + 1] = a * x * P[:, n] - b * P[:, n - 1]
    elif family == "hermite":
        # h_n = He_n / sqrt(n!)
        P[:, 1] = x
        for n in range(1, p_max):
            P[:, n + 1] = (x * P[:, n] - np.sqrt(n) * P[:, n - 1]) / np.sqrt(n + 1)
    else:
        raise ValueError(family)
    return P


def stiffness(family: str, xi: np.ndarray, cov: float) -> np.ndarray:
    if family == "legendre":
        if np.sqrt(3) * cov >= 1:
            raise ValueError("uniform stiffness would reach zero")
        return 1.0 + np.sqrt(3.0) * cov * xi
    sig = np.sqrt(np.log1p(cov**2))
    return np.exp(sig * xi - 0.5 * sig**2)


def frf(omega: np.ndarray, k: np.ndarray, c: float) -> np.ndarray:
    """H[N, F] = 1 / (k - w^2 + i c w)."""
    return 1.0 / (k[:, None] - omega[None, :] ** 2 + 1j * c * omega[None, :])


def frequency_cov(family: str, cov: float, x: np.ndarray, w: np.ndarray) -> float:
    wn = np.sqrt(stiffness(family, x, cov))
    m = np.sum(w * wn)
    return float(np.sqrt(np.sum(w * (wn - m) ** 2)) / m)


@dataclass
class CaseResult:
    family: str
    zeta: float
    cov: float
    s: float
    Pi: float
    p_max: int
    p_req_at_mean: int | None  # None = censored (> p_max)
    p_req_band: int | None
    worst_band_omega: float
    var_err_at_mean: np.ndarray  # relative variance error vs p at w = 1
    quad_check_rel: float  # change in Var[H] when the quadrature is refined 2x


def _variance_error_curve(H: np.ndarray, P: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Relative variance error 1 - Var_p/Var for p = 0..p_max; H: [N, F] -> [p_max+1, F]."""
    coeffs = P.T @ (w[:, None] * H)  # [p+1, F]
    mean = coeffs[0]
    var_true = np.sum(w[:, None] * np.abs(H - mean[None, :]) ** 2, axis=0)
    cum = np.cumsum(np.abs(coeffs) ** 2, axis=0) - np.abs(coeffs[0]) ** 2
    return 1.0 - cum / var_true[None, :]


def _first_below(err: np.ndarray, tol: float) -> int | None:
    idx = np.nonzero(err <= tol)[0]
    return int(idx[0]) if idx.size else None


def run_case(
    family: str,
    zeta: float,
    cov: float,
    p_max: int,
    tol: float = 0.01,
    band: tuple[float, float] = (0.5, 1.5),
    n_band: int = 801,
    n_panels: int = 2000,
) -> CaseResult:
    x, w = quadrature(family, n_panels)
    k = stiffness(family, x, cov)
    c = 2.0 * zeta  # deterministic damper; zeta is the ratio at k = 1
    s = frequency_cov(family, cov, x, w)
    P = orthonormal_polys(family, x, p_max)

    omegas = np.concatenate([[1.0], np.linspace(band[0], band[1], n_band)])
    err = _variance_error_curve(frf(omegas, k, c), P, w)  # [p+1, F]
    p_mean = _first_below(err[:, 0], tol)
    p_each = [_first_below(err[:, j], tol) for j in range(1, err.shape[1])]
    if any(p is None for p in p_each):
        p_band, worst = None, float(omegas[1 + next(i for i, p in enumerate(p_each) if p is None)])
    else:
        j = int(np.argmax(p_each))
        p_band, worst = int(p_each[j]), float(omegas[1 + j])

    # quadrature refinement check on Var[H] at w = 1
    x2, w2 = quadrature(family, 2 * n_panels)
    H1 = frf(np.array([1.0]), k, c)[:, 0]
    H2 = frf(np.array([1.0]), stiffness(family, x2, cov), c)[:, 0]
    v1 = np.sum(w * np.abs(H1 - np.sum(w * H1)) ** 2)
    v2 = np.sum(w2 * np.abs(H2 - np.sum(w2 * H2)) ** 2)

    return CaseResult(
        family=family, zeta=zeta, cov=cov, s=s, Pi=s / zeta, p_max=p_max,
        p_req_at_mean=p_mean, p_req_band=p_band, worst_band_omega=worst,
        var_err_at_mean=err[:, 0], quad_check_rel=float(abs(v1 - v2) / v2),
    )


def fit_loglog_slope(Pi: np.ndarray, p: np.ndarray) -> dict:
    """Least-squares fit log p = a + b log Pi; returns slope, intercept, R^2, n."""
    lx, ly = np.log(Pi), np.log(p)
    A = np.stack([np.ones_like(lx), lx], 1)
    coef, *_ = np.linalg.lstsq(A, ly, rcond=None)
    resid = ly - A @ coef
    r2 = 1 - resid.var() / ly.var() if ly.var() > 0 else float("nan")
    # standard error of the slope
    n = lx.size
    se = np.sqrt(resid @ resid / max(n - 2, 1) / np.sum((lx - lx.mean()) ** 2)) if n > 2 else float("nan")
    return {"slope": float(coef[1]), "slope_se": float(se), "intercept": float(coef[0]), "r2": float(r2), "n": int(n)}
