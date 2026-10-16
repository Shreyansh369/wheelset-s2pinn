# Table 6. Model-form sensitivity and absolute bias budget (rail-coupled model)

| Parameter | 1σ (log) | Range source | Bias per +10% (%) | Nominal: bias at −1σ / +1σ (%) | k_f, k_H0 co-estimated: bias at −1σ / +1σ (%) |
|---|---|---|---|---|---|
| kf | 0.60 | rail pad 80-800 MN/m per pad at 0.60-0.65 m spacing -> 123-1333 MN/m^2 (Thompson et al. 2007; EUROBOLT; snippets) | +2.00 | -9.87 / -18.81 | +0.00 / -0.00 |
| eta_f | 0.23 | rail pad loss factor 0.1-0.25 (snippets) | -0.14 | +0.12 / -0.55 | +0.40 / -1.08 |
| kH0 | 0.13 | linearised contact stiffness 1.388 GN/m (Hertz, S1002 transverse radius +0.5 m) to 2.3 GN/m (published spread, Hasan 2020) | -0.44 | +0.62 / -0.46 | -0.00 / +0.00 |
| unsprung_scale | 0.04 | about 20 kg per axlebox, 4% of the wheelset unsprung mass, between axlebox designs (SKF Evolution, snippet) | -16.55 | +7.10 / -6.81 | +7.04 / -6.66 |
| axle_damp_scale | 0.75 | wheelset modal damping 0.1-2% (Chaar 2007: measured below 2%; IPME paper 0.1-1%; snippets) | +0.57 | -2.59 / +6.90 | -2.59 / +6.98 |

| Budget (RSS of worst-side 1σ terms) | Unsprung mass ±3% | Unsprung mass ±1% |
|---|---|---|
| Nominal fit | 6.1% | 5.1% |
| k_f, k_H0 co-estimated | 3.9% | 1.8% |


Large-sample (pseudo-true) biases. The ±3% unsprung-mass range is an assumption with no source; ±1% corresponds to mass known from drawings.

Source: `results/p2/model_form_mw_sensitivity.json`, `results/p2/relative_intervals.json`
