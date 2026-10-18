# Table 16. Relative change under simultaneous model errors (κ replicates) (partly earlier configuration: metro wheel layout, BS113A rail, +-30-bin kernel)

**(a) Relative change under simultaneous model errors, co-estimating fit**

| Quantity | Value |
|---|---|
| n (stratified k_f draws) | 34 |
| k_f range drawn | ×0.26 – ×3.80 |
| Coverage, κ = 0.12791109736480646 | 0.82 [0.65, 0.93] |
| Coverage, statistical only | 0.53 [0.35, 0.70] |
| Interval inflation for 90% coverage | 1.25 |
| rms change error (fraction of Δ) | 0.151 |
| mean change error (fraction of Δ) | -0.020 |
| rms absolute k_B0 bias, base period (%) | 16.06 |

**Worst cases**

| Rep | k_f | η_f | k_H0 | Unsprung | Axle damping | True change (%) | Estimated (%) | Error (fraction of Δ) | Covered |
|---|---|---|---|---|---|---|---|---|---|
| 35 | ×0.26 | ×1.01 | ×0.77 | ×1.00 | ×1.31 | -3.83 | -48.22 | -15.859 | no |
| 6 | ×0.65 | ×0.95 | ×1.18 | ×1.01 | ×3.89 | -6.89 | -9.42 | -0.386 | no |
| 37 | ×0.35 | ×0.82 | ×1.02 | ×1.02 | ×3.02 | -9.55 | -12.82 | -0.366 | no |
| 1 | ×1.40 | ×0.83 | ×0.86 | ×0.99 | ×1.90 | -4.14 | -5.48 | -0.334 | no |
| 26 | ×0.84 | ×0.98 | ×0.87 | ×1.01 | ×3.24 | -9.74 | -12.22 | -0.272 | yes |

**(b) Coverage of the change by standard error (earlier configuration; κ = 0.044; slope correction 0.99998)**

| SE of the change | Median SE (%) | Statistical only | With κ | With κ and slope correction |
|---|---|---|---|---|
| stored (fit) | 0.250 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| expected information | 0.254 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, bin clusters | 0.261 | 13/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, 8-bin blocks | 0.288 | 14/20 | 14/20 [0.46, 0.88] | 14/20 |
| sandwich, 61-bin blocks | 0.348 | 14/20 | 16/20 [0.56, 0.94] | 16/20 |

**(c) Calibration of the change, correct model (pseudo-true, k_f and k_H0 co-estimated)**

| True change (%) | Estimated change (%) |
|---|---|
| -2.0 | -2.0000 |
| -5.0 | -5.0000 |
| -10.0 | -9.9998 |
| Slope | 0.99998 |


All five uncertain model parameters drawn at random from their 1σ ranges in every replicate; true change 2–10% decrease.

Source: `results/p3/validation_mc.json`, `results/p3/robust_se.json`, `results/p3/calibration.json`
