# Paper 1: proposed outline and frozen experiment list

Status: proposal. Experiments are frozen as of 2026-10-12, after this batch. Every number in the
paper must come from a `results/` JSON file produced by the scripts listed here. "Missing" marks
work that does not exist yet.

## Proposed title and main claim

**Title.** *Tracking wheelset bearing-support stiffness from in-service axle-box acceleration
without measuring rail roughness: a multi-pass debiased Whittle likelihood*

**Main claim (reframed around relative change, as the relative-change test supports).**
1. Bearing-support stiffness k_B0 can be identified from axle-box acceleration recorded over many
   passes, without measuring roughness.
   - Speed diversity separates roughness, which is fixed in wavenumber, from the support resonance,
     which is fixed in frequency.
   - A multi-pass Whittle likelihood treats the roughness sub-band levels and the WIM-measured
     payload as nuisances. It is debiased (exact expected periodogram) where wheel-to-wheel cross
     terms are present.
   - It reaches the Cramér–Rao bound: about 0.17–0.23% at N = 50 passes, 60–110 km/h.
2. Absolute k_B0 accuracy is limited by model form, not by data.
   - The bearing-supported (unsprung) mass enters about 1:1 (−12% k_B0 bias per +10% mass error).
   - The realistic 1σ bias budget is 6.1% RSS with a nominal model, or 3.9% when foundation and
     contact stiffness are co-estimated.
3. The robust output is the *change* of k_B0 relative to a baseline from the same vehicle.
   - With the same misspecified model in both periods, a 2/5/10% stiffness loss is recovered with a
     gain error of about 20% of the change or less.
   - Over the same misspecifications, absolute biases reach 6.5%.
4. The rail-coupled multi-wheel model is necessary.
   - A single-wheelset model fitted to data from 2–8 coupled wheels biases k_B0 by −9 to −14%.

## Section-by-section map

| § | Content | Figure / table | Script → result |
|---|---|---|---|
| 1 | Introduction. Positioning: CT23's conclusion asks for a reliable way to reject bad P2 stiffness estimates; Pieringer & Kropp name joint estimation as open; drive-by speed diversity (Jin, Yang et al. 2021); Bayesian FFT (Au) | — | `docs/lit_review_fe_direct.md` (novelty caveats C1–C9) |
| 2.1 | Wheelset model: stepped Timoshenko FE, bearings k_B = k_B0 (W/W0)^0.1, axleboxes, primary suspension | **Table 1** parameters with sources | `config/params.yaml`, `config/track.yaml` → **missing**: `experiments/make_tables.py` (Table 1 from configs) |
| 2.2 | Rail and multi-wheel coupling: Timoshenko rail on a hysteretic foundation, coupling with cross terms (CT23 Eqs. 5–11) | **Fig. 1** transfer functions for 1/2/4/8 wheels at 60 and 110 km/h | `src/analysis/multiwheel.py` → **missing**: figure script |
| 2.3 | Verification: G1 (free–free Timoshenko vs closed form 0.5%, energy 1e-6, frequency vs time domain 1e-3); rail receptance vs Eq. 11 and numerical inverse transform; single-wheel coupling = rail-oscillator model (1e-9) | **Table 2** | `experiments/p1_verify.py` → `results/p1/verification.json`, `results/gates/G1.json`; `tests/test_track.py` |
| 3.1 | Observation model: 20-revolution records, DFT bins, roughness sub-band levels, WIM prior | — | `docs/method_notes.md` §1–2 |
| 3.2 | Identifiability: Fisher information and CRB; why speed diversity works; CRB vs speed spread and sub-band resolution K | **Fig. 2** CRB vs speed spread for K = 1…256 | `experiments/p1_bound_speed_subband.py` → `results/p1/bound_speed_subband.json`; **missing**: figure script |
| 3.3 | Debiased Whittle likelihood (Sykulski et al. 2019): why the bin-sampled form fails with cross terms | **Fig. 3** averaged periodogram vs bin-sampled vs Fejér-convolved model | currently an ad-hoc check (inline script; numbers quoted in method notes) → **missing**: `experiments/p2_debias_check.py` writing a result JSON |
| 3.4 | Profiling, Wald and profile intervals, pseudo-true bias | — | `docs/method_notes.md` §7–8 |
| 4.1 | Headline Monte Carlo: N = 50, 60–110 km/h, 5 seeds × 10 datasets, SNR 20/40 dB | **Table 3** bias, RMSE/CRB, Wald and profile coverage | `experiments/p2_headline.py` → `results/p2/headline.json` (+ `_noisefit`, `_debias` diagnostics at 40 dB) |
| 4.2 | Speed spread and N: fixed / 95–105 / 60–110 km/h, N = 50 / 200 | **Table 4** | `experiments/p1_fe_direct.py` → `results/p1/fe_direct.json` |
| 4.3 | Multi-wheel coupling: bound for 1/2/4/8 wheels; correct vs single-wheelset fit | **Table 5**, **Fig. 4** bias of the single-wheelset fit | `experiments/p2_multiwheel.py` → `results/p2/multiwheel_bound.json`, `results/p2/multiwheel_mc.json` |
| 4.4 | Model-form sensitivity and bias budget (rail-coupled model) | **Fig. 5** tornado (% bias per 10% error and at ±1σ); **Table 6** budget | `experiments/p2_model_form_mw.py` → `results/p2/model_form_mw_sensitivity.json`; validation `results/p2/pseudo_true_check.json`, `results/p2/model_form.json`; **missing**: tornado figure script |
| 4.5 | **Relative change (main result)**: Δk_B0/k_B0 under misspecification vs absolute bias | **Fig. 6** estimated vs true change per misspecification; **Table 7** | `experiments/p2_relative_change.py` → `results/p2/relative_change.json` |
| 4.6 | Wheel roughness at rotation orders: notch vs tachometer lines | **Table 8** | `experiments/p2_wheel_lines.py` → `results/p2/wheel_lines_bound.json`, `results/p2/wheel_lines_mc.json` |
| 4.7 | Repeated passes over one section, partial coherence (ρ = 0.5/0.7/0.9, random lateral offsets) | **Table 9** | `experiments/p2_shared_section.py` → `results/p2/partial_coherence_bound.json`, `results/p2/partial_coherence_mc.json` |
| 4.8 | Noise floor and window: taper vs rectangular; profiled floor | Supplementary table | `experiments/p1_fe_direct_taper_compare.py` → `results/p1/fe_direct_taper_compare*.json`; `p2_headline.py --fit-noise/--debias` |
| 5 | Discussion | — | — |
| 5.1 | Why not a physics-informed surrogate (FE-direct is exact; separable rank; veering) | Supplementary table | `experiments/p1_surrogate_rank.py` → `results/p1/surrogate_rank.json`; `docs/derivations/surrogate_vs_fe_direct.md` |
| 5.2 | Scope: the same likelihood for P2 track stiffness (CT23 failure mode); in paper 1 or Child A (your decision) | **Fig. 7** per-pass CT23 fits vs multi-pass estimates, with and without corrugation | `experiments/p2_scope_p2.py` → `results/p2/scope_p2_hysteretic.json`, `scope_p2_fractional.json` |
| 5.3 | Limitations | — | see "Open items" |
| App. A | Rail receptance derivation (= CT23 Eq. 11) | — | `src/reference/track.py`, `tests/test_track.py` |
| App. B | Fisher information for the rank-one / partially coherent covariance | — | `src/inverse/variants.py` |
| App. C | Π gPC diagnostic (H1) and the S²-PINN reproduction (G0), if kept at all | — | `experiments/p0_h1_sdof.py`, `p0_reproduce_s2pinn_resumable.py` |

## Frozen experiment list (paper 1)

| Area | Scripts |
|---|---|
| Verification | p1_verify, tests/test_track |
| Bounds | p1_bound_speed_subband, p2_multiwheel (--bound), p2_wheel_lines (--bound), p2_shared_section (--bound) |
| Estimator Monte Carlo | p1_fe_direct, p1_fe_direct_taper_compare, p2_headline (plain, --fit-noise, --debias), p2_multiwheel (--mc), p2_wheel_lines (--mc), p2_shared_section (--mc) |
| Model form | p2_model_form (rail oscillator, validation only), p2_model_form_mw (--sensitivity, --validate-pseudo), p2_relative_change |
| Scope and discussion | p2_scope_p2, p1_surrogate_rank |

Superseded and not cited as results: p1_bound_scan, p1_bound_robustness, p1_bound_speed (the
single-line roughness model), and the `*_binsampled` result files (kept for transparency).

## Missing before drafting

1. **Figures.** No paper-figure scripts exist. Needed: `experiments/make_figures.py` for Figs. 1–7,
   reading only `results/`. Table 1 also needs `experiments/make_tables.py`.
2. **Debias check as a result file.** Fig. 3 is backed only by an inline check →
   `experiments/p2_debias_check.py`.
3. **Headline on the final model.** The five-seed headline and the speed-spread tables use the
   single-wheelset rail-oscillator model. The paper's final model is rail-coupled. Either rerun the
   headline on the 4-wheel rail-coupled model (≈5 min per fit), or state that the
   single-wheelset model is the statistical-performance benchmark.
4. **Relative-change coverage.** Statistical intervals under-cover once model-form error exceeds
   the SD of the change. The claim needs a gain-uncertainty term (e.g. ±20% of the change) or a
   stated detection threshold.
5. **Parameter sources.**
   - All FE wheelset parameters (axle geometry, wheel and axlebox masses, primary suspension,
     bearing values) are placeholders in `config/params.yaml`. The unsprung mass is now the dominant
     term in the budget, so it needs a cited value.
   - Indian-track values (60E1 profile data marked "verify", ballasted two-layer foundation,
     pad stiffness, freight layout) are flagged in `config/track.yaml`.
6. **Real-data validation.** None. Everything is synthetic, with generator and estimator built
   from the same model class. This is the main threat to the paper.
7. **Repeated passes over the same stretch with independent-section likelihood.** In service the
   same route is re-measured. Even unaligned records share |R_k|² over the same stretch, which
   violates the independence assumed across passes. Not tested.
8. **Foundation frequency dependence at 450–700 Hz.** In the P2 scope check, the fractional vs
   hysteretic foundation mismatch gave about 7% bias in k_f. Not tested for k_B0.
9. **Literature.** Full-text checks of Shen et al. 2023 (MSSP 204) and the Chinese axle-box bearing
   papers; the Sykulski et al. citation (cited from memory: verify).

## Open items (results that need an explanation)

- **2-wheel coupled fit bias +0.24 ± 0.07%** (RMSE/CRB 1.9, coverage 0.50; 4 and 8 wheels are
  fine). Best hypothesis: an approximation in the debiased nuisance scoring. Each bin's
  kernel-smoothed variance is attributed to its own roughness sub-band (`_nuisance_solve`,
  debias branch), so the Fisher-scoring fixed point is not the exact profile maximum where the
  smoothed variance mixes sub-bands. That error grows where |H| changes fastest across the
  kernel. With 2 wheels, the bogie neighbour at 2.05 m gives the deepest, most regular coupling
  ripples, so the error peaks there. Second candidate: the estimator interpolates the coupled
  components linearly on a 0.5 Hz grid while the generator uses 0.25 Hz.
  Test: refit the 10 datasets with exact sub-band derivatives in the scoring step, and with a
  0.25 Hz estimator grid.
- **40 dB headline under-coverage** (RMSE/CRB 1.18, Wald coverage 0.82; 20 dB is fine at 0.78 and
  0.98). Diagnosis runs: profiled floor and debiased likelihood at 40 dB; see
  `results/p2/headline_noisefit.json` and `headline_debias.json`.
- **Partial coherence.** The exchangeable-ρ estimator is overconfident (coverage 0.50–0.75) and
  gives no RMSE gain over independent sections. The oracle bound (lateral offsets known) is
  ≈0.004%, i.e. 50× better, but unattainable without lateral position.
