# Table 3. Headline Monte Carlo, 4-wheel rail-coupled model, frozen estimator (k_B0)

| SNR (dB) | n | Bias (%) ± SE | RMSE (%) | CRB (%) | RMSE/CRB | RMSE/SE | Wald 90% coverage [95% CI] | Simulation calibration: bias b, inflation r; held-out coverage | Ignore coupling (seed 42, 10 datasets): bias (%) ± SE |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 100 | 0.01 ± 0.02 | 0.21 | 0.19 | 1.13 | 1.13 | 0.85 [0.76, 0.91] | none (uncalibrated coverage ≥ 0.85) | – |
| 40 | 100 | 0.05 ± 0.02 | 0.18 | 0.17 | 1.09 | 1.08 | 0.84 [0.75, 0.91] | b = +0.048%, r = 1.08; split A 0.90 [0.78, 0.97], split B 0.92 [0.81, 0.98] | -5.55 ± 0.20 (covered 0/10) |


N = 50 passes, 60–110 km/h, 10 seeds × 10 datasets per SNR. Frozen estimator: debiased Whittle, kernel ±120 bins, own-sub-band scoring, K = 16, load exponent fixed. Split A calibrates on seeds 42/123/456/789/1024 and tests on 2048/3141/5772/8128/9973 (whole seeds); split B the reverse.

Source: `results/p3/headline_v2_kb120_attr_frozen10.json`, `results/p3/calibrated.json`, `results/p4/ignore_coupling.json`
