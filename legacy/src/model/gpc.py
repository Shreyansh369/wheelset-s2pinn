"""Anisotropic, mixed-family gPC basis.

The released S2-PINN ``GPCBasis`` (third_party/s2pinn/src/spinn/models/bases.py)
uses one polynomial family for every random variable, an isotropic total-degree
set, and unnormalised polynomials. This paper needs:

* Legendre for the uniform health and payload variables (theta, W) and Hermite
  for the Gaussian forcing variables (zeta_2), in one tensor basis;
* an anisotropic multi-index set: degree <= p_theta in (theta, W) and degree <= 1
  in zeta_2, because the reference model is exactly linear in zeta_2;
* orthonormal polynomials, so closed-form moments are plain sums of squares.

Polynomials use the same three-term recurrences as the released code, then
divide by the norm: E[P_n(U)^2] = 1/(2n+1) for U ~ U(-1, 1) and
E[He_n(Z)^2] = n! for Z ~ N(0, 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import Sequence

import torch
import torch.nn as nn

FAMILIES = ("legendre", "hermite")


def univariate_norm_sq(family: str, n: int) -> float:
    if family == "legendre":
        return 1.0 / (2 * n + 1)
    if family == "hermite":
        return float(math.factorial(n))
    raise ValueError(f"unknown family {family!r}")


def eval_univariate(family: str, x: torch.Tensor, max_degree: int, normalized: bool) -> torch.Tensor:
    """Return [..., max_degree+1] polynomial values at ``x``."""
    vals = [torch.ones_like(x)]
    if max_degree >= 1:
        vals.append(x)
    for n in range(1, max_degree):
        if family == "legendre":
            vals.append(((2 * n + 1) * x * vals[n] - n * vals[n - 1]) / (n + 1))
        elif family == "hermite":
            vals.append(x * vals[n] - n * vals[n - 1])
        else:
            raise ValueError(f"unknown family {family!r}")
    out = torch.stack(vals, dim=-1)
    if normalized:
        norms = torch.tensor(
            [math.sqrt(univariate_norm_sq(family, n)) for n in range(max_degree + 1)],
            dtype=x.dtype, device=x.device,
        )
        out = out / norms
    return out


@dataclass(frozen=True)
class DegreeGroup:
    """A block of variables whose summed degree is capped at ``max_degree``."""

    dims: tuple[int, ...]
    max_degree: int


def anisotropic_multi_indices(
    n_dims: int,
    groups: Sequence[DegreeGroup],
    total_degree: int | None = None,
) -> list[tuple[int, ...]]:
    """Multi-indices with per-group degree caps and an optional total cap.

    Every dimension must belong to exactly one group. With ``total_degree=None``
    the set is the product of the per-group total-degree sets; otherwise it is
    further cut to ``|alpha| <= total_degree``. Indices are sorted by total
    degree, then lexicographically, so index 0 is the constant mode.
    """
    covered = sorted(d for g in groups for d in g.dims)
    if covered != list(range(n_dims)):
        raise ValueError(f"groups must partition range({n_dims}), got {covered}")

    per_group: list[list[tuple[int, ...]]] = []
    for g in groups:
        k = len(g.dims)
        per_group.append([a for a in product(range(g.max_degree + 1), repeat=k) if sum(a) <= g.max_degree])

    out: list[tuple[int, ...]] = []
    for combo in product(*per_group):
        alpha = [0] * n_dims
        for g, part in zip(groups, combo):
            for d, a in zip(g.dims, part):
                alpha[d] = a
        if total_degree is None or sum(alpha) <= total_degree:
            out.append(tuple(alpha))
    out.sort(key=lambda a: (sum(a), tuple(-x for x in a)))
    return out


class AnisotropicMixedGPC(nn.Module):
    """Tensor gPC basis Psi_alpha(z) = prod_i psi^{(family_i)}_{alpha_i}(z_i)."""

    def __init__(
        self,
        families: Sequence[str],
        groups: Sequence[DegreeGroup],
        total_degree: int | None = None,
        normalized: bool = True,
    ):
        super().__init__()
        for f in families:
            if f not in FAMILIES:
                raise ValueError(f"family must be one of {FAMILIES}, got {f!r}")
        self.families = tuple(families)
        self.groups = tuple(groups)
        self.total_degree = total_degree
        self.normalized = normalized
        idx = anisotropic_multi_indices(len(families), groups, total_degree)
        self.register_buffer("multi_indices", torch.tensor(idx, dtype=torch.long), persistent=True)
        self.max_degree_per_dim = [int(self.multi_indices[:, i].max()) for i in range(len(families))]

    @property
    def R(self) -> int:
        return len(self.families)

    @property
    def num_basis(self) -> int:
        return int(self.multi_indices.shape[0])

    def norms_sq(self) -> torch.Tensor:
        """E[Psi_alpha^2] for every mode (all ones when normalized)."""
        if self.normalized:
            return torch.ones(self.num_basis, dtype=torch.float64)
        mi = self.multi_indices.tolist()
        return torch.tensor(
            [math.prod(univariate_norm_sq(f, a) for f, a in zip(self.families, alpha)) for alpha in mi],
            dtype=torch.float64,
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """z: [B, R] -> [B, G]."""
        if z.ndim != 2 or z.shape[1] != self.R:
            raise ValueError(f"z must have shape [B, {self.R}], got {tuple(z.shape)}")
        feats = z.new_ones((z.shape[0], self.num_basis))
        for i, fam in enumerate(self.families):
            p_i = self.max_degree_per_dim[i]
            if p_i == 0:
                continue
            uni = eval_univariate(fam, z[:, i], p_i, self.normalized)
            feats = feats * uni.index_select(1, self.multi_indices[:, i])
        return feats
