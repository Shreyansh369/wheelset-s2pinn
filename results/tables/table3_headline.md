# Table 3. Headline Monte Carlo, 4-wheel rail-coupled model (k_B0)

| SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | Wald 90% coverage [95% CI] | Profile 90% coverage (seed 42) | Ignore coupling (seed 42): bias (%) ± SE; Wald cov. |
|---|---|---|---|---|---|---|---|---|
| 20 | 50 | 0.11 ± 0.02 | 0.20 | 0.18 | 1.12 (seed sd 0.13) | 0.88 [0.76, 0.95] | 0.80 (n=10) | -13.91 ± 0.05; cov. 0.00 |
| 40 | 50 | 0.15 ± 0.03 | 0.26 | 0.17 | 1.56 (seed sd 0.26) | 0.70 [0.55, 0.82] | 0.90 (n=10) | -13.98 ± 0.08; cov. 0.00 |


N = 50 passes, 60–110 km/h, 5 seeds × 10 datasets, debiased Whittle likelihood. The ignore-coupling column fits the same data with the single-wheelset model on the same rail.

Source: `results/p2/headline_mw.json`
