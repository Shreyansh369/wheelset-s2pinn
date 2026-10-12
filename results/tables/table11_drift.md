# Table 11. Seasonal foundation-stiffness drift between baseline and later period

| Estimator | Later-period k_f | Apparent change, true Δ = 0 (%) | Bias at true Δ = −5% (pp) | SD of Δ (%) | False-alarm rate (nominal 5%) | MDC (%) |
|---|---|---|---|---|---|---|
| nominal | ×0.8 | -2.03 | -2.90 | 0.24 | 1.000 | – |
| nominal | ×0.9 | -0.67 | -1.14 | 0.24 | 0.870 | – |
| nominal | ×1.1 | +0.37 | +0.85 | 0.24 | 0.001 | 1.19 |
| nominal | ×1.2 | +0.77 | +1.68 | 0.24 | 0.000 | 1.82 |
| coest | ×0.8 | -0.00 | -0.00 | 0.24 | 0.050 | 0.71 |
| coest | ×0.9 | -0.00 | +0.00 | 0.24 | 0.050 | 0.71 |
| coest | ×1.1 | -0.00 | -0.00 | 0.24 | 0.050 | 0.71 |
| coest | ×1.2 | -0.00 | +0.00 | 0.24 | 0.050 | 0.71 |
| nominal | ×1.0 (no drift) | 0 | 0 | 0.25 | 0.050 | 0.71 |
| coest | ×1.0 (no drift) | 0 | 0 | 0.25 | 0.050 | 0.72 |

**Monte Carlo check (k_f ×1.2)**

| Estimator | n | False alarms | Rate [95% CI] | Mean Δ̂ (%) |
|---|---|---|---|---|
| nominal | 6 | 0 | 0.00 [0.00, 0.46] | +0.87 |
| coest | 5 | 0 | 0.00 [0.00, 0.52] | -0.02 |


N = 50 passes per period, 40 dB. 'nominal' fits (k_B0, c_B) with k_f, k_H0 at nominal values; 'coest' co-estimates k_f and k_H0 per period.

Source: `results/p2/relative_coest_drift.json`
