# Table 2. Verification of the reference model

| Check | Measured | Threshold | Gate |
|---|---|---|---|
| Free–free Timoshenko frequencies vs closed form (max rel. error, 4 modes) | 3.62e-03 | 5e-03 | PASS |
| Energy balance, windowed integral (max rel. residual, 3 cases) | 6.7e-11 | 1e-06 | PASS |
| Frequency vs time domain, axlebox accel. (max rel. L2, 3 cases) | 1.8e-06 | 1e-03 | PASS |
| Mesh 20 vs 40 elements, modes (max rel. diff.) | 2.0e-03 | – | – |
| Gyroscopic neglect, Ω/ω₁ | 0.101 | – | – |


Rail receptance vs CT23 Eq. 11 and the numerical inverse transform, and the single-wheel coupling identity (1e-9), are unit tests in `tests/test_track.py` (all pass).

Source: `results/p1/verification.json`, `results/gates/G1.json`
