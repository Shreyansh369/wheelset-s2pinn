# Table 16. Relative change under simultaneous model errors (κ replicates) (earlier configuration: metro wheel layout, BS113A rail, +-30-bin kernel)

**(a) Relative change under simultaneous model errors, co-estimating fit**

| Quantity | Value |
|---|---|
| n (stratified k_f draws) | 20 |
| k_f range drawn | ×0.58 – ×2.19 |
| Coverage, κ = 0.044 | 0.70 [0.46, 0.88] |
| Coverage, statistical only | 0.65 [0.41, 0.85] |
| Interval inflation for 90% coverage | 1.37 |
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

**(b) Coverage of the change by standard error (κ = 0.044; slope correction 0.99998)**

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
