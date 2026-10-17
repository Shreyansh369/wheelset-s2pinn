"""Closed-form gPC moments against Monte Carlo, plus basis sanity checks."""

import math

import numpy as np
import pytest
import torch

from src.model.gpc import AnisotropicMixedGPC, DegreeGroup, anisotropic_multi_indices
from src.model.moments import (
    conditional_moments,
    cp_stochastic_coeffs,
    paper_basis,
    sobol_indices,
    total_moments,
)

torch.set_default_dtype(torch.float64)
N_MC = 1_000_000


def _small_basis(normalized: bool) -> AnisotropicMixedGPC:
    # 2 health (Legendre) + 1 payload (Legendre) up to degree 3, 3 forcing (Hermite) up to degree 1
    fam = ["legendre"] * 3 + ["hermite"] * 3
    groups = [DegreeGroup((0, 1, 2), 3), DegreeGroup((3, 4, 5), 1)]
    return AnisotropicMixedGPC(fam, groups, total_degree=3, normalized=normalized)


def _sample(basis: AnisotropicMixedGPC, n: int, gen: torch.Generator) -> torch.Tensor:
    cols = []
    for fam in basis.families:
        if fam == "legendre":
            cols.append(2 * torch.rand(n, generator=gen) - 1)
        else:
            cols.append(torch.randn(n, generator=gen))
    return torch.stack(cols, 1)


def test_g_counts_match_hand_count():
    # (theta1, theta2, W) degree <= p, 14 Gaussian forcing variables degree <= 1
    assert paper_basis(6, total_degree=True).num_basis == 84 + 14 * 56 == 868
    assert paper_basis(6, total_degree=False).num_basis == 84 * 15 == 1260
    assert paper_basis(4, total_degree=True).num_basis == 35 + 14 * 20 == 315
    assert paper_basis(4, total_degree=False).num_basis == 525
    # isotropic set reduces to the S2-PINN count C(R+p, p)
    iso = anisotropic_multi_indices(5, [DegreeGroup(tuple(range(5)), 3)])
    assert len(iso) == math.comb(8, 3)
    assert iso[0] == (0,) * 5


@pytest.mark.parametrize("normalized", [True, False])
def test_basis_is_orthogonal_by_quadrature(normalized):
    basis = _small_basis(normalized)
    # exact tensor quadrature: Gauss-Legendre (uniform density 1/2) and Gauss-Hermite_e
    xl, wl = np.polynomial.legendre.leggauss(6)
    wl = wl / 2
    xh, wh = np.polynomial.hermite_e.hermegauss(4)
    wh = wh / math.sqrt(2 * math.pi)
    nodes = [xl] * 3 + [xh] * 3
    weights = [wl] * 3 + [wh] * 3
    grid = np.stack(np.meshgrid(*nodes, indexing="ij"), -1).reshape(-1, 6)
    w = np.prod(np.stack(np.meshgrid(*weights, indexing="ij"), -1).reshape(-1, 6), 1)
    psi = basis(torch.from_numpy(grid))
    gram = psi.T @ (psi * torch.from_numpy(w)[:, None])
    assert torch.allclose(gram, torch.diag(basis.norms_sq()), atol=1e-10)


@pytest.mark.parametrize("normalized", [True, False])
def test_total_moments_vs_monte_carlo(normalized):
    gen = torch.Generator().manual_seed(0)
    basis = _small_basis(normalized)
    G = basis.num_basis
    coeffs = torch.randn(4, G, generator=gen) / torch.sqrt(basis.norms_sq())
    mean_cf, var_cf = total_moments(coeffs, basis)

    z = _sample(basis, N_MC, gen)
    a = basis(z) @ coeffs.T  # [N, 4]
    mean_mc, var_mc = a.mean(0), a.var(0)
    se_mean = torch.sqrt(var_mc / N_MC)
    assert torch.all((mean_mc - mean_cf).abs() < 5 * se_mean)
    assert torch.allclose(var_mc, var_cf, rtol=1e-2)


@pytest.mark.parametrize("normalized", [True, False])
def test_conditional_moments_vs_monte_carlo(normalized):
    gen = torch.Generator().manual_seed(1)
    basis = _small_basis(normalized)
    coeffs = torch.randn(3, basis.num_basis, generator=gen) / torch.sqrt(basis.norms_sq())
    cond_dims = [0, 1]  # condition on theta; marginalise W and forcing
    theta = torch.tensor([[0.3, -0.7], [-0.9, 0.1], [0.0, 0.95]])
    mean_cf, var_cf = conditional_moments(coeffs, basis, cond_dims, theta)

    for t in range(theta.shape[0]):
        z = _sample(basis, N_MC, gen)
        z[:, cond_dims] = theta[t]
        a = basis(z) @ coeffs.T
        se = torch.sqrt(a.var(0) / N_MC)
        assert torch.all((a.mean(0) - mean_cf[:, t]).abs() < 5 * se)
        assert torch.allclose(a.var(0), var_cf[:, t], rtol=1e-2)


def test_conditioning_on_nothing_equals_total():
    gen = torch.Generator().manual_seed(2)
    basis = _small_basis(True)
    coeffs = torch.randn(2, basis.num_basis, generator=gen)
    m0, v0 = total_moments(coeffs, basis)
    m1, v1 = conditional_moments(coeffs, basis, [], torch.zeros(1, 0))
    assert torch.allclose(m0, m1[:, 0]) and torch.allclose(v0, v1[:, 0])


def test_sobol_on_function_with_known_indices():
    # f = a P1(z0) + b z3 + c P1(z0) z3 with z0 ~ U(-1,1), z3 ~ N(0,1), unnormalised basis:
    # Var parts a^2/3, b^2, c^2/3
    basis = _small_basis(normalized=False)
    mi = basis.multi_indices.tolist()
    coeffs = torch.zeros(basis.num_basis)
    a, b, c = 1.5, -0.8, 0.6
    coeffs[mi.index([1, 0, 0, 0, 0, 0])] = a
    coeffs[mi.index([0, 0, 0, 1, 0, 0])] = b
    coeffs[mi.index([1, 0, 0, 1, 0, 0])] = c
    s = sobol_indices(coeffs, basis, {"theta": [0, 1], "zeta2": [3, 4, 5]})
    tot = a**2 / 3 + b**2 + c**2 / 3
    assert s["theta"]["first"].item() == pytest.approx(a**2 / 3 / tot)
    assert s["theta"]["total"].item() == pytest.approx((a**2 + c**2) / 3 / tot)
    assert s["zeta2"]["first"].item() == pytest.approx(b**2 / tot)


def test_cp_coefficients_reproduce_cp_forward():
    gen = torch.Generator().manual_seed(3)
    basis = _small_basis(True)
    q, P = 5, 7
    sa, tb = torch.randn(P, q, generator=gen), torch.randn(P, q, generator=gen)
    D, w = torch.randn(basis.num_basis, q, generator=gen), torch.randn(q, generator=gen)
    z = _sample(basis, P, gen)
    u_cp = ((sa * tb * (basis(z) @ D)) @ w)  # S2-PINN forward map, Eq. (4)
    c = cp_stochastic_coeffs(sa, tb, D, w)
    assert torch.allclose(u_cp, (c * basis(z)).sum(1))
