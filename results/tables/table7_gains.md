# Table 7. Relative change Δk_B0/k_B0: model-form gains, κ and interval coverage

| Parameter | Gain γ per unit log error (nominal) | γ at Δ = −2/−5/−10% | κ term (1σ) | γ with k_f, k_H0 co-estimated |
|---|---|---|---|---|
| unsprung_scale | +1.782 | +1.94, +1.79, +1.61 | 0.053 | +1.313 |
| kH0 | +0.532 | +0.58, +0.51, +0.50 | 0.080 | – |
| axle_damp_scale | -0.020 | -0.16, +0.01, +0.09 | 0.010 | -0.018 |
| kf | +0.684 | +0.30, +0.75, +1.01 | 0.240 | – |
| eta_f | +0.046 | +0.04, +0.05, +0.04 | 0.009 | +0.086 |

| Quantity | Value |
|---|---|
| κ, nominal (mass ±3% / ±1%) | 0.258 / 0.253 |
| κ, k_f and k_H0 co-estimated | 0.044 |
| Combined-interval coverage, control (n=6) | 1.00 [0.54, 1.00] (statistical only 0.67) |
| Combined-interval coverage, kf_x1.2 (n=6) | 1.00 [0.54, 1.00] (statistical only 0.00) |
| Combined-interval coverage, unsprung_x1.05 (n=6) | 1.00 [0.54, 1.00] (statistical only 0.33) |
| Fresh MC, misspecifications drawn from 1σ ranges (n=20): combined coverage | 0.70 [0.46, 0.88] (statistical only 0.35) |
| Fresh MC: rms absolute k_B0 bias / rms relative-change error (fraction of Δ) | 10.16% / 0.420 |


Estimated change error = γ · log(parameter error) · Δ; κ = RSS of γ·σ; combined 90% interval = ±1.645·sqrt(SE² + (κΔ)²).

Source: `results/p2/relative_intervals.json`, `results/p2/relative_coest_drift.json`
