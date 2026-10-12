# Table 6. Model-form sensitivity and absolute bias budget (rail-coupled model)

| Parameter | 1σ (log) | Range source | Bias per +10% (%) | Nominal: bias at −1σ / +1σ (%) | k_f, k_H0 co-estimated: bias at −1σ / +1σ (%) |
|---|---|---|---|---|---|
| kf | 0.35 | CT23: in-situ ABA-derived kf 1.2-2.6x the lab value (Tables 2, 5 vs Sec. 5.1.1); section-to-section spread | +0.60 | -4.75 / +2.37 | +0.00 / -0.00 |
| eta_f | 0.20 | CT23 Sec. 5.1.1: literature loss factor 0.2-0.3 | +0.46 | -0.86 / +0.97 | -0.90 / +0.98 |
| kH0 | 0.15 | assumption: Hertz constant C_H for freight wheel/60E1 profiles not sourced (CT23 value is metro); wheel load from WIM | +0.35 | -0.34 / +0.67 | -0.00 / -0.00 |
| unsprung_scale | 0.03 | assumption: design mass known; wear and fittings | -12.10 | +3.62 / -3.62 | +3.65 / -3.72 |
| axle_damp_scale | 0.50 | assumption: axle damping is a placeholder (1% at 80 Hz); factor ~1.65 either way | -0.17 | +0.55 / -0.55 | +0.79 / -0.60 |

| Budget (RSS of worst-side 1σ terms) | Unsprung mass ±3% | Unsprung mass ±1% |
|---|---|---|
| Nominal fit | 6.1% | 5.1% |
| k_f, k_H0 co-estimated | 3.9% | 1.8% |


Large-sample (pseudo-true) biases. The ±3% unsprung-mass range is an assumption with no source; ±1% corresponds to mass known from drawings.

Source: `results/p2/model_form_mw_sensitivity.json`, `results/p2/relative_intervals.json`
