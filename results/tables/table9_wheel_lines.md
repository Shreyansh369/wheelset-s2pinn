# Table 9. Wheel roughness at rotation orders: notch vs tachometer nuisance lines

**(a) Bound, N = 50, 40 dB**

| Speeds | Wheel-line level above roughness (dB) | Method | CRB k_B0 (%) | CRB c_B (%) |
|---|---|---|---|---|
| fixed_100 | – | no_wheel_roughness | 0.624 | 21.5 |
| fixed_100 | 0 | notch | 0.639 | 22.0 |
| fixed_100 | 0 | tacho | 0.489 | 16.6 |
| fixed_100 | 10 | notch | 0.640 | 22.0 |
| fixed_100 | 10 | tacho | 0.242 | 8.2 |
| uniform_60_110 | – | no_wheel_roughness | 0.228 | 7.5 |
| uniform_60_110 | 0 | notch | 0.232 | 7.7 |
| uniform_60_110 | 0 | tacho | 0.179 | 5.2 |
| uniform_60_110 | 10 | notch | 0.232 | 7.7 |
| uniform_60_110 | 10 | tacho | 0.096 | 2.3 |

**(b) Monte Carlo, 60–110 km/h**

| Level (dB) | Method | n | Bias (%) ± SE | RMSE/CRB | Wald 90% cov. [95% CI] |
|---|---|---|---|---|---|
| 0 | ignore | 10 | -0.01 ± 0.07 | 0.89 | 0.90 [0.55, 1.00] |
| 0 | notch | 10 | 0.02 ± 0.09 | 1.21 | 0.80 [0.44, 0.97] |
| 0 | tacho | 10 | -0.02 ± 0.06 | 0.99 | 0.80 [0.44, 0.97] |
| 10 | ignore | 10 | -0.11 ± 0.06 | 0.96 | 0.90 [0.55, 1.00] |
| 10 | notch | 10 | 0.06 ± 0.07 | 0.87 | 0.90 [0.55, 1.00] |
| 10 | tacho | 10 | 0.02 ± 0.04 | 1.19 | 0.80 [0.44, 0.97] |


Source: `results/p2/wheel_lines_bound.json`, `results/p2/wheel_lines_mc.json`
