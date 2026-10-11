# Does a physics-informed surrogate help over FE-direct? (scenario a, option iv)

Status: paper assessment. I trained no surrogate for this. The numbers below come from the exact FE
transfer function: `experiments/p1_surrogate_rank.py` → `results/p1/surrogate_rank.json`, and
`experiments/p1_fe_direct.py` → `results/p1/fe_direct.json`.

## 1. What FE-direct costs

All figures are single-threaded CPU in this container. The machine was shared with the reproduction
run at the time, so treat them as upper bounds.

| item | value |
|---|---|
| FE model (L1-lin + Hertz contact + rail oscillator) | 70 DOF |
| one complex eigendecomposition (all modes, exact H via residues) | 7 ms |
| direct solve, whole 50–700 Hz band (1301 lines) | 0.12 s |
| H on the estimator grid (25 payload nodes × modal sum) | 0.19–0.29 s per (kB0, cB) |
| one profile-likelihood evaluation, N = 50 | ≈ 0.5 s (H ≈ 0.25 s + nuisance profiling ≈ 0.25 s) |
| full fit (Nelder–Mead, ≈ 75 evaluations + Hessian), N = 50 / 200 | see `fe_direct.json` (≈ 40 s / ≈ 90 s) |

A surrogate could replace only the H part. The nuisance profiling (sub-band levels, per-pass payload)
stays the same whatever produces H. **The best a surrogate can do is roughly halve the cost of one
likelihood evaluation.** Against that, training costs ≈ 90 min on a T4 (S²-PINN Table 18), which
equals ≈ 100+ full FE-direct fits on one CPU core.

## 2. Is H(f; kB0, W) low-rank separable? (the user's caveat)

Your note was that a pole moving with kB0 makes H non-separable. That holds in principle: the
ε-rank grows as the tolerance tightens. In practice it is small here, because the support-type modes
are well damped (ζ ≈ 5–10%). Over the factor-2 prior on kB0 (0.5e9–2e9) the support pole travels
from 476 to 691 Hz at W = 5.5 t, about 4 half-power bandwidths. The table gives the best rank-R
approximation (truncated SVD, optimal in Frobenius norm) of H[f, (kB0, W)] over the prior and over
E equal elements in log kB0:

| elements E (kB0 ratio per element) | R for 10% | R for 1% | R for 0.1% |
|---|---|---|---|
| 1 (4.0) | 4 | 8 | 13 |
| 2 (2.0) | 3 | 7 | 11 |
| 4 (1.41) | 3 | 6 | 10 |
| 8 (1.19) | 3 | 6 | 9 |
| 1, W fixed at 14 t | 3 | 6 | 9 |

Multi-element splitting in kB0 helps only a little, from 13 to 9–10 at 0.1%. After that the payload
direction and the in-band mode structure set the rank.

**What does a surrogate error do to the kB0 estimate?** I propagated the rank-R truncation error
through the Whittle estimator. The first-order misspecified-ML bias is b = −J⁻¹Dᵀδ, with δ the error
in log v per bin. The design was N = 50, speeds 60–110 km/h, K = 16 sub-bands, 3% WIM, 40 dB
SNR, and CRB(kB0) = 0.20%.

| R | E = 1: rel. Frobenius error | E = 1: bias / CRB | E = 4: rel. Frobenius error | E = 4: bias / CRB |
|---|---|---|---|---|
| 3 | 1.3e-1 | 3.8 | 4.9e-2 | 1.2 |
| 5 | 4.4e-2 | 1.1 | 1.6e-2 | 0.06 |
| 8 | 9.9e-3 | 0.10 | 2.0e-3 | 0.002 |
| 10 | 3.8e-3 | 0.06 | 3.9e-4 | < 0.001 |
| 13 | 7.9e-4 | < 0.001 | 4.9e-5 | 0.001 |

The SVD truncation is the *best possible* separable approximation at each R. A trained CP surrogate
has larger error, and its structure is not controlled. Bias depends on how that error projects onto
the sensitivity directions, which varies non-monotonically (E = 1, R = 5 against R = 8). To be
harmless the error must be at the ≈ 1e-2 level or better *in the structured sense*, and that has to be
checked against FE solves after training. So the FE model is needed anyway, at least for validation.
With S²-PINN's default R = 5 and a single element, even the optimal error gives a bias of about 1 CRB.

## 3. Multi-element CP against a modal surrogate with θ-dependent poles

**Modal facts at the nominal point.** Five modes are excited by the symmetric roughness input below
1.5 kHz: 55, 96, 440, 544 and 609 Hz (ζ = 0.18, 0.03, 0.08, 0.07, 0.05). Antisymmetric modes have
zero residue at the left axlebox under symmetric input. They cross the symmetric ones exactly, with
no veering, and filtering on the residue removes them.

**Veering.** Two cases occur among the excited (symmetric) modes over the prior:
- At W = 5.5 t the support mode sweeps through a weakly coupled 513 Hz mode. Its residue rises from
  5 to 45 at the crossing, and the gap between the veering poles is 11–17 Hz, smaller than the
  ≈ 50 Hz bandwidth.
- At W = 22.5 t the 502→576 Hz and 593→720 Hz branches veer strongly.

The pole and residue branches therefore have square-root branch points close to the real (kB0, W)
domain. A per-mode polynomial fit (tensor Legendre in log kB0 and log W, degree 8 × 4) fails:
- median H error 31%, maximum 107%;
- worst pole error 1.7 times the pole's own decay rate.

A second factor is the acceleration output. Its modal terms do not decay with frequency, so the
remainder from the modes left out is as large as H itself (up to 2.8 times). It cancels only when
combined with the kept terms, so it needs residual-flexibility terms.

| | multi-element CP (S²-PINN style, ω as coordinate) | modal surrogate, θ-dependent poles |
|---|---|---|
| handles veering | yes. H itself is analytic in θ for real ω; branch points cancel in the sum | no, if poles and residues are fitted per mode. Yes only as a parametric reduced-order model (smooth reduced matrices M_r, C_r, K_r(θ), poles by a small eig) |
| size for 1% / 0.1% | R = 8 / 13 (E = 1); 6 / 10 (E = 4), each with a θ-polynomial | 5 complex poles and residues plus a residual term, once veering is handled |
| frequency extrapolation and resolution | needs an f-dictionary dense enough to resolve peaks of width ≈ 50 Hz | exact in ω by construction |
| interpretable outputs | none directly | support-mode f_s and ζ_s directly (useful for H2 and for reporting ζ_s) |
| training | yes (≈ T4-hours), with error certified only after the fact | none needed: this model is affine in (k_B, k_H), so Galerkin projection onto a fixed basis is exact-affine and certifiable |

**On paper, the modal or reduced-order route beats the CP route here.** It is smaller and
interpretable, and veering is handled by a small eig rather than a large rank. It also needs no
learning. Done properly it is model-order reduction, and the "physics-informed" training step adds
nothing to it.

## 4. Where a surrogate could genuinely help

None of these applies to the current two-target L1-lin problem.

1. **Many uncertain model-form parameters marginalised by sampling.** Examples are contact
   stiffness, axle damping, k_p, m_b and rail-pad parameters. With 6–10 such inputs and MCMC needing
   10⁵ likelihood evaluations, FE-direct costs about 0.4 s × 10⁵ ≈ 11 h. A cheap surrogate would cut
   that to minutes. A parametric reduced-order model does the same without training, so the advantage
   is over brute-force FE, not over good numerics.
2. **Nonlinear supports (L0: clearance, roller contact).** Here no frequency-domain solve exists and
   each pass needs a transient nonlinear simulation. This is the one setting where a learned surrogate
   could have a real speed advantage. It is outside L1-lin and the current paper.
3. **Non-stationary records** (speed varying within a pass). Whittle assumes stationarity within a
   record, and a time-domain physics-informed model could avoid that. It is cheaper to shorten the
   records instead.
4. **Fleet-scale amortisation.** Thousands of wheelsets refit daily on one fixed prior. A tabulated H
   or a reduced-order model amortises equally well, with certified error.

## 5. Verdict

For scenario (a)/(iv) with targets (kB0, cB), FE-direct is:
- exact to the reference model (payload-interpolation error 6.6e-5);
- fast enough (under 2 min per fit on one core);
- training-free.

Its statistical performance is in `fe_direct.json` (bias, RMSE/CRB and coverage per cell).

A physics-informed surrogate offers:
- no accuracy advantage, and adds a bias that must be validated against FE;
- at most ≈ 2× on one likelihood evaluation, which does not repay its training below ≈ 100 fits;
- no interpretability advantage over a modal or reduced-order model.

Its credible niches are the four items in §4. None is the current paper's problem.
