import numpy as np
import pytest

from src.analysis.sdof import frf, orthonormal_polys, quadrature, run_case, stiffness


def test_legendre_orthonormal_up_to_high_degree():
    x, w = quadrature("legendre", 2000)
    P = orthonormal_polys("legendre", x, 300)
    assert np.max(np.abs(P.T @ (w[:, None] * P) - np.eye(301))) < 1e-6


def test_hermite_orthonormal_with_wide_cut():
    # h_n^2 phi has mass out to |xi| ~ 2 sqrt(n), so the Gram check needs a wide cut
    x, w = quadrature("hermite", 4000, cut=25.0)
    P = orthonormal_polys("hermite", x, 100)
    assert np.max(np.abs(P.T @ (w[:, None] * P) - np.eye(101))) < 1e-9


def test_hermite_frf_coefficients_insensitive_to_cut():
    # coefficients of a bounded function only need P(|xi| > cut) to be negligible
    cov, zeta, p = 0.2, 0.005, 400
    out = []
    for cut, panels in [(10.0, 2000), (14.0, 2800)]:
        x, w = quadrature("hermite", panels, cut=cut)
        H = frf(np.array([1.0]), stiffness("hermite", x, cov), 2 * zeta)[:, 0]
        out.append(orthonormal_polys("hermite", x, p).T @ (w * H))
    assert np.max(np.abs(out[0] - out[1])) < 1e-9 * np.max(np.abs(out[1]))


@pytest.mark.parametrize("family", ["legendre", "hermite"])
def test_quadrature_variance_matches_monte_carlo(family):
    rng = np.random.default_rng(0)
    cov, zeta = 0.05, 0.02
    xi = 2 * rng.random(2_000_000) - 1 if family == "legendre" else rng.standard_normal(2_000_000)
    H = frf(np.array([1.0]), stiffness(family, xi, cov), 2 * zeta)[:, 0]
    x, w = quadrature(family, 2000)
    Hq = frf(np.array([1.0]), stiffness(family, x, cov), 2 * zeta)[:, 0]
    var_q = np.sum(w * np.abs(Hq - np.sum(w * Hq)) ** 2)
    assert np.var(H) == pytest.approx(var_q, rel=5e-3)


def test_variance_error_is_monotone_and_converges():
    r = run_case("legendre", zeta=0.05, cov=0.02, p_max=40)
    e = r.var_err_at_mean
    assert np.all(np.diff(e[1:]) <= 1e-12)
    assert e[-1] < 1e-10
    assert r.p_req_at_mean is not None and r.quad_check_rel < 1e-8
