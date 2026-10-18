# Method notes: multi-pass frequency-domain likelihood (FE-direct)

These notes support the paper's methods section. The code is in `src/inverse/multipass.py`
(independent sections, debiased option, profile intervals, misspecification bias) and
`src/inverse/variants.py` (wheel-order lines, shared and partially coherent sections).

## 1. Observation model
- **Data.** Each pass i is a record of 20 wheel revolutions of left-axlebox acceleration. Its length
  is fixed in space (L = 20·2πr₀), so DFT bin k corresponds to the same wavenumber γ_k = 2πk/L on
  every pass, while its frequency f_ik = V_i γ_k / 2π depends on the pass speed.
- **Signal.** Rail roughness with one-sided wavenumber PSD G(γ) excites the vehicle–track system.
  The transfer function is H(f; θ, W_i, V_i), where θ holds the health parameters and the other
  globals, and W_i is the payload.
- **Roughness model.** G has the ISO 3095:2013 Fig. 2 shape times a free level g_s for each sub-band
  (K per one-third octave). The levels are nuisance parameters.
- **Payload.** Each pass's payload is measured by WIM. The prior on log W_i is Gaussian, with
  σ_W = 3%.
- **Noise.** The sensor noise floor e_i comes from an out-of-band region of the same record.

## 2. Whittle likelihood (independent sections)
The DFT coefficients are treated as independent complex Gaussians, giving

  −log L = Σ_i Σ_k [log v_ik + |c_ik|²/v_ik] + Σ_i (log W_i − log Ŵ_i)²/(2σ_W²).

This is the standard frequency-domain (Whittle) approximation.

Bayesian-FFT operational modal analysis uses the same structure, with the unknown modal-force PSD
in each band as a nuisance parameter (Au 2011, *J. Eng. Mech.* 137(3), 214–226; Au 2012, *MSSP*
26(1), 60–75 and 76–90). The nuisances are profiled out by Fisher scoring. The globals are then
maximised by Nelder–Mead on the profile likelihood.

## 3. Debiased Whittle likelihood (exact expected periodogram)
Setting v_ik = |H(f_ik)|² · 2G(γ_k) Δγ · g + e_i assumes the spectrum is flat across the record's
frequency kernel. The true expectation of the rectangular-window periodogram is the spectrum
convolved with the Fejér kernel T sinc²((f − f_k)T).

The bin-sampled form becomes biased once H has structure on the scale of one bin. That is the case
for the multi-wheel cross terms, whose ripple period V/d approaches 1/T for the farthest wheels. On
a setup like CT23's P2 case, the bin-sampled model's log-ratio to the averaged periodogram was off
by 0.47 rms, against 0.06 expected from sampling noise. Estimates then scattered about 3% around
the truth while the SE was 0.15%. Profile intervals never covered the truth.

The fix is the debiased Whittle likelihood:

> Sykulski, A.M., Olhede, S.C., Guillaumin, A.P., Lilly, J.M., Early, J.J. (2019). The debiased
> Whittle likelihood. *Biometrika* 106(2), 251–266. doi:10.1093/biomet/asy071 (verified 2026-10-12: author PDF header and RePEc listing, Biometrika 106(2):251-266; arXiv:1605.06718; open access CC BY 4.0)

It keeps the Whittle form but replaces v_ik by the exact expected periodogram:

  v_ik = Σ_m sinc²((f_m − f_ik)T)/M · |H(f_m)|² · 2G(γ_m) Δγ · g(m) + e_i.

The sum runs over a grid M = 4 times finer than the bins, truncated at ±120 bins (the frozen default
of `MultiPassWhittle`; the earlier ±30-bin truncation biased k_B0 upwards by about 0.03 pp, see the
bias diagnosis), over the analysis band. With this, the P2 estimates are consistent: 7.64–7.79 MN/m²
against a truth of 7.7, with an SE of about 0.5% (that P2 check was run with the ±30-bin kernel). For a single wheelset with smooth H, the two forms agree, and the bin-sampled
one is used there.

Correlation between neighbouring bins is still ignored, as in Sykulski et al. Their analysis
covers when this is harmless.

## 4. Multi-wheel coupling through the rail
Each rail carries N wheels with receptance A^w_kk, contact compliance 1/k_H, and rail receptance
A^r_jk = R(|d_j − d_k|). R is the receptance of an infinite Timoshenko beam on a hysteretic
foundation; the derivation is in `src/reference/track.py` and equals CT23 Eq. (11). The contact
forces are F = (A^c + A^r + A^w)⁻¹Z, where Z_k = Z·exp(iω d_k/V) (CT23 Eqs. 5 and 8).

CT23 drop the exp(iω d_k/V) cross terms (their Eq. 6) because coarse spectra cannot resolve them.
We keep them and handle the resolution issue with the debiased likelihood (§3).

## 5. Wheel roughness at rotation orders
Records are angle-synchronous (tachometer resampling), so order n falls exactly on bin 20n. There
are two options:
- **Notch.** Drop the order bins from the likelihood.
- **Tachometer model.** Model each order bin as having mean H·w_n, where the complex amplitude w_n
  is shared by all passes because every record starts at the same wheel angle. The w_n are profiled
  in closed form.

CT23 §5.3.4 instead remove wheel roughness with a notch comb filter before their fit.

## 6. Repeated passes over one section
When records are aligned in position, bin k of every pass sees the same roughness coefficient.
With pass-to-pass coherence ρ (exchangeable model), the covariance of bin k across passes is

  Σ_k = s_k (ρ hh^H + (1 − ρ) diag|h|²) + E.

This is rank one plus a diagonal, so log-det and inverse follow from Sherman–Morrison. ρ is
estimated with the other globals. The oracle bound uses the exact Gaussian Fisher information
tr(Σ⁻¹∂Σ Σ⁻¹∂Σ) with the true, offset-dependent coherence matrix.

## 7. Uncertainty
- **Wald intervals** use the observed information of the profile likelihood (a numerical Hessian).
- **Profile-likelihood intervals** use the 90% χ²₁ cut, re-optimising the other globals and all
  nuisances.
- **CRB** is the expected Fisher information, with all nuisances free and the WIM prior included.

## 8. Model-form bias
The first-order bias of the ML estimate when the data come from another model is

  b ≈ J⁻¹ E[score at the truth],   E[score] = Σ_k D_k (v_true,k / v_k − 1),

with all nuisances free. This is used for bias-per-error sensitivities, and is checked against full
Monte Carlo fits on the rail-oscillator model.
