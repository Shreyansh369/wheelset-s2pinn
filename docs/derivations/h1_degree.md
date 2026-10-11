# H1: gPC degree needed near resonance, a pre-training diagnostic

This is classical approximation theory applied to one oscillator, with constants measured by `experiments/p0_h1_sdof.py` and checked by `experiments/p0_h1_theory.py` (`results/p0/h1_theory_check.json`). It is presented as a diagnostic, not a new theorem. The phenomenon itself, slow PC convergence near resonance, is known (Jacquelin et al. 2015, 2016; Yaghoubi et al. 2017; see `docs/lit_review.md`).

## Setup

Receptance H(ω; ξ) = 1/(k(ξ) − ω² + icω), with unit mass, mean stiffness 1, damper c = 2ζ, evaluated at ω = 1. Π = s/ζ, where s is the coefficient of variation of the natural frequency. For small CoV, s ≈ CoV_k/2.

The pole is where k(ξ_p) = 1 − 2iζ. Its distance from the real ξ axis sets how fast the gPC coefficients decay.

## Uniform input, Legendre basis

k = 1 + √3·CoV·ξ with ξ ~ U(−1, 1). The pole is ξ_p = −2iζ/(√3·CoV) ≈ −i/(√3·Π).

H is analytic inside the Bernstein ellipse through ξ_p. For a pole on the imaginary axis at height y, the ellipse parameter is ρ = y + √(1+y²) ≈ 1 + y. Orthonormal Legendre coefficients therefore decay like ρ⁻ⁿ (Bernstein's theorem), and the relative variance left after truncating at degree p is about ρ^(−2p). Setting this equal to ε:

  p ≈ ln(1/ε) / (2 ln ρ) ≈ (√3/2)·Π·ln(1/ε).

The √3/2 factor comes from the uniform variable's half-width √3σ. At ε = 1%, (√3/2)·ln 100 = 3.99, so p ≈ 4.0Π.

**Measured** (1% variance error), p/Π by Π bin:

| Π bin | [0.5, 2) | [2, 5) | [5, 10) | [10, 40) |
|---|---|---|---|---|
| p/Π | 4.69 | 4.16 | 4.06 | 3.98 |
| measured / predicted | 1.09 | 1.05 | 1.04 | 1.01 |

The local log-log slope is ≈ 1 in every bin. **Degree ∝ Π·ln(1/ε)**, with the measured constant matching the leading-order prediction to within 10%.

## Gaussian (log-normal) input, Hermite basis

k = exp(σ_L ξ − σ_L²/2) with ξ ~ N(0, 1). H is analytic in the strip |Im ξ| < τ, with τ = atan(2ζ)/σ_L ≈ 1/Π.

Hille's theorem: Hermite-*function* coefficients of a function analytic in |Im u| < τ′ decay like exp(−τ′√(2n+1)). The probabilists' basis Heₙ under N(0, 1) maps to Hermite functions in u = x/√2, so τ′ = τ/√2 and the decay is exp(−τ√n). The variance tail after degree p is then about exp(−2τ√p), so

  p ≈ ln²(1/ε) / (4τ²) ≈ Π²·ln²(1/ε) / 4.

At ε = 1% the constant is 5.30.

**Measured**, p/Π² by Π bin:

| Π bin | [0.5, 2) | [2, 5) | [5, 10) | [10, 40) |
|---|---|---|---|---|
| p/Π² | 10.1 | 6.92 | 5.89 | 5.57 |
| measured / predicted | 1.90 | 1.31 | 1.12 | 1.06 |

The local slope rises 1.41 → 1.77 → 1.87 → 1.93 towards 2. **Degree ∝ Π² asymptotically.** At small Π the asymptotic rate hasn't taken over yet, which explains the larger ratio there.

The difference between the two families matches Jacquelin et al. (2016): Hermite roots spread without bound, Legendre roots stay in [−1, 1].

## Use as a diagnostic

Before training, compute Π from the prior on (θ, W). The frequency spread s can come from a few FE eigen-solves at prior corners, or from the gPC of ω_n. Then choose p from the measured constants above:
- uniform inputs: p ≈ 4.0Π at ε = 1%;
- Gaussian inputs: p ≈ 5.6Π² at large Π.

**G2, reworded (agreed 2026-10-11):** "Π ≤ 1.5 (uniform inputs)". On the SDOF this needs **p = 6** for a 1% variance error: the largest measured p_req for Π ≤ 1.5 is 6, and the leading-order prediction at Π = 1.5 is 5.98.

These rates are for a single isolated resonance. In the L1-lin model, Π must use the frequency spread of the mode nearest the forcing; Phase 1, P1.6, computes it.
