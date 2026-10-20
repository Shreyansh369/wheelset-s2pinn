# Status (updated 19 Oct 2026, 22:10 UTC)

Branch `claude/inspiring-cori-690nu3`. `main` is untouched at `bae360d` until the authors' review. Submission target
24 Oct 2026 (25–30 Oct reserve); all compute to finish by 21 Oct 20:00 IST.

## Configuration identity

- Config hash is **values-v2** from 19 Oct 2026 (`src/utils/results.py: config_hash`). It is the sha256 of the parsed
  `params.yaml` + `track.yaml` with every `source` field and comment removed. Every result written from now on records
  `config_hash_version: values-v2`.
- Frozen config `config/`: values-v2 **601c1afdbb42** (chain e0a22f267362 -> b8adde501aa3 -> 601c1afdbb42). The byte
  hash recorded in earlier results was e0a22f267362.
  Pinned snapshot `config/snapshots/headline_freight_v1`: values-v2 **77c60818b705** (byte hash 10d9b91451c2).
- `config/hash_aliases.yaml` maps the two byte hashes to their values-v2 hashes. `scripts/check_config_values.py`
  proves it: it compares the parsed values at f965b56, the commit with those byte hashes, against the current files
  and fails on any numeric or structural difference. It passes.
- `experiments/make_provenance_check.py` accepts a recorded hash that is the values-v2 hash, or a byte hash aliased to
  it, and says which. PASS, 0 failures; 14 result files are accepted through an alias chain. The 22 Oct final regeneration
  (`scripts/final_regenerate.sh`, clean tree required) rewrites all of them under values-v2, including
  `p1/verification.json` and `p2/fig1_transfer.json`.

## Table 1 sources

- Verified by full-text fetch (19 Oct 2026). Verbatim quotes and URLs are in `docs/table1_sources_candidates.md`.
  Applied as source text only to the config, Tables 1, 6 and 15, the §2 and §4 citations, `refs.bib`,
  `docs/parameter_sources.md` and `docs/reference_check.md`.
- No "[snippet]" label remains in `paper/`, `results/tables/` or `config/`.
- Deleted as unverified: k_B0 indications, Bustos 2025, Hasan 2020, Mu 2021, EUROBOLT, and Thompson 2007 as a value
  source.
- Tapered-unit geometry: now from Li et al. 2019 Table 3 (CHR380 EMU TRB), replacing Guan et al. 2023 in the config
  and in §4. Guan et al. stays cited in §1 as related work.
- Range ends:
  - Axlebox mass 158.4 kg: assumed (+58%).
  - k_H0: Hertz 1.388–1.576 GN/m; the 2.3 GN/m sweep end is assumed.
- Range fields (19 Oct 2026, commit d6ec9f1):
  - The axle-length range is dropped, the unverified tapered range ends (z 17/23, D 21.4/26.5 mm) are dropped, and
    W_min's range is now 5.6–6.6 t.
  - No computation reads these fields; only the Table 1 display does.
  - New values-v2 hash **601c1afdbb42**, chained b8adde501aa3 -> 601c1afdbb42 in `config/hash_aliases.yaml`. The link
    is a range-only proof: `check_config_values.py --range-only` finds the four named range fields as the only
    differences.
- W_min: the bound sweep runs over 5.6–6.6 t (new 5.6 t point; the stored 6.6 t point was recomputed bit-identical).
  CRB at the low end 0.16616% (it was 0.16629% at 5.8 t); the macros are unchanged at two decimals.
- Bibliography: every Table 1 source has a URL or DOI; Bizic & Petrovic 2024 DOI restored; li2019axlebox 11(4),
  April 2019 (DOAJ). guan2023 is cited only in §1 as related work (no number comes from it).
- Open (no verified source): k_B0, wheel diametral inertia, WJ/WJP internal geometry, mounted clearance,
  collar/section boundaries.

## Literature (19 Oct 2026, verified by full-text fetch)

- Novelty table: the Shen et al. 2023 row now covers six track parameters, a PSD with a level parameter, speeds
  7/10/13 km/h compared separately, ring-track rig validation and GP regression with 95% intervals.
- New rows: Stoura et al. 2023 and An et al. 2024. Cells not read in full text are n.r.
- §1: one sentence placing multi-pass drive-by (Keenahan et al. 2020) and joint input–state rail estimation (Stoura
  et al. 2023) relative to this paper.
- The "only relative vehicle properties" claim in `docs/lit_review_fe_direct.md` is re-attributed to Ren (2022, UCD
  PhD thesis). It isn't in the paper, so the thesis is not cited.
- refs.bib: stoura2023 and keenahan2020 added. The an2024 author list is incomplete (middle authors to confirm) and
  is flagged in `reference_check.md`.

## Zero-change study: complete and applied (approved 19 Oct; commits ddafb42 and the next one)

- 40 of 40 replicates, all converged. 9 have singular information (reps 2, 8, 14, 17, 20, 21, 34, 36, 38); they use the
  c_B-fixed sensitivity SE (0.0016–0.0024).
- Pre-registered result:

  | Statistic | Value |
  |---|---|
  | sd(z) | 1.165 |
  | s0 | 1.165 |
  | False alarms | 1/40 = 2.5%, Clopper–Pearson 0.06–13.2% (rep 8, a singular rep with the sensitivity SE, z = −2.22) |
  | g90 | 0.151 |
  | MDC factor s0/(1 − g90) | 1.373 |
  | Conservative MDC, empty band, N = 50 | 1.04–1.13% |
  | Conservative MDC, empty band, N = 200 | 0.48–0.53% |
  | Laden band | 2.81–2.93% (N = 50), 1.29–1.34% (N = 200) |
  | Inflation-factor comparison (ConsInfl, factor 1.248) | 0.94–1.03% (N = 50) |

- Finite-SE replicates only (n = 31): sd(z) 1.131, mean z 0.268, no false alarms.
- **Applied.** `validation_mc.json` is regenerated at clean commit ddafb42 (values-v2 601c1afdbb42, 20 input hashes);
  ZeroChangeDone = 1.
- **Conservative limit:** `\BandEmpty/LadenMDC*Cons*` hold the pre-registered value. `…ConsInfl…` (inflation factor,
  0.94–1.03%) and `…ConsGain…` (gain study, 1.282κ = 0.164 in place of g90: 1.05–1.15%) are agreement checks.
- **§4.5:** new paragraph "Detection limit allowing for simultaneous model errors".
- **Abstract, highlights, conclusions, cover letter:** no text change needed (the approved wording is already there
  through the macros); the rendered abstract is 244 words.
- **Lean sentence in §4:** applied 20 Oct (pooled lean, fit-order diagnostic passed).

## Typesetting fixes (19 Oct 2026)

- The abstract and conclusions now read "about 10%" via `\BudgetCoestInt`; the tables keep one decimal.
- Negative macro values are typeset with a true minus: `\minus`, which is `\ensuremath{-}`, works in text and math.
  This covers −5.6% and −0.74% in the abstract and conclusions, and every other negative macro.
- **Unsprung-mass sentence (§4.5)**, from the model's own mass build-up (bare wheelset 1005 kg + 2 × 100 kg
  axleboxes = 1205 kg), no RIVAS citation. Omitted bearings and journal-mounted parts "about 150 kg (estimated)"
  (the 15 kg-per-bearing figure is a supplier snippet only), so the truth is 1355/1205 = 1.124 × the model.
- `unsprung_scale` scales the TRUTH (whole wheelset mass matrix incl. axleboxes); the fit stays at nominal. A heavier
  truth gives a lower estimate.
- `\UnsprungOmitShift` = 18 is computed, not extrapolated: a pseudo-true fit at unsprung_scale = 1355/1205 (rows in
  `results/p2/model_form_mw_runs_freight/*__unsprung_scale.jsonl`, summary key `unsprung_omitted` in
  `model_form_mw_sensitivity.json`): nominal −18.297%, coest −18.160%, both converged. Table 6 (`table6_budget`,
  numbered Table 8 in the PDF) and the budget are unchanged. Text: "about 18% lower than the true value".
- §4 "Payload-dependent primary suspension" now ends: pooling over the whole payload range would need a
  payload-dependent model of the primary suspension (Section 5).
- Checks (19 Oct 22:10 UTC): freeze OK; provenance PASS, 0 failures; abstract 238 words (`make_submission.py`);
  highlights max 84 characters.

## A1 two-start sensitivity: complete (20 Oct 06:53 UTC; post-hoc, does not replace the pre-registered statistics; in §4.5)

- 40 of 40 kappa replicates. Rule: each period refitted from the other period's solution (k_B0 moved to its own
  truth), lower NLL kept.
- The refit was kept in 33 replicates, but D̂ moved by more than 1e-3 in only one: rep 35 (a local optimum, NLL gap
  about 37 800; |ΔD̂| = 0.62). Elsewhere the NLL gap is 0 to rounding and D̂ is unchanged.
- Coverage 0.87 (27/31 finite SE; CP 0.70–0.96), against 0.82 (0.65–0.93) pre-registered; singular counted as not
  covered 0.68 (pre-registered 0.70). Inflation factor for 90%: 1.04 (pre-registered 1.248). c_B at its lower bound
  after the refit in 15 replicates.
- Refit better by > 10 in NLL: 1 replicate (rep 35); refit gain < 0.01: 39 (same solution to rounding; in the JSON
  only). `\KapTwoStartChanged` now counts the first (1); the 33 "kept refit" ties stay in the JSON as `n_changed`.
- Finite SE 31 (not 34): 9 singular replicates (2, 8, 9, 14, 19, 29, 36, 38, 39) against 6 pre-registered (2, 8, 17,
  20, 21, 36). All 15 are at the c_B lower bound, where the information is near-singular: the Hessian re-evaluated
  at the same solution flips (e.g. rep 19 keeps both stored solutions, yet its base-period SE is now singular).
- §4.5 (after the rep-35 passage): post-hoc two-start sentence, with that clause; "the pre-registered values
  above stand". `validation_mc.json` regenerated at clean commit 5363254.

## Fit-order diagnostic: complete and passed (20 Oct 08:58 UTC)

- 15 of 15 rows: zero-change reps 0, 1, 3, 4, 6; each period refitted alone in a fresh process (base, later), and
  the pair in reversed order (later first) in one process. All converged.
- Against the stored rows: max |Δphi| = 0 and max |ΔD̂| = 0 exactly (also for D̂ formed from the two separate
  processes). No shared state between the fits.
- Pooled lean: the 31 finite-information zero-change replicates (mean z 0.268, sd 1.131) with the 20 empty-band
  zero-change pairs (mean z 0.497, sd 0.936): n = 51, mean z = +0.36, 95% t interval 0.06–0.65 (p = 0.02).
- §4 (empty-band pairs), revised 20 Oct on the authors' wording: pooled lean with its interval; the two periods are
  exchangeable and the fit-order refits reproduce every estimate, so the distribution is symmetric by
  construction and the pooled mean is sampling variation; the lean was noticed first in the empty-band pairs, so
  the pooled interval overstates the evidence; the zero-change study alone gives mean z = 0.27 ± 0.20
  (`\ZeroMeanZ`, `\ZeroMeanZSE`). The
  "exchanging the period labels gives exactly −D" sentence is now backed by the reversed-order refit.
- `validation_mc.json` regenerated at clean commit a9b1a43 with the complete `zero_change_fit_order` block.

## Simulation truth stated (20 Oct, approved)

- The simulation truth is hard-coded in `experiments/p1_fe_direct.py` (TRUTH k_B0 = 0.85 GN/m, c_B = 6.0 kN s/m;
  START 1.0 GN/m = the config nominal, 5.0 kN s/m) and used by every simulation study (headline, sweep nominal,
  banded MDC, kappa / zero-change). Macros `\kBtruth`, `\kBstart`, `\cBtruth`, `\cBstart`, `\kBtruthBelowPct` (15,
  computed from TRUTH and the config nominal; `\missing` if START differs from the nominal); source
  `experiments/p1_fe_direct.py`, declared frozen in `config/provenance.yaml` (not part of the config hash).
- §4.1: clause stating the truth and start; §2: "used throughout" -> "of the model"; §4 health paragraph: the
  effective-stiffness change is "(at the nominal \kBnom~GN/m)" (`p3_bearing_clearance.py` uses the config nominal).
- Grep of abstract, highlights, cover letter, captions and §1–§6: no other statement that the headline or the MDC
  refers to 1 GN/m.

## A2 support stiffness: text to apply on completion (authors' instruction 20 Oct; no abstract change)

- Prepared (commit 503e91d): `p3_headline_v2.py --aggregate` adds `n_singular`, `n_finite_se` and Wald coverage on
  finite SE; `make_paper_numbers.py` emits `\AStiff{TwoFive,Five}{Twenty,Forty}{Bias,BiasSE,RMSE,CRB,Ratio,Cov,
  CovLo,CovHi,NSing,N}`, `\AStiffRatioMin/Max`, `\AStiffCRB{TwoFive,Five}Min/Max` once both runs have 100 fits per
  SNR. Provenance class "sensitivity" is already declared in `config/provenance.yaml`.
- On completion: `WHEELSET_CONFIG_DIR=config/sensitivity/kB0_X python3 experiments/p3_headline_v2.py --kb 120
  --attributed --ten --label _kb0_X --kb0-from-config --aggregate` for X = 2p5, 5p0 (clean tree), then
  make_paper_numbers, make_tables, freeze, provenance, LaTeX, abstract 238, highlights <= 85.
- §4 "Parameter error", after "A softer support (0.5~GN/m) lowers the MDC to \SweepKBMDCLo\%.":
  "\paragraph{Support stiffness (sensitivity)}\label{sec:res-astiff} The headline design was repeated with the
  true $k_{B0}$ at 2.5 and 5~GN/m (sensitivity configurations, same relative start offset). At stiffer supports
  the estimator still attains the bound (RMSE/CRB \AStiffRatioMin--\AStiffRatioMax{} at 2.5 and 5~GN/m), but the
  bound grows as the support mode approaches the upper end of the analysis band (CRB
  \AStiffCRBFiveMin--\AStiffCRBFiveMax\% at 5~GN/m against \HLCRBMin--\HLCRBMax\% in the matched-model headline,
  Section~\ref{sec:res-headline}). The detection limit therefore depends on the actual support stiffness, which
  must be measured or bounded for a given vehicle (Section~\ref{sec:requirements})."
  (The authors wrote "\HLCRB\% at 1 GN/m": no \HLCRB macro exists, and the headline truth is 0.85 GN/m, so the
  headline range is cited instead.)
- §5 "Representative parameter values", after "(Table~\ref{tab:table15_sweep})": "; for the support stiffness
  the full estimator was also run at 2.5 and 5~GN/m, where it attains a larger bound
  (Section~\ref{sec:res-astiff})".
- Interim (5 GN/m, 161 of 200 fits, 10:30 UTC): RMSE/CRB 1.03 (20 dB), 1.18 (40 dB); CRB 1.45% / 1.26%; 7 singular.

## Monte Carlo queue (detached workers, 4 cores)

Order: zero-change κ study (40, **complete 19 Oct 14:35 UTC**) → zero-change singular-SE (9 reps; moved to the front,
done) → A1 two-start sensitivity (40, **complete 20 Oct 06:53 UTC**) → A2 support stiffness at k_B0 = 2.5 and 5 GN/m (40 chunks)
→ c_B restart diagnostic (14 reps left).

- **Persistence:** after every job the worker runs `scripts/persist_rows.sh`. It commits `results/**/*.jsonl`
  (diag_* rows on their own) under `.git/rows.lock` and pushes to this branch, with 3 tries and backoff.
  - Non-zero exits go to `results/p4/logs/queue_live.txt.errors`; the push log is `results/p4/logs/persist.log`.
  - Manual commits take the same lock.
- **Reporting:** a silent check-in about every hour restarts the workers after a container restart. Messages go out
  only when a study completes, a job errors, a push or check fails, or a decision is needed, plus one status line
  every 6 h. **Next status line: 20 Oct 22:25 UTC** (last one 20 Oct 16:25).
- **Container restarts so far:** 18 Oct 17:36, about 20:20 and 21:35 UTC; 19 Oct about 01:50, 15:15 and 16:10 UTC; 20 Oct 03:36 UTC (A1 reps 33, 36–38 and diag rep 4 reversed requeued).
  The container held for 13 h (01:51–15:15) while a tracked watcher was running, and was reclaimed within minutes of
  idle twice once it was stopped (14:47). A tracked keepalive (110-min sleep, no per-row wake-ups) now runs. Each one loses the
  in-flight jobs (at most 4 × about 1–3 h); the lost jobs are requeued at the front.
- **Estimated end:** main queue about 83 core-h left, so about 14:00 UTC on 20 Oct with the diagnostic on the
  fifth slot, plus restart losses. The deadline is 21 Oct 14:30 UTC (20:00 IST).

## Step-8 STOP

Abstract, highlights, conclusions and cover letter stay unchanged until the zero-change study is in and the authors
approve the old→new table. The cover-letter framing is a draft only (`docs/drafts/cover_letter_framing.md`).
