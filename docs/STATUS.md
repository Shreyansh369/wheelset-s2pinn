# Status (updated 18 Oct 2026, 22:05 UTC)

Branch `claude/inspiring-cori-690nu3`. `main` is untouched at `bae360d` until the authors' review. Submission target
24 Oct 2026 (25–30 Oct reserve); all compute to finish by 21 Oct 20:00 IST.

## Configuration identity

- Config hash is **values-v2** from 19 Oct 2026 (`src/utils/results.py: config_hash`). It is the sha256 of the parsed
  `params.yaml` + `track.yaml` with every `source` field and comment removed. Every result written from now on records
  `config_hash_version: values-v2`.
- Frozen config `config/`: values-v2 **b8adde501aa3**. The byte hash recorded in earlier results was e0a22f267362.
  Pinned snapshot `config/snapshots/headline_freight_v1`: values-v2 **77c60818b705** (byte hash 10d9b91451c2).
- `config/hash_aliases.yaml` maps the two byte hashes to their values-v2 hashes. `scripts/check_config_values.py`
  proves it: it compares the parsed values at f965b56, the commit with those byte hashes, against the current files
  and fails on any numeric or structural difference. It passes.
- `experiments/make_provenance_check.py` accepts a recorded hash that is the values-v2 hash, or a byte hash aliased to
  it, and says which. PASS, 0 failures; 12 result files are accepted through an alias. The 22 Oct final regeneration
  (`scripts/final_regenerate.sh`, clean tree required) rewrites all of them under values-v2, including
  `p1/verification.json` and `p2/fig1_transfer.json`.

## Table 1 sources

- Verified by full-text fetch (19 Oct 2026) and applied as source text only to the config, Table 1, Table 6
  (range sources), §2 citations, `refs.bib`, `docs/parameter_sources.md` and `docs/table1_sources_candidates.md`.
- No "[snippet]" label remains in `paper/`, `results/tables/` or `config/`.
- Deleted as unverified: k_B0 indications, Bustos 2025, Hasan 2020 (also from §2), Mu 2021, EUROBOLT, and
  Thompson 2007 as a value source.
- Open: k_B0, wheel diametral inertia, WJ/WJP internal geometry, mounted clearance, collar/section boundaries, the
  tapered-unit geometry. Also the bibliographic gaps flagged in `docs/reference_check.md`: Jin 2016 authors and
  title, the SKF Evolution 2022 title, author initials for Han et al. 2025, and missing URLs.
- W_min text now gives an empty axle load of 5.65–6.3 t. The sweep was not rerun and covers 5.8–6.6 t.

## Monte Carlo queue (detached workers, 4 cores)

Order: zero-change κ study (40) → A1 two-start sensitivity (40) → zero-change singular-SE → A2 support stiffness at
k_B0 = 2.5 and 5 GN/m (40 chunks) → c_B restart diagnostic (14 reps left). Zero-change reps 0–3 are running (restarted
21:36 UTC after the third container restart). Estimated end about 13:00 UTC on 20 Oct. A tracked keepalive watcher
and an hourly check-in guard against idle reclamation of the container.

## Step-8 STOP

Abstract, highlights, conclusions and cover letter stay unchanged until the zero-change study is in and the authors
approve the old→new table. The cover-letter framing is a draft only (`docs/drafts/cover_letter_framing.md`).
