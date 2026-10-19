# Status (updated 19 Oct 2026, 01:55 UTC)

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

## Monte Carlo queue (detached workers, 4 cores)

Order: zero-change κ study (40) → A1 two-start sensitivity (40) → zero-change singular-SE → A2 support stiffness at
k_B0 = 2.5 and 5 GN/m (40 chunks) → c_B restart diagnostic (14 reps left).

- Zero-change: 13 of 40 rows in (reps 0–12). Reps 2 and 8 are singular and get the c_B-fixed SE later in the queue.
- Container restarts so far: 18 Oct 17:36, about 20:20 and 21:35 UTC; 19 Oct about 01:50 UTC. Each one loses the
  in-flight jobs (at most 4 × about 1 h); the lost jobs were requeued at the front each time.
- A tracked watcher does not prevent the restarts (the 01:50 one came while a watcher was running). It and an hourly
  check-in mean the workers are restarted within about an hour.
- Remaining compute: about 134 core-h, so about 34 h on 4 cores. The estimated end is about 12:00 UTC on 20 Oct
  plus restart losses, against the deadline of 21 Oct 14:30 UTC (20:00 IST).

## Step-8 STOP

Abstract, highlights, conclusions and cover letter stay unchanged until the zero-change study is in and the authors
approve the old→new table. The cover-letter framing is a draft only (`docs/drafts/cover_letter_framing.md`).
