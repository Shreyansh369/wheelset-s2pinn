"""Job queues of the four preregistration-v2 sessions (docs/preregistration_v2_addendum.md), assigned up front.

Writes docs/queues_v2/s0.txt ... s3.txt, one shell command per line in launch-priority order:
  1 headline Monte Carlo, 2 banded MDC bounds, 3 simultaneous-error and zero-change replicates (a zero-change
  replicate runs right after its simultaneous-error twin, sharing the baseline fit), 4 model-form budget,
  5 nonlinear-contact check, 6 A2 stiffness checks, 7 bound sweep (cheap; distribution check of the mass) and small checks.
Every row file carries the session suffix _v2_sN (or _kb0_*_v2_sN), so sessions never write the same file.
Session s0 is the coordinating session (branch claude/inspiring-cori-690nu3); s1-s3 push claude/rows-sN.

    python3 scripts/make_queues_v2.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "queues_v2"
S = 4
N_SE, N_ZC = 200, 100
# change studies: the minimum set first (simultaneous-error replicates 0-99 each with its zero-change twin,
# 25 per session), then simultaneous-error replicates 100-199 (25 per session); contiguous ranges
PAIRS = {s: range(25 * s, 25 * s + 25) for s in range(S)}
SE_ONLY = {s: range(100 + 25 * s, 125 + 25 * s) for s in range(S)}
LOG = "results/p5/logs"


def q():
    jobs = {s: [] for s in range(S)}
    # 1 headline: 20 chunks of 10 datasets (KEYS order: 20 dB then 40 dB; seeds; j), chunk k -> session k mod 4
    for k in range(20):
        s = k % S
        jobs[s].append(f"python3 experiments/p3_headline_v2.py --kb 120 --attributed --ten --label _v2_s{s} "
                       f"--j0 {10 * k} --j1 {10 * k + 10} > {LOG}/hl_{k}.log 2>&1")
    # 2 banded MDC bounds (8 cells)
    jobs[0].append(f"python3 experiments/p4_banded.py --bounds --tag _v2_s0 > {LOG}/bounds.log 2>&1")
    # 3 change studies: minimum set (pairs), then replicates 100-199
    for s in range(S):
        for j in PAIRS[s]:
            jobs[s].append(f"python3 experiments/p5_v2.py --kind simerr --n {N_SE} --j0 {j} --j1 {j + 1} --tag _v2_s{s} > {LOG}/se_{j}.log 2>&1"
                           f" && python3 experiments/p5_v2.py --kind zero --n {N_SE} --j0 {j} --j1 {j + 1} --tag _v2_s{s} > {LOG}/zc_{j}.log 2>&1")
    for s in range(S):
        for j in SE_ONLY[s]:
            jobs[s].append(f"python3 experiments/p5_v2.py --kind simerr --n {N_SE} --j0 {j} --j1 {j + 1} --tag _v2_s{s} > {LOG}/se_{j}.log 2>&1")
    # 4 model-form budget: one job per estimator and parameter
    mf = [(e, p) for e in ("nominal", "coest") for p in ("kf", "eta_f", "kH0", "unsprung_scale", "axle_damp_scale")]
    for i, (e, p) in enumerate(mf):
        s = i % S
        jobs[s].append(f"python3 experiments/p2_model_form_mw.py --sensitivity --estimators {e} --params {p} --label _v2_s{s} "
                       f"> {LOG}/mf_{e}_{p}.log 2>&1")
    # 5 nonlinear contact: chunks of 5 datasets (nl, lin) and of 5 pairs; the restart chunk of a pair chunk
    # runs in the same session after it
    for i in range(4):
        s = i % S
        j0, j1 = 5 * i, 5 * i + 5
        for mode in ("nl", "lin", "pairs"):
            jobs[s].append(f"python3 experiments/p4_inverse_crime.py --mode {mode} --j0 {j0} --j1 {j1} --tag _v2_s{s} "
                           f"> {LOG}/ic_{mode}_{j0}.log 2>&1")
    for i in range(4):
        s = i % S
        j0, j1 = 5 * i, 5 * i + 5
        jobs[s].append(f"python3 experiments/p4_inverse_crime.py --mode pairsx --j0 {j0} --j1 {j1} --tag _v2_s{s} "
                       f"> {LOG}/ic_pairsx_{j0}.log 2>&1")
    # 6 A2: 20 chunks per stiffness, chunk k -> session k mod 4
    for kb in ("2p5", "5p0"):
        for k in range(20):
            s = k % S
            jobs[s].append(f"WHEELSET_CONFIG_DIR=config/sensitivity/kB0_{kb} python3 experiments/p3_headline_v2.py --kb 120 "
                           f"--attributed --ten --label _kb0_{kb}_v2_s{s} --kb0-from-config --j0 {10 * k} --j1 {10 * k + 10} "
                           f"> {LOG}/a2_{kb}_{k}.log 2>&1")
    # 7 bound sweep at the re-frozen configuration (resumable; two passes cover the 110-minute budget), and the
    # small checks that write rows or need minutes to an hour: ignore-coupling (10 fits), generator checks
    for _ in range(2):
        jobs[3].append(f"python3 experiments/p4_sweep.py --run --tag _v2_s3 >> {LOG}/sweep.log 2>&1")
    jobs[0].append(f"python3 experiments/p4_ignore_coupling.py --tag _v2_s0 > {LOG}/ignore_coupling.log 2>&1")
    jobs[0].append(f"python3 experiments/p4_generator_check.py > {LOG}/generator_check.log 2>&1")
    jobs[0].append(f"python3 experiments/p4_generator_expper.py > {LOG}/generator_expper.log 2>&1")
    return jobs


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s, js in q().items():
        (OUT / f"s{s}.txt").write_text("\n".join(js) + "\n")
        print(f"s{s}: {len(js)} jobs")
