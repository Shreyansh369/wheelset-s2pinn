# Preregistration v2 — addendum (29 Oct 2026): Route A on four sessions

Pushed before any long run. It adds to `docs/preregistration_v2.md` and does not change its estimator,
statistics or decision rules except where §5 says so.

## 1. Route and configuration

- **Route A**, with N_SE = 200 simultaneous-error replicates and N_ZC = 100 zero-change pairs (the authors'
  decision of 29 Oct).
- **Compute:** 16 cores. That is this session (s0) plus three sibling cloud sessions (s1–s3), 4 worker
  processes each.
- **Re-frozen configuration:** `config/` takes the corrected mass of preregistration_v2 §1 (Dusza et al. 2024,
  Table A1). The wheelset is 1400 kg with (1400 − 1005)/2 = 197.5 kg lumped on each journal, and the axleboxes
  stay 2 × 100 kg, giving 1600 kg unsprung.
  - The total mass is sourced; its distribution is our choice. The bound sweep compares the mass on the wheels
    with the mass on the journals (priority 7).
  - New frozen values-v2 hash: **e7e594eacc87**. It is identical to `config/sensitivity/mass_dusza`, which the
    Step 1 timing used.
  - The A2 configurations take the same mass: `config/sensitivity/kB0_2p5` (hash d5ebb6df862e) and `kB0_5p0`
    (hash 47be2e8881c1).
- **Earlier results:** results computed at the earlier frozen configuration (hash 601c1afdbb42) stay as they are
  and are labelled "earlier configuration" wherever they are still used.

## 2. Pinned code

- Every session runs the code at commit **PINNED** (§8).
- Sibling sessions write result rows only. They never change code, config or docs, never push any branch but
  their own, and never touch `main`.
- **Branches:** s0 is `claude/inspiring-cori-690nu3`; s1–s3 are `claude/rows-s1`, `claude/rows-s2` and
  `claude/rows-s3`.
- **Rows and keepalive:** rows are committed and pushed after every job by `scripts/persist_rows.sh`, with
  `ROWS_BRANCH` set to the session's branch. Each session keeps a tracked keepalive and an hourly check-in that
  restarts its workers after a container restart. Every job is resumable.
- **Row files:** every row file carries the session suffix (`_v2_sN`, A2: `_kb0_2p5_v2_sN`, `_kb0_5p0_v2_sN`),
  so no two sessions write the same file.

## 3. Seeds and work, assigned up front

The job list of every session is `docs/queues_v2/sN.txt` at the pinned commit, written by
`scripts/make_queues_v2.py`. Seeds are fixed by the replicate or dataset index, so the index sets below are
the disjoint seed ranges.

| Study | Seed key | s0 | s1 | s2 | s3 |
|---|---|---|---|---|---|
| Headline MC (200 datasets) | (seed, snr, j), KEYS index k = 0–199 | chunks 0, 4, 8, 12, 16 | 1, 5, 9, 13, 17 | 2, 6, 10, 14, 18 | 3, 7, 11, 15, 19 |
| Banded bounds (8 cells) | (48, N, snr) | all | – | – | – |
| Simultaneous-error, rep j | (47, j, 0/1) | j = 0–24, 100–124 | 25–49, 125–149 | 50–74, 150–174 | 75–99, 175–199 |
| Zero-change, rep j (with its twin) | (47, j, 0/1) | j = 0–24 | 25–49 | 50–74 | 75–99 |
| Model-form (estimator × parameter) | design (31, 0) | nominal k_f, axle damping; coest unsprung | nominal η_f; coest k_f, axle damping | nominal k_H0; coest η_f | nominal unsprung; coest k_H0 |
| Nonlinear contact | (60, j), (61, j, per) | j = 0–4 | 5–9 | 10–14 | 15–19 |
| A2, each stiffness (200 datasets) | KEYS index | chunks 0, 4, … | 1, 5, … | 2, 6, … | 3, 7, … |
| Bound sweep | one row per parameter end | – | – | – | all |

Headline chunk k covers KEYS indices 10k … 10k + 9, in KEYS order: 20 dB then 40 dB, seeds 42 123 456 789 1024
2048 3141 5772 8128 9973, then j 0–9. The queues give the exact commands.

## 4. Launch priority

Within every queue, jobs are in this order:
1. headline Monte Carlo (and with it the calibration: s0 and the held-out split by seed);
2. banded MDC bounds;
3. simultaneous-error and zero-change replicates; a zero-change replicate runs in the same job right after its
   twin, sharing the identical baseline fit;
4. model-form budget;
5. nonlinear-contact check (standard fits, then the cross-period restart of the pairs);
6. A2 stiffness checks;
7. bound sweep at the re-frozen configuration (cheap; it gives the mass-distribution check `\SweepWs*`), the
   ignore-coupling rows and the two generator checks (s0).

## 5. Merging and the time stop

- **Merging:** this session merges the rows with `scripts/merge_rows_v2.py`.
  - It reads s0's files from its own tree and the others from `origin/claude/rows-sN`.
  - It removes duplicates by seed key (first occurrence kept, in session order) and writes the merged files
    (suffix `_v2`).
  - It records, for every merged row, the session, branch, file and the commit that added the row
    (`git blame`). The summary goes to `results/p5/merge_provenance.json`.
  - The summaries read only the merged files.
- **Time stop: 3 Nov 2026 06:00 UTC. The time stop decides the final N.**
  - The analysis uses every replicate committed by then, with a minimum of 100 each for the simultaneous-error
    and zero-change studies. The N achieved is reported.
  - Each queue is ordered so that the minimum set lands first: simultaneous-error replicates 0–99, each with its
    zero-change twin, 25 per session (s0: 0–24, s1: 25–49, s2: 50–74, s3: 75–99). Then come replicates 100–199,
    25 per session (s0: 100–124, s1: 125–149, s2: 150–174, s3: 175–199).
  - This replaces the contiguity rule of preregistration_v2 §5. With four sessions the completed set is the
    lower part of each session's range, so it is not contiguous. No replicate is dropped for its result.
  - Priority items 5–7 that have not finished by then are reported from the earlier mass, labelled as
    robustness checks at that mass.
  - At the time stop the sibling sessions stop their workers.

## 6. Compute breakdown (core-hours and wall time)

Per-unit costs, single core with 4 workers per machine:
- **Measured at the corrected mass** (`results/p5/timing.jsonl`), each scaled by the frozen-run mean/median
  ratio for the tail:
  - headline fit 401 s, so 497 s mean;
  - A2 fit 337 s, so 390 s mean;
  - model-form pseudo-true fit 422 s (co-estimating 2.3× that);
  - nonlinear-contact dataset 423 s, so 463 s mean;
  - one bound cell 203 s.
- **Change-study fit (co-estimating, 4 parameters):** the authors' rule of 29 Oct sets it at 1.5 × the v1 time,
  **3000 s (50 min)**. The Step 1 timing replicate had not finished its first fit after 98 min, so the real cost
  may be higher. The 12-hourly progress reports give the measured mean and the projected N at the time stop.

| Priority | Study | Units | Core-h | Wall on 16 cores (h) |
|---|---|---|---|---|
| 1 | Headline Monte Carlo | 200 fits × 497 s | 27.6 | 1.7 |
| 2 | Banded MDC bounds | 8 cells | 0.3 | 0.0 |
| 3a | Minimum set: simultaneous-error 0–99 with zero-change twins | 100 × 7 fits × 3000 s | 583.3 | 36.5 |
| 3b | Simultaneous-error 100–199 | 100 × 4 fits × 3000 s | 333.3 | 20.8 |
| 4 | Model-form budget | 20 nominal + 10 co-estimating pseudo-true fits | 5.1 | 0.3 |
| 5 | Nonlinear contact | 80 datasets × 463 s + 40 restart fits × 392 s | 14.6 | 0.9 |
| 6 | A2 stiffness checks | 400 fits × 390 s | 43.3 | 2.7 |
| 7 | Bound sweep, ignore-coupling, generator checks | 31 cells, 10 fits, 2 checks | 5.1 | 0.3 |
| | **Total** | | **1012.6** | **63.3** |

- **Total wall time:** 63.3 h with ideal load balance (each session about 253 core-h, i.e. 63 h on 4 workers),
  or **82 h with the 30% buffer**.
- **Minimum set** (priorities 1–3a) reached after 38 h, 50 h with the buffer.
- **Available time:** launch on 29 Oct at about 19:00 UTC leaves 107 h to the time stop.
- The earlier figure of 59 h used 2500 s per change-study fit; at 3000 s it is 63 h.
- **If the measured fit cost is 2× the assumed one:** priorities 1–3a need 74 h, which still fits before the
  time stop. Replicates 100–199 and items 4–7 then fall to the time-stop rule of §5.

## 7. Sibling-session instructions

Each sibling is created at the pinned commit with the prompt in `docs/queues_v2/README.md`.

## 8. Pinned commit

**1ee4e3d4852406edc9026c38ab04b525c8e465e0** (`1ee4e3d`). It contains the re-frozen configuration, all run code, the queues and the sibling
instructions. This addendum is the next commit and changes no code.

## 9. Rerun-or-label inventory

The re-freeze turns every result of the earlier frozen configuration (601c1afdbb42 and earlier hashes) into an
earlier-configuration result. The table below lists every macro, table and figure the paper uses, grouped by
the result file it comes from. Each source is marked either "rerun in v2" (with its queue, or "at the final
regeneration" for deterministic bound or analytic results that take minutes) or "kept as labelled
earlier-configuration result" (with the section where the label appears). Nothing is unassigned. Written by
`scripts/v2_inventory.py`, which exits non-zero if a source has no disposition. The dispositions are the `v2`
entries of `config/provenance.yaml`.

**Enforcement.** `experiments/make_provenance_check.py` fails on any result that is neither rerun nor labelled:
- a file declared frozen fails unless it records the current frozen hash (a missing hash fails too);
- an earlier-configuration source fails unless every paragraph or caption that uses it carries the label;
- an earlier-configuration source fails in the abstract or conclusions under any condition.

It fails now, by design, and must pass at the final regeneration.

| Source | Tables | Figures | Macros (count: names) | Disposition |
|---|---|---|---|---|
| `config/params.yaml` | table1_parameters | – | 24: AxleboxMass, BandHi, BandLo, BearingOrderOR, BearingOrderORHi, BearingOrderORLo, ISOLambdaMax, ISOLambdaMinMM, ISONBands, LambdaMaxM, LambdaMinCM, LoadExp, NoiseBinsMax, NoiseBinsMin, NoiseHi, NoiseLo, NoiseRelSEMax, NumRevs, PayloadMax, PayloadMin, RecordLength, SampleRate, WIMsigmaPct, kBnom | configuration (re-frozen in v2: hash e7e594eacc87) |
| `config/track.yaml` | table1_parameters | – | 0: – | configuration (re-frozen in v2: hash e7e594eacc87) |
| `experiments/p1_fe_direct.py` | – | – | 4: cBstart, cBtruth, kBtruth, kBtruthBelowPct | simulation design constants (unchanged) |
| `results/gates/G1.json` | table2_verification | – | 0: – | rerun in v2: at the final regeneration (gate report) |
| `results/p1/bound_speed_subband.json` | – | fig2_crb_vs_speed_spread | 0: – | kept as labelled earlier-configuration result: Fig. 2 caption (Section 4.2) |
| `results/p1/fe_direct.json` | table4_speed_N | – | 4: SpeedCRBFixed, SpeedCRBNarrow, SpeedCRBWide, SpeedCRBWideTwoHundred | kept as labelled earlier-configuration result: Table 4 caption and Section 4.2 |
| `results/p1/verification.json` | table2_verification | – | 2: GyroRatio, NElements | rerun in v2: at the final regeneration (FE verification, minutes) |
| `results/p2/debias_check.json` | – | fig3_debiased_periodogram | 4: DebiasBin, DebiasDeb, DebiasNoise, DebiasRecords | kept as labelled earlier-configuration result: Fig. 3 caption (Section 3) |
| `results/p2/drift_freight.json` | table11_drift | – | 6: DriftCoestMDC, DriftSoftTenApparent, DriftSoftTenFA, DriftSoftTwentyApparent, DriftStiffTenMDC, DriftStiffTwentyMDC | kept as labelled earlier-configuration result: Section 4.5.4 Foundation drift and the Table 12 caption |
| `results/p2/fig1_transfer.json` | – | fig1_transfer_functions | 0: – | rerun in v2: at the final regeneration (make_figures.py) |
| `results/p2/model_form_mw_sensitivity.json` | table6_budget | fig5_model_form_tornado | 8: BudgetCoest, BudgetCoestInt, BudgetCoestMassOne, BudgetNominal, BudgetNominalMassOne, SensKf, SensUnsprung, UnsprungOmitShift | rerun in v2: Q4 (model-form, s0-s3) -> results/p2/model_form_mw_sensitivity_v2.json |
| `results/p2/multiwheel_bound.json` | table5_multiwheel | – | 4: MWCRBFixedMax, MWCRBFixedMin, MWCRBMax, MWCRBMin | rerun in v2: at the final regeneration (bound, minutes) |
| `results/p2/multiwheel_mc_y25.json` | table5_multiwheel | fig4_multiwheel_bias | 10: MWCorrectBiasEight, MWCorrectBiasFour, MWCorrectBiasSEEight, MWCorrectBiasSEFour, MWCorrectBiasSETwo, MWCorrectBiasTwo, MWCorrectZTwo, MWSingleBiasEight, MWSingleBiasFour, MWSingleBiasTwo | kept as labelled earlier-configuration result: Section 4.3 Multi-wheel coupling, the Fig. 4 and Table 6 captions |
| `results/p2/partial_coherence_bound.json` | table10_partial | – | 0: – | kept as labelled earlier-configuration result: Table 16 caption (Section 4.7) |
| `results/p2/partial_coherence_mc.json` | table10_partial | – | 0: – | kept as labelled earlier-configuration result: Table 16 caption (Section 4.7) |
| `results/p2/partial_indep.json` | table10_partial | – | 5: PCBiasMax, PCModelRatioMax, PCModelRatioMin, PCSandRatioMax, PCSandRatioMin | kept as labelled earlier-configuration result: Table 16 caption and Section 4.7 Repeated passes |
| `results/p2/relative_change.json` | – | fig6_relative_change | 0: – | kept as labelled earlier-configuration result: Fig. 6 caption (moves to Appendix A) |
| `results/p2/relative_coest_drift.json` | table7_gains | – | 5: KapNomCov, KapNomGainErr, KapNomHi, KapNomLo, KappaCoest | kept as labelled earlier-configuration result: Table 10 caption (moves to Appendix A) |
| `results/p2/relative_intervals.json` | table7_gains | fig6_relative_change | 2: KappaKfTerm, KappaNominal | kept as labelled earlier-configuration result: Table 10 and Fig. 6 captions (move to Appendix A) |
| `results/p2/scope_p2_hysteretic.json` | table12_p2 | fig7_p2_validation | 7: PTwoCTMedianCorr, PTwoCTOutsideClean, PTwoCTOutsideCorr, PTwoWhCovClean, PTwoWhCovCorr, PTwoWhMedianClean, PTwoWhMedianCorr | kept as labelled earlier-configuration result: Table 17 and Fig. 7 captions, Section 4.7 Track-side use |
| `results/p2/wheel_lines_bound.json` | table9_wheel_lines | – | 4: WLNone, WLNotchCost, WLTachoTen, WLTachoZero | kept as labelled earlier-configuration result: Table 13 caption and Section 4.5.4 Wheel roughness |
| `results/p2/wheel_lines_mc.json` | table9_wheel_lines | – | 0: – | kept as labelled earlier-configuration result: Table 13 caption (Section 4.5.4) |
| `results/p3/bearing_clearance.json` | table13_health | – | 27: AxleboxModeContactHz, ClearanceZero, ContactPctTenEmpty, ContactPctTenLoaded, CylEffTenEmptyMax, CylEffTenEmptyMin, CylEffTenLoadedMax, CylEffTenLoadedMin, CylGrowthMDCEmptyMax, CylGrowthMDCEmptyMin, CylGrowthMDCEmptyNom, CylGrowthMDCLoadedMax, CylGrowthMDCLoadedMin, CylGrowthMDCLoadedNom, DilutionEmpty, DilutionLoaded, EffPctTenEmpty, EffPctTenLoaded, HealthMDC, KcontactEmpty, KcontactLoaded, RollerLength, RollersPerRow, TapGrowthMDCEmptyMax, TapGrowthMDCEmptyMin, TapGrowthMDCLoadedMax, TapGrowthMDCLoadedMin | rerun in v2: at the final regeneration (analytic, minutes) |
| `results/p3/calibrated.json` | table3_headline, table8_mdc | – | 25: CalBiasForty, CalInflForty, CalSplitACov, CalSplitAHi, CalSplitAInfl, CalSplitALo, CalSplitAk, CalSplitAn, CalSplitBCov, CalSplitBHi, CalSplitBInfl, CalSplitBLo, CalSplitBk, CalSplitBn, CalTwentyRawCov, CalTwentySplitACov, CalTwentySplitAk, CalTwentySplitAn, CalTwentySplitBCov, CalTwentySplitBHi, CalTwentySplitBLo, CalTwentySplitBk, CalTwentySplitBn, MDCCalFiftyForty, MDCCalTwoHundredForty | rerun in v2: recomputed from the Q1 headline rows and the v2 MDC bounds at the final regeneration |
| `results/p3/calibration.json` | table16_kappa | – | 1: CalSlope | kept as labelled earlier-configuration result: Table 11 caption (moves to Appendix A) |
| `results/p3/drift_mc_freight.json` | table11_drift | – | 0: – | kept as labelled earlier-configuration result: Section 4.5.4 Foundation drift and the Table 12 caption |
| `results/p3/exponent_bound.json` | table13_health | – | 11: ExpCRBFifty, ExpCRBTwoHundred, ExpMDCFifty, ExpMDCTwoHundred, ExpShiftTen, ExpShiftTwenty, KBCRBExpFixed, KBCRBExpFree, KernelFine, KernelHalfWidth, PeffSeries | rerun in v2: at the final regeneration (bound, minutes) |
| `results/p3/headline_v2_kb120_attr_frozen10.json` | table3_headline | – | 25: HLBiasAbsMax, HLCBBoundN, HLCBBoundOf, HLCRBMax, HLCRBMin, HLFortyBias, HLFortyBiasSE, HLFortyCov, HLFortyCovHi, HLFortyCovLo, HLFortyRMSE, HLFortyRatioCRB, HLFortycBBias, HLN, HLRMSEMax, HLRMSEMin, HLRatioCRBMax, HLTwentyBias, HLTwentyBiasSE, HLTwentyCov, HLTwentyCovHi, HLTwentyCovLo, HLTwentyRMSE, HLTwentyRatioCRB, HLTwentycBBias | rerun in v2: Q1 (headline, s0-s3) -> results/p3/headline_v2_kb120_attr_v2.json |
| `results/p3/headline_v2_kb120_attr_kb0_2p5.json` | – | – | 4: AStiffTwoFiveCovMax, AStiffTwoFiveCovMin, AStiffTwoFiveRatioMax, AStiffTwoFiveRatioMin | rerun in v2: Q6 (A2, s0-s3) -> results/p3/headline_v2_kb120_attr_kb0_2p5_v2.json |
| `results/p3/headline_v2_kb120_attr_kb0_5p0.json` | – | – | 5: AStiffCRBFiveMax, AStiffCRBFiveMin, AStiffFiveFortyCov, AStiffFiveSingN, AStiffRatioMax | rerun in v2: Q6 (A2, s0-s3) -> results/p3/headline_v2_kb120_attr_kb0_5p0_v2.json |
| `results/p3/robust_se.json` | table16_kappa | – | 0: – | kept as labelled earlier-configuration result: Table 11 caption (moves to Appendix A) |
| `results/p3/validation_mc.json` | table16_kappa | – | 77: BandEmptyMDCFiftyConsGainMax, BandEmptyMDCFiftyConsGainMin, BandEmptyMDCFiftyConsInflMax, BandEmptyMDCFiftyConsInflMin, BandEmptyMDCFiftyConsMax, BandEmptyMDCFiftyConsMin, BandEmptyMDCTwoHundredConsMax, BandEmptyMDCTwoHundredConsMin, BandLadenMDCFiftyConsMax, BandLadenMDCFiftyConsMin, BandLadenMDCTwoHundredConsMax, BandLadenMDCTwoHundredConsMin, DriftMCCoestFA, DriftMCCoestHi, DriftMCCoestLo, DriftMCCoestMean, DriftMCCoestN, DriftMCNomFA, DriftMCNomHi, DriftMCNomLo, DriftMCNomMean, DriftMCNomN, FitOrderReps, KapAttrAllRsq, KapAttrAxleCorr, KapAttrAxleRsq, KapAttrAxleSpearman, KapAttrResidRMS, KapCBBoundN, KapCalCovered, KapCalHi, KapCalLo, KapCalN, KapCoestCovSingMiss, KapCoestCovSingMissHi, KapCoestCovSingMissLo, KapCoestCovered, KapCoestHi, KapCoestKfMax, KapCoestKfMin, KapCoestLo, KapCoestMean, KapCoestN, KapCoestNAll, KapCoestNSing, KapCoestRMS, KapGrossReps, KapInflNinety, KapInflOf, KapInflRank, KapRepThirtyFiveNLLGap, KapRepThirtyFiveRefitD, KapRepThirtyFiveTrueD, KapSingSECheckMaxDev, KapTwoStartCov, KapTwoStartCovHi, KapTwoStartCovLo, KapTwoStartCovSingMiss, KapTwoStartInfl, KapTwoStartN, KapTwoStartNFinite, KapTwoStartNSing, ZeroFA, ZeroFAHiPct, ZeroFALoPct, ZeroFAPct, ZeroFAReps, ZeroFiniteN, ZeroFiniteZsd, ZeroGNinety, ZeroMDCFactor, ZeroMeanZ, ZeroMeanZSE, ZeroN, ZeroNSing, ZeroSzero, ZeroZsd | kept as labelled earlier-configuration result: v1 preregistered studies (kappa, zero change, A1 two-start, fit order, c_B restart) in the v1 column of Section 4.5.1 and Appendix A; drift Monte Carlo (DriftMC*) in Section 4.5.4 Foundation drift; the conservative MDC macros (*Cons*) are replaced by the Q3 v2 summary (results/p5/v2_summary_v2.json) |
| `results/p4/banded.json` | – | – | 49: BandEmptyMDCFiftyMax, BandEmptyMDCFiftyMin, BandEmptyMDCTwoHundredMax, BandEmptyMDCTwoHundredMin, BandEmptyPairsFA, BandEmptyPairsFAHi, BandEmptyPairsFALo, BandEmptyPairsN, BandEmptyPseudo, BandEmptyZMax, BandEmptyZMin, BandLadenFixDMax, BandLadenFixPairsFA, BandLadenFixPairsN, BandLadenFixPseudoHalf, BandLadenFixPseudoOne, BandLadenFixPseudoTwo, BandLadenFixSE, BandLadenFixZMax, BandLadenFixZMin, BandLadenMDCFiftyMax, BandLadenMDCFiftyMin, BandLadenMDCTwoHundredMax, BandLadenMDCTwoHundredMin, BandLadenNSingular, BandLadenPairsN, BandLadenPseudo, LeanCorrMax, LeanMean, LeanMeanSE, LeanMeanZ, LeanOneMean, LeanOneN, LeanOnePos, LeanOneSE, LeanPoolN, LeanPoolZ, LeanPoolZHi, LeanPoolZLo, LeanSDOverSE, LeanSDPct, LeanSEPct, LeanTwoMean, LeanTwoN, LeanTwoPos, LeanTwoSE, LeanTwoZ, LeanZMean, LeanZSD | kept as labelled earlier-configuration result: payload-band stress test (pairs, pseudo-true, lean, laden c_B fixed) in Section 4.5.3 Payload bands; the MDC bounds (BandEmptyMDC*, BandLadenMDC*) are replaced by Q2 (results/p4/banded_v2.json) |
| `results/p4/bias_diag_y25.json` | table14_validation | – | 22: BDYHeadBias, BDYHeadBiasSE, BDYHeadRatio, BDYKFourRatio, BDYKOneCov, BDYKOneRatio, BDYKbMax, BDYKbMean, BDYSFBias, BDYSFRatio, BDYSixtyMax, BRegYN, BRegYP, BRegYRsq, RSEYBlockCov, RSEYBlockSE, RSEYModelCov, RSEYModelSE, RSEYN, ScoreExactMaxDiff, ScoreExactMeanDiff, ScoreExactSERatio | kept as labelled pinned-configuration result: bias diagnosis on the headline datasets (pinned headline configuration) |
| `results/p4/contact_hertz.json` | – | – | 3: KHZeroHertz, KHZeroHi, KHZeroLo | rerun in v2: at the final regeneration (analytic, seconds) |
| `results/p4/gain_y25.json` | – | – | 3: KapGainAxle, KapGainCoest, ZeroGainStudyGNinety | kept as labelled earlier-configuration result: Appendix A (Earlier-configuration exploratory results) |
| `results/p4/generator_check.json` | – | – | 4: GenBuildupMs, GenOpMisfitPct, GenRecMisfitPct, GenZetaHP | rerun in v2: Q7 (s0), rewrites this file |
| `results/p4/generator_expper.json` | – | – | 7: GenPgramDiff, GenPgramDiffSE, GenPgramN, ICPairsFACal, ICPairsFACalHi, ICPairsFACalLo, ICPairsN | rerun in v2: Q7 (s0), rewrites this file |
| `results/p4/ignore_coupling.json` | table3_headline | – | 4: IgnoreCouplingCovered, IgnoreCouplingForty, IgnoreCouplingFortySE, IgnoreCouplingN | rerun in v2: Q7 (s0) -> results/p4/ignore_coupling_v2.json |
| `results/p4/inverse_crime.json` | – | – | 29: GenN, GenPadN, GenPadcB, GenPadcBSE, GenPadkB, GenPadkBSE, GencB, GencBSE, GenkB, GenkBSE, ICContactLossMax, ICDeltaRmsMax, ICDiffMax, ICDiffMean, ICDiffSE, ICFDBias, ICFDcBBias, ICLinBias, ICLinBiasSE, ICLinCovCal, ICLinRMSE, ICLincBBias, ICNLBias, ICNLBiasSE, ICNLCovCal, ICNLCovCalHi, ICNLCovCalLo, ICNLN, ICNLRMSE | rerun in v2: Q5 (nonlinear contact, s0-s3) -> results/p4/inverse_crime_v2.json |
| `results/p4/mdc_bounds.json` | table8_mdc | – | 4: MDCFiftyForty, MDCFiftyTwenty, MDCTwoHundredForty, MDCTwoHundredTwenty | rerun in v2: at the final regeneration (bound, minutes) |
| `results/p4/primary_damping.json` | – | – | 8: PDCoestBias, PDLevelMax, PDLevelMin, PDPairsAbsZMax, PDPairsAbsZMin, PDPairsFA, PDPairsN, PDPairsSE | kept as labelled earlier-configuration result: Section 4.5.3 Mixed payloads |
| `results/p4/sweep.json` | table15_sweep | – | 25: SweepCRBMax, SweepCRBMin, SweepCpMDCHi, SweepCpMDCLo, SweepKBExtMDCHi, SweepKBExtModeHi, SweepKBMDCHi, SweepKBMDCLo, SweepKBModeHi, SweepMDCMax, SweepMDCMin, SweepModeMax, SweepModeMin, SweepNomCRB, SweepNomMDC, SweepNomMode, SweepWminCRBHi, SweepWminCRBLo, SweepWminHi, SweepWminLo, SweepWsJournalsCRBHi, SweepWsJournalsCRBLo, SweepWsJournalsModeLo, SweepWsWheelsCRBHi, SweepWsWheelsCRBLo | rerun in v2: Q7 (bound sweep, s3) -> results/p4/sweep_v2.json |
