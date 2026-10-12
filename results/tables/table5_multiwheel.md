# Table 5. Multi-wheel coupling through the rail (k_B0)

**(a) Bound**

| Rail | Wheels | Speeds | N | SNR (dB) | CRB k_B0 (%) | CRB c_B (%) |
|---|---|---|---|---|---|---|
| BS113A | 1 | fixed_100 | 50 | 40 | 0.824 | 31.1 |
| BS113A | 1 | uniform_95_105 | 50 | 40 | 0.381 | 14.5 |
| BS113A | 1 | uniform_60_110 | 50 | 40 | 0.169 | 6.8 |
| BS113A | 2 | fixed_100 | 50 | 40 | 0.802 | 29.7 |
| BS113A | 2 | uniform_95_105 | 50 | 40 | 0.379 | 14.3 |
| BS113A | 2 | uniform_60_110 | 50 | 40 | 0.164 | 6.4 |
| BS113A | 4 | fixed_100 | 50 | 40 | 0.878 | 32.7 |
| BS113A | 4 | uniform_95_105 | 50 | 40 | 0.367 | 13.9 |
| BS113A | 4 | uniform_60_110 | 50 | 40 | 0.166 | 6.5 |
| BS113A | 8 | fixed_100 | 50 | 40 | 0.756 | 28.3 |
| BS113A | 8 | uniform_95_105 | 50 | 40 | 0.398 | 15.1 |
| BS113A | 8 | uniform_60_110 | 50 | 40 | 0.167 | 6.5 |
| 60E1 | 1 | uniform_60_110 | 50 | 40 | 0.170 | 6.8 |
| 60E1 | 2 | uniform_60_110 | 50 | 40 | 0.168 | 6.5 |
| 60E1 | 4 | uniform_60_110 | 50 | 40 | 0.170 | 6.6 |
| 60E1 | 8 | uniform_60_110 | 50 | 40 | 0.169 | 6.6 |

**(b) Monte Carlo, 60–110 km/h, N = 50, 40 dB**

| Wheels | Fitted model | Datasets | Bias (%) ± SE | RMSE (%) | RMSE/CRB | Wald 90% cov. [95% CI] |
|---|---|---|---|---|---|---|
| 2 | rail-coupled | 10 | 0.24 ± 0.07 | 0.32 | 1.91 | 0.50 [0.19, 0.81] |
| 2 | single wheelset | 10 | -13.34 ± 0.08 | 14.32 | 85.89 | 0.10 [0.00, 0.45] |
| 4 | rail-coupled | 10 | 0.12 ± 0.04 | 0.17 | 0.98 | 0.90 [0.55, 1.00] |
| 4 | single wheelset | 10 | -13.85 ± 0.07 | 14.91 | 87.88 | 0.00 [0.00, 0.31] |
| 8 | rail-coupled | 10 | 0.04 ± 0.04 | 0.14 | 0.81 | 0.90 [0.55, 1.00] |
| 8 | single wheelset | 10 | -8.60 ± 0.09 | 9.00 | 52.86 | 0.00 [0.00, 0.31] |


The 2-wheel rail-coupled bias is an open item (docs/paper1_outline.md).

Source: `results/p2/multiwheel_bound.json`, `results/p2/multiwheel_mc.json`
