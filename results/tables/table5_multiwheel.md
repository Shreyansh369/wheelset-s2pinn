# Table 5. Multi-wheel coupling through the rail (k_B0)

**(a) Bound**

| Rail | Wheels | Speeds | N | SNR (dB) | CRB k_B0 (%) | CRB c_B (%) |
|---|---|---|---|---|---|---|
| 60E1 | 1 | fixed_100 | 50 | 40 | 0.811 | 36.9 |
| 60E1 | 1 | uniform_95_105 | 50 | 40 | 0.398 | 18.6 |
| 60E1 | 1 | uniform_60_110 | 50 | 40 | 0.166 | 7.5 |
| 60E1 | 2 | fixed_100 | 50 | 40 | 0.822 | 37.3 |
| 60E1 | 2 | uniform_95_105 | 50 | 40 | 0.411 | 19.2 |
| 60E1 | 2 | uniform_60_110 | 50 | 40 | 0.161 | 7.3 |
| 60E1 | 4 | fixed_100 | 50 | 40 | 0.906 | 41.2 |
| 60E1 | 4 | uniform_95_105 | 50 | 40 | 0.401 | 18.8 |
| 60E1 | 4 | uniform_60_110 | 50 | 40 | 0.164 | 7.4 |
| 60E1 | 8 | fixed_100 | 50 | 40 | 0.774 | 35.0 |
| 60E1 | 8 | uniform_95_105 | 50 | 40 | 0.432 | 20.2 |
| 60E1 | 8 | uniform_60_110 | 50 | 40 | 0.165 | 7.5 |

**(b) Monte Carlo, 60–110 km/h, N = 50, 40 dB**

| Wheels | Fitted model | Datasets | Bias (%) ± SE | RMSE (%) | RMSE/CRB | Wald 90% cov. [95% CI] |
|---|---|---|---|---|---|---|
| 2 | rail-coupled | 10 | 0.11 ± 0.05 | 0.18 | 1.10 | 0.80 [0.44, 0.97] |
| 2 | single wheelset | 10 | -5.09 ± 0.16 | 5.25 | 31.80 | 0.00 [0.00, 0.31] |
| 4 | rail-coupled | 10 | 0.02 ± 0.06 | 0.18 | 1.07 | 0.90 [0.55, 1.00] |
| 4 | single wheelset | 10 | -5.38 ± 0.21 | 5.57 | 33.19 | 0.00 [0.00, 0.31] |
| 8 | rail-coupled | 10 | -0.02 ± 0.06 | 0.18 | 1.09 | 0.90 [0.55, 1.00] |
| 8 | single wheelset | 10 | -2.80 ± 0.22 | 2.91 | 17.29 | 0.00 [0.00, 0.31] |


Rail-coupled bias beyond 2 SE: 2-wheel +0.11 ± 0.05% (2.2 SE); not explained (open item, docs/paper1_outline.md).

Source: `results/p2/multiwheel_bound.json`, `results/p2/multiwheel_mc_y25.json`
