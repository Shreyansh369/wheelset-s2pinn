# Table 8. Minimum detectable decrease of k_B0 (5% false alarm, 90% detection)

| N per period | SNR (dB) | Model-form term | SD of Δ at Δ = 0 (%) | MDC from CRB (%) | MDC with RMSE/CRB inflation (%) | Inflation |
|---|---|---|---|---|---|---|
| 50 | 20 | mass3pct | 0.24 | 0.81 | 0.81 | 1.00 |
| 50 | 20 | mass1pct | 0.24 | 0.81 | 0.81 | 1.00 |
| 50 | 20 | no_model_form | 0.24 | 0.71 | 0.71 | 1.00 |
| 50 | 40 | mass3pct | 0.24 | 0.80 | 0.94 | 1.18 |
| 50 | 40 | mass1pct | 0.24 | 0.79 | 0.94 | 1.18 |
| 50 | 40 | no_model_form | 0.24 | 0.70 | 0.83 | 1.18 |
| 200 | 20 | mass3pct | 0.12 | 0.41 | 0.41 | 1.00 |
| 200 | 20 | mass1pct | 0.12 | 0.41 | 0.41 | 1.00 |
| 200 | 20 | no_model_form | 0.12 | 0.36 | 0.36 | 1.00 |
| 200 | 40 | mass3pct | 0.12 | 0.39 | 0.46 | 1.18 |
| 200 | 40 | mass1pct | 0.12 | 0.39 | 0.46 | 1.18 |
| 200 | 40 | no_model_form | 0.12 | 0.34 | 0.40 | 1.18 |

**Simulation-calibrated MDC (frozen estimator; 40 dB only)**

| N per period | SNR (dB) | MDC (%) | SE inflation | Calibrated MDC (%) | Source |
|---|---|---|---|---|---|
| 50 | 20 | 0.71 | 1.00 | 0.71 | relative_intervals.json (CRB, no model-form term) |
| 50 | 40 | 0.72 | 1.39 | 1.00 | relative_coest_drift.json (coest, no drift) |
| 200 | 20 | 0.36 | 1.00 | 0.36 | relative_intervals.json (CRB, no model-form term) |
| 200 | 40 | 0.34 | 1.39 | 0.48 | relative_intervals.json (CRB, no model-form term) |


Source: `results/p2/relative_intervals.json`, `results/p3/calibrated.json`
