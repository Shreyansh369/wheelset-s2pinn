# Table 10. Repeated passes over one section with partial coherence (k_B0)

**(a) Independent-pass estimator on partially coherent data**

| ρ | n | Bias (%) ± SE | RMSE (%) | Variance | Median SE (%) | RMSE/SE | 90% cov. [95% CI] |
|---|---|---|---|---|---|---|---|
| 0.5 | 12 | 0.01 ± 0.06 | 0.19 | model SE | 0.23 | 0.82 | 0.83 [0.52, 0.98] |
| 0.5 | 12 | 0.01 ± 0.06 | 0.19 | sandwich, bin clusters | 0.17 | 1.10 | 0.83 [0.52, 0.98] |
| 0.5 | 12 | 0.01 ± 0.06 | 0.19 | sandwich, pass clusters | 0.15 | 1.24 | 0.83 [0.52, 0.98] |
| 0.7 | 12 | 0.04 ± 0.05 | 0.19 | model SE | 0.23 | 0.82 | 1.00 [0.74, 1.00] |
| 0.7 | 12 | 0.04 ± 0.05 | 0.19 | sandwich, bin clusters | 0.17 | 1.09 | 0.75 [0.43, 0.95] |
| 0.7 | 12 | 0.04 ± 0.05 | 0.19 | sandwich, pass clusters | 0.13 | 1.41 | 0.83 [0.52, 0.98] |
| 0.9 | 12 | 0.09 ± 0.03 | 0.15 | model SE | 0.23 | 0.64 | 1.00 [0.74, 1.00] |
| 0.9 | 12 | 0.09 ± 0.03 | 0.15 | sandwich, bin clusters | 0.14 | 1.08 | 0.92 [0.62, 1.00] |
| 0.9 | 12 | 0.09 ± 0.03 | 0.15 | sandwich, pass clusters | 0.13 | 1.12 | 0.83 [0.52, 0.98] |

**(b) Bounds and the exchangeable-ρ likelihood**

| ρ | Oracle CRB (%) | Exchangeable, ρ estimated: CRB (%) | Independent CRB (%) | Exchangeable MC bias (%) ± SE | Exchangeable MC RMSE (%) | Exchangeable Wald cov. |
|---|---|---|---|---|---|---|
| 0.5 | 0.005 | 0.182 | 0.225 | 0.08 ± 0.11 | 0.37 | 0.67 [0.35, 0.90] |
| 0.7 | 0.004 | 0.156 | 0.225 | 0.09 ± 0.06 | 0.21 | 0.75 [0.43, 0.95] |
| 0.9 | 0.005 | 0.120 | 0.241 | 0.10 ± 0.05 | 0.19 | 0.50 [0.21, 0.79] |


The oracle assumes the coherence matrix is known exactly; it is not achievable in practice.

Source: `results/p2/partial_indep.json`, `results/p2/partial_coherence_bound.json`, `results/p2/partial_coherence_mc.json`
