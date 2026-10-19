# Status (updated 19 Oct 2026, 15:25 UTC)

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

## Zero-change study: complete, waiting for the authors' decision (19 Oct 15:10 UTC)

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
- **Not applied.** `validation_mc.json`, the macros and the freeze check are kept at the committed versions. The new
  outputs are in the session scratchpad. The authors' approval conditions (s0 1.0–1.2; no false alarms; MDC about
  1.0–1.1%) are met for s0 only, so the authors decide.

## Fit-order diagnostic (item 3, started 19 Oct 14:55 UTC)

- **Purpose:** the zero-change mean z is +0.27 ± 0.20 (n = 31). The diagnostic checks whether fitting both periods in
  one process could share state.
- **Design:** zero-change reps 0, 1, 3, 4 and 6. Each period is refitted alone in a fresh process, and the pair once in
  reversed order (later first) in one process. Rows go to `diag_order_zero_frozen.jsonl`. It runs on its own queue
  (`queue_diag.txt`, one worker, about 0.8 core) beside the main queue, about 20 fits in all.
- **Pass mark:** expected |Δphi| and |ΔD̂| < 1e-6. STOP if any |ΔD̂| > 1e-4.
- **What the paper's period-symmetry check is:** the §4 sentence "exchanging the period labels gives exactly −D" is
  an argument from the construction (each period fitted separately from the same start, no warm start). It is
  not a reversed-order refit; no reversed-order refit was run before this diagnostic.

## Monte Carlo queue (detached workers, 4 cores)

Order: zero-change κ study (40, **complete 19 Oct 14:35 UTC**) → zero-change singular-SE (9 reps; moved to the front,
done) → A1 two-start sensitivity (40; reps 0–2 in) → A2 support stiffness at k_B0 = 2.5 and 5 GN/m (40 chunks)
→ c_B restart diagnostic (14 reps left).

- **Persistence:** after every job the worker runs `scripts/persist_rows.sh`. It commits `results/**/*.jsonl`
  (diag_* rows on their own) under `.git/rows.lock` and pushes to this branch, with 3 tries and backoff.
  - Non-zero exits go to `results/p4/logs/queue_live.txt.errors`; the push log is `results/p4/logs/persist.log`.
  - Manual commits take the same lock.
- **Reporting:** a silent check-in about every hour restarts the workers after a container restart. Messages go out
  only when a study completes, a job errors, a push or check fails, or a decision is needed, plus one status line
  every 6 h. **Next status line: 19 Oct 20:50 UTC.**
- **Container restarts so far:** 18 Oct 17:36, about 20:20 and 21:35 UTC; 19 Oct about 01:50 and 15:15 UTC. Each one loses the
  in-flight jobs (at most 4 × about 1–3 h); the lost jobs are requeued at the front.
- **Estimated end:** main queue about 83 core-h left, so about 14:00 UTC on 20 Oct with the diagnostic on the
  fifth slot, plus restart losses. The deadline is 21 Oct 14:30 UTC (20:00 IST).

## Step-8 STOP

Abstract, highlights, conclusions and cover letter stay unchanged until the zero-change study is in and the authors
approve the old→new table. The cover-letter framing is a draft only (`docs/drafts/cover_letter_framing.md`).
