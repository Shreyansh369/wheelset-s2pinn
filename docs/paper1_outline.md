# Paper 1: proposed outline and frozen experiment list

Status: proposal. Experiments are frozen as of 2026-10-12, after this batch. Every number in the
paper must come from a `results/` JSON file produced by the scripts listed here. "Missing" marks
work that does not exist yet.

## Proposed title and main claim

**Title.** *Tracking wheelset bearing-support stiffness from in-service axle-box acceleration
without measuring rail roughness: a multi-pass debiased Whittle likelihood*

**Main claim: relative change is the headline.**
1. **Output.** The change of bearing-support stiffness relative to a baseline from the same
   vehicle and sensor, Δk_B0/k_B0. It is estimated from in-service axle-box acceleration over many
   passes, without measuring roughness.
   - Speed diversity separates roughness, which is fixed in wavenumber, from the support resonance,
     which is fixed in frequency.
   - The likelihood is a multi-pass Whittle likelihood, debiased for wheel-to-wheel cross terms.
     Roughness sub-band levels and the WIM payload are nuisances.
2. **Detection.**
   - Minimum detectable change (one-sided, 5% false alarm, 90% detection; rail-coupled model,
     60–110 km/h): **0.8% at N = 50** passes per period (0.94% with the 40 dB empirical inflation)
     and **0.4% at N = 200**. The figures are the same at 20 and 40 dB.
3. **Interval.** Δ̂ ± 1.645·√(se² + (κ·Δ̂)²), with κ = 0.26.
   - κ is the model-form gain uncertainty. It comes from pseudo-true fits over foundation
     stiffness, loss factor, contact stiffness, unsprung mass and axle damping, at realistic 1σ
     ranges. It is dominated by foundation stiffness (0.24).
   - It covered the true change in 18/18 Monte Carlo replicates across 3 cases (6 each; Clopper–
     Pearson 95% lower bound 0.54 per case).
   - The statistical-only interval covered 0/6, 2/6 and 4/6.
4. **Absolute k_B0 is reported only with its model-form budget.**
   - Nominal model: 6.1% RSS at 1σ, or 5.1% if the unsprung mass is known to ±1%.
   - Foundation and contact stiffness co-estimated: 3.9%, or 1.8% with mass to ±1%.
   - The unsprung mass enters about 1:1 (−12% bias per +10% mass error).
5. **The rail-coupled multi-wheel model is necessary.** A single-wheelset model on 2–8-wheel data
   biases k_B0 by −9 to −14%.

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
| 4.5 | **Relative change (main result)**: Δk_B0/k_B0 under misspecification vs absolute bias; combined intervals; minimum detectable change | **Fig. 6** estimated vs true change per misspecification; **Table 7** gains and κ; **Table 8** MDC for N = 50/200 × 20/40 dB | `experiments/p2_relative_change.py` → `results/p2/relative_change.json`; `experiments/p2_relative_intervals.py` → `results/p2/relative_intervals.json` |
| 4.6 | Wheel roughness at rotation orders: notch vs tachometer lines | **Table 9** | `experiments/p2_wheel_lines.py` → `results/p2/wheel_lines_bound.json`, `results/p2/wheel_lines_mc.json` |
| 4.7 | Repeated passes over one section, partial coherence (ρ = 0.5/0.7/0.9, random lateral offsets): the main independent-pass estimator with model and sandwich SE; the exchangeable-ρ likelihood; the oracle bound | **Table 10** | `experiments/p2_partial_indep.py` → `results/p2/partial_indep.json`; `experiments/p2_shared_section.py` → `results/p2/partial_coherence_bound.json`, `results/p2/partial_coherence_mc.json` |
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
| Model form | p2_model_form (rail oscillator, validation only), p2_model_form_mw (--sensitivity, --validate-pseudo, mass ±1% via --factors), p2_relative_change, p2_relative_intervals |
| Repeated passes | p2_partial_indep, p2_shared_section |
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
4. **Relative change with the co-estimating fit.** κ (0.26) is driven by foundation stiffness. In
   the absolute budget, co-estimating k_f and k_H0 removes those terms. That would cut κ to about
   0.05–0.06 if the same holds for changes, but this has not been computed: rerun
   `p2_relative_change.py` with the coest estimator.
   - The relative-change Monte Carlo has only 6 replicates per case and 3 cases.
5. **Parameter sources.**
   - All FE wheelset parameters (axle geometry, wheel and axlebox masses, primary suspension,
     bearing values) are placeholders in `config/params.yaml`.
   - The unsprung-mass uncertainty ranges have **no source**. ±3% is my assumption ("design mass
     known; wear and fittings"); ±1% assumes masses from drawings or weighed wheelsets. In the
     model, "unsprung mass" scales the whole wheelset mass matrix (axle, wheels at 350 kg each
     (placeholder), axleboxes at 60 kg each (placeholder)). The part that matters most is the
     mass carried on the bearings (axlebox, adapter, sensors). A cited mass, or weighing records,
     plus a tolerance are needed.
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
   papers.

## Open items (results that need an explanation)

- **Small positive bias in rail-coupled fits.**
  - Observed: 2 wheels +0.24 ± 0.07% (RMSE/CRB 1.9, coverage 0.50); 4 wheels +0.12 ± 0.04%;
    8 wheels +0.04 ± 0.05%; relative-change control +0.18 ± 0.10 pp (n = 6).
  - Best hypothesis: an approximation in the debiased nuisance scoring. Each bin's kernel-smoothed
    variance is attributed to its own roughness sub-band (`_nuisance_solve`, debias branch), so
    the Fisher-scoring fixed point is not the exact profile maximum where the smoothed variance
    mixes sub-bands. That error grows where |H| changes fastest across the kernel; with 2 wheels,
    the bogie neighbour at 2.05 m gives the deepest, most regular coupling ripples.
  - Second candidate: the estimator interpolates the coupled components linearly on 0.5 Hz while
    the generator uses 0.25 Hz.
  - Test: refit with exact sub-band derivatives in the scoring step and with a 0.25 Hz estimator grid.
- **40 dB headline RMSE/CRB 1.18, coverage 0.82** (20 dB is fine: 0.78 and 0.98).
  - A profiled noise floor changes nothing (1.18, 0.82). The debiased likelihood also changes
    nothing on 14 paired datasets (RMSE 0.277% vs 0.280%). Floor and leakage are ruled out.
  - Pooled with the earlier 20 datasets at 40 dB (RMSE/CRB 0.89), the overall ratio is about 1.10,
    roughly one sampling SE from 1.
  - Working conclusion: sampling variation. The MDC table also gives values inflated by 1.18.
- **Repeated passes over one section.**
  - The main independent-pass estimator is unbiased (≤ 0.09% bias; +0.09 ± 0.03% at ρ = 0.9) and
    is *not* overconfident. Its model SE is conservative: RMSE/SE 0.64–0.82, coverage 0.83–1.0.
  - The bin-clustered sandwich SE is calibrated (RMSE/SE 1.08–1.10, coverage 0.75–0.92), so it is
    the recommended SE for repeated passes.
  - The exchangeable-ρ likelihood gives no gain and is overconfident (coverage 0.50–0.75).
  - The oracle bound (known lateral offsets) is ≈0.004% and not attainable in practice.
