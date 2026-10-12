# FE-direct Whittle estimator: Monte Carlo results (scenario a, option iv)

Code: `src/inverse/whittle.py`, `experiments/p1_fe_direct.py`, `experiments/p1_fe_direct_taper_compare.py`.
Results: `results/p1/fe_direct.json` (per cell), `results/p1/fe_direct_runs/*.jsonl` (per dataset),
`results/p1/fe_direct_taper_compare.json`.

## Setup
- **Data.** Reference FE model: direct solves on 0.25 Hz. Hertz contact, rail oscillator, left-axlebox acceleration.
  - 20-revolution records, fs = 2 kHz, bins 50–700 Hz, SNR 40 dB.
  - Roughness has the ISO 3095:2013 Fig. 2 shape, realised on a wavenumber grid 4× finer than the bins. The 4T record is truncated to T, so leakage is realistic.
  - Per-sub-band levels (K = 16 per one-third octave) are drawn with 3 dB (1 sigma) deviations from the ISO shape, new for each dataset.
- **Truth.** kB0 = 0.85e9 N/m (15% stiffness loss), cB = 6e3 N s/m. Start point is nominal (1e9, 5e3).
- **Passes.** Payload uniform 5.5–22.5 t, measured with 3% (1 sigma) WIM error. Speeds:
  - fixed 100 km/h;
  - uniform 95–105 km/h;
  - uniform 60–110 km/h.
- **Estimator.** Maximum-likelihood Whittle fit across passes.
  - Model H: exact complex-modal, 25 log-W nodes, 0.5 Hz grid.
  - Nuisances profiled out by Fisher scoring: about 250 sub-band levels plus N per-pass log W with the WIM prior.
  - Outer 2-D problem by Nelder–Mead. Standard errors from the observed profile Hessian.
  - CRB: the expected Fisher information at the truth over all parameters.
- 20 random datasets per cell. Wald 90% coverage, with Clopper–Pearson 95% intervals on the coverage fraction.

## Results (rectangular window, all bins)
| N | speeds | kB0 bias | kB0 RMSE | CRB | RMSE/CRB | cov90 | cB RMSE | cB CRB | cB cov90 | s/eval | s/fit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 | fixed 100 | −0.09 ± 0.15% | 0.64% | 0.66% | 0.97 | 0.90 [0.68, 0.99] | 22.6% | 22.7% | 1.00 | 0.50 | 41 |
| 50 | 95–105 | +0.07 ± 0.07% | 0.33% | 0.47% | 0.70 | 1.00 [0.83, 1.00] | 17.9% | 16.8% | 0.85 | 0.49 | 37 |
| 50 | 60–110 | +0.09 ± 0.04% | 0.20% | 0.23% | 0.89 | 0.95 [0.75, 1.00] | 7.7% | 7.4% | 0.85 | 0.49 | 38 |
| 200 | fixed 100 | +0.10 ± 0.07% | 0.31% | 0.32% | 0.96 | 0.95 [0.75, 1.00] | 13.9% | 11.0% | 0.80 | 1.21 | 93 |
| 200 | 95–105 | +0.04 ± 0.05% | 0.22% | 0.22% | 0.98 | 0.95 [0.75, 1.00] | 6.9% | 7.9% | 0.90 | 1.21 | 93 |
| 200 | 60–110 | +0.00 ± 0.03% | 0.11% | 0.12% | 0.95 | 0.90 [0.68, 0.99] | 4.1% | 3.7% | 0.85 | 1.32 | 103 |

- Pooled kB0 coverage is 113/120 = 0.94 [0.88, 0.98]. Pooled cB coverage is 105/120 = 0.875 [0.80, 0.93].
- All 120 fits converged. Worst single kB0 error: 1.19% (N = 50, fixed speed).
- kB0 bias is at most 0.1%, i.e. ≤ 2 standard errors in every cell. N = 50 at 60–110 km/h shows +0.086 ± 0.043%, which is 2 SE. That is small against the CRB, but the cell with the largest bias/SE should be watched.
- cB at N = 200 and fixed speed: RMSE/CRB = 1.26 and coverage 0.80. This is the only cell where the asymptotics look strained.
- With 20 datasets per cell, RMSE/CRB carries about ±16% sampling error and coverage about ±0.07 (1 sigma).

## Taper check (N = 50, same datasets, paired by seed)
Hann taper in both the floor estimate and the likelihood; every second bin, because adjacent Hann bins correlate. The reference CRB uses the true sensor-noise floor, a rectangular window and all bins.

| speeds | taper | floor / true noise | kB0 bias | kB0 RMSE / CRB_ref | own CRB / CRB_ref | cov90 (observed SE) | cB RMSE / CRB_ref | cB cov90 |
|---|---|---|---|---|---|---|---|---|
| fixed 100 | rect | 5.39 | −0.09 ± 0.15% | 0.97 | 1.00 | 0.90 | 1.00 | 1.00 |
| fixed 100 | Hann | 1.00 | −0.09 ± 0.19% | 1.24 | 1.38 | 0.95 | 1.56 | 1.00 |
| 95–105 | rect | 5.90 | +0.07 ± 0.07% | 0.70 | 1.00 | 1.00 | 1.06 | 0.85 |
| 95–105 | Hann | 1.00 | −0.20 ± 0.13% | 1.25 | 1.37 | 0.95 | 1.64 | 0.85 |
| 60–110 | rect | 4.87 | +0.09 ± 0.04% | 0.89 | 1.00 | 0.95 | 1.04 | 0.85 |
| 60–110 | Hann | 1.00 | +0.06 ± 0.07% | 1.43 | 1.28 | 0.85 | 1.74 | 0.85 |

1. The Hann taper fixes the floor estimate, from about 5× the true noise to 1.00×.
2. **The leakage-inflated floor did not widen the intervals here.** The rectangular CRB with the measured (inflated) floor equals the CRB with the true floor (ratio 1.00 to two decimals). The observed SE over CRB_ref is 0.99–1.01. At 40 dB SNR the floor sits far below the in-band signal, so a 5× error in it carries no weight in the Fisher information. The rectangular coverage is therefore not inflated by the floor. This holds only at this SNR and dynamic range; the effect will grow at lower SNR or where |H|² dips deeply.
3. **No sign that leakage breaks the independent-bin assumption at this level.** For the rectangular estimator, RMSE/CRB is 0.70–0.97 and coverage 0.90–1.00, within the ±16% / ±0.07 sampling error of 20 datasets. A real violation would show RMSE above the CRB and coverage below nominal.
4. **The tapered estimator is worse.** Its own CRB is 1.28–1.38× the reference, from decimation plus taper loss. Its RMSE is 1.24–1.43× the reference CRB for kB0 and 1.56–1.74× for cB. Coverage with its own observed SE is 0.85–0.95. Its RMSE exceeds its own nominal CRB by up to 1.11× (kB0) and 1.25× (cB), probably from the residual lag-2 bin correlation (|ρ|² ≈ 0.03) and the local-spectrum approximation.
5. **Recommendation.** Keep the rectangular estimator at this SNR, and flag the floor as "noise plus leakage" in the paper. Rerun the paired check at 20 dB before claiming robustness to the floor. If tapering becomes necessary, a multitaper or full-bin Hann likelihood with the bin covariance would recover most of the lost efficiency.

## Taper check at 20 dB SNR (N = 50, paired, 20 datasets per speed case)
Source: `results/p1/fe_direct_taper_compare_snr20.json`. The datasets are new (the seed key includes the SNR), so they are not paired with the 40 dB runs. All 120 fits converged.

| speeds | taper | floor / noise | kB0 bias | kB0 RMSE / CRB_ref | cov90 kB0 | cB bias | cB RMSE / CRB_ref | cov90 cB |
|---|---|---|---|---|---|---|---|---|
| fixed 100 | rect | 1.04 | −0.10 ± 0.18% | 1.22 | 0.80 | +3.8 ± 5.6% | 1.12 | 0.85 |
| fixed 100 | Hann | 1.00 | −0.12 ± 0.26% | 1.70 | 0.90 | −2.4 ± 5.9% | 1.35 | 1.00 |
| 95–105 | rect | 1.05 | −0.06 ± 0.11% | 1.05 | 0.95 | +6.4 ± 3.3% | 0.91 | 0.85 |
| 95–105 | Hann | 1.00 | −0.03 ± 0.13% | 1.29 | 0.90 | −4.1 ± 4.5% | 1.43 | 0.95 |
| 60–110 | rect | 1.04 | +0.09 ± 0.06% | 1.12 | 0.85 | +4.9 ± 1.6% | 1.06 | 0.80 |
| 60–110 | Hann | 1.00 | +0.07 ± 0.08% | 1.51 | 0.90 | +2.3 ± 2.5% | 1.47 | 0.85 |

1. At 20 dB, leakage is negligible next to the sensor noise: the measured rectangular floor is only 1.04–1.05× the true noise. The CRB barely changes from 40 dB (kB0: 0.66% / 0.44% / 0.23%).
2. **kB0, rectangular window.** Bias is within 1.5 SE, and RMSE/CRB is 1.05–1.22. Pooled coverage is 52/60 = 0.87.
3. **kB0, Hann.** RMSE/CRB_ref is 1.29–1.70, about 1.3× its own CRB inflation. Pooled coverage is 54/60 = 0.90, slightly closer to nominal.
4. **cB, rectangular window.** At 60–110 km/h the bias is +4.9 ± 1.6% (3 SE). cB is a secondary output, but this bias is real at N = 50 and 20 dB.
5. **Verdict.** Unchanged: keep the rectangular estimator, since Hann costs 1.3–1.7× in RMSE. Rectangular kB0 coverage at 20 dB sits at the low edge of [0.85, 0.95]. A profile-likelihood interval should replace Wald before any coverage claim.
