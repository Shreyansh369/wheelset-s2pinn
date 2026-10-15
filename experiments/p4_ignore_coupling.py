"""Ignore-coupling check at the current configuration (Y25/Eanos layout, sourced nominals).

Data: the 4-wheel rail-coupled model (instrumented wheelset and the next three wheels of the wagon,
config/track.yaml: layout_freight) at the current config, generated exactly as the headline
(experiments/p2_multiwheel.dataset) for keys (42, 40, j), j = 0..9: N = 50 passes, 60-110 km/h, payload
5.5-22.5 t with 3% WIM error, K = 16 roughness levels with a 3 dB spread, 40 dB.
Fit: the frozen estimator (debiased Whittle, +-120-bin kernel, own-sub-band scoring, (k_B0, c_B) free)
with the single-wheelset model on the same rail, i.e. ignoring the neighbouring wheels.
Rows: results/p4/ignore_coupling_runs.jsonl (resumable, 110-minute budget); --summarise ->
results/p4/ignore_coupling.json.
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

from experiments.p2_common import START, TRUTH, WIM, setup  # noqa: E402
from experiments.p2_multiwheel import dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import RESULTS_DIR, save_result  # noqa: E402

FP = RESULTS_DIR / "p4" / "ignore_coupling_runs.jsonl"
KEYS = [(42, 40, j) for j in range(10)]
T0, BUDGET = time.perf_counter(), 110 * 60


def run():
    sm, thb, rough, _ = setup()
    mws = models(sm)[0]
    fam1 = MultiWheelFamily(mws["1"], thb)
    FP.parent.mkdir(parents=True, exist_ok=True)
    done = {tuple(json.loads(l)["key"]) for l in FP.read_text().splitlines()} if FP.exists() else set()
    lt, tmax = math.log(TRUTH["kB0"]), 12 * 60
    for key in KEYS:
        if key in done:
            continue
        if time.perf_counter() - T0 + tmax > BUDGET:
            print("deadline", flush=True)
            break
        t0 = time.perf_counter()
        P, Wm, Ws, g = dataset(sm, thb, rough, mws["4"], key, N=50, snr=float(key[1]))
        r = MultiPassWhittle([dict(q) for q in P], Wm, WIM, rough, fam1, debias=True).fit(np.log([START["kB0"], START["cB"]]))
        row = {"key": list(key), "err_log": r["phi"][0] - lt, "se_log": r["se_log"][0], "converged": r["converged"],
               "wall_s": time.perf_counter() - t0}
        with FP.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        tmax = max(tmax, 1.3 * row["wall_s"])


def summarise():
    R = [json.loads(l) for l in FP.read_text().splitlines() if l.strip()]
    e = np.array([r["err_log"] for r in R])
    se = np.array([r["se_log"] for r in R])
    out = {"n": len(R), "bias_pct": float(np.mean(np.exp(e) - 1) * 100),
           "bias_se_pct": float(np.std(np.exp(e) - 1, ddof=1) / math.sqrt(len(R)) * 100) if len(R) > 1 else None,
           "covered_90": int(np.sum(np.abs(e) <= 1.6448536269514722 * se)), "all_converged": all(r["converged"] for r in R)}
    save_result("p4/ignore_coupling", out, cfg={"data": "4-wheel freight layout, current config", "fit": "single wheelset, frozen estimator",
                                               "keys": "seed 42, 40 dB, j = 0..9"}, seed=42)
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()
    summarise() if a.summarise else run()
