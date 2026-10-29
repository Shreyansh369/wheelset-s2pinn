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
| Simultaneous-error, rep j | (47, j, 0/1) | j = 0–38 | 39–77 | 78–129 | 130–199 |
| Zero-change, rep j (with its twin) | (47, j, 0/1) | j = 0–38 | 39–77 | 78–99 | – |
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
7. bound sweep at the re-frozen configuration. It is cheap, and gives the mass-distribution check (`\SweepWs*`).

## 5. Merging and the time stop

- **Merging:** this session merges the rows with `scripts/merge_rows_v2.py`.
  - It reads s0's files from its own tree and the others from `origin/claude/rows-sN`.
  - It removes duplicates by seed key (first occurrence kept, in session order) and writes the merged files
    (suffix `_v2`).
  - It records, for every merged row, the session, branch, file and the commit that added the row
    (`git blame`). The summary goes to `results/p5/merge_provenance.json`.
  - The summaries read only the merged files.
- **Time stop: 3 Nov 2026 06:00 UTC.**
  - The analysis uses every replicate committed by then, with a minimum of 100 each for the simultaneous-error
    and zero-change studies. The N achieved is reported.
  - This replaces the contiguity rule of preregistration_v2 §5. With four sessions the completed set is the
    lower part of each session's range, so it is not contiguous. No replicate is dropped for its result.
  - Priority items 5–7 that have not finished by then are reported from the earlier mass, labelled as
    robustness checks at that mass.
  - At the time stop the sibling sessions stop their workers.

## 6. Compute breakdown (core-hours and wall time)

FILLED

## 7. Sibling-session instructions

Each sibling is created at the pinned commit with the prompt in `docs/queues_v2/README.md`.

## 8. Pinned commit

FILLED
