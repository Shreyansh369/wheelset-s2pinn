# DRAFT GitHub issue for DMax1314/s2pinn: post only if the Nc=4096 run ends above threshold

Status: draft. Do not post until `results/p0/s2pinn_repro_seed42_nc4096.json` exists and
G0(a) fails. Before posting, fill the `<final ...>` fields with values from that file.

---

**Title:** Reproducing stochastic diffusion (Table 1 / Table 14): mean rel. L2 well above reported values with the released code

Hi, and thanks for releasing the code. I'm trying to reproduce the stochastic diffusion result and get much larger errors than the paper reports. My setup is below; I'd appreciate a pointer to whatever differs from your runs.

**Setup**
- Commit `1cd6fa2` (current `main`).
- `src/spinn/train.py` training loop with `configs/base.yaml`, overridden to the Appendix E defaults: R=5 (`kl.n_terms`=5), p=3, M=256, Mt=17, q=16, lr 1e-3, 20k Adam steps, all loss weights 1, `w_fac_orth`=0.1, `normalize_cp_every`=1, Gaussian Z, AMP off, no L-BFGS. Seed 42.
- CPU only, so PDE batch Nc=4096 (as with `--colloc 4096`); BC/IC batches 32768. Compared with Table 14 (Nc=4096: 6.34e-3).
- Metric: final `uq/mean_rel_l2` from `evaluate_uq`.

**Result:** mean rel. L2 = `<final mean>`, var rel. L2 = `<final var>` after 20k steps, against 6.34e-3 (Table 14) and 3.71e-3 (Table 1). Trajectory (every 500 steps): 0.95, 0.67, 0.24, 0.26, 0.27, 0.28, 0.28, 0.28, 0.27, 0.24, 0.22, … `<rest>`. A run at the default Nc=32768 behaved the same way up to step 1800: 0.50, 0.25, 0.26.

**Checks I ran**
1. The exact solution passed through `evaluate()` / `evaluate_uq()` gives mean/var rel. L2 = 0, so the evaluation is fine.
2. `compute_residual` on the exact solution (float64 autograd) is ~1e-14, so the source term and residual are consistent.
3. Training the same model on the exact solution by MSE (no physics) reaches mean rel. L2 ≈ 2.9e-2 after 1.5k steps and keeps falling, so representation isn't the limit.
4. In the physics-trained run, the BC and IC MSE stay at ~0.02 and ~0.012 while the PDE loss falls from 2 to 0.2. At step 5.4k the predicted mean overshoots the exact mean by 10–16%, with boundary RMS 0.07–0.18. It looks like loss balance between the PDE term and BC/IC.

**Questions**
1. Which config produced Tables 1 and 14? The README points to `configs/diffusion.yaml`, which isn't in the repo. `base.yaml` is the diffusion config but has R=3, while the paper uses R=5.
2. Were BC/IC weights, an LR schedule, L-BFGS, or hard BC/IC used for the reported runs?
3. `compute_gpc_projection_loss` averages r·Ψ over all (t, x, Z) tuples, but §3.2 describes a per-(t, x) projection over several Z draws. Which was used?
4. `gram_penalty` uses `.mean()` over M² entries, while Eq. (6) is a Frobenius norm, a factor M² apart. Which matches the reported runs?
5. The diffusion residual is u_t − k Δu − s (non-divergence form), while Appendix C writes ∇·(k∇u). Is that intended?
6. Table 14's Nc=32768 row gives 6.43e-3 but Table 1 gives 3.71e-3. Do they differ by seed set or config?
7. Minor: `configs/base.yaml` has a non-UTF-8 byte in a comment, so `load_config` fails on UTF-8 locales.
8. Minor: the exact solution itself scores calibration error ≈ 0.016 under `evaluate_uq` (finite-sample quantiles), above the 0.006 reported for S²-PINN. Is a different estimator used for Table 3?

Thanks!
