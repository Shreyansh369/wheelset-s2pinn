# Compute cost

Recorded single-core wall time (sum of per-row wall times in the run files), on the 4-core cloud machine used, often with all cores busy. Regenerate with `python3 experiments/make_compute_cost.py`.

| Study | Rows | Core-hours |
|---|---|---|
| Headline Monte Carlo (pinned) | 100 | 15.3 |
| Ignore-coupling fits | 10 | 1.6 |
| Drift Monte Carlo | 40 | 20.8 |
| Model-form sensitivity (pseudo-true) | 30 | 5.5 |
| Drift (pseudo-true) | 18 | 3.9 |
| Nonlinear contact and generator check | 113 | 11.9 |
| Primary suspension stress test | 5 | 3.2 |
| Payload bands | 38 | 18.7 |
| Bias diagnosis (headline datasets) | 0 | 0.0 |
| Multi-wheel Monte Carlo | 0 | 0.0 |
| Parameter sweep | 31 | 0.4 |
| **Total** | | **81.4** |

