# Table 8. Minimum detectable decrease of k_B0 (5% false alarm, 90% detection), mixed payloads

| N per period | SNR (dB) | Estimated globals | CRB of k_B0 (%) | MDC from CRB (%) |
|---|---|---|---|---|
| 50 | 20 | k_B0, c_B (k_f, k_H0 fixed) | 0.184 | 0.76 |
| 50 | 20 | k_B0, c_B, k_f, k_H0 | 0.204 | 0.84 |
| 50 | 40 | k_B0, c_B (k_f, k_H0 fixed) | 0.165 | 0.68 |
| 50 | 40 | k_B0, c_B, k_f, k_H0 | 0.176 | 0.73 |
| 200 | 20 | k_B0, c_B (k_f, k_H0 fixed) | 0.092 | 0.38 |
| 200 | 20 | k_B0, c_B, k_f, k_H0 | 0.101 | 0.42 |
| 200 | 40 | k_B0, c_B (k_f, k_H0 fixed) | 0.083 | 0.34 |
| 200 | 40 | k_B0, c_B, k_f, k_H0 | 0.089 | 0.37 |

**Simulation-calibrated MDC (k_f, k_H0 re-estimated; calibration factor from the headline study, 40 dB only)**

| N per period | SNR (dB) | MDC (%) | SE inflation | Calibrated MDC (%) |
|---|---|---|---|---|
| 50 | 20 | 0.84 | 1.00 | 0.84 |
| 50 | 40 | 0.73 | 1.08 | 0.79 |
| 200 | 20 | 0.42 | 1.00 | 0.42 |
| 200 | 40 | 0.37 | 1.08 | 0.40 |


MDC = (1.645 + 1.282) √2 · CRB for two periods of N passes, 60–110 km/h, payload 5.5–22.5 t. Payload-band limits: Section 4 (results/p4/banded.json).

Source: `results/p4/mdc_bounds.json`, `results/p3/calibrated.json`
