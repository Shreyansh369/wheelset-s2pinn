"""Headline Monte Carlo with the frozen estimator settings (rerun of experiments/p2_headline_mw.py).

Same data as the p2 headline (4-wheel rail-coupled model, keys (seed, snr, j), N = 50, 60-110 km/h,
seeds 42/123/456/789/1024 x 10, SNR 20 and 40 dB). Estimator: debiased Whittle with the +-Kb-bin kernel
(default 120), exact sub-band scoring (or --attributed: own-sub-band scoring, which agreed with exact to
0.006 pp on 3 datasets and is 5x faster), and optionally the random-walk smoothness prior on the log
sub-band levels (--smooth, dB). Wald 90% intervals from the observed profile information. Chunked by
--j0/--j1 over the 100 (snr, seed, j) keys with a 110-minute budget per process.
Rows: results/p3/headline_v2_runs/<tag>.jsonl; --aggregate -> results/p3/headline_v2_<tag>.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import SEEDS, START, TRUTH, WIM, setup, summarise as summ  # noqa: E402
from experiments.p2_multiwheel import dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

RUN_DIR = RESULTS_DIR / "p3" / "headline_v2_runs"
SEEDS_USED = list(SEEDS)    # --seeds overrides (10-seed rerun at the frozen configuration: SEEDS + SEEDS_EXTRA)
SEEDS_EXTRA = (2048, 3141, 5772, 8128, 9973)
KEYS = [(seed, snr, j) for snr in (20, 40) for seed in SEEDS for j in range(10)]
T0, BUDGET = time.perf_counter(), 110 * 60
FIT_MAX = [12 * 60]   # updated to the slowest fit seen in this process


LABEL = [""]   # appended to the run tag (e.g. "_freight" for the sourced-nominal rerun)


def tag_of(kb, smooth, exact=True):
    return f"kb{kb}" + ("" if exact else "_attr") + (f"_sm{smooth:g}" if smooth else "") + LABEL[0]


def run(j0, j1, kb, smooth, exact=True):
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fam = MultiWheelFamily(mw, thb)
    fp = RUN_DIR / f"{tag_of(kb, smooth, exact)}.jsonl"
    done = {tuple(json.loads(l)["seed_key"]) for l in fp.read_text().splitlines()} if fp.exists() else set()
    lt = math.log(TRUTH["kB0"])
    for key in KEYS[j0:j1]:
        if key in done:
            continue
        if time.perf_counter() - T0 + FIT_MAX[0] > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mw, key, N=50, snr=float(key[1]))
        est = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam, debias=True, Kb=kb, exact_subband=exact,
                               smooth_sigma_db=smooth)
        r = est.fit(np.log([START["kB0"], START["cB"]]))
        crb = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.log(g), np.log(Ws))["crb_log"]
        row = {"seed_key": list(key), "snr_db": key[1], "seed": key[0], "err_log": [r["phi"][0] - lt, r["phi"][1] - math.log(TRUTH["cB"])],
               "se_log": r["se_log"], "crb_log": crb, "converged": r["converged"], "wall_s": time.perf_counter() - t0}
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        with fp.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        FIT_MAX[0] = max(FIT_MAX[0], 1.3 * row["wall_s"])


def aggregate(kb, smooth, exact=True):
    tag = tag_of(kb, smooth, exact)
    R = [json.loads(l) for l in (RUN_DIR / f"{tag}.jsonl").read_text().splitlines() if l.strip()]
    cells = []
    for snr in (20, 40):
        Rs = [r for r in R if r["snr_db"] == snr]
        if not Rs:
            continue
        pooled = summ([r["err_log"][0] for r in Rs], [r["se_log"][0] for r in Rs], [r["crb_log"][0] for r in Rs])
        per_seed = [{"seed": s, **summ([r["err_log"][0] for r in Rs if r["seed"] == s], [r["se_log"][0] for r in Rs if r["seed"] == s],
                                       [r["crb_log"][0] for r in Rs if r["seed"] == s])} for s in SEEDS_USED if any(r["seed"] == s for r in Rs)]
        e = np.array([r["err_log"][0] for r in Rs])
        se = np.array([r["se_log"][0] for r in Rs])
        cells.append({"snr_db": snr, "kB0_pooled": pooled, "kB0_per_seed": per_seed,
                      "rmse_over_median_se": float(np.sqrt(np.mean(e**2)) / np.median(se)),
                      "sd_over_median_se": float(np.std(e, ddof=1) / np.median(se)),
                      "mean_err_log": float(e.mean()),
                      "cB_pooled": summ([r["err_log"][1] for r in Rs], [r["se_log"][1] for r in Rs], [r["crb_log"][1] for r in Rs]),
                      "all_converged": all(r["converged"] for r in Rs), "fit_s_median": float(np.median([r["wall_s"] for r in Rs]))})
    save_result(f"p3/headline_v2_{tag}", {"cells": cells}, cfg={"kernel_half_width_bins": kb, "smooth_sigma_db": smooth,
                                                                 "exact_subband": exact, "data": "keys (seed, snr, j), j < 10", "seeds": SEEDS_USED, "N": 50}, seed=SEEDS_USED[0])
    print(json.dumps(cells, indent=1)[:3000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--j0", type=int, default=0)
    ap.add_argument("--j1", type=int, default=100)
    ap.add_argument("--kb", type=int, default=120)
    ap.add_argument("--smooth", type=float, default=None)
    ap.add_argument("--attributed", action="store_true", help="default (own-sub-band) scoring instead of exact; 5x faster at Kb=120")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--label", default="", help="suffix of the run tag, e.g. _freight")
    ap.add_argument("--seeds", type=int, nargs="+", default=None, help="seeds (default 42 123 456 789 1024); 'ten' set via --ten")
    ap.add_argument("--ten", action="store_true", help="10 seeds: the 5 defaults and 2048 3141 5772 8128 9973")
    a = ap.parse_args()
    LABEL[0] = a.label
    if a.ten or a.seeds:
        SEEDS_USED[:] = list(SEEDS) + list(SEEDS_EXTRA) if a.ten else a.seeds
        KEYS[:] = [(seed, snr, j) for snr in (20, 40) for seed in SEEDS_USED for j in range(10)]
    aggregate(a.kb, a.smooth, not a.attributed) if a.aggregate else run(a.j0, a.j1, a.kb, a.smooth, not a.attributed)
