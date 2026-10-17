# Table 14. Validation: κ revalidation, drift at k_f ×0.8, bias diagnosis, robust standard errors, calibration (earlier configuration: kappa replicates and bias diagnosis: metro wheel layout; metro wheel layout, BS113A rail; metro wheel layout, BS113A rail, +-30-bin kernel)

**(a) κ revalidation, co-estimating fit**

| Quantity | Value |
|---|---|
| n (stratified k_f draws) | 20 |
| k_f range drawn | ×0.58 – ×2.19 |
| Coverage, κ = 0.044 | 0.70 [0.46, 0.88] |
| Coverage, statistical only | 0.65 [0.41, 0.85] |
| rms change error (fraction of Δ) | 0.096 |
| mean change error (fraction of Δ) | +0.057 |
| rms absolute k_B0 bias, base period (%) | 3.25 |

**Worst cases**

| Rep | k_f | η_f | k_H0 | Unsprung | Axle damping | True change (%) | Estimated (%) | Error (fraction of Δ) | Covered |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ×1.22 | ×0.85 | ×0.83 | ×0.99 | ×1.53 | -4.14 | -3.42 | +0.177 | no |
| 5 | ×0.93 | ×1.60 | ×0.94 | ×1.04 | ×2.25 | -9.22 | -7.82 | +0.158 | no |
| 13 | ×0.62 | ×0.87 | ×1.11 | ×1.03 | ×0.96 | -2.31 | -2.01 | +0.133 | yes |
| 4 | ×0.65 | ×0.87 | ×1.20 | ×1.03 | ×1.36 | -6.06 | -5.32 | +0.126 | no |
| 3 | ×0.86 | ×1.02 | ×0.96 | ×0.99 | ×1.37 | -6.59 | -5.83 | +0.119 | no |

**(b) Drift Monte Carlo (true change 0)**

| Later k_f | Estimator | n | False alarms | Rate [95% CI] | Mean Δ̂ (%) | SD Δ̂ (%) | Median SE (%) |
|---|---|---|---|---|---|---|---|
| ×0.8 | nominal | 20 | 20 | 1.00 [0.83, 1.00] | -2.21 | 0.35 | 0.27 |
| ×0.8 | coest | 20 | 1 | 0.05 [0.00, 0.25] | -0.02 | 0.22 | 0.24 |
| ×0.8 | nominal | 20 | 20 | 1.00 [0.83, 1.00] | -5.85 | 0.81 | 0.25 |
| ×0.8 | coest | 20 | 0 | 0.00 [0.00, 0.17] | +0.07 | 0.25 | 0.25 |

**(c) Bias diagnosis on paired datasets (same data, different SNR or estimator)**

| Seed | Estimator | SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | Wald cov. |
|---|---|---|---|---|---|---|---|---|
| 42 | base | 20 | 10 | -0.068 ± 0.080 | 0.249 | 0.179 | 1.40 | 0.90 |
| 42 | base | 40 | 10 | +0.021 ± 0.075 | 0.226 | 0.170 | 1.33 | 0.90 |
| 42 | base | 60 | 10 | +0.022 ± 0.075 | 0.227 | 0.170 | 1.33 | 0.80 |
| 42 | refined | 40 | 10 | +0.021 ± 0.075 | 0.225 | 0.170 | 1.32 | 0.80 |
| 123 | base | 40 | 10 | +0.277 ± 0.047 | 0.310 | 0.169 | 1.83 | 0.40 |
| 123 | base | 60 | 10 | +0.284 ± 0.047 | 0.316 | 0.169 | 1.87 | 0.30 |
| 123 | kb120 | 40 | 10 | +0.219 ± 0.046 | 0.259 | 0.169 | 1.53 | 0.70 |
| 123 | kb120_K1 | 40 | 10 | +0.046 ± 0.284 | 0.854 | 0.164 | 5.22 | 0.20 |
| 123 | kb120_K4 | 40 | 10 | +0.239 ± 0.059 | 0.297 | 0.169 | 1.76 | 0.70 |
| 123 | refined | 40 | 10 | +0.274 ± 0.047 | 0.307 | 0.169 | 1.81 | 0.40 |

**(d) Regression of the 50 headline errors (40 dB) on pass-design features**

| Feature | Coef. (% per SD) | t | p | r alone (p) |
|---|---|---|---|---|
| speed_sd_kmh | -0.044 | -1.39 | 0.171 | -0.23 (0.110) |
| payload_sd_t | +0.064 | +2.09 | 0.042 | +0.33 (0.021) |
| speed_min_kmh | +0.031 | +1.00 | 0.324 | +0.17 (0.228) |
| bins_near_resonance | +0.031 | +1.01 | 0.320 | +0.17 (0.247) |
| Intercept (mean error) | +0.146 |  |  |  |
| R² / F-test p | 0.19 |  | 0.049 |  |
| Seed one-way ANOVA p |  |  | 0.036 |  |

**(e) Wald 90% coverage of k_B0 on the 50 headline fits per SNR, by standard error**

| SE | 20 dB: coverage [95% CI] | 40 dB: coverage [95% CI] | 20 dB: median SE (%) | 40 dB: median SE (%) | 20 dB: RMSE / median SE | 40 dB: RMSE / median SE |
|---|---|---|---|---|---|---|
| observed information (stored) | 0.88 [0.76, 0.95] | 0.70 [0.55, 0.82] | 0.178 | 0.170 | 1.12 | 1.55 |
| expected information | 0.88 [0.76, 0.95] | 0.68 [0.53, 0.80] | 0.177 | 0.170 | 1.12 | 1.55 |
| sandwich, bin clusters | 0.88 [0.76, 0.95] | 0.62 [0.47, 0.75] | 0.172 | 0.165 | 1.16 | 1.60 |
| sandwich, 8-bin blocks | 0.88 [0.76, 0.95] | 0.72 [0.58, 0.84] | 0.178 | 0.177 | 1.12 | 1.49 |
| sandwich, 61-bin blocks | 0.90 [0.78, 0.97] | 0.74 [0.60, 0.85] | 0.181 | 0.179 | 1.10 | 1.47 |

**(f) κ replicates (n = 20): coverage of the change, κ = 0.044, slope correction 0.99998**

| SE of the change | Median SE (%) | Statistical only | With κ | With κ and slope correction |
|---|---|---|---|---|
| stored (fit) | 0.250 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| expected information | 0.254 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, bin clusters | 0.261 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, 8-bin blocks | 0.288 | 14/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, 61-bin blocks | 0.348 | 14/20 | 16/20 [0.56, 0.94] | 16/20 |

**(g) Calibration of the change, correct model (pseudo-true, k_f and k_H0 co-estimated)**

| True change (%) | Estimated change (%) |
|---|---|
| -2.0 | -2.0000 |
| -5.0 | -5.0000 |
| -10.0 | -9.9998 |
| Slope | 0.99998 |


The slope correction and the sandwich SEs were not tuned on the κ replicates. kb120 = debiasing kernel half-width 120 bins (default 30).

Source: `results/p3/validation_mc.json`, `results/p3/bias_regression.json`, `results/p3/robust_se.json`, `results/p3/calibration.json`
