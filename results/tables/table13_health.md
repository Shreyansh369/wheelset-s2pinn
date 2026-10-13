# Table 13. Health relevance: clearance growth, effective support stiffness and the load exponent

**(a) Roller-contact stiffness and effective support stiffness against diametral clearance growth**

| Initial clearance (µm) | Load | Bearing load (kN) | k_contact (GN/m) | Contact: change, first 10 µm (%) | Contact: mean per 10 µm, 0–50 µm (%) | Contact: growth at MDC (µm) | k_B/k_contact | Effective k_B: change, first 10 µm (%) | Effective k_B: growth at MDC (µm) |
|---|---|---|---|---|---|---|---|---|---|
| 20 | empty | 22 | 5.90 | -6.18 | -4.17 | 0.8 | 0.17 | -1.10 | 6.4 |
| 20 | loaded | 105 | 7.78 | -2.02 | -1.84 | 3.7 | 0.13 | -0.26 | 27.4 |
| 0 | empty | 22 | 6.79 | -6.43 | -5.08 | 2.6 | 0.15 | -1.00 | 8.0 |
| 0 | loaded | 105 | 7.96 | -0.62 | -1.57 | 10.7 | 0.13 | -0.08 | 37.1 |
| 50 | empty | 22 | 5.07 | -3.85 | -2.94 | 0.5 | 0.20 | -0.78 | 7.3 |
| 50 | loaded | 105 | 7.33 | -1.80 | -1.62 | 2.8 | 0.14 | -0.25 | 27.4 |

**(b) Effective load exponent of the series model (reading B)**

| Clearance growth (µm) | p_eff (least squares over payload range) | p_eff (two-point) | k_B empty / loaded (GN/m) |
|---|---|---|---|
| 0.0 | 0.0271 | 0.0285 | 0.961 / 1.000 |
| 10.0 | 0.0323 | 0.0342 | 0.951 / 0.997 |
| 20.0 | 0.0367 | 0.0385 | 0.942 / 0.995 |

**(c) Bound on the load exponent (k_B0, c_B, p free; 4-wheel rail-coupled, 40 dB)**

| p at truth | N | CRB p (abs.) | CRB k_B0, p free (%) | CRB k_B0, p fixed (%) | Two-period MDC of p | Δp 10 µm (z) | Δp 20 µm (z) | Detectable 10 / 20 µm |
|---|---|---|---|---|---|---|---|---|
| 0.100 | 50 | 0.0034 | 0.26 | 0.17 | 0.0141 | 0.0053 (1.5) | 0.0097 (2.8) | no / no |
| 0.100 | 200 | 0.0019 | 0.14 | 0.08 | 0.0077 | 0.0053 (2.9) | 0.0097 (5.2) | no / yes |
| 0.027 | 50 | 0.0033 | 0.25 | 0.16 | 0.0136 | 0.0053 (1.6) | 0.0097 (2.9) | no / no |
| 0.027 | 200 | 0.0018 | 0.13 | 0.08 | 0.0074 | 0.0053 (3.0) | 0.0097 (5.4) | no / yes |


Bearing geometry, initial clearance and k_housing are placeholders (config/params.yaml). MDC = 0.71% (N = 50, 40 dB, co-estimating fit). z = Δp / CRB of a single period; detection between two periods needs Δp ≥ 2.93·√2·CRB.

Source: `results/p3/bearing_clearance.json`, `results/p3/exponent_bound.json`
