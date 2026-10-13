# Table 14. Validation Monte Carlo: κ revalidation, drift at k_f ×0.8, bias diagnosis

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

**(c) Bias diagnosis on paired datasets (same data, different SNR or estimator)**

| Seed | Estimator | SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | Wald cov. |
|---|---|---|---|---|---|---|---|---|
| 42 | base | 20 | 10 | -0.068 ± 0.080 | 0.249 | 0.179 | 1.40 | 0.90 |
| 42 | base | 40 | 10 | +0.021 ± 0.075 | 0.226 | 0.170 | 1.33 | 0.90 |
| 42 | base | 60 | 10 | +0.022 ± 0.075 | 0.227 | 0.170 | 1.33 | 0.80 |
| 42 | refined | 40 | 10 | +0.021 ± 0.075 | 0.225 | 0.170 | 1.32 | 0.80 |
| 123 | base | 40 | 10 | +0.277 ± 0.047 | 0.310 | 0.169 | 1.83 | 0.40 |
| 123 | base | 60 | 10 | +0.284 ± 0.047 | 0.316 | 0.169 | 1.87 | 0.30 |
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


Source: `results/p3/validation_mc.json`, `results/p3/bias_regression.json`
