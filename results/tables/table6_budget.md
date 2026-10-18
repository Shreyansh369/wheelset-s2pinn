# Table 6. Model-form sensitivity and absolute bias budget (rail-coupled model)

| Parameter | 1σ (log) | Range source | Bias per +10% (%) | Nominal: bias at −1σ / +1σ (%) | k_f, k_H0 co-estimated: bias at −1σ / +1σ (%) |
|---|---|---|---|---|---|
| kf | 0.60 | rail pad swept 80-800 MN/m per pad (published 105-800: Knuth et al. 2025; Thompson et al., Southampton eprint 436918) at 0.60-0.65 m spacing (Sanudo et al. 2022; Thompson et al.) -> 123-1333 MN/m^2 | +2.00 | -9.87 / -18.81 | +0.00 / -0.00 |
| eta_f | 0.23 | rail pad loss factor 0.1-0.25 (Jones & Edwards 1996: 0.1-0.3; Knuth et al. 2025: 0.15; Thompson et al., eprint 436918: 0.2/0.25) | -0.14 | +0.12 / -0.55 | +0.40 / -1.08 |
| kH0 | 0.13 | linearised contact stiffness 1.388-1.576 GN/m Hertz (S1002 transverse radius); upper sweep end 2.3 GN/m assumed | -0.44 | +0.62 / -0.46 | -0.00 / +0.00 |
| unsprung_scale | 0.04 | about 20 kg per axlebox, around 4% of the wheelset unsprung weight, between axlebox designs (SKF Evolution, New axlebox concept for heavy loads, 8 Dec 2005) | -16.55 | +7.10 / -6.81 | +7.04 / -6.66 |
| axle_damp_scale | 0.75 | wheelset modal damping 0.1-2% (Chaar 2007: measured less than 2%; Jin 2016 via Ahmedov & Mirsaidov 2023: 0.1-1%) | +0.57 | -2.59 / +6.90 | -2.59 / +6.98 |

| Budget (RSS of worst-side 1σ terms) | Unsprung mass 1σ = 4% | Unsprung mass known to 1% |
|---|---|---|
| Nominal fit | 21.3% | 20.1% |
| k_f, k_H0 co-estimated | 10.0% | 7.3% |


Large-sample (pseudo-true) biases at the current configuration. The 1σ ranges and their sources are listed in the table; the 1% mass case scales the unsprung-mass term linearly.

Source: `results/p2/model_form_mw_sensitivity.json`
