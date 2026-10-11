"""Closed-form moments and Sobol indices from gPC coefficients.

For a surrogate a(x, t, z) = sum_g c_g(x, t) Psi_g(z) with an orthogonal tensor
basis, and z split into conditioning variables theta and the rest r, each mode
factorises as Psi_g = Psi_{alpha_theta}(theta) Psi_{alpha_r}(r). Grouping modes
by alpha_r gives conditional coefficients

    d_beta(theta) = sum_{g : alpha_r(g) = beta} c_g Psi_{alpha_theta(g)}(theta),

so that

    E_r[a | theta]   = d_0(theta),
    Var_r[a | theta] = sum_{beta != 0} d_beta(theta)^2 ||Psi_beta||^2.

For S2-PINN's CP core, c_g(x, t) = sum_r w_r (F_space A)_r (F_time B)_r D_{g r}
(see :func:`cp_stochastic_coeffs`), so these moments need no sampling.
Sobol indices of variable groups are the classical gPC result (Sudret 2008);
they are used here as a tool, not claimed as a contribution.
"""

from __future__ import annotations

import math
from typing import Sequence

import torch

from src.model.gpc import AnisotropicMixedGPC, DegreeGroup, eval_univariate, univariate_norm_sq


def cp_stochastic_coeffs(sa: torch.Tensor, tb: torch.Tensor, D: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    """Stochastic coefficients of a CP model at given (x, t) points.

    sa = F_space @ A and tb = F_time @ B, both [B, q]; D is [G, q]; w is [q].
    Returns c: [B, G] with u(x, t, z) = c @ Psi(z).
    """
    return (sa * tb * w) @ D.transpose(0, 1)


def total_moments(coeffs: torch.Tensor, basis: AnisotropicMixedGPC) -> tuple[torch.Tensor, torch.Tensor]:
    """Mean and variance over all random inputs. coeffs: [..., G]."""
    norms = basis.norms_sq().to(coeffs)
    mean = coeffs[..., 0]
    var = (coeffs[..., 1:] ** 2 * norms[1:]).sum(-1)
    return mean, var


def _split_indices(basis: AnisotropicMixedGPC, cond_dims: Sequence[int]):
    mi = basis.multi_indices
    cond = list(cond_dims)
    rest = [d for d in range(basis.R) if d not in cond]
    keys = [tuple(row) for row in mi[:, rest].tolist()]
    uniq = sorted(set(keys), key=lambda a: (sum(a), a))
    group_of = torch.tensor([uniq.index(k) for k in keys], dtype=torch.long)
    return cond, rest, uniq, group_of


def conditional_moments(
    coeffs: torch.Tensor,
    basis: AnisotropicMixedGPC,
    cond_dims: Sequence[int],
    cond_values: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """E[a | z_cond] and Var[a | z_cond] over the remaining variables.

    coeffs: [P, G] coefficients at P space-time points.
    cond_values: [T, len(cond_dims)] values of the conditioning variables, in
    the basis's standard coordinates.
    Returns mean, var: [P, T].
    """
    cond, rest, uniq, group_of = _split_indices(basis, cond_dims)
    mi = basis.multi_indices
    dtype = coeffs.dtype
    T = cond_values.shape[0]

    # Psi_{alpha_theta(g)}(theta_t) for every mode g: [T, G]
    psi_c = torch.ones(T, basis.num_basis, dtype=dtype, device=coeffs.device)
    for j, d in enumerate(cond):
        p_d = int(mi[:, d].max())
        if p_d == 0:
            continue
        uni = eval_univariate(basis.families[d], cond_values[:, j].to(dtype), p_d, basis.normalized)
        psi_c = psi_c * uni.index_select(1, mi[:, d].to(coeffs.device))

    # d_beta(theta_t) = sum_{g in beta} c_g psi_c[t, g]: [P, T, n_beta]
    weighted = coeffs.unsqueeze(1) * psi_c.unsqueeze(0)  # [P, T, G]
    n_beta = len(uniq)
    d = torch.zeros(coeffs.shape[0], T, n_beta, dtype=dtype, device=coeffs.device)
    d.index_add_(2, group_of.to(coeffs.device), weighted)

    zero = tuple([0] * len(rest))
    i0 = uniq.index(zero)
    if basis.normalized:
        norms_r = torch.ones(n_beta, dtype=dtype, device=coeffs.device)
    else:
        norms_r = torch.tensor(
            [math.prod(univariate_norm_sq(basis.families[dd], a) for dd, a in zip(rest, beta)) for beta in uniq],
            dtype=dtype, device=coeffs.device,
        )
    mask = torch.ones(n_beta, dtype=torch.bool, device=coeffs.device)
    mask[i0] = False
    mean = d[..., i0]
    var = (d[..., mask] ** 2 * norms_r[mask]).sum(-1)
    return mean, var


def sobol_indices(
    coeffs: torch.Tensor,
    basis: AnisotropicMixedGPC,
    groups: dict[str, Sequence[int]],
) -> dict[str, dict[str, torch.Tensor]]:
    """First-order and total Sobol indices for named groups of variables.

    coeffs: [..., G]. A mode counts toward a group's first-order index when it
    is non-constant and depends only on that group's variables; toward its
    total index when it depends on any of them.
    """
    norms = basis.norms_sq().to(coeffs)
    mi = basis.multi_indices.to(coeffs.device)
    energy = coeffs**2 * norms
    nonconst = mi.sum(1) > 0
    var = energy[..., nonconst].sum(-1)
    out: dict[str, dict[str, torch.Tensor]] = {}
    for name, dims in groups.items():
        dims = list(dims)
        others = [d for d in range(basis.R) if d not in dims]
        in_g = mi[:, dims].sum(1) > 0
        in_o = mi[:, others].sum(1) > 0 if others else torch.zeros_like(in_g)
        first = energy[..., in_g & ~in_o].sum(-1) / var
        total = energy[..., in_g].sum(-1) / var
        out[name] = {"first": first, "total": total}
    return out


def paper_basis(p_theta: int, n_theta: int = 2, n_payload: int = 1, n_zeta2: int = 14,
                total_degree: bool = True, normalized: bool = True) -> AnisotropicMixedGPC:
    """The paper's basis: Legendre in (theta, W) up to p_theta, Hermite in zeta_2 up to 1.

    ``total_degree=True`` additionally caps |alpha| <= p_theta (the
    "anisotropic total-degree set"); ``False`` gives the product set.
    """
    n_tw = n_theta + n_payload
    families = ["legendre"] * n_tw + ["hermite"] * n_zeta2
    groups = [DegreeGroup(tuple(range(n_tw)), p_theta), DegreeGroup(tuple(range(n_tw, n_tw + n_zeta2)), 1)]
    return AnisotropicMixedGPC(families, groups, total_degree=p_theta if total_degree else None, normalized=normalized)
