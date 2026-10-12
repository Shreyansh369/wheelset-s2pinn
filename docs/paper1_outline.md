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
2. **Detection** (one-sided, 5% false alarm, 90% detection; rail-coupled model, 60–110 km/h, 40 dB).
   - Minimum detectable change **0.71% at N = 50** passes per period with per-period co-estimation
     of k_f and k_H0. That is the same as with k_f, k_H0 fixed and no drift (0.71%), so co-estimation
     costs nothing in MDC (`relative_coest_drift.json`). N = 200 gives 0.4% (`relative_intervals.json`).
   - **Seasonal foundation drift breaks the fixed-k_f fit.** With k_f fixed at nominal, a later-period
     foundation 10% / 20% softer reads as a bearing softening of −0.67% / −2.0%. The false-alarm rate
     becomes 0.87 / 1.00. A stiffer foundation masks real loss: MDC rises to 1.2% / 1.8%. With
     per-period co-estimation, the false-alarm rate stays at 0.050 and the MDC at 0.71% for every drift
     level (Table 11).
3. **Interval.** Δ̂ ± 1.645·√(se² + (κ·Δ̂)²).
   - With the fixed-k_f fit, κ = 0.26 **failed revalidation**. On a fresh Monte Carlo with all five
     misspecifications drawn from their 1σ ranges (n = 20), coverage was 0.70 [0.46, 0.88]. The rms
     relative-change error was 0.42 of Δ, not 0.26. All six misses have k_f ≥ 1.45× nominal: the
     gain grows faster than linearly in k_f. At ×2.7 the estimate was +1.9% for a true −9.6% change.
   - **Headline interval: per-period co-estimation, κ = 0.044.** Contributions: unsprung mass 0.039,
     η_f 0.017, axle damping 0.009; k_f and k_H0 contribute ~2e-5. **Not yet revalidated** on a fresh
     random-misspecification Monte Carlo (missing item 4).
4. **Absolute k_B0 is reported only with its model-form budget.**
   - Nominal model: 6.1% RSS at 1σ, or 5.1% if the unsprung mass is known to ±1%.
   - Foundation and contact stiffness co-estimated: 3.9%, or 1.8% with mass to ±1%.
   - The unsprung mass enters about 1:1 (−12% bias per +10% mass error).
   - On the fresh random-misspecification Monte Carlo, the rms absolute bias (nominal fit) was 10.2%,
     against the 6.1% one-at-a-time RSS budget: the same nonlinearity in k_f.
5. **The rail-coupled multi-wheel model is necessary.** On the 4-wheel headline data, the
   single-wheelset fit is biased by −13.9% / −14.0% at 20 / 40 dB, with 0/10 coverage. On 2–8-wheel
   data the bias is −9 to −14%.

## Section-by-section map

| § | Content | Figure / table | Script → result |
|---|---|---|---|
| 1 | Introduction. Positioning: CT23's conclusion asks for a reliable way to reject bad P2 stiffness estimates; Pieringer & Kropp name joint estimation as open; drive-by speed diversity (Jin, Yang et al. 2021); Bayesian FFT (Au) | — | `docs/lit_review_fe_direct.md` (novelty caveats C1–C9) |
| 2.1 | Wheelset model: stepped Timoshenko FE, bearings k_B = k_B0 (W/W0)^0.1, axleboxes, primary suspension | **Table 1** parameters with sources | `config/params.yaml`, `config/track.yaml` → `experiments/make_tables.py` → `results/tables/table1_parameters.md` (vehicle masses stay placeholders until the target vehicle is confirmed) |
| 2.2 | Rail and multi-wheel coupling: Timoshenko rail on a hysteretic foundation, coupling with cross terms (CT23 Eqs. 5–11) | **Fig. 1** transfer functions for 1/2/4/8 wheels at 60 and 110 km/h | `src/analysis/multiwheel.py` → `results/p2/fig1_transfer.json` → `make_figures.py` (`figures/fig1_transfer_functions`) |
| 2.3 | Verification: G1 (free–free Timoshenko vs closed form 0.5%, energy 1e-6, frequency vs time domain 1e-3); rail receptance vs Eq. 11 and numerical inverse transform; single-wheel coupling = rail-oscillator model (1e-9) | **Table 2** | `make_tables.py`; `experiments/p1_verify.py` → `results/p1/verification.json`, `results/gates/G1.json`; `tests/test_track.py` |
| 3.1 | Observation model: 20-revolution records, DFT bins, roughness sub-band levels, WIM prior | — | `docs/method_notes.md` §1–2 |
| 3.2 | Identifiability: Fisher information and CRB; why speed diversity works; CRB vs speed spread and sub-band resolution K | **Fig. 2** CRB vs speed spread for K = 1…256 | `experiments/p1_bound_speed_subband.py` → `results/p1/bound_speed_subband.json` → `make_figures.py` (`fig2_crb_vs_speed_spread`) |
| 3.3 | Debiased Whittle likelihood (Sykulski et al. 2019): why the bin-sampled form fails with cross terms | **Fig. 3** averaged periodogram vs bin-sampled vs Fejér-convolved model | `experiments/p2_debias_check.py` → `results/p2/debias_check.json` (300 records, CT23 12-wheel setup: rms log ratio 0.47 bin-sampled vs 0.10 debiased, sampling noise 0.06) → `make_figures.py` (`fig3_debiased_periodogram`) |
| 3.4 | Profiling, Wald and profile intervals, pseudo-true bias | — | `docs/method_notes.md` §7–8 |
| 4.1 | Headline Monte Carlo on the final rail-coupled 4-wheel model: N = 50, 60–110 km/h, 5 seeds × 10 datasets, SNR 20/40 dB; the single-wheelset fit appears only as the ignore-coupling column (seed 42) | **Table 3** bias, RMSE/CRB, Wald and profile coverage | `experiments/p2_headline_mw.py` → `results/p2/headline_mw.json`. The single-wheelset rail-oscillator headline (`p2_headline.py` → `results/p2/headline.json`, `_noisefit`, `_debias`) moves to the supplement as the noise-floor diagnostic |
| 4.2 | Speed spread and N: fixed / 95–105 / 60–110 km/h, N = 50 / 200 | **Table 4** | `experiments/p1_fe_direct.py` → `results/p1/fe_direct.json` |
| 4.3 | Multi-wheel coupling: bound for 1/2/4/8 wheels; correct vs single-wheelset fit | **Table 5**, **Fig. 4** bias of the single-wheelset fit (`make_tables.py`, `make_figures.py`) | `experiments/p2_multiwheel.py` → `results/p2/multiwheel_bound.json`, `results/p2/multiwheel_mc.json` |
| 4.4 | Model-form sensitivity and bias budget (rail-coupled model) | **Fig. 5** tornado (% bias per 10% error and at ±1σ); **Table 6** budget | `experiments/p2_model_form_mw.py` → `results/p2/model_form_mw_sensitivity.json`; validation `results/p2/pseudo_true_check.json`, `results/p2/model_form.json` → `make_figures.py` (`fig5_model_form_tornado`), `make_tables.py` |
| 4.5 | **Relative change (main result)**: Δk_B0/k_B0 under misspecification vs absolute bias, nominal fit and with per-period co-estimation of k_f, k_H0; combined intervals; κ revalidated on a fresh Monte Carlo with misspecifications drawn from the 1σ ranges; minimum detectable change | **Fig. 6** estimated vs true change per misspecification; **Table 7** gains and κ; **Table 8** MDC for N = 50/200 × 20/40 dB | `experiments/p2_relative_change.py` → `results/p2/relative_change.json`; `experiments/p2_relative_intervals.py` → `results/p2/relative_intervals.json`; `experiments/p2_relative_coest_drift.py` (`--coest-rel`, `--kappa-mc`) → `results/p2/relative_coest_drift.json`; `make_figures.py` (`fig6_relative_change`), `make_tables.py` |
| 4.6 | Wheel roughness at rotation orders: notch vs tachometer lines | **Table 9** | `experiments/p2_wheel_lines.py` → `results/p2/wheel_lines_bound.json`, `results/p2/wheel_lines_mc.json` |
| 4.7 | Repeated passes over one section, partial coherence (ρ = 0.5/0.7/0.9, random lateral offsets): the main independent-pass estimator with model and sandwich SE; the exchangeable-ρ likelihood; the oracle bound | **Table 10** | `experiments/p2_partial_indep.py` → `results/p2/partial_indep.json`; `experiments/p2_shared_section.py` → `results/p2/partial_coherence_bound.json`, `results/p2/partial_coherence_mc.json` |
| 4.8 | Seasonal foundation drift between periods: k_f ×0.8/0.9/1.1/1.2 in the later period, true Δk_B0 = 0 and −5%; false-alarm rate and MDC with and without per-period co-estimation of k_f, k_H0; Monte Carlo check at k_f ×1.2 | **Table 11** | `experiments/p2_relative_coest_drift.py` (`--drift`, `--drift-mc`) → `results/p2/relative_coest_drift.json` |
| 4.9 | Validation against the CT23 P2 failure mode: the same multi-pass likelihood for track stiffness k_f on their simulated 12-wheel metro setup; per-pass peak fits vs multi-pass, with and without corrugation near P2 | **Fig. 7**, **Table 12** | `experiments/p2_scope_p2.py` → `results/p2/scope_p2_hysteretic.json`, `scope_p2_fractional.json` |
| 4.10 | Noise floor and window: taper vs rectangular; profiled floor | Supplementary table | `experiments/p1_fe_direct_taper_compare.py` → `results/p1/fe_direct_taper_compare*.json`; `p2_headline.py --fit-noise/--debias` |
| 5 | Discussion | — | — |
| 5.1 | Why not a physics-informed surrogate (FE-direct is exact; separable rank; veering) | Supplementary table | `experiments/p1_surrogate_rank.py` → `results/p1/surrogate_rank.json`; `docs/derivations/surrogate_vs_fe_direct.md` |
| 5.2 | Scope and follow-on work. Child A: route-scale track-stiffness mapping, plus wheel-radius / speed-bias confounding | — | — |
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

1. ~~Figures and tables~~: done. `experiments/make_figures.py` (Figs. 1–7 → `figures/`) and
   `experiments/make_tables.py` (Tables 1–12 → `results/tables/`) read only configs and `results/`.
2. ~~Debias check~~: done (`p2_debias_check.py`).
3. ~~Headline on the final model~~: done (`p2_headline_mw.py`). It shows a significant positive bias
   (open items).
4. **Revalidate κ = 0.044 (co-estimating fit)** on a fresh random-misspecification Monte Carlo, as
   was done for κ = 0.26 (`p2_relative_coest_drift.py --kappa-mc` with the coest family; about
   2 × 20 four-global fits).
5. **Drift Monte Carlo at k_f ×0.8.** The Monte Carlo check (n = 6) used ×1.2, where the fixed-k_f
   bias is positive and cannot raise false alarms. The false-alarm case (×0.8) is pseudo-true only.
6. **Parameter sources.**
   - All FE wheelset parameters (axle geometry, wheel and axlebox masses, primary suspension,
     bearing values) are placeholders in `config/params.yaml`. Vehicle masses stay placeholders
     until the target vehicle is confirmed.
   - The unsprung-mass uncertainty range has **no source**. ±3% is an assumption; ±1% assumes
     masses from drawings or weighed wheelsets. With co-estimation, unsprung mass dominates both κ
     and the absolute budget, so a cited mass and tolerance are needed.
   - The k_f range (σ_log 0.35, from CT23's lab vs in-situ spread) drives the nonlinearity above. A
     route-specific range would narrow it.
   - Indian-track values (60E1 profile data marked "verify", ballasted two-layer foundation,
     pad stiffness, freight layout) are flagged in `config/track.yaml`.
7. **Real-data validation.** None. Everything is synthetic, with generator and estimator built
   from the same model class. This is the main threat to the paper.
8. **Foundation frequency dependence at 450–700 Hz.** In the P2 check, the fractional vs hysteretic
   foundation mismatch gave about 7% bias in k_f. Not tested for k_B0.
9. **Literature.** Full-text checks of Shen et al. 2023 (MSSP 204) and the Chinese axle-box bearing
   papers.

## Open items (results that need an explanation)

- **Positive bias in rail-coupled fits: now the main open item.**
  - Rail-coupled headline (n = 50 per SNR): +0.11 ± 0.02% at 20 dB and +0.15 ± 0.03% at 40 dB (5–6
    SE). RMSE/CRB is 1.12 / 1.56 and Wald coverage 0.88 / 0.70 [0.55, 0.82]; c_B bias is +2.8% / +8.3%.
    The bias explains part of the 40 dB under-coverage: with the mean removed, the scatter is 0.92 ×
    CRB at 20 dB but still 1.30 × CRB at 40 dB, so the 40 dB excess is not bias alone. In relative change, a constant bias cancels; the control case shows
    +0.18 ± 0.10 pp.
  - Earlier MC: 2 wheels +0.24 ± 0.07% (RMSE/CRB 1.9, coverage 0.50); 4 wheels +0.12 ± 0.04%;
    8 wheels +0.04 ± 0.05%; relative-change control +0.18 ± 0.10 pp (n = 6).
  - Best hypothesis: an approximation in the debiased nuisance scoring. Each bin's kernel-smoothed
    variance is attributed to its own roughness sub-band (`_nuisance_solve`, debias branch), so
    the Fisher-scoring fixed point is not the exact profile maximum where the smoothed variance
    mixes sub-bands. That error grows where |H| changes fastest across the kernel; with 2 wheels,
    the bogie neighbour at 2.05 m gives the deepest, most regular coupling ripples.
  - Second candidate: the estimator interpolates the coupled components linearly on 0.5 Hz while
    the generator uses 0.25 Hz.
  - Test: refit with exact sub-band derivatives in the scoring step and with a 0.25 Hz estimator grid.
- **Single-wheelset benchmark headline, 40 dB: RMSE/CRB 1.18, coverage 0.82** (20 dB: 0.78 and 0.98).
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
- **P2 validation interval under corrugation.** The multi-pass point estimate stays within 2% of the
  truth, but the profile interval covers the truth in only 0.45 of sections (0.80 clean). Not diagnosed.
