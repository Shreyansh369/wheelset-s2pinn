# Table 3. Headline Monte Carlo, 4-wheel rail-coupled model, frozen estimator (k_B0)

| SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | RMSE/SE | Wald 90% coverage [95% CI] | Simulation calibration: bias b, inflation r; held-out coverage | Ignore coupling (seed 42, 10 datasets): bias (%) ± SE |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 50 | -0.01 ± 0.03 | 0.20 | 0.20 | 1.04 | 1.04 | 0.88 [0.76, 0.95] | none (uncalibrated coverage ≥ 0.85) | – |
| 40 | 50 | 0.07 ± 0.02 | 0.19 | 0.17 | 1.08 | 1.07 | 0.84 [0.71, 0.93] | b = +0.069%, r = 1.07; split A 0.80 [0.56, 0.94], split B 0.97 [0.83, 1.00] | -5.55 ± 0.20 (covered 0/10) |


N = 50 passes, 60–110 km/h, 5 seeds × 10 datasets. Frozen estimator: debiased Whittle, kernel ±120 bins, own-sub-band scoring, K = 16, load exponent fixed. Split A calibrates on seeds 42/123/456 and tests on 789/1024; split B the reverse.

Source: `results/p3/headline_v2_kb120_attr_freight.json`, `results/p3/calibrated.json`, `results/p4/ignore_coupling.json`
