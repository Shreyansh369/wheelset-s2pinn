# Table 3. Headline Monte Carlo, 4-wheel rail-coupled model, frozen estimator (k_B0)

| SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | RMSE/SE | Wald 90% coverage [95% CI] | Simulation calibration: bias b, inflation r; held-out coverage | Ignore coupling (seed 42, ±30-bin kernel): bias (%) |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 50 | 0.10 ± 0.02 | 0.19 | 0.18 | 1.09 | 1.08 | 0.90 [0.78, 0.97] | none (uncalibrated coverage ≥ 0.85) | -13.91 ± 0.05 |
| 40 | 50 | 0.09 ± 0.03 | 0.24 | 0.17 | 1.39 | 1.39 | 0.76 [0.62, 0.87] | b = +0.093%, r = 1.39; split A 0.80 [0.56, 0.94], split B 0.97 [0.83, 1.00] | -13.98 ± 0.08 |


N = 50 passes, 60–110 km/h, 5 seeds × 10 datasets. Frozen estimator: debiased Whittle, kernel ±120 bins, own-sub-band scoring, K = 16, load exponent fixed. Split A calibrates on seeds 42/123/456 and tests on 789/1024; split B the reverse.

Source: `results/p3/headline_v2_kb120_attr.json`, `results/p3/calibrated.json`, `results/p2/headline_mw.json`
