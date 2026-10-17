# Table 11. Seasonal foundation-stiffness drift between baseline and later period

| Estimator | Later-period k_f | Apparent change, true Δ = 0 (%) | Bias at true Δ = −5% (pp) | SD of Δ (%) | False-alarm rate (nominal 5%) | MDC (%) |
|---|---|---|---|---|---|---|
| nominal | ×0.8 | -6.05 | -6.17 | 0.24 | 1.000 | – |
| nominal | ×0.9 | -2.75 | -2.78 | 0.24 | 1.000 | – |
| nominal | ×1.1 | +1.71 | +1.48 | 0.24 | 0.000 | 2.30 |
| nominal | ×1.2 | +1.67 | +0.64 | 0.24 | 0.000 | 1.96 |
| coest | ×0.8 | -0.00 | +0.00 | 0.26 | 0.050 | 0.75 |
| coest | ×0.9 | +0.00 | -0.00 | 0.26 | 0.050 | 0.75 |
| coest | ×1.1 | -0.00 | -0.00 | 0.26 | 0.050 | 0.75 |
| coest | ×1.2 | +0.00 | +0.00 | 0.26 | 0.050 | 0.75 |
| nominal | ×1.0 (no drift) | 0 | 0 | 0.24 | 0.050 | 0.70 |
| coest | ×1.0 (no drift) | 0 | 0 | 0.26 | 0.050 | 0.75 |


N = 50 passes per period, 40 dB. 'nominal' fits (k_B0, c_B) with k_f, k_H0 at nominal values; 'coest' co-estimates k_f and k_H0 per period.

Source: `results/p2/drift_freight.json`
