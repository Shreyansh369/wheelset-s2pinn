# Preregistration v2 (29 Oct 2026)

Written and pushed before any v2 run, timing runs included. Results of the first pre-registration
(18 Oct 2026, `docs/paper1_outline.md`: κ study, zero-change study, A1 two-start, fit-order diagnostic, c_B
restart diagnostic) stay reported as they are, in their own columns and labelled "v1". Nothing below changes
how they were computed.

Code: `experiments/p5_v2.py` (corrected estimator, change studies) and `experiments/p5_timing.py` (Step 1
timing), committed with this file. Any later change to them is recorded in §7 with its reason, before the run
it affects.

## 1. Configuration and the corrected unsprung mass (review Major 1)

- **Frozen configuration:** `config/`, values-v2 hash `601c1afdbb42`: bare wheelset 1005 kg (FE axle 397 kg
  plus two 304 kg wheels) and two 100 kg axleboxes, i.e. 1205 kg unsprung per wheelset.
- **Corrected mass, sourced:** Dusza, Gołofit-Stawińska & Zboiński (2024), *Appl. Sci.* 14(11) 4545,
  Table A1, which the authors checked against the full text. Their Y25 multibody model has a 1400 kg wheelset
  and 100 kg axleboxes. The 1526 kg in the sweep has no citation and is not used.
  - The model wheelset is raised to 1400 kg by lumping (1400 − 1005)/2 = 197.5 kg on each journal.
  - The axleboxes stay at 2 × 100 kg, so the unsprung mass is 1600 kg per wheelset.
  - Dusza et al. give only the total; how the 395 kg is distributed is not published. Journal lumping is the
    placement already used in the sweep (`wheelset_mass_journals`, Table 15 of the PDF). It puts the added mass
    where the bearings and journal-mounted parts sit.
  - The "about 150 kg (estimated)" sentence is withdrawn.
- **Corrected-mass configuration:** `config/sensitivity/mass_dusza/` (values-v2 hash `e7e594eacc87`). It is
  identical to `config/` except `axle.journal_mass = 197.5 kg`.

**Route rule** (applied to the Step 1 timing in §6, before any long run):

- **Compute budget:** 72 h of wall time on the 4-core session machine, i.e. 288 core-hours. 30% of it is held
  back as a buffer, so the projected total must not exceed 72/1.3 = 55.4 h of wall time (221 core-hours with
  4 workers).
- **Projection:** for each study, the measured wall time per unit × the number of units, summed over the
  studies and divided by 4. Single-unit studies are counted as one worker-slot each.
- **Route A** if the full re-freeze of §3 (with N_SE = 100, the minimum) fits the budget. `config/` then takes
  the corrected mass and is re-frozen under a new hash, and every study in §3 is rerun on it.
- **Route B** otherwise. The frozen configuration stays, and the decisive studies (headline Monte Carlo,
  simultaneous-error study, zero-change study) run at the corrected mass as a robustness section. The parameter
  budget (about 10%) and the omitted-mass systematic (`\UnsprungOmitShift`) are then stated separately.
- **Replicate count:** N_SE = 200 if the chosen route still fits the budget with 200, otherwise the largest of
  150 or 100 that fits. N_ZC = 100.
- The chosen route and N_SE are recorded in §6 with the timing numbers before launch.

## 2. Corrected estimator, "xpr-1" (review Major 3)

**Base fit.** This is the frozen estimator, unchanged ("multipass-whittle-2", described in `config/provenance.yaml`):
- debiased Whittle likelihood with a ±120-bin kernel and own-sub-band scoring;
- K = 16 roughness levels and the payloads profiled out;
- k_B0, c_B, k_f, k_H0 estimated (the co-estimating fit), on log parameters;
- Nelder–Mead with `xatol` 1e-4, `fatol` 1e-3 and `maxiter` 200·d;
- initial simplex steps 0.15 / 0.3 / 0.2 / 0.2 in log k_B0, log c_B, log k_f, log k_H0;
- standard start k_B0 1 GN/m, c_B 5 kN s/m, and k_f and k_H0 at their nominal values.

**Cross-period restart**, for every change estimate between two periods:
1. Fit the baseline and the later period from the standard start.
2. Refit the baseline from the later period's estimate, and the later period from the baseline's estimate. The
   full parameter vector is copied unchanged, with no truth information. (The v1 A1 two-start study moved
   k_B0 to the period's own truth; xpr-1 does not.)
3. Per period, keep the solution with the lower negative log-likelihood. A restart replaces the standard-start
   fit only if it lowers the NLL by more than 0.01. Equal NLLs keep the standard-start fit, so the rule is
   deterministic.
4. The change is D̂ = log k̂_B0(later) − log k̂_B0(base). Its SE is the root of the sum of the two periods'
   squared SEs.

Single-period studies (headline Monte Carlo, A2 stiffness checks, model-form pseudo-true fits) have no
partner period. For them xpr-1 is the base fit.

**Stopping criteria.** A fit stops at the Nelder–Mead tolerances above or at `maxiter`. A replicate always
runs all four fits; there is no early stopping and no interim analysis.

**Singular information.** The observed information is the finite-difference profile Hessian (steps 0.005,
0.03, 0.01, 0.01).
- If it is not positive definite at the kept solution, the period is "singular". In practice this is c_B driven
  towards zero, i.e. log c_B < 0, flagged `cb_at_bound`.
- Its SE is then the expected-information SE of log k_B0 with c_B fixed at its kept estimate, evaluated at the
  *fitted* roughness levels and payloads. This uses no truth information; the v1 rule used the generating
  levels.
- Singular periods are counted and reported. Every statistic is also given with singular replicates counted
  as not covered.

**Failed fits.** A fit fails if Nelder–Mead reports no convergence, or the NLL or the estimate is not finite.
- Every failed fit, at either start, is appended to `results/p5/failed_fits.jsonl` with the study, replicate,
  period, start, reason, NLL, estimate, iterations, seed key and commit.
- A failed kept solution stays in every statistic as it is, with no exclusion.
- The paper points to the log and gives the count.

**Frozen-estimator column.** Each replicate row also carries the frozen estimator's result on the same data:
the standard-start fits only, with the same singular rule. §4 of the paper reports v1, frozen-on-v2-data and
xpr-1 in separate columns.

## 3. Run designs

All designs use 4-wheel rail coupling, the Y25/Eanos layout, 60E1 track, a ±120-bin kernel, 3% WIM error and
K = 16 roughness levels with a 3 dB spread, unless stated otherwise.

| Study | Route A | Route B | Design |
|---|---|---|---|
| Headline Monte Carlo | yes | yes (corrected mass) | 10 seeds × 10 datasets per noise level (20, 40 dB), N = 50, 60–110 km/h, payload 5.5–22.5 t, (k_B0, c_B) free; held-out calibration on two five-seed splits as v1 |
| Banded MDC | yes | no | bound cells: empty and laden band × N = 50, 200 × 20, 40 dB |
| Model-form budget | yes | no | pseudo-true fits, five parameters, ±10% and ±1σ (nominal estimator), ±1σ (co-estimating) |
| Zero-change study | yes | yes (corrected mass) | N_ZC = 100 pairs; replicate j has the draws and data seeds of simultaneous-error replicate j, true change 0 |
| Simultaneous-error study | yes | yes (corrected mass) | N_SE ≥ 100 (200 if the budget allows), §3.1 |
| Nonlinear-contact check | yes | no | 20 nonlinear and 20 linear datasets, 20 zero-change pairs (xpr-1 for the pairs) |
| A2 stiffness checks | yes | no | headline design at true k_B0 = 2.5 and 5 GN/m, 100 datasets per noise level each |

### 3.1 Simultaneous-error and zero-change design (review Major 2)

- **Band and design:** empty payload band (5.5–7 t, the band's primary values), 50 passes per period,
  60–110 km/h, 40 dB.
- **Model errors**, all five factors random and independent per replicate, with the v1 ranges
  (`experiments/p2_model_form_mw.RANGES`):
  - k_f, η_f, k_H0, unsprung mass and axle damping each take a factor exp(σ_p z), with z ~ N(0, 1);
  - k_f is stratified over the N_SE replicates: z_j = Φ⁻¹((π_j + 0.5)/N_SE), with π a fixed random permutation.
- **True change:** x ~ U(2%, 10%) in the simultaneous-error study, and 0 in the zero-change study.
- **Seeds:** draws from SeedSequence([47, j]); permutation from SeedSequence([47, 999, N_SE]); data keys
  (47, j, 0) and (47, j, 1). These are new; v1 used 45.
- **Coupling between the two studies:** zero-change replicate j shares draw j and its data keys with
  simultaneous-error replicate j, for j < N_ZC. Both use N = N_SE in the draw, so the strata are those of the
  simultaneous-error study.
- **Configuration:** the final one, i.e. `config/` re-frozen under Route A, or `config/sensitivity/mass_dusza`
  under Route B. The estimator is xpr-1.

## 4. Statistics and their uncertainty

All statistics are computed for xpr-1 (primary) and for the frozen estimator on the same data (secondary).

- **Coverage:** the fraction of simultaneous-error replicates whose Wald 90% interval D̂ ± 1.645·se covers
  D. It is also given counting singular replicates as not covered. 95% Clopper–Pearson interval, with the
  bootstrap percentile interval alongside.
- **Inflation factor:** F90 is the 90th percentile (numpy, linear) of r_j = |D̂_j − D_j|/(1.645·se_j) over the
  simultaneous-error replicates. It is the factor by which the Wald half-width must grow to cover 90%. Bootstrap
  95% percentile interval.
- **False-alarm rate (zero change):** the fraction with D̂ < −1.645·se (one-sided test for a loss). 95%
  Clopper–Pearson interval.
- **Calibration of the SE:** s0 = max(1, sd(z)), with z = D̂/se over the zero-change replicates.
- **Gain shrinkage:** g90 is the 90th percentile (numpy, linear) of e_j = (D_j − D̂_j)/D_j over the
  simultaneous-error replicates (positive when the change is underestimated).
- **Conservative MDC:**
  - MDC_cons = MDC_nom × s0/(1 − g90), for N = 50 and 200 passes in each payload band.
  - MDC_nom is the banded nominal MDC: one-sided 5% false alarm, 90% detection, (1.645 + 1.282)·√2·CRB.
  - Under Route B, MDC_nom stays at the frozen value and the factor comes from the corrected-mass studies. That
    combination is stated in the paper.
  - The factor is estimated in the empty band and applied to both bands; that assumption is stated.
  - Its uncertainty: B = 2000 bootstrap resamples, with the zero-change and simultaneous-error replicates drawn
    independently (fixed seed 4747), recomputing s0, g90 and MDC_cons. 95% percentile interval.
- **Detection probability at the conservative limit:**
  - For replicate j, P_j = Φ(2.927·(1 − e_j)/(1 − g90) − 1.645). This is the probability that a loss equal to
    MDC_cons is detected, given that replicate's gain error and the SE calibration s0.
  - P_det is the mean of P_j; its uncertainty comes from the same bootstrap.
- **Bootstrap generally:** B = 2000 resamples of replicates with replacement, percentile intervals, seed 4747.
  Proportions are reported with Clopper–Pearson as primary.
- **Headline, A2 and nonlinear-contact:** as v1 (bias ± SE, RMSE, CRB, RMSE/CRB, Wald coverage on finite SE
  with Clopper–Pearson, count of singular fits).

## 5. Decision rules

- **Wording of the result:**
  - The conservative MDC is reported as "an empirically conservative design threshold at N_SE replicates".
  - "Validated 90% detection" is used only if the bootstrap 95% lower bound of P_det is ≥ 0.90. Otherwise the
    paper gives P_det with its interval and does not use the word "validated".
- **Coverage:** if the Clopper–Pearson interval of coverage lies wholly below 0.90, the paper says the Wald
  interval under-covers under simultaneous model errors and gives F90 with its interval. Otherwise it says
  coverage is consistent with 90%.
- **False alarms:** if the Clopper–Pearson upper bound of the false-alarm rate exceeds 10%, the conservative MDC
  takes s0 from the zero-change z as defined above and the paper says so. No other rule changes.
- **Earlier results:** v1 results and the one-at-a-time gain study (`\KappaNominal`, `\KappaCoest`,
  `\KapNom*`, Table 7, Fig. 6) are moved to an appendix "Earlier-configuration exploratory results", or deleted
  if the main text no longer uses them.
- **Incomplete run:** if compute is not complete by 3 Nov 2026 23:59 IST, the analysis uses the completed
  replicates with the lowest indices (j = 0 … n−1, contiguous), reports n and says the run was cut short. No
  replicate is dropped for its result.

## 6. Step 1 timing and the route taken

(Filled in before launch, from `results/p5/timing.jsonl` and one replicate of each change study with
`--tag _timing`; those replicates are not part of any study.)

## 7. Deviations

(Any change after this file was pushed, with its date and reason, before the run it affects.)
