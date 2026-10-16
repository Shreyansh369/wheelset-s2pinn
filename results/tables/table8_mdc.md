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
| 50 | 20.0 | 0.84 | 1.00 | 0.84 | p4/mdc_bounds.json (coest, CRB, current config) |
| 50 | 40.0 | 0.73 | 1.07 | 0.78 | p4/mdc_bounds.json (coest, CRB, current config) |
| 200 | 20.0 | 0.42 | 1.00 | 0.42 | p4/mdc_bounds.json (coest, CRB, current config) |
| 200 | 40.0 | 0.37 | 1.07 | 0.39 | p4/mdc_bounds.json (coest, CRB, current config) |


Source: `results/p2/relative_intervals.json`, `results/p3/calibrated.json`
