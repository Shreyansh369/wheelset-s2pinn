# Table 14. Bias diagnosis on the headline datasets (pinned headline configuration)

**(a) Bias diagnosis on the ten seed-123 headline datasets (variants change one thing each)**

| Estimator / data | Seed | SNR (dB) | n | Bias (%) ± SE | RMSE (%) | RMSE/CRB | Wald cov. | c_B bias (%) | Max |Δ| vs headline (pp) | SE ratio vs headline |
|---|---|---|---|---|---|---|---|---|---|---|
| Headline (frozen estimator) | 123 | 40 | 10 | -0.027 ± 0.057 | 0.172 | 0.99 | 1.00 | +10.6 | – | – |
| Headline (frozen estimator) | 42 | 40 | 10 | +0.083 ± 0.047 | 0.163 | 0.93 | 0.90 | +6.8 | – | – |
| ±30-bin kernel | 123 | 40 | 10 | +0.005 ± 0.058 | 0.174 | 1.00 | 0.90 | +12.4 | 0.053 | 1.001 |
| same data at 60 dB | 123 | 60 | 10 | -0.028 ± 0.056 | 0.171 | 0.99 | 1.00 | +10.6 | 0.016 | 0.998 |
| exact sub-band scoring, 0.25 Hz table | 123 | 40 | 10 | -0.026 ± 0.057 | 0.173 | 1.00 | 1.00 | +10.6 | 0.006 | 1.001 |
| K = 4 roughness levels | 123 | 40 | 10 | -0.076 ± 0.073 | 0.230 | 1.33 | 0.80 | +10.7 | 0.288 | 0.997 |
| K = 1 roughness level | 123 | 40 | 10 | -0.164 ± 0.171 | 0.538 | 3.19 | 0.40 | +9.1 | 1.240 | 0.973 |

**(b) Wald 90% coverage of k_B0 on the 50 headline fits at 40 dB, by standard error**

| Standard error | Median SE (%) | Coverage [95% CI] |
|---|---|---|
| expected information | 0.174 | 0.84 [0.71, 0.93] |
| sandwich, bin clusters | 0.172 | 0.84 [0.71, 0.93] |
| sandwich, 8-bin blocks | 0.175 | 0.82 [0.69, 0.91] |
| sandwich, 61-bin blocks | 0.176 | 0.84 [0.71, 0.93] |

**(c) Regression of the 50 headline errors (40 dB) on pass-design features**

| Feature | r alone (p) |
|---|---|
| speed_sd_kmh | -0.03 (0.818) |
| payload_sd_t | +0.05 (0.707) |
| speed_min_kmh | +0.08 (0.585) |
| bins_near_resonance | +0.08 (0.590) |
| Joint R² / F-test p | 0.02 / 0.947 |


Same datasets (roughness, speeds, payloads, noise draw) for every variant; the headline row is the frozen estimator (debiased, ±120-bin kernel, own-sub-band scoring, 0.5 Hz table, K = 16).

Source: `results/p4/bias_diag_y25.json`
